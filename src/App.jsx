// ---------------------------------------
// Main Component
// ---------------------------------------

// Hoisted styles (module-scope to avoid per-render allocations)
var inputStyle = { width: "100%", padding: "8px 12px", borderRadius: 8, border: "1px solid #444", background: "#28283e", color: "#fff", fontSize: 14, boxSizing: "border-box" };
var labelStyle = { display: "block", marginBottom: 6, fontWeight: 600, fontSize: 13, color: "#bbb", letterSpacing: 0.5 };
var INLINE_SWATCHES = ["#ffffff", "#1a1a2e", "#333333", "#22c55e", "#a5b4fc", "#f59e0b", "#fb7185", "#22d3ee", "#a78bfa", "#38bdf8", "#d97706", "#fef3c7", "#e0f2fe", "#e0e7ff", "#f0fdf4", "#9ca3af"];
var smallBtnStyle = { padding: "2px 8px", borderRadius: 4, border: "1px solid #444", background: "#28283e", color: "#ccc", cursor: "pointer", fontSize: 9, fontWeight: 600 };
var pickerDropdownStyle = { position: "absolute", top: "100%", left: 0, zIndex: 60, marginTop: 4, background: "#1a1a30", border: "1px solid #444", borderRadius: 10, padding: 10, width: 200, boxShadow: "0 8px 24px rgba(0,0,0,0.6)" };

export default function App() {
  var canvasRef = useRef(null);
  var profilePicInputRef = useRef(null);
  var screenshotInputRef = useRef(null);
  var customBgInputRef = useRef(null);
  var renderTimerRef = useRef(null);
  var pdfUrlRef = useRef(null);
  var [isCustomProfilePic, setIsCustomProfilePic] = useState(false);
  var [confirmDialog, setConfirmDialog] = useState(null);
  var [pdfDownload, setPdfDownload] = useState(null);
  var [pdfError, setPdfError] = useState("");

  // Preset save/load state
  var presetInputRef = useRef(null);
  var presetUrlRef = useRef(null);
  var presetLoadTokenRef = useRef(0);
  var [presetDownload, setPresetDownload] = useState(null);
  var [presetDialog, setPresetDialog] = useState(null);
  var [presetName, setPresetName] = useState("");
  var [presetIncludeImages, setPresetIncludeImages] = useState(true);
  var [presetError, setPresetError] = useState("");

  // Undo/redo
  var undoManagerRef = useRef(createUndoManager());

  var [openPicker, setOpenPicker] = useState(null);

  // Font sizes
  var [sizes, setSizes] = useState({
    heading: 48,
    body: 38,
    cardText: 22,
    topCorner: 13,
    bottomCorner: 16,
    brandName: 20,
  });

  var setSize = function(key, val) {
    setSizes(function(prev) {
      var next = Object.assign({}, prev);
      next[key] = val;
      return next;
    });
  };

  // Close picker on outside click
  useEffect(function() {
    if (!openPicker) return;
    var handler = function(e) {
      var picker = document.querySelector('[data-picker="' + openPicker + '"]');
      if (picker && !picker.contains(e.target)) {
        setOpenPicker(null);
      }
    };
    document.addEventListener("mousedown", handler);
    return function() { document.removeEventListener("mousedown", handler); };
  }, [openPicker]);

  // Slides state
  var [seriesSlides, setSeriesSlides] = useState([makeDefaultSlide("Heading", "Body text")]);
  var [activeSlide, setActiveSlide] = useState(0);
  var [slideAssets, setSlideAssets] = useState({});
  // shape: { [slideIndex]: { image: Image|null, name: string|null, scale: number } }

  var getAsset = function(idx) {
    return slideAssets[idx] || { image: null, name: null, scale: 1 };
  };

  var setAsset = function(idx, patch) {
    setSlideAssets(function(prev) {
      var entry = prev[idx] || { image: null, name: null, scale: 1 };
      var next = Object.assign({}, prev);
      next[idx] = Object.assign({}, entry, patch);
      return next;
    });
  };

  var setScale = function(key, val) {
    setAsset(key, { scale: val });
  };

  // Drag-to-reorder state
  var [dragFrom, setDragFrom] = useState(null);
  var [dragOver, setDragOver] = useState(null);

  // Export prefix
  var [exportPrefix, setExportPrefix] = useState("linkedin-slide");

  // Image loading - no default profile pic; starts empty, user uploads
  var [profileImg, setProfileImg] = useState(null);

  // Filename tracking
  var [profilePicName, setProfilePicName] = useState(null);

  // --- Undo/redo snapshot helpers ---

  var captureSnapshot = function() {
    return {
      seriesSlides: seriesSlides,
      slideAssets: slideAssets,
      sizes: sizes,
      activeSlide: activeSlide,
      exportPrefix: exportPrefix,
      profileImg: profileImg,
      isCustomProfilePic: isCustomProfilePic,
      profilePicName: profilePicName
    };
  };

  var restoreSnapshot = function(snap) {
    setSeriesSlides(snap.seriesSlides);
    setSlideAssets(snap.slideAssets);
    setSizes(snap.sizes);
    setActiveSlide(snap.activeSlide);
    setExportPrefix(snap.exportPrefix);
    setProfileImg(snap.profileImg);
    setIsCustomProfilePic(snap.isCustomProfilePic);
    setProfilePicName(snap.profilePicName);
  };

  var pushUndo = function() {
    undoManagerRef.current.pushSnapshot(captureSnapshot());
  };

  // Global keyboard handler for undo/redo
  useEffect(function() {
    var handler = function(e) {
      // Skip if focus is in an input, textarea, or select (preserve native text undo)
      var tag = e.target && e.target.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      var isCtrl = e.ctrlKey || e.metaKey;
      if (!isCtrl || e.key !== "z") return;
      e.preventDefault();
      if (e.shiftKey) {
        // Redo
        var redoSnap = undoManagerRef.current.redo(captureSnapshot());
        if (redoSnap) restoreSnapshot(redoSnap);
      } else {
        // Undo
        var undoSnap = undoManagerRef.current.undo(captureSnapshot());
        if (undoSnap) restoreSnapshot(undoSnap);
      }
    };
    document.addEventListener("keydown", handler);
    return function() { document.removeEventListener("keydown", handler); };
  });

  var handleCustomUpload = function(e) {
    var file = e.target.files[0];
    if (!file) return;
    var fileName = file.name;
    var reader = new FileReader();
    reader.onload = function(ev) {
      var img = new Image();
      img.onload = function() {
        setSeriesSlides(function(prev) {
          return prev.map(function(s, i) {
            if (i !== activeSlide) return s;
            return Object.assign({}, s, { customBgImage: img, customBgName: fileName, bgType: "custom" });
          });
        });
      };
      img.src = ev.target.result;
    };
    reader.readAsDataURL(file);
  };

  var handleScreenshotUpload = function(key, e) {
    var file = e.target.files[0];
    if (!file) return;
    var fileName = file.name;
    var reader = new FileReader();
    reader.onload = function(ev) {
      var img = new Image();
      img.onload = function() {
        setAsset(key, { name: fileName, image: img });
      };
      img.src = ev.target.result;
    };
    reader.readAsDataURL(file);
  };

  var handleProfilePicUpload = function(e) {
    var file = e.target.files[0];
    if (!file) return;
    setProfilePicName(file.name);
    var reader = new FileReader();
    reader.onload = function(ev) {
      var img = new Image();
      img.onload = function() { setProfileImg(img); setIsCustomProfilePic(true); };
      img.src = ev.target.result;
    };
    reader.readAsDataURL(file);
  };

  var removeProfilePic = function() {
    if (profilePicInputRef.current) { profilePicInputRef.current.value = ""; }
    setIsCustomProfilePic(false);
    setProfilePicName(null);
    setProfileImg(null);
  };

  var removeCustomBg = function() {
    if (customBgInputRef.current) { customBgInputRef.current.value = ""; }
    setSeriesSlides(function(prev) {
      return prev.map(function(s, i) {
        if (i !== activeSlide) return s;
        return Object.assign({}, s, { customBgImage: null, customBgName: null, bgType: "solid" });
      });
    });
  };

  var removeScreenshot = function(key) {
    if (screenshotInputRef.current) { screenshotInputRef.current.value = ""; }
    setSlideAssets(function(prev) {
      var next = Object.assign({}, prev);
      delete next[key];
      return next;
    });
  };

  // Screenshot metadata is unified in slideAssets.

  // --- Preset serialize/deserialize ---

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

  var serializePreset = function(name, includeImages) {
    var images = {};

    // Profile pic
    if (profileImg && profileImg.src) {
      images["profile"] = {
        name: profilePicName || "profile.jpg",
        dataUrl: includeImages ? profileImg.src : null
      };
    }

    // Per-slide images
    var serializedSlides = seriesSlides.map(function(s, i) {
      var slide = {};
      for (var k = 0; k < PRESET_SLIDE_KEYS.length; k++) {
        var key = PRESET_SLIDE_KEYS[k];
        if (key === "cards") {
          slide[key] = s[key] ? s[key].slice() : ["Card 1"];
        } else {
          slide[key] = s[key];
        }
      }

      // Custom bg -> ref
      slide.customBgRef = null;
      if (s.customBgImage && s.customBgImage.src) {
        var bgRef = "bg-" + i;
        slide.customBgRef = bgRef;
        images[bgRef] = {
          name: s.customBgName || ("bg-" + i + ".jpg"),
          dataUrl: includeImages ? s.customBgImage.src : null
        };
      }

      // Screenshot -> ref
      slide.screenshotRef = null;
      var asset = slideAssets[i];
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
      exportPrefix: exportPrefix,
      sizes: Object.assign({}, sizes),
      slides: serializedSlides,
      profilePicRef: (profileImg && profileImg.src) ? "profile" : null,
      images: images
    };
  };

  var loadPresetData = function(data) {
    pushUndo();
    // Increment load token to invalidate any in-flight async image loads from prior presets
    var loadToken = ++presetLoadTokenRef.current;

    // Restore sizes
    if (data.sizes) {
      setSizes(Object.assign({
        heading: 48, body: 38, cardText: 22,
        topCorner: 13, bottomCorner: 16, brandName: 20
      }, data.sizes));
    }

    // Restore export prefix
    if (data.exportPrefix != null) {
      setExportPrefix(data.exportPrefix);
    }

    // Restore profile pic
    var profileRef = data.profilePicRef;
    var profileEntry = profileRef && data.images && data.images[profileRef];
    if (profileEntry && profileEntry.dataUrl) {
      var pImg = new Image();
      pImg.onload = function() {
        if (presetLoadTokenRef.current !== loadToken) return;
        setProfileImg(pImg);
        setIsCustomProfilePic(true);
      };
      pImg.src = profileEntry.dataUrl;
      setProfilePicName(profileEntry.name || null);
    } else {
      setProfileImg(null);
      setIsCustomProfilePic(false);
      setProfilePicName(profileEntry ? profileEntry.name : null);
    }

    // Restore slides
    var newAssets = {};

    var newSlides = (data.slides || []).map(function(sd, i) {
      var slide = makeDefaultSlide(sd.title, sd.body);
      // Overwrite all serializable fields
      for (var k = 0; k < PRESET_SLIDE_KEYS.length; k++) {
        var key = PRESET_SLIDE_KEYS[k];
        if (sd[key] !== undefined) {
          slide[key] = key === "cards" ? (sd.cards || []).slice() : sd[key];
        }
      }

      // Custom bg image
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
              setSeriesSlides(function(prev) {
                return prev.map(function(s, si) {
                  if (si !== idx) return s;
                  return Object.assign({}, s, { customBgImage: bgImg });
                });
              });
            };
          })(i);
          bgImg.src = bgEntry.dataUrl;
        }
      }

      // Screenshot
      var ssRef = sd.screenshotRef;
      var ssEntry = ssRef && data.images && data.images[ssRef];
      if (ssEntry) {
        newAssets[i] = { image: null, name: ssEntry.name || null, scale: ssEntry.scale || 1 };
        if (ssEntry.dataUrl) {
          (function(idx) {
            var ssImg = new Image();
            ssImg.onload = function() {
              if (presetLoadTokenRef.current !== loadToken) return;
              setSlideAssets(function(prev) {
                var next = Object.assign({}, prev);
                next[idx] = Object.assign({}, next[idx] || {}, { image: ssImg });
                return next;
              });
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

    setSeriesSlides(newSlides);
    setSlideAssets(newAssets);
    setActiveSlide(0);

    // Clear PDF state
    clearPdfDownload();
    setPdfError("");
  };

  // --- Render to canvas ---

  var renderSlide = useCallback(function(ctx, slideIndex) {
    renderSlideToCanvas(ctx, slideIndex, seriesSlides, slideAssets, sizes, profileImg);
  }, [sizes, profileImg, seriesSlides, slideAssets]);

  var render = useCallback(function() {
    var canvas = canvasRef.current;
    if (!canvas) return;
    var ctx = canvas.getContext("2d");
    var idx = activeSlide;
    renderSlide(ctx, idx);
  }, [renderSlide, activeSlide]);

  useEffect(function() {
    if (renderTimerRef.current) clearTimeout(renderTimerRef.current);
    renderTimerRef.current = setTimeout(function() {
      render();
    }, 40);
    return function() {
      if (renderTimerRef.current) clearTimeout(renderTimerRef.current);
    };
  }, [render]);

  // --- Downloads (PDF) ---
  // Pure PDF utilities (sanitizePrefix, extractJpegBinaryFromDataUrl, buildPdfFromJpegs) in pdfBuilder.js

  var captureSlideJpegBinary = function(ctx, idx) {
    var canvas = canvasRef.current;
    renderSlide(ctx, idx);
    var dataUrl = canvas.toDataURL("image/jpeg", 0.92);
    var jpeg = extractJpegBinaryFromDataUrl(dataUrl);
    if (!jpeg || jpeg.length === 0) {
      throw new Error("Failed to capture JPEG data from canvas");
    }
    return jpeg;
  };

  var clearPdfDownload = function() {
    if (pdfUrlRef.current) {
      URL.revokeObjectURL(pdfUrlRef.current);
      pdfUrlRef.current = null;
    }
    setPdfDownload(null);
  };

  // --- Preset export/import ---

  var clearPresetDownload = function() {
    if (presetUrlRef.current) {
      URL.revokeObjectURL(presetUrlRef.current);
      presetUrlRef.current = null;
    }
    setPresetDownload(null);
  };

  var downloadPreset = function(name, includeImages) {
    var preset = serializePreset(name, includeImages);
    var json = JSON.stringify(preset, null, 2);
    var blob = new Blob([json], { type: "application/json" });
    clearPresetDownload();
    var url = URL.createObjectURL(blob);
    presetUrlRef.current = url;
    var fileName = sanitizePrefix(name || exportPrefix || "preset") + ".json";
    setPresetDownload({ name: fileName, url: url });
  };

  var handlePresetUpload = function(e) {
    var file = e.target.files[0];
    if (!file) return;
    setPresetError("");
    var reader = new FileReader();
    reader.onload = function(ev) {
      try {
        var data = JSON.parse(ev.target.result);
        if (data.version !== 1 || !Array.isArray(data.slides)) {
          setPresetError("Invalid preset file format (expected v1).");
          return;
        }

        // Count missing images
        var imageMap = (data.images && typeof data.images === "object") ? data.images : {};
        var missingCount = 0;
        if (data.profilePicRef) {
          var profileEntry = imageMap[data.profilePicRef];
          if (!profileEntry || !profileEntry.dataUrl) missingCount++;
        }
        for (var i = 0; i < data.slides.length; i++) {
          var sd = data.slides[i];
          if (sd.customBgRef) {
            var bgEntry = imageMap[sd.customBgRef];
            if (!bgEntry || !bgEntry.dataUrl) missingCount++;
          }
          if (sd.screenshotRef) {
            var ssEntry = imageMap[sd.screenshotRef];
            if (!ssEntry || !ssEntry.dataUrl) missingCount++;
          }
        }

        var msg = "Load preset \u201c" + (data.name || "Untitled") + "\u201d? This replaces all current slides and settings.";
        if (missingCount > 0) {
          msg += " (" + missingCount + " image" + (missingCount > 1 ? "s" : "") + " not included \u2014 re-upload after loading.)";
        }

        setPresetError("");
        setConfirmDialog({
          message: msg,
          onConfirm: function() {
            setPresetError("");
            loadPresetData(data);
          }
        });
      } catch (err) {
        setPresetError("Failed to parse preset file.");
      }
    };
    reader.readAsText(file);
    if (presetInputRef.current) presetInputRef.current.value = "";
  };

  var downloadCurrentPDF = function() {
    var canvas = canvasRef.current;
    if (!canvas) return;
    setPdfError("");
    try {
      var ctx = canvas.getContext("2d");
      var jpeg = captureSlideJpegBinary(ctx, activeSlide);
      var blob = buildPdfFromJpegs([jpeg], W, H);
      clearPdfDownload();
      var prefix = sanitizePrefix(exportPrefix);
      var nn = (activeSlide + 1 < 10 ? "0" : "") + (activeSlide + 1);
      var fileName = prefix + "-" + nn + ".pdf";
      var url = URL.createObjectURL(blob);
      pdfUrlRef.current = url;
      setPdfDownload({ name: fileName, url: url });
    } catch (err) {
      setPdfError("PDF generation failed");
    }
  };

  var downloadAllPDF = function() {
    var canvas = canvasRef.current;
    if (!canvas) return;
    var ctx = canvas.getContext("2d");
    var total = seriesSlides.length;
    setPdfError("");
    try {
      var jpegPages = [];
      for (var i = 0; i < total; i++) {
        jpegPages.push(captureSlideJpegBinary(ctx, i));
      }
      var blob = buildPdfFromJpegs(jpegPages, W, H);
      clearPdfDownload();
      var prefix = sanitizePrefix(exportPrefix);
      var fileName = prefix + "-all.pdf";
      var url = URL.createObjectURL(blob);
      pdfUrlRef.current = url;
      setPdfDownload({ name: fileName, url: url });
    } catch (err) {
      setPdfError("PDF generation failed");
    } finally {
      renderSlide(ctx, activeSlide);
    }
  };

  useEffect(function() {
    return function() {
      if (pdfUrlRef.current) {
        URL.revokeObjectURL(pdfUrlRef.current);
        pdfUrlRef.current = null;
      }
      if (presetUrlRef.current) {
        URL.revokeObjectURL(presetUrlRef.current);
        presetUrlRef.current = null;
      }
    };
  }, []);

  // --- Series slide management ---

  var updateSlide = function(idx, field, val) {
    var next = seriesSlides.map(function(s, i) {
      if (i !== idx) return s;
      var updated = Object.assign({}, s);
      updated[field] = val;
      return updated;
    });
    setSeriesSlides(next);
  };

  var updateBgField = function(field, value) {
    updateSlide(activeSlide, field, value);
  };

  var syncBgToAll = function() {
    setConfirmDialog({
      message: "Apply Slide " + (activeSlide + 1) + "\u2019s background settings to all slides?",
      onConfirm: function() {
        pushUndo();
        var src = seriesSlides[activeSlide];
        setSeriesSlides(function(prev) {
          return prev.map(function(s) {
            return Object.assign({}, s, {
              solidColor: src.solidColor,
              bgType: src.bgType,
              customBgImage: src.customBgImage,
              customBgName: src.customBgName,
              geoEnabled: src.geoEnabled,
              geoLines: src.geoLines,
              frameEnabled: src.frameEnabled,
              accentColor: src.accentColor,
              borderColor: src.borderColor,
              borderOpacity: src.borderOpacity,
              footerBg: src.footerBg
            });
          });
        });
      }
    });
  };

  var resetBgToDefault = function() {
    setConfirmDialog({
      message: "Reset Slide " + (activeSlide + 1) + "\u2019s background to defaults?",
      onConfirm: function() {
        pushUndo();
        setSeriesSlides(function(prev) {
          return prev.map(function(s, i) {
            if (i !== activeSlide) return s;
            return Object.assign({}, s, {
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
            });
          });
        });
      }
    });
  };

  var addSlide = function() {
    setSeriesSlides(function(prev) {
      if (prev.length >= 10) return prev;
      return prev.concat([makeDefaultSlide()]);
    });
  };

  var duplicateSlide = function() {
    if (seriesSlides.length >= 10) return;
    setConfirmDialog({
      message: "Duplicate Slide " + (activeSlide + 1) + "?",
      onConfirm: function() {
        pushUndo();
        var insertIdx = activeSlide + 1;

        setSeriesSlides(function(prev) {
          if (prev.length >= 10) return prev;
          var src = prev[activeSlide];
          if (!src) return prev;
          var copy = Object.assign({}, src, { cards: src.cards.slice() });
          var next = prev.slice();
          next.splice(insertIdx, 0, copy);
          return next;
        });

        setSlideAssets(function(prev) {
          // Shift all asset keys >= insertIdx up by 1, then copy source asset
          var next = {};
          Object.keys(prev).forEach(function(k) {
            var ki = Number(k);
            if (ki >= insertIdx) {
              next[ki + 1] = prev[ki];
            } else {
              next[ki] = prev[ki];
            }
          });
          var srcAsset = prev[activeSlide];
          if (srcAsset) {
            next[insertIdx] = Object.assign({}, srcAsset);
          }
          return next;
        });

        setActiveSlide(insertIdx);
      }
    });
  };

  var removeSlide = function(idx) {
    if (seriesSlides.length <= 1) return;
    pushUndo();
    setSeriesSlides(function(prev) {
      if (prev.length <= 1) return prev;
      return prev.filter(function(_, i) { return i !== idx; });
    });
    setSlideAssets(function(prev) {
      var next = {};
      Object.keys(prev).forEach(function(k) {
        var ki = Number(k);
        if (ki < idx) next[ki] = prev[ki];
        else if (ki > idx) next[ki - 1] = prev[ki];
      });
      return next;
    });
    setActiveSlide(function(prev) {
      var newLen = seriesSlides.length - 1;
      if (prev >= newLen) return newLen - 1;
      if (prev === idx) return Math.max(0, idx - 1);
      if (prev > idx) return prev - 1;
      return prev;
    });
  };

  var reorderSlide = function(fromIdx, toIdx) {
    if (fromIdx === toIdx || fromIdx == null || toIdx == null) return;
    pushUndo();

    setSeriesSlides(function(prev) {
      if (fromIdx < 0 || fromIdx >= prev.length) return prev;
      if (toIdx < 0 || toIdx >= prev.length) return prev;
      var next = prev.slice();
      var moved = next.splice(fromIdx, 1)[0];
      next.splice(toIdx, 0, moved);
      return next;
    });

    // Build index map for asset remapping
    var buildIndexMap = function(len) {
      var map = {};
      for (var i = 0; i < len; i++) {
        var newPos;
        if (i === fromIdx) {
          newPos = toIdx;
        } else if (fromIdx < toIdx) {
          if (i > fromIdx && i <= toIdx) { newPos = i - 1; }
          else { newPos = i; }
        } else {
          if (i >= toIdx && i < fromIdx) { newPos = i + 1; }
          else { newPos = i; }
        }
        map[i] = newPos;
      }
      return map;
    };

    setSlideAssets(function(prev) {
      var indexMap = buildIndexMap(seriesSlides.length);
      var next = {};
      Object.keys(prev).forEach(function(k) {
        var ki = Number(k);
        if (indexMap[ki] != null) {
          next[indexMap[ki]] = prev[ki];
        }
      });
      return next;
    });

    setActiveSlide(function(prev) {
      var indexMap = buildIndexMap(seriesSlides.length);
      if (prev === fromIdx) return toIdx;
      if (indexMap[prev] != null) return indexMap[prev];
      return prev;
    });

    setDragFrom(null);
    setDragOver(null);
  };

  var updateSlideCard = function(slideIdx, cardIdx, val) {
    updateSlide(slideIdx, "cards", seriesSlides[slideIdx].cards.map(function(c, i) { return i === cardIdx ? val : c; }));
  };
  var addSlideCard = function(slideIdx) {
    var s = seriesSlides[slideIdx];
    if (s.cards.length < 5) updateSlide(slideIdx, "cards", s.cards.concat(["Card " + (s.cards.length + 1)]));
  };
  var removeSlideCard = function(slideIdx, cardIdx) {
    var s = seriesSlides[slideIdx];
    if (s.cards.length > 1) updateSlide(slideIdx, "cards", s.cards.filter(function(_, i) { return i !== cardIdx; }));
  };

  // --- Styles ---

  // inputStyle, labelStyle, INLINE_SWATCHES, smallBtnStyle, pickerDropdownStyle hoisted to module scope

  var sizeLabel = function(text, sizeKey, min, max, extra, colorVal, colorSet, colorPickerKey, opacityVal, opacitySet) {
    if (!sizeKey) return <label style={labelStyle}>{text}{extra ? " " : ""}{extra}</label>;
    var cpOpen = colorPickerKey && openPicker === colorPickerKey;
    return (
      <div style={{ display: "flex", alignItems: "center", marginBottom: text ? 6 : 0, gap: text ? 0 : 6 }}>
        {text && <span style={{ fontWeight: 600, fontSize: 13, color: "#bbb", letterSpacing: 0.5, flex: 1 }}>{text}{extra ? " " : ""}{extra}</span>}
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          {colorPickerKey && (
            <div style={{ position: "relative" }} data-picker={colorPickerKey}>
              <button onClick={function(e) { e.stopPropagation(); setOpenPicker(cpOpen ? null : colorPickerKey); }}
                style={{ width: 18, height: 18, borderRadius: 4, border: cpOpen ? "2px solid #6366f1" : "1px solid #444", background: colorVal || "#fff", cursor: "pointer", padding: 0, display: "block" }} />
              {cpOpen && (
                <div style={Object.assign({}, pickerDropdownStyle, { left: "auto", right: 0 })}>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(8, 1fr)", gap: 4, marginBottom: 8 }}>
                    {INLINE_SWATCHES.map(function(c) {
                      var active = colorVal === c;
                      return (
                        <button key={c} onClick={function() { colorSet(c); }}
                          style={{ width: 20, height: 20, borderRadius: 4, border: active ? "2px solid #fff" : "1px solid #444", background: c, cursor: "pointer", padding: 0, boxShadow: active ? "0 0 0 1px #6366f1" : "none" }} />
                      );
                    })}
                  </div>
                  <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                    <input type="color" value={colorVal && colorVal.charAt(0) === "#" ? colorVal : "#ffffff"} onChange={function(e) { colorSet(e.target.value); }}
                      style={{ width: 24, height: 24, border: "1px solid #444", borderRadius: 4, cursor: "pointer", background: "none", padding: 0 }} />
                    <input value={colorVal || ""} onChange={function(e) { colorSet(e.target.value); }}
                      style={{ flex: 1, padding: "4px 6px", borderRadius: 4, border: "1px solid #444", background: "#0e0e1a", color: "#bbb", fontSize: 11, fontFamily: "monospace" }} />
                  </div>
                  {opacitySet && (
                    <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 8, paddingTop: 8, borderTop: "1px solid #3a3a50" }}>
                      <span style={{ fontSize: 10, color: "#666", whiteSpace: "nowrap" }}>Opacity</span>
                      <input type="range" min={0} max={100} value={opacityVal != null ? opacityVal : 100} onChange={function(e) { opacitySet(Number(e.target.value)); }}
                        style={{ flex: 1 }} />
                      <span style={{ fontSize: 10, color: "#555", width: 28, textAlign: "right" }}>{(opacityVal != null ? opacityVal : 100) + "%"}</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
          <div style={{ display: "flex", alignItems: "center", gap: 0, background: "#28283e", borderRadius: 4, border: "1px solid #444", height: 28, overflow: "hidden" }}>
            <button onClick={function() { if (sizes[sizeKey] > (min || 10)) setSize(sizeKey, sizes[sizeKey] - 1); }}
              style={{ minWidth: 28, minHeight: 28, border: "none", background: "transparent", color: "#555", cursor: "pointer", fontSize: 14, padding: 0, lineHeight: "28px" }}>{"\u2212"}</button>
            <input value={sizes[sizeKey]} onChange={function(e) { var v = parseInt(e.target.value, 10); if (!isNaN(v)) setSize(sizeKey, Math.max(min || 10, Math.min(max || 60, v))); }}
              style={{ width: 30, height: 28, border: "none", borderLeft: "1px solid #444", borderRight: "1px solid #444", background: "transparent", color: "#666", fontSize: 11, fontFamily: "monospace", textAlign: "center", padding: 0, outline: "none" }} />
            <button onClick={function() { if (sizes[sizeKey] < (max || 60)) setSize(sizeKey, sizes[sizeKey] + 1); }}
              style={{ minWidth: 28, minHeight: 28, border: "none", background: "transparent", color: "#555", cursor: "pointer", fontSize: 14, padding: 0, lineHeight: "28px" }}>+</button>
          </div>
        </div>
      </div>
    );
  };

  var currentSlide = seriesSlides[activeSlide] || seriesSlides[0];
  var isCustomBg = currentSlide.bgType === "custom";

  return (
    <div style={{ fontFamily: '"Helvetica Neue", Helvetica, Arial, sans-serif', background: "#000000", minHeight: "100vh", color: "#e0e0e0", padding: 16 }}>
      <div style={{ maxWidth: 1400, margin: "0 auto" }}>
        <h2 style={{ color: "#fff", marginBottom: 16, fontSize: 20 }}>LinkedIn Carousel Generator</h2>

        <div style={{ display: "flex", gap: 20, alignItems: "flex-start" }}>


        {/* -- COL 1: Settings + Slides -- */}
        <div style={{ flex: "0 0 240px", minWidth: 220 }}>

          {/* --- PRESETS --- */}
          <div style={{ marginBottom: 14 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
              <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>PRESETS</label>
              <button onClick={function() { setPresetName(exportPrefix || ""); setPresetDialog({ type: "save" }); }}
                style={smallBtnStyle}>
                Save
              </button>
              <button onClick={function() { if (presetInputRef.current) presetInputRef.current.click(); }}
                style={smallBtnStyle}>
                Load
              </button>
              <input ref={presetInputRef} type="file" accept=".json" onChange={handlePresetUpload} style={{ display: "none" }} />
            </div>
            {presetDownload && (
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 4 }}>
                <a href={presetDownload.url} download={presetDownload.name}
                  onClick={function() { setTimeout(clearPresetDownload, 1500); }}
                  style={{ fontSize: 11, color: "#a5b4fc", textDecoration: "underline", flex: 1, wordBreak: "break-all" }}>
                  {"Save " + presetDownload.name}
                </a>
                <button onClick={clearPresetDownload}
                  style={{ background: "none", border: "none", color: "#999", cursor: "pointer", fontSize: 14, padding: "0 2px", lineHeight: 1 }}>
                  {"\u00d7"}
                </button>
              </div>
            )}
            {presetError && (
              <div style={{ marginTop: 4, padding: "4px 8px", borderRadius: 6, background: "#3a1a1a", border: "1px solid #7f1d1d", color: "#fca5a5", fontSize: 11 }}>
                {presetError}
              </div>
            )}
          </div>
          <div style={{ borderTop: "1px solid #444", marginBottom: 10 }} />

          {/* --- BACKGROUND --- */}
          <div style={{ marginBottom: 14 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
              <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>BACKGROUND</label>
              <button onClick={syncBgToAll} style={smallBtnStyle}>
                Sync All
              </button>
              <button onClick={resetBgToDefault} style={smallBtnStyle}>
                Reset
              </button>
            </div>

            {/* 50/50 split: controls left, thumbnail right */}
            <div style={{ display: "flex", gap: 14, alignItems: "stretch" }}>

              {/* Left zone: Solid/Photo pill + Accent / Base / Layer / Frame */}
              <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column" }}>

                {/* Solid / Photo pill */}
                <div style={{ marginBottom: 20 }}>
                  <div style={{ display: "flex", borderRadius: 10, overflow: "hidden", border: "1px solid #444" }}>
                    <button onClick={function() { if (isCustomBg) updateBgField("bgType", "solid"); }}
                      style={{ flex: 1, padding: "2px 0", border: "none", background: !isCustomBg ? "#6366f1" : "#28283e", color: !isCustomBg ? "#fff" : "#999", cursor: "pointer", fontSize: 9, fontWeight: 700, letterSpacing: 0.5, textAlign: "center" }}>
                      Solid
                    </button>
                    <button onClick={function() { if (!isCustomBg) updateBgField("bgType", "custom"); }}
                      style={{ flex: 1, padding: "2px 0", border: "none", borderLeft: "1px solid #444", background: isCustomBg ? "#6366f1" : "#28283e", color: isCustomBg ? "#fff" : "#999", cursor: "pointer", fontSize: 9, fontWeight: 700, letterSpacing: 0.5, textAlign: "center" }}>
                      Photo
                    </button>
                  </div>
                </div>

                {/* Group 1: Accent + Base */}
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>

                {/* Accent row */}
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <label style={{ fontSize: 13, color: "#999", fontWeight: 600, width: 46 }}>Accent</label>
                  <ColorPickerInline pickerKey="accent" value={currentSlide.accentColor || "#fff"} onChange={function(c) { updateBgField("accentColor", c); }} openPicker={openPicker} setOpenPicker={setOpenPicker} />
                </div>

                {/* Base row */}
                <div style={{ display: "flex", alignItems: "center", gap: 10, opacity: isCustomBg ? 0.35 : 1 }}>
                  <label style={{ fontSize: 13, color: "#999", fontWeight: 600, width: 46 }}>Base</label>
                  <ColorPickerInline pickerKey="solidColor" value={currentSlide.solidColor || "#fff"} onChange={function(c) { updateBgField("solidColor", c); }} openPicker={openPicker} setOpenPicker={setOpenPicker} disabled={isCustomBg} />
                </div>
                </div>

                {/* Spacer between groups */}
                <div style={{ height: 14 }} />

                {/* Group 2: Layer + Frame */}
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {/* Layer row */}
                <div style={{ display: "flex", alignItems: "center", gap: 10, opacity: isCustomBg ? 0.35 : 1 }}>
                  <label style={{ fontSize: 13, color: "#999", fontWeight: 600, width: 46 }}>Layer</label>
                  <button onClick={function() { if (!isCustomBg) updateBgField("geoEnabled", !currentSlide.geoEnabled); }}
                    style={{ padding: "3px 8px", borderRadius: 20, border: "none", background: (!isCustomBg && currentSlide.geoEnabled) ? GREEN : "#555", color: "#fff", cursor: isCustomBg ? "default" : "pointer", fontSize: 11, fontWeight: 600 }}>
                    {(!isCustomBg && currentSlide.geoEnabled) ? "ON" : "OFF"}
                  </button>
                  <div style={{ opacity: (isCustomBg || !currentSlide.geoEnabled) ? 0.5 : 1 }}>
                    <ColorPickerInline pickerKey="geoLines" value={currentSlide.geoLines} onChange={function(c) { updateBgField("geoLines", c); }} openPicker={openPicker} setOpenPicker={setOpenPicker} disabled={isCustomBg || !currentSlide.geoEnabled} />
                  </div>
                </div>

                {/* Frame row */}
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <label style={{ fontSize: 13, color: "#999", fontWeight: 600, width: 46 }}>Frame</label>
                  <button onClick={function() { updateBgField("frameEnabled", !currentSlide.frameEnabled); }}
                    style={{ padding: "3px 8px", borderRadius: 20, border: "none", background: currentSlide.frameEnabled ? GREEN : "#555", color: "#fff", cursor: "pointer", fontSize: 11, fontWeight: 600 }}>
                    {currentSlide.frameEnabled ? "ON" : "OFF"}
                  </button>
                  <div style={{ opacity: currentSlide.frameEnabled ? 1 : 0.35 }}>
                    <ColorPickerInline pickerKey="border" value={currentSlide.borderColor || "#fff"} onChange={function(c) { updateBgField("borderColor", c); }} openPicker={openPicker} setOpenPicker={setOpenPicker} disabled={!currentSlide.frameEnabled} opacityVal={currentSlide.borderOpacity} onOpacityChange={function(v) { updateBgField("borderOpacity", v); }} />
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <label style={{ fontSize: 13, color: "#999", fontWeight: 600, width: 46 }}>Footer</label>
                  <ColorPickerInline pickerKey="footerBg" value={currentSlide.footerBg || "#ffffff"} onChange={function(c) { updateBgField("footerBg", c); }} openPicker={openPicker} setOpenPicker={setOpenPicker} />
                </div>
                </div>

              </div>

              {/* Right zone: upload + thumbnail + status */}
              <div style={{ flex: 1, minWidth: 0, position: "relative", display: "flex", flexDirection: "column", alignItems: "center" }}>

                {/* Photo upload - above thumbnail; visible only in Photo mode */}
                <div style={{ width: "100%", marginBottom: 2, visibility: isCustomBg ? "visible" : "hidden" }}>
                  <input ref={customBgInputRef} type="file" accept="image/*" onChange={function(e) { handleCustomUpload(e); }} style={{ display: "none" }} />
                  <button onClick={function() { if (customBgInputRef.current) customBgInputRef.current.click(); }}
                    style={{ padding: "3px 8px", borderRadius: 4, border: "1px solid #444", background: "#28283e", color: "#ccc", cursor: "pointer", fontSize: 10, fontWeight: 600 }}>
                    Choose File
                  </button>
                  <p style={{ fontSize: 9, color: "#666", margin: "2px 0 0 0", wordBreak: "break-all", lineHeight: 1.3, minHeight: 10 }}>{currentSlide.customBgName || "\u00a0"}</p>
                </div>

                {/* Thumbnail preview */}
                <div style={{ width: "100%", aspectRatio: "4/5", maxHeight: 130, borderRadius: 6, overflow: "hidden", border: "2px solid #444", background: "#111119", position: "relative" }}>
                  {currentSlide.bgType === "solid" && (
                    <div style={{ width: "100%", height: "100%", background: currentSlide.solidColor || "#111119" }} />
                  )}
                  {currentSlide.bgType === "custom" && currentSlide.customBgImage && (
                    <img src={currentSlide.customBgImage.src} alt="Custom background"
                      style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                  )}
                  {currentSlide.bgType === "custom" && !currentSlide.customBgImage && (
                    <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 9, color: "#666" }}>No photo</div>
                  )}
                  {/* Layer overlay */}
                  {currentSlide.geoEnabled && !isCustomBg && (
                    <div style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%", pointerEvents: "none", borderRadius: 4, background: "radial-gradient(circle at 0% 22%, " + hexToRgba(currentSlide.geoLines, 12) + " 0%, transparent 40%), radial-gradient(circle at 0% 80%, " + hexToRgba(currentSlide.geoLines, 10) + " 0%, transparent 35%), radial-gradient(circle at 92% 13%, " + hexToRgba(currentSlide.geoLines, 8) + " 0%, transparent 30%), radial-gradient(circle at 88% 83%, " + hexToRgba(currentSlide.geoLines, 9) + " 0%, transparent 32%), repeating-linear-gradient(0deg, transparent, transparent 10px, " + hexToRgba(currentSlide.geoLines, 12) + " 10px, " + hexToRgba(currentSlide.geoLines, 12) + " 11px), repeating-linear-gradient(90deg, transparent, transparent 10px, " + hexToRgba(currentSlide.geoLines, 12) + " 10px, " + hexToRgba(currentSlide.geoLines, 12) + " 11px), linear-gradient(32deg, transparent 40%, " + hexToRgba(currentSlide.geoLines, 6) + " 50%, transparent 60%), linear-gradient(148deg, transparent 40%, " + hexToRgba(currentSlide.geoLines, 6) + " 50%, transparent 60%)" }} />
                  )}
                  {/* Frame overlay */}
                  {currentSlide.frameEnabled && (
                    <div style={{ position: "absolute", top: 15, left: 15, right: 15, bottom: 15, pointerEvents: "none", borderRadius: 3, border: "2px solid " + hexToRgba(currentSlide.borderColor, currentSlide.borderOpacity) }} />
                  )}
                </div>

                {/* Status - below thumbnail; visible only in Photo mode */}
                <div style={{ width: "100%", marginTop: 4, visibility: isCustomBg ? "visible" : "hidden" }}>
                  <div style={{ minHeight: 14 }}>
                    {currentSlide.customBgImage ? (
                      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        <span style={{ fontSize: 9, color: GREEN }}>{"\u2713"} Uploaded</span>
                        <button onClick={removeCustomBg} style={{ background: "none", border: "none", color: "#f87171", cursor: "pointer", fontSize: 9, padding: 0 }}>{"\u00d7"} Remove</button>
                      </div>
                    ) : (
                      <span style={{ fontSize: 9, color: "#555" }}>No image</span>
                    )}
                  </div>
                </div>
              </div>

            </div>
          </div>

          {/* -- Divider: Above Profile Pic -- */}
          <div style={{ borderTop: "1px solid #444", marginTop: 10, marginBottom: 10 }} />

          {/* --- PROFILE PIC --- */}
          <div style={{ marginBottom: 10 }}>
            <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
              {/* Left zone: label + file input + filename + status */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                  <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>PROFILE PIC</label>
                  <span style={{ fontSize: 10, color: "#555", fontWeight: 400 }}>(84 {"\u00d7"} 84px)</span>
                </div>
                <input ref={profilePicInputRef} type="file" accept="image/*" onChange={handleProfilePicUpload} style={{ display: "none" }} />
                <button onClick={function() { if (profilePicInputRef.current) profilePicInputRef.current.click(); }}
                  style={{ padding: "3px 8px", borderRadius: 4, border: "1px solid #444", background: "#28283e", color: "#ccc", cursor: "pointer", fontSize: 10, fontWeight: 600, marginBottom: 2 }}>
                  Choose File
                </button>
                {/* Filename - always reserves space */}
                <p style={{ fontSize: 10, color: "#666", margin: "2px 0 2px 0", wordBreak: "break-all", lineHeight: 1.3, maxWidth: 150, minHeight: 13 }}>{profilePicName || "\u00a0"}</p>
                {/* Status - always reserves space */}
                <div style={{ marginTop: 2, minHeight: 16 }}>
                  {profileImg && isCustomProfilePic ? (
                    <>
                      <span style={{ fontSize: 11, color: GREEN }}>{"\u2713"} Uploaded</span>
                      <button onClick={removeProfilePic} style={{ background: "none", border: "none", color: "#f87171", cursor: "pointer", fontSize: 11, marginLeft: 8 }}>{"\u00d7"} Remove</button>
                    </>
                  ) : (
                    <span style={{ fontSize: 11, color: "#555" }}>No image</span>
                  )}
                </div>
              </div>
              {/* Right zone: circular preview */}
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                <div style={{ width: 64, height: 64, borderRadius: "50%", overflow: "hidden", border: "2px solid #444", background: "#111119", flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>
                  {profileImg ? (
                    <img src={profileImg.src} alt="Profile pic" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                  ) : (
                    <span style={{ fontSize: 9, color: "#555" }}>None</span>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* -- Divider: Global ? / Per-Slide ? -- */}
          <div style={{ borderTop: "1px solid #444", marginTop: 10, marginBottom: 10, paddingTop: 10 }}>

          {/* --- SLIDES --- */}
          <div style={{ marginBottom: 10 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
              <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>SLIDES</label>
              <button onClick={duplicateSlide}
                style={{
                  padding: "2px 8px",
                  borderRadius: 4,
                  border: "1px solid #444",
                  background: "#28283e",
                  color: "#ccc",
                  cursor: "pointer",
                  fontSize: 9,
                  fontWeight: 600,
                  opacity: seriesSlides.length >= 10 ? 0.4 : 1
                }}>
                Duplicate
              </button>
            </div>
            <div style={{ display: "flex", gap: 4, marginBottom: 0, flexWrap: "wrap" }}>
              {seriesSlides.map(function(s, i) {
                var isActive = activeSlide === i;
                var isDragSource = dragFrom === i;
                var isDragTarget = dragOver === i && dragFrom !== i;
                var label = (i + 1).toString();
                return (
                  <button key={i}
                    draggable
                    onClick={function() { setActiveSlide(i); }}
                    onDragStart={function(e) { setDragFrom(i); e.dataTransfer.effectAllowed = "move"; }}
                    onDragOver={function(e) { e.preventDefault(); e.dataTransfer.dropEffect = "move"; setDragOver(i); }}
                    onDragLeave={function() { if (dragOver === i) setDragOver(null); }}
                    onDrop={function(e) { e.preventDefault(); if (dragFrom != null) { reorderSlide(dragFrom, i); } }}
                    onDragEnd={function() { setDragFrom(null); setDragOver(null); }}
                    style={{ width: 56, height: 56, borderRadius: 8, border: isDragTarget ? "2px dashed #6366f1" : (isActive ? "2px solid " + GREEN : "2px solid #555"), background: isDragTarget ? "rgba(99,102,241,0.10)" : (isActive ? "rgba(34,197,94,0.15)" : "#1a1a30"), color: isActive ? GREEN : "#aaa", cursor: isDragSource ? "grabbing" : "grab", fontSize: 16, fontWeight: 700, padding: 0, display: "flex", alignItems: "center", justifyContent: "center", opacity: isDragSource ? 0.4 : 1, transition: "opacity 0.15s, border 0.15s, background 0.15s" }}>
                    {label}
                  </button>
                );
              })}
              {seriesSlides.length < 10 && (
                <button onClick={addSlide}
                  style={{ width: 56, height: 56, borderRadius: 8, border: "2px dashed #555", background: "#1a1a30", color: "#888", cursor: "pointer", fontSize: 18, fontWeight: 700, padding: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>+</button>
              )}
            </div>
          </div>

          {/* --- SCREENSHOT (per-slide, in Col 1) --- */}
          {currentSlide && (
            <div style={{ marginTop: 6 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>SCREENSHOT</label>
                <span style={{ fontSize: 10, color: "#555", fontWeight: 400 }}>(640 {"\u00D7"} 500px)</span>
                <button onClick={function() { var next = !currentSlide.showScreenshot; updateSlide(activeSlide, "showScreenshot", next); if (!next) { removeScreenshot(activeSlide); } }}
                  style={{ padding: "3px 12px", borderRadius: 20, border: "none", background: currentSlide.showScreenshot ? GREEN : "#555", color: "#fff", cursor: "pointer", fontSize: 11, fontWeight: 600 }}>
                  {currentSlide.showScreenshot ? "ON" : "OFF"}
                </button>
              </div>
              {currentSlide.showScreenshot && (
                <div style={{ marginBottom: 8, paddingLeft: 8, borderLeft: "2px solid #555" }}>
                  <input ref={screenshotInputRef} type="file" accept="image/*" onChange={function(e) { handleScreenshotUpload(activeSlide, e); }} style={{ display: "none" }} />
                  <button onClick={function() { if (screenshotInputRef.current) screenshotInputRef.current.click(); }}
                    style={{ padding: "3px 8px", borderRadius: 4, border: "1px solid #444", background: "#28283e", color: "#ccc", cursor: "pointer", fontSize: 10, fontWeight: 600 }}>
                    Choose File
                  </button>
                  {/* Filename - below Choose File, above status */}
                  {getAsset(activeSlide).name && (
                    <p style={{ fontSize: 10, color: "#666", margin: "2px 0 2px 0", wordBreak: "break-all", lineHeight: 1.3, maxWidth: 150 }}>{getAsset(activeSlide).name}</p>
                  )}
                  {getAsset(activeSlide).image && (
                    <div style={{ marginTop: 4 }}>
                      <span style={{ fontSize: 11, color: GREEN }}>{"\u2713"} Uploaded</span>
                      <button onClick={function() { removeScreenshot(activeSlide); }} style={{ background: "none", border: "none", color: "#f87171", cursor: "pointer", fontSize: 11, marginLeft: 8 }}>{"\u00d7"} Remove</button>
                      <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 6 }}>
                        <span style={{ fontSize: 10, color: "#666" }}>Scale</span>
                        <input type="range" min={50} max={200} value={Math.round(getAsset(activeSlide).scale * 100)} onChange={function(e) { setScale(activeSlide, Number(e.target.value) / 100); }}
                          style={{ flex: 1 }} />
                        <span style={{ fontSize: 10, color: "#555", width: 32, textAlign: "right" }}>{Math.round(getAsset(activeSlide).scale * 100) + "%"}</span>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          </div>

        </div>

          {/* -- COL 2: Slide Editor -- */}
          <div style={{ flex: "1 1 280px", minWidth: 260 }}>

          {/* --- SLIDE EDITOR --- */}
          {currentSlide && (
            <div style={{ background: "#1a1a30", borderRadius: 10, padding: 14, border: "1px solid #3a3a50", marginBottom: 14 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                <span style={{ color: "#888", fontSize: 12, fontWeight: 600 }}>
                  {"SLIDE " + (activeSlide + 1)}
                </span>
                {seriesSlides.length > 1 && (
                  <button onClick={function() { removeSlide(activeSlide); }}
                    style={{ background: "none", border: "1px solid #f8717133", color: "#f87171", cursor: "pointer", fontSize: 11, padding: "3px 10px", borderRadius: 6 }}>Remove</button>
                )}
              </div>

              {/* -- Footer & Pic toggle (per-slide) -- */}
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4, marginTop: 4 }}>
                <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>FOOTER & PIC</label>
                <button onClick={function() { updateSlide(activeSlide, "showBrandName", !currentSlide.showBrandName); }}
                  style={{ padding: "3px 12px", borderRadius: 20, border: "none", background: currentSlide.showBrandName ? GREEN : "#555", color: "#fff", cursor: "pointer", fontSize: 11, fontWeight: 600 }}>
                  {currentSlide.showBrandName ? "ON" : "OFF"}
                </button>
                {currentSlide.showBrandName && (
                  <>
                    <div style={{ flex: 1 }} />
                    {sizeLabel("", "brandName", 12, 60, null, currentSlide.brandNameColor, function(c) { updateSlide(activeSlide, "brandNameColor", c); }, "s-" + activeSlide + "-bn")}
                  </>
                )}
              </div>
              {currentSlide.showBrandName && (
                <div style={{ marginBottom: 8, paddingLeft: 8, borderLeft: "2px solid #555" }}>
                  <input value={currentSlide.brandNameText} onChange={function(e) { updateSlide(activeSlide, "brandNameText", e.target.value); }} placeholder="Brand name..."
                    style={Object.assign({}, inputStyle, { marginBottom: 6, fontSize: 12 })} />
                </div>
              )}

              {/* -- Top Corner toggle (per-slide) -- */}
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4, marginTop: 4 }}>
                <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>TOP CORNER</label>
                <button onClick={function() { updateSlide(activeSlide, "showTopCorner", !currentSlide.showTopCorner); }}
                  style={{ padding: "3px 12px", borderRadius: 20, border: "none", background: currentSlide.showTopCorner ? GREEN : "#555", color: "#fff", cursor: "pointer", fontSize: 11, fontWeight: 600 }}>
                  {currentSlide.showTopCorner ? "ON" : "OFF"}
                </button>
                {currentSlide.showTopCorner && (<><div style={{ flex: 1 }} />{sizeLabel("", "topCorner", 8, 60, null, currentSlide.topCornerColor, function(c) { updateSlide(activeSlide, "topCornerColor", c); }, "s-" + activeSlide + "-tc", currentSlide.topCornerOpacity, function(v) { updateSlide(activeSlide, "topCornerOpacity", v); })}</>)}
              </div>
              {currentSlide.showTopCorner && (
                <div style={{ marginBottom: 8, paddingLeft: 8, borderLeft: "2px solid #555" }}>
                  <input value={currentSlide.topCornerText} onChange={function(e) { updateSlide(activeSlide, "topCornerText", e.target.value); }} placeholder="Top corner..."
                    style={Object.assign({}, inputStyle, { marginBottom: 4, fontSize: 12 })} />
                </div>
              )}

              {/* -- Bottom Corner toggle (per-slide) -- */}
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4, marginTop: 4 }}>
                <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>BOTTOM CORNER</label>
                <button onClick={function() { updateSlide(activeSlide, "showBottomCorner", !currentSlide.showBottomCorner); }}
                  style={{ padding: "3px 12px", borderRadius: 20, border: "none", background: currentSlide.showBottomCorner ? GREEN : "#555", color: "#fff", cursor: "pointer", fontSize: 11, fontWeight: 600 }}>
                  {currentSlide.showBottomCorner ? "ON" : "OFF"}
                </button>
                {currentSlide.showBottomCorner && (<><div style={{ flex: 1 }} />{sizeLabel("", "bottomCorner", 10, 60, null, currentSlide.bottomCornerColor, function(c) { updateSlide(activeSlide, "bottomCornerColor", c); }, "s-" + activeSlide + "-bc", currentSlide.bottomCornerOpacity, function(v) { updateSlide(activeSlide, "bottomCornerOpacity", v); })}</>)}
              </div>
              {currentSlide.showBottomCorner && (
                <div style={{ marginBottom: 8, paddingLeft: 8, borderLeft: "2px solid #555" }}>
                  <input value={currentSlide.bottomCornerText} onChange={function(e) { updateSlide(activeSlide, "bottomCornerText", e.target.value); }} placeholder="Bottom corner..."
                    style={Object.assign({}, inputStyle, { marginBottom: 4, fontSize: 12 })} />
                </div>
              )}

              {/* -- Heading toggle (per-slide) -- */}
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4, marginTop: 4 }}>
                <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>HEADING</label>
                <button onClick={function() { updateSlide(activeSlide, "showHeading", !currentSlide.showHeading); }}
                  style={{ padding: "3px 12px", borderRadius: 20, border: "none", background: currentSlide.showHeading ? GREEN : "#555", color: "#fff", cursor: "pointer", fontSize: 11, fontWeight: 600 }}>
                  {currentSlide.showHeading ? "ON" : "OFF"}
                </button>
                {currentSlide.showHeading && (
                  <>
                    <button onClick={function() { updateSlide(activeSlide, "showAccentBar", !currentSlide.showAccentBar); }}
                      title="Accent bar"
                      style={{ padding: "2px 6px", borderRadius: 4, border: "1px solid #444", background: (currentSlide.showAccentBar !== false) ? "rgba(34,197,94,0.2)" : "#28283e", color: (currentSlide.showAccentBar !== false) ? GREEN : "#666", cursor: "pointer", fontSize: 9, fontWeight: 700, lineHeight: "14px" }}>
                      {"\u2501"}
                    </button>
                    <div style={{ flex: 1 }} />{sizeLabel("", "heading", 24, 160, null, currentSlide.titleColor, function(c) { updateSlide(activeSlide, "titleColor", c); }, "s-" + activeSlide + "-title")}
                  </>
                )}
              </div>
              {currentSlide.showHeading && (
                <div style={{ marginBottom: 8, paddingLeft: 8, borderLeft: "2px solid #555" }}>
                  <input value={currentSlide.title} onChange={function(e) { updateSlide(activeSlide, "title", e.target.value); }} placeholder="Heading..."
                    style={Object.assign({}, inputStyle, { marginBottom: 4, fontSize: 12 })} />
                </div>
              )}

              {/* Body | Cards toggle */}
              <div style={{ display: "flex", alignItems: "center", marginTop: 12, marginBottom: 6, gap: 4 }}>
                <span onClick={function() { updateSlide(activeSlide, "showCards", false); }}
                  style={{ fontWeight: 600, fontSize: 13, color: !currentSlide.showCards ? GREEN : "#555", letterSpacing: 0.5, cursor: "pointer" }}>BODY</span>
                <span style={{ color: "#2a2a3e", margin: "0 4px", fontSize: 14 }}>|</span>
                <span onClick={function() { updateSlide(activeSlide, "showCards", true); }}
                  style={{ fontWeight: 600, fontSize: 13, color: currentSlide.showCards ? GREEN : "#555", letterSpacing: 0.5, cursor: "pointer" }}>CARDS</span>
              </div>

              {/* Color swatch row - Text + Base always visible; Base greyed when Body mode */}
              <div style={{ display: "flex", gap: 8, marginBottom: 6 }}>
                {/* Text swatch - context-aware: bodyColor in Body mode, cardTextColor in Cards mode */}
                <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                  <ColorPickerInline pickerKey={"s-" + activeSlide + (currentSlide.showCards ? "-cardtext" : "-body")} value={currentSlide.showCards ? (currentSlide.cardTextColor || "#333333") : (currentSlide.bodyColor || "#ffffff")} onChange={function(c) { updateSlide(activeSlide, currentSlide.showCards ? "cardTextColor" : "bodyColor", c); }} openPicker={openPicker} setOpenPicker={setOpenPicker} />
                  <span style={{ fontSize: 11, color: "#777", fontWeight: 600 }}>Text</span>
                </div>
                {/* Base swatch (card bg) - greyed out in Body mode */}
                <div style={{ display: "flex", alignItems: "center", gap: 4, opacity: currentSlide.showCards ? 1 : 0.35 }}>
                  <ColorPickerInline pickerKey={"s-" + activeSlide + "-cardbg"} value={currentSlide.cardBgColor || "#ffffff"} onChange={function(c) { updateSlide(activeSlide, "cardBgColor", c); }} openPicker={openPicker} setOpenPicker={setOpenPicker} disabled={!currentSlide.showCards} />
                  <span style={{ fontSize: 11, color: "#777", fontWeight: 600 }}>Base</span>
                </div>
                <div style={{ flex: 1 }} />
                {/* Font size stepper - always visible, context-aware */}
                {(function() { var sk = currentSlide.showCards ? "cardText" : "body"; return (
                <div style={{ display: "flex", alignItems: "center", gap: 0, background: "#28283e", borderRadius: 4, border: "1px solid #444", height: 28, overflow: "hidden" }}>
                  <button onClick={function() { if (sizes[sk] > 12) setSize(sk, sizes[sk] - 1); }}
                    style={{ minWidth: 28, minHeight: 28, border: "none", background: "transparent", color: "#555", cursor: "pointer", fontSize: 14, padding: 0, lineHeight: "28px" }}>{"\u2212"}</button>
                  <input value={sizes[sk]} onChange={function(e) { var v = parseInt(e.target.value, 10); if (!isNaN(v)) setSize(sk, Math.max(12, Math.min(100, v))); }}
                    style={{ width: 30, height: 28, border: "none", borderLeft: "1px solid #444", borderRight: "1px solid #444", background: "transparent", color: "#666", fontSize: 11, fontFamily: "monospace", textAlign: "center", padding: 0, outline: "none" }} />
                  <button onClick={function() { if (sizes[sk] < 100) setSize(sk, sizes[sk] + 1); }}
                    style={{ minWidth: 28, minHeight: 28, border: "none", background: "transparent", color: "#555", cursor: "pointer", fontSize: 14, padding: 0, lineHeight: "28px" }}>+</button>
                </div>
                ); })()}
              </div>

              {/* Body content */}
              {!currentSlide.showCards && (
                <div>
                  <textarea value={currentSlide.body} onChange={function(e) { updateSlide(activeSlide, "body", e.target.value); }} rows={2}
                    style={{ width: "100%", padding: "8px 12px", borderRadius: 8, border: "1px solid #444", background: "#28283e", color: "#fff", fontSize: 13, boxSizing: "border-box", resize: "vertical" }} />
                  <p style={{ fontSize: 11, color: "#555", marginTop: 2, marginBottom: 8 }}>**word** = accent color.</p>
                </div>
              )}

              {/* Cards content */}
              {currentSlide.showCards && (
                <div>
                  {currentSlide.cards.map(function(c, i) {
                    return (
                      <div key={i} style={{ display: "flex", gap: 8, marginBottom: 6, alignItems: "center" }}>
                        <input value={c} onChange={function(e) { updateSlideCard(activeSlide, i, e.target.value); }} placeholder={"Card " + (i + 1) + "..."}
                          style={{ width: "100%", padding: "6px 10px", borderRadius: 8, border: "1px solid #444", background: "#28283e", color: "#fff", fontSize: 12, boxSizing: "border-box" }} />
                        {currentSlide.cards.length > 1 && (
                          <button onClick={function() { removeSlideCard(activeSlide, i); }} style={{ background: "none", border: "none", color: "#f87171", cursor: "pointer", fontSize: 18, padding: 4 }}>{"\u00d7"}</button>
                        )}
                      </div>
                    );
                  })}
                  {currentSlide.cards.length < 5 && (
                    <button onClick={function() { addSlideCard(activeSlide); }} style={{ background: "#28283e", border: "1px dashed #444", color: "#888", padding: "5px 12px", borderRadius: 8, cursor: "pointer", fontSize: 12, marginTop: 4 }}>+ Add Card</button>
                  )}
                  <p style={{ fontSize: 11, color: "#555", marginTop: 6, marginBottom: 4 }}>**word** = accent color.</p>
                </div>
              )}
            </div>
          )}


          </div>

          {/* -- COL 3: Preview -- */}
          <div style={{ flex: "0 0 auto", position: "sticky", top: 24, alignSelf: "flex-start" }}>
            <p style={{ fontSize: 13, color: "#666", marginBottom: 8, fontWeight: 600, letterSpacing: 1 }}>PREVIEW</p>
            <canvas ref={canvasRef} width={W} height={H}
              style={{ width: 360, height: 450, borderRadius: 12, border: "1px solid #222", display: "block" }} />
            <button onClick={downloadCurrentPDF}
              style={{ marginTop: 12, width: "100%", padding: "12px 0", borderRadius: 8, border: "none", background: "#6366f1", color: "#fff", fontSize: 14, fontWeight: 700, cursor: "pointer" }}>
              Download Current Slide (PDF)
            </button>
            {seriesSlides.length > 1 && (
              <button onClick={downloadAllPDF}
                style={{ marginTop: 6, width: "100%", padding: "10px 0", borderRadius: 8, border: "2px solid " + GREEN, background: "transparent", color: GREEN, fontSize: 13, fontWeight: 700, cursor: "pointer" }}>
                {"Download All " + seriesSlides.length + " Slides (PDF)"}
              </button>
            )}
            {pdfDownload && (
              <div style={{ marginTop: 8, display: "flex", alignItems: "center", gap: 6 }}>
                <a href={pdfDownload.url} download={pdfDownload.name}
                  onClick={function() { setTimeout(clearPdfDownload, 1500); }}
                  style={{ fontSize: 11, color: "#a5b4fc", textDecoration: "underline", flex: 1, wordBreak: "break-all" }}>
                  {"Save " + pdfDownload.name}
                </a>
                <button onClick={clearPdfDownload}
                  style={{ background: "none", border: "none", color: "#999", cursor: "pointer", fontSize: 14, padding: "0 2px", lineHeight: 1 }}>
                  {"\u00d7"}
                </button>
              </div>
            )}
            <p style={{ fontSize: 9, color: "#888", marginTop: 2, textAlign: "center" }}>Generated locally in browser; no upload.</p>
            {pdfError && (
              <p style={{ fontSize: 10, color: "#ef4444", marginTop: 4, margin: "4px 0 0 0" }}>{pdfError}</p>
            )}
            <div style={{ marginTop: 8 }}>
              <label style={{ fontSize: 10, color: "#666", display: "block", marginBottom: 2 }}>Filename prefix</label>
              <input value={exportPrefix}
                onChange={function(e) { setExportPrefix(e.target.value); }}
                placeholder="linkedin-slide"
                style={{ width: "100%", padding: "6px 8px", borderRadius: 6, border: "1px solid #444", background: "#28283e", color: "#ccc", fontSize: 11, boxSizing: "border-box", fontFamily: "monospace" }} />
            </div>
            <p style={{ fontSize: 10, color: "#555", marginTop: 6, textAlign: "center" }}>{"800 \u00d7 1000px"}</p>
          </div>
        </div>
      </div>

      {/* Confirm dialog overlay */}
      {confirmDialog && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 9999 }}
          onClick={function() { setConfirmDialog(null); }}>
          <div style={{ background: "#1a1a30", border: "1px solid #444", borderRadius: 10, padding: "20px 24px", maxWidth: 320, textAlign: "center", boxShadow: "0 8px 32px rgba(0,0,0,0.6)" }}
            onClick={function(e) { e.stopPropagation(); }}>
            <p style={{ color: "#ccc", fontSize: 13, margin: "0 0 16px 0", lineHeight: 1.4 }}>{confirmDialog.message}</p>
            <div style={{ display: "flex", gap: 10, justifyContent: "center" }}>
              <button onClick={function() { setConfirmDialog(null); }}
                style={{ padding: "6px 18px", borderRadius: 6, border: "1px solid #444", background: "#28283e", color: "#999", cursor: "pointer", fontSize: 12, fontWeight: 600 }}>
                Cancel
              </button>
              <button onClick={function() { confirmDialog.onConfirm(); setConfirmDialog(null); }}
                style={{ padding: "6px 18px", borderRadius: 6, border: "none", background: "#6366f1", color: "#fff", cursor: "pointer", fontSize: 12, fontWeight: 600 }}>
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Save Preset dialog overlay */}
      {presetDialog && presetDialog.type === "save" && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 9999 }}
          onClick={function() { setPresetDialog(null); }}>
          <div style={{ background: "#1a1a30", border: "1px solid #444", borderRadius: 10, padding: "20px 24px", maxWidth: 360, textAlign: "left", boxShadow: "0 8px 32px rgba(0,0,0,0.6)" }}
            onClick={function(e) { e.stopPropagation(); }}>
            <p style={{ color: "#ccc", fontSize: 14, fontWeight: 600, margin: "0 0 12px 0" }}>Save Preset</p>
            <label style={{ fontSize: 11, color: "#888", display: "block", marginBottom: 4 }}>Preset name</label>
            <input value={presetName} onChange={function(e) { setPresetName(e.target.value); }}
              placeholder="My Carousel"
              style={inputStyle} />
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 12, marginBottom: 16 }}>
              <button onClick={function() { setPresetIncludeImages(!presetIncludeImages); }}
                style={{ padding: "3px 12px", borderRadius: 20, border: "none",
                  background: presetIncludeImages ? GREEN : "#555",
                  color: "#fff", cursor: "pointer", fontSize: 11, fontWeight: 600 }}>
                {presetIncludeImages ? "ON" : "OFF"}
              </button>
              <span style={{ fontSize: 12, color: "#999" }}>Include images (larger file)</span>
            </div>
            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
              <button onClick={function() { setPresetDialog(null); }}
                style={{ padding: "6px 18px", borderRadius: 6, border: "1px solid #444", background: "#28283e", color: "#999", cursor: "pointer", fontSize: 12, fontWeight: 600 }}>
                Cancel
              </button>
              <button onClick={function() { downloadPreset(presetName, presetIncludeImages); setPresetDialog(null); }}
                style={{ padding: "6px 18px", borderRadius: 6, border: "none", background: "#6366f1", color: "#fff", cursor: "pointer", fontSize: 12, fontWeight: 600 }}>
                Save
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
