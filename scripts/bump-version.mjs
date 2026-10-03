#!/usr/bin/env node
// usage: node scripts/bump-version.mjs <skill-id> <patch|minor|major> "<note>" [--dry-run]
// edits plugin.json, marketplace.json and CHANGELOG.md so scripts/check-versions.mjs passes
import { existsSync, readFileSync, writeFileSync } from 'node:fs';

const MARKETPLACE = '.claude-plugin/marketplace.json';
const [id, kind, note, flag] = process.argv.slice(2);
const die = (m) => { console.error(`bump-version: ${m}`); process.exit(1); };

const dir = `skills/${id}`;
const pjPath = `${dir}/.claude-plugin/plugin.json`;
const clPath = `${dir}/CHANGELOG.md`;
if (!id || !existsSync(pjPath)) die(`no skill "${id}" (missing ${pjPath})`);
if (!['patch', 'minor', 'major'].includes(kind)) die(`bump kind must be patch, minor or major, got "${kind}"`);
if (!note || !note.trim()) die('the note saying what changed is missing');
if (flag && flag !== '--dry-run') die(`unknown 4th argument "${flag}"`);

const pj = readFileSync(pjPath, 'utf8');
const mk = readFileSync(MARKETPLACE, 'utf8');
const entry = JSON.parse(mk).plugins.find((p) => p.name === id);
if (!entry) die(`${MARKETPLACE} has no entry named "${id}"`);
const old = JSON.parse(pj).version;
if (old !== entry.version) die(`plugin.json says ${old} but marketplace.json says ${entry.version}; make them equal first`);
const m = /^(\d+)\.(\d+)\.(\d+)$/.exec(old || '');
if (!m) die(`current version "${old}" is not x.y.z`);
const [a, b, c] = m.slice(1).map(Number);
const next = kind === 'major' ? `${a + 1}.0.0` : kind === 'minor' ? `${a}.${b + 1}.0` : `${a}.${b}.${c + 1}`;

// swap only the version value, so formatting and key order stay put
const verRe = /("version":\s*")[^"]*(")/;
const newPj = pj.replace(verRe, `$1${next}$2`);
const at = mk.indexOf(`"name": "${id}"`);
const end = mk.indexOf('\n    }', at);
const newMk = mk.slice(0, at) + mk.slice(at, end).replace(verRe, `$1${next}$2`) + mk.slice(end);

const section = `## ${next}\n${note.trim()}\n`;
let cl = existsSync(clPath) ? readFileSync(clPath, 'utf8') : '# What changed\n';
const first = cl.search(/^## /m); // newest first
cl = first < 0 ? `${cl.trimEnd()}\n\n${section}` : `${cl.slice(0, first)}${section}\n${cl.slice(first)}`;

if (flag !== '--dry-run') { writeFileSync(pjPath, newPj); writeFileSync(MARKETPLACE, newMk); writeFileSync(clPath, cl); }
console.log(`${id} ${old} -> ${next}`);
