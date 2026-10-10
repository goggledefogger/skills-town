#!/usr/bin/env python3
"""Add the Token Saver helper block to a subagent's context, only when the skill is on.

What it is: a Claude Code SubagentStart command. Claude Code pipes the event JSON to
stdin. If the session transcript shows /token-saver was run, this prints the helper
block as additionalContext so the helper starts with the 3 rules. Otherwise it prints
nothing.

Why it exists: the skill sets disable-model-invocation, so it cannot be preloaded into
a subagent through an agent definition's `skills:` field. A helper would start with
none of the rules.

What it does not do: it keeps no state, opens no file but the transcript named in the
event, selects nothing, filters nothing. Missing or unreadable input prints nothing and
exits 0, which is the safe direction (no block added). It never exits non-zero in the
default mode.

Other modes:
  --print-block   print the helper block (this file is the one source of the text)
  --selftest      run the checks, including that SKILL.md quotes the block verbatim
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HELPER_BLOCK = (
    "Token Saver is on for this job. Read passages, not files: search first "
    "(rg -n or grep -n), then read only the span you need, and take a second "
    "bounded read before you ever load a whole file. Never retry a token or "
    "usage-limit failure. Correctness outranks saving: on anything consequential, "
    "read fully and say so. In your summary, name what you did not read, and give "
    "bytes read against the file's total for each narrow read, or say unavailable."
)

COMMAND_MARKER = "<command-name>/token-saver"  # also covers /token-saver:token-saver[-report]
TYPED_PREFIX = "/token-saver"  # a plain-typed command is the start of the message


def _texts(content):
    """Yield the text pieces of a message content: a string, or a list of blocks."""
    if isinstance(content, str):
        yield content
    elif isinstance(content, list):
        for block in content:
            if isinstance(block, str):
                yield block
            elif isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text")
                if isinstance(text, str):
                    yield text


def activated(transcript_path) -> bool:
    """One pass over the transcript JSONL: did a user entry invoke the skill?"""
    try:
        # errors="replace": one bad byte spoils only its own line, not the scan
        with open(transcript_path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(entry, dict) or entry.get("type") != "user":
                    continue
                message = entry.get("message")
                content = message.get("content") if isinstance(message, dict) else None
                if any(COMMAND_MARKER in t or t.strip().startswith(TYPED_PREFIX)
                       for t in _texts(content)):
                    return True
    except OSError:
        return False
    return False


def run_hook() -> int:
    try:
        event = json.load(sys.stdin)
        path = event.get("transcript_path") if isinstance(event, dict) else None
        if isinstance(path, str) and path and activated(path):
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "SubagentStart",
                "additionalContext": HELPER_BLOCK}}))
    except Exception:  # any failure adds nothing
        pass
    return 0


def selftest() -> int:
    me = Path(__file__).resolve()
    tmp = Path(tempfile.mkdtemp(prefix="ts-helper-"))
    ok = True

    def check(name, cond):
        nonlocal ok
        print(f"{'PASS' if cond else 'FAIL'}  {name}")
        ok = ok and bool(cond)

    def call(stdin_text):
        r = subprocess.run([sys.executable, str(me)], input=stdin_text,
                           capture_output=True, text=True, timeout=10)
        return r.returncode, r.stdout

    def transcript(name, entries):
        p = tmp / name
        p.write_text("\n".join(json.dumps(e) if not isinstance(e, str) else e
                               for e in entries) + "\n")
        return p

    noise = [{"type": "assistant", "message": {"content": "mentions /token-saver"}}, "not json"]
    a = transcript("a.jsonl", noise + [{"type": "user", "message": {"role": "user", "content": "/token-saver"}}])
    b = transcript("b.jsonl", [{"type": "user", "message": {"role": "user", "content": [
        {"type": "text", "text": "<command-name>/token-saver:token-saver</command-name>"}]}}])
    c = transcript("c.jsonl", noise + [{"type": "user", "message": {"role": "user", "content": "hello"}}])

    def user(text):
        return {"type": "user", "message": {"role": "user", "content": text}}

    d = transcript("d.jsonl", [user("look at skills/token-saver/SKILL.md")])
    e = transcript("e.jsonl", [user("do not run /token-saver here")])
    f = transcript("f.jsonl", [user("/token-saver report")])
    g = tmp / "g.jsonl"
    g.write_bytes(b'\xff\xfe bad bytes \x80\n' + json.dumps(user("/token-saver")).encode() + b"\n")

    for label, p in (("activation as string", a), ("activation in text blocks", b),
                     ("plain-typed /token-saver report", f),
                     ("bad bytes on line 1, activation on line 2", g)):
        code, out = call(json.dumps({"hook_event_name": "SubagentStart", "transcript_path": str(p)}))
        try:
            ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        except Exception:
            ctx = None
        check(f"{label} injects the block", code == 0 and ctx == HELPER_BLOCK)
    for label, p in (("no activation", c),
                     ("a message that mentions the skill's file path", d),
                     ("a message that says not to run /token-saver", e)):
        code, out = call(json.dumps({"transcript_path": str(p)}))
        check(f"{label} prints nothing", code == 0 and out == "")
    code, out = call("{not json")
    check("malformed stdin prints nothing, exit 0", code == 0 and out == "")
    code, out = call(json.dumps({"hook_event_name": "SubagentStart"}))
    check("missing transcript_path prints nothing, exit 0", code == 0 and out == "")
    code, out = call(json.dumps({"transcript_path": str(tmp / "nope.jsonl")}))
    check("unreadable transcript prints nothing, exit 0", code == 0 and out == "")
    skill = me.parent.parent / "SKILL.md"
    check("SKILL.md contains the block verbatim",
          skill.is_file() and HELPER_BLOCK in skill.read_text(encoding="utf-8"))

    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    print("selftest: PASS" if ok else "selftest: FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv[1:]:
        raise SystemExit(selftest())
    if "--print-block" in sys.argv[1:]:
        print(HELPER_BLOCK)
        raise SystemExit(0)
    raise SystemExit(run_hook())
