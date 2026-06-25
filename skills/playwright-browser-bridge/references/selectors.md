# Selectors drift — re-derive, don't remember

The single most common way browser automation breaks: acting on a selector or element reference that
was valid one state ago and isn't anymore.

## The rule
Re-derive every target from a **fresh snapshot taken immediately before you act**. Treat any selector
older than the current page state as stale.

## In practice
- Snapshot → read the element ref → act on that ref → (page changes) → snapshot again before the next
  action. Don't reuse the old ref.
- If a click/type targets nothing or the wrong thing, **do not retry the same selector**. Re-snapshot,
  see what actually changed (a modal opened? a field revealed? navigation happened?), and re-derive.
- Conditional fields (Greenhouse/Lever/Ashby/Workday) appear *after* a prior answer — they won't be in
  an earlier snapshot. Re-snapshot after each answer to find them.

## Why not just use CSS selectors and retries?
Because pages built with modern frameworks re-render: ids change, nodes detach, content shifts. A
retry loop on a stale selector silently does the wrong thing. A fresh snapshot tells you the truth.
