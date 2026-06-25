#!/usr/bin/env bash
# walk-and-talk: audio-check (macOS) — diagnose AND fix the hands-free voice loop.
#
# Surfaces the two traps found while dogfooding (you hear the brief, talk back,
# and nothing happens):
#   1. Voice Control isn't running -> nothing captures your speech, so dictation
#      is silently dropped. (Can't be toggled from a script reliably — it's an
#      Accessibility setting needing the UI + permissions — but --fix opens the
#      exact settings pane for you.)
#   2. Bluetooth earbuds set as BOTH default mic and default output -> macOS drops
#      them into low-quality HFP ("phone call") mode when the mic is used,
#      degrading what you hear. --fix moves INPUT to the built-in mic (needs
#      SwitchAudioSource: `brew install switchaudio-osx`), keeping earbuds for
#      OUTPUT only.
#
# Usage:
#   audio-check.sh            # diagnose only
#   audio-check.sh --fix      # apply the automatable fixes (mic switch + open VC pane)
# Exit: 0 always (diagnostic).
set -uo pipefail

FIX=0
[ "${1:-}" = "--fix" ] && FIX=1

if [ "$(uname -s)" != "Darwin" ]; then
  echo "audio-check: macOS-only (input/output routing differs elsewhere). Skipping."
  exit 0
fi

AUDIO="$(system_profiler SPAudioDataType 2>/dev/null || true)"

# default input/output device name + transport
parse="$(awk '
  function flush() {
    if (dev!="") {
      if (din=="yes") printf "IN|%s|%s\n", dev, tr
      if (dout=="yes") printf "OUT|%s|%s\n", dev, tr
    }
    din=""; dout=""; tr=""
  }
  /^[[:space:]]+[^[:space:]].*:[[:space:]]*$/ { flush(); dev=$0; gsub(/^[[:space:]]+/,"",dev); sub(/:[[:space:]]*$/,"",dev); next }
  /Default Input Device: Yes/  { din="yes" }
  /Default Output Device: Yes/ { dout="yes" }
  /Transport:/ { tr=$NF }
  END { flush() }
' <<<"$AUDIO")"
IN_DEV="$(printf '%s\n' "$parse" | awk -F'|' '/^IN\|/{print $2; exit}')"
IN_TR="$(printf '%s\n' "$parse" | awk -F'|' '/^IN\|/{print $3; exit}')"
OUT_DEV="$(printf '%s\n' "$parse" | awk -F'|' '/^OUT\|/{print $2; exit}')"
OUT_TR="$(printf '%s\n' "$parse" | awk -F'|' '/^OUT\|/{print $3; exit}')"

# the built-in mic name (model varies: "MacBook Pro/Air Microphone", "Built-in Microphone")
BUILTIN_MIC="$(awk '
  /^[[:space:]]+[^[:space:]].*:[[:space:]]*$/ { name=$0; gsub(/^[[:space:]]+/,"",name); sub(/:[[:space:]]*$/,"",name); tr=""; isin=0 }
  /Transport:[[:space:]]*Built-in/ { tr="builtin" }
  /Input (Channels|Source)/ { isin=1 }
  (tr=="builtin" && isin==1) { print name; exit }
' <<<"$AUDIO")"

echo "walk-and-talk audio check"
echo "========================="
echo "  default mic (input):  ${IN_DEV:-?}  [${IN_TR:-?}]"
echo "  default output:       ${OUT_DEV:-?}  [${OUT_TR:-?}]"
if [ "$OUT_TR" = "Bluetooth" ]; then
  echo "  earbuds:              connected and playing"
else
  echo "  earbuds:              not connected. For a walk, turn them on and connect them"
  echo "                        (click the sound icon in the menu bar, pick your earbuds)."
  echo "                        At a desk, the laptop speakers are fine — no earbuds needed."
fi

# --- Trap 2: same Bluetooth device for mic + output ---
if [ -n "$IN_DEV" ] && [ "$IN_DEV" = "$OUT_DEV" ] && [ "$IN_TR" = "Bluetooth" ]; then
  echo
  echo "  ⚠ HFP trap: '$IN_DEV' is your mic AND your output over Bluetooth — using it"
  echo "    as a mic forces low-quality 'phone call' mode and degrades your TTS."
  if [ "$FIX" -eq 1 ]; then
    if command -v SwitchAudioSource >/dev/null 2>&1 && [ -n "$BUILTIN_MIC" ]; then
      SwitchAudioSource -t input -s "$BUILTIN_MIC" >/dev/null 2>&1 \
        && echo "    ✓ FIXED: input → '$BUILTIN_MIC' (earbuds stay output-only, full quality)." \
        || echo "    ✗ could not switch input automatically — set it in System Settings → Sound → Input."
    elif ! command -v SwitchAudioSource >/dev/null 2>&1; then
      echo "    To auto-fix this, install the switcher: brew install switchaudio-osx"
    else
      echo "    Couldn't detect a built-in mic to switch to — set input manually."
    fi
  else
    echo "    Fix: set INPUT to the built-in mic (earbuds for OUTPUT only). Re-run with"
    echo "    --fix to do it automatically, or System Settings → Sound → Input."
  fi
fi

# --- Trap 1: Voice Control running? (best-effort) ---
# Voice Control state can't be detected reliably (no VC-specific process or API),
# so don't assert on/off — surface the things that actually trip people up.
VC_HINT=""
pgrep -xi 'corespeechd' >/dev/null 2>&1 || pgrep -fi 'DictationIM' >/dev/null 2>&1 && VC_HINT="  (speech services are active)"
echo
echo "  Voice Control — confirm it's ON in the menu bar$VC_HINT. It's an Accessibility"
echo "  toggle (System Settings → Accessibility → Voice Control), not plain Dictation, and"
echo "  a script can't flip it reliably. One trap once it's on:"
echo "    • Set Voice Control's OWN Microphone (in its menu) to your built-in mic, NOT"
echo "      'Automatic' — Automatic can latch onto a dead aggregate device and hear nothing."
echo "  Quick check it hears you: say \"open Notes\" — if Notes opens, the mic is good."
echo "  To SUBMIT hands-free, use the auto-submit helper:"
echo "      bash \"\$(dirname \"\$0\")/auto-submit/run.sh\" --button   # earbud tap presses Return"
echo "  Do NOT make a Voice Control \"Press Keyboard Shortcut → Return\" custom command —"
echo "  current macOS can't bind Return to it (it mis-binds, e.g. \"Press A\"). Otherwise tap Return."
if [ "$FIX" -eq 1 ]; then
  open "x-apple.systempreferences:com.apple.preference.universalaccess?VoiceControl" >/dev/null 2>&1 \
    && echo "    ✓ opened the Voice Control settings pane."
fi

echo
echo "  Loop: dictate → submit (earbud-tap via auto-submit, or tap Return) → I answer + speak."
echo "  See references/hands-free-input.md for the full submit options."
