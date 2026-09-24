#!/usr/bin/env python3
"""Grade a token-saver session from an explicit ledger. Arithmetic only, no judgment.

Honesty rules this enforces mechanically:
  - A number that was not supplied prints as `unavailable`, never inferred.
  - "Avoided" counts only bytes in files whose real total size was recorded, so
    the baseline is a fact about the file, not a guess about an un-run session.
  - A session where the skill was not used, or that recorded nothing, grades
    UNSCORED on both axes. UNSCORED must never render as a pass.
  - Any recorded incident forces risk=HARM and efficiency grade F. A cheap wrong
    answer is not a saving.

Ledger JSON (every key optional; missing keys degrade the report, never fake it):
  {"used": true,
   "reads":       [{"path": "a.py", "bytes_read": 900, "bytes_total": 40000}],
   "calls":       [{"model": "opus", "in_tokens": 1200, "out_tokens": 300}],
   "retries": 0, "corrections": 1, "tool_output_bytes": 52000,
   "incidents":   [{"severity": "harm", "note": "answered from a partial read"}],
   "price_in_per_mtok": 15.0}

Usage:
  report.py --ledger ledger.json [--json]
  report.py --ledger ledger.json --log ~/some-dir/token-saver-cards.jsonl
  report.py --selftest

--log appends the summary JSON as one line to the given file (opt-in, per
invocation — the default remains: nothing touches disk). A failed --log write
errors loudly and exits nonzero, never a silent skip: a dashboard may trust
these cards only because a failed write cannot masquerade as "no cards logged".

Persistence decision, 2026-08-08: this skill's "no state file" rule came from
an audit where the machinery that broke was content SELECTION (a relevance
filter silently returning an empty packet). An opt-in, append-only line of the
grader's own output has the opposite failure direction — it can only fail loud
— and exists so a dashboard or log of your own can show reading-discipline results
beside its other numbers. The default behavior is unchanged; a session that
never passes --log writes nothing, exactly as before.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BYTES_PER_TOKEN = 4  # crude divisor, labelled ESTIMATED everywhere it is used
GRADE_BANDS = ((0.10, "A"), (0.25, "B"), (0.50, "C"), (0.75, "D"))


def _num(value) -> int | None:
    """Accept only real, non-negative numbers. Anything else is unavailable."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(value) if value >= 0 else None


def summarize(ledger: dict) -> dict:
    if not isinstance(ledger, dict):
        raise ValueError("ledger must be a JSON object")

    reads = [r for r in ledger.get("reads") or [] if isinstance(r, dict)]
    calls = [c for c in ledger.get("calls") or [] if isinstance(c, dict)]
    # An incident the caller supplied must never vanish on a shape mismatch —
    # a malformed entry coerces to harm instead of silently improving the grade.
    incidents = [
        i if isinstance(i, dict) else {"severity": "harm", "note": str(i)}
        for i in ledger.get("incidents") or []
    ]
    retries = _num(ledger.get("retries")) or 0
    corrections = _num(ledger.get("corrections")) or 0
    used = ledger.get("used")

    # Only reads with BOTH numbers can support a ratio; the rest are counted and named.
    scorable = [
        r for r in reads
        if _num(r.get("bytes_read")) is not None and _num(r.get("bytes_total")) is not None
    ]
    read_bytes = sum(_num(r["bytes_read"]) for r in scorable)
    total_bytes = sum(_num(r["bytes_total"]) for r in scorable)
    unscorable = len(reads) - len(scorable)
    ratio = (read_bytes / total_bytes) if total_bytes > 0 else None
    avoided = max(0, total_bytes - read_bytes) if total_bytes > 0 else None

    in_tok = [t for t in (_num(c.get("in_tokens")) for c in calls) if t is not None]
    out_tok = [t for t in (_num(c.get("out_tokens")) for c in calls) if t is not None]
    tokens_complete = bool(calls) and len(in_tok) == len(calls) and len(out_tok) == len(calls)

    # Unlabelled severity defaults to harm: an agent unsure enough to omit the
    # label is not the right party to be granted the benefit of the doubt.
    harmed = any(str(i.get("severity", "harm")).lower() not in {"low", "minor"} for i in incidents)

    # --- risk: four states, and the absent case is never CLEAN ---
    if used is False:
        risk, why = "UNSCORED", "skill was not used this session"
    elif harmed:
        risk, why = "HARM", f"{len(incidents)} incident(s) recorded"
    # A missing read ratio leaves efficiency ungraded, not safety: recorded
    # corrections and incidents are facts, and dropping them hides a slip
    elif not reads and not calls and not (incidents or corrections or retries):
        risk, why = "UNSCORED", "ledger recorded no reads and no calls"
    elif incidents or corrections or retries:
        bits = []
        if corrections:
            bits.append(f"{corrections} second read(s) after a miss")
        if retries:
            bits.append(f"{retries} retry(ies)")
        if incidents:
            bits.append(f"{len(incidents)} low-severity incident(s)")
        risk, why = "CORRECTION", ", ".join(bits)
    else:
        risk, why = "CLEAN", "no corrections, retries, or incidents recorded"

    # --- efficiency grade: mechanical, and refuses when it has no ratio ---
    if risk == "UNSCORED" or ratio is None:
        grade, basis = "UNSCORED", "no read ratio available"
    elif harmed or retries:
        grade, basis = "F", "incident or limit-retry recorded"
    else:
        grade = "F"
        for cap, letter in GRADE_BANDS:
            if ratio <= cap:
                grade = letter
                break
        basis = f"read {ratio:.1%} of recorded source bytes"
        if corrections:
            basis += f", {corrections} correction(s)"

    tool_bytes = _num(ledger.get("tool_output_bytes"))
    price = ledger.get("price_in_per_mtok")
    price = float(price) if isinstance(price, (int, float)) and not isinstance(price, bool) else None
    cost_avoided = (
        round((avoided / BYTES_PER_TOKEN) / 1_000_000 * price, 4)
        if avoided is not None and price is not None
        else None
    )

    return {
        "efficiency": {
            "grade": grade,
            "basis": basis,
            "read_ratio": ratio,
            "tool_output_tokens_estimated": (tool_bytes // BYTES_PER_TOKEN) if tool_bytes else None,
            "bytes_read": read_bytes if scorable else None,
            "bytes_available": total_bytes if scorable else None,
            "bytes_avoided": avoided,
            "tokens_avoided_estimated": (avoided // BYTES_PER_TOKEN) if avoided else None,
            "cost_avoided_usd_estimated": cost_avoided,
            "calls": len(calls) or None,
            "input_tokens": sum(in_tok) if tokens_complete else None,
            "output_tokens": sum(out_tok) if tokens_complete else None,
            "reads_without_totals": unscorable or None,
        },
        "risk": {"state": risk, "why": why},
    }


def render(s: dict) -> str:
    """Plain-language card: 3 KPIs (grade, saved, safety), zero jargon."""
    e, r = s["efficiency"], s["risk"]

    if e["grade"] == "UNSCORED":
        grade_line = "not graded — nothing was measured, so no credit claimed"
    elif e["grade"] == "F":
        grade_line = "F — something went wrong, so no efficiency credit (see safety)"
    else:
        skipped_pct = round((1 - e["read_ratio"]) * 100)
        grade_line = f"{e['grade']} — read just what it needed, skipping {skipped_pct}% of the file content"

    if e["tokens_avoided_estimated"]:
        saved_line = f"~{e['tokens_avoided_estimated']:,} tokens of reading avoided (estimate)"
        if e["cost_avoided_usd_estimated"] is not None:
            saved_line += f", roughly ${e['cost_avoided_usd_estimated']}"
    else:
        saved_line = "nothing measurable"

    if e["input_tokens"] is not None:
        spent_line = (
            f"{e['calls']} model call(s), {e['input_tokens']:,} tokens in / {e['output_tokens']:,} out"
        )
    else:
        rough = (e["bytes_read"] or 0) // BYTES_PER_TOKEN + (e["tool_output_tokens_estimated"] or 0)
        spent_line = (
            f"~{rough:,} tokens of recorded reading and command output (rough estimate; model token counts not reported)"
            if rough
            else "unknown — nothing recorded"
        )

    safety_words = {
        "CLEAN": "clean — no corners cut, nothing went wrong",
        "CORRECTION": f"ok — {r['why']}, caught and corrected",
        "HARM": f"PROBLEM — {r['why']}",
        "UNSCORED": "unknown — the skill wasn't used or nothing was recorded",
    }

    lines = [
        "token-saver report card",
        f"  grade    {grade_line}",
        f"  saved    {saved_line}",
        f"  spent    {spent_line}",
        f"  safety   {safety_words[r['state']]}",
    ]
    if e["tool_output_tokens_estimated"]:
        lines.append(
            f"  note     ~{e['tool_output_tokens_estimated']:,} of the spent tokens were command output, "
            "which reading discipline can't shrink"
        )
    notes = []
    if e["reads_without_totals"]:
        notes.append(f"{e['reads_without_totals']} read(s) had no size on record, left out of the grade")
    if r["state"] == "UNSCORED":
        notes.append("an unmeasured session is not a good one, it is an unknown one")
    for n in notes:
        lines.append(f"  note     {n}")
    return "\n".join(lines)


def selftest() -> int:
    # good session
    s = summarize({"used": True, "reads": [{"bytes_read": 500, "bytes_total": 40000}]})
    assert s["efficiency"]["grade"] == "A", s
    assert s["risk"]["state"] == "CLEAN", s
    assert s["efficiency"]["bytes_avoided"] == 39500

    # negative control: unused session must not grade well
    s = summarize({"used": False, "reads": [{"bytes_read": 1, "bytes_total": 99999}]})
    assert s["risk"]["state"] == "UNSCORED" and s["efficiency"]["grade"] == "UNSCORED", s

    # empty ledger is UNSCORED, never CLEAN
    assert summarize({})["risk"]["state"] == "UNSCORED"

    # an incident forces F/HARM even with a perfect ratio
    s = summarize({"used": True, "reads": [{"bytes_read": 10, "bytes_total": 100000}],
                   "incidents": [{"severity": "harm", "note": "wrong answer"}]})
    assert s["efficiency"]["grade"] == "F" and s["risk"]["state"] == "HARM", s

    # a limit retry forces F
    s = summarize({"used": True, "reads": [{"bytes_read": 10, "bytes_total": 100000}], "retries": 1})
    assert s["efficiency"]["grade"] == "F", s

    # corrections downgrade risk but keep the grade band
    s = summarize({"used": True, "reads": [{"bytes_read": 500, "bytes_total": 40000}], "corrections": 1})
    assert s["risk"]["state"] == "CORRECTION" and s["efficiency"]["grade"] == "A", s

    # missing token counts stay unavailable, never summed from partial data
    s = summarize({"used": True, "reads": [{"bytes_read": 5, "bytes_total": 100}],
                   "calls": [{"in_tokens": 10, "out_tokens": 5}, {"model": "haiku"}]})
    assert s["efficiency"]["input_tokens"] is None, s

    # a read with no recorded total cannot inflate the ratio
    s = summarize({"used": True, "reads": [{"bytes_read": 500, "bytes_total": 1000},
                                           {"bytes_read": 9_000_000}]})
    assert s["efficiency"]["bytes_read"] == 500 and s["efficiency"]["reads_without_totals"] == 1, s

    # no price means no dollar figure
    assert summarize({"used": True, "reads": [{"bytes_read": 1, "bytes_total": 2}]}
                     )["efficiency"]["cost_avoided_usd_estimated"] is None

    # bad types are rejected, not coerced
    s = summarize({"used": True, "reads": [{"bytes_read": "lots", "bytes_total": 100}]})
    assert s["efficiency"]["grade"] == "UNSCORED", s

    # a string incident coerces to harm, never silently vanishes (found live 2026-07-29:
    # a filtered-out incident produced grade A over an honestly-recorded problem)
    s = summarize({"used": True, "reads": [{"bytes_read": 10, "bytes_total": 100000}],
                   "incidents": ["hand-wrote the report card instead of running the grader"]})
    assert s["efficiency"]["grade"] == "F" and s["risk"]["state"] == "HARM", s

    # an incident dict without a severity label also defaults to harm
    s = summarize({"used": True, "reads": [{"bytes_read": 10, "bytes_total": 100000}],
                   "incidents": [{"note": "no severity given"}]})
    assert s["risk"]["state"] == "HARM", s

    # explicitly low-severity incidents downgrade to CORRECTION, not HARM
    s = summarize({"used": True, "reads": [{"bytes_read": 10, "bytes_total": 100000}],
                   "incidents": [{"severity": "low", "note": "cosmetic"}]})
    assert s["risk"]["state"] == "CORRECTION", s

    # tool output shows up as estimated spend plus its own note
    s = summarize({"used": True, "reads": [{"bytes_read": 400, "bytes_total": 40000}],
                   "tool_output_bytes": 52000})
    assert s["efficiency"]["tool_output_tokens_estimated"] == 13000, s
    card = render(s)
    assert "13,000" in card and "command output" in card, card

    # recorded corrections and a low incident keep their safety state even with no
    # read ratio (found live 2026-09-24: the card said "nothing was recorded" over both)
    s = summarize({"used": True, "corrections": 2, "tool_output_bytes": 160000,
                   "incidents": [{"severity": "low", "note": "stale count, corrected"}]})
    assert s["risk"]["state"] == "CORRECTION" and s["efficiency"]["grade"] == "UNSCORED", s
    assert "wasn't used" not in render(s), render(s)
    s = summarize({"used": True, "incidents": [{"severity": "harm", "note": "x"}]})
    assert s["risk"]["state"] == "HARM", s

    # render never crashes and never lets UNSCORED read as a pass
    for ledger in ({}, {"used": True, "reads": [{"bytes_read": 500, "bytes_total": 40000}]},
                   {"used": True, "reads": [{"bytes_read": 10, "bytes_total": 100}],
                    "incidents": [{"severity": "harm", "note": "x"}]}):
        card = render(summarize(ledger))
        assert card.startswith("token-saver report card"), card
    assert "unknown" in render(summarize({})), "UNSCORED must render as unknown"

    # --log: one appended line per invocation, none without the flag, loud on failure
    import contextlib
    import io
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="ts-log-"))
    ledger_f = tmp / "ledger.json"
    ledger_f.write_text(json.dumps(
        {"used": True, "reads": [{"bytes_read": 5, "bytes_total": 100}]}))
    cards = tmp / "cards.jsonl"
    with contextlib.redirect_stdout(io.StringIO()):
        assert main(["--ledger", str(ledger_f), "--log", str(cards)]) == 0
        assert main(["--ledger", str(ledger_f), "--log", str(cards)]) == 0
        assert main(["--ledger", str(ledger_f)]) == 0
    lines = cards.read_text().splitlines()
    assert len(lines) == 2, lines
    rec = json.loads(lines[0])
    assert rec["kind"] == "token-saver-card" and rec["efficiency"]["grade"] == "A", rec
    blocked = tmp / "ledger.json" / "cards.jsonl"  # parent is a file: must fail loud
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as err:
        assert main(["--ledger", str(ledger_f), "--log", str(blocked)]) == 2
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)

    print("selftest: 18 checks passed")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--ledger", type=Path, help="Ledger JSON file. Omit to read stdin.")
    p.add_argument("--json", action="store_true", help="Emit the report as JSON.")
    p.add_argument("--log", type=Path, metavar="PATH",
                   help="Append the summary JSON as one line to PATH (opt-in; "
                        "fails loud and nonzero on any write error).")
    p.add_argument("--selftest", action="store_true", help="Run assertions and exit.")
    args = p.parse_args(argv)

    if args.selftest:
        return selftest()
    try:
        raw = args.ledger.read_text(encoding="utf-8") if args.ledger else sys.stdin.read()
        summary = summarize(json.loads(raw))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return p.exit(2, f"report.py: {exc}\n") or 2
    print(json.dumps(summary, indent=2) if args.json else render(summary))
    if args.log:
        import datetime
        import socket
        try:
            args.log.parent.mkdir(parents=True, exist_ok=True)
            line = json.dumps({
                "at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                "host": socket.gethostname().split(".")[0],
                "kind": "token-saver-card",
                **summary,
            }, separators=(",", ":"))
            with open(args.log, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except OSError as exc:
            print(f"report.py: --log write FAILED ({exc}) — this card is NOT "
                  f"recorded", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
