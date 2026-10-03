#!/usr/bin/env node
// usage: node scripts/catalog-listing.mjs <skill-id>
// prints an Astrolabe store listing stub: facts this repo knows are filled in, the copy a human writes is "TODO"
import { existsSync } from 'node:fs';

const id = process.argv[2];
const die = (m) => { console.error(`catalog-listing: ${m}`); process.exit(1); };

const dir = `skills/${id}`;
for (const f of [`${dir}/.claude-plugin/plugin.json`, `${dir}/commands/${id}.md`]) {
  if (!id || !existsSync(f)) die(`no skill "${id}" (missing ${f})`);
}
const has = (suffix) => existsSync(`${dir}/commands/${id}-${suffix}.md`);

const T = 'TODO';
const title = id[0].toUpperCase() + id.slice(1).replace(/-/g, ' ');
const ritual = { id, label: title, icon: T, target: T, model: T, phrase: T };
if (has('report')) { ritual.activePhrase = T; }
ritual.command = `/${id}`;
if (has('report')) ritual.activeCommand = `/${id} report`;
if (has('handoff')) Object.assign(ritual, { inPlace: true, handoffPhrase: T, handoffCommand: `/${id} handoff` });
Object.assign(ritual, { accent: T, desc: T });

const listing = {
  id,
  stage: 'staged', // not shown on the shelf until a human flips it to "live"
  audience: [T],
  category: 'skills',
  title,
  label: `${title}, a Claude Code skill`,
  creator: T, agent: T, creatorRole: T,
  verb: 'Made by',
  promise: T,
  minutes: 'a skill for Claude Code',
  price: T,
  desc: T, bio: T,
  cta: 'Get this skill',
  install: {
    preview: `Read the skill first: https://github.com/goggledefogger/skills-town/tree/main/${dir}`,
    steps: [
      'add the plugin marketplace goggledefogger/skills-town and turn on auto-update for it',
      `install ${id} from it`,
      T,
    ],
    updates: 'Auto-updates once that marketplace has it switched on; on any other agent, npx skills update brings the next version.',
    touches: T,
    ritual,
  },
};
console.log(JSON.stringify(listing, null, 2));
