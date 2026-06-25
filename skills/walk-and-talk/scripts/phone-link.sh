#!/usr/bin/env bash
# walk-and-talk: phone-link — check & guide the context-continuing connection from
# the phone to the ONE Claude Code session on this Mac (Termius + Tailscale + tmux
# + Mosh). The Telegram bridge is audio-OUT only; THIS is what continues context:
# the phone reattaches to the same tmux session, so the conversation carries over.
#
# Read-only. It inspects readiness and prints the single next plain step. The
# assistant performs the installs (`brew install ...`) and `tailscale up` as
# visible steps, then relays the phone-side steps in plain words. Never make the
# user read this raw — translate it.
#
# Usage: phone-link.sh [--session NAME]   (default session name: walk)
set -uo pipefail

SESSION="walk"
while [ $# -gt 0 ]; do
  case "$1" in
    --session)   SESSION="${2:-walk}"; shift 2 ;;
    --vault|--state-dir) shift 2 ;;   # accepted for call-site symmetry; unused
    *) shift ;;
  esac
done

have(){ command -v "$1" >/dev/null 2>&1; }
USER_NAME="$(whoami)"
ssh_up=no; nc -z -G1 127.0.0.1 22 >/dev/null 2>&1 && ssh_up=yes
ts_state=""; ts_name=""
if have tailscale; then
  tailscale status >/dev/null 2>&1 && ts_state=up || ts_state=down
  ts_name="$(tailscale status --json 2>/dev/null | python3 -c 'import json,sys;print(json.load(sys.stdin).get("Self",{}).get("DNSName","").rstrip("."))' 2>/dev/null)"
fi

# Print ONLY the first unmet step, in plain words.
if ! have brew; then
  echo "NEXT (you): install Homebrew first — see https://brew.sh — tmux and mosh need it."; exit 0
fi
if ! have tmux || ! have mosh; then
  miss=""; have tmux || miss="tmux"; have mosh || miss="${miss:+$miss }mosh"
  echo "NEXT (assistant installs): the Mac needs ${miss}. Run:  brew install ${miss}"; exit 0
fi
if [ "$ssh_up" != "yes" ]; then
  echo "NEXT (you, ~10s): turn on Remote Login — System Settings > General > Sharing > Remote Login."; exit 0
fi
if ! have tailscale; then
  echo "NEXT (you): install the Tailscale app on this Mac AND your phone, signed into the SAME account."; exit 0
fi
if [ "$ts_state" != "up" ]; then
  echo "NEXT (assistant + you): Tailscale is installed but stopped. Run:  tailscale up  (sign in if asked). Then open Tailscale on your phone, same account."; exit 0
fi

# Everything Mac-side is ready — emit the connection facts + phone steps.
cat <<EOF
READY — the Mac side is set. Connection facts (for the phone app):
  host (Tailscale): ${ts_name:-<run: tailscale status>}
  username:         ${USER_NAME}
  tmux session:     ${SESSION}

On the phone, one time:
  1. Tailscale app — signed into the same account, so the phone can see this Mac.
  2. Termius (or Blink) — add a host:  address = ${ts_name:-<tailscale host>},
     username = ${USER_NAME},  turn Mosh ON.
  3. Set it to run on connect:  tmux new-session -A -s ${SESSION}
     (-A = attach if it exists, else create — so the session survives disconnects.)

Run walk-and-talk so it persists: on the Mac, start it INSIDE tmux —
  tmux new-session -A -s ${SESSION}    then launch Claude Code and start the session.
On the walk, Termius+Mosh reattaches to that SAME "${SESSION}" session — full context.
EOF
