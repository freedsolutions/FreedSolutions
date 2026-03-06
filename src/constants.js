import { useState, useRef, useEffect, useCallback } from "react";
import { createPortal } from "react-dom";

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
  { value: "Cambria, Georgia, serif", label: "Cambria" },
  { value: '"Courier New", Courier, monospace', label: "Courier New" },
  { value: "Arial, sans-serif", label: "Arial" },
  { value: '"Trebuchet MS", sans-serif', label: "Trebuchet MS" }
];

var DEFAULT_FONT = '"Helvetica Neue", Helvetica, Arial, sans-serif';

// Canvas layout tokens — rendering geometry
var CANVAS = {
  // Content area
  pad: 80,
  innerPad: 20,

  // Line heights (multipliers of font size)
  headingLH: 1.22,
  headingBlankLH: 0.5,
  bodyLH: 1.4,
  bodyBlankLH: 0.6,
  cardLineSpacing: 6,
  cardBlankLH: 0.5,

  // Cards
  cardGap: 20,
  cardPadV: 20,
  cardTextPad: 40,
  cardMinH: 80,
  cardExtraH: 10,
  cardRadius: 16,
  cardFirstLineY: 38,
  cardCheckRadius: 22,
  cardCheckOffsetY: -14,

  // Screenshot
  ssRadius: 12,
  ssMinH: 60,
  ssBottomPad: 20,
  ssFloorExpandHeading: 300,
  ssFloorExpandNoHeading: 180,
  ssFloorNormalHeading: 420,
  ssFloorNormalNoHeading: 200,

  // Footer
  footerBadgeW: 220,
  footerBadgeRadius: 12,
  footerTextY: 31,
  footerPicOffsetY: -8,
  footerStrokeWidth: 3,

  // Accent bar
  accentBarW: 50,
  accentBarH: 3,
  accentBarOffset: 10,

  // Spacing offsets after heading
  cardGapAfterHeadingExpand: 20,
  cardGapAfterHeading: 45,
  cardGapNoHeadingExpand: 30,
  cardGapNoHeading: 60,
  bodyGapAfterHeadingExpand: 40,
  bodyGapAfterHeading: 100,
  bodyGapNoHeadingExpand: 30,
  bodyGapNoHeading: 60,
};

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

var GEO_SHAPES = [
  { id: "solid",   label: "Solid" },
  { id: "lines",   label: "Lines" },
  { id: "bokeh",   label: "Bokeh" },
  { id: "waves",   label: "Waves" },
  { id: "stripes", label: "Stripes" },
  { id: "hex",     label: "Hexagons" },
  { id: "dots",    label: "Dots" },
  { id: "crosshatch", label: "Crosshatch" },
  { id: "diamonds",   label: "Diamonds" }
];