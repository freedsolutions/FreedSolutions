#!/usr/bin/env node

/*
 * Sync smoke handoff metadata with current repo state.
 * Intended to run after a successful build and commit.
 * Canonical file: SMOKE_TEST.md
 * One-cycle fallback: SMOKE_TEST_HANDOFF_TEMPLATE.md
 */

var fs = require("fs");
var path = require("path");
var cp = require("child_process");

var ROOT = path.join(__dirname, "..");
var HANDOFF_CANDIDATES = [
  "SMOKE_TEST.md",
  "SMOKE_TEST_HANDOFF_TEMPLATE.md"
];

function run(cmd) {
  return cp.execSync(cmd, { cwd: ROOT, stdio: ["ignore", "pipe", "pipe"] }).toString().trim();
}

function todayIsoDate() {
  var d = new Date();
  var y = String(d.getFullYear());
  var m = String(d.getMonth() + 1).padStart(2, "0");
  var day = String(d.getDate()).padStart(2, "0");
  return y + "-" + m + "-" + day;
}

function resolveHandoffPath() {
  for (var i = 0; i < HANDOFF_CANDIDATES.length; i++) {
    var candidatePath = path.join(ROOT, HANDOFF_CANDIDATES[i]);
    if (fs.existsSync(candidatePath)) return candidatePath;
  }
  throw new Error("Missing smoke handoff file. Expected one of: " + HANDOFF_CANDIDATES.join(", "));
}

var handoffPath = resolveHandoffPath();
var handoffName = path.basename(handoffPath);

var hash = run("git rev-parse --short HEAD");
if (!hash) {
  throw new Error("Failed to resolve current commit hash.");
}

var date = todayIsoDate();
var text = fs.readFileSync(handoffPath, "utf8");

if (!/^- Commit hash under test: `.*`$/m.test(text)) {
  throw new Error("Could not find commit hash line in handoff template.");
}
if (!/^- Build confirmation: `node build\.js` succeeded \(.+\)$/m.test(text)) {
  throw new Error("Could not find build confirmation line in handoff template.");
}

text = text.replace(/^- Commit hash under test: `.*`$/m, "- Commit hash under test: `" + hash + "`");
text = text.replace(
  /^- Build confirmation: `node build\.js` succeeded \(.+\)$/m,
  "- Build confirmation: `node build.js` succeeded (yes, " + date + ")"
);

fs.writeFileSync(handoffPath, text, "utf8");

console.log("Updated " + handoffName + ":");
console.log("- File path: " + handoffPath);
console.log("- Commit hash under test: " + hash);
console.log("- Build confirmation date: " + date);
