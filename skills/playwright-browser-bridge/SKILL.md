---
name: playwright-browser-bridge
description: "A shared browser helper that other skills build on. It joins a browser you already have open instead of launching a new one, re-checks buttons before clicking, and deletes anything it downloads. Use as the browser layer under skills that read or act on web pages, like job-search-copilot and browser-ai-bridge."
---

# playwright-browser-bridge

A small, reusable layer that other skills build on to drive a **real browser** through Playwright.
It exists so that "an agent touches the page" follows the same safe, predictable rules everywhere,
instead of each skill reinventing session handling and selector hygiene.

This is a **substrate**: it is consumed by `job-search-copilot` (form discovery + guided
walkthrough) and `browser-ai-bridge` (dogfood/QA). It deliberately does **not** ship a user-facing
flow of its own.

## Core principles

1. **Attach, don't launch.** Prefer connecting to a browser session the user already has open
   (`browser_navigate` against the running context). Launch a fresh headless instance only when no
   session exists and the caller explicitly asks for it. The user keeps control of the window.
2. **Navigate in place.** Reuse the current tab/page rather than spawning new ones, so the user's
   context (logins, scroll, open forms) is preserved.
3. **Selectors are drift-prone.** Treat any selector as stale until re-verified against a fresh
   snapshot. Re-snapshot before acting; never act on a remembered element reference from an earlier
   page state. When a selector misses, refresh and re-derive — don't retry blindly.
4. **Read before you write.** Use `browser_snapshot` / `browser_evaluate` to read DOM, console,
   network, and computed layout first. Measure with `getBoundingClientRect()` + computed styles —
   don't eyeball pixel positions.
5. **Data-lifecycle discipline (hard rule).** Anything the browser downloads or exports goes to a
   temporary directory, is parsed there, and is **deleted** when done. Never write fetched page data
   or downloads into the repo, and never commit it. Aggregate/transform in memory where possible.

## Read patterns

- **Snapshot** for structure and an actionable element map (the basis for any click/type).
- **Evaluate** for precise reads: text content, attribute values, `getBoundingClientRect()`,
  `getComputedStyle()`, console/network state.
- Re-snapshot after every navigation or DOM mutation; cache nothing across page transitions.

## Acting (for consumers that write)

When a consuming skill performs actions (click/type/select/navigate), this layer requires:

- Re-derive the target from a **current** snapshot immediately before acting.
- One action at a time, re-reading state between actions on dynamic pages.
- Surface what is about to happen to the caller; the caller decides whether confirmation is needed
  (e.g. `job-search-copilot` requires explicit human confirmation before any submit).

## Compatibility

Requires a Playwright-capable runtime (e.g. the Playwright MCP server, or an equivalent browser
driver). Tool-agnostic in spirit, but the browser-driving capability narrows where it runs — declare
it so the gallery's "works on" badge reflects the dependency.

## What this is NOT

Not a scraper, not a credential harvester, not a headless bot for mass automation. It is a careful,
session-respecting bridge for an agent working **alongside** a human on a real page.
