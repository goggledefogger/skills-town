# Transport default — talking to Claude Code on a walk

**The constraint:** Claude Code's native `/voice` dictation needs local microphone access, so it **does not work over SSH or Claude Code web** — and the official Remote Control feature is text-only (no voice input). So a walk-time session can't use built-in `/voice`. You assemble a transport.

## Recommended default: Termius + Tailscale + tmux + Mosh

The tested default. Drives a real Claude Code session on your own always-on machine, from your phone, with the vault repo and git intact.

- **Tailscale** — a private network between phone and desktop; no port-forwarding, no public exposure.
- **tmux** — session persistence on the desktop: the Claude Code session survives disconnects.
- **Mosh** — connection persistence: survives phone sleep and Wi‑Fi↔cellular handoff (plain SSH/TCP drops on both). This is the piece that makes it usable on a moving walk.
- **Termius** (or Blink) — the phone terminal; use its keyboard mic / phone-OS dictation for input, since native `/voice` is unavailable here.

Topology: **capture/dictation on the phone → desktop runs the orchestration** (and any heavy local model). Don't stack a heavy LLM + STT + TTS on one machine.

## Hearing replies on the phone (the output half)

The transport above carries your *input* — you dictate in the terminal. It does **not** carry the assistant's voice back: `speak.sh` uses macOS `say`, which plays on the **Mac's own speakers**, so on a walk that audio never reaches you. This is the half most setups miss.

**Solution: the Telegram voice bridge (`scripts/tg-send.sh`).** The Mac renders each reply to speech, encodes it to OPUS/OGG, and posts it as a Telegram **voice note**. The phone auto-plays it through whatever earbuds are paired to the *phone* — **identical on Android and iOS**, no screen reader, near hands-free. `speak.sh` calls it automatically when a bridge is configured. One-time setup (a @BotFather token + your chat id) lives in the gitignored `<vault>/.walk-and-talk/telegram.env`; run `tg-send.sh --get-chat-id`, then `--test`.

Two apps on the phone for now: the terminal to dictate in, Telegram to hear back. Fully-Telegram *input* (send a voice note → transcribe → feed the session) is a clean phase-2; the output gap was the real blocker.

Lower-tech fallback (zero setup): the phone's own screen-reader TTS reading the terminal — **Select to Speak** on Android, **Speak Screen** on iOS. It works, but reads terminal chrome and isn't automatic — use it only to smoke-test the loop.

### First quick win + playback

Once a test voice note reaches the phone, give the user the quick win — don't open with navigation. If they want earbuds (a stored per-user preference; ask once, some care and some don't), prompt them to pop one in now. Then, plainly: tap the first voice note; after that Telegram voice notes **auto-play one after another** as replies arrive, routed to the earbud, with the earbud button as play/pause. Re-hearing an older note is the rough edge — for now "repeat" re-sends the last line (`speak.sh --repeat` also pushes to the phone); proper back/skip is a later refinement. Early on the entire win is: you talk, voice notes answer in your ear.

## Alternatives the advisor may suggest

- **Moshi** — native iOS client with SSH/Mosh+tmux and on-device dictation (best privacy); the closest single-app fit.
- **Claude mobile app voice mode** — great for *briefing-only* (speech↔speech), but it talks to the assistant, not your Claude Code session, so it can't drive the vault repo or commit.
- **Telegram/Discord bridges** — voice-note → transcription → local agent; text-centric.

## Re-verify monthly

If Anthropic ships voice input for Remote Control, switch the default to it. Track the open requests (Claude Code issues #29399 / #25115).
