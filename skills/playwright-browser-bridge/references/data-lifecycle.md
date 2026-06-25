# Data lifecycle: download → temp → parse → delete

Anything the browser pulls down — an export, a CSV, a PDF, a generated file — is treated as
**transient**. It lands in a temp dir, gets parsed there, and is deleted when you're done.

## The rule
- Downloads/exports go to a temp dir, **never** into the project/repo.
- Parse or aggregate in place; keep only the derived result you actually need.
- Delete the temp dir when finished — don't leave fetched data lingering, and never commit it.

## The helper
`scripts/with-tmp.sh` gives you a self-deleting scratch dir (removed on exit, even on error):

```bash
bash scripts/with-tmp.sh -- python3 parse.py "$BRIDGE_TMP/export.csv"
# $BRIDGE_TMP is created fresh, used by your command, and rm -rf'd on exit.
```

## Why
Fetched web data can contain more than you asked for (other people's info in an export, tokens in a
response, PII in a report). Keeping it on disk or in git is how leaks happen. Transient-by-default
means the only thing that survives is the small, intentional result you extracted.
