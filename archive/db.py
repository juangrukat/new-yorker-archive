from contextlib import contextmanager
import sqlite3
from .config import CATALOG, DATA, PERSONAL


@contextmanager
def catalog():
    if not CATALOG.exists():
        raise RuntimeError('Import the archive first: python -m archive.importer')
    db = sqlite3.connect(CATALOG.as_uri() + '?mode=ro',uri=True)
    db.row_factory = sqlite3.Row
    try:
        yield db
    finally:
        db.close()


@contextmanager
def personal():
    db = sqlite3.connect(PERSONAL,timeout=15)
    db.row_factory = sqlite3.Row
    try:
        yield db
        db.commit()
    finally:
        db.close()


def setup_personal():
    DATA.mkdir(parents=True,exist_ok=True)
    with personal() as db:
        db.execute('PRAGMA journal_mode=WAL')
        db.executescript('''
          CREATE TABLE IF NOT EXISTS progress(issue_id INTEGER PRIMARY KEY,page INTEGER NOT NULL,updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
          CREATE TABLE IF NOT EXISTS bookmarks(issue_id INTEGER,page INTEGER,collection TEXT NOT NULL DEFAULT 'Reading list',note TEXT NOT NULL DEFAULT '',updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,PRIMARY KEY(issue_id,page));
        ''')
