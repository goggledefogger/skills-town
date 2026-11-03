---
name: scrappy-video-understanding
description: Understand any video or link (YouTube, Google Drive, Twitter/X, TikTok, Loom, Vimeo, direct URLs, or local files) using scrappy, progressive passes: fast metadata probe, instant subtitle harvesting, keyframe scene-change extraction, contact sheet storyboard generation, and audio speech transcription. Use when the user provides a video URL, drops a media file, or asks to understand/summarize/extract frames from a video.
---

# Scrappy Video Understanding

A versatile, progressive multi-pass video analyzer designed to make sense of any video or media link without brittle dependencies or heavy GPU infrastructure.

Built on [yt-dlp](https://github.com/yt-dlp/yt-dlp) (Unlicense) for streaming media and instant subtitle harvesting, [ffmpeg / ffprobe](https://ffmpeg.org) (LGPL/GPL) for frame grabbing and audio processing, and [whisper-ctranslate2](https://github.com/Softcatala/whisper-ctranslate2) (MIT) for optional local speech-to-text.

## Inputs Supported

1. **Remote URLs**:
   - YouTube (standard `watch?v=`, short links `youtu.be/`, Shorts `youtube.com/shorts/`)
   - Google Drive shared video links (`drive.google.com/file/d/...`, `drive.google.com/open?id=...`)
   - Twitter / X video posts
   - TikTok & Instagram Reels
   - Loom recordings & Vimeo
   - Direct HTTP/HTTPS video files (`.mp4`, `.webm`, `.mov`, `.m4v`, `.ts`)
2. **Local Media Files**:
   - Video containers: `.mp4`, `.mov`, `.mkv`, `.webm`, `.avi`, `.m4v`, `.ts`
   - Audio recordings: `.mp3`, `.m4a`, `.wav`, `.aac`, `.flac`, `.ogg`
   - Screen recordings & camera captures

## The Front-Door Intake Protocol (Primary Scenario)

When the user provides a video (YouTube link, Google Drive link, Twitter/X, TikTok, Loom, Vimeo, or local file), follow this 3-step conversational pattern:

### Step 1: Run Instant Local Reconnaissance (1-2s, 0 Video Bytes)
Run the leanest pass immediately:
```bash
python3 .agents/skills/scrappy-video-understanding/scrappy_video.py "<url_or_path>" --stage subs
```
This inspects the host hardware profile (Mac vs Raspberry Pi), extracts duration/codecs, and harvests subtitles/captions without downloading heavy video streams.

### Step 2: Present the Concise Assessment & Split Recommendation
Do not overwhelm the user with long text. Give a punchy, 3-bullet breakdown:
1. **What we discovered locally**: (Duration, resolution, subtitles harvested or missing, and whether the local host is a Mac or edge Raspberry Pi).
2. **Recommended Local vs Cloud Split**:
   - **Local Execution**: Probing, zero-download subtitle harvesting, audio extraction, and visual 4x3 contact sheet generation (drastically cuts token usage and bandwidth).
   - **Cloud AI (and which model)**:
     - **Claude 3.5 Sonnet / Opus**: If transcripts are present and the goal is analytical synthesis, architecture reasoning, code extraction, or editorial critique.
     - **Gemini 1.5 Pro / 2.0 Flash**: If the video is long (>30m) and needs native multimodal temporal grounding or direct video upload into its 1M-2M context window.
     - **100% Local**: If privacy or offline operation is required (using local Qwen2.5-VL 3B + local Whisper on Mac; guarded on Pi).
   - **Why**: Local extraction distills the video into high-signal artifacts (clean text + contact sheet) for free; Cloud AI performs deep synthesis without melting laptop memory or crashing a Raspberry Pi.

### Step 3: Ask Two Confirming Questions Before Saying Too Much
Before escalating to deep processing or heavy downloading, ask:
1. **Goal**: *"What's your primary goal with this video? (e.g. quick takeaway summary, timestamped chapter outline, exact code/slide transcription, or deep analytical critique?)"*
2. **Tools & Privacy**: *"Do you prefer keeping this 100% local, or would you like me to feed the distilled transcript and contact sheet to Cloud AI (Claude / Gemini) for synthesis?"*

## Progressive Scrappy Passes

The tool runs in progressive tiers from cheapest/fastest to deepest:

1. **Pass 1: Probe & Metadata**
   - Extracts title, duration, dimensions, framerate, video/audio codecs, and chapters.
   - Zero video downloaded if remote.

2. **Pass 2: Subtitle / Transcript Harvest**
   - **For YouTube videos**: First leverages the public `youtube-transcript` skill (`~/.claude/skills/youtube-transcript/run.sh`). Fetches full timestamped captions in milliseconds via `youtube-transcript-api`, with automatic server-side fallback (`youtube-transcript.ai`) if the host IP is datacenter-blocked. Zero video bytes downloaded.
   - **For other web URLs (Twitter/X, TikTok, Loom, Vimeo)**: Extracts existing manual subtitles or auto-generated captions via `yt-dlp --skip-download` in seconds with zero video download.
   - **For local files**: Extracts embedded subtitle streams (e.g. `0:s:0`) or detects companion `.vtt` / `.srt` files.
   - Converts WebVTT / SRT timestamps into clean, readable `[MM:SS]` timestamped blocks.

3. **Pass 3: Visual Keyframe Sampling & Contact Sheet**
   - **Scene Cut Detection**: Uses ffmpeg's `select='gt(scene,0.3)'` filter to grab keyframes at genuine scene transitions (slide changes, camera switches, interface shifts).
   - **Uniform Interval Fallback**: Samples evenly across the timeline if scene cuts are sparse (e.g. talking heads, static presentations).
   - **Contact Sheet (Storyboard Grid)**: Renders a single 4x3 tiled overview image (`contact_sheet.jpg`). This enables you or the user to visually inspect the entire video in a single glance with minimal token overhead.

4. **Pass 4: Audio Track Extraction & Speech Transcription**
   - Extracts 16kHz mono audio (`audio_16k.mp3`) with ffmpeg.
   - If subtitles were unavailable and spoken speech is present, transcribes audio via local Whisper (`whisper-ctranslate2` / `mlx_whisper` / `whisper`) or multimodal audio ingestion.

5. **Pass 5: Agent Synthesis & Delivery**
   - Presents an executive summary of what happened.
   - Links key chapters and timestamps.
   - Displays the contact sheet in an `images` fence.
   - Pulls out key quotes, action items, or code snippets shown on screen.

## Resourcefulness First: Leanest Pass First

An important core value throughout is being resourceful and efficient: try things quickly and minimally first to see what is available and what works, before escalating compute or downloading heavy files.

- **Start minimal (`--stage subs` or `--stage quick`)**:
  - For web links (YouTube, Loom, etc.), harvesting subtitles takes 1-2 seconds and 0 bytes of video download. If the spoken transcript answers the user's question, stop there!
  - If visual context is needed, the `quick` pass samples a low-resolution stream into a single 4x3 contact sheet (`contact_sheet.jpg`). One glance usually answers what was shown.
- **Escalate only on demand (`--stage full`)**:
  - Run full scene-cut frame extraction or local Whisper audio transcription only when deep slide OCR, specific frame crops, or uncaptioned local media require it.

## How to Run

Before running for the first time, check system dependencies:
```bash
python3 .agents/skills/scrappy-video-understanding/scrappy_video.py --check
```

Progressive execution:
```bash
# 1. Fastest: probe metadata and chapters only (<1s, 0 bytes video download)
python3 .agents/skills/scrappy-video-understanding/scrappy_video.py "<url_or_path>" --stage probe

# 2. Lean transcript: probe + instant subtitle harvest (zero video download)
python3 .agents/skills/scrappy-video-understanding/scrappy_video.py "<url_or_path>" --stage subs

# 3. Quick visual: probe + subs + low-res 4x3 contact sheet (default)
python3 .agents/skills/scrappy-video-understanding/scrappy_video.py "<url_or_path>" --quick

# 4. Full deep pass: scene cuts + keyframes + audio extraction
python3 .agents/skills/scrappy-video-understanding/scrappy_video.py "<url_or_path>" --full
```

Options:
- `--stage <probe|subs|quick|full>`: Progressive execution stage (default `quick`).
- `--quick`: Shorthand for `--stage quick`.
- `--full`: Shorthand for `--stage full`.
- `--profile`: Assess current host hardware (RAM, arch, edge/Pi tier) and print capability matrix.
- `--tools`: Browse the open tools catalog, showing host install status and install instructions.
- `--register-tool <name>`: Register a new open tool in the learning registry (`custom_tools.json`).
- `--detector <auto|ffmpeg|scenedetect>`: Scene cut detection engine.
- `--max-frames <N>`: Maximum keyframes to retain in full pass (default 16).
- `--check`: Run dependency health check and print installation instructions if anything is missing.
- `--selftest`: Run hermetic parser test suite.

## Running on Constrained Devices (Raspberry Pi & Edge SBCs)

When running on an edge device like Sheila's Raspberry Pi (or any machine with $\le$ 4GB RAM), the skill automatically recognizes the `constrained` profile and enforces lean edge guards:

- **What an Edge Device / Pi CAN Do Fast**:
  1. **Metadata Probing**: Instant container and codec analysis via `ffprobe` (<50ms).
  2. **Subtitle & Transcript Harvesting**: Zero-byte video downloads using `youtube-transcript` or `yt-dlp --skip-download` (<2s, minimal RAM).
  3. **Low-Overhead Keyframes**: Native FFmpeg extracts downscaled keyframes (`scale=480:-1`) using `-skip_frame nokey` to avoid CPU thermal throttling and SD card wear.
  4. **Single-Glance Contact Sheet**: Generates a 4x3 visual grid scaled to 320px width (~150KB image).
  5. **Audio Track Extraction**: Extracts 16kHz mono audio (`audio_16k.mp3`) with stream filtering.
  6. **Quantized Speech-to-Text**: `whisper.cpp` using the quantized `tiny` or `base` model (<200MB RAM, optimized via ARM NEON instructions).

- **What an Edge Device / Pi MUST NOT Do (Automatic Edge Guards)**:
  1. **Heavy PyTorch / GPU Stacks**: PySceneDetect or heavy YOLO models are guarded; native FFmpeg is used instead.
  2. **Local Vision-Language Models (>2B)**: Attempting to run 7B/11B VLMs on a Pi causes immediate out-of-memory swap death and system freezes.
  3. **High-Resolution Transcoding**: Video downloads and processing are capped at 480p maximum.

- **Upstream Delegation**:
  When a user on a Raspberry Pi asks for deep visual understanding or heavy transcription, the edge node performs the lightweight passes (probe, subtitles, audio extraction, contact sheet), and hands the heavy inference pass to a stronger machine on the same network.

## Local Model Directives (From `integrating-local-models`)

When feeding extracted frames or transcripts into local models, always observe these four empirically measured rules:

1. **Downscale before you caption**: VLMs tile images into vision tokens at native resolution. Full-res photos blow the context window and trigger silent truncation. Always downscale keyframes to $\le$ 768px on the longest edge (or 480px on a Pi) before passing to any vision model.
2. **Turn thinking OFF for perception**: Captioning an image, reading a slide, or identifying a scene are look-and-say tasks. Reasoning models (e.g. Qwen 3.x, Gemma 4) burn hundreds of tokens in `<think>` tags without improving visual accuracy, causing timeouts and empty answers. Always pass `chat_template_kwargs: {"enable_thinking": false}` or `--reasoning off`.
3. **Build facts in code first, let model phrase**: Extract durations, chapters, OCR text, and transcripts in deterministic Python code first. Present those concrete facts to the model rather than expecting an LLM to reliably count seconds or read timestamps from raw unparsed blobs.
4. **Memory guard scales with model**: Never use a flat memory headroom. Check actual model weight size + 1GB context buffer before launching local inference.

## Predefined & Learning Open Tools Registry

The skill leverages an open-source tool registry (`open_tools.json`), organized by capability. It detects what is already installed on the member's machine, falls back gracefully, and expands as new open tools are discovered:

- **Ingestion & Subtitles**: `youtube-transcript` (Public skill, direct API + hosted fallback, MIT), `yt-dlp` (Unlicense), `streamlink` (BSD-2-Clause), `curl`
- **Probing & Metadata**: `ffprobe` (LGPL/GPL), `mediainfo` (BSD-2-Clause)
- **Speech-to-Text & Captions**: `whisper-ctranslate2` (MIT), `mlx-whisper` (Apple Silicon MLX, MIT), `whisper.cpp` (Metal, MIT)
- **Scene Cut Detection**: `ffmpeg` (gt(scene,0.3)), `scenedetect` (PySceneDetect, BSD-3-Clause)
- **Storyboards & Contact Sheets**: `ffmpeg` (tile filter), `vcsi` (MIT), `imagemagick` (montage, Apache-2.0)
- **Audio Manipulation & Filtering**: `ffmpeg`, `sox` (GPL), `auto-editor` (MIT)
- **Speaker Diarization**: `whisperx` (BSD-2-Clause), `pyannote.audio` (MIT)
- **Visual OCR & Slide Extraction**: `tesseract` (Apache-2.0), macOS Vision framework
- **Local Vision Models**: `qwen2.5-vl` / `qwen3-vl` via Ollama (Apache-2.0)
- **Object Detection & Video Tracking**: `ultralytics` (YOLOv8/v11/v12, AGPL-3.0)
- **Video Rendering & Captions**: `hyperframes` (HeyGen, Apache-2.0)

To check what tools are installed right now:
```bash
python3 .agents/skills/scrappy-video-understanding/scrappy_video.py --tools
```

To register a newly discovered open tool (learned permanently into `custom_tools.json`):
```bash
python3 .agents/skills/scrappy-video-understanding/scrappy_video.py --register-tool "toolname" --bin "toolbin" --cat "ocr" --desc "Description" --install "brew install tool" --url "https://..."
```

## What to Show the User

1. **Executive Summary**: 2-3 sentences on what the video covers, the author/speaker, and core thesis.
2. **Visual Contact Sheet**:
   ```images
   .scratch/video_understanding/<slug>/contact_sheet.jpg
   ```
3. **Timeline & Chapters**: Bulleted list with `[MM:SS]` timestamps for key topic shifts.
4. **Key Quotes / Transcripts**: Exact quotes where actionable advice, numbers, or decisions were made.
5. **Path to Artifacts**: Point to the generated `report.md`, `summary.json`, and extracted frames directory.
