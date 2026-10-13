# Standalone archive — 2026-10-13

User-approved direction: independent modern archive app, with file access established before UI work. Initial release uses a local Python HTTP server and browser UI. No cloud APIs, original application, or activation dependency.

## Architecture
An importer reads the shipped catalog and cover images, writes a normalized SQLite catalog with full-text indexing over titles/abstracts/bylines/keywords, and inventories all eight ISO-format MDF files. The source images remain read-only. Issue identifiers preserve original article-to-page relationships. DjVu CELX chunks are decoded using the validated Blowfish method, then rendered with DjVuLibre. Per-issue decoded standard DjVu files and per-page image caches are created on demand. Cached files can be deleted and rebuilt. Personal reading progress, collections, and notes live in a separate writable SQLite database.

## Experience
Warm ivory, ink typography, quiet red accents, cover imagery and ample whitespace. Cover browsing by year/decade, unified catalog search with year/contributor/department filters, article details and direct page links. Reader supports page navigation, printed folio labels, zoom, keyboard controls, issue contents, bookmarks, notes and resume reading. Responsive layout supports desktop and mobile. A library screen holds saved items and reading history.

## Delivery and validation
Docker Compose binds source images read-only and keeps app data in a separate volume. A native launcher supports this Mac. Validate importer counts and issue availability, article-page mapping, protected and standard DjVu decoding, API query bounds, personal data persistence and page rendering. Browser QA covers browsing, search, reading and saved items. Full article OCR is deferred: catalog text exists, image-only sample pages lack a searchable text layer.

## Implementation sequence
1. Format-aware ISO reader, importer and normalized catalog.
2. Decoder/render cache and HTTP APIs.
3. Responsive browse/search/reader/library UI.
4. Packaging, documentation, API and browser verification.
