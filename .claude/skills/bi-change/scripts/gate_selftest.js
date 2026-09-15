#!/usr/bin/env node
// gate_selftest.js — the self-test for kickoff_check.js's P2 size caps and P3 seal grain.
//
//   node <skill>/scripts/gate_selftest.js [path/to/kickoff_check.js]
//
// Exit 0 = every assertion held. Exit 1 = at least one failed; the report names it.
//
// WHY THIS EXISTS. A gate check can sit in the file for weeks reporting nothing and never actually
// fire — that happened here: the Open-for-Adam check was inert on every run for days. So each check
// is proven in BOTH directions: a clean fixture must report ✔ with the count we expect, and a
// fixture broken in exactly one place must report ✘ with the count we expect. A check that cannot
// be made to fail has not been tested.
//
// The groups, in the order they were added (E and G predate F and H; J is the newest — and note
// that the 2026-09-14 handoff calls J's cases E1–E6, which collides with the register-header group
// already holding that letter; renaming a cited label is worse than a gap, so they are J1–J6 here):
//   A. each size cap — green when clean, red when broken (under `--caps fail`), and never red
//      under `--caps info`, which is what "report-only for one run, then enforce" rests on.
//   B. the seal grain — an OPEN kickoff with in-grain drift must STILL FAIL (the regression guard),
//      while a closed kickoff, or drift outside header.rules, is reported and not failed.
//   C. the per-cap DEFAULT enforcement, run with no flag at all. Group A passes an explicit
//      `--caps`, which overrides the defaults, so it proves the mechanism but not the setting.
//   D. `--pointer <tenant dir>` — the kickoff-free scaffold check: it runs with no kickoff, scores
//      C3–C8 and nothing that needs a register or a header, still reddens on an enforced breach,
//      and finds the estate by the Dictionary rather than by the folder's name.
//   E. the REGISTER HEADER shape — both the 5-column and the 8-column register parse, to the count
//      their own header row declares, and NOT BUILT is read out of segment 2 and nowhere else.
//   F. the SCAFFOLD · G. C8 template conformance · H. the two template placeholders.
//   J. the DECISIONS record — a minted rule's ruling is on file and names this kickoff (D1), and
//      every register rule has a ruling somewhere (D2).
//
// Every case runs at `--phase plan`, which stops before the estate/scope/scan machinery — the caps
// and the seal check both run ahead of that early return, so the fixture needs no Looker JSON.

const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');
const { spawnSync } = require('child_process');

// The gate is the sibling of this file unless one is named explicitly, so the self-test runs the
// same way from the skill source and from a synced wrapper copy.
const GATE = path.resolve(process.argv[2] || path.join(__dirname, 'kickoff_check.js'));
if (!fs.existsSync(GATE)) { console.error('gate_selftest: no kickoff_check.js at ' + GATE); process.exit(2); }

// Fixtures live in a fresh temp dir, never beside the skill — a self-test must not be able to
// leave debris in a tracked tree, and two concurrent runs must not collide.
const ROOT = fs.mkdtempSync(path.join(os.tmpdir(), 'bi-change-selftest-'));
const CLIENT = path.join(ROOT, 'client');
const EST = path.join(CLIENT, 'bi-estate');
// Clean up on EVERY exit path, including a thrown assertion — otherwise a crash leaves a temp
// estate behind on each run.
process.on('exit', () => { try { fs.rmSync(ROOT, { recursive: true, force: true }); } catch (e) { /* best effort */ } });

// Same normalisation the gate seals with.
const sha1 = s => crypto.createHash('sha1').update(s.replace(/\s+/g, ' ').trim()).digest('hex').slice(0, 12);

const RULE1 = 'Fixture rule one, short and well under the cap.';
const RULE2 = 'Fixture rule two, also short.';

// Register header shapes. The gate takes its expected segment count from the register's OWN header
// row, never a constant — so BOTH shapes this estate has carried must parse, and on both, SEGMENT 2
// is the impl cell the NOT BUILT check reads (`Implementation` before Phase B, `Surface` after).
// `v1` is the pre-compaction 5-column register; `v2` is the 8-column contract Phase B left behind.
// Group E proves both, in both directions: parse to the right segment count, and read NOT BUILT out
// of segment 2 rather than out of whatever column happens to sit there.
// `v1` has NO `Since` column at all, which is itself a case D1 must handle: it finds the column by
// header NAME, so on v1 it can only report that a mint is indistinguishable from a citation.
const HEADERS = {
  v1: {
    cols: ['Rule', 'Key', 'Implementation', 'Ruled'],
    cells: (txt, impl) => [txt, 'per product', impl, '2026-09-08'],
  },
  v2: {
    cols: ['Rule', 'Grain', 'Surface', 'Status', 'Since', 'Links', 'Record'],
    cells: (txt, impl, since) => [txt, 'per product', impl, 'ACTIVE', since || '2026-09-09', '—', 'fx-kickoff-2026-09-08.md'],
  },
};
// A rule is `[id, text, impl, since]`. `since` reaches the `Since` column on v2 and is ignored by
// v1, which has no such column — deliberately, so the two shapes stay honestly different.
function dd(rules, shape = 'v1') {
  const h = HEADERS[shape];
  return [
    '# Fixture Data Dictionary',
    '',
    'Purpose line.',
    '',
    '## Register',
    '',
    '| # | ' + h.cols.join(' | ') + ' |',
    '|---'.repeat(h.cols.length + 1) + '|',
    ...rules.map(([id, txt, impl, since]) => '| ' + id + ' | ' + h.cells(txt, impl || 'tile 1', since).join(' | ') + ' |'),
    '',
  ].join('\n');
}

// The decisions record. Every fixture ruling carries a `code span` AND an escaped `\|` on purpose:
// the record is the LAST cell, and a naive `split('|')` would cut the ruling in two and read the
// fragment after the bare pipe as the record. If the gate ever regresses to a plain split, the
// clean case below stops finding `fx-kickoff-2026-09-08.md` and goes red on its own.
function decisions(rows) {
  return [
    '# Fixture decisions record',
    '',
    '| date | rule | ruling | record |',
    '|---|---|---|---|',
    ...rows.map(([date, rule, record]) =>
      '| ' + date + ' | ' + rule + ' | Fixture ruling, with a `code span` and an escaped \\| pipe. | ' + record + ' |'),
    '',
  ].join('\n');
}
// R1 is recorded by THIS kickoff, R2 by an earlier one — so on the v2 register (R1 Since
// 2026-09-08, R2 Since 2026-09-01) R1 is minted by this change and R2 is cite-only.
const CLEAN_DECISIONS = [
  ['2026-09-08', 'R1', '`fx-kickoff-2026-09-08.md`'],
  ['2026-09-01', 'R2', '`other-kickoff-2026-09-01.md`'],
];
// A Dictionary whose PREAMBLE — the lines before the first `## ` heading — is exactly `n` lines.
// dd() opens with 4 such lines, so the rest is filler that must not itself start a section.
function ddPreamble(n, shape = 'v1') {
  const body = dd([['R1', RULE1], ['R2', RULE2]], shape);
  const fill = Array.from({ length: Math.max(0, n - 4) }, (_, i) => 'preamble line ' + i);
  return fill.length ? fill.join('\n') + '\n' + body : body;
}

// `done`:  false          no done block at all (an open kickoff)
//          true           a real close — an ISO built_at
//          'placeholder'  the TEMPLATE's shape example, built_at `<ISO>` — not a close
//          'nested'       a real close still wrapped in the template's `<!-- appended by … -->`
//                         comment, which is how the build lane has written it since 2026-09-05 and
//                         therefore MUST keep counting as a close (group H7)
// `seals`: null = key absent · {} = the template's empty placeholder · {Rn: hash} = a real seal.
//          An empty object is truthy, which is the whole reason H4/H5 exist.
// `builtAt` overrides the close's timestamp (group K compares INSTANTS across three written shapes:
// `…Z`, a `-04:00` offset and a bare date). `dashboards` / `baseline` / `scope` let a fixture reach
// the estate scope diff at all — with `dashboards: []` the whole waiver branch is unreachable, which
// is why the defect group K covers could sit in the gate unmeasured.
function kickoff({ rules = ['R1'], seals = null, done = false, kpath = 'rule', ratified = true,
                   builtAt = '2026-09-08T00:00:00Z', dashboards = [], baseline = null, scope = {} }) {
  const hdr = {
    path: kpath, lane: 'build', model: 'opus', rules, dashboards, scope,
    baseline, ratified,
  };
  if (seals) hdr.rule_text_sha1 = seals;
  const doneJson = built => JSON.stringify(
    { built_at: built, harvest: {}, elements_touched: [], counts: {}, open_items: [] }, null, 2);
  const doneLines = {
    true: ['<!-- bi-change:done -->', '```json', doneJson(builtAt), '```'],
    placeholder: ['<!-- bi-change:done -->', '```json', doneJson('<ISO>'), '```'],
    nested: ['<!-- appended by the build lane — verbatim shape:',
      '<!-- bi-change:done -->', '```json', doneJson('2026-09-08T00:00:00Z'), '```', '-->'],
  }[String(done)] || ['- open, not built'];
  return [
    '# Fixture kickoff',
    '',
    '<!-- bi-change:header -->',
    '```json',
    JSON.stringify(hdr, null, 2),
    '```',
    '',
    '## Open for Adam',
    '',
    '| # | Question | Recommendation | Ruling |',
    '|---|---|---|---|',
    '| 1 | Fixture question? | Yes | Approved |',
    '',
    '## Status',
    '',
    ...doneLines,
    '',
  ].join('\n');
}

function guide(entries) {
  return ['# Fixture guide 99999', '', '## Change log', '', ...entries, '', '## Other', '', 'x', ''].join('\n');
}

// The tenant pointer file. C7 measures the Current-state bullets, so the clean fixture must carry a
// real section: a heading, framing prose that is NOT a bullet, and bullets at or under the cap. One
// bullet sits at exactly 2 lines on purpose — a cap that rejected its own boundary would be wrong,
// and only a fixture written at the boundary can catch that.
const CLEAN_BULLETS = [
  '- **Estate:** one fixture board — `bi-estate/dashboard-99999-fixture.md`',
  '- **Dictionary:** R1–R2, stamped 2026-09-08.',
  '- **In flight:** two lines is legal, being exactly the cap.',
  '  Second line, still inside the cap — `bi-estate/fx-kickoff-2026-09-08.md`',
];
function claudeMd(bullets) {
  return [
    '# Fixture tenant', '',
    '## Current state (2026-09-08) — replace at close-out, never append', '',
    'Framing prose ahead of the first bullet is section framing, not a bullet, and is not measured.', '',
    ...bullets, '',
    '## Change log', '',
    '- 2026-09-08 — fx-kickoff-2026-09-08.md', '',
  ].join('\n');
}

// ---- the clean baseline fixture -------------------------------------------------------------
function buildClean() {
  fs.rmSync(ROOT, { recursive: true, force: true });
  fs.mkdirSync(EST, { recursive: true });
  fs.writeFileSync(path.join(EST, 'DATA-DICTIONARY.md'), dd([['R1', RULE1], ['R2', RULE2]]));
  // D1/D2 `fail` from the start, so the clean baseline must satisfy them or every assertion in
  // every group that expects exit 0 would redden on a missing DECISIONS.md rather than on the one
  // thing its own fixture broke.
  fs.writeFileSync(path.join(EST, 'DECISIONS.md'), decisions(CLEAN_DECISIONS));
  fs.writeFileSync(path.join(CLIENT, 'CLAUDE.md'), claudeMd(CLEAN_BULLETS));
  fs.writeFileSync(path.join(EST, 'README.md'), '# Fixture\n\n**Last synced: 2026-09-08** (one board re-harvested).\n');
  fs.writeFileSync(path.join(EST, 'dashboard-99999-fixture.md'),
    guide(['- 2026-09-08 — fx-kickoff-2026-09-08.md', '- 2026-09-07 — other-kickoff-2026-09-07.md']));
  fs.writeFileSync(path.join(EST, 'fx-kickoff-2026-09-08.md'),
    kickoff({ rules: ['R1'], seals: { R1: sha1(RULE1) }, done: true }));
}

function run(file, capsMode) {
  const a = [GATE, path.join(EST, file), '--phase', 'plan'];
  if (capsMode) a.push('--caps', capsMode);
  const r = spawnSync(process.execPath, a, { encoding: 'utf8' });
  return { status: r.status, out: ((r.stdout || '') + (r.stderr || '')).replace(/\r\n/g, '\n') };
}
// Find one check line by its label prefix.
function line(out, label) {
  return out.split('\n').find(l => l.trim().slice(2).startsWith(label)) || '';
}
function mark(out, label) { const l = line(out, label); return l ? l.trim()[0] : '(absent)'; }

const cases = [];
function check(name, cond, detail) { cases.push({ name, pass: !!cond, detail }); }

// =============================================================================================
// A. Each cap is GREEN on the clean fixture, and RED on a fixture broken only in that one place.
// =============================================================================================
const CAPS = [
  {
    id: 'C1 rule cell ≤ 600',
    label: 'cap: rule cell',
    // one rule cell pushed just over 600 chars; nothing else touched
    break: () => fs.writeFileSync(path.join(EST, 'DATA-DICTIONARY.md'), dd([['R1', 'x'.repeat(601)], ['R2', RULE2]])),
    expect: /1 of 2 row\(s\) over \(max 601 chars, R1\)/,
  },
  {
    id: 'C2 Dictionary preamble ≤ 40 lines',
    label: 'cap: Dictionary preamble',
    // Broken at the BOUNDARY, one line over the cap — a fixture 11 lines over would pass equally
    // well against a check that measured the wrong span, which is exactly the defect C2 had.
    break: () => fs.writeFileSync(path.join(EST, 'DATA-DICTIONARY.md'), ddPreamble(41)),
    expect: /\b41 lines\b/,
  },
  {
    id: 'C3a CLAUDE.md ≤ 120 lines',
    label: 'cap: CLAUDE.md ≤ 120 lines',
    break: () => fs.writeFileSync(path.join(CLIENT, 'CLAUDE.md'), Array.from({ length: 121 }, (_, i) => '- line ' + i).join('\n') + '\n'),
    expect: /122 lines/,
  },
  {
    id: 'C3b CLAUDE.md line ≤ 300 chars',
    label: 'cap: CLAUDE.md line ≤ 300 chars',
    break: () => fs.writeFileSync(path.join(CLIENT, 'CLAUDE.md'), '- short\n- ' + 'y'.repeat(400) + '\n'),
    expect: /1 line\(s\) over \(max 402 chars at line 2\)/,
  },
  {
    id: 'C4 README stamp ≤ 200',
    label: 'cap: README stamp',
    break: () => fs.writeFileSync(path.join(EST, 'README.md'), '# Fixture\n\n**Last synced: 2026-09-08** (' + 'z'.repeat(300) + ').\n'),
    expect: /\b\d{3} chars \(1 stamp line\)/,
  },
  {
    id: 'C5 guide change log = pointer lines',
    label: 'cap: guide change log',
    break: () => fs.writeFileSync(path.join(EST, 'dashboard-99999-fixture.md'),
      guide(['- 2026-09-08 — **A narrative entry** that runs on', '  and on across a continuation line.', '- 2026-09-07 — other-kickoff-2026-09-07.md'])),
    // Wording changed 2026-09-08 when the check learned to allow a bounded section frame and to
    // stop rejecting entries that quote a `|` literal. The SUBSTANCE asserted is unchanged: one
    // entry not pointing at a record, one line of narrative after an entry.
    expect: /1 of 1 guide\(s\) carry narrative .*1 not pointing at a record, 1 narrative lines/,
  },
  {
    id: 'C6 tenant root ≤ 10 loose files',
    label: 'cap: tenant root ≤ 10 loose files',
    // eleven loose files at the tenant root; the estate SUBDIR must not be counted, which is why
    // the clean fixture (1 file, 1 subdir) and this one differ only in files.
    break: () => { for (let i = 0; i < 10; i++) fs.writeFileSync(path.join(CLIENT, 'loose-' + i + '.csv'), 'x\n'); },
    expect: /11 loose file\(s\), 1 subdir\(s\) excluded/,
  },
  {
    id: 'C7 Current-state bullet ≤ 2 lines',
    label: 'cap: Current-state bullet ≤ 2 lines',
    // one bullet pushed to three lines; the two-line bullet beside it must stay legal, so the
    // expected COUNT is 1 of 3 and not 2 of 3.
    break: () => fs.writeFileSync(path.join(CLIENT, 'CLAUDE.md'), claudeMd([
      ...CLEAN_BULLETS,
      '  A third line appended to the bullet above — this is the append-log shape.',
    ])),
    expect: /1 of 3 bullet\(s\) over \(max 3 lines, "In flight: two lines is lega"\)/,
  },
];

buildClean();
{
  const clean = run('fx-kickoff-2026-09-08.md', 'fail');
  for (const c of CAPS) check('CLEAN: ' + c.id + ' reports ✔', mark(clean.out, c.label) === '✔', line(clean.out, c.label).trim());
  check('CLEAN: fixture is green overall (exit 0)', clean.status === 0, 'exit ' + clean.status);
}

for (const c of CAPS) {
  buildClean();
  c.break();
  const broken = run('fx-kickoff-2026-09-08.md', 'fail');
  const l = line(broken.out, c.label).trim();
  check('BROKEN: ' + c.id + ' fires ✘ under --caps fail', mark(broken.out, c.label) === '✘', l);
  check('BROKEN: ' + c.id + ' reddens the run (exit 1)', broken.status === 1, 'exit ' + broken.status);
  check('BROKEN: ' + c.id + ' reports the expected COUNT', c.expect.test(l), l);
  // report-only mode must NOT redden — that is what "one run report-only, then fail" rests on
  const info = run('fx-kickoff-2026-09-08.md', 'info');
  check('BROKEN: ' + c.id + ' is · (not ✘) under --caps info', mark(info.out, c.label) === '·', line(info.out, c.label).trim());
  check('BROKEN: ' + c.id + ' does not redden under --caps info', info.status === 0, 'exit ' + info.status);
}

// =============================================================================================
// B. P3 seal grain. The hard check must SURVIVE for the case it exists to catch.
// =============================================================================================
const SEAL = 'rule text unchanged since seal';

// B1 — OPEN kickoff, drift on a row INSIDE header.rules → still fails. This is the regression guard:
// if P3 had over-reached, this is the case that would silently stop protecting anything.
buildClean();
fs.writeFileSync(path.join(EST, 'DATA-DICTIONARY.md'), dd([['R1', RULE1 + ' EDITED'], ['R2', RULE2]]));
fs.writeFileSync(path.join(EST, 'fx-kickoff-2026-09-08.md'), kickoff({ rules: ['R1'], seals: { R1: sha1(RULE1) }, done: false }));
{
  const r = run('fx-kickoff-2026-09-08.md');
  check('P3: OPEN + in-grain drift still FAILS', mark(r.out, SEAL) === '✘' && r.status === 1, line(r.out, SEAL).trim() + ' | exit ' + r.status);
}

// B2 — CLOSED kickoff, same in-grain drift → reported, never failed (ruling 3).
buildClean();
fs.writeFileSync(path.join(EST, 'DATA-DICTIONARY.md'), dd([['R1', RULE1 + ' EDITED'], ['R2', RULE2]]));
fs.writeFileSync(path.join(EST, 'fx-kickoff-2026-09-08.md'), kickoff({ rules: ['R1'], seals: { R1: sha1(RULE1) }, done: true }));
{
  const r = run('fx-kickoff-2026-09-08.md');
  check('P3: CLOSED + in-grain drift is ✔ + reported', mark(r.out, SEAL) === '✔' && r.status === 0, line(r.out, SEAL).trim());
  check('P3: CLOSED drift names the row in a drift line', /R1/.test(line(r.out, 'rule text drift')), line(r.out, 'rule text drift').trim());
}

// B3 — OPEN kickoff sealed over BOTH rows (the pre-2026-09-08 all-rows seal), drift on the row
// OUTSIDE header.rules → reported, never failed. This is the "red forever" defect itself.
buildClean();
fs.writeFileSync(path.join(EST, 'DATA-DICTIONARY.md'), dd([['R1', RULE1], ['R2', RULE2 + ' EDITED BY A PEER']]));
fs.writeFileSync(path.join(EST, 'fx-kickoff-2026-09-08.md'),
  kickoff({ rules: ['R1'], seals: { R1: sha1(RULE1), R2: sha1(RULE2) }, done: false }));
{
  const r = run('fx-kickoff-2026-09-08.md');
  check('P3: OPEN + out-of-grain drift is ✔ (not failed)', mark(r.out, SEAL) === '✔' && r.status === 0, line(r.out, SEAL).trim());
  check('P3: out-of-grain drift is still REPORTED', /R2/.test(line(r.out, 'rule text drift')), line(r.out, 'rule text drift').trim());
}

// B4 — --seal writes ONLY the grain, not every register row.
buildClean();
fs.writeFileSync(path.join(EST, 'fx-kickoff-2026-09-08.md'), kickoff({ rules: ['R1'], done: false }));
{
  spawnSync(process.execPath, [GATE, path.join(EST, 'fx-kickoff-2026-09-08.md'), '--phase', 'plan', '--seal'], { encoding: 'utf8' });
  const body = fs.readFileSync(path.join(EST, 'fx-kickoff-2026-09-08.md'), 'utf8');
  const m = body.match(/"rule_text_sha1": \{([\s\S]*?)\}/);
  const keys = m ? (m[1].match(/"R\d+"/g) || []) : [];
  check('P3: --seal hashes only header.rules (1 of 2 rows)', keys.length === 1 && keys[0] === '"R1"', 'sealed keys: ' + keys.join(', '));
}

// B5 — an empty grain (a sync/config change resting on no rule) seals and passes rather than
// falling through to "header sealed ✘".
buildClean();
fs.writeFileSync(path.join(EST, 'fx-kickoff-2026-09-08.md'), kickoff({ rules: [], seals: {}, done: true }));
{
  const r = run('fx-kickoff-2026-09-08.md');
  check('P3: empty grain seals green', mark(r.out, SEAL) === '✔', line(r.out, SEAL).trim());
}

// =============================================================================================
// C. PER-CAP DEFAULT ENFORCEMENT (§6 step 5). Everything above passes an explicit --caps, which
// overrides the defaults — so it proves the mechanism, not the setting. This proves the SETTING:
// with NO flag at all, C3/C4/C5 must redden and C1/C2 must not.
// =============================================================================================
function runDefault(file) {
  const r = spawnSync(process.execPath, [GATE, path.join(EST, file), '--phase', 'plan'], { encoding: 'utf8' });
  return { status: r.status, out: ((r.stdout || '') + (r.stderr || '')).replace(/\r\n/g, '\n') };
}
const ENFORCED = [
  ['C3a CLAUDE.md lines', 'cap: CLAUDE.md ≤ 120 lines',
    () => fs.writeFileSync(path.join(CLIENT, 'CLAUDE.md'), Array.from({ length: 121 }, (_, i) => '- line ' + i).join('\n') + '\n')],
  ['C3b CLAUDE.md line length', 'cap: CLAUDE.md line ≤ 300 chars',
    () => fs.writeFileSync(path.join(CLIENT, 'CLAUDE.md'), '- short\n- ' + 'y'.repeat(400) + '\n')],
  ['C4 README stamp', 'cap: README stamp',
    () => fs.writeFileSync(path.join(EST, 'README.md'), '# Fx\n\n**Last synced: 2026-09-08** (' + 'z'.repeat(300) + ').\n')],
  ['C5 guide change log', 'cap: guide change log',
    () => fs.writeFileSync(path.join(EST, 'dashboard-99999-fixture.md'),
      guide(['- 2026-09-08 — **Narrative entry** that runs on', '  and onto a continuation line.']))],
  // Both moved here from REPORTED as their A2 step landed: C6 when the tenant-root move took the
  // root from 235 loose files to 1, C7 when the one three-line bullet was reshaped to two. Flipping
  // the gate without moving the row fails the run — which is what the row is for.
  ['C6 tenant root loose files', 'cap: tenant root ≤ 10 loose files',
    () => { for (let i = 0; i < 10; i++) fs.writeFileSync(path.join(CLIENT, 'loose-' + i + '.csv'), 'x\n'); }],
  ['C7 Current-state bullet shape', 'cap: Current-state bullet ≤ 2 lines',
    () => fs.writeFileSync(path.join(CLIENT, 'CLAUDE.md'), claudeMd([...CLEAN_BULLETS, '  A third line appended.']))],
  // C1 and C2 made the same trip on 2026-09-09, when Phase B's compaction brought the register
  // (71 rows, max rule cell 400 chars) and the preamble (27 lines) under their caps. C2's
  // MEASUREMENT changed in the same change as its enforcement — see the boundary rows below.
  ['C1 rule cell', 'cap: rule cell',
    () => fs.writeFileSync(path.join(EST, 'DATA-DICTIONARY.md'), dd([['R1', 'x'.repeat(601)], ['R2', RULE2]]))],
  ['C2 Dictionary preamble', 'cap: Dictionary preamble',
    () => fs.writeFileSync(path.join(EST, 'DATA-DICTIONARY.md'), ddPreamble(41))],
];
for (const [name, label, brk] of ENFORCED) {
  buildClean(); brk();
  const r = runDefault('fx-kickoff-2026-09-08.md');
  check('DEFAULT (no --caps): ' + name + ' REDDENS', mark(r.out, label) === '✘' && r.status === 1,
    line(r.out, label).trim() + ' | exit ' + r.status);
}
// Every cap is now ENFORCED, so this list is empty — and it stays here rather than being deleted,
// because it is the shape a future cap arrives in: land it report-only, then move it up in the same
// change that brings its surface under the cap. The loop below runs zero times, which is honest;
// the ENFORCED loop is what carries the setting today.
const REPORTED = [];
for (const [name, label, brk] of REPORTED) {
  buildClean(); brk();
  const r = runDefault('fx-kickoff-2026-09-08.md');
  check('DEFAULT (no --caps): ' + name + ' REPORTS, does not redden',
    mark(r.out, label) === '·' && r.status === 0, line(r.out, label).trim() + ' | exit ' + r.status);
}

// C2's boundary, at the DEFAULT enforcement — the pair that makes the re-spec provable. 40 lines of
// preamble is legal and must stay green; 41 must redden. Both fixtures carry a `## Register`
// heading with §-style content BELOW it, so a check that reverted to "everything before the
// register header row" would read far more than the preamble and fail the 40-line case.
for (const [n, wantMark, wantExit] of [[40, '✔', 0], [41, '✘', 1]]) {
  buildClean();
  fs.writeFileSync(path.join(EST, 'DATA-DICTIONARY.md'), ddPreamble(n));
  const r = runDefault('fx-kickoff-2026-09-08.md');
  check('DEFAULT: C2 preamble of ' + n + ' lines is ' + wantMark + ' (cap 40)',
    mark(r.out, 'cap: Dictionary preamble') === wantMark && r.status === wantExit,
    line(r.out, 'cap: Dictionary preamble').trim() + ' | exit ' + r.status);
}

// C2 measures the PREAMBLE, not the run-up to the register. A Dictionary with a 4-line preamble and
// a 60-line section sitting between the first heading and the register header row must stay green:
// this is the exact file shape (§1 Taxonomy layers above the register) that made the old reading
// report 174 lines on a 27-line preamble.
{
  buildClean();
  const body = dd([['R1', RULE1], ['R2', RULE2]]);
  const [head, tail] = [body.slice(0, body.indexOf('## Register')), body.slice(body.indexOf('## Register'))];
  fs.writeFileSync(path.join(EST, 'DATA-DICTIONARY.md'),
    head + '## Taxonomy layers\n\n' + Array.from({ length: 60 }, (_, i) => '- layer ' + i).join('\n') + '\n\n' + tail);
  const r = runDefault('fx-kickoff-2026-09-08.md');
  check('DEFAULT: C2 ignores a section between the first heading and the register',
    mark(r.out, 'cap: Dictionary preamble') === '✔' && /\b4 lines\b/.test(line(r.out, 'cap: Dictionary preamble')),
    line(r.out, 'cap: Dictionary preamble').trim() + ' | exit ' + r.status);
}

// =============================================================================================
// D. --pointer mode. It scores C3–C8 with NO kickoff, so it must (a) run at all with no kickoff
// argument, (b) score exactly that set and nothing that needs a register or a header, (c) still
// redden on an enforced breach, and (d) find the estate by CONTENT — the Dictionary — rather than
// by a folder name, or the mode silently stops measuring C4/C5 on the next tenant that names its
// estate folder differently.
// =============================================================================================
function runPointer(dir, capsMode) {
  const a = [GATE, '--pointer', dir];
  if (capsMode) a.push('--caps', capsMode);
  const r = spawnSync(process.execPath, a, { encoding: 'utf8' });
  return { status: r.status, out: ((r.stdout || '') + (r.stderr || '')).replace(/\r\n/g, '\n') };
}
const POINTER_LABELS = [
  'cap: CLAUDE.md ≤ 120 lines', 'cap: CLAUDE.md line ≤ 300 chars', 'cap: README stamp',
  'cap: guide change log', 'cap: tenant root ≤ 10 loose files', 'cap: Current-state bullet ≤ 2 lines',
];

// D1 — clean tenant: runs with no kickoff, exits 0, and every C3–C8 line is present and green.
buildClean();
{
  const r = runPointer(CLIENT);
  check('--pointer: clean tenant exits 0', r.status === 0, 'exit ' + r.status);
  check('--pointer: clean tenant is identified as one', mark(r.out, 'pointer file present') === '✔' && mark(r.out, 'estate found below the tenant') === '✔',
    line(r.out, 'pointer file present').trim() + ' | ' + line(r.out, 'estate found below the tenant').trim());
  for (const l of POINTER_LABELS) check('--pointer: reports ' + l, mark(r.out, l) === '✔', line(r.out, l).trim());
  // Nothing that needs a header or a register may appear: those are the checks the mode drops.
  const leaked = ['cap: rule cell', 'cap: Dictionary preamble', 'ratified', 'done block', '--stale']
    .filter(l => line(r.out, l));
  check('--pointer: scores C3–C8 ONLY (no register / header / scan checks)', leaked.length === 0, 'leaked: ' + (leaked.join(', ') || 'none'));
}

// D2 — an ENFORCED breach (C3, 'fail' by default) must redden pointer mode, or the standing check
// is decorative.
buildClean();
fs.writeFileSync(path.join(CLIENT, 'CLAUDE.md'), Array.from({ length: 121 }, (_, i) => '- line ' + i).join('\n') + '\n');
{
  const r = runPointer(CLIENT);
  check('--pointer: an enforced breach exits 1', mark(r.out, 'cap: CLAUDE.md ≤ 120 lines') === '✘' && r.status === 1,
    line(r.out, 'cap: CLAUDE.md ≤ 120 lines').trim() + ' | exit ' + r.status);
}

// D3 — a report-only breach (C6) reddens pointer mode under --caps fail and not otherwise. This is
// the switch that will be thrown when the tenant-root move lands.
buildClean();
for (let i = 0; i < 10; i++) fs.writeFileSync(path.join(CLIENT, 'loose-' + i + '.csv'), 'x\n');
{
  const r = runPointer(CLIENT, 'fail');
  check('--pointer: C6 reddens under --caps fail', mark(r.out, 'cap: tenant root ≤ 10 loose files') === '✘' && r.status === 1,
    line(r.out, 'cap: tenant root ≤ 10 loose files').trim() + ' | exit ' + r.status);
  const q = runPointer(CLIENT);
  check('--pointer: C6 reddens on its shipped default too', mark(q.out, 'cap: tenant root ≤ 10 loose files') === '✘' && q.status === 1,
    line(q.out, 'cap: tenant root ≤ 10 loose files').trim() + ' | exit ' + q.status);
}

// D4 — the estate is found by the Dictionary, not by the folder being called `bi-estate`. Rename it
// and C4/C5 must still measure; if discovery were name-based they would silently go quiet.
buildClean();
fs.renameSync(EST, path.join(CLIENT, 'estate-under-another-name'));
{
  const r = runPointer(CLIENT);
  check('--pointer: finds the estate by the Dictionary, not the folder name',
    mark(r.out, 'cap: README stamp') === '✔' && mark(r.out, 'cap: guide change log') === '✔',
    line(r.out, 'cap: README stamp').trim() + ' | ' + line(r.out, 'cap: guide change log').trim());
}

// D5 — a path that does not exist fails loudly rather than reporting a green nothing.
{
  const r = runPointer(path.join(ROOT, 'no-such-tenant'));
  check('--pointer: a missing tenant dir exits 1', r.status === 1, 'exit ' + r.status + ' — ' + r.out.trim().split('\n')[0]);
}

// D6 — an EXISTING directory that is not a tenant. This is the harder case and the one the mode
// shipped broken: a nonexistent path was the only thing that failed. With no pointer file every
// CLAUDE.md check degrades to `info`, C4 printed nothing at all, and C6 passes on any directory
// holding ten files or fewer — so a plain asset folder scored "All checks passed" at exit 0.
// EXACTLY ten files here, because ten is the vacuous pass; eleven would have reddened C6 by luck
// and the fixture would prove the wrong thing.
buildClean();
{
  const NOT_TENANT = path.join(ROOT, 'not-a-tenant');
  fs.mkdirSync(NOT_TENANT, { recursive: true });
  for (let i = 0; i < 10; i++) fs.writeFileSync(path.join(NOT_TENANT, 'asset-' + i + '.png'), 'x');
  const r = runPointer(NOT_TENANT);
  check('--pointer: an EXISTING non-tenant dir exits 1', r.status === 1, 'exit ' + r.status);
  check('--pointer: names the missing pointer file', mark(r.out, 'pointer file present') === '✘', line(r.out, 'pointer file present').trim());
  check('--pointer: names the missing estate', mark(r.out, 'estate found below the tenant') === '✘', line(r.out, 'estate found below the tenant').trim());
  // C6 must still be the vacuous pass it always was — the fixture is only honest if the identity
  // check, not a lucky file count, is what reddens the run.
  check('--pointer: C6 alone would still have passed it', mark(r.out, 'cap: tenant root ≤ 10 loose files') === '✔',
    line(r.out, 'cap: tenant root ≤ 10 loose files').trim());
  // Identity is not a cap, so --caps info must not be able to green it.
  const q = runPointer(NOT_TENANT, 'info');
  check('--pointer: --caps info cannot green a non-tenant dir', q.status === 1, 'exit ' + q.status);
  // C4 printed NOTHING when there was no estate; every branch must report.
  check('--pointer: C4 reports even with no README', line(r.out, 'cap: README stamp') !== '', line(r.out, 'cap: README stamp').trim() || '(absent)');
}

// =============================================================================================
// E. REGISTER HEADER SHAPE. The expected segment count comes from the register's own header row,
// so the gate must parse the 5-column register this estate carried before Phase B AND the
// 8-column one it carries after, with no edit between them. Two things are proven per shape:
// the row parses to the right segment count (an unshaped row loses per-cell checking and its
// impl cell goes unchecked), and the NOT BUILT marker is read out of SEGMENT 2 — `Implementation`
// in the old shape, `Surface` in the new one. E3 is the guard that matters: a check reading a
// hardcoded index, or the whole row, would fire on NOT BUILT sitting in any column.
// =============================================================================================
function runBuild(file) {
  const r = spawnSync(process.execPath, [GATE, path.join(EST, file)], { encoding: 'utf8' });
  return { status: r.status, out: ((r.stdout || '') + (r.stderr || '')).replace(/\r\n/g, '\n') };
}
for (const [shape, segs] of [['v1', 5], ['v2', 8]]) {
  // E1/E2 — both shapes parse, to the segment count their own header declares.
  buildClean();
  fs.writeFileSync(path.join(EST, 'DATA-DICTIONARY.md'), dd([['R1', RULE1], ['R2', RULE2]], shape));
  {
    const r = run('fx-kickoff-2026-09-08.md', 'fail');
    check('HEADER ' + shape + ': ' + segs + '-column register parses, all rows shaped',
      mark(r.out, 'register row shape') === '✔' && new RegExp('2 row\\(s\\), all ' + segs + ' cells').test(line(r.out, 'register row shape')),
      line(r.out, 'register row shape').trim());
    check('HEADER ' + shape + ': C1 still measures the rule cell', mark(r.out, 'cap: rule cell') === '✔' && /0 of 2 row\(s\) over/.test(line(r.out, 'cap: rule cell')),
      line(r.out, 'cap: rule cell').trim());
  }
  // NOT BUILT in SEGMENT 2 must fail.
  buildClean();
  fs.writeFileSync(path.join(EST, 'DATA-DICTIONARY.md'), dd([['R1', RULE1, 'NOT BUILT'], ['R2', RULE2]], shape));
  fs.writeFileSync(path.join(EST, 'fx-kickoff-2026-09-08.md'),
    kickoff({ rules: ['R1'], kpath: 'config', seals: { R1: sha1(RULE1) }, done: true }));
  {
    const r = runBuild('fx-kickoff-2026-09-08.md');
    check('HEADER ' + shape + ': NOT BUILT in segment 2 FAILS the impl cell',
      mark(r.out, 'impl cell R1') === '✘', line(r.out, 'impl cell R1').trim());
  }
  // E3 — the same marker in a cell that is NOT segment 2 must NOT fire. Segment 2 is the last cell
  // in the 5-column shape's `Ruled` column and the `Record` column in the 8-column one; either way
  // it is a column the check has no business reading.
  buildClean();
  const h = HEADERS[shape];
  const cells = h.cells(RULE1, 'tile 1'); cells[cells.length - 1] = 'NOT BUILT';
  const reg = dd([['R1', RULE1], ['R2', RULE2]], shape)
    .replace(new RegExp('^\\| R1 \\|.*$', 'm'), '| R1 | ' + cells.join(' | ') + ' |');
  fs.writeFileSync(path.join(EST, 'DATA-DICTIONARY.md'), reg);
  fs.writeFileSync(path.join(EST, 'fx-kickoff-2026-09-08.md'),
    kickoff({ rules: ['R1'], kpath: 'config', seals: { R1: sha1(RULE1) }, done: true }));
  {
    const r = runBuild('fx-kickoff-2026-09-08.md');
    check('HEADER ' + shape + ': NOT BUILT outside segment 2 does NOT fire',
      mark(r.out, 'impl cell R1') === '✔', line(r.out, 'impl cell R1').trim());
  }
}

// =============================================================================================
// G. C8 TEMPLATE CONFORMANCE. It measures a tenant against the shape the client template declares,
// which is the only cap whose reference is another file rather than a number — so it is proven the
// same way as the rest: green on a tenant that carries everything, red with the right COUNT on one
// missing exactly one file, one pointer key, or a matching register header. The scaffolded tenant
// IS the clean fixture: nothing else is guaranteed to conform to the template by construction.
// =============================================================================================
{
  const c8 = (out) => line(out, 'C8: template conformance').trim();
  const dest = path.join(ROOT, 'c8');
  const r0 = spawnSync(process.execPath, [path.join(path.dirname(GATE), 'new_client.js'),
    '--client', 'fixture', '--tenant', 'c8tenant', '--lsp', 'C8 Fixture Co', '--dest', dest,
    '--no-verify'], { encoding: 'utf8' });
  const TEN = path.join(dest, 'fixture', 'c8tenant');
  if (r0.status !== 0 || !fs.existsSync(TEN)) {
    check('C8: a scaffolded tenant is available as the clean fixture', false, 'scaffold exit ' + r0.status);
  } else {
    // G1 — a freshly scaffolded tenant conforms by construction, on all three counts.
    let r = runPointer(TEN, null);
    check('C8: a freshly scaffolded tenant reads 0 missing on all three counts',
      mark(r.out, 'C8: template conformance') === '✔' && /0 of \d+ template path\(s\) missing/.test(c8(r.out)) &&
      /0 of \d+ pointer key\(s\) missing/.test(c8(r.out)) && /register header matches/.test(c8(r.out)), c8(r.out));

    // G2 — remove ONE file the template names. The count must move to exactly 1 and name it.
    const victim = path.join(TEN, 'scripts', 'README.md');
    fs.rmSync(victim);
    r = runPointer(TEN, 'fail');
    check('C8: one missing template path reddens with a count of 1, naming the path',
      mark(r.out, 'C8: template conformance') === '✘' && /1 of \d+ template path\(s\) missing: scripts\/README\.md/.test(c8(r.out)),
      c8(r.out));
    // …and stays quiet under `--caps info`, which is what report-only-for-one-phase rests on.
    r = runPointer(TEN, 'info');
    check('C8: the same breach is `·` under --caps info', mark(r.out, 'C8: template conformance') === '·', c8(r.out));
    // …and is `·` by its shipped default this phase, which is what makes Phase C non-blocking.
    r = runPointer(TEN, null);
    check('C8: `info` is its shipped default for now', mark(r.out, 'C8: template conformance') === '·', c8(r.out));
    fs.writeFileSync(victim, '# fixture\n');

    // G3 — a DATED sibling satisfies the template's undated name, because an estate dates some
    // standing artifacts and renaming one would dangle every citation of it.
    const reg = path.join(TEN, 'bi-estate', 'qc-surface-register.md');
    fs.renameSync(reg, path.join(TEN, 'bi-estate', 'qc-surface-register-2026-09-04.md'));
    r = runPointer(TEN, 'fail');
    check('C8: a dated sibling satisfies the template name', mark(r.out, 'C8: template conformance') === '✔', c8(r.out));
    // …but a MISSING document is still missing, dated convention or not.
    fs.rmSync(path.join(TEN, 'bi-estate', 'qc-surface-register-2026-09-04.md'));
    r = runPointer(TEN, 'fail');
    check('C8: the dated-sibling rule does not excuse an absent document',
      mark(r.out, 'C8: template conformance') === '✘' && /qc-surface-register\.md/.test(c8(r.out)), c8(r.out));
    fs.writeFileSync(reg, '# fixture\n');

    // G4 — drop one pointer-block key from the tenant CLAUDE.md.
    const cmd = path.join(TEN, 'CLAUDE.md');
    const kept = fs.readFileSync(cmd, 'utf8').split('\n').filter(l => !/^- \*\*Write channel:/.test(l)).join('\n');
    fs.writeFileSync(cmd, kept);
    r = runPointer(TEN, 'fail');
    check('C8: one missing pointer key reddens with a count of 1, naming the key',
      mark(r.out, 'C8: template conformance') === '✘' && /1 of \d+ pointer key\(s\) missing: write channel/.test(c8(r.out)),
      c8(r.out));
  }
}

// =============================================================================================
// F. THE SCAFFOLD. `new_client.js` is the one command that stands a tenant up, so it is proven in
// all three directions, not just the happy one: a clean scaffold verifies itself against the gate
// it ships with; a template carrying a placeholder the scaffold does not fill is REFUSED and the
// placeholder is named; and a scaffold aimed at an existing tenant is REFUSED rather than merged.
// The second case is the one that matters — a mis-cased `<Tenant>` in the template would otherwise
// ship silently into a live tenant's pointer file and read as prose.
// =============================================================================================
const NEW_CLIENT = path.join(path.dirname(GATE), 'new_client.js');
const TEMPLATE_DIR = path.join(path.dirname(GATE), '..', 'templates', 'client');

function scaffold(dest, extra = []) {
  const r = spawnSync(process.execPath, [NEW_CLIENT,
    '--client', 'fixture', '--tenant', 'fxtenant', '--lsp', 'Fixture Cannabis Co',
    '--dest', dest, ...extra], { encoding: 'utf8' });
  return { status: r.status, out: ((r.stdout || '') + (r.stderr || '')).replace(/\r\n/g, '\n') };
}
// Copy the template so a fixture can be broken without touching the shipped one.
function copyDir(src, dst) {
  fs.mkdirSync(dst, { recursive: true });
  for (const e of fs.readdirSync(src, { withFileTypes: true })) {
    const s = path.join(src, e.name); const d = path.join(dst, e.name);
    if (e.isDirectory()) copyDir(s, d); else fs.copyFileSync(s, d);
  }
}

if (!fs.existsSync(NEW_CLIENT) || !fs.existsSync(TEMPLATE_DIR)) {
  check('SCAFFOLD: new_client.js and templates/client/ ship with the skill', false,
    'missing ' + (fs.existsSync(NEW_CLIENT) ? TEMPLATE_DIR : NEW_CLIENT));
} else {
  // F1 — a clean scaffold stands up and passes BOTH of its own gate runs.
  const dest1 = path.join(ROOT, 'scaffold-clean');
  const r1 = scaffold(dest1);
  check('SCAFFOLD: one command scaffolds a tenant that verifies (exit 0)',
    r1.status === 0, (r1.status === 0 ? 'exit 0' : 'exit ' + r1.status + '\n          ' + r1.out.trim().split('\n').slice(-6).join('\n          ')));
  check('SCAFFOLD: --pointer PASSES on the new tenant',
    /✔ --pointer on the new tenant \(must PASS\) — exit 0/.test(r1.out),
    (r1.out.split('\n').find(l => l.includes('--pointer on the new tenant')) || '(absent)').trim());
  check('SCAFFOLD: the plan gate PASSES on the fixture kickoff over an EMPTY register',
    /✔ --phase plan on the fixture kickoff .* — exit 0/.test(r1.out),
    (r1.out.split('\n').find(l => l.includes('--phase plan on the fixture')) || '(absent)').trim());
  // Every path the template names is on disk under the new tenant — the same set C8 scores.
  {
    const missing = [];
    (function walk(rel) {
      const src = path.join(TEMPLATE_DIR, '__tenant__', rel);
      for (const e of fs.readdirSync(src, { withFileTypes: true })) {
        const r = rel ? rel + '/' + e.name : e.name;
        if (e.isDirectory()) { walk(r); continue; }
        if (!fs.existsSync(path.join(dest1, 'fixture', 'fxtenant', r))) missing.push(r);
      }
    })('');
    check('SCAFFOLD: every template path lands in the tenant', missing.length === 0,
      missing.length ? 'missing ' + missing.join(', ') : 'all template paths present');
  }

  // F1b — the wrapper sync stamps a provenance banner on every `.md` it copies. Scaffolding FROM a
  // synced wrapper must not carry that banner into a client's documents: it is true of the skill
  // copy and false of the tenant. The fixture reproduces the sync's own banner exactly.
  {
    const banneredTpl = path.join(ROOT, 'bannered-template');
    copyDir(TEMPLATE_DIR, banneredTpl);
    const BAN = '<!-- Generated from "freed-solutions/skills/bi-change/templates/client/x.md". ' +
      'Edit the repo skill source and rerun ops/notion-workspace/scripts/sync-claude-skill-wrappers.ps1; ' +
      'do not edit this Claude copy directly. -->\n\n';
    (function banner(dir) {
      for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
        const p = path.join(dir, e.name);
        if (e.isDirectory()) { banner(p); continue; }
        if (e.name.endsWith('.md')) fs.writeFileSync(p, BAN + fs.readFileSync(p, 'utf8'), 'utf8');
      }
    })(banneredTpl);
    const destB = path.join(ROOT, 'scaffold-bannered');
    const rB = scaffold(destB, ['--template', banneredTpl, '--no-verify']);
    const leaked = [];
    if (rB.status === 0) {
      (function walk(rel) {
        const d = path.join(destB, 'fixture', 'fxtenant', rel);
        for (const e of fs.readdirSync(d, { withFileTypes: true })) {
          const r = rel ? rel + '/' + e.name : e.name;
          if (e.isDirectory()) { walk(r); continue; }
          if (e.name.endsWith('.md') && /^<!--\s*Generated from/.test(fs.readFileSync(path.join(d, e.name), 'utf8'))) {
            leaked.push(r);
          }
        }
      })('');
    }
    check('SCAFFOLD: the wrapper provenance banner never reaches a scaffolded tenant',
      rB.status === 0 && leaked.length === 0,
      rB.status !== 0 ? 'scaffold exit ' + rB.status : (leaked.length ? 'banner in ' + leaked.join(', ') : 'no banner in any tenant .md'));
  }

  // F2 — a template carrying an UNFILLABLE placeholder is refused, and the placeholder is named.
  // `<Tenant>` is the realistic defect: a human editing the template mis-cases one token.
  const brokenTpl = path.join(ROOT, 'broken-template');
  copyDir(TEMPLATE_DIR, brokenTpl);
  {
    const f = path.join(brokenTpl, '__tenant__', 'CLAUDE.md');
    fs.writeFileSync(f, fs.readFileSync(f, 'utf8') + '\n- Tenant: <Tenant>\n', 'utf8');
  }
  const r2 = scaffold(path.join(ROOT, 'scaffold-broken'), ['--template', brokenTpl]);
  check('SCAFFOLD: an unfilled placeholder REFUSES the scaffold (exit 1)', r2.status === 1,
    'exit ' + r2.status);
  check('SCAFFOLD: the refusal NAMES the placeholder and its file',
    /unfilled placeholder <Tenant>/.test(r2.out) && /CLAUDE\.md:\d+/.test(r2.out),
    (r2.out.split('\n').find(l => l.includes('unfilled placeholder')) || '(absent)').trim());

  // F3 — scaffolding onto an existing tenant is refused. A merge over a live tenant is
  // unrecoverable, so this must fail before it writes anything.
  const r3 = scaffold(dest1);
  check('SCAFFOLD: an existing tenant is REFUSED, never overwritten', r3.status === 1 && /REFUSED/.test(r3.out),
    (r3.out.split('\n').find(l => l.includes('REFUSED')) || '(absent)').trim());
  {
    // …and the refusal left the existing tenant untouched: its pointer file still verifies.
    const p = runPointer(path.join(dest1, 'fixture', 'fxtenant'), null);
    check('SCAFFOLD: the refused target is unharmed (--pointer still exit 0)', p.status === 0,
      'exit ' + p.status);
  }
}

// =============================================================================================
// H. THE TWO TEMPLATE PLACEHOLDERS (2026-09-10). `templates/kickoff.md` ships `"built_at": "<ISO>"`
// and `"rule_text_sha1": {}`, and until this change the gate could not tell either from the real
// thing — so a kickoff that had built nothing read CLOSED (which downgrades its own seal check from
// fail to report) and a kickoff resting on two rules could reach the build lane unsealed and be
// called sealed.
//
// ⚠ H7 IS THE GUARD THAT MATTERS MOST, and it encodes a diagnosis that was wrong the first time.
// The obvious reading was "the done marker is nested inside an HTML comment, so reject nested
// markers". Measuring first: of the 4 estate kickoffs whose only marker is nested, THREE carry a
// real built_at and are legitimately closed built records — the build lane fills that JSON in place
// and leaves the wrapper, and has since 2026-09-05. Rejecting the nesting would have reddened three
// closed records to catch one unbuilt one. The discriminator is the VALUE, never the placement, and
// H7 fails loudly if anyone re-introduces the placement test.
// =============================================================================================
{
  // H1 — the clean close still reads closed. The regression floor for everything below.
  buildClean();
  {
    const r = runBuild('fx-kickoff-2026-09-08.md');
    check('H1: a real ISO built_at is a CLOSE', mark(r.out, 'done block') === '✔' && /CLOSED/.test(line(r.out, 'rule text unchanged since seal')),
      line(r.out, 'done block').trim());
  }

  // H2 — the template placeholder is NOT a close, and says why.
  buildClean();
  fs.writeFileSync(path.join(EST, 'fx-kickoff-2026-09-08.md'),
    kickoff({ rules: ['R1'], seals: { R1: sha1(RULE1) }, done: 'placeholder' }));
  {
    const r = runBuild('fx-kickoff-2026-09-08.md');
    check('H2: built_at "<ISO>" FAILS the done block', mark(r.out, 'done block built_at') === '✘',
      line(r.out, 'done block built_at').trim());
    check('H2: …and the kickoff reads OPEN, not CLOSED', /OPEN/.test(line(r.out, 'rule text unchanged since seal')),
      line(r.out, 'rule text unchanged since seal').trim());
  }

  // H3 — the consequence that made it worth fixing: a placeholder must not waive the seal. With
  // in-grain rule text moved, a CLOSED kickoff reports and an OPEN one fails. Before this change the
  // placeholder bought the report.
  buildClean();
  fs.writeFileSync(path.join(EST, 'DATA-DICTIONARY.md'), dd([['R1', RULE1 + ' MOVED.'], ['R2', RULE2]]));
  fs.writeFileSync(path.join(EST, 'fx-kickoff-2026-09-08.md'),
    kickoff({ rules: ['R1'], seals: { R1: sha1(RULE1) }, done: 'placeholder' }));
  {
    const r = runBuild('fx-kickoff-2026-09-08.md');
    check('H3: a placeholder built_at does NOT waive the seal on in-grain drift',
      mark(r.out, 'rule text unchanged since seal') === '✘',
      line(r.out, 'rule text unchanged since seal').trim());
  }

  // H4 — an empty seal with a non-empty grain FAILS at build phase.
  buildClean();
  fs.writeFileSync(path.join(EST, 'fx-kickoff-2026-09-08.md'),
    kickoff({ rules: ['R1', 'R2'], seals: {}, done: true }));
  {
    const r = runBuild('fx-kickoff-2026-09-08.md');
    check('H4: rule_text_sha1 {} with a non-empty header.rules FAILS at build',
      mark(r.out, 'header sealed') === '✘', line(r.out, 'header sealed').trim());
    check('H4: …and the message names the real rules, never "[]"',
      /R1, R2/.test(line(r.out, 'header sealed')) && !/header\.rules is \[\]/.test(r.out),
      line(r.out, 'header sealed').trim());
  }

  // H5 — the same fixture at PLAN phase is not a failure: the plan lane has not sealed yet, which is
  // normal. It must still say so truthfully rather than claiming an empty grain.
  {
    const r = run('fx-kickoff-2026-09-08.md', null);
    check('H5: the same unsealed kickoff at --phase plan does not fail', r.status === 0, 'exit ' + r.status);
    check('H5: …and the plan-phase line names the rules awaiting a seal',
      /R1, R2/.test(line(r.out, 'header not sealed yet')), line(r.out, 'header not sealed yet').trim());
  }

  // H6 — the legitimate empty seal still passes: a sync/config change resting on no rule.
  buildClean();
  fs.writeFileSync(path.join(EST, 'fx-kickoff-2026-09-08.md'),
    kickoff({ rules: [], seals: {}, kpath: 'sync', done: true }));
  {
    const r = runBuild('fx-kickoff-2026-09-08.md');
    check('H6: rule_text_sha1 {} with header.rules [] is still a valid empty seal',
      mark(r.out, 'rule text unchanged since seal') === '✔' && /empty grain/.test(line(r.out, 'rule text unchanged since seal')),
      line(r.out, 'rule text unchanged since seal').trim());
  }

  // H7 — a REAL close wrapped in the template's comment is still a close. See the group note.
  buildClean();
  fs.writeFileSync(path.join(EST, 'fx-kickoff-2026-09-08.md'),
    kickoff({ rules: ['R1'], seals: { R1: sha1(RULE1) }, done: 'nested' }));
  {
    const r = runBuild('fx-kickoff-2026-09-08.md');
    check('H7: a real built_at nested in the build-lane comment IS a close (3 estate records rely on this)',
      mark(r.out, 'done block') === '✔' && /CLOSED/.test(line(r.out, 'rule text unchanged since seal')),
      line(r.out, 'done block').trim());
  }
}

// =============================================================================================
// J. THE DECISIONS RECORD — D1 and D2 (2026-09-14). Until this change `kickoff_check.js` never
// mentioned `DECISIONS.md`: a change could mint a rule, seal it and close green with no record of
// who ruled it or why. D1 is per-change (a rule whose register `Since` equals THIS kickoff's date
// owes a row naming THIS kickoff); D2 is estate-wide (every register rule owes at least one row).
//
// ⚠ NAMING. The handoff spec calls these cases E1–E6. Group E above was already taken by the
// REGISTER HEADER SHAPE group, and renaming a cited label is worse than a gap — so they live here
// as J1–J6 in the spec's order, and J7 covers the `Since`-less register the spec describes in prose.
//
// Both checks `fail` from the start, which is only legitimate because the surface was brought under
// them first — the one register rule with no row anywhere was backfilled on Adam's ruling the same
// day. That is the order every cap in group C was flipped in.
//
// Each case breaks the clean fixture in EXACTLY ONE place, and the two checks are read separately:
// a case that reddens both tells you nothing about which one fired.
// =============================================================================================
{
  const D1 = 'DECISIONS: minted rules on record';
  const D2 = 'DECISIONS: every register rule recorded';
  // The v2 register is the one that carries a `Since` column, so D1 is only measurable on it.
  // R1 Since = the kickoff's own date (minted by this change); R2 earlier (cite-only).
  const V2 = () => dd([['R1', RULE1, 'tile 1', '2026-09-08'], ['R2', RULE2, 'tile 1', '2026-09-01']], 'v2');
  function buildDecClean() {
    buildClean();
    fs.writeFileSync(path.join(EST, 'DATA-DICTIONARY.md'), V2());
  }

  // J0 — the clean case. Both green, with the counts the spec names.
  buildDecClean();
  {
    const r = run('fx-kickoff-2026-09-08.md', 'fail');
    check('J0: D1 is ✔ "1 minted of 1" on the clean fixture',
      mark(r.out, D1) === '✔' && /1 minted of 1 header rule\(s\) — 1 recorded/.test(line(r.out, D1)), line(r.out, D1).trim());
    check('J0: D2 is ✔ "2 of 2" on the clean fixture',
      mark(r.out, D2) === '✔' && /2 of 2 rule\(s\) recorded/.test(line(r.out, D2)), line(r.out, D2).trim());
    check('J0: the DECISIONS fixture does not redden the run (exit 0)', r.status === 0, 'exit ' + r.status);
  }

  // J1 (spec E1) — R1's row deleted. D1 loses the row naming this kickoff; D2 loses R1 entirely.
  buildDecClean();
  fs.writeFileSync(path.join(EST, 'DECISIONS.md'), decisions(CLEAN_DECISIONS.filter(d => d[1] !== 'R1')));
  {
    const r = run('fx-kickoff-2026-09-08.md', 'fail');
    check('J1: a minted rule with no row FAILS D1, naming the rule and the kickoff',
      mark(r.out, D1) === '✘' && /no row naming `fx-kickoff-2026-09-08\.md` for R1/.test(line(r.out, D1)), line(r.out, D1).trim());
    check('J1: …and D2 FAILS with a count of 1 of 2, naming R1',
      mark(r.out, D2) === '✘' && /1 of 2 rule\(s\) recorded — no row at all for R1/.test(line(r.out, D2)), line(r.out, D2).trim());
    check('J1: the run reddens (exit 1)', r.status === 1, 'exit ' + r.status);
  }

  // J2 (spec E2) — R1 HAS a row, but its record cell names a sibling kickoff. This is the case the
  // estate's own history is full of, and the one a "does the rule appear anywhere" check misses: D2
  // must stay green while D1 reddens. If D1 ever degrades into D2, this is the case that catches it.
  buildDecClean();
  fs.writeFileSync(path.join(EST, 'DECISIONS.md'), decisions([
    ['2026-09-08', 'R1', '`other-kickoff-2026-09-01.md`'],
    ['2026-09-01', 'R2', '`other-kickoff-2026-09-01.md`'],
  ]));
  {
    const r = run('fx-kickoff-2026-09-08.md', 'fail');
    check('J2: a row whose record names a SIBLING kickoff still FAILS D1',
      mark(r.out, D1) === '✘' && /R1/.test(line(r.out, D1)), line(r.out, D1).trim());
    check('J2: …while D2 stays ✔ — the rule IS recorded, just not by this change',
      mark(r.out, D2) === '✔' && /2 of 2 rule\(s\) recorded/.test(line(r.out, D2)), line(r.out, D2).trim());
  }

  // J3 (spec E3) — no DECISIONS.md at all. Both checks ✘ with a plain detail, exit 1, and NO throw:
  // an absent file must be a finding, not a crash that takes every other check down with it.
  buildDecClean();
  fs.rmSync(path.join(EST, 'DECISIONS.md'));
  {
    const r = spawnSync(process.execPath, [GATE, path.join(EST, 'fx-kickoff-2026-09-08.md'), '--phase', 'plan'], { encoding: 'utf8' });
    const out = (r.stdout || '').replace(/\r\n/g, '\n');
    const err = (r.stderr || '').trim();
    check('J3: a missing DECISIONS.md is ✘ on D1', mark(out, D1) === '✘', line(out, D1).trim());
    check('J3: a missing DECISIONS.md is ✘ on D2', mark(out, D2) === '✘', line(out, D2).trim());
    check('J3: it exits 1 and does NOT throw (no stack trace on stderr)',
      r.status === 1 && !/^\s*at .*:\d+:\d+/m.test(err),
      'exit ' + r.status + (err ? ' | stderr: ' + err.split('\n')[0] : ' | stderr empty'));
  }

  // J4 (spec E4) — an UNRATIFIED plan. Adam has not ruled yet, so there is no ruling to record and
  // nothing is owed; D1 says so rather than reddening a plan that is doing the right thing.
  buildDecClean();
  fs.writeFileSync(path.join(EST, 'fx-kickoff-2026-09-08.md'),
    kickoff({ rules: ['R1'], seals: { R1: sha1(RULE1) }, done: false, ratified: false }));
  {
    const r = run('fx-kickoff-2026-09-08.md', 'fail');
    check('J4: an unratified kickoff reports D1 as `·`, not owed yet', mark(r.out, D1) === '·', line(r.out, D1).trim());
    check('J4: …and does not redden the plan run', r.status === 0, 'exit ' + r.status);
  }

  // J5 (spec E5) — two header rules, only ONE minted by this change. The cite-only rule must be
  // counted in the detail and never failed: citing a rule is not amending it.
  buildDecClean();
  fs.writeFileSync(path.join(EST, 'fx-kickoff-2026-09-08.md'),
    kickoff({ rules: ['R1', 'R2'], seals: { R1: sha1(RULE1), R2: sha1(RULE2) }, done: false }));
  {
    const r = run('fx-kickoff-2026-09-08.md', 'fail');
    check('J5: a cite-only rule is counted, not failed — D1 ✔ "1 minted of 2"',
      mark(r.out, D1) === '✔' && /1 minted of 2 header rule\(s\) — 1 recorded/.test(line(r.out, D1)), line(r.out, D1).trim());
    check('J5: …and the run stays green', r.status === 0, 'exit ' + r.status);
  }

  // J6 (spec E6) — an UNSHAPED register row (a bare `|` in the rule text). Its cells are not the
  // columns the header names, so `Since` is unreadable: D1 must report `·`, never a green tick over
  // a column it could not read. The kickoff is left unsealed so the ONE broken thing is the row
  // shape — an unshaped row is hashed whole, which would otherwise redden the seal check too.
  buildDecClean();
  fs.writeFileSync(path.join(EST, 'DATA-DICTIONARY.md'),
    dd([['R1', 'Fixture rule one | with a bare pipe in it.', 'tile 1', '2026-09-08'], ['R2', RULE2, 'tile 1', '2026-09-01']], 'v2'));
  fs.writeFileSync(path.join(EST, 'fx-kickoff-2026-09-08.md'), kickoff({ rules: ['R1'], done: false }));
  {
    const r = run('fx-kickoff-2026-09-08.md', 'fail');
    check('J6: an unshaped register row reports D1 as `·`, never a silent ✔',
      mark(r.out, D1) === '·' && /`Since` unreadable: R1/.test(line(r.out, D1)), line(r.out, D1).trim());
    check('J6: …and D2 is unaffected — it needs no cells, only the rule id',
      mark(r.out, D2) === '✔' && /2 of 2 rule\(s\) recorded/.test(line(r.out, D2)), line(r.out, D2).trim());
  }

  // J7 — the v1 register has no `Since` column at all. D1 finds the column BY NAME, so it must say
  // it cannot tell a mint from a citation rather than reading index 4 of a 5-column row and calling
  // whatever sits there a date. This is the same defect class as the NOT BUILT check reading `8/30;
  // 8/31` out of a hardcoded index.
  buildClean();   // v1 is buildClean's own shape
  {
    const r = run('fx-kickoff-2026-09-08.md', 'fail');
    check('J7: a register with no `Since` column reports D1 as `·`, naming the columns it found',
      mark(r.out, D1) === '·' && /no `Since` column/.test(line(r.out, D1)), line(r.out, D1).trim());
  }
}

// =============================================================================================
// K. THE SCOPE-DIFF WAIVER COMPARES INSTANTS, NOT CHARACTERS (2026-09-15).
//
// A closed kickoff waives its scope diff once the live snapshot has moved on past the close: the
// build verified the board at `built_at`, and later builds have since changed it, so a diff against
// that old baseline measures other people's work. The test for "has moved on past" was
// `b.harvested_at > doneBlk.obj.built_at` — a JavaScript STRING comparison of two ISO stamps that
// are not written in the same shape. The build lane writes whatever the machine handed it: 42 of the
// 45 closes in the reference estate end in `Z`, two carry a `-04:00` offset, one is a bare date.
// Text sorts `2026-09-09T21:05:00-04:00` BELOW `2026-09-10T01:05:00Z` although they are the SAME
// INSTANT, so a harvest that does not postdate the close reads as though it does and the diff is
// waived — silently, with the run printing green, which is the worst way for a gate to be wrong.
//
// ⚠ WHY THIS NEEDED A FIXTURE AND NOT A RE-RUN. Baselining the gate over all 46 kickoffs in the
// reference estate before and after the fix produced ZERO verdict flips. Not because the defect is
// imaginary, but because neither offset-stamped kickoff declares a dashboard, so neither one reaches
// this branch at all, and the bare-date one waives under both readings. The defect is latent: it
// needs a kickoff that is closed with an offset stamp AND carries a baseline. K1 is that kickoff.
// A fix whose only evidence is "nothing changed" has not been shown to do anything — K1 is the
// falsification, and it fails against the pre-2026-09-15 gate.
// =============================================================================================
{
  // A board pair the scope diff can actually read: same element, one title changed, in scope. The
  // baseline is always older than the current snapshot so the `re-harvest` check cannot fire and
  // confuse the assertion — the only thing these fixtures vary is `built_at`.
  const BOARD = '99999';
  const HARVEST = '2026-09-10T01:05:00.000Z';
  function estatePair() {
    const el = (title) => ({ id: '900001', type: 'vis', title, query_id: 'q1' });
    fs.writeFileSync(path.join(EST, 'estate-' + BOARD + '.pre-fx.json'),
      JSON.stringify({ harvested_at: '2026-09-09T00:00:00.000Z', elements: [el('Fixture tile')], filters: [] }, null, 2));
    fs.writeFileSync(path.join(EST, 'estate-' + BOARD + '.json'),
      JSON.stringify({ harvested_at: HARVEST, elements: [el('Fixture tile v2')], filters: [] }, null, 2));
  }
  function scopeFixture(builtAt) {
    buildClean();
    estatePair();
    fs.writeFileSync(path.join(EST, 'fx-kickoff-2026-09-08.md'), kickoff({
      rules: ['R1'], seals: { R1: sha1(RULE1) }, done: true, kpath: 'tile', builtAt,
      dashboards: [BOARD], baseline: 'estate-' + BOARD + '.pre-fx.json', scope: { elements: ['900001'] },
    }));
    return runBuild('fx-kickoff-2026-09-08.md');
  }
  // `line()` matches a label PREFIX, and `scope 99999 waiver` shares its prefix with the verdict
  // line `scope 99999`. Ask for the em dash so the verdict is read, never the note beside it — a
  // prefix collision here would have these assertions grading the wrong line.
  const verdict = (out) => line(out, 'scope ' + BOARD + ' —');
  const waived = (out) => /no longer applies/.test(verdict(out));
  const measured = (out) => /changed, \d+ added, \d+ removed/.test(verdict(out));

  // K1 — THE NEW GUARD. An offset `built_at` naming the SAME INSTANT as the harvest must not waive:
  // the waiver needs the snapshot to be strictly NEWER than the close, and an equal instant is not
  // newer. Under the old string compare this waived, because `-04:00` sorts below `Z`.
  {
    const r = scopeFixture('2026-09-09T21:05:00-04:00');   // === 2026-09-10T01:05:00.000Z
    check('K1: an offset built_at EQUAL to the harvest instant does NOT waive the scope diff',
      !waived(r.out) && measured(r.out), verdict(r.out).trim());
    check('K1: …and the run names the shape it had to reconcile',
      /UTC offset/.test(line(r.out, 'scope ' + BOARD + ' waiver')), line(r.out, 'scope ' + BOARD + ' waiver').trim());
  }

  // K2 — THE CONTROL. A `Z` close LATER than the harvest must not waive either. Both readings agree
  // here, which is the point: it holds the ordinary case still, so K1 cannot be passing merely
  // because the fix broke the waiver outright.
  {
    const r = scopeFixture('2026-09-11T00:00:00Z');        // after the 09-10 harvest
    check('K2: a Z built_at LATER than the harvest does NOT waive the scope diff',
      !waived(r.out) && measured(r.out), verdict(r.out).trim());
  }

  // K3 — THE REGRESSION FLOOR. The waiver must still fire when it should, or K1 and K2 prove only
  // that the branch is dead. 36 of the reference estate's scope lines are this case.
  {
    const r = scopeFixture('2026-09-09T12:00:00Z');        // before the 09-10 harvest
    check('K3: a Z built_at EARLIER than the harvest still waives the scope diff',
      waived(r.out) && !measured(r.out), verdict(r.out).trim());
  }

  // K4 — the bare date. It parses (midnight UTC), so it stays a real close and still decides the
  // waiver; the gate simply says which shape it read, because midnight is not when anyone built.
  {
    const r = scopeFixture('2026-09-09');                  // midnight UTC, before the harvest
    check('K4: a bare-date built_at is still a real close and still waives',
      waived(r.out) && mark(r.out, 'done block') === '✔', line(r.out, 'done block').trim());
    check('K4: …and both the done block and the waiver name it as a bare date',
      /bare date/.test(line(r.out, 'done block')) && /bare date/.test(line(r.out, 'scope ' + BOARD + ' waiver')),
      line(r.out, 'scope ' + BOARD + ' waiver').trim());
  }
}

// ---- report ---------------------------------------------------------------------------------
let bad = 0;
console.log('gate self-test — ' + GATE);
console.log('fixtures — ' + ROOT + '\n');
for (const c of cases) {
  if (!c.pass) bad++;
  // Print every assertion, not just the failures: a self-test that prints nothing when it passes
  // is indistinguishable from one that ran no assertions at all.
  console.log('  ' + (c.pass ? 'PASS' : 'FAIL') + '  ' + c.name + (c.detail ? '\n          ' + c.detail : ''));
}
console.log('\n' + cases.length + ' assertion(s), ' + bad + ' failed.');
if (bad) {
  console.log('FAIL — a gate check is not behaving as specified. Do not ship the gate.');
} else {
  console.log('PASS — every cap fires and reddens on a broken fixture, stays quiet on a clean one,');
  console.log('       the seal grain still FAILS an open kickoff whose in-grain rule text moved, and');
  console.log('       --pointer scores C3–C8 with no kickoff and reddens on an enforced breach;');
  console.log('       the scaffold stands a tenant up that passes its own gate runs, while');
  console.log('       refusing an unfilled placeholder and refusing to overwrite a live tenant;');
  console.log('       and a minted rule with no DECISIONS row — or one recorded against a SIBLING');
  console.log('       kickoff — reddens, while a cite-only rule and an unratified plan do not.');
}
process.exit(bad ? 1 : 0);
