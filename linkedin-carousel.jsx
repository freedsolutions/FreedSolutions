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
  { id: "hex",     label: "Hexagons" }
];

// ===================================================
// Layout Tokens — design system constants
// ===================================================

// --- Spacing scale ---
// Every gap, margin, and padding should use one of these values.
var SPACE = { 0: 0, 1: 2, 2: 4, 3: 6, 4: 8, 5: 10, 6: 12, 7: 16, 8: 24, 9: 48 };

// --- Border radius scale ---
var RADIUS = { sm: 4, md: 6, lg: 8, xl: 10, xxl: 12, pill: 20 };

// --- Z-index layers ---
var Z = { dropdown: 60, modal: 9999 };

// --- Component sizes ---
var SIZE = {
  swatchBtn: 18,
  swatch: 20,
  colorInput: 24,
  stepper: 28,
  stepperInput: 30,
  slideBtn: 35,
  toggleSm: 32,
  toggleMd: 44,
  removeBadge: 20,
  uploadFrame: 88,
  uploadBtn: 24,
  uploadBgWidth: 107,
  leftPane: 220,
  rightPaneMax: 480,
  pagePadH: 48,
  pagePadV: 28,
  columnGap: 48,
  pickerWidth: 200,
  dialogSm: 320,
  dialogMd: 360,
};

// --- UI surface colors (dark to light) ---
var SURFACE = {
  page: "#000000",
  inputDeep: "#0e0e1a",
  uploadBg: "#0f0f1a",
  panelDeep: "#10101a",
  uploadBtn: "#111119",
  panel: "#1a1a30",
  canvasBorder: "#222",
  input: "#28283e",
  pipeSep: "#2a2a3e",
  divider: "#2a2a40",
  uploadBorder: "#343447",
  panelBorder: "#3a3a50",
  border: "#444",
  muted: "#555",
  dimmed: "#666",
  secondary: "#777",
  tertiary: "#888",
  subtle: "#999",
  inactive: "#aaa",
  label: "#bbb",
  text: "#ccc",
  body: "#e0e0e0",
  white: "#fff",
};

// --- Semantic colors ---
var CLR = {
  primary: "#6366f1",
  primaryLight: "#a5b4fc",
  danger: "#f87171",
  dangerBorder: "#f8717133",
  error: "#ef4444",
  errorLight: "#fca5a5",
  errorBg: "#3a1a1a",
  errorBorder: "#7f1d1d",
  activeOverlay: "rgba(165,180,252,0.25)",
  activeOverlay2: "rgba(165,180,252,0.2)",
  dragTarget: "rgba(99,102,241,0.10)",
  activeSlide: "rgba(34,197,94,0.15)",
  removeBadgeBg: "rgba(100,100,100,0.7)",
  modalOverlay: "rgba(0,0,0,0.5)",
  shadow: "0 8px 24px rgba(0,0,0,0.6)",
  shadowLg: "0 8px 32px rgba(0,0,0,0.6)",
};

// --- Style helpers ---
// Compose common inline style objects from tokens.

function panelBtn(overrides) {
  var base = {
    padding: SPACE[3] + "px " + SPACE[6] + "px",
    borderRadius: RADIUS.md,
    border: "1px solid " + SURFACE.border,
    background: SURFACE.input,
    color: SURFACE.text,
    cursor: "pointer",
    fontSize: 11,
    fontWeight: 700,
  };
  return overrides ? Object.assign({}, base, overrides) : base;
}

function toggleBtn(isOn, overrides) {
  var base = {
    minWidth: SIZE.toggleMd,
    padding: "3px " + SPACE[6] + "px",
    borderRadius: RADIUS.pill,
    border: "none",
    background: isOn ? GREEN : SURFACE.muted,
    color: SURFACE.white,
    cursor: "pointer",
    fontSize: 11,
    fontWeight: 600,
  };
  return overrides ? Object.assign({}, base, overrides) : base;
}

function uploadFrameStyle(overrides) {
  var base = {
    minHeight: SIZE.uploadFrame,
    background: SURFACE.uploadBg,
    border: "1px solid " + SURFACE.uploadBorder,
    borderRadius: RADIUS.lg,
    padding: SPACE[2] + "px " + SPACE[4] + "px",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    boxSizing: "border-box",
    overflow: "hidden",
  };
  return overrides ? Object.assign({}, base, overrides) : base;
}

function uploadBtnStyle(hasFile) {
  return {
    width: "100%",
    height: SIZE.uploadBtn,
    borderRadius: 5,
    border: "1px solid " + (hasFile ? GREEN : SURFACE.border),
    background: SURFACE.uploadBtn,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    cursor: "pointer",
    gap: SPACE[4] * 2,
  };
}

function dividerStyle() {
  return { borderTop: "1px solid " + SURFACE.divider, marginTop: SPACE[6], marginBottom: SPACE[6] };
}

function dialogOverlay() {
  return {
    position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
    background: CLR.modalOverlay,
    display: "flex", alignItems: "center", justifyContent: "center",
    zIndex: Z.modal,
  };
}

function dialogBox(maxWidth) {
  return {
    background: SURFACE.panel,
    border: "1px solid " + SURFACE.border,
    borderRadius: RADIUS.xl,
    padding: SPACE[8] + "px",
    maxWidth: maxWidth || SIZE.dialogSm,
    boxShadow: CLR.shadowLg,
  };
}

function dialogBtn(isPrimary) {
  return {
    padding: SPACE[3] + "px " + SPACE[7] + "px",
    borderRadius: RADIUS.md,
    border: isPrimary ? "none" : "1px solid " + SURFACE.border,
    background: isPrimary ? CLR.primary : SURFACE.input,
    color: isPrimary ? SURFACE.white : SURFACE.subtle,
    cursor: "pointer",
    fontSize: 12,
    fontWeight: 600,
  };
}

// ---------------------------------------
// hexToRgba
// ---------------------------------------

function hexToRgba(hex, opacity) {
  if (!hex || typeof hex !== "string") return "rgba(255,255,255," + ((opacity || 0) / 100) + ")";
  if (hex.indexOf("rgba") === 0 || hex.indexOf("rgb") === 0) return hex;
  if (hex.charAt(0) !== "#" || hex.length < 7) return hex;
  var r = parseInt(hex.slice(1, 3), 16);
  var g = parseInt(hex.slice(3, 5), 16);
  var b = parseInt(hex.slice(5, 7), 16);
  if (isNaN(r) || isNaN(g) || isNaN(b)) return "rgba(255,255,255," + ((opacity || 0) / 100) + ")";
  return "rgba(" + r + "," + g + "," + b + "," + ((opacity != null ? opacity : 100) / 100) + ")";
}

// ---------------------------------------
// Background renderers
// ---------------------------------------

function drawSolidBg(ctx, color) {
  ctx.fillStyle = color;
  ctx.fillRect(0, 0, W, H);
}

// --- Shape-specific drawing functions ---
// All share signature: (ctx, lcR, lcG, lcB, opScale)

function drawGeoLines(ctx, lcR, lcG, lcB, opScale) {
  var spheres = [
    { x: -30, y: 220, r: 170, a: 0.10 },
    { x: -10, y: 800, r: 150, a: 0.08 },
    { x: 740, y: 130, r: 110, a: 0.06 },
    { x: 700, y: 830, r: 130, a: 0.07 },
  ];
  for (var si = 0; si < spheres.length; si++) {
    var s = spheres[si];
    ctx.fillStyle = "rgba(" + lcR + "," + lcG + "," + lcB + "," + (s.a * opScale) + ")";
    ctx.beginPath();
    ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = "rgba(" + lcR + "," + lcG + "," + lcB + "," + (s.a * 0.6 * opScale) + ")";
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
    ctx.stroke();
  }
  ctx.strokeStyle = "rgba(" + lcR + "," + lcG + "," + lcB + "," + (0.06 * opScale) + ")";
  ctx.lineWidth = 0.7;
  var lines = [
    [0, 50, 800, 380], [50, 0, 750, 550], [150, 0, 800, 480],
    [300, 0, 800, 350], [450, 0, 800, 200], [550, 0, 800, 120],
    [0, 150, 650, 1000], [0, 350, 500, 1000], [0, 500, 400, 1000],
    [0, 650, 350, 1000], [100, 0, 550, 1000], [250, 0, 700, 1000],
    [400, 0, 800, 800], [0, 100, 800, 650], [0, 750, 250, 1000],
    [600, 0, 800, 300], [0, 200, 300, 1000], [500, 0, 150, 700],
    [700, 0, 350, 1000], [0, 400, 700, 1000], [200, 0, 0, 400],
    [800, 200, 400, 1000], [800, 400, 500, 1000], [800, 50, 200, 700],
    [650, 0, 0, 600], [0, 600, 600, 1000], [350, 0, 800, 650],
    [800, 600, 550, 1000], [0, 900, 150, 1000], [750, 0, 800, 100],
  ];
  for (var li = 0; li < lines.length; li++) {
    ctx.beginPath();
    ctx.moveTo(lines[li][0], lines[li][1]);
    ctx.lineTo(lines[li][2], lines[li][3]);
    ctx.stroke();
  }
}

function drawGeoBokeh(ctx, lcR, lcG, lcB, opScale) {
  // Hand-placed translucent circles — organic scatter, varying size and opacity
  var orbs = [
    { x: 90,  y: 80,   r: 65,  a: 0.06 },
    { x: 680, y: 60,   r: 45,  a: 0.05 },
    { x: 350, y: 180,  r: 95,  a: 0.04 },
    { x: 750, y: 280,  r: 80,  a: 0.06 },
    { x: 60,  y: 420,  r: 110, a: 0.05 },
    { x: 520, y: 370,  r: 35,  a: 0.08 },
    { x: 200, y: 550,  r: 70,  a: 0.05 },
    { x: 700, y: 520,  r: 55,  a: 0.07 },
    { x: 420, y: 620,  r: 120, a: 0.04 },
    { x: 130, y: 740,  r: 50,  a: 0.06 },
    { x: 600, y: 760,  r: 85,  a: 0.05 },
    { x: 330, y: 870,  r: 40,  a: 0.07 },
    { x: 760, y: 900,  r: 70,  a: 0.05 },
    { x: 50,  y: 940,  r: 90,  a: 0.04 },
    { x: 480, y: 140,  r: 30,  a: 0.09 },
    { x: 260, y: 320,  r: 50,  a: 0.06 },
  ];
  for (var i = 0; i < orbs.length; i++) {
    var o = orbs[i];
    // Soft filled circle
    ctx.fillStyle = "rgba(" + lcR + "," + lcG + "," + lcB + "," + (o.a * opScale) + ")";
    ctx.beginPath();
    ctx.arc(o.x, o.y, o.r, 0, Math.PI * 2);
    ctx.fill();
    // Subtle rim
    ctx.strokeStyle = "rgba(" + lcR + "," + lcG + "," + lcB + "," + (o.a * 0.5 * opScale) + ")";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.arc(o.x, o.y, o.r, 0, Math.PI * 2);
    ctx.stroke();
  }
}

function drawGeoWaves(ctx, lcR, lcG, lcB, opScale) {
  // Flowing curves that sweep across the canvas — topographic/organic feel
  var curves = [
    { y: 80,   amp: 30,  freq: 1.2, phase: 0,    a: 0.10 },
    { y: 200,  amp: 45,  freq: 0.8, phase: 1.5,  a: 0.08 },
    { y: 340,  amp: 25,  freq: 1.5, phase: 0.8,  a: 0.11 },
    { y: 460,  amp: 55,  freq: 0.6, phase: 2.2,  a: 0.07 },
    { y: 580,  amp: 35,  freq: 1.1, phase: 0.4,  a: 0.10 },
    { y: 720,  amp: 40,  freq: 0.9, phase: 3.0,  a: 0.08 },
    { y: 850,  amp: 50,  freq: 0.7, phase: 1.8,  a: 0.09 },
    { y: 960,  amp: 20,  freq: 1.4, phase: 0.6,  a: 0.07 },
  ];
  ctx.lineWidth = 1.2;
  for (var i = 0; i < curves.length; i++) {
    var c = curves[i];
    // Every other pair: fill between this curve and the next curve
    if (i % 2 === 0 && i + 1 < curves.length) {
      var n = curves[i + 1];
      ctx.fillStyle = "rgba(" + lcR + "," + lcG + "," + lcB + "," + (c.a * 0.35 * opScale) + ")";
      ctx.beginPath();
      // Trace top wave left-to-right
      ctx.moveTo(-10, c.y + Math.sin(c.phase) * c.amp);
      for (var fx = 0; fx <= W + 10; fx += 4) {
        var ft = (fx / W) * Math.PI * 2 * c.freq + c.phase;
        ctx.lineTo(fx, c.y + Math.sin(ft) * c.amp);
      }
      // Trace bottom wave right-to-left
      for (var bx = W + 10; bx >= -10; bx -= 4) {
        var bt = (bx / W) * Math.PI * 2 * n.freq + n.phase;
        ctx.lineTo(bx, n.y + Math.sin(bt) * n.amp);
      }
      ctx.closePath();
      ctx.fill();
    }
    // Stroke the wave line
    ctx.strokeStyle = "rgba(" + lcR + "," + lcG + "," + lcB + "," + (c.a * opScale) + ")";
    ctx.beginPath();
    ctx.moveTo(-10, c.y + Math.sin(c.phase) * c.amp);
    for (var x = 0; x <= W + 10; x += 4) {
      var t = (x / W) * Math.PI * 2 * c.freq + c.phase;
      ctx.lineTo(x, c.y + Math.sin(t) * c.amp);
    }
    ctx.stroke();
  }
}

function drawGeoStripes(ctx, lcR, lcG, lcB, opScale) {
  ctx.strokeStyle = "rgba(" + lcR + "," + lcG + "," + lcB + "," + (0.07 * opScale) + ")";
  ctx.lineWidth = 1.0;
  for (var d = -1000; d < 1600; d += 50) {
    ctx.beginPath();
    ctx.moveTo(d, 0);
    ctx.lineTo(d - H, H);
    ctx.stroke();
  }
}

function drawGeoHex(ctx, lcR, lcG, lcB, opScale) {
  var side = 55;
  var colStep = side * 1.5;
  var rowStep = Math.sqrt(3) * side;
  ctx.strokeStyle = "rgba(" + lcR + "," + lcG + "," + lcB + "," + (0.09 * opScale) + ")";
  ctx.lineWidth = 1.0;
  ctx.beginPath();
  for (var col = -1; col * colStep < W + side * 2; col++) {
    for (var row = -1; row * rowStep < H + side * 2; row++) {
      var cx = col * colStep;
      var cy = row * rowStep + (col % 2 !== 0 ? rowStep / 2 : 0);
      for (var a = 0; a < 6; a++) {
        var angle = Math.PI / 3 * a;
        var px = cx + side * Math.cos(angle);
        var py = cy + side * Math.sin(angle);
        if (a === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      }
      ctx.closePath();
    }
  }
  ctx.stroke();
}

// --- Dispatcher ---

function drawGeoBg(ctx, baseColor, lineColor, geoOpacity, geoShape) {
  var opScale = (geoOpacity != null ? geoOpacity : 100) / 100;
  if (baseColor) {
    ctx.fillStyle = baseColor;
    ctx.fillRect(0, 0, W, H);
  }
  var lc = lineColor || "#a0a0af";
  var lcR = 160, lcG = 160, lcB = 175;
  if (lc.charAt(0) === "#" && lc.length >= 7) {
    var pr = parseInt(lc.slice(1,3), 16);
    var pg = parseInt(lc.slice(3,5), 16);
    var pb = parseInt(lc.slice(5,7), 16);
    if (!isNaN(pr)) lcR = pr;
    if (!isNaN(pg)) lcG = pg;
    if (!isNaN(pb)) lcB = pb;
  }
  var shape = geoShape || "lines";
  if (shape === "bokeh") drawGeoBokeh(ctx, lcR, lcG, lcB, opScale);
  else if (shape === "waves") drawGeoWaves(ctx, lcR, lcG, lcB, opScale);
  else if (shape === "stripes") drawGeoStripes(ctx, lcR, lcG, lcB, opScale);
  else if (shape === "hex") drawGeoHex(ctx, lcR, lcG, lcB, opScale);
  else drawGeoLines(ctx, lcR, lcG, lcB, opScale);
}

function drawCustomBg(ctx, img) {
  if (!img.width || !img.height) return;
  var imgRatio = img.width / img.height;
  var canvasRatio = W / H;
  var dw, dh;
  if (imgRatio > canvasRatio) {
    dh = H; dw = dh * imgRatio;
  } else {
    dw = W; dh = dw / imgRatio;
  }
  var dx = (W - dw) / 2;
  var dy = (H - dh) / 2;
  ctx.drawImage(img, dx, dy, dw, dh);
  ctx.fillStyle = "rgba(0,0,0,0.70)";
  ctx.fillRect(0, 0, W, H);
}

function renderBg(ctx, bgType, solidColor, customImg, geoLines, geoEnabled, geoOpacity, geoShape) {
  if (bgType === "custom" && customImg) {
    drawCustomBg(ctx, customImg);
  } else {
    drawSolidBg(ctx, solidColor);
    if (geoEnabled) {
      drawGeoBg(ctx, null, geoLines, geoOpacity, geoShape);
    }
  }
}

// ---------------------------------------
// Text helpers
// ---------------------------------------

function wrapText(ctx, text, maxWidth, fontSize, fontWeight, fontFamily, fontItalic) {
  fontWeight = fontWeight || "bold";
  ctx.font = composeFont(fontFamily || DEFAULT_FONT, fontSize, fontWeight, !!fontItalic);
  var words = text.split(" ");
  var lines = [];
  var line = "";
  for (var i = 0; i < words.length; i++) {
    var test = line ? line + " " + words[i] : words[i];
    if (ctx.measureText(test).width > maxWidth && line) {
      lines.push(line);
      line = words[i];
    } else {
      line = test;
    }
  }
  if (line) lines.push(line);
  return lines;
}

function extractAccentMarkers(text) {
  var markers = [];
  var re = /\*\*(.+?)\*\*/g;
  var m;
  var offset = 0;
  while ((m = re.exec(text)) !== null) {
    var cleanStart = m.index - offset;
    offset += 4;
    markers.push({ start: cleanStart, end: cleanStart + m[1].length });
  }
  var cleanText = text.replace(/\*\*(.+?)\*\*/g, "$1");
  return { cleanText: cleanText, markers: markers };
}

function renderLineWithAccents(ctx, line, x, y, fontSize, baseWeight, baseColor, accentColor, markers, lineOffset, fontFamily, fontItalic) {
  var family = fontFamily || DEFAULT_FONT;
  if (!markers || markers.length === 0 || accentColor === "transparent") {
    ctx.font = composeFont(family, fontSize, baseWeight, !!fontItalic);
    ctx.fillStyle = baseColor;
    ctx.fillText(line, x, y);
    return;
  }
  var lineEnd = lineOffset + line.length;
  var hits = [];
  for (var mi = 0; mi < markers.length; mi++) {
    var mk = markers[mi];
    if (mk.end <= lineOffset || mk.start >= lineEnd) continue;
    var s = Math.max(mk.start, lineOffset) - lineOffset;
    var e = Math.min(mk.end, lineEnd) - lineOffset;
    hits.push({ start: s, end: e });
  }
  if (hits.length === 0) {
    ctx.font = composeFont(family, fontSize, baseWeight, !!fontItalic);
    ctx.fillStyle = baseColor;
    ctx.fillText(line, x, y);
    return;
  }
  hits.sort(function(a, b) { return a.start - b.start; });
  var segments = [];
  var pos = 0;
  for (var hi = 0; hi < hits.length; hi++) {
    if (hits[hi].start > pos) {
      segments.push({ text: line.substring(pos, hits[hi].start), isAccent: false });
    }
    segments.push({ text: line.substring(hits[hi].start, hits[hi].end), isAccent: true });
    pos = hits[hi].end;
  }
  if (pos < line.length) segments.push({ text: line.substring(pos), isAccent: false });
  var xPos = x;
  for (var si = 0; si < segments.length; si++) {
    var seg = segments[si];
    if (seg.isAccent) {
      ctx.font = composeFont(family, fontSize, "900", !!fontItalic);
      ctx.fillStyle = accentColor;
    } else {
      ctx.font = composeFont(family, fontSize, baseWeight, !!fontItalic);
      ctx.fillStyle = baseColor;
    }
    ctx.fillText(seg.text, xPos, y);
    xPos += ctx.measureText(seg.text).width;
  }
}

// ---------------------------------------
// Overlays: footer, corners, border frame
// ---------------------------------------

function drawCenteredFooter(ctx, profileImg, name, borderBottom, footerBg, footerText, textSize, opacity, fontFamily, fontBold, fontItalic) {
  var prevAlpha = ctx.globalAlpha;
  ctx.globalAlpha = (opacity != null ? opacity : 100) / 100;
  var badgeH = FOOTER_BADGE_H;
  var badgeW = CANVAS.footerBadgeW;
  var badgeX = (W - badgeW) / 2;
  var badgeY = borderBottom - badgeH / 2;

  ctx.fillStyle = footerBg || "#ffffff";
  ctx.beginPath();
  ctx.roundRect(badgeX, badgeY, badgeW, badgeH, CANVAS.footerBadgeRadius);
  ctx.fill();

  ctx.fillStyle = footerText || "#1a1a2e";
  var footerWeight = fontBold !== false ? "bold" : "normal";
  ctx.font = composeFont(fontFamily || DEFAULT_FONT, textSize || 20, footerWeight, !!fontItalic);
  var tw = ctx.measureText(name).width;
  ctx.fillText(name, (W - tw) / 2, badgeY + CANVAS.footerTextY);

  if (profileImg) {
    var picSize = FOOTER_PIC_SIZE;
    var picX = W / 2;
    var picY = badgeY + badgeH + picSize / 2 + CANVAS.footerPicOffsetY;
    ctx.save();
    ctx.beginPath();
    ctx.arc(picX, picY, picSize / 2, 0, Math.PI * 2);
    ctx.clip();
    ctx.drawImage(profileImg, picX - picSize / 2, picY - picSize / 2, picSize, picSize);
    ctx.restore();
    ctx.strokeStyle = "rgba(255,255,255,0.5)";
    ctx.lineWidth = CANVAS.footerStrokeWidth;
    ctx.beginPath();
    ctx.arc(picX, picY, picSize / 2, 0, Math.PI * 2);
    ctx.stroke();
  }
  ctx.globalAlpha = prevAlpha;
}

function drawTopCorner(ctx, text, color, opacity, size, fontFamily, fontBold, fontItalic) {
  var weight = fontBold !== false ? "700" : "normal";
  ctx.font = composeFont(fontFamily || DEFAULT_FONT, size || 13, weight, !!fontItalic);
  ctx.fillStyle = hexToRgba(color || "#ffffff", opacity != null ? opacity : 40);
  ctx.fillText(text, MARGIN, MARGIN + (size || 13));
}

function drawBottomCorner(ctx, text, color, opacity, size, fontFamily, fontBold, fontItalic) {
  var weight = fontBold ? "700" : "600";
  ctx.font = composeFont(fontFamily || DEFAULT_FONT, size || 16, weight, !!fontItalic);
  ctx.fillStyle = hexToRgba(color || "#ffffff", opacity != null ? opacity : 35);
  ctx.fillText(text, MARGIN, H - MARGIN + 4);
}

function drawBorderFrame(ctx, top, bottom, hasFooter, strokeColor) {
  var left = MARGIN;
  var right = W - MARGIN;
  var r = BORDER_RADIUS;
  ctx.strokeStyle = strokeColor || "rgba(255,255,255,0.25)";
  ctx.lineWidth = BORDER_WIDTH;

  if (hasFooter) {
    var badgeW = CANVAS.footerBadgeW;
    var gapLeft = (W - badgeW) / 2;
    var gapRight = (W + badgeW) / 2;
    ctx.beginPath();
    ctx.moveTo(gapLeft, bottom);
    ctx.lineTo(left + r, bottom);
    ctx.arcTo(left, bottom, left, bottom - r, r);
    ctx.lineTo(left, top + r);
    ctx.arcTo(left, top, left + r, top, r);
    ctx.lineTo(right - r, top);
    ctx.arcTo(right, top, right, top + r, r);
    ctx.lineTo(right, bottom - r);
    ctx.arcTo(right, bottom, right - r, bottom, r);
    ctx.lineTo(gapRight, bottom);
    ctx.stroke();
  } else {
    ctx.beginPath();
    ctx.roundRect(left, top, right - left, bottom - top, r);
    ctx.stroke();
  }
}

// ---------------------------------------
// Screenshot renderer
// ---------------------------------------

function drawScreenshot(ctx, screenshot, x, y, w, h, scale, edgeToEdge) {
  var radius = edgeToEdge ? 0 : CANVAS.ssRadius;
  if (!screenshot) {
    ctx.strokeStyle = "rgba(255,255,255,0.1)";
    ctx.lineWidth = 1;
    ctx.setLineDash([6, 6]);
    ctx.beginPath();
    ctx.roundRect(x, y, w, h, radius);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = "rgba(255,255,255,0.15)";
    ctx.font = '500 16px "Helvetica Neue", Helvetica, Arial, sans-serif';
    var phText = "Upload screenshot";
    var phW = ctx.measureText(phText).width;
    ctx.fillText(phText, x + (w - phW) / 2, y + h / 2 + 6);
    return;
  }
  var s = scale || 1;
  var imgRatio = screenshot.width / screenshot.height;
  var boxRatio = w / h;
  var dw, dh;
  if (imgRatio > boxRatio) {
    dw = w; dh = dw / imgRatio;
  } else {
    dh = h; dw = dh * imgRatio;
  }
  dw *= s;
  dh *= s;
  var dx = x + (w - dw) / 2;
  var dy = y + (h - dh) / 2;

  ctx.save();
  ctx.beginPath();
  ctx.roundRect(x, y, w, h, radius);
  ctx.clip();
  ctx.drawImage(screenshot, dx, dy, dw, dh);
  ctx.restore();
}

// ---------------------------------------
// Unified slide content renderer
// ---------------------------------------

function renderSlideContent(ctx, slide, screenshot, colors, sizes, scale, frameTop, frameBottom) {
  var pad = CANVAS.pad;
  var innerPad = CANVAS.innerPad;
  var topY = Math.max(pad, (frameTop || 0) + innerPad);
  var maxW = W - pad * 2;

  // Resolve per-element typography with backward-compat defaults
  var titleFamily = slide.titleFontFamily || DEFAULT_FONT;
  var titleBold = slide.titleBold !== false;
  var titleItalic = !!slide.titleItalic;
  var bodyFamily = slide.bodyFontFamily || DEFAULT_FONT;
  var bodyBold = !!slide.bodyBold;
  var bodyItalic = !!slide.bodyItalic;
  var cardFamily = slide.cardFontFamily || DEFAULT_FONT;
  var cardBold = !!slide.cardBold;
  var cardItalic = !!slide.cardItalic;

  var titleWeight = titleBold ? "bold" : "normal";
  var bodyWeight = bodyBold ? "bold" : "600";
  var cardWeight = cardBold ? "bold" : "600";

  var expand = !!slide.expandScreenshot;

  var ty = topY;
  if (slide.showHeading !== false) {
    ctx.font = composeFont(titleFamily, sizes.heading, titleWeight, titleItalic);
    ty = topY + sizes.heading * CANVAS.headingLH;
    var headingRawLines = (slide.title || "").split("\n");
    for (var hli = 0; hli < headingRawLines.length; hli++) {
      var hRaw = headingRawLines[hli];
      if (hRaw.trim() === "") { ty += sizes.heading * CANVAS.headingBlankLH; continue; }
      var headingParsed = extractAccentMarkers(hRaw);
      var titleLines = wrapText(ctx, headingParsed.cleanText, maxW, sizes.heading, titleWeight, titleFamily, titleItalic);
      var hOffset = 0;
      for (var i = 0; i < titleLines.length; i++) {
        renderLineWithAccents(ctx, titleLines[i], pad, ty, sizes.heading, titleWeight, slide.titleColor || colors.text, colors.accent, headingParsed.markers, hOffset, titleFamily, titleItalic);
        hOffset += titleLines[i].length + 1;
        ty += sizes.heading * CANVAS.headingLH;
      }
    }

    if (slide.showAccentBar !== false && (!slide.showCards || !slide.cards || slide.cards.length === 0)) {
      var accentBarOffset = expand ? 0 : CANVAS.accentBarOffset;
      ctx.fillStyle = colors.decoration;
      ctx.fillRect(pad, ty + accentBarOffset, CANVAS.accentBarW, CANVAS.accentBarH);
    }
  }

  if (slide.showCards && slide.cards && slide.cards.length > 0) {
    var showChecks = slide.showCardChecks !== false;
    var cardStartY = (slide.showHeading !== false) ? ty + (expand ? CANVAS.cardGapAfterHeadingExpand : CANVAS.cardGapAfterHeading) : ty + (expand ? CANVAS.cardGapNoHeadingExpand : CANVAS.cardGapNoHeading);
    var cardPadV = CANVAS.cardPadV;
    var gap = CANVAS.cardGap;
    var textPadding = CANVAS.cardTextPad;
    var cardContentW = maxW - CANVAS.cardTextPad;
    // Pre-compute wrapped lines per card (handling newlines)
    var cardsLineData = [];
    for (var cpi = 0; cpi < slide.cards.length; cpi++) {
      var cardRaw = slide.cards[cpi] || "";
      if (cardRaw.replace(/\*\*(.+?)\*\*/g, "$1").trim() === "") {
        cardsLineData.push([]);
        continue;
      }
      var cardNlLines = cardRaw.split("\n");
      var allWrapped = [];
      for (var cnl = 0; cnl < cardNlLines.length; cnl++) {
        var nlLine = cardNlLines[cnl];
        if (nlLine.trim() === "") { allWrapped.push({ text: "", empty: true }); continue; }
        var nlParsed = extractAccentMarkers(nlLine);
        ctx.font = composeFont(cardFamily, sizes.cardText, cardWeight, cardItalic);
        var nlWrapped = wrapText(ctx, nlParsed.cleanText, cardContentW, sizes.cardText, cardWeight, cardFamily, cardItalic);
        var nlOffset = 0;
        for (var nw = 0; nw < nlWrapped.length; nw++) {
          allWrapped.push({ text: nlWrapped[nw], parsed: nlParsed, offset: nlOffset });
          nlOffset += nlWrapped[nw].length + 1;
        }
      }
      cardsLineData.push(allWrapped);
    }
    var cardHeights = [];
    for (var ch = 0; ch < cardsLineData.length; ch++) {
      var visibleLines = 0;
      var emptyLines = 0;
      for (var chl = 0; chl < cardsLineData[ch].length; chl++) {
        if (cardsLineData[ch][chl].empty) emptyLines++;
        else visibleLines++;
      }
      if (visibleLines === 0 && emptyLines === 0) { cardHeights.push(0); continue; }
      var textH = visibleLines * (sizes.cardText + CANVAS.cardLineSpacing) + emptyLines * (sizes.cardText * CANVAS.cardBlankLH);
      cardHeights.push(Math.max(CANVAS.cardMinH, textH + cardPadV * 2 + CANVAS.cardExtraH));
    }
    var runningY = cardStartY;
    for (var ci = 0; ci < cardsLineData.length; ci++) {
      if (cardHeights[ci] === 0) continue;
      var cy = runningY;
      var cardH = cardHeights[ci];
      var cardX = pad - 10 + textPadding;
      var cardW = maxW - textPadding * 2 + 20;
      ctx.fillStyle = slide.cardBgColor || colors.cardBg;
      ctx.beginPath();
      ctx.roundRect(cardX, cy, cardW, cardH, CANVAS.cardRadius);
      ctx.fill();
      if (showChecks) {
        ctx.fillStyle = colors.decoration;
        ctx.beginPath();
        ctx.arc(pad + textPadding + 18, cy + CANVAS.cardCheckOffsetY, CANVAS.cardCheckRadius, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = slide.cardBgColor || colors.cardBg;
        ctx.lineWidth = 3;
        ctx.lineCap = "round";
        ctx.lineJoin = "round";
        ctx.beginPath();
        ctx.moveTo(pad + textPadding + 8, cy + CANVAS.cardCheckOffsetY);
        ctx.lineTo(pad + textPadding + 16, cy + CANVAS.cardCheckOffsetY + 8);
        ctx.lineTo(pad + textPadding + 30, cy + CANVAS.cardCheckOffsetY - 8);
        ctx.stroke();
      }
      ctx.save();
      ctx.beginPath();
      ctx.roundRect(cardX, cy, cardW, cardH, CANVAS.cardRadius);
      ctx.clip();
      ctx.font = composeFont(cardFamily, sizes.cardText, cardWeight, cardItalic);
      var lineY = cy + CANVAS.cardFirstLineY;
      for (var cli = 0; cli < cardsLineData[ci].length; cli++) {
        var ld = cardsLineData[ci][cli];
        if (ld.empty) { lineY += sizes.cardText * CANVAS.cardBlankLH; continue; }
        renderLineWithAccents(ctx, ld.text, pad + textPadding + 20, lineY, sizes.cardText, cardWeight, slide.cardTextColor || colors.cardText, colors.accent, ld.parsed.markers, ld.offset, cardFamily, cardItalic);
        lineY += sizes.cardText + CANVAS.cardLineSpacing;
      }
      ctx.restore();
      runningY += cardH + gap;
    }
    ty = runningY;
  } else if (slide.body) {
    var bodyLines = (slide.body || "").split("\n");
    var bodyY = (slide.showHeading !== false) ? ty + (expand ? CANVAS.bodyGapAfterHeadingExpand : CANVAS.bodyGapAfterHeading) : ty + (expand ? CANVAS.bodyGapNoHeadingExpand : CANVAS.bodyGapNoHeading);
    for (var bli = 0; bli < bodyLines.length; bli++) {
      var rawLine = bodyLines[bli];
      if (rawLine.trim() === "" || rawLine.replace(/\*\*(.+?)\*\*/g, "$1").trim() === "") {
        bodyY += sizes.body * CANVAS.bodyBlankLH;
      } else {
        var lineParsed = extractAccentMarkers(rawLine);
        var wrapped = wrapText(ctx, lineParsed.cleanText, maxW, sizes.body, bodyWeight, bodyFamily, bodyItalic);
        var bOffset = 0;
        for (var wi = 0; wi < wrapped.length; wi++) {
          renderLineWithAccents(ctx, wrapped[wi], pad, bodyY, sizes.body, bodyWeight, slide.bodyColor || colors.accent, colors.accent, lineParsed.markers, bOffset, bodyFamily, bodyItalic);
          bOffset += wrapped[wi].length + 1;
          bodyY += sizes.body * CANVAS.bodyLH;
        }
      }
    }
    ty = bodyY + 10;
  }

  if (slide.showScreenshot || screenshot) {
    var bottomBound = frameBottom ? frameBottom - CANVAS.ssBottomPad : H - pad;
    var hasHeading = slide.showHeading !== false;
    var ssFloor = expand ? (hasHeading ? CANVAS.ssFloorExpandHeading : CANVAS.ssFloorExpandNoHeading) : (hasHeading ? CANVAS.ssFloorNormalHeading : CANVAS.ssFloorNormalNoHeading);
    var ssY = Math.max(ty + CANVAS.ssBottomPad, ssFloor);
    var ssX = expand ? 0 : pad;
    var ssW = expand ? W : maxW;
    var ssH = bottomBound - ssY;
    if (ssH > CANVAS.ssMinH) {
      drawScreenshot(ctx, screenshot || null, ssX, ssY, ssW, ssH, scale, expand);
    }
  }
}

// ---------------------------------------
// Top-level render orchestrator (pure function)
// ---------------------------------------

function renderSlideToCanvas(ctx, slideIndex, seriesSlides, slideAssets) {
  ctx.clearRect(0, 0, W, H);
  var slide = seriesSlides[slideIndex] || seriesSlides[0];

  var sizes = {
    heading: slide.headingSize || 48,
    body: slide.bodySize || 38,
    cardText: slide.cardTextSize || 22,
    topCorner: slide.topCornerSize || 13,
    bottomCorner: slide.bottomCornerSize || 16,
    brandName: slide.brandNameSize || 20,
  };

  // Resolve custom bg image
  var customImg = (slide.bgType === "custom" && slide.customBgImage) ? slide.customBgImage : null;

  renderBg(ctx, slide.bgType, slide.solidColor, customImg, slide.geoLines, slide.geoEnabled, slide.geoOpacity, slide.geoShape);

  // Build render colors from per-slide properties with hard fallbacks for backward-compat
  var renderColors = {
    heading: slide.titleColor || "#ffffff",
    body: slide.bodyColor || "#ffffff",
    text: slide.titleColor || "#ffffff",
    accent: slide.accentColor || "#22c55e",
    decoration: slide.decorationColor || "#22c55e",
    border: hexToRgba(slide.borderColor || "#ffffff", slide.borderOpacity != null ? slide.borderOpacity : 100),
    cardBg: slide.cardBgColor || "#ffffff",
    cardText: slide.cardTextColor || "#333333",
  };

  var topCornerOffset = (slide.showTopCorner && slide.topCornerText) ? sizes.topCorner * 2.2 : 0;
  var borderTop = MARGIN + topCornerOffset + 8;
  var borderBottom = slide.showBrandName ? H - MARGIN - FOOTER_PIC_SIZE + 8 - FOOTER_BADGE_H / 2 : H - MARGIN - 16;

  if (slide.showTopCorner && slide.topCornerText) {
    drawTopCorner(ctx, slide.topCornerText, slide.topCornerColor, slide.topCornerOpacity, sizes.topCorner, slide.topCornerFontFamily, slide.topCornerBold, slide.topCornerItalic);
  }

  var asset = slideAssets[slideIndex] || { image: null, name: null, scale: 1 };
  renderSlideContent(ctx, slide, asset.image, renderColors, sizes, asset.scale, borderTop, borderBottom);

  if (slide.frameEnabled) {
    drawBorderFrame(ctx, borderTop, borderBottom, slide.showBrandName, renderColors.border);
  }

  if (slide.showBrandName) {
    drawCenteredFooter(ctx, slide.profileImg, slide.brandNameText, borderBottom, slide.footerBg, slide.brandNameColor, sizes.brandName, 100, slide.brandNameFontFamily, slide.brandNameBold, slide.brandNameItalic);
  }

  if (slide.showBottomCorner && slide.bottomCornerText) {
    drawBottomCorner(ctx, slide.bottomCornerText, slide.bottomCornerColor, slide.bottomCornerOpacity, sizes.bottomCorner, slide.bottomCornerFontFamily, slide.bottomCornerBold, slide.bottomCornerItalic);
  }
}

// ===================================================
// Default Slide Factory
// ===================================================

function makeDefaultSlide(title, body) {
  return {
    title: title || "New Slide",
    showHeading: true,
    showAccentBar: true,
    body: body || "Your text here...",
    titleColor: "#ffffff",
    titleFontFamily: DEFAULT_FONT,
    titleBold: true,
    titleItalic: false,
    bodyColor: "#a5b4fc",
    bodyFontFamily: DEFAULT_FONT,
    bodyBold: false,
    bodyItalic: false,
    showCards: false,
    showCardChecks: true,
    cards: ["Card 1"],
    cardTextColor: "#333333",
    cardFontFamily: DEFAULT_FONT,
    cardBold: false,
    cardItalic: false,
    cardBgColor: "#ffffff",
    expandScreenshot: false,
    showScreenshot: false,
    showBrandName: false,
    brandNameText: "Brand Name",
    brandNameColor: "#1a1a2e",
    brandNameFontFamily: DEFAULT_FONT,
    brandNameBold: true,
    brandNameItalic: false,
    showTopCorner: false,
    topCornerText: "LABEL",
    topCornerColor: "#ffffff",
    topCornerFontFamily: DEFAULT_FONT,
    topCornerBold: true,
    topCornerItalic: false,
    topCornerOpacity: 40,
    showBottomCorner: false,
    bottomCornerText: "01 / ",
    bottomCornerColor: "#ffffff",
    bottomCornerFontFamily: DEFAULT_FONT,
    bottomCornerBold: false,
    bottomCornerItalic: false,
    bottomCornerOpacity: 35,
    solidColor: "#1e1e2e",
    bgType: "solid",
    customBgImage: null,
    customBgName: null,
    geoEnabled: true,
    geoLines: "#a0a0af",
    geoOpacity: 100,
    geoShape: "lines",
    frameEnabled: true,
    accentColor: "#a5b4fc",
    decorationColor: "#a5b4fc",
    borderColor: "#ffffff",
    borderOpacity: 100,
    footerBg: "#ffffff",
    profileImg: null,
    profilePicName: null,
    headingSize: 48,
    bodySize: 38,
    cardTextSize: 22,
    topCornerSize: 13,
    bottomCornerSize: 16,
    brandNameSize: 20
  };
}

// ===================================================
// Undo/Redo History Manager
// ===================================================

var UNDO_MAX = 20;

function createUndoManager() {
  var undoStack = [];
  var redoStack = [];

  return {
    pushSnapshot: function(snapshot) {
      undoStack.push(snapshot);
      if (undoStack.length > UNDO_MAX) {
        undoStack.shift();
      }
      // Any new action clears the redo stack
      redoStack.length = 0;
    },

    undo: function(currentSnapshot) {
      if (undoStack.length === 0) return null;
      redoStack.push(currentSnapshot);
      return undoStack.pop();
    },

    redo: function(currentSnapshot) {
      if (redoStack.length === 0) return null;
      undoStack.push(currentSnapshot);
      return redoStack.pop();
    },

    canUndo: function() { return undoStack.length > 0; },
    canRedo: function() { return redoStack.length > 0; }
  };
}

// ===================================================
// PDF Builder (pure utility functions)
// ===================================================

function sanitizePrefix(raw) {
  var trimmed = (raw || "").replace(/^\s+|\s+$/g, "");
  if (!trimmed) return "linkedin-slide";
  return trimmed.replace(/[^a-zA-Z0-9_\-]/g, "_");
}

function decodeBase64ToBinary(b64) {
  if (!b64 || typeof b64 !== "string") return "";
  return atob(b64);
}

function extractJpegBinaryFromDataUrl(dataUrl) {
  if (!dataUrl || typeof dataUrl !== "string") return "";
  if (dataUrl.indexOf("data:image/jpeg;base64,") !== 0) return "";
  var marker = "base64,";
  var idx = dataUrl.indexOf(marker);
  if (idx === -1) return "";
  return decodeBase64ToBinary(dataUrl.substring(idx + marker.length));
}

function buildPdfFromJpegs(jpegPages, pageW, pageH) {
  if (!jpegPages || jpegPages.length === 0) {
    throw new Error("No JPEG pages to encode");
  }
  var numPages = jpegPages.length;
  var pieces = [];
  var pos = 0;
  var offsets = {};

  var writeStr = function(s) {
    pieces.push(s);
    pos += s.length;
  };

  var markObj = function(n) {
    offsets[n] = pos;
  };

  var padOffset = function(n) {
    var s = n.toString();
    while (s.length < 10) s = "0" + s;
    return s;
  };

  // Header
  writeStr("%PDF-1.4\n");

  // Object numbering:
  // 1 = Catalog, 2 = Pages
  // Per page i: 3+i*3 = Page, 4+i*3 = Content stream, 5+i*3 = Image XObject
  var totalObjs = 2 + numPages * 3;

  // 1: Catalog
  markObj(1);
  writeStr("1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n");

  // 2: Pages
  markObj(2);
  var kids = "";
  for (var k = 0; k < numPages; k++) {
    if (k > 0) kids += " ";
    kids += (3 + k * 3) + " 0 R";
  }
  writeStr("2 0 obj\n<< /Type /Pages /Kids [" + kids + "] /Count " + numPages + " >>\nendobj\n");

  // Each page
  for (var i = 0; i < numPages; i++) {
    var pgObj = 3 + i * 3;
    var ctObj = 4 + i * 3;
    var imObj = 5 + i * 3;
    var jpeg = jpegPages[i];
    if (!jpeg || jpeg.length === 0) {
      throw new Error("Invalid JPEG page payload");
    }
    var cs = "q " + pageW + " 0 0 " + pageH + " 0 0 cm /Im0 Do Q";

    markObj(pgObj);
    writeStr(pgObj + " 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 " + pageW + " " + pageH + "] /Contents " + ctObj + " 0 R /Resources << /XObject << /Im0 " + imObj + " 0 R >> >> >>\nendobj\n");

    markObj(ctObj);
    writeStr(ctObj + " 0 obj\n<< /Length " + cs.length + " >>\nstream\n" + cs + "\nendstream\nendobj\n");

    markObj(imObj);
    var imHeader = imObj + " 0 obj\n<< /Type /XObject /Subtype /Image /Width " + pageW + " /Height " + pageH + " /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length " + jpeg.length + " >>\nstream\n";
    writeStr(imHeader);
    writeStr(jpeg);
    writeStr("\nendstream\nendobj\n");
  }

  // xref table
  var xrefPos = pos;
  writeStr("xref\n0 " + (totalObjs + 1) + "\n");
  writeStr("0000000000 65535 f\r\n");
  for (var n = 1; n <= totalObjs; n++) {
    writeStr(padOffset(offsets[n]) + " 00000 n\r\n");
  }

  writeStr("trailer\n<< /Size " + (totalObjs + 1) + " /Root 1 0 R >>\nstartxref\n" + xrefPos + "\n%%EOF\n");

  // Convert binary string pieces to Uint8Array
  var totalLen = 0;
  for (var t = 0; t < pieces.length; t++) {
    totalLen += pieces[t].length;
  }
  var buf = new Uint8Array(totalLen);
  var off = 0;
  for (var t2 = 0; t2 < pieces.length; t2++) {
    var s = pieces[t2];
    for (var c = 0; c < s.length; c++) {
      buf[off++] = s.charCodeAt(c) & 0xFF;
    }
  }

  return new Blob([buf], { type: "application/pdf" });
}

// ===================================================
// Inline Color Picker Component
// ===================================================

function drawShapeThumbnail(ctx, shapeId, w, h) {
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = SURFACE.inputDeep;
  ctx.fillRect(0, 0, w, h);
  var c = SURFACE.dimmed;
  if (shapeId === "solid") {
    ctx.fillStyle = "rgba(102,102,102,0.35)";
    ctx.fillRect(2, 2, w - 4, h - 4);
    ctx.strokeStyle = "rgba(102,102,102,0.5)";
    ctx.lineWidth = 0.6;
    ctx.strokeRect(2, 2, w - 4, h - 4);
  } else if (shapeId === "lines") {
    // Simplified spheres + lines
    ctx.fillStyle = "rgba(102,102,102,0.3)";
    ctx.beginPath(); ctx.arc(2, 8, 6, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.arc(26, 22, 5, 0, Math.PI * 2); ctx.fill();
    ctx.strokeStyle = "rgba(102,102,102,0.4)";
    ctx.lineWidth = 0.5;
    var tl = [[0, 2, 28, 18], [4, 0, 24, 28], [0, 14, 28, 6], [10, 0, 0, 20], [18, 0, 28, 22]];
    for (var i = 0; i < tl.length; i++) {
      ctx.beginPath(); ctx.moveTo(tl[i][0], tl[i][1]); ctx.lineTo(tl[i][2], tl[i][3]); ctx.stroke();
    }
  } else if (shapeId === "bokeh") {
    // Scattered translucent circles at varying sizes
    var orbs = [
      { x: 5, y: 6, r: 4, a: 0.3 }, { x: 20, y: 4, r: 3, a: 0.25 },
      { x: 12, y: 16, r: 6, a: 0.2 }, { x: 24, y: 18, r: 4.5, a: 0.25 },
      { x: 3, y: 24, r: 5, a: 0.2 }, { x: 17, y: 25, r: 3, a: 0.35 },
      { x: 8, y: 12, r: 2.5, a: 0.3 },
    ];
    for (var oi = 0; oi < orbs.length; oi++) {
      var ob = orbs[oi];
      ctx.fillStyle = "rgba(102,102,102," + ob.a + ")";
      ctx.beginPath(); ctx.arc(ob.x, ob.y, ob.r, 0, Math.PI * 2); ctx.fill();
    }
  } else if (shapeId === "waves") {
    ctx.strokeStyle = "rgba(102,102,102,0.4)";
    ctx.lineWidth = 0.5;
    var waveYs = [5, 11, 17, 23];
    for (var wi = 0; wi < waveYs.length; wi++) {
      ctx.beginPath();
      for (var wx = 0; wx <= w; wx += 2) {
        var wy = waveYs[wi] + Math.sin(wx * 0.3 + wi * 1.5) * 2.5;
        if (wx === 0) ctx.moveTo(wx, wy); else ctx.lineTo(wx, wy);
      }
      ctx.stroke();
    }
  } else if (shapeId === "stripes") {
    ctx.strokeStyle = "rgba(102,102,102,0.4)";
    ctx.lineWidth = 0.6;
    for (var d = -28; d < 56; d += 6) {
      ctx.beginPath(); ctx.moveTo(d, 0); ctx.lineTo(d - h, h); ctx.stroke();
    }
  } else if (shapeId === "hex") {
    var s = 8;
    var colSt = s * 1.5;
    var rowSt = Math.sqrt(3) * s;
    ctx.strokeStyle = "rgba(102,102,102,0.4)";
    ctx.lineWidth = 0.4;
    ctx.beginPath();
    for (var col = 0; col * colSt < w + s; col++) {
      for (var row = 0; row * rowSt < h + s; row++) {
        var cx = col * colSt;
        var cy = row * rowSt + (col % 2 !== 0 ? rowSt / 2 : 0);
        for (var a = 0; a < 6; a++) {
          var angle = Math.PI / 3 * a;
          var px = cx + s * Math.cos(angle);
          var py = cy + s * Math.sin(angle);
          if (a === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
        }
        ctx.closePath();
      }
    }
    ctx.stroke();
  }
}

function ColorPickerInline(props) {
  var pickerKey = props.pickerKey;
  var value = props.value || "#ffffff";
  var onChange = props.onChange;
  var openPicker = props.openPicker;
  var setOpenPicker = props.setOpenPicker;
  var disabled = props.disabled || false;
  var opacityVal = props.opacityVal;
  var onOpacityChange = props.onOpacityChange;
  // Typography props (optional)
  var fontFamily = props.fontFamily;
  var onFontFamilyChange = props.onFontFamilyChange;
  var bold = props.bold;
  var onBoldChange = props.onBoldChange;
  var italic = props.italic;
  var onItalicChange = props.onItalicChange;
  // Layer shape props (optional)
  var geoShape = props.geoShape;
  var onShapeChange = props.onShapeChange;
  // Dual-color mode props (optional — used by merged Layer swatch)
  var fillValue = props.fillValue;
  var onFillChange = props.onFillChange;
  var dualColor = props.dualColor || false;

  // Customizable swatches + transparent option (used by Frame/Accent pickers)
  var swatches = props.swatches || INLINE_SWATCHES;
  var allowTransparent = props.allowTransparent || false;

  var hasTypography = !!onFontFamilyChange;
  var isTransparentValue = value === "transparent";
  var isOpen = openPicker === pickerKey && !disabled;
  var isSolidShape = dualColor && (geoShape || "lines") === "solid";

  var swatchBtnRef = useRef(null);
  var thumbCanvasRefs = useRef({});

  // Draw shape thumbnails when picker opens
  useEffect(function() {
    if (!isOpen || !onShapeChange) return;
    // Small delay to let portal mount
    var raf = requestAnimationFrame(function() {
      GEO_SHAPES.forEach(function(shape) {
        var canvas = thumbCanvasRefs.current[shape.id];
        if (!canvas) return;
        var tctx = canvas.getContext("2d");
        drawShapeThumbnail(tctx, shape.id, 28, 28);
      });
    });
    return function() { cancelAnimationFrame(raf); };
  }, [isOpen, onShapeChange]);

  // Helper: render a color grid section (swatches + hex input)
  function renderColorSection(label, colorVal, colorOnChange) {
    var isColorTransparent = colorVal === "transparent";
    return (
      <div>
        <span style={{ fontSize: 10, color: SURFACE.dimmed, display: "block", marginBottom: SPACE[3] }}>{label}</span>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(8, 1fr)", gap: SPACE[2], marginBottom: SPACE[4] }}>
          {swatches.map(function(c) {
            return (
              <button key={c} onClick={function() { colorOnChange(c); }}
                style={{
                  width: SIZE.swatch, height: SIZE.swatch, borderRadius: RADIUS.sm,
                  border: colorVal === c ? "2px solid " + SURFACE.white : "1px solid " + SURFACE.border,
                  background: c, cursor: "pointer", padding: 0,
                  boxShadow: colorVal === c ? "0 0 0 1px " + CLR.primary : "none"
                }}
              />
            );
          })}
        </div>
        <div style={{ display: "flex", gap: SPACE[3], alignItems: "center" }}>
          <input type="color"
            value={!isColorTransparent && colorVal && colorVal.charAt(0) === "#" ? colorVal : "#a0a0af"}
            onChange={function(e) { colorOnChange(e.target.value); }}
            style={{ width: SIZE.colorInput, height: SIZE.colorInput, border: "1px solid " + SURFACE.border, borderRadius: RADIUS.sm, cursor: "pointer", background: "none", padding: 0 }}
          />
          <input value={colorVal || ""}
            onChange={function(e) { colorOnChange(e.target.value); }}
            style={{ flex: 1, padding: SPACE[2] + "px " + SPACE[3] + "px", borderRadius: RADIUS.sm, border: "1px solid " + SURFACE.border, background: SURFACE.inputDeep, color: SURFACE.label, fontSize: 11, fontFamily: "monospace" }}
          />
        </div>
      </div>
    );
  }

  // Compute portal position from swatch button
  var portalStyle = null;
  if (isOpen && swatchBtnRef.current) {
    var rect = swatchBtnRef.current.getBoundingClientRect();
    portalStyle = {
      position: "fixed",
      top: rect.bottom + SPACE[2],
      left: Math.max(4, rect.right - SIZE.pickerWidth),
      zIndex: Z.dropdown,
      background: SURFACE.panel,
      border: "1px solid " + SURFACE.border,
      borderRadius: RADIUS.xl,
      padding: SPACE[5],
      width: SIZE.pickerWidth,
      boxShadow: CLR.shadow
    };
  }

  var popout = isOpen && portalStyle ? (
    <div data-picker-portal={pickerKey} style={portalStyle}>
      {hasTypography && (
        <div style={{ marginBottom: SPACE[4], paddingBottom: SPACE[4], borderBottom: "1px solid " + SURFACE.panelBorder }}>
          <select value={fontFamily || DEFAULT_FONT} onChange={function(e) { onFontFamilyChange(e.target.value); }}
            style={{ width: "100%", padding: SPACE[2] + "px " + SPACE[3] + "px", borderRadius: RADIUS.sm, border: "1px solid " + SURFACE.border, background: SURFACE.inputDeep, color: SURFACE.label, fontSize: 11, marginBottom: SPACE[3], cursor: "pointer" }}>
            {FONT_OPTIONS.map(function(f) {
              return <option key={f.value} value={f.value} style={{ fontFamily: f.value }}>{f.label}</option>;
            })}
          </select>
          <div style={{ display: "flex", gap: SPACE[2] }}>
            <button onClick={function() { onBoldChange(!bold); }}
              title="Bold"
              style={{ flex: 1, padding: "3px 0", borderRadius: RADIUS.sm, border: "1px solid " + SURFACE.border, background: bold ? CLR.activeOverlay : SURFACE.input, color: bold ? CLR.primaryLight : SURFACE.dimmed, cursor: "pointer", fontSize: 12, fontWeight: 900, lineHeight: "16px" }}>B</button>
            <button onClick={function() { onItalicChange(!italic); }}
              title="Italic"
              style={{ flex: 1, padding: "3px 0", borderRadius: RADIUS.sm, border: "1px solid " + SURFACE.border, background: italic ? CLR.activeOverlay : SURFACE.input, color: italic ? CLR.primaryLight : SURFACE.dimmed, cursor: "pointer", fontSize: 12, fontStyle: "italic", fontWeight: 600, lineHeight: "16px" }}>I</button>
          </div>
        </div>
      )}
      {dualColor ? (
        <>
          {renderColorSection("Fill", fillValue || "#1e1e2e", onFillChange)}
          {!isSolidShape && (
            <>
              <div style={{ borderTop: "1px solid " + SURFACE.panelBorder, marginTop: SPACE[4], paddingTop: SPACE[4] }}>
                {renderColorSection("Pattern", value, onChange)}
              </div>
              {onOpacityChange && (
                <div style={{ display: "flex", alignItems: "center", gap: SPACE[3], marginTop: SPACE[4] }}>
                  <span style={{ fontSize: 10, color: SURFACE.dimmed, whiteSpace: "nowrap" }}>Opacity</span>
                  <input type="range" min={0} max={100}
                    value={opacityVal != null ? opacityVal : 100}
                    onChange={function(e) { onOpacityChange(Number(e.target.value)); }}
                    style={{ flex: 1 }}
                  />
                  <span style={{ fontSize: 10, color: SURFACE.muted, width: SIZE.stepper, textAlign: "right" }}>
                    {(opacityVal != null ? opacityVal : 100) + "%"}
                  </span>
                </div>
              )}
            </>
          )}
        </>
      ) : (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(8, 1fr)", gap: SPACE[2], marginBottom: SPACE[4] }}>
            {allowTransparent && (
              <button onClick={function() { onChange("transparent"); }}
                title="None (transparent)"
                style={{
                  width: SIZE.swatch, height: SIZE.swatch, borderRadius: RADIUS.sm,
                  border: isTransparentValue ? "2px solid " + SURFACE.white : "1px solid " + SURFACE.border,
                  background: "linear-gradient(45deg, #ccc 25%, transparent 25%), linear-gradient(-45deg, #ccc 25%, transparent 25%), linear-gradient(45deg, transparent 75%, #ccc 75%), linear-gradient(-45deg, transparent 75%, #ccc 75%)",
                  backgroundSize: "8px 8px",
                  backgroundPosition: "0 0, 0 4px, 4px -4px, -4px 0",
                  cursor: "pointer", padding: 0,
                  boxShadow: isTransparentValue ? "0 0 0 1px " + CLR.primary : "none"
                }}
              />
            )}
            {swatches.map(function(c) {
              return (
                <button key={c} onClick={function() { onChange(c); }}
                  style={{
                    width: SIZE.swatch, height: SIZE.swatch, borderRadius: RADIUS.sm,
                    border: value === c ? "2px solid " + SURFACE.white : "1px solid " + SURFACE.border,
                    background: c, cursor: "pointer", padding: 0,
                    boxShadow: value === c ? "0 0 0 1px " + CLR.primary : "none"
                  }}
                />
              );
            })}
          </div>
          <div style={{ display: "flex", gap: SPACE[3], alignItems: "center", opacity: isTransparentValue ? 0.4 : 1 }}>
            <input type="color"
              value={!isTransparentValue && value && value.charAt(0) === "#" ? value : "#a0a0af"}
              onChange={function(e) { onChange(e.target.value); }}
              disabled={isTransparentValue}
              style={{ width: SIZE.colorInput, height: SIZE.colorInput, border: "1px solid " + SURFACE.border, borderRadius: RADIUS.sm, cursor: isTransparentValue ? "default" : "pointer", background: "none", padding: 0 }}
            />
            <input value={isTransparentValue ? "none" : value}
              onChange={function(e) { if (!isTransparentValue) onChange(e.target.value); }}
              disabled={isTransparentValue}
              style={{ flex: 1, padding: SPACE[2] + "px " + SPACE[3] + "px", borderRadius: RADIUS.sm, border: "1px solid " + SURFACE.border, background: SURFACE.inputDeep, color: SURFACE.label, fontSize: 11, fontFamily: "monospace" }}
            />
          </div>
          {onOpacityChange && (
            <div style={{ display: "flex", alignItems: "center", gap: SPACE[3], marginTop: SPACE[4], paddingTop: SPACE[4], borderTop: "1px solid " + SURFACE.panelBorder }}>
              <span style={{ fontSize: 10, color: SURFACE.dimmed, whiteSpace: "nowrap" }}>Opacity</span>
              <input type="range" min={0} max={100}
                value={opacityVal != null ? opacityVal : 100}
                onChange={function(e) { onOpacityChange(Number(e.target.value)); }}
                style={{ flex: 1 }}
              />
              <span style={{ fontSize: 10, color: SURFACE.muted, width: SIZE.stepper, textAlign: "right" }}>
                {(opacityVal != null ? opacityVal : 100) + "%"}
              </span>
            </div>
          )}
        </>
      )}
      {onShapeChange && (
        <div style={{ marginTop: SPACE[4], paddingTop: SPACE[4], borderTop: "1px solid " + SURFACE.panelBorder }}>
          <span style={{ fontSize: 10, color: SURFACE.dimmed, display: "block", marginBottom: SPACE[3] }}>Shape</span>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: SPACE[2] }}>
            {GEO_SHAPES.map(function(shape) {
              var isActive = (geoShape || "lines") === shape.id;
              return (
                <button key={shape.id}
                  onClick={function() { onShapeChange(shape.id); }}
                  title={shape.label}
                  style={{
                    width: "100%", aspectRatio: "1", borderRadius: RADIUS.sm,
                    border: isActive ? "2px solid " + CLR.primaryLight : "1px solid " + SURFACE.border,
                    background: isActive ? CLR.activeOverlay : "transparent",
                    cursor: "pointer", padding: 1, display: "flex", alignItems: "center", justifyContent: "center"
                  }}>
                  <canvas
                    ref={function(el) { thumbCanvasRefs.current[shape.id] = el; }}
                    width={28} height={28}
                    style={{ width: 28, height: 28, borderRadius: 2, display: "block" }}
                  />
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  ) : null;

  // Swatch button background
  var swatchBtnBg, swatchBtnBgImage;
  if (dualColor) {
    if (isSolidShape) {
      swatchBtnBg = fillValue || "#1e1e2e";
      swatchBtnBgImage = "none";
    } else {
      swatchBtnBg = "transparent";
      swatchBtnBgImage = "linear-gradient(135deg, " + (fillValue || "#1e1e2e") + " 50%, " + (value || "#a0a0af") + " 50%)";
    }
  } else if (isTransparentValue) {
    swatchBtnBg = "transparent";
    swatchBtnBgImage = "linear-gradient(45deg, #ccc 25%, transparent 25%), linear-gradient(-45deg, #ccc 25%, transparent 25%), linear-gradient(45deg, transparent 75%, #ccc 75%), linear-gradient(-45deg, transparent 75%, #ccc 75%)";
  } else {
    swatchBtnBg = value;
    swatchBtnBgImage = "none";
  }

  return (
    <div style={{ position: "relative" }} data-picker={pickerKey}>
      <button
        ref={swatchBtnRef}
        onClick={function(e) {
          if (disabled) return;
          e.stopPropagation();
          setOpenPicker(isOpen ? null : pickerKey);
        }}
        style={{
          width: SIZE.swatchBtn, height: SIZE.swatchBtn, borderRadius: RADIUS.sm,
          border: isOpen ? "2px solid " + CLR.primary : "1px solid " + SURFACE.border,
          backgroundColor: swatchBtnBg,
          backgroundImage: swatchBtnBgImage,
          backgroundSize: isTransparentValue && !dualColor ? "8px 8px" : "auto",
          backgroundPosition: isTransparentValue && !dualColor ? "0 0, 0 4px, 4px -4px, -4px 0" : "auto",
          cursor: disabled ? "default" : "pointer",
          padding: 0, display: "block"
        }}
      />
      {popout && createPortal(popout, document.body)}
    </div>
  );
}

// ===================================================
// SizeControl Component
// ===================================================
// Renders a font-size stepper with optional color picker, opacity, and typography controls.
// Props: text, sizeKey, min, max, extra, sizes, setSize, colorVal, colorSet,
//        colorPickerKey, openPicker, setOpenPicker, opacityVal, opacitySet,
//        fontFamily, fontFamilySet, boldVal, boldSet, italicVal, italicSet

function SizeControl(props) {
  var text = props.text;
  var sizeKey = props.sizeKey;
  var min = props.min || 10;
  var max = props.max || 60;
  var extra = props.extra;
  var sizes = props.sizes;
  var setSize = props.setSize;
  var colorVal = props.colorVal;
  var colorSet = props.colorSet;
  var colorPickerKey = props.colorPickerKey;
  var openPicker = props.openPicker;
  var setOpenPicker = props.setOpenPicker;
  var opacityVal = props.opacityVal;
  var opacitySet = props.opacitySet;
  // Typography props (optional)
  var fontFamily = props.fontFamily;
  var fontFamilySet = props.fontFamilySet;
  var boldVal = props.boldVal;
  var boldSet = props.boldSet;
  var italicVal = props.italicVal;
  var italicSet = props.italicSet;
  var swatchLabel = props.swatchLabel;

  var hasTypography = !!fontFamilySet;

  if (!sizeKey) return <label style={labelStyle}>{text}{extra ? " " : ""}{extra}</label>;

  var cpOpen = colorPickerKey && openPicker === colorPickerKey;
  var scSwatchRef = useRef(null);

  // Compute portal position from swatch button
  var scPortalStyle = null;
  if (cpOpen && scSwatchRef.current) {
    var scRect = scSwatchRef.current.getBoundingClientRect();
    scPortalStyle = {
      position: "fixed",
      top: scRect.bottom + SPACE[2],
      left: Math.max(4, scRect.right - SIZE.pickerWidth),
      zIndex: Z.dropdown,
      background: SURFACE.panel,
      border: "1px solid " + SURFACE.border,
      borderRadius: RADIUS.xl,
      padding: SPACE[5],
      width: SIZE.pickerWidth,
      boxShadow: CLR.shadow
    };
  }

  var scPopout = cpOpen && scPortalStyle ? (
    <div data-picker-portal={colorPickerKey} style={scPortalStyle}>
      {hasTypography && (
        <div style={{ marginBottom: SPACE[4], paddingBottom: SPACE[4], borderBottom: "1px solid " + SURFACE.panelBorder }}>
          <select value={fontFamily || DEFAULT_FONT} onChange={function(e) { fontFamilySet(e.target.value); }}
            style={{ width: "100%", padding: SPACE[2] + "px " + SPACE[3] + "px", borderRadius: RADIUS.sm, border: "1px solid " + SURFACE.border, background: SURFACE.inputDeep, color: SURFACE.label, fontSize: 11, marginBottom: SPACE[3], cursor: "pointer" }}>
            {FONT_OPTIONS.map(function(f) {
              return <option key={f.value} value={f.value} style={{ fontFamily: f.value }}>{f.label}</option>;
            })}
          </select>
          <div style={{ display: "flex", gap: SPACE[2] }}>
            <button onClick={function() { boldSet(!boldVal); }}
              title="Bold"
              style={{ flex: 1, padding: "3px 0", borderRadius: RADIUS.sm, border: "1px solid " + SURFACE.border, background: boldVal ? CLR.activeOverlay : SURFACE.input, color: boldVal ? CLR.primaryLight : SURFACE.dimmed, cursor: "pointer", fontSize: 12, fontWeight: 900, lineHeight: "16px" }}>B</button>
            <button onClick={function() { italicSet(!italicVal); }}
              title="Italic"
              style={{ flex: 1, padding: "3px 0", borderRadius: RADIUS.sm, border: "1px solid " + SURFACE.border, background: italicVal ? CLR.activeOverlay : SURFACE.input, color: italicVal ? CLR.primaryLight : SURFACE.dimmed, cursor: "pointer", fontSize: 12, fontStyle: "italic", fontWeight: 600, lineHeight: "16px" }}>I</button>
          </div>
        </div>
      )}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(8, 1fr)", gap: SPACE[2], marginBottom: SPACE[4] }}>
        {INLINE_SWATCHES.map(function(c) {
          var active = colorVal === c;
          return (
            <button key={c} onClick={function() { colorSet(c); }}
              style={{ width: SIZE.swatch, height: SIZE.swatch, borderRadius: RADIUS.sm, border: active ? "2px solid " + SURFACE.white : "1px solid " + SURFACE.border, background: c, cursor: "pointer", padding: 0, boxShadow: active ? "0 0 0 1px " + CLR.primary : "none" }} />
          );
        })}
      </div>
      <div style={{ display: "flex", gap: SPACE[3], alignItems: "center" }}>
        <input type="color" value={colorVal && colorVal.charAt(0) === "#" ? colorVal : "#ffffff"} onChange={function(e) { colorSet(e.target.value); }}
          style={{ width: SIZE.colorInput, height: SIZE.colorInput, border: "1px solid " + SURFACE.border, borderRadius: RADIUS.sm, cursor: "pointer", background: "none", padding: 0 }} />
        <input value={colorVal || ""} onChange={function(e) { colorSet(e.target.value); }}
          style={{ flex: 1, padding: SPACE[2] + "px " + SPACE[3] + "px", borderRadius: RADIUS.sm, border: "1px solid " + SURFACE.border, background: SURFACE.inputDeep, color: SURFACE.label, fontSize: 11, fontFamily: "monospace" }} />
      </div>
      {opacitySet && (
        <div style={{ display: "flex", alignItems: "center", gap: SPACE[3], marginTop: SPACE[4], paddingTop: SPACE[4], borderTop: "1px solid " + SURFACE.panelBorder }}>
          <span style={{ fontSize: 10, color: SURFACE.dimmed, whiteSpace: "nowrap" }}>Opacity</span>
          <input type="range" min={0} max={100} value={opacityVal != null ? opacityVal : 100} onChange={function(e) { opacitySet(Number(e.target.value)); }}
            style={{ flex: 1 }} />
          <span style={{ fontSize: 10, color: SURFACE.muted, width: SIZE.stepper, textAlign: "right" }}>{(opacityVal != null ? opacityVal : 100) + "%"}</span>
        </div>
      )}
    </div>
  ) : null;

  return (
    <div style={{ display: "flex", alignItems: "center", marginBottom: text ? SPACE[3] : 0, gap: text ? 0 : SPACE[3] }}>
      {text && <span style={{ fontWeight: 600, fontSize: 13, color: SURFACE.label, letterSpacing: 0.5, flex: 1 }}>{text}{extra ? " " : ""}{extra}</span>}
      <div style={{ display: "flex", alignItems: "center", gap: SPACE[3] }}>
        {colorPickerKey && (
          <div style={{ position: "relative" }} data-picker={colorPickerKey}>
            <button ref={scSwatchRef} onClick={function(e) { e.stopPropagation(); setOpenPicker(cpOpen ? null : colorPickerKey); }}
              style={{ width: SIZE.swatchBtn, height: SIZE.swatchBtn, borderRadius: RADIUS.sm, border: cpOpen ? "2px solid " + CLR.primary : "1px solid " + SURFACE.border, background: colorVal || "#fff", cursor: "pointer", padding: 0, display: "block" }} />
            {scPopout && createPortal(scPopout, document.body)}
          </div>
        )}
        {swatchLabel && (
          <span style={{ fontSize: 11, color: SURFACE.secondary, fontWeight: 600, whiteSpace: "nowrap" }}>{swatchLabel}</span>
        )}
        <div style={{ display: "flex", alignItems: "center", gap: 0, background: SURFACE.input, borderRadius: RADIUS.sm, border: "1px solid " + SURFACE.border, height: SIZE.stepper, overflow: "hidden" }}>
          <button onClick={function() { if (sizes[sizeKey] > min) setSize(sizeKey, sizes[sizeKey] - 1); }}
            style={{ minWidth: SIZE.stepper, minHeight: SIZE.stepper, border: "none", background: "transparent", color: SURFACE.muted, cursor: "pointer", fontSize: 14, padding: 0, lineHeight: SIZE.stepper + "px" }}>{"\u2212"}</button>
          <input value={sizes[sizeKey]} onChange={function(e) { var v = parseInt(e.target.value, 10); if (!isNaN(v)) setSize(sizeKey, Math.max(min, Math.min(max, v))); }}
            style={{ width: SIZE.stepperInput, height: SIZE.stepper, border: "none", borderLeft: "1px solid " + SURFACE.border, borderRight: "1px solid " + SURFACE.border, background: "transparent", color: SURFACE.dimmed, fontSize: 11, fontFamily: "monospace", textAlign: "center", padding: 0, outline: "none" }} />
          <button onClick={function() { if (sizes[sizeKey] < max) setSize(sizeKey, sizes[sizeKey] + 1); }}
            style={{ minWidth: SIZE.stepper, minHeight: SIZE.stepper, border: "none", background: "transparent", color: SURFACE.muted, cursor: "pointer", fontSize: 14, padding: 0, lineHeight: SIZE.stepper + "px" }}>+</button>
        </div>
      </div>
    </div>
  );
}

// ===================================================
// SlideSelector Component
// ===================================================
// Renders numbered slide buttons with drag-to-reorder, remove overlay, and add/duplicate controls.
// Props: seriesSlides, activeSlide, setActiveSlide, dragFrom, setDragFrom,
//        dragOver, setDragOver, reorderSlide, addSlide, duplicateSlide, removeSlide

function SlideSelector(props) {
  var seriesSlides = props.seriesSlides;
  var activeSlide = props.activeSlide;
  var setActiveSlide = props.setActiveSlide;
  var dragFrom = props.dragFrom;
  var setDragFrom = props.setDragFrom;
  var dragOver = props.dragOver;
  var setDragOver = props.setDragOver;
  var reorderSlide = props.reorderSlide;
  var addSlide = props.addSlide;
  var duplicateSlide = props.duplicateSlide;
  var removeSlide = props.removeSlide;

  var canRemove = seriesSlides.length > 1;

  return (
    <div style={{ marginBottom: SPACE[5] }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: SPACE[5], paddingTop: SPACE[2], padding: "0 " + SPACE[5] + "px" }}>
        {seriesSlides.map(function(s, i) {
          var isActive = activeSlide === i;
          var isDragSource = dragFrom === i;
          var isDragTarget = dragOver === i && dragFrom !== i;
          var label = (i + 1).toString();
          return (
            <div key={i} style={{ position: "relative" }}>
              <button
                draggable
                onClick={function() { setActiveSlide(i); }}
                onDragStart={function(e) { setDragFrom(i); e.dataTransfer.effectAllowed = "move"; }}
                onDragOver={function(e) { e.preventDefault(); e.dataTransfer.dropEffect = "move"; setDragOver(i); }}
                onDragLeave={function() { if (dragOver === i) setDragOver(null); }}
                onDrop={function(e) { e.preventDefault(); if (dragFrom != null) { reorderSlide(dragFrom, i); } }}
                onDragEnd={function() { setDragFrom(null); setDragOver(null); }}
                style={{ width: "100%", aspectRatio: "1", borderRadius: RADIUS.md, border: isDragTarget ? "2px dashed " + CLR.primary : (isActive ? "2px solid " + GREEN : "2px solid " + SURFACE.muted), background: isDragTarget ? CLR.dragTarget : (isActive ? CLR.activeSlide : SURFACE.panel), color: isActive ? GREEN : SURFACE.inactive, cursor: isDragSource ? "grabbing" : "grab", fontSize: 13, fontWeight: 700, padding: 0, display: "flex", alignItems: "center", justifyContent: "center", opacity: isDragSource ? 0.4 : 1, transition: "opacity 0.15s, border 0.15s, background 0.15s" }}>
                {label}
              </button>
              {canRemove && (
                <button
                  onClick={function(e) { e.stopPropagation(); removeSlide(i); }}
                  onDragStart={function(e) { e.preventDefault(); e.stopPropagation(); }}
                  style={{ position: "absolute", top: -SPACE[3], right: -SPACE[3], width: SIZE.removeBadge, height: SIZE.removeBadge, borderRadius: RADIUS.lg, border: "none", background: CLR.removeBadgeBg, color: CLR.danger, cursor: "pointer", fontSize: 12, fontWeight: 700, padding: 0, display: "flex", alignItems: "center", justifyContent: "center", lineHeight: 1 }}>{"\u00d7"}</button>
              )}
            </div>
          );
        })}
        {seriesSlides.length < MAX_SLIDES && (
          <button onClick={addSlide}
            style={{ width: "100%", aspectRatio: "1", borderRadius: RADIUS.md, border: "2px dashed " + SURFACE.muted, background: SURFACE.panel, color: SURFACE.tertiary, cursor: "pointer", fontSize: 15, fontWeight: 700, padding: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>+</button>
        )}
      </div>
      <div style={{ display: "flex", justifyContent: "center", marginTop: SPACE[5] }}>
        <button onClick={duplicateSlide}
          disabled={seriesSlides.length >= MAX_SLIDES}
          style={panelBtn({ cursor: seriesSlides.length >= MAX_SLIDES ? "default" : "pointer", opacity: seriesSlides.length >= MAX_SLIDES ? 0.4 : 1 })}>
          Duplicate Slide
        </button>
      </div>
    </div>
  );
}

// ===================================================
// useSlideManagement Hook
// ===================================================
// Manages slide CRUD, reorder, duplicate, card management, and image uploads.
// Params: deps object { pushUndo, setConfirmDialog }
// Returns: { seriesSlides, setSeriesSlides, activeSlide, setActiveSlide,
//   slideAssets, setSlideAssets, getAsset, setAsset, setScale,
//   dragFrom, setDragFrom, dragOver, setDragOver,
//   profilePicInputRef, screenshotInputRef, customBgInputRef,
//   updateSlide, updateBgField, syncBgToAll, resetAllToDefault,
//   addSlide, duplicateSlide, removeSlide, reorderSlide,
//   updateSlideCard, addSlideCard, removeSlideCard,
//   handleCustomUpload, handleScreenshotUpload, handleProfilePicUpload,
//   removeProfilePic, removeCustomBg, removeScreenshot }

function useSlideManagement(deps) {
  var profilePicInputRef = useRef(null);
  var screenshotInputRef = useRef(null);
  var customBgInputRef = useRef(null);

  var [seriesSlides, setSeriesSlides] = useState([makeDefaultSlide("Heading", "Body text")]);
  var [activeSlide, setActiveSlide] = useState(0);
  var [slideAssets, setSlideAssets] = useState({});
  var [dragFrom, setDragFrom] = useState(null);
  var [dragOver, setDragOver] = useState(null);

  var getAsset = function(idx) {
    return slideAssets[idx] || { image: null, name: null, scale: 1 };
  };

  var setAsset = function(idx, patch) {
    setSlideAssets(function(prev) {
      var entry = prev[idx] || { image: null, name: null, scale: 1 };
      var next = Object.assign({}, prev);
      next[idx] = Object.assign({}, entry, patch);
      return next;
    });
  };

  var setScale = function(key, val) {
    setAsset(key, { scale: val });
  };

  // --- Image uploads ---

  var handleCustomUpload = function(e) {
    var file = e.target.files[0];
    if (!file) return;
    var fileName = file.name;
    var targetSlide = activeSlide;
    var reader = new FileReader();
    reader.onload = function(ev) {
      var img = new Image();
      img.onload = function() {
        setSeriesSlides(function(prev) {
          return prev.map(function(s, i) {
            if (i !== targetSlide) return s;
            return Object.assign({}, s, { customBgImage: img, customBgName: fileName, bgType: "custom" });
          });
        });
      };
      img.onerror = function() { console.warn("Image failed to load: " + fileName); };
      img.src = ev.target.result;
    };
    reader.readAsDataURL(file);
  };

  var handleScreenshotUpload = function(key, e) {
    var file = e.target.files[0];
    if (!file) return;
    var fileName = file.name;
    var reader = new FileReader();
    reader.onload = function(ev) {
      var img = new Image();
      img.onload = function() {
        setAsset(key, { name: fileName, image: img });
        // Auto-enable showScreenshot when image is uploaded
        setSeriesSlides(function(prev) {
          return prev.map(function(s, i) {
            if (i !== key) return s;
            if (s.showScreenshot) return s;
            return Object.assign({}, s, { showScreenshot: true });
          });
        });
      };
      img.onerror = function() { console.warn("Image failed to load: " + fileName); };
      img.src = ev.target.result;
    };
    reader.readAsDataURL(file);
  };

  var handleProfilePicUpload = function(e) {
    var file = e.target.files[0];
    if (!file) return;
    var fileName = file.name;
    var targetSlide = activeSlide;
    var reader = new FileReader();
    reader.onload = function(ev) {
      var img = new Image();
      img.onload = function() {
        setSeriesSlides(function(prev) {
          return prev.map(function(s, i) {
            if (i !== targetSlide) return s;
            return Object.assign({}, s, { profileImg: img, profilePicName: fileName });
          });
        });
      };
      img.onerror = function() { console.warn("Image failed to load: " + fileName); };
      img.src = ev.target.result;
    };
    reader.readAsDataURL(file);
  };

  var removeProfilePic = function() {
    if (profilePicInputRef.current) { profilePicInputRef.current.value = ""; }
    setSeriesSlides(function(prev) {
      return prev.map(function(s, i) {
        if (i !== activeSlide) return s;
        return Object.assign({}, s, { profileImg: null, profilePicName: null });
      });
    });
  };

  var removeCustomBg = function() {
    if (customBgInputRef.current) { customBgInputRef.current.value = ""; }
    setSeriesSlides(function(prev) {
      return prev.map(function(s, i) {
        if (i !== activeSlide) return s;
        return Object.assign({}, s, { customBgImage: null, customBgName: null, bgType: "solid" });
      });
    });
  };

  var removeScreenshot = function(key) {
    if (screenshotInputRef.current) { screenshotInputRef.current.value = ""; }
    setSlideAssets(function(prev) {
      var next = Object.assign({}, prev);
      delete next[key];
      return next;
    });
    setSeriesSlides(function(prev) {
      return prev.map(function(s, i) {
        if (i !== key) return s;
        if (!s.showScreenshot) return s;
        return Object.assign({}, s, { showScreenshot: false });
      });
    });
  };

  // --- Slide CRUD ---

  var updateSlide = function(idx, field, val, shouldSnapshot) {
    if (shouldSnapshot) deps.pushUndo();
    setSeriesSlides(function(prev) {
      return prev.map(function(s, i) {
        if (i !== idx) return s;
        var updated = Object.assign({}, s);
        updated[field] = val;
        return updated;
      });
    });
  };

  var updateBgField = function(field, value) {
    updateSlide(activeSlide, field, value);
  };

  var syncBgToAll = function() {
    deps.setConfirmDialog({
      message: "Apply Slide " + (activeSlide + 1) + "\u2019s visual settings to all slides? (Text content and screenshots are not affected.)",
      onConfirm: function() {
        deps.pushUndo();
        var src = seriesSlides[activeSlide];
        setSeriesSlides(function(prev) {
          return prev.map(function(s) {
            return Object.assign({}, s, {
              // Background
              solidColor: src.solidColor,
              bgType: src.bgType,
              customBgImage: src.customBgImage,
              customBgName: src.customBgName,
              geoEnabled: src.geoEnabled,
              geoLines: src.geoLines,
              geoOpacity: src.geoOpacity,
              geoShape: src.geoShape,
              // Frame
              frameEnabled: src.frameEnabled,
              accentColor: src.accentColor,
              decorationColor: src.decorationColor,
              borderColor: src.borderColor,
              borderOpacity: src.borderOpacity,
              // Profile
              profileImg: src.profileImg,
              profilePicName: src.profilePicName,
              footerBg: src.footerBg,
              // Toggles (not text content)
              showHeading: src.showHeading,
              showAccentBar: src.showAccentBar,
              showCards: src.showCards,
              showCardChecks: src.showCardChecks,
              showBrandName: src.showBrandName,
              showTopCorner: src.showTopCorner,
              showBottomCorner: src.showBottomCorner,
              // Font sizes
              headingSize: src.headingSize,
              bodySize: src.bodySize,
              cardTextSize: src.cardTextSize,
              topCornerSize: src.topCornerSize,
              bottomCornerSize: src.bottomCornerSize,
              brandNameSize: src.brandNameSize,
              // Title typography
              titleColor: src.titleColor,
              titleFontFamily: src.titleFontFamily,
              titleBold: src.titleBold,
              titleItalic: src.titleItalic,
              // Body typography
              bodyColor: src.bodyColor,
              bodyFontFamily: src.bodyFontFamily,
              bodyBold: src.bodyBold,
              bodyItalic: src.bodyItalic,
              // Card typography
              cardTextColor: src.cardTextColor,
              cardFontFamily: src.cardFontFamily,
              cardBold: src.cardBold,
              cardItalic: src.cardItalic,
              cardBgColor: src.cardBgColor,
              // Brand name typography
              brandNameColor: src.brandNameColor,
              brandNameFontFamily: src.brandNameFontFamily,
              brandNameBold: src.brandNameBold,
              brandNameItalic: src.brandNameItalic,
              // Top corner typography
              topCornerColor: src.topCornerColor,
              topCornerFontFamily: src.topCornerFontFamily,
              topCornerBold: src.topCornerBold,
              topCornerItalic: src.topCornerItalic,
              topCornerOpacity: src.topCornerOpacity,
              // Bottom corner typography
              bottomCornerColor: src.bottomCornerColor,
              bottomCornerFontFamily: src.bottomCornerFontFamily,
              bottomCornerBold: src.bottomCornerBold,
              bottomCornerItalic: src.bottomCornerItalic,
              bottomCornerOpacity: src.bottomCornerOpacity
            });
          });
        });
      }
    });
  };

  var resetAllToDefault = function() {
    deps.setConfirmDialog({
      message: "Reset ALL slides to defaults? This resets everything except text content.",
      onConfirm: function() {
        deps.pushUndo();
        setSeriesSlides(function(prev) {
          return prev.map(function() {
            return makeDefaultSlide();
          });
        });
        setSlideAssets(function() {
          return {};
        });
      }
    });
  };

  var addSlide = function() {
    setSeriesSlides(function(prev) {
      if (prev.length >= MAX_SLIDES) return prev;
      return prev.concat([makeDefaultSlide()]);
    });
  };

  var duplicateSlide = function() {
    if (seriesSlides.length >= MAX_SLIDES) return;
    deps.setConfirmDialog({
      message: "Duplicate Slide " + (activeSlide + 1) + "?",
      onConfirm: function() {
        deps.pushUndo();
        var insertIdx = activeSlide + 1;

        setSeriesSlides(function(prev) {
          if (prev.length >= MAX_SLIDES) return prev;
          var src = prev[activeSlide];
          if (!src) return prev;
          var copy = Object.assign({}, src, { cards: src.cards.slice() });
          var next = prev.slice();
          next.splice(insertIdx, 0, copy);
          return next;
        });

        setSlideAssets(function(prev) {
          var next = {};
          Object.keys(prev).forEach(function(k) {
            var ki = Number(k);
            if (ki >= insertIdx) {
              next[ki + 1] = prev[ki];
            } else {
              next[ki] = prev[ki];
            }
          });
          var srcAsset = prev[activeSlide];
          if (srcAsset) {
            next[insertIdx] = Object.assign({}, srcAsset);
          }
          return next;
        });

        setActiveSlide(insertIdx);
      }
    });
  };

  var removeSlide = function(idx) {
    if (seriesSlides.length <= 1) return;
    deps.setConfirmDialog({
      message: "Remove Slide " + (idx + 1) + "?",
      onConfirm: function() {
        deps.pushUndo();
        setSeriesSlides(function(prev) {
          if (prev.length <= 1) return prev;
          return prev.filter(function(_, i) { return i !== idx; });
        });
        setSlideAssets(function(prev) {
          var next = {};
          Object.keys(prev).forEach(function(k) {
            var ki = Number(k);
            if (ki < idx) next[ki] = prev[ki];
            else if (ki > idx) next[ki - 1] = prev[ki];
          });
          return next;
        });
        setActiveSlide(function(prev) {
          var newLen = seriesSlides.length - 1;
          if (prev >= newLen) return newLen - 1;
          if (prev === idx) return Math.max(0, idx - 1);
          if (prev > idx) return prev - 1;
          return prev;
        });
      }
    });
  };

  var resetSlide = function(idx) {
    deps.setConfirmDialog({
      message: "Reset Slide " + (idx + 1) + " to defaults?",
      onConfirm: function() {
        deps.pushUndo();
        setSeriesSlides(function(prev) {
          return prev.map(function(s, i) {
            if (i !== idx) return s;
            return makeDefaultSlide();
          });
        });
        setSlideAssets(function(prev) {
          var next = Object.assign({}, prev);
          delete next[idx];
          return next;
        });
      }
    });
  };

  var reorderSlide = function(fromIdx, toIdx) {
    if (fromIdx === toIdx || fromIdx == null || toIdx == null) return;
    var snapshotLen = seriesSlides.length;
    if (fromIdx < 0 || fromIdx >= snapshotLen || toIdx < 0 || toIdx >= snapshotLen) {
      setDragFrom(null);
      setDragOver(null);
      return;
    }
    deps.pushUndo();

    var buildIndexMap = function(len) {
      var map = {};
      for (var i = 0; i < len; i++) {
        var newPos;
        if (i === fromIdx) {
          newPos = toIdx;
        } else if (fromIdx < toIdx) {
          if (i > fromIdx && i <= toIdx) { newPos = i - 1; }
          else { newPos = i; }
        } else {
          if (i >= toIdx && i < fromIdx) { newPos = i + 1; }
          else { newPos = i; }
        }
        map[i] = newPos;
      }
      return map;
    };

    setSeriesSlides(function(prev) {
      if (fromIdx < 0 || fromIdx >= prev.length) return prev;
      if (toIdx < 0 || toIdx >= prev.length) return prev;
      var next = prev.slice();
      var moved = next.splice(fromIdx, 1)[0];
      next.splice(toIdx, 0, moved);
      return next;
    });

    var indexMap = buildIndexMap(snapshotLen);

    setSlideAssets(function(prev) {
      var next = {};
      Object.keys(prev).forEach(function(k) {
        var ki = Number(k);
        if (indexMap[ki] != null) {
          next[indexMap[ki]] = prev[ki];
        }
      });
      return next;
    });

    setActiveSlide(function(prev) {
      if (prev === fromIdx) return toIdx;
      if (indexMap[prev] != null) return indexMap[prev];
      return prev;
    });

    setDragFrom(null);
    setDragOver(null);
  };

  // --- Card management ---

  var updateSlideCard = function(slideIdx, cardIdx, val) {
    updateSlide(slideIdx, "cards", seriesSlides[slideIdx].cards.map(function(c, i) { return i === cardIdx ? val : c; }));
  };
  var addSlideCard = function(slideIdx) {
    var s = seriesSlides[slideIdx];
    if (s.cards.length < 5) updateSlide(slideIdx, "cards", s.cards.concat(["Card " + (s.cards.length + 1)]));
  };
  var removeSlideCard = function(slideIdx, cardIdx) {
    var s = seriesSlides[slideIdx];
    if (s.cards.length > 1) updateSlide(slideIdx, "cards", s.cards.filter(function(_, i) { return i !== cardIdx; }));
  };

  return {
    seriesSlides: seriesSlides, setSeriesSlides: setSeriesSlides,
    activeSlide: activeSlide, setActiveSlide: setActiveSlide,
    slideAssets: slideAssets, setSlideAssets: setSlideAssets,
    getAsset: getAsset, setAsset: setAsset, setScale: setScale,
    dragFrom: dragFrom, setDragFrom: setDragFrom,
    dragOver: dragOver, setDragOver: setDragOver,
    profilePicInputRef: profilePicInputRef,
    screenshotInputRef: screenshotInputRef,
    customBgInputRef: customBgInputRef,
    updateSlide: updateSlide, updateBgField: updateBgField,
    syncBgToAll: syncBgToAll, resetAllToDefault: resetAllToDefault,
    addSlide: addSlide, duplicateSlide: duplicateSlide,
    removeSlide: removeSlide, resetSlide: resetSlide, reorderSlide: reorderSlide,
    updateSlideCard: updateSlideCard, addSlideCard: addSlideCard, removeSlideCard: removeSlideCard,
    handleCustomUpload: handleCustomUpload,
    handleScreenshotUpload: handleScreenshotUpload,
    handleProfilePicUpload: handleProfilePicUpload,
    removeProfilePic: removeProfilePic,
    removeCustomBg: removeCustomBg,
    removeScreenshot: removeScreenshot
  };
}

// ===================================================
// useCanvasRenderer Hook
// ===================================================
// Manages canvas rendering with 40ms debounce.
// Params: canvasRef, seriesSlides, slideAssets, activeSlide
// Returns: { renderSlide }

function useCanvasRenderer(canvasRef, seriesSlides, slideAssets, activeSlide) {
  var renderTimerRef = useRef(null);

  var renderSlide = useCallback(function(ctx, slideIndex) {
    renderSlideToCanvas(ctx, slideIndex, seriesSlides, slideAssets);
  }, [seriesSlides, slideAssets]);

  var render = useCallback(function() {
    var canvas = canvasRef.current;
    if (!canvas) return;
    var ctx = canvas.getContext("2d");
    renderSlide(ctx, activeSlide);
  }, [renderSlide, activeSlide]);

  useEffect(function() {
    if (renderTimerRef.current) clearTimeout(renderTimerRef.current);
    renderTimerRef.current = setTimeout(function() {
      render();
    }, 40);
    return function() {
      if (renderTimerRef.current) clearTimeout(renderTimerRef.current);
    };
  }, [render]);

  return { renderSlide: renderSlide };
}

// ===================================================
// usePdfExport Hook
// ===================================================
// Manages PDF generation and download state.
// Params: canvasRef, renderSlide, seriesSlides, activeSlide, exportPrefix
// Returns: { pdfDownload, pdfError, downloadCurrentPDF, downloadAllPDF, clearPdfDownload }

function usePdfExport(canvasRef, renderSlide, seriesSlides, activeSlide, exportPrefix) {
  var pdfUrlRef = useRef(null);
  var [pdfDownload, setPdfDownload] = useState(null);
  var [pdfError, setPdfError] = useState("");

  var clearPdfDownload = function() {
    if (pdfUrlRef.current) {
      URL.revokeObjectURL(pdfUrlRef.current);
      pdfUrlRef.current = null;
    }
    setPdfDownload(null);
  };

  var captureSlideJpegBinary = function(ctx, idx) {
    var canvas = canvasRef.current;
    renderSlide(ctx, idx);
    var dataUrl = canvas.toDataURL("image/jpeg", 0.92);
    var jpeg = extractJpegBinaryFromDataUrl(dataUrl);
    if (!jpeg || jpeg.length === 0) {
      throw new Error("Failed to capture JPEG data from canvas");
    }
    return jpeg;
  };

  var downloadCurrentPDF = function() {
    var canvas = canvasRef.current;
    if (!canvas) return;
    setPdfError("");
    try {
      var ctx = canvas.getContext("2d");
      var jpeg = captureSlideJpegBinary(ctx, activeSlide);
      var blob = buildPdfFromJpegs([jpeg], W, H);
      clearPdfDownload();
      var prefix = sanitizePrefix(exportPrefix);
      var nn = (activeSlide + 1 < 10 ? "0" : "") + (activeSlide + 1);
      var fileName = prefix + "-" + nn + ".pdf";
      var url = URL.createObjectURL(blob);
      pdfUrlRef.current = url;
      setPdfDownload({ name: fileName, url: url });
    } catch (err) {
      setPdfError("PDF generation failed");
    }
  };

  var downloadAllPDF = function() {
    var canvas = canvasRef.current;
    if (!canvas) return;
    var ctx = canvas.getContext("2d");
    var total = seriesSlides.length;
    setPdfError("");
    try {
      var jpegPages = [];
      for (var i = 0; i < total; i++) {
        jpegPages.push(captureSlideJpegBinary(ctx, i));
      }
      var blob = buildPdfFromJpegs(jpegPages, W, H);
      clearPdfDownload();
      var prefix = sanitizePrefix(exportPrefix);
      var fileName = prefix + "-all.pdf";
      var url = URL.createObjectURL(blob);
      pdfUrlRef.current = url;
      setPdfDownload({ name: fileName, url: url });
    } catch (err) {
      setPdfError("PDF generation failed");
    } finally {
      renderSlide(ctx, activeSlide);
    }
  };

  // Cleanup on unmount
  useEffect(function() {
    return function() {
      if (pdfUrlRef.current) {
        URL.revokeObjectURL(pdfUrlRef.current);
        pdfUrlRef.current = null;
      }
    };
  }, []);

  return {
    pdfDownload: pdfDownload,
    pdfError: pdfError,
    setPdfError: setPdfError,
    downloadCurrentPDF: downloadCurrentPDF,
    downloadAllPDF: downloadAllPDF,
    clearPdfDownload: clearPdfDownload
  };
}

// ===================================================
// usePresets Hook
// ===================================================
// Manages preset serialize/deserialize, export/import, and stale-load guard.
// Params: deps object { seriesSlides, slideAssets,
//   exportPrefix, setExportPrefix, setSeriesSlides,
//   setSlideAssets, setActiveSlide, clearPdfDownload, setPdfError, pushUndo,
//   setConfirmDialog }
// Returns: { presetInputRef, presetDownload, presetDialog, setPresetDialog,
//   presetName, setPresetName, presetIncludeImages, setPresetIncludeImages,
//   presetError, setPresetError, downloadPreset, handlePresetUpload,
//   clearPresetDownload }

var PRESET_SLIDE_KEYS = [
  "title", "showHeading", "showAccentBar", "body",
  "titleColor", "titleFontFamily", "titleBold", "titleItalic",
  "bodyColor", "bodyFontFamily", "bodyBold", "bodyItalic",
  "showCards", "showCardChecks", "cards",
  "cardTextColor", "cardFontFamily", "cardBold", "cardItalic", "cardBgColor",
  "expandScreenshot", "showScreenshot",
  "showBrandName", "brandNameText", "brandNameColor",
  "brandNameFontFamily", "brandNameBold", "brandNameItalic",
  "showTopCorner", "topCornerText", "topCornerColor",
  "topCornerFontFamily", "topCornerBold", "topCornerItalic", "topCornerOpacity",
  "showBottomCorner", "bottomCornerText", "bottomCornerColor",
  "bottomCornerFontFamily", "bottomCornerBold", "bottomCornerItalic", "bottomCornerOpacity",
  "solidColor", "bgType", "geoEnabled", "geoLines", "geoOpacity", "geoShape",
  "frameEnabled", "accentColor", "decorationColor", "borderColor", "borderOpacity", "footerBg",
  "profilePicName",
  "headingSize", "bodySize", "cardTextSize",
  "topCornerSize", "bottomCornerSize", "brandNameSize"
];

var LEGACY_GEORGIA_FONT = "Georgia, serif";
var CAMBRIA_FONT_STACK = "Cambria, Georgia, serif";

function normalizeLegacyFontFamily(value) {
  if (value === LEGACY_GEORGIA_FONT) return CAMBRIA_FONT_STACK;
  return value;
}

function usePresets(deps) {
  var presetInputRef = useRef(null);
  var presetUrlRef = useRef(null);
  var presetLoadTokenRef = useRef(0);
  var [presetDownload, setPresetDownload] = useState(null);
  var [presetDialog, setPresetDialog] = useState(null);
  var [presetName, setPresetName] = useState("");
  var [presetIncludeImages, setPresetIncludeImages] = useState(true);
  var [presetError, setPresetError] = useState("");

  // Auto-dismiss preset errors after 10 seconds
  useEffect(function() {
    if (!presetError) return;
    var timer = setTimeout(function() { setPresetError(""); }, 10000);
    return function() { clearTimeout(timer); };
  }, [presetError]);

  var clearPresetDownload = function() {
    if (presetUrlRef.current) {
      URL.revokeObjectURL(presetUrlRef.current);
      presetUrlRef.current = null;
    }
    setPresetDownload(null);
  };

  var serializePreset = function(name, includeImages) {
    var images = {};

    var serializedSlides = deps.seriesSlides.map(function(s, i) {
      var slide = {};
      for (var k = 0; k < PRESET_SLIDE_KEYS.length; k++) {
        var key = PRESET_SLIDE_KEYS[k];
        if (key === "cards") {
          slide[key] = s[key] ? s[key].slice() : ["Card 1"];
        } else {
          slide[key] = s[key];
        }
      }

      slide.profileRef = null;
      if (s.profileImg && s.profileImg.src) {
        var profRef = "prof-" + i;
        slide.profileRef = profRef;
        images[profRef] = {
          name: s.profilePicName || ("profile-" + i + ".jpg"),
          dataUrl: includeImages ? s.profileImg.src : null
        };
      }

      slide.customBgRef = null;
      if (s.customBgImage && s.customBgImage.src) {
        var bgRef = "bg-" + i;
        slide.customBgRef = bgRef;
        images[bgRef] = {
          name: s.customBgName || ("bg-" + i + ".jpg"),
          dataUrl: includeImages ? s.customBgImage.src : null
        };
      }

      slide.screenshotRef = null;
      var asset = deps.slideAssets[i];
      if (asset && asset.image && asset.image.src) {
        var ssRef = "ss-" + i;
        slide.screenshotRef = ssRef;
        images[ssRef] = {
          name: asset.name || ("screenshot-" + i + ".jpg"),
          dataUrl: includeImages ? asset.image.src : null,
          scale: asset.scale || 1
        };
      }

      return slide;
    });

    return {
      version: 1,
      generator: "linkedin-carousel",
      name: name || "Untitled Preset",
      createdAt: new Date().toISOString(),
      exportPrefix: deps.exportPrefix,
      slides: serializedSlides,
      images: images
    };
  };

  var loadPresetData = function(data) {
    deps.pushUndo();
    var loadToken = ++presetLoadTokenRef.current;

    // Legacy: global sizes → per-slide migration handled after newSlides are built

    if (data.exportPrefix != null) {
      deps.setExportPrefix(data.exportPrefix);
    }

    // Legacy backward compat: old presets stored profile globally as profilePicRef
    var legacyProfileRef = data.profilePicRef;
    var legacyProfileEntry = legacyProfileRef && data.images && data.images[legacyProfileRef];

    var newAssets = {};

    var newSlides = (data.slides || []).map(function(sd, i) {
      var slide = makeDefaultSlide(sd.title, sd.body);
      for (var k = 0; k < PRESET_SLIDE_KEYS.length; k++) {
        var key = PRESET_SLIDE_KEYS[k];
        if (sd[key] !== undefined) {
          if (key === "cards") {
            slide[key] = (sd.cards || []).slice();
          } else if (/FontFamily$/.test(key)) {
            slide[key] = normalizeLegacyFontFamily(sd[key]);
          } else {
            slide[key] = sd[key];
          }
        }
      }

      // Per-slide profile image
      slide.profileImg = null;
      var profRef = sd.profileRef;
      var profEntry = profRef && data.images && data.images[profRef];
      if (profEntry) {
        slide.profilePicName = profEntry.name || null;
        if (profEntry.dataUrl) {
          (function(idx) {
            var profImg = new Image();
            profImg.onload = function() {
              if (presetLoadTokenRef.current !== loadToken) return;
              deps.setSeriesSlides(function(prev) {
                return prev.map(function(s, si) {
                  if (si !== idx) return s;
                  return Object.assign({}, s, { profileImg: profImg });
                });
              });
            };
            profImg.onerror = function() {
              if (presetLoadTokenRef.current !== loadToken) return;
              setPresetError("Failed to load profile image for slide " + (idx + 1) + ".");
            };
            profImg.src = profEntry.dataUrl;
          })(i);
        }
      } else if (legacyProfileEntry && legacyProfileEntry.dataUrl) {
        // Legacy: apply global profile to first slide only
        if (i === 0) {
          slide.profilePicName = legacyProfileEntry.name || null;
          (function(idx) {
            var legImg = new Image();
            legImg.onload = function() {
              if (presetLoadTokenRef.current !== loadToken) return;
              deps.setSeriesSlides(function(prev) {
                return prev.map(function(s, si) {
                  if (si !== idx) return s;
                  return Object.assign({}, s, { profileImg: legImg });
                });
              });
            };
            legImg.onerror = function() {
              if (presetLoadTokenRef.current !== loadToken) return;
              setPresetError("Failed to load profile image from preset.");
            };
            legImg.src = legacyProfileEntry.dataUrl;
          })(i);
        }
      }

      slide.customBgImage = null;
      slide.customBgName = null;
      var bgRef = sd.customBgRef;
      var bgEntry = bgRef && data.images && data.images[bgRef];
      if (bgEntry) {
        slide.customBgName = bgEntry.name || null;
        if (bgEntry.dataUrl) {
          var bgImg = new Image();
          (function(idx) {
            bgImg.onload = function() {
              if (presetLoadTokenRef.current !== loadToken) return;
              deps.setSeriesSlides(function(prev) {
                return prev.map(function(s, si) {
                  if (si !== idx) return s;
                  return Object.assign({}, s, { customBgImage: bgImg });
                });
              });
            };
            bgImg.onerror = function() {
              if (presetLoadTokenRef.current !== loadToken) return;
              setPresetError("Failed to load background image for slide " + (idx + 1) + ".");
            };
          })(i);
          bgImg.src = bgEntry.dataUrl;
        }
      }

      var ssRef = sd.screenshotRef;
      var ssEntry = ssRef && data.images && data.images[ssRef];
      if (ssEntry) {
        newAssets[i] = { image: null, name: ssEntry.name || null, scale: ssEntry.scale || 1 };
        if (ssEntry.dataUrl) {
          (function(idx) {
            var ssImg = new Image();
            ssImg.onload = function() {
              if (presetLoadTokenRef.current !== loadToken) return;
              deps.setSlideAssets(function(prev) {
                var next = Object.assign({}, prev);
                next[idx] = Object.assign({}, next[idx] || {}, { image: ssImg });
                return next;
              });
            };
            ssImg.onerror = function() {
              if (presetLoadTokenRef.current !== loadToken) return;
              setPresetError("Failed to load screenshot image for slide " + (idx + 1) + ".");
            };
            ssImg.src = ssEntry.dataUrl;
          })(i);
        }
      }

      return slide;
    });

    if (newSlides.length === 0) {
      newSlides = [makeDefaultSlide()];
    }

    // Legacy migration: old presets have global sizes but no per-slide size fields
    if (data.sizes && newSlides.length > 0 && newSlides[0].headingSize == null) {
      var ls = Object.assign({
        heading: 48, body: 38, cardText: 22,
        topCorner: 13, bottomCorner: 16, brandName: 20
      }, data.sizes);
      for (var li = 0; li < newSlides.length; li++) {
        newSlides[li].headingSize = ls.heading;
        newSlides[li].bodySize = ls.body;
        newSlides[li].cardTextSize = ls.cardText;
        newSlides[li].topCornerSize = ls.topCorner;
        newSlides[li].bottomCornerSize = ls.bottomCorner;
        newSlides[li].brandNameSize = ls.brandName;
      }
    }

    deps.setSeriesSlides(newSlides);
    deps.setSlideAssets(newAssets);
    deps.setActiveSlide(0);

    deps.clearPdfDownload();
    deps.setPdfError("");
  };

  var downloadPreset = function(name, includeImages) {
    setPresetError("");
    var preset = serializePreset(name, includeImages);
    var json = JSON.stringify(preset, null, 2);
    var blob = new Blob([json], { type: "application/json" });
    clearPresetDownload();
    var url = URL.createObjectURL(blob);
    presetUrlRef.current = url;
    var fileName = sanitizePrefix(name || deps.exportPrefix || "preset") + ".json";
    setPresetDownload({ name: fileName, url: url });
  };

  var validatePresetData = function(data) {
    if (!data || typeof data !== "object") return "Invalid preset file (not an object).";
    if (data.version !== 1) return "Invalid preset file format (expected v1).";
    if (!Array.isArray(data.slides)) return "Invalid preset file (missing slides array).";
    if (data.slides.length === 0) return "Preset contains no slides.";
    if (data.slides.length > MAX_SLIDES) return "Preset exceeds maximum of " + MAX_SLIDES + " slides.";
    for (var i = 0; i < data.slides.length; i++) {
      var entry = data.slides[i];
      if (!entry || typeof entry !== "object" || Array.isArray(entry)) {
        return "Malformed slide entry at position " + (i + 1) + ".";
      }
    }
    return null;
  };

  var handlePresetUpload = function(e) {
    var file = e.target.files[0];
    if (!file) return;
    setPresetError("");
    var reader = new FileReader();
    reader.onload = function(ev) {
      try {
        var data = JSON.parse(ev.target.result);
        var validationError = validatePresetData(data);
        if (validationError) {
          setPresetError(validationError);
          return;
        }

        var imageMap = (data.images && typeof data.images === "object") ? data.images : {};
        var missingCount = 0;
        for (var i = 0; i < data.slides.length; i++) {
          var sd = data.slides[i];
          if (sd.profileRef) {
            var profEntryCheck = imageMap[sd.profileRef];
            if (!profEntryCheck || !profEntryCheck.dataUrl) missingCount++;
          }
          if (sd.customBgRef) {
            var bgEntryCheck = imageMap[sd.customBgRef];
            if (!bgEntryCheck || !bgEntryCheck.dataUrl) missingCount++;
          }
          if (sd.screenshotRef) {
            var ssEntryCheck = imageMap[sd.screenshotRef];
            if (!ssEntryCheck || !ssEntryCheck.dataUrl) missingCount++;
          }
        }
        // Legacy compat: check global profilePicRef from old presets
        if (data.profilePicRef && !data.slides.some(function(s) { return s.profileRef; })) {
          var legacyProfCheck = imageMap[data.profilePicRef];
          if (!legacyProfCheck || !legacyProfCheck.dataUrl) missingCount++;
        }

        var msg = "Load preset \u201c" + (data.name || "Untitled") + "\u201d? This replaces all current slides and settings.";
        if (missingCount > 0) {
          msg += " (" + missingCount + " image" + (missingCount > 1 ? "s" : "") + " not included \u2014 re-upload after loading.)";
        }

        setPresetError("");
        deps.setConfirmDialog({
          message: msg,
          onConfirm: function() {
            setPresetError("");
            try {
              loadPresetData(data);
            } catch (loadErr) {
              setPresetError("Failed to apply preset: " + (loadErr.message || "unknown error"));
            }
          }
        });
      } catch (err) {
        setPresetError("Failed to parse preset file.");
      }
    };
    reader.readAsText(file);
    if (presetInputRef.current) presetInputRef.current.value = "";
  };

  // Cleanup on unmount
  useEffect(function() {
    return function() {
      if (presetUrlRef.current) {
        URL.revokeObjectURL(presetUrlRef.current);
        presetUrlRef.current = null;
      }
    };
  }, []);

  return {
    presetInputRef: presetInputRef,
    presetDownload: presetDownload,
    presetDialog: presetDialog,
    setPresetDialog: setPresetDialog,
    presetName: presetName,
    setPresetName: setPresetName,
    presetIncludeImages: presetIncludeImages,
    setPresetIncludeImages: setPresetIncludeImages,
    presetError: presetError,
    setPresetError: setPresetError,
    downloadPreset: downloadPreset,
    handlePresetUpload: handlePresetUpload,
    clearPresetDownload: clearPresetDownload
  };
}

// ---------------------------------------
// Main Component
// ---------------------------------------

// Hoisted styles (module-scope to avoid per-render allocations)
var inputStyle = { width: "100%", padding: SPACE[4] + "px " + SPACE[6] + "px", borderRadius: RADIUS.lg, border: "1px solid " + SURFACE.border, background: SURFACE.input, color: SURFACE.white, fontSize: 14, boxSizing: "border-box" };
var labelStyle = { display: "block", marginBottom: SPACE[3], fontWeight: 600, fontSize: 13, color: SURFACE.label, letterSpacing: 0.5 };
var INLINE_SWATCHES = ["#ffffff", "#1a1a2e", "#333333", "#22c55e", "#a5b4fc", "#f59e0b", "#fb7185", "#22d3ee", "#a78bfa", "#38bdf8", "#d97706", "#fef3c7", "#e0f2fe", "#e0e7ff", "#f0fdf4", "#9ca3af"];
var smallBtnStyle = { padding: SPACE[1] + "px " + SPACE[4] + "px", borderRadius: RADIUS.sm, border: "1px solid " + SURFACE.border, background: SURFACE.input, color: SURFACE.text, cursor: "pointer", fontSize: 9, fontWeight: 600 };
var pickerDropdownStyle = { position: "absolute", top: "100%", left: 0, zIndex: Z.dropdown, marginTop: SPACE[2], background: SURFACE.panel, border: "1px solid " + SURFACE.border, borderRadius: RADIUS.xl, padding: SPACE[5], width: SIZE.pickerWidth, boxShadow: CLR.shadow };

export default function App() {
  var canvasRef = useRef(null);
  var [confirmDialog, setConfirmDialog] = useState(null);

  // Undo/redo
  var undoManagerRef = useRef(createUndoManager());
  var pushUndoRef = useRef(null);

  var [openPicker, setOpenPicker] = useState(null);

  // Close picker on outside click
  useEffect(function() {
    if (!openPicker) return;
    var handler = function(e) {
      var picker = document.querySelector('[data-picker="' + openPicker + '"]');
      var portal = document.querySelector('[data-picker-portal="' + openPicker + '"]');
      if (picker && !picker.contains(e.target) && (!portal || !portal.contains(e.target))) {
        setOpenPicker(null);
      }
    };
    document.addEventListener("mousedown", handler);
    return function() { document.removeEventListener("mousedown", handler); };
  }, [openPicker]);

  // Export prefix
  var [exportPrefix, setExportPrefix] = useState("linkedin-slide");

  // --- Slide management hook ---
  var slideMgmt = useSlideManagement({ pushUndo: function() { if (pushUndoRef.current) pushUndoRef.current(); }, setConfirmDialog: setConfirmDialog });

  var seriesSlides = slideMgmt.seriesSlides;
  var setSeriesSlides = slideMgmt.setSeriesSlides;
  var activeSlide = slideMgmt.activeSlide;
  var setActiveSlide = slideMgmt.setActiveSlide;
  var slideAssets = slideMgmt.slideAssets;
  var setSlideAssets = slideMgmt.setSlideAssets;
  var getAsset = slideMgmt.getAsset;
  var setScale = slideMgmt.setScale;
  // --- Undo/redo snapshot helpers ---

  var captureSnapshot = function() {
    return {
      seriesSlides: seriesSlides.map(function(s) {
        return Object.assign({}, s, { cards: s.cards ? s.cards.slice() : s.cards });
      }),
      slideAssets: Object.keys(slideAssets).reduce(function(acc, k) {
        acc[k] = Object.assign({}, slideAssets[k]);
        return acc;
      }, {}),
      activeSlide: activeSlide,
      exportPrefix: exportPrefix
    };
  };

  var restoreSnapshot = function(snap) {
    setSeriesSlides(snap.seriesSlides);
    setSlideAssets(snap.slideAssets);
    setActiveSlide(snap.activeSlide);
    setExportPrefix(snap.exportPrefix);
  };

  // Keep pushUndoRef current so hooks always call the latest captureSnapshot
  pushUndoRef.current = function() {
    undoManagerRef.current.pushSnapshot(captureSnapshot());
  };

  // Stable refs for undo/redo keyboard handler
  var captureSnapshotRef = useRef(captureSnapshot);
  var restoreSnapshotRef = useRef(restoreSnapshot);
  captureSnapshotRef.current = captureSnapshot;
  restoreSnapshotRef.current = restoreSnapshot;

  // Global keyboard handler for undo/redo (registered once)
  useEffect(function() {
    var handler = function(e) {
      // Skip if focus is in an input, textarea, or select (preserve native text undo)
      var tag = e.target && e.target.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      var isCtrl = e.ctrlKey || e.metaKey;
      if (!isCtrl || (e.key && e.key.toLowerCase()) !== "z") return;
      e.preventDefault();
      if (e.shiftKey) {
        var redoSnap = undoManagerRef.current.redo(captureSnapshotRef.current());
        if (redoSnap) restoreSnapshotRef.current(redoSnap);
      } else {
        var undoSnap = undoManagerRef.current.undo(captureSnapshotRef.current());
        if (undoSnap) restoreSnapshotRef.current(undoSnap);
      }
    };
    document.addEventListener("keydown", handler);
    return function() { document.removeEventListener("keydown", handler); };
  }, []);

  // Stable refs for paste handler (registered once)
  var activeSlideRef = useRef(activeSlide);
  activeSlideRef.current = activeSlide;
  var seriesSlidesRef = useRef(seriesSlides);
  seriesSlidesRef.current = seriesSlides;
  var slideMgmtRef = useRef(slideMgmt);
  slideMgmtRef.current = slideMgmt;

  // Global paste handler for screenshot images (registered once)
  useEffect(function() {
    var handler = function(e) {
      // Skip if focus is in an input, textarea, or select (preserve normal text paste)
      var tag = e.target && e.target.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;

      // Check for image data in clipboard
      var items = e.clipboardData && e.clipboardData.items;
      if (!items) return;
      var imageItem = null;
      for (var i = 0; i < items.length; i++) {
        if (items[i].type.indexOf("image/") === 0) {
          imageItem = items[i];
          break;
        }
      }
      if (!imageItem) return;

      e.preventDefault();
      // Capture target slide at paste time so async load can't drift to another slide.
      var targetSlide = activeSlideRef.current;
      var blob = imageItem.getAsFile();
      if (!blob) return;
      var reader = new FileReader();
      reader.onload = function(ev) {
        var img = new Image();
        img.onload = function() {
          var mgmt = slideMgmtRef.current;
          var slides = seriesSlidesRef.current;
          // Auto-enable screenshot if not already on
          if (slides[targetSlide] && !slides[targetSlide].showScreenshot) {
            mgmt.updateSlide(targetSlide, "showScreenshot", true);
          }
          mgmt.setAsset(targetSlide, { name: "pasted-image.png", image: img });
        };
        img.src = ev.target.result;
      };
      reader.readAsDataURL(blob);
    };
    document.addEventListener("paste", handler);
    return function() { document.removeEventListener("paste", handler); };
  }, []);

  // --- Canvas rendering hook ---
  var canvasRenderer = useCanvasRenderer(canvasRef, seriesSlides, slideAssets, activeSlide);
  var renderSlide = canvasRenderer.renderSlide;

  // --- PDF export hook ---
  var pdfExport = usePdfExport(canvasRef, renderSlide, seriesSlides, activeSlide, exportPrefix);
  var pdfDownload = pdfExport.pdfDownload;
  var pdfError = pdfExport.pdfError;
  var setPdfError = pdfExport.setPdfError;
  var downloadCurrentPDF = pdfExport.downloadCurrentPDF;
  var downloadAllPDF = pdfExport.downloadAllPDF;
  var clearPdfDownload = pdfExport.clearPdfDownload;

  // --- Presets hook ---
  var presets = usePresets({
    seriesSlides: seriesSlides, slideAssets: slideAssets,
    exportPrefix: exportPrefix, setExportPrefix: setExportPrefix,
    setSeriesSlides: setSeriesSlides, setSlideAssets: setSlideAssets,
    setActiveSlide: setActiveSlide, clearPdfDownload: clearPdfDownload,
    setPdfError: setPdfError,
    pushUndo: function() { if (pushUndoRef.current) pushUndoRef.current(); },
    setConfirmDialog: setConfirmDialog
  });

  // --- Convenience aliases ---
  var updateSlide = slideMgmt.updateSlide;
  var updateBgField = slideMgmt.updateBgField;
  var currentSlide = seriesSlides[activeSlide] || seriesSlides[0];
  var isCustomBg = currentSlide.bgType === "custom";
  var effectiveGeoShape = (!currentSlide.geoEnabled && (currentSlide.geoShape || "lines") !== "solid") ? "solid" : (currentSlide.geoShape || "lines");

  // Per-slide font sizes (derived from active slide)
  var sizes = {
    heading: currentSlide.headingSize || 48,
    body: currentSlide.bodySize || 38,
    cardText: currentSlide.cardTextSize || 22,
    topCorner: currentSlide.topCornerSize || 13,
    bottomCorner: currentSlide.bottomCornerSize || 16,
    brandName: currentSlide.brandNameSize || 20,
  };
  var SIZE_FIELD_MAP = { heading: "headingSize", body: "bodySize", cardText: "cardTextSize", topCorner: "topCornerSize", bottomCorner: "bottomCornerSize", brandName: "brandNameSize" };
  var setSize = function(key, val) {
    var field = SIZE_FIELD_MAP[key];
    if (field) updateSlide(activeSlide, field, val);
  };

  return (
    <div style={{ fontFamily: '"Helvetica Neue", Helvetica, Arial, sans-serif', background: SURFACE.page, height: "100vh", overflow: "hidden", color: SURFACE.body, padding: SIZE.pagePadV + "px " + SIZE.pagePadH + "px", boxSizing: "border-box" }}>
      <div style={{ margin: "0 auto", height: "100%", display: "flex", flexDirection: "column" }}>

        <div style={{ display: "grid", gridTemplateColumns: SIZE.leftPane + "px 1fr minmax(0," + SIZE.rightPaneMax + "px)", gridTemplateAreas: '"sidebar editor preview"', gap: SIZE.columnGap, flex: 1, minHeight: 0 }}>

        {/* -- LEFT COLUMN: Presets + Background + Slides -- */}
        <div style={{ gridArea: "sidebar", overflowY: "auto", minHeight: 0 }}>
          {/* Presets */}
          <div>
            <h2 style={{ color: SURFACE.white, margin: "0 0 " + SPACE[5] + "px 0", fontSize: 18 }}>Carousel Generator</h2>
            {/* --- DOWNLOAD --- */}
            <div style={{ marginBottom: SPACE[7], position: "relative" }}>
              <label style={Object.assign({}, labelStyle, { marginBottom: SPACE[3], whiteSpace: "nowrap" })}>DOWNLOAD</label>
              <input value={exportPrefix}
                onChange={function(e) { setExportPrefix(e.target.value); }}
                placeholder="linkedin-slide"
                style={{ width: "100%", padding: SPACE[3] + "px " + SPACE[5] + "px", borderRadius: RADIUS.md, border: "1px solid " + SURFACE.border, background: SURFACE.input, color: SURFACE.text, fontSize: 11, boxSizing: "border-box", fontFamily: "monospace", marginBottom: SPACE[3] }} />
              <div style={{ display: "flex", alignItems: "center", gap: SPACE[4] }}>
                <button onClick={downloadCurrentPDF}
                  style={{ flex: 1, padding: SPACE[3] + "px " + SPACE[5] + "px", borderRadius: RADIUS.md, border: "none", background: CLR.primary, color: SURFACE.white, fontSize: 11, fontWeight: 700, cursor: "pointer", whiteSpace: "nowrap", lineHeight: 1.3 }}>
                  {"Current Slide"}
                </button>
                <button onClick={downloadAllPDF}
                  disabled={seriesSlides.length <= 1}
                  style={{ flex: 1, padding: SPACE[3] + "px " + SPACE[5] + "px", borderRadius: RADIUS.md, border: "2px solid " + GREEN, background: "transparent", color: GREEN, fontSize: 11, fontWeight: 700, cursor: seriesSlides.length > 1 ? "pointer" : "default", opacity: seriesSlides.length > 1 ? 1 : 0.4, whiteSpace: "nowrap", lineHeight: 1.3 }}>
                  {"All Slides"}
                </button>
              </div>
              <div style={{ position: "absolute", left: 0, right: 0, top: "100%", paddingTop: SPACE[1] }}>
                {pdfDownload && (
                  <div style={{ display: "flex", alignItems: "center", gap: SPACE[2] }}>
                    <a href={pdfDownload.url} download={pdfDownload.name}
                      onClick={function() { setTimeout(clearPdfDownload, 1500); }}
                      style={{ fontSize: 10, color: CLR.primaryLight, textDecoration: "underline", flex: 1, wordBreak: "break-all" }}>
                      {"Save " + pdfDownload.name}
                    </a>
                    <button onClick={clearPdfDownload}
                      style={{ background: "none", border: "none", color: SURFACE.subtle, cursor: "pointer", fontSize: 13, padding: "0 " + SPACE[1] + "px", lineHeight: 1 }}>
                      {"\u00d7"}
                    </button>
                  </div>
                )}
                {pdfError && !pdfDownload && (
                  <span style={{ fontSize: 10, color: CLR.error, display: "block" }}>{pdfError}</span>
                )}
              </div>
            </div>
            <div style={dividerStyle()} />
            {/* --- PRESETS --- */}
            <div style={{ marginBottom: SPACE[3], minHeight: 36 }}>
              <label style={Object.assign({}, labelStyle, { marginBottom: SPACE[3] })}>PRESETS</label>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: SPACE[2], marginBottom: SPACE[2] }}>
                <button onClick={function() { presets.setPresetError(""); presets.setPresetName(exportPrefix || ""); presets.setPresetDialog({ type: "save" }); }}
                  style={panelBtn()}>
                  Save
                </button>
                <button onClick={function() { presets.setPresetError(""); if (presets.presetInputRef.current) presets.presetInputRef.current.click(); }}
                  style={panelBtn()}>
                  Load
                </button>
                <input ref={presets.presetInputRef} type="file" accept=".json" onChange={presets.handlePresetUpload} style={{ display: "none" }} />
              </div>
              {presets.presetDownload && (
                <div style={{ display: "flex", alignItems: "center", gap: SPACE[2], marginTop: SPACE[1] }}>
                  <a href={presets.presetDownload.url} download={presets.presetDownload.name}
                    onClick={function() { setTimeout(presets.clearPresetDownload, 1500); }}
                    style={{ fontSize: 10, color: CLR.primaryLight, textDecoration: "underline", flex: 1, wordBreak: "break-all" }}>
                    {"Save " + presets.presetDownload.name}
                  </a>
                  <button onClick={presets.clearPresetDownload}
                    style={{ background: "none", border: "none", color: SURFACE.subtle, cursor: "pointer", fontSize: 13, padding: "0 " + SPACE[1] + "px", lineHeight: 1 }}>
                    {"\u00d7"}
                  </button>
                </div>
              )}
              {presets.presetError && (
                <div style={{ marginTop: SPACE[1], padding: "3px " + SPACE[3] + "px", borderRadius: RADIUS.md, background: CLR.errorBg, border: "1px solid " + CLR.errorBorder, color: CLR.errorLight, fontSize: 10, display: "flex", alignItems: "center", gap: SPACE[2] }}>
                  <span style={{ flex: 1 }}>{presets.presetError}</span>
                  <button onClick={function() { presets.setPresetError(""); }}
                    style={{ background: "none", border: "none", color: CLR.errorLight, cursor: "pointer", fontSize: 13, padding: "0 " + SPACE[1] + "px", lineHeight: 1 }}>{"\u00d7"}</button>
                </div>
              )}
            </div>
            <div style={dividerStyle()} />
          </div>
          {/* Slides list */}
          <div>
            <div style={{ background: SURFACE.panelDeep, border: "1px solid " + SURFACE.uploadBorder, borderRadius: RADIUS.xl, padding: SPACE[7] }}>
              <label style={Object.assign({}, labelStyle, { marginBottom: SPACE[4] })}>SLIDES</label>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: SPACE[2], marginBottom: SPACE[5] }}>
                <button onClick={slideMgmt.syncBgToAll} style={panelBtn({ whiteSpace: "nowrap" })}>Sync All</button>
                <button onClick={slideMgmt.resetAllToDefault} style={panelBtn()}>Reset All</button>
              </div>
              <SlideSelector seriesSlides={seriesSlides} activeSlide={activeSlide} setActiveSlide={setActiveSlide}
                dragFrom={slideMgmt.dragFrom} setDragFrom={slideMgmt.setDragFrom} dragOver={slideMgmt.dragOver} setDragOver={slideMgmt.setDragOver}
                reorderSlide={slideMgmt.reorderSlide} addSlide={slideMgmt.addSlide} duplicateSlide={slideMgmt.duplicateSlide}
                removeSlide={slideMgmt.removeSlide} />
            </div>
          </div>
        </div>

        {/* -- CENTER PANE: Slide Editor -- */}
        <div style={{ gridArea: "editor", display: "flex", flexDirection: "column", minWidth: 0, minHeight: 0 }}>

          {/* Scrollable: Slide Editor */}
          <div style={{ flex: 1, overflowY: "auto", minHeight: 0 }}>

          {/* --- SLIDE EDITOR --- */}
          {currentSlide && (
            <div style={{ background: SURFACE.panel, borderRadius: RADIUS.xl, padding: SPACE[6], border: "1px solid " + SURFACE.panelBorder, marginBottom: SPACE[6] }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: SPACE[5] }}>
                <span style={{ color: SURFACE.tertiary, fontSize: 14, fontWeight: 700 }}>
                  {"SLIDE " + (activeSlide + 1)}
                </span>
                <div style={{ flex: 1 }} />
                <div style={{ display: "flex", gap: SPACE[3] }}>
                  <button onClick={function() { if (getAsset(activeSlide).image) updateSlide(activeSlide, "expandScreenshot", !currentSlide.expandScreenshot, true); }}
                    style={{ background: "none", border: "1px solid " + (currentSlide.expandScreenshot ? CLR.primary : SURFACE.border), color: currentSlide.expandScreenshot ? CLR.primary : SURFACE.text, cursor: getAsset(activeSlide).image ? "pointer" : "default", fontSize: 11, padding: "3px " + SPACE[5] + "px", borderRadius: RADIUS.md, opacity: getAsset(activeSlide).image ? 1 : 0.4 }}>Expand Screenshot</button>
                  <button onClick={slideMgmt.duplicateSlide}
                    style={panelBtn({ background: "none", opacity: seriesSlides.length >= MAX_SLIDES ? 0.4 : 1, cursor: seriesSlides.length >= MAX_SLIDES ? "default" : "pointer" })}>Duplicate</button>
                  <button onClick={function() { slideMgmt.resetSlide(activeSlide); }}
                    style={{ background: "none", border: "1px solid " + SURFACE.border, color: SURFACE.text, cursor: "pointer", fontSize: 11, padding: "3px " + SPACE[5] + "px", borderRadius: RADIUS.md }}>Reset</button>
                  {seriesSlides.length > 1 && (
                    <button onClick={function() { slideMgmt.removeSlide(activeSlide); }}
                      style={{ background: "none", border: "1px solid " + CLR.dangerBorder, color: CLR.danger, cursor: "pointer", fontSize: 11, padding: "3px " + SPACE[5] + "px", borderRadius: RADIUS.md }}>Remove</button>
                  )}
                </div>
              </div>

              {/* -- Uploads: Background, Footer, Screenshot side by side -- */}
              <div style={{ display: "flex", gap: SPACE[3], marginBottom: SPACE[5] }}>
                {/* BACKGROUND upload */}
                <div style={uploadFrameStyle({ flex: 1, minWidth: 0, padding: SPACE[2] + "px " + SPACE[3] + "px" })}>
                  <label style={{ fontSize: 11, color: SURFACE.label, fontWeight: 600, marginBottom: 3 }}>BACKGROUND</label>
                  <span style={{ fontSize: 11, color: SURFACE.muted, marginBottom: SPACE[2] }}>800×1000px</span>
                  <input ref={slideMgmt.customBgInputRef} type="file" accept="image/*" onChange={function(e) { slideMgmt.handleCustomUpload(e); }} style={{ display: "none" }} />
                  <div style={uploadBtnStyle(currentSlide.customBgImage)}
                    onClick={function() { if (!isCustomBg) updateBgField("bgType", "custom"); if (slideMgmt.customBgInputRef.current) slideMgmt.customBgInputRef.current.click(); }}>
                    {currentSlide.customBgImage ? (
                      <>
                        <span style={{ fontSize: 11, color: GREEN, lineHeight: 1, fontWeight: 700 }}>{"\u2713"}</span>
                        <button onClick={function(e) { e.stopPropagation(); slideMgmt.removeCustomBg(); }}
                          style={{ background: "none", border: "none", color: CLR.danger, cursor: "pointer", fontSize: 14, padding: 0, lineHeight: 1, fontWeight: 700 }}>{"\u00d7"}</button>
                      </>
                    ) : (
                      <span style={{ fontSize: 9, color: SURFACE.text, fontWeight: 600 }}>Upload</span>
                    )}
                  </div>
                  {currentSlide.customBgName && (
                    <span style={{ fontSize: 11, color: SURFACE.dimmed, marginTop: 3, maxWidth: "100%", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", display: "block", textAlign: "center" }}>{currentSlide.customBgName}</span>
                  )}
                </div>
                {/* FOOTER upload */}
                <div style={uploadFrameStyle({ flex: 1, minWidth: 0 })}>
                  <label style={{ fontSize: 11, color: SURFACE.label, fontWeight: 600, marginBottom: 3 }}>FOOTER</label>
                  <span style={{ fontSize: 11, color: SURFACE.muted, marginBottom: SPACE[2] }}>84×84px</span>
                  <input ref={slideMgmt.profilePicInputRef} type="file" accept="image/*" onChange={slideMgmt.handleProfilePicUpload} style={{ display: "none" }} />
                  <div style={uploadBtnStyle(currentSlide.profileImg)}
                    onClick={function() { if (slideMgmt.profilePicInputRef.current) slideMgmt.profilePicInputRef.current.click(); }}>
                    {currentSlide.profileImg ? (
                      <>
                        <span style={{ fontSize: 11, color: GREEN, lineHeight: 1, fontWeight: 700 }}>{"\u2713"}</span>
                        <button onClick={function(e) { e.stopPropagation(); slideMgmt.removeProfilePic(); }}
                          style={{ background: "none", border: "none", color: CLR.danger, cursor: "pointer", fontSize: 14, padding: 0, lineHeight: 1, fontWeight: 700 }}>{"\u00d7"}</button>
                      </>
                    ) : (
                      <span style={{ fontSize: 9, color: SURFACE.text, fontWeight: 600 }}>Upload</span>
                    )}
                  </div>
                  {currentSlide.profilePicName && (
                    <span style={{ fontSize: 11, color: SURFACE.dimmed, marginTop: 3, maxWidth: "100%", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", display: "block", textAlign: "center" }}>{currentSlide.profilePicName}</span>
                  )}
                </div>
                {/* SCREENSHOT upload */}
                <div style={uploadFrameStyle({ flex: 1, minWidth: 0 })}>
                  <label style={{ fontSize: 11, color: SURFACE.label, fontWeight: 600, marginBottom: 3 }}>SCREENSHOT</label>
                  {getAsset(activeSlide).image ? (
                    <div style={{ display: "flex", alignItems: "center", gap: SPACE[1], marginBottom: SPACE[2], width: "100%" }}>
                      <input type="range" min={50} max={200} value={Math.round(getAsset(activeSlide).scale * 100)} onChange={function(e) { setScale(activeSlide, Number(e.target.value) / 100); }}
                        style={{ flex: 1, minWidth: 0 }} />
                      <span style={{ fontSize: 7, color: SURFACE.secondary, minWidth: 20, textAlign: "right" }}>{Math.round(getAsset(activeSlide).scale * 100) + "%"}</span>
                    </div>
                  ) : (
                    <span style={{ fontSize: 11, color: SURFACE.muted, marginBottom: SPACE[2] }}>{"\u00A0"}</span>
                  )}
                  <input ref={slideMgmt.screenshotInputRef} type="file" accept="image/*" onChange={function(e) { slideMgmt.handleScreenshotUpload(activeSlide, e); }} style={{ display: "none" }} />
                  <div style={uploadBtnStyle(getAsset(activeSlide).image)}
                    onClick={function() { if (slideMgmt.screenshotInputRef.current) slideMgmt.screenshotInputRef.current.click(); }}>
                    {getAsset(activeSlide).image ? (
                      <>
                        <span style={{ fontSize: 11, color: GREEN, lineHeight: 1, fontWeight: 700 }}>{"\u2713"}</span>
                        <button onClick={function(e) { e.stopPropagation(); slideMgmt.removeScreenshot(activeSlide); }}
                          style={{ background: "none", border: "none", color: CLR.danger, cursor: "pointer", fontSize: 14, padding: 0, lineHeight: 1, fontWeight: 700 }}>{"\u00d7"}</button>
                      </>
                    ) : (
                      <span style={{ fontSize: 9, color: SURFACE.text, fontWeight: 600 }}>Upload</span>
                    )}
                  </div>
                  {getAsset(activeSlide).name && (
                    <span style={{ fontSize: 11, color: SURFACE.dimmed, marginTop: 3, maxWidth: "100%", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", display: "block", textAlign: "center" }}>{getAsset(activeSlide).name}</span>
                  )}
                </div>
              </div>

              {/* -- Background color swatches -- */}
              <div style={{ display: "flex", alignItems: "center", gap: SPACE[4], marginBottom: SPACE[4] }}>
                <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>BACKGROUND</label>
                <div style={{ display: "flex", alignItems: "center", gap: SPACE[3] }}>
                  <ColorPickerInline pickerKey="layer" value={currentSlide.geoLines || "#a0a0af"} onChange={function(c) { updateBgField("geoLines", c); }} fillValue={currentSlide.solidColor || "#1e1e2e"} onFillChange={function(c) { updateBgField("solidColor", c); }} dualColor={true} openPicker={openPicker} setOpenPicker={setOpenPicker} disabled={isCustomBg} opacityVal={currentSlide.geoOpacity} onOpacityChange={function(v) { updateBgField("geoOpacity", v); }} geoShape={effectiveGeoShape} onShapeChange={function(s) { updateBgField("geoShape", s); updateBgField("geoEnabled", s !== "solid"); }} />
                  <span style={{ fontSize: 11, color: SURFACE.secondary, fontWeight: 600, opacity: isCustomBg ? 0.35 : 1 }}>Layer</span>
                  <span style={{ color: SURFACE.pipeSep, fontSize: 14 }}>|</span>
                  <ColorPickerInline pickerKey="border" value={currentSlide.frameEnabled ? (currentSlide.borderColor || "#fff") : "transparent"} onChange={function(c) { if (c === "transparent") { updateBgField("frameEnabled", false); } else { updateBgField("borderColor", c); updateBgField("frameEnabled", true); } }} openPicker={openPicker} setOpenPicker={setOpenPicker} disabled={isCustomBg} allowTransparent={true} opacityVal={currentSlide.borderOpacity} onOpacityChange={function(v) { updateBgField("borderOpacity", v); }} />
                  <span style={{ fontSize: 11, color: SURFACE.secondary, fontWeight: 600, opacity: isCustomBg ? 0.35 : 1 }}>Frame</span>
                  <span style={{ color: SURFACE.pipeSep, fontSize: 14 }}>|</span>
                  <ColorPickerInline pickerKey="decoration" value={currentSlide.decorationColor === "transparent" ? "transparent" : (currentSlide.decorationColor || "#a5b4fc")} onChange={function(c) { if (c === "transparent") { updateSlide(activeSlide, "decorationColor", "transparent"); updateSlide(activeSlide, "showAccentBar", false); } else { updateSlide(activeSlide, "decorationColor", c); updateSlide(activeSlide, "showAccentBar", true); } }} openPicker={openPicker} setOpenPicker={setOpenPicker} allowTransparent={true} disabled={isCustomBg} />
                  <span style={{ fontSize: 11, color: SURFACE.secondary, fontWeight: 600, opacity: isCustomBg ? 0.35 : 1 }}>Decorations</span>
                  <span style={{ color: SURFACE.pipeSep, fontSize: 14 }}>|</span>
                  <ColorPickerInline pickerKey="accent" value={currentSlide.accentColor || "#a5b4fc"} onChange={function(c) { updateSlide(activeSlide, "accentColor", c); }} openPicker={openPicker} setOpenPicker={setOpenPicker} disabled={isCustomBg} />
                  <span style={{ fontSize: 11, color: SURFACE.secondary, fontWeight: 600, opacity: isCustomBg ? 0.35 : 1 }}>Accent</span>
                  <span style={{ fontSize: 11, color: SURFACE.muted, marginLeft: SPACE[6] }}>**word** = accent color</span>
                </div>
              </div>

              <div style={dividerStyle()} />

              {/* -- Footer & Pic toggle (per-slide) -- */}
              <div style={{ display: "flex", alignItems: "center", gap: SPACE[4], marginBottom: SPACE[2], marginTop: SPACE[2] }}>
                <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>FOOTER & PIC</label>
                <button onClick={function() { updateSlide(activeSlide, "showBrandName", !currentSlide.showBrandName); }}
                  style={toggleBtn(currentSlide.showBrandName)}>
                  {currentSlide.showBrandName ? "ON" : "OFF"}
                </button>
                {currentSlide.showBrandName && (
                  <>
                    <input value={currentSlide.brandNameText} onChange={function(e) { updateSlide(activeSlide, "brandNameText", e.target.value); }} placeholder="Brand name..."
                      style={Object.assign({}, inputStyle, { flex: 1, minWidth: 0, fontSize: 12, padding: SPACE[2] + "px " + SPACE[3] + "px" })} />
                    <div style={{ display: "flex", alignItems: "center", gap: SPACE[3] }}>
                      <div style={{ display: "flex", flexDirection: "column", gap: SPACE[2] }}>
                        <div style={{ display: "flex", alignItems: "center", gap: SPACE[3] }}>
                          <ColorPickerInline pickerKey={"s-" + activeSlide + "-bn"} value={currentSlide.brandNameColor || "#1a1a2e"} onChange={function(c) { updateSlide(activeSlide, "brandNameColor", c); }} openPicker={openPicker} setOpenPicker={setOpenPicker}
                            fontFamily={currentSlide.brandNameFontFamily} onFontFamilyChange={function(v) { updateSlide(activeSlide, "brandNameFontFamily", v, true); }}
                            bold={currentSlide.brandNameBold} onBoldChange={function(v) { updateSlide(activeSlide, "brandNameBold", v, true); }}
                            italic={currentSlide.brandNameItalic} onItalicChange={function(v) { updateSlide(activeSlide, "brandNameItalic", v, true); }} />
                          <span style={{ fontSize: 11, color: SURFACE.secondary, fontWeight: 600 }}>Text</span>
                        </div>
                        <div style={{ display: "flex", alignItems: "center", gap: SPACE[3] }}>
                          <ColorPickerInline pickerKey={"s-" + activeSlide + "-footerBase"} value={currentSlide.footerBg || "#ffffff"} onChange={function(c) { updateSlide(activeSlide, "footerBg", c); }} openPicker={openPicker} setOpenPicker={setOpenPicker} />
                          <span style={{ fontSize: 11, color: SURFACE.secondary, fontWeight: 600 }}>Base</span>
                        </div>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: 0, background: SURFACE.input, borderRadius: RADIUS.sm, border: "1px solid " + SURFACE.border, height: SIZE.stepper, overflow: "hidden" }}>
                        <button onClick={function() { if (sizes.brandName > 12) setSize("brandName", sizes.brandName - 1); }}
                          style={{ minWidth: SIZE.stepper, minHeight: SIZE.stepper, border: "none", background: "transparent", color: SURFACE.muted, cursor: "pointer", fontSize: 14, padding: 0, lineHeight: SIZE.stepper + "px" }}>{"\u2212"}</button>
                        <input value={sizes.brandName} onChange={function(e) { var v = parseInt(e.target.value, 10); if (!isNaN(v)) setSize("brandName", Math.max(12, Math.min(60, v))); }}
                          style={{ width: SIZE.stepperInput, height: SIZE.stepper, border: "none", borderLeft: "1px solid " + SURFACE.border, borderRight: "1px solid " + SURFACE.border, background: "transparent", color: SURFACE.dimmed, fontSize: 11, fontFamily: "monospace", textAlign: "center", padding: 0, outline: "none" }} />
                        <button onClick={function() { if (sizes.brandName < 60) setSize("brandName", sizes.brandName + 1); }}
                          style={{ minWidth: SIZE.stepper, minHeight: SIZE.stepper, border: "none", background: "transparent", color: SURFACE.muted, cursor: "pointer", fontSize: 14, padding: 0, lineHeight: SIZE.stepper + "px" }}>+</button>
                      </div>
                    </div>
                  </>
                )}
              </div>

              {/* -- Top Corner toggle (per-slide) -- */}
              <div style={dividerStyle()} />
              <div style={{ display: "flex", alignItems: "center", gap: SPACE[4], marginBottom: SPACE[2], marginTop: SPACE[2] }}>
                <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>TOP CORNER</label>
                <button onClick={function() { updateSlide(activeSlide, "showTopCorner", !currentSlide.showTopCorner); }}
                  style={toggleBtn(currentSlide.showTopCorner)}>
                  {currentSlide.showTopCorner ? "ON" : "OFF"}
                </button>
                {currentSlide.showTopCorner && (<>
                  <input value={currentSlide.topCornerText} onChange={function(e) { updateSlide(activeSlide, "topCornerText", e.target.value); }} placeholder="Top corner..."
                    style={Object.assign({}, inputStyle, { flex: 1, minWidth: 0, fontSize: 12, padding: SPACE[2] + "px " + SPACE[3] + "px" })} />
                  <SizeControl sizeKey="topCorner" min={8} max={60} sizes={sizes} setSize={setSize}
                    swatchLabel="Text"
                    colorVal={currentSlide.topCornerColor} colorSet={function(c) { updateSlide(activeSlide, "topCornerColor", c); }}
                    colorPickerKey={"s-" + activeSlide + "-tc"} openPicker={openPicker} setOpenPicker={setOpenPicker}
                    opacityVal={currentSlide.topCornerOpacity} opacitySet={function(v) { updateSlide(activeSlide, "topCornerOpacity", v); }}
                    fontFamily={currentSlide.topCornerFontFamily} fontFamilySet={function(v) { updateSlide(activeSlide, "topCornerFontFamily", v, true); }}
                    boldVal={currentSlide.topCornerBold} boldSet={function(v) { updateSlide(activeSlide, "topCornerBold", v, true); }}
                    italicVal={currentSlide.topCornerItalic} italicSet={function(v) { updateSlide(activeSlide, "topCornerItalic", v, true); }} />
                </>)}
              </div>

              {/* -- Bottom Corner toggle (per-slide) -- */}
              <div style={dividerStyle()} />
              <div style={{ display: "flex", alignItems: "center", gap: SPACE[4], marginBottom: SPACE[2], marginTop: SPACE[2] }}>
                <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>BOTTOM CORNER</label>
                <button onClick={function() { updateSlide(activeSlide, "showBottomCorner", !currentSlide.showBottomCorner); }}
                  style={toggleBtn(currentSlide.showBottomCorner)}>
                  {currentSlide.showBottomCorner ? "ON" : "OFF"}
                </button>
                {currentSlide.showBottomCorner && (<>
                  <input value={currentSlide.bottomCornerText} onChange={function(e) { updateSlide(activeSlide, "bottomCornerText", e.target.value); }} placeholder="Bottom corner..."
                    style={Object.assign({}, inputStyle, { flex: 1, minWidth: 0, fontSize: 12, padding: SPACE[2] + "px " + SPACE[3] + "px" })} />
                  <SizeControl sizeKey="bottomCorner" min={10} max={60} sizes={sizes} setSize={setSize}
                    swatchLabel="Text"
                    colorVal={currentSlide.bottomCornerColor} colorSet={function(c) { updateSlide(activeSlide, "bottomCornerColor", c); }}
                    colorPickerKey={"s-" + activeSlide + "-bc"} openPicker={openPicker} setOpenPicker={setOpenPicker}
                    opacityVal={currentSlide.bottomCornerOpacity} opacitySet={function(v) { updateSlide(activeSlide, "bottomCornerOpacity", v); }}
                    fontFamily={currentSlide.bottomCornerFontFamily} fontFamilySet={function(v) { updateSlide(activeSlide, "bottomCornerFontFamily", v, true); }}
                    boldVal={currentSlide.bottomCornerBold} boldSet={function(v) { updateSlide(activeSlide, "bottomCornerBold", v, true); }}
                    italicVal={currentSlide.bottomCornerItalic} italicSet={function(v) { updateSlide(activeSlide, "bottomCornerItalic", v, true); }} />
                </>)}
              </div>

              {/* -- Heading toggle (per-slide) -- */}
              <div style={dividerStyle()} />
              <div style={{ display: "flex", alignItems: "center", gap: SPACE[4], marginBottom: SPACE[2], marginTop: SPACE[2] }}>
                <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>HEADING</label>
                <button onClick={function() { updateSlide(activeSlide, "showHeading", !currentSlide.showHeading); }}
                  style={toggleBtn(currentSlide.showHeading)}>
                  {currentSlide.showHeading ? "ON" : "OFF"}
                </button>
                {currentSlide.showCards && (
                  <button onClick={function() { updateSlide(activeSlide, "showCardChecks", !(currentSlide.showCardChecks !== false), true); }}
                    title="Card checkmarks"
                    style={Object.assign({}, smallBtnStyle, { marginLeft: SPACE[2], padding: SPACE[1] + "px " + SPACE[4] + "px", background: (currentSlide.showCardChecks !== false) ? CLR.activeOverlay2 : SURFACE.input, color: (currentSlide.showCardChecks !== false) ? CLR.primaryLight : SURFACE.dimmed, cursor: "pointer", fontSize: 10, lineHeight: "14px" })}>
                    Checks
                  </button>
                )}
                {currentSlide.showHeading && (
                  <>
                    <div style={{ flex: 1 }} />
                    <SizeControl sizeKey="heading" min={24} max={160} sizes={sizes} setSize={setSize}
                      swatchLabel="Text"
                      colorVal={currentSlide.titleColor} colorSet={function(c) { updateSlide(activeSlide, "titleColor", c); }}
                      colorPickerKey={"s-" + activeSlide + "-title"} openPicker={openPicker} setOpenPicker={setOpenPicker}
                      fontFamily={currentSlide.titleFontFamily} fontFamilySet={function(v) { updateSlide(activeSlide, "titleFontFamily", v, true); }}
                      boldVal={currentSlide.titleBold} boldSet={function(v) { updateSlide(activeSlide, "titleBold", v, true); }}
                      italicVal={currentSlide.titleItalic} italicSet={function(v) { updateSlide(activeSlide, "titleItalic", v, true); }} />
                  </>
                )}
              </div>
              {currentSlide.showHeading && (
                <div style={{ marginBottom: SPACE[4], paddingLeft: SPACE[4], borderLeft: "2px solid " + SURFACE.muted }}>
                  <textarea value={currentSlide.title} onChange={function(e) { updateSlide(activeSlide, "title", e.target.value); var el = e.target; el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; }} placeholder="Heading..." rows={1}
                    ref={function(el) { if (el) { el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; } }}
                    style={Object.assign({}, inputStyle, { marginBottom: SPACE[2], fontSize: 12, lineHeight: "1.5", resize: "none", overflow: "hidden" })} />
                </div>
              )}

              {/* Body | Cards toggle */}
              <div style={dividerStyle()} />
              <div style={{ display: "flex", alignItems: "center", marginTop: SPACE[2], marginBottom: SPACE[2], gap: SPACE[2] }}>
                <span onClick={function() { updateSlide(activeSlide, "showCards", false); }}
                  style={{ fontWeight: 600, fontSize: 13, color: !currentSlide.showCards ? GREEN : SURFACE.muted, letterSpacing: 0.5, cursor: "pointer" }}>BODY</span>
                <span style={{ color: SURFACE.pipeSep, margin: "0 " + SPACE[2] + "px", fontSize: 14 }}>|</span>
                <span onClick={function() { updateSlide(activeSlide, "showCards", true); }}
                  style={{ fontWeight: 600, fontSize: 13, color: currentSlide.showCards ? GREEN : SURFACE.muted, letterSpacing: 0.5, cursor: "pointer" }}>CARDS</span>
                <div style={{ flex: 1 }} />
                <div style={{ display: "flex", alignItems: "center", gap: SPACE[3] }}>
                  <div style={{ display: "flex", flexDirection: "column", gap: SPACE[2] }}>
                    <div style={{ display: "flex", alignItems: "center", gap: SPACE[3] }}>
                      <ColorPickerInline pickerKey={"s-" + activeSlide + (currentSlide.showCards ? "-cardtext" : "-body")} value={currentSlide.showCards ? (currentSlide.cardTextColor || "#333333") : (currentSlide.bodyColor || "#ffffff")} onChange={function(c) { updateSlide(activeSlide, currentSlide.showCards ? "cardTextColor" : "bodyColor", c); }} openPicker={openPicker} setOpenPicker={setOpenPicker}
                        fontFamily={currentSlide.showCards ? currentSlide.cardFontFamily : currentSlide.bodyFontFamily} onFontFamilyChange={function(v) { updateSlide(activeSlide, currentSlide.showCards ? "cardFontFamily" : "bodyFontFamily", v, true); }}
                        bold={currentSlide.showCards ? currentSlide.cardBold : currentSlide.bodyBold} onBoldChange={function(v) { updateSlide(activeSlide, currentSlide.showCards ? "cardBold" : "bodyBold", v, true); }}
                        italic={currentSlide.showCards ? currentSlide.cardItalic : currentSlide.bodyItalic} onItalicChange={function(v) { updateSlide(activeSlide, currentSlide.showCards ? "cardItalic" : "bodyItalic", v, true); }} />
                      <span style={{ fontSize: 11, color: SURFACE.secondary, fontWeight: 600 }}>Text</span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: SPACE[3], opacity: currentSlide.showCards ? 1 : 0.35 }}>
                      <ColorPickerInline pickerKey={"s-" + activeSlide + "-cardbg"} value={currentSlide.cardBgColor || "#ffffff"} onChange={function(c) { updateSlide(activeSlide, "cardBgColor", c); }} openPicker={openPicker} setOpenPicker={setOpenPicker} disabled={!currentSlide.showCards} />
                      <span style={{ fontSize: 11, color: SURFACE.secondary, fontWeight: 600 }}>Base</span>
                    </div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 0, background: SURFACE.input, borderRadius: RADIUS.sm, border: "1px solid " + SURFACE.border, height: SIZE.stepper, overflow: "hidden" }}>
                    <button onClick={function() { var sk = currentSlide.showCards ? "cardText" : "body"; if (sizes[sk] > 12) setSize(sk, sizes[sk] - 1); }}
                      style={{ minWidth: SIZE.stepper, minHeight: SIZE.stepper, border: "none", background: "transparent", color: SURFACE.muted, cursor: "pointer", fontSize: 14, padding: 0, lineHeight: SIZE.stepper + "px" }}>{"\u2212"}</button>
                    <input value={sizes[currentSlide.showCards ? "cardText" : "body"]} onChange={function(e) { var v = parseInt(e.target.value, 10); if (!isNaN(v)) setSize(currentSlide.showCards ? "cardText" : "body", Math.max(12, Math.min(100, v))); }}
                      style={{ width: SIZE.stepperInput, height: SIZE.stepper, border: "none", borderLeft: "1px solid " + SURFACE.border, borderRight: "1px solid " + SURFACE.border, background: "transparent", color: SURFACE.dimmed, fontSize: 11, fontFamily: "monospace", textAlign: "center", padding: 0, outline: "none" }} />
                    <button onClick={function() { var sk = currentSlide.showCards ? "cardText" : "body"; if (sizes[sk] < 100) setSize(sk, sizes[sk] + 1); }}
                      style={{ minWidth: SIZE.stepper, minHeight: SIZE.stepper, border: "none", background: "transparent", color: SURFACE.muted, cursor: "pointer", fontSize: 14, padding: 0, lineHeight: SIZE.stepper + "px" }}>+</button>
                  </div>
                </div>
              </div>

              {/* Body content */}
              {!currentSlide.showCards && (
                <div>
                  <textarea value={currentSlide.body} onChange={function(e) { updateSlide(activeSlide, "body", e.target.value); var el = e.target; el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; }} rows={3}
                    ref={function(el) { if (el) { el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; } }}
                    style={Object.assign({}, inputStyle, { fontSize: 13, resize: "none", overflow: "hidden", maxHeight: "50vh", overflowY: "auto" })} />
                </div>
              )}

              {/* Cards content */}
              {currentSlide.showCards && (
                <div>
                  {currentSlide.cards.map(function(c, i) {
                    return (
                      <div key={i} style={{ display: "flex", gap: SPACE[4], marginBottom: SPACE[3], alignItems: "center" }}>
                        <textarea value={c} onChange={function(e) { slideMgmt.updateSlideCard(activeSlide, i, e.target.value); var el = e.target; el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; }} placeholder={"Card " + (i + 1) + "..."} rows={1}
                          ref={function(el) { if (el) { el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; } }}
                          style={Object.assign({}, inputStyle, { padding: SPACE[3] + "px " + SPACE[5] + "px", fontSize: 12, resize: "none", overflow: "hidden", maxHeight: "50vh", overflowY: "auto" })} />
                        {currentSlide.cards.length > 1 && (
                          <button onClick={function() { slideMgmt.removeSlideCard(activeSlide, i); }} style={{ background: "none", border: "none", color: CLR.danger, cursor: "pointer", fontSize: 18, padding: SPACE[2] }}>{"\u00d7"}</button>
                        )}
                      </div>
                    );
                  })}
                  {currentSlide.cards.length < 5 && (
                    <button onClick={function() { slideMgmt.addSlideCard(activeSlide); }} style={{ background: SURFACE.input, border: "1px dashed " + SURFACE.border, color: SURFACE.tertiary, padding: SPACE[3] + "px " + SPACE[6] + "px", borderRadius: RADIUS.lg, cursor: "pointer", fontSize: 12, marginTop: SPACE[2] }}>+ Add Card</button>
                  )}
                </div>
              )}
            </div>
          )}

          </div>
        </div>

          {/* -- RIGHT PANE: Canvas preview -- */}
          <div style={{ gridArea: "preview", display: "flex", flexDirection: "column", minWidth: 0, minHeight: 0 }}>
            <canvas ref={canvasRef} width={W} height={H}
              style={{ maxWidth: "100%", minHeight: 0, flex: "0 1 auto", borderRadius: RADIUS.xxl, border: "1px solid " + SURFACE.canvasBorder, display: "block", objectFit: "contain", aspectRatio: W + "/" + H }} />
          </div>
        </div>
      </div>

      {/* Confirm dialog overlay */}
      {confirmDialog && (
        <div style={dialogOverlay()}
          onClick={function() { setConfirmDialog(null); }}>
          <div style={Object.assign({}, dialogBox(SIZE.dialogSm), { textAlign: "center" })}
            onClick={function(e) { e.stopPropagation(); }}>
            <p style={{ color: SURFACE.text, fontSize: 13, margin: "0 0 " + SPACE[7] + "px 0", lineHeight: 1.4 }}>{confirmDialog.message}</p>
            <div style={{ display: "flex", gap: SPACE[5], justifyContent: "center" }}>
              <button onClick={function() { setConfirmDialog(null); }}
                style={dialogBtn(false)}>
                Cancel
              </button>
              <button onClick={function() { confirmDialog.onConfirm(); setConfirmDialog(null); }}
                style={dialogBtn(true)}>
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Save Preset dialog overlay */}
      {presets.presetDialog && presets.presetDialog.type === "save" && (
        <div style={dialogOverlay()}
          onClick={function() { presets.setPresetDialog(null); }}>
          <div style={Object.assign({}, dialogBox(SIZE.dialogMd), { textAlign: "left" })}
            onClick={function(e) { e.stopPropagation(); }}>
            <p style={{ color: SURFACE.text, fontSize: 14, fontWeight: 600, margin: "0 0 " + SPACE[6] + "px 0" }}>Save Preset</p>
            <label style={{ fontSize: 11, color: SURFACE.tertiary, display: "block", marginBottom: SPACE[2] }}>Preset name</label>
            <input value={presets.presetName} onChange={function(e) { presets.setPresetName(e.target.value); }}
              placeholder="My Carousel"
              style={inputStyle} />
            <div style={{ display: "flex", alignItems: "center", gap: SPACE[4], marginTop: SPACE[6], marginBottom: SPACE[7] }}>
              <button onClick={function() { presets.setPresetIncludeImages(!presets.presetIncludeImages); }}
                style={toggleBtn(presets.presetIncludeImages)}>
                {presets.presetIncludeImages ? "ON" : "OFF"}
              </button>
              <span style={{ fontSize: 12, color: SURFACE.subtle }}>Include images (larger file)</span>
            </div>
            <div style={{ display: "flex", gap: SPACE[5], justifyContent: "flex-end" }}>
              <button onClick={function() { presets.setPresetDialog(null); }}
                style={dialogBtn(false)}>
                Cancel
              </button>
              <button onClick={function() { presets.downloadPreset(presets.presetName, presets.presetIncludeImages); presets.setPresetDialog(null); }}
                style={dialogBtn(true)}>
                Save
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
