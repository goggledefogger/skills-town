#!/usr/bin/env bash
# walk-and-talk: vc-listen — toggle Apple Voice Control listening (macOS).
#
# Ties listening to MODE: active -> on, passive/quiet -> off (so it's on and kept
# on while you work, off and kept off while you zone out). `session.sh` calls this
# on a mode change.
#
# Reality: macOS exposes no clean API to toggle Voice Control listening. The
# reliable control is the spoken command "Start listening" / "Stop listening"
# (a.k.a. "Wake up" / "Go to sleep") — so this script's job today is to tell you
# the right command for the mode. Programmatic toggling (UI scripting, needs
# Accessibility permission) is best-effort and arrives properly with the planned
# voice loop.
#
# Usage: vc-listen.sh on|off|toggle
set -uo pipefail
ACTION="${1:-toggle}"
[ "$(uname -s)" = "Darwin" ] || { echo "vc-listen: macOS-only."; exit 0; }
case "$ACTION" in on|off|toggle) ;; *) echo "usage: vc-listen.sh on|off|toggle" >&2; exit 2 ;; esac

# Best-effort programmatic toggle would go here (System Events UI scripting +
# Accessibility permission). Until that's reliable, surface the spoken command:
case "$ACTION" in
  on)     echo "Voice Control → ON:  say \"Start listening\" (or \"Wake up\")." ;;
  off)    echo "Voice Control → OFF: say \"Stop listening\" (or \"Go to sleep\")." ;;
  toggle) echo "Voice Control: say \"Start listening\" / \"Stop listening\" to toggle." ;;
esac
exit 0
