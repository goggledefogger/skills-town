# skills-town

Public, audited Agent Skills you can install across tools. Every skill here passed a
sanitization + readiness audit before it was published — no personal data, no half-finished
work, works for someone who isn't me.

These are showcased at the [Skills Gallery](https://skills.roytown.net). Private,
in-progress skills live elsewhere and are not published here.

## Install

```bash
npx skills add goggledefogger/skills-town
```

Or add as a Claude Code plugin marketplace:

```
/plugin marketplace add goggledefogger/skills-town
```

## Skills

| Skill | What it does |
|---|---|
| [job-search-copilot](skills/job-search-copilot/) | A careful job-hunt helper — drafts in your voice, explains every application field, fills forms for your review (never submits on its own). |
| [walk-and-talk](skills/walk-and-talk/) | Work on any project by voice while you walk — hands-free capture or real work, nothing sent without you. |
| [browser-ai-bridge](skills/browser-ai-bridge/) | Walk through your app with an AI helper in a real browser it can read and act on while you talk. |
| [playwright-browser-bridge](skills/playwright-browser-bridge/) | The shared browser layer the two browser skills build on — careful by default. |

## The audit gate

A skill is only published here once it passes all of:

1. Firewall clean — no personal/family data, no private paths
2. No hardcoded personal config — vault names, machine paths, account IDs
3. Works for someone who isn't the author
4. Actually finished, not a work in progress
5. License clear (MIT)
