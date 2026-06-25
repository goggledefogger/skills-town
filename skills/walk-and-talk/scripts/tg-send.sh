#!/usr/bin/env bash
# walk-and-talk: tg-send — push a spoken reply to the phone as a Telegram VOICE
# NOTE, so a walk works on Android *and* iOS through earbuds.
#
# Why this exists: speak.sh's macOS `say` only plays on the Mac's own speakers.
# On a walk you drive the Mac's Claude Code session from your phone over SSH, so
# that audio never reaches you. Telegram voice notes auto-play on the phone (same
# behavior on Android + iOS), through whatever earbuds are paired to the PHONE —
# closing the output half of the loop without a screen reader.
#
# Config (lives in the gitignored <vault>/.walk-and-talk/telegram.env — secrets
# never hit git):
#   WAT_TG_TOKEN=123456:ABC...     # bot token from @BotFather
#   WAT_TG_CHAT=123456789          # your chat id (discover with --get-chat-id)
# Either source that file via --state-dir, or pass the two vars in the environment.
#
# Usage:
#   tg-send.sh --state-dir <dir> --text "hello"   # say -> ogg/opus -> sendVoice
#   tg-send.sh --state-dir <dir> --get-chat-id    # AFTER you message the bot once
#   tg-send.sh --state-dir <dir> --test           # send a test voice note
#   tg-send.sh --state-dir <dir> --setup          # guided setup, one step at a time
#   tg-send.sh --token <t> --chat <c> --text "hi" # explicit, no config file
#
# Exit codes: 0 ok · 2 bad args · 3 missing token/chat · 4 send failed.
set -uo pipefail

STATE_DIR=""; TEXT=""; MODE="send"; RATE="${WAT_SPEAK_RATE:-185}"
TOKEN="${WAT_TG_TOKEN:-}"; CHAT="${WAT_TG_CHAT:-}"

while [ $# -gt 0 ]; do
  case "$1" in
    --state-dir) STATE_DIR="${2:-}"; shift 2 ;;
    --text)      TEXT="${2:-}"; shift 2 ;;
    --token)     TOKEN="${2:-}"; shift 2 ;;
    --chat)      CHAT="${2:-}"; shift 2 ;;
    --get-chat-id) MODE="chatid"; shift ;;
    --test)      MODE="test"; shift ;;
    --setup)     MODE="setup"; shift ;;
    *) echo "tg-send: unknown arg: $1" >&2; exit 2 ;;
  esac
done

# Pull token/chat from the gitignored config if not already set.
if [ -n "$STATE_DIR" ] && [ -f "$STATE_DIR/telegram.env" ]; then
  # shellcheck disable=SC1090
  set -a; . "$STATE_DIR/telegram.env"; set +a
  TOKEN="${TOKEN:-${WAT_TG_TOKEN:-}}"
  CHAT="${CHAT:-${WAT_TG_CHAT:-}}"
fi

API="https://api.telegram.org/bot${TOKEN}"

# --- guided setup: figure out which step the user is on; print ONLY plain words
# for the user (no file paths, flags, or var names) and self-heal what it can. ---
if [ "$MODE" = "setup" ]; then
  ENVF="${STATE_DIR:+$STATE_DIR/telegram.env}"; ENVF="${ENVF:-telegram.env}"
  if [ -z "$TOKEN" ]; then
    cat <<'EOF'
To hear me on your phone, set up a quick Telegram bot — about a minute, on your phone:
  • Open Telegram and message @BotFather
  • Send /newbot and follow the prompts
  • Copy the token it gives you
Then paste that token to me here and I'll save it for you.
EOF
    exit 0
  fi
  if [ -z "$CHAT" ]; then
    resp="$(curl -fsS "${API}/getUpdates" 2>/dev/null || true)"
    cid=""
    if [ -n "$resp" ] && command -v python3 >/dev/null 2>&1; then
      cid="$(python3 - "$resp" <<'PY'
import json, sys
d = json.loads(sys.argv[1])
for u in d.get("result", []):
    m = u.get("message") or u.get("edited_message") or {}
    c = m.get("chat") or {}
    if c.get("id") is not None:
        print(c["id"]); break
PY
)"
    fi
    if [ -z "$cid" ]; then
      cat <<'EOF'
Almost there — open your new bot in Telegram and send it any message (like "hi").
Then tell me you've done that.
EOF
      exit 0
    fi
    # Save the chat id for the user so they never touch a file.
    if [ -f "$ENVF" ] && grep -q '^WAT_TG_CHAT=' "$ENVF" 2>/dev/null; then
      tmpf="$(mktemp)"; sed "s|^WAT_TG_CHAT=.*|WAT_TG_CHAT=${cid}|" "$ENVF" > "$tmpf" && mv "$tmpf" "$ENVF"
    else
      printf 'WAT_TG_CHAT=%s\n' "$cid" >> "$ENVF"
    fi
    CHAT="$cid"
  fi
  echo "All set — sending a test to your phone now."
  MODE="test"
fi

if [ -z "$TOKEN" ]; then
  echo "tg-send: no bot token (set WAT_TG_TOKEN in $STATE_DIR/telegram.env)." >&2
  exit 3
fi

# --- discover chat id: read recent updates after you DM the bot once ---
if [ "$MODE" = "chatid" ]; then
  resp="$(curl -fsS "${API}/getUpdates" 2>/dev/null || true)"
  if [ -z "$resp" ]; then echo "tg-send: getUpdates failed (token wrong?)." >&2; exit 4; fi
  if command -v python3 >/dev/null 2>&1; then
    python3 - "$resp" <<'PY'
import json, sys
data = json.loads(sys.argv[1])
seen = {}
for u in data.get("result", []):
    msg = u.get("message") or u.get("edited_message") or {}
    ch = msg.get("chat") or {}
    if ch.get("id") is not None:
        who = ch.get("username") or ch.get("first_name") or ch.get("title") or "?"
        seen[ch["id"]] = who
if not seen:
    print("No messages yet. Open Telegram, send your bot any message, then re-run.")
else:
    print("Chat id(s) found — add WAT_TG_CHAT=<id> to telegram.env:")
    for cid, who in seen.items():
        print(f"  {cid}   ({who})")
PY
  else
    echo "$resp" | grep -oE '"chat":\{"id":[-0-9]+' | grep -oE '[-0-9]+$' | sort -u
  fi
  exit 0
fi

[ "$MODE" = "test" ] && TEXT="${TEXT:-Walk and talk bridge is working. You should hear this through your earbuds.}"
[ -n "$TEXT" ] || { echo "tg-send: nothing to send (--text)." >&2; exit 2; }
if [ -z "$CHAT" ]; then
  echo "tg-send: no chat id (run --get-chat-id, then set WAT_TG_CHAT)." >&2
  exit 3
fi

# --- render speech -> ogg/opus (Telegram voice-note format) and send ---
tmp="$(mktemp -d "${TMPDIR:-/tmp}/wat-tg.XXXXXX")"
trap 'rm -rf "$tmp"' EXIT
aiff="$tmp/r.aiff"; ogg="$tmp/r.ogg"

if [ "$(uname -s)" = "Darwin" ] && command -v say >/dev/null 2>&1; then
  say -r "$RATE" -o "$aiff" "$TEXT" 2>/dev/null || true
fi

ok_voice=0
if [ -s "$aiff" ] && command -v ffmpeg >/dev/null 2>&1; then
  # Voice notes must be OPUS-in-OGG; homebrew ffmpeg ships libopus.
  if ffmpeg -y -loglevel error -i "$aiff" -c:a libopus -b:a 32k "$ogg" 2>/dev/null && [ -s "$ogg" ]; then
    if curl -fsS -X POST "${API}/sendVoice" \
        -F "chat_id=${CHAT}" -F "voice=@${ogg};type=audio/ogg" \
        -F "caption=" >/dev/null 2>&1; then
      ok_voice=1
    fi
  fi
fi

# Fallbacks: m4a via afconvert as a normal audio file, else plain text message —
# so the user still gets *something* even if audio encoding/upload fails.
if [ "$ok_voice" = "0" ]; then
  m4a="$tmp/r.m4a"
  if [ -s "$aiff" ] && command -v afconvert >/dev/null 2>&1 \
     && afconvert "$aiff" "$m4a" -f m4af -d aac >/dev/null 2>&1 && [ -s "$m4a" ]; then
    curl -fsS -X POST "${API}/sendAudio" -F "chat_id=${CHAT}" -F "audio=@${m4a};type=audio/mp4" >/dev/null 2>&1 \
      && ok_voice=1
  fi
fi
if [ "$ok_voice" = "0" ]; then
  curl -fsS -X POST "${API}/sendMessage" \
    --data-urlencode "chat_id=${CHAT}" --data-urlencode "text=🔊 ${TEXT}" >/dev/null 2>&1 \
    || { echo "tg-send: all send paths failed." >&2; exit 4; }
fi
exit 0
