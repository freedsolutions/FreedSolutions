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
  var baseBorderBottom = slide.showBrandName ? H - MARGIN - FOOTER_PIC_SIZE + 8 - FOOTER_BADGE_H / 2 : H - MARGIN - 16;
  var bottomCornerOffset = (slide.showBottomCorner && slide.bottomCornerText) ? Math.max(0, baseBorderBottom - (H - MARGIN + 12 - sizes.bottomCorner - 6) + 8) : 0;
  var borderBottom = baseBorderBottom - bottomCornerOffset;

  if (slide.showTopCorner && slide.topCornerText) {
    drawTopCorner(ctx, slide.topCornerText, slide.topCornerColor, slide.topCornerOpacity, sizes.topCorner, slide.topCornerFontFamily, slide.topCornerBold, slide.topCornerItalic, slide.topCornerBgColor, slide.topCornerBgOpacity);
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
    drawBottomCorner(ctx, slide.bottomCornerText, slide.bottomCornerColor, slide.bottomCornerOpacity, sizes.bottomCorner, slide.bottomCornerFontFamily, slide.bottomCornerBold, slide.bottomCornerItalic, slide.bottomCornerBgColor, slide.bottomCornerBgOpacity);
  }
}