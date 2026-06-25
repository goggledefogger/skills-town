#!/usr/bin/env python3
"""Render a cover letter to clean HTML and flag tired / AI-sounding phrasing.

Stdlib only. The point isn't to write the letter for you — it's to format what YOU wrote and warn
when a line reads like a template or a chatbot, so it still sounds like a person. Your text stays local.

Usage:
  python3 format_cover_letter.py letter.json [-o out.html]

letter.json shape:
  {
    "name": "Jordan Rivera",
    "contact": {"email": "...", "phone": "...", "location": "..."},
    "date": "2026-06-24",
    "recipient": "Hiring Team",
    "company": "Northwind",
    "role": "Senior Backend Engineer",
    "body": ["First paragraph.", "Second paragraph.", "Closing paragraph."],
    "signoff": "Sincerely"
  }
"""
import argparse
import html
import json
import re
import sys

# Phrases that read as filler or AI boilerplate. Each entry: (regex, why).
TIRED = [
    (r"\bI am writing to (express|apply|inquire)", "Generic opener — lead with something specific to them."),
    (r"\bto whom it may concern\b", "Find a name or use the team; this reads as mass-mailed."),
    (r"\bteam player\b", "Cliché — show it with an example instead of claiming it."),
    (r"\bfast[- ]paced environment\b", "Filler phrase recruiters skim past."),
    (r"\b(passionate|passion) about\b", "Overused — what specifically, and what did you do about it?"),
    (r"\bproven track record\b", "Cliché — cite the actual result instead."),
    (r"\bthink outside the box\b", "Cliché."),
    (r"\bperfect (fit|candidate)\b", "Let the evidence say it; this sounds like a chatbot."),
    (r"\bleverage\b", "Corporate-speak — 'use' is fine."),
    (r"\bsynerg(y|ies|ize)\b", "Jargon."),
    (r"\bI believe (that )?my\b", "Hedge — state it plainly."),
    (r"\bdelve into\b", "Common AI tell."),
    (r"\b(tapestry|testament to|underscores|reinvigorate)\b", "Common AI tell — rephrase plainly."),
]


def e(x):
    return html.escape(str(x)) if x is not None else ""


def check_voice(body_text):
    out = []
    for rx, why in TIRED:
        for m in re.finditer(rx, body_text, re.IGNORECASE):
            snippet = body_text[max(0, m.start() - 20): m.end() + 20].replace("\n", " ").strip()
            out.append(f'"…{snippet}…" → {why}')
    # Length nudge: cover letters over ~400 words tend to lose the reader.
    words = len(re.findall(r"\b\w+\b", body_text))
    if words > 400:
        out.append(f"Letter is ~{words} words — most strong ones are 250–350. Consider trimming.")
    return out


def render(letter):
    name = e(letter.get("name", ""))
    c = letter.get("contact", {}) or {}
    header_bits = " · ".join(e(c.get(k)) for k in ("email", "phone", "location") if c.get(k))
    paras = "".join(f"<p>{e(p)}</p>" for p in letter.get("body", []))
    role = e(letter.get("role", ""))
    company = e(letter.get("company", ""))
    subject = f"Re: {role}{(' at ' + company) if company else ''}" if role else ""
    css = ("body{font-family:Georgia,serif;max-width:640px;margin:2.5rem auto;padding:0 1.5rem;"
           "color:#1a1a1a;line-height:1.55;}.hdr{margin-bottom:1.4rem;}.hdr .name{font-size:1.3rem;"
           "font-weight:600;}.meta{color:#555;font-size:.9rem;}p{margin:0 0 1rem;}.sub{font-weight:600;}")
    return (f"<!doctype html><html><head><meta charset='utf-8'><title>{name} — Cover Letter</title>"
            f"<style>{css}</style></head><body>"
            f"<div class='hdr'><div class='name'>{name}</div><div class='meta'>{header_bits}</div></div>"
            f"<p class='meta'>{e(letter.get('date',''))}</p>"
            f"<p>{e(letter.get('recipient','Hiring Team'))},</p>"
            f"{('<p class=sub>' + subject + '</p>') if subject else ''}"
            f"{paras}"
            f"<p>{e(letter.get('signoff','Sincerely'))},<br>{name}</p>"
            f"</body></html>")


def main():
    ap = argparse.ArgumentParser(description="Format a cover letter and flag tired phrasing.")
    ap.add_argument("letter", help="Path to letter.json")
    ap.add_argument("-o", "--out", help="Output HTML path (default: stdout)")
    args = ap.parse_args()

    with open(args.letter, encoding="utf-8") as f:
        letter = json.load(f)

    body_text = "\n".join(letter.get("body", []))
    flags = check_voice(body_text)
    if flags:
        print(f"[voice] {len(flags)} thing(s) to look at — these make it sound less like you:", file=sys.stderr)
        for fl in flags:
            print(f"  • {fl}", file=sys.stderr)
    else:
        print("[voice] no tired-phrase flags — reads clean.", file=sys.stderr)

    out = render(letter)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(out)
        print(f"[ok] wrote {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(out)


if __name__ == "__main__":
    main()
