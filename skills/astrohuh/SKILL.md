---
name: astrohuh
description: Report something in Astrolabe that made the member go "huh" (a modal, tooltip, message or feature that reads unclear) for the people who build Astrolabe, as a GitHub issue when the member can file there, otherwise a report kept in Astrolabe's own reports. Use when the member presses the AstroHuh card, types /astrohuh, says "report this", "this is confusing, file it", or provides an Astrolabe screenshot.
---

# AstroHuh

A member found something in Astrolabe that made them go "huh" (it reads unclear). Goal: a well-placed report with the code location, kept or filed after exactly one yes. Do not interview them; their words are optional.

Operates in place without switching away or opening unnecessary chat tabs.

## 1. Requirements Check

If running for the first time or diagnosing errors, check dependencies using `astrohuh.py check` in this skill's own folder (under Claude Code, `${CLAUDE_PLUGIN_ROOT}/astrohuh.py`).

Run the script with whichever of `python3`, `python` or `py -3` exists on this computer. `check` reports which screenshot route it has; with none, pasting a screenshot still works (on Linux, installing gnome-screenshot, or grim and slurp on Wayland, adds drag-select).

Filing a GitHub issue needs `gh` (GitHub CLI) installed and authenticated (`gh auth login`). Keeping it in Astrolabe's reports needs only Astrolabe running.

## 2. Screenshot

- **Drag-select it on your screen (Mac, Windows or Linux)**: run `astrohuh.py grab --crop` in this skill's own folder (under Claude Code, `${CLAUDE_PLUGIN_ROOT}/astrohuh.py`). It uses the computer's own screenshot tool (screencapture on Mac, Snipping Tool on Windows, gnome-screenshot, grim and slurp, maim or similar on Linux) so you can drag the exact region.
- **Paste a screenshot (works anywhere, including a phone)**: attach or paste an image in this chat session, then run `astrohuh.py grab`.
- **Full screen capture**: run `astrohuh.py grab --screen`.

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
- Body sections: **What I saw** (their words if given, quoted), **Why it reads unclear**, **Where** (`path:line` and the cause), **A possible fix** (one line, optional), then `{{SCREENSHOT}}` on its own line
- Label: `what-is-this`

Glance for anything private on screen (a note's contents, an email) and crop or ask before filing.

Pick the door before asking. `gh repo view <repo>` succeeding means this GitHub account can file there; anything else (no `gh`, not signed in, not found) means Astrolabe's reports.

- **GitHub door.** Directly above the question, show this line, verbatim: "This goes to Astrolabe's GitHub issues, under your GitHub account. Dan and Danny read every one. Some can be fixed soon, some can't. Nothing is sent until you say yes." Then one AskUserQuestion: "File it" (Recommended) / "Keep it in Astrolabe's reports instead" / "Change something first".
- **Reports door.** Write the draft body (no `{{SCREENSHOT}}` line, the picture stays on this computer) to a temp file and run `astrohuh.py draft <body.md>`. Show its `payload_json` in a `json` fence: it is exactly what is kept, Astrolabe's usual facts plus their words, with paths scrubbed. Directly above the question, show this line, verbatim: "This is kept in Astrolabe's reports on this computer, exactly as shown. Dan and Danny read every report that reaches them, though some can't be fixed soon. Nothing leaves this computer until you send it from there." Then one AskUserQuestion: "Keep it" (Recommended) / "Change something first".

Extra words from the member go in "What I saw" (and a fresh draft) before filing.

## 5. File or keep

**Reports door:** run `astrohuh.py save <draft id>` and say "Kept as report <ref>." in one line. A save that says the draft is gone means make a fresh draft and show it again. Then stop.

**GitHub door:** check that GitHub CLI is authenticated as the appropriate user, then run `astrohuh.py file <repo> "<title>" <body.md> <image> what-is-this` in this skill's own folder (under Claude Code, `${CLAUDE_PLUGIN_ROOT}/astrohuh.py`).

Write the body to a temp file first. Print the issue link in one line.

If `gh` reports the account cannot create issues on that repo (not found or permission), say in one plain line that this GitHub account does not have access to file there yet, and offer the reports door instead (a fresh draft, shown, one yes), so nothing is lost. No retries.
Do not fix the code in this flow unless requested.

## Attribution
Built on GitHub CLI `gh` (https://cli.github.com, MIT license), and Astrolabe's own report sheet. It captures with the computer's own screenshot tool (screencapture on Mac, Snipping Tool on Windows, or one of gnome-screenshot, grim, maim and friends on Linux).
