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