---
name: browser-ai-bridge
description: "Walk through your app with an AI helper in a real browser you can watch. It reads the live page and actually clicks, types, and edits it (via Playwright) while you talk — not just looking, and not hidden. Use to test your own web app, reproduce a bug, or get guided help walking through a UI."
---

# browser-ai-bridge

Dogfood your own app *with* an AI co-pilot in a **real, visible browser**. You narrate what you want
changed or checked; it reads the live page back to you and acts on it — for real — through Playwright.
It both **observes** (DOM/console/error/network) and **acts** (click/type/navigate/mutate). Built on
the shared `playwright-browser-bridge`.

## What makes it different

- **Head-full, not headless.** It targets a browser **you can see**, attaching to your existing
  session rather than launching a hidden one, so you watch every action and stay in the loop.
- **It acts, not just reports.** Beyond reading state, it clicks, types, navigates, and edits the DOM
  on your narration — then reads back the result.

## The dogfood loop

1. **Narrate** the change or check you want ("the submit button looks misaligned on mobile").
2. **Read** the live state — snapshot the DOM, pull console/network, measure with
   `getBoundingClientRect()` + computed styles at real viewport sizes (e.g. 1200px desktop and a
   ~390px phone width). Measure, don't eyeball.
3. **Find the real source.** Locate the actual file/component behind the UI suggestion before
   proposing a change. Grep siblings for the same pattern; check whether the data is real or a
   fixture.
4. **Triage honestly.** Separate genuine regressions from pre-existing failures and from fixture
   artifacts. "Verified — no change needed" is a valid, useful outcome.
5. **Act** (when asked) through the bridge — one action at a time, re-reading state between actions.
6. **Decide stopgap vs durable** and say which a change is.

## Verification discipline

- Test at concrete viewport sizes, not "looks fine."
- Attribute failures: is this new, or was it already broken? Don't claim a fix for something you
  didn't change.
- Prefer measured evidence (rects, computed styles, console output) over impressions.

## Boundaries

- Works alongside you on your own app — not a headless crawler or mass-automation bot.
- Browser access goes through `playwright-browser-bridge`: attach-don't-launch, navigate in place,
  re-snapshot before acting, and the download→temp→delete data discipline.

## Compatibility

Depends on a Playwright-capable runtime (via `playwright-browser-bridge`) and a real browser — which
narrows where it runs; declare the dependency so the "works on" badge reflects it.
