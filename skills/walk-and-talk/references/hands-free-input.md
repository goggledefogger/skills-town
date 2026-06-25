# Hands-free input & output (macOS)

The loop is **turn-based**: the assistant speaks a reply only when your message is actually **submitted**. So the two things to get right are getting your voice *out of* the Mac (audio you can hear) and *into* the loop (text that gets submitted). Everything here uses **only built-in / Apple-native tools** — no third-party installs.

> This file is the distilled result of a long live dogfooding session. It documents what **works** and explicitly flags the dead-ends so nobody re-tries them.

## Setup (once)

1. **Fix the mic + audio routing:** `bash scripts/audio-check.sh --fix`. Bluetooth earbuds used as *both* mic and output drop into low-quality HFP mode, and Voice Control may hear nothing. `--fix` sets **input = built-in mic** (so earbuds stay output-only at full quality, and voice input keeps working even if earbuds disconnect) and opens the Voice Control pane.
2. **Turn on Voice Control** (System Settings → Accessibility → **Voice Control** — *not* plain Dictation; only Voice Control runs commands).
3. **Set Voice Control's OWN microphone to the built-in mic, not "Automatic."** This is the trap that silently breaks everything: VC's mic picker defaults to "Automatic," which can latch onto a dead aggregate device and hear nothing. Pick "MacBook … Microphone" explicitly. *Test:* say **"open Notes"** — if Notes opens, VC hears you.

## Output — speak via `speak.sh`

Speak replies with **`scripts/speak.sh "..."`** (wraps `say`). Why not raw `say`:
- **Bluetooth clips the tail** — `speak.sh` appends `[[slnc 700]]` trailing silence so the last word survives (confirmed). Tunable: `WAT_SPEAK_TAIL_MS` (device-dependent), `WAT_SPEAK_RATE` (185 wpm), `WAT_SPEAK_LEAD_MS`.
- **See + repeat** — it prints the text and logs a transcript to `.walk-and-talk/transcripts/` (set `WAT_STATE_DIR=<vault>/.walk-and-talk`); `speak.sh --repeat` re-speaks the last line.
- **`WAT_SILENT=1`** — text only, no audio (e.g. headphones disconnected — don't blast the laptop speakers). The text is still printed/logged.

The assistant must **also restate spoken text in its visible reply** — the client can collapse tool output, so the words must live in the message, and a missed word is always readable.

## Submitting — how your message actually gets sent

| Option | Hands-free? | Setup |
|---|---|---|
| **Tap the Return key** (default, simplest) | one tap | none |
| **`scripts/auto-submit` → `--button`** | yes | grant Accessibility once |
| **`scripts/auto-submit` → `--voice`** | yes | grant Accessibility + Microphone |

**Dead-ends — do NOT retry these (all ruled out live on current macOS):**
- A VC custom command "Press Keyboard Shortcut" → Return **can't capture Return** (the recorder won't bind it).
- **"new line"** only inserts a line break; it does *not* press Enter to submit.
- There is **no built-in "Press Return" voice command** (search VC Commands for "return" → nothing).
- **Shortcuts is sandboxed from sending keystrokes** ("Shortcuts is not allowed to send keystrokes"), and the Automator route is a separate app and was dropped from VC's current "Perform" menu.

That's *why* the auto-submit helper exists: a tiny Apple-native program that presses Return for you.

## The auto-submit helper (`scripts/auto-submit/`) — fully hands-free OPTION

Apple-native (Swift + AVFoundation + CoreGraphics, compiled with `swiftc` — no third-party). It only ever presses **Return** (key code 36). It's an **option**, not the default.

```
bash scripts/auto-submit/run.sh            # both modes
bash scripts/auto-submit/run.sh --button   # earbud-tap only
bash scripts/auto-submit/run.sh --voice --hangover-ms 1800
```

- **`--button`** (confirmed working) — a **tap on your Bluetooth earbuds submits.** Bluetooth taps don't arrive as keyboard events (a CoreGraphics event tap can't see them — they go through Apple's *MediaRemote* to whatever app is "now playing"), so the helper **registers itself as the now-playing app** (MediaPlayer framework: `MPRemoteCommandCenter` + a silent audio loop) and handles the earbud play-pause as a togglePlayPause → presses Return. **Tradeoff:** while it runs it owns the media controls — your earbud tap submits to walk-and-talk, *not* YouTube/Music. Intended for a focused session; stop it (Ctrl-C) to give media control back.
- **`--voice`** — presses Return after you speak then go quiet for `--hangover-ms`. **Caveat:** Voice Control types with lag, so `--hangover-ms` (default 1500) must exceed that lag or it submits early. Tunables: `--threshold-db -40`, `--min-speech-ms 400`, `--cooldown-ms 800`.
- **Permissions:** **Accessibility** (to press Return) and, for `--voice`, **Microphone**. It's **one grant to the app that launches the helper** (your terminal/IDE — e.g. Antigravity, Terminal, iTerm), *not* per-app: that single grant lets it press Return into whatever app you're focused on. Run it from a stable launcher so you grant once.

## Listening on/off — tied to modes

`scripts/vc-listen.sh` + `session.sh` map **active → listening on**, **passive/quiet → off** (on and kept on for work; off to zone out). The reliable control is the spoken **"Start listening" / "Stop listening"**; a clean programmatic toggle is part of the planned voice loop.

## Device disconnect — handled

- **Voice input is unaffected** by earbuds disconnecting, because the mic is the built-in one (that's why `--fix` sets it there).
- **Output** auto-falls-back to the laptop speakers; set **`WAT_SILENT=1`** for text-only so nothing blasts. `audio-check.sh` reports the current input/output devices.
- **`auto-submit --button`** simply idles with no Bluetooth device connected (no events, no crash); `--voice` keeps working on the built-in mic.

## Roadmap / still planned
- A reliable programmatic VC listen-toggle, and the through-the-Bluetooth-mic mobility mode (HFP tradeoff), both part of the planned voice loop.
- Generating Voice Control `.voicecommands` for non-keystroke commands (mode switches) via import — note the keystroke sandbox means it can't be used for *submit*.

## If you hear/see nothing — quick checklist
1. Did the message actually **submit**? (Most common — tap Return, or use auto-submit.)
2. Is the Claude terminal **focused**? (Voice Control types into the frontmost window.)
3. Is **Voice Control** on (not Dictation), with its **own mic set to built-in** (not Automatic)?
4. No audio? Check output device (`audio-check.sh`) or `WAT_SILENT`.
