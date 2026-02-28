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
    bodyColor: "#a5b4fc",
    showCards: false,
    showCardChecks: true,
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
    accentColor: "#a5b4fc",
    borderColor: "#ffffff",
    borderOpacity: 25,
    footerBg: "#ffffff"
  };
}