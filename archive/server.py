from contextlib import asynccontextmanager
from functools import lru_cache
import logging
import re
import shutil

from fastapi import FastAPI, HTTPException, Query, Path as PathParam
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import ROOT, DATA
from .db import catalog, personal, setup_personal
from .render import page_image, issue_document


@asynccontextmanager
async def lifespan(app):
    setup_personal()
    yield


app = FastAPI(title='The Archive',lifespan=lifespan)


@app.exception_handler(RuntimeError)
def runtime_error(request,error):
    logging.exception('Archive operation failed',exc_info=error)
    return JSONResponse(status_code=503,content={'detail':str(error)})


def get_issue(issue_id):
    with catalog() as db:
        row = db.execute('SELECT * FROM issues WHERE id=?',(issue_id,)).fetchone()
    if row is None:
        raise HTTPException(404,'Issue not found')
    return dict(row)


def valid_page(issue_id,page):
    issue = get_issue(issue_id)
    if page > issue['page_count']:
        raise HTTPException(422,'Page outside this issue')
    return issue


@lru_cache(maxsize=1)
def stats():
    with catalog() as db:
        summary = dict(db.execute("SELECT count(*) AS issues,sum(image!='') AS available,sum(page_count) AS pages,min(year) AS first_year,max(year) AS last_year FROM issues").fetchone())
        summary['articles'] = db.execute('SELECT count(*) FROM articles').fetchone()[0]
        summary['years'] = [dict(r) for r in db.execute('SELECT year,count(*) AS count FROM issues GROUP BY year ORDER BY year DESC')]
        summary['departments'] = [dict(r) for r in db.execute('SELECT d.id,d.name,count(*) AS count FROM departments d JOIN articles a ON a.department_id=d.id GROUP BY d.id ORDER BY count(*) DESC')]
    return summary


@app.get('/api/stats')
def archive_stats():
    return stats()


@app.get('/api/issues')
def issues(year: int | None=None, decade: int | None=None, offset: int=Query(0,ge=0), limit: int=Query(24,ge=1,le=100), sort: str=Query('oldest',pattern='^(oldest|newest)$')):
    terms, args = [], []
    if year is not None:
        terms.append('year=?'); args.append(year)
    elif decade is not None:
        terms.append('year BETWEEN ? AND ?'); args.extend([decade,decade+9])
    where = ' WHERE ' + ' AND '.join(terms) if terms else ''
    with catalog() as db:
        count = db.execute('SELECT count(*) FROM issues'+where,args).fetchone()[0]
        rows = db.execute('SELECT * FROM issues'+where+f' ORDER BY date {"DESC" if sort=="newest" else "ASC"} LIMIT ? OFFSET ?',[*args,limit,offset]).fetchall()
    return {'total':count,'items':[dict(r) for r in rows]}


@app.get('/api/issues/{issue_id}')
def issue_details(issue_id: int):
    issue = get_issue(issue_id)
    with catalog() as db:
        issue['contents'] = [dict(r) for r in db.execute('SELECT id,title,byline,page,folio,department,page_mapped FROM articles WHERE issue_id=? ORDER BY page,id',(issue_id,))]
        issue['folios'] = {str(r['page']):r['folio'] for r in db.execute('SELECT * FROM pages WHERE issue_id=?',(issue_id,))}
    with personal() as db:
        progress = db.execute('SELECT page FROM progress WHERE issue_id=?',(issue_id,)).fetchone()
        issue['resume_page'] = progress['page'] if progress else 1
        issue['bookmarks'] = [dict(r) for r in db.execute('SELECT * FROM bookmarks WHERE issue_id=?',(issue_id,))]
    return issue


@app.get('/api/covers/{issue_id}')
def cover(issue_id: int):
    issue = get_issue(issue_id)
    path = DATA / 'covers' / f'{issue["stem"]}.jpg'
    if not path.exists():
        raise HTTPException(404,'Cover not available')
    return FileResponse(path,headers={'Cache-Control':'public, max-age=86400'})


@app.get('/api/issues/{issue_id}/pages/{page}')
def render_page(issue_id: int,page: int=PathParam(ge=1),width: int=Query(1400,ge=320,le=2400)):
    issue = valid_page(issue_id,page)
    width = min(2400,((width+199)//200)*200)
    try:
        path = page_image(issue,page,width)
    except FileNotFoundError as error:
        raise HTTPException(404,str(error)) from error
    except ValueError as error:
        raise HTTPException(422,str(error)) from error
    return FileResponse(path,media_type='image/jpeg',headers={'Cache-Control':'public, max-age=31536000, immutable'})


@app.get('/api/issues/{issue_id}/download')
def download_issue(issue_id: int):
    issue = get_issue(issue_id)
    try:
        path = issue_document(issue)
    except FileNotFoundError as error:
        raise HTTPException(404,str(error)) from error
    return FileResponse(path,media_type='image/vnd.djvu',filename=f'{issue["stem"]}.djvu')


@app.get('/api/search')
def search(q: str=Query('',max_length=300),year: int | None=None,department: int | None=None,author: int | None=None,offset: int=Query(0,ge=0),limit: int=Query(30,ge=1,le=100)):
    terms, args = [], []
    words = re.findall(r'[^\W_]+',q,flags=re.UNICODE)
    ranked = bool(words)
    if ranked:
        terms.append('a.id IN (SELECT rowid FROM search WHERE search MATCH ?)')
        args.append(' AND '.join('"'+word+'"*' for word in words))
    if year is not None:
        terms.append('i.year=?'); args.append(year)
    if department is not None:
        terms.append('a.department_id=?'); args.append(department)
    if author is not None:
        terms.append('a.id IN (SELECT article_id FROM contributors WHERE author_id=?)'); args.append(author)
    where = ' WHERE ' + ' AND '.join(terms) if terms else ''
    base = ' FROM articles a JOIN issues i ON a.issue_id=i.id'
    with catalog() as db:
        total = db.execute('SELECT count(*)'+base+where,args).fetchone()[0]
        # Chronological order keeps adjacent pieces together and remains fast across the entire catalog.
        rows = db.execute('SELECT a.id,a.issue_id,a.title,a.byline,a.abstract,a.page,a.folio,a.department,a.page_mapped,i.label,i.year,i.stem'+base+where+' ORDER BY i.date DESC,a.page LIMIT ? OFFSET ?',[*args,limit,offset]).fetchall()
    return {'total':total,'items':[dict(r) for r in rows]}


@app.get('/api/authors')
def authors(q: str=Query('',max_length=100)):
    with catalog() as db:
        rows = db.execute('SELECT id,name FROM authors WHERE name LIKE ? ORDER BY name LIMIT 30',('%'+q+'%',)).fetchall()
    return [dict(r) for r in rows]


@app.get('/api/articles/{article_id}')
def article(article_id: int):
    with catalog() as db:
        row = db.execute('SELECT a.*,i.label,i.year FROM articles a JOIN issues i ON i.id=a.issue_id WHERE a.id=?',(article_id,)).fetchone()
    if row is None:
        raise HTTPException(404,'Article not found')
    return dict(row)


class Progress(BaseModel):
    page: int = Field(ge=1)


class Bookmark(Progress):
    collection: str = Field(default='Reading list',min_length=1,max_length=80)
    note: str = Field(default='',max_length=10000)


@app.put('/api/progress/{issue_id}')
def save_progress(issue_id: int,body: Progress):
    valid_page(issue_id,body.page)
    with personal() as db:
        db.execute('INSERT INTO progress(issue_id,page) VALUES(?,?) ON CONFLICT(issue_id) DO UPDATE SET page=excluded.page,updated=CURRENT_TIMESTAMP',(issue_id,body.page))
    return {'saved':True}


@app.put('/api/bookmarks/{issue_id}')
def save_bookmark(issue_id: int,body: Bookmark):
    valid_page(issue_id,body.page)
    with personal() as db:
        db.execute('INSERT INTO bookmarks(issue_id,page,collection,note) VALUES(?,?,?,?) ON CONFLICT(issue_id,page) DO UPDATE SET collection=excluded.collection,note=excluded.note,updated=CURRENT_TIMESTAMP',(issue_id,body.page,body.collection.strip() or 'Reading list',body.note))
    return {'saved':True}


@app.delete('/api/bookmarks/{issue_id}/{page}')
def remove_bookmark(issue_id: int,page: int):
    with personal() as db:
        db.execute('DELETE FROM bookmarks WHERE issue_id=? AND page=?',(issue_id,page))
    return {'deleted':True}


@app.get('/api/library')
def library():
    with personal() as db:
        bookmarks = [dict(r) for r in db.execute('SELECT * FROM bookmarks ORDER BY updated DESC,issue_id DESC')]
        progress = [dict(r) for r in db.execute('SELECT * FROM progress ORDER BY updated DESC LIMIT 12')]
    for item in bookmarks + progress:
        issue = get_issue(item['issue_id'])
        item.update(label=issue['label'],page_count=issue['page_count'],stem=issue['stem'])
    return {'bookmarks':bookmarks,'progress':progress}


@app.get('/api/health')
def health():
    return {'ready':True,'renderer':bool(shutil.which('ddjvu')),'catalog':stats()['issues']}


@app.get('/')
def home():
    return FileResponse(ROOT / 'static' / 'index.html',headers={'Cache-Control':'no-cache'})


class FreshStaticFiles(StaticFiles):
    async def get_response(self,path,scope):
        response=await super().get_response(path,scope)
        response.headers['Cache-Control']='no-cache'
        return response


app.mount('/static',FreshStaticFiles(directory=ROOT / 'static'),name='static')
