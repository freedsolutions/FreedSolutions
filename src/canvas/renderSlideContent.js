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

    // Pre-compute heading lines for measurement + drawing
    var headingRawLines = (slide.title || "").split("\n");
    var headingLineData = [];
    for (var hli = 0; hli < headingRawLines.length; hli++) {
      var hRaw = headingRawLines[hli];
      if (hRaw.trim() === "") {
        headingLineData.push({ type: "blank" });
      } else {
        var headingParsed = extractAccentMarkers(hRaw);
        var titleLines = wrapText(ctx, headingParsed.cleanText, maxW, sizes.heading, titleWeight, titleFamily, titleItalic);
        headingLineData.push({ type: "text", parsed: headingParsed, lines: titleLines });
      }
    }

    // Measure total heading height
    var headingTotalH = 0;
    for (var hmi = 0; hmi < headingLineData.length; hmi++) {
      if (headingLineData[hmi].type === "blank") {
        headingTotalH += sizes.heading * CANVAS.headingBlankLH;
      } else {
        headingTotalH += headingLineData[hmi].lines.length * sizes.heading * CANVAS.headingLH;
      }
    }

    // Draw heading background bubble (tied to actual text metrics)
    var headingBg = slide.headingBgColor || "transparent";
    if (headingBg !== "transparent") {
      var hBgPad = 10;
      var hMetrics = ctx.measureText("Hg");
      var hAscent = hMetrics.actualBoundingBoxAscent;
      var hDescent = hMetrics.actualBoundingBoxDescent;
      var hFirstBL = topY + sizes.heading * CANVAS.headingLH;
      var hLastBL = topY + headingTotalH;
      var hBgTop = hFirstBL - hAscent - hBgPad;
      var hBgBot = hLastBL + hDescent + hBgPad;
      var prevAlpha = ctx.globalAlpha;
      ctx.globalAlpha = (slide.headingBgOpacity != null ? slide.headingBgOpacity : 100) / 100;
      ctx.fillStyle = headingBg;
      ctx.beginPath();
      ctx.roundRect(MARGIN, hBgTop, W - MARGIN * 2, hBgBot - hBgTop, BORDER_RADIUS);
      ctx.fill();
      ctx.globalAlpha = prevAlpha;
    }

    // Draw heading text from pre-computed data
    ty = topY + sizes.heading * CANVAS.headingLH;
    for (var hdi = 0; hdi < headingLineData.length; hdi++) {
      var hd = headingLineData[hdi];
      if (hd.type === "blank") { ty += sizes.heading * CANVAS.headingBlankLH; continue; }
      var hOffset = 0;
      for (var i = 0; i < hd.lines.length; i++) {
        renderLineWithAccents(ctx, hd.lines[i], pad, ty, sizes.heading, titleWeight, slide.titleColor || colors.text, colors.accent, hd.parsed.markers, hOffset, titleFamily, titleItalic);
        hOffset += hd.lines[i].length + 1;
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
      var cardPrevAlpha = ctx.globalAlpha;
      ctx.globalAlpha = (slide.cardBgOpacity != null ? slide.cardBgOpacity : 100) / 100;
      ctx.fillStyle = slide.cardBgColor || colors.cardBg;
      ctx.beginPath();
      ctx.roundRect(cardX, cy, cardW, cardH, CANVAS.cardRadius);
      ctx.fill();
      ctx.globalAlpha = cardPrevAlpha;
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
    ctx.font = composeFont(bodyFamily, sizes.body, bodyWeight, bodyItalic);
    var bodyLines = (slide.body || "").split("\n");
    var bodyStartY = (slide.showHeading !== false) ? ty + (expand ? CANVAS.bodyGapAfterHeadingExpand : CANVAS.bodyGapAfterHeading) : ty + (expand ? CANVAS.bodyGapNoHeadingExpand : CANVAS.bodyGapNoHeading);

    // Pre-compute body lines for measurement + drawing
    var bodyLineData = [];
    for (var bli = 0; bli < bodyLines.length; bli++) {
      var rawLine = bodyLines[bli];
      if (rawLine.trim() === "" || rawLine.replace(/\*\*(.+?)\*\*/g, "$1").trim() === "") {
        bodyLineData.push({ type: "blank" });
      } else {
        var lineParsed = extractAccentMarkers(rawLine);
        var wrapped = wrapText(ctx, lineParsed.cleanText, maxW, sizes.body, bodyWeight, bodyFamily, bodyItalic);
        bodyLineData.push({ type: "text", parsed: lineParsed, lines: wrapped });
      }
    }

    // Measure total body height
    var bodyTotalH = 0;
    for (var bmi = 0; bmi < bodyLineData.length; bmi++) {
      if (bodyLineData[bmi].type === "blank") {
        bodyTotalH += sizes.body * CANVAS.bodyBlankLH;
      } else {
        bodyTotalH += bodyLineData[bmi].lines.length * sizes.body * CANVAS.bodyLH;
      }
    }

    // Draw body background bubble (tied to actual text metrics)
    var bodyBg = slide.bodyBgColor || "transparent";
    if (bodyBg !== "transparent") {
      var bBgPad = 10;
      var bMetrics = ctx.measureText("Hg");
      var bAscent = bMetrics.actualBoundingBoxAscent;
      var bDescent = bMetrics.actualBoundingBoxDescent;
      var bFirstBL = bodyStartY;
      var bLastBL = bodyStartY + bodyTotalH - sizes.body * CANVAS.bodyLH;
      var bBgTop = bFirstBL - bAscent - bBgPad;
      var bBgBot = bLastBL + bDescent + bBgPad;
      var prevAlpha = ctx.globalAlpha;
      ctx.globalAlpha = (slide.bodyBgOpacity != null ? slide.bodyBgOpacity : 100) / 100;
      ctx.fillStyle = bodyBg;
      ctx.beginPath();
      ctx.roundRect(MARGIN, bBgTop, W - MARGIN * 2, bBgBot - bBgTop, BORDER_RADIUS);
      ctx.fill();
      ctx.globalAlpha = prevAlpha;
    }

    // Draw body text from pre-computed data
    var bodyY = bodyStartY;
    for (var bdi = 0; bdi < bodyLineData.length; bdi++) {
      var bd = bodyLineData[bdi];
      if (bd.type === "blank") { bodyY += sizes.body * CANVAS.bodyBlankLH; continue; }
      var bOffset = 0;
      for (var wi = 0; wi < bd.lines.length; wi++) {
        renderLineWithAccents(ctx, bd.lines[wi], pad, bodyY, sizes.body, bodyWeight, slide.bodyColor || colors.accent, colors.accent, bd.parsed.markers, bOffset, bodyFamily, bodyItalic);
        bOffset += bd.lines[wi].length + 1;
        bodyY += sizes.body * CANVAS.bodyLH;
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