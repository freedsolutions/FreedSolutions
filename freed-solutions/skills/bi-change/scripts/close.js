#!/usr/bin/env node
// close.js — the bi-change CLOSE-OUT of the tenant pointer in ONE call. Zero dependencies.
//
//   node close.js --tenant <dir> --lane "<lane>" --what "<what>" --record <path> [--date YYYY-MM-DD]
//                 [--state <Key> "<bullet text>"]... [--sub "<old>" "<new>"]... [--fold N]
//                 [--decision <rule cell> "<ruling>"]... [--decision-record "<record cell>"]
//                 [--verify-twin <a> <b>] [--spec <file.json>] [--dry-run]
//   node close.js --verify-twin <a> <b>          the twin verdict alone; no tenant, nothing written
//
// It replaces the per-session one-off scripts that each re-implemented the same edit:
//   1. --verify-twin  md5 + row count of two result files (real vs twin); ONE verdict line. DIFFER = exit 1,
//                     and nothing else runs.
//   2. --state        REPLACE one Current-state bullet, found by its bold key (`- **Estate:**`; exact key,
//                     else a unique prefix). Never an append. Text without a leading `- ` keeps the key;
//                     a `\n` in the text makes the second line (indented two spaces). --sub swaps a literal
//                     that occurs exactly ONCE in the Current-state section. Either moves the heading's
//                     `(YYYY-MM-DD)` forward to --date.
//   3. change log     ONE line `- <date> (<lane>) — <what> — `<record>`` above the newest dated line. The
//                     record must exist inside the tenant dir (looked up from the tenant, the estate, cwd);
//                     text after its first space is kept as a note (`notes/x.md §2e`).
//   4. fold           while the pointer is over CAPS.claudeLines (or --fold N asks for N), move the OLDEST
//                     dated line — the one directly above `- Earlier (N folded …)` — to the archive file
//                     that Earlier line names in backticks, and bump N (and its `to <date>`).
//   5. --decision     append one `| date | rule | ruling | record |` row per flag to the estate DECISIONS.md.
//                     Record = --decision-record, else the change-log record's basename in backticks.
//   6. caps           every number comes from kickoff_check.js (CAPS, POINTER_EOL) — never a copy here.
//                     Any breach REFUSES: exit 2, nothing written.
//   7. write + gate   archive, DECISIONS, pointer; then `kickoff_check.js --pointer <tenant>`. A red gate
//                     restores every file byte for byte and exits 1.
// Line endings: each file keeps its own and a BOM is kept. The pointer must already be pure POINTER_EOL
// (it is rewritten); the archive and DECISIONS are only appended to, so a mixed one takes its dominant
// terminator and the report names the mix.
// --dry-run prints the diff and the verdicts and writes nothing.
// --spec  a JSON file with the same fields in snake_case: {"tenant", "date", "lane", "what", "record",
//         "state": [{"key", "text"}], "subs": [{"old", "new"}], "fold", "decisions": [{"rule", "ruling",
//         "record"}], "decision_record", "verify_twin": [a, b], "dry_run"}. A flag overrides a scalar and
//         adds to a list. Use a spec for any text with quotes: no shell quoting applies to a file.
//
// Exit 0 = written (or dry run, or twin SAME). 1 = twin DIFFER, or the gate was red after the write and
// every file was restored. 2 = refused: nothing written. Nothing here names a client.
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { spawnSync } = require('child_process');
const { refuse, runMain, localDate, isoDate, checkCell } = require('./canon_common.js');
const GATE = path.join(__dirname, 'kickoff_check.js');
const { CAPS, POINTER_EOL, findEstate } = require(GATE);

// ---------- arguments ----------
// name -> how many values it takes (0 = boolean). An unknown flag is refused, so a typo is never ignored.
const ARITY = { tenant: 1, date: 1, lane: 1, what: 1, record: 1, state: 2, sub: 2, fold: 1, decision: 2,
  'decision-record': 1, 'verify-twin': 2, spec: 1, 'dry-run': 0 };
const LISTS = new Set(['state', 'sub', 'decision']);
function parse(argv) {
  const a = { state: [], sub: [], decision: [] };
  for (let i = 0; i < argv.length; i++) {
    const t = argv[i];
    if (!t.startsWith('--')) refuse('unexpected argument ' + JSON.stringify(t));
    const name = t.slice(2);
    if (!(name in ARITY)) refuse('unknown flag ' + t);
    const n = ARITY[name];
    if (!n) { a[name] = true; continue; }
    const vals = argv.slice(i + 1, i + 1 + n);
    if (vals.length < n || vals.some(v => v.startsWith('--'))) refuse(t + ' needs ' + n + ' value(s)');
    i += n;
    if (LISTS.has(name)) a[name].push(vals); else a[name] = n === 1 ? vals[0] : vals;
  }
  return a;
}
function request(argv) {
  const a = parse(argv);
  let s = {};
  if (a.spec) {
    try { s = JSON.parse(fs.readFileSync(a.spec, 'utf8').replace(/^﻿/, '')); }
    catch (e) { refuse('--spec ' + a.spec + ': ' + e.message); }
  }
  const pick = (flag, key) => (a[flag] !== undefined ? a[flag] : s[key]);
  const specState = Array.isArray(s.state) ? s.state : Object.entries(s.state || {}).map(([key, text]) => ({ key, text }));
  const r = {
    tenant: pick('tenant', 'tenant'), date: pick('date', 'date'), lane: pick('lane', 'lane'),
    what: pick('what', 'what'), record: pick('record', 'record'), fold: pick('fold', 'fold'),
    decisionRecord: pick('decision-record', 'decision_record'), twin: pick('verify-twin', 'verify_twin'),
    dryRun: !!(a['dry-run'] || s.dry_run),
    state: [...specState, ...a.state.map(([key, text]) => ({ key, text }))],
    subs: [...(s.subs || []), ...a.sub.map(([o, n]) => ({ old: o, new: n }))],
    decisions: [...(s.decisions || []), ...a.decision.map(([rule, ruling]) => ({ rule, ruling }))],
  };
  r.date = isoDate(r.date || localDate(), '--date');
  const f = r.fold === undefined ? 0 : Number(r.fold);
  if (!Number.isInteger(f) || f < 0) refuse('--fold must be a whole number ≥ 0, got ' + JSON.stringify(r.fold));
  r.fold = f;
  if (r.twin !== undefined && (!Array.isArray(r.twin) || r.twin.length !== 2)) refuse('--verify-twin takes two files');
  return r;
}

// ---------- small helpers ----------
const md5 = b => crypto.createHash('md5').update(b).digest('hex');
// The line terminator of a text, or MIXED. A file with none at all reads as `none`.
function eolOf(t) {
  const crlf = (t.match(/\r\n/g) || []).length;
  const lf = (t.match(/(?<!\r)\n/g) || []).length;
  const cr = (t.match(/\r(?!\n)/g) || []).length;
  const kinds = [['CRLF', crlf], ['LF', lf], ['CR', cr]].filter(([, n]) => n);
  return kinds.length === 0 ? 'none' : kinds.length > 1 ? 'MIXED' : kinds[0][0];
}
const EOLS = { CRLF: '\r\n', LF: '\n', CR: '\r' };
// The terminator an APPEND uses. An append-only file is never rewritten, so a mixed one is not refused:
// the new lines take its DOMINANT terminator (ties: the last one in the file) and the report names the mix.
function appendEol(t, fallback, label) {
  const n = { CRLF: (t.match(/\r\n/g) || []).length, LF: (t.match(/(?<!\r)\n/g) || []).length, CR: (t.match(/\r(?!\n)/g) || []).length };
  const found = Object.entries(n).filter(([, c]) => c);
  if (!found.length) return { eol: fallback, note: null };
  if (found.length === 1) return { eol: EOLS[found[0][0]], note: null };
  const lastK = /\r\n$/.test(t) ? 'CRLF' : /\n$/.test(t) ? 'LF' : /\r$/.test(t) ? 'CR' : null;
  const top = Math.max(...found.map(([, c]) => c));
  const pick = found.filter(([, c]) => c === top).map(([k]) => k);
  const k = pick.includes(lastK) ? lastK : pick[0];
  return { eol: EOLS[k], note: label + ' has MIXED line endings (' + found.map(([x, c]) => c + ' ' + x).join(', ') +
    '); appended in ' + k + ', the dominant one; its existing bytes are untouched' };
}
function oneLine(v, what) {
  if (typeof v !== 'string' || !v.trim()) refuse(what + ' is missing');
  if (/[\r\n]/.test(v)) refuse(what + ' holds a line break (it is one line)');
  if (v !== v.trim()) refuse(what + ' has leading or trailing whitespace');
  return v;
}
const norm = s => String(s).toLowerCase().replace(/[`*]/g, '').replace(/\s+/g, ' ').trim();
function section(lines, re) {
  const s = lines.findIndex(l => re.test(l));
  if (s < 0) return null;
  let e = lines.slice(s + 1).findIndex(l => /^## /.test(l));
  return [s, e < 0 ? lines.length : s + 1 + e];
}
const STATE_RE = /^##\s+Current state\b/i;          // the gate's C7 / C10 heading
const LOG_RE = /^##\s+Change log\s*$/i;
const isTop = l => /^[-*] /.test(l);                 // the gate's C10 top-level bullet
const isDated = l => /^- \d{4}-\d{2}-\d{2}/.test(l);
const EARLIER_RE = /^- Earlier \((\d+) folded/;
// Top-level bullets of a section: the opening line plus its contiguous non-blank continuation lines.
function bullets(lines, s, e) {
  const out = [];
  for (let k = s + 1; k < e; k++) {
    const l = lines[k];
    if (isTop(l)) {
      const m = l.match(/^[-*] \*\*(.+?)\*\*/);
      out.push({ start: k, end: k + 1, label: m ? m[1].replace(/:\s*$/, '').trim() : null });
    } else if (out.length && l.trim() && out[out.length - 1].end === k) out[out.length - 1].end = k + 1;
  }
  return out;
}

// ---------- 1. the twin verdict ----------
// Rows = non-blank lines; a JSON file holding an array counts its elements.
function rowsOf(buf, f) {
  const t = buf.toString('utf8').replace(/^﻿/, '');
  if (/\.json$/i.test(f)) { try { const j = JSON.parse(t); if (Array.isArray(j)) return j.length; } catch (e) { /* text */ } }
  return t.split(/\r\n|\r|\n/).filter(l => l.trim()).length;
}
function twin([a, b]) {
  for (const f of [a, b]) if (!fs.existsSync(f) || !fs.statSync(f).isFile()) refuse('--verify-twin: no such file ' + f);
  const A = fs.readFileSync(a), B = fs.readFileSync(b);
  const [ma, mb, ra, rb] = [md5(A), md5(B), rowsOf(A, a), rowsOf(B, b)];
  if (ma === mb) return { same: true, line: 'twin: SAME — md5 ' + ma + ' · ' + ra + ' row(s) · ' + path.basename(a) + ' = ' + path.basename(b) };
  const unify = buf => buf.toString('utf8').replace(/\r\n?/g, '\n');
  const eolOnly = unify(A) === unify(B);
  return { same: false, line: 'twin: DIFFER — md5 ' + ma + ' ≠ ' + mb + ' · rows ' + ra + ' vs ' + rb +
    (eolOnly ? ' · LINE ENDINGS ONLY' : '') + ' · ' + path.basename(a) + ' vs ' + path.basename(b) };
}

// ---------- the record ----------
function resolveRecord(rec, tenant, est) {
  const m = oneLine(rec, '--record').match(/^(\S+)(\s+.*)?$/);
  const p = m[1].replace(/^`|`$/g, '');
  const tries = path.isAbsolute(p) ? [p] : [path.join(tenant, p), ...(est ? [path.join(est, p)] : []), path.resolve(p)];
  const hit = tries.find(t => fs.existsSync(t) && fs.statSync(t).isFile());
  if (!hit) refuse('record not found: ' + p + ' (looked from the tenant, the estate and the working dir) — the log line must point at a real record');
  const rel = path.relative(tenant, hit);
  if (!rel || rel.startsWith('..') || path.isAbsolute(rel)) refuse('record ' + hit + ' is outside the tenant dir ' + tenant);
  return { shown: '`' + rel.split(path.sep).join('/') + '`' + (m[2] || ''), base: path.basename(hit) };
}

// ---------- the pointer edit (pure: lines in, lines out) ----------
function editPointer(lines0, r, logLine) {
  const lines = lines0.slice();
  const notes = [];
  // 2. state bullets and subs, all located on the ORIGINAL lines, applied bottom-up.
  if (r.state.length || r.subs.length) {
    const sr = section(lines, STATE_RE);
    if (!sr) refuse('no `## Current state` heading in the pointer — nothing to replace');
    const bl = bullets(lines, sr[0], sr[1]);
    const seen = new Set();
    const repl = r.state.map(({ key, text }) => {
      oneLine(String(key || ''), '--state key');
      if (typeof text !== 'string' || !text.trim()) refuse('--state ' + key + ': the new text is missing');
      const k = norm(key);
      let hit = bl.filter(b => b.label && norm(b.label) === k);
      if (!hit.length) hit = bl.filter(b => b.label && norm(b.label).startsWith(k));
      if (hit.length !== 1) refuse('--state ' + JSON.stringify(key) + ' matches ' + hit.length + ' bullet(s) of ' +
        bl.length + ' (' + bl.map(b => b.label || '(no key)').join(' · ') + ') — exactly one, by its bold key');
      if (seen.has(hit[0].start)) refuse('--state ' + JSON.stringify(key) + ': that bullet is already replaced by another --state');
      seen.add(hit[0].start);
      const parts = text.split(/\r?\n/);
      if (!isTop(parts[0])) parts[0] = '- **' + hit[0].label + ':** ' + parts[0];
      for (let i = 1; i < parts.length; i++) {
        if (!parts[i].trim()) refuse('--state ' + key + ': a blank continuation line ends the bullet');
        if (isTop(parts[i])) refuse('--state ' + key + ': line ' + (i + 1) + ' opens a NEW bullet — one bullet per --state');
        if (!/^\s/.test(parts[i])) parts[i] = '  ' + parts[i];
      }
      if (parts.length > CAPS.stateBullet) refuse('--state ' + key + ': ' + parts.length + ' lines, the cap is ' +
        CAPS.stateBullet + ' — the record keeps the detail');
      return { b: hit[0], parts, key: hit[0].label };
    });
    const subHits = r.subs.map(({ old: o, new: n }) => {
      oneLine(String(o || ''), '--sub old text');
      if (typeof n !== 'string' || /[\r\n]/.test(n)) refuse('--sub new text must be one line');
      if (o === n) refuse('--sub: the old and new text are the same');
      const at = [];
      for (let k = sr[0] + 1; k < sr[1]; k++) { let i = -1; while ((i = lines[k].indexOf(o, i + 1)) >= 0) at.push(k); }
      if (at.length !== 1) refuse('--sub ' + JSON.stringify(o) + ' occurs ' + at.length + ' time(s) in Current state — exactly once');
      if (repl.some(x => at[0] >= x.b.start && at[0] < x.b.end)) refuse('--sub ' + JSON.stringify(o) + ' sits in a bullet --state replaces');
      return { k: at[0], o, n };
    });
    for (const s of subHits) lines[s.k] = lines[s.k].replace(s.o, () => s.n);
    for (const x of repl.slice().sort((p, q) => q.b.start - p.b.start)) {
      notes.push('state: "' + x.key + '" replaced (' + (x.b.end - x.b.start) + ' → ' + x.parts.length + ' line(s))');
      lines.splice(x.b.start, x.b.end - x.b.start, ...x.parts);
    }
    if (subHits.length) notes.push('state: ' + subHits.length + ' literal(s) swapped');
    const hm = lines[sr[0]].match(/\((\d{4}-\d{2}-\d{2})\)/);
    if (hm && r.date > hm[1]) { lines[sr[0]] = lines[sr[0]].replace(hm[0], '(' + r.date + ')'); notes.push('state: heading ' + hm[1] + ' → ' + r.date); }
  }
  // 3. the change-log line.
  let cr = section(lines, LOG_RE);
  if (!cr) refuse('no `## Change log` heading in the pointer');
  if (lines.includes(logLine)) refuse('that change-log line is already in the pointer');
  let at = -1;
  for (let k = cr[0] + 1; k < cr[1]; k++) if (isDated(lines[k]) || EARLIER_RE.test(lines[k])) { at = k; break; }
  if (at < 0) { at = cr[1]; while (at > cr[0] + 1 && !lines[at - 1].trim()) at--; }
  lines.splice(at, 0, logLine);
  // 4. the fold.
  const folded = [];
  let archive = null;
  while (folded.length < r.fold || lines.length > CAPS.claudeLines) {
    cr = section(lines, LOG_RE);
    const ei = [];
    for (let k = cr[0] + 1; k < cr[1]; k++) if (EARLIER_RE.test(lines[k])) ei.push(k);
    if (ei.length !== 1) refuse('the pointer is ' + lines.length + ' lines (cap ' + CAPS.claudeLines + ') or --fold asks for one, ' +
      'and the change log has ' + ei.length + ' `- Earlier (N folded …)` line(s) — exactly one names the archive');
    const e = ei[0];
    const tick = lines[e].match(/`[^`]+`/g) || [];
    archive = tick.length ? tick[tick.length - 1].slice(1, -1) : null;
    if (!archive) refuse('the Earlier line names no archive file in backticks');
    let oldest = -1;
    for (let k = cr[0] + 1; k < e; k++) if (isDated(lines[k])) oldest = k;
    if (oldest !== e - 1) refuse('the oldest dated change-log line does not sit directly above the Earlier line — fold by hand');
    if (lines[oldest] === logLine) refuse('folding would archive the line this close adds — the log holds nothing older');
    folded.push(lines[oldest]);
    lines.splice(oldest, 1);
    const n = e - 1;
    lines[n] = lines[n].replace(EARLIER_RE, (m, c) => m.replace('(' + c + ' folded', '(' + (Number(c) + 1) + ' folded'));
    const fd = folded[folded.length - 1].match(/^- (\d{4}-\d{2}-\d{2})/)[1];
    const to = lines[n].match(/folded, to (\d{4}-\d{2}-\d{2})/);
    if (to && fd > to[1]) lines[n] = lines[n].replace(to[0], 'folded, to ' + fd);
  }
  return { lines, notes, folded, archive };
}

// The caps the gate enforces on what this edit touches, measured the gate's way (JS chars, the gate's split).
function capCheck(lines) {
  const why = [];
  if (lines.length > CAPS.claudeLines) why.push(lines.length + ' lines, cap ' + CAPS.claudeLines);
  const long = lines.map((l, i) => [i + 1, l.length]).filter(([, n]) => n > CAPS.claudeLine);
  if (long.length) why.push(long.length + ' line(s) over ' + CAPS.claudeLine + ' chars: ' + long.map(([i, n]) => 'L' + i + ' ' + n).join(', '));
  const sr = section(lines, STATE_RE);
  if (sr) {
    const bl = bullets(lines, sr[0], sr[1]);
    if (bl.length > CAPS.stateBullets) why.push(bl.length + ' Current-state bullets, cap ' + CAPS.stateBullets);
    const fat = bl.filter(b => b.end - b.start > CAPS.stateBullet);
    if (fat.length) why.push(fat.length + ' bullet(s) over ' + CAPS.stateBullet + ' lines: ' + fat.map(b => b.label || 'L' + (b.start + 1)).join(', '));
  }
  return why;
}

// A line diff (LCS) for the dry run; the pointer is ~120 lines, so the table is small.
function diff(a, b) {
  const n = a.length, m = b.length;
  const dp = Array.from({ length: n + 1 }, () => new Int32Array(m + 1));
  for (let i = n - 1; i >= 0; i--) for (let j = m - 1; j >= 0; j--) dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
  const out = [];
  let i = 0, j = 0, hunk = null;
  const flush = () => { if (hunk) { out.push('@@ -' + hunk.i + ' +' + hunk.j + ' @@', ...hunk.del, ...hunk.add); hunk = null; } };
  while (i < n || j < m) {
    if (i < n && j < m && a[i] === b[j]) { flush(); i++; j++; continue; }
    if (!hunk) hunk = { i: i + 1, j: j + 1, del: [], add: [] };
    if (j < m && (i >= n || dp[i][j + 1] >= dp[i + 1][j])) hunk.add.push('+ ' + b[j++]);
    else hunk.del.push('- ' + a[i++]);
  }
  flush();
  return out;
}

// ---------- main ----------
function main() {
  const r = request(process.argv.slice(2));
  const say = s => console.log(s);
  let tw = null;
  if (r.twin) {
    tw = twin(r.twin);
    if (!r.tenant) { say(tw.line); return tw.same ? 0 : 1; }
    if (!tw.same) { say(tw.line); say('close: NOT written — the twin differs; nothing else ran.'); return 1; }
  }
  if (!r.tenant) refuse('--tenant <dir> is required (or --verify-twin <a> <b> alone)');
  const tenant = path.resolve(r.tenant);
  const ptr = path.join(tenant, 'CLAUDE.md');
  if (!fs.existsSync(ptr)) refuse('no CLAUDE.md in ' + tenant + ' — not a tenant dir');
  const est = findEstate(tenant);
  const lane = oneLine(r.lane, '--lane');
  const what = oneLine(r.what, '--what');
  const rec = resolveRecord(r.record, tenant, est);
  const logLine = '- ' + r.date + ' (' + lane + ') — ' + what + ' — ' + rec.shown;
  if (logLine.length > CAPS.claudeLine) refuse('the change-log line is ' + logLine.length + ' chars, the cap is ' +
    CAPS.claudeLine + ' — shorten --what; the record holds the narrative');

  // The pointer: pure POINTER_EOL, or refused (C9 would redden it anyway, and a rewrite must not convert it).
  const ptrBuf = fs.readFileSync(ptr);
  const ptrText = ptrBuf.toString('utf8');
  const kind = eolOf(ptrText);
  if (kind !== POINTER_EOL) refuse('the pointer line endings are ' + kind + ', the convention is ' + POINTER_EOL +
    ' — convert the endings first, change nothing else');
  const EOL = EOLS[kind];
  const before = ptrText.split(EOL);
  const ed = editPointer(before, r, logLine);
  const capWhy = capCheck(ed.lines);
  if (capWhy.length) refuse('the closed pointer would breach a cap: ' + capWhy.join('; '));
  const writes = [];   // [file, new text]

  // The archive takes the folded lines, oldest first as folded, in its own line ending.
  let archRel = null;
  if (ed.folded.length) {
    const arch = path.isAbsolute(ed.archive) ? ed.archive : path.join(tenant, ed.archive);
    if (!fs.existsSync(arch)) refuse('the archive the Earlier line names does not exist: ' + arch);
    const at = fs.readFileSync(arch, 'utf8');
    const { eol: ae, note: an } = appendEol(at, EOL, 'the archive');
    if (an) ed.notes.push(an);
    const have = new Set(at.split(/\r\n|\r|\n/));
    const dup = ed.folded.filter(l => have.has(l));
    if (dup.length) refuse('the archive already holds ' + dup.length + ' of the folded line(s): ' + dup[0]);
    writes.push([arch, at + (at === '' || /[\r\n]$/.test(at) ? '' : ae) + ed.folded.map(l => l + ae).join('')]);
    archRel = path.relative(tenant, arch).split(path.sep).join('/');
  }

  // 5. DECISIONS rows.
  if (r.decisions.length) {
    if (!est) refuse('no estate (DATA-DICTIONARY.md) below ' + tenant + ' — DECISIONS.md cannot be found');
    const dec = path.join(est, 'DECISIONS.md');
    if (!fs.existsSync(dec)) refuse('no DECISIONS.md in ' + est);
    const dt = fs.readFileSync(dec, 'utf8');
    const { eol: de, note: dn } = appendEol(dt, '\n', 'DECISIONS.md');
    if (dn) ed.notes.push(dn);
    const dl = dt.split(/\r\n|\r|\n/);
    const last = dl.filter(l => l.trim()).pop() || '';
    if (!last.startsWith('|')) refuse('DECISIONS.md does not end on its table — append the row by hand where it belongs');
    const rows = r.decisions.map(d => {
      const recCell = d.record || r.decisionRecord || '`' + rec.base + '`';
      const row = '| ' + r.date + ' | ' + checkCell(d.rule, 'decision rule cell') + ' | ' + checkCell(d.ruling, 'decision ruling') +
        ' | ' + checkCell(recCell, 'decision record') + ' |';
      if (dl.includes(row)) refuse('DECISIONS.md already holds that row: ' + row);
      return row;
    });
    writes.push([dec, dt + (dt === '' || /[\r\n]$/.test(dt) ? '' : de) + rows.map(l => l + de).join('')]);
  }
  const ptrNew = ed.lines.join(EOL);
  writes.push([ptr, ptrNew]);

  // Report.
  say('bi-change close — ' + path.basename(tenant) + ' — ' + r.date + (r.dryRun ? ' — DRY RUN, nothing written' : ''));
  if (tw) say('  ' + tw.line);
  for (const n of ed.notes) say('  ' + n);
  say('  change log: +1 line (' + logLine.length + ' of ' + CAPS.claudeLine + ' chars)');
  if (ed.folded.length) say('  fold: ' + ed.folded.length + ' oldest line(s) → ' + archRel);
  if (r.decisions.length) say('  DECISIONS: +' + r.decisions.length + ' row(s)');
  const maxLen = ed.lines.reduce((m, l) => Math.max(m, l.length), 0);
  say('  pointer: ' + before.length + ' → ' + ed.lines.length + ' lines (cap ' + CAPS.claudeLines + '), longest ' + maxLen +
    ' chars (cap ' + CAPS.claudeLine + '), ' + POINTER_EOL + ' kept');
  if (r.dryRun) {
    say('\n--- ' + path.basename(ptr));
    for (const l of diff(before, ed.lines)) say(l);
    for (const [f, t] of writes.slice(0, -1)) {
      const old = fs.readFileSync(f, 'utf8');
      say('\n--- ' + path.relative(tenant, f).split(path.sep).join('/') + ' (append; line endings ' + eolOf(old) + ' before)');
      for (const l of t.slice(old.length).split(/\r\n|\r|\n/).filter(x => x !== '')) say('+ ' + l);
    }
    say('\ndry run: caps pass in memory; the gate runs on the real write.');
    return 0;
  }

  // 7. Write, then the gate. Red = every file restored byte for byte.
  const orig = writes.map(([f]) => [f, fs.readFileSync(f)]);
  const restore = () => { for (const [f, b] of orig) fs.writeFileSync(f, b); };
  try { for (const [f, t] of writes) fs.writeFileSync(f, Buffer.from(t, 'utf8')); }
  catch (e) { restore(); throw e; }
  const g = spawnSync(process.execPath, [GATE, '--pointer', tenant], { encoding: 'utf8' });
  const gout = ((g.stdout || '') + (g.stderr || '')).trim().split(/\r?\n/);
  if (g.status !== 0) {
    restore();
    for (const l of gout.filter(l => l.includes('✘'))) say('  ' + l.trim());
    const again = spawnSync(process.execPath, [GATE, '--pointer', tenant], { encoding: 'utf8' });
    say('  gate: RED after the write — every file restored; ' +
      (again.status === 0 ? 'the tenant is green without this close, so the close caused it.' : 'the tenant was already red before this close.'));
    return 1;
  }
  say('  gate: ' + gout[gout.length - 1] + ' (kickoff_check.js --pointer)');
  if (r.decisions.length && /^- \*\*Canon:\*\*.*Mirror:\s*SHADOW/m.test(ptrText))
    say('  canon: DECISIONS.md changed and the Canon line says Mirror: SHADOW — the mirror sync is owed (SKILL.md Close-out step 7).');
  say('  written: ' + writes.map(([f]) => path.relative(tenant, f).split(path.sep).join('/')).join(', '));
  return 0;
}

runMain(main);
