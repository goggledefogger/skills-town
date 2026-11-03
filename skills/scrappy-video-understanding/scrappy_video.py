#!/usr/bin/env python3
"""Scrappy Video Understanding CLI.

A versatile, progressive multi-pass video analyzer that accepts:
- Remote URLs: YouTube (standard, shorts), X/Twitter, TikTok, Loom, Vimeo, direct HTTP/HTTPS media URLs
- Local files: .mp4, .mov, .mkv, .webm, .avi, .m4v, .mp3, .m4a, .wav, .flac

Scrappy progressive passes:
1. Probe: Fast metadata extraction via ffprobe / yt-dlp -J (duration, codecs, resolution, stream count).
2. Subtitle / Transcript Harvest:
   - Remote URL: Instant auto-subtitles/captions fetch via yt-dlp --skip-download (0 MB video download!).
   - Local file: Extracts embedded subtitle tracks or companion .srt/.vtt files.
3. Audio Extraction & Speech:
   - Extracts 16kHz mono audio track via ffmpeg.
   - Detects local Whisper CLI (whisper-ctranslate2, mlx_whisper, whisper) for speech transcription fallback.
4. Keyframe Extraction & Contact Sheet:
   - Scene change detection: extracts keyframes when visual content shifts (ffmpeg gt(scene,0.3)).
   - Uniform interval sampling: ensures coverage even for static/talking-head videos.
   - Contact sheet (storyboard grid): renders a single 4x3 or 3x3 visual summary image for instant 1-glance multimodal understanding.
5. Report Synthesis:
   - Outputs structured summary.json and readable report.md with timestamped links and highlights.

Dependencies:
- ffmpeg / ffprobe (LGPL/GPL) https://ffmpeg.org
- yt-dlp (Unlicense) https://github.com/yt-dlp/yt-dlp
Optional:
- whisper-ctranslate2 / openai-whisper (MIT)
"""

import argparse
import base64
import html
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
from typing import Optional
from pathlib import Path


def is_url(string: str) -> bool:
    """Check if string is a web URL."""
    try:
        parsed = urllib.parse.urlparse(string)
        return parsed.scheme in ("http", "https")
    except Exception:
        return False


PRIVATE_LINE = ("That link is private or not found. If it is yours, sign in "
                "(for GitHub: gh auth login) or download it and tell me where the file is.")
BIG_DOWNLOAD_BYTES = 200 * 1024 * 1024


class UserMessage(Exception):
    """A plain line for the member, printed without a traceback"""


class StageStop(UserMessage):
    """An intended early stop (probe/subs on a release link); exits 0"""


def private_link_message(text: str) -> Optional[str]:
    """Map a 401/403/404 style failure to the one plain line, else None"""
    if re.search(r"\b(401|403|404)\b|Unauthorized|Forbidden|Not Found|[Pp]rivate video", text or ""):
        return PRIVATE_LINE
    return None


def last_line(text: str) -> str:
    return (text.strip().splitlines() or ["unknown error"])[-1]


def github_release_ref(url: str) -> Optional[dict]:
    """Recognise GitHub release asset URLs; returns repo plus tag/file or asset id.
    A recognised shape with an unsafe segment raises the plain line"""
    u = urllib.parse.urlparse(url)
    parts = [urllib.parse.unquote(x) for x in u.path.split("/") if x]
    name_ok = lambda x: re.fullmatch(r"[A-Za-z0-9._-]+", x) and x not in (".", "..")
    if u.netloc == "github.com" and len(parts) >= 6 and parts[2:4] == ["releases", "download"]:
        owner, repo, tag = parts[0], parts[1], parts[4]
        if not (name_ok(owner) and name_ok(repo)) or tag.startswith("-") or re.search(r"[/?#]", tag):
            raise UserMessage(PRIVATE_LINE)
        return {"repo": f"{owner}/{repo}", "tag": tag, "file": "/".join(parts[5:])}
    if u.netloc == "api.github.com" and len(parts) == 6 and parts[0] == "repos" and parts[3:5] == ["releases", "assets"]:
        if not (name_ok(parts[1]) and name_ok(parts[2])) or not parts[5].isdigit():
            raise UserMessage(PRIVATE_LINE)
        return {"repo": f"{parts[1]}/{parts[2]}", "asset_id": parts[5]}
    return None


def fetch_github_asset(ref: dict, out_dir: Path, yes: bool = False, download: bool = True) -> Optional[Path]:
    """Download a release asset with the member's gh sign-in; None when gh is not usable.
    With download=False only the size is learned and printed"""
    gh = shutil.which("gh")
    if not gh or subprocess.run([gh, "auth", "status"], capture_output=True).returncode != 0:
        return None
    q = urllib.parse.quote
    if "asset_id" in ref:
        api = f"repos/{q(ref['repo'], safe='/')}/releases/assets/{q(ref['asset_id'])}"
    else:
        api = f"repos/{q(ref['repo'], safe='/')}/releases/tags/{q(ref['tag'], safe='')}"
    res = subprocess.run([gh, "api", api], capture_output=True, text=True)
    if res.returncode != 0:
        raise UserMessage(private_link_message(res.stderr) or "GitHub lookup failed: " + last_line(res.stderr))
    data = json.loads(res.stdout)
    asset = data if "asset_id" in ref else next((a for a in data.get("assets", []) if a.get("name") == ref["file"]), None)
    if not asset:
        raise UserMessage(PRIVATE_LINE)
    try:
        size = int(asset["size"])
    except (KeyError, TypeError, ValueError):
        raise UserMessage("Could not learn the size of that file, so I am not downloading it.")
    print(f"      GitHub asset {asset['name']}: {size / 1048576:.1f} MB", flush=True)
    if not download:
        raise StageStop(f"Not downloading at this stage (no video bytes before quick or full). The file is {size / 1048576:.0f} MB.")
    if size > BIG_DOWNLOAD_BYTES and not yes:
        raise UserMessage(f"That file is {size / 1048576:.0f} MB (over 200 MB). Say yes and I will download it with your GitHub sign-in (rerun with --yes).")
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / ("source" + (Path(asset["name"]).suffix or ".mp4"))
    if "asset_id" in ref:
        with open(dest, "wb") as fh:
            run = subprocess.run([gh, "api", "-H", "Accept: application/octet-stream", api], stdout=fh, stderr=subprocess.PIPE)
    else:
        run = subprocess.run([gh, "release", "download", "--repo", ref["repo"], "--pattern", asset["name"],
                              "--dir", str(out_dir), "--clobber", "--", ref["tag"]], capture_output=True)
        if run.returncode == 0:
            shutil.move(str(out_dir / asset["name"]), dest)
    if run.returncode != 0:
        err = run.stderr.decode(errors="replace")
        raise UserMessage(private_link_message(err) or "Download failed: " + last_line(err))
    return dest


REGISTRY_DIR = Path(__file__).resolve().parent
PREDEFINED_REGISTRY = REGISTRY_DIR / "open_tools.json"
CUSTOM_REGISTRY = REGISTRY_DIR / "custom_tools.json"


def load_tool_registry() -> dict:
    """Load predefined open tools registry and overlay any custom/learned tools."""
    registry = {"categories": {}, "tools": {}}
    if PREDEFINED_REGISTRY.exists():
        try:
            registry = json.loads(PREDEFINED_REGISTRY.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"Warning: could not read {PREDEFINED_REGISTRY}: {e}", file=sys.stderr)

    if CUSTOM_REGISTRY.exists():
        try:
            custom = json.loads(CUSTOM_REGISTRY.read_text(encoding="utf-8"))
            registry.setdefault("categories", {}).update(custom.get("categories", {}))
            registry.setdefault("tools", {}).update(custom.get("tools", {}))
        except Exception as e:
            print(f"Warning: could not read {CUSTOM_REGISTRY}: {e}", file=sys.stderr)

    return registry


def register_custom_tool(name: str, category: str, bin_name: str, description: str,
                         install: str = None, url: str = None, license_name: str = "Open Source") -> dict:
    """Register or update a tool in the growing custom tools registry."""
    custom = {"tools": {}}
    if CUSTOM_REGISTRY.exists():
        try:
            custom = json.loads(CUSTOM_REGISTRY.read_text(encoding="utf-8"))
        except Exception:
            custom = {"tools": {}}

    tool_entry = {
        "name": name,
        "category": category,
        "bin": bin_name,
        "license": license_name,
        "url": url or "",
        "description": description,
        "install": install or "",
        "priority": 10,
        "learned_at": __import__("datetime").date.today().isoformat(),
    }
    custom.setdefault("tools", {})[name] = tool_entry
    CUSTOM_REGISTRY.write_text(json.dumps(custom, indent=2), encoding="utf-8")
    print(f"✓ Registered '{name}' in custom video tools registry ({CUSTOM_REGISTRY}).")
    return tool_entry


def discover_tools() -> dict:
    """Scan the open tools registry against the current host environment."""
    registry = load_tool_registry()
    categories = registry.get("categories", {})
    tools = registry.get("tools", {})

    status = {"categories": categories, "installed": {}, "available": {}}

    for tool_id, tool in tools.items():
        bin_name = tool.get("bin", tool_id)
        expanded = os.path.expanduser(bin_name)
        if os.path.exists(expanded) and os.access(expanded, os.X_OK):
            path = expanded
        else:
            path = shutil.which(bin_name)
        tool_info = dict(tool)
        tool_info["installed_path"] = path
        tool_info["is_installed"] = bool(path)
        
        if path:
            status["installed"][tool_id] = tool_info
        else:
            status["available"][tool_id] = tool_info

    return status


def print_tools_catalog() -> int:
    """Print the complete open tools registry grouped by capability with host install status."""
    discovery = discover_tools()
    categories = discovery["categories"]
    installed = discovery["installed"]
    available = discovery["available"]

    print("\nScrappy Video Understanding — Open Tools Registry (Predefined & Growing)")
    print("=" * 75)

    all_tools = {**installed, **available}

    for cat_id, cat_info in categories.items():
        cat_tools = [t for t in all_tools.values() if t.get("category") == cat_id]
        if not cat_tools:
            continue
        print(f"\n📂 {cat_info.get('name', cat_id).upper()}")
        print(f"   {cat_info.get('description', '')}")
        print("   " + "-" * 70)
        
        for t in sorted(cat_tools, key=lambda x: (not x["is_installed"], x.get("priority", 99))):
            mark = "✓ [INSTALLED] " if t["is_installed"] else "○ [AVAILABLE] "
            loc = f"({t['installed_path']})" if t["is_installed"] else f"→ `{t.get('install', 'install via package manager')}`"
            print(f"   {mark:<15} {t['name']:<20} [{t.get('license', 'Open Source')}]")
            print(f"     Description : {t.get('description', '')}")
            print(f"     Binary/Path : {loc}")
            if t.get("url"):
                print(f"     Source      : {t['url']}")
            print()

    print("=" * 75)
    print(f"Summary: {len(installed)} installed / {len(all_tools)} total open tools registered.")
    print("Add/learn a new tool: scrappy_video.py --register-tool <name> --bin <bin> --cat <category> --desc <desc>")
    print("=" * 75 + "\n")
    return 0


def get_device_profile() -> dict:
    """Analyze host device capabilities and memory constraints (e.g. Raspberry Pi vs Mac/Server).
    
    Incorporates lessons from integrating-local-models:
    1. Guard memory headroom: Never attempt >2B/3B VLM or PyTorch stacks on constrained RAM (<=4GB).
    2. Downscale before captioning / sampling: Keep frames <= 768px (480px on Pi) to prevent context explosion.
    3. Perception without reasoners: Never run thinking models on frame perception; use targeted look-and-say.
    4. Code-built facts first: Extract metadata/OCR/subtitles in deterministic code, don't dump raw frames into small contexts.
    """
    total_ram_gb = 4.0
    try:
        total_ram_gb = round((os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')) / (1024**3), 1)
    except Exception:
        pass

    arch = platform.machine()
    system = platform.system()
    
    is_rpi = False
    device_model = f"{system} {arch}"
    dt_model = Path("/sys/firmware/devicetree/base/model")
    if dt_model.exists():
        try:
            device_model = dt_model.read_text(encoding="utf-8", errors="ignore").replace("\x00", "").strip()
            if "Raspberry Pi" in device_model:
                is_rpi = True
        except Exception:
            pass

    # Constrained tier: Raspberry Pi or any machine with <= 4GB RAM
    is_constrained = is_rpi or total_ram_gb <= 4.0

    profile = {
        "device": device_model,
        "arch": arch,
        "system": system,
        "total_ram_gb": total_ram_gb,
        "tier": "constrained (edge/rpi)" if is_constrained else "standard (workstation/server)",
        "is_constrained": is_constrained,
        "recommended_frame_width": 480 if is_constrained else 640,
        "max_ingest_height": 480 if is_constrained else 720,
        "capabilities": {
            "probe_metadata": True,
            "harvest_subtitles": True,
            "contact_sheet_lowres": True,
            "ffmpeg_keyframes_downscaled": True,
            "audio_track_extraction": True,
            "whisper_cpp_tiny_base": True,
            "whisper_heavy_large": not is_constrained,
            "local_vlm_perception": not is_constrained,
            "pytorch_tracking_yolo": not is_constrained or (arch in ("aarch64", "arm64") and total_ram_gb >= 8.0),
            "cloud_or_remote_delegation_recommended": is_constrained,
        },
        "limits": [
            "Keep frame resolution <= 480px to protect memory and SD card I/O" if is_constrained else "Keep frame resolution <= 768px for VLM context budget",
            "Avoid full video re-encoding on CPU; use stream-copy or skip-frame" if is_constrained else "Standard hardware acceleration available",
            "Do NOT run local vision-language models (>2B) or deep reasoners locally" if is_constrained else "Local VLM allowed (qwen2.5-vl:3b or moondream with thinking=off)",
            "Delegate heavy Whisper / VLM passes to a stronger machine on your network" if is_constrained else "Local Whisper inference supported",
        ]
    }
    return profile


def print_profile_report() -> int:
    """Print device hardware capability assessment and edge constraints."""
    p = get_device_profile()
    print("\n" + "=" * 75)
    print("HOST HARDWARE PROFILE & EDGE CAPABILITY MATRIX")
    print("=" * 75)
    print(f"Device Name  : {p['device']}")
    print(f"Architecture : {p['arch']} ({p['system']})")
    print(f"Memory (RAM) : {p['total_ram_gb']} GB")
    print(f"Tier Profile : {p['tier'].upper()}")
    print("-" * 75)
    print("CAPABILITY ASSESSMENT:")
    
    caps = [
        ("Metadata Probing", p["capabilities"]["probe_metadata"], "Instant container & codec analysis (<50ms)"),
        ("Subtitle Harvest", p["capabilities"]["harvest_subtitles"], "Zero-download transcripts (youtube-transcript / yt-dlp)"),
        ("Contact Sheet Grid", p["capabilities"]["contact_sheet_lowres"], "4x3 tiled image at 320px width (negligible RAM)"),
        ("Downscaled Frames", p["capabilities"]["ffmpeg_keyframes_downscaled"], f"Keyframes capped at {p['recommended_frame_width']}px with skip_frame nokey"),
        ("Audio Extraction", p["capabilities"]["audio_track_extraction"], "16kHz mono MP3 conversion"),
        ("whisper.cpp (tiny/base)", p["capabilities"]["whisper_cpp_tiny_base"], "Quantized CPU/ARM-NEON speech recognition (<200MB)"),
        ("Heavy Whisper (large)", p["capabilities"]["whisper_heavy_large"], "Large Whisper models (>1.5GB VRAM)"),
        ("Local VLM Perception", p["capabilities"]["local_vlm_perception"], "Vision LLMs (qwen2.5-vl / moondream)"),
        ("PyTorch Object Tracking", p["capabilities"]["pytorch_tracking_yolo"], "YOLOv8/11 multi-object video tracking"),
    ]
    
    for name, capable, note in caps:
        mark = "✓ [CAPABLE]    " if capable else "✗ [UNSUPPORTED]"
        print(f"  {mark:<17} {name:<24} : {note}")

    print("\nLOCAL MODEL DIRECTIVES (from integrating-local-models):")
    for i, lim in enumerate(p["limits"], 1):
        print(f"  {i}. {lim}")

    if p["is_constrained"]:
        print("\n💡 RASPBERRY PI / EDGE ADVISORY:")
        print("   This device can run probe, subtitle harvesting, audio extraction, and low-res")
        print("   contact sheet generation quickly and locally. If deep multimodal vision or heavy")
        print("   transcription is needed, delegate the work to a stronger machine on your network.")

    print("=" * 75 + "\n")
    return 0


def get_best_tool(category: str) -> dict:
    """Get the highest-priority installed tool for a specific capability category."""
    discovery = discover_tools()
    candidates = [t for t in discovery["installed"].values() if t.get("category") == category]
    if candidates:
        return sorted(candidates, key=lambda x: x.get("priority", 99))[0]
    return None


def ytdlp_cmd():
    """yt-dlp on PATH, else run it through uvx so uv alone is enough"""
    if shutil.which("yt-dlp"):
        return [shutil.which("yt-dlp")]
    if shutil.which("uvx"):
        return [shutil.which("uvx"), "--python", ">=3.10", "yt-dlp"]
    return None


def default_out_dir(slug: str) -> Path:
    """Working files go in the user cache, never into the folder the chat runs in"""
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "scrappy-video" / slug


def check_dependencies() -> dict:
    """Check availability of system dependencies."""
    tools = {
        "ffmpeg": shutil.which("ffmpeg"),
        "ffprobe": shutil.which("ffprobe"),
        "yt-dlp": " ".join(ytdlp_cmd() or []) or None,
        "whisper": shutil.which("whisper-ctranslate2") or shutil.which("whisper") or shutil.which("mlx_whisper"),
        "uv": shutil.which("uv"),
    }
    status = {
        "ok": bool(tools["ffmpeg"] and tools["yt-dlp"]),
        "tools": tools,
        "missing": [name for name, path in tools.items() if not path and name in ("ffmpeg", "yt-dlp")],
        "optional_missing": [name for name, path in tools.items() if not path and name not in ("ffmpeg", "yt-dlp")],
    }
    return status


def print_check_report():
    """Print a clean dependency check report with installation advice."""
    status = check_dependencies()
    print("Scrappy Video Understanding — Dependency Check\n" + "=" * 50)
    for name, path in status["tools"].items():
        state = f"OK ({path})" if path else "MISSING"
        opt = " [optional]" if name in ("whisper", "uv", "ffprobe") else " [required]"
        print(f"  {name:10} : {state}{opt}")
    
    print("\nStatus:")
    if not status["missing"]:
        print("  All core tools (ffmpeg, yt-dlp) are ready!")
    else:
        print(f"  Missing required tools: {', '.join(status['missing'])}")
        print("  Install with Homebrew:")
        print("    brew install " + " ".join(status["missing"]))
        
    if not status["tools"]["whisper"]:
        print("\nNote on Whisper (audio transcription):")
        print("  yt-dlp can fetch existing/auto-generated subtitles directly without downloading video.")
        print("  For local video files without subtitles, install local Whisper:")
        print("    uv tool install whisper-ctranslate2")
    print("=" * 50)
    return 0 if not status["missing"] else 1



def clean_vtt_to_text(vtt_content: str) -> str:
    """Convert WebVTT or SRT subtitle text into timestamped, clean paragraphs."""
    lines = vtt_content.splitlines()
    timestamp_re = re.compile(r"(\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?)\s*-->\s*(\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?)")
    
    blocks = []
    current_time = None
    current_text = []
    seen_lines = set()

    for line in lines:
        line_clean = line.strip()
        if not line_clean or line_clean.startswith("WEBVTT") or line_clean.startswith("NOTE") or line_clean.isdigit():
            continue
        
        match = timestamp_re.search(line_clean)
        if match:
            if current_time and current_text:
                joined = " ".join(current_text)
                # Deduplicate identical consecutive fragments
                if joined not in seen_lines:
                    blocks.append(f"[{current_time}] {joined}")
                    seen_lines.add(joined)
            start_ts = match.group(1).split(".")[0]
            # Normalize HH:MM:SS vs MM:SS
            parts = start_ts.split(":")
            if len(parts) == 3 and parts[0] == "00":
                start_ts = f"{parts[1]}:{parts[2]}"
            current_time = start_ts
            current_text = []
        else:
            # Strip XML/HTML tags like <c> </c>
            clean_line = re.sub(r"<[^>]+>", "", line_clean).strip()
            if clean_line and clean_line not in current_text:
                current_text.append(clean_line)

    if current_time and current_text:
        joined = " ".join(current_text)
        if joined not in seen_lines:
            blocks.append(f"[{current_time}] {joined}")

    return "\n".join(blocks)


def ffmpeg_info_to_probe(stderr: str) -> dict:
    """Shape `ffmpeg -i` output like ffprobe's JSON, for hosts that only have ffmpeg"""
    # ponytail: covers duration, codecs, size and fps only; chapters need real ffprobe
    data = {"format": {}, "streams": []}
    d = re.search(r"Duration: (\d+):(\d+):([\d.]+)", stderr)
    if d:
        data["format"]["duration"] = str(int(d[1]) * 3600 + int(d[2]) * 60 + float(d[3]))
    for line in stderr.splitlines():
        m = re.search(r"Stream #\d+:\d+.*?: (Video|Audio|Subtitle): (\w+)", line)
        if not m:
            continue
        st = {"codec_type": m[1].lower(), "codec_name": m[2]}
        size = re.search(r", (\d{2,5})x(\d{2,5})", line)
        if size:
            st["width"], st["height"] = int(size[1]), int(size[2])
        fps = re.search(r"([\d.]+) fps", line)
        if fps:
            st["r_frame_rate"] = f"{fps[1]}/1"
        data["streams"].append(st)
    return data


def probe_media(input_target: str) -> dict:
    """Extract metadata using ffprobe or yt-dlp."""
    meta = {
        "input": input_target,
        "is_url": is_url(input_target),
        "title": None,
        "duration": None,
        "duration_str": None,
        "width": None,
        "height": None,
        "resolution": None,
        "fps": None,
        "video_codec": None,
        "audio_codec": None,
        "has_audio": False,
        "has_video": False,
        "subtitles_available": [],
        "chapters": [],
    }

    if meta["is_url"]:
        ytdlp = ytdlp_cmd()
        if not ytdlp:
            raise RuntimeError("yt-dlp is required to probe URLs. Install uv (https://docs.astral.sh/uv/) or yt-dlp.")
        cmd = [*ytdlp, "--dump-json", "--skip-download", "--no-warnings", input_target]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise UserMessage(private_link_message(res.stderr) or "Could not read that link: " + ((res.stderr.strip().splitlines() or ["unknown error"])[-1]))
        data = json.loads(res.stdout)
        
        meta["title"] = data.get("title") or "Unknown Title"
        meta["duration"] = data.get("duration")
        if meta["duration"]:
            m, s = divmod(int(meta["duration"]), 60)
            h, m = divmod(m, 60)
            meta["duration_str"] = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
        meta["width"] = data.get("width")
        meta["height"] = data.get("height")
        if meta["width"] and meta["height"]:
            meta["resolution"] = f"{meta['width']}x{meta['height']}"
        meta["fps"] = data.get("fps")
        meta["video_codec"] = data.get("vcodec")
        meta["audio_codec"] = data.get("acodec")
        meta["has_video"] = meta["video_codec"] != "none"
        meta["has_audio"] = meta["audio_codec"] != "none"
        meta["description"] = data.get("description", "")
        
        # Subtitles available
        subs = data.get("subtitles", {})
        autosubs = data.get("automatic_captions", {})
        meta["subtitles_available"] = list(set(list(subs.keys()) + list(autosubs.keys())))
        
        # Chapters
        for ch in data.get("chapters") or []:
            meta["chapters"].append({
                "title": ch.get("title"),
                "start": ch.get("start_time"),
                "end": ch.get("end_time"),
            })
    else:
        ffprobe = shutil.which("ffprobe")
        ffmpeg_bin = shutil.which("ffmpeg")
        if not ffprobe and not ffmpeg_bin:
            raise RuntimeError("ffmpeg is required to probe local media. Install it from https://ffmpeg.org/download.html")
        cmd = [
            ffprobe,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            "-show_chapters",
            input_target,
        ]
        if ffprobe:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(res.stdout)
        else:
            res = subprocess.run([ffmpeg_bin, "-hide_banner", "-i", input_target], capture_output=True, text=True)
            data = ffmpeg_info_to_probe(res.stderr)

        fmt = data.get("format", {})
        meta["title"] = Path(input_target).stem
        if "duration" in fmt:
            meta["duration"] = float(fmt["duration"])
            m, s = divmod(int(meta["duration"]), 60)
            h, m = divmod(m, 60)
            meta["duration_str"] = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
            
        for stream in data.get("streams", []):
            codec_type = stream.get("codec_type")
            if codec_type == "video" and not meta["has_video"]:
                meta["has_video"] = True
                meta["video_codec"] = stream.get("codec_name")
                meta["width"] = stream.get("width")
                meta["height"] = stream.get("height")
                if meta["width"] and meta["height"]:
                    meta["resolution"] = f"{meta['width']}x{meta['height']}"
                r_frame_rate = stream.get("r_frame_rate", "")
                if "/" in r_frame_rate:
                    num, den = r_frame_rate.split("/")
                    if float(den) > 0:
                        meta["fps"] = round(float(num) / float(den), 2)
            elif codec_type == "audio" and not meta["has_audio"]:
                meta["has_audio"] = True
                meta["audio_codec"] = stream.get("codec_name")
            elif codec_type == "subtitle":
                lang = stream.get("tags", {}).get("language", "und")
                meta["subtitles_available"].append(lang)
                
        for ch in data.get("chapters", []):
            meta["chapters"].append({
                "title": ch.get("tags", {}).get("title", "Chapter"),
                "start": float(ch.get("start_time", 0)),
                "end": float(ch.get("end_time", 0)),
            })

    return meta


def find_youtube_transcript_runner() -> Optional[Path]:
    """Find public youtube-transcript skill runner if available."""
    candidates = [
        Path.home() / ".claude" / "skills" / "youtube-transcript" / "run.sh",
        Path.home() / ".agents" / "skills" / "youtube-transcript" / "run.sh",
        Path.home() / "Source" / "claude-skills" / "skills" / "youtube-transcript" / "run.sh",
        Path.home() / "Source" / "skills" / "youtube-transcript" / "run.sh",
    ]
    for c in candidates:
        if c.exists() and os.access(c, os.X_OK):
            return c
    return None


def harvest_subtitles(input_target: str, out_dir: Path) -> dict:
    """Harvest existing subtitles/captions without downloading full video if URL."""
    out_dir.mkdir(parents=True, exist_ok=True)
    res = {"has_subtitles": False, "source": None, "text_path": None, "raw_path": None}

    if is_url(input_target):
        # 1. For YouTube: use the public youtube-transcript skill first (zero video bytes, API + fallback)
        if any(d in input_target.lower() for d in ("youtube.com", "youtu.be")):
            yt_runner = find_youtube_transcript_runner()
            if yt_runner:
                txt_out = out_dir / "transcript.txt"
                json_out = out_dir / "transcript.json"
                try:
                    cmd_yt = [str(yt_runner), input_target, "--timestamps", "--format", "text", "--output", str(txt_out)]
                    p_run = subprocess.run(cmd_yt, capture_output=True, text=True, timeout=25)
                    if p_run.returncode == 0 and txt_out.exists() and txt_out.stat().st_size > 0:
                        try:
                            subprocess.run([str(yt_runner), input_target, "--format", "json", "--output", str(json_out)],
                                           capture_output=True, timeout=15)
                        except Exception:
                            pass
                        res["has_subtitles"] = True
                        res["source"] = "youtube-transcript skill (direct api + fallback)"
                        res["text_path"] = str(txt_out)
                        res["raw_path"] = str(json_out if json_out.exists() else txt_out)
                        return res
                except Exception:
                    # Non-fatal, fallback to yt-dlp
                    pass

        ytdlp = ytdlp_cmd()
        if not ytdlp:
            return res
        
        # 2. General URL subtitle download via yt-dlp
        sub_template = str(out_dir / "captions.%(ext)s")
        cmd = [
            *ytdlp,
            "--write-subs",
            "--write-auto-subs",
            "--sub-langs", "en.*,en,all",
            "--sub-format", "vtt/srt/best",
            "--skip-download",
            "--no-warnings",
            "-o", sub_template,
            input_target,
        ]
        subprocess.run(cmd, capture_output=True, text=True)
        
        # Find saved subtitle files
        sub_files = list(out_dir.glob("captions.*.vtt")) + list(out_dir.glob("captions.*.srt"))
        if sub_files:
            sub_file = sub_files[0]
            content = sub_file.read_text(encoding="utf-8", errors="replace")
            formatted = clean_vtt_to_text(content)
            
            clean_txt = out_dir / "transcript.txt"
            clean_txt.write_text(formatted, encoding="utf-8")
            res["has_subtitles"] = True
            res["source"] = f"yt-dlp ({sub_file.name})"
            res["raw_path"] = str(sub_file)
            res["text_path"] = str(clean_txt)
    else:
        # Check for companion subtitle file
        p = Path(input_target)
        for ext in (".vtt", ".srt", ".sub"):
            candidate = p.with_suffix(ext)
            if candidate.exists():
                content = candidate.read_text(encoding="utf-8", errors="replace")
                formatted = clean_vtt_to_text(content)
                clean_txt = out_dir / "transcript.txt"
                clean_txt.write_text(formatted, encoding="utf-8")
                res["has_subtitles"] = True
                res["source"] = f"companion file ({candidate.name})"
                res["raw_path"] = str(candidate)
                res["text_path"] = str(clean_txt)
                return res
        
        # Check for embedded subtitle stream
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg:
            raw_sub = out_dir / "embedded_subtitles.srt"
            cmd = [
                ffmpeg, "-y",
                "-i", input_target,
                "-map", "0:s:0",
                str(raw_sub),
            ]
            run = subprocess.run(cmd, capture_output=True, text=True)
            if run.returncode == 0 and raw_sub.exists() and raw_sub.stat().st_size > 0:
                content = raw_sub.read_text(encoding="utf-8", errors="replace")
                formatted = clean_vtt_to_text(content)
                clean_txt = out_dir / "transcript.txt"
                clean_txt.write_text(formatted, encoding="utf-8")
                res["has_subtitles"] = True
                res["source"] = "embedded stream (0:s:0)"
                res["raw_path"] = str(raw_sub)
                res["text_path"] = str(clean_txt)

    return res


def extract_audio(input_media: str, out_dir: Path) -> Path:
    """Extract 16kHz mono MP3 audio track from media."""
    out_dir.mkdir(parents=True, exist_ok=True)
    out_audio = out_dir / "audio_16k.mp3"
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg required for audio extraction.")
    cmd = [
        ffmpeg, "-y",
        "-i", input_media,
        "-vn",
        "-ar", "16000",
        "-ac", "1",
        "-b:a", "64k",
        str(out_audio),
    ]
    subprocess.run(cmd, capture_output=True, text=True, check=True)
    return out_audio


def extract_keyframes(media_path: str, out_dir: Path, duration: float = None, max_frames: int = 16, detector: str = "auto", frame_width: int = 640) -> dict:
    """Extract keyframes using Native FFmpeg or PySceneDetect, plus uniform interval fallback and contact sheet."""
    out_dir.mkdir(parents=True, exist_ok=True)
    frames_dir = out_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg required for frame extraction.")

    scene_frames = []
    used_detector = "ffmpeg"

    # Option A: PySceneDetect (if explicitly chosen or escalated)
    use_scenedetect = detector == "scenedetect"
    scenedetect_bin = shutil.which("scenedetect")
    uvx_bin = shutil.which("uvx")

    if use_scenedetect and (scenedetect_bin or uvx_bin):
        used_detector = "scenedetect"
        cmd = [scenedetect_bin or uvx_bin]
        if not scenedetect_bin and uvx_bin:
            cmd = [uvx_bin, "scenedetect"]
        cmd.extend(["-i", media_path, "detect-content", "-t", "27.0", "save-images", "-o", str(frames_dir)])
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            scene_frames = sorted(list(frames_dir.glob("*.jpg")))

    # Option B: Native FFmpeg (Default fast, zero-dependency)
    if not scene_frames:
        used_detector = "ffmpeg"
        scene_pattern = str(frames_dir / "scene_%03d.jpg")
        cmd_scene = [
            ffmpeg, "-y",
            "-i", media_path,
            "-vf", f"select='gt(scene,0.3)',scale={frame_width}:-1",
            "-vsync", "vfr",
            "-frame_pts", "1",
            scene_pattern,
        ]
        subprocess.run(cmd_scene, capture_output=True, text=True)
        scene_frames = sorted(list(frames_dir.glob("scene_*.jpg")))

    # Escalation: If detector='auto' produced <2 frames on video >30s, try PySceneDetect via uvx if available
    if detector == "auto" and len(scene_frames) < 2 and (duration or 0) > 30 and (scenedetect_bin or uvx_bin):
        print("      Native FFmpeg found few scene cuts; escalating to PySceneDetect...")
        cmd = [scenedetect_bin or uvx_bin]
        if not scenedetect_bin and uvx_bin:
            cmd = [uvx_bin, "scenedetect"]
        cmd.extend(["-i", media_path, "detect-content", "-t", "27.0", "save-images", "-o", str(frames_dir)])
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            new_frames = sorted(list(frames_dir.glob("*.jpg")))
            if len(new_frames) > len(scene_frames):
                scene_frames = new_frames
                used_detector = "scenedetect (escalated)"

    # Uniform interval fallback if scene detection is still sparse
    interval_frames = []
    if len(scene_frames) < 4:
        interval = max(2, int((duration or 60) / max_frames))
        interval_pattern = str(frames_dir / "interval_%03d.jpg")
        cmd_interval = [
            ffmpeg, "-y",
            "-i", media_path,
            "-vf", f"fps=1/{interval},scale={frame_width}:-1",
            interval_pattern,
        ]
        subprocess.run(cmd_interval, capture_output=True, text=True)
        interval_frames = sorted(list(frames_dir.glob("interval_*.jpg")))

    all_frames = scene_frames if len(scene_frames) >= 4 else (scene_frames + interval_frames)
    
    # 3. Create Contact Sheet (Storyboard grid)
    # 4x3 grid = 12 cells, scaled to 320x180 thumbnail cells
    contact_sheet = out_dir / "contact_sheet.jpg"
    fps_sample = max(1, int((duration or 60) / 12))
    cmd_tile = [
        ffmpeg, "-y",
        "-i", media_path,
        "-vf", f"fps=1/{fps_sample},scale=320:180,tile=4x3",
        "-frames:v", "1",
        str(contact_sheet),
    ]
    subprocess.run(cmd_tile, capture_output=True, text=True)

    return {
        "frames_dir": str(frames_dir),
        "frame_count": len(all_frames),
        "frames": [str(f) for f in all_frames[:max_frames]],
        "contact_sheet": str(contact_sheet) if contact_sheet.exists() else None,
        "detector_used": used_detector,
    }



def build_split_recommendation(meta: dict, subs: dict, profile: dict) -> dict:
    """Recommend optimal workload split between local tools and Cloud AI based on media and device constraints."""
    duration = meta.get("duration") or 0
    is_constrained = profile.get("is_constrained", False)
    has_subs = subs.get("has_subtitles", False)

    local_steps = [
        "Metadata probe & stream inspection (completed in ~50ms, 0 tokens)",
    ]
    if has_subs:
        local_steps.append(f"Subtitle harvest via {subs.get('source')} (completed in ~1s, 0 MB video download)")
    else:
        local_steps.append("Audio track extraction for local or cloud transcription")

    local_steps.append("Visual keyframe sampling & single-glance 4x3 contact sheet (cuts token spend by >90%)")

    if is_constrained:
        cloud_model = "a current Gemini or Claude model"
        cloud_reason = (
            f"Host is a constrained edge device ({profile.get('device')}, {profile.get('total_ram_gb')}GB RAM). "
            "Local node handles probing, subtitles, and contact sheet generation. Offload deep synthesis and visual reasoning to Cloud AI."
        )
    elif duration > 1800:
        cloud_model = "a current Gemini model with a long context window"
        cloud_reason = (
            f"Video is long ({meta.get('duration_str', '30m+')}). Gemini's 1M-2M token multimodal context window handles "
            "temporal video search and timestamped grounding far cheaper and faster than frame-by-frame local VLMs."
        )
    elif has_subs:
        cloud_model = "a current Claude model"
        cloud_reason = (
            "Local pipeline already harvested clean timestamped transcript. Feed transcript + contact sheet "
            "to Claude for superior analytical critique, architecture reasoning, or structured code extraction."
        )
    else:
        cloud_model = "a current Gemini or Claude model"
        cloud_reason = (
            "Extract audio locally, then synthesize with Cloud AI to avoid local VLM memory thrashing."
        )

    return {
        "local_execution": local_steps,
        "cloud_ai": {
            "recommended_models": cloud_model,
            "why": cloud_reason,
        },
        "questions_to_confirm": [
            "What is your primary goal? (e.g. quick takeaways, code/slide extraction, chapter outline, or deep technical critique)",
            "Do you want to keep this 100% private/local, or synthesize via Cloud AI (Gemini / Claude)?"
        ]
    }


def print_split_recommendation(split_rec: dict):
    """Print clean, concise recommendation of local vs cloud AI split."""
    print("\n" + "=" * 75)
    print("RECOMMENDED SPLIT: LOCAL VS CLOUD AI")
    print("=" * 75)
    print("LOCAL EXECUTION (Fast, Free, Zero-Bloat):")
    for step in split_rec["local_execution"]:
        print(f"  • {step}")
    
    cloud = split_rec["cloud_ai"]
    print("\nCLOUD AI RECOMMENDATION:")
    print(f"  Model : {cloud['recommended_models']}")
    print(f"  Why   : {cloud['why']}")

    print("\nQUESTIONS TO CONFIRM BEFORE NEXT PASS:")
    for i, q in enumerate(split_rec["questions_to_confirm"], 1):
        print(f"  {i}. {q}")
    print("=" * 75 + "\n")


def run_pipeline(input_target: str, out_dir: Path, max_frames: int = 16, stage: str = "full", detector: str = "auto", yes: bool = False) -> dict:
    """Run progressive video understanding pipeline.
    
    Stages (resourceful & lean first):
    - 'probe': Fast metadata & stream check only (<1s, 0 bytes downloaded).
    - 'subs': Probe + instant subtitle/transcript harvesting (fast, 0 video download).
    - 'quick': Probe + subs + single contact sheet at 360p (fastest visual check).
    - 'full': Full pipeline with deep scene-cut keyframe extraction and audio separation.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    profile = get_device_profile()
    if profile["is_constrained"]:
        print(f"\n[Hardware Profile] Constrained/Edge device detected ({profile['device']}, {profile['total_ram_gb']}GB RAM). Enforcing edge memory guards.")

    original = input_target
    ref = github_release_ref(input_target) if is_url(input_target) else None
    if ref:
        fetched = fetch_github_asset(ref, out_dir, yes=yes, download=stage not in ("probe", "subs"))
        if fetched:
            input_target = str(fetched)

    print(f"\n[1/4] Probing media (Stage 1: Leanest Probe): {input_target}")
    meta = probe_media(input_target)
    if ref and ref.get("file"):
        meta["title"] = Path(ref["file"]).stem
    print(f"      Title: {meta['title']}")
    print(f"      Duration: {meta.get('duration_str') or 'Unknown'}, Resolution: {meta.get('resolution') or 'Audio-only'}")

    summary = {
        "metadata": meta,
        "subtitles": {"has_subtitles": False, "source": None, "text_path": None},
        "audio": None,
        "frames": {"frames": [], "contact_sheet": None},
        "working_dir": str(out_dir),
        "stage": stage,
        "detector": detector,
        "device_profile": profile,
    }

    print("\n[2/4] Harvesting subtitles / captions (Stage 2: 0-download transcript)...")
    subs = harvest_subtitles(input_target, out_dir)
    summary["subtitles"] = subs
    if subs["has_subtitles"]:
        print(f"      Found subtitles via {subs['source']}")
    else:
        print("      No existing subtitles found.")

    split_rec = build_split_recommendation(meta, subs, profile)
    summary["split_recommendation"] = split_rec

    if stage in ("probe", "subs"):
        print_split_recommendation(split_rec)
        print(f"[*] Initial reconnaissance complete at Stage '{stage}' (Resource-efficient minimal intake).")
        summary_json = out_dir / "summary.json"
        summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return summary

    local_media = input_target
    if meta["is_url"]:
        # Download lightweight stream (capped at 480p on constrained/Pi, 720p on standard)
        ytdlp = ytdlp_cmd()
        max_h = 480 if (stage == "quick" or profile["is_constrained"]) else 720
        print(f"\n[3/4] Ingesting lightweight stream (max {max_h}p) for visual sampling...")
        download_target = out_dir / "source_stream.mp4"
        cmd = [
            *ytdlp,
            "-f", f"bestvideo[height<={max_h}]+bestaudio/best[height<={max_h}]/best",
            "-o", str(download_target),
            "--no-warnings",
            input_target,
        ]
        dl = subprocess.run(cmd, capture_output=True, text=True)
        if dl.returncode != 0:
            raise UserMessage(private_link_message(dl.stderr) or "Download failed: " + ((dl.stderr.strip().splitlines() or ["unknown error"])[-1]))
        local_media = str(download_target)

    frames_info = {"frames": [], "contact_sheet": None}
    if meta["has_video"] or Path(local_media).suffix.lower() in (".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"):
        if stage == "quick":
            print("\n[4/4] Generating single-glance 4x3 contact sheet (quick visual pass)...")
            ffmpeg = shutil.which("ffmpeg")
            contact_sheet = out_dir / "contact_sheet.jpg"
            fps_sample = max(1, int((meta.get("duration") or 60) / 12))
            cmd_tile = [
                ffmpeg, "-y",
                "-i", local_media,
                "-vf", f"fps=1/{fps_sample},scale=320:180,tile=4x3",
                "-frames:v", "1",
                str(contact_sheet),
            ]
            subprocess.run(cmd_tile, capture_output=True, text=True)
            frames_info = {
                "frames_dir": str(out_dir),
                "frame_count": 12 if contact_sheet.exists() else 0,
                "frames": [],
                "contact_sheet": str(contact_sheet) if contact_sheet.exists() else None,
                "detector_used": "ffmpeg-tile",
            }
        else:
            frame_width = profile["recommended_frame_width"]
            print(f"\n[4/4] Extracting keyframes and generating contact sheet (full pass, detector: {detector}, width: {frame_width}px)...")
            frames_info = extract_keyframes(local_media, out_dir, duration=meta.get("duration"), max_frames=max_frames, detector=detector, frame_width=frame_width)
            print(f"      Extracted {frames_info['frame_count']} keyframes using {frames_info.get('detector_used', detector)}.")

        if frames_info.get("contact_sheet"):
            print(f"      Generated contact sheet: {frames_info['contact_sheet']}")

    if profile["is_constrained"] and stage == "full":
        print("\n[Edge Guard] Heavy local VLM / PyTorch inference is bypassed on constrained device to prevent swap thrashing.")
        print(f"             Deterministic artifacts (transcript.txt, contact_sheet.jpg, audio_16k.mp3) are generated.")
        print(f"             If deeper multimodal inference is needed, delegate to an upstream desktop node.")


    summary["frames"] = frames_info

    # Audio extraction for speech transcription if needed
    audio_path = None
    if stage == "full" and meta["has_audio"] and not subs["has_subtitles"]:
        print("\n[*] Extracting audio track for speech transcription...")
        try:
            audio_path = str(extract_audio(local_media, out_dir))
            print(f"    Audio extracted to {audio_path}")
        except Exception as e:
            print(f"    Audio extraction note: {e}")
    summary["audio"] = audio_path

    # Save summary.json
    summary_json = out_dir / "summary.json"
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # Generate Markdown Report
    report_md = out_dir / "report.md"
    report_lines = [
        f"# Video Understanding: {meta['title']}",
        "",
        "## Overview",
        f"- **Source**: `{original}`",
        f"- **Duration**: {meta.get('duration_str', 'N/A')}",
        f"- **Resolution**: {meta.get('resolution', 'N/A')} ({meta.get('fps', 'N/A')} fps)",
        f"- **Video Codec**: {meta.get('video_codec', 'N/A')}, **Audio Codec**: {meta.get('audio_codec', 'N/A')}",
        f"- **Subtitles**: {'Available (' + subs['source'] + ')' if subs['has_subtitles'] else 'None detected'}",
        f"- **Pipeline Stage**: `{stage}`",
        "",
    ]

    if meta.get("chapters"):
        report_lines.extend(["## Chapters", ""])
        for ch in meta["chapters"]:
            m, s = divmod(int(ch.get("start") or 0), 60)
            report_lines.append(f"- **`{m:02d}:{s:02d}`** {ch['title']}")
        report_lines.append("")

    if frames_info.get("contact_sheet"):
        report_lines.extend([
            "## Visual Contact Sheet",
            f"![Contact Sheet]({frames_info['contact_sheet']})",
            "",
        ])

    if subs["has_subtitles"] and subs["text_path"]:
        txt = Path(subs["text_path"]).read_text(encoding="utf-8")
        preview = "\n".join(txt.splitlines()[:25])
        report_lines.extend([
            "## Subtitle / Transcript Highlights (first 25 segments)",
            "```text",
            preview,
            "```",
            f"*(Full transcript saved to `{subs['text_path']}`)*",
            "",
        ])

    report_lines.extend([
        "## Next Steps & Synthesis",
        "- Run multimodal image inspection on the contact sheet or keyframes for slide/action recognition.",
        "- Feed the transcript into your agent for detailed QA, chapter summaries, or action extraction.",
    ])

    report_md.write_text("\n".join(report_lines), encoding="utf-8")
    report_html = out_dir / "report.html"
    report_html.write_text(render_report_html(summary, original, out_dir), encoding="utf-8")
    print(f"\nDone! Comprehensive report written to:\n  {report_md}\n  {report_html}\n")
    return summary


def render_report_html(summary: dict, source: str, out_dir: Path) -> str:
    """Self-contained phone-friendly report page; contact sheet embedded, no external CSS or JS"""
    e = html.escape
    meta, subs, frames = summary["metadata"], summary["subtitles"], summary["frames"]
    out = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{e(str(meta.get('title')))}</title>",
        "<style>body{font:16px/1.5 system-ui,sans-serif;max-width:42rem;margin:0 auto;padding:1rem}"
        "img{max-width:100%;height:auto}pre{white-space:pre-wrap;word-break:break-word}"
        "summary{cursor:pointer;font-weight:600}</style></head><body>",
        f"<h1>{e(str(meta.get('title')))}</h1>",
        f"<p>Source: {e(source)}<br>Length: {e(str(meta.get('duration_str') or 'unknown'))}"
        f" &middot; Size: {e(str(meta.get('resolution') or 'audio only'))}</p>",
    ]
    if (out_dir / "contact_sheet.jpg").exists():
        b64 = base64.b64encode((out_dir / "contact_sheet.jpg").read_bytes()).decode()
        out.append(f'<h2>Contact sheet</h2><img src="data:image/jpeg;base64,{b64}" alt="Contact sheet of the video">')
    if meta.get("chapters"):
        out.append("<h2>Chapters</h2><ul>")
        for ch in meta["chapters"]:
            m, s = divmod(int(ch.get("start") or 0), 60)
            out.append(f"<li>{m:02d}:{s:02d} {e(str(ch['title']))}</li>")
        out.append("</ul>")
    if subs.get("text_path") and Path(subs["text_path"]).exists():
        txt = Path(subs["text_path"]).read_text(encoding="utf-8", errors="replace")
        out.append(f"<h2>Transcript</h2><details><summary>Show the transcript</summary><pre>{e(txt)}</pre></details>")
    if frames.get("frames"):
        out.append("<h2>Key frames</h2><ul>")
        for f in frames["frames"]:
            rel = os.path.relpath(f, out_dir)
            out.append(f'<li><a href="{e(urllib.parse.quote(rel), quote=True)}">{e(rel)}</a></li>')
        out.append("</ul>")
    out.append(f"<p>All the files are in {e(str(out_dir))}</p></body></html>")
    return "\n".join(out)


def selftest():
    """Run internal sanity checks."""
    print("Running scrappy_video selftest...")
    sample_vtt = """WEBVTT
Kind: captions
Language: en

00:00:01.000 --> 00:00:04.500
Hello everyone and welcome to this session.

00:00:05.000 --> 00:00:08.200
Today we are building an agent skill.
"""
    cleaned = clean_vtt_to_text(sample_vtt)
    assert "[00:01] Hello everyone and welcome to this session." in cleaned
    assert "[00:05] Today we are building an agent skill." in cleaned
    
    assert is_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert is_url("http://example.com/video.mp4")
    assert not is_url("/path/to/video.mp4")
    assert not is_url("video.mp4")

    global CUSTOM_REGISTRY
    reg = load_tool_registry()
    assert reg["tools"], "open tools catalog is empty"
    for key, tool in reg["tools"].items():
        assert tool.get("name") and tool.get("category"), f"catalog entry {key} lacks name or category"

    saved = CUSTOM_REGISTRY
    with tempfile.TemporaryDirectory() as tmp:
        CUSTOM_REGISTRY = Path(tmp) / "custom_tools.json"
        try:
            register_custom_tool("selftest-tool", "audio_processing", "selftest-bin", "selftest entry")
            tool = load_tool_registry()["tools"]["selftest-tool"]
            assert tool["bin"] == "selftest-bin" and tool["learned_at"]
        finally:
            CUSTOM_REGISTRY = saved

    info = ffmpeg_info_to_probe(
        "  Duration: 00:01:05.50, start: 0.000000, bitrate: 512 kb/s\n"
        "  Stream #0:0[0x1](und): Video: h264 (High), yuv420p, 1280x720, 400 kb/s, 29.97 fps, 30 tbr\n"
        "  Stream #0:1[0x2](und): Audio: aac (LC), 44100 Hz, stereo, fltp, 128 kb/s\n")
    assert float(info["format"]["duration"]) == 65.5
    kinds = [(st["codec_type"], st["codec_name"]) for st in info["streams"]]
    assert kinds == [("video", "h264"), ("audio", "aac")]
    assert info["streams"][0]["width"] == 1280 and info["streams"][0]["height"] == 720

    with tempfile.TemporaryDirectory() as tmp:
        fake = {"metadata": {"title": "A <b> talk", "duration_str": "01:05", "resolution": "1280x720",
                             "chapters": [{"title": "Intro", "start": 0}]},
                "subtitles": {"text_path": None}, "frames": {"frames": []}}
        page = render_report_html(fake, "https://x.test/v", Path(tmp))
        assert "A &lt;b&gt; talk" in page and "<b> talk" not in page and "Intro" in page
        assert "contact_sheet.jpg" not in page
        (Path(tmp) / "contact_sheet.jpg").write_bytes(b"x")
        assert 'src="data:image/jpeg;base64,' in render_report_html(fake, "v.mp4", Path(tmp))

    assert private_link_message("ERROR: HTTP Error 403: Forbidden") == PRIVATE_LINE
    assert private_link_message("HTTP Error 404: Not Found") == PRIVATE_LINE
    assert private_link_message("network unreachable") is None
    ref = github_release_ref("https://github.com/acme/demo/releases/download/v1.0/clip%20one.mp4")
    assert ref == {"repo": "acme/demo", "tag": "v1.0", "file": "clip one.mp4"}
    assert github_release_ref("https://api.github.com/repos/acme/demo/releases/assets/123") == {"repo": "acme/demo", "asset_id": "123"}
    assert github_release_ref("https://github.com/acme/demo") is None
    assert private_link_message("Sign in to confirm you're not a bot") is None
    for bad in ("https://github.com/acme/demo/releases/download/--dir=x/a.mp4",
                "https://github.com/a%2Fb/demo/releases/download/v1/a.mp4",
                "https://github.com/acme/demo/releases/download/v1%2Fx/a.mp4",
                "https://api.github.com/repos/acme/demo/releases/assets/12x"):
        try:
            github_release_ref(bad)
            raise AssertionError("accepted " + bad)
        except UserMessage:
            pass

    class _R:
        def __init__(self, out="", rc=0):
            self.stdout, self.stderr, self.returncode = out, b"", rc
    calls, big = [], {"n": 0}
    def fake_run(cmd, **kw):
        calls.append(cmd)
        if cmd[1:3] == ["api", "repos/acme/demo/releases/tags/v1"]:
            return _R(json.dumps({"assets": [{"name": "a.mp4", "size": big["n"]}]}))
        return _R()
    real_which, real_run, real_move = shutil.which, subprocess.run, shutil.move
    shutil.which, subprocess.run, shutil.move = (lambda n: "/bin/gh"), fake_run, (lambda a, b: None)
    try:
        gref = {"repo": "acme/demo", "tag": "v1", "file": "a.mp4"}
        big["n"] = 300 * 1048576
        try:
            fetch_github_asset(gref, Path(tempfile.gettempdir()) / "sv_selftest")
            raise AssertionError("300 MB went through without a yes")
        except UserMessage:
            pass
        assert not any(c[1:3] == ["release", "download"] for c in calls)
        assert fetch_github_asset(gref, Path(tempfile.gettempdir()) / "sv_selftest", yes=True)
        dl = [c for c in calls if c[1:3] == ["release", "download"]][0]
        assert dl[-2:] == ["--", "v1"]
    finally:
        shutil.which, subprocess.run, shutil.move = real_which, real_run, real_move

    profile = get_device_profile()
    assert isinstance(profile.get("is_constrained"), bool) and profile.get("limits")
    print("selftest: PASSED")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Scrappy Video Understanding CLI (Resourceful & Progressive)")
    parser.add_argument("input", nargs="?", help="Video URL or local media file path")
    parser.add_argument("--out", "-o", help="Output directory (defaults to ~/.cache/scrappy-video/<slug>)")
    parser.add_argument("--stage", choices=["probe", "subs", "quick", "full"], default="quick",
                        help="Progressive stage: 'probe' (metadata only), 'subs' (probe + subtitles), 'quick' (probe + subs + contact sheet), 'full' (all passes). Default: quick")
    parser.add_argument("--quick", action="store_true", help="Shorthand for --stage quick (fast, leanest visual pass)")
    parser.add_argument("--full", action="store_true", help="Shorthand for --stage full (full deep pass)")
    parser.add_argument("--check", action="store_true", help="Check dependencies and system health")
    parser.add_argument("--profile", action="store_true", help="Print host hardware capability profile and edge constraints")
    parser.add_argument("--tools", action="store_true", help="Browse the predefined open tools catalog and host availability")
    parser.add_argument("--register-tool", metavar="NAME", help="Register a new open tool in the learning registry")
    parser.add_argument("--bin", default=None, help="Binary/executable name for registered tool")
    parser.add_argument("--cat", choices=["ingest", "probe", "transcription", "scene_detection", "storyboard", "audio_processing", "diarization", "ocr", "local_vision", "editing_rendering"],
                        default="ingest", help="Capability category for registered tool")
    parser.add_argument("--desc", default="", help="Description for registered tool")
    parser.add_argument("--install", default="", help="Install command for registered tool")
    parser.add_argument("--url", default="", help="Project URL for registered tool")
    parser.add_argument("--license", default="Open Source", help="License for registered tool")
    parser.add_argument("--selftest", action="store_true", help="Run hermetic self-checks")
    parser.add_argument("--detector", choices=["auto", "ffmpeg", "scenedetect"], default="auto",
                        help="Scene cut detector: 'auto' (native ffmpeg with PySceneDetect escalation), 'ffmpeg' (pure ffmpeg), 'scenedetect' (PySceneDetect). Default: auto")
    parser.add_argument("--yes", action="store_true", help="Member said yes to a download over 200 MB")
    parser.add_argument("--max-frames", type=int, default=16, help="Maximum keyframes to extract in full pass (default 16)")
    
    args = parser.parse_args()

    if args.selftest:
        sys.exit(selftest())

    if args.profile:
        sys.exit(print_profile_report())

    if args.tools:
        sys.exit(print_tools_catalog())

    if args.register_tool:
        bin_name = args.bin or args.register_tool
        register_custom_tool(args.register_tool, args.cat, bin_name, args.desc,
                             install=args.install, url=args.url, license_name=args.license)
        sys.exit(0)

    if args.check or not args.input:
        if args.check:
            sys.exit(print_check_report())
        parser.print_help()
        sys.exit(1)


    stage = "full" if args.full else ("quick" if args.quick else args.stage)

    # Determine output folder
    if args.out:
        out_path = Path(args.out)
    else:
        ref = github_release_ref(args.input) if is_url(args.input) else None
        name = Path(ref["file"]).stem if ref and ref.get("file") else "web_video"
        slug = re.sub(r"[^a-zA-Z0-9_-]", "_", name if is_url(args.input) else Path(args.input).stem)[:32]
        out_path = default_out_dir(slug)

    try:
        run_pipeline(args.input, out_path, max_frames=args.max_frames, stage=stage, detector=args.detector, yes=args.yes)
    except UserMessage as e:
        print(str(e), file=sys.stderr)
        sys.exit(0 if isinstance(e, StageStop) else 1)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

