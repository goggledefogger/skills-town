# Contributing to skills-town

skills-town is the **public, audited** source of Agent Skills. A skill that lands here is published to
the public Skills Gallery at [skills.roytown.net](https://skills.roytown.net). So the bar is: no
personal data, no half-finished work, works for someone who isn't the author.

> Not ready for the public yet? Keep the skill in the private `claude-skills` source instead. It still
> shows up on the login-gated admin frontend ([skills-admin.roytown.net](https://skills-admin.roytown.net))
> for your own review, and you promote it to public later. See the gallery's
> [`docs/PUBLISHING.md`](https://github.com/goggledefogger/skills-gallery/blob/main/docs/PUBLISHING.md).

## Add a skill

1. Create `skills/<skill-id>/SKILL.md` plus any supporting files. The frontmatter needs at least:

   ```yaml
   ---
   name: My Skill
   description: One clear line on what it does and when to use it.
   allowed-tools: [Read, Bash]   # what it actually touches — drives the gallery's trust panel
   ---
   ```

2. Make sure it clears **the audit gate** (below).
3. Open a PR. On merge to `main`, the `notify-gallery.yml` workflow tells the gallery to rebuild, and
   the skill appears on [skills.roytown.net](https://skills.roytown.net) automatically — no manual
   publish step. (How that works: the gallery README → "How a skill here gets showcased".)

## The audit gate

A skill is only published here once it passes **all** of:

1. **Firewall clean** — no personal/family data, no private paths.
2. **No hardcoded personal config** — vault names, machine paths, account IDs.
3. **Works for someone who isn't the author.**
4. **Actually finished**, not a work in progress.
5. **License clear** (MIT).

The gallery re-runs a fail-closed sanitization firewall on every build as a backstop, but don't rely
on it — the audit is the real gate.

## Trust panel

The gallery derives a skill's trust panel (does it run shell? hit the network? `curl | bash`?) from
your `SKILL.md` — its `allowed-tools` and body. Declare tools honestly; that panel is shown to people
*before* they install, and the gallery never marks a skill "verified" on your behalf.
