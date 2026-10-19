// canon_common.js — shared helpers for canon_write.js and canon_render.js (HELD until the canon flip).
//
// The tenant's canon (the Dictionary register and the DECISIONS record) lives in the warehouse schema
// `canon` (tables + writer procedures). These helpers hold what both scripts need: argument parsing, the
// gate's seal hash, SQL literals that survive psql on Windows, the cell rules the writer procedures
// enforce, and the psql call. Zero dependencies (node standard library only). Nothing here names a client.
'use strict';
const crypto = require('crypto');
const { spawnSync } = require('child_process');

class Refusal extends Error {}
// A refusal is a usage or input defect: exit 2, nothing sent, nothing written.
function refuse(msg) { throw new Refusal(msg); }
function runMain(main) {
  try { const code = main(); process.exit(code || 0); }
  catch (e) {
    if (e instanceof Refusal) { console.error('REFUSED: ' + e.message); process.exit(2); }
    throw e;
  }
}

// --flag value | --flag (boolean). `spec` = { name: 'value' | 'bool' }; an unknown flag is refused, so a typo
// can never be silently ignored. Positional arguments are returned in `_`.
function parseArgs(argv, spec) {
  const out = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith('--')) { out._.push(a); continue; }
    const name = a.slice(2);
    if (!(name in spec)) refuse('unknown flag ' + a);
    if (spec[name] === 'bool') { out[name] = true; continue; }
    const v = argv[i + 1];
    if (v === undefined || v.startsWith('--')) refuse(a + ' needs a value');
    out[name] = v; i++;
  }
  return out;
}

// The gate's seal hash, verbatim from kickoff_check.js (gate_selftest T1 compares the two sources).
function sha1(s) { return crypto.createHash('sha1').update(s.replace(/\s+/g, ' ').trim()).digest('hex').slice(0, 12); }
const sha256 = b => crypto.createHash('sha256').update(Buffer.isBuffer(b) ? b : Buffer.from(String(b), 'utf8')).digest('hex');

// A SQL literal. A text with a line break becomes an E'' literal with \r / \n escapes, so the SQL never holds a
// raw CR or LF inside a string: psql on Windows reads a script in text mode and turns CRLF into LF (the
// canon loader lost a CRLF head that way once).
function lit(s) {
  if (s === null || s === undefined) return 'null';
  s = String(s);
  if (!/[\r\n\\]/.test(s)) return "'" + s.replace(/'/g, "''") + "'";
  return "E'" + s.replace(/\\/g, '\\\\').replace(/'/g, "''").replace(/\r/g, '\\r').replace(/\n/g, '\\n') + "'";
}
// A dollar-quote tag that does not occur in the body.
function dollarTag(body, base) { let t = base; while (body.includes('$' + t + '$')) t += 'x'; return t; }

function localDate() { const d = new Date(); const p = n => String(n).padStart(2, '0'); return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`; }
const ISO = /^\d{4}-\d{2}-\d{2}$/;
function isoDate(v, what) {
  if (!ISO.test(v || '') || Number.isNaN(Date.parse(v + 'T00:00:00Z'))) refuse(what + ' must be YYYY-MM-DD, got ' + JSON.stringify(v));
  return v;
}

// The cell rules of the writer procedures (canon.check_cell), applied before anything is sent.
const STATUSES = ['ACTIVE', 'RETIRED', 'DEFERRED', 'PROPOSED'];
const RULE_CAP = 600;   // gate C1
function checkCell(v, what, { allowEmpty = false, allowPipe = false } = {}) {
  if (v === null || v === undefined) refuse(what + ' is missing');
  v = String(v);
  if (v === '' && !allowEmpty) refuse(what + ' is empty');
  if (/[\r\n]/.test(v)) refuse(what + ' holds a line break (a table cell is one line)');
  if (!allowPipe && /(?<!\\)\|/.test(v)) refuse(what + ' holds an unescaped pipe (escape it as \\|)');
  if (v !== v.replace(/^[ \t\f\v]+|[ \t\f\v]+$/g, '')) refuse(what + ' has leading or trailing whitespace');
  return v;
}
// The rule keys a DECISIONS rule cell names (canon.decision_keys): its R / DD / SOP tokens; any other token
// makes the cell keyless, which maps to DD.
function decisionKeys(cell) {
  const toks = String(cell).split(/[\s,]+/).filter(Boolean);
  if (toks.length && toks.every(t => /^(R\d+|DD|SOP)$/.test(t))) return [...new Set(toks)].sort();
  return ['DD'];
}

// A login named like an agent, analyst, ingest or surface login is not a person; canon.writer_refusal
// refuses it in the database. The scripts refuse it first, with the same words.
const NOT_A_PERSON = /_(agent|analyst|ingest|surface)$/;

// The connection comes from the environment variable NAMED by --url-env, never from a literal on the command
// line. The URL is split into libpq variables of the psql child and the SQL goes on stdin, so the connection
// string is never on a command line, in the SQL or on disk.
function connection(urlEnv) {
  if (!urlEnv) refuse('--send needs --url-env <ENV VAR NAME> (the variable holds the login; never pass a URL)');
  if (/[:/@]/.test(urlEnv)) refuse('--url-env takes the NAME of an environment variable, not a connection string');
  const url = process.env[urlEnv];
  if (!url) refuse('environment variable ' + urlEnv + ' is not set (load the login into it first)');
  let u;
  try { u = new URL(url); } catch (e) { refuse('environment variable ' + urlEnv + ' does not hold a postgres URL'); }
  const env = { ...process.env, PGHOST: u.hostname, PGPORT: u.port || '5432', PGUSER: decodeURIComponent(u.username),
    PGPASSWORD: decodeURIComponent(u.password), PGDATABASE: decodeURIComponent(u.pathname.slice(1)),
    PGSSLMODE: u.searchParams.get('sslmode') || 'require', PGCLIENTENCODING: 'UTF8' };
  delete env[urlEnv];
  return { env, user: env.PGUSER };
}
// Runs the SQL with psql. oneTxn = psql -1 (all or nothing). capture = return stdout (tuples only, unaligned).
function psql(sql, conn, { oneTxn = true, capture = false } = {}) {
  if (sql.includes('\r')) refuse('internal: the SQL holds a raw CR (psql on Windows would drop it)');
  const args = ['-X', '-q', '-v', 'ON_ERROR_STOP=1', ...(oneTxn ? ['-1'] : []), ...(capture ? ['-A', '-t'] : []), '-f', '-'];
  const r = spawnSync('psql', args, { input: sql, env: conn.env, encoding: capture ? 'utf8' : undefined,
    stdio: ['pipe', capture ? 'pipe' : 'inherit', 'inherit'], maxBuffer: 64 * 1024 * 1024 });
  if (r.error) refuse('psql did not start: ' + r.error.message);
  if (r.status !== 0) { console.error('psql exit ' + r.status + ': nothing committed'); process.exit(1); }
  return capture ? r.stdout : null;
}

module.exports = { Refusal, refuse, runMain, parseArgs, sha1, sha256, lit, dollarTag, localDate, isoDate,
  STATUSES, RULE_CAP, checkCell, decisionKeys, NOT_A_PERSON, connection, psql };
