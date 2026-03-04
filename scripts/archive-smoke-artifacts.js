#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..");
const archiveStamp = new Date()
  .toISOString()
  .replace(/[-:]/g, "")
  .replace(/\..+$/, "")
  .replace("T", "-");
const archiveRoot = path.join(repoRoot, ".playwright-mcp", "archive", archiveStamp);

const ROOT_SCREENSHOT_PATTERNS = [
  /^smoke-test.*\.png$/i,
  /^slide-panel.*\.png$/i,
  /^layer-.*-test\.png$/i,
  /^final-layout\.png$/i,
];

function exists(targetPath) {
  return fs.existsSync(targetPath);
}

function collectFiles(dirPath, shouldKeep, skipDir, out = []) {
  if (!exists(dirPath)) return out;

  for (const entry of fs.readdirSync(dirPath, { withFileTypes: true })) {
    const fullPath = path.join(dirPath, entry.name);
    if (entry.isDirectory()) {
      if (skipDir && skipDir(fullPath)) continue;
      collectFiles(fullPath, shouldKeep, skipDir, out);
      continue;
    }
    if (shouldKeep(fullPath, entry)) out.push(fullPath);
  }
  return out;
}

function moveFile(srcPath, dstPath) {
  fs.mkdirSync(path.dirname(dstPath), { recursive: true });
  try {
    fs.renameSync(srcPath, dstPath);
  } catch (err) {
    if (err && err.code === "EXDEV") {
      fs.copyFileSync(srcPath, dstPath);
      fs.unlinkSync(srcPath);
      return;
    }
    throw err;
  }
}

function pruneEmptyDirs(startPath, stopPath) {
  if (!exists(startPath)) return;
  let current = startPath;
  const stopAbs = path.resolve(stopPath);

  while (true) {
    const currentAbs = path.resolve(current);
    if (!currentAbs.startsWith(stopAbs)) break;
    if (!exists(currentAbs)) break;

    const contents = fs.readdirSync(currentAbs);
    if (contents.length > 0) break;
    fs.rmdirSync(currentAbs);
    if (currentAbs === stopAbs) break;
    current = path.dirname(currentAbs);
  }
}

const candidates = [];

for (const entry of fs.readdirSync(repoRoot, { withFileTypes: true })) {
  if (!entry.isFile()) continue;
  if (!ROOT_SCREENSHOT_PATTERNS.some((pattern) => pattern.test(entry.name))) continue;
  candidates.push({
    srcPath: path.join(repoRoot, entry.name),
    relPath: path.join("repo-root", entry.name),
  });
}

const mcpRoot = path.join(repoRoot, ".playwright-mcp");
const mcpArchiveRoot = path.join(mcpRoot, "archive");
collectFiles(
  mcpRoot,
  () => true,
  (dirPath) => path.resolve(dirPath) === path.resolve(mcpArchiveRoot)
).forEach((srcPath) => {
  candidates.push({
    srcPath,
    relPath: path.relative(repoRoot, srcPath),
  });
});

const testResultsRoot = path.join(repoRoot, "test-results");
collectFiles(testResultsRoot, () => true).forEach((srcPath) => {
  candidates.push({
    srcPath,
    relPath: path.relative(repoRoot, srcPath),
  });
});

if (candidates.length === 0) {
  console.log("[archive-smoke-artifacts] No Playwright/smoke artifacts to archive.");
  process.exit(0);
}

for (const item of candidates) {
  moveFile(item.srcPath, path.join(archiveRoot, item.relPath));
}

pruneEmptyDirs(testResultsRoot, repoRoot);
pruneEmptyDirs(mcpRoot, repoRoot);

console.log(
  `[archive-smoke-artifacts] Archived ${candidates.length} artifact(s) to ${path.relative(
    repoRoot,
    archiveRoot
  )}`
);
