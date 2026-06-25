#!/usr/bin/env bash
# walk-and-talk: ambient-check — "tell me what I can't see."
#
# A core vocal-OS idea: eyes-free, you can't glance at the screen to notice that
# *another session/agent is already working on this project*, a build or browser
# automation is running, or your local checkout is behind the remote — and if you
# just dictate and submit, you might collide with or overwrite that work. So
# before engaging a project (and ideally periodically), surface what's already
# going on. Read-only (a `git fetch` updates remote refs only, never your tree).
#
# Usage:
#   ambient-check.sh --project PATH [--mins 15] [--json]
# Exit: 0 = looks quiet, 10 = active work detected (so callers/automation can gate).
set -uo pipefail

PROJECT="$(pwd)"; MINS=15; JSON=0
while [ $# -gt 0 ]; do
  case "$1" in
    --project|--vault) PROJECT="${2:-}"; shift 2 ;;   # --vault is an alias (other scripts use it)
    --mins) MINS="${2:-15}"; shift 2 ;;
    --json) JSON=1; shift ;;
    -h|--help) sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done
[ -d "$PROJECT" ] || { echo "ERROR: --project must be a dir" >&2; exit 2; }

# --- recent edits (the strongest signal something is actively working) ---
recent="$(find "$PROJECT" -type f -mmin -"$MINS" \
  -not -path '*/.git/*' -not -path '*/.walk-and-talk/*' -not -path '*/node_modules/*' \
  -not -name '*.lock' 2>/dev/null)"
recent_n=$(printf '%s' "$recent" | grep -c . || true)
# content edits (someone editing) vs automation/tool noise
content="$(printf '%s\n' "$recent" | grep -iE '\.(md|ts|tsx|js|jsx|py|swift|go|rs|css|html|json|yaml|yml)$' | grep -ivE '/\.obsidian/|/\.playwright|workspace\.json' | head -5)"
tooling=""
printf '%s\n' "$recent" | grep -q '/.playwright' && tooling="${tooling}playwright-browser "
printf '%s\n' "$recent" | grep -qiE '/dist/|/build/|/\.next/' && tooling="${tooling}build "
printf '%s\n' "$recent" | grep -q '/.obsidian/' && tooling="${tooling}obsidian "

# --- agent sessions running (count; can't cleanly attribute to this project) ---
agents=$(pgrep -fl 'bin/claude|/claude |codex|aider' 2>/dev/null | grep -ivc 'walk-and-talk\|grep' || echo 0)

# --- git: dirty + behind/ahead of remote ---
g_branch=""; g_dirty=0; g_behind=0; g_ahead=0; g_remote="no"
if git -C "$PROJECT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  g_branch="$(git -C "$PROJECT" branch --show-current)"
  g_dirty=$(git -C "$PROJECT" status --porcelain | grep -vcE '^\?\?' || true)
  if git -C "$PROJECT" remote get-url origin >/dev/null 2>&1; then
    g_remote="yes"
    git -C "$PROJECT" fetch -q 2>/dev/null || true
    g_behind=$(git -C "$PROJECT" rev-list --count HEAD..@{u} 2>/dev/null || echo 0)
    g_ahead=$(git -C "$PROJECT" rev-list --count @{u}..HEAD 2>/dev/null || echo 0)
  fi
fi

# --- verdict ---
busy=0
[ "$recent_n" -gt 0 ] && [ -n "$content$tooling" ] && busy=1
[ "$g_behind" -gt 0 ] && busy=1

if [ "$JSON" -eq 1 ]; then
  printf '{"project":"%s","recent_files":%s,"content_edits":%s,"tooling":"%s","agents":%s,"branch":"%s","dirty":%s,"behind":%s,"ahead":%s,"busy":%s}\n' \
    "$PROJECT" "${recent_n:-0}" "$(printf '%s' "$content" | grep -c . || echo 0)" "${tooling% }" "${agents:-0}" "$g_branch" "${g_dirty:-0}" "${g_behind:-0}" "${g_ahead:-0}" "$busy"
  [ "$busy" -eq 1 ] && exit 10 || exit 0
fi

echo "ambient check — $(basename "$PROJECT")"
echo "  recent edits (last ${MINS}m): ${recent_n:-0} file(s)"
[ -n "$content" ] && printf '%s\n' "$content" | sed "s#$PROJECT/#    • #"
[ -n "$tooling" ] && echo "    • automation running: ${tooling% }"
echo "  agent sessions running: ${agents:-0}"
if [ -n "$g_branch" ]; then
  echo "  git: $g_branch · ${g_dirty} uncommitted$([ "$g_remote" = yes ] && echo " · ${g_behind} behind / ${g_ahead} ahead of origin")"
  [ "${g_behind:-0}" -gt 0 ] && echo "    → behind remote — pull latest before you start"
fi
echo
if [ "$busy" -eq 1 ]; then
  echo "  ⚠ ACTIVE WORK detected — don't submit changes here until it's quiet (you could collide)."
  exit 10
else
  echo "  ✓ looks quiet — safe to engage."
  exit 0
fi
