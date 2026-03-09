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

  if (footerBg !== "transparent") {
    ctx.fillStyle = footerBg || "#ffffff";
    ctx.beginPath();
    ctx.roundRect(badgeX, badgeY, badgeW, badgeH, CANVAS.footerBadgeRadius);
    ctx.fill();
  }

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

function drawTopCorner(ctx, text, color, opacity, size, fontFamily, fontBold, fontItalic, bgColor, bgOpacity) {
  var weight = fontBold !== false ? "700" : "normal";
  var fs = size || 13;
  ctx.font = composeFont(fontFamily || DEFAULT_FONT, fs, weight, !!fontItalic);
  if (bgColor && bgColor !== "transparent") {
    var bgPad = 6;
    var tw = ctx.measureText(text).width;
    var prevAlpha = ctx.globalAlpha;
    ctx.globalAlpha = (bgOpacity != null ? bgOpacity : 100) / 100;
    ctx.fillStyle = bgColor;
    ctx.beginPath();
    ctx.roundRect(MARGIN - bgPad, MARGIN - bgPad, tw + bgPad * 2, fs + bgPad * 2, BORDER_RADIUS);
    ctx.fill();
    ctx.globalAlpha = prevAlpha;
  }
  ctx.fillStyle = hexToRgba(color || "#ffffff", opacity != null ? opacity : 40);
  ctx.fillText(text, MARGIN, MARGIN + fs);
}

function drawBottomCorner(ctx, text, color, opacity, size, fontFamily, fontBold, fontItalic, bgColor, bgOpacity) {
  var weight = fontBold ? "700" : "600";
  var fs = size || 16;
  ctx.font = composeFont(fontFamily || DEFAULT_FONT, fs, weight, !!fontItalic);
  var textY = H - MARGIN;
  if (bgColor && bgColor !== "transparent") {
    var bgPad = 6;
    var tw = ctx.measureText(text).width;
    var prevAlpha = ctx.globalAlpha;
    ctx.globalAlpha = (bgOpacity != null ? bgOpacity : 100) / 100;
    ctx.fillStyle = bgColor;
    ctx.beginPath();
    ctx.roundRect(MARGIN - bgPad, textY - fs - bgPad, tw + bgPad * 2, fs + bgPad * 2, BORDER_RADIUS);
    ctx.fill();
    ctx.globalAlpha = prevAlpha;
  }
  ctx.fillStyle = hexToRgba(color || "#ffffff", opacity != null ? opacity : 35);
  ctx.fillText(text, MARGIN, textY);
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