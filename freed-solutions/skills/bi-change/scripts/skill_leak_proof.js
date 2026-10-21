#!/usr/bin/env node
// Client-leakage proof for TRACKED skill files.
//
// The earlier version of this check grepped tenant NAMES only, case-sensitively, and reported
// "zero leakage" while 14 concrete `clients/primitiv/...` paths and two lowercase `hscg-`
// filenames sat in the same files. The repo CLAUDE.md forbids naming a client engagement in any
// tracked file, so the proof now covers, case-insensitively:
//
//   1. tenant names          HSCG / High Street / Primitiv (also catches `hscg-*` filename tokens)
//   2. concrete client paths clients/<a real slug>/... — a generic `clients/<slug>/` placeholder
//                            is the MECHANISM and is allowed; a real slug is the leak
//   3. tenant ids as values   a quoted run of bare integers beside lsp_id / loc_id / LspId / LocId
//   4. backoffice server host <label>.backoffice.dutchie.com with a concrete label
//
// Classes 3 and 4 are DIFFERENT IN KIND and are named differently on purpose. A tenant id is the
// client: `"<lsp id>, <lsp id>"` filled in with real numbers names the engagement. A Backoffice
// subdomain is a Dutchie SERVER CLUSTER shared by many tenants, so a concrete one is not a tenant
// reference — it is a stale environment pin that teaches the reader to hit one cluster. Worth
// genericising, but do not read a `server identifier` hit as a client leak.
//
// Exit 1 on any hit, so it can gate a commit.
//   node <skill>/scripts/skill_leak_proof.js [skills root]   scan the tracked skill sources
//   node <skill>/scripts/skill_leak_proof.js --selftest      prove every rule on breaker fixtures
const fs = require('fs');
const path = require('path');

// Scan the SKILL SOURCE tree, found by walking up — never a hardcoded path, and never `../..`,
// so this runs identically from the source and from a synced wrapper copy (whose `../..` would
// point at `.claude/skills` and check generated files instead of tracked ones).
//   node <skill>/scripts/skill_leak_proof.js [skills root]
function findSkillsRoot(start) {
  let d = start;
  for (let i = 0; i < 10; i++) {
    const c = path.join(d, 'freed-solutions', 'skills');
    if (fs.existsSync(c)) return c;
    const up = path.dirname(d);
    if (up === d) break;
    d = up;
  }
  throw new Error('skill_leak_proof: cannot find freed-solutions/skills above ' + start +
    ' — pass the skills root as an argument.');
}
const ROOT = process.argv[2] ? path.resolve(process.argv[2]) : findSkillsRoot(__dirname);

// Placeholders that are the portable mechanism, not a client reference.
const ALLOWED_PLACEHOLDER = /clients[\/\\](<[^>]+>|\.\.\.|\{[^}]+\})/i;

// A rule may carry `allow`, tested against ITS CAPTURE GROUP 1 — the one span whose concreteness
// is the whole question (the quoted value; the host label). A match whose group 1 is a placeholder
// is the documented generic form and passes. The escape is deliberately reachable, not dead code:
// the host pattern MATCHES `<server>.backoffice…` and is cleared here, and the id pattern matches a
// NUMBERED placeholder (`"<lsp id 1>, <lsp id 2>"`) and is cleared here too. A fixture can exercise
// this branch; an escape that could never fire would prove nothing about either rule.
const ALLOWED_GENERIC = /<[^>]+>|\{[^}]+\}/;

const RULES = [
  // Word-bounded: bare `Primitiv` also matches the word "primitive", which appears legitimately in
  // the traps file. `\b` still catches the `hscg-` filename token, since `-` is a non-word char.
  { name: 'tenant name', re: /\bHSCG\b|\bHigh Street\b|\bPrimitiv\b/gi },
  { name: 'concrete client path', re: /clients[\/\\][A-Za-z0-9_-]+[\/\\]/gi },
  // A RULE ID inside the client template is client residue (Adam, 2026-09-09). The template's
  // process sections are lifted verbatim from a reference tenant, so any `Rnn` that survives the
  // lift is that tenant's register label — a number the scaffolded tenant will never own, pointing
  // at a rule it does not have. SCOPED to templates/client/: rule ids are legitimate everywhere
  // else in this skill (the kickoff template's `R00`, the gate's header contract, SKILL.md's
  // worked example), so a repo-wide version of this rule would be noise and get switched off.
  { name: 'rule id in the client template', re: /\bR\d+\b/g, only: /templates[\/\\]client[\/\\]/ },
  // A TENANT ID PRESENTED AS A REAL VALUE — the actual client leak of the two added below. The
  // shape, never the numbers: a tenant-id key (`lsp_id`, `loc_id`, `LspId`, `LocId`, and the
  // `logged_in_lsp_id` family — no leading \b, so a prefixed key still counts) followed within one
  // line by a QUOTED span carrying bare integers. Quoted is the discriminator, because that is the
  // form in which an embed user attribute is quoted back as a real value.
  //   NOT matched, and these are the mechanism that must keep passing:
  //     `lsp_id|number`          a schema line — the key with no quoted value at all
  //     `"LspId":…`              an elided payload — quoted KEY, value elided to `…`
  //     `LspId: 11`              an unquoted fixture literal in a script
  //     `"<lsp id>, <lsp id>"`   the placeholder — no bare integer inside the quotes
  { name: 'tenant id as a real value',
    re: /(?:lsp|loc)_?id\b[^\n]{0,120}?((["'])[^"'\n]*\d[^"'\n]*\2)/gi, allow: ALLOWED_GENERIC },
  // A CONCRETE BACKOFFICE SERVER HOST. Named as a SERVER identifier, not a tenant one: the
  // subdomain is a Dutchie server cluster that many tenants share, so pinning one teaches the
  // reader an environment they may not be on — it does not name the client. Group 1 is the host
  // label, so `<server>` and `{server}` clear via the escape and a concrete label does not.
  { name: 'backoffice server host',
    re: /([A-Za-z0-9_<>{}.-]+)\.backoffice\.dutchie\.com/gi, allow: ALLOWED_GENERIC },
];

// THIS DETECTOR EXCLUDES ITSELF, and says so in the report. A detector that names the strings it
// hunts for will always match itself; the alternative — assembling the literals from fragments so
// they never appear whole — would make the one file a reviewer most needs to read unreadable.
//
// Matched by BASENAME, not by `__filename`. When this runs from a synced wrapper copy it scans the
// SOURCE tree, so `__filename` is a different path from the copy under scan and a path-equality
// test silently protects nothing — which is exactly what happened on the first wrapper run.
// The exclusion is one filename, and it is printed on every run so it can never be a silent hole.
const SELF_NAME = path.basename(__filename);

// A JSON string encodes its line breaks as the two characters `\n` (or four, `\r\n`), so a
// markdown document embedded in a .json file — Dutchie's OpenAPI spec carries its Getting-Started
// guide that way — arrives as ONE physical line. The tenant-id rule reads "within one line", and
// on that physical line the spec's example `"lspId": 123,\r\n "locId": 456` paired the key's
// closing quote with the NEXT key's opening quote and read `: 123,\r\n "` as a quoted value
// (2026-10-21, the first scan after the spec moved under the skill). An encoded break is therefore
// a line break for the rules too; the reported line number stays the physical one, so a hit is
// still findable in the file. Not a carve-out: the same example with the id QUOTED
// (`\"lspId\": \"123\"`) still fails, and `--selftest` holds both halves of that pair.
const ENCODED_BREAK = /\\r\\n|\\n/;

function scanRoot(root) {
  const files = [];
  (function walk(d) {
    for (const e of fs.readdirSync(d, { withFileTypes: true })) {
      const p = path.join(d, e.name);
      if (e.isDirectory()) { walk(p); continue; }
      if (e.name === SELF_NAME) continue;
      if (/\.(md|js|sh|py|ps1|json|txt)$/i.test(e.name)) files.push(p);
    }
  })(root);

  const hits = [];
  for (const f of files) {
    const rel = path.relative(root, f).replace(/\\/g, '/');
    const lines = fs.readFileSync(f, 'utf8').replace(/\r\n/g, '\n').split('\n');
    lines.forEach((physical, i) => {
      for (const l of physical.split(ENCODED_BREAK)) {
        for (const r of RULES) {
          // A scoped rule runs only on the paths it names. The scope is on the RULE, not on the
          // file walk, so a scoped rule can never quietly narrow what the unscoped rules see.
          if (r.only && !r.only.test(rel)) continue;
          r.re.lastIndex = 0;
          let m;
          while ((m = r.re.exec(l))) {
            if (r.name === 'concrete client path') {
              const around = l.slice(Math.max(0, m.index), m.index + 40);
              if (ALLOWED_PLACEHOLDER.test(around)) continue;
            }
            // The placeholder escape, judged on the ONE span the rule captured — not on the whole
            // match, where a placeholder sitting in the surrounding prose would clear a real value.
            if (r.allow && m[1] !== undefined && r.allow.test(m[1])) continue;
            hits.push({ file: rel, line: i + 1, rule: r.name, text: m[0], ctx: l.trim().slice(0, 110) });
          }
        }
      }
    });
  }
  return { files, hits };
}

// --selftest: every rule proven to FAIL on a breaker and to PASS on the documented mechanism, on
// fixtures written to a temp root. A green scan of the real tree says nothing about whether the
// detector can still see anything; this does. Each fixture is one file and the exact number of
// hits it must raise. Exit 1 on any fixture whose count is not the expected one.
if (process.argv[2] === '--selftest') {
  const os = require('os');
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'skill-leak-proof-'));
  const fixtures = [
    // [relative path, content, expected hits, what the fixture proves]
    ['tenant-name.md', 'the HSCG estate\n', 1, 'a tenant name hits'],
    ['tenant-name-token.md', 'see hscg-rules.md\n', 1, 'a lowercase filename token hits'],
    ['client-path.md', 'see clients/acme/discovery/\n', 1, 'a concrete client path hits'],
    ['client-path-placeholder.md', 'see clients/<slug>/discovery/\n', 0, 'the clients/<slug>/ placeholder passes'],
    ['templates/client/x.md', 'per R12 the line\n', 1, 'a rule id inside templates/client/ hits'],
    ['templates/kickoff.md', 'per R12 the line\n', 0, 'a rule id outside templates/client/ passes'],
    ['tenant-id.md', 'lsp_id: "11, 12"\n', 1, 'a quoted tenant id hits'],
    ['tenant-id-mechanism.md', 'lsp_id|number\n"LspId":…\nlsp_id: "<lsp id 1>, <lsp id 2>"\nLspId: 11\n', 0,
      'a schema line, an elided payload, a numbered placeholder and an unquoted fixture literal pass'],
    ['spec-example.json', '{"description": "```json\\r\\n{\\r\\n  \\"lspId\\": 123,\\r\\n  \\"locId\\": 456\\r\\n}"}\n', 0,
      'an id on one ENCODED line and a quote on the next do not pair into a value'],
    ['spec-quoted-id.json', '{"description": "\\"lspId\\": \\"123\\""}\n', 1, 'a quoted id inside an encoded line still hits'],
    ['host.md', 'curl https://nj-prod.backoffice.dutchie.com/\n', 1, 'a concrete backoffice host hits'],
    ['host-placeholder.md', 'curl https://<server>.backoffice.dutchie.com/\n', 0, 'the <server> host passes'],
  ];
  for (const [rel, content] of fixtures) {
    const p = path.join(tmp, rel);
    fs.mkdirSync(path.dirname(p), { recursive: true });
    fs.writeFileSync(p, content, 'utf8');
  }
  const counts = {};
  for (const h of scanRoot(tmp).hits) counts[h.file] = (counts[h.file] || 0) + 1;
  fs.rmSync(tmp, { recursive: true, force: true });

  let failed = 0;
  console.log('skill_leak_proof --selftest: ' + fixtures.length + ' fixtures');
  for (const [rel, , expected, proves] of fixtures) {
    const got = counts[rel] || 0;
    const ok = got === expected;
    if (!ok) failed++;
    console.log('  ' + (ok ? 'PASS' : 'FAIL') + '  ' + rel + ': ' + proves + ' (expected ' + expected + ', got ' + got + ')');
  }
  console.log(failed ? '\nFAIL — ' + failed + ' fixture(s) did not behave.' : '\nPASS — every rule fails on its breaker and passes on its mechanism.');
  process.exit(failed ? 1 : 0);
}

const { files, hits } = scanRoot(ROOT);

console.log('client-leakage proof — ' + ROOT);
console.log('  ' + files.length + ' tracked skill file(s) scanned');
console.log('  rules: tenant name (case-insensitive, so a lowercase filename token counts)');
console.log('         concrete client path (a `clients/<slug>/` placeholder is allowed)');
console.log('         rule id `Rnn` — SCOPED to templates/client/, where a register label is residue');
console.log('         tenant id as a real value (a quoted integer run beside an lsp_id/loc_id key;');
console.log('           a schema line, an elided payload and a `<lsp id>` placeholder all pass)');
console.log('         backoffice server host (a concrete `<label>.backoffice.dutchie.com` — a SERVER');
console.log('           cluster pin, not a tenant name; `<server>` passes, as does the shared Looker host)');
console.log('  EXCLUDED: any file named ' + SELF_NAME + ' — the detector names the strings it hunts for\n');

if (!hits.length) {
  console.log('PASS — 0 hits across all ' + RULES.length + ' classes.');
  process.exit(0);
}
for (const h of hits) console.log('  ' + h.file + ':' + h.line + '  [' + h.rule + ' "' + h.text + '"]\n      ' + h.ctx);
console.log('\nFAIL — ' + hits.length + ' hit(s).');
process.exit(1);
