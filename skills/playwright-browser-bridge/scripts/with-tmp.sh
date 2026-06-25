#!/bin/bash
# Run a command with a fresh, SELF-DELETING temp dir for anything the browser downloads or exports.
# The dir is removed on exit no matter how the command ends — so fetched data never lingers or gets
# committed. The path is exported as BRIDGE_TMP.
#
# Usage:
#   bash with-tmp.sh -- <command...>
#   # e.g.  bash with-tmp.sh -- python3 parse_export.py "$BRIDGE_TMP/download.csv"
set -e
[ "$1" = "--" ] && shift
[ -z "$1" ] && { echo "usage: with-tmp.sh -- <command...>" >&2; exit 1; }

BRIDGE_TMP="$(mktemp -d "${TMPDIR:-/tmp}/bridge.XXXXXX")"
export BRIDGE_TMP
cleanup() { rm -rf "$BRIDGE_TMP"; }
trap cleanup EXIT INT TERM
echo "[bridge] scratch dir: $BRIDGE_TMP (auto-deletes on exit)" >&2
"$@"
