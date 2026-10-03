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

## Update a skill

The version string is the release. Claude Code only offers an update when the version changes, so a
merged fix with the same version never reaches anyone.

The script does all 3 steps below: `node scripts/bump-version.mjs <skill-id> <patch|minor|major> "<note>"`.
Add `--dry-run` as a 4th argument to preview. It refuses if the two versions already disagree.

1. Bump `version` in `skills/<skill-id>/.claude-plugin/plugin.json`, and set the skill's entry in
   `.claude-plugin/marketplace.json` to the same number. Do it in the same PR as the change. When both
   files set a version, Claude Code uses the `plugin.json` one.
2. Add an entry to `skills/<skill-id>/CHANGELOG.md`, newest first, with the heading `## <new version>`
   and one or two sentences saying what changed. Write it for someone who already has the skill. The
   `Version check` fails a bump with no entry. The Astrolabe Store shows this note to people who have
   the skill.

   ```markdown
   # What changed

   ## 1.7.5
   One or two plain sentences for someone who already has the skill.
   ```

3. Run `node scripts/check-versions.mjs` before you push. It fails if the two numbers differ, if a
   skill's files changed and its version did not, or if a bump has no changelog entry. The
   `Version check` workflow runs it on every PR.
   `node scripts/check-versions.mjs --self-test` checks the script itself.

What people see after the bump on Claude Code: if they turned on auto-update for this marketplace, new
chats load the new version. Otherwise they run `claude plugin marketplace update skills-town`, then
`claude plugin update <skill-id>@skills-town`. `claude plugin list` shows the version they have. On other
agents, `npx skills update` pulls the latest.

Keep command file names and any phrase a launcher or button types the same across updates. Things
outside this repo point at them.


## Rename a skill or command

Renaming an existing skill is a breaking change for installed users, chat ribbons, and automated launchers. When you must rename (for example, to resolve collisions with framework terms or built-in tools):

1. **Rename the folder and commands**:
   - Move `skills/<old-id>` to `skills/<new-id>`.
   - Update command files in `skills/<new-id>/commands/` (e.g. `<new-id>.md`).
   - A shim inside the renamed folder reaches nobody: a plugin's id is its name, so people on the old id never receive another update. If nobody has it installed yet, ship no shim. If people do, keep a small stub plugin under the old name whose only job is to say where it went.
2. **Update identifiers across the package**:
   - In `skills/<new-id>/.claude-plugin/plugin.json`: update `"name": "<new-id>"` and bump `"version"`.
   - In `.claude-plugin/marketplace.json`: update `"name": "<new-id>"`, `"source": "./skills/<new-id>"`, and match the bumped `"version"`.
   - In `skills/<new-id>/SKILL.md`: update frontmatter `name: <new-id>` and any slash command mentions.
3. **Log the rename**:
   - Add a `## <new version>` entry in `skills/<new-id>/CHANGELOG.md` explaining the rename.
4. **Coordinate with the Astrolabe Store**:
   - If the skill has a store listing in Astrolabe (`sbd-astrolabe/dashboard/app/market-catalog.json`), submit a paired PR updating the listing `id`, `command`, `activeCommand`, `handoffCommand`, and install steps to match.
   - Run `node scripts/catalog-listing.mjs <new-id>` and copy its `id`, commands and install lines into the listing rather than retyping them. Anything it prints as `TODO` is copy a human keeps.
5. **Tell people who have the old one**:
   - A rename is a new plugin that shares a repo, so `claude plugin update` does not carry anyone over. They run `claude plugin uninstall <old-id>@skills-town`, then `claude plugin install <new-id>@skills-town`.
   - Say so in the CHANGELOG entry, and in the README table, which must point at the new folder.

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
