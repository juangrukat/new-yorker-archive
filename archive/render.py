from functools import lru_cache
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading

from PIL import Image
from .config import DATA, SOURCE
from .discs import Disc
from .djvu import decode_data

_RENDER_SLOTS = threading.Semaphore(2)


@lru_cache(maxsize=5000)
def issue_lock(issue_id):
    return threading.Lock()


@lru_cache(maxsize=16)
def disc(name):
    path = SOURCE / name
    if path.parent != SOURCE:
        raise ValueError('Invalid source path')
    return Disc(path)


def run(args):
    try:
        result = subprocess.run(args,capture_output=True,timeout=90)
    except FileNotFoundError as error:
        raise RuntimeError('DjVuLibre is missing. Install djvulibre and restart.') from error
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors='replace')[:500] or 'DjVu decoding failed')


def document(issue):
    target = DATA / 'documents' / f'{issue["stem"]}.djvu'
    if target.exists():
        return target
    if not issue['image']:
        raise FileNotFoundError('This issue is not present in the connected disc images')
    target.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target.parent) as tmp:
        temp = Path(tmp)
        raw = disc(issue['image']).read(issue['member'])
        pending = temp / 'issue.djvu'
        if raw[:4] == b'AT&T':
            pending.write_bytes(raw)
        else:
            page_dir = temp / 'pages'
            count = decode_data(raw,page_dir)
            if count != issue['page_count']:
                raise ValueError(f'Catalog expects {issue["page_count"]} pages; file has {count}')
            run(['djvm','-c',str(pending),*[str(p) for p in sorted(page_dir.glob('page-*.djvu'))]])
        pending.replace(target)
    return target


def issue_document(issue):
    with issue_lock(issue['id']):
        return document(issue)


def page_image(issue, page, width):
    target = DATA / 'pages' / issue['stem'] / f'{page}-{width}.jpg'
    if target.exists():
        return target
    with issue_lock(issue['id']):
        if target.exists():
            return target
        djvu = document(issue)
        target.parent.mkdir(parents=True,exist_ok=True)
        with _RENDER_SLOTS, tempfile.TemporaryDirectory(dir=target.parent) as tmp:
            ppm = Path(tmp) / 'page.ppm'
            run(['ddjvu','-format=ppm',f'-page={page}',f'-size={width}x{width*2}',str(djvu),str(ppm)])
            jpeg = Path(tmp) / 'page.jpg'
            with Image.open(ppm) as image:
                image.convert('RGB').save(jpeg,quality=91,optimize=True)
            jpeg.replace(target)
    return target
