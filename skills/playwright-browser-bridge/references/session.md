# Session: attach, don't launch

The default is to work in a browser the **user already has open**, not a fresh instance.

## Why
A new headless/incognito browser is logged out and stripped of the user's context. Forms they
half-filled, sessions they're authenticated into, the tab they're looking at — all gone. Attaching
keeps the human in the loop and avoids re-doing logins (or worse, prompting for credentials).

## How
- Use `browser_navigate(url)` against the **current** context to move the open tab, rather than
  opening new tabs or a new window.
- Only launch a fresh browser when there is no running session **and** the calling skill explicitly
  asks for one (e.g. a headless QA run with no human watching).
- When you do launch, say so plainly — the user should never be surprised by a new window acting on
  its own.

## Head-full by default for human-in-the-loop work
If a person is watching and steering (job application fill, dogfooding), prefer a **visible**
browser so they can see every action. Headless is for unattended reads only.
