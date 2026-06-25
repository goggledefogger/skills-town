# Modes & the audio-OS feel

walk-and-talk is not one fixed flow. It runs in **modes**, and it **tailors itself** to each person's second brain, habits, and scenario. Two real modes, synthesized from how people actually walk-and-think:

## The two modes

**Passive capture** — the quiet default. Ideas surface on a walk and get dropped into the user's capture inbox; the second brain ingests, triages, and schedules later. The defining principle is **passivity**: let the user enjoy the walk or listen to a book — don't make them interact with a device. Mostly one-way capture, minimal prompting, near-zero friction. This is the **default**: stay quiet until told otherwise.

**Walk-and-work** — the active mode, opt-in. Beyond capture, actually get work done by voice on the move: draft an email end to end, work a note, triage with confirmations. Interactive and productive — "a standing desk, but better." Only entered when the user opts in (by command, routine, or context).

These are modes, not products. The user can run either, blend them, or switch by context — including by **time of day / routine** (capture-only on the morning commute, walk-and-work in a focused afternoon block, fully quiet in the evening).

A third convenience mode, **quiet**, is fully silent capture (evening zone-out): captures locally, says nothing.

## Audio-OS principles (how every mode should feel)

1. **Right amount at the right time.** Say only what's useful; default brief. Silence is a valid, often correct, output.
2. **Mostly yes/no.** Prefer confirmations and simple either/or choices over open-ended back-and-forth — easy to answer hands-free.
3. **Know when NOT to barrage.** Read the context. A relaxed walk is not a work session. In passive/quiet mode, stay silent unless the user reaches for you.
4. **One button + voice.** Assume a single physical button for advance/confirm — by default a button on the user's **Bluetooth headphones/earbuds** (most have a multifunction/play-pause button); a ring or clicker works too. Design every interaction so it works with one button plus short voice — never a menu that needs eyes.
5. **Graceful with and without service.** Degrade cleanly offline: capture locally, sync later. Never assume connectivity (capture-before-network, invariant #3).

## How a mode is chosen

Resolved **per user**, in this order (first match wins):

1. **Explicit command** — "switch to work mode" / "go quiet" / "just capture."
2. **Time-of-day / recurring routine** — `mode_triggers` in `config.yaml` (e.g. `07:00-09:30 passive`). `session.sh mode --resolve` reads the clock and picks. This is the deterministic, built path.
3. **Location / calendar context** — behavioral for now: if the user (or a calendar note in the vault) says they're commuting vs in a focus block, honor it. Not auto-detected in v1.
4. **Default** — `voice.default_mode`, which ships as **passive** (Dan's principle).

The current mode lives in `state.json` (`mode`), so scripts and the assistant agree on it.

## Self-tailoring (the core directive)

When pointed at a second brain, the skill must **not assume a fixed structure**. On first run it briefly senses + interviews:

- **What the second brain is** — Obsidian vault, plain notes, a task system.
- **Where capture lands** — an inbox file, the daily note, or an external task app (e.g. Google Tasks). For external targets the skill captures **locally first** and hands off to the user's existing triage/scheduling loop — it does not reimplement their system.
- **Their existing triage/schedule loop** — who owns sync and scheduling (usually the user's setup; the skill feeds it, doesn't replace it).
- **Device + connectivity + walk/commute context.**
- **What they want and how much to hear** — passive, active, or both, and when each kicks in.

It then writes a tailored `config.yaml` (capture target, triage owner, verbosity/quiet defaults, modes + triggers, offline behavior) wired to that user — defaulting to **passive + quiet** until they opt into more.
