"""Read the ISO 9660 view of the original 2048-byte-sector MDF images.
Their redundant UDF view has malformed metadata; ISO extents are valid.
"""
from dataclasses import dataclass
from pathlib import Path
import struct

BLOCK = 2048


@dataclass(frozen=True)
class Entry:
    path: str
    extents: tuple[tuple[int, int], ...]


class Disc:
    def __init__(self, path: Path):
        self.path = path
        self.size = path.stat().st_size
        self.entries: dict[str, Entry] = {}
        with path.open('rb') as stream:
            stream.seek(16 * BLOCK)
            descriptor = stream.read(BLOCK)
            if descriptor[:7] != b'\x01CD001\x01':
                raise ValueError(f'{path.name}: expected ISO 9660 primary descriptor')
            if struct.unpack_from('<H', descriptor, 128)[0] != BLOCK:
                raise ValueError('Unsupported logical block size')
            self._walk(stream, descriptor[156:190], '', set())

    def _walk(self, stream, directory, prefix, visited):
        extent = struct.unpack_from('<I', directory, 2)[0]
        size = struct.unpack_from('<I', directory, 10)[0]
        if extent in visited:
            return
        visited.add(extent)
        if extent * BLOCK + size > self.size or size > 16 * 1024 * 1024:
            raise ValueError('Invalid directory extent')
        stream.seek(extent * BLOCK)
        data = stream.read(size)
        pos = 0
        children = []
        while pos < len(data):
            length = data[pos]
            if not length:
                pos = (pos // BLOCK + 1) * BLOCK
                continue
            record = data[pos:pos + length]
            if length < 34 or len(record) != length or 33 + record[32] > length:
                raise ValueError('Invalid ISO directory record')
            name_bytes = record[33:33 + record[32]]
            pos += length
            if name_bytes in (b'\x00', b'\x01'):
                continue
            name = name_bytes.decode('ascii').split(';')[0]
            path = f'{prefix}/{name}'
            if record[25] & 2:
                children.append((record, path))
                continue
            offset = struct.unpack_from('<I', record, 2)[0] * BLOCK
            length = struct.unpack_from('<I', record, 10)[0]
            if offset + length > self.size:
                raise ValueError(f'Invalid file extent: {path}')
            old = self.entries.get(path.casefold())
            segments = (() if old is None else old.extents) + ((offset, length),)
            self.entries[path.casefold()] = Entry(path, segments)
        for record, path in children:
            self._walk(stream, record, path, visited)

    def read(self, path: str) -> bytes:
        entry = self.entries[path.casefold()]
        with self.path.open('rb') as stream:
            parts = []
            for offset, length in entry.extents:
                stream.seek(offset)
                part = stream.read(length)
                if len(part) != length:
                    raise IOError('Truncated disc image')
                parts.append(part)
        return b''.join(parts)


def inventory(root: Path):
    result = {}
    for image in sorted(root.iterdir()):
        if image.suffix.lower() not in ('.mdf', '.iso'):
            continue
        disc = Disc(image)
        for entry in disc.entries.values():
            name = Path(entry.path).name
            if name.lower().endswith('.djvu'):
                result[Path(name).stem] = (image.name, entry.path)
    return result
