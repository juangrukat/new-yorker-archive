# Verification — 2026-10-13

## Confirmed

- Native app starts through `./start.sh` using the project virtual environment; no dependency on `research/` is required.
- Source images indexed without mounting/extracting entire discs: 4,100 issue files across eight images.
- Catalog imports 4,109 issues, 188,792 entries, and 500,592 page mappings. All 4,109 cover thumbnails imported.
- Automatic first-start installer extraction tested directly on disc 1: recovered the 601,788,416-byte catalog and 4,109 thumbnails. The old installer payload is gzip-compressed ASCII cpio, despite its `.pax.gz` name; no installer executes.
- Ten automated tests pass (including two portable format checks): catalog totals/filtering, article-to-scan mapping, keyword/contributor search, persistence and bounds, static assets, source-byte fidelity, malformed input rejection, and real decoding/rendering from every disc.
- One issue from each disc was independently decoded into standard DjVu, with page counts matching the original catalog, and its cover rendered successfully.
- Source-reader bytes for 1998-01-05 match the 7-Zip-extracted original byte-for-byte by SHA-256.
- Prior format investigation rendered all 124 pages of 1925-02-21 and 1998-01-05 without failures.
- Browser verified cover browsing, search for Robert Moses, filtering to 1998, article details, opening The City-Shaper at scan 44 / printed page 038, next-page navigation, notes with a named collection, saved-page library, and automatic resume position.
- Temporary browser test note was removed after verification; reading positions remain.
- Phone viewport (390 × 844): browse and reader render correctly, and browse document has no horizontal overflow. Temporary viewport override was reset.
- JavaScript syntax and Python compilation checks pass.

## Limits

- All files were inventoried; every page of every issue has not been rendered. Real samples were checked across all eight discs, and two sample issues were fully rendered.
- Nine catalog dates have no corresponding issue file: 1947-09-06; 1989-02-20, 04-03, 07-03, 08-14, 08-28, 10-09, 10-16, 11-27. They remain searchable and are visibly marked unavailable.
- Original folios occasionally repeat. Article links choose the first matching scan; all scans remain navigable. 114 entries have no exact folio mapping; they are marked unverified, and the app offers issue browsing rather than claiming an exact article location.
- Search uses catalog text, not full-page OCR.
- One shared personal library; no user-account separation.
- Dockerfile and Compose configuration supplied. Docker is not installed on this Mac, so a container build/run has not been verified here.
- Native runtime verified with Python 3.14.5 / macOS / DjVuLibre 3.5.30. Other target platforms need their own deployment check.

Screenshots are in `docs/screenshots/`.
