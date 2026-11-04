#!/usr/bin/env python3
"""Report an Astrolabe confusion as a GitHub issue.

  confusion.py check                                   -> checks dependencies and auth
  confusion.py grab [--screen] [--crop]               -> prints the saved screenshot path
  confusion.py file REPO TITLE BODY_MD IMAGE [LABEL]  -> prints the issue URL

grab checks for a recent shot in tools/screens in the last 180 s, then checks
pasted images from the session transcript. With --crop on macOS, it triggers
interactive drag-to-select capture. With --screen it captures full screen. If
neither was passed and no screenshot is found, it exits with instructions.
CONFUSION_TEST_FIXTURE=<png> makes --crop copy that file instead of capturing.

file uploads the image to the repo's `issue-screens` branch (no workflows run
there) and embeds it in the created GitHub issue.
"""
import base64, datetime, glob, json, os, shutil, subprocess, sys, time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def get_screens_dir():
    cwd_shots = os.path.join(os.getcwd(), "tools", "screens")
    if os.path.isdir(cwd_shots):
        return cwd_shots
    rel_shots = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", "tools", "screens"))
    if os.path.isdir(rel_shots):
        return rel_shots
    fallback = os.path.expanduser("~/.astrolabe/screens")
    os.makedirs(fallback, exist_ok=True)
    return fallback

SHOTS = get_screens_dir()
BRANCH = "issue-screens"


def run_cmd(args, stdin=None):
    return subprocess.run(args, input=stdin, capture_output=True, text=True)


def check_deps():
    status = {"ready": True, "missing": [], "details": {}}
    
    # 1. GitHub CLI
    gh_bin = shutil.which("gh")
    if not gh_bin:
        status["ready"] = False
        status["missing"].append("gh (GitHub CLI not found in PATH)")
        status["details"]["gh"] = "Missing. Install via: brew install gh"
    else:
        auth = run_cmd(["gh", "auth", "status"])
        if auth.returncode != 0:
            status["ready"] = False
            status["missing"].append("gh auth (not logged in)")
            status["details"]["gh"] = "Not authenticated. Run: gh auth login"
        else:
            status["details"]["gh"] = "Installed and authenticated."

    # 2. Screenshot capabilities
    has_screencapture = bool(shutil.which("screencapture"))
    status["details"]["screencapture"] = "Available (macOS)" if has_screencapture else "Unavailable (paste a screenshot instead)"
    
    # 3. Screens directory
    os.makedirs(SHOTS, exist_ok=True)
    status["details"]["screens_dir"] = f"Ready: {SHOTS}"

    return status


def last_recent_shot(max_age_seconds=180):
    """Find a confusion-* screenshot saved to tools/screens in the last few minutes."""
    if not os.path.isdir(SHOTS):
        return None
    now = time.time()
    candidates = []
    for f in os.listdir(SHOTS):
        if f.startswith("confusion-") and f.endswith((".png", ".jpg", ".jpeg", ".webp")):
            full = os.path.join(SHOTS, f)
            mtime = os.path.getmtime(full)
            if now - mtime <= max_age_seconds:
                candidates.append((mtime, full))
    if candidates:
        candidates.sort(reverse=True)
        return candidates[0][1]
    return None


def last_pasted_image():
    """Extract last pasted base64 image from session transcripts if available."""
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID")
    if sid:
        for path in glob.glob(os.path.expanduser(f"~/.claude/projects/*/{sid}.jsonl")):
            found = None
            try:
                with open(path) as f:
                    for line in f:
                        if '"image"' not in line:
                            continue
                        msg = json.loads(line).get("message") or {}
                        if msg.get("role") != "user" or not isinstance(msg.get("content"), list):
                            continue
                        for c in msg["content"]:
                            src = c.get("source") or {}
                            if c.get("type") == "image" and src.get("type") == "base64":
                                found = src
            except Exception:
                pass
            if found:
                return found

    # Check for antigravity / assistant transcript logs
    ag_log = os.environ.get("TRANSCRIPT_PATH")
    if ag_log and os.path.exists(ag_log):
        found = None
        try:
            with open(ag_log) as f:
                for line in f:
                    if '"image"' in line or '"media"' in line:
                        entry = json.loads(line)
                        media = entry.get("media") or []
                        for m in media:
                            uri = m.get("uri")
                            if uri and os.path.exists(uri):
                                return {"file_path": uri}
        except Exception:
            pass

    return None


def grab(screen=False, crop=False):
    os.makedirs(SHOTS, exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")

    # 1. If explicit --screen requested, run full-screen capture
    if screen:
        out = os.path.join(SHOTS, f"confusion-{stamp}.png")
        if shutil.which("screencapture"):
            subprocess.run(["screencapture", "-x", out], check=True)
            print(out)
            return
        else:
            raise SystemExit("screencapture is not available on this platform for --screen")

    # 2. If explicit --crop requested, run interactive drag-select crosshair
    if crop:
        out = os.path.join(SHOTS, f"confusion-{stamp}.png")
        fixture = os.environ.get("CONFUSION_TEST_FIXTURE")
        if fixture:
            # tests stand in for the drag-select so nothing pops over the live screen
            shutil.copyfile(fixture, out)
            print(out)
            return
        if shutil.which("screencapture"):
            r = subprocess.run(["screencapture", "-i", "-s", "-x", out])
            if r.returncode == 0 and os.path.exists(out) and os.path.getsize(out) > 0:
                print(out)
                return
            else:
                if os.path.exists(out) and os.path.getsize(out) == 0:
                    os.remove(out)
                raise SystemExit("Interactive capture cancelled or empty.")
        else:
            raise SystemExit("screencapture is not available on this platform for --crop")

    # 3. No flags: check recent shot (within 180s)
    recent = last_recent_shot(max_age_seconds=180)
    if recent:
        print(recent)
        return

    # 4. No flags: check for pasted image in transcript
    img = last_pasted_image()
    if img:
        if "file_path" in img:
            print(img["file_path"])
            return
        ext = img.get("media_type", "image/png").split("/")[-1].replace("jpeg", "jpg")
        out = os.path.join(SHOTS, f"confusion-{stamp}.{ext}")
        with open(out, "wb") as f:
            f.write(base64.b64decode(img["data"]))
        print(out)
        return

    # 5. grab with no flags and no screenshot found
    raise SystemExit("No screenshot found: paste one, or run grab --crop / --screen")


def gh(*args, data=None):
    r = subprocess.run(["gh", *args], input=data, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"gh {' '.join(args[:2])} failed: {r.stderr.strip()}")
    return r.stdout.strip()


def file_issue(repo, title, body_path, image, label=None):
    if not os.path.exists(image):
        raise SystemExit(f"No image at {image}")

    # Ensure branch exists
    try:
        gh("api", f"repos/{repo}/branches/{BRANCH}")
    except SystemExit:
        default = gh("api", f"repos/{repo}", "--jq", ".default_branch")
        sha = gh("api", f"repos/{repo}/git/ref/heads/{default}", "--jq", ".object.sha")
        gh("api", "-X", "POST", f"repos/{repo}/git/refs", "--input", "-",
           data=json.dumps({"ref": f"refs/heads/{BRANCH}", "sha": sha}))

    # Upload image
    name = os.path.basename(image)
    with open(image, "rb") as f:
        payload = {
            "message": f"screen: {name}",
            "branch": BRANCH,
            "content": base64.b64encode(f.read()).decode()
        }
    gh("api", "-X", "PUT", f"repos/{repo}/contents/screens/{name}", "--input", "-", data=json.dumps(payload))
    url = f"https://github.com/{repo}/blob/{BRANCH}/screens/{name}?raw=true"

    # Format body
    with open(body_path) as f:
        body = f.read().replace("{{SCREENSHOT}}", f"![screenshot]({url})")

    # Create issue
    args = ["issue", "create", "-R", repo, "--title", title, "--body", body]
    try:
        labels = gh("label", "list", "-R", repo, "--limit", "200", "--json", "name", "--jq", ".[].name").split("\n")
        if label and label in labels:
            args += ["--label", label]
    except Exception:
        pass

    print(gh(*args))


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] == "check":
        res = check_deps()
        print(json.dumps(res, indent=2))
        sys.exit(0 if res["ready"] else 1)
    elif args[0] == "grab":
        grab(screen="--screen" in args, crop="--crop" in args)
    elif args[0] == "file" and len(args) >= 5:
        file_issue(*args[1:6])
    else:
        raise SystemExit(__doc__)
