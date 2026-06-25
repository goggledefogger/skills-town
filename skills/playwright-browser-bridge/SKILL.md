---
name: playwright-browser-bridge
description: "A shared browser helper that other skills build on. It joins a browser you already have open instead of launching a new one, re-checks buttons before clicking, and deletes anything it downloads. Use as the browser layer under skills that read or act on web pages, like job-search-copilot and browser-ai-bridge."
---

# playwright-browser-bridge

A small set of **rules for driving a real browser** through a Playwright-capable runtime (the
Playwright MCP server, or any equivalent `browser_*` tools). Other skills build on it so that "an
agent touches a web page" works the same careful way every time, instead of each skill reinventing
session handling and getting the risky parts wrong.

This is a **substrate**: `job-search-copilot` (form discovery + guided fill) and `browser-ai-bridge`
(dogfood/QA) both use it. It ships no user-facing flow of its own — it ships discipline (and one
small safety helper, `scripts/with-tmp.sh`).

## The five rules

1. **Attach, don't launch.** Prefer a browser the user already has open. Navigate the current
   context rather than spawning a fresh, logged-out instance. Launch a new one only when none exists
   and the caller explicitly asks. The user keeps the window and stays in control. → `references/session.md`
2. **Navigate in place.** Reuse the current tab so logins, scroll position, and open forms survive.
3. **Read before you write.** `browser_snapshot` for structure and an actionable element map;
   `browser_evaluate` for precise reads (text, attributes, `getBoundingClientRect()`, computed
   styles, console, network). Measure — don't eyeball. → `references/reads.md`
4. **Selectors are drift-prone.** Re-derive every target from a *current* snapshot immediately before
   acting. Never act on an element reference remembered from an earlier page state; if a selector
   misses, re-snapshot and re-derive instead of retrying blindly. → `references/selectors.md`
5. **Data lifecycle (hard rule).** Anything downloaded or exported goes to a temp dir, is parsed
   there, and is **deleted** when done — never written into the repo, never committed. Use
   `scripts/with-tmp.sh` to get a self-cleaning temp dir. → `references/data-lifecycle.md`

## Acting (for skills that write)

When a consuming skill clicks / types / selects / navigates:

- Re-derive the target from a **fresh** snapshot right before acting.
- One action at a time on dynamic pages; re-read state between actions.
- Surface what's about to happen to the caller. The caller decides whether confirmation is required
  (e.g. `job-search-copilot` demands explicit human confirmation before any submit).

## Quick reference: the tool calls

| Need | Call |
|---|---|
| Go to a page (in place) | `browser_navigate(url)` |
| Get an actionable element map | `browser_snapshot()` |
| Read exact text / rect / styles | `browser_evaluate(fn)` |
| Click / type a fresh target | `browser_click(ref)` / `browser_type(ref, text)` — ref from the latest snapshot |
| Self-cleaning scratch dir | `bash scripts/with-tmp.sh -- <your command>` |

## What this is NOT

Not a scraper, not a credential harvester, not a headless bot for mass automation. It's a careful,
session-respecting bridge for an agent working **alongside** a human on a real page.

## Compatibility

Requires a Playwright-capable runtime (Playwright MCP or equivalent). That dependency narrows where
it runs — declare it so a gallery's "works on" badge reflects it.
