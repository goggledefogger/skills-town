# Triage — turning a capture pile into vault commitments

Capture and commitment are different jobs. A walk should stay frictionless — drop a stray thought, an errand, a half-formed idea into the inbox without stopping to categorize or judge it. But nothing earns a spot in the vault's real task/priority files until it's been through triage, or "current priorities" turns into the same anxiety-pile the inbox was.

## When this applies

Only when `triage.loop: agent` in `config.yaml` — no separate external system owns triage, so the assistant runs it. If `triage.loop: user`, the user's own loop (Todoist, a planner, a partner review) owns this and this file doesn't apply — the skill only feeds that loop, never reconciles for it. If `triage.loop: none`, nothing triages the pile on purpose (rare) and this file doesn't apply either.

**The rule that makes agent mode work: never dump the raw capture list straight into the vault's task/priority files.** Always run it through the loop below first.

## The loop

Run this weekly, or whenever the pile is bugging the user — not mid-walk (see "Where this fits" below).

1. **Parse and bucket.** Sort everything into a few buckets without judging volume: strategic/project work, admin/ops, ideas/someday (not actionable this week), quick wins (under 15 minutes — worth batching into one sitting, not sprinkling through the week).
2. **Align to the vault.** If an item maps to an active project or a stated priority already in the vault, say so explicitly (a link, a tag — whatever the vault uses for cross-referencing).
3. **Recommend when, not just what.** Don't hand the list back "organized" — give a small set of concrete suggestions: what fits this week, what to batch, and what to explicitly defer, so the backlog stops feeling like an accusation.
4. **Clarify ambiguity — batched, not one at a time.** Never guess where an ambiguous item belongs. Ask short, concrete, ideally multiple-choice questions, batched up to ~5 at a time so the user answers inline instead of being interrogated one at a time. **This is the one place in the skill where batched/multi-part questions are correct** — a triage session is a desk/text reconciliation, not the walking voice loop, so it doesn't conflict with `voice-mode-contract.md`'s "one light question at a time" rule (that rule governs live walking turns; see also `task-affinity.md`'s command-vs-click framing for why triage sits at the desk). Nothing ambiguous gets locked into the plan until the user answers.
5. **Write back to the vault.** Once confirmed, persist the outcome (checkboxes, new project bullets, a parked-ideas list) through the normal git write path — `scripts/git-safe-commit.sh`, same session-branch/no-force guarantees as any other vault write. The next session inherits reality instead of re-litigating the same pile.
6. **Remember stable resolutions.** When the same kind of clarifying question keeps recurring ("does this item mean X or Y"), write that resolution into the vault note at `triage.preferences_note` (config) so it stops being asked. This note is normal vault content — committed and synced like everything else — not `.walk-and-talk/` runtime state.

## Failure modes to avoid

- **Blind filing.** Silently guessing where an ambiguous item belongs and locking it in — wrong calls compound invisibly.
- **Un-triaged handback.** Surfacing the entire raw list back to the user, organized-looking but still undecided — just as much noise as skipping triage altogether.

## Where this fits

Triage is normally an async, desk-based reconciliation pass over what capture already delivered — it is not one of the numbered steps in "Running a session" (SKILL.md), and it doesn't need voice mode active at all. The capture side (getting things *into* the inbox in the first place, one item at a time, hands-free) is the walk's job; this file is about what happens to that pile afterward.
