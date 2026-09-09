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
//
// Exit 1 on any hit, so it can gate a commit.
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

const files = [];
(function walk(d) {
  for (const e of fs.readdirSync(d, { withFileTypes: true })) {
    const p = path.join(d, e.name);
    if (e.isDirectory()) { walk(p); continue; }
    if (e.name === SELF_NAME) continue;
    if (/\.(md|js|sh|py|ps1|json|txt)$/i.test(e.name)) files.push(p);
  }
})(ROOT);

const hits = [];
for (const f of files) {
  const rel = path.relative(ROOT, f).replace(/\\/g, '/');
  const lines = fs.readFileSync(f, 'utf8').replace(/\r\n/g, '\n').split('\n');
  lines.forEach((l, i) => {
    for (const r of RULES) {
      // A scoped rule runs only on the paths it names. The scope is on the RULE, not on the file
      // walk, so a scoped rule can never quietly narrow what the unscoped rules see.
      if (r.only && !r.only.test(rel)) continue;
      r.re.lastIndex = 0;
      let m;
      while ((m = r.re.exec(l))) {
        if (r.name === 'concrete client path') {
          const around = l.slice(Math.max(0, m.index), m.index + 40);
          if (ALLOWED_PLACEHOLDER.test(around)) continue;
        }
        hits.push({
          file: path.relative(ROOT, f).replace(/\\/g, '/'),
          line: i + 1, rule: r.name, text: m[0], ctx: l.trim().slice(0, 110),
        });
      }
    }
  });
}

console.log('client-leakage proof — ' + ROOT);
console.log('  ' + files.length + ' tracked skill file(s) scanned');
console.log('  rules: tenant name (case-insensitive, so a lowercase filename token counts)');
console.log('         concrete client path (a `clients/<slug>/` placeholder is allowed)');
console.log('         rule id `Rnn` — SCOPED to templates/client/, where a register label is residue');
console.log('  EXCLUDED: any file named ' + SELF_NAME + ' — the detector names the strings it hunts for\n');

if (!hits.length) {
  console.log('PASS — 0 hits across all ' + RULES.length + ' classes.');
  process.exit(0);
}
for (const h of hits) console.log('  ' + h.file + ':' + h.line + '  [' + h.rule + ' "' + h.text + '"]\n      ' + h.ctx);
console.log('\nFAIL — ' + hits.length + ' hit(s).');
process.exit(1);
