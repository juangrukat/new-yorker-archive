import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get('TNY_DATA', ROOT / 'data')).resolve()
SOURCE = Path(os.environ.get('TNY_SOURCE', '/Volumes/two1/the_complete_new_yorker')).resolve()
CATALOG = DATA / 'catalog.db'
PERSONAL = DATA / 'personal.db'
