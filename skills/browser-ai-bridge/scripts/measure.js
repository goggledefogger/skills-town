// Pass this function to `browser_evaluate` to measure a real element instead of eyeballing a
// screenshot. Returns its box, key computed styles, the viewport, and whether it's offscreen.
//
// Usage (Playwright MCP): browser_evaluate(<this function>, { selector: 'button[type=submit]' })
// Stands alone — no imports, runs in the page.
({ selector }) => {
  const el = document.querySelector(selector);
  if (!el) return { found: false, selector };
  const r = el.getBoundingClientRect();
  const cs = getComputedStyle(el);
  const vw = window.innerWidth, vh = window.innerHeight;
  const pick = [
    'display', 'position', 'color', 'backgroundColor', 'fontSize', 'fontWeight',
    'padding', 'margin', 'border', 'borderRadius', 'textAlign', 'zIndex', 'overflow',
  ];
  const styles = {};
  for (const k of pick) styles[k] = cs[k];
  return {
    found: true,
    selector,
    rect: { x: Math.round(r.x), y: Math.round(r.y), width: Math.round(r.width), height: Math.round(r.height) },
    styles,
    viewport: { w: vw, h: vh },
    offscreen: r.bottom < 0 || r.right < 0 || r.top > vh || r.left > vw,
    clippedRight: r.right > vw,
  };
};
