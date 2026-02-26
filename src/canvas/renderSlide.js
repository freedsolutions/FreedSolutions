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