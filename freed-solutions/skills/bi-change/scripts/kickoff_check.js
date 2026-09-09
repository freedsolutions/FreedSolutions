#!/usr/bin/env node
// kickoff_check.js — the login-free gate of the bi-change skill. Zero dependencies.
//
//   node kickoff_check.js <kickoff.md>                 build-phase gate (default): the change is complete
//   node kickoff_check.js <kickoff.md> --phase plan    plan-phase gate: header sane, rules registered
//   node kickoff_check.js <kickoff.md> --seal          plan lane only: write rule-text hashes into the header
//
// The kickoff's location fixes every path: the estate dir is its folder, the scripts dir is
// ../scripts beside it, the Dictionary is DATA-DICTIONARY.md in the estate dir. Nothing here
// names a client. Exit 0 = pass, 1 = fail; the checklist is the report.
//
// Header contract (a fenced ```json block right after the marker line `<!-- bi-change:header -->`):
//   path            rule | tile | new-tile | dashboard | retire | config | sync
//   lane, model     who executes next (plan | build) and the model Adam routes it to
//   rules           ["R62", ...]  R rows this change touches (may be [] for sync)
//   dashboards      ["28006", ...]  boards touched (may be [] for rule / config)
//   scope           { elements: [ids the build may change], new_elements: [titles], retired_elements: [ids],
//                     retired_titles: [titles that must vanish from the docs], filters: true|false }
//   baseline        estate-<id>.pre-<slug>.json captured before the build (one board) or {id: file}
//   retire_needles  strings that must be gone from every executable surface after the build (--verify)
//   ratified        true once Adam has ruled on every "Open for Adam" row
//   rule_text_sha1  written by --seal: {R62: "<sha1 of the rule cell>", ...} for EVERY register row
//
// Done block contract (a fenced ```json block after the marker `<!-- bi-change:done -->`, inside the
// Status section): built_at, harvest (snapshot file name per board), elements_touched, counts
// ({before, after} per touched query), open_items (may be []).

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { spawnSync } = require('child_process');

const args = process.argv.slice(2);
// Flags that consume the NEXT argument, which therefore is not a candidate kickoff path. Without
// this, `--phase build` left "build" eligible as the kickoff — harmless only by the convention that
// the kickoff comes first — and `--caps fail` would have made "fail" eligible too.
const VALUED = new Set(['--phase', '--caps']);
const consumedArg = new Set();
args.forEach((a, i) => { if (VALUED.has(a)) consumedArg.add(i + 1); });
const kickoff = args.find((a, i) => !a.startsWith('--') && !consumedArg.has(i));
if (!kickoff) { console.log('usage: node kickoff_check.js <kickoff.md> [--phase plan|build] [--seal] [--caps info|fail]'); process.exit(1); }
const phase = args.includes('--phase') ? args[args.indexOf('--phase') + 1] : 'build';
const seal = args.includes('--seal');
// P2 size caps. Every surface here accepts appends, so every surface became a log; the gate checked
// presence and never size, and what the gate does not measure drifts. Each cap reports a COUNT so a
// silently-inert check is visible as a zero that never moves.
// `--caps info|fail` overrides the per-cap default below: that is how a deliberately-broken
// fixture proves each check both FIRES and REDDENS, rather than passing vacuously.
const CAP_MODE = args.includes('--caps') ? args[args.indexOf('--caps') + 1] : null;
if (CAP_MODE && !['info', 'fail'].includes(CAP_MODE)) { console.log('--caps must be info|fail, got: ' + CAP_MODE); process.exit(1); }
// Caps in chars / lines, ruled 2026-09-08.
const CAPS = { rule: 600, preamble: 40, claudeLines: 120, claudeLine: 300, readmeStamp: 200 };
// ENFORCEMENT IS PER CAP, not global (scaffold-cleanup §6 step 5).
//   C3 CLAUDE.md · C4 README stamp · C5 guide change logs -> 'fail'. P4 brought them under the
//     caps in Phase A, so a breach from here is new drift and should redden.
//   C1 rule cell · C2 Dictionary preamble -> 'info' until Phase B. They measure the register and
//     the preamble, which P1 rewrites and which Phase A is explicitly forbidden to touch; failing
//     them now would redden every kickoff for a breach nothing is allowed to fix. Phase B flips
//     them as its last step.
const CAP_ENFORCE = { rule: 'info', preamble: 'info', claude: 'fail', readme: 'fail', guides: 'fail' };

const KICK = path.resolve(kickoff);
const EST_DIR = path.dirname(KICK);
const SCRIPTS = path.join(EST_DIR, '..', 'scripts');
// The scanner ships WITH the skill now (P6, 2026-09-08) — it is client-agnostic by content and was
// only ever tied to one client by sitting beside it. The old client-side copy is still honoured so
// an estate that has not migrated keeps working; the skill copy wins when both exist.
const SCAN = [
  path.join(__dirname, 'bi_impact_scan.js'),
  path.join(SCRIPTS, 'bi_impact_scan.js'),
].find(p => fs.existsSync(p)) || path.join(__dirname, 'bi_impact_scan.js');
const DD = path.join(EST_DIR, 'DATA-DICTIONARY.md');
const CLAUDE_MD = path.join(EST_DIR, '..', 'CLAUDE.md');
const BI_PATHS = new Set(['tile', 'new-tile', 'dashboard', 'retire', 'sync']);
const PATHS = new Set(['rule', 'tile', 'new-tile', 'dashboard', 'retire', 'config', 'sync']);

const results = [];
function ok(label, detail) { results.push(['✔', label, detail]); }
function fail(label, detail) { results.push(['✘', label, detail]); }
function info(label, detail) { results.push(['·', label, detail]); }
// A cap breach. `which` names the cap so enforcement can differ per cap (see CAP_ENFORCE);
// an explicit `--caps` on the command line overrides every one of them, for fixtures.
function cap(which, label, detail) {
  const mode = CAP_MODE || CAP_ENFORCE[which] || 'info';
  (mode === 'fail' ? fail : info)(label, detail);
}
function read(p) { return fs.readFileSync(p, 'utf8'); }
function sha1(s) { return crypto.createHash('sha1').update(s.replace(/\s+/g, ' ').trim()).digest('hex').slice(0, 12); }
function norm(s) { return s.toLowerCase().replace(/[‘’]/g, "'").replace(/[“”]/g, '"').replace(/\s+/g, ' '); }

// ---------- header ----------
let text = read(KICK);
const nl = text.includes('\r\n') ? '\r\n' : '\n';
function block(marker) {
  const re = new RegExp('<!-- bi-change:' + marker + ' -->\\r?\\n```json\\r?\\n([\\s\\S]*?)```');
  const m = text.match(re); if (!m) return null;
  try { return { obj: JSON.parse(m[1]), raw: m[0], json: m[1] }; } catch (e) { fail('header ' + marker + ' parses', e.message); return null; }
}
const hdr = block('header');
if (!hdr) { fail('header block present', 'expected `<!-- bi-change:header -->` followed by a ```json fence'); report(); }
const H = hdr.obj;
if (!PATHS.has(H.path)) fail('path is one of ' + [...PATHS].join('|'), String(H.path)); else ok('path', H.path);
if (!['plan', 'build'].includes(H.lane)) fail('lane is plan|build', String(H.lane)); else ok('lane / model', H.lane + ' / ' + (H.model || '?'));
H.rules = H.rules || []; H.dashboards = (H.dashboards || []).map(String); H.scope = H.scope || {};
H.scope.elements = (H.scope.elements || []).map(String); H.scope.new_elements = H.scope.new_elements || [];
H.scope.retired_elements = (H.scope.retired_elements || []).map(String); H.scope.retired_titles = H.scope.retired_titles || [];
H.artifacts = H.artifacts || [];
if (BI_PATHS.has(H.path) && !H.dashboards.length && !(H.path === 'sync' && H.artifacts.length)) fail('BI path names its dashboards', 'dashboards: [] (a sync of a reference artifact lists it under artifacts instead)');
if (H.path === 'rule' && !H.rules.length) fail('rule path names its R rows', 'rules: []');
// artifacts: reference files the change produces or refreshes (a sync of the explore catalog, a baseline
// census) — each must exist in the estate dir at build phase
if (phase !== 'plan') for (const a of H.artifacts) { if (fs.existsSync(path.join(EST_DIR, a))) ok('artifact ' + a, 'present'); else fail('artifact ' + a, 'not in the estate dir'); }

// ---------- Dictionary: rows present, rule text sealed / unchanged ----------
const dd = fs.existsSync(DD) ? read(DD) : '';
if (!dd) fail('Dictionary found', DD);
// The register is the FIRST contiguous run of `| Rnn |` rows; later tables that cite rule ids in their
// first cell (the export-only register, appendices) are not register rows. First occurrence wins.
// Split on UNESCAPED pipes only — `\|` inside a cell is content, not a delimiter. The expected
// segment count comes from the register's own header row, never a hardcoded 5.
function splitCells(body) { return body.split(/(?<!\\)\|/).map(c => c.trim()); }
const hdrRow = dd.match(/^\| # \|([^\r\n]*)$/m);
// header body ends with a trailing empty segment, same as a data row; -1 for the consumed `| Rnn |`
const EXPECT = hdrRow ? splitCells(hdrRow[1]).length : 4;

const rows = {};
for (const m of dd.matchAll(/^\| (R\d+) \|([^\r\n]*)$/gm)) {
  if (rows[m[1]]) continue;
  const cells = splitCells(m[2]);
  // A row carrying an unescaped `|` inside its prose cannot be cut into cells reliably — the extra
  // pipes are indistinguishable from delimiters, and they land in BOTH the rule and the impl cell
  // (Product Line names are themselves pipe-delimited, so this recurs). For those rows the whole
  // body is hashed, so no rule text can be edited outside the seal, and `impl` is left null rather
  // than pointing at whatever segment happens to sit at index 2 (on 3-segment rows that is the
  // DATES cell, and the NOT BUILT check was silently testing `8/30; 8/31`).
  const shaped = cells.length === EXPECT;
  rows[m[1]] = {
    rule: shaped ? (cells[0] || '') : m[2],
    impl: shaped ? (cells[2] || '') : null,
    // The rule CELL as best it can be cut, for the size cap only — never for the seal. On an
    // unshaped row this is the text up to the first unescaped pipe, so it is a LOWER BOUND on the
    // real cell; a lower bound over the cap still proves the breach, and one under it is reported
    // as unmeasured rather than counted as passing.
    ruleCell: cells[0] || '',
    legacyRule: m[2].split(' | ').map(c => c.trim())[0] || '',
    segments: cells.length, shaped, line: m[0],
  };
}
{
  const odd = Object.entries(rows).filter(([, v]) => !v.shaped);
  // Reported, never failed: the ACTUAL defect (rule text escaping the seal) is closed by the
  // whole-row hash above, so an unshaped row is a known limitation, not a broken kickoff. Failing
  // here would redden every kickoff in the estate until canon is re-escaped, which Adam has not
  // asked for. Read the COUNT — if it grows, a new row has picked up an unescaped pipe.
  if (odd.length) info('register row shape', odd.length + ' of ' + Object.keys(rows).length +
    ' row(s) carry an unescaped `|` and cannot be cut into cells: ' +
    odd.map(([r, v]) => r + ' (' + v.segments + ' vs ' + EXPECT + ')').join(', ') +
    ' — rule text is hashed WHOLE-ROW for these so nothing escapes the seal, and their impl cell is not checked; escape the pipes as `\\|` to restore per-cell checking');
  else ok('register row shape', Object.keys(rows).length + ' row(s), all ' + EXPECT + ' cells');
}
for (const r of H.rules) { if (rows[r]) ok('register row ' + r, 'present'); else fail('register row ' + r, 'not in the Dictionary — plan lane writes it first'); }
if (seal) {
  // P3 — SEAL GRAIN. A seal exists to prove the rules THIS change rests on did not move under it.
  // Hashing all 76 register rows made every kickoff hostage to every peer: one rule cell edited
  // anywhere reddened every closed record in the estate, forever, and the only way to clear it was
  // to re-seal — which rewrites the record. The grain is header.rules.
  const grain = H.rules.filter(r => rows[r]);
  H.rule_text_sha1 = Object.fromEntries(grain.map(r => [r, sha1(rows[r].rule)]));
  const json = JSON.stringify(H, null, 2);
  text = text.replace(hdr.raw, hdr.raw.replace(hdr.json, json + nl));
  fs.writeFileSync(KICK, text);
  ok('sealed', grain.length + ' rule cell(s) hashed into the header' +
    (grain.length ? ': ' + grain.join(', ') : ' (header.rules is empty — this change rests on no rule)'));
} else if (H.rule_text_sha1 && Object.keys(H.rule_text_sha1).length) {
  // A kickoff sealed BEFORE 2026-09-06 hashed `split(' | ')[0]` for every row, which on an
  // unshaped row is a truncated fragment. Accept that legacy value on unshaped rows only, and
  // report it — re-sealing a closed kickoff to clear it would rewrite the record.
  // Tolerance keys on the SEAL, not on row shape: the pre-2026-09-06 parser split on the literal
  // `' | '`, which both truncated the ambiguous rows AND mis-cut rows whose pipes lack surrounding
  // spaces (R14 / R46 / R47 parse correctly now, so their hashes legitimately moved). Accepting the
  // legacy value is safe because it is recomputed from the CURRENT text — if the text had changed,
  // neither hash would match and the row still fails.
  const mism = Object.entries(H.rule_text_sha1).filter(([r, h]) => rows[r] && sha1(rows[r].rule) !== h);
  const legacy = mism.filter(([r, h]) => sha1(rows[r].legacyRule) === h).map(([r]) => r);
  const changed = mism.filter(([r, h]) => sha1(rows[r].legacyRule) !== h).map(([r]) => r);
  const gone = Object.keys(H.rule_text_sha1).filter(r => !rows[r]);
  // P3 — the two axes that decide whether drift is a DEFECT or just history moving on.
  //
  // GRAIN: kickoffs sealed before 2026-09-08 hashed all 76 rows, not just header.rules. Those extra
  // hashes are not this change's business, so drift on them is reported, never failed. Scoping at
  // CHECK time (rather than re-sealing) is deliberate: re-sealing a closed kickoff rewrites the
  // record, and the record is the thing being protected.
  //
  // CLOSED: a done block means the change shipped and was verified at built_at. Canon moving after
  // that is expected, not a regression in this record — the same reasoning the scope diff already
  // applies to a newer live snapshot. Closed kickoffs report drift; open ones still fail on it.
  const closed = !!block('done');
  const inGrain = r => H.rules.includes(r);
  const hard = closed ? [] : changed.filter(inGrain);
  const soft = changed.filter(r => !hard.includes(r));
  const goneHard = closed ? [] : gone.filter(inGrain);
  const goneSoft = gone.filter(r => !goneHard.includes(r));
  const why = closed ? 'closed kickoff — canon moved after this record closed' : 'outside header.rules — not this change’s grain';
  const sealedNote = Object.keys(H.rule_text_sha1).length + ' sealed row(s), grain = ' +
    (H.rules.length ? H.rules.join(', ') : '(none — this change rests on no rule)') +
    (closed ? '; CLOSED' : '; OPEN');

  if (hard.length) fail('rule text unchanged since seal', hard.join(', ') + ' — a build lane edits impl cells only; re-seal from the plan lane if Adam re-ruled');
  else ok('rule text unchanged since seal', sealedNote +
    (legacy.length ? '; ' + legacy.length + ' sealed under the pre-2026-09-06 parser: ' + legacy.join(', ') + ' — unchanged, do NOT re-seal a closed kickoff' : ''));
  if (soft.length) info('rule text drift (not failed)', soft.length + ' row(s) moved since the seal — ' + why + ': ' + soft.join(', '));
  if (goneHard.length) fail('sealed rows still present', goneHard.join(', ') + ' — rows are struck through, never deleted');
  if (goneSoft.length) info('sealed rows gone (not failed)', goneSoft.length + ' row(s) no longer in the register — ' + why + ': ' + goneSoft.join(', '));
} else if (H.rule_text_sha1) {
  // An EMPTY seal is a real seal under P3: a sync / config change that rests on no rule has nothing
  // to hash. Without this branch it fell through to "header sealed ✘" and could never go green.
  ok('rule text unchanged since seal', 'sealed with an empty grain — header.rules is [], so this change rests on no rule text');
} else if (phase === 'build') fail('header sealed', 'run `--seal` from the plan lane before handing off');
else info('header not sealed yet', 'run `--seal` once the R rows are written');

// ---------- P2 size caps ----------
// Estate-wide, not per-kickoff: every run of the gate re-measures them, so bloat cannot creep back
// in behind a change that happens not to touch the bloated surface. Every check prints a COUNT even
// when clean — a check that reports nothing is indistinguishable from a check that never ran.
{
  // C1 — rule cell ≤ CAPS.rule chars. The register is the surface that turned into a log.
  const measured = Object.entries(rows).map(([r, v]) => ({ r, n: v.ruleCell.length, shaped: v.shaped }));
  const over = measured.filter(m => m.n > CAPS.rule).sort((a, b) => b.n - a.n);
  // An unshaped row's cell is a lower bound (see rows[].ruleCell): under the cap it proves nothing.
  const unmeasured = measured.filter(m => !m.shaped && m.n <= CAPS.rule);
  const worst = measured.reduce((a, b) => (b.n > a.n ? b : a), { r: '-', n: 0 });
  if (over.length) cap('rule', 'cap: rule cell ≤ ' + CAPS.rule,
    over.length + ' of ' + measured.length + ' row(s) over (max ' + worst.n + ' chars, ' + worst.r + '): ' +
    over.slice(0, 8).map(m => m.r + ' ' + m.n).join(', ') + (over.length > 8 ? ', …' : ''));
  else ok('cap: rule cell ≤ ' + CAPS.rule, '0 of ' + measured.length + ' row(s) over (max ' + worst.n + ' chars, ' + worst.r + ')');
  if (unmeasured.length) info('cap: rule cell — unmeasured', unmeasured.length + ' unshaped row(s) measured to the first unescaped `|` only, so their length is a lower bound: ' + unmeasured.map(m => m.r).join(', '));

  // C2 — Dictionary preamble ≤ CAPS.preamble lines. Everything before the register header row.
  if (dd) {
    const hdrIdx = dd.split(/\r?\n/).findIndex(l => /^\| # \|/.test(l));
    if (hdrIdx < 0) info('cap: Dictionary preamble', 'no `| # |` register header row found — cannot measure');
    else {
      const pre = dd.split(/\r?\n/).slice(0, hdrIdx);
      const longest = pre.reduce((a, l, i) => (l.length > a.n ? { n: l.length, i: i + 1 } : a), { n: 0, i: 0 });
      if (pre.length > CAPS.preamble) cap('preamble', 'cap: Dictionary preamble ≤ ' + CAPS.preamble + ' lines',
        pre.length + ' lines (longest ' + longest.n + ' chars at line ' + longest.i + ')');
      else ok('cap: Dictionary preamble ≤ ' + CAPS.preamble + ' lines', pre.length + ' lines (longest ' + longest.n + ' chars)');
    }
  }

  // C3 — client CLAUDE.md ≤ CAPS.claudeLines lines, no line > CAPS.claudeLine chars. It loads into
  // EVERY session, so its size is a tax on all of them. Two separate counts: a file can sit inside
  // the line budget purely because its log was appended onto one enormous line.
  if (fs.existsSync(CLAUDE_MD)) {
    const cl = read(CLAUDE_MD).split(/\r?\n/);
    const longLines = cl.map((l, i) => ({ i: i + 1, n: l.length })).filter(x => x.n > CAPS.claudeLine).sort((a, b) => b.n - a.n);
    const maxLen = cl.reduce((a, l) => Math.max(a, l.length), 0);
    if (cl.length > CAPS.claudeLines) cap('claude', 'cap: CLAUDE.md ≤ ' + CAPS.claudeLines + ' lines', cl.length + ' lines');
    else ok('cap: CLAUDE.md ≤ ' + CAPS.claudeLines + ' lines', cl.length + ' lines');
    if (longLines.length) cap('claude', 'cap: CLAUDE.md line ≤ ' + CAPS.claudeLine + ' chars',
      longLines.length + ' line(s) over (max ' + maxLen + ' chars at line ' + longLines[0].i + '): ' +
      longLines.slice(0, 8).map(x => 'L' + x.i + ' ' + x.n).join(', ') + (longLines.length > 8 ? ', …' : ''));
    else ok('cap: CLAUDE.md line ≤ ' + CAPS.claudeLine + ' chars', '0 of ' + cl.length + ' line(s) over (max ' + maxLen + ')');
  } else info('cap: CLAUDE.md', 'not found at ' + CLAUDE_MD);

  // C4 — README "Last synced" stamp ≤ CAPS.readmeStamp chars. A one-line latest-state field that
  // was appended to instead of replaced; the narrative belongs to the owning kickoff.
  const readmePath = path.join(EST_DIR, 'README.md');
  if (fs.existsSync(readmePath)) {
    const stamp = read(readmePath).split(/\r?\n/).find(l => /^\*\*Last synced/.test(l));
    if (stamp === undefined) info('cap: README stamp', 'no `**Last synced` line found — cannot measure');
    else if (stamp.length > CAPS.readmeStamp) cap('readme', 'cap: README stamp ≤ ' + CAPS.readmeStamp, stamp.length + ' chars (1 stamp line)');
    else ok('cap: README stamp ≤ ' + CAPS.readmeStamp, stamp.length + ' chars');
  }

  // C5 — guide "## Change log" entries are POINTER lines: one line, a date, and the kickoff that
  // holds the narrative. Counted per guide across the estate, not just the board in scope.
  const guides = fs.readdirSync(EST_DIR).filter(f => /^dashboard-\d+.*\.md$/.test(f)).sort();
  const bad = [];
  let entries = 0, sectionLines = 0;
  for (const g of guides) {
    const lines = read(path.join(EST_DIR, g)).split(/\r?\n/);
    const start = lines.findIndex(l => /^##\s+Change log\s*$/i.test(l));
    if (start < 0) continue;
    let end = lines.slice(start + 1).findIndex(l => /^## /.test(l));
    end = end < 0 ? lines.length : start + 1 + end;
    const sec = lines.slice(start + 1, end).filter(l => l.trim());
    sectionLines += sec.length;
    const isEntry = l => /^\s*[-*] /.test(l);
    // A short prose block BEFORE the first entry is section framing — it states the convention and
    // names the archive. That is not the per-entry narrative this cap exists to move out, so it is
    // allowed, but bounded: past FRAME_MAX lines it is a log growing back and counts as narrative.
    const FRAME_MAX = 4;
    const first = sec.findIndex(isEntry);
    const frame = first < 0 ? sec.length : first;
    const body = first < 0 ? [] : sec.slice(first);
    const opens = body.filter(isEntry);
    entries += opens.length;
    // Continuation lines are counted only AFTER the first entry — those are wrapped narrative.
    const cont = body.length - opens.length + Math.max(0, frame - FRAME_MAX);
    // An entry must be ONE line that names its record. Deliberately NOT anchored on an ISO date:
    // two guides open with a legitimately undated origin entry ("Earlier —", "2026-05 (approx) —").
    // And no `[^|]*` guard — an entry may legitimately quote a filter literal containing `|`
    // (`-Promo |%`), which the old guard rejected as if it were a table pipe.
    const notPointer = opens.filter(l => !/\.md`?\s*$/.test(l) && !/\.(?:xlsx|pdf|csv|docx|json)`?\s*$/.test(l));
    if (cont || notPointer.length) bad.push(g.replace(/^dashboard-/, '').replace(/\.md$/, '') +
      ' (' + opens.length + ' entries, ' + notPointer.length + ' not pointing at a record, ' + cont + ' narrative lines)');
  }
  if (!guides.length) info('cap: guide change logs', 'no dashboard-*.md guides in the estate dir');
  else if (bad.length) cap('guides', 'cap: guide change log = pointer lines',
    bad.length + ' of ' + guides.length + ' guide(s) carry narrative (' + entries + ' entries over ' + sectionLines + ' lines): ' + bad.join('; '));
  else ok('cap: guide change log = pointer lines', guides.length + ' guide(s), ' + entries + ' entries, all pointer-shaped');
}

// ---------- plan phase stops here ----------
if (phase === 'plan') report();

// ---------- ratification ----------
if (H.ratified !== true) fail('ratified', 'header.ratified must be true before any build step');
else ok('ratified', 'header says Adam ruled');
// ⚠ The section terminator must be "the next `## ` heading, or the true end of the string". Written as
// `\s*$` under /m it matched at the FIRST line end, capturing zero characters — so this check parsed no
// rows and passed vacuously on every kickoff, leaving `ratified` as the only ratification guard
// (found 2026-09-05, conc-tile-retire run). `$(?![\s\S])` is end-of-input even under /m.
const openSec = text.match(/^## [^\r\n]*Open for Adam[^\r\n]*\r?\n([\s\S]*?)(?=^## |$(?![\s\S]))/m);
if (openSec) {
  const trs = [...openSec[1].matchAll(/^\|([^\r\n]+)\|\s*$/gm)].map(m => m[1].split('|').map(c => c.trim())).filter(c => c.length > 1 && !/^-+$/.test(c[0]) && !/^#?\s*$/.test(c[0]));
  // The filter above already drops a `| # |`-style header, so an unconditional slice(1) ate the FIRST
  // REAL row (its Ruling was never checked). Drop a leading row only when it IS the header.
  const body = trs.length && /^ruling$/i.test(trs[0][trs[0].length - 1] || '') ? trs.slice(1) : trs;
  const unruled = body.filter(c => { const last = c[c.length - 1]; return !last || /^(—|-|open|tbd|\?)$/i.test(last); });
  if (unruled.length) fail('every Open-for-Adam row ruled', unruled.length + ' row(s) with an empty Ruling cell: ' + unruled.map(c => c[0]).join('; '));
  else ok('every Open-for-Adam row ruled', body.length + ' row(s)');
} else info('Open-for-Adam section', 'none found (fine when the plan had no questions)');

// ---------- impl cells no longer say NOT BUILT (BI paths) ----------
if (BI_PATHS.has(H.path) || H.path === 'config') {
  for (const r of H.rules) if (rows[r]) {
    // On a row whose cell boundaries are ambiguous, test the WHOLE row rather than skipping: the
    // marker is caught wherever it sits, which is strictly more conservative than reading one
    // segment. Never leave the check unrun — an unchecked row is how a NOT BUILT ships.
    const hay = rows[r].impl === null ? rows[r].line : rows[r].impl;
    const where = rows[r].impl === null ? ' (whole row — ambiguous cells, see `register row shape`)' : '';
    if (/NOT BUILT/i.test(hay)) fail('impl cell ' + r, 'still says NOT BUILT' + where);
    else ok('impl cell ' + r, 'no NOT BUILT marker' + where);
  }
}

// ---------- estate scope diff ----------
function loadEstate(file) { const d = JSON.parse(read(path.join(EST_DIR, file))); return d.sandbox || d; }
function estateFile(id) { return fs.readdirSync(EST_DIR).find(f => new RegExp('^estate-' + id + '[^.]*\\.json$').test(f)); }
for (const id of H.dashboards) {
  const cur = estateFile(id);
  if (!cur) { fail('estate ' + id, 'no estate-' + id + '*.json — harvest it'); continue; }
  const base = typeof H.baseline === 'object' && H.baseline ? H.baseline[id] : (H.dashboards.length === 1 ? H.baseline : null);
  if (H.path === 'dashboard' && !base) { ok('estate ' + id, cur + ' present (new board, no baseline expected)'); }
  else if (!base || !fs.existsSync(path.join(EST_DIR, base))) { fail('baseline ' + id, 'header.baseline missing or not on disk: ' + base); continue; }
  else {
    const a = loadEstate(base), b = loadEstate(cur);
    const doneBlk = block('done');
    if (doneBlk && doneBlk.obj.built_at && b.harvested_at > doneBlk.obj.built_at) {
      // closed kickoff: later builds have moved the live snapshot on; its own verification happened at built_at
      info('scope ' + id, 'closed ' + doneBlk.obj.built_at + '; live snapshot ' + b.harvested_at + ' is newer, so the scope diff no longer applies');
      continue;
    }
    if (b.harvested_at <= a.harvested_at) fail('re-harvest ' + id, cur + ' (' + b.harvested_at + ') is not newer than the baseline (' + a.harvested_at + ')');
    else ok('re-harvest ' + id, b.harvested_at);
    const A = Object.fromEntries(a.elements.map(e => [String(e.id), e])), B = Object.fromEntries(b.elements.map(e => [String(e.id), e]));
    // Compare on a shape-normalised copy: `null`, `undefined` and `""` are the same ABSENCE, and an
    // absent key is the same as an empty one. Harvester versions disagree on which they write (the
    // pre-2026-09 harvester emitted `null` for title / query_id / merge_result_id / look_id and
    // always carried the look keys; the current one writes `""` and omits them), so a raw
    // JSON.stringify compare reports EVERY element of an older baseline as changed and buries a real
    // hand-drift in the noise. Proven on 26741 2026-09-04: 10 "changed" elements, 0 real differences.
    const elSig = (e) => JSON.stringify(Object.fromEntries(Object.keys(e).sort()
      .map(k => [k, e[k] === null || e[k] === undefined ? '' : e[k]])
      .filter(([, v]) => v !== '')));
    const changed = Object.keys(B).filter(k => A[k] && elSig(A[k]) !== elSig(B[k]));
    const added = Object.keys(B).filter(k => !A[k]);
    const removed = Object.keys(A).filter(k => !B[k]);
    // A blank text tile is a LAYOUT SPACER, not content (Adam's convention, confirmed 2026-09-04):
    // type `text` with no title, title_text, subtitle_text or body_text. It carries no query and no
    // merge, so it cannot move any count or any tile's result — adding or removing one is never a
    // scope violation. Reported below so it stays visible, never failed on.
    const isSpacer = e => e && e.type === 'text' &&
      !(e.title || '').trim() && !(e.title_text || '').trim() &&
      !(e.subtitle_text || '').trim() && !(e.body_text || '').trim();
    const addedSpacers = added.filter(k => isSpacer(B[k]));
    const removedSpacers = removed.filter(k => isSpacer(A[k]));
    const offScope = changed.filter(k => !H.scope.elements.includes(k));
    const offAdded = added.filter(k => !addedSpacers.includes(k) && !H.scope.new_elements.some(t => norm(t) === norm(B[k].title || '')));
    const offRemoved = removed.filter(k => !removedSpacers.includes(k) && !H.scope.retired_elements.includes(k));
    if (addedSpacers.length || removedSpacers.length) ok('spacer tiles ' + id,
      [addedSpacers.length ? '+' + addedSpacers.join(', +') : '', removedSpacers.length ? '-' + removedSpacers.join(', -') : '']
        .filter(Boolean).join(' ') + ' — blank text tile(s), layout spacers, not scope');
    if (offScope.length) fail('scope ' + id + ' changed elements', offScope.map(k => k + ' "' + (B[k].title || '').slice(0, 40) + '"').join('; ') + ' — not in scope.elements');
    if (offAdded.length) fail('scope ' + id + ' added elements', offAdded.map(k => k + ' "' + (B[k].title || '').slice(0, 40) + '"').join('; ') + ' — not in scope.new_elements');
    if (offRemoved.length) fail('scope ' + id + ' removed elements', offRemoved.map(k => k + ' "' + (A[k].title || '').slice(0, 40) + '"').join('; ') + ' — not in scope.retired_elements');
    if (!offScope.length && !offAdded.length && !offRemoved.length) ok('scope ' + id, changed.length + ' changed, ' + added.length + ' added, ' + removed.length + ' removed — all in scope');
    // Spacers do not count as evidence the build landed — a blank tile someone else added must not
    // satisfy this check on behalf of a build that never wrote anything.
    const realAdded = added.length - addedSpacers.length, realRemoved = removed.length - removedSpacers.length;
    if (H.path !== 'sync' && !changed.length && !realAdded && !realRemoved && H.path !== 'rule') fail('estate ' + id + ' moved', 'no element differs from the baseline — was the build applied and re-harvested?');
    const fa = JSON.stringify(a.filters || []), fb = JSON.stringify(b.filters || []);
    if (fa !== fb && !H.scope.filters) fail('scope ' + id + ' dashboard filters', 'filters changed but scope.filters is not true');
    else if (fa !== fb) ok('scope ' + id + ' dashboard filters', 'changed, in scope');
  }
  // docs carry the board: guide, SOP section, WI page (new-tile / dashboard) and the new titles
  const guide = fs.readdirSync(EST_DIR).find(f => f.startsWith('dashboard-' + id) && f.endsWith('.md'));
  const sop = fs.existsSync(path.join(EST_DIR, 'BI-SOP.md')) ? read(path.join(EST_DIR, 'BI-SOP.md')) : '';
  const wi = fs.existsSync(path.join(EST_DIR, 'BI-WI.md')) ? read(path.join(EST_DIR, 'BI-WI.md')) : '';
  const readme = fs.existsSync(path.join(EST_DIR, 'README.md')) ? read(path.join(EST_DIR, 'README.md')) : '';
  if (H.path === 'dashboard') {
    if (guide) ok('guide ' + id, guide); else fail('guide ' + id, 'no dashboard-' + id + '-*.md');
    if (new RegExp('Dashboard SOP — .*\\(' + id + '\\)').test(sop)) ok('SOP section ' + id, 'present'); else fail('SOP section ' + id, 'no "Dashboard SOP — … (' + id + ')" heading (Appendix A template)');
    if (readme.includes('estate-' + id)) ok('README roster ' + id, 'present'); else fail('README roster ' + id, 'README.md does not list estate-' + id);
  }
  const surfaces = [['BI-SOP.md', norm(sop)], ['BI-WI.md', norm(wi)], [guide || '(no guide)', norm(guide ? read(path.join(EST_DIR, guide)) : '')]];
  for (const t of H.scope.new_elements) {
    const missing = surfaces.filter(([, s]) => !s.includes(norm(t))).map(([n]) => n);
    if (missing.length) fail('new tile in docs "' + t.slice(0, 40) + '"', 'missing from ' + missing.join(', ')); else ok('new tile in docs "' + t.slice(0, 40) + '"', 'SOP, WI, guide');
  }
  for (const t of H.scope.retired_titles) {
    const still = surfaces.filter(([, s]) => s.includes(norm(t))).map(([n]) => n);
    if (still.length) fail('retired tile out of docs "' + t.slice(0, 40) + '"', 'still named in ' + still.join(', ')); else ok('retired tile out of docs "' + t.slice(0, 40) + '"', 'gone');
  }
}

// ---------- mechanized scans ----------
function scan(argv) {
  if (!fs.existsSync(SCAN)) return { status: -1, out: 'scan not found: ' + SCAN };
  // The estate dir is passed explicitly: the scanner no longer infers it from its own location.
  const r = spawnSync(process.execPath, [SCAN, '--estate', EST_DIR, ...argv], { encoding: 'utf8' });
  return { status: r.status, out: (r.stdout || '') + (r.stderr || '') };
}
{
  const r = scan(['--stale']);
  const tail = r.out.trim().split(/\r?\n/).slice(-1)[0] || '';
  if (r.status === 0) ok('--stale', tail); else fail('--stale', tail || ('exit ' + r.status));
}
for (const n of H.retire_needles || []) {
  const r = scan(['--verify', n]);
  const tail = r.out.trim().split(/\r?\n/).slice(-1)[0] || '';
  if (r.status === 0) ok('--verify "' + n + '"', tail); else fail('--verify "' + n + '"', tail + ' — clean it, or drop the needle from the header and record the accepted residual in Status');
}

// ---------- Status + done block ----------
if (!/^## [^\r\n]*Status/m.test(text)) fail('Status section', 'none — append it (as-built, dated)'); else ok('Status section', 'present');
const done = block('done');
if (!done) fail('done block', 'expected `<!-- bi-change:done -->` + ```json inside Status');
else {
  const need = ['built_at', 'harvest', 'elements_touched', 'counts', 'open_items'].filter(k => !(k in done.obj));
  if (need.length) fail('done block keys', 'missing ' + need.join(', ')); else ok('done block', 'built_at ' + done.obj.built_at + ', open items ' + (done.obj.open_items || []).length);
}

report();

function report() {
  const fails = results.filter(r => r[0] === '✘').length;
  console.log('bi-change check — ' + path.basename(KICK) + ' — phase ' + phase + (seal ? ' (seal)' : ''));
  for (const [m, l, d] of results) console.log('  ' + m + ' ' + l + (d ? ' — ' + d : ''));
  console.log(fails ? '\n' + fails + ' check(s) failed.' : '\nAll checks passed.');
  process.exit(fails ? 1 : 0);
}
