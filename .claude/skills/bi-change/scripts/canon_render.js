#!/usr/bin/env node
// canon_render.js — HELD until the canon flip. Renders the tenant's two canon documents from the warehouse
// (canon.render_document) to <estate>/DATA-DICTIONARY.md and <estate>/DECISIONS.md, and prints the sha256 of
// each. `--check` writes nothing: it compares the two files on disk with the database render and exits 1 on
// ANY difference (a hand edit after the flip; plan step F7: it runs before kickoff_check.js in every build).
//
//   node canon_render.js --estate <dir> --org-code <code> --url-env <ENV VAR NAME> [--check]
//   node canon_render.js --estate <dir> --render-from <render.json> [--check]
//   node canon_render.js --org-code <code> --emit-sql            (print the read SQL; send nothing)
//
// --url-env      the NAME of the environment variable that holds the login (never a literal URL). A read-only
//                login is enough: render_document runs as the caller, under row-level security.
// --render-from  a saved render: the JSON the read SQL returns ([{doc_key, file_name, sha256, render}]). For a
//                render taken through another channel (a database tool) and for the self-test.
// --emit-sql     print the read SQL. It returns JSON whose text values carry every CR and LF escaped, so psql
//                cannot change a line ending inside a document.
//
// Every render is checked before it is used: the sha256 the database computed must equal the sha256 of the text
// that arrived, so a byte lost in transit (a code page, a line ending) is refused, never written. It writes ONLY
// the two document names (no dated file, no other path), each through a temp file and a rename.
//
// Exit 0 = written, or --check found no difference. 1 = --check found a difference (or psql failed).
// 2 = refused (usage, a bad render, a transport loss); nothing written.
'use strict';
const fs = require('fs');
const path = require('path');
const C = require('./canon_common.js');
const { refuse, lit } = C;

const FILES = { 'data-dictionary': 'DATA-DICTIONARY.md', decisions: 'DECISIONS.md' };
const FLAGS = { estate: 'value', 'org-code': 'value', 'url-env': 'value', 'render-from': 'value', check: 'bool',
  'emit-sql': 'bool', url: 'value' };

function readSql(orgCode) {
  return `-- canon_render.js read for ${orgCode}: both documents, rendered by canon.render_document, as JSON (line breaks escaped).
select coalesce(json_agg(json_build_object('doc_key', d.doc_key, 'file_name', d.file_name,
         'sha256', encode(sha256(convert_to(x.t, 'UTF8')), 'hex'), 'render', x.t) order by d.doc_key), '[]'::json)
  from canon.documents d
 cross join lateral (select canon.render_document(d.org_id, d.doc_key) as t) x
 where d.org_id = (select org_id from security.organizations where org_code = ${lit(orgCode)});
`;
}

// The renders, checked: exactly the two documents, the known file names, and every text = its database sha256.
function checkRenders(list) {
  if (!Array.isArray(list)) refuse('the render is not a JSON array of documents');
  const seen = {};
  for (const d of list) {
    if (!d || !(d.doc_key in FILES)) refuse('unknown document in the render: ' + JSON.stringify(d && d.doc_key));
    if (seen[d.doc_key]) refuse('the render holds ' + d.doc_key + ' twice');
    if (d.file_name !== FILES[d.doc_key]) refuse(`${d.doc_key} renders to ${JSON.stringify(d.file_name)}; this script writes only ${FILES[d.doc_key]}`);
    if (typeof d.render !== 'string' || !d.render) refuse(d.doc_key + ' rendered empty (no head section, or this login cannot see the org)');
    const got = C.sha256(d.render);
    if (got !== d.sha256) refuse(`${d.file_name}: the text that arrived hashes ${got}, the database computed ${d.sha256} (a byte was lost in transit; nothing written)`);
    seen[d.doc_key] = d;
  }
  for (const k of Object.keys(FILES)) if (!seen[k]) refuse('the render lacks ' + k + ' (is the org loaded? can this login see it?)');
  return Object.keys(FILES).map(k => seen[k]);
}

// The first byte where two buffers differ, as a line and column of `a`, with a short excerpt of each line.
function firstDifference(a, b) {
  const n = Math.min(a.length, b.length);
  let i = 0;
  while (i < n && a[i] === b[i]) i++;
  if (i === n && a.length === b.length) return null;
  const lineStart = buf => { let s = i; while (s > 0 && buf[s - 1] !== 0x0a) s--; return s; };
  const lineOf = buf => { const s = lineStart(buf); let e = s; while (e < buf.length && buf[e] !== 0x0a) e++; return buf.slice(s, e).toString('utf8'); };
  let line = 1;
  for (let k = 0; k < i; k++) if (a[k] === 0x0a) line++;
  const cut = s => (s.length > 120 ? s.slice(0, 120) + '…' : s).replace(/\r/g, '\\r');
  return { offset: i, line, column: i - lineStart(a) + 1, file: cut(lineOf(a)), render: cut(lineOf(b)) };
}
// file bytes (or null when missing) vs render text → { equal, why }
function compareDoc(fileBuf, renderText) {
  const r = Buffer.from(renderText, 'utf8');
  if (fileBuf === null) return { equal: false, why: 'the file is missing' };
  const d = firstDifference(fileBuf, r);
  if (!d) return { equal: true };
  const lf = b => b.toString('utf8').replace(/\r\n/g, '\n');
  const eol = lf(fileBuf) === lf(r) ? ' — LINE ENDINGS ONLY (the render is the line-ending contract)' : '';
  return { equal: false, why: `first difference at byte ${d.offset}, line ${d.line}, column ${d.column}${eol}; file: "${d.file}" | render: "${d.render}"` };
}

function main(argv) {
  const a = C.parseArgs(argv, FLAGS);
  if (a.url !== undefined) refuse('--url is not accepted: pass --url-env <ENV VAR NAME>');
  if (a._.length) refuse('unexpected argument ' + a._[0]);
  if (a['org-code'] !== undefined && !/^[A-Za-z0-9_-]+$/.test(a['org-code'])) refuse('--org-code: letters, digits, _ and -');
  if (a['emit-sql']) {
    if (!a['org-code']) refuse('--emit-sql needs --org-code');
    process.stdout.write(readSql(a['org-code']));
    return 0;
  }
  if (!a.estate) refuse('--estate <dir> is required');
  if (!fs.existsSync(a.estate) || !fs.statSync(a.estate).isDirectory()) refuse('--estate ' + a.estate + ' is not a directory');
  let list;
  if (a['render-from']) {
    if (a['url-env']) refuse('give --render-from or --url-env, not both');
    try { list = JSON.parse(fs.readFileSync(a['render-from'], 'utf8').replace(/^﻿/, '')); }
    catch (e) { refuse('--render-from ' + a['render-from'] + ': ' + e.message); }
  } else {
    if (!a['org-code']) refuse('--org-code is required to read the database');
    const out = C.psql(readSql(a['org-code']), C.connection(a['url-env']), { oneTxn: false, capture: true });
    try { list = JSON.parse(out.trim()); } catch (e) { refuse('psql did not return the render JSON: ' + e.message); }
  }
  const docs = checkRenders(list);

  if (a.check) {
    let bad = 0;
    for (const d of docs) {
      const p = path.join(a.estate, d.file_name);
      const c = compareDoc(fs.existsSync(p) ? fs.readFileSync(p) : null, d.render);
      if (c.equal) console.log(`✔ ${d.file_name} = the database render (sha256 ${d.sha256})`);
      else { bad++; console.log(`✘ ${d.file_name} differs from the database render (sha256 ${d.sha256}): ${c.why}`); }
    }
    console.log(bad ? `canon --check: ${bad} of 2 documents differ. Re-render to discard a hand edit, or make the edit a canon_write.js call.`
      : 'canon --check: 0 differences.');
    return bad ? 1 : 0;
  }
  for (const d of docs) {
    const p = path.join(a.estate, d.file_name);
    const tmp = p + '.canon-render.tmp';
    fs.writeFileSync(tmp, Buffer.from(d.render, 'utf8'));
    fs.renameSync(tmp, p);
    const back = C.sha256(fs.readFileSync(p));
    if (back !== d.sha256) { console.error(`✘ ${d.file_name}: read back ${back} <> render ${d.sha256}`); return 1; }
    console.log(`wrote ${d.file_name} sha256 ${d.sha256} (${Buffer.byteLength(d.render, 'utf8')} bytes)`);
  }
  return 0;
}

if (require.main === module) C.runMain(() => main(process.argv.slice(2)));
module.exports = { readSql, checkRenders, firstDifference, compareDoc, FILES };
