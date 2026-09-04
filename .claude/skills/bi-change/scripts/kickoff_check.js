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
const kickoff = args.find(a => !a.startsWith('--'));
if (!kickoff) { console.log('usage: node kickoff_check.js <kickoff.md> [--phase plan|build] [--seal]'); process.exit(1); }
const phase = args.includes('--phase') ? args[args.indexOf('--phase') + 1] : 'build';
const seal = args.includes('--seal');

const KICK = path.resolve(kickoff);
const EST_DIR = path.dirname(KICK);
const SCRIPTS = path.join(EST_DIR, '..', 'scripts');
const SCAN = path.join(SCRIPTS, 'bi_impact_scan.js');
const DD = path.join(EST_DIR, 'DATA-DICTIONARY.md');
const BI_PATHS = new Set(['tile', 'new-tile', 'dashboard', 'retire', 'sync']);
const PATHS = new Set(['rule', 'tile', 'new-tile', 'dashboard', 'retire', 'config', 'sync']);

const results = [];
function ok(label, detail) { results.push(['✔', label, detail]); }
function fail(label, detail) { results.push(['✘', label, detail]); }
function info(label, detail) { results.push(['·', label, detail]); }
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
if (BI_PATHS.has(H.path) && !H.dashboards.length) fail('BI path names its dashboards', 'dashboards: []');
if (H.path === 'rule' && !H.rules.length) fail('rule path names its R rows', 'rules: []');

// ---------- Dictionary: rows present, rule text sealed / unchanged ----------
const dd = fs.existsSync(DD) ? read(DD) : '';
if (!dd) fail('Dictionary found', DD);
const rows = {};
for (const m of dd.matchAll(/^\| (R\d+) \|([^\r\n]*)$/gm)) {
  const cells = m[2].split(' | ').map(c => c.trim());
  rows[m[1]] = { rule: cells[0] || '', impl: cells[2] || '', line: m[0] };
}
for (const r of H.rules) { if (rows[r]) ok('register row ' + r, 'present'); else fail('register row ' + r, 'not in the Dictionary — plan lane writes it first'); }
if (seal) {
  H.rule_text_sha1 = Object.fromEntries(Object.entries(rows).map(([r, v]) => [r, sha1(v.rule)]));
  const json = JSON.stringify(H, null, 2);
  text = text.replace(hdr.raw, hdr.raw.replace(hdr.json, json + nl));
  fs.writeFileSync(KICK, text);
  ok('sealed', Object.keys(rows).length + ' rule cells hashed into the header');
} else if (H.rule_text_sha1 && Object.keys(H.rule_text_sha1).length) {
  const changed = Object.entries(H.rule_text_sha1).filter(([r, h]) => rows[r] && sha1(rows[r].rule) !== h).map(([r]) => r);
  const gone = Object.keys(H.rule_text_sha1).filter(r => !rows[r]);
  if (changed.length) fail('rule text unchanged since seal', changed.join(', ') + ' — a build lane edits impl cells only; re-seal from the plan lane if Adam re-ruled');
  else ok('rule text unchanged since seal', Object.keys(H.rule_text_sha1).length + ' rows');
  if (gone.length) fail('sealed rows still present', gone.join(', ') + ' — rows are struck through, never deleted');
} else if (phase === 'build') fail('header sealed', 'run `--seal` from the plan lane before handing off');
else info('header not sealed yet', 'run `--seal` once the R rows are written');

// ---------- plan phase stops here ----------
if (phase === 'plan') report();

// ---------- ratification ----------
if (H.ratified !== true) fail('ratified', 'header.ratified must be true before any build step');
else ok('ratified', 'header says Adam ruled');
const openSec = text.match(/^## [^\r\n]*Open for Adam[^\r\n]*\r?\n([\s\S]*?)(?=^## |\s*$)/m);
if (openSec) {
  const trs = [...openSec[1].matchAll(/^\|([^\r\n]+)\|\s*$/gm)].map(m => m[1].split('|').map(c => c.trim())).filter(c => c.length > 1 && !/^-+$/.test(c[0]) && !/^#?\s*$/.test(c[0]));
  const body = trs.slice(1);
  const unruled = body.filter(c => { const last = c[c.length - 1]; return !last || /^(—|-|open|tbd|\?)$/i.test(last); });
  if (unruled.length) fail('every Open-for-Adam row ruled', unruled.length + ' row(s) with an empty Ruling cell: ' + unruled.map(c => c[0]).join('; '));
  else ok('every Open-for-Adam row ruled', body.length + ' row(s)');
} else info('Open-for-Adam section', 'none found (fine when the plan had no questions)');

// ---------- impl cells no longer say NOT BUILT (BI paths) ----------
if (BI_PATHS.has(H.path) || H.path === 'config') {
  for (const r of H.rules) if (rows[r]) {
    if (/NOT BUILT/i.test(rows[r].impl)) fail('impl cell ' + r, 'still says NOT BUILT'); else ok('impl cell ' + r, 'no NOT BUILT marker');
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
    if (b.harvested_at <= a.harvested_at) fail('re-harvest ' + id, cur + ' (' + b.harvested_at + ') is not newer than the baseline (' + a.harvested_at + ')');
    else ok('re-harvest ' + id, b.harvested_at);
    const A = Object.fromEntries(a.elements.map(e => [String(e.id), e])), B = Object.fromEntries(b.elements.map(e => [String(e.id), e]));
    const changed = Object.keys(B).filter(k => A[k] && JSON.stringify(A[k]) !== JSON.stringify(B[k]));
    const added = Object.keys(B).filter(k => !A[k]);
    const removed = Object.keys(A).filter(k => !B[k]);
    const offScope = changed.filter(k => !H.scope.elements.includes(k));
    const offAdded = added.filter(k => !H.scope.new_elements.some(t => norm(t) === norm(B[k].title || '')));
    const offRemoved = removed.filter(k => !H.scope.retired_elements.includes(k));
    if (offScope.length) fail('scope ' + id + ' changed elements', offScope.map(k => k + ' "' + (B[k].title || '').slice(0, 40) + '"').join('; ') + ' — not in scope.elements');
    if (offAdded.length) fail('scope ' + id + ' added elements', offAdded.map(k => k + ' "' + (B[k].title || '').slice(0, 40) + '"').join('; ') + ' — not in scope.new_elements');
    if (offRemoved.length) fail('scope ' + id + ' removed elements', offRemoved.map(k => k + ' "' + (A[k].title || '').slice(0, 40) + '"').join('; ') + ' — not in scope.retired_elements');
    if (!offScope.length && !offAdded.length && !offRemoved.length) ok('scope ' + id, changed.length + ' changed, ' + added.length + ' added, ' + removed.length + ' removed — all in scope');
    if (H.path !== 'sync' && !changed.length && !added.length && !removed.length && H.path !== 'rule') fail('estate ' + id + ' moved', 'no element differs from the baseline — was the build applied and re-harvested?');
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
  const r = spawnSync(process.execPath, [SCAN, ...argv], { encoding: 'utf8' });
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
