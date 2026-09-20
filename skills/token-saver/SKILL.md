---
name: token-saver
description: "Cuts token spend with three rules: read passages not files, count every call in the job, never retry a usage-limit failure. Use when a session gets expensive or before adopting an efficiency skill."
license: MIT
disable-model-invocation: true
allowed-tools: [Read, Grep, Bash]
---

# token-saver

## Arguments

`$ARGUMENTS` may carry a subcommand:

- **(none)** — activate for the session, greet per "On activation" below
- **`report`** — grade the session so far, right now. Build the ledger from what you have tracked since activation and pipe it to the grader (see "Report back"). Show the report card, then continue working, and keep tracking — a mid-session report does not reset the ledger. If the skill was not active before this call, there is nothing tracked: say so in one line and let the grader print its honest UNSCORED rather than reconstructing numbers from memory

## On activation

Open with a short, plain greeting — close to this, in your own words:

> Token-saver is on. For this session I'll read only the parts of files I actually need, tell you whenever an answer came from a partial read, and never cut corners on anything important — correctness always wins over savings. Ask for `/token-saver report` any time to see how it's going, and I'll show a report card at the end either way. What are we working on?

Do not recite the rules, list tools, or explain the tracking mechanics up front. The rules below are for you to follow, not to announce. If the user asks how it works, then explain.

Three rules. They are the residue of auditing an 8-strategy token-saving skill and comparing it against a measured baseline. The other 5 strategies were already covered elsewhere or were actively wrong.

The one script here is a grader, not machinery: it only does arithmetic on numbers you hand it, and it refuses to invent any it wasn't given. Nothing in this skill selects, retrieves, or filters content. See "What this deliberately does not do" below.

## The three rules

1. **Read passages, not files.** Search first (`rg -n`, `rg -l`, a scoped `grep`), then read the span you need. If the first bounded read misses, take a second bounded read. Do not fall back to loading everything, because that is the move the discipline exists to prevent.

2. **Count the whole job, not the turn.** Every call counts: planning, selecting, answering, verifying, repairing. Moving work to a subagent, a cheaper model, or another host is not a saving unless the combined total falls. If a number is not reported, write `unavailable` and do not infer one.

3. **Never retry a token or usage limit failure.** A limit error is not transient. Reduce the input, pick a cheaper path, or wait for the reset. Retrying turns one refusal into several.

## Never trade these for tokens

This is the load-bearing half of the skill. A token budget that produces a wrong answer cost more than it saved.

- **Correctness outranks the saving, always.** On anything consequential (production, money, security, migrations, a decision someone will act on) read fully. The saving is off. Say so in one line rather than silently economizing
- **Name what you did not read.** After a bounded read, if the answer could turn on material outside the span, state the gap: "answered from `config.py:40-95`, did not read the 3 other call sites." An unqualified answer from a partial read is the failure this skill exists to prevent
- **A second read is cheaper than a wrong answer.** When uncertain whether the span was enough, take the second read. The rule is "read narrowly," never "read once"
- **No skipping**: input validation at trust boundaries, error handling that prevents data loss, security checks, accessibility basics, or anything the user explicitly asked for
- **Never skip reading to save tokens on code you are about to change.** Trace every file the change touches. A small diff in the wrong place is a second bug, not a saving

## What this deliberately does not do

No packet builder, no state file, no relevance scoring, no content selection of any kind. The skill this was extracted from shipped all of that, and the machinery was the part that broke:

- A relevance filter that drops below-threshold chunks returned an **empty packet on a paraphrased question** while reporting a successful selection on stderr
- Any broad verb (summarize, review, explain, analyze) disabled the filter, leaving file position as the only signal, so selection degraded to `head` with a passage count still attached. Truncation labeled as selection produces confident wrong summaries
- Writing a packet to disk and reading it back costs **more** than a scoped `rg -C 5`, because the agent doing the reading is the model you were trying to protect. Packet building only pays when the packet crosses into a different context

A rule you follow cannot silently return nothing. That is the entire argument for keeping the working half of this skill prose-only. The grader is exempt from that argument because its failure mode is the safe direction: given missing or malformed input it degrades to `unavailable` and `UNSCORED`, never to a good grade.

## Already covered, do not duplicate

| Concern | Where it already lives |
|---|---|
| Output brevity, artifact size, no unrequested abstractions | a brevity or minimalism ruleset, if you run one |
| Which model or agent fits a task | a model-routing skill, if you run one |
| Measuring actual spend per project | a spend or token audit, if you keep one |

Check what you already run before installing anything new. Overlap is the normal case.

## Before adopting another efficiency skill

Ten minutes, four checks:

1. **Plant a needle and paraphrase the question.** Retrieval that only works when you already know the file's wording is a slower `grep`. The paraphrase leg has to be able to fail, or the test proves nothing
2. **Try the boring verbs.** Summarize, review, explain. The most common asks are the most likely to bypass a relevance filter
3. **Check the cost direction, not just the magnitude.** An always-on ruleset is re-sent as input on every call. One published benchmark shows a 42-75% saving on Claude reversing to 26-39% *more expensive* on reasoning models for exactly this reason
4. **Prefer the thing with receipts.** A measured range with a published method, especially one whose authors corrected their own headline downward, outranks any asserted percentage

Safe, careful authorship says nothing about whether the algorithm works. The skill audited here had no network calls, skipped `.env` and secret-named files, and escaped injection markers in its output. Its selector still missed the answer.

## Report back

Track 4 things as you work, then grade the session. Do not keep a running commentary, just note them:

- each file you read narrowly: bytes read, and the file's real total size (`wc -c`)
- token counts per call when the host reports them
- a rough running total of tool output you received (command results, probe output, logs) as `tool_output_bytes` — this is usually the real cost driver, and recording it turns a recurring caveat sentence into a number on the card
- **corrections**: every time a bounded read missed and needed a second read
- **incidents**: any wrong or partial answer that reached the user, and any case where the discipline cost more than it saved

At the end, hand those to the grader on stdin (no file is written into the user's project unless they ask):

```bash
echo '{"used":true,
       "reads":[{"path":"a.py","bytes_read":900,"bytes_total":42000}],
       "calls":[{"model":"opus","in_tokens":4100,"out_tokens":600}],
       "corrections":0, "tool_output_bytes":52000,
       "incidents":[{"severity":"harm","note":"answered from a partial read"}],
       "price_in_per_mtok":15.0}' \
  | python3 "<this skill's folder>/scripts/report.py"
```

Incidents are objects: `{"severity": "harm"|"low", "note": "..."}`. A bare string still counts (it coerces to harm — nothing you record can vanish on a shape mismatch), but the object form is what lets a genuinely minor issue grade as minor. Omit `price_in_per_mtok` unless you have the real rate; never supply one from memory.

**Persisting the card (opt-in).** If you keep a log or dashboard of your sessions, add `--log "<some-dir>/token-saver-cards.jsonl"` to the grader call and it appends the card as one JSON line there (`scripts/report.py`'s docstring says why an append-only line of the grader's own output is the one persistence this skill allows). Without `--log`, nothing touches disk. A failed `--log` write errors loudly — report it, never shrug it off.

```
token-saver report card
  grade    A — read just what it needed, skipping 98% of the file content
  saved    ~10,275 tokens of reading avoided (estimate), roughly $0.15
  spent    1 model call(s), 4,100 tokens in / 600 out
  safety   clean — no corners cut, nothing went wrong
  note     ~13,000 of the spent tokens were command output, which reading discipline can't shrink
```

**Subagents are off the card.** The ledger only knows what this session read; a lane run by a subagent reads on its own and reports nothing back to the grader. When lanes did real reading, say so in the one sentence after the card rather than letting the grade imply the whole job was cheap.

**Present the card as the grader prints it.** Do not rewrite it, pad it with per-file breakdowns, byte tallies, or method notes — that turns 3 KPIs back into jargon. One plain sentence after the card is allowed when the real cost driver was something the ledger cannot see (tool output, SSH probes); keep it to words a non-engineer follows. Full detail only if the user asks.

**Always run the grader, even with gaps.** Missing token counts or file sizes are its normal diet: it prints what it has and says `unavailable` for the rest. Skipping it and hand-writing a report is the one move that is worse than either.

**Grade quietly, speak plainly.** When talking to the user, never say ledger, grader, ratio, bytes, or packet — the card speaks in tokens and percentages, and so do you. Collect sizes and build the tracking JSON without narrating it — no play-by-play of `wc -c` runs, no ledger JSON in your reply, no commentary on what the grader did. The user's view of reporting is the card plus at most one plain sentence. If you hit a bug in the skill itself, note it in 1-2 lines after the card and move on — diagnosis essays go to a GitHub issue on goggledefogger/skills-town, not into the session.

**Efficiency** is a grade from one mechanical rubric: A ≤10% of available bytes read, B ≤25%, C ≤50%, D ≤75%, F above that. Any limit-retry or incident forces F, because a cheap wrong answer is not a saving.

**Risk** is 1 of 4 states, never 2:

| State | Meaning |
|---|---|
| `CLEAN` | no corrections, retries, or incidents recorded |
| `CORRECTION` | a bounded read missed and needed a second read, or a retry happened. Working as intended, but the narrow read was too narrow |
| `HARM` | a wrong or partial answer reached the user, or spend went up. Forces grade F |
| `UNSCORED` | the skill was not used, or nothing was recorded. **Not a pass** |

What the grader will not do: infer a number that was not supplied (it prints `unavailable`), print a dollar figure without a real price, count a read whose file total was never recorded, or grade a session it has no ratio for. "Avoided" is honest here only because a file's size is a knowable fact, so it is what you did not load, not a guess about an alternate session. Run `python3 scripts/report.py --selftest` to see the negative controls that hold those rules in place.

## Invocation

Manual only (`/token-saver`), set by `disable-model-invocation: true`. A token-saving ruleset that auto-triggers can quietly narrow what gets read on work where that is the wrong trade. Remove that frontmatter line if you want it model-invocable. It is a Claude Code field; other agents ignore it.

The skill is a plain Agent Skills folder: `SKILL.md`, `scripts/report.py`, and two thin `commands/` pointers for Claude Code. Install it as a Claude Code plugin from the `goggledefogger/skills-town` marketplace, or into any agent that reads `SKILL.md` with `npx skills add goggledefogger/skills-town --skill token-saver`.
