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