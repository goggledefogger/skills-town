#!/usr/bin/env node
// usage: node scripts/check-versions.mjs [base-ref]   (default origin/main, or env BASE_REF)
//        node scripts/check-versions.mjs --self-test
import { execFileSync } from 'node:child_process';
import { existsSync, readFileSync, mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert';

const MARKETPLACE = '.claude-plugin/marketplace.json';
const git = (...a) => execFileSync('git', a, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
const tryGit = (...a) => { try { return git(...a); } catch { return null; } };
const norm = (s) => s.replace(/^\.\//, '').replace(/\/$/, '');

// plugin.json wins when both set a version, so it is the first place to look
function versionOf(entry, readFile) {
  const pj = readFile(`${norm(entry.source)}/.claude-plugin/plugin.json`);
  return (pj && JSON.parse(pj).version) || entry.version;
}

function check(base) {
  const errors = [];
  const now = JSON.parse(readFileSync(MARKETPLACE, 'utf8')).plugins.filter((p) => typeof p.source === 'string');
  const readNow = (f) => (existsSync(f) ? readFileSync(f, 'utf8') : null);

  for (const p of now) {
    const pj = readNow(`${norm(p.source)}/.claude-plugin/plugin.json`);
    const v = pj && JSON.parse(pj).version;
    if (v && p.version && v !== p.version) {
      errors.push(`${p.name}: marketplace.json says ${p.version} but plugin.json says ${v}. Make them equal. Claude Code uses plugin.json.`);
    }
  }

  const root = tryGit('merge-base', base, 'HEAD');
  if (!root) return [...errors, `Cannot find base ref "${base}". Fetch it or pass another ref.`];
  const readBase = (f) => tryGit('show', `${root}:${f}`);
  const baseMarket = JSON.parse(readBase(MARKETPLACE) || '{"plugins":[]}').plugins;
  const changed = git('diff', '--name-only', root).split('\n').filter(Boolean);

  for (const p of now) {
    const dir = norm(p.source);
    if (!changed.some((f) => f.startsWith(`${dir}/`))) continue;
    const old = baseMarket.find((b) => b.name === p.name);
    if (!old || !tryGit('ls-tree', root, `${dir}/`)) continue; // new skill
    if (versionOf(old, readBase) === versionOf(p, readNow)) {
      errors.push(`${p.name}: files under ${dir}/ changed but the version is still ${versionOf(p, readNow)}. Bump "version" in ${dir}/.claude-plugin/plugin.json and in ${MARKETPLACE}, or users never get this change.`);
    }
  }
  return errors;
}

function selfTest() {
  const tmp = mkdtempSync(join(tmpdir(), 'check-versions-'));
  const script = fileURLToPath(import.meta.url);
  const run = () => { try { execFileSync('node', [script, 'main'], { cwd: tmp, stdio: 'ignore' }); return 0; } catch (e) { return e.status; } };
  const sh = (...a) => execFileSync('git', a, { cwd: tmp, stdio: 'ignore' });
  const put = (f, s) => { mkdirSync(dirname(join(tmp, f)), { recursive: true }); writeFileSync(join(tmp, f), s); };
  const market = (v) => JSON.stringify({ plugins: [{ name: 'a', source: './skills/a', version: v }] });
  const plugin = (v) => JSON.stringify({ name: 'a', version: v });
  try {
    sh('init', '-q', '-b', 'main');
    sh('config', 'user.email', 't@t'); sh('config', 'user.name', 't');
    put(MARKETPLACE, market('1.0.0')); put('skills/a/.claude-plugin/plugin.json', plugin('1.0.0')); put('skills/a/SKILL.md', 'one');
    sh('add', '.'); sh('commit', '-q', '-m', 'base');
    sh('checkout', '-q', '-b', 'pr');
    put('README.md', 'outside skills'); sh('add', '.'); sh('commit', '-q', '-m', 'docs');
    assert.equal(run(), 0, 'change outside skills/ should pass');
    put('skills/a/SKILL.md', 'two'); sh('add', '.'); sh('commit', '-q', '-m', 'change');
    assert.notEqual(run(), 0, 'unbumped change should fail');
    put(MARKETPLACE, market('1.0.1')); put('skills/a/.claude-plugin/plugin.json', plugin('1.0.1')); sh('add', '.'); sh('commit', '-q', '-m', 'bump');
    assert.equal(run(), 0, 'bumped change should pass');
    put(MARKETPLACE, market('1.0.2')); sh('add', '.'); sh('commit', '-q', '-m', 'mismatch');
    assert.notEqual(run(), 0, 'marketplace/plugin.json mismatch should fail');
    console.log('self-test ok');
  } finally { rmSync(tmp, { recursive: true, force: true }); }
}

if (process.argv[2] === '--self-test') selfTest();
else {
  const errors = check(process.argv[2] || process.env.BASE_REF || 'origin/main');
  if (errors.length) { console.error(errors.map((e) => `ERROR ${e}`).join('\n')); process.exit(1); }
  console.log('versions ok');
}
