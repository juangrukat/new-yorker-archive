#!/bin/sh
set -eu
if [ ! -f "$TNY_DATA/catalog.db" ]; then
  python -m archive.importer
fi
exec python -m uvicorn archive.server:app --host 0.0.0.0 --port 8765
