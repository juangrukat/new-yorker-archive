# The Archive

A standalone reading room for **The Complete New Yorker (1925–2005)**. Reads the original ISO-format `.mdf` disc images, decodes their SDJV pages, and serves a modern browser app. No original executable, activation service, external fonts, or cloud API is required.

## Features

- Cover browsing by decade/year and chronological sorting.
- Unified search over 188,792 catalog entries: titles, bylines, abstracts, and keywords, with contributor/department/year filters.
- Original scanned pages with zoom, keyboard navigation, printed page labels, issue contents, and automatic reading progress.
- Saved pages, named collections, and notes, stored in a separate personal database.
- Download a decoded, standard DjVu issue.
- On-demand document/image caching; original discs remain read-only.

## Run on this Mac

Requires Python 3.12+ and DjVuLibre. First-time import also requires 7-Zip:

```sh
brew install djvulibre sevenzip
./start.sh
```

Open **http://localhost:8765**. The default source is `/Volumes/two1/the_complete_new_yorker`. Override it if needed:

```sh
TNY_SOURCE=/path/to/discs TNY_DATA=/path/to/app-data ./start.sh
```

First startup imports the original catalog and thumbnails from the Mac installer on disc 1. It inventories the images without copying or mounting them. Allow a few minutes for import. The server starts once import finishes. Keep the archive drive connected while reading uncached issues.

## Run on a standalone server

Requires Docker with Compose:

```sh
ARCHIVE_PATH=/path/to/discs docker compose up --build -d
```

Open http://localhost:8765. The source directory is mounted read-only; `./data` holds the normalized catalog, thumbnails, personal data, and caches. Move the application source and disc images to the server; the old application is unnecessary. Supported images have 2048-byte sectors and an ISO 9660 primary descriptor, as all eight supplied images do. The accompanying `.mds` files are not needed.

The app defaults to loopback access. It has **one shared personal library and no account system**. For remote access, use an SSH tunnel (`ssh -L 8765:localhost:8765 your-server`) or a reverse proxy with authentication/TLS. Do not expose it as an unauthenticated public service. Native LAN hosting is possible with `TNY_HOST=0.0.0.0 ./start.sh`; all users then share bookmarks and notes.

## Data and maintenance

- `data/catalog.db`: normalized catalog and FTS5 index.
- `data/personal.db`: bookmarks, notes, and progress. Back this up.
- `data/covers/`: original cover thumbnails.
- `data/documents/`: standard DjVu copies, generated per issue on demand.
- `data/pages/`: rendered page JPEGs, generated on demand.
- `data/import.json`: import totals.

`documents/` and `pages/` can be removed while the server is stopped to reclaim space; they are rebuilt from the discs. The on-demand cache grows as you read; no automatic eviction is implemented. If the archive location changes, update `TNY_SOURCE` or `ARCHIVE_PATH`; stored image filenames are relative.

Rebuild the catalog while the server is stopped:

```sh
.venv/bin/python -m archive.importer --source /path/to/discs
```

If you already extracted the installer, pass `--legacy-root /path/to/extracted`. Import preserves `personal.db`. An interrupted import never replaces the previous complete catalog. Restart the server after importing to refresh catalog statistics.

## Scope and format

Search covers the original catalog, not OCR of the full scanned page text. Some catalog dates may have no matching file, and some printed folios repeat: links choose the first matching scan; every scan is available in the reader. Missing issues are visibly marked instead of fabricating content.

The decoder processes CELX Blowfish CBC chunks into ordinary DjVu, using the format described in [this independent format investigation](https://gist.github.com/NoMoreNicksLeft/d3a4a59c7b4de0cdef1e26695606e51c). It uses Python/PyCryptodome, then DjVuLibre for bundling/rendering. It does not load the original native libraries. The ISO reader deliberately uses the valid ISO 9660 view because the images' redundant UDF metadata causes stricter UDF parsers to fail.

## Verification

```sh
.venv/bin/pip install httpx
.venv/bin/python -m unittest discover -s tests -v
```

Tests use temporary personal storage, read-only catalog access, and supplied disc samples when present. See `docs/VALIDATION.md` for actual verification and limits.
