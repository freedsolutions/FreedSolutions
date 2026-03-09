// ===================================================
// usePresets Hook
// ===================================================
// Manages preset serialize/deserialize, export/import, and stale-load guard.
// Params: deps object { seriesSlides, slideAssets,
//   exportPrefix, setExportPrefix, setSeriesSlides,
//   setSlideAssets, setActiveSlide, clearPdfDownload, setPdfError, pushUndo,
//   setConfirmDialog }
// Returns: { presetInputRef, presetDownload, presetDialog, setPresetDialog,
//   presetName, setPresetName, presetIncludeImages, setPresetIncludeImages,
//   presetError, setPresetError, downloadPreset, handlePresetUpload,
//   clearPresetDownload }

var PRESET_SLIDE_KEYS = [
  "title", "showHeading", "showAccentBar", "body",
  "titleColor", "titleFontFamily", "titleBold", "titleItalic", "headingBgColor", "headingBgOpacity",
  "bodyColor", "bodyFontFamily", "bodyBold", "bodyItalic", "bodyBgColor", "bodyBgOpacity",
  "showCards", "showCardChecks", "cards",
  "cardTextColor", "cardFontFamily", "cardBold", "cardItalic", "cardBgColor", "cardBgOpacity",
  "expandScreenshot", "showScreenshot",
  "showBrandName", "brandNameText", "brandNameColor",
  "brandNameFontFamily", "brandNameBold", "brandNameItalic",
  "showTopCorner", "topCornerText", "topCornerColor",
  "topCornerFontFamily", "topCornerBold", "topCornerItalic", "topCornerOpacity", "topCornerBgColor", "topCornerBgOpacity",
  "showBottomCorner", "bottomCornerText", "bottomCornerColor",
  "bottomCornerFontFamily", "bottomCornerBold", "bottomCornerItalic", "bottomCornerOpacity", "bottomCornerBgColor", "bottomCornerBgOpacity",
  "solidColor", "bgType", "geoEnabled", "geoLines", "geoOpacity", "geoShape",
  "frameEnabled", "accentColor", "decorationColor", "borderColor", "borderOpacity", "footerBg",
  "profilePicName",
  "headingSize", "bodySize", "cardTextSize",
  "topCornerSize", "bottomCornerSize", "brandNameSize"
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
      slides: serializedSlides,
      images: images
    };
  };

  var loadPresetData = function(data) {
    deps.pushUndo();
    var loadToken = ++presetLoadTokenRef.current;

    // Legacy: global sizes → per-slide migration handled after newSlides are built

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

    // Legacy migration: old presets have global sizes but no per-slide size fields
    if (data.sizes && newSlides.length > 0 && newSlides[0].headingSize == null) {
      var ls = Object.assign({
        heading: 48, body: 38, cardText: 22,
        topCorner: 13, bottomCorner: 16, brandName: 20
      }, data.sizes);
      for (var li = 0; li < newSlides.length; li++) {
        newSlides[li].headingSize = ls.heading;
        newSlides[li].bodySize = ls.body;
        newSlides[li].cardTextSize = ls.cardText;
        newSlides[li].topCornerSize = ls.topCorner;
        newSlides[li].bottomCornerSize = ls.bottomCorner;
        newSlides[li].brandNameSize = ls.brandName;
      }
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
