#!/usr/bin/env bash
# walk-and-talk session / voice-mode state (Epic 2 + Epic 6).
#
# Owns <vault>/.walk-and-talk/state.json — the voice-mode flag, current session
# branch, and the active MODE (passive | active | quiet; see references/modes.md).
# Default mode is passive (Dan's principle: quiet, capture-only, until told
# otherwise). The behavioral contract is injected by the assistant on `start`;
# this script is the durable state that scripts + the assistant agree on.
#
# Usage:
#   session.sh start  --vault P [--branch walk/2026-06-18] [--mode passive|active|quiet]
#   session.sh status --vault P [--json]
#   session.sh mode   --vault P [--set MODE | --resolve]   # get / set / time-resolve the mode
#   session.sh stop   --vault P
#
# Exit: 0 ok; 1 error; 2 usage.
set -uo pipefail

CMD="${1:-}"; shift || true
VAULT=""; BRANCH=""; MODE=""; SET_MODE=""; RESOLVE=0; JSON_ONLY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --vault) VAULT="${2:-}"; shift 2 ;;
    --branch) BRANCH="${2:-}"; shift 2 ;;
    --mode) MODE="${2:-}"; shift 2 ;;
    --set) SET_MODE="${2:-}"; shift 2 ;;
    --resolve) RESOLVE=1; shift ;;
    --json) JSON_ONLY=1; shift ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

[ -n "$VAULT" ] && [ -d "$VAULT" ] || { echo "ERROR: --vault PATH (existing) required" >&2; exit 1; }
STATE_DIR="$VAULT/.walk-and-talk"
STATE="$STATE_DIR/state.json"
CFG="$STATE_DIR/config.yaml"

json_get() { # $1 key -> value from state.json (string/bool)
  [ -f "$STATE" ] || return 0
  grep -o "\"$1\": *\"\?[^\",}]*\"\?" "$STATE" | head -1 | sed 's/.*: *"\{0,1\}\([^"]*\)"\{0,1\}/\1/'
}

default_mode() {
  local d=""
  [ -f "$CFG" ] && d="$(grep -oE 'default_mode:[[:space:]]*[a-z]+' "$CFG" | head -1 | awk '{print $2}')"
  [ -n "$d" ] && echo "$d" || echo "passive"
}

resolve_mode() { # time-of-day triggers -> mode, else default
  local now chosen f t m
  now="$(date +%H:%M)"
  chosen=""
  if [ -f "$CFG" ]; then
    while read -r f t m; do
      [ -z "$m" ] && continue
      if [[ "$now" > "$f" || "$now" == "$f" ]] && [[ "$now" < "$t" || "$now" == "$t" ]]; then
        chosen="$m"; break
      fi
    done < <(grep -oE '[0-9]{2}:[0-9]{2}-[0-9]{2}:[0-9]{2} [a-z]+' "$CFG" | sed 's/-/ /')
  fi
  [ -n "$chosen" ] && echo "$chosen" || default_mode
}

write_state() { # $1 voice_mode  $2 mode  $3 branch  $4 started_at
  mkdir -p "$STATE_DIR" || { echo "ERROR: cannot create $STATE_DIR" >&2; exit 1; }
  cat > "$STATE" <<JSON
{
  "voice_mode": $1,
  "mode": "$2",
  "session_branch": "$3",
  "started_at": "$4"
}
JSON
}

# Tie Apple Voice Control listening to the mode (active -> on, passive/quiet -> off).
# Best-effort: vc-listen surfaces the right spoken command (see references/hands-free-input.md).
vc_for_mode() {
  local sh="$(dirname "$0")/vc-listen.sh"
  [ -f "$sh" ] || return 0
  case "$1" in
    active) bash "$sh" on ;;
    passive|quiet) bash "$sh" off ;;
  esac
}

case "$CMD" in
  start)
    # recover from an abruptly-ended previous session: clear strays so the earbud
    # tap / mic aren't left hijacked by a dead session.
    if [ "$(json_get voice_mode)" = "true" ]; then
      echo "• previous session didn't end cleanly — clearing strays."
      pkill -f 'auto-submit/build/auto-submit' 2>/dev/null || true
      pkill -f 'ambient-watch.sh' 2>/dev/null || true
    fi
    [ -n "$BRANCH" ] || BRANCH="walk/$(date +%F)"
    [ -n "$MODE" ] || MODE="$(resolve_mode)"
    write_state true "$MODE" "$BRANCH" "$(date -u +%FT%TZ)"
    echo "Voice mode ON. Mode: $MODE. Session branch: $BRANCH"
    case "$MODE" in
      passive) echo "(Passive: capture-only, stay quiet. Inject references/voice-mode-contract.md.)" ;;
      quiet)   echo "(Quiet: silent capture. Say nothing unless reached for.)" ;;
      active)  echo "(Active walk-and-work. Inject references/voice-mode-contract.md.)" ;;
    esac
    vc_for_mode "$MODE"
    ;;
  stop)
    # tear down background helpers — releases media controls, mic, now-playing
    pkill -f 'auto-submit/build/auto-submit' 2>/dev/null && echo "• stopped auto-submit (earbud/media controls + mic released)" || true
    pkill -f 'ambient-watch.sh' 2>/dev/null && echo "• stopped ambient-watch" || true
    write_state false "" "" ""
    pend=$(ls "$STATE_DIR"/queue/*.json 2>/dev/null | wc -l | tr -d ' ')
    [ "${pend:-0}" -gt 0 ] && echo "• ${pend} queued capture(s) still on disk — run offline-queue flush when online"
    echo "Voice mode OFF — session ended cleanly. Say \"Stop listening\" to take Voice Control out of dictation."
    ;;
  mode)
    cur="$(json_get mode)"; [ -n "$cur" ] || cur="$(default_mode)"
    if [ -n "$SET_MODE" ]; then
      vm="$(json_get voice_mode)"; [ -n "$vm" ] || vm=true
      br="$(json_get session_branch)"; st="$(json_get started_at)"
      write_state "${vm:-true}" "$SET_MODE" "$br" "$st"
      echo "Mode set: $SET_MODE"
      vc_for_mode "$SET_MODE"
    elif [ "$RESOLVE" -eq 1 ]; then
      new="$(resolve_mode)"
      vm="$(json_get voice_mode)"; [ -n "$vm" ] || vm=true
      br="$(json_get session_branch)"; st="$(json_get started_at)"
      write_state "${vm:-true}" "$new" "$br" "$st"
      echo "Mode resolved by time: $new"
      vc_for_mode "$new"
    else
      echo "$cur"
    fi
    ;;
  status)
    if [ ! -f "$STATE" ]; then
      [ "$JSON_ONLY" -eq 1 ] && echo '{"voice_mode": false, "mode": "'"$(default_mode)"'", "session_branch": "", "started_at": ""}' || echo "Voice mode: OFF (default mode $(default_mode))"
      exit 0
    fi
    if [ "$JSON_ONLY" -eq 1 ]; then
      cat "$STATE"
    else
      vm="$(json_get voice_mode)"; md="$(json_get mode)"; br="$(json_get session_branch)"
      echo "Voice mode: $([ "$vm" = true ] && echo ON || echo OFF)  mode: ${md:-?}${br:+  branch: $br}"
    fi
    ;;
  *)
    echo "usage: session.sh {start|stop|mode|status} --vault P [--branch B] [--mode M] [--set M] [--resolve] [--json]" >&2
    exit 2 ;;
esac
