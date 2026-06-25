#!/usr/bin/env bash
# walk-and-talk: prime — GATHER project context for the assistant to distill into
# a concise primer at <vault>/.walk-and-talk/primer.md.
#
# Two-phase model:
#   First run  — no primer.md: this prints the full gather; the assistant distills
#                it into primer.md (frontmatter as_of/as_of_sha + short sections).
#   Later runs — primer.md exists: the assistant loads it and uses the "Since last
#                primer" section here to REFRESH incrementally (not re-read all).
#
# Deterministic GATHER only — no LLM, no mutations. primer.md lives in the
# gitignored .walk-and-talk/ (never synced), per-vault.
#
# Usage: prime.sh --vault PATH [--days 7] [--json]
set -uo pipefail

VAULT=""; DAYS=7; JSON=0
while [ $# -gt 0 ]; do
  case "$1" in
    --vault) VAULT="${2:-}"; shift 2 ;;
    --days) DAYS="${2:-7}"; shift 2 ;;
    --json) JSON=1; shift ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done
[ -n "$VAULT" ] && [ -d "$VAULT" ] || { echo "ERROR: --vault PATH (existing) required" >&2; exit 2; }

STATE_DIR="$VAULT/.walk-and-talk"
PRIMER="$STATE_DIR/primer.md"
CFG="$STATE_DIR/config.yaml"

# capture/inbox path from config (default Inbox/)
INBOX="Inbox/"
[ -f "$CFG" ] && INBOX="$(awk '/^capture:/{c=1} c&&$1=="path:"{print $2; exit}' "$CFG" 2>/dev/null)"
[ -z "$INBOX" ] && INBOX="Inbox/"

g() { git -C "$VAULT" "$@"; }
IS_GIT=0; g rev-parse --is-inside-work-tree >/dev/null 2>&1 && IS_GIT=1
HEAD_SHA=""; [ "$IS_GIT" -eq 1 ] && HEAD_SHA="$(g rev-parse --short HEAD 2>/dev/null)"

# primer freshness
HAS_PRIMER=0; AS_OF_SHA=""; NEW_COMMITS=0
if [ -f "$PRIMER" ]; then
  HAS_PRIMER=1
  AS_OF_SHA="$(awk -F'[:[:space:]]+' '/^as_of_sha:/{print $2; exit}' "$PRIMER" 2>/dev/null)"
  if [ "$IS_GIT" -eq 1 ] && [ -n "$AS_OF_SHA" ] && g cat-file -e "$AS_OF_SHA" 2>/dev/null; then
    NEW_COMMITS="$(g rev-list --count "$AS_OF_SHA"..HEAD 2>/dev/null || echo 0)"
  fi
fi

# read-only remote sync info
AHEAD=0; BEHIND=0; BRANCH=""; DIRTY=0
if [ "$IS_GIT" -eq 1 ]; then
  BRANCH="$(g branch --show-current)"
  DIRTY=$(g status --porcelain | grep -vcE '^\?\?' || true)
  if g remote get-url origin >/dev/null 2>&1; then
    g fetch -q 2>/dev/null || true
    AHEAD=$(g rev-list --count @{u}..HEAD 2>/dev/null || echo 0)
    BEHIND=$(g rev-list --count HEAD..@{u} 2>/dev/null || echo 0)
  fi
fi

if [ "$JSON" -eq 1 ]; then
  printf '{"vault":"%s","has_primer":%s,"as_of_sha":"%s","new_commits_since_primer":%s,"branch":"%s","dirty":%s,"ahead":%s,"behind":%s,"head":"%s"}\n' \
    "$(basename "$VAULT")" "$HAS_PRIMER" "${AS_OF_SHA:-}" "${NEW_COMMITS:-0}" "$BRANCH" "${DIRTY:-0}" "${AHEAD:-0}" "${BEHIND:-0}" "$HEAD_SHA"
  exit 0
fi

# ---- full markdown gather (for the assistant to distill) ----
echo "# walk-and-talk priming gather — $(basename "$VAULT")"
echo "_Gathered $(date '+%Y-%m-%d %H:%M'). Distill into a CONCISE primer.md (don't paste this verbatim)._"
echo

echo "## Git"
if [ "$IS_GIT" -eq 1 ]; then
  echo "- branch: ${BRANCH:-?} · ${DIRTY} uncommitted · ${AHEAD} ahead / ${BEHIND} behind origin · HEAD ${HEAD_SHA}"
  echo "- recent commits:"
  g log -8 --pretty='  - %h %s (%cr)' 2>/dev/null
else
  echo "- (not a git repo)"
fi
echo

echo "## Key docs (first 40 lines each)"
for d in CLAUDE.md AGENTS.md README.md README ROADMAP.md ROADMAP docs/index.md; do
  if [ -f "$VAULT/$d" ]; then
    echo "### $d"; echo '```'; head -40 "$VAULT/$d"; echo '```'
  fi
done
echo

echo "## Recent notes"
if [ -d "$VAULT/$INBOX" ]; then
  echo "### inbox ($INBOX)"
  # shellcheck disable=SC2012
  ls -t "$VAULT/$INBOX"*.md 2>/dev/null | head -8 | sed "s#$VAULT/#- #"
fi
echo "### modified in last ${DAYS}d (newest first)"
find "$VAULT" -name '*.md' -mtime -"$DAYS" \
  -not -path '*/.git/*' -not -path '*/.walk-and-talk/*' -not -path '*/node_modules/*' -print 2>/dev/null \
  | tr '\n' '\0' | xargs -0 ls -t 2>/dev/null | head -15 | sed "s#$VAULT/#- #"
echo

if [ "$HAS_PRIMER" -eq 1 ]; then
  echo "## Since last primer (refresh incrementally — don't re-read everything)"
  echo "- primer as_of_sha: ${AS_OF_SHA:-unknown} → current HEAD: ${HEAD_SHA:-?}"
  if [ "${NEW_COMMITS:-0}" != "0" ]; then
    echo "- ${NEW_COMMITS} new commit(s) since the primer:"
    g log "${AS_OF_SHA}"..HEAD --pretty='  - %h %s' 2>/dev/null | head -12
  else
    echo "- no new commits since the primer."
  fi
  echo "- after refreshing, set primer.md frontmatter as_of_sha: ${HEAD_SHA} and as_of: $(date '+%Y-%m-%d')"
else
  echo "## First run"
  echo "- No primer.md yet. Distill the above into ${PRIMER} with frontmatter:"
  echo "    as_of: $(date '+%Y-%m-%d')"
  echo "    as_of_sha: ${HEAD_SHA}"
  echo "  and short sections: What this project is · Current focus / where you left off · Open / in-flight · Recent changes."
fi
