"""Decode TNY SDJV pages without the original app.
Format reference: https://gist.github.com/NoMoreNicksLeft/d3a4a59c7b4de0cdef1e26695606e51c
Independently validates chunk boundaries; writes only to a new directory.
"""
import argparse
import hashlib
from pathlib import Path
import struct
from Crypto.Cipher import Blowfish


def chunks(data, start, end):
    while start < end:
        if start + 8 > end:
            raise ValueError('Truncated chunk header')
        tag, size = struct.unpack_from('>4sI', data, start)
        first, last = start + 8, start + 8 + size
        if last > end:
            raise ValueError(f'Chunk {tag!r} exceeds container')
        yield tag, data[first:last]
        start = last + (size % 2)


def pack(tag, payload):
    return struct.pack('>4sI', tag, len(payload)) + payload + b'\0' * (len(payload) % 2)


def decode_data(data, destination):
    if data[:8] != b'SDJVFORM' or data[12:16] != b'DJVM':
        raise ValueError('Expected bundled SDJV')
    end = 12 + struct.unpack_from('>I', data, 8)[0]
    if end > len(data):
        raise ValueError('Truncated document')
    destination.mkdir(parents=True, exist_ok=False)
    key = hashlib.md5(b'secureDVD_UIDLizardTech_DVDKey_Internal_Salt').digest()
    pages = encrypted = 0
    for tag, payload in chunks(data, 16, end):
        if tag != b'FORM' or payload[:4] != b'DJVU':
            continue
        result = bytearray(b'DJVU')
        for kind, content in chunks(payload, 4, len(payload)):
            if kind in (b'SINF', b'INCL', b'CIDa', b'DVDK'):
                continue
            if kind == b'CELX':
                if len(content) < 12:
                    raise ValueError('Truncated CELX')
                kind, length, counter = struct.unpack_from('>4sII', content)
                ciphertext = content[12:]
                if len(ciphertext) % 8 or length > len(ciphertext):
                    raise ValueError('Invalid cipher length')
                iv = hashlib.md5(b'Blowfish' + struct.pack('>I', counter)).digest()[:8]
                content = Blowfish.new(key, Blowfish.MODE_CBC, iv).decrypt(ciphertext)[:length]
                encrypted += 1
            result.extend(pack(kind, content))
        pages += 1
        (destination / f'page-{pages:04}.djvu').write_bytes(b'AT&T' + pack(b'FORM', result))
    if not pages:
        raise ValueError('No pages found')
    return pages


