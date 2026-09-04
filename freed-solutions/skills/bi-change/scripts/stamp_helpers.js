// stamp_helpers.js — anchored, transactional edits for the estate documents (Dictionary, SOP, WI,
// guides, README). Every edit anchors on a unique string or regex and throws before writing when
// the anchor is missing or ambiguous, so a concurrent session's edit can never be clobbered
// silently. Usage: const { fs, load, once, onceRe, restamp, restampDictionary } = require(<this file>);
const fs = require("fs");

function load(p) { const s = fs.readFileSync(p, "utf8"); return { s, nl: s.includes("\r\n") ? "\r\n" : "\n" }; }

// index of a unique literal anchor; throws when missing or repeated
function once(hay, needle, label) {
  const i = hay.indexOf(needle); if (i < 0) throw new Error("anchor missing: " + label);
  if (hay.indexOf(needle, i + 1) >= 0) throw new Error("anchor not unique: " + label); return i;
}
// match of a unique regex anchor; throws when missing or repeated
function onceRe(hay, re, label) {
  const m = hay.match(re); if (!m) throw new Error("regex anchor missing: " + label);
  const g = hay.match(new RegExp(re.source, re.flags.includes("g") ? re.flags : re.flags + "g"));
  if (g.length !== 1) throw new Error("regex anchor not unique: " + label + " (" + g.length + ")"); return m;
}
// replace a unique literal anchor (swap(s, a, b, label))
function swap(s, a, b, label) { if (s.split(a).length !== 2) throw new Error("anchor not unique/missing: " + label); return s.replace(a, b); }

// Same-day stamps count up: "2026-09-03" → "2026-09-03 ×2" → "×3". `today` = YYYY-MM-DD.
function nextStamp(current, today) {
  if (!current.startsWith(today)) return today;
  const n = parseInt((current.match(/×(\d+)/) || [0, 1])[1], 10) || 1; return today + " ×" + (n + 1);
}
// Prepend a new stamp, nesting the current one as Prior. form = "sop" | "guide" (**Last synced: X** (text)
// or "wi" (**Last synced: X.** *(text)). Returns { s, stamp }.
function restamp(s, form, today, text) {
  if (form === "wi") {
    const m = onceRe(s, /^\*\*Last synced: ([^*]+?)\.?\*\* \*\(/m, "stamp"); const stamp = nextStamp(m[1], today);
    return { s: s.replace(m[0], "**Last synced: " + stamp + ".** *(" + text + " Prior: " + m[1] + ".** *("), stamp };
  }
  const m = onceRe(s, /^\*\*Last synced: ([^*]+)\*\* \(/m, "stamp"); const stamp = nextStamp(m[1], today);
  return { s: s.replace(m[0], "**Last synced: " + stamp + "** (" + text + " Prior: **" + m[1] + "** ("), stamp };
}
// The Dictionary header: "Last updated: **X** (text … Prior: **Y** (…". Returns { s, stamp }.
function restampDictionary(s, today, text) {
  const m = onceRe(s, /^Last updated: \*\*([^*]+)\*\* \(/m, "DD header"); const stamp = nextStamp(m[1], today);
  return { s: s.replace(m[0], "Last updated: **" + stamp + "** (" + text + " Prior: **" + m[1] + "** ("), stamp };
}
// Append a register row after the last "| Rnn |" row. Throws when the id already exists.
function appendRegisterRow(s, nl, row) {
  const id = row.match(/^\| (R\d+) \|/); if (!id) throw new Error("row must start with | Rnn |");
  if (new RegExp("^\\| " + id[1] + " \\|", "m").test(s)) throw new Error(id[1] + " already present");
  const rows = [...s.matchAll(/^\| R\d+ \|[^\r\n]*$/gm)]; const last = rows[rows.length - 1];
  return s.slice(0, last.index + last[0].length) + nl + row + s.slice(last.index + last[0].length);
}
module.exports = { fs, load, once, onceRe, swap, nextStamp, restamp, restampDictionary, appendRegisterRow };
