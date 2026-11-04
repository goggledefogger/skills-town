#!/usr/bin/env python3
"""Report something in Astrolabe that made you go huh, as a GitHub issue.

  astrohuh.py check                                   -> checks dependencies and auth
  astrohuh.py grab [--screen] [--crop]               -> prints the saved screenshot path
  astrohuh.py file REPO TITLE BODY_MD IMAGE [LABEL]  -> prints the issue URL
  astrohuh.py selftest                               -> checks the capture-route picking
  astrohuh.py draft BODY_MD                          -> Astrolabe report draft: prints {draft, payload_json}
  astrohuh.py save DRAFT_ID                          -> keeps that exact draft in Astrolabe's reports, prints the ref

grab checks for a recent shot in tools/screens in the last 180 s, then checks
pasted images from the session transcript. With --crop it triggers
interactive drag-to-select capture (Windows: Snipping Tool; Linux: the first of
gnome-screenshot, spectacle, grim+slurp, maim, scrot, flameshot, import on PATH).
With --screen it captures full screen. If
neither was passed and no screenshot is found, it exits with instructions.
ASTROHUH_TEST_FIXTURE=<png> makes --crop copy that file instead of capturing.

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
    fallback = os.path.join(os.path.expanduser("~"), ".astrolabe", "screens")
    os.makedirs(fallback, exist_ok=True)
    return fallback

SHOTS = get_screens_dir()
PREFIX = "astrohuh-"
BRANCH = "issue-screens"


def run_cmd(args, stdin=None):
    return subprocess.run(args, input=stdin, capture_output=True, text=True)


# Linux tools in preference order: (name, region argv, full-screen argv)
# {out} is the file path; flameshot writes to stdout, which goes to the file
LINUX_TOOLS = [
    ("gnome-screenshot", ["gnome-screenshot", "-a", "-f", "{out}"], ["gnome-screenshot", "-f", "{out}"]),
    ("spectacle", ["spectacle", "-r", "-b", "-n", "-o", "{out}"], ["spectacle", "-f", "-b", "-n", "-o", "{out}"]),
    ("grim", ["grim", "-g", "{geom}", "{out}"], ["grim", "{out}"]),
    ("maim", ["maim", "-s", "{out}"], ["maim", "{out}"]),
    ("scrot", ["scrot", "-s", "{out}"], ["scrot", "{out}"]),
    ("flameshot", ["flameshot", "gui", "--raw"], ["flameshot", "full", "--raw"]),
    ("import", ["import", "{out}"], ["import", "-window", "root", "{out}"]),
]

PS_HEAD = "Add-Type -AssemblyName System.Windows.Forms; Add-Type -AssemblyName System.Drawing; $p=$env:ASTROHUH_OUT; "
# Clipboard is cleared first so an old image is not mistaken for the new clip
PS_CROP = PS_HEAD + (
    "[Windows.Forms.Clipboard]::Clear(); Start-Process 'ms-screenclip:'; "
    "for($i=0;$i -lt 120;$i++){Start-Sleep -Milliseconds 500; "
    "if([Windows.Forms.Clipboard]::ContainsImage()){[Windows.Forms.Clipboard]::GetImage().Save($p,[Drawing.Imaging.ImageFormat]::Png); exit 0}}; exit 1")
PS_SCREEN = PS_HEAD + (
    "$v=[Windows.Forms.SystemInformation]::VirtualScreen; $b=New-Object Drawing.Bitmap $v.Width,$v.Height; "
    "$g=[Drawing.Graphics]::FromImage($b); $g.CopyFromScreen($v.Left,$v.Top,0,0,$b.Size); "
    "$b.Save($p,[Drawing.Imaging.ImageFormat]::Png)")


def capture_plan(crop, platform=None, which=shutil.which):
    """Pick the capture route: a dict with name and argv, or None if this machine has none."""
    platform = platform or sys.platform
    if platform == "darwin":
        if which("screencapture"):
            return {"name": "screencapture", "argv": ["screencapture", "-i", "-s", "-x", "{out}"] if crop else ["screencapture", "-x", "{out}"]}
    elif platform.startswith("win"):
        ps = which("powershell") or which("pwsh")
        if ps:
            return {"name": "Snipping Tool" if crop else "PowerShell", "env": True,
                    "argv": [ps, "-NoProfile", "-STA", "-Command", PS_CROP if crop else PS_SCREEN]}
    else:
        for name, region, full in LINUX_TOOLS:
            if not which(name):
                continue
            if name == "grim" and crop and not which("slurp"):
                continue
            return {"name": name + ("+slurp" if name == "grim" and crop else ""),
                    "argv": region if crop else full, "stdout": name == "flameshot",
                    "slurp": name == "grim" and crop}
    return None


def run_capture(plan, out):
    argv = [a.replace("{out}", out) for a in plan["argv"]]
    env = dict(os.environ, ASTROHUH_OUT=out) if plan.get("env") else None
    if plan.get("slurp"):
        geom = subprocess.run(["slurp"], capture_output=True, text=True).stdout.strip()
        if not geom:
            return False
        argv = [geom if a == "{geom}" else a for a in argv]
    if plan.get("stdout"):
        with open(out, "wb") as f:
            r = subprocess.run(argv, stdout=f)
    else:
        r = subprocess.run(argv, env=env)
    return r.returncode == 0 and os.path.exists(out) and os.path.getsize(out) > 0


def capture_to(out, crop):
    plan = capture_plan(crop)
    if not plan:
        raise SystemExit("No screenshot tool found on this computer: paste a screenshot into the chat instead. "
                         + install_hint())
    if run_capture(plan, out):
        print(out)
        return
    if os.path.exists(out) and os.path.getsize(out) == 0:
        os.remove(out)
    raise SystemExit("Capture cancelled or empty." if crop else "Screen capture failed.")


def install_hint():
    if sys.platform == "darwin" or sys.platform.startswith("win"):
        return "Pasting a screenshot always works."
    return "To enable capture here, install gnome-screenshot (or grim and slurp on Wayland)."


def selftest():
    def pick(crop, plat, *tools):
        return capture_plan(crop, plat, lambda n: "/bin/" + n if n in tools else None)
    assert pick(True, "darwin", "screencapture")["argv"][:2] == ["screencapture", "-i"]
    assert pick(False, "darwin", "screencapture")["argv"][:2] == ["screencapture", "-x"]
    assert pick(True, "darwin") is None
    c = pick(True, "win32", "powershell")
    assert c["name"] == "Snipping Tool" and "-STA" in c["argv"] and "ms-screenclip:" in c["argv"][-1]
    s = pick(False, "win32", "pwsh")
    assert s["argv"][0] == "/bin/pwsh" and "CopyFromScreen" in s["argv"][-1]
    g = pick(True, "linux", "grim", "slurp", "scrot")
    assert g["name"] == "grim+slurp" and g["slurp"] and g["argv"][0] == "grim"
    assert pick(True, "linux", "grim", "maim")["name"] == "maim"  # grim without slurp is skipped
    assert pick(True, "linux", "maim")["argv"] == ["maim", "-s", "{out}"]
    assert pick(False, "linux", "maim")["argv"] == ["maim", "{out}"]
    assert pick(True, "linux", "gnome-screenshot", "maim")["name"] == "gnome-screenshot"
    assert pick(True, "linux", "flameshot")["stdout"]
    assert pick(True, "linux") is None
    print("selftest ok")


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
    plan = capture_plan(True)
    status["details"]["capture"] = (f"Drag-select via {plan['name']}" if plan
                                    else "No screenshot tool found. Paste a screenshot instead. " + install_hint())

    # 3. Screens directory
    os.makedirs(SHOTS, exist_ok=True)
    status["details"]["screens_dir"] = f"Ready: {SHOTS}"

    return status


def last_recent_shot(max_age_seconds=180):
    """Find an astrohuh-* screenshot saved to tools/screens in the last few minutes."""
    if not os.path.isdir(SHOTS):
        return None
    now = time.time()
    candidates = []
    for f in os.listdir(SHOTS):
        if f.startswith(PREFIX) and f.endswith((".png", ".jpg", ".jpeg", ".webp")):
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
        for path in glob.glob(os.path.join(os.path.expanduser("~"), ".claude", "projects", "*", f"{sid}.jsonl")):
            found = None
            try:
                with open(path, encoding="utf-8") as f:
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

    # 1. Explicit --screen: full-screen capture
    if screen:
        return capture_to(os.path.join(SHOTS, f"{PREFIX}{stamp}.png"), crop=False)

    # 2. Explicit --crop: interactive drag-select
    if crop:
        out = os.path.join(SHOTS, f"{PREFIX}{stamp}.png")
        fixture = os.environ.get("ASTROHUH_TEST_FIXTURE")
        if fixture:
            # tests stand in for the drag-select so nothing pops over the live screen
            shutil.copyfile(fixture, out)
            print(out)
            return
        return capture_to(out, crop=True)

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
        out = os.path.join(SHOTS, f"{PREFIX}{stamp}.{ext}")
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


def astrolabe(route, body):
    # The member's own report outbox (Astrolabe's "Tell Dan and Danny" sheet).
    # Desk-only routes on the loopback; a draft is what the member is shown,
    # and save keeps that exact string. Nothing here sends anything off the machine
    import urllib.request
    port = os.environ.get("ASTROLABE_PORT", "27246")
    req = urllib.request.Request(f"http://127.0.0.1:{port}/api/report/{route}",
                                 data=json.dumps(body).encode(), method="POST",
                                 headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r)
    except Exception as e:
        raise SystemExit(f"Astrolabe's reports are not reachable here ({e}). Is the dashboard running?")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] == "check":
        res = check_deps()
        print(json.dumps(res, indent=2))
        sys.exit(0 if res["ready"] else 1)
    elif args[0] == "selftest":
        selftest()
    elif args[0] == "grab":
        grab(screen="--screen" in args, crop="--crop" in args)
    elif args[0] == "file" and len(args) >= 5:
        file_issue(*args[1:6])
    elif args[0] == "draft" and len(args) == 2:
        with open(args[1]) as f:
            words = f.read()
        tab = os.environ.get("ASTROLABE_TAB_ID")
        d = astrolabe("draft", {"words": words, **({"tab": tab} if tab else {})})
        print(json.dumps({"draft": d.get("draft"), "payload_json": d.get("payload_json")}, indent=2))
    elif args[0] == "save" and len(args) == 2:
        print(astrolabe("save", {"draft": args[1]}).get("ref") or "not saved")
    else:
        raise SystemExit(__doc__)
