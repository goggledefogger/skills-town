---
name: walkthrough-video
allowed-tools: [Read, Write, Edit, Bash]
description: Make a captioned how-to or walkthrough video of any web app from one JSON script, by recording its real screens in headless Chrome and rendering title cards and captions around them with HyperFrames. Re-runnable, so a redesign or a new step is one command away from a fresh video. Use when someone asks for a how-to video, walkthrough, demo video, screen recording with captions, or "a video of how the app works", or wants to remake one after the app changed. Do NOT use for a short PR demo GIF (that's ce-demo-reel) or a motion-graphics film with no real screens (that's hyperframes).
---

# walkthrough-video

One file, `walkthrough.json`, describes the video: how to start the app, the scenes, the clicks and typing in each, and the caption that goes with each step. `scripts/walkthrough.ts` plays it in headless Chrome, records each scene as a clip, and writes a HyperFrames project around the clips; `--render` turns that into an MP4. Captions are timed from the recording itself, so they stay in sync when the app gets faster, slower or restyled.

Needs Node 22+, ffmpeg and Chrome (or `CHROME=<path>`). HyperFrames runs through `npx` only for `--render`; nothing installs into the app.

Before the first recording, run `node <this skill>/scripts/walkthrough.ts --check`. It names anything missing and how to add it; pass that on in one line and offer to run the install. If Node itself errors on the `.ts` file, it is older than 22.18: say so and point at nodejs.org.

## Start or continue

Work in the project this chat is about, or the app the user names. If the chat is not already inside that project's checkout, find it before anything else: the checkout the chat's own context names, or, from an app's name, its `owner/repo` (the user's notes or project registry usually name it) and then a repo map the host keeps (Astrolabe: `node <dashboard>/premium/repo-map.js where owner/repo`). Do not sweep a whole home or source folder for it; ask once where the checkout is, then `cd` there for the rest of the run. Then look for an existing script: `git ls-files | grep walkthrough.json`, plus any tracker or notes that mention the walkthrough video (`git grep -n -i "walkthrough video"`).

- **Found one:** continue it. Read the JSON and the tracker lines, say in one line which scenes exist and what is next, then add or fix scenes. A re-run after the app changed needs no edits unless a selector broke.
- **None yet:** start one. Read how the app starts and its stable selectors, propose the scenes in plain words (one idea each, sample data only), and on a yes write `docs/walkthrough/walkthrough.json`, a short README beside it, and `video/` in its `.gitignore`. Record scene 1 and show it before writing the rest.
- **Several apps in one repo:** ask which one, once.

When a scene is done, tick it wherever the project tracks its work, so the next chat knows where to pick up.

## Run it

```bash
node <this skill>/scripts/walkthrough.ts path/to/walkthrough.json --render
node <this skill>/scripts/walkthrough.ts path/to/walkthrough.json --scenes 3 --render   # re-record one scene, keep the rest
node <this skill>/scripts/walkthrough.ts --selftest
```

Output goes to `video/` beside the JSON: `assets/scene-N.mp4` (raw clips), `compositions/` and `index.html` (the HyperFrames project), `renders/walkthrough.mp4`. Put `video/` in `.gitignore`; commit only the JSON.

To tweak the look of the cards and captions by hand, `npx hyperframes preview` inside `video/` opens the editor; a re-run overwrites `video/`, so lasting changes go in the JSON's `theme` or in the script.

## Writing the script

Read the app first: its README, how it starts, and which stable selectors exist (`data-test` hooks, ids, roles). Selectors built on wording break when copy changes. Then plan one idea per scene, captions in plain words.

```json
{
  "title": "My app, how it works",
  "url": "http://127.0.0.1:{port}/",
  "start": { "command": "npm start -- --port {port}", "cwd": "." },
  "viewport": [1440, 900],
  "theme": { "ground": "#1d2330", "ink": "#f4f1ea", "accent": "#e8583c", "font": "Inter, sans-serif" },
  "scenes": [
    {
      "title": "Sign in",
      "before": [{ "goto": "/login" }],
      "steps": [
        { "caption": "Type your email." },
        { "type": ["#email", "sam@example.com"] },
        { "click": "[data-test=submit]" },
        { "wait": 1500 }
      ]
    }
  ]
}
```

- `start` is optional: leave it out and point `url` at an app already running. `{port}` becomes a free port; `cwd` is relative to the JSON.
- Scenes run in one page, in order, each continuing from where the last ended. `reload: true` starts a scene fresh; `before` runs steps off camera.
- `caption` marks the moment its text appears; it stays until the next caption or the end of the scene. Put it just before the action it explains, and follow the action with a `wait` long enough to read it (about 1 s per 3 words).

Steps:

| Step | Does |
| --- | --- |
| `{ "caption": "text" }` | Caption from this moment |
| `{ "click": sel }` | Glide the pointer there and click |
| `{ "point": sel }` | Scroll to it and glide the pointer there |
| `{ "type": [sel, text], "delay": 110 }` | Click, then type one letter at a time, replacing what was there (`"append": true` adds to it); fires input and change |
| `{ "clear": sel }` | Empty an input |
| `{ "select": [sel, value] }` | Pick an option in a `<select>` |
| `{ "upload": [sel, path] }` | Put a file in a file input (path relative to the JSON) |
| `{ "goto": "/path" }` or `{ "goto": "#hash" }` | Navigate |
| `{ "wait": ms }` / `{ "waitFor": "js expression", "timeout": ms }` | Hold, or wait for the page |
| `{ "viewport": [390, 844], "mobile": true }` | Change screen size (phone clips are framed to fit) |
| `{ "media": "print" }` / `{ "media": "screen" }` | Show the print styles on screen |
| `{ "printPages": 2, "hold": 4000 }` | Print to PDF and show the first pages side by side, as they come out of the printer (repeating headers, page breaks). Needs `pdftoppm` (poppler) |
| `{ "eval": "js" }` | Anything else, run in the page |

## Before you hand it over

- Pull 2 or 3 stills from the render (`ffmpeg -ss 4 -i video/renders/walkthrough.mp4 -frames:v 1 still.jpg`) and look: captions readable, pointer on the right thing, nothing private on screen.
- Use sample or made-up data. A real customer's numbers in a video are a leak waiting to happen.
- If a step fails, the error names the selector or expression that timed out.
- If the run ends with "recorded with uncommitted changes", the video shows half-finished edits; say so, or commit first and re-run.
