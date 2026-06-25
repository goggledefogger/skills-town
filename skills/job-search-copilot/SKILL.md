---
name: job-search-copilot
description: "A careful job-hunt helper. Writes resumes and cover letters in your voice, reads an existing resume, explains every field on an application, and fills forms in the browser for your review — never submitting on its own. Use to prepare job applications, understand a posting's fields, or get guided help filling one out. Bring your own writing and details."
---

# job-search-copilot

An assistant for the whole arc of a job application — written so that **you stay in control of
anything that leaves your hands**. It drafts and explains; it does not apply *for* you.

> You provide your own resume content, writing voice, and the specifics of each role. This skill
> supplies the capabilities and the caution. It ships with **no personal data of its own.**

## What it helps with

- **Resume drafting & formatting** — turn your structured experience into clean resume output
  (classic or modern), validating chronology (reverse-chron, no gaps left unexplained).
- **Resume ingestion** — parse an existing resume you provide into structured fields you can edit
  and re-target per role.
- **Cover letters in your voice** — draft from *your* phrasing and examples; it flags lines that
  sound unlike you rather than smoothing everything into generic AI prose.
- **Application-field comprehension** — for a given posting/form, enumerate every field and explain
  what it actually wants (and which are conditional, EEO/optional, or free-text traps).
- **Careful browser autofill** — using the shared `playwright-browser-bridge`, walk a form
  field-by-field, proposing values sourced from your materials.
- **Job-search utilities** — light helpers for tracking applications and triaging postings/emails.

## The caution layer (the distinctive part)

Every action that could affect the outside world is **draft → present → confirm**:

- **Never blind-submit.** The skill fills and reviews; *you* press submit. Application status only
  flips to "submitted" after you explicitly confirm you submitted it.
- **Show the field, then the value.** Before entering anything, it shows what the field is and the
  value it proposes, sourced from your material — so you can correct it.
- **Flag risk.** Surface anything irreversible (final submit, withdraw, "save & send"), anything that
  posts publicly, and any field asking for sensitive personal data, before touching it.
- **Your voice, not a generated persona.** It writes from what you give it and warns when a draft
  drifts from your tone.

## How it fits together

```
your resume / voice / role details  ──►  draft (resume, cover letter)
posting or application URL           ──►  decode fields (what each wants)
                                          │
                          playwright-browser-bridge (attach to YOUR browser)
                                          │
                              guided fill: field → proposed value → YOUR confirm → submit (by you)
```

## Boundaries

- Bring your own data; the skill stores none and ships none.
- It does not scrape job boards en masse or auto-apply. It is a careful copilot for *your*
  applications, one at a time.
- Browser actions go through `playwright-browser-bridge`, which attaches to your existing session
  and follows its download→temp→delete data discipline.

## Compatibility

The autofill/field-discovery path depends on a Playwright-capable runtime (via
`playwright-browser-bridge`). The drafting/parsing/tracking paths are tool-agnostic.
