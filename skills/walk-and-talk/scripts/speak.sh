#!/usr/bin/env bash
# walk-and-talk: speak — on-device TTS with a trailing-silence guard, a visible
# transcript, and repeat.
#
# Two problems it solves:
#  1. Bluetooth clips the tail — when TTS ends and the stream closes, the last
#     ~0.3-0.7s buffered in the headphones never flushes, cutting the final word.
#     Fix: append [[slnc]] silence (last word survives); small lead avoids
#     first-word clipping while BT "wakes". Harmless on wired/built-in.
#  2. You might MISS what was said — so the text is also printed and logged, and
#     can be repeated. (The assistant must ALSO restate spoken text in its visible
#     reply: the client can collapse tool output, so the words must live in the
#     message, not only here.)
#
# Usage:
#   speak.sh "text"            # speak + print + log
#   echo "text" | speak.sh
#   speak.sh --repeat          # re-speak the last thing said
#
# Env: WAT_SPEAK_RATE (wpm, 185), WAT_SPEAK_TAIL_MS (700, device-dependent),
#      WAT_SPEAK_LEAD_MS (150), WAT_STATE_DIR (=<vault>/.walk-and-talk to persist
#      the transcript + last-spoken for see/repeat).
set -uo pipefail

RATE="${WAT_SPEAK_RATE:-185}"
TAIL_MS="${WAT_SPEAK_TAIL_MS:-700}"
LEAD_MS="${WAT_SPEAK_LEAD_MS:-150}"
STATE_DIR="${WAT_STATE_DIR:-}"
LAST_FILE=""
[ -n "$STATE_DIR" ] && LAST_FILE="$STATE_DIR/last-spoken.txt"

if [ "${1:-}" = "--repeat" ]; then
  if [ -n "$LAST_FILE" ] && [ -f "$LAST_FILE" ]; then
    TEXT="$(cat "$LAST_FILE")"
  else
    echo "speak: nothing to repeat (set WAT_STATE_DIR; no last-spoken.txt yet)." >&2
    exit 1
  fi
else
  TEXT="${1:-}"
  [ -n "$TEXT" ] || TEXT="$(cat)"
fi
[ -n "$TEXT" ] || exit 0

# Make it visible — so a missed word can still be SEEN.
printf '🔊 %s\n' "$TEXT"

# Persist for see / repeat / scrollback.
if [ -n "$STATE_DIR" ]; then
  mkdir -p "$STATE_DIR/transcripts" 2>/dev/null || true
  printf '%s\n' "$TEXT" > "$LAST_FILE" 2>/dev/null || true
  printf '[%s] %s\n' "$(date +%H:%M)" "$TEXT" >> "$STATE_DIR/transcripts/session-$(date +%F).txt" 2>/dev/null || true
fi

# WAT_SILENT=1 -> text only, no audio (e.g. headphones disconnected — don't blast
# the laptop speakers). The text was already printed + logged above, so nothing
# is lost; "repeat" still works once audio is back.
SILENT="${WAT_SILENT:-0}"
if [ "$SILENT" = "0" ] || [ "$SILENT" = "false" ]; then
  if [ "$(uname -s)" = "Darwin" ] && command -v say >/dev/null 2>&1; then
    say -r "$RATE" "[[slnc ${LEAD_MS}]] ${TEXT} [[slnc ${TAIL_MS}]]"
  fi
fi

# Cross-device output: `say` above only reaches THIS Mac's speakers. On a walk you
# drive this session from your phone over SSH, so also push the line to the phone
# as a Telegram voice note when a bridge is configured (gitignored telegram.env or
# WAT_TG_TOKEN+WAT_TG_CHAT). Non-fatal and best-effort — local audio/transcript
# above already guarantee nothing is lost.
if { [ -n "${WAT_TG_TOKEN:-}" ] && [ -n "${WAT_TG_CHAT:-}" ]; } \
   || { [ -n "$STATE_DIR" ] && [ -f "$STATE_DIR/telegram.env" ]; }; then
  "$(dirname "$0")/tg-send.sh" --state-dir "$STATE_DIR" --text "$TEXT" >/dev/null 2>&1 || true
fi
