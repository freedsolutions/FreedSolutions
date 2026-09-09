#!/usr/bin/env node
// new_client.js — scaffold a tenant from `templates/client/` in one command, then prove it.
//
//   node new_client.js --client <slug> --tenant <slug> --lsp "<LSP name>" --dest <clients dir>
//                      [--backoffice <url>] [--folder <looker folder id>]
//                      [--template <dir>] [--no-verify]
//
// It copies the template, fills every placeholder it owns, REFUSES to overwrite an existing
// tenant, and then verifies its own output: `kickoff_check.js --pointer` on the new tenant must
// PASS, and `kickoff_check.js --phase plan` on a fixture kickoff written into the new estate must
// reach its report rather than crash on an empty register. A scaffold that cannot pass the gate
// it ships with is not a scaffold.
//
// Nothing here names a client. The tenant directory is `__tenant__` in the template because
// Windows forbids `<` and `>` in a file name; it is renamed on copy.

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

function arg(name, dflt) {
  const i = process.argv.indexOf('--' + name);
  return i > -1 && process.argv[i + 1] && !process.argv[i + 1].startsWith('--') ? process.argv[i + 1] : dflt;
}
const has = (name) => process.argv.includes('--' + name);

const CLIENT = arg('client', null);
const TENANT = arg('tenant', null);
const LSP = arg('lsp', null);
const DEST = arg('dest', null);
// Optional. The defaults are HUMAN PROMPTS, not placeholders: a multi-word `<…>` never collides
// with a scaffold key, so the guard below stays honest while the four-flag form still works.
const BACKOFFICE = arg('backoffice', 'https://<server>.backoffice.dutchie.com/');
const FOLDER = arg('folder', '<the Looker Shared folder id>');
const TEMPLATE = path.resolve(arg('template', path.join(__dirname, '..', 'templates', 'client')));
const VERIFY = !has('no-verify');

const SLUG = /^[a-z0-9][a-z0-9-]*$/;
const bad = [];
if (!CLIENT || !SLUG.test(CLIENT)) bad.push('--client <slug> (lower-case letters, digits, hyphens)');
if (!TENANT || !SLUG.test(TENANT)) bad.push('--tenant <slug> (lower-case letters, digits, hyphens)');
if (!LSP) bad.push('--lsp "<LSP name>"');
if (!DEST) bad.push('--dest <clients dir>');
if (bad.length) {
  console.error('new_client: missing or invalid ' + bad.join(', '));
  console.error('usage: node new_client.js --client <slug> --tenant <slug> --lsp "<name>" --dest <clients dir>');
  process.exit(2);
}

// The scaffold's OWN placeholders. Anything else written as `<something>` in the template is a
// deliberate prompt to the human filling the tenant in and is left alone.
const MAP = {
  '<TENANT>': TENANT.toUpperCase(),
  '<lsp_name>': LSP,
  '<backoffice_url>': BACKOFFICE,
  '<folder_id>': FOLDER,
  '<client>': CLIENT,
  '<tenant>': TENANT,
  '<date>': new Date().toISOString().slice(0, 10),
};
const KEYS = new Set(Object.keys(MAP).map((k) => k.slice(1, -1).toLowerCase()));

const SRC_TENANT = path.join(TEMPLATE, '__tenant__');
if (!fs.existsSync(SRC_TENANT)) {
  console.error('new_client: no template tenant tree at ' + SRC_TENANT);
  process.exit(2);
}

const CLIENT_DIR = path.join(path.resolve(DEST), CLIENT);
const TENANT_DIR = path.join(CLIENT_DIR, TENANT);

// REFUSE rather than merge. A half-scaffolded tenant over a live one is unrecoverable, and the
// caller who meant to add a second tenant to an existing client still gets that (below).
if (fs.existsSync(TENANT_DIR)) {
  console.error('new_client: REFUSED — ' + TENANT_DIR + ' already exists.');
  console.error('  A scaffold never overwrites a tenant. Move or delete it first, or pick another --tenant.');
  process.exit(1);
}

// The wrapper sync stamps a provenance banner onto every `.md` it copies into `.claude/skills/`.
// That banner is true of the SKILL copy and false of anything scaffolded FROM it: a client's
// DECISIONS.md opening with "do not edit this Claude copy directly" is both wrong and alarming.
// It has already shipped once through `templates/kickoff.md` (one live kickoff carries it), so the
// scaffold strips a LEADING banner — and only a leading one, so a banner discussed in body text
// survives. Proven in gate_selftest.js group F.
// ALL leading banners, not just one: a template that has passed through the sync twice carries two,
// and stripping one would leave the second in a client's file. Caught by running this very
// self-test from the synced wrapper, where the fixture's banner lands on top of the sync's own.
const BANNER = /^(?:<!--\s*Generated from [\s\S]*?-->\s*\n+)+/;
function strip(text) { return text.replace(BANNER, ''); }

function fill(text) {
  const pairs = Object.entries(MAP).sort((a, b) => b[0].length - a[0].length);
  let t = strip(text);
  for (const [ph, val] of pairs) t = t.split(ph).join(val);
  return t;
}

const written = [];
const TEXT = /\.(md|js|sh|py|ps1|json|txt|toml|yml|yaml)$/i;

function copyTree(src, dst) {
  fs.mkdirSync(dst, { recursive: true });
  for (const e of fs.readdirSync(src, { withFileTypes: true })) {
    const s = path.join(src, e.name);
    const d = path.join(dst, e.name);
    if (e.isDirectory()) { copyTree(s, d); continue; }
    if (TEXT.test(e.name)) {
      fs.writeFileSync(d, fill(fs.readFileSync(s, 'utf8').replace(/\r\n/g, '\n')), 'utf8');
    } else {
      fs.copyFileSync(s, d);
    }
    written.push(d);
  }
}

console.log('new_client — scaffolding ' + CLIENT + '/' + TENANT);
copyTree(SRC_TENANT, TENANT_DIR);

// The client roster: written once, never overwritten. A second tenant under an existing client
// gets a line added by hand — the roster carries engagement facts a scaffold cannot know.
const rosterSrc = path.join(TEMPLATE, 'CLAUDE.md');
const rosterDst = path.join(CLIENT_DIR, 'CLAUDE.md');
if (fs.existsSync(rosterDst)) {
  console.log('  · client roster exists — left untouched: ' + rosterDst);
  console.log('    add a Tenants line for `' + TENANT + '/` by hand.');
} else if (fs.existsSync(rosterSrc)) {
  fs.writeFileSync(rosterDst, fill(fs.readFileSync(rosterSrc, 'utf8').replace(/\r\n/g, '\n')), 'utf8');
  written.push(rosterDst);
}
console.log('  ' + written.length + ' file(s) written under ' + CLIENT_DIR);

// ---------- guard: no scaffold placeholder may survive ----------
// A placeholder the scaffold OWNS and did not fill is a broken template, not a prompt. Matched
// case-insensitively so a mis-cased `<Tenant>` in the template is caught rather than shipped.
const leftovers = [];
for (const f of written) {
  if (!TEXT.test(f)) continue;
  const lines = fs.readFileSync(f, 'utf8').split('\n');
  lines.forEach((l, i) => {
    for (const m of l.matchAll(/<([A-Za-z][A-Za-z0-9_]*)>/g)) {
      if (KEYS.has(m[1].toLowerCase())) {
        leftovers.push('  ' + path.relative(CLIENT_DIR, f).replace(/\\/g, '/') + ':' + (i + 1) +
          '  unfilled placeholder <' + m[1] + '>');
      }
    }
  });
}
if (leftovers.length) {
  console.error('\nnew_client: FAILED — ' + leftovers.length + ' unfilled scaffold placeholder(s):');
  console.error(leftovers.join('\n'));
  console.error('The template names a placeholder this scaffold does not fill. Fix the template, not the tenant.');
  process.exit(1);
}
console.log('  ✔ no unfilled scaffold placeholder (' + [...KEYS].map((k) => '<' + k + '>').join(' ') + ')');

// ---------- fixture kickoff, so the plan gate has something to read ----------
const EST = path.join(TENANT_DIR, 'bi-estate');
const kickSrc = path.join(__dirname, '..', 'templates', 'kickoff.md');
const kickDst = path.join(EST, 'scaffold-fixture-kickoff-' + MAP['<date>'] + '.md');
if (fs.existsSync(kickSrc)) {
  // `sync` naming the Dictionary as its artifact is the emptiest LEGAL header: no rules, no
  // boards, so it exercises the register read on an EMPTY register — the shape a fresh estate is
  // in — while still passing the plan gate, which is what makes a red result here mean something.
  const k = strip(fs.readFileSync(kickSrc, 'utf8').replace(/\r\n/g, '\n'))
    .replace('"path": "tile"', '"path": "sync"')
    .replace('"lane": "build"', '"lane": "plan"')
    .replace('"rules": ["R00"]', '"rules": [],\n  "artifacts": ["DATA-DICTIONARY.md"]')
    .replace('"dashboards": ["00000"]', '"dashboards": []')
    .replace('"baseline": "estate-00000.pre-<slug>.json"', '"baseline": ""')
    .replace('# Kickoff — <one-line title: what changes, on which board(s), under which R rows>',
      '# Kickoff — scaffold fixture (delete once the first real change lands)')
    .replace('- <the specific traps this change is exposed to — cite the skill section, do not restate it>',
      '- none; this file exists so the gate has a kickoff to read in a fresh estate.');
  fs.writeFileSync(kickDst, k, 'utf8');
  console.log('  ✔ fixture kickoff written: ' + path.basename(kickDst));
}

if (!VERIFY) {
  console.log('\n--no-verify: skipping the two gate runs. Scaffold at ' + TENANT_DIR);
  process.exit(0);
}

// ---------- prove it ----------
const GATE = path.join(__dirname, 'kickoff_check.js');
function run(label, argv, requirePass) {
  const r = spawnSync(process.execPath, [GATE, ...argv], { encoding: 'utf8' });
  const out = (r.stdout || '') + (r.stderr || '');
  const reached = /All checks passed\.|check\(s\) failed\./.test(out);
  const good = requirePass ? r.status === 0 : reached;
  console.log('  ' + (good ? '✔' : '✘') + ' ' + label + ' — exit ' + r.status +
    (reached ? ', report reached' : ', NO REPORT (it crashed or bailed early)'));
  if (!good) console.log(out.split('\n').map((l) => '      ' + l).join('\n'));
  return good;
}

console.log('\nverifying the scaffold with the gate it ships with:');
let ok = true;
ok = run('--pointer on the new tenant (must PASS)', ['--pointer', TENANT_DIR], true) && ok;
if (fs.existsSync(kickDst)) {
  // Required to PASS, not merely to reach its report. The fixture header is deliberately the
  // emptiest legal one, so a red here is a real defect — the gate reading an empty register
  // wrongly, or a template file the caps now break on — never the fixture's own content.
  ok = run('--phase plan on the fixture kickoff (must PASS on an empty register)',
    [kickDst, '--phase', 'plan'], true) && ok;
}

console.log('');
if (!ok) {
  console.log('FAIL — the scaffold is on disk at ' + TENANT_DIR + ' but does not verify. Read the output above.');
  process.exit(1);
}
console.log('PASS — tenant scaffolded and verified: ' + TENANT_DIR);
console.log('Next: fill the <…> prompts (they are prompts, not defects), then re-run --pointer.');
process.exit(0);
