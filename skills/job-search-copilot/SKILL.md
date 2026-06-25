---
name: job-search-copilot
description: "A careful job-hunt helper. Writes resumes and cover letters in your voice, explains every field on an application, and fills forms in the browser for your review — never submitting on its own. Use to prepare job applications, understand a posting's fields, or get guided help filling one out. Bring your own writing and details."
---

# job-search-copilot

Help someone through a job application **without ever applying for them**. It drafts, formats, and
explains; the human reviews and presses submit. Caution isn't a setting — it's the whole point.

You bring your own resume content, writing, and the role details. This skill brings the tools and
the discipline. It ships no personal data and stores nothing remotely.

## What's in the box

Three stdlib-only scripts (no install step — just `python3`):

| Script | Does |
|---|---|
| `scripts/format_resume.py` | Renders a structured resume (`resume.json`) → clean ATS-friendly HTML; **warns on out-of-order dates and gaps**. |
| `scripts/format_cover_letter.py` | Renders a cover letter (`letter.json`) → HTML; **flags clichés and AI-sounding phrasing** so it still reads like you. |
| `scripts/track_application.py` | A local application tracker (add / status / note / list active-first). Status only advances when you say so. |

See `examples/` for the input shapes. Run any with `--help`.

```bash
python3 scripts/format_resume.py examples/resume.example.json --theme modern -o resume.html
python3 scripts/format_cover_letter.py letter.json -o cover.html
python3 scripts/track_application.py add --company "Northwind" --role "Backend Engineer"
```

## Understanding an application's fields (browser)

When the user points at a posting or application URL, **read the form before touching it** — use the
`playwright-browser-bridge` discipline (attach to a browser they already have open; never auto-submit):

1. Navigate to the form and take a snapshot of the page.
2. Enumerate **every** field: label, type (text / select / file / checkbox), required?, and any
   **conditional fields** that only appear after a prior answer (common on Greenhouse, Lever, Ashby,
   Workday).
3. For each field, write down **what it's actually asking** and **where its value would come from**
   (resume, cover letter, a link, free text). Flag EEO/optional fields and free-text "traps."
4. Present that map to the user. Don't fill anything yet.

## The careful fill workflow (the part that matters)

Every action that touches the outside world is **draft → present → confirm**:

- **Show the field, then the value.** Before typing anything, show the user the field and the value
  you propose (sourced from their materials). Let them correct it.
- **One field at a time** on dynamic forms; re-read state between fields.
- **Never blind-submit.** You fill and review; the *user* clicks submit. Only after they confirm they
  submitted do you run `track_application.py status <id> applied`.
- **Flag risk before it happens:** anything irreversible (final submit, withdraw, "save & send"),
  anything that posts publicly, and any field asking for sensitive personal data.
- **Their voice, not a generated persona.** Draft from what they give you; the cover-letter checker
  warns when a line drifts into template/AI tone.

## Boundaries

- Bring-your-own-data. It stores nothing remotely and ships no one's information.
- It does not scrape job boards or auto-apply. One careful application at a time.
- Browser steps go through `playwright-browser-bridge`: attach-don't-launch, re-check before acting,
  download → temp → delete.

## Compatibility

The drafting / formatting / tracking scripts are tool-agnostic (Python 3, stdlib). The field-discovery
and guided-fill steps need a Playwright-capable runtime (via `playwright-browser-bridge`).
