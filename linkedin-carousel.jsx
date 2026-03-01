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
  { value: "Cambria, Georgia, serif", label: "Cambria" },
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
  if (!markers || markers.length === 0) {
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
  var badgeW = 220;
  var badgeX = (W - badgeW) / 2;
  var badgeY = borderBottom - badgeH / 2;

  ctx.fillStyle = footerBg || "#ffffff";
  ctx.beginPath();
  ctx.roundRect(badgeX, badgeY, badgeW, badgeH, 12);
  ctx.fill();

  ctx.fillStyle = footerText || "#1a1a2e";
  var footerWeight = fontBold !== false ? "bold" : "normal";
  ctx.font = composeFont(fontFamily || DEFAULT_FONT, textSize || 20, footerWeight, !!fontItalic);
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

function drawTopCorner(ctx, text, color, opacity, size, fontFamily, fontBold, fontItalic) {
  var weight = fontBold !== false ? "700" : "normal";
  ctx.font = composeFont(fontFamily || DEFAULT_FONT, size || 13, weight, !!fontItalic);
  ctx.fillStyle = hexToRgba(color || "#ffffff", opacity != null ? opacity : 40);
  ctx.fillText(text, MARGIN, MARGIN + (size || 13));
}

function drawBottomCorner(ctx, text, color, opacity, size, fontFamily, fontBold, fontItalic) {
  var weight = fontBold ? "bold" : "600";
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

function drawScreenshot(ctx, screenshot, x, y, w, h, scale, edgeToEdge) {
  var radius = edgeToEdge ? 0 : 12;
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
  var pad = 80;
  var innerPad = 20;
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
    ty = topY + sizes.heading * 1.22;
    var headingRawLines = (slide.title || "").split("\n");
    for (var hli = 0; hli < headingRawLines.length; hli++) {
      var hRaw = headingRawLines[hli];
      if (hRaw.trim() === "") { ty += sizes.heading * 0.5; continue; }
      var headingParsed = extractAccentMarkers(hRaw);
      var titleLines = wrapText(ctx, headingParsed.cleanText, maxW, sizes.heading, titleWeight, titleFamily, titleItalic);
      var hOffset = 0;
      for (var i = 0; i < titleLines.length; i++) {
        renderLineWithAccents(ctx, titleLines[i], pad, ty, sizes.heading, titleWeight, slide.titleColor || colors.text, colors.accent, headingParsed.markers, hOffset, titleFamily, titleItalic);
        hOffset += titleLines[i].length + 1;
        ty += sizes.heading * 1.22;
      }
    }

    if (slide.showAccentBar !== false && (!slide.showCards || !slide.cards || slide.cards.length === 0)) {
      var accentBarOffset = expand ? 0 : 10;
      ctx.fillStyle = colors.accent;
      ctx.fillRect(pad, ty + accentBarOffset, 50, 3);
    }
  }

  if (slide.showCards && slide.cards && slide.cards.length > 0) {
    var showChecks = slide.showCardChecks !== false;
    var cardStartY = (slide.showHeading !== false) ? ty + (expand ? 20 : 45) : ty + (expand ? 30 : 60);
    var cardPadV = 20;
    var gap = 20;
    var textPadding = 40;
    var cardContentW = maxW - 40;
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
      var textH = visibleLines * (sizes.cardText + 6) + emptyLines * (sizes.cardText * 0.5);
      cardHeights.push(Math.max(80, textH + cardPadV * 2 + 10));
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
      ctx.roundRect(cardX, cy, cardW, cardH, 16);
      ctx.fill();
      if (showChecks) {
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
      }
      ctx.save();
      ctx.beginPath();
      ctx.roundRect(cardX, cy, cardW, cardH, 16);
      ctx.clip();
      ctx.font = composeFont(cardFamily, sizes.cardText, cardWeight, cardItalic);
      var lineY = cy + 38;
      for (var cli = 0; cli < cardsLineData[ci].length; cli++) {
        var ld = cardsLineData[ci][cli];
        if (ld.empty) { lineY += sizes.cardText * 0.5; continue; }
        renderLineWithAccents(ctx, ld.text, pad + textPadding + 20, lineY, sizes.cardText, cardWeight, slide.cardTextColor || colors.cardText, colors.accent, ld.parsed.markers, ld.offset, cardFamily, cardItalic);
        lineY += sizes.cardText + 6;
      }
      ctx.restore();
      runningY += cardH + gap;
    }
    ty = runningY;
  } else if (slide.body) {
    var bodyLines = (slide.body || "").split("\n");
    var bodyY = (slide.showHeading !== false) ? ty + (expand ? 40 : 100) : ty + (expand ? 30 : 60);
    for (var bli = 0; bli < bodyLines.length; bli++) {
      var rawLine = bodyLines[bli];
      if (rawLine.trim() === "" || rawLine.replace(/\*\*(.+?)\*\*/g, "$1").trim() === "") {
        bodyY += sizes.body * 0.6;
      } else {
        var lineParsed = extractAccentMarkers(rawLine);
        var wrapped = wrapText(ctx, lineParsed.cleanText, maxW, sizes.body, bodyWeight, bodyFamily, bodyItalic);
        var bOffset = 0;
        for (var wi = 0; wi < wrapped.length; wi++) {
          renderLineWithAccents(ctx, wrapped[wi], pad, bodyY, sizes.body, bodyWeight, slide.bodyColor || colors.accent, colors.accent, lineParsed.markers, bOffset, bodyFamily, bodyItalic);
          bOffset += wrapped[wi].length + 1;
          bodyY += sizes.body * 1.4;
        }
      }
    }
    ty = bodyY + 10;
  }

  if (slide.showScreenshot) {
    var bottomBound = frameBottom ? frameBottom - 20 : H - 80;
    var hasHeading = slide.showHeading !== false;
    var ssFloor = expand ? (hasHeading ? 300 : 180) : (hasHeading ? 420 : 200);
    var ssY = Math.max(ty + 20, ssFloor);
    var ssX = expand ? 0 : pad;
    var ssW = expand ? W : maxW;
    var ssH = bottomBound - ssY;
    if (ssH > 60) {
      drawScreenshot(ctx, screenshot || null, ssX, ssY, ssW, ssH, scale, expand);
    }
  }
}

// ---------------------------------------
// Top-level render orchestrator (pure function)
// ---------------------------------------

function renderSlideToCanvas(ctx, slideIndex, seriesSlides, slideAssets, sizes) {
  ctx.clearRect(0, 0, W, H);
  var slide = seriesSlides[slideIndex] || seriesSlides[0];

  // Resolve custom bg image
  var customImg = (slide.bgType === "custom" && slide.customBgImage) ? slide.customBgImage : null;

  renderBg(ctx, slide.bgType, slide.solidColor, customImg, slide.geoLines, slide.geoEnabled);

  // Build render colors from per-slide properties with hard fallbacks for backward-compat
  var renderColors = {
    heading: slide.titleColor || "#ffffff",
    body: slide.bodyColor || "#ffffff",
    text: slide.titleColor || "#ffffff",
    accent: slide.accentColor || "#22c55e",
    border: hexToRgba(slide.borderColor || "#ffffff", slide.borderOpacity != null ? slide.borderOpacity : 25),
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
    showBrandName: true,
    brandNameText: "Brand Name",
    brandNameColor: "#1a1a2e",
    brandNameFontFamily: DEFAULT_FONT,
    brandNameBold: true,
    brandNameItalic: false,
    showTopCorner: true,
    topCornerText: "LABEL",
    topCornerColor: "#ffffff",
    topCornerFontFamily: DEFAULT_FONT,
    topCornerBold: true,
    topCornerItalic: false,
    topCornerOpacity: 40,
    showBottomCorner: false,
    bottomCornerText: "Brand Name",
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
    frameEnabled: true,
    accentColor: "#a5b4fc",
    borderColor: "#ffffff",
    borderOpacity: 25,
    footerBg: "#ffffff",
    profileImg: null,
    profilePicName: null
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

  var hasTypography = !!onFontFamilyChange;
  var isOpen = openPicker === pickerKey && !disabled;

  return (
    <div style={{ position: "relative" }} data-picker={pickerKey}>
      <button
        onClick={function(e) {
          if (disabled) return;
          e.stopPropagation();
          setOpenPicker(isOpen ? null : pickerKey);
        }}
        style={{
          width: 18, height: 18, borderRadius: 4,
          border: isOpen ? "2px solid #6366f1" : "1px solid #444",
          background: value,
          cursor: disabled ? "default" : "pointer",
          padding: 0, display: "block"
        }}
      />
      {isOpen && (
        <div style={pickerDropdownStyle}>
          {hasTypography && (
            <div style={{ marginBottom: 8, paddingBottom: 8, borderBottom: "1px solid #3a3a50" }}>
              <select value={fontFamily || DEFAULT_FONT} onChange={function(e) { onFontFamilyChange(e.target.value); }}
                style={{ width: "100%", padding: "4px 6px", borderRadius: 4, border: "1px solid #444", background: "#0e0e1a", color: "#bbb", fontSize: 11, marginBottom: 6, cursor: "pointer" }}>
                {FONT_OPTIONS.map(function(f) {
                  return <option key={f.value} value={f.value} style={{ fontFamily: f.value }}>{f.label}</option>;
                })}
              </select>
              <div style={{ display: "flex", gap: 4 }}>
                <button onClick={function() { onBoldChange(!bold); }}
                  title="Bold"
                  style={{ flex: 1, padding: "3px 0", borderRadius: 4, border: "1px solid #444", background: bold ? "rgba(165,180,252,0.25)" : "#28283e", color: bold ? "#a5b4fc" : "#666", cursor: "pointer", fontSize: 12, fontWeight: 900, lineHeight: "16px" }}>B</button>
                <button onClick={function() { onItalicChange(!italic); }}
                  title="Italic"
                  style={{ flex: 1, padding: "3px 0", borderRadius: 4, border: "1px solid #444", background: italic ? "rgba(165,180,252,0.25)" : "#28283e", color: italic ? "#a5b4fc" : "#666", cursor: "pointer", fontSize: 12, fontStyle: "italic", fontWeight: 600, lineHeight: "16px" }}>I</button>
              </div>
            </div>
          )}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(8, 1fr)", gap: 4, marginBottom: 8 }}>
            {INLINE_SWATCHES.map(function(c) {
              return (
                <button key={c} onClick={function() { onChange(c); }}
                  style={{
                    width: 20, height: 20, borderRadius: 4,
                    border: value === c ? "2px solid #fff" : "1px solid #444",
                    background: c, cursor: "pointer", padding: 0,
                    boxShadow: value === c ? "0 0 0 1px #6366f1" : "none"
                  }}
                />
              );
            })}
          </div>
          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <input type="color"
              value={value && value.charAt(0) === "#" ? value : "#ffffff"}
              onChange={function(e) { onChange(e.target.value); }}
              style={{ width: 24, height: 24, border: "1px solid #444", borderRadius: 4, cursor: "pointer", background: "none", padding: 0 }}
            />
            <input value={value}
              onChange={function(e) { onChange(e.target.value); }}
              style={{ flex: 1, padding: "4px 6px", borderRadius: 4, border: "1px solid #444", background: "#0e0e1a", color: "#bbb", fontSize: 11, fontFamily: "monospace" }}
            />
          </div>
          {onOpacityChange && (
            <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 8, paddingTop: 8, borderTop: "1px solid #3a3a50" }}>
              <span style={{ fontSize: 10, color: "#666", whiteSpace: "nowrap" }}>Opacity</span>
              <input type="range" min={0} max={100}
                value={opacityVal != null ? opacityVal : 100}
                onChange={function(e) { onOpacityChange(Number(e.target.value)); }}
                style={{ flex: 1 }}
              />
              <span style={{ fontSize: 10, color: "#555", width: 28, textAlign: "right" }}>
                {(opacityVal != null ? opacityVal : 100) + "%"}
              </span>
            </div>
          )}
        </div>
      )}
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

  var hasTypography = !!fontFamilySet;

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
              <div style={Object.assign({}, pickerDropdownStyle, { left: "auto", right: 0 })}>
                {hasTypography && (
                  <div style={{ marginBottom: 8, paddingBottom: 8, borderBottom: "1px solid #3a3a50" }}>
                    <select value={fontFamily || DEFAULT_FONT} onChange={function(e) { fontFamilySet(e.target.value); }}
                      style={{ width: "100%", padding: "4px 6px", borderRadius: 4, border: "1px solid #444", background: "#0e0e1a", color: "#bbb", fontSize: 11, marginBottom: 6, cursor: "pointer" }}>
                      {FONT_OPTIONS.map(function(f) {
                        return <option key={f.value} value={f.value} style={{ fontFamily: f.value }}>{f.label}</option>;
                      })}
                    </select>
                    <div style={{ display: "flex", gap: 4 }}>
                      <button onClick={function() { boldSet(!boldVal); }}
                        title="Bold"
                        style={{ flex: 1, padding: "3px 0", borderRadius: 4, border: "1px solid #444", background: boldVal ? "rgba(165,180,252,0.25)" : "#28283e", color: boldVal ? "#a5b4fc" : "#666", cursor: "pointer", fontSize: 12, fontWeight: 900, lineHeight: "16px" }}>B</button>
                      <button onClick={function() { italicSet(!italicVal); }}
                        title="Italic"
                        style={{ flex: 1, padding: "3px 0", borderRadius: 4, border: "1px solid #444", background: italicVal ? "rgba(165,180,252,0.25)" : "#28283e", color: italicVal ? "#a5b4fc" : "#666", cursor: "pointer", fontSize: 12, fontStyle: "italic", fontWeight: 600, lineHeight: "16px" }}>I</button>
                    </div>
                  </div>
                )}
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
          <button onClick={function() { if (sizes[sizeKey] > min) setSize(sizeKey, sizes[sizeKey] - 1); }}
            style={{ minWidth: 28, minHeight: 28, border: "none", background: "transparent", color: "#555", cursor: "pointer", fontSize: 14, padding: 0, lineHeight: "28px" }}>{"\u2212"}</button>
          <input value={sizes[sizeKey]} onChange={function(e) { var v = parseInt(e.target.value, 10); if (!isNaN(v)) setSize(sizeKey, Math.max(min, Math.min(max, v))); }}
            style={{ width: 30, height: 28, border: "none", borderLeft: "1px solid #444", borderRight: "1px solid #444", background: "transparent", color: "#666", fontSize: 11, fontFamily: "monospace", textAlign: "center", padding: 0, outline: "none" }} />
          <button onClick={function() { if (sizes[sizeKey] < max) setSize(sizeKey, sizes[sizeKey] + 1); }}
            style={{ minWidth: 28, minHeight: 28, border: "none", background: "transparent", color: "#555", cursor: "pointer", fontSize: 14, padding: 0, lineHeight: "28px" }}>+</button>
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
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
        <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>SLIDES</label>
      </div>
      <div style={{ display: "flex", gap: 8, marginBottom: 0, flexDirection: "column" }}>
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
                style={{ width: "100%", height: 64, borderRadius: 8, border: isDragTarget ? "2px dashed #6366f1" : (isActive ? "2px solid " + GREEN : "2px solid #555"), background: isDragTarget ? "rgba(99,102,241,0.10)" : (isActive ? "rgba(34,197,94,0.15)" : "#1a1a30"), color: isActive ? GREEN : "#aaa", cursor: isDragSource ? "grabbing" : "grab", fontSize: 22, fontWeight: 700, padding: 0, display: "flex", alignItems: "center", justifyContent: "center", opacity: isDragSource ? 0.4 : 1, transition: "opacity 0.15s, border 0.15s, background 0.15s" }}>
                {label}
              </button>
              {canRemove && (
                <button
                  onClick={function(e) { e.stopPropagation(); removeSlide(i); }}
                  onDragStart={function(e) { e.preventDefault(); e.stopPropagation(); }}
                  style={{ position: "absolute", top: -4, right: -4, width: 16, height: 16, borderRadius: 8, border: "none", background: "rgba(100,100,100,0.7)", color: "#f87171", cursor: "pointer", fontSize: 10, fontWeight: 700, padding: 0, display: "flex", alignItems: "center", justifyContent: "center", lineHeight: 1 }}>{"\u00d7"}</button>
              )}
            </div>
          );
        })}
        {seriesSlides.length < MAX_SLIDES && (
          <button onClick={addSlide}
            style={{ width: "100%", height: 64, borderRadius: 8, border: "2px dashed #555", background: "#1a1a30", color: "#888", cursor: "pointer", fontSize: 24, fontWeight: 700, padding: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>+</button>
        )}
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
//   updateSlide, updateBgField, syncBgToAll, resetBgToDefault,
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
  };

  // --- Slide CRUD ---

  var updateSlide = function(idx, field, val, shouldSnapshot) {
    if (shouldSnapshot) deps.pushUndo();
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
    deps.setConfirmDialog({
      message: "Apply Slide " + (activeSlide + 1) + "\u2019s background, profile, and screenshot settings to all slides?",
      onConfirm: function() {
        deps.pushUndo();
        var src = seriesSlides[activeSlide];
        var srcAsset = slideAssets[activeSlide] || null;
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
              footerBg: src.footerBg,
              profileImg: src.profileImg,
              profilePicName: src.profilePicName,
              showScreenshot: src.showScreenshot,
              expandScreenshot: src.expandScreenshot
            });
          });
        });
        setSlideAssets(function(prev) {
          var next = {};
          for (var i = 0; i < seriesSlides.length; i++) {
            if (srcAsset) {
              next[i] = Object.assign({}, srcAsset);
            }
          }
          return next;
        });
      }
    });
  };

  var resetBgToDefault = function() {
    deps.setConfirmDialog({
      message: "Reset Slide " + (activeSlide + 1) + "\u2019s background, profile, and screenshot to defaults?",
      onConfirm: function() {
        deps.pushUndo();
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
              accentColor: "#a5b4fc",
              borderColor: "#ffffff",
              borderOpacity: 25,
              footerBg: "#ffffff",
              profileImg: null,
              profilePicName: null,
              showScreenshot: false,
              expandScreenshot: false
            });
          });
        });
        setSlideAssets(function(prev) {
          var next = Object.assign({}, prev);
          delete next[activeSlide];
          return next;
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
    syncBgToAll: syncBgToAll, resetBgToDefault: resetBgToDefault,
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
// Params: canvasRef, seriesSlides, slideAssets, sizes, activeSlide
// Returns: { renderSlide }

function useCanvasRenderer(canvasRef, seriesSlides, slideAssets, sizes, activeSlide) {
  var renderTimerRef = useRef(null);

  var renderSlide = useCallback(function(ctx, slideIndex) {
    renderSlideToCanvas(ctx, slideIndex, seriesSlides, slideAssets, sizes);
  }, [sizes, seriesSlides, slideAssets]);

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
// Params: deps object { seriesSlides, slideAssets, sizes, setSizes,
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
  "solidColor", "bgType", "geoEnabled", "geoLines",
  "frameEnabled", "accentColor", "borderColor", "borderOpacity", "footerBg",
  "profilePicName"
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
      sizes: Object.assign({}, deps.sizes),
      slides: serializedSlides,
      images: images
    };
  };

  var loadPresetData = function(data) {
    deps.pushUndo();
    var loadToken = ++presetLoadTokenRef.current;

    if (data.sizes) {
      deps.setSizes(Object.assign({
        heading: 48, body: 38, cardText: 22,
        topCorner: 13, bottomCorner: 16, brandName: 20
      }, data.sizes));
    }

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
var inputStyle = { width: "100%", padding: "8px 12px", borderRadius: 8, border: "1px solid #444", background: "#28283e", color: "#fff", fontSize: 14, boxSizing: "border-box" };
var labelStyle = { display: "block", marginBottom: 6, fontWeight: 600, fontSize: 13, color: "#bbb", letterSpacing: 0.5 };
var INLINE_SWATCHES = ["#ffffff", "#1a1a2e", "#333333", "#22c55e", "#a5b4fc", "#f59e0b", "#fb7185", "#22d3ee", "#a78bfa", "#38bdf8", "#d97706", "#fef3c7", "#e0f2fe", "#e0e7ff", "#f0fdf4", "#9ca3af"];
var smallBtnStyle = { padding: "2px 8px", borderRadius: 4, border: "1px solid #444", background: "#28283e", color: "#ccc", cursor: "pointer", fontSize: 9, fontWeight: 600 };
var pickerDropdownStyle = { position: "absolute", top: "100%", left: 0, zIndex: 60, marginTop: 4, background: "#1a1a30", border: "1px solid #444", borderRadius: 10, padding: 10, width: 200, boxShadow: "0 8px 24px rgba(0,0,0,0.6)" };

export default function App() {
  var canvasRef = useRef(null);
  var [confirmDialog, setConfirmDialog] = useState(null);

  // Undo/redo
  var undoManagerRef = useRef(createUndoManager());
  var pushUndoRef = useRef(null);

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
      sizes: Object.assign({}, sizes),
      activeSlide: activeSlide,
      exportPrefix: exportPrefix
    };
  };

  var restoreSnapshot = function(snap) {
    setSeriesSlides(snap.seriesSlides);
    setSlideAssets(snap.slideAssets);
    setSizes(snap.sizes);
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
  var canvasRenderer = useCanvasRenderer(canvasRef, seriesSlides, slideAssets, sizes, activeSlide);
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
    seriesSlides: seriesSlides, slideAssets: slideAssets, sizes: sizes,
    setSizes: setSizes,
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

  return (
    <div style={{ fontFamily: '"Helvetica Neue", Helvetica, Arial, sans-serif', background: "#000000", minHeight: "100vh", color: "#e0e0e0", padding: 16 }}>
      <div style={{ maxWidth: 1520, margin: "0 auto" }}>
        <h2 style={{ color: "#fff", marginBottom: 16, fontSize: 20 }}>LinkedIn Carousel Generator</h2>

        <div style={{ display: "flex", gap: 20, alignItems: "flex-start" }}>

        {/* -- LEFT COLUMN: Presets + Slides -- */}
        <div style={{ flex: "0 0 136px", minWidth: 136, maxWidth: 136, alignSelf: "flex-start" }}>
          {/* --- PRESETS --- */}
          <div style={{ marginBottom: 0 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 4, marginBottom: 4 }}>
              <label style={Object.assign({}, labelStyle, { marginBottom: 0, fontSize: 11 })}>PRESETS</label>
              <button onClick={function() { presets.setPresetError(""); presets.setPresetName(exportPrefix || ""); presets.setPresetDialog({ type: "save" }); }}
                style={smallBtnStyle}>
                Save
              </button>
              <button onClick={function() { presets.setPresetError(""); if (presets.presetInputRef.current) presets.presetInputRef.current.click(); }}
                style={smallBtnStyle}>
                Load
              </button>
              <input ref={presets.presetInputRef} type="file" accept=".json" onChange={presets.handlePresetUpload} style={{ display: "none" }} />
            </div>
            {presets.presetDownload && (
              <div style={{ display: "flex", alignItems: "center", gap: 4, marginTop: 2 }}>
                <a href={presets.presetDownload.url} download={presets.presetDownload.name}
                  onClick={function() { setTimeout(presets.clearPresetDownload, 1500); }}
                  style={{ fontSize: 10, color: "#a5b4fc", textDecoration: "underline", flex: 1, wordBreak: "break-all" }}>
                  {"Save " + presets.presetDownload.name}
                </a>
                <button onClick={presets.clearPresetDownload}
                  style={{ background: "none", border: "none", color: "#999", cursor: "pointer", fontSize: 13, padding: "0 2px", lineHeight: 1 }}>
                  {"\u00d7"}
                </button>
              </div>
            )}
            {presets.presetError && (
              <div style={{ marginTop: 2, padding: "3px 6px", borderRadius: 6, background: "#3a1a1a", border: "1px solid #7f1d1d", color: "#fca5a5", fontSize: 10, display: "flex", alignItems: "center", gap: 4 }}>
                <span style={{ flex: 1 }}>{presets.presetError}</span>
                <button onClick={function() { presets.setPresetError(""); }}
                  style={{ background: "none", border: "none", color: "#fca5a5", cursor: "pointer", fontSize: 13, padding: "0 2px", lineHeight: 1 }}>{"\u00d7"}</button>
              </div>
            )}
          </div>
          <div style={{ borderTop: "1px solid #444", marginTop: 6, marginBottom: 6 }} />
          <div style={{ marginBottom: 10 }}>
            <button onClick={slideMgmt.duplicateSlide}
              style={{ width: "100%", padding: "6px 8px", borderRadius: 8, border: "1px solid #444", background: "#28283e", color: "#ccc", cursor: seriesSlides.length >= MAX_SLIDES ? "default" : "pointer", fontSize: 10, fontWeight: 700, opacity: seriesSlides.length >= MAX_SLIDES ? 0.4 : 1 }}>
              Duplicate
            </button>
          </div>
          <div style={{ background: "#10101a", border: "1px solid #343447", borderRadius: 10, padding: 12 }}>
            <SlideSelector seriesSlides={seriesSlides} activeSlide={activeSlide} setActiveSlide={setActiveSlide}
              dragFrom={slideMgmt.dragFrom} setDragFrom={slideMgmt.setDragFrom} dragOver={slideMgmt.dragOver} setDragOver={slideMgmt.setDragOver}
              reorderSlide={slideMgmt.reorderSlide} addSlide={slideMgmt.addSlide} duplicateSlide={slideMgmt.duplicateSlide}
              removeSlide={slideMgmt.removeSlide} />
          </div>
        </div>

        {/* -- CENTER PANE: Settings + Slide Editor -- */}
        <div style={{ flex: "1 1 0", minWidth: 420 }}>

        {/* --- BACKGROUND --- */}
          <div style={{ marginBottom: 14, position: "relative", paddingRight: 140 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
              <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>BACKGROUND</label>
              <button onClick={slideMgmt.syncBgToAll} style={smallBtnStyle}>
                Sync All
              </button>
              <button onClick={slideMgmt.resetBgToDefault} style={smallBtnStyle}>
                Reset
              </button>
            </div>

            {/* Background controls row */}
            <div style={{ display: "flex", gap: 14, alignItems: "stretch" }}>

              {/* Left zone: Solid/Photo pill + Accent / Base / Layer / Frame */}
              <div style={{ flex: "0 0 auto", display: "flex", flexDirection: "column" }}>

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
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <label style={{ fontSize: 13, color: "#999", fontWeight: 600, width: 46 }}>Accent</label>
                  <ColorPickerInline pickerKey="accent" value={currentSlide.accentColor || "#fff"} onChange={function(c) { updateBgField("accentColor", c); }} openPicker={openPicker} setOpenPicker={setOpenPicker} />
                </div>

                {/* Base row */}
                <div style={{ display: "flex", alignItems: "center", gap: 10, opacity: isCustomBg ? 0.35 : 1 }}>
                  <label style={{ fontSize: 13, color: "#999", fontWeight: 600, width: 46 }}>Base</label>
                  <ColorPickerInline pickerKey="solidColor" value={currentSlide.solidColor || "#fff"} onChange={function(c) { updateBgField("solidColor", c); }} openPicker={openPicker} setOpenPicker={setOpenPicker} disabled={isCustomBg} />
                </div>
                </div>

                {/* Spacer between groups */}
                <div style={{ height: 14 }} />

                {/* Group 2: Layer + Frame */}
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {/* Layer row */}
                <div style={{ display: "flex", alignItems: "center", gap: 10, opacity: isCustomBg ? 0.35 : 1 }}>
                  <label style={{ fontSize: 13, color: "#999", fontWeight: 600, width: 46 }}>Layer</label>
                  <button onClick={function() { if (!isCustomBg) updateBgField("geoEnabled", !currentSlide.geoEnabled); }}
                    style={{ minWidth: 44, padding: "3px 8px", borderRadius: 20, border: "none", background: (!isCustomBg && currentSlide.geoEnabled) ? GREEN : "#555", color: "#fff", cursor: isCustomBg ? "default" : "pointer", fontSize: 11, fontWeight: 600 }}>
                    {(!isCustomBg && currentSlide.geoEnabled) ? "ON" : "OFF"}
                  </button>
                  <div style={{ opacity: (isCustomBg || !currentSlide.geoEnabled) ? 0.5 : 1 }}>
                    <ColorPickerInline pickerKey="geoLines" value={currentSlide.geoLines} onChange={function(c) { updateBgField("geoLines", c); }} openPicker={openPicker} setOpenPicker={setOpenPicker} disabled={isCustomBg || !currentSlide.geoEnabled} />
                  </div>
                </div>

                {/* Frame row */}
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <label style={{ fontSize: 13, color: "#999", fontWeight: 600, width: 46 }}>Frame</label>
                  <button onClick={function() { updateBgField("frameEnabled", !currentSlide.frameEnabled); }}
                    style={{ minWidth: 44, padding: "3px 8px", borderRadius: 20, border: "none", background: currentSlide.frameEnabled ? GREEN : "#555", color: "#fff", cursor: "pointer", fontSize: 11, fontWeight: 600 }}>
                    {currentSlide.frameEnabled ? "ON" : "OFF"}
                  </button>
                  <div style={{ opacity: currentSlide.frameEnabled ? 1 : 0.35 }}>
                    <ColorPickerInline pickerKey="border" value={currentSlide.borderColor || "#fff"} onChange={function(c) { updateBgField("borderColor", c); }} openPicker={openPicker} setOpenPicker={setOpenPicker} disabled={!currentSlide.frameEnabled} opacityVal={currentSlide.borderOpacity} onOpacityChange={function(v) { updateBgField("borderOpacity", v); }} />
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <label style={{ fontSize: 13, color: "#999", fontWeight: 600, width: 46 }}>Footer</label>
                  <ColorPickerInline pickerKey="footerBg" value={currentSlide.footerBg || "#ffffff"} onChange={function(c) { updateBgField("footerBg", c); }} openPicker={openPicker} setOpenPicker={setOpenPicker} />
                </div>
                </div>

              </div>

              {/* Middle zone: upload + thumbnail + status */}
              <div style={{ flex: "0 1 180px", minWidth: 130, position: "relative", display: "flex", flexDirection: "column", alignItems: "center" }}>

                {/* Photo upload - above thumbnail; visible only in Photo mode */}
                <div style={{ width: "100%", marginBottom: 2, visibility: isCustomBg ? "visible" : "hidden" }}>
                  <input ref={slideMgmt.customBgInputRef} type="file" accept="image/*" onChange={function(e) { slideMgmt.handleCustomUpload(e); }} style={{ display: "none" }} />
                  <button onClick={function() { if (slideMgmt.customBgInputRef.current) slideMgmt.customBgInputRef.current.click(); }}
                    style={{ padding: "3px 8px", borderRadius: 4, border: "1px solid #444", background: "#28283e", color: "#ccc", cursor: "pointer", fontSize: 10, fontWeight: 600 }}>
                    Choose File
                  </button>
                  <p style={{ fontSize: 9, color: "#666", margin: "2px 0 0 0", wordBreak: "break-all", lineHeight: 1.3, minHeight: 10 }}>{currentSlide.customBgName || "\u00a0"}</p>
                </div>

                {/* Thumbnail preview */}
                <div style={{ width: "100%", maxWidth: 110, aspectRatio: "4/5", borderRadius: 6, overflow: "hidden", border: "2px solid #444", background: "#111119", position: "relative" }}>
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
                        <button onClick={slideMgmt.removeCustomBg} style={{ background: "none", border: "none", color: "#f87171", cursor: "pointer", fontSize: 9, padding: 0 }}>{"\u00d7"} Remove</button>
                      </div>
                    ) : (
                      <span style={{ fontSize: 9, color: "#555" }}>No image</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Right zone: Profile Pic + Screenshot (stacked) — absolutely positioned */}
              <div style={{ position: "absolute", top: 0, right: 0, width: 126, paddingLeft: 6, borderLeft: "1px solid #333", display: "flex", flexDirection: "column", alignItems: "stretch", gap: 6 }}>
                {/* Profile card */}
                <div style={{ background: "#0f0f1a", border: "1px solid #343447", borderRadius: 8, padding: "6px 6px 5px", display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center", position: "relative" }}>
                  {currentSlide.profileImg && (
                    <button onClick={slideMgmt.removeProfilePic}
                      title="Remove profile image"
                      style={{ position: "absolute", top: 4, right: 5, background: "none", border: "none", color: "#f87171", cursor: "pointer", fontSize: 11, fontWeight: 700, padding: 0, lineHeight: 1 }}>
                      {"\u00d7"}
                    </button>
                  )}
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 6, marginBottom: 4 }}>
                    <label style={{ fontSize: 10, color: "#888", fontWeight: 600, letterSpacing: 0.5, marginBottom: 0 }}>PROFILE</label>
                    <span style={{ fontSize: 9, color: "#555" }}>84{"\u00d7"}84</span>
                  </div>
                  <input ref={slideMgmt.profilePicInputRef} type="file" accept="image/*" onChange={slideMgmt.handleProfilePicUpload} style={{ display: "none" }} />
                  <button onClick={function() { if (slideMgmt.profilePicInputRef.current) slideMgmt.profilePicInputRef.current.click(); }}
                    style={{ width: "100%", padding: "3px 6px", borderRadius: 4, border: "1px solid #444", background: "#28283e", color: "#ccc", cursor: "pointer", fontSize: 9, fontWeight: 600, marginBottom: 4 }}>
                    Choose
                  </button>
                  <div style={{ width: 48, height: 48, borderRadius: "50%", overflow: "hidden", border: "2px solid #444", background: "#111119", display: "flex", alignItems: "center", justifyContent: "center" }}>
                    {currentSlide.profileImg ? (
                      <img src={currentSlide.profileImg.src} alt="Profile pic" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                    ) : (
                      <span style={{ fontSize: 9, color: "#555" }}>None</span>
                    )}
                  </div>
                </div>

                {/* Screenshot card */}
                {currentSlide && (
                  <div style={{ background: "#0f0f1a", border: "1px solid #343447", borderRadius: 8, padding: "6px 6px", display: "flex", flexDirection: "column", position: "relative" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 4, marginBottom: 5, justifyContent: "space-between" }}>
                      <label style={{ fontSize: 9, color: "#888", fontWeight: 600, letterSpacing: 0.5, marginBottom: 0 }}>SCREENSHOT</label>
                      <button onClick={function() { var next = !currentSlide.showScreenshot; updateSlide(activeSlide, "showScreenshot", next); if (!next) { slideMgmt.removeScreenshot(activeSlide); } }}
                        style={{ minWidth: 40, padding: "2px 8px", borderRadius: 20, border: "none", background: currentSlide.showScreenshot ? GREEN : "#555", color: "#fff", cursor: "pointer", fontSize: 9, fontWeight: 600 }}>
                        {currentSlide.showScreenshot ? "ON" : "OFF"}
                      </button>
                    </div>
                    {currentSlide.showScreenshot ? (
                      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                        <input ref={slideMgmt.screenshotInputRef} type="file" accept="image/*" onChange={function(e) { slideMgmt.handleScreenshotUpload(activeSlide, e); }} style={{ display: "none" }} />
                        <button onClick={function() { if (slideMgmt.screenshotInputRef.current) slideMgmt.screenshotInputRef.current.click(); }}
                          style={{ width: "100%", padding: "4px 6px", borderRadius: 4, border: "1px solid #444", background: "#28283e", color: "#ccc", cursor: "pointer", fontSize: 9, fontWeight: 600 }}>
                          Choose File
                        </button>
                        {getAsset(activeSlide).name && (
                          <p style={{ fontSize: 9, color: "#666", margin: "0", wordBreak: "break-all", lineHeight: 1.25 }}>{getAsset(activeSlide).name}</p>
                        )}
                        {getAsset(activeSlide).image ? (
                          <div>
                            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                              <span style={{ fontSize: 9, color: GREEN }}>{"\u2713"} Uploaded</span>
                              <button onClick={function() { slideMgmt.removeScreenshot(activeSlide); }} style={{ background: "none", border: "none", color: "#f87171", cursor: "pointer", fontSize: 9, padding: 0 }}>{"\u00d7"} Remove</button>
                            </div>
                            <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 6, overflow: "hidden" }}>
                              <span style={{ fontSize: 9, color: "#666" }}>Scale</span>
                              <input type="range" min={50} max={200} value={Math.round(getAsset(activeSlide).scale * 100)} onChange={function(e) { setScale(activeSlide, Number(e.target.value) / 100); }}
                                style={{ flex: 1, minWidth: 0 }} />
                              <span style={{ fontSize: 9, color: "#777", width: 32, textAlign: "right" }}>{Math.round(getAsset(activeSlide).scale * 100) + "%"}</span>
                            </div>
                          </div>
                        ) : (
                          <p style={{ fontSize: 9, color: "#555", margin: "0" }}>No image</p>
                        )}
                      </div>
                    ) : (
                      <div style={{ minHeight: 38, border: "1px dashed #333", borderRadius: 6, display: "flex", alignItems: "center", justifyContent: "center" }}>
                        <span style={{ fontSize: 9, color: "#555" }}>Enable to add image</span>
                      </div>
                    )}
                  </div>
                )}
              </div>

            </div>
          </div>

          {/* -- Divider before Slide Editor -- */}
          <div style={{ borderTop: "1px solid #444", marginTop: 10, marginBottom: 10 }} />

          {/* --- Bottom Section: Slide Editor --- */}

          {/* --- SLIDE EDITOR --- */}
          {currentSlide && (
            <div style={{ background: "#1a1a30", borderRadius: 10, padding: 14, border: "1px solid #3a3a50", marginBottom: 14 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                <span style={{ color: "#888", fontSize: 12, fontWeight: 600 }}>
                  {"SLIDE " + (activeSlide + 1)}
                </span>
                <div style={{ display: "flex", gap: 6 }}>
                  <button onClick={slideMgmt.duplicateSlide}
                    style={{ background: "none", border: "1px solid #444", color: "#ccc", cursor: seriesSlides.length >= MAX_SLIDES ? "default" : "pointer", fontSize: 11, padding: "3px 10px", borderRadius: 6, opacity: seriesSlides.length >= MAX_SLIDES ? 0.4 : 1 }}>Duplicate</button>
                  <button onClick={function() { slideMgmt.resetSlide(activeSlide); }}
                    style={{ background: "none", border: "1px solid #444", color: "#ccc", cursor: "pointer", fontSize: 11, padding: "3px 10px", borderRadius: 6 }}>Reset</button>
                  {seriesSlides.length > 1 && (
                    <button onClick={function() { slideMgmt.removeSlide(activeSlide); }}
                      style={{ background: "none", border: "1px solid #f8717133", color: "#f87171", cursor: "pointer", fontSize: 11, padding: "3px 10px", borderRadius: 6 }}>Remove</button>
                  )}
                </div>
              </div>

              {/* -- Footer & Pic toggle (per-slide) -- */}
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4, marginTop: 4 }}>
                <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>FOOTER & PIC</label>
                <button onClick={function() { updateSlide(activeSlide, "showBrandName", !currentSlide.showBrandName); }}
                  style={{ minWidth: 44, padding: "3px 12px", borderRadius: 20, border: "none", background: currentSlide.showBrandName ? GREEN : "#555", color: "#fff", cursor: "pointer", fontSize: 11, fontWeight: 600 }}>
                  {currentSlide.showBrandName ? "ON" : "OFF"}
                </button>
                {currentSlide.showBrandName && (
                  <>
                    <div style={{ flex: 1 }} />
                    <SizeControl sizeKey="brandName" min={12} max={60} sizes={sizes} setSize={setSize}
                      colorVal={currentSlide.brandNameColor} colorSet={function(c) { updateSlide(activeSlide, "brandNameColor", c); }}
                      colorPickerKey={"s-" + activeSlide + "-bn"} openPicker={openPicker} setOpenPicker={setOpenPicker}
                      fontFamily={currentSlide.brandNameFontFamily} fontFamilySet={function(v) { updateSlide(activeSlide, "brandNameFontFamily", v, true); }}
                      boldVal={currentSlide.brandNameBold} boldSet={function(v) { updateSlide(activeSlide, "brandNameBold", v, true); }}
                      italicVal={currentSlide.brandNameItalic} italicSet={function(v) { updateSlide(activeSlide, "brandNameItalic", v, true); }} />
                  </>
                )}
              </div>
              {currentSlide.showBrandName && (
                <div style={{ marginBottom: 8, paddingLeft: 8, borderLeft: "2px solid #555" }}>
                  <textarea value={currentSlide.brandNameText} onChange={function(e) { updateSlide(activeSlide, "brandNameText", e.target.value); var el = e.target; el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; }} onKeyDown={function(e) { if (e.key === "Enter") e.preventDefault(); }} placeholder="Brand name..." rows={1}
                    ref={function(el) { if (el) { el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; } }}
                    style={Object.assign({}, inputStyle, { marginBottom: 6, fontSize: 12, resize: "none", overflow: "hidden", maxHeight: "50vh", overflowY: "auto" })} />
                </div>
              )}

              {/* -- Top Corner toggle (per-slide) -- */}
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4, marginTop: 4 }}>
                <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>TOP CORNER</label>
                <button onClick={function() { updateSlide(activeSlide, "showTopCorner", !currentSlide.showTopCorner); }}
                  style={{ minWidth: 44, padding: "3px 12px", borderRadius: 20, border: "none", background: currentSlide.showTopCorner ? GREEN : "#555", color: "#fff", cursor: "pointer", fontSize: 11, fontWeight: 600 }}>
                  {currentSlide.showTopCorner ? "ON" : "OFF"}
                </button>
                {currentSlide.showTopCorner && (<><div style={{ flex: 1 }} />
                  <SizeControl sizeKey="topCorner" min={8} max={60} sizes={sizes} setSize={setSize}
                    colorVal={currentSlide.topCornerColor} colorSet={function(c) { updateSlide(activeSlide, "topCornerColor", c); }}
                    colorPickerKey={"s-" + activeSlide + "-tc"} openPicker={openPicker} setOpenPicker={setOpenPicker}
                    opacityVal={currentSlide.topCornerOpacity} opacitySet={function(v) { updateSlide(activeSlide, "topCornerOpacity", v); }}
                    fontFamily={currentSlide.topCornerFontFamily} fontFamilySet={function(v) { updateSlide(activeSlide, "topCornerFontFamily", v, true); }}
                    boldVal={currentSlide.topCornerBold} boldSet={function(v) { updateSlide(activeSlide, "topCornerBold", v, true); }}
                    italicVal={currentSlide.topCornerItalic} italicSet={function(v) { updateSlide(activeSlide, "topCornerItalic", v, true); }} />
                </>)}
              </div>
              {currentSlide.showTopCorner && (
                <div style={{ marginBottom: 8, paddingLeft: 8, borderLeft: "2px solid #555" }}>
                  <textarea value={currentSlide.topCornerText} onChange={function(e) { updateSlide(activeSlide, "topCornerText", e.target.value); var el = e.target; el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; }} onKeyDown={function(e) { if (e.key === "Enter") e.preventDefault(); }} placeholder="Top corner..." rows={1}
                    ref={function(el) { if (el) { el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; } }}
                    style={Object.assign({}, inputStyle, { marginBottom: 4, fontSize: 12, resize: "none", overflow: "hidden", maxHeight: "50vh", overflowY: "auto" })} />
                </div>
              )}

              {/* -- Bottom Corner toggle (per-slide) -- */}
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4, marginTop: 4 }}>
                <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>BOTTOM CORNER</label>
                <button onClick={function() { updateSlide(activeSlide, "showBottomCorner", !currentSlide.showBottomCorner); }}
                  style={{ minWidth: 44, padding: "3px 12px", borderRadius: 20, border: "none", background: currentSlide.showBottomCorner ? GREEN : "#555", color: "#fff", cursor: "pointer", fontSize: 11, fontWeight: 600 }}>
                  {currentSlide.showBottomCorner ? "ON" : "OFF"}
                </button>
                {currentSlide.showBottomCorner && (<><div style={{ flex: 1 }} />
                  <SizeControl sizeKey="bottomCorner" min={10} max={60} sizes={sizes} setSize={setSize}
                    colorVal={currentSlide.bottomCornerColor} colorSet={function(c) { updateSlide(activeSlide, "bottomCornerColor", c); }}
                    colorPickerKey={"s-" + activeSlide + "-bc"} openPicker={openPicker} setOpenPicker={setOpenPicker}
                    opacityVal={currentSlide.bottomCornerOpacity} opacitySet={function(v) { updateSlide(activeSlide, "bottomCornerOpacity", v); }}
                    fontFamily={currentSlide.bottomCornerFontFamily} fontFamilySet={function(v) { updateSlide(activeSlide, "bottomCornerFontFamily", v, true); }}
                    boldVal={currentSlide.bottomCornerBold} boldSet={function(v) { updateSlide(activeSlide, "bottomCornerBold", v, true); }}
                    italicVal={currentSlide.bottomCornerItalic} italicSet={function(v) { updateSlide(activeSlide, "bottomCornerItalic", v, true); }} />
                </>)}
              </div>
              {currentSlide.showBottomCorner && (
                <div style={{ marginBottom: 8, paddingLeft: 8, borderLeft: "2px solid #555" }}>
                  <textarea value={currentSlide.bottomCornerText} onChange={function(e) { updateSlide(activeSlide, "bottomCornerText", e.target.value); var el = e.target; el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; }} onKeyDown={function(e) { if (e.key === "Enter") e.preventDefault(); }} placeholder="Bottom corner..." rows={1}
                    ref={function(el) { if (el) { el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; } }}
                    style={Object.assign({}, inputStyle, { marginBottom: 4, fontSize: 12, resize: "none", overflow: "hidden", maxHeight: "50vh", overflowY: "auto" })} />
                </div>
              )}

              {/* -- Heading toggle (per-slide) -- */}
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4, marginTop: 4 }}>
                <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>HEADING</label>
                <button onClick={function() { updateSlide(activeSlide, "showHeading", !currentSlide.showHeading); }}
                  style={{ minWidth: 44, padding: "3px 12px", borderRadius: 20, border: "none", background: currentSlide.showHeading ? GREEN : "#555", color: "#fff", cursor: "pointer", fontSize: 11, fontWeight: 600 }}>
                  {currentSlide.showHeading ? "ON" : "OFF"}
                </button>
                {!currentSlide.showCards ? (
                  <button onClick={function() { updateSlide(activeSlide, "showAccentBar", !currentSlide.showAccentBar, true); }}
                    title="Accent bar"
                    style={{ padding: "2px 6px", borderRadius: 4, border: "1px solid #444", background: (currentSlide.showAccentBar !== false) ? "rgba(165,180,252,0.2)" : "#28283e", color: (currentSlide.showAccentBar !== false) ? "#a5b4fc" : "#666", cursor: "pointer", fontSize: 9, fontWeight: 700, lineHeight: "14px" }}>
                    {"\u2501"}
                  </button>
                ) : (
                  <button onClick={function() { updateSlide(activeSlide, "showCardChecks", !(currentSlide.showCardChecks !== false), true); }}
                    title="Card checkmarks"
                    style={{ padding: "2px 6px", borderRadius: 4, border: "1px solid #444", background: (currentSlide.showCardChecks !== false) ? "rgba(165,180,252,0.2)" : "#28283e", color: (currentSlide.showCardChecks !== false) ? "#a5b4fc" : "#666", cursor: "pointer", fontSize: 9, fontWeight: 700, lineHeight: "14px" }}>
                    {"\u2713"}
                  </button>
                )}
                {currentSlide.showHeading && (
                  <>
                    <div style={{ flex: 1 }} />
                    <SizeControl sizeKey="heading" min={24} max={160} sizes={sizes} setSize={setSize}
                      colorVal={currentSlide.titleColor} colorSet={function(c) { updateSlide(activeSlide, "titleColor", c); }}
                      colorPickerKey={"s-" + activeSlide + "-title"} openPicker={openPicker} setOpenPicker={setOpenPicker}
                      fontFamily={currentSlide.titleFontFamily} fontFamilySet={function(v) { updateSlide(activeSlide, "titleFontFamily", v, true); }}
                      boldVal={currentSlide.titleBold} boldSet={function(v) { updateSlide(activeSlide, "titleBold", v, true); }}
                      italicVal={currentSlide.titleItalic} italicSet={function(v) { updateSlide(activeSlide, "titleItalic", v, true); }} />
                  </>
                )}
              </div>
              {currentSlide.showHeading && (
                <div style={{ marginBottom: 8, paddingLeft: 8, borderLeft: "2px solid #555" }}>
                  <textarea value={currentSlide.title} onChange={function(e) { updateSlide(activeSlide, "title", e.target.value); var el = e.target; el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; }} placeholder="Heading..." rows={1}
                    ref={function(el) { if (el) { el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; } }}
                    style={Object.assign({}, inputStyle, { marginBottom: 4, fontSize: 12, resize: "none", overflow: "hidden", maxHeight: "50vh", overflowY: "auto" })} />
                </div>
              )}

              {/* Body | Cards toggle */}
              <div style={{ display: "flex", alignItems: "center", marginTop: 12, marginBottom: 6, gap: 4 }}>
                <span onClick={function() { updateSlide(activeSlide, "showCards", false); }}
                  style={{ fontWeight: 600, fontSize: 13, color: !currentSlide.showCards ? GREEN : "#555", letterSpacing: 0.5, cursor: "pointer" }}>BODY</span>
                <span style={{ color: "#2a2a3e", margin: "0 4px", fontSize: 14 }}>|</span>
                <span onClick={function() { updateSlide(activeSlide, "showCards", true); }}
                  style={{ fontWeight: 600, fontSize: 13, color: currentSlide.showCards ? GREEN : "#555", letterSpacing: 0.5, cursor: "pointer" }}>CARDS</span>
                <button onClick={function() { updateSlide(activeSlide, "expandScreenshot", !currentSlide.expandScreenshot, true); }}
                  title="Expand screenshot area"
                  style={{ padding: "2px 6px", borderRadius: 4, border: "1px solid #444", background: currentSlide.expandScreenshot ? "rgba(165,180,252,0.2)" : "#28283e", color: currentSlide.expandScreenshot ? "#a5b4fc" : "#666", cursor: "pointer", fontSize: 9, fontWeight: 700, lineHeight: "14px", marginLeft: 6 }}>
                  {"\u2922"}
                </button>
                <div style={{ flex: 1 }} />
                {/* Font size stepper - always visible, context-aware */}
                {(function() { var sk = currentSlide.showCards ? "cardText" : "body"; return (
                <div style={{ display: "flex", alignItems: "center", gap: 0, background: "#28283e", borderRadius: 4, border: "1px solid #444", height: 28, overflow: "hidden" }}>
                  <button onClick={function() { if (sizes[sk] > 12) setSize(sk, sizes[sk] - 1); }}
                    style={{ minWidth: 28, minHeight: 28, border: "none", background: "transparent", color: "#555", cursor: "pointer", fontSize: 14, padding: 0, lineHeight: "28px" }}>{"\u2212"}</button>
                  <input value={sizes[sk]} onChange={function(e) { var v = parseInt(e.target.value, 10); if (!isNaN(v)) setSize(sk, Math.max(12, Math.min(100, v))); }}
                    style={{ width: 30, height: 28, border: "none", borderLeft: "1px solid #444", borderRight: "1px solid #444", background: "transparent", color: "#666", fontSize: 11, fontFamily: "monospace", textAlign: "center", padding: 0, outline: "none" }} />
                  <button onClick={function() { if (sizes[sk] < 100) setSize(sk, sizes[sk] + 1); }}
                    style={{ minWidth: 28, minHeight: 28, border: "none", background: "transparent", color: "#555", cursor: "pointer", fontSize: 14, padding: 0, lineHeight: "28px" }}>+</button>
                </div>
                ); })()}
              </div>

              {/* Color swatch row */}
              <div style={{ display: "flex", gap: 16, marginTop: 6, marginBottom: 6, alignItems: "center" }}>
                {/* Text swatch - context-aware: bodyColor in Body mode, cardTextColor in Cards mode */}
                <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                  <ColorPickerInline pickerKey={"s-" + activeSlide + (currentSlide.showCards ? "-cardtext" : "-body")} value={currentSlide.showCards ? (currentSlide.cardTextColor || "#333333") : (currentSlide.bodyColor || "#ffffff")} onChange={function(c) { updateSlide(activeSlide, currentSlide.showCards ? "cardTextColor" : "bodyColor", c); }} openPicker={openPicker} setOpenPicker={setOpenPicker}
                    fontFamily={currentSlide.showCards ? currentSlide.cardFontFamily : currentSlide.bodyFontFamily}
                    onFontFamilyChange={function(v) { updateSlide(activeSlide, currentSlide.showCards ? "cardFontFamily" : "bodyFontFamily", v, true); }}
                    bold={currentSlide.showCards ? currentSlide.cardBold : currentSlide.bodyBold}
                    onBoldChange={function(v) { updateSlide(activeSlide, currentSlide.showCards ? "cardBold" : "bodyBold", v, true); }}
                    italic={currentSlide.showCards ? currentSlide.cardItalic : currentSlide.bodyItalic}
                    onItalicChange={function(v) { updateSlide(activeSlide, currentSlide.showCards ? "cardItalic" : "bodyItalic", v, true); }} />
                  <span style={{ fontSize: 11, color: "#777", fontWeight: 600 }}>Text</span>
                </div>
                {/* Base swatch (card bg) - greyed out in Body mode */}
                <div style={{ display: "flex", alignItems: "center", gap: 4, opacity: currentSlide.showCards ? 1 : 0.35 }}>
                  <ColorPickerInline pickerKey={"s-" + activeSlide + "-cardbg"} value={currentSlide.cardBgColor || "#ffffff"} onChange={function(c) { updateSlide(activeSlide, "cardBgColor", c); }} openPicker={openPicker} setOpenPicker={setOpenPicker} disabled={!currentSlide.showCards} />
                  <span style={{ fontSize: 11, color: "#777", fontWeight: 600 }}>Base</span>
                </div>
              </div>

              {/* Body content */}
              {!currentSlide.showCards && (
                <div>
                  <textarea value={currentSlide.body} onChange={function(e) { updateSlide(activeSlide, "body", e.target.value); var el = e.target; el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; }} rows={1}
                    ref={function(el) { if (el) { el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; } }}
                    style={{ width: "100%", padding: "8px 12px", borderRadius: 8, border: "1px solid #444", background: "#28283e", color: "#fff", fontSize: 13, boxSizing: "border-box", resize: "none", overflow: "hidden", maxHeight: "50vh", overflowY: "auto" }} />
                  <p style={{ fontSize: 11, color: "#555", marginTop: 2, marginBottom: 8 }}>**word** = accent color.</p>
                </div>
              )}

              {/* Cards content */}
              {currentSlide.showCards && (
                <div>
                  {currentSlide.cards.map(function(c, i) {
                    return (
                      <div key={i} style={{ display: "flex", gap: 8, marginBottom: 6, alignItems: "center" }}>
                        <textarea value={c} onChange={function(e) { slideMgmt.updateSlideCard(activeSlide, i, e.target.value); var el = e.target; el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; }} placeholder={"Card " + (i + 1) + "..."} rows={1}
                          ref={function(el) { if (el) { el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; } }}
                          style={{ width: "100%", padding: "6px 10px", borderRadius: 8, border: "1px solid #444", background: "#28283e", color: "#fff", fontSize: 12, boxSizing: "border-box", resize: "none", overflow: "hidden", maxHeight: "50vh", overflowY: "auto" }} />
                        {currentSlide.cards.length > 1 && (
                          <button onClick={function() { slideMgmt.removeSlideCard(activeSlide, i); }} style={{ background: "none", border: "none", color: "#f87171", cursor: "pointer", fontSize: 18, padding: 4 }}>{"\u00d7"}</button>
                        )}
                      </div>
                    );
                  })}
                  {currentSlide.cards.length < 5 && (
                    <button onClick={function() { slideMgmt.addSlideCard(activeSlide); }} style={{ background: "#28283e", border: "1px dashed #444", color: "#888", padding: "5px 12px", borderRadius: 8, cursor: "pointer", fontSize: 12, marginTop: 4 }}>+ Add Card</button>
                  )}
                  <p style={{ fontSize: 11, color: "#555", marginTop: 6, marginBottom: 4 }}>**word** = accent color.</p>
                </div>
              )}
            </div>
          )}

        </div>

          {/* -- RIGHT PANE: Preview -- */}
          <div style={{ flex: "1 1 0", minWidth: 360, alignSelf: "flex-start" }}>
            <p style={{ fontSize: 13, color: "#666", marginBottom: 8, fontWeight: 600, letterSpacing: 1 }}>PREVIEW</p>
            <div style={{ marginBottom: 8 }}>
              <label style={{ fontSize: 10, color: "#666", display: "block", marginBottom: 2 }}>Filename prefix</label>
              <input value={exportPrefix}
                onChange={function(e) { setExportPrefix(e.target.value); }}
                placeholder="linkedin-slide"
                style={{ width: "100%", padding: "6px 8px", borderRadius: 6, border: "1px solid #444", background: "#28283e", color: "#ccc", fontSize: 11, boxSizing: "border-box", fontFamily: "monospace" }} />
            </div>
            <button onClick={downloadCurrentPDF}
              style={{ marginTop: 0, width: "100%", padding: "12px 0", borderRadius: 8, border: "none", background: "#6366f1", color: "#fff", fontSize: 14, fontWeight: 700, cursor: "pointer" }}>
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
            {pdfError && (
              <p style={{ fontSize: 10, color: "#ef4444", marginTop: 4, margin: "4px 0 0 0" }}>{pdfError}</p>
            )}
            <canvas ref={canvasRef} width={W} height={H}
              style={{ width: "100%", height: "auto", borderRadius: 12, border: "1px solid #222", display: "block", marginTop: 10 }} />
            <p style={{ fontSize: 9, color: "#888", marginTop: 2, textAlign: "center" }}>Generated locally in browser; no upload.</p>
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
      {presets.presetDialog && presets.presetDialog.type === "save" && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 9999 }}
          onClick={function() { presets.setPresetDialog(null); }}>
          <div style={{ background: "#1a1a30", border: "1px solid #444", borderRadius: 10, padding: "20px 24px", maxWidth: 360, textAlign: "left", boxShadow: "0 8px 32px rgba(0,0,0,0.6)" }}
            onClick={function(e) { e.stopPropagation(); }}>
            <p style={{ color: "#ccc", fontSize: 14, fontWeight: 600, margin: "0 0 12px 0" }}>Save Preset</p>
            <label style={{ fontSize: 11, color: "#888", display: "block", marginBottom: 4 }}>Preset name</label>
            <input value={presets.presetName} onChange={function(e) { presets.setPresetName(e.target.value); }}
              placeholder="My Carousel"
              style={inputStyle} />
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 12, marginBottom: 16 }}>
              <button onClick={function() { presets.setPresetIncludeImages(!presets.presetIncludeImages); }}
                style={{ minWidth: 44, padding: "3px 12px", borderRadius: 20, border: "none",
                  background: presets.presetIncludeImages ? GREEN : "#555",
                  color: "#fff", cursor: "pointer", fontSize: 11, fontWeight: 600 }}>
                {presets.presetIncludeImages ? "ON" : "OFF"}
              </button>
              <span style={{ fontSize: 12, color: "#999" }}>Include images (larger file)</span>
            </div>
            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
              <button onClick={function() { presets.setPresetDialog(null); }}
                style={{ padding: "6px 18px", borderRadius: 6, border: "1px solid #444", background: "#28283e", color: "#999", cursor: "pointer", fontSize: 12, fontWeight: 600 }}>
                Cancel
              </button>
              <button onClick={function() { presets.downloadPreset(presets.presetName, presets.presetIncludeImages); presets.setPresetDialog(null); }}
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
