'use strict';
const $ = (s, root=document) => root.querySelector(s);
const main = $('#main');
const dialog = $('#detail-dialog');
const state = {stats:null, featured:[], issue:null, seq:0, zoom:85, contents:innerWidth>720, library:null};
const esc = value => String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num = value => Number(value).toLocaleString();
const cover = (id, alt='', lazy=true) => `<img src="/api/covers/${Number(id)}" alt="${esc(alt)}" ${lazy?'loading="lazy"':''} decoding="async">`;
const empty = (title, text) => `<div class="empty"><h2>${esc(title)}</h2><p>${esc(text)}</p></div>`;
const yearOptions = value => `<option value="">All years</option>${state.stats.years.map(y=>`<option value="${y.year}" ${Number(value)===y.year?'selected':''}>${y.year}</option>`).join('')}`;
let toastTimer, authorTimer;
function toast(message){ $('#toast').textContent=message; $('#toast').classList.add('show'); clearTimeout(toastTimer); toastTimer=setTimeout(()=>$('#toast').classList.remove('show'),3500); }
async function api(path, options={}){
 const response=await fetch(path,{...options,headers:{'Content-Type':'application/json',...options.headers}});
 if(!response.ok){let data;try{data=await response.json();}catch{}throw Error(typeof data?.detail==='string'?data.detail:`Request failed (${response.status})`);}
 return response.json();
}
function queryPath(base, params){const q=new URLSearchParams();Object.entries(params).forEach(([k,v])=>{if(v!==''&&v!=null)q.set(k,v)});return base+(q.size?'?'+q:'');}
function routeInfo(){const hash=location.hash.slice(1)||'browse';const [path,query='']=hash.split('?');return {path,params:new URLSearchParams(query)};}
function navigate(path,params={}){location.hash=queryPath(path,params);}
function issueCard(issue){return `<a class="issue-card" href="#issue/${issue.id}" aria-label="Read ${esc(issue.label)}"><div class="cover-wrap">${cover(issue.id,`Cover of ${issue.label}`)}${!issue.image?'<span class="unavailable">File unavailable</span>':''}</div><h3>${esc(issue.label)}</h3><p>${issue.page_count} PAGES</p></a>`;}
function pager(total,offset,limit,route,params){if(total<=limit)return '';return `<div class="pagination"><button class="button" data-action="paginate" data-route="${route}" data-offset="${offset-limit}" ${offset===0?'disabled':''}>← Previous</button><span class="subtle">${num(offset+1)}–${num(Math.min(total,offset+limit))} of ${num(total)}</span><button class="button" data-action="paginate" data-route="${route}" data-offset="${offset+limit}" ${offset+limit>=total?'disabled':''}>Next →</button></div>`;}
async function browse(params,seq){
 const year=params.get('year')||'',decade=params.get('decade')||'',sort=params.get('sort')||'oldest',offset=Math.max(0,Number(params.get('offset'))||0);
 const data=await api(queryPath('/api/issues',{year,decade,sort,offset}));if(seq!==state.seq)return;
 const title=year?`${year}`:decade?`The ${decade}s`:'Explore the collection';
 main.innerHTML=`<section class="hero"><div><span class="eyebrow">1925 — 2005 · THE COMPLETE COLLECTION</span><h1>A lifetime of<br><em>good reading.</em></h1><p>Writers, ideas, cartoons, and conversations.<br>Step into eight decades of The New Yorker.</p><div class="hero-meta"><div><strong>${num(state.stats.issues)}</strong>ISSUES</div><div><strong>${num(state.stats.articles)}</strong>CATALOG ENTRIES</div><div><strong>81</strong>YEARS</div></div></div><div class="hero-art" aria-label="A selection through the decades">${state.featured.map(i=>`<a href="#issue/${i.id}" aria-label="Read ${esc(i.label)}">${cover(i.id,`Cover of ${i.label}`,false)}</a>`).join('')}</div></section><section><div class="section-header"><div><h2>${title}</h2><div class="subtle">${num(data.total)} issues${year||decade?' in this selection':' to discover'}</div></div><div class="browse-tools"><label><span class="sr-only">Year</span><select id="browse-year" class="select-control">${yearOptions(year)}</select></label><label><span class="sr-only">Sort order</span><select id="browse-sort" class="select-control"><option value="oldest" ${sort==='oldest'?'selected':''}>Oldest first</option><option value="newest" ${sort==='newest'?'selected':''}>Newest first</option></select></label></div></div><div class="decades" aria-label="Browse by decade"><button data-action="decade" data-decade="" class="${!decade&&!year?'active':''}">All years</button>${Array.from({length:9},(_,i)=>1920+i*10).map(d=>`<button data-action="decade" data-decade="${d}" class="${Number(decade)===d&&!year?'active':''}">${d}s</button>`).join('')}</div><div class="cover-grid">${data.items.map(issueCard).join('')}</div>${!data.items.length?empty('No issues found','Choose another year or decade.'):''}${pager(data.total,offset,24,'browse',params)}</section>`;
}
async function search(params,seq){
 const q=params.get('q')||'',year=params.get('year')||'',department=params.get('department')||'',author=params.get('author')||'',authorName=params.get('authorName')||'',offset=Math.max(0,Number(params.get('offset'))||0);
 const data=await api(queryPath('/api/search',{q,year,department,author,offset}));if(seq!==state.seq)return;
 main.innerHTML=`<section class="page-title"><span class="eyebrow">FOLLOW YOUR CURIOSITY</span><h1>Find your next story.</h1><p>Search titles, abstracts, contributors, and the original subject index.</p><form class="search-form" id="search-form"><input id="search-query" name="q" type="search" value="${esc(q)}" placeholder="An idea, a writer, a place…" aria-label="Search the archive"><button class="button primary" type="submit">Search →</button></form></section><div class="search-layout"><aside class="filters" aria-label="Search filters"><div class="filter"><label for="search-year">Year</label><select class="select-control" id="search-year">${yearOptions(year)}</select></div><div class="filter"><label for="search-department">Department</label><select class="select-control" id="search-department"><option value="">All departments</option>${state.stats.departments.map(d=>`<option value="${d.id}" ${Number(department)===d.id?'selected':''}>${esc(d.name)} (${num(d.count)})</option>`).join('')}</select></div><div class="filter"><label for="search-author">Contributor</label><input id="search-author" class="input-control" list="authors" value="${esc(authorName)}" placeholder="Type a name…" autocomplete="off"><datalist id="authors"></datalist><span class="subtle" id="author-status"></span></div><div class="filter"><button class="text-button" data-action="clear-search">Clear all filters</button></div><p class="filter-hint">The original index includes articles, poetry, cartoons, and covers. Search matches all words you enter.<br><br>This searches the catalog; the scanned page text has not been indexed.</p></aside><section aria-label="Search results"><div class="result-count">${num(data.total)} results${q?` for “${esc(q)}”`:''} · Newest first</div>${data.items.map(a=>`<article class="result-row"><a href="#issue/${a.issue_id}/${a.page}">${cover(a.issue_id,`Cover of ${a.label}`)}</a><div><span class="eyebrow">${esc(a.department)} · ${esc(a.label)}</span><button class="result-title" data-action="article" data-id="${a.id}"><h3>${esc(a.title)}</h3></button><div class="byline">${esc(a.byline||'Unsigned')} · Page ${esc(a.folio||a.page)}${a.page_mapped===0?' · Scan location unverified':''}</div>${a.abstract?`<p class="abstract">${esc(a.abstract)}</p>`:''}</div><a class="arrow" href="#issue/${a.issue_id}/${a.page}" aria-label="Read ${esc(a.title)}">↗</a></article>`).join('')}${!data.items.length?empty('Nothing here yet','Try fewer search words or a different filter.'):''}${pager(data.total,offset,30,'search',params)}</section></div>`;
 if(author)$('#author-status').textContent='Contributor filter active';
}
async function showArticle(id){
 const a=await api(`/api/articles/${id}`);
 $('#dialog-body').innerHTML=`<span class="eyebrow">${esc(a.department)}</span><h2 class="dialog-title">${esc(a.title)}</h2><div class="dialog-meta">${esc(a.byline||'Unsigned')}<br>${esc(a.label)} · Page ${esc(a.folio||a.page)}</div>${a.page_mapped===0?`<p class="error">The catalog has no exact scan location for this entry. Open the issue and look for printed page ${esc(a.folio)}.</p>`:''}${a.abstract?`<p class="dialog-abstract">${esc(a.abstract)}</p>`:'<p class="dialog-abstract">This entry has no abstract. Open the original page to read it.</p>'}<div class="dialog-actions"><a class="button primary" href="#issue/${a.issue_id}/${a.page}" data-action="close-dialog">${a.page_mapped===0?'Browse this issue →':'Read the original →'}</a></div>`;
 dialog.showModal();
}
async function reader(path,seq){
 const parts=path.split('/'),id=Number(parts[1]);if(!Number.isInteger(id)||id<1)throw Error('Invalid issue');
 let issue=state.issue;
 if(!issue||issue.id!==id){issue=await api(`/api/issues/${id}`);if(seq!==state.seq)return;state.issue=issue;state.zoom=innerWidth<720?98:85;}
 const page=parts[2]?Number(parts[2]):issue.resume_page;
 if(!Number.isInteger(page)||page<1||page>issue.page_count)throw Error('That page is outside this issue.');
 state.page=page;
 const saved=issue.bookmarks.some(b=>b.page===page),folio=issue.folios[page]||page;
 main.innerHTML=`<div class="reader-header"><div class="reader-title"><a class="eyebrow" href="#browse?year=${issue.year}">← BACK TO ${issue.year}</a><h1>${esc(issue.label)}</h1></div><div class="reader-actions"><button class="button" data-action="contents">Contents</button><button class="button ${saved?'red':''}" data-action="save-page">${saved?'✓ Saved':'＋ Save page'}</button><button class="button" data-action="note">Notes</button><a class="button" href="/api/issues/${issue.id}/download" title="Download a standard DjVu copy of this issue">Download ↓</a></div></div><div class="reader-layout ${state.contents?'':'hide-contents'}"><aside class="contents" aria-label="Issue contents"><h2>In this issue</h2><p>${num(issue.contents.length)} catalog entries · ${issue.page_count} pages</p><a href="#issue/${issue.id}/1"><span class="article-label">THE COVER</span><span class="article-title">${esc(issue.label)}</span></a>${issue.contents.filter(a=>a.department!=='Cover').map(a=>`<a href="#issue/${issue.id}/${a.page}" class="${a.page===page?'current':''}"><span class="article-label">${esc(a.department)} · ${esc(a.folio||a.page)}${a.page_mapped===0?' · LOCATION UNVERIFIED':''}</span><span class="article-title">${esc(a.title)}</span>${a.byline?`<span class="article-byline">${esc(a.byline)}</span>`:''}</a>`).join('')}</aside><section class="reader-pane" aria-label="Page reader"><div class="reader-toolbar"><div class="page-controls"><button class="icon-button" data-action="prev-page" aria-label="Previous page" ${page===1?'disabled':''}>←</button><label><span class="sr-only">Scan page number</span><input class="page-input" id="page-number" type="number" min="1" max="${issue.page_count}" value="${page}"></label><span class="reader-status">/ ${issue.page_count}</span><button class="icon-button" data-action="next-page" aria-label="Next page" ${page===issue.page_count?'disabled':''}>→</button></div><span class="reader-status">Printed page ${esc(folio)}</span><div class="zoom-controls"><button class="icon-button" data-action="zoom-out" aria-label="Zoom out">−</button><button class="button" data-action="zoom-fit" style="padding:6px 9px">Fit</button><button class="icon-button" data-action="zoom-in" aria-label="Zoom in">＋</button></div></div><div class="page-stage"><div class="loading" id="page-loading">Opening the original page…</div>${issue.image?`<img id="page-image" class="pending" alt="${esc(issue.label)}, printed page ${esc(folio)}, scan ${page}" style="width:${state.zoom}%">`:'<div class="error">This issue is catalogued, but its file was not found in the connected disc images.</div>'}</div><div class="reader-note">← → Turn pages &nbsp; · &nbsp; + − Zoom &nbsp; · &nbsp; Your reading position is saved automatically</div></section></div>`;
 if(!issue.image){$('#page-loading').remove();return;}
 const current=$('.contents a.current'),contents=$('.contents');
 if(current && contents)contents.scrollTop=current.offsetTop-contents.offsetTop-70;
 const image=$('#page-image');
 image.onload=()=>{if(seq!==state.seq)return;$('#page-loading')?.remove();image.classList.remove('pending');issue.resume_page=page;api(`/api/progress/${id}`,{method:'PUT',body:JSON.stringify({page})}).catch(e=>toast(e.message));};
 image.onerror=()=>{if(seq!==state.seq)return;$('#page-loading').innerHTML='<div class="error">Unable to render this page. Check that the archive drive is connected.<br><button class="button" data-action="retry-page">Try again</button></div>';};
 image.src=`/api/issues/${id}/pages/${page}?width=1800`;
}
function setZoom(value){state.zoom=Math.max(35,Math.min(220,value));const image=$('#page-image');if(image)image.style.width=state.zoom+'%';}
function turnPage(delta){const p=state.page+delta;if(p>=1&&p<=state.issue.page_count)navigate(`issue/${state.issue.id}/${p}`);}
async function savePage(){
 const issue=state.issue,page=state.page;
 const existing=issue.bookmarks.find(b=>b.page===page);
 if(existing){await noteDialog();return;}
 const bookmark={page,collection:'Reading list',note:''};
 await api(`/api/bookmarks/${issue.id}`,{method:'PUT',body:JSON.stringify(bookmark)});
 issue.bookmarks.push(bookmark);toast('Page saved to your reading list');reader(routeInfo().path,state.seq);
}
async function noteDialog(){
 const issue=state.issue,page=state.page,b=issue.bookmarks.find(b=>b.page===page)||{collection:'Reading list',note:''};
 const library=await api('/api/library');
 $('#dialog-body').innerHTML=`<span class="eyebrow">YOUR READING ROOM</span><h2 class="dialog-title">A thought to keep.</h2><div class="dialog-meta">${esc(issue.label)} · Printed page ${esc(issue.folios[page]||page)}</div><form class="note-form" id="note-form" data-issue="${issue.id}" data-page="${page}"><label for="collection">Collection</label><input id="collection" name="collection" list="collections" value="${esc(b.collection)}" maxlength="80" required><datalist id="collections">${[...new Set(library.bookmarks.map(x=>x.collection))].map(x=>`<option value="${esc(x)}"></option>`).join('')}</datalist><label for="note">Your note</label><textarea id="note" name="note" maxlength="10000" placeholder="What caught your attention?">${esc(b.note)}</textarea><button class="button primary" type="submit">Save page & note</button>${issue.bookmarks.some(x=>x.page===page)?'<button class="text-button" type="button" data-action="unsave-page" style="margin-left:20px">Remove saved page</button>':''}</form>`;
 dialog.showModal();
}
async function library(params,seq){
 const data=await api('/api/library');if(seq!==state.seq)return;state.library=data;
 const collection=params.get('collection')||'',collections=[...new Set(data.bookmarks.map(b=>b.collection))].sort(),bookmarks=data.bookmarks.filter(b=>!collection||b.collection===collection);
 main.innerHTML=`<section class="page-title"><span class="eyebrow">MAKE YOURSELF AT HOME</span><h1>My reading room.</h1><p>A place for the pages you want to return to, and the thoughts you want to keep.</p></section>${data.progress.length?`<section><div class="section-header"><h2>Pick up where you left off</h2></div><div class="continue-grid">${data.progress.map(p=>`<a class="continue-card" href="#issue/${p.issue_id}/${p.page}">${cover(p.issue_id,`Cover of ${p.label}`)}<div><h3>${esc(p.label)}</h3><p>Page ${p.page} of ${p.page_count}</p><div class="progress-track"><span style="width:${Math.round(p.page/p.page_count*100)}%"></span></div></div></a>`).join('')}</div></section>`:''}<section><div class="section-header"><h2>Saved pages <span class="subtle">(${data.bookmarks.length})</span></h2></div><div class="library-tabs"><button class="pill ${!collection?'active':''}" data-action="collection" data-collection="">All collections</button>${collections.map(c=>`<button class="pill ${collection===c?'active':''}" data-action="collection" data-collection="${esc(c)}">${esc(c)}</button>`).join('')}</div>${bookmarks.length?bookmarks.map(b=>`<article class="bookmark-card"><a href="#issue/${b.issue_id}/${b.page}">${cover(b.issue_id,`Cover of ${b.label}`)}</a><div class="card-main"><span class="eyebrow">${esc(b.collection)}</span><h3><a href="#issue/${b.issue_id}/${b.page}">${esc(b.label)}</a></h3><span class="subtle">Scan page ${b.page} of ${b.page_count}</span>${b.note?`<p class="note">${esc(b.note)}</p>`:''}<div class="dialog-actions"><a class="button" href="#issue/${b.issue_id}/${b.page}">Return to page →</a><button class="text-button" data-action="remove-bookmark" data-issue="${b.issue_id}" data-page="${b.page}">Remove</button></div></div></article>`).join(''):empty('Your collection starts here','Save a page while reading. Add a note or create a collection to make it yours.')}</section>`;
}
async function route(){
 const seq=++state.seq,{path,params}=routeInfo(),kind=path.split('/')[0];
 document.body.classList.toggle('reader-mode',kind==='issue');
 document.querySelectorAll('[data-nav]').forEach(a=>a.classList.toggle('active',a.dataset.nav===kind));
 if(dialog.open)dialog.close();
 main.innerHTML='<div class="loading">Opening the archive…</div>';
 try{
  if(!state.stats){state.stats=await api('/api/stats');const covers=await Promise.all([1925,1955,1985].map(year=>api(`/api/issues?year=${year}&limit=1`)));state.featured=covers.flatMap(x=>x.items);}
  if(seq!==state.seq)return;
  document.title=kind==='issue'?'Reading — The Archive':kind==='search'?'Search — The Archive':kind==='library'?'My library — The Archive':'The Archive — The New Yorker';
  if(kind==='issue')await reader(path,seq);else if(kind==='search')await search(params,seq);else if(kind==='library')await library(params,seq);else await browse(params,seq);
 }catch(error){if(seq===state.seq)main.innerHTML=`<div class="error"><h2>Couldn’t open the archive</h2><p>${esc(error.message)}</p><button class="button" data-action="retry">Try again</button> <a class="button" href="#browse">Browse the archive</a></div>`;}
}
function searchParams(){const params=Object.fromEntries(routeInfo().params);params.q=$('#search-query')?.value||'';params.year=$('#search-year')?.value||'';params.department=$('#search-department')?.value||'';delete params.offset;return params;}
document.addEventListener('click',async event=>{
 if(event.target.closest('.skip')){event.preventDefault();main.focus();main.scrollIntoView();return;}
 const el=event.target.closest('[data-action]');if(!el||el.disabled)return;
 const action=el.dataset.action,{params}=routeInfo();
 try{
  if(action==='decade')navigate('browse',{decade:el.dataset.decade,sort:params.get('sort')||'oldest'});
  if(action==='paginate'){navigate(el.dataset.route,{...Object.fromEntries(params),offset:el.dataset.offset});scrollTo({top:el.dataset.route==='browse'?450:180,behavior:'smooth'});}
  if(action==='article')await showArticle(el.dataset.id);
  if(action==='clear-search')navigate('search');
  if(action==='close-dialog')dialog.close();
  if(action==='contents'){state.contents=!state.contents;$('.reader-layout').classList.toggle('hide-contents',!state.contents);}
  if(action==='prev-page')turnPage(-1);if(action==='next-page')turnPage(1);
  if(action==='zoom-in')setZoom(state.zoom+15);if(action==='zoom-out')setZoom(state.zoom-15);if(action==='zoom-fit')setZoom(innerWidth<720?98:85);
  if(action==='save-page')await savePage();if(action==='note')await noteDialog();
  if(action==='collection')navigate('library',{collection:el.dataset.collection});
  if(action==='remove-bookmark'){await api(`/api/bookmarks/${el.dataset.issue}/${el.dataset.page}`,{method:'DELETE'});if(state.issue?.id===Number(el.dataset.issue))state.issue.bookmarks=state.issue.bookmarks.filter(b=>b.page!==Number(el.dataset.page));await route();toast('Saved page removed');}
  if(action==='unsave-page'){await api(`/api/bookmarks/${state.issue.id}/${state.page}`,{method:'DELETE'});state.issue.bookmarks=state.issue.bookmarks.filter(b=>b.page!==state.page);dialog.close();await reader(routeInfo().path,state.seq);toast('Saved page removed');}
  if(action==='retry')await route();if(action==='retry-page')await reader(routeInfo().path,state.seq);
 }catch(error){toast(error.message);}
});
document.addEventListener('submit',async event=>{
 if(event.target.id==='search-form'){event.preventDefault();navigate('search',searchParams());}
 if(event.target.id==='note-form'){
  event.preventDefault();const form=event.target,button=$('button[type=submit]',form);button.disabled=true;
  try{const body={page:Number(form.dataset.page),collection:form.collection.value,note:form.note.value};await api(`/api/bookmarks/${form.dataset.issue}`,{method:'PUT',body:JSON.stringify(body)});state.issue.bookmarks=state.issue.bookmarks.filter(b=>b.page!==body.page);state.issue.bookmarks.push(body);dialog.close();await reader(routeInfo().path,state.seq);toast('Page and note saved');}catch(e){toast(e.message);button.disabled=false;}
 }
});
document.addEventListener('change',event=>{
 const id=event.target.id,{params}=routeInfo();
 if(id==='browse-year')navigate('browse',{year:event.target.value,sort:params.get('sort')||'oldest'});
 if(id==='browse-sort')navigate('browse',{year:params.get('year')||'',decade:params.get('decade')||'',sort:event.target.value});
 if(id==='search-year'||id==='search-department')navigate('search',searchParams());
 if(id==='search-author'){const opt=[...$('#authors').options].find(o=>o.value===event.target.value);if(!event.target.value||opt){const p=searchParams();p.author=opt?.dataset.id||'';p.authorName=opt?.value||'';navigate('search',p);}else{$('#author-status').textContent='Choose a contributor from the suggestions.';}}
 if(id==='page-number'){const p=Number(event.target.value);if(Number.isInteger(p)&&p>=1&&p<=state.issue.page_count)navigate(`issue/${state.issue.id}/${p}`);else{event.target.value=state.page;toast(`Choose a page from 1 to ${state.issue.page_count}`);}}
});
document.addEventListener('input',event=>{
 if(event.target.id==='search-author'){clearTimeout(authorTimer);const input=event.target;authorTimer=setTimeout(async()=>{try{const names=await api(queryPath('/api/authors',{q:input.value}));if(!input.isConnected)return;$('#authors').innerHTML=names.map(a=>`<option value="${esc(a.name)}" data-id="${a.id}"></option>`).join('');}catch(e){toast(e.message);}},180);}
});
document.addEventListener('keydown',event=>{
 if(!state.issue||!routeInfo().path.startsWith('issue/')||dialog.open||event.target.closest('input,textarea,select'))return;
 if(event.key==='ArrowLeft'){event.preventDefault();turnPage(-1);}if(event.key==='ArrowRight'){event.preventDefault();turnPage(1);}
 if(event.key==='+'||event.key==='='){event.preventDefault();setZoom(state.zoom+15);}if(event.key==='-'){event.preventDefault();setZoom(state.zoom-15);}
});
// A missing thumbnail should not leave a broken-image icon in the reading room.
document.addEventListener('error',event=>{const img=event.target;if(img.tagName==='IMG'&&img.id!=='page-image'){const p=document.createElement('div');p.className='cover-fallback';p.textContent='The New Yorker';img.replaceWith(p);}},true);
$('.close-dialog').addEventListener('click',()=>dialog.close());
dialog.addEventListener('click',event=>{if(event.target===dialog){const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close();}});
addEventListener('hashchange',route);
route();
