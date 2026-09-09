#!/usr/bin/env node
// Template-vs-instance conformance proof for `templates/client/`.
//
// The template's process sections are LIFTED from a reference tenant, never re-typed. This
// proves the lift is still faithful: reverse-substitute the template with that tenant's values
// and every declared section must be byte-identical to the tenant's own copy.
//
//   node template_diff.js --instance <tenant dir> --map <placeholder map .json> [--template <dir>]
//
// The map is a plain `{"<placeholder>": "value"}` object and lives CLIENT-side, because it is
// the one file in the chain that knows a tenant's real values. Nothing here names a client.
//
// Exit 0 when every section matches, 1 on the first that does not (with a line-level diff).
//
// EXCLUSIONS are regexes applied to BOTH sides before comparing — an instance-only tail the
// template deliberately drops. Every one is PRINTED on every run: an exclusion nobody can see
// is a hole, and this gate has shipped an invisible one before.

const fs = require('fs');
const path = require('path');

function arg(name, dflt) {
  const i = process.argv.indexOf('--' + name);
  return i > -1 && process.argv[i + 1] ? process.argv[i + 1] : dflt;
}

const TEMPLATE = path.resolve(arg('template', path.join(__dirname, '..', 'templates', 'client')));
const INSTANCE = arg('instance', null);
const MAPFILE = arg('map', null);

if (!INSTANCE || !MAPFILE) {
  console.error('usage: template_diff.js --instance <tenant dir> --map <map.json> [--template <dir>]');
  process.exit(2);
}

const MAP = JSON.parse(fs.readFileSync(path.resolve(MAPFILE), 'utf8'));
const TDIR = path.join(TEMPLATE, '__tenant__');

// Sections: each names the file on both sides and the anchors that bound it.
// `file` is relative to the tenant root; a `instanceFile` glob covers a dated instance name.
const SECTIONS = [
  {
    name: 'BI-SOP §2 — the ripple runbook',
    file: 'bi-estate/BI-SOP.md',
    start: /^## 2 · When a business rule changes/,
    end: /^## 3 · Shared definitions/,
  },
  {
    name: 'Dictionary preamble — contract + writing rules',
    file: 'bi-estate/DATA-DICTIONARY.md',
    start: /^# .* BI Data Dictionary/,
    end: /^Last updated:/,
  },
  {
    name: 'Tenant CLAUDE.md — the pointer instruction block',
    file: 'CLAUDE.md',
    start: /^> \*\*A POINTER, not a log\.\*\*/,
    end: /^## /,
    exclude: [
      { why: 'instance-only tail: the pre-diet archive pointer', re: / Pre-diet: `[^`]*`\./g },
    ],
  },
  {
    name: 'Tenant CLAUDE.md — the Current-state instruction paragraph',
    file: 'CLAUDE.md',
    start: /^Caps, checked by/,
    end: /^- \*\*/,
  },
  {
    name: 'BI-SOP Appendix A · the dashboard section template',
    file: 'bi-estate/BI-SOP.md',
    start: /^## Appendix A · Section template/,
    end: /^### A2 · The WI page template/,
  },
  {
    name: 'BI-SOP Appendix A2 · the WI page template',
    file: 'bi-estate/BI-SOP.md',
    start: /^### A2 · The WI page template/,
    end: /^Dashboard-section \(SOP\) template rules/,
  },
  {
    name: 'QC surface register — the three surfaces',
    file: 'bi-estate/qc-surface-register.md',
    instanceGlob: /^qc-surface-register.*\.md$/,
    instanceDir: 'bi-estate',
    start: /^## The three surfaces/,
    end: /^## 1 · /,
  },
];

function read(p) {
  return fs.readFileSync(p, 'utf8').replace(/\r\n/g, '\n');
}

// Resolve the instance-side path, allowing a dated file name.
function instancePath(sec) {
  if (!sec.instanceGlob) return path.join(INSTANCE, sec.file);
  const dir = path.join(INSTANCE, sec.instanceDir);
  const hits = fs.readdirSync(dir).filter((f) => sec.instanceGlob.test(f));
  if (hits.length !== 1) {
    throw new Error(`instance file ${hits.length === 0 ? 'missing' : 'ambiguous'} for "${sec.name}" in ${dir}` +
      (hits.length ? ' — ' + hits.join(', ') : ''));
  }
  return path.join(dir, hits[0]);
}

// Slice by anchors. The START must match exactly one line — a repeated anchor silently
// re-points a span, which is how a doc patch once deleted five SOP sections.
function slice(text, sec, side) {
  const lines = text.split('\n');
  const starts = lines.reduce((a, l, i) => (sec.start.test(l) ? a.concat(i) : a), []);
  if (starts.length !== 1) {
    throw new Error(`${side}: start anchor ${starts.length === 0 ? 'missing' : 'repeated ' + starts.length + '×'} ` +
      `for "${sec.name}" (${sec.start})`);
  }
  const a = starts[0];
  let b = lines.length;
  for (let i = a + 1; i < lines.length; i++) {
    if (sec.end.test(lines[i])) { b = i; break; }
  }
  return lines.slice(a, b).join('\n').replace(/\s+$/, '');
}

// Reverse-substitute: the template's placeholders become the reference tenant's values.
// Longest value first so one value that contains another cannot be half-replaced.
function fill(text) {
  const pairs = Object.entries(MAP).sort((x, y) => y[1].length - x[1].length);
  let t = text;
  for (const [ph, val] of pairs) t = t.split(ph).join(val);
  return t;
}

function normalize(text, sec) {
  let t = text;
  for (const ex of sec.exclude || []) t = t.replace(ex.re, '');
  return t;
}

function diff(a, b) {
  const A = a.split('\n');
  const B = b.split('\n');
  const out = [];
  for (let i = 0; i < Math.max(A.length, B.length); i++) {
    if (A[i] !== B[i]) {
      out.push('    line ' + (i + 1));
      out.push('      template : ' + (A[i] === undefined ? '<end of section>' : JSON.stringify(A[i].slice(0, 160))));
      out.push('      instance : ' + (B[i] === undefined ? '<end of section>' : JSON.stringify(B[i].slice(0, 160))));
      if (out.length > 30) { out.push('    … more differences suppressed'); break; }
    }
  }
  return out;
}

console.log('template conformance — lifted process sections must round-trip');
console.log('  template : ' + TEMPLATE);
console.log('  instance : ' + path.resolve(INSTANCE));
console.log('  map      : ' + Object.keys(MAP).join(' '));
const exclusions = SECTIONS.flatMap((s) => (s.exclude || []).map((e) => '    ' + s.name + ' — ' + e.why));
console.log('  EXCLUSIONS applied to BOTH sides (' + exclusions.length + '):');
console.log(exclusions.length ? exclusions.join('\n') : '    none');
console.log('');

let failed = 0;
for (const sec of SECTIONS) {
  let tText, iText;
  try {
    tText = normalize(fill(slice(read(path.join(TDIR, sec.file)), sec, 'template')), sec);
    iText = normalize(slice(read(instancePath(sec)), sec, 'instance'), sec);
  } catch (e) {
    console.log('  ✘ ' + sec.name + ' — ' + e.message);
    failed++;
    continue;
  }
  if (tText === iText) {
    console.log('  ✔ ' + sec.name + ' — ' + tText.split('\n').length + ' lines identical after substitution');
  } else {
    failed++;
    console.log('  ✘ ' + sec.name + ' — differs');
    console.log(diff(tText, iText).join('\n'));
  }
}

console.log('');
if (failed) {
  console.log('FAIL — ' + failed + ' of ' + SECTIONS.length + ' section(s) drifted.');
  console.log('Fix the side that is wrong, or declare the difference as an exclusion with a reason.');
  process.exit(1);
}
console.log('PASS — all ' + SECTIONS.length + ' lifted section(s) round-trip byte-identical.');
process.exit(0);
