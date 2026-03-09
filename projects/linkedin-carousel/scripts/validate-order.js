#!/usr/bin/env node

// Validates that every file in build.js ORDER exists on disk
// and every .js/.jsx file under src/ is listed in ORDER.
// Non-zero exit blocks commits when wired into pre-commit.

var fs = require("fs");
var path = require("path");

var ROOT = path.resolve(__dirname, "..");
var SRC = path.join(ROOT, "src");

// --- Extract ORDER array from build.js ---

var buildSrc = fs.readFileSync(path.join(ROOT, "build.js"), "utf8");
var match = buildSrc.match(/var ORDER\s*=\s*\[([\s\S]*?)\]/);
if (!match) {
  console.error("validate-order: could not parse ORDER array from build.js");
  process.exit(1);
}

var ORDER = match[1]
  .split(",")
  .map(function (s) { return s.trim().replace(/^["']|["']$/g, ""); })
  .filter(function (s) { return s.length > 0; });

// --- Check 1: every ORDER entry exists on disk ---

var missing = [];
ORDER.forEach(function (rel) {
  if (!fs.existsSync(path.join(ROOT, rel))) {
    missing.push(rel);
  }
});

// --- Check 2: every src/**/*.{js,jsx} is in ORDER ---

function collectFiles(dir) {
  var results = [];
  fs.readdirSync(dir).forEach(function (name) {
    var full = path.join(dir, name);
    var stat = fs.statSync(full);
    if (stat.isDirectory()) {
      results = results.concat(collectFiles(full));
    } else if (/\.(js|jsx)$/.test(name)) {
      results.push(path.relative(ROOT, full).replace(/\\/g, "/"));
    }
  });
  return results;
}

var diskFiles = collectFiles(SRC);
var orderSet = {};
ORDER.forEach(function (rel) { orderSet[rel] = true; });

var unlisted = diskFiles.filter(function (f) { return !orderSet[f]; });

// --- Report ---

var ok = true;

if (missing.length > 0) {
  console.error("validate-order: files in ORDER but missing on disk:");
  missing.forEach(function (f) { console.error("  " + f); });
  ok = false;
}

if (unlisted.length > 0) {
  console.error("validate-order: src/ files not listed in ORDER:");
  unlisted.forEach(function (f) { console.error("  " + f); });
  ok = false;
}

if (ok) {
  console.log("validate-order: OK (" + ORDER.length + " files, all matched)");
} else {
  process.exit(1);
}
