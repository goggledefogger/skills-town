#!/bin/bash
# Single entrypoint. Routes to the stdlib-only Python tools (no deps, no venv).
#   ./run.sh resume <resume.json> [--theme classic|modern] [-o out.html]
#   ./run.sh cover  <letter.json> [-o out.html]
#   ./run.sh track  add|status|note|list|show ...
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
PY="$(command -v python3 || command -v python || true)"
[ -z "$PY" ] && { echo "python3 not found — install Python 3." >&2; exit 1; }

cmd="${1:-}"; shift || true
case "$cmd" in
  resume) exec "$PY" "$DIR/scripts/format_resume.py" "$@" ;;
  cover)  exec "$PY" "$DIR/scripts/format_cover_letter.py" "$@" ;;
  track)  exec "$PY" "$DIR/scripts/track_application.py" "$@" ;;
  *) echo "usage: ./run.sh {resume|cover|track} ..." >&2; exit 1 ;;
esac
