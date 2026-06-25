#!/usr/bin/env bash
# walk-and-talk: engine-route (Epic 5, stories 5.1-5.4) — the local-model seam.
#
# Resolves which engine (cloud|local) a given step runs on. Local models are
# GRADUAL + PLANNED and OFF BY DEFAULT (§12): everything resolves to cloud unless
# the config opts a step in, and even then the rung gate (invariant #6) refuses
# to route an *agentic* step to local unless that model was proven with
# probe-opencode.sh from the integrating-local-models skill.
#
# Resolution order for a step:
#   1. config engine.<step>  (else engine.default, else cloud)
#   2. transcription urgency escalation: urgency=high forces cloud even if local
#   3. agentic gate: agentic step + local + not verified  ->  downgrade to cloud
#
# Usage:
#   engine-route.sh --vault P --step draft [--urgency normal] [--json]
#   engine-route.sh --vault P --step transcription --urgency low
#   engine-route.sh --vault P --step orchestration --verify --model lmstudio/qwen3.5-9b
#
# Exit: 0 ok; 2 usage. (Resolution always returns an engine; it never fails the run.)
set -uo pipefail

VAULT=""; STEP=""; URGENCY="normal"; JSON_ONLY=0; VERIFY=0; MODEL=""
while [ $# -gt 0 ]; do
  case "$1" in
    --vault) VAULT="${2:-}"; shift 2 ;;
    --step) STEP="${2:-}"; shift 2 ;;
    --urgency) URGENCY="${2:-}"; shift 2 ;;
    --model) MODEL="${2:-}"; shift 2 ;;
    --verify) VERIFY=1; shift ;;
    --json) JSON_ONLY=1; shift ;;
    -h|--help) sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

[ -n "$VAULT" ] && [ -d "$VAULT" ] || { echo "ERROR(usage): --vault PATH (existing) required" >&2; exit 2; }
[ -n "$STEP" ] || { echo "ERROR(usage): --step required" >&2; exit 2; }

STATE_DIR="$VAULT/.walk-and-talk"
CFG="$STATE_DIR/config.yaml"
VERIFIED="$STATE_DIR/local-verified.txt"   # lines: "<step> <model>" proven agentic-ready

# Agentic (rung-3) steps must not run on an unproven local model. Everything else
# is completion-shaped (rung-2 safe). Unknown steps are treated as agentic (safe default).
is_agentic() {
  case "$1" in
    auditory_view|draft|transcription|summarize) return 1 ;;  # completion-shaped
    *) return 0 ;;                                             # orchestration, git, vault-nav, unknown
  esac
}

# --- verify path: run the sibling rung probe, record on pass ---
if [ "$VERIFY" -eq 1 ]; then
  [ -n "$MODEL" ] || { echo "ERROR(usage): --verify needs --model" >&2; exit 2; }
  SIB="$(dirname "$0")/../../integrating-local-models/scripts"
  if is_agentic "$STEP"; then PROBE="$SIB/probe-opencode.sh"; ARGS=(--model "$MODEL"); else PROBE="$SIB/probe.sh"; ARGS=(--model "$MODEL"); fi
  if [ ! -x "$PROBE" ] && [ ! -f "$PROBE" ]; then
    echo "Cannot find probe: $PROBE (is the integrating-local-models skill installed?)" >&2; exit 2
  fi
  echo "Running rung gate for step '$STEP' / model '$MODEL' via $(basename "$PROBE")..."
  if bash "$PROBE" "${ARGS[@]}"; then
    mkdir -p "$STATE_DIR"
    grep -qxF "$STEP $MODEL" "$VERIFIED" 2>/dev/null || echo "$STEP $MODEL" >> "$VERIFIED"
    echo "VERIFIED: '$STEP' may use local model '$MODEL'."
  else
    echo "NOT verified: '$STEP' stays on cloud for '$MODEL'." >&2
  fi
  exit 0
fi

# --- resolve ---
cfg_engine() { # $1 = key under engine: ; echoes value or empty
  [ -f "$CFG" ] || return 0
  awk -v k="$1" '
    /^engine:/ {inblk=1; next}
    inblk && /^[^[:space:]]/ {inblk=0}
    inblk && $1==k":" {print $2; exit}
  ' "$CFG"
}

requested="$(cfg_engine "$STEP")"
[ -n "$requested" ] || requested="$(cfg_engine default)"
[ -n "$requested" ] || requested="cloud"

resolved="$requested"
reason="from config (engine.${STEP:-default})"

# urgency escalation for transcription: a human waiting -> cloud
if [ "$STEP" = "transcription" ] && [ "$URGENCY" = "high" ] && [ "$resolved" = "local" ]; then
  resolved="cloud"; reason="urgency=high escalates transcription to cloud"
fi

# agentic gate
if [ "$resolved" = "local" ] && is_agentic "$STEP"; then
  if grep -qxF "$STEP ${MODEL:-}" "$VERIFIED" 2>/dev/null || { [ -z "$MODEL" ] && grep -q "^$STEP " "$VERIFIED" 2>/dev/null; }; then
    reason="agentic step, local model verified (rung 3)"
  else
    resolved="cloud"
    reason="agentic step not proven on local (run --verify; see integrating-local-models) -> cloud"
  fi
fi

if [ "$JSON_ONLY" -eq 1 ]; then
  printf '{"step":"%s","urgency":"%s","requested":"%s","resolved":"%s","reason":"%s"}\n' \
    "$STEP" "$URGENCY" "$requested" "$resolved" "$reason"
else
  echo "step:      $STEP"
  echo "resolved:  $resolved   ($reason)"
  if [ "$resolved" = "local" ]; then
    echo "reminder:  resource discipline — don't co-resident a heavy LLM + STT + TTS;"
    echo "           prefer small Whisper; split capture(phone)/orchestration(desktop)."
  fi
fi
