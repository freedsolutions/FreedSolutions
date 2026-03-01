import { useState, useRef, useEffect, useCallback } from "react";

// ---------------------------------------
// Canvas Constants
// ---------------------------------------

var W = 800;
var H = 1000;
var MARGIN = 44;
var BORDER_RADIUS = 24;
var BORDER_WIDTH = 2.5;
var GREEN = "#22c55e";
var FOOTER_PIC_SIZE = 84;
var FOOTER_BADGE_H = 48;
var MAX_SLIDES = 10;

// System-safe font options for typography controls
var FONT_OPTIONS = [
  { value: '"Helvetica Neue", Helvetica, Arial, sans-serif', label: "Helvetica Neue" },
  { value: "Georgia, serif", label: "Georgia" },
  { value: '"Courier New", Courier, monospace', label: "Courier New" },
  { value: "Arial, sans-serif", label: "Arial" },
  { value: '"Trebuchet MS", sans-serif', label: "Trebuchet MS" }
];

var DEFAULT_FONT = '"Helvetica Neue", Helvetica, Arial, sans-serif';

// Compose a valid ctx.font string: "italic bold 24px FontFamily"
// weight can be boolean true ("bold"), false (omit), or a string like "600", "700", "900", "bold"
function composeFont(family, size, weight, italic) {
  var parts = [];
  if (italic) parts.push("italic");
  if (weight === true) parts.push("bold");
  else if (weight && weight !== "normal" && weight !== false) parts.push(weight);
  parts.push(size + "px");
  parts.push(family || DEFAULT_FONT);
  return parts.join(" ");
}