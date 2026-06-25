---
name: browser-ai-bridge
description: "Walk through your app with an AI helper in a real browser you can watch. It reads the live page and actually clicks, types, and edits it while you talk — not just looking, and not hidden. Use to test your own web app, reproduce a bug, or get guided help walking through a UI."
---

# browser-ai-bridge

Dogfood your own app **with** an AI co-pilot in a real, visible browser. You narrate what to check or
change; it reads the live page back to you and acts on it — for real — through a Playwright runtime.
It both **observes** (DOM / console / network / layout) and **acts** (click / type / navigate / edit),
and it stays honest about what's actually a bug versus what was already broken.

Built on `playwright-browser-bridge` — so it inherits attach-don't-launch, re-snapshot-before-acting,
and the download→temp→delete discipline.

## What makes it useful (not just a screenshot bot)

- **Head-full, watched.** It works in a browser you can see, attaching to your session rather than a
  hidden one. You watch every click.
- **It acts, then re-reads.** Beyond reading state, it clicks/types/edits on your narration and reads
  back the result.

## The dogfood loop

1. **Narrate** the check or change ("the submit button looks off on mobile").
2. **Read the live state** — snapshot the DOM, pull console/network, and **measure** with
   `scripts/measure.js` at real viewport sizes (desktop ~1280px and phone ~390px). Measure, don't
   eyeball.
3. **Find the real source** — locate the actual file/component behind the UI before proposing a
   change. Grep siblings for the same pattern; check whether the data is real or a fixture.
   → `references/tracking.md`
4. **Triage honestly** — separate a true regression from a pre-existing failure and from a fixture
   artifact. "Verified — no change needed" is a real, useful outcome. → `references/verification.md`
5. **Act** (when asked) through the bridge — one action at a time, re-reading between actions.
6. **Say stopgap vs durable** — be explicit about which kind of fix a change is.

## Measuring (the honest part)

Use `scripts/measure.js` with `browser_evaluate` to get an element's real box and computed styles at
the current viewport, instead of guessing from a screenshot:

```
browser_evaluate( <contents of scripts/measure.js>, { selector: 'button[type=submit]' } )
→ { found, rect:{x,y,width,height}, styles:{...}, viewport:{w,h}, offscreen }
```

Resize the viewport (e.g. 390×844 for phone), re-measure, and compare. Numbers settle arguments that
screenshots start.

## Boundaries

- Works alongside you on **your own** app — not a headless crawler or mass-automation bot.
- Browser access goes through `playwright-browser-bridge` (attach, re-check, temp-delete).

## Compatibility

Needs a Playwright-capable runtime and a real browser (via `playwright-browser-bridge`) — which
narrows where it runs; declare the dependency so a "works on" badge reflects it.
