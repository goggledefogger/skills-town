---
name: report-confusion
description: Report a confusing moment in Astrolabe (a modal, tooltip, message or feature that reads unclear) as a GitHub issue, one approval away. Use when a member presses the Confusing card ("Report an Astrolabe confusion"), says "report this confusion", "this is confusing, file it", or provides an Astrolabe screenshot.
---

# Report an Astrolabe confusion

A member found something in Astrolabe that reads unclear. Goal: a well-placed issue with a screenshot and the code location, filed after exactly one yes. Do not interview them; their words are optional.

Operates in place without switching away or opening unnecessary chat tabs.

## 1. Requirements Check

If running for the first time or diagnosing errors, check dependencies using `confusion.py check` in this skill's own folder (under Claude Code, `${CLAUDE_PLUGIN_ROOT}/confusion.py`).

Requires `gh` (GitHub CLI) installed and authenticated (`gh auth login`).

## 2. Screenshot

- **Drag-select crop on a Mac desktop**: run `confusion.py grab --crop` in this skill's own folder (under Claude Code, `${CLAUDE_PLUGIN_ROOT}/confusion.py`). Turns the cursor into a crosshair to drag and crop the exact region.
- **Paste a screenshot (works anywhere, including a phone)**: attach or paste an image in this chat session, then run `confusion.py grab`.
- **Full screen capture**: run `confusion.py grab --screen`.

It prints the saved image path.

## 3. Where in the app

Look at the image. Grep the visible words (and any tooltip quoted) in the Astrolabe repository (`dashboard/`, skipping `test/`). Find the `file:line` that draws it and read enough around it to say *why* it reads that way (a missing case, a fallback, jargon). That diagnosis is the most useful part of the issue.

Repo by where the code lives:
- `dashboard/premium/**` -> `aportlandcareer/astrolabe-premium`
- anything else -> `goggledefogger/second-brain-dashboard`

Quick duplicate check: `gh issue list -R <repo> --search "<key words>" --state open --limit 5`.
If one matches, offer a comment on it instead.

## 4. Draft and ask once

Show the image (`images` fence), then the draft in a `paste` card:

- Title: what a new member sees, plainly ("Chair tooltip says All good while 12 saves wait to back up")
- Body sections: **What I saw** (their words if given, quoted), **Why it confuses**, **Where** (`path:line` and the cause), **A possible fix** (one line, optional), then `{{SCREENSHOT}}` on its own line
- Label: `what-is-this`

Then one AskUserQuestion: "File it" (Recommended) / "Change something first".
Extra words from the member go in "What I saw" before filing.

## 5. File

Check that GitHub CLI is authenticated as the appropriate user, then run `confusion.py file <repo> "<title>" <body.md> <image> what-is-this` in this skill's own folder (under Claude Code, `${CLAUDE_PLUGIN_ROOT}/confusion.py`).

Write the body to a temp file first. Print the issue link in one line.
Glance for anything private on screen (a note's contents, an email) and crop or ask before filing. Do not fix the code in this flow unless requested.

## Attribution
Built on GitHub CLI `gh` (MIT license) and `screencapture` on macOS.
