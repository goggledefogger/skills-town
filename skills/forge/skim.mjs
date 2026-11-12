#!/usr/bin/env node
// Forge's reading step: a cheap digest of the open Astrolabe chats.
//   node skim.mjs [dashboard-url] [--skip <tab id>]   every open chat, the member's own words first
//   node skim.mjs [dashboard-url] --tab <tab id>      one chat, its recent turns in full
//   node skim.mjs --self-test
// Reads only; prints to stdout; keeps nothing

const MEMBER_CLIP = 400;   // the member's messages carry the repeated asks, so they get the room
const REPLY_CLIP = 120;    // a reply's opening is enough to tell what was made
const TAB_CAP = 7000;      // ponytail: flat cap per chat; 3000 cut most long chats and hid ideas (2026-11-11)
const MIN_MEMBER_TURNS = 3;

const clip = (s, n) => {
  const one = String(s || '').replace(/\s+/g, ' ').trim();
  return one.length > n ? one.slice(0, n) + '…' : one;
};

export function digest(tab, turns) {
  const mine = turns.filter((t) => t.role === 'user');
  if (mine.length < MIN_MEMBER_TURNS) return '';
  const lines = turns.map((t) => (t.role === 'user'
    ? '- member: ' + clip(t.text, MEMBER_CLIP)
    : '  reply: ' + clip(t.text, REPLY_CLIP)));
  let body = lines.join('\n');
  if (body.length > TAB_CAP) body = body.slice(0, TAB_CAP) + '\n  (cut here; read this chat with --tab for the rest)';
  return `## ${tab.title || 'Untitled'} (tab ${tab.id}, ${mine.length} member messages)\n${body}\n`;
}

async function get(base, path) {
  const res = await fetch(base + path, { signal: AbortSignal.timeout(10000) });
  if (!res.ok) throw new Error(`${path} answered ${res.status}`);
  return res.json();
}

async function main(argv) {
  if (argv.includes('--self-test')) return selfTest();
  const flag = (name) => { const i = argv.indexOf(name); return i >= 0 ? argv[i + 1] : ''; };
  const base = (argv.find((a) => /^https?:\/\//.test(a)) || 'http://127.0.0.1:27246').replace(/\/$/, '');
  const one = flag('--tab');
  const skip = flag('--skip');
  const tabs = (await get(base, '/api/tabs')).tabs || [];

  if (one) {
    const tab = tabs.find((t) => t.id === one) || { id: one, title: '' };
    const { turns = [] } = await get(base, '/api/history?tab=' + encodeURIComponent(one));
    console.log(`# ${tab.title || one}\n`);
    for (const t of turns) console.log(`### ${t.role === 'user' ? 'member' : 'reply'}\n${String(t.text || '').trim()}\n`);
    return;
  }

  let shown = 0;
  const thin = [];
  for (const tab of tabs) {
    if (tab.id === skip) continue;
    let turns = [];
    try { ({ turns = [] } = await get(base, '/api/history?tab=' + encodeURIComponent(tab.id))); }
    catch (e) { thin.push(`${tab.title || tab.id} (could not be read: ${e.message})`); continue; }
    const d = digest(tab, turns);
    if (d) { console.log(d); shown += 1; } else thin.push(tab.title || tab.id);
  }
  console.log(`${shown} chats shown of ${tabs.length} open.`);
  if (thin.length) console.log('Too short to skim, or unreadable: ' + thin.join('; '));
}

function selfTest() {
  const assert = (ok, what) => { if (!ok) { console.error('FAIL: ' + what); process.exit(1); } };
  const turn = (role, text) => ({ role, text });
  const tab = { id: 't1', title: 'Deck' };
  assert(digest(tab, [turn('user', 'a'), turn('assistant', 'b')]) === '', 'a chat with under 3 member messages is skipped');
  const d = digest(tab, [turn('user', 'one\n two'), turn('assistant', 'x'.repeat(500)), turn('user', 'three'), turn('user', 'four')]);
  assert(d.startsWith('## Deck (tab t1, 3 member messages)'), 'the heading names the chat and counts member messages');
  assert(d.includes('- member: one two'), 'member text is flattened to one line');
  assert(d.includes('x'.repeat(REPLY_CLIP) + '…') && !d.includes('x'.repeat(REPLY_CLIP + 1)), 'a long reply is clipped');
  const long = digest(tab, Array.from({ length: 40 }, () => turn('user', 'y'.repeat(390))));
  assert(long.length < TAB_CAP + 200 && long.includes('cut here'), 'a long chat is capped');
  console.log('ok');
}

main(process.argv.slice(2)).catch((e) => { console.error('skim: ' + e.message); process.exit(1); });
