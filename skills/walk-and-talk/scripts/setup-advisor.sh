#!/usr/bin/env bash
# walk-and-talk setup advisor.
#
# Detects the user's situation, recommends the thinnest viable voice stack
# (naming the tested transport default and the SSH/web /voice constraint), and
# optionally writes a config + gitignores the state dir.
#
# READ-ONLY by default. Only --write-config mutates anything, and only inside
# the vault's .walk-and-talk/ state dir + the vault .gitignore.
#
# Usage:
#   setup-advisor.sh --vault /path/to/vault                 # human report
#   setup-advisor.sh --vault /path/to/vault --json          # capabilities JSON only
#   setup-advisor.sh --vault /path/to/vault --write-config  # write config.yaml + gitignore
#   setup-advisor.sh --vault /path/to/vault --write-config --force --dry-run
#
# Exit: 0 always for report/json (advice never fails). --write-config exits
#       non-zero only on a real write error.
set -uo pipefail

VAULT=""
JSON_ONLY=0
WRITE_CONFIG=0
FORCE=0
DRY_RUN=0

while [ $# -gt 0 ]; do
  case "$1" in
    --vault) VAULT="${2:-}"; shift 2 ;;
    --json) JSON_ONLY=1; shift ;;
    --write-config) WRITE_CONFIG=1; shift ;;
    --force) FORCE=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

# ---- detection (each probe is guarded; absence is reported, never errored) ----

OS="$(uname -s 2>/dev/null || echo unknown)"

IN_SSH=false
[ -n "${SSH_CONNECTION:-}${SSH_TTY:-}" ] && IN_SSH=true

CLAUDE_CLI=false
command -v claude >/dev/null 2>&1 && CLAUDE_CLI=true

GEMINI_KEY=false
[ -n "${GEMINI_API_KEY:-}${GOOGLE_API_KEY:-}" ] && GEMINI_KEY=true

WHISPER=false
for w in whisper whisper-cpp whisper-cli faster-whisper; do
  command -v "$w" >/dev/null 2>&1 && { WHISPER=true; break; }
done

LMSTUDIO=false
curl -s --max-time 1 http://localhost:1234/v1/models >/dev/null 2>&1 && LMSTUDIO=true
OLLAMA=false
curl -s --max-time 1 http://localhost:11434/api/tags >/dev/null 2>&1 && OLLAMA=true

# vault-dependent detection
V_EXISTS=false; V_OBSIDIAN=false; V_GIT=false; V_REMOTE=false; V_REMOTE_URL=""
SECOND_BRAIN="notes"; CAPTURE_PATH="Inbox/"; DAILY_HINT=""
if [ -n "$VAULT" ] && [ -d "$VAULT" ]; then
  V_EXISTS=true
  [ -d "$VAULT/.obsidian" ] && { V_OBSIDIAN=true; SECOND_BRAIN="obsidian"; }
  # sense the capture target (don't assume) — first existing inbox-ish dir wins
  for d in Inbox inbox 0-Inbox "00 Inbox" _inbox; do
    [ -d "$VAULT/$d" ] && { CAPTURE_PATH="$d/"; break; }
  done
  # hint a daily-note location for schedule_note (sensed, user confirms)
  for d in Daily "Daily Notes" Journal Calendar; do
    [ -d "$VAULT/$d" ] && { DAILY_HINT="$d/"; break; }
  done
  if git -C "$VAULT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    V_GIT=true
    if V_REMOTE_URL="$(git -C "$VAULT" remote get-url origin 2>/dev/null)" && [ -n "$V_REMOTE_URL" ]; then
      V_REMOTE=true
    fi
  fi
fi

# ---- capabilities JSON ----
read -r -d '' CAPS <<JSON
{
  "os": "$OS",
  "in_ssh": $IN_SSH,
  "claude_cli": $CLAUDE_CLI,
  "gemini_key": $GEMINI_KEY,
  "whisper": $WHISPER,
  "local_llm": { "lmstudio": $LMSTUDIO, "ollama": $OLLAMA },
  "vault": {
    "path": "$VAULT",
    "exists": $V_EXISTS,
    "is_obsidian": $V_OBSIDIAN,
    "is_git": $V_GIT,
    "has_remote": $V_REMOTE,
    "remote": "$V_REMOTE_URL"
  }
}
JSON

if [ "$JSON_ONLY" -eq 1 ]; then
  printf '%s\n' "$CAPS"
  exit 0
fi

# ---- human report + recommendation ----
yn() { [ "$1" = true ] && echo "yes" || echo "no"; }

echo "walk-and-talk — setup advisor"
echo "============================="
echo
echo "Detected:"
echo "  OS:                 $OS"
echo "  In SSH session:     $(yn $IN_SSH)"
echo "  Claude Code CLI:    $(yn $CLAUDE_CLI)"
echo "  Gemini/Google key:  $(yn $GEMINI_KEY)  (for optional rich TTS)"
echo "  Local Whisper:      $(yn $WHISPER)"
echo "  Local LLM:          LM Studio $(yn $LMSTUDIO), Ollama $(yn $OLLAMA)"
if [ -n "$VAULT" ]; then
  echo "  Vault:              $VAULT"
  echo "    exists:           $(yn $V_EXISTS)"
  echo "    Obsidian vault:   $(yn $V_OBSIDIAN)"
  echo "    git repo:         $(yn $V_GIT)"
  echo "    git remote:       $(yn $V_REMOTE)${V_REMOTE_URL:+  ($V_REMOTE_URL)}"
else
  echo "  Vault:              (none given — pass --vault PATH for full advice)"
fi
echo

echo "Recommendation:"
echo "  • The constraint: Claude Code native /voice does NOT work over SSH or"
echo "    Claude Code web — local machine only, and Remote Control is text-only."
if [ "$IN_SSH" = true ]; then
  echo "    You are in an SSH session right now, so /voice is unavailable here."
fi
echo "  • Tested transport default: Termius + Tailscale + tmux + Mosh"
echo "    (tmux = session persistence, Mosh = connection persistence across phone"
echo "    sleep / network handoff). See references/transport-default.md."
echo "    Alternatives: Moshi (single-app, on-device dictation); the Claude mobile"
echo "    app voice mode for briefing-only (can't drive the vault repo)."

# graceful-degrade + gaps
if [ "$V_GIT" != true ] || [ "$V_REMOTE" != true ]; then
  echo "  • Read-aloud-only mode: your vault isn't a git repo with a remote, so"
  echo "    drafting + cross-device commit won't work yet — you'll get the briefing"
  echo "    experience only. Add a git remote to unlock draft-to-inbox + sync."
fi
if [ "$GEMINI_KEY" != true ]; then
  echo "  • No Gemini/Google key found: TTS falls back to your runtime's own /"
  echo "    on-device voice (fine for v1). Set GEMINI_API_KEY later for richer pacing."
fi
echo "  • Local models are optional and OFF by default; turn a step local only after"
echo "    it passes the rung probes in the integrating-local-models skill."
echo "  • Modes: defaults to PASSIVE (quiet, capture-only) until you opt into active"
echo "    walk-and-work. The assistant will briefly interview you to tailor the config"
echo "    to your second brain and routine. See references/modes.md."
if [ -n "$DAILY_HINT" ]; then echo "  • Sensed a daily-note dir ('$DAILY_HINT') — confirm your real schedule note."; fi
echo

# macOS: surface the hands-free voice-loop traps (read-only diagnose)
if [ "$OS" = "Darwin" ] && [ -f "$(dirname "$0")/audio-check.sh" ]; then
  echo "Hands-free voice loop (macOS) — see references/hands-free-input.md:"
  bash "$(dirname "$0")/audio-check.sh" | sed 's/^/  /'
  echo "  → run scripts/audio-check.sh --fix to auto-repair the mic + open Voice Control."
  echo
fi

# ---- optional config write (story 1.4) ----
if [ "$WRITE_CONFIG" -ne 1 ]; then
  echo "Run again with --write-config to create <vault>/.walk-and-talk/config.yaml."
  exit 0
fi

if [ "$V_EXISTS" != true ]; then
  echo "ERROR: --write-config needs an existing --vault directory." >&2
  exit 1
fi

STATE_DIR="$VAULT/.walk-and-talk"
CONFIG="$STATE_DIR/config.yaml"
GITIGNORE="$VAULT/.gitignore"

CONFIG_CONTENT="$(cat <<YAML
# walk-and-talk config (first draft by setup-advisor.sh).
# The assistant tailors the rest by briefly interviewing you — see
# references/modes.md ("Self-tailoring"). Defaults to PASSIVE + quiet.
vault: $VAULT
second_brain: $SECOND_BRAIN          # sensed; confirm if wrong
capture:
  target: inbox-file                 # inbox-file | daily-note | external
  path: $CAPTURE_PATH
  external_note: ""
triage:
  loop: user
schedule_note: "$DAILY_HINT"         # sensed daily-note dir, if any; confirm/point at your real note
voice:
  default_mode: passive              # quiet, capture-only, until you opt into more
  verbosity: brief
  confirmations: yes-no
  quiet_when_relaxed: true
modes:
  passive: { speak: minimal, capture: true,  interactive: false }
  active:  { speak: normal,  capture: true,  interactive: true  }
  quiet:   { speak: off,     capture: true,  interactive: false }
# Time-of-day mode switching is OFF by default, so default_mode holds cleanly.
# To turn it on, add your real routine, e.g. - "07:00-09:30 passive". First match wins.
mode_triggers: []
navigation:
  button: bluetooth-headphones      # any BT headphones/earbuds button; or ring/clicker/phone tap
offline:
  capture_locally: true
  degrade: graceful
push_policy: push
transport: termius-tailscale-tmux-mosh
tts: runtime
engine:
  default: cloud
YAML
)"

if [ "$DRY_RUN" -eq 1 ]; then
  echo "[dry-run] would create dir:   $STATE_DIR"
  echo "[dry-run] would write config: $CONFIG"
  echo "[dry-run] would ensure '.walk-and-talk/' in: $GITIGNORE"
  echo "[dry-run] config contents:"
  printf '%s\n' "$CONFIG_CONTENT" | sed 's/^/    /'
  exit 0
fi

mkdir -p "$STATE_DIR" || { echo "ERROR: could not create $STATE_DIR" >&2; exit 1; }

if [ -e "$CONFIG" ] && [ "$FORCE" -ne 1 ]; then
  echo "Config already exists: $CONFIG (use --force to overwrite). Left untouched."
else
  printf '%s\n' "$CONFIG_CONTENT" > "$CONFIG" || { echo "ERROR: could not write $CONFIG" >&2; exit 1; }
  echo "Wrote $CONFIG"
fi

# Keep state out of git WITHOUT dirtying a tracked .gitignore. Prefer the repo-
# local, untracked .git/info/exclude; fall back to .gitignore only for a non-git
# vault. (Dogfood finding 2026-06-18: appending to a *tracked* .gitignore dirties
# the tree, and the refuse-on-dirty guard then blocks the very first walk commit.)
if git -C "$VAULT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  EXCLUDE="$(git -C "$VAULT" rev-parse --git-path info/exclude 2>/dev/null)"
  case "$EXCLUDE" in /*) : ;; *) EXCLUDE="$VAULT/$EXCLUDE" ;; esac   # resolve relative to vault
  mkdir -p "$(dirname "$EXCLUDE")"
  if [ -f "$EXCLUDE" ] && grep -qxF ".walk-and-talk/" "$EXCLUDE"; then
    echo "'.walk-and-talk/' already excluded (.git/info/exclude)."
  else
    printf '%s\n' ".walk-and-talk/" >> "$EXCLUDE" || { echo "ERROR: could not update $EXCLUDE" >&2; exit 1; }
    echo "Excluded '.walk-and-talk/' via .git/info/exclude (local, untracked — leaves your tree clean)."
  fi
else
  if ! { [ -f "$GITIGNORE" ] && grep -qxF ".walk-and-talk/" "$GITIGNORE"; }; then
    printf '%s\n' ".walk-and-talk/" >> "$GITIGNORE" || { echo "ERROR: could not update $GITIGNORE" >&2; exit 1; }
    echo "Added '.walk-and-talk/' to $GITIGNORE (not a git repo)."
  else
    echo "'.walk-and-talk/' already gitignored."
  fi
fi

# Do the audio + Voice Control setup NOW, during setup — not deferred to session
# start. Sets the mic to built-in and OPENS the Voice Control settings so the user
# can turn it on right here. (macOS only; harmless to repeat.)
if [ "$OS" = "Darwin" ] && [ -f "$(dirname "$0")/audio-check.sh" ]; then
  echo
  bash "$(dirname "$0")/audio-check.sh" --fix
fi

echo
echo "Setup complete. Voice Control settings are open — turn it on there (the mic is already set)."
