#!/usr/bin/env bash
# walk-and-talk: auditory-view — markdown -> ear-ready text (Epic 2, story 2.3).
# Pure stdin -> stdout. sanitize.py uses only the Python stdlib, so no venv is
# needed; we just need a Python 3 interpreter.
set -euo pipefail
cd "$(dirname "$0")"

if command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON=python
else
  echo "auditory-view needs Python 3 on PATH." >&2
  exit 1
fi

exec "$PYTHON" sanitize.py "$@"
