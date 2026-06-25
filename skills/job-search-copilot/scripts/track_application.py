#!/usr/bin/env python3
"""Track job applications in a local JSON file — add, update status, and list active-first.

Stdlib only. Your application data never leaves your machine. Status only advances when YOU say
so (the skill never marks something 'applied' on its own).

Usage:
  python3 track_application.py add --company "Northwind" --role "Backend Engineer" [--url ... --notes ...]
  python3 track_application.py status <id> <new-status>      # e.g. status 3 applied
  python3 track_application.py note <id> "called back 6/24"
  python3 track_application.py list [--all]                  # active-first; --all includes closed
  python3 track_application.py show <id>

Tracker file defaults to ./applications.json (override with --file).
"""
import argparse
import json
import os
import sys

# Lifecycle, ordered. "applied" and beyond require an explicit user action.
STATUSES = ["interested", "drafting", "applied", "screening", "interview", "offer", "rejected", "withdrawn"]
CLOSED = {"rejected", "withdrawn"}
# Active sorts before closed; within active, later-stage first.
RANK = {s: i for i, s in enumerate(STATUSES)}


def load(path):
    if not os.path.exists(path):
        return {"next_id": 1, "apps": []}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def find(data, app_id):
    for a in data["apps"]:
        if a["id"] == int(app_id):
            return a
    sys.exit(f"[!] no application with id {app_id}")


def main():
    ap = argparse.ArgumentParser(description="Track job applications locally.")
    ap.add_argument("--file", default="applications.json")
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add")
    a.add_argument("--company", required=True)
    a.add_argument("--role", required=True)
    a.add_argument("--url", default="")
    a.add_argument("--notes", default="")
    a.add_argument("--status", default="interested", choices=STATUSES)

    s = sub.add_parser("status")
    s.add_argument("id")
    s.add_argument("new_status", choices=STATUSES)

    n = sub.add_parser("note")
    n.add_argument("id")
    n.add_argument("text")

    lst = sub.add_parser("list")
    lst.add_argument("--all", action="store_true")

    sh = sub.add_parser("show")
    sh.add_argument("id")

    args = ap.parse_args()
    data = load(args.file)

    if args.cmd == "add":
        app = {"id": data["next_id"], "company": args.company, "role": args.role,
               "url": args.url, "status": args.status, "notes": [args.notes] if args.notes else []}
        data["apps"].append(app)
        data["next_id"] += 1
        save(args.file, data)
        print(f"[ok] added #{app['id']}: {app['role']} @ {app['company']} ({app['status']})")

    elif args.cmd == "status":
        app = find(data, args.id)
        old = app["status"]
        app["status"] = args.new_status
        save(args.file, data)
        flag = "  ← you confirmed you submitted this" if args.new_status == "applied" else ""
        print(f"[ok] #{app['id']} {app['company']}: {old} → {args.new_status}{flag}")

    elif args.cmd == "note":
        app = find(data, args.id)
        app.setdefault("notes", []).append(args.text)
        save(args.file, data)
        print(f"[ok] note added to #{app['id']}")

    elif args.cmd == "show":
        app = find(data, args.id)
        print(json.dumps(app, indent=2))

    elif args.cmd == "list":
        apps = data["apps"]
        if not args.all:
            apps = [a for a in apps if a["status"] not in CLOSED]
        apps = sorted(apps, key=lambda a: (a["status"] in CLOSED, -RANK.get(a["status"], 0), a["company"].lower()))
        if not apps:
            print("(no applications yet)")
            return
        for a in apps:
            print(f"  #{a['id']:>2}  {a['status']:<10}  {a['role']} @ {a['company']}")


if __name__ == "__main__":
    main()
