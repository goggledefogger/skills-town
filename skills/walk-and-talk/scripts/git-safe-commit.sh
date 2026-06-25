#!/usr/bin/env bash
# walk-and-talk: git-safe-commit (Epic 3, stories 3.2/3.3).
#
# The ONLY sanctioned git write path for a walk session (invariant #2). Commits
# the given draft file(s) to an isolated session branch. Hard guarantees:
#   - session branch only, NEVER main/master                       (FR-D3)
#   - refuse to switch onto a dirty tree (no cross-device merge)    (FR-D4)
#   - never pull / merge / rebase; never --force                   (FR-D4/D5)
#   - push the session branch only, when policy allows             (FR-D5)
# It stages ONLY the files you name — never `git add -A`.
#
# Usage:
#   git-safe-commit.sh --vault /path --message "draft: reply to Acme" Inbox/2026-06-18-acme.md
#   git-safe-commit.sh --vault /path -m "..." --branch walk/2026-06-18 --no-push file.md
#   git-safe-commit.sh --vault /path -m "..." --dry-run file.md
#
# Exit: 0 ok. Reason codes (non-zero) on stderr:
#   2 usage  3 E_NOTREPO  4 E_MAIN  5 E_DIRTY  6 E_NOFILES  7 E_PUSH
set -uo pipefail

VAULT=""; MESSAGE=""; BRANCH=""; PUSH=""; DRY_RUN=0
FILES=()
while [ $# -gt 0 ]; do
  case "$1" in
    --vault) VAULT="${2:-}"; shift 2 ;;
    -m|--message) MESSAGE="${2:-}"; shift 2 ;;
    --branch) BRANCH="${2:-}"; shift 2 ;;
    --push) PUSH=1; shift ;;
    --no-push) PUSH=0; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    --) shift; while [ $# -gt 0 ]; do FILES+=("$1"); shift; done ;;
    -*) echo "unknown arg: $1" >&2; exit 2 ;;
    *) FILES+=("$1"); shift ;;
  esac
done

g() { git -C "$VAULT" "$@"; }

[ -n "$VAULT" ] && [ -d "$VAULT" ] || { echo "ERROR(usage): --vault PATH (existing) required" >&2; exit 2; }
g rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "ERROR(E_NOTREPO): $VAULT is not a git repo" >&2; exit 3; }
[ -n "$MESSAGE" ] || { echo "ERROR(usage): --message required" >&2; exit 2; }
[ "${#FILES[@]}" -gt 0 ] || { echo "ERROR(E_NOFILES): name the draft file(s) to commit; never blanket-add" >&2; exit 6; }

# Resolve session branch: --branch > state.json session_branch > walk/<date>.
if [ -z "$BRANCH" ]; then
  STATE="$VAULT/.walk-and-talk/state.json"
  if [ -f "$STATE" ]; then
    BRANCH="$(grep -o '"session_branch": *"[^"]*"' "$STATE" | sed 's/.*: *"\(.*\)"/\1/')"
  fi
  [ -n "$BRANCH" ] || BRANCH="walk/$(date +%F)"
fi

# NEVER main/master.
case "$BRANCH" in
  main|master|HEAD) echo "ERROR(E_MAIN): refusing to commit to '$BRANCH' — session branch only" >&2; exit 4 ;;
esac

# Resolve push policy: flag > config push_policy > default push.
if [ -z "$PUSH" ]; then
  CFG="$VAULT/.walk-and-talk/config.yaml"
  if [ -f "$CFG" ] && grep -q '^push_policy:[[:space:]]*commit-only' "$CFG"; then PUSH=0; else PUSH=1; fi
fi

CURRENT="$(g branch --show-current 2>/dev/null || echo "")"

# Refuse-on-dirty: only when a branch SWITCH is required, and only for *other
# modified tracked* files — the genuine cross-device merge risk. The draft files
# we're about to commit are excluded (they're the payload), and untracked files
# elsewhere carry harmlessly across a switch, so neither blocks.
NEED_SWITCH=0
[ "$CURRENT" != "$BRANCH" ] && NEED_SWITCH=1
if [ "$NEED_SWITCH" -eq 1 ]; then
  blocking=""
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    xy="${line:0:2}"; path="${line:3}"
    [ "$xy" = "??" ] && continue            # untracked carries over harmlessly
    is_target=0
    for f in "${FILES[@]}"; do [ "$path" = "$f" ] || [ "$path" = "${f#./}" ] && { is_target=1; break; }; done
    [ "$is_target" -eq 1 ] && continue       # the payload itself doesn't count
    blocking="$path"; break
  done <<EOF
$(g status --porcelain)
EOF
  if [ -n "$blocking" ]; then
    echo "ERROR(E_DIRTY): uncommitted change to tracked file '$blocking' and a switch to '$BRANCH' is needed." >&2
    echo "  Reconcile at the keyboard — walk sessions never merge onto a dirty tree." >&2
    exit 5
  fi
fi

# Plan summary.
echo "vault:   $VAULT"
echo "branch:  $BRANCH (current: ${CURRENT:-<detached>})"
echo "files:   ${FILES[*]}"
echo "push:    $([ "$PUSH" -eq 1 ] && echo yes || echo no)"
if [ "$DRY_RUN" -eq 1 ]; then echo "[dry-run] no changes made"; exit 0; fi

# Switch/create the session branch (tree is clean if we got here needing a switch).
if [ "$NEED_SWITCH" -eq 1 ]; then
  if g rev-parse --verify "$BRANCH" >/dev/null 2>&1; then
    g checkout "$BRANCH" >/dev/null 2>&1 || { echo "ERROR(E_DIRTY): checkout '$BRANCH' failed" >&2; exit 5; }
  else
    g checkout -b "$BRANCH" >/dev/null 2>&1 || { echo "ERROR(E_DIRTY): create '$BRANCH' failed" >&2; exit 5; }
  fi
fi

# Stage ONLY the named files, then commit.
g add -- "${FILES[@]}" || { echo "ERROR(E_NOFILES): could not stage ${FILES[*]}" >&2; exit 6; }
if [ -z "$(g diff --cached --name-only)" ]; then
  echo "Nothing to commit (named files unchanged). No-op."
  exit 0
fi
g commit -q -m "$MESSAGE" -m "walk-and-talk session" || { echo "ERROR: commit failed" >&2; exit 1; }
echo "Committed to $BRANCH: $(g rev-parse --short HEAD)"

# Push the session branch ONLY, never --force.
if [ "$PUSH" -eq 1 ]; then
  if g remote get-url origin >/dev/null 2>&1; then
    if g push -u origin "$BRANCH" >/dev/null 2>&1; then
      echo "Pushed $BRANCH to origin."
    else
      echo "ERROR(E_PUSH): push of '$BRANCH' failed (commit is safe locally)." >&2
      exit 7
    fi
  else
    echo "No 'origin' remote — committed locally only."
  fi
fi
