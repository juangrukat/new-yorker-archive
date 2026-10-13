"""Build a standalone catalog and cover library from the original installers."""
import argparse
from datetime import date
import json
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import gzip
import tempfile

from .config import DATA, SOURCE
from .discs import Disc, inventory


def extract_legacy(source, output):
    tool = shutil.which('7zz') or shutil.which('7z')
    if not tool:
        raise RuntimeError('Install 7-Zip (brew install sevenzip / apt install 7zip)')
    first = next((p for p in source.iterdir() if 'disk_1_' in p.name.lower() and p.suffix.lower() in ('.mdf', '.iso')), None)
    if first is None:
        raise RuntimeError('Disc 1 is required to import the original catalog')
    disc = Disc(first)
    installer = next((e for e in disc.entries.values() if e.path.lower().endswith('.dmg')), None)
    if not installer:
        raise RuntimeError('Mac installer not found on disc 1')
    dmg = output / 'installer.dmg'
    dmg.write_bytes(disc.read(installer.path))
    subprocess.run([tool, 'x', str(dmg), f'-o{output / "packages"}', '-r', '*Archive.pax.gz', '-y'], check=True, stdout=subprocess.DEVNULL)
    legacy = output / 'legacy'
    legacy.mkdir()
    # Apple's .pax.gz payloads are actually gzip-compressed old ASCII cpio.
    # Extract only known regular catalog/thumbnail basenames, never archive paths.
    for package in (output / 'packages').rglob('Archive.pax.gz'):
        with gzip.open(package, 'rb') as archive:
            while True:
                header = archive.read(76)
                if not header:
                    break
                if len(header) != 76 or header[:6] != b'070707':
                    raise ValueError('Unsupported installer cpio header')
                mode = int(header[18:24], 8)
                name_size = int(header[59:65], 8)
                file_size = int(header[65:76], 8)
                if not 1 <= name_size <= 4096:
                    raise ValueError('Invalid installer filename length')
                name_bytes = archive.read(name_size)
                if len(name_bytes) != name_size:
                    raise ValueError('Truncated installer filename')
                name = Path(name_bytes.rstrip(b'\0').decode('utf-8', errors='replace')).name
                if name == 'TRAILER!!!':
                    break
                selected = mode & 0o170000 == 0o100000 and (name == 'ny-sqlite-3.db' or re.fullmatch(r'\d{4}_\d{2}_\d{2}_v256\.jpg', name))
                target = (legacy / name).open('wb') if selected else None
                try:
                    remaining = file_size
                    while remaining:
                        block = archive.read(min(remaining, 1024 * 1024))
                        if not block:
                            raise ValueError('Truncated installer payload')
                        if target:
                            target.write(block)
                        remaining -= len(block)
                finally:
                    if target:
                        target.close()
    return legacy


def build(source: Path, data: Path, legacy: Path | None = None):
    data.mkdir(parents=True, exist_ok=True)
    print('Indexing original disc images…', flush=True)
    available = inventory(source)
    print(f'{len(available):,} issue files found', flush=True)
    with tempfile.TemporaryDirectory(prefix='tny-import-') as temp:
        if legacy is None:
            legacy = extract_legacy(source, Path(temp))
        database = next(legacy.rglob('ny-sqlite-3.db'), None)
        if not database:
            raise RuntimeError('Original catalog not found')
        covers = data / 'covers'
        covers.mkdir(exist_ok=True)
        for image in legacy.rglob('*_v256.jpg'):
            shutil.copyfile(image, covers / image.name.replace('_v256', ''))
        target = data / 'catalog.new.db'
        target.unlink(missing_ok=True)
        conn = sqlite3.connect(target)
        try:
            conn.execute('PRAGMA journal_mode=OFF')
            conn.execute('PRAGMA synchronous=OFF')
            conn.execute('ATTACH DATABASE ? AS legacy', (database.resolve().as_uri() + '?mode=ro',))
            conn.executescript('''
                CREATE TABLE issues(id INTEGER PRIMARY KEY, date TEXT, label TEXT, year INTEGER,
                  month INTEGER, day INTEGER, page_count INTEGER, stem TEXT, image TEXT, member TEXT);
                CREATE TABLE pages(issue_id INTEGER, page INTEGER, folio TEXT, PRIMARY KEY(issue_id,page));
                INSERT INTO pages SELECT IssueID,Offset,Folio FROM legacy.Pages;
                CREATE TABLE authors AS SELECT AuthorID AS id,Author AS name FROM legacy.Authors;
                CREATE INDEX authors_id ON authors(id);
                CREATE TABLE departments AS SELECT RubricID AS id,Rubric AS name FROM legacy.Rubrics WHERE Rubric != '';
                CREATE TABLE contributors AS SELECT ArticleID AS article_id,AuthorID AS author_id FROM legacy.ArticleAuthorMap;
                CREATE INDEX contributors_article ON contributors(article_id);
                CREATE INDEX contributors_author ON contributors(author_id,article_id);
                CREATE TABLE article_keywords AS SELECT m.ArticleID AS article_id,group_concat(k.Keyword,' ') AS terms
                  FROM legacy.ArticleKeywordMap m JOIN legacy.Keywords k ON k.KeywordID=m.KeywordID GROUP BY m.ArticleID;
                CREATE INDEX article_keywords_id ON article_keywords(article_id);
                CREATE TABLE articles AS SELECT a.ArticleID AS id,a.IssueID AS issue_id,a.RubricID AS department_id,
                  a.AuthorID AS author_id,coalesce(nullif(a.Title,''),r.Rubric,'Untitled') AS title,
                  coalesce(a.Byline,'') AS byline,coalesce(b.Abstract,'') AS abstract,
                  coalesce((SELECT min(p.Offset) FROM legacy.Pages p WHERE p.IssueID=a.IssueID AND p.Folio=a.PageStart),1) AS page,a.PageStart AS folio,
                  EXISTS(SELECT 1 FROM legacy.Pages p WHERE p.IssueID=a.IssueID AND p.Folio=a.PageStart) AS page_mapped,
                  coalesce(r.Rubric,'') AS department,coalesce(k.terms,'') AS keywords
                  FROM legacy.Articles a LEFT JOIN legacy.ArticleAbstracts b ON a.AbstractID=b.AbstractID
                  LEFT JOIN legacy.Rubrics r ON a.RubricID=r.RubricID
                  LEFT JOIN article_keywords k ON k.article_id=a.ArticleID;
                CREATE UNIQUE INDEX article_id ON articles(id);
                CREATE INDEX articles_issue ON articles(issue_id,page,id);
                CREATE INDEX articles_department ON articles(department_id);
                CREATE INDEX articles_author ON articles(author_id);
                CREATE VIRTUAL TABLE search USING fts5(title,byline,abstract,keywords,content='articles',content_rowid='id',tokenize='unicode61 remove_diacritics 2');
                INSERT INTO search(search) VALUES('rebuild');
                DROP TABLE article_keywords;
            ''')
            for row in conn.execute('SELECT IssueID,Year,Month,Day,PageCount FROM legacy.Issues').fetchall():
                iid, year, month, day, count = row
                iso_date = date(year, month, day)
                stem = iso_date.strftime('%Y_%m_%d')
                image, member = available.get(stem, ('', ''))
                conn.execute('INSERT INTO issues VALUES(?,?,?,?,?,?,?,?,?,?)',
                    (iid,iso_date.isoformat(),iso_date.strftime('%B %-d, %Y'),year,month,day,count,stem,image,member))
            conn.executescript('CREATE INDEX issues_year ON issues(year,date); CREATE INDEX issues_date ON issues(date);')
            conn.commit()
            stats = dict(issues=conn.execute('SELECT count(*) FROM issues').fetchone()[0],
                         available=conn.execute("SELECT count(*) FROM issues WHERE image!=''").fetchone()[0],
                         articles=conn.execute('SELECT count(*) FROM articles').fetchone()[0])
            conn.execute('ANALYZE main')
            conn.commit()
        finally:
            conn.close()
        target.replace(data / 'catalog.db')
        (data / 'import.json').write_text(json.dumps(stats, indent=2))
        print(json.dumps(stats), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=SOURCE)
    parser.add_argument('--data',type=Path,default=DATA)
    parser.add_argument('--legacy-root',type=Path)
    args = parser.parse_args()
    build(args.source.resolve(),args.data.resolve(),args.legacy_root)
