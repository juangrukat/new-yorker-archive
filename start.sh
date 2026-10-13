#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi
export TNY_SOURCE="${TNY_SOURCE:-$(pwd)/discs}"
export TNY_DATA="${TNY_DATA:-$(pwd)/data}"
if ! command -v ddjvu >/dev/null 2>&1; then
  echo 'DjVuLibre is required: brew install djvulibre (macOS), or apt install djvulibre-bin (Linux).' >&2
  exit 1
fi
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi
if [ ! -f "$TNY_DATA/catalog.db" ]; then
  .venv/bin/python -m archive.importer
fi
exec .venv/bin/python -m uvicorn archive.server:app --host "${TNY_HOST:-127.0.0.1}" --port "${TNY_PORT:-8765}"
