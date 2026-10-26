#!/usr/bin/env node
// canon_write.js — HELD until the canon flip. ONE canon write per run, through the warehouse writer
// procedures (schema `canon`), in ONE transaction. After the flip this is the only canon write path: the
// Dictionary and DECISIONS files are renders (canon_render.js), never edited by hand.
//
//   node canon_write.js <kind> --org-code <code> --kickoff <basename> --changed-on YYYY-MM-DD
//                       [--spec <file.json>] [field flags] [--stamp "<text>"]
//                       (--emit-sql [--out <file>] | --url-env <ENV VAR NAME> --send)
//
// kinds (each is one procedure call; a rule change carries its DECISIONS row in the SAME call):
//   mint     canon.mint_rule        --rule Rn --after Rm --rule-text --grain --surface --status --since --links
//                                   --record + the decision
//   amend    canon.amend_rule_text  --rule Rn --expected-version N --rule-text [--since] + the decision
//   status   canon.set_rule_status  --rule Rn --expected-version N --status + the decision
//   impl     canon.set_rule_impl    --rule Rn --expected-version N [--surface] [--links] [--record]
//                                   (an omitted cell keeps its current value; impl cannot move the rule text)
//   decision canon.record_decision  --rule-cell <R / DD / SOP keys> --ruling --decision-record [--decided-on]
//   section  canon.set_section      --doc data-dictionary|decisions --section head|tail --expected-version N
//                                   --body-file <file> (the prose around a table, verbatim bytes)
//
// The decision (mint, amend, status): --ruling, --decision-record (must name the kickoff: the D1 test),
//   --decided-on (default --changed-on), --rule-cell (default the rule key; it must name the rule).
// --spec       a JSON file with the same fields in snake_case ({"rule": "R9", "rule_text": "...",
//              "decision": {"ruling": "...", "record": "..."}}). A flag overrides the spec. Use a spec for any
//              cell with quotes or pipes: no shell quoting rules apply to a file.
// --stamp      (F4 form; OFF unless given) also rewrite the Dictionary stamp line `Last updated: **X** — text` in
//              the head, through canon.set_section('head'), in the same transaction. Same-day stamps count up
//              (X, X ×2, X ×3). Refused while the stamp line still carries a `Prior:` chain (pre-F4 header).
// --emit-sql   print the SQL (one DO block) and send nothing: the dry run. --out writes it to a file instead.
// --send       run it with psql -1. The login comes from the environment variable NAMED by --url-env (never a
//              literal URL). The login must be a person in wh_canon_writer; an _agent / _analyst / _ingest /
//              _surface login is refused here and again in the database.
// --changed-on is the operator's LOCAL date, never the server clock. Default: this machine's local date.
//
// Exit 0 = emitted, or written and committed. 1 = psql failed (nothing committed). 2 = refused (nothing sent).
'use strict';
const fs = require('fs');
const path = require('path');
const C = require('./canon_common.js');
const { refuse, lit } = C;

const KINDS = ['mint', 'amend', 'status', 'impl', 'decision', 'section'];
const FLAGS = {
  'org-code': 'value', kickoff: 'value', 'changed-on': 'value', spec: 'value', rule: 'value', after: 'value',
  'rule-text': 'value', grain: 'value', surface: 'value', status: 'value', since: 'value', links: 'value',
  record: 'value', 'expected-version': 'value', ruling: 'value', 'decision-record': 'value', 'decided-on': 'value',
  'rule-cell': 'value', doc: 'value', section: 'value', 'body-file': 'value', stamp: 'value',
  'emit-sql': 'bool', out: 'value', 'url-env': 'value', send: 'bool', url: 'value',
};

// spec (snake_case) + flags (kebab-case) → one request object; a flag wins.
function request(argv) {
  const a = C.parseArgs(argv, FLAGS);
  if (a.url !== undefined) refuse('--url is not accepted: pass --url-env <ENV VAR NAME>; a connection string never goes on a command line');
  const kind = a._[0];
  if (!KINDS.includes(kind)) refuse('first argument must be one of ' + KINDS.join(' | ') + (kind ? ', got ' + kind : ''));
  if (a._.length > 1) refuse('unexpected argument ' + a._[1]);
  let spec = {};
  if (a.spec) {
    try { spec = JSON.parse(fs.readFileSync(a.spec, 'utf8').replace(/^﻿/, '')); }
    catch (e) { refuse('--spec ' + a.spec + ': ' + e.message); }
  }
  const dec = spec.decision || {};
  const pick = (flag, key, from = spec) => (a[flag] !== undefined ? a[flag] : from[key]);
  const r = {
    kind,
    org_code: pick('org-code', 'org_code'), kickoff: pick('kickoff', 'kickoff'), changed_on: pick('changed-on', 'changed_on'),
    rule: pick('rule', 'rule'), after: pick('after', 'after'), rule_text: pick('rule-text', 'rule_text'),
    grain: pick('grain', 'grain'), surface: pick('surface', 'surface'), status: pick('status', 'status'),
    since: pick('since', 'since'), links: pick('links', 'links'), record: pick('record', 'record'),
    expected_version: pick('expected-version', 'expected_version'),
    doc: pick('doc', 'doc'), section: pick('section', 'section'), body_file: pick('body-file', 'body_file'),
    stamp: pick('stamp', 'stamp'),
    decision: { ruling: pick('ruling', 'ruling', dec), record: pick('decision-record', 'record', dec),
      decided_on: pick('decided-on', 'decided_on', dec), rule_cell: pick('rule-cell', 'rule_cell', dec) },
    emit: !!a['emit-sql'], out: a.out, send: !!a.send, url_env: a['url-env'],
  };
  if (r.emit === r.send) refuse('give exactly one of --emit-sql (dry run) or --send');
  if (r.out && !r.emit) refuse('--out goes with --emit-sql');
  return r;
}

function validate(r) {
  if (!r.org_code || !/^[A-Za-z0-9_-]+$/.test(r.org_code)) refuse('--org-code is required (letters, digits, _ and -)');
  r.changed_on = C.isoDate(r.changed_on || C.localDate(), '--changed-on');
  if (r.kickoff) r.kickoff = path.basename(String(r.kickoff));
  if (!r.kickoff && r.kind !== 'decision') refuse('--kickoff <basename> is required: every version names the kickoff that carried it');
  const needRule = () => { if (!/^R\d+$/.test(r.rule || '')) refuse('--rule must be R<n>, got ' + JSON.stringify(r.rule)); };
  const needVersion = () => {
    if (!/^[1-9]\d*$/.test(String(r.expected_version || '')))
      refuse('--expected-version N is required: the version you read (canon.v_rules); it is the optimistic lock');
    r.expected_version = Number(r.expected_version);
  };
  const needStatus = () => { if (!C.STATUSES.includes(r.status)) refuse('--status must be ' + C.STATUSES.join(' / ') + ', got ' + JSON.stringify(r.status)); };
  const ruleText = () => {
    C.checkCell(r.rule_text, 'the rule cell (--rule-text)');
    if (r.rule_text.length > C.RULE_CAP) refuse(`the rule cell is ${r.rule_text.length} chars; the cap is ${C.RULE_CAP} (gate C1)`);
    r.rule_sha1 = C.sha1(r.rule_text);
  };
  const decision = (ruleKey) => {
    const d = r.decision;
    d.decided_on = C.isoDate(d.decided_on || r.changed_on, 'the decision date (--decided-on)');
    d.rule_cell = C.checkCell(d.rule_cell || ruleKey, 'the decision rule cell (--rule-cell)');
    C.checkCell(d.ruling, 'the ruling (--ruling)', { allowPipe: true });
    if (!C.decisionShapeOk(d.ruling)) refuse('the ruling (--ruling) holds an unescaped pipe: the warehouse would store the row with shape_ok = false (escape it as \\|)');
    C.checkCell(d.record, 'the decision record (--decision-record)');
    if (ruleKey && !C.decisionKeys(d.rule_cell).includes(ruleKey)) refuse(`the decision rule cell ${JSON.stringify(d.rule_cell)} does not name ${ruleKey}`);
    if (r.kickoff && !d.record.includes(r.kickoff)) refuse(`the decision record must name the kickoff ${r.kickoff} (the D1 test)`);
  };
  switch (r.kind) {
    case 'mint':
      needRule();
      if (!/^R\d+$/.test(r.after || '')) refuse('--after must be the R<n> the new rule follows, got ' + JSON.stringify(r.after));
      ruleText(); needStatus();
      r.since = C.isoDate(r.since || r.changed_on, '--since');
      for (const k of ['grain', 'surface', 'links', 'record']) C.checkCell(r[k], '--' + k, { allowEmpty: true });
      decision(r.rule); break;
    case 'amend':
      needRule(); needVersion(); ruleText();
      if (r.since) C.isoDate(r.since, '--since');
      decision(r.rule); break;
    case 'status':
      needRule(); needVersion(); needStatus(); decision(r.rule); break;
    case 'impl':
      needRule(); needVersion();
      if ([r.surface, r.links, r.record].every(v => v === undefined)) refuse('impl needs at least one of --surface, --links, --record');
      for (const k of ['surface', 'links', 'record']) if (r[k] !== undefined) C.checkCell(r[k], '--' + k, { allowEmpty: true });
      if (r.rule_text !== undefined) refuse('impl cannot change the rule text (use amend, which carries a ruling)');
      break;
    case 'decision':
      if (!r.decision.rule_cell) refuse('decision needs --rule-cell (R / DD / SOP keys)');
      decision(null); break;
    case 'section':
      if (!['data-dictionary', 'decisions'].includes(r.doc)) refuse('--doc must be data-dictionary or decisions');
      if (!['head', 'tail'].includes(r.section)) refuse('--section must be head or tail');
      needVersion();
      if (!r.body_file) refuse('--body-file <file> is required (the section bytes, verbatim)');
      try {
        const raw = fs.readFileSync(r.body_file);
        r.body = raw.toString('utf8');
        if (Buffer.from(r.body, 'utf8').compare(raw) !== 0) refuse('--body-file is not valid UTF-8');
        if (r.body.charCodeAt(0) === 0xFEFF) refuse('--body-file starts with a BOM');
      } catch (e) { if (e instanceof C.Refusal) throw e; refuse('--body-file ' + r.body_file + ': ' + e.message); }
      break;
  }
  if (r.stamp !== undefined) {
    C.checkCell(r.stamp, 'the stamp text (--stamp)', { allowPipe: true });
    if (r.kind === 'section' && r.doc === 'data-dictionary' && r.section === 'head')
      refuse('--stamp with `section --doc data-dictionary --section head` would write the head twice; put the stamp in the body');
  }
  return r;
}

// The procedure call, as plpgsql inside the DO block. v_org is resolved first; v_ver receives the version.
function callOf(r) {
  const dj = d => lit(JSON.stringify({ decided_on: d.decided_on, rule_cell: d.rule_cell, ruling: d.ruling, record: d.record })) + '::jsonb';
  const D = s => lit(s) + '::date';
  switch (r.kind) {
    case 'mint':
      return `call canon.mint_rule(v_org, ${lit(r.rule)}, ${lit(r.after)}, ${lit(r.rule_text)}, ${lit(r.grain)}, ${lit(r.surface)},
    ${lit(r.status)}, ${D(r.since)}, ${lit(r.links)}, ${lit(r.record)}, ${lit(r.rule_sha1)}, ${lit(r.kickoff)}, ${D(r.changed_on)},
    ${dj(r.decision)}, v_ver);`;
    case 'amend':
      // no --since: pass the current Since, so the procedure's "unchanged" refusal still sees an unchanged text
      // (a CALL argument cannot hold a subquery, so it is read into v_since first)
      return `${r.since ? `v_since := ${D(r.since)};` : `select since into v_since from canon.rules where org_id = v_org and rule_key = ${lit(r.rule)};`}
  call canon.amend_rule_text(v_org, ${lit(r.rule)}, ${r.expected_version}, ${lit(r.rule_text)}, v_since,
    ${lit(r.rule_sha1)}, ${lit(r.kickoff)}, ${D(r.changed_on)}, ${dj(r.decision)}, v_ver);`;
    case 'status':
      return `call canon.set_rule_status(v_org, ${lit(r.rule)}, ${r.expected_version}, ${lit(r.status)}, ${lit(r.kickoff)}, ${D(r.changed_on)},
    ${dj(r.decision)}, v_ver);`;
    case 'impl': {
      // an omitted cell keeps the current value, read under the same lock the procedure takes
      const cell = k => (r[k] !== undefined ? lit(r[k]) : 'v_cur.' + k);
      return `select surface, links, record into v_cur from canon.rules where org_id = v_org and rule_key = ${lit(r.rule)};
  call canon.set_rule_impl(v_org, ${lit(r.rule)}, ${r.expected_version}, ${cell('surface')}, ${cell('links')}, ${cell('record')},
    ${lit(r.kickoff)}, ${D(r.changed_on)}, v_ver);`;
    }
    case 'decision':
      return `call canon.record_decision(v_org, ${D(r.decision.decided_on)}, ${lit(r.decision.rule_cell)}, ${lit(r.decision.ruling)},
    ${lit(r.decision.record)}, v_dec);`;
    case 'section':
      return `call canon.set_section(v_org, ${lit(r.doc)}, ${lit(r.section)}, ${r.expected_version}, ${lit(r.body)}, ${lit(r.kickoff)},
    ${D(r.changed_on)}, v_ver);`;
  }
}

// F4: the Dictionary stamp line, rewritten in the head through canon.set_section, in the same transaction.
function stampOf(r) {
  if (r.stamp === undefined) return '';
  return `
  -- F4 stamp: exactly one stamp line in the Dictionary head; refused while it carries a Prior chain (pre-F4)
  select version_no, body into v_hv, v_head from canon.v_sections_current
   where org_id = v_org and doc_key = 'data-dictionary' and section_key = 'head';
  if v_head is null then raise exception 'canon_write: org has no Dictionary head section'; end if;
  select count(*) into v_n from regexp_matches(v_head, '^Last updated: \\*\\*[^*]+\\*\\*.*$', 'gn');
  if v_n <> 1 then raise exception 'canon_write: the Dictionary head holds % stamp lines (want exactly 1)', v_n; end if;
  v_m := regexp_match(v_head, '^(Last updated: \\*\\*([^*]+)\\*\\*.*)$', 'n');
  if position(' Prior: ' in v_m[1]) > 0 then
    raise exception 'canon_write: the stamp line still carries a Prior chain; drop it first (F4, a section write), then stamp';
  end if;
  v_new := case when v_m[2] like ${lit(r.changed_on)} || '%'
                then ${lit(r.changed_on)} || ' ×' || (coalesce(substring(v_m[2] from '×(\\d+)')::int, 1) + 1)
                else ${lit(r.changed_on)} end;
  v_line := 'Last updated: **' || v_new || '** — ' || ${lit(r.stamp)};
  -- a backslash in the replacement text is doubled (regexp_replace reads \\1 and \\& in it)
  v_head := regexp_replace(v_head, '^Last updated: \\*\\*[^*]+\\*\\*.*$', replace(v_line, '\\', '\\\\'), 'n');
  call canon.set_section(v_org, 'data-dictionary', 'head', v_hv, v_head, ${lit(r.kickoff)}, ${lit(r.changed_on)}::date, v_sv);`;
}

function emit(r) {
  const what = r.kind === 'section' ? `${r.doc} ${r.section}` : r.kind === 'decision' ? r.decision.rule_cell : r.rule;
  const inner = `declare
  v_org bigint; v_ver integer; v_dec bigint; v_cur record;
  v_hv integer; v_sv integer; v_head text; v_n integer; v_m text[]; v_new text; v_line text; v_since date;
  v_dd text; v_dc text;
begin
  select org_id into strict v_org from security.organizations where org_code = ${lit(r.org_code)};
  ${callOf(r)}${stampOf(r)}
  if exists (select from canon.v_current_mismatch where org_id = v_org) then
    raise exception 'canon_write: canon.v_current_mismatch is not empty after the write; nothing committed';
  end if;
  v_dd := encode(sha256(convert_to(canon.render_document(v_org, 'data-dictionary'), 'UTF8')), 'hex');
  v_dc := encode(sha256(convert_to(canon.render_document(v_org, 'decisions'), 'UTF8')), 'hex');
  raise notice 'canon_write ${r.kind} ${what.replace(/'/g, "''").replace(/%/g, '%%')}: version %, decision %, stamp %, decisions %, render sha256 dictionary % decisions %',
    coalesce(v_ver::text, '-'), coalesce(v_dec::text, (select max(seq)::text from canon.decisions where org_id = v_org)),
    coalesce(v_new, '-'), (select count(*) from canon.decisions where org_id = v_org), v_dd, v_dc;
end`;
  const tag = C.dollarTag(inner, 'cw');
  const sql = `-- canon_write.js ${r.kind} ${what} for ${r.org_code}, kickoff ${r.kickoff || '-'}, changed_on ${r.changed_on}${r.stamp !== undefined ? ', with the F4 stamp' : ''}.
-- One statement. Run with psql -1 as a person in wh_canon_writer; then render (canon_render.js).
do $${tag}$
${inner}
$${tag}$;
`;
  if (sql.includes('\r')) refuse('internal: the SQL holds a raw CR');
  return sql;
}

function main(argv) {
  const r = validate(request(argv));
  const sql = emit(r);
  if (r.emit) {
    if (r.out) { fs.writeFileSync(r.out, sql, 'utf8'); console.error(`wrote ${r.out} (${Buffer.byteLength(sql)} bytes, ${r.kind})`); }
    else process.stdout.write(sql);
    return 0;
  }
  const conn = C.connection(r.url_env);
  if (C.NOT_A_PERSON.test(conn.user)) refuse(`login ${conn.user} is not a person; canon is written by people only (wh_canon_writer)`);
  C.psql(sql, conn, { oneTxn: true });
  console.error('committed. Next: node canon_render.js --estate <estate> --org-code ' + r.org_code + ' --url-env ' + r.url_env);
  return 0;
}

if (require.main === module) C.runMain(() => main(process.argv.slice(2)));
module.exports = { request, validate, emit };
