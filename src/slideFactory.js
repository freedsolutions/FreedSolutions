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
    brandNameText: "Freed Solutions",
    brandNameColor: "#1a1a2e",
    showTopCorner: true,
    topCornerText: "FEATURE",
    topCornerColor: "#ffffff",
    topCornerOpacity: 40,
    showBottomCorner: false,
    bottomCornerText: "Freed Solutions",
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