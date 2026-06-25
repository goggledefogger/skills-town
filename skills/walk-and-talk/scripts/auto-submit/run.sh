#!/usr/bin/env bash
# walk-and-talk: auto-submit — Apple-native hands-free "submit" (OPTION, not the
# default; tap-Return stays the simplest path). Compiles auto-submit.swift once
# (cached) and runs it. Two ways to press Return without the keyboard:
#   --button  tap your Bluetooth/headphone play-pause to submit (no music)
#   --voice   submit after you speak then go quiet (tune --hangover-ms)
#   --both    (default) both
#
# Usage:
#   run.sh                      # both
#   run.sh --button             # just the earbud-tap
#   run.sh --voice --hangover-ms 1800
#
# Permissions (one time): Accessibility (key-press + media-key tap) and, for
# --voice, Microphone — grant them to the terminal/app that runs this.
set -euo pipefail
cd "$(dirname "$0")"

SRC="auto-submit.swift"
BIN="build/auto-submit"   # build/ is gitignored

command -v swiftc >/dev/null 2>&1 || {
  echo "auto-submit needs swiftc (Xcode Command Line Tools): xcode-select --install" >&2
  exit 1
}

mkdir -p build
if [ ! -x "$BIN" ] || [ "$SRC" -nt "$BIN" ]; then
  echo "compiling auto-submit.swift…" >&2
  swiftc -O "$SRC" -o "$BIN"
fi

echo "Note: needs Accessibility (+ Microphone for --voice). Grant if prompted:" >&2
echo "      System Settings → Privacy & Security → Accessibility / Microphone." >&2
exec "$BIN" "$@"
