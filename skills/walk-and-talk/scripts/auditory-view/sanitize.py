#!/usr/bin/env python3
"""walk-and-talk auditory-view sanitizer (Epic 2, story 2.3).

Turns vault markdown into ear-ready text so it is never read aloud raw
(FR-B5, invariant #5). Pure stdin -> stdout transform, no file writes, no
network. Deterministic: it strips/translates syntax and conversationalizes
dates. Actual *summarization* of long passages is left to the assistant/engine
that calls this — this script makes the text speakable, not shorter-by-meaning.

Usage:
    cat note.md | sanitize.py
    sanitize.py < note.md
    sanitize.py --today 2026-06-18 < note.md   # fix "now" for deterministic dates
"""
import argparse
import datetime as _dt
import re
import sys

# Standalone ISO date only — the lookarounds skip dates embedded in filename/path
# tokens (e.g. 2026-05-21-working-session.md or a/2026-05-21/b), which should be
# spoken as-is, not conversationalized. (Dogfood finding 2026-06-18.)
ISO_DATE = re.compile(r"(?<![\w/-])(\d{4})-(\d{2})-(\d{2})(?![\w/-])")


def _relative_date(y: int, m: int, d: int, today: _dt.date) -> str:
    try:
        then = _dt.date(y, m, d)
    except ValueError:
        return f"{y}-{m:02d}-{d:02d}"
    days = (today - then).days
    if days == 0:
        return "today"
    if days == 1:
        return "yesterday"
    if days == -1:
        return "tomorrow"
    if 0 < days < 7:
        return f"{days} days ago"
    if -7 < days < 0:
        return f"in {-days} days"
    if 7 <= days < 14:
        return "last week"
    if 0 < days < 28:
        return f"{days // 7} weeks ago"
    if 28 <= days < 45:
        return "last month"
    months = round(days / 30.4)
    if 1 < months < 12:
        return f"{months} months ago"
    return then.strftime("%B %Y")


def _conversationalize_dates(text: str, today: _dt.date) -> str:
    return ISO_DATE.sub(
        lambda mo: _relative_date(int(mo[1]), int(mo[2]), int(mo[3]), today), text
    )


def _split_frontmatter(text: str):
    """Return (frontmatter_dict, body). Frontmatter is the leading --- ... --- block."""
    if not text.startswith("---"):
        return {}, text
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?", text, re.DOTALL)
    if not m:
        return {}, text
    fm = {}
    for line in m[1].splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip().lower()] = v.strip().strip("\"'")
    return fm, text[m.end():]


def sanitize(text: str, today: _dt.date) -> str:
    fm, body = _split_frontmatter(text)

    # Lead with the title if the frontmatter carried one (the ear has no <h1>).
    lead = ""
    title = fm.get("title")
    if title:
        lead = title.strip() + ". "

    # Remove fenced code blocks entirely (unspeakable).
    body = re.sub(r"```.*?```", " (code omitted) ", body, flags=re.DOTALL)
    body = re.sub(r"~~~.*?~~~", " (code omitted) ", body, flags=re.DOTALL)

    # Images ![alt](url) -> alt (or nothing).
    body = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", body)
    # Links [text](url) -> text.
    body = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", body)
    # Wikilinks [[Page|alias]] -> alias ; [[Page]] -> Page.
    body = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", body)
    body = re.sub(r"\[\[([^\]]+)\]\]", r"\1", body)
    # Bare URLs -> "a link".
    body = re.sub(r"https?://\S+", "a link", body)
    # Inline code `x` -> x.
    body = re.sub(r"`([^`]*)`", r"\1", body)
    # Emphasis / strong / strike markers.
    body = re.sub(r"(\*\*|__|\*|_|~~)(.*?)\1", r"\2", body)
    # Heading hashes -> drop the hashes, keep text.
    body = re.sub(r"^#{1,6}\s*", "", body, flags=re.MULTILINE)
    # Blockquote markers.
    body = re.sub(r"^\s*>\s?", "", body, flags=re.MULTILINE)
    # List markers -> nothing (the pause between lines carries the structure).
    body = re.sub(r"^\s*[-*+]\s+", "", body, flags=re.MULTILINE)
    body = re.sub(r"^\s*\d+\.\s+", "", body, flags=re.MULTILINE)
    # Horizontal rules.
    body = re.sub(r"^\s*([-*_])\1{2,}\s*$", "", body, flags=re.MULTILINE)
    # Tables: drop separator rows, then turn pipes into pauses.
    body = re.sub(r"^\s*\|?[-:\s|]+\|?\s*$", "", body, flags=re.MULTILINE)
    body = body.replace("|", ", ")

    body = _conversationalize_dates(body, today)

    # Collapse whitespace: blank lines -> single breaks, runs of spaces -> one.
    body = re.sub(r"[ \t]+", " ", body)
    out = (lead + body).strip()
    lines = []
    for line in out.splitlines():
        # trim table-pipe artifacts (leading/trailing commas) and whitespace
        line = re.sub(r"^[\s,]+|[\s,]+$", "", line)
        line = re.sub(r"\s*,\s*", ", ", line)
        if line:
            lines.append(line)
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="markdown -> ear-ready text")
    ap.add_argument("--today", help="YYYY-MM-DD to anchor relative dates (default: real today)")
    args = ap.parse_args()
    today = _dt.date.today()
    if args.today:
        today = _dt.date.fromisoformat(args.today)
    sys.stdout.write(sanitize(sys.stdin.read(), today) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
