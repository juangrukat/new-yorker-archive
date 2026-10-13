import hashlib
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image

from archive import db, render
from archive.config import CATALOG, SOURCE, ROOT
from archive.discs import Disc
from archive.djvu import decode_data
from archive.server import app


@unittest.skipUnless(CATALOG.exists(),'Import the catalog first')
class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.patch = patch.object(db,'PERSONAL',Path(self.temp.name) / 'personal.db')
        self.patch.start()
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None,None,None)
        self.patch.stop()
        self.temp.cleanup()

    def test_complete_catalog_and_browse(self):
        stats = self.client.get('/api/stats').json()
        self.assertEqual(stats['issues'],4109)
        self.assertEqual(stats['articles'],188792)
        issues = self.client.get('/api/issues?year=1925&limit=2').json()['items']
        self.assertEqual(issues[0]['date'],'1925-02-21')
        self.assertEqual(issues[1]['date'],'1925-02-28')
        self.assertEqual(self.client.get('/api/issues?limit=10000').status_code,422)

    def test_article_page_mapping_uses_scan_offset(self):
        article = self.client.get('/api/articles/2').json()
        self.assertEqual(article['folio'],'002')
        self.assertEqual(article['page'],4)
        issue = self.client.get('/api/issues/1').json()
        self.assertEqual(issue['folios']['4'],'002')
        unmapped=self.client.get('/api/articles/1915').json()
        self.assertEqual(unmapped['page_mapped'],0)
        self.assertEqual(unmapped['page'],1)

    def test_search_and_contributor_filters(self):
        result = self.client.get('/api/search',params={'q':'Robert Moses','year':1998}).json()
        self.assertGreater(result['total'],0)
        self.assertTrue(all(i['year']==1998 for i in result['items']))
        names = self.client.get('/api/authors?q=Updike').json()
        author = next(a for a in names if a['name']=='Updike, John')
        result = self.client.get('/api/search',params={'author':author['id'],'department':5}).json()
        self.assertGreater(result['total'],0)
        self.assertTrue(all(i['department']=='Fiction' for i in result['items']))
        self.assertEqual(self.client.get('/api/search',params={'q':'" OR NOT ( ) *'}).status_code,200)

    def test_personal_data_and_invalid_pages(self):
        body={'page':4,'collection':'Early cartoons','note':'A note with <markup> & quotes'}
        self.assertEqual(self.client.put('/api/bookmarks/1',json=body).status_code,200)
        self.client.put('/api/progress/1',json={'page':4})
        library=self.client.get('/api/library').json()
        self.assertEqual(library['bookmarks'][0]['note'],body['note'])
        self.assertEqual(library['progress'][0]['page'],4)
        self.assertEqual(self.client.get('/api/issues/1').json()['resume_page'],4)
        self.assertEqual(self.client.put('/api/progress/1',json={'page':37}).status_code,422)
        self.assertEqual(self.client.put('/api/bookmarks/1',json={'page':0}).status_code,422)
        self.assertEqual(self.client.get('/api/issues/1/pages/0').status_code,422)
        self.assertEqual(self.client.get('/api/issues/99999').status_code,404)
        self.client.delete('/api/bookmarks/1/4')
        self.assertEqual(self.client.get('/api/library').json()['bookmarks'],[])

    def test_static_app_assets(self):
        self.assertEqual(self.client.get('/').status_code,200)
        self.assertEqual(self.client.get('/static/app.js').status_code,200)
        self.assertEqual(self.client.get('/api/covers/1').status_code,200)


@unittest.skipUnless(SOURCE.exists() and CATALOG.exists(),'Original discs required')
class DiscTests(unittest.TestCase):
    def test_original_bytes_match_extracted_sample(self):
        sample=ROOT / 'research/artifacts/Issues/1998_01_05.djvu'
        if not sample.exists():
            self.skipTest('Research sample not present')
        disc=Disc(SOURCE / 'disk_1_1998_2005.mdf')
        raw=disc.read('/Issues/1998_01_05.djvu')
        self.assertEqual(hashlib.sha256(raw).digest(),hashlib.sha256(sample.read_bytes()).digest())

    def test_decode_render_and_page_counts_from_each_disc(self):
        con=sqlite3.connect(CATALOG)
        con.row_factory=sqlite3.Row
        names=[r[0] for r in con.execute("SELECT DISTINCT image FROM issues WHERE image!='' ORDER BY image")]
        self.assertEqual(len(names),8)
        with tempfile.TemporaryDirectory() as tmp,patch.object(render,'DATA',Path(tempfile.mkdtemp(dir=tmp))):
            for name in names:
                issue=dict(con.execute('SELECT * FROM issues WHERE image=? ORDER BY date LIMIT 1',(name,)).fetchone())
                with self.subTest(disc=name,issue=issue['date']):
                    image=render.page_image(issue,1,600)
                    with Image.open(image) as im:
                        self.assertGreater(im.width,200)
                        self.assertGreater(im.height,300)
                    decoded=render.issue_document(issue)
                    self.assertEqual(decoded.read_bytes()[:4],b'AT&T')
        con.close()

    def test_reject_truncated_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                decode_data(b'SDJVFORM'+b'\xff'*4+b'DJVM',Path(tmp)/'pages')


if __name__=='__main__':
    unittest.main()
