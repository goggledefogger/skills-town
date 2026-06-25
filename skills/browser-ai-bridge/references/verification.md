# Verification: measure, and attribute failures honestly

## Measure at real viewports, don't eyeball
Test at concrete sizes, not "looks fine":
- Desktop ~1280×800, phone ~390×844 are good defaults.
- Resize the browser, then use `scripts/measure.js` via `browser_evaluate` to read the element's real
  `getBoundingClientRect()` and computed styles at that size.
- Compare numbers across viewports. `clippedRight: true` or `offscreen: true` is a fact; "it looks
  cramped" is an opinion.

## Attribute failures
Before claiming a fix or reporting a bug, answer: **is this new, or was it already broken?**
- Reproduce on the unchanged state first. If it was already failing, say so and scope it out — don't
  claim credit for "fixing" something you didn't change, and don't block on a pre-existing issue.
- A regression you introduced is yours to fix; a pre-existing failure is a separate, noted item.

## Evidence over impressions
Prefer measured evidence — rects, computed styles, console output, network status — over screenshots
and vibes. Screenshots start arguments; measurements end them.
