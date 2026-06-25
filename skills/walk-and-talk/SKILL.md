---
name: walk-and-talk
description: "Turn any second brain (Obsidian, notes, a task system) into a voice-first, eyes-free walk-and-talk companion. Two modes: PASSIVE capture (the quiet default — drop ideas into your inbox, stay out of the way) and ACTIVE walk-and-work (draft and get things done by voice). It tailors ITSELF to your setup, habits, and routine rather than shipping one fixed flow, and can switch modes by time of day, routine, or spoken command. Reads briefs aloud (synthesized, never raw markdown), drafts without sending, commits safely. Use to run a walk-and-talk session, set up a hands-free capture/work loop, or point the skill at your own second brain. Runtime-agnostic; includes a self-tailoring setup advisor."
---

# walk-and-talk

A listening-first way to work **any** second brain on a walk — or a walk-and-*work*. This skill is **behavioral + advisory**: it does not capture microphone audio or run a voice loop itself. It shapes how the assistant behaves inside whatever voice runtime you already drive, and it ships deterministic scripts that enforce the field-safety rules that must not be left to chance (git isolation, capture-before-network, never-send).

**It runs in modes and tailors itself to you.** The default is **passive capture** — quiet, one-way, let you enjoy the walk. **Active walk-and-work** is opt-in: draft and get real work done by voice. It can switch by time of day, routine, or spoken command. See `references/modes.md` — this is the heart of how it should *feel*.

## Talk like a person — plain language (applies to everything, setup too)

This is a voice-first, eyes-free tool, so *how you talk* matters as much as what you do. Keep all output — spoken and written, setup and in-session — simple and human:

- **Plain words, no jargon.** Say "tap your earbud to send," not "`--button` / CGEvent / Apple-native helper." The flags, frameworks, and permission mechanics are *yours* — don't make the user read them.
- **One thing at a time.** Lead with the single recommended next step and a yes/no. Don't dump every option, tradeoff, and caveat at once.
- **Few symbols.** Avoid arrows, nested bullets, and code blocks unless the user asks.
- **Permissions, simply.** "It'll ask permission once — just allow it," not a lecture on Accessibility.
- **When something won't work,** say so in one plain sentence and offer the easy alternative — skip the internals of *why*.
- **End setup in a sentence, not a report.** When setup finishes, don't recap the config and machine notes in sections. Say it's ready, surface at most *one* thing the user needs to do (e.g. "turn Voice Control on" or "connect your earbuds"), and offer the single next step ("want to start now?"). The details live in the config — don't read them back.

> **Hard constraint:** Claude Code's native `/voice` dictation works only on the local machine — **not over SSH or Claude Code web**. So a walk-time session needs another runtime. The setup advisor handles this; see below.

## Start here: run the setup advisor

Before a first session, detect the user's situation and write a config:

```
bash ${CLAUDE_SKILL_DIR}/scripts/setup-advisor.sh --vault /path/to/vault            # report only
bash ${CLAUDE_SKILL_DIR}/scripts/setup-advisor.sh --vault /path/to/vault --write-config
```

It reports what's present (OS, vault, git remote, voice runtimes, API keys, local-vs-remote), names the tested transport default, states the SSH/web voice constraint, and (with `--write-config`) writes `<vault>/.walk-and-talk/config.yaml` and gitignores the state dir. On macOS, `--write-config` **also does the audio setup during setup** — it sets the mic to the built-in one and **opens the Voice Control settings** so the user can turn it on right then. So don't defer that to session start; in your wrap-up, just point at the open Voice Control window ("turn it on there"). See `references/transport-default.md` for the recommended remote setup.

**Guided setup is a theme.** Whenever the user lacks a prerequisite — the Telegram bridge, Voice Control, earbuds, a transport app — don't just name it; walk them through it one plain step at a time, saying only the next step (the bridge's `tg-send.sh --setup` is the pattern). The user never sees file paths, flags, env-var names, or tool errors, and never edits a config file themselves: if a step needs a secret like the bot token, they paste it to you and **you** write it into the gitignored config. Don't narrate debugging — if a command fails, fix it quietly and surface only the plain next step. They speak intent; you run the tool.

### Sense & tailor (first run) — the core directive

Do **not** assume a fixed structure. The advisor senses what it can (second brain type, an inbox/daily-note dir); you fill the rest with a **brief, yes/no-friendly interview**, then refine the config. Ask only what you can't sense, one light question at a time:

1. **Where should capture land?** (the sensed `capture.path`, the daily note, or an external app like Google Tasks — for external, you capture locally and hand off to their loop).
2. **Who owns triage/scheduling?** (almost always their existing loop — confirm).
3. **How much do you want to hear, and when?** → sets `voice.verbosity` and the `mode_triggers` (e.g. capture-only commute, active afternoon, quiet evening).
4. **Default mode?** Default to **passive** unless they say otherwise.

Write the answers into `config.yaml`. The goal: a person points this at their own second brain and gets a walk-and-talk that fits *their* scenario — Dan's quiet passive capture and Danny's active walk-and-work, both available.

## Earbuds — do you need them, and connecting them

Help the user decide and get connected — don't assume the earbuds are sorted:

- **Going for a walk?** Use earbuds — private audio, hands free. Make sure they're charged, turned on, and connected to this Mac (click the sound icon in the menu bar and pick them; if they've never paired, pair them once in Bluetooth settings).
- **At your desk in a quiet spot?** You can skip earbuds — the laptop speakers and mic work fine. Earbuds are still nicer if you want the audio private.
- **Right after you connect earbuds,** the mic often switches to them, which sounds worse and can stop Voice Control hearing you. Just run the audio check again — it puts the mic back on the built-in one.
- **On a phone, same idea:** pair the earbuds in the phone's Bluetooth settings first. (The full walk-from-your-phone setup is a bigger piece; this is just getting the earbuds connected.)
- **Adapt to the user on earbuds.** Some always want one in, some don't care — ask once and store it (`earbud_ready_nudge` in config). Surface the "pop an earbud in" nudge right *after* the first phone audio works (the quick win), not before — and skip it entirely for users who don't want it.

## Runtime state

All runtime state lives in **`<vault>/.walk-and-talk/`** and is **kept out of git** (never synced): `config.yaml`, `state.json` (voice-mode flag, mode, session branch), `queue/` (capture-before-network jobs), `audio/` + `transcripts/`. For a git vault the advisor excludes it via **`.git/info/exclude`** (local, untracked) so setup never dirties your tracked `.gitignore`; for a non-git vault it falls back to `.gitignore`.

## Running a session

**0. Pick the mode (default passive).** `session.sh start` resolves the mode from `mode_triggers` (time of day) or `voice.default_mode`. Honor a spoken override immediately: "work mode" → active, "go quiet"/"just capture" → passive/quiet (`session.sh mode --set <mode>`). **In passive/quiet, stay out of the way** — capture what's said, acknowledge in a word or stay silent, no briefing or follow-ups unless the user reaches for you. Only the steps below (briefing, drafting, back-and-forth) belong to **active** walk-and-work. See `references/modes.md`. In active mode, also weigh `references/task-affinity.md` — keep scriptable/CLI work on the walk (talk it out, move/download files, transfer info, edit notes, git) and park GUI work (slicers, CAD, image editors) for the desk; tune the talk-vs-nudge cadence and how often you speak updates to the user.

**1. Activate.** Start a session and adopt the contract:

```
bash ${CLAUDE_SKILL_DIR}/scripts/session.sh start --vault <vault>            # resolves mode by time
bash ${CLAUDE_SKILL_DIR}/scripts/session.sh start --vault <vault> --mode active
```

Then **read `references/voice-mode-contract.md` and follow it for every turn** until the user exits. It is mode-aware and sets the rules: the audio-OS feel (right amount/right time, mostly yes/no, one button + voice), one-breath turns, tactile interrupt, and the safety boundaries. `session.sh` writes the `voice_mode` flag **and `mode`** to `state.json` so scripts and the assistant agree. Switch modes mid-walk with `session.sh mode --set <mode>` or `--resolve`; exit with `session.sh stop`.

**Desk → walk handoff (one session — attach, don't restart).** Context lives in the **single Claude Code session running in tmux** on the always-on machine — that's the whole reason the stack uses tmux (session persistence) + Mosh (survives phone sleep / network handoff). On the walk the phone *attaches to that same session* via Termius+Mosh; it does **not** start a new one. So when the desk session is primed and started, **acknowledge the handoff out loud**: say it's running persistently and that from the phone they reattach to *this* session to keep full context. A brand-new session knows only the durable anchors on disk (`primer.md`, `state.json`, vault notes + offline queue) — enough to re-prime the gist, not the live conversation. And note the split: the Telegram bridge is audio **output** only; the context-continuing path is the tmux attach, so a walk needs both. Set the attach up with `scripts/phone-link.sh` — same guided-setup pattern (one plain step at a time, assistant runs the installs / `tailscale up`, user does only the phone-app + Termius bits).

**Getting voice in and out (read `references/hands-free-input.md`).** The loop is turn-based: the assistant speaks a reply only when the user's message is actually **submitted**, so dictated-but-unsent input = silence (the #1 gotcha). Output: speak each reply with **`scripts/speak.sh "..."`** (wraps macOS `say` with a trailing-silence guard so Bluetooth doesn't clip the last word — a real, confirmed issue; tunable via `WAT_SPEAK_TAIL_MS`). It prints + logs a transcript so a missed word can be **seen**, and `speak.sh --repeat` re-speaks the last line. **Also restate spoken text in your visible reply** — the client can collapse tool output, so the words must live in the message, not only in the Bash result. Input: dictate with **Voice Control** (Accessibility — *not* plain Dictation), then submit. Submit options, simplest-first: (1) **tap Return**; (2) fully hands-free via **`scripts/auto-submit/run.sh`** — an Apple-native helper where an **earbud play-pause tap** (`--button`) or a **speak-then-pause** (`--voice`) presses Return for you. VC can't bind Return itself and Shortcuts is sandboxed from keystrokes — that's why the helper exists (details + dead-ends in `references/hands-free-input.md`). Run **`scripts/audio-check.sh --fix`** first (sets input to the built-in mic; the earbud-as-mic HFP trap and VC's "Automatic" mic are the silent killers).

**If the user tests the earbud tap,** first check the helper is actually running: `pgrep -f auto-submit/build/auto-submit`. If it's **not** running, their message came through by tapping Return or via Voice Control — *not* the earbud tap. Say that plainly and offer to start the helper; don't let them believe the tap is wired when it isn't.

**1.5 Make sure I can hear you — before the conversation.** Opening the Voice Control settings is **not** the same as it being ON (the toggle may still be off — this is the #1 thing that silently breaks a session). So before you give the spoken brief and wait for a reply, do one plain check: *"Turn Voice Control on in the window I opened, then say 'open Notes' — tell me when it opens."* Wait until that works before starting the back-and-forth. If you speak and hear nothing back, **assume Voice Control is still off and ask them to turn it on** — don't keep talking into silence. (If the user is clearly typing replies at the desk, you can skip this.)

**2. Brief (vault-first, synthesized).** Offer a short spoken menu of what's waiting (briefs, todos, drafts). Anything from email or other apps should be brought into the vault **before** the walk so it's there in a dead zone — see `references/getting-info-in.md` (copy/paste-and-ingest is the reliable default; live mailbox MCP only when the *right* account is actually connected — verify it). Read the vault-first schedule/task-fit note named in `config.yaml` (`schedule_note`) before considering anything else — if it's empty, just proceed; do **not** reach for a calendar API (v1 has none). Never read a note raw — pipe it through `auditory-view` first, then summarize what comes back:

```
bash ${CLAUDE_SKILL_DIR}/scripts/auditory-view/run.sh < <vault>/Path/To/Note.md
```

**3. Speak it.** TTS in v1 is the runtime's own / on-device voice (`tts: runtime` in config). Pacing is **behavioral** — you shorten or re-render on "faster/shorter", rather than relying on engine tags. The `speak()` path is a seam: a richer Gemini-3.1-Flash-TTS engine is a Phase-2 swap that needs no change to this contract.

**4. Interrupt.** v1 interrupt is **tactile** — a phone or Bluetooth-device tap stops playback (see `references/transport-default.md` for wiring). Honor "skip"/"next" promptly. Vocal barge-in (talking over the assistant) is *not* a v1 requirement.

**5. Draft, don't send.** When the user dictates an email or note: draft it as markdown, **read it back** (synthesized), revise on spoken feedback, then write it to the vault **inbox** (`inbox` in config, default `Inbox/`) with `status: draft` frontmatter. It is **never sent** — sending is the user's job at the desk. Then commit it safely:

```
bash ${CLAUDE_SKILL_DIR}/scripts/git-safe-commit.sh \
  --vault <vault> -m "draft: reply to Acme" Inbox/2026-06-18-acme-reply.md
```

This is the **only** sanctioned git write path (invariant #2): it commits to the session branch from `state.json` (never `main`), refuses to switch onto a dirty tree, never force-pushes, and pushes only the session branch (per `push_policy`). Reconcile/merge happens at the keyboard.

**Never-send boundary (invariant #1):** no script in this skill sends anything outward. The inbox is a *drafts* location; there is no outbox. If outward actions are ever added, they must live in a separate directory and require an explicit confirmation phrase — never a casual "yeah."

**6. Capture before network (invariant #3).** Whenever the user dictates something — a thought, a draft, a transcription job — persist it **first** with `offline-queue enqueue`, *before* any model/network call. Then process it. If you're in a dead zone, it's already safe on disk and flushes when you reconnect.

```
# the moment the user speaks something worth keeping:
bash ${CLAUDE_SKILL_DIR}/scripts/offline-queue.sh enqueue --vault <vault> --kind draft --text "..."
# back online — drain FIFO, process each, mark done:
bash ${CLAUDE_SKILL_DIR}/scripts/offline-queue.sh flush --vault <vault>   # JSON array; text is base64 in text_b64
bash ${CLAUDE_SKILL_DIR}/scripts/offline-queue.sh done  --vault <vault> --id <id>
```

Non-urgent transcription jobs (`--kind transcription --urgency low`) can route to local Whisper later (Epic 5); urgent ones escalate. Same queue.

**7. Traffic mode (FR-H1).** If the user says they're near traffic (or "traffic mode"), **suppress dialogue** — drop to capture-only + minimal confirmations, no briefings or back-and-forth. Speaking is more cognitively demanding than listening; this protects attention near roads. Resume on "clear" / "resume."

## Safety invariants (never violate)

1. **Never-send.** No script sends anything outward; drafts only. Inbox is a separate directory from any outbox.
2. **Git single-funnel.** All commits go through `scripts/git-safe-commit.sh` — session branch only, never `main`, never `--force`, refuse-merge-on-dirty.
3. **Capture-before-network.** User words/drafts hit local disk via `offline-queue` *before* any network call.
4. **Gitignore state.** `.walk-and-talk/` (state, queue, audio, keys) is never committed.
5. **Synthesize, never recite.** Vault content for the ear passes through `auditory-view`.
6. **Local-model gate.** No agentic/git step routes to a local model unless it passed the rung probes (see the `integrating-local-models` skill). Default cloud.
7. **Resource discipline.** Don't co-resident a heavy LLM + STT + TTS on one device; prefer small Whisper; split capture(phone)/orchestration(desktop).

## Scripts

- `scripts/setup-advisor.sh` — situation detection + recommendation + config writer (read-only unless `--write-config`).
- `scripts/session.sh` — session + mode state (`state.json`): start / stop / status / mode. **`stop` tears down** background helpers (auto-submit, ambient-watch — releases earbud/media controls + mic) and clears state; **`start` recovers** strays from an abruptly-ended prior session.
- `scripts/ambient-check.sh` — "tell me what I can't see": detects active work on a project (recent edits, running agents, browser/build automation, behind-remote) before you engage, so you don't collide. Exit 10 = busy.
- `scripts/ambient-watch.sh` — watches a busy project and **says** when it goes quiet (safe to engage).
- `scripts/prime.sh` — gathers project context (key docs, recent notes, git, freshness vs the last primer) for the assistant to distill into `.walk-and-talk/primer.md`; later runs surface what changed for an incremental refresh.
- `scripts/audio-check.sh` — (macOS) diagnose/fix the voice loop: earbud HFP trap, Voice Control mic/submit traps; `--fix` switches mic to built-in + opens the VC pane.
- `scripts/vc-listen.sh` — (macOS) tie Voice Control listening to mode (active→on, passive/quiet→off); surfaces the "Start/Stop listening" command. Called by `session.sh` on mode change.
- `scripts/auto-submit/` — (macOS, Apple-native Swift) fully hands-free submit *option*: `--button` (earbud play-pause tap → Return) and/or `--voice` (speak-then-pause → Return). Compiled by `run.sh`; needs Accessibility (+ Microphone for `--voice`).
- `scripts/speak.sh` — on-device TTS (BT tail-clip fix, transcript, `--repeat`, `WAT_SILENT` for text-only when headphones are off). Auto-forwards each reply to the phone via `tg-send.sh` when a Telegram bridge is configured.
- `scripts/tg-send.sh` — phone audio OUTPUT bridge: renders a reply to speech and posts it as a Telegram voice note that auto-plays on Android + iOS through the phone's earbuds (macOS `say` only reaches the local Mac, never the phone over SSH). `--get-chat-id` / `--test`; token+chat live in the gitignored `.walk-and-talk/telegram.env`. See `references/transport-default.md`.
- `scripts/phone-link.sh` — guides the context-continuing connection (Termius+Tailscale+tmux+Mosh): checks Mac readiness and prints the single next plain step, then emits the connection facts + phone-side steps. Read-only; the assistant runs the installs / `tailscale up` and relays the rest plainly. This is the INPUT/context path — distinct from `tg-send.sh`'s audio-out.
- `scripts/auditory-view/` — markdown→ear sanitizer (`run.sh` → `sanitize.py`, stdlib-only).
- `scripts/git-safe-commit.sh` — session-branch isolation, refuse-on-dirty, no force-push.
- `scripts/offline-queue.sh` — enqueue-before-network / flush / done / status.
- `scripts/engine-route.sh` — per-step cloud|local resolver, rung-gated, off by default.

## Local models (gradual, planned, OFF by default)

Local models are opt-in **per step**, never a global switch. Resolve a step's engine with `engine-route.sh --vault <vault> --step <step>` — with no config it returns `cloud` for everything. Opt a step in via the `engine` map in `config.yaml`. Completion-shaped steps (`auditory_view`, `draft`, `transcription`, `summarize`) are rung-2-safe; **agentic steps (orchestration, git, vault-nav) are refused on local until proven** with `--verify --model <m>`, which runs the rung probe from the `integrating-local-models` skill and records the result. Non-urgent transcription routes to local Whisper; urgent escalates to cloud. Mind resource discipline — don't co-resident a heavy LLM + STT + TTS; prefer small Whisper; split capture(phone)/orchestration(desktop). Full rationale: PRD §12 + the `integrating-local-models` skill.

## Priming — first run vs. primed (start informed)

The skill works in two phases (this is the model the user expects):

- **First run on a project (gain context):** after `setup-advisor`, run **`prime.sh --vault <vault>`** and **distill** the gather into a *concise* `<vault>/.walk-and-talk/primer.md` — frontmatter (`as_of`, `as_of_sha`) + short sections: *What this project is · Current focus / where you left off · Open / in-flight · Recent changes.* Keep it small; it loads every session.
- **Later runs (primed):** load `primer.md`, run `prime.sh --json` for freshness; if there are new commits/notes, **refresh the affected sections incrementally** (don't re-read everything) and bump `as_of_sha`. Then greet with the primer by voice — "last time you were on X; since then Y shipped; Z is open." The primer is per-vault and gitignored (never synced).

**Full session sequence:** `setup-advisor` (first time) → **`prime`** → `ambient-check` → `session.sh start` → brief.

## Ambient awareness — tell the user what they can't see

A core vocal-OS principle: eyes-free, the user can't glance at the screen to notice that **another session/agent is already working on this project**, a build or browser automation is running, or the checkout is **behind the remote** — and if they just dictate and submit, they may collide with or overwrite that work. So **before engaging a project (and before submitting changes), run `ambient-check.sh` and surface anything active** — by voice. If it's busy, say so and hold off; offer `ambient-watch.sh` to be told when it's safe. Pull latest when behind. Don't let the user collide with work they couldn't see.

**If another session already owns a project, don't compete for it.** When a parallel session has created the note or asset folder (watch for name variants — the user says "water globes," the other session made "Pet Water Globes"), do **not** create a second note or write into its folder. Hold your vault writes, say which session owns it, and reconcile once it's quiet. Two sessions, one vault: ownership is first-writer.

## Ending a session — clean exit (planned or abrupt)

End with **`session.sh stop`** — it stops the background helpers (so the earbud tap, media controls, mic, and now-playing claim are released), clears voice-mode state, and notes any still-queued captures (which are safe on disk). If a session ends **abruptly** (disconnect/crash), the next `session.sh start` detects the unclean state and clears strays, and the offline queue means nothing dictated is lost. **Voice Control gotcha:** "Stop listening" only *pauses* it — the mic stays claimed (the orange dot persists). To fully release the mic, **turn Voice Control OFF** in System Settings → Accessibility → Voice Control.

Planning artifacts (PRD, architecture, epics) live under `_bmad-output/planning-artifacts/prds/prd-walk-and-talk-2026-06-17/`.
