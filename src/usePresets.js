// ===================================================
// usePresets Hook
// ===================================================
// Manages preset serialize/deserialize, export/import, and stale-load guard.
// Params: deps object { seriesSlides, slideAssets, sizes, setSizes, profileImg,
//   setProfileImg, profilePicName, setProfilePicName, isCustomProfilePic,
//   setIsCustomProfilePic, exportPrefix, setExportPrefix, setSeriesSlides,
//   setSlideAssets, setActiveSlide, clearPdfDownload, setPdfError, pushUndo,
//   setConfirmDialog }
// Returns: { presetInputRef, presetDownload, presetDialog, setPresetDialog,
//   presetName, setPresetName, presetIncludeImages, setPresetIncludeImages,
//   presetError, setPresetError, downloadPreset, handlePresetUpload,
//   clearPresetDownload }

var PRESET_SLIDE_KEYS = [
  "title", "showHeading", "showAccentBar", "body",
  "titleColor", "bodyColor", "showCards", "cards",
  "cardTextColor", "cardBgColor", "showScreenshot",
  "showBrandName", "brandNameText", "brandNameColor",
  "showTopCorner", "topCornerText", "topCornerColor", "topCornerOpacity",
  "showBottomCorner", "bottomCornerText", "bottomCornerColor", "bottomCornerOpacity",
  "solidColor", "bgType", "geoEnabled", "geoLines",
  "frameEnabled", "accentColor", "borderColor", "borderOpacity", "footerBg"
];

function usePresets(deps) {
  var presetInputRef = useRef(null);
  var presetUrlRef = useRef(null);
  var presetLoadTokenRef = useRef(0);
  var [presetDownload, setPresetDownload] = useState(null);
  var [presetDialog, setPresetDialog] = useState(null);
  var [presetName, setPresetName] = useState("");
  var [presetIncludeImages, setPresetIncludeImages] = useState(true);
  var [presetError, setPresetError] = useState("");

  // Auto-dismiss preset errors after 5 seconds
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

    if (deps.profileImg && deps.profileImg.src) {
      images["profile"] = {
        name: deps.profilePicName || "profile.jpg",
        dataUrl: includeImages ? deps.profileImg.src : null
      };
    }

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
      sizes: Object.assign({}, deps.sizes),
      slides: serializedSlides,
      profilePicRef: (deps.profileImg && deps.profileImg.src) ? "profile" : null,
      images: images
    };
  };

  var loadPresetData = function(data) {
    deps.pushUndo();
    var loadToken = ++presetLoadTokenRef.current;

    if (data.sizes) {
      deps.setSizes(Object.assign({
        heading: 48, body: 38, cardText: 22,
        topCorner: 13, bottomCorner: 16, brandName: 20
      }, data.sizes));
    }

    if (data.exportPrefix != null) {
      deps.setExportPrefix(data.exportPrefix);
    }

    var profileRef = data.profilePicRef;
    var profileEntry = profileRef && data.images && data.images[profileRef];
    if (profileEntry && profileEntry.dataUrl) {
      var pImg = new Image();
      pImg.onload = function() {
        if (presetLoadTokenRef.current !== loadToken) return;
        deps.setProfileImg(pImg);
        deps.setIsCustomProfilePic(true);
      };
      pImg.onerror = function() {
        if (presetLoadTokenRef.current !== loadToken) return;
        setPresetError("Failed to load profile image from preset.");
      };
      pImg.src = profileEntry.dataUrl;
      deps.setProfilePicName(profileEntry.name || null);
    } else {
      deps.setProfileImg(null);
      deps.setIsCustomProfilePic(false);
      deps.setProfilePicName(profileEntry ? profileEntry.name : null);
    }

    var newAssets = {};

    var newSlides = (data.slides || []).map(function(sd, i) {
      var slide = makeDefaultSlide(sd.title, sd.body);
      for (var k = 0; k < PRESET_SLIDE_KEYS.length; k++) {
        var key = PRESET_SLIDE_KEYS[k];
        if (sd[key] !== undefined) {
          slide[key] = key === "cards" ? (sd.cards || []).slice() : sd[key];
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
        if (data.profilePicRef) {
          var profileEntryCheck = imageMap[data.profilePicRef];
          if (!profileEntryCheck || !profileEntryCheck.dataUrl) missingCount++;
        }
        for (var i = 0; i < data.slides.length; i++) {
          var sd = data.slides[i];
          if (sd.customBgRef) {
            var bgEntryCheck = imageMap[sd.customBgRef];
            if (!bgEntryCheck || !bgEntryCheck.dataUrl) missingCount++;
          }
          if (sd.screenshotRef) {
            var ssEntryCheck = imageMap[sd.screenshotRef];
            if (!ssEntryCheck || !ssEntryCheck.dataUrl) missingCount++;
          }
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