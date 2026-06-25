#!/usr/bin/env python3
"""Render a structured resume (JSON) into clean, ATS-friendly HTML.

Stdlib only — no install step. Validates reverse-chronological ordering and flags gaps so you
catch problems before a recruiter does. Two themes: classic (serif, conservative) and modern
(sans, lightly styled). Your data stays local; nothing is sent anywhere.

Usage:
  python3 format_resume.py resume.json [--theme classic|modern] [-o out.html]

resume.json shape (all fields optional except name):
  {
    "name": "Jordan Rivera",
    "headline": "Backend Engineer",
    "contact": {"email": "...", "phone": "...", "location": "...", "links": {"GitHub": "..."}},
    "summary": "One or two sentences.",
    "experience": [
      {"title": "...", "company": "...", "start": "2021-03", "end": "present",
       "location": "...", "bullets": ["Did X, measured by Y.", "..."]}
    ],
    "education": [{"degree": "...", "school": "...", "start": "2014", "end": "2018"}],
    "skills": ["Python", "PostgreSQL"]
  }
"""
import argparse
import html
import json
import re
import sys
from datetime import datetime


def parse_month(value):
    """Return a comparable (year, month) tuple. 'present'/'current' sorts as the future."""
    if value is None:
        return (0, 0)
    s = str(value).strip().lower()
    if s in ("present", "current", "now", ""):
        return (9999, 12)
    m = re.match(r"(\d{4})(?:[-/](\d{1,2}))?", s)
    if not m:
        return (0, 0)
    year = int(m.group(1))
    month = int(m.group(2)) if m.group(2) else 1
    return (year, month)


def validate_chronology(experience):
    """Return a list of human-readable warnings about ordering and gaps."""
    warnings = []
    spans = []
    for i, job in enumerate(experience):
        start, end = parse_month(job.get("start")), parse_month(job.get("end"))
        label = f"{job.get('title', '?')} @ {job.get('company', '?')}"
        if start > end:
            warnings.append(f"{label}: start is after end — check the dates.")
        spans.append((start, end, label))

    # Reverse-chronological check (most recent first) by end date.
    for a, b in zip(spans, spans[1:]):
        if a[1] < b[1]:
            warnings.append(f"Out of order: '{a[2]}' is listed before '{b[2]}' but ended earlier. Resumes go newest-first.")

    # Gap detection (> 6 months between consecutive jobs, chronologically).
    chrono = sorted([s for s in spans if s[0] != (0, 0)], key=lambda s: s[0])
    for a, b in zip(chrono, chrono[1:]):
        gap_months = (b[0][0] - a[1][0]) * 12 + (b[0][1] - a[1][1])
        if gap_months > 6 and a[1] != (9999, 12):
            warnings.append(f"~{gap_months}-month gap between '{a[2]}' and '{b[2]}' — be ready to explain it (it's fine to have one).")
    return warnings


def fmt_range(job):
    def show(v):
        s = str(v).strip() if v is not None else ""
        return "Present" if s.lower() in ("present", "current", "now", "") else s
    start, end = show(job.get("start")), show(job.get("end"))
    return f"{start} – {end}".strip(" –") if (start or end) else ""


def e(x):
    return html.escape(str(x)) if x is not None else ""


def render(resume, theme):
    name = e(resume.get("name", "Your Name"))
    headline = e(resume.get("headline", ""))
    c = resume.get("contact", {}) or {}
    bits = [c.get("email"), c.get("phone"), c.get("location")]
    contact_line = " · ".join(e(b) for b in bits if b)
    links = " · ".join(f'<a href="{e(u)}">{e(k)}</a>' for k, u in (c.get("links") or {}).items())

    parts = [f'<header><h1>{name}</h1>']
    if headline:
        parts.append(f'<p class="headline">{headline}</p>')
    if contact_line or links:
        parts.append(f'<p class="contact">{contact_line}{(" · " + links) if links and contact_line else links}</p>')
    parts.append("</header>")

    if resume.get("summary"):
        parts.append(f'<section><h2>Summary</h2><p>{e(resume["summary"])}</p></section>')

    if resume.get("experience"):
        parts.append('<section><h2>Experience</h2>')
        for job in resume["experience"]:
            parts.append('<div class="job"><div class="job-head">'
                         f'<span class="job-title">{e(job.get("title",""))}</span>'
                         f'<span class="job-dates">{e(fmt_range(job))}</span></div>'
                         f'<div class="job-sub">{e(job.get("company",""))}'
                         f'{(" — " + e(job.get("location"))) if job.get("location") else ""}</div>')
            if job.get("bullets"):
                parts.append("<ul>" + "".join(f"<li>{e(b)}</li>" for b in job["bullets"]) + "</ul>")
            parts.append("</div>")
        parts.append("</section>")

    if resume.get("education"):
        parts.append('<section><h2>Education</h2>')
        for ed in resume["education"]:
            parts.append('<div class="job"><div class="job-head">'
                         f'<span class="job-title">{e(ed.get("degree",""))}</span>'
                         f'<span class="job-dates">{e(fmt_range(ed))}</span></div>'
                         f'<div class="job-sub">{e(ed.get("school",""))}</div></div>')
        parts.append("</section>")

    if resume.get("skills"):
        parts.append('<section><h2>Skills</h2><p class="skills">'
                     + " · ".join(e(s) for s in resume["skills"]) + "</p></section>")

    serif = theme == "classic"
    font = "Georgia, 'Times New Roman', serif" if serif else "system-ui, -apple-system, sans-serif"
    accent = "#222" if serif else "#1a4d7a"
    css = f"""
      body{{font-family:{font};max-width:760px;margin:2rem auto;padding:0 1.5rem;color:#1a1a1a;line-height:1.45;}}
      h1{{margin:0;font-size:1.7rem;letter-spacing:-0.01em;}}
      .headline{{margin:.2rem 0 0;color:{accent};font-weight:600;}}
      .contact{{margin:.4rem 0 0;color:#555;font-size:.9rem;}}
      .contact a{{color:{accent};}}
      h2{{font-size:1rem;text-transform:uppercase;letter-spacing:.05em;border-bottom:1px solid #ccc;padding-bottom:.2rem;margin:1.4rem 0 .6rem;color:{accent};}}
      .job{{margin-bottom:.9rem;}}
      .job-head{{display:flex;justify-content:space-between;font-weight:600;}}
      .job-dates{{color:#666;font-weight:400;font-size:.9rem;white-space:nowrap;}}
      .job-sub{{color:#444;font-size:.92rem;margin-bottom:.25rem;}}
      ul{{margin:.3rem 0 0;padding-left:1.1rem;}} li{{margin:.15rem 0;}}
      .skills{{color:#333;}}
    """
    return (f"<!doctype html><html><head><meta charset='utf-8'><title>{name} — Resume</title>"
            f"<style>{css}</style></head><body>{''.join(parts)}</body></html>")


def main():
    ap = argparse.ArgumentParser(description="Render a structured resume (JSON) to clean HTML.")
    ap.add_argument("resume", help="Path to resume.json")
    ap.add_argument("--theme", choices=["classic", "modern"], default="classic")
    ap.add_argument("-o", "--out", help="Output HTML path (default: stdout)")
    args = ap.parse_args()

    with open(args.resume, encoding="utf-8") as f:
        resume = json.load(f)

    for w in validate_chronology(resume.get("experience", []) or []):
        print(f"[check] {w}", file=sys.stderr)

    html_out = render(resume, args.theme)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(html_out)
        print(f"[ok] wrote {args.out} ({args.theme} theme)", file=sys.stderr)
    else:
        sys.stdout.write(html_out)


if __name__ == "__main__":
    main()
