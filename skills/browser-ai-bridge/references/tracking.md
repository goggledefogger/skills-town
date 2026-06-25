# Tracking: find the real source before you touch anything

A UI symptom is not a fix location. Before changing code, find the thing that actually renders it.

## Steps
1. **From symptom to file.** The misaligned button on screen maps to a component somewhere. Find that
   file — search for the visible text, the class, the test id, the route.
2. **Grep siblings.** Is this pattern used in five other places? A local hack here may need to be a
   shared fix (or may break the other five). Look before you leap.
3. **Real data or fixture?** Confirm whether what you're seeing is live data or a mock/fixture. A
   "bug" in fixture data isn't a code bug. Don't fix the wrong layer.
4. **Stopgap vs durable.** Decide and *say* which one your change is. A quick patch to unblock is
   fine — as long as everyone knows it's a patch, not the real fix.

## "Verified — no change needed" is a result
If you investigate and the behavior is correct (or the failure is pre-existing and out of scope),
that's a legitimate, valuable outcome. Don't invent a change to look productive.
