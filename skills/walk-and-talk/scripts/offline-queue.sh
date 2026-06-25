#!/usr/bin/env bash
# walk-and-talk: offline-queue (Epic 4, stories 4.1/4.2).
#
# Field durability: the user's words/drafts hit local disk HERE, before any
# network or model call (invariant #3 / FR-G1), so nothing is lost in a dead
# zone or on phone sleep. Jobs persist in <vault>/.walk-and-talk/queue/ and are
# drained FIFO when back online (FR-G2).
#
# Payloads are stored base64-encoded (text_b64) so arbitrary dictation — quotes,
# newlines, emoji — round-trips losslessly with zero JSON-escaping risk.
#
# Usage:
#   offline-queue.sh enqueue --vault P --kind capture|draft|transcription \
#       [--urgency low|normal|high] [--engine cloud|local] (--text "..." | --file PATH | -)
#   offline-queue.sh flush  --vault P            # FIFO JSON array of pending jobs (to process online)
#   offline-queue.sh done   --vault P --id ID    # remove a processed job (idempotent)
#   offline-queue.sh status --vault P            # queue depth
#
# Exit: 0 ok; 1 error; 2 usage. enqueue NEVER touches the network.
set -uo pipefail

CMD="${1:-}"; shift || true
VAULT=""; KIND="capture"; URGENCY="normal"; ENGINE="cloud"; TEXT=""; FILE=""; ID=""; FROM_STDIN=0
while [ $# -gt 0 ]; do
  case "$1" in
    --vault) VAULT="${2:-}"; shift 2 ;;
    --kind) KIND="${2:-}"; shift 2 ;;
    --urgency) URGENCY="${2:-}"; shift 2 ;;
    --engine) ENGINE="${2:-}"; shift 2 ;;
    --text) TEXT="${2:-}"; shift 2 ;;
    --file) FILE="${2:-}"; shift 2 ;;
    --id) ID="${2:-}"; shift 2 ;;
    -) FROM_STDIN=1; shift ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

[ -n "$VAULT" ] && [ -d "$VAULT" ] || { echo "ERROR(usage): --vault PATH (existing) required" >&2; exit 2; }
QDIR="$VAULT/.walk-and-talk/queue"

b64enc() { base64 | tr -d '\n'; }   # encode stdin -> single line

case "$CMD" in
  enqueue)
    # gather payload WITHOUT any network: --text, --file, or stdin
    if [ -n "$TEXT" ]; then payload="$TEXT"
    elif [ -n "$FILE" ]; then payload="$(cat "$FILE")"
    elif [ "$FROM_STDIN" -eq 1 ]; then payload="$(cat)"
    else echo "ERROR(usage): need --text, --file PATH, or - (stdin)" >&2; exit 2; fi
    mkdir -p "$QDIR" || { echo "ERROR: cannot create $QDIR" >&2; exit 1; }
    id="$(date +%Y%m%d%H%M%S)-$$-${RANDOM}"
    text_b64="$(printf '%s' "$payload" | b64enc)"
    cat > "$QDIR/$id.json" <<JSON
{
  "id": "$id",
  "created_at": "$(date -u +%FT%TZ)",
  "kind": "$KIND",
  "urgency": "$URGENCY",
  "engine": "$ENGINE",
  "text_b64": "$text_b64"
}
JSON
    echo "$id"
    ;;
  flush)
    # read-only: surface pending jobs FIFO (filename is timestamp-sortable) as a
    # JSON array. The assistant processes each (online) then calls `done --id`.
    shopt -s nullglob
    jobs=("$QDIR"/*.json)
    printf '['
    first=1
    for j in $(printf '%s\n' "${jobs[@]}" | sort); do
      [ "$first" -eq 1 ] || printf ','
      first=0
      printf '\n'; cat "$j"
    done
    [ "$first" -eq 1 ] && printf ']\n' || printf '\n]\n'
    ;;
  done)
    [ -n "$ID" ] || { echo "ERROR(usage): --id required" >&2; exit 2; }
    if [ -f "$QDIR/$ID.json" ]; then rm -f "$QDIR/$ID.json" && echo "removed $ID"; else echo "no such job: $ID (already done?)"; fi
    ;;
  status)
    shopt -s nullglob
    jobs=("$QDIR"/*.json)
    echo "queued jobs: ${#jobs[@]}"
    ;;
  *)
    echo "usage: offline-queue.sh {enqueue|flush|done|status} --vault P ..." >&2
    exit 2 ;;
esac
