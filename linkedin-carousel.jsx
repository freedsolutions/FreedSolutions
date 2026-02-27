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
  return "rgba(" + r + "," + g + "," + b + "," + (opacity / 100) + ")";
}

// ---------------------------------------
// Background renderers
// ---------------------------------------

function drawSolidBg(ctx, color) {
  ctx.fillStyle = color;
  ctx.fillRect(0, 0, W, H);
}

function drawGeoBg(ctx, baseColor, lineColor) {
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
  var spheres = [
    { x: -30, y: 220, r: 170, a: 0.10 },
    { x: -10, y: 800, r: 150, a: 0.08 },
    { x: 740, y: 130, r: 110, a: 0.06 },
    { x: 700, y: 830, r: 130, a: 0.07 },
  ];
  for (var si = 0; si < spheres.length; si++) {
    var s = spheres[si];
    ctx.fillStyle = "rgba(" + lcR + "," + lcG + "," + lcB + "," + s.a + ")";
    ctx.beginPath();
    ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = "rgba(" + lcR + "," + lcG + "," + lcB + "," + (s.a * 0.6) + ")";
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
    ctx.stroke();
  }
  ctx.strokeStyle = "rgba(" + lcR + "," + lcG + "," + lcB + ",0.06)";
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

function drawCustomBg(ctx, img) {
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

function renderBg(ctx, bgType, solidColor, customImg, geoLines, geoEnabled) {
  if (bgType === "custom" && customImg) {
    drawCustomBg(ctx, customImg);
  } else {
    drawSolidBg(ctx, solidColor);
    if (geoEnabled) {
      drawGeoBg(ctx, null, geoLines);
    }
  }
}

// ---------------------------------------
// Text helpers
// ---------------------------------------

function wrapText(ctx, text, maxWidth, fontSize, fontWeight) {
  fontWeight = fontWeight || "bold";
  ctx.font = fontWeight + " " + fontSize + 'px "Helvetica Neue", Helvetica, Arial, sans-serif';
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

function renderLineWithAccents(ctx, line, x, y, fontSize, baseWeight, baseColor, accentColor, markers, lineOffset) {
  if (!markers || markers.length === 0) {
    ctx.font = baseWeight + " " + fontSize + 'px "Helvetica Neue", Helvetica, Arial, sans-serif';
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
    ctx.font = baseWeight + " " + fontSize + 'px "Helvetica Neue", Helvetica, Arial, sans-serif';
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
      ctx.font = "900 " + fontSize + 'px "Helvetica Neue", Helvetica, Arial, sans-serif';
      ctx.fillStyle = accentColor;
    } else {
      ctx.font = baseWeight + " " + fontSize + 'px "Helvetica Neue", Helvetica, Arial, sans-serif';
      ctx.fillStyle = baseColor;
    }
    ctx.fillText(seg.text, xPos, y);
    xPos += ctx.measureText(seg.text).width;
  }
}

// ---------------------------------------
// Overlays: footer, corners, border frame
// ---------------------------------------

function drawCenteredFooter(ctx, profileImg, name, borderBottom, footerBg, footerText, textSize, opacity) {
  var prevAlpha = ctx.globalAlpha;
  ctx.globalAlpha = (opacity != null ? opacity : 100) / 100;
  var badgeH = FOOTER_BADGE_H;
  var badgeW = 220;
  var badgeX = (W - badgeW) / 2;
  var badgeY = borderBottom - badgeH / 2;

  ctx.fillStyle = footerBg || "#ffffff";
  ctx.beginPath();
  ctx.roundRect(badgeX, badgeY, badgeW, badgeH, 12);
  ctx.fill();

  ctx.fillStyle = footerText || "#1a1a2e";
  ctx.font = 'bold ' + (textSize || 20) + 'px "Helvetica Neue", Helvetica, Arial, sans-serif';
  var tw = ctx.measureText(name).width;
  ctx.fillText(name, (W - tw) / 2, badgeY + 31);

  if (profileImg) {
    var picSize = FOOTER_PIC_SIZE;
    var picX = W / 2;
    var picY = badgeY + badgeH + picSize / 2 - 8;
    ctx.save();
    ctx.beginPath();
    ctx.arc(picX, picY, picSize / 2, 0, Math.PI * 2);
    ctx.clip();
    ctx.drawImage(profileImg, picX - picSize / 2, picY - picSize / 2, picSize, picSize);
    ctx.restore();
    ctx.strokeStyle = "rgba(255,255,255,0.5)";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.arc(picX, picY, picSize / 2, 0, Math.PI * 2);
    ctx.stroke();
  }
  ctx.globalAlpha = prevAlpha;
}

function drawTopCorner(ctx, text, color, opacity, size) {
  ctx.font = '700 ' + (size || 13) + 'px "Helvetica Neue", Helvetica, Arial, sans-serif';
  ctx.fillStyle = hexToRgba(color || "#ffffff", opacity != null ? opacity : 40);
  ctx.fillText(text.toUpperCase(), MARGIN, MARGIN + (size || 13));
}

function drawBottomCorner(ctx, text, color, opacity, size) {
  ctx.font = '600 ' + (size || 16) + 'px "Helvetica Neue", Helvetica, Arial, sans-serif';
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
    var badgeW = 220;
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

function drawScreenshot(ctx, screenshot, x, y, w, h, scale) {
  if (!screenshot) {
    ctx.strokeStyle = "rgba(255,255,255,0.1)";
    ctx.lineWidth = 1;
    ctx.setLineDash([6, 6]);
    ctx.beginPath();
    ctx.roundRect(x, y, w, h, 12);
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
  ctx.roundRect(x, y, w, h, 12);
  ctx.clip();
  ctx.drawImage(screenshot, dx, dy, dw, dh);
  ctx.restore();

  ctx.strokeStyle = "rgba(255,255,255,0.1)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.roundRect(x, y, w, h, 12);
  ctx.stroke();
}

// ---------------------------------------
// Unified slide content renderer
// ---------------------------------------

function renderSlideContent(ctx, slide, screenshot, colors, sizes, scale, frameTop, frameBottom) {
  var pad = 80;
  var innerPad = 20;
  var topY = Math.max(pad, (frameTop || 0) + innerPad);
  var maxW = W - pad * 2;

  var ty = topY;
  if (slide.showHeading !== false) {
    var headingParsed = extractAccentMarkers(slide.title || "");
    ctx.font = 'bold ' + sizes.heading + 'px "Helvetica Neue", Helvetica, Arial, sans-serif';
    var titleLines = wrapText(ctx, headingParsed.cleanText, maxW, sizes.heading, "bold");
    ty = topY + sizes.heading * 1.22;
    var hOffset = 0;
    for (var i = 0; i < titleLines.length; i++) {
      renderLineWithAccents(ctx, titleLines[i], pad, ty, sizes.heading, "bold", slide.titleColor || colors.text, colors.accent, headingParsed.markers, hOffset);
      hOffset += titleLines[i].length + 1;
      ty += sizes.heading * 1.22;
    }

    if (slide.showAccentBar !== false && (!slide.showCards || !slide.cards || slide.cards.length === 0)) {
      ctx.fillStyle = colors.accent;
      ctx.fillRect(pad, ty + 10, 50, 3);
    }
  }

  if (slide.showCards && slide.cards && slide.cards.length > 0) {
    var cardStartY = (slide.showHeading !== false) ? ty + 45 : ty + 60;
    var cardPadV = 20;
    var gap = 20;
    var textPadding = 40;
    var cardContentW = maxW - 40;
    var cardsParsed = [];
    for (var cpi = 0; cpi < slide.cards.length; cpi++) {
      cardsParsed.push(extractAccentMarkers(slide.cards[cpi] || ""));
    }
    var cardHeights = [];
    for (var ch = 0; ch < cardsParsed.length; ch++) {
      if (!cardsParsed[ch].cleanText.trim()) { cardHeights.push(0); continue; }
      var chLines = wrapText(ctx, cardsParsed[ch].cleanText, cardContentW, sizes.cardText, "600");
      var textH = chLines.length * (sizes.cardText + 6);
      cardHeights.push(Math.max(80, textH + cardPadV * 2 + 10));
    }
    var runningY = cardStartY;
    for (var ci = 0; ci < cardsParsed.length; ci++) {
      if (!cardsParsed[ci].cleanText.trim()) continue;
      var cy = runningY;
      var cardH = cardHeights[ci];
      ctx.fillStyle = slide.cardBgColor || colors.cardBg;
      ctx.beginPath();
      ctx.roundRect(pad - 10 + textPadding, cy, maxW - textPadding * 2 + 20, cardH, 16);
      ctx.fill();
      ctx.fillStyle = colors.accent;
      ctx.beginPath();
      ctx.arc(pad + textPadding + 18, cy - 14, 22, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = slide.cardBgColor || colors.cardBg;
      ctx.lineWidth = 3;
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      ctx.beginPath();
      ctx.moveTo(pad + textPadding + 8, cy - 14);
      ctx.lineTo(pad + textPadding + 16, cy - 6);
      ctx.lineTo(pad + textPadding + 30, cy - 22);
      ctx.stroke();
      ctx.font = '600 ' + sizes.cardText + 'px "Helvetica Neue", Helvetica, Arial, sans-serif';
      var cardLines = wrapText(ctx, cardsParsed[ci].cleanText, cardContentW, sizes.cardText, "600");
      var cOffset = 0;
      for (var cli = 0; cli < cardLines.length; cli++) {
        renderLineWithAccents(ctx, cardLines[cli], pad + textPadding + 20, cy + 38 + cli * (sizes.cardText + 6), sizes.cardText, "600", slide.cardTextColor || colors.cardText, colors.accent, cardsParsed[ci].markers, cOffset);
        cOffset += cardLines[cli].length + 1;
      }
      runningY += cardH + gap;
    }
    ty = runningY;
  } else if (slide.body) {
    var bodyLines = (slide.body || "").split("\n");
    var bodyY = (slide.showHeading !== false) ? ty + 100 : ty + 60;
    for (var bli = 0; bli < bodyLines.length; bli++) {
      var rawLine = bodyLines[bli];
      if (rawLine.trim() === "" || rawLine.replace(/\*\*(.+?)\*\*/g, "$1").trim() === "") {
        bodyY += sizes.body * 0.6;
      } else {
        var lineParsed = extractAccentMarkers(rawLine);
        var wrapped = wrapText(ctx, lineParsed.cleanText, maxW, sizes.body, "600");
        var bOffset = 0;
        for (var wi = 0; wi < wrapped.length; wi++) {
          renderLineWithAccents(ctx, wrapped[wi], pad, bodyY, sizes.body, "600", slide.bodyColor || colors.accent, colors.accent, lineParsed.markers, bOffset);
          bOffset += wrapped[wi].length + 1;
          bodyY += sizes.body * 1.4;
        }
      }
    }
    ty = bodyY + 10;
  }

  if (slide.showScreenshot) {
    var bottomBound = frameBottom ? frameBottom - 20 : H - 80;
    var ssY = Math.max(ty + 20, 420);
    var ssW = maxW;
    var ssH = bottomBound - ssY;
    if (ssH > 60) {
      drawScreenshot(ctx, screenshot || null, pad, ssY, ssW, ssH, scale);
    }
  }
}

// ---------------------------------------
// Top-level render orchestrator (pure function)
// ---------------------------------------

function renderSlideToCanvas(ctx, slideIndex, seriesSlides, slideAssets, colors, sizes, profileImg) {
  ctx.clearRect(0, 0, W, H);
  var slide = seriesSlides[slideIndex] || seriesSlides[0];

  // Resolve custom bg image
  var customImg = (slide.bgType === "custom" && slide.customBgImage) ? slide.customBgImage : null;

  renderBg(ctx, slide.bgType, slide.solidColor, customImg, slide.geoLines, slide.geoEnabled);

  var renderColors = {
    heading: colors.heading,
    body: colors.body,
    text: colors.heading,
    accent: slide.accentColor,
    border: hexToRgba(slide.borderColor, slide.borderOpacity),
    cardBg: colors.cardBg,
    cardText: colors.cardText,
  };

  var topCornerOffset = (slide.showTopCorner && slide.topCornerText) ? sizes.topCorner * 2.2 : 0;
  var borderTop = MARGIN + topCornerOffset + 8;
  var borderBottom = slide.showBrandName ? H - MARGIN - FOOTER_PIC_SIZE + 8 - FOOTER_BADGE_H / 2 : H - MARGIN - 16;

  if (slide.showTopCorner && slide.topCornerText) {
    drawTopCorner(ctx, slide.topCornerText, slide.topCornerColor, slide.topCornerOpacity, sizes.topCorner);
  }

  var asset = slideAssets[slideIndex] || { image: null, name: null, scale: 1 };
  renderSlideContent(ctx, slide, asset.image, renderColors, sizes, asset.scale, borderTop, borderBottom);

  if (slide.frameEnabled) {
    drawBorderFrame(ctx, borderTop, borderBottom, slide.showBrandName, renderColors.border);
  }

  if (slide.showBrandName) {
    drawCenteredFooter(ctx, profileImg, slide.brandNameText, borderBottom, slide.footerBg, slide.brandNameColor, sizes.brandName, 100);
  }

  if (slide.showBottomCorner && slide.bottomCornerText) {
    drawBottomCorner(ctx, slide.bottomCornerText, slide.bottomCornerColor, slide.bottomCornerOpacity, sizes.bottomCorner);
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
    bodyColor: "#22c55e",
    showCards: false,
    cards: ["Card 1"],
    cardTextColor: "#333333",
    cardBgColor: "#ffffff",
    showScreenshot: false,
    showBrandName: true,
    brandNameText: "Brand Name",
    brandNameColor: "#1a1a2e",
    showTopCorner: true,
    topCornerText: "LABEL",
    topCornerColor: "#ffffff",
    topCornerOpacity: 40,
    showBottomCorner: false,
    bottomCornerText: "Brand Name",
    bottomCornerColor: "#ffffff",
    bottomCornerOpacity: 35,
    solidColor: "#1e1e2e",
    bgType: "solid",
    customBgImage: null,
    customBgName: null,
    geoEnabled: true,
    geoLines: "#a0a0af",
    frameEnabled: true,
    accentColor: "#22c55e",
    borderColor: "#ffffff",
    borderOpacity: 25,
    footerBg: "#ffffff"
  };
}

// ---------------------------------------
// Main Component
// ---------------------------------------

export default function App() {
  var canvasRef = useRef(null);
  var profilePicInputRef = useRef(null);
  var screenshotInputRef = useRef(null);
  var customBgInputRef = useRef(null);
  var renderTimerRef = useRef(null);
  var pdfUrlRef = useRef(null);
  var [isCustomProfilePic, setIsCustomProfilePic] = useState(false);
  var [confirmDialog, setConfirmDialog] = useState(null);
  var [pdfDownload, setPdfDownload] = useState(null);
  var [pdfError, setPdfError] = useState("");

  // Preset save/load state
  var presetInputRef = useRef(null);
  var presetUrlRef = useRef(null);
  var [presetDownload, setPresetDownload] = useState(null);
  var [presetDialog, setPresetDialog] = useState(null);
  var [presetName, setPresetName] = useState("");
  var [presetIncludeImages, setPresetIncludeImages] = useState(true);



  // Colors (only non-background colors remain here)
  var [colors] = useState({
    heading: "#ffffff",
    body: "#ffffff",
    cardBg: "#ffffff",
    cardText: "#333333",
  });
  var [openPicker, setOpenPicker] = useState(null);

  // Font sizes
  var [sizes, setSizes] = useState({
    heading: 48,
    body: 38,
    cardText: 22,
    topCorner: 13,
    bottomCorner: 16,
    brandName: 20,
  });

  var setSize = function(key, val) {
    setSizes(function(prev) {
      var next = Object.assign({}, prev);
      next[key] = val;
      return next;
    });
  };

  // Close picker on outside click
  useEffect(function() {
    if (!openPicker) return;
    var handler = function(e) {
      var picker = document.querySelector('[data-picker="' + openPicker + '"]');
      if (picker && !picker.contains(e.target)) {
        setOpenPicker(null);
      }
    };
    document.addEventListener("mousedown", handler);
    return function() { document.removeEventListener("mousedown", handler); };
  }, [openPicker]);

  // Slides state
  var [seriesSlides, setSeriesSlides] = useState([makeDefaultSlide("Heading", "Body text")]);
  var [activeSlide, setActiveSlide] = useState(0);
  var [slideAssets, setSlideAssets] = useState({});
  // shape: { [slideIndex]: { image: Image|null, name: string|null, scale: number } }

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

  // Drag-to-reorder state
  var [dragFrom, setDragFrom] = useState(null);
  var [dragOver, setDragOver] = useState(null);

  // Export prefix
  var [exportPrefix, setExportPrefix] = useState("linkedin-slide");

  // Image loading - no default profile pic; starts empty, user uploads
  var [profileImg, setProfileImg] = useState(null);

  // Filename tracking
  var [profilePicName, setProfilePicName] = useState(null);

  var handleCustomUpload = function(e) {
    var file = e.target.files[0];
    if (!file) return;
    var fileName = file.name;
    var reader = new FileReader();
    reader.onload = function(ev) {
      var img = new Image();
      img.onload = function() {
        setSeriesSlides(function(prev) {
          return prev.map(function(s, i) {
            if (i !== activeSlide) return s;
            return Object.assign({}, s, { customBgImage: img, customBgName: fileName, bgType: "custom" });
          });
        });
      };
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
      };
      img.src = ev.target.result;
    };
    reader.readAsDataURL(file);
  };

  var handleProfilePicUpload = function(e) {
    var file = e.target.files[0];
    if (!file) return;
    setProfilePicName(file.name);
    var reader = new FileReader();
    reader.onload = function(ev) {
      var img = new Image();
      img.onload = function() { setProfileImg(img); setIsCustomProfilePic(true); };
      img.src = ev.target.result;
    };
    reader.readAsDataURL(file);
  };

  var removeProfilePic = function() {
    if (profilePicInputRef.current) { profilePicInputRef.current.value = ""; }
    setIsCustomProfilePic(false);
    setProfilePicName(null);
    setProfileImg(null);
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
  };

  // Screenshot metadata is unified in slideAssets.

  // --- Preset serialize/deserialize ---

  var PRESET_SLIDE_KEYS = [
    "title", "showHeading", "showAccentBar", "body",
    "titleColor", "bodyColor", "showCards", "cards",
    "cardTextColor", "cardBgColor", "showScreenshot",
    "showBrandName", "brandNameText", "brandNameColor",
    "showTopCorner", "topCornerText", "topCornerColor", "topCornerOpacity",
    "showBottomCorner", "bottomCornerText", "bottomCornerColor", "bottomCornerOpacity",
    "solidColor", "bgType", "geoEnabled", "geoLines",
    "frameEnabled", "accentColor", "borderColor", "borderOpacity", "footerBg"
  ];

  var serializePreset = function(name, includeImages) {
    var images = {};

    // Profile pic
    if (profileImg && profileImg.src) {
      images["profile"] = {
        name: profilePicName || "profile.jpg",
        dataUrl: includeImages ? profileImg.src : null
      };
    }

    // Per-slide images
    var serializedSlides = seriesSlides.map(function(s, i) {
      var slide = {};
      for (var k = 0; k < PRESET_SLIDE_KEYS.length; k++) {
        var key = PRESET_SLIDE_KEYS[k];
        if (key === "cards") {
          slide[key] = s[key] ? s[key].slice() : ["Card 1"];
        } else {
          slide[key] = s[key];
        }
      }

      // Custom bg -> ref
      slide.customBgRef = null;
      if (s.customBgImage && s.customBgImage.src) {
        var bgRef = "bg-" + i;
        slide.customBgRef = bgRef;
        images[bgRef] = {
          name: s.customBgName || ("bg-" + i + ".jpg"),
          dataUrl: includeImages ? s.customBgImage.src : null
        };
      }

      // Screenshot -> ref
      slide.screenshotRef = null;
      var asset = slideAssets[i];
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
      exportPrefix: exportPrefix,
      sizes: Object.assign({}, sizes),
      slides: serializedSlides,
      profilePicRef: (profileImg && profileImg.src) ? "profile" : null,
      images: images
    };
  };

  var loadPresetData = function(data) {
    // Restore sizes
    if (data.sizes) {
      setSizes(Object.assign({
        heading: 48, body: 38, cardText: 22,
        topCorner: 13, bottomCorner: 16, brandName: 20
      }, data.sizes));
    }

    // Restore export prefix
    if (data.exportPrefix != null) {
      setExportPrefix(data.exportPrefix);
    }

    // Restore profile pic
    var profileRef = data.profilePicRef;
    var profileEntry = profileRef && data.images && data.images[profileRef];
    if (profileEntry && profileEntry.dataUrl) {
      var pImg = new Image();
      pImg.onload = function() {
        setProfileImg(pImg);
        setIsCustomProfilePic(true);
      };
      pImg.src = profileEntry.dataUrl;
      setProfilePicName(profileEntry.name || null);
    } else {
      setProfileImg(null);
      setIsCustomProfilePic(false);
      setProfilePicName(profileEntry ? profileEntry.name : null);
    }

    // Restore slides
    var newAssets = {};

    var newSlides = (data.slides || []).map(function(sd, i) {
      var slide = makeDefaultSlide(sd.title, sd.body);
      // Overwrite all serializable fields
      for (var k = 0; k < PRESET_SLIDE_KEYS.length; k++) {
        var key = PRESET_SLIDE_KEYS[k];
        if (sd[key] !== undefined) {
          slide[key] = key === "cards" ? (sd.cards || []).slice() : sd[key];
        }
      }

      // Custom bg image
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
              setSeriesSlides(function(prev) {
                return prev.map(function(s, si) {
                  if (si !== idx) return s;
                  return Object.assign({}, s, { customBgImage: bgImg });
                });
              });
            };
          })(i);
          bgImg.src = bgEntry.dataUrl;
        }
      }

      // Screenshot
      var ssRef = sd.screenshotRef;
      var ssEntry = ssRef && data.images && data.images[ssRef];
      if (ssEntry) {
        newAssets[i] = { image: null, name: ssEntry.name || null, scale: ssEntry.scale || 1 };
        if (ssEntry.dataUrl) {
          (function(idx) {
            var ssImg = new Image();
            ssImg.onload = function() {
              setSlideAssets(function(prev) {
                var next = Object.assign({}, prev);
                next[idx] = Object.assign({}, next[idx] || {}, { image: ssImg });
                return next;
              });
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

    setSeriesSlides(newSlides);
    setSlideAssets(newAssets);
    setActiveSlide(0);

    // Clear PDF state
    clearPdfDownload();
    setPdfError("");
  };

  // --- Render to canvas ---

  var renderSlide = useCallback(function(ctx, slideIndex) {
    renderSlideToCanvas(ctx, slideIndex, seriesSlides, slideAssets, colors, sizes, profileImg);
  }, [colors, sizes, profileImg, seriesSlides, slideAssets]);

  var render = useCallback(function() {
    var canvas = canvasRef.current;
    if (!canvas) return;
    var ctx = canvas.getContext("2d");
    var idx = activeSlide;
    renderSlide(ctx, idx);
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

  // --- Downloads (PDF) ---

  var sanitizePrefix = function(raw) {
    var trimmed = (raw || "").replace(/^\s+|\s+$/g, "");
    if (!trimmed) return "linkedin-slide";
    return trimmed.replace(/[^a-zA-Z0-9_\-]/g, "_");
  };

  var decodeBase64ToBinary = function(b64) {
    if (!b64 || typeof b64 !== "string") return "";
    return atob(b64);
  };

  var extractJpegBinaryFromDataUrl = function(dataUrl) {
    if (!dataUrl || typeof dataUrl !== "string") return "";
    if (dataUrl.indexOf("data:image/jpeg;base64,") !== 0) return "";
    var marker = "base64,";
    var idx = dataUrl.indexOf(marker);
    if (idx === -1) return "";
    return decodeBase64ToBinary(dataUrl.substring(idx + marker.length));
  };

  var buildPdfFromJpegs = function(jpegPages, pageW, pageH) {
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
    for (var t = 0; t < pieces.length; t++) {
      var s = pieces[t];
      for (var c = 0; c < s.length; c++) {
        buf[off++] = s.charCodeAt(c) & 0xFF;
      }
    }

    return new Blob([buf], { type: "application/pdf" });
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

  var clearPdfDownload = function() {
    if (pdfUrlRef.current) {
      URL.revokeObjectURL(pdfUrlRef.current);
      pdfUrlRef.current = null;
    }
    setPdfDownload(null);
  };

  // --- Preset export/import ---

  var clearPresetDownload = function() {
    if (presetUrlRef.current) {
      URL.revokeObjectURL(presetUrlRef.current);
      presetUrlRef.current = null;
    }
    setPresetDownload(null);
  };

  var downloadPreset = function(name, includeImages) {
    var preset = serializePreset(name, includeImages);
    var json = JSON.stringify(preset, null, 2);
    var blob = new Blob([json], { type: "application/json" });
    clearPresetDownload();
    var url = URL.createObjectURL(blob);
    presetUrlRef.current = url;
    var fileName = sanitizePrefix(name || exportPrefix || "preset") + ".json";
    setPresetDownload({ name: fileName, url: url });
  };

  var handlePresetUpload = function(e) {
    var file = e.target.files[0];
    if (!file) return;
    var reader = new FileReader();
    reader.onload = function(ev) {
      try {
        var data = JSON.parse(ev.target.result);
        if (data.version !== 1 || !Array.isArray(data.slides)) {
          setPdfError("Invalid preset file format (expected v1).");
          return;
        }

        // Count missing images
        var imageMap = (data.images && typeof data.images === "object") ? data.images : {};
        var missingCount = 0;
        if (data.profilePicRef) {
          var profileEntry = imageMap[data.profilePicRef];
          if (!profileEntry || !profileEntry.dataUrl) missingCount++;
        }
        for (var i = 0; i < data.slides.length; i++) {
          var sd = data.slides[i];
          if (sd.customBgRef) {
            var bgEntry = imageMap[sd.customBgRef];
            if (!bgEntry || !bgEntry.dataUrl) missingCount++;
          }
          if (sd.screenshotRef) {
            var ssEntry = imageMap[sd.screenshotRef];
            if (!ssEntry || !ssEntry.dataUrl) missingCount++;
          }
        }

        var msg = "Load preset \u201c" + (data.name || "Untitled") + "\u201d? This replaces all current slides and settings.";
        if (missingCount > 0) {
          msg += " (" + missingCount + " image" + (missingCount > 1 ? "s" : "") + " not included \u2014 re-upload after loading.)";
        }

        setConfirmDialog({
          message: msg,
          onConfirm: function() {
            loadPresetData(data);
          }
        });
      } catch (err) {
        setPdfError("Failed to parse preset file.");
      }
    };
    reader.readAsText(file);
    if (presetInputRef.current) presetInputRef.current.value = "";
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

  useEffect(function() {
    return function() {
      if (pdfUrlRef.current) {
        URL.revokeObjectURL(pdfUrlRef.current);
        pdfUrlRef.current = null;
      }
      if (presetUrlRef.current) {
        URL.revokeObjectURL(presetUrlRef.current);
        presetUrlRef.current = null;
      }
    };
  }, []);

  // --- Series slide management ---

  var updateSlide = function(idx, field, val) {
    var next = seriesSlides.map(function(s, i) {
      if (i !== idx) return s;
      var updated = Object.assign({}, s);
      updated[field] = val;
      return updated;
    });
    setSeriesSlides(next);
  };

  var updateBgField = function(field, value) {
    updateSlide(activeSlide, field, value);
  };

  var syncBgToAll = function() {
    setConfirmDialog({
      message: "Apply Slide " + (activeSlide + 1) + "\u2019s background settings to all slides?",
      onConfirm: function() {
        var src = seriesSlides[activeSlide];
        setSeriesSlides(function(prev) {
          return prev.map(function(s) {
            return Object.assign({}, s, {
              solidColor: src.solidColor,
              bgType: src.bgType,
              customBgImage: src.customBgImage,
              customBgName: src.customBgName,
              geoEnabled: src.geoEnabled,
              geoLines: src.geoLines,
              frameEnabled: src.frameEnabled,
              accentColor: src.accentColor,
              borderColor: src.borderColor,
              borderOpacity: src.borderOpacity,
              footerBg: src.footerBg
            });
          });
        });
      }
    });
  };

  var resetBgToDefault = function() {
    setConfirmDialog({
      message: "Reset Slide " + (activeSlide + 1) + "\u2019s background to defaults?",
      onConfirm: function() {
        setSeriesSlides(function(prev) {
          return prev.map(function(s, i) {
            if (i !== activeSlide) return s;
            return Object.assign({}, s, {
              solidColor: "#1e1e2e",
              bgType: "solid",
              customBgImage: null,
              customBgName: null,
              geoEnabled: true,
              geoLines: "#a0a0af",
              frameEnabled: true,
              accentColor: "#22c55e",
              borderColor: "#ffffff",
              borderOpacity: 25,
              footerBg: "#ffffff"
            });
          });
        });
      }
    });
  };

  var addSlide = function() {
    if (seriesSlides.length >= 10) return;
    setSeriesSlides(seriesSlides.concat([makeDefaultSlide()]));
  };

  var duplicateSlide = function() {
    if (seriesSlides.length >= 10) return;
    setConfirmDialog({
      message: "Duplicate Slide " + (activeSlide + 1) + "?",
      onConfirm: function() {
        var src = seriesSlides[activeSlide];
        var copy = Object.assign({}, src, { cards: src.cards.slice() });

        var newIdx = seriesSlides.length;
        setSeriesSlides(seriesSlides.concat([copy]));

        setSlideAssets(function(prev) {
          var next = Object.assign({}, prev);
          next[newIdx] = Object.assign({}, getAsset(activeSlide));
          return next;
        });

        setActiveSlide(newIdx);
      }
    });
  };

  var removeSlide = function(idx) {
    if (seriesSlides.length <= 1) return;
    var next = seriesSlides.filter(function(_, i) { return i !== idx; });
    var nextAssets = {};
    Object.keys(slideAssets).forEach(function(k) {
      var ki = Number(k);
      if (ki < idx) nextAssets[ki] = slideAssets[ki];
      else if (ki > idx) nextAssets[ki - 1] = slideAssets[ki];
    });
    setSeriesSlides(next);
    setSlideAssets(nextAssets);
    if (activeSlide >= next.length) setActiveSlide(next.length - 1);
    else if (activeSlide === idx) setActiveSlide(Math.max(0, idx - 1));
  };

  var reorderSlide = function(fromIdx, toIdx) {
    if (fromIdx === toIdx || fromIdx == null || toIdx == null) return;
    if (fromIdx < 0 || fromIdx >= seriesSlides.length) return;
    if (toIdx < 0 || toIdx >= seriesSlides.length) return;

    // Reorder seriesSlides
    var nextSlides = seriesSlides.slice();
    var moved = nextSlides.splice(fromIdx, 1)[0];
    nextSlides.splice(toIdx, 0, moved);
    setSeriesSlides(nextSlides);

    // Build index map: old position -> new position
    var indexMap = {};
    for (var i = 0; i < seriesSlides.length; i++) {
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
      indexMap[i] = newPos;
    }

    // Remap slideAssets keys
    var oldAssets = Object.assign({}, slideAssets);
    var nextAssets = {};
    Object.keys(oldAssets).forEach(function(k) {
      var ki = Number(k);
      if (indexMap[ki] != null) {
        nextAssets[indexMap[ki]] = oldAssets[ki];
      }
    });
    setSlideAssets(nextAssets);

    // Update activeSlide to follow the same logical slide
    if (activeSlide === fromIdx) {
      setActiveSlide(toIdx);
    } else if (indexMap[activeSlide] != null) {
      setActiveSlide(indexMap[activeSlide]);
    }

    setDragFrom(null);
    setDragOver(null);
  };

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

  // --- Styles ---

  var inputStyle = { width: "100%", padding: "8px 12px", borderRadius: 8, border: "1px solid #444", background: "#28283e", color: "#fff", fontSize: 14, boxSizing: "border-box" };
  var labelStyle = { display: "block", marginBottom: 6, fontWeight: 600, fontSize: 13, color: "#bbb", letterSpacing: 0.5 };
  var INLINE_SWATCHES = ["#ffffff", "#1a1a2e", "#333333", "#22c55e", "#a5b4fc", "#f59e0b", "#fb7185", "#22d3ee", "#a78bfa", "#38bdf8", "#d97706", "#fef3c7", "#e0f2fe", "#e0e7ff", "#f0fdf4", "#9ca3af"];

  var sizeLabel = function(text, sizeKey, min, max, extra, colorVal, colorSet, colorPickerKey, opacityVal, opacitySet) {
    if (!sizeKey) return <label style={labelStyle}>{text}{extra ? " " : ""}{extra}</label>;
    var cpOpen = colorPickerKey && openPicker === colorPickerKey;
    return (
      <div style={{ display: "flex", alignItems: "center", marginBottom: text ? 6 : 0, gap: text ? 0 : 6 }}>
        {text && <span style={{ fontWeight: 600, fontSize: 13, color: "#bbb", letterSpacing: 0.5, flex: 1 }}>{text}{extra ? " " : ""}{extra}</span>}
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          {colorPickerKey && (
            <div style={{ position: "relative" }} data-picker={colorPickerKey}>
              <button onClick={function(e) { e.stopPropagation(); setOpenPicker(cpOpen ? null : colorPickerKey); }}
                style={{ width: 18, height: 18, borderRadius: 4, border: cpOpen ? "2px solid #6366f1" : "1px solid #444", background: colorVal || "#fff", cursor: "pointer", padding: 0, display: "block" }} />
              {cpOpen && (
                <div style={{ position: "absolute", top: "100%", right: 0, zIndex: 60, marginTop: 4, background: "#1a1a30", border: "1px solid #444", borderRadius: 10, padding: 10, width: 200, boxShadow: "0 8px 24px rgba(0,0,0,0.6)" }}>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(8, 1fr)", gap: 4, marginBottom: 8 }}>
                    {INLINE_SWATCHES.map(function(c) {
                      var active = colorVal === c;
                      return (
                        <button key={c} onClick={function() { colorSet(c); }}
                          style={{ width: 20, height: 20, borderRadius: 4, border: active ? "2px solid #fff" : "1px solid #444", background: c, cursor: "pointer", padding: 0, boxShadow: active ? "0 0 0 1px #6366f1" : "none" }} />
                      );
                    })}
                  </div>
                  <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                    <input type="color" value={colorVal && colorVal.charAt(0) === "#" ? colorVal : "#ffffff"} onChange={function(e) { colorSet(e.target.value); }}
                      style={{ width: 24, height: 24, border: "1px solid #444", borderRadius: 4, cursor: "pointer", background: "none", padding: 0 }} />
                    <input value={colorVal || ""} onChange={function(e) { colorSet(e.target.value); }}
                      style={{ flex: 1, padding: "4px 6px", borderRadius: 4, border: "1px solid #444", background: "#0e0e1a", color: "#bbb", fontSize: 11, fontFamily: "monospace" }} />
                  </div>
                  {opacitySet && (
                    <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 8, paddingTop: 8, borderTop: "1px solid #3a3a50" }}>
                      <span style={{ fontSize: 10, color: "#666", whiteSpace: "nowrap" }}>Opacity</span>
                      <input type="range" min={0} max={100} value={opacityVal != null ? opacityVal : 100} onChange={function(e) { opacitySet(Number(e.target.value)); }}
                        style={{ flex: 1 }} />
                      <span style={{ fontSize: 10, color: "#555", width: 28, textAlign: "right" }}>{(opacityVal != null ? opacityVal : 100) + "%"}</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
          <div style={{ display: "flex", alignItems: "center", gap: 0, background: "#28283e", borderRadius: 4, border: "1px solid #444", height: 28, overflow: "hidden" }}>
            <button onClick={function() { if (sizes[sizeKey] > (min || 10)) setSize(sizeKey, sizes[sizeKey] - 1); }}
              style={{ minWidth: 28, minHeight: 28, border: "none", background: "transparent", color: "#555", cursor: "pointer", fontSize: 14, padding: 0, lineHeight: "28px" }}>{"\u2212"}</button>
            <input value={sizes[sizeKey]} onChange={function(e) { var v = parseInt(e.target.value, 10); if (!isNaN(v)) setSize(sizeKey, Math.max(min || 10, Math.min(max || 60, v))); }}
              style={{ width: 30, height: 28, border: "none", borderLeft: "1px solid #444", borderRight: "1px solid #444", background: "transparent", color: "#666", fontSize: 11, fontFamily: "monospace", textAlign: "center", padding: 0, outline: "none" }} />
            <button onClick={function() { if (sizes[sizeKey] < (max || 60)) setSize(sizeKey, sizes[sizeKey] + 1); }}
              style={{ minWidth: 28, minHeight: 28, border: "none", background: "transparent", color: "#555", cursor: "pointer", fontSize: 14, padding: 0, lineHeight: "28px" }}>+</button>
          </div>
        </div>
      </div>
    );
  };

  var currentSlide = seriesSlides[activeSlide] || seriesSlides[0];
  var isCustomBg = currentSlide.bgType === "custom";

  return (
    <div style={{ fontFamily: '"Helvetica Neue", Helvetica, Arial, sans-serif', background: "#000000", minHeight: "100vh", color: "#e0e0e0", padding: 16 }}>
      <div style={{ maxWidth: 1400, margin: "0 auto" }}>
        <h2 style={{ color: "#fff", marginBottom: 16, fontSize: 20 }}>LinkedIn Carousel Generator</h2>

        <div style={{ display: "flex", gap: 20, alignItems: "flex-start" }}>


        {/* -- COL 1: Settings + Slides -- */}
        <div style={{ flex: "0 0 240px", minWidth: 220 }}>

          {/* --- PRESETS --- */}
          <div style={{ marginBottom: 14 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
              <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>PRESETS</label>
              <button onClick={function() { setPresetName(exportPrefix || ""); setPresetDialog({ type: "save" }); }}
                style={{ padding: "2px 8px", borderRadius: 4, border: "1px solid #444", background: "#28283e", color: "#ccc", cursor: "pointer", fontSize: 9, fontWeight: 600 }}>
                Save
              </button>
              <button onClick={function() { if (presetInputRef.current) presetInputRef.current.click(); }}
                style={{ padding: "2px 8px", borderRadius: 4, border: "1px solid #444", background: "#28283e", color: "#ccc", cursor: "pointer", fontSize: 9, fontWeight: 600 }}>
                Load
              </button>
              <input ref={presetInputRef} type="file" accept=".json" onChange={handlePresetUpload} style={{ display: "none" }} />
            </div>
            {presetDownload && (
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 4 }}>
                <a href={presetDownload.url} download={presetDownload.name}
                  onClick={function() { setTimeout(clearPresetDownload, 1500); }}
                  style={{ fontSize: 11, color: "#a5b4fc", textDecoration: "underline", flex: 1, wordBreak: "break-all" }}>
                  {"Save " + presetDownload.name}
                </a>
                <button onClick={clearPresetDownload}
                  style={{ background: "none", border: "none", color: "#999", cursor: "pointer", fontSize: 14, padding: "0 2px", lineHeight: 1 }}>
                  {"\u00d7"}
                </button>
              </div>
            )}
          </div>
          <div style={{ borderTop: "1px solid #444", marginBottom: 10 }} />

          {/* --- BACKGROUND --- */}
          <div style={{ marginBottom: 14 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
              <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>BACKGROUND</label>
              <button onClick={syncBgToAll}
                style={{
                  padding: "2px 8px",
                  borderRadius: 4,
                  border: "1px solid #444",
                  background: "#28283e",
                  color: "#ccc",
                  cursor: "pointer",
                  fontSize: 9,
                  fontWeight: 600
                }}>
                Sync All
              </button>
              <button onClick={resetBgToDefault}
                style={{
                  padding: "2px 8px",
                  borderRadius: 4,
                  border: "1px solid #444",
                  background: "#28283e",
                  color: "#ccc",
                  cursor: "pointer",
                  fontSize: 9,
                  fontWeight: 600
                }}>
                Reset
              </button>
            </div>

            {/* 50/50 split: controls left, thumbnail right */}
            <div style={{ display: "flex", gap: 14, alignItems: "stretch" }}>

              {/* Left zone: Solid/Photo pill + Accent / Base / Layer / Frame */}
              <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column" }}>

                {/* Solid / Photo pill */}
                <div style={{ marginBottom: 20 }}>
                  <div style={{ display: "flex", borderRadius: 10, overflow: "hidden", border: "1px solid #444" }}>
                    <button onClick={function() { if (isCustomBg) updateBgField("bgType", "solid"); }}
                      style={{ flex: 1, padding: "2px 0", border: "none", background: !isCustomBg ? "#6366f1" : "#28283e", color: !isCustomBg ? "#fff" : "#999", cursor: "pointer", fontSize: 9, fontWeight: 700, letterSpacing: 0.5, textAlign: "center" }}>
                      Solid
                    </button>
                    <button onClick={function() { if (!isCustomBg) updateBgField("bgType", "custom"); }}
                      style={{ flex: 1, padding: "2px 0", border: "none", borderLeft: "1px solid #444", background: isCustomBg ? "#6366f1" : "#28283e", color: isCustomBg ? "#fff" : "#999", cursor: "pointer", fontSize: 9, fontWeight: 700, letterSpacing: 0.5, textAlign: "center" }}>
                      Photo
                    </button>
                  </div>
                </div>

                {/* Group 1: Accent + Base */}
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>

                {/* Accent row */}
                {(function() {
                  var aOpen = openPicker === "accent";
                  var aVal = currentSlide.accentColor || "#fff";
                  return (
                    <div style={{ display: "flex", alignItems: "center", gap: 10, position: "relative" }} data-picker="accent">
                      <label style={{ fontSize: 13, color: "#999", fontWeight: 600, width: 46 }}>Accent</label>
                      <span onClick={function(e) { e.stopPropagation(); setOpenPicker(aOpen ? null : "accent"); }}
                        style={{ width: 20, height: 20, borderRadius: 5, background: aVal, display: "block", border: aOpen ? "2px solid #6366f1" : "1px solid #444", boxSizing: "border-box", cursor: "pointer" }} />
                      {aOpen && (
                        <div style={{ position: "absolute", top: "100%", left: 0, zIndex: 60, marginTop: 4, background: "#1a1a30", border: "1px solid #444", borderRadius: 10, padding: 10, width: 200, boxShadow: "0 8px 24px rgba(0,0,0,0.6)" }}>
                          <div style={{ display: "grid", gridTemplateColumns: "repeat(8, 1fr)", gap: 4, marginBottom: 8 }}>
                            {INLINE_SWATCHES.map(function(c) {
                              return (
                                <button key={c} onClick={function() { updateBgField("accentColor", c); }}
                                  style={{ width: 20, height: 20, borderRadius: 4, border: aVal === c ? "2px solid #fff" : "1px solid #444", background: c, cursor: "pointer", padding: 0, boxShadow: aVal === c ? "0 0 0 1px #6366f1" : "none" }} />
                              );
                            })}
                          </div>
                          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                            <input type="color" value={aVal && aVal.charAt(0) === "#" ? aVal : "#ffffff"} onChange={function(e) { updateBgField("accentColor", e.target.value); }}
                              style={{ width: 24, height: 24, border: "1px solid #444", borderRadius: 4, cursor: "pointer", background: "none", padding: 0 }} />
                            <input value={aVal} onChange={function(e) { updateBgField("accentColor", e.target.value); }}
                              style={{ flex: 1, padding: "4px 6px", borderRadius: 4, border: "1px solid #444", background: "#0e0e1a", color: "#bbb", fontSize: 11, fontFamily: "monospace" }} />
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })()}

                {/* Base row */}
                {(function() {
                  var bsOpen = openPicker === "solidColor";
                  var bsVal = currentSlide.solidColor || "#fff";
                  var bsDisabled = isCustomBg;
                  return (
                    <div style={{ display: "flex", alignItems: "center", gap: 10, position: "relative", opacity: bsDisabled ? 0.35 : 1 }} data-picker="solidColor">
                      <label style={{ fontSize: 13, color: "#999", fontWeight: 600, width: 46 }}>Base</label>
                      <span onClick={function(e) { if (bsDisabled) return; e.stopPropagation(); setOpenPicker(bsOpen ? null : "solidColor"); }}
                        style={{ width: 20, height: 20, borderRadius: 5, background: bsVal, display: "block", border: bsOpen ? "2px solid #6366f1" : "1px solid #444", boxSizing: "border-box", cursor: bsDisabled ? "default" : "pointer" }} />
                      {bsOpen && !bsDisabled && (
                        <div style={{ position: "absolute", top: "100%", left: 0, zIndex: 60, marginTop: 4, background: "#1a1a30", border: "1px solid #444", borderRadius: 10, padding: 10, width: 200, boxShadow: "0 8px 24px rgba(0,0,0,0.6)" }}>
                          <div style={{ display: "grid", gridTemplateColumns: "repeat(8, 1fr)", gap: 4, marginBottom: 8 }}>
                            {INLINE_SWATCHES.map(function(c) {
                              return (
                                <button key={c} onClick={function() { updateBgField("solidColor", c); }}
                                  style={{ width: 20, height: 20, borderRadius: 4, border: bsVal === c ? "2px solid #fff" : "1px solid #444", background: c, cursor: "pointer", padding: 0, boxShadow: bsVal === c ? "0 0 0 1px #6366f1" : "none" }} />
                              );
                            })}
                          </div>
                          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                            <input type="color" value={bsVal && bsVal.charAt(0) === "#" ? bsVal : "#ffffff"} onChange={function(e) { updateBgField("solidColor", e.target.value); }}
                              style={{ width: 24, height: 24, border: "1px solid #444", borderRadius: 4, cursor: "pointer", background: "none", padding: 0 }} />
                            <input value={bsVal} onChange={function(e) { updateBgField("solidColor", e.target.value); }}
                              style={{ flex: 1, padding: "4px 6px", borderRadius: 4, border: "1px solid #444", background: "#0e0e1a", color: "#bbb", fontSize: 11, fontFamily: "monospace" }} />
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })()}
                </div>

                {/* Spacer between groups */}
                <div style={{ height: 14 }} />

                {/* Group 2: Layer + Frame */}
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {/* Layer row */}
                <div style={{ display: "flex", alignItems: "center", gap: 10, opacity: isCustomBg ? 0.35 : 1 }}>
                  <label style={{ fontSize: 13, color: "#999", fontWeight: 600, width: 46 }}>Layer</label>
                  <button onClick={function() { if (!isCustomBg) updateBgField("geoEnabled", !currentSlide.geoEnabled); }}
                    style={{ padding: "3px 8px", borderRadius: 20, border: "none", background: (!isCustomBg && currentSlide.geoEnabled) ? GREEN : "#555", color: "#fff", cursor: isCustomBg ? "default" : "pointer", fontSize: 11, fontWeight: 600 }}>
                    {(!isCustomBg && currentSlide.geoEnabled) ? "ON" : "OFF"}
                  </button>
                  {(function() {
                    var lOpen = openPicker === "geoLines";
                    var lDisabled = isCustomBg || !currentSlide.geoEnabled;
                    return (
                      <div style={{ position: "relative", opacity: lDisabled ? 0.5 : 1 }} data-picker="geoLines">
                        <button onClick={function(e) { if (lDisabled) return; e.stopPropagation(); setOpenPicker(lOpen ? null : "geoLines"); }}
                          style={{ width: 18, height: 18, borderRadius: 4, border: lOpen ? "2px solid #6366f1" : "1px solid #444", background: currentSlide.geoLines, cursor: lDisabled ? "default" : "pointer", padding: 0, display: "block" }} />
                        {lOpen && !lDisabled && (
                          <div style={{ position: "absolute", top: "100%", left: 0, zIndex: 60, marginTop: 4, background: "#1a1a30", border: "1px solid #444", borderRadius: 10, padding: 10, width: 200, boxShadow: "0 8px 24px rgba(0,0,0,0.6)" }}>
                            <div style={{ display: "grid", gridTemplateColumns: "repeat(8, 1fr)", gap: 4, marginBottom: 8 }}>
                              {INLINE_SWATCHES.map(function(c) {
                                return (
                                  <button key={c} onClick={function() { updateBgField("geoLines", c); }}
                                    style={{ width: 20, height: 20, borderRadius: 4, border: currentSlide.geoLines === c ? "2px solid #fff" : "1px solid #444", background: c, cursor: "pointer", padding: 0, boxShadow: currentSlide.geoLines === c ? "0 0 0 1px #6366f1" : "none" }} />
                                );
                              })}
                            </div>
                            <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                              <input type="color" value={currentSlide.geoLines} onChange={function(e) { updateBgField("geoLines", e.target.value); }}
                                style={{ width: 24, height: 24, border: "1px solid #444", borderRadius: 4, cursor: "pointer", background: "none", padding: 0 }} />
                              <input value={currentSlide.geoLines} onChange={function(e) { updateBgField("geoLines", e.target.value); }}
                                style={{ flex: 1, padding: "4px 6px", borderRadius: 4, border: "1px solid #444", background: "#0e0e1a", color: "#bbb", fontSize: 11, fontFamily: "monospace" }} />
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })()}
                </div>

                {/* Frame row */}
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <label style={{ fontSize: 13, color: "#999", fontWeight: 600, width: 46 }}>Frame</label>
                  <button onClick={function() { updateBgField("frameEnabled", !currentSlide.frameEnabled); }}
                    style={{ padding: "3px 8px", borderRadius: 20, border: "none", background: currentSlide.frameEnabled ? GREEN : "#555", color: "#fff", cursor: "pointer", fontSize: 11, fontWeight: 600 }}>
                    {currentSlide.frameEnabled ? "ON" : "OFF"}
                  </button>
                  {(function() {
                    var bOpen = openPicker === "border";
                    var bVal = currentSlide.borderColor || "#fff";
                    return (
                      <div style={{ position: "relative", opacity: currentSlide.frameEnabled ? 1 : 0.35 }} data-picker="border">
                        <button onClick={function(e) { if (!currentSlide.frameEnabled) return; e.stopPropagation(); setOpenPicker(bOpen ? null : "border"); }}
                          style={{ width: 18, height: 18, borderRadius: 4, border: bOpen ? "2px solid #6366f1" : "1px solid #444", background: bVal, cursor: currentSlide.frameEnabled ? "pointer" : "default", padding: 0, display: "block" }} />
                        {bOpen && currentSlide.frameEnabled && (
                          <div style={{ position: "absolute", top: "100%", left: 0, zIndex: 60, marginTop: 4, background: "#1a1a30", border: "1px solid #444", borderRadius: 10, padding: 10, width: 200, boxShadow: "0 8px 24px rgba(0,0,0,0.6)" }}>
                            <div style={{ display: "grid", gridTemplateColumns: "repeat(8, 1fr)", gap: 4, marginBottom: 8 }}>
                              {INLINE_SWATCHES.map(function(c) {
                                return (
                                  <button key={c} onClick={function() { updateBgField("borderColor", c); }}
                                    style={{ width: 20, height: 20, borderRadius: 4, border: bVal === c ? "2px solid #fff" : "1px solid #444", background: c, cursor: "pointer", padding: 0, boxShadow: bVal === c ? "0 0 0 1px #6366f1" : "none" }} />
                                );
                              })}
                            </div>
                            <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                              <input type="color" value={bVal && bVal.charAt(0) === "#" ? bVal : "#ffffff"} onChange={function(e) { updateBgField("borderColor", e.target.value); }}
                                style={{ width: 24, height: 24, border: "1px solid #444", borderRadius: 4, cursor: "pointer", background: "none", padding: 0 }} />
                              <input value={bVal} onChange={function(e) { updateBgField("borderColor", e.target.value); }}
                                style={{ flex: 1, padding: "4px 6px", borderRadius: 4, border: "1px solid #444", background: "#0e0e1a", color: "#bbb", fontSize: 11, fontFamily: "monospace" }} />
                            </div>
                            <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 8, paddingTop: 8, borderTop: "1px solid #3a3a50" }}>
                              <span style={{ fontSize: 10, color: "#666" }}>Opacity</span>
                              <input type="range" min={0} max={100} value={currentSlide.borderOpacity} onChange={function(e) { updateBgField("borderOpacity", Number(e.target.value)); }}
                                style={{ flex: 1 }} />
                              <span style={{ fontSize: 10, color: "#555" }}>{currentSlide.borderOpacity + "%"}</span>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })()}
                </div>
                {(function() {
                  var fOpen = openPicker === "footerBg";
                  var fVal = currentSlide.footerBg || "#ffffff";
                  return (
                    <div style={{ display: "flex", alignItems: "center", gap: 10, position: "relative" }} data-picker="footerBg">
                      <label style={{ fontSize: 13, color: "#999", fontWeight: 600, width: 46 }}>Footer</label>
                      <span onClick={function(e) { e.stopPropagation(); setOpenPicker(fOpen ? null : "footerBg"); }}
                        style={{ width: 20, height: 20, borderRadius: 5, background: fVal, display: "block", border: fOpen ? "2px solid #6366f1" : "1px solid #444", boxSizing: "border-box", cursor: "pointer" }} />
                      {fOpen && (
                        <div style={{ position: "absolute", top: "100%", left: 0, zIndex: 60, marginTop: 4, background: "#1a1a30", border: "1px solid #444", borderRadius: 10, padding: 10, width: 200, boxShadow: "0 8px 24px rgba(0,0,0,0.6)" }}>
                          <div style={{ display: "grid", gridTemplateColumns: "repeat(8, 1fr)", gap: 4, marginBottom: 8 }}>
                            {INLINE_SWATCHES.map(function(c) {
                              return (
                                <button key={c} onClick={function() { updateBgField("footerBg", c); }}
                                  style={{ width: 20, height: 20, borderRadius: 4, border: fVal === c ? "2px solid #fff" : "1px solid #444", background: c, cursor: "pointer", padding: 0, boxShadow: fVal === c ? "0 0 0 1px #6366f1" : "none" }} />
                              );
                            })}
                          </div>
                          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                            <input type="color" value={fVal && fVal.charAt(0) === "#" ? fVal : "#ffffff"} onChange={function(e) { updateBgField("footerBg", e.target.value); }}
                              style={{ width: 24, height: 24, border: "1px solid #444", borderRadius: 4, cursor: "pointer", background: "none", padding: 0 }} />
                            <input value={fVal} onChange={function(e) { updateBgField("footerBg", e.target.value); }}
                              style={{ flex: 1, padding: "4px 6px", borderRadius: 4, border: "1px solid #444", background: "#0e0e1a", color: "#bbb", fontSize: 11, fontFamily: "monospace" }} />
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })()}
                </div>

              </div>

              {/* Right zone: upload + thumbnail + status */}
              <div style={{ flex: 1, minWidth: 0, position: "relative", display: "flex", flexDirection: "column", alignItems: "center" }}>

                {/* Photo upload - above thumbnail; visible only in Photo mode */}
                <div style={{ width: "100%", marginBottom: 2, visibility: isCustomBg ? "visible" : "hidden" }}>
                  <input ref={customBgInputRef} type="file" accept="image/*" onChange={function(e) { handleCustomUpload(e); }} style={{ display: "none" }} />
                  <button onClick={function() { if (customBgInputRef.current) customBgInputRef.current.click(); }}
                    style={{ padding: "3px 8px", borderRadius: 4, border: "1px solid #444", background: "#28283e", color: "#ccc", cursor: "pointer", fontSize: 10, fontWeight: 600 }}>
                    Choose File
                  </button>
                  <p style={{ fontSize: 9, color: "#666", margin: "2px 0 0 0", wordBreak: "break-all", lineHeight: 1.3, minHeight: 10 }}>{currentSlide.customBgName || "\u00a0"}</p>
                </div>

                {/* Thumbnail preview */}
                <div style={{ width: "100%", aspectRatio: "4/5", maxHeight: 130, borderRadius: 6, overflow: "hidden", border: "2px solid #444", background: "#111119", position: "relative" }}>
                  {currentSlide.bgType === "solid" && (
                    <div style={{ width: "100%", height: "100%", background: currentSlide.solidColor || "#111119" }} />
                  )}
                  {currentSlide.bgType === "custom" && currentSlide.customBgImage && (
                    <img src={currentSlide.customBgImage.src} alt="Custom background"
                      style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                  )}
                  {currentSlide.bgType === "custom" && !currentSlide.customBgImage && (
                    <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 9, color: "#666" }}>No photo</div>
                  )}
                  {/* Layer overlay */}
                  {currentSlide.geoEnabled && !isCustomBg && (
                    <div style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%", pointerEvents: "none", borderRadius: 4, background: "radial-gradient(circle at 0% 22%, " + hexToRgba(currentSlide.geoLines, 12) + " 0%, transparent 40%), radial-gradient(circle at 0% 80%, " + hexToRgba(currentSlide.geoLines, 10) + " 0%, transparent 35%), radial-gradient(circle at 92% 13%, " + hexToRgba(currentSlide.geoLines, 8) + " 0%, transparent 30%), radial-gradient(circle at 88% 83%, " + hexToRgba(currentSlide.geoLines, 9) + " 0%, transparent 32%), repeating-linear-gradient(0deg, transparent, transparent 10px, " + hexToRgba(currentSlide.geoLines, 12) + " 10px, " + hexToRgba(currentSlide.geoLines, 12) + " 11px), repeating-linear-gradient(90deg, transparent, transparent 10px, " + hexToRgba(currentSlide.geoLines, 12) + " 10px, " + hexToRgba(currentSlide.geoLines, 12) + " 11px), linear-gradient(32deg, transparent 40%, " + hexToRgba(currentSlide.geoLines, 6) + " 50%, transparent 60%), linear-gradient(148deg, transparent 40%, " + hexToRgba(currentSlide.geoLines, 6) + " 50%, transparent 60%)" }} />
                  )}
                  {/* Frame overlay */}
                  {currentSlide.frameEnabled && (
                    <div style={{ position: "absolute", top: 15, left: 15, right: 15, bottom: 15, pointerEvents: "none", borderRadius: 3, border: "2px solid " + hexToRgba(currentSlide.borderColor, currentSlide.borderOpacity) }} />
                  )}
                </div>

                {/* Status - below thumbnail; visible only in Photo mode */}
                <div style={{ width: "100%", marginTop: 4, visibility: isCustomBg ? "visible" : "hidden" }}>
                  <div style={{ minHeight: 14 }}>
                    {currentSlide.customBgImage ? (
                      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        <span style={{ fontSize: 9, color: GREEN }}>{"\u2713"} Uploaded</span>
                        <button onClick={removeCustomBg} style={{ background: "none", border: "none", color: "#f87171", cursor: "pointer", fontSize: 9, padding: 0 }}>{"\u00d7"} Remove</button>
                      </div>
                    ) : (
                      <span style={{ fontSize: 9, color: "#555" }}>No image</span>
                    )}
                  </div>
                </div>
              </div>

            </div>
          </div>

          {/* -- Divider: Above Profile Pic -- */}
          <div style={{ borderTop: "1px solid #444", marginTop: 10, marginBottom: 10 }} />

          {/* --- PROFILE PIC --- */}
          <div style={{ marginBottom: 10 }}>
            <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
              {/* Left zone: label + file input + filename + status */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                  <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>PROFILE PIC</label>
                  <span style={{ fontSize: 10, color: "#555", fontWeight: 400 }}>(84 {"\u00d7"} 84px)</span>
                </div>
                <input ref={profilePicInputRef} type="file" accept="image/*" onChange={handleProfilePicUpload} style={{ display: "none" }} />
                <button onClick={function() { if (profilePicInputRef.current) profilePicInputRef.current.click(); }}
                  style={{ padding: "3px 8px", borderRadius: 4, border: "1px solid #444", background: "#28283e", color: "#ccc", cursor: "pointer", fontSize: 10, fontWeight: 600, marginBottom: 2 }}>
                  Choose File
                </button>
                {/* Filename - always reserves space */}
                <p style={{ fontSize: 10, color: "#666", margin: "2px 0 2px 0", wordBreak: "break-all", lineHeight: 1.3, maxWidth: 150, minHeight: 13 }}>{profilePicName || "\u00a0"}</p>
                {/* Status - always reserves space */}
                <div style={{ marginTop: 2, minHeight: 16 }}>
                  {profileImg && isCustomProfilePic ? (
                    <>
                      <span style={{ fontSize: 11, color: GREEN }}>{"\u2713"} Uploaded</span>
                      <button onClick={removeProfilePic} style={{ background: "none", border: "none", color: "#f87171", cursor: "pointer", fontSize: 11, marginLeft: 8 }}>{"\u00d7"} Remove</button>
                    </>
                  ) : (
                    <span style={{ fontSize: 11, color: "#555" }}>No image</span>
                  )}
                </div>
              </div>
              {/* Right zone: circular preview */}
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                <div style={{ width: 64, height: 64, borderRadius: "50%", overflow: "hidden", border: "2px solid #444", background: "#111119", flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>
                  {profileImg ? (
                    <img src={profileImg.src} alt="Profile pic" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                  ) : (
                    <span style={{ fontSize: 9, color: "#555" }}>None</span>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* -- Divider: Global ? / Per-Slide ? -- */}
          <div style={{ borderTop: "1px solid #444", marginTop: 10, marginBottom: 10, paddingTop: 10 }}>

          {/* --- SLIDES --- */}
          <div style={{ marginBottom: 10 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
              <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>SLIDES</label>
              <button onClick={duplicateSlide}
                style={{
                  padding: "2px 8px",
                  borderRadius: 4,
                  border: "1px solid #444",
                  background: "#28283e",
                  color: "#ccc",
                  cursor: "pointer",
                  fontSize: 9,
                  fontWeight: 600,
                  opacity: seriesSlides.length >= 10 ? 0.4 : 1
                }}>
                Duplicate
              </button>
            </div>
            <div style={{ display: "flex", gap: 4, marginBottom: 0, flexWrap: "wrap" }}>
              {seriesSlides.map(function(s, i) {
                var isActive = activeSlide === i;
                var isDragSource = dragFrom === i;
                var isDragTarget = dragOver === i && dragFrom !== i;
                var label = (i + 1).toString();
                return (
                  <button key={i}
                    draggable
                    onClick={function() { setActiveSlide(i); }}
                    onDragStart={function(e) { setDragFrom(i); e.dataTransfer.effectAllowed = "move"; }}
                    onDragOver={function(e) { e.preventDefault(); e.dataTransfer.dropEffect = "move"; setDragOver(i); }}
                    onDragLeave={function() { if (dragOver === i) setDragOver(null); }}
                    onDrop={function(e) { e.preventDefault(); if (dragFrom != null) { reorderSlide(dragFrom, i); } }}
                    onDragEnd={function() { setDragFrom(null); setDragOver(null); }}
                    style={{ width: 56, height: 56, borderRadius: 8, border: isDragTarget ? "2px dashed #6366f1" : (isActive ? "2px solid " + GREEN : "2px solid #555"), background: isDragTarget ? "rgba(99,102,241,0.10)" : (isActive ? "rgba(34,197,94,0.15)" : "#1a1a30"), color: isActive ? GREEN : "#aaa", cursor: isDragSource ? "grabbing" : "grab", fontSize: 16, fontWeight: 700, padding: 0, display: "flex", alignItems: "center", justifyContent: "center", opacity: isDragSource ? 0.4 : 1, transition: "opacity 0.15s, border 0.15s, background 0.15s" }}>
                    {label}
                  </button>
                );
              })}
              {seriesSlides.length < 10 && (
                <button onClick={addSlide}
                  style={{ width: 56, height: 56, borderRadius: 8, border: "2px dashed #555", background: "#1a1a30", color: "#888", cursor: "pointer", fontSize: 18, fontWeight: 700, padding: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>+</button>
              )}
            </div>
          </div>

          {/* --- SCREENSHOT (per-slide, in Col 1) --- */}
          {currentSlide && (
            <div style={{ marginTop: 6 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>SCREENSHOT</label>
                <span style={{ fontSize: 10, color: "#555", fontWeight: 400 }}>(640 {"\u00D7"} 500px)</span>
                <button onClick={function() { var next = !currentSlide.showScreenshot; updateSlide(activeSlide, "showScreenshot", next); if (!next) { removeScreenshot(activeSlide); } }}
                  style={{ padding: "3px 12px", borderRadius: 20, border: "none", background: currentSlide.showScreenshot ? GREEN : "#555", color: "#fff", cursor: "pointer", fontSize: 11, fontWeight: 600 }}>
                  {currentSlide.showScreenshot ? "ON" : "OFF"}
                </button>
              </div>
              {currentSlide.showScreenshot && (
                <div style={{ marginBottom: 8, paddingLeft: 8, borderLeft: "2px solid #555" }}>
                  <input ref={screenshotInputRef} type="file" accept="image/*" onChange={function(e) { handleScreenshotUpload(activeSlide, e); }} style={{ display: "none" }} />
                  <button onClick={function() { if (screenshotInputRef.current) screenshotInputRef.current.click(); }}
                    style={{ padding: "3px 8px", borderRadius: 4, border: "1px solid #444", background: "#28283e", color: "#ccc", cursor: "pointer", fontSize: 10, fontWeight: 600 }}>
                    Choose File
                  </button>
                  {/* Filename - below Choose File, above status */}
                  {getAsset(activeSlide).name && (
                    <p style={{ fontSize: 10, color: "#666", margin: "2px 0 2px 0", wordBreak: "break-all", lineHeight: 1.3, maxWidth: 150 }}>{getAsset(activeSlide).name}</p>
                  )}
                  {getAsset(activeSlide).image && (
                    <div style={{ marginTop: 4 }}>
                      <span style={{ fontSize: 11, color: GREEN }}>{"\u2713"} Uploaded</span>
                      <button onClick={function() { removeScreenshot(activeSlide); }} style={{ background: "none", border: "none", color: "#f87171", cursor: "pointer", fontSize: 11, marginLeft: 8 }}>{"\u00d7"} Remove</button>
                      <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 6 }}>
                        <span style={{ fontSize: 10, color: "#666" }}>Scale</span>
                        <input type="range" min={50} max={200} value={Math.round(getAsset(activeSlide).scale * 100)} onChange={function(e) { setScale(activeSlide, Number(e.target.value) / 100); }}
                          style={{ flex: 1 }} />
                        <span style={{ fontSize: 10, color: "#555", width: 32, textAlign: "right" }}>{Math.round(getAsset(activeSlide).scale * 100) + "%"}</span>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          </div>

        </div>

          {/* -- COL 2: Slide Editor -- */}
          <div style={{ flex: "1 1 280px", minWidth: 260 }}>

          {/* --- SLIDE EDITOR --- */}
          {currentSlide && (
            <div style={{ background: "#1a1a30", borderRadius: 10, padding: 14, border: "1px solid #3a3a50", marginBottom: 14 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                <span style={{ color: "#888", fontSize: 12, fontWeight: 600 }}>
                  {"SLIDE " + (activeSlide + 1)}
                </span>
                {seriesSlides.length > 1 && (
                  <button onClick={function() { removeSlide(activeSlide); }}
                    style={{ background: "none", border: "1px solid #f8717133", color: "#f87171", cursor: "pointer", fontSize: 11, padding: "3px 10px", borderRadius: 6 }}>Remove</button>
                )}
              </div>

              {/* -- Footer & Pic toggle (per-slide) -- */}
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4, marginTop: 4 }}>
                <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>FOOTER & PIC</label>
                <button onClick={function() { updateSlide(activeSlide, "showBrandName", !currentSlide.showBrandName); }}
                  style={{ padding: "3px 12px", borderRadius: 20, border: "none", background: currentSlide.showBrandName ? GREEN : "#555", color: "#fff", cursor: "pointer", fontSize: 11, fontWeight: 600 }}>
                  {currentSlide.showBrandName ? "ON" : "OFF"}
                </button>
                {currentSlide.showBrandName && (
                  <>
                    <div style={{ flex: 1 }} />
                    {sizeLabel("", "brandName", 12, 60, null, currentSlide.brandNameColor, function(c) { updateSlide(activeSlide, "brandNameColor", c); }, "s-" + activeSlide + "-bn")}
                  </>
                )}
              </div>
              {currentSlide.showBrandName && (
                <div style={{ marginBottom: 8, paddingLeft: 8, borderLeft: "2px solid #555" }}>
                  <input value={currentSlide.brandNameText} onChange={function(e) { updateSlide(activeSlide, "brandNameText", e.target.value); }} placeholder="Brand name..."
                    style={Object.assign({}, inputStyle, { marginBottom: 6, fontSize: 12 })} />
                </div>
              )}

              {/* -- Top Corner toggle (per-slide) -- */}
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4, marginTop: 4 }}>
                <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>TOP CORNER</label>
                <button onClick={function() { updateSlide(activeSlide, "showTopCorner", !currentSlide.showTopCorner); }}
                  style={{ padding: "3px 12px", borderRadius: 20, border: "none", background: currentSlide.showTopCorner ? GREEN : "#555", color: "#fff", cursor: "pointer", fontSize: 11, fontWeight: 600 }}>
                  {currentSlide.showTopCorner ? "ON" : "OFF"}
                </button>
                {currentSlide.showTopCorner && (<><div style={{ flex: 1 }} />{sizeLabel("", "topCorner", 8, 60, null, currentSlide.topCornerColor, function(c) { updateSlide(activeSlide, "topCornerColor", c); }, "s-" + activeSlide + "-tc", currentSlide.topCornerOpacity, function(v) { updateSlide(activeSlide, "topCornerOpacity", v); })}</>)}
              </div>
              {currentSlide.showTopCorner && (
                <div style={{ marginBottom: 8, paddingLeft: 8, borderLeft: "2px solid #555" }}>
                  <input value={currentSlide.topCornerText} onChange={function(e) { updateSlide(activeSlide, "topCornerText", e.target.value); }} placeholder="Top corner..."
                    style={Object.assign({}, inputStyle, { marginBottom: 4, fontSize: 12 })} />
                </div>
              )}

              {/* -- Bottom Corner toggle (per-slide) -- */}
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4, marginTop: 4 }}>
                <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>BOTTOM CORNER</label>
                <button onClick={function() { updateSlide(activeSlide, "showBottomCorner", !currentSlide.showBottomCorner); }}
                  style={{ padding: "3px 12px", borderRadius: 20, border: "none", background: currentSlide.showBottomCorner ? GREEN : "#555", color: "#fff", cursor: "pointer", fontSize: 11, fontWeight: 600 }}>
                  {currentSlide.showBottomCorner ? "ON" : "OFF"}
                </button>
                {currentSlide.showBottomCorner && (<><div style={{ flex: 1 }} />{sizeLabel("", "bottomCorner", 10, 60, null, currentSlide.bottomCornerColor, function(c) { updateSlide(activeSlide, "bottomCornerColor", c); }, "s-" + activeSlide + "-bc", currentSlide.bottomCornerOpacity, function(v) { updateSlide(activeSlide, "bottomCornerOpacity", v); })}</>)}
              </div>
              {currentSlide.showBottomCorner && (
                <div style={{ marginBottom: 8, paddingLeft: 8, borderLeft: "2px solid #555" }}>
                  <input value={currentSlide.bottomCornerText} onChange={function(e) { updateSlide(activeSlide, "bottomCornerText", e.target.value); }} placeholder="Bottom corner..."
                    style={Object.assign({}, inputStyle, { marginBottom: 4, fontSize: 12 })} />
                </div>
              )}

              {/* -- Heading toggle (per-slide) -- */}
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4, marginTop: 4 }}>
                <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>HEADING</label>
                <button onClick={function() { updateSlide(activeSlide, "showHeading", !currentSlide.showHeading); }}
                  style={{ padding: "3px 12px", borderRadius: 20, border: "none", background: currentSlide.showHeading ? GREEN : "#555", color: "#fff", cursor: "pointer", fontSize: 11, fontWeight: 600 }}>
                  {currentSlide.showHeading ? "ON" : "OFF"}
                </button>
                {currentSlide.showHeading && (
                  <>
                    <button onClick={function() { updateSlide(activeSlide, "showAccentBar", !currentSlide.showAccentBar); }}
                      title="Accent bar"
                      style={{ padding: "2px 6px", borderRadius: 4, border: "1px solid #444", background: (currentSlide.showAccentBar !== false) ? "rgba(34,197,94,0.2)" : "#28283e", color: (currentSlide.showAccentBar !== false) ? GREEN : "#666", cursor: "pointer", fontSize: 9, fontWeight: 700, lineHeight: "14px" }}>
                      {"\u2501"}
                    </button>
                    <div style={{ flex: 1 }} />{sizeLabel("", "heading", 24, 160, null, currentSlide.titleColor, function(c) { updateSlide(activeSlide, "titleColor", c); }, "s-" + activeSlide + "-title")}
                  </>
                )}
              </div>
              {currentSlide.showHeading && (
                <div style={{ marginBottom: 8, paddingLeft: 8, borderLeft: "2px solid #555" }}>
                  <input value={currentSlide.title} onChange={function(e) { updateSlide(activeSlide, "title", e.target.value); }} placeholder="Heading..."
                    style={Object.assign({}, inputStyle, { marginBottom: 4, fontSize: 12 })} />
                </div>
              )}

              {/* Body | Cards toggle */}
              <div style={{ display: "flex", alignItems: "center", marginTop: 12, marginBottom: 6, gap: 4 }}>
                <span onClick={function() { updateSlide(activeSlide, "showCards", false); }}
                  style={{ fontWeight: 600, fontSize: 13, color: !currentSlide.showCards ? GREEN : "#555", letterSpacing: 0.5, cursor: "pointer" }}>BODY</span>
                <span style={{ color: "#2a2a3e", margin: "0 4px", fontSize: 14 }}>|</span>
                <span onClick={function() { updateSlide(activeSlide, "showCards", true); }}
                  style={{ fontWeight: 600, fontSize: 13, color: currentSlide.showCards ? GREEN : "#555", letterSpacing: 0.5, cursor: "pointer" }}>CARDS</span>
              </div>

              {/* Color swatch row - Text + Base always visible; Base greyed when Body mode */}
              <div style={{ display: "flex", gap: 8, marginBottom: 6 }}>
                {/* Text swatch - context-aware: bodyColor in Body mode, cardTextColor in Cards mode */}
                {(function() {
                  var isCards = currentSlide.showCards;
                  var pickerKey = "s-" + activeSlide + (isCards ? "-cardtext" : "-body");
                  var colorVal = isCards ? (currentSlide.cardTextColor || "#333333") : (currentSlide.bodyColor || "#ffffff");
                  var colorField = isCards ? "cardTextColor" : "bodyColor";
                  return (
                    <div style={{ display: "flex", alignItems: "center", gap: 4, position: "relative" }} data-picker={pickerKey}>
                      <span style={{ width: 18, height: 18, borderRadius: 4, background: colorVal, display: "block", border: openPicker === pickerKey ? "2px solid #6366f1" : "1px solid #444", boxSizing: "border-box", cursor: "pointer" }}
                        onClick={function(e) { e.stopPropagation(); setOpenPicker(openPicker === pickerKey ? null : pickerKey); }} />
                      <span style={{ fontSize: 11, color: openPicker === pickerKey ? "#a5b4fc" : "#777", fontWeight: 600 }}>Text</span>
                      {openPicker === pickerKey && (
                        <div style={{ position: "absolute", top: "100%", left: 0, zIndex: 60, marginTop: 4, background: "#1a1a30", border: "1px solid #444", borderRadius: 10, padding: 10, width: 200, boxShadow: "0 8px 24px rgba(0,0,0,0.6)" }}>
                          <div style={{ display: "grid", gridTemplateColumns: "repeat(8, 1fr)", gap: 4, marginBottom: 8 }}>
                            {INLINE_SWATCHES.map(function(c) { return (
                              <button key={c} onClick={function() { updateSlide(activeSlide, colorField, c); }}
                                style={{ width: 20, height: 20, borderRadius: 4, border: colorVal === c ? "2px solid #fff" : "1px solid #444", background: c, cursor: "pointer", padding: 0, boxShadow: colorVal === c ? "0 0 0 1px #6366f1" : "none" }} />
                            ); })}
                          </div>
                          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                            <input type="color" value={colorVal && colorVal.charAt(0) === "#" ? colorVal : "#ffffff"} onChange={function(e) { updateSlide(activeSlide, colorField, e.target.value); }}
                              style={{ width: 24, height: 24, border: "1px solid #444", borderRadius: 4, cursor: "pointer", background: "none", padding: 0 }} />
                            <input value={colorVal || ""} onChange={function(e) { updateSlide(activeSlide, colorField, e.target.value); }}
                              style={{ flex: 1, padding: "4px 6px", borderRadius: 4, border: "1px solid #444", background: "#0e0e1a", color: "#bbb", fontSize: 11, fontFamily: "monospace" }} />
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })()}
                {/* Base swatch (card bg) - greyed out in Body mode */}
                <div style={{ display: "flex", alignItems: "center", gap: 4, position: "relative", opacity: currentSlide.showCards ? 1 : 0.35 }} data-picker={"s-" + activeSlide + "-cardbg"}>
                  <span style={{ width: 18, height: 18, borderRadius: 4, background: currentSlide.cardBgColor || "#ffffff", display: "block", border: openPicker === "s-" + activeSlide + "-cardbg" ? "2px solid #6366f1" : "1px solid #444", boxSizing: "border-box", cursor: currentSlide.showCards ? "pointer" : "default" }}
                    onClick={function(e) { if (!currentSlide.showCards) return; e.stopPropagation(); setOpenPicker(openPicker === "s-" + activeSlide + "-cardbg" ? null : "s-" + activeSlide + "-cardbg"); }} />
                  <span style={{ fontSize: 11, color: openPicker === "s-" + activeSlide + "-cardbg" ? "#a5b4fc" : "#777", fontWeight: 600 }}>Base</span>
                  {openPicker === "s-" + activeSlide + "-cardbg" && currentSlide.showCards && (
                    <div style={{ position: "absolute", top: "100%", left: 0, zIndex: 60, marginTop: 4, background: "#1a1a30", border: "1px solid #444", borderRadius: 10, padding: 10, width: 200, boxShadow: "0 8px 24px rgba(0,0,0,0.6)" }}>
                      <div style={{ display: "grid", gridTemplateColumns: "repeat(8, 1fr)", gap: 4, marginBottom: 8 }}>
                        {INLINE_SWATCHES.map(function(c) { return (
                          <button key={c} onClick={function() { updateSlide(activeSlide, "cardBgColor", c); }}
                            style={{ width: 20, height: 20, borderRadius: 4, border: currentSlide.cardBgColor === c ? "2px solid #fff" : "1px solid #444", background: c, cursor: "pointer", padding: 0, boxShadow: currentSlide.cardBgColor === c ? "0 0 0 1px #6366f1" : "none" }} />
                        ); })}
                      </div>
                      <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                        <input type="color" value={currentSlide.cardBgColor || "#ffffff"} onChange={function(e) { updateSlide(activeSlide, "cardBgColor", e.target.value); }}
                          style={{ width: 24, height: 24, border: "1px solid #444", borderRadius: 4, cursor: "pointer", background: "none", padding: 0 }} />
                        <input value={currentSlide.cardBgColor || ""} onChange={function(e) { updateSlide(activeSlide, "cardBgColor", e.target.value); }}
                          style={{ flex: 1, padding: "4px 6px", borderRadius: 4, border: "1px solid #444", background: "#0e0e1a", color: "#bbb", fontSize: 11, fontFamily: "monospace" }} />
                      </div>
                    </div>
                  )}
                </div>
                <div style={{ flex: 1 }} />
                {/* Font size stepper - always visible, context-aware */}
                <div style={{ display: "flex", alignItems: "center", gap: 0, background: "#28283e", borderRadius: 4, border: "1px solid #444", height: 28, overflow: "hidden" }}>
                  {(function() {
                    var sk = currentSlide.showCards ? "cardText" : "body";
                    var mn = 12; var mx = 100;
                    return (
                      <>
                        <button onClick={function() { if (sizes[sk] > mn) setSize(sk, sizes[sk] - 1); }}
                          style={{ minWidth: 28, minHeight: 28, border: "none", background: "transparent", color: "#555", cursor: "pointer", fontSize: 14, padding: 0, lineHeight: "28px" }}>{"\u2212"}</button>
                        <input value={sizes[sk]} onChange={function(e) { var v = parseInt(e.target.value, 10); if (!isNaN(v)) setSize(sk, Math.max(mn, Math.min(mx, v))); }}
                          style={{ width: 30, height: 28, border: "none", borderLeft: "1px solid #444", borderRight: "1px solid #444", background: "transparent", color: "#666", fontSize: 11, fontFamily: "monospace", textAlign: "center", padding: 0, outline: "none" }} />
                        <button onClick={function() { if (sizes[sk] < mx) setSize(sk, sizes[sk] + 1); }}
                          style={{ minWidth: 28, minHeight: 28, border: "none", background: "transparent", color: "#555", cursor: "pointer", fontSize: 14, padding: 0, lineHeight: "28px" }}>+</button>
                      </>
                    );
                  })()}
                </div>
              </div>

              {/* Body content */}
              {!currentSlide.showCards && (
                <div>
                  <textarea value={currentSlide.body} onChange={function(e) { updateSlide(activeSlide, "body", e.target.value); }} rows={2}
                    style={{ width: "100%", padding: "8px 12px", borderRadius: 8, border: "1px solid #444", background: "#28283e", color: "#fff", fontSize: 13, boxSizing: "border-box", resize: "vertical" }} />
                  <p style={{ fontSize: 11, color: "#555", marginTop: 2, marginBottom: 8 }}>**word** = accent color.</p>
                </div>
              )}

              {/* Cards content */}
              {currentSlide.showCards && (
                <div>
                  {currentSlide.cards.map(function(c, i) {
                    return (
                      <div key={i} style={{ display: "flex", gap: 8, marginBottom: 6, alignItems: "center" }}>
                        <input value={c} onChange={function(e) { updateSlideCard(activeSlide, i, e.target.value); }} placeholder={"Card " + (i + 1) + "..."}
                          style={{ width: "100%", padding: "6px 10px", borderRadius: 8, border: "1px solid #444", background: "#28283e", color: "#fff", fontSize: 12, boxSizing: "border-box" }} />
                        {currentSlide.cards.length > 1 && (
                          <button onClick={function() { removeSlideCard(activeSlide, i); }} style={{ background: "none", border: "none", color: "#f87171", cursor: "pointer", fontSize: 18, padding: 4 }}>{"\u00d7"}</button>
                        )}
                      </div>
                    );
                  })}
                  {currentSlide.cards.length < 5 && (
                    <button onClick={function() { addSlideCard(activeSlide); }} style={{ background: "#28283e", border: "1px dashed #444", color: "#888", padding: "5px 12px", borderRadius: 8, cursor: "pointer", fontSize: 12, marginTop: 4 }}>+ Add Card</button>
                  )}
                  <p style={{ fontSize: 11, color: "#555", marginTop: 6, marginBottom: 4 }}>**word** = accent color.</p>
                </div>
              )}
            </div>
          )}


          </div>

          {/* -- COL 3: Preview -- */}
          <div style={{ flex: "0 0 auto", position: "sticky", top: 24, alignSelf: "flex-start" }}>
            <p style={{ fontSize: 13, color: "#666", marginBottom: 8, fontWeight: 600, letterSpacing: 1 }}>PREVIEW</p>
            <canvas ref={canvasRef} width={W} height={H}
              style={{ width: 360, height: 450, borderRadius: 12, border: "1px solid #222", display: "block" }} />
            <button onClick={downloadCurrentPDF}
              style={{ marginTop: 12, width: "100%", padding: "12px 0", borderRadius: 8, border: "none", background: "#6366f1", color: "#fff", fontSize: 14, fontWeight: 700, cursor: "pointer" }}>
              Download Current Slide (PDF)
            </button>
            {seriesSlides.length > 1 && (
              <button onClick={downloadAllPDF}
                style={{ marginTop: 6, width: "100%", padding: "10px 0", borderRadius: 8, border: "2px solid " + GREEN, background: "transparent", color: GREEN, fontSize: 13, fontWeight: 700, cursor: "pointer" }}>
                {"Download All " + seriesSlides.length + " Slides (PDF)"}
              </button>
            )}
            {pdfDownload && (
              <div style={{ marginTop: 8, display: "flex", alignItems: "center", gap: 6 }}>
                <a href={pdfDownload.url} download={pdfDownload.name}
                  onClick={function() { setTimeout(clearPdfDownload, 1500); }}
                  style={{ fontSize: 11, color: "#a5b4fc", textDecoration: "underline", flex: 1, wordBreak: "break-all" }}>
                  {"Save " + pdfDownload.name}
                </a>
                <button onClick={clearPdfDownload}
                  style={{ background: "none", border: "none", color: "#999", cursor: "pointer", fontSize: 14, padding: "0 2px", lineHeight: 1 }}>
                  {"\u00d7"}
                </button>
              </div>
            )}
            <p style={{ fontSize: 9, color: "#888", marginTop: 2, textAlign: "center" }}>Generated locally in browser; no upload.</p>
            {pdfError && (
              <p style={{ fontSize: 10, color: "#ef4444", marginTop: 4, margin: "4px 0 0 0" }}>{pdfError}</p>
            )}
            <div style={{ marginTop: 8 }}>
              <label style={{ fontSize: 10, color: "#666", display: "block", marginBottom: 2 }}>Filename prefix</label>
              <input value={exportPrefix}
                onChange={function(e) { setExportPrefix(e.target.value); }}
                placeholder="linkedin-slide"
                style={{ width: "100%", padding: "6px 8px", borderRadius: 6, border: "1px solid #444", background: "#28283e", color: "#ccc", fontSize: 11, boxSizing: "border-box", fontFamily: "monospace" }} />
            </div>
            <p style={{ fontSize: 10, color: "#555", marginTop: 6, textAlign: "center" }}>{"800 \u00d7 1000px"}</p>
          </div>
        </div>
      </div>

      {/* Confirm dialog overlay */}
      {confirmDialog && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 9999 }}
          onClick={function() { setConfirmDialog(null); }}>
          <div style={{ background: "#1a1a30", border: "1px solid #444", borderRadius: 10, padding: "20px 24px", maxWidth: 320, textAlign: "center", boxShadow: "0 8px 32px rgba(0,0,0,0.6)" }}
            onClick={function(e) { e.stopPropagation(); }}>
            <p style={{ color: "#ccc", fontSize: 13, margin: "0 0 16px 0", lineHeight: 1.4 }}>{confirmDialog.message}</p>
            <div style={{ display: "flex", gap: 10, justifyContent: "center" }}>
              <button onClick={function() { setConfirmDialog(null); }}
                style={{ padding: "6px 18px", borderRadius: 6, border: "1px solid #444", background: "#28283e", color: "#999", cursor: "pointer", fontSize: 12, fontWeight: 600 }}>
                Cancel
              </button>
              <button onClick={function() { confirmDialog.onConfirm(); setConfirmDialog(null); }}
                style={{ padding: "6px 18px", borderRadius: 6, border: "none", background: "#6366f1", color: "#fff", cursor: "pointer", fontSize: 12, fontWeight: 600 }}>
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Save Preset dialog overlay */}
      {presetDialog && presetDialog.type === "save" && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 9999 }}
          onClick={function() { setPresetDialog(null); }}>
          <div style={{ background: "#1a1a30", border: "1px solid #444", borderRadius: 10, padding: "20px 24px", maxWidth: 360, textAlign: "left", boxShadow: "0 8px 32px rgba(0,0,0,0.6)" }}
            onClick={function(e) { e.stopPropagation(); }}>
            <p style={{ color: "#ccc", fontSize: 14, fontWeight: 600, margin: "0 0 12px 0" }}>Save Preset</p>
            <label style={{ fontSize: 11, color: "#888", display: "block", marginBottom: 4 }}>Preset name</label>
            <input value={presetName} onChange={function(e) { setPresetName(e.target.value); }}
              placeholder="My Carousel"
              style={inputStyle} />
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 12, marginBottom: 16 }}>
              <button onClick={function() { setPresetIncludeImages(!presetIncludeImages); }}
                style={{ padding: "3px 12px", borderRadius: 20, border: "none",
                  background: presetIncludeImages ? GREEN : "#555",
                  color: "#fff", cursor: "pointer", fontSize: 11, fontWeight: 600 }}>
                {presetIncludeImages ? "ON" : "OFF"}
              </button>
              <span style={{ fontSize: 12, color: "#999" }}>Include images (larger file)</span>
            </div>
            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
              <button onClick={function() { setPresetDialog(null); }}
                style={{ padding: "6px 18px", borderRadius: 6, border: "1px solid #444", background: "#28283e", color: "#999", cursor: "pointer", fontSize: 12, fontWeight: 600 }}>
                Cancel
              </button>
              <button onClick={function() { downloadPreset(presetName, presetIncludeImages); setPresetDialog(null); }}
                style={{ padding: "6px 18px", borderRadius: 6, border: "none", background: "#6366f1", color: "#fff", cursor: "pointer", fontSize: 12, fontWeight: 600 }}>
                Save
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
