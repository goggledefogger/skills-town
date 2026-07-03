# Getting info in — prep before the walk

A walk is for *using* information, not hunting for it. Bring anything you'll want to talk about into the vault **before** you leave, so it's there even in a dead zone and never needs a live fetch.

## Email and other accounts

Two ways to pull in an email (or doc):

1. **Copy/paste-and-ingest (the reliable default).** You paste the body + links and drop any images into the vault; the assistant files them and folds them into the relevant note. Provider-agnostic (works for Proton, Fastmail, anything), needs no integration, and it's a deliberate "I want this for the walk" step.
2. **Live mailbox access via an MCP (only if it fits).** Convenient *only* when the relevant mailbox is actually a connected account. **Verify the account first** — a connected Gmail MCP may point at a different address than the one holding the email (and won't help at all for non-Gmail providers). If the account doesn't match, fall back to copy/paste; don't go spelunking the wrong mailbox.

Either way, ingest **intentionally and ahead of time**: extract the parts you'll discuss, save images to `Assets/<Project>/`, keep links as links. The walk then runs on what's already on disk.

## Calendar, tasks, and other periodic data (automated sync)

For things that change constantly (a calendar, an external task app, health data) rather than a one-off email, copy/paste doesn't scale. The reliable pattern is a small sibling tool — separate from the vault, not something this skill implements — that pulls from the source (Calendar, Tasks, a wearable API, whatever) via its own OAuth and writes **compiled, read-only files into the vault** (e.g. a daily tasks-inbox note, a daily calendar note). Treat these like any other vault content this skill reads — through `auditory-view`, never hand-edited — with a few rules specific to sync:

- **Regenerated, not edited.** A compiled file is fully rewritten from the source on every sync; hand-edit one and the next sync silently discards the edit.
- **Credentials never travel with the vault.** OAuth tokens are gitignored and machine-local, so a second machine starts with no access until the token is copied over or re-authed there. Detect which machine you're on (hostname is enough) and branch: primary machine, skip sync unless asked; unfamiliar machine, offer the full sync-first checklist.
- **Sync only when stale.** Don't re-run it at the start of every session — it's slow and the last sync is almost always still accurate. Run it only when today's compiled file doesn't exist yet, the machine changed, or the user explicitly asks for a refresh.
- **Read compiled files instead of asking the user to recite their schedule** — faster and more accurate, and it's exactly what `schedule_note` in `config.yaml` can point at once a sync tool exists (see the `sync:` block in `config.example.yaml`).
