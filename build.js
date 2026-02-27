#!/usr/bin/env node

var fs = require("fs");
var path = require("path");

var ROOT = __dirname;
var OUTPUT = path.join(ROOT, "linkedin-carousel.jsx");

// Keep this order explicit for deterministic builds.
// Dependencies flow top-to-bottom: each file may use symbols from files above it.
var ORDER = [
  "src/constants.js",
  "src/canvas/hexToRgba.js",
  "src/canvas/backgrounds.js",
  "src/canvas/text.js",
  "src/canvas/overlays.js",
  "src/canvas/screenshot.js",
  "src/canvas/renderSlideContent.js",
  "src/canvas/renderSlide.js",
  "src/slideFactory.js",
  "src/undoRedo.js",
  "src/pdfBuilder.js",
  "src/ColorPickerInline.jsx",
  "src/App.jsx"
];

var parts = ORDER.map(function(relPath) {
  var absPath = path.join(ROOT, relPath);
  if (!fs.existsSync(absPath)) {
    throw new Error("Missing source file: " + relPath);
  }
  return fs.readFileSync(absPath, "utf8").replace(/^\uFEFF/, "").replace(/\s+$/, "");
});

var out = parts.join("\n\n");
fs.writeFileSync(OUTPUT, out + "\n", "utf8");

console.log("Built " + OUTPUT + " from " + ORDER.length + " source file(s).");
