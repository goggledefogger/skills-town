# Reads: snapshot vs evaluate

Two read tools, two jobs. Use the right one.

## Snapshot — structure + an actionable element map
`browser_snapshot()` returns the accessibility/DOM structure with stable references you can act on.
Use it to:
- Understand what's on the page right now.
- Get the element references for the next click/type (always from the **latest** snapshot).

## Evaluate — precise values
`browser_evaluate(fn)` runs JS in the page and returns real values. Use it to:
- Read exact text or an attribute: `el.textContent`, `el.value`, `el.getAttribute('...')`.
- **Measure, don't eyeball:** `el.getBoundingClientRect()` for position/size, `getComputedStyle(el)`
  for actual rendered styles.
- Inspect console and network state when debugging.

Example — measure a button at the current viewport:
```js
() => {
  const b = document.querySelector('button[type=submit]');
  const r = b.getBoundingClientRect();
  return { x: r.x, y: r.y, w: r.width, h: r.height,
           color: getComputedStyle(b).backgroundColor };
}
```

## Re-read after every change
Any navigation or DOM mutation invalidates what you knew. Re-snapshot before the next action; never
trust cached structure across a page transition.
