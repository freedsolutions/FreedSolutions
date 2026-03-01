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
      ctx.fillStyle = colors.accent;
      ctx.fillRect(pad, ty + 10, 50, 3);
    }
  }

  if (slide.showCards && slide.cards && slide.cards.length > 0) {
    var showChecks = slide.showCardChecks !== false;
    var cardStartY = (slide.showHeading !== false) ? ty + 45 : ty + 60;
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
    var bodyY = (slide.showHeading !== false) ? ty + 100 : ty + 60;
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
    var ssY = Math.max(ty + 20, 420);
    var ssW = maxW;
    var ssH = bottomBound - ssY;
    if (ssH > 60) {
      drawScreenshot(ctx, screenshot || null, pad, ssY, ssW, ssH, scale);
    }
  }
}