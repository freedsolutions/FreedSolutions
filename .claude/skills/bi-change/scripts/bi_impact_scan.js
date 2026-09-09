#!/usr/bin/env node
// bi_impact_scan.js — the mechanized Step 2 / Step 4 / Step 5 checks of the BI change-ripple
// runbook (BI-SOP.md §2 — the single copy since 2026-09-02).
//
// Usage:
//   node <skill>/scripts/bi_impact_scan.js --estate <dir> "<needle>"     literal, case-insensitive
//   node <skill>/scripts/bi_impact_scan.js --estate <dir> "/regex/i"     regex form
//   node <skill>/scripts/bi_impact_scan.js --estate <dir> --verify "<n>" Step 4 residual check: structured
//                                                                        surfaces only, raw hits classified
//   node <skill>/scripts/bi_impact_scan.js --estate <dir> --stale        doc-stamp vs harvest freshness +
//                                                                        render freshness + dictionary-ahead
//                                                                        + content checks (tiles/filters in docs)
//
// Needle mode scans, per estate snapshot: dashboard filters (name / field / default), element
// titles + text tiles, element LISTEN mappings, queries (dynamic-field labels + expressions +
// slugs, filtered-measure filters / filter_expression, baked filters, filter_config chips,
// fields, sorts, pivots), merges (merge-level calcs + filtered measures, merge_fields, sorts),
// folder Looks (calcs, filters, fields) — every hit attributed to dashboard + tile id + title —
// then the dictionary, the guides, the SOPs, the WIs, the README and the latest expression
// inventory. Output is the ripple worklist (Step 3 tiles) and the doc sync list (Step 5).
//
// History: 8/29 shipped · 8/30 render-freshness · 8/31 filtered-measure filters (a room-rename
// ripple found 7 tiles the scan had missed) · 9/2 listen / sorts / filter_config / merge_fields
// / Look filters coverage, --verify with raw-vs-structured self-check (whole-file greps had
// produced false residual failures from Looker's vis_config cache), --stale content checks.

const fs = require('fs');
const path = require('path');

// The estate dir is an ARGUMENT, not this file's location (P6, 2026-09-08). The scanner is
// client-agnostic by content — it was only ever bound to one client by sitting next to it — so it
// moved into the bi-change skill and now takes `--estate <dir>`. Resolution order:
//   1. --estate <dir>
//   2. $BI_ESTATE_DIR
//   3. ./bi-estate under the cwd, then ../bi-estate — the shapes an operator runs from
// `--estate` is stripped from argv before any positional read, so `--stale` / `--verify` / a bare
// needle keep working in either position.
const rawArgs = process.argv.slice(2);
let estateArg = null;
{
  const i = rawArgs.indexOf('--estate');
  if (i !== -1) { estateArg = rawArgs[i + 1]; rawArgs.splice(i, 2); }
}
const ARGS = rawArgs;
function resolveEstate() {
  if (estateArg) return path.resolve(estateArg);
  if (process.env.BI_ESTATE_DIR) return path.resolve(process.env.BI_ESTATE_DIR);
  for (const c of [path.resolve('bi-estate'), path.resolve('..', 'bi-estate')]) {
    if (fs.existsSync(path.join(c, 'DATA-DICTIONARY.md'))) return c;
  }
  console.error('bi_impact_scan: no estate dir. Pass --estate <dir>, set BI_ESTATE_DIR, or run from a\n' +
    'directory holding bi-estate/DATA-DICTIONARY.md.');
  process.exit(2);
}
const EST_DIR = resolveEstate();
// Estate files are discovered, not listed (9/4): every estate-<id>*.json without a dot before .json is a
// live snapshot; .pre-<slug>.json baselines are excluded by the dot. A new dashboard needs no edit here.
const ESTATES = Object.fromEntries(fs.readdirSync(EST_DIR).filter(f => /^estate-\d+[^.]*\.json$/.test(f))
  .sort().map(f => [f.match(/^estate-(\d+)/)[1], f]));
const CROSS_DOCS = ['BI-SOP.md', 'BI-WI.md', 'ITEM-CREATION-SOP.md', 'ITEM-CREATION-WI.md', 'DATA-DICTIONARY.md', 'README.md'];

function loadEstate(file) {
  const doc = JSON.parse(fs.readFileSync(path.join(EST_DIR, file), 'utf8'));
  return { doc, est: doc.sandbox || doc, looks: doc.looks ? (Array.isArray(doc.looks) ? doc.looks : Object.values(doc.looks)) : [] };
}
function guideFiles() { return fs.readdirSync(EST_DIR).filter(f => /^dashboard-\d+.*\.md$/.test(f)); }
function latestInventory() {
  const cands = fs.readdirSync(EST_DIR).filter(f => /^expression-inventory-.*\.csv$/.test(f)).sort();
  return cands[cands.length - 1] || null;
}
function dfList(q) {
  let d = q && q.dynamic_fields;
  if (typeof d === 'string') { try { d = JSON.parse(d); } catch (e) { return []; } }
  return Array.isArray(d) ? d : [];
}
function makeRe(raw) {
  const rm = raw.match(/^\/(.*)\/([a-z]*)$/);
  if (rm) return new RegExp(rm[1], rm[2].includes('g') ? rm[2] : rm[2] + 'g');
  return new RegExp(raw.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
}

// ---------- structured estate walk (shared by needle mode and --verify) ----------
function scanEstates(re) {
  const hits = (text) => { if (typeof text !== 'string') return 0; const m = text.match(re); return m ? m.length : 0; };
  const worklist = []; let total = 0;
  for (const [dash, file] of Object.entries(ESTATES)) {
    const { est, looks } = loadEstate(file);
    const byQid = {}, byMid = {};
    for (const el of est.elements || []) {
      if (el.query_id) (byQid[el.query_id] = byQid[el.query_id] || []).push(el);
      if (el.merge_result_id) (byMid[el.merge_result_id] = byMid[el.merge_result_id] || []).push(el);
      if (el.look_query_id) (byQid[el.look_query_id] = byQid[el.look_query_id] || []).push(el);
    }
    const srcToMid = {};
    for (const [mid, m] of Object.entries(est.merges || {}))
      for (const sq of m.source_queries || []) (srcToMid[sq.query_id] = srcToMid[sq.query_id] || []).push(mid);
    function owners(qid, mid) {
      const els = new Map();
      if (qid) { for (const el of byQid[qid] || []) els.set(el.id, el); for (const m of srcToMid[qid] || []) for (const el of byMid[m] || []) els.set(el.id, el); }
      if (mid) for (const el of byMid[mid] || []) els.set(el.id, el);
      return [...els.values()].map(el => `${el.id} "${el.title || '(untitled)'}"`).join(', ') || '(no live tile — orphan/query-only)';
    }
    function report(kind, where, ownersStr, detail) { total++; worklist.push(`  [${dash}] ${kind} ${where} -> tiles: ${ownersStr}${detail ? `\n        ${detail}` : ''}`); }

    for (const f of est.filters || []) {
      if (hits(`${f.name} ${f.field || f.dimension || ''} ${f.default_value || ''}`)) report('dashboard-filter', `"${f.name}" default "${f.default_value}"`, '(board-level)');
    }
    for (const el of est.elements || []) {
      if (hits(`${el.title || ''} ${el.title_text || ''} ${el.subtitle_text || ''} ${el.body_text || ''}`)) report('tile-title/text', `element ${el.id}`, `${el.id} "${el.title || el.title_text || '(text)'}"`);
      // LISTEN mappings: renaming a dashboard filter or a listened field breaks these silently
      for (const fb of el.listen || []) for (const l of fb.listen || []) {
        if (hits(`${l.dashboard_filter_name || ''} ${l.field || ''}`)) report('listen', `element ${el.id} view ${fb.view} filter "${l.dashboard_filter_name}" -> ${l.field}`, `${el.id} "${el.title || ''}"`);
      }
    }
    function scanQuery(qid, q, label) {
      for (const df of dfList(q)) {
        const nm = df.dimension || df.measure || df.table_calculation || '?';
        if (hits(`${df.label || ''} ${df.expression || ''} ${nm} ${df.based_on || ''}`)) report(label + 'expression', `query ${qid.slice(0, 8)}… field "${df.label || nm}"`, owners(qid, null));
        if (hits(JSON.stringify(df.filters || {})) || hits(df.filter_expression || '')) report(label + 'filtered-measure', `query ${qid.slice(0, 8)}… measure "${df.label || nm}" filters ${JSON.stringify(df.filters || {})}${df.filter_expression ? ' fexpr ' + df.filter_expression : ''}`, owners(qid, null));
      }
      if (hits(JSON.stringify(q.filters || {})) || hits(q.filter_expression || '')) report(label + 'baked-filter', `query ${qid.slice(0, 8)}… filters ${JSON.stringify(q.filters)}${q.filter_expression ? ' fexpr ' + q.filter_expression : ''}`, owners(qid, null));
      if (hits(JSON.stringify(q.filter_config || {}))) report(label + 'filter-chip', `query ${qid.slice(0, 8)}… filter_config (the UI chip text — must move in lockstep with filters)`, owners(qid, null));
      if (hits(JSON.stringify(q.fields || []))) report(label + 'field-ref', `query ${qid.slice(0, 8)}… fields`, owners(qid, null));
      if (hits(JSON.stringify(q.sorts || []))) report(label + 'sort', `query ${qid.slice(0, 8)}… sorts ${JSON.stringify(q.sorts)}`, owners(qid, null));
      if (hits(JSON.stringify(q.pivots || []))) report(label + 'pivot', `query ${qid.slice(0, 8)}… pivots ${JSON.stringify(q.pivots)}`, owners(qid, null));
    }
    for (const [qid, q] of Object.entries(est.queries || {})) scanQuery(qid, q, '');
    for (const [mid, m] of Object.entries(est.merges || {})) {
      for (const df of dfList(m)) {
        const nm = df.table_calculation || df.dimension || '?';
        if (hits(`${df.label || ''} ${df.expression || ''} ${nm}`)) report('merge-calc', `merge ${mid.slice(0, 8)}… calc "${df.label || nm}"`, owners(null, mid));
        if (hits(JSON.stringify(df.filters || {})) || hits(df.filter_expression || '')) report('merge-filtered-measure', `merge ${mid.slice(0, 8)}… measure "${df.label || nm}" filters ${JSON.stringify(df.filters || {})}`, owners(null, mid));
      }
      for (const sq of m.source_queries || []) if (hits(JSON.stringify(sq.merge_fields || []))) report('merge-fields', `merge ${mid.slice(0, 8)}… source "${sq.name || sq.query_id.slice(0, 8)}" merge_fields ${JSON.stringify(sq.merge_fields)}`, owners(null, mid));
      if (hits(JSON.stringify(m.sorts || []))) report('merge-sort', `merge ${mid.slice(0, 8)}… sorts ${JSON.stringify(m.sorts)}`, owners(null, mid));
    }
    for (const lk of looks) {
      const q = lk.query || lk;
      if (hits(lk.title || '')) report('look-title', `Look ${lk.id} "${lk.title || ''}"`, `(Look ${lk.id})`);
      scanQuery(String(lk.id), q, `look-${lk.id}-`);
    }
  }
  return { worklist, total };
}

function scanDocs(re, targets) {
  const hits = (text) => { const m = text.match(re); return m ? m.length : 0; };
  const out = [];
  for (const f of targets) {
    const p = path.join(EST_DIR, f);
    if (!fs.existsSync(p)) continue;
    const lines = fs.readFileSync(p, 'utf8').split('\n');
    const ln = [];
    lines.forEach((l, i) => { if (hits(l)) ln.push(i + 1); });
    if (ln.length) out.push(`  ${f}: ${ln.length} line(s) — ${ln.slice(0, 12).join(', ')}${ln.length > 12 ? ', …' : ''}`);
  }
  return out;
}

// ---------- raw JSON walk for --verify: classify every string hit by its path ----------
function rawWalk(re) {
  const tally = { structured: {}, cache: {}, unexplained: {} };
  function cls(p) {
    if (/\.vis_config\b/.test(p)) return 'cache';
    if (/\.(dynamic_fields|filters|filter_expression|filter_config|fields|sorts|pivots|merge_fields|listen|title|title_text|subtitle_text|body_text|name|field|dimension|default_value)\b/.test(p)) return 'structured';
    return 'unexplained';
  }
  function walk(o, p, cb) {
    if (typeof o === 'string') { cb(p, o); return; }
    if (Array.isArray(o)) { o.forEach((v, i) => walk(v, p + '[' + i + ']', cb)); return; }
    if (o && typeof o === 'object') for (const k of Object.keys(o)) walk(o[k], p + '.' + k, cb);
  }
  for (const [dash, file] of Object.entries(ESTATES)) {
    const doc = JSON.parse(fs.readFileSync(path.join(EST_DIR, file), 'utf8'));
    walk(doc, dash, (p, s) => {
      if (!s.match(re)) return;
      const key = p.replace(/\.queries\.[^.\[]+/, '.queries.<qid>').replace(/\.merges\.[^.\[]+/, '.merges.<mid>').replace(/\[\d+\]/g, '[]');
      const c = cls(key); tally[c][key] = (tally[c][key] || 0) + 1;
    });
  }
  return tally;
}

// ---------- stamp parsing ----------
function readStamp(file) {
  const p = path.join(EST_DIR, file);
  if (!fs.existsSync(p)) return null;
  const head = fs.readFileSync(p, 'utf8').slice(0, 6000);
  const all = [...head.matchAll(/Last (?:synced|updated|full audit)[:*\s]*[* (]*(\d{4}-\d{2}-\d{2})(?:\s*×(\d+))?/gi)].map(m => ({ date: m[1], n: m[2] ? +m[2] : 1, idx: m.index }));
  if (!all.length) return { date: null, n: 0, entry: '' };
  const latest = all.slice().sort((a, b) => a.date < b.date ? 1 : a.date > b.date ? -1 : b.n - a.n)[0];
  const tail = head.slice(latest.idx);
  const cut = tail.search(/\bPrior\b/); const entry = cut > 0 ? tail.slice(0, cut) : tail.slice(0, 1500);
  return { date: latest.date, n: latest.n, entry };
}
const norm = (s) => String(s || '').replace(/\s+/g, ' ').replace(/[’‘]/g, "'").trim().toLowerCase();

// ================= --stale =================
// `harvested_at` is UTC (`new Date().toISOString()` from the browser); doc stamps are written in
// Adam's LOCAL date. Slicing the ISO string compares the two in different timezones, so an evening
// harvest (after 20:00 ET = 00:00Z next day) reported every correctly-stamped doc as stale.
// Convert to the local calendar day before comparing. (Fixed 2026-09-04 after a 20:41 ET build.)
function localDay(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (isNaN(d)) return String(iso).slice(0, 10);
  const p = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

if (ARGS[0] === '--stale') {
  console.log('== BI doc-freshness check ==\n');
  let latestHarvest = null; const boardDay = {};
  for (const [dash, file] of Object.entries(ESTATES)) {
    const { est } = loadEstate(file);
    const h = est.harvested_at || '(unknown)';
    if (!latestHarvest || h > latestHarvest) latestHarvest = h;
    boardDay[dash] = localDay(est.harvested_at);
    console.log(`harvest  ${dash}: ${h}`);
  }
  const harvestDay = localDay(latestHarvest);
  console.log(`\nlatest harvest day: ${harvestDay}\n`);
  const docs = [...guideFiles(), ...CROSS_DOCS];
  let stale = 0; const stamps = {};
  for (const f of docs) {
    const st = readStamp(f); if (!st) continue; stamps[f] = st;
    const m = f.match(/^dashboard-(\d+)/);
    const against = m && boardDay[m[1]] ? boardDay[m[1]] : harvestDay;
    const flag = !st.date ? '?? no stamp found' : (st.date < against ? '** STALE **' : 'ok');
    if (flag !== 'ok') stale++;
    console.log(`${(flag + '        ').slice(0, 12)} ${f}  (stamp ${st.date ? st.date + (st.n > 1 ? ' ×' + st.n : '') : 'n/a'})`);
  }
  // RENDER FRESHNESS (8/30): a .md edited after its .docx/.pdf means the shareable copies are behind
  console.log('');
  let rstale = 0;
  // Renders moved to EST_DIR/renders/ on 2026-09-08 (P6). Both locations are checked: a render that
  // has not been regenerated since the move still sits beside its source, and silently skipping it
  // would report "All renders current" for a deliverable nobody has rebuilt.
  const RENDER_DIRS = [path.join(EST_DIR, 'renders'), EST_DIR].filter(d => fs.existsSync(d));
  const renderPath = (base, ext) => {
    for (const d of RENDER_DIRS) { const p = path.join(d, base + ext); if (fs.existsSync(p)) return p; }
    return path.join(RENDER_DIRS[0], base + ext);
  };
  for (const f of fs.readdirSync(EST_DIR).filter(x => x.endsWith('.md'))) {
    const base = f.slice(0, -3);
    const pdf = renderPath(base, '.pdf'), docx = renderPath(base, '.docx');
    if (!fs.existsSync(pdf) && !fs.existsSync(docx)) continue;
    const mt = fs.statSync(path.join(EST_DIR, f)).mtimeMs;
    const behind = [];
    if (fs.existsSync(pdf) && fs.statSync(pdf).mtimeMs < mt) behind.push('pdf');
    if (fs.existsSync(docx) && fs.statSync(docx).mtimeMs < mt) behind.push('docx');
    if (behind.length) { rstale++; console.log(`** RENDER BEHIND ** ${base} (${behind.join(' + ')}) — re-run pandoc-deliverable`); }
  }
  console.log(rstale ? `${rstale} deliverable(s) need re-rendering.` : 'All renders current.');

  // DICTIONARY-AHEAD (9/2): a rule changed in the Dictionary whose operator docs still sit on an older stamp
  console.log('\n== Dictionary vs operator docs ==');
  let ahead = 0;
  const dd = stamps['DATA-DICTIONARY.md'];
  if (dd && dd.date) {
    const ops = ['BI-SOP.md', 'BI-WI.md', ...guideFiles()].map(f => stamps[f]).filter(Boolean);
    const maxOp = ops.map(s => s.date || '').sort().slice(-1)[0] || '';
    if (dd.date > maxOp) { ahead++; console.log(`** DICTIONARY AHEAD ** DATA-DICTIONARY.md stamped ${dd.date}, newest operator doc ${maxOp} — a rule change has not rippled (runbook Steps 2–6).`); }
    else console.log(`ok         dictionary ${dd.date} vs newest operator doc ${maxOp}`);
    const rules = [...new Set([...dd.entry.matchAll(/\bR(\d{1,3})\b/g)].map(m => 'R' + m[1]))];
    if (rules.length) {
      const sop = stamps['BI-SOP.md'] || { entry: '' }, wi = stamps['BI-WI.md'] || { entry: '' };
      const sopBody = fs.readFileSync(path.join(EST_DIR, 'BI-SOP.md'), 'utf8');
      for (const r of rules) {
        const inSopStamp = new RegExp('\\b' + r + '\\b').test(sop.entry), inWiStamp = new RegExp('\\b' + r + '\\b').test(wi.entry), inSopBody = new RegExp('\\b' + r + '\\b').test(sopBody);
        console.log(`info       dictionary's latest entry names ${r}: SOP stamp ${inSopStamp ? 'mentions it' : 'silent'}, WI stamp ${inWiStamp ? 'mentions it' : 'silent'}, SOP body ${inSopBody ? 'cites it' : 'never cites it'}${(!inSopStamp && !inSopBody) ? '  <- verify the ripple, or confirm the rule has no BI surface' : ''}`);
      }
    }
  }

  // CONTENT CHECKS (9/2): for every board with an SOP section, every live tile title and every
  // dashboard filter must appear in the SOP, the WI and the guide. Stamps cannot see this class
  // (on 9/2 three documents stamped "current" described one filter where the board had two, and
  // the WI tiles table lacked a tile that had been live for a day).
  console.log('\n== Content checks (promoted boards) ==');
  let content = 0;
  const sopText = fs.readFileSync(path.join(EST_DIR, 'BI-SOP.md'), 'utf8');
  const wiText = fs.existsSync(path.join(EST_DIR, 'BI-WI.md')) ? fs.readFileSync(path.join(EST_DIR, 'BI-WI.md'), 'utf8') : '';
  const promoted = [...sopText.matchAll(/^## \d+ · Dashboard SOP — .*\((\d+)\)/gm)].map(m => m[1]);
  if (!promoted.length) console.log('  (no promoted boards found in BI-SOP.md)');
  for (const dash of promoted) {
    const file = ESTATES[dash]; if (!file) { console.log(`  ?? board ${dash} has an SOP section but no estate file`); continue; }
    const { est } = loadEstate(file);
    const guide = guideFiles().find(g => g.startsWith('dashboard-' + dash));
    const guideText = guide ? fs.readFileSync(path.join(EST_DIR, guide), 'utf8') : '';
    const surfaces = [['BI-SOP.md', norm(sopText)], ['BI-WI.md', norm(wiText)], [guide || '(no guide)', norm(guideText)]];
    const tiles = (est.elements || []).filter(e => e.type === 'vis' || e.merge_result_id || e.query_id);
    let missing = 0;
    for (const t of tiles) {
      const title = norm(t.title); if (!title) continue;
      for (const [name, text] of surfaces) if (!text.includes(title)) { missing++; content++; console.log(`** CONTENT ** [${dash}] tile ${t.id} "${t.title}" not found in ${name}`); }
    }
    for (const f of est.filters || []) {
      const nm = norm(f.name);
      for (const [name, text] of surfaces) if (!text.includes(nm)) { missing++; content++; console.log(`** CONTENT ** [${dash}] dashboard filter "${f.name}" not found in ${name}`); }
    }
    if (!missing) console.log(`ok         [${dash}] all ${tiles.length} live tile titles and ${(est.filters || []).length} dashboard filters appear in SOP, WI and guide`);
  }

  const problems = stale + rstale + ahead + content;
  console.log(problems ? `\n${stale} stale stamp(s), ${rstale} render(s) behind, ${ahead} dictionary-ahead, ${content} content gap(s) — run the runbook (BI-SOP.md §2).` : '\nAll documents current, renders current, dictionary in step, content matches the live tiles and filters.');
  process.exit(problems ? 1 : 0);
}

// ================= --verify =================
if (ARGS[0] === '--verify') {
  const raw = ARGS[1];
  if (!raw) { console.log('usage: node bi_impact_scan.js --verify "<needle>"'); process.exit(1); }
  const re = makeRe(raw);
  const { worklist, total } = scanEstates(re);
  const tally = rawWalk(re);
  const sum = (o) => Object.values(o).reduce((a, b) => a + b, 0);
  console.log(`== bi_impact_scan --verify: ${raw} ==\n`);
  console.log(`-- Structured surfaces (must be 0 after a ripple) — ${total} hit(s) --`);
  console.log(worklist.length ? worklist.join('\n') : '  (none)');
  console.log(`\n-- Raw-snapshot self-check --`);
  console.log(`  vis_config cache hits (IGNORED — Looker keeps retired strings here forever): ${sum(tally.cache)}`);
  for (const [k, v] of Object.entries(tally.cache)) console.log(`      ${v}  ${k}`);
  console.log(`  structured-surface raw hits (should agree with the walk above): ${sum(tally.structured)}`);
  const unexpl = Object.entries(tally.unexplained);
  console.log(`  UNEXPLAINED raw hits (a surface the scanner does not walk — extend the scanner): ${sum(tally.unexplained)}`);
  for (const [k, v] of unexpl) console.log(`      ${v}  ${k}`);
  const clean = total === 0 && unexpl.length === 0;
  console.log(clean ? `\nCLEAN — no live surface carries "${raw}".` : `\nNOT CLEAN — ${total} structured hit(s), ${unexpl.length} unexplained path class(es).`);
  process.exit(clean ? 0 : 1);
}

// ================= needle mode =================
const raw = ARGS[0];
if (!raw) { console.log('usage: node bi_impact_scan.js "<needle>" | "/regex/[i]" | --verify "<needle>" | --stale'); process.exit(1); }
const re = makeRe(raw);
const { worklist, total } = scanEstates(re);
const docTargets = [...CROSS_DOCS, ...guideFiles()];
const inv = latestInventory(); if (inv) docTargets.push(inv);
const docHits = scanDocs(re, docTargets);
console.log(`== bi_impact_scan: ${raw} ==\n`);
console.log(`-- BI estate (Step 3 worklist: tiles/queries to edit) — ${total} hit(s) --`);
console.log(worklist.length ? worklist.join('\n') : '  (none)');
console.log(`\n-- Documents (Step 5 sync list) — ${docHits.length} file(s) --`);
console.log(docHits.length ? docHits.join('\n') : '  (none)');
console.log('\nRunbook: BI-SOP.md §2 (dictionary first, scan old + new strings, peer read on generalizations, verify-before-bind, re-harvest + --verify, sync + stamp the docs, count invariance).');
