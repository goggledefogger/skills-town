#!/usr/bin/env bash
# walk-and-talk: ambient-watch — watch a project until the active work goes quiet,
# then SAY so. Pairs with ambient-check (the "tell me what I can't see" idea):
# you're told when it's safe to engage, eyes-free, instead of guessing.
#
# Usage:
#   ambient-watch.sh --project PATH [--interval 60] [--mins 15] [--max-min 60]
# Speaks (speak.sh) the busy→quiet transition. Stops after --max-min (says so).
set -uo pipefail

DIR="$(dirname "$0")"
PROJECT="$(pwd)"; INTERVAL=60; MINS=15; MAXMIN=60
while [ $# -gt 0 ]; do
  case "$1" in
    --project|--vault) PROJECT="${2:-}"; shift 2 ;;   # --vault alias
    --interval) INTERVAL="${2:-60}"; shift 2 ;;
    --mins) MINS="${2:-15}"; shift 2 ;;
    --max-min) MAXMIN="${2:-60}"; shift 2 ;;
    -h|--help) echo "usage: ambient-watch.sh --vault PATH [--interval 60] [--mins 15] [--max-min 60]"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

say_it() { bash "$DIR/speak.sh" "$1" >/dev/null 2>&1 || echo "$1"; }
name="$(basename "$PROJECT")"
deadline=$(( $(date +%s) + MAXMIN * 60 ))
seen_busy=0

while true; do
  if bash "$DIR/ambient-check.sh" --project "$PROJECT" --mins "$MINS" --json >/dev/null 2>&1; then
    # exit 0 = quiet
    if [ "$seen_busy" -eq 1 ]; then
      say_it "Heads up: the $name is quiet now — the other session stopped. Safe to engage."
    else
      echo "$name already quiet — nothing to watch."
    fi
    exit 0
  fi
  seen_busy=1
  if [ "$(date +%s)" -ge "$deadline" ]; then
    say_it "The $name is still active after $MAXMIN minutes — I've stopped watching. Check again when you want."
    exit 0
  fi
  sleep "$INTERVAL"
done
