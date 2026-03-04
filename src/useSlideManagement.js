// ===================================================
// useSlideManagement Hook
// ===================================================
// Manages slide CRUD, reorder, duplicate, card management, and image uploads.
// Params: deps object { pushUndo, setConfirmDialog }
// Returns: { seriesSlides, setSeriesSlides, activeSlide, setActiveSlide,
//   slideAssets, setSlideAssets, getAsset, setAsset, setScale,
//   dragFrom, setDragFrom, dragOver, setDragOver,
//   profilePicInputRef, screenshotInputRef, customBgInputRef,
//   updateSlide, updateBgField, syncBgToAll, resetAllToDefault,
//   addSlide, duplicateSlide, removeSlide, reorderSlide,
//   updateSlideCard, addSlideCard, removeSlideCard,
//   handleCustomUpload, handleScreenshotUpload, handleProfilePicUpload,
//   removeProfilePic, removeCustomBg, removeScreenshot }

function useSlideManagement(deps) {
  var profilePicInputRef = useRef(null);
  var screenshotInputRef = useRef(null);
  var customBgInputRef = useRef(null);

  var [seriesSlides, setSeriesSlides] = useState([makeDefaultSlide("Heading", "Body text")]);
  var [activeSlide, setActiveSlide] = useState(0);
  var [slideAssets, setSlideAssets] = useState({});
  var [dragFrom, setDragFrom] = useState(null);
  var [dragOver, setDragOver] = useState(null);

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

  // --- Image uploads ---

  var handleCustomUpload = function(e) {
    var file = e.target.files[0];
    if (!file) return;
    var fileName = file.name;
    var targetSlide = activeSlide;
    var reader = new FileReader();
    reader.onload = function(ev) {
      var img = new Image();
      img.onload = function() {
        setSeriesSlides(function(prev) {
          return prev.map(function(s, i) {
            if (i !== targetSlide) return s;
            return Object.assign({}, s, { customBgImage: img, customBgName: fileName, bgType: "custom" });
          });
        });
      };
      img.onerror = function() { console.warn("Image failed to load: " + fileName); };
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
        // Auto-enable showScreenshot when image is uploaded
        setSeriesSlides(function(prev) {
          return prev.map(function(s, i) {
            if (i !== key) return s;
            if (s.showScreenshot) return s;
            return Object.assign({}, s, { showScreenshot: true });
          });
        });
      };
      img.onerror = function() { console.warn("Image failed to load: " + fileName); };
      img.src = ev.target.result;
    };
    reader.readAsDataURL(file);
  };

  var handleProfilePicUpload = function(e) {
    var file = e.target.files[0];
    if (!file) return;
    var fileName = file.name;
    var targetSlide = activeSlide;
    var reader = new FileReader();
    reader.onload = function(ev) {
      var img = new Image();
      img.onload = function() {
        setSeriesSlides(function(prev) {
          return prev.map(function(s, i) {
            if (i !== targetSlide) return s;
            return Object.assign({}, s, { profileImg: img, profilePicName: fileName });
          });
        });
      };
      img.onerror = function() { console.warn("Image failed to load: " + fileName); };
      img.src = ev.target.result;
    };
    reader.readAsDataURL(file);
  };

  var removeProfilePic = function() {
    if (profilePicInputRef.current) { profilePicInputRef.current.value = ""; }
    setSeriesSlides(function(prev) {
      return prev.map(function(s, i) {
        if (i !== activeSlide) return s;
        return Object.assign({}, s, { profileImg: null, profilePicName: null });
      });
    });
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
    setSeriesSlides(function(prev) {
      return prev.map(function(s, i) {
        if (i !== key) return s;
        if (!s.showScreenshot) return s;
        return Object.assign({}, s, { showScreenshot: false });
      });
    });
  };

  // --- Slide CRUD ---

  var updateSlide = function(idx, field, val, shouldSnapshot) {
    if (shouldSnapshot) deps.pushUndo();
    setSeriesSlides(function(prev) {
      return prev.map(function(s, i) {
        if (i !== idx) return s;
        var updated = Object.assign({}, s);
        updated[field] = val;
        return updated;
      });
    });
  };

  var updateBgField = function(field, value) {
    updateSlide(activeSlide, field, value);
  };

  var syncBgToAll = function() {
    deps.setConfirmDialog({
      message: "Apply Slide " + (activeSlide + 1) + "\u2019s visual settings to all slides? (Text content and screenshots are not affected.)",
      onConfirm: function() {
        deps.pushUndo();
        var src = seriesSlides[activeSlide];
        setSeriesSlides(function(prev) {
          return prev.map(function(s) {
            return Object.assign({}, s, {
              // Background
              solidColor: src.solidColor,
              bgType: src.bgType,
              customBgImage: src.customBgImage,
              customBgName: src.customBgName,
              geoEnabled: src.geoEnabled,
              geoLines: src.geoLines,
              geoOpacity: src.geoOpacity,
              geoShape: src.geoShape,
              // Frame
              frameEnabled: src.frameEnabled,
              accentColor: src.accentColor,
              decorationColor: src.decorationColor,
              borderColor: src.borderColor,
              borderOpacity: src.borderOpacity,
              // Profile
              profileImg: src.profileImg,
              profilePicName: src.profilePicName,
              footerBg: src.footerBg,
              // Toggles (not text content)
              showHeading: src.showHeading,
              showAccentBar: src.showAccentBar,
              showCards: src.showCards,
              showCardChecks: src.showCardChecks,
              showBrandName: src.showBrandName,
              showTopCorner: src.showTopCorner,
              showBottomCorner: src.showBottomCorner,
              // Font sizes
              headingSize: src.headingSize,
              bodySize: src.bodySize,
              cardTextSize: src.cardTextSize,
              topCornerSize: src.topCornerSize,
              bottomCornerSize: src.bottomCornerSize,
              brandNameSize: src.brandNameSize,
              // Title typography
              titleColor: src.titleColor,
              titleFontFamily: src.titleFontFamily,
              titleBold: src.titleBold,
              titleItalic: src.titleItalic,
              headingBgColor: src.headingBgColor,
              headingBgOpacity: src.headingBgOpacity,
              // Body typography
              bodyColor: src.bodyColor,
              bodyFontFamily: src.bodyFontFamily,
              bodyBold: src.bodyBold,
              bodyItalic: src.bodyItalic,
              bodyBgColor: src.bodyBgColor,
              bodyBgOpacity: src.bodyBgOpacity,
              // Card typography
              cardTextColor: src.cardTextColor,
              cardFontFamily: src.cardFontFamily,
              cardBold: src.cardBold,
              cardItalic: src.cardItalic,
              cardBgColor: src.cardBgColor,
              cardBgOpacity: src.cardBgOpacity,
              // Brand name typography
              brandNameColor: src.brandNameColor,
              brandNameFontFamily: src.brandNameFontFamily,
              brandNameBold: src.brandNameBold,
              brandNameItalic: src.brandNameItalic,
              // Top corner typography
              topCornerColor: src.topCornerColor,
              topCornerFontFamily: src.topCornerFontFamily,
              topCornerBold: src.topCornerBold,
              topCornerItalic: src.topCornerItalic,
              topCornerOpacity: src.topCornerOpacity,
              topCornerBgColor: src.topCornerBgColor,
              topCornerBgOpacity: src.topCornerBgOpacity,
              // Bottom corner typography
              bottomCornerColor: src.bottomCornerColor,
              bottomCornerFontFamily: src.bottomCornerFontFamily,
              bottomCornerBold: src.bottomCornerBold,
              bottomCornerItalic: src.bottomCornerItalic,
              bottomCornerOpacity: src.bottomCornerOpacity,
              bottomCornerBgColor: src.bottomCornerBgColor,
              bottomCornerBgOpacity: src.bottomCornerBgOpacity
            });
          });
        });
      }
    });
  };

  var resetAllToDefault = function() {
    deps.setConfirmDialog({
      message: "Reset ALL slides to defaults? This resets everything except text content.",
      onConfirm: function() {
        deps.pushUndo();
        setSeriesSlides(function(prev) {
          return prev.map(function() {
            return makeDefaultSlide();
          });
        });
        setSlideAssets(function() {
          return {};
        });
      }
    });
  };

  var addSlide = function() {
    setSeriesSlides(function(prev) {
      if (prev.length >= MAX_SLIDES) return prev;
      return prev.concat([makeDefaultSlide()]);
    });
  };

  var duplicateSlide = function() {
    if (seriesSlides.length >= MAX_SLIDES) return;
    deps.setConfirmDialog({
      message: "Duplicate Slide " + (activeSlide + 1) + "?",
      onConfirm: function() {
        deps.pushUndo();
        var insertIdx = activeSlide + 1;

        setSeriesSlides(function(prev) {
          if (prev.length >= MAX_SLIDES) return prev;
          var src = prev[activeSlide];
          if (!src) return prev;
          var copy = Object.assign({}, src, { cards: src.cards.slice() });
          var next = prev.slice();
          next.splice(insertIdx, 0, copy);
          return next;
        });

        setSlideAssets(function(prev) {
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
    deps.setConfirmDialog({
      message: "Remove Slide " + (idx + 1) + "?",
      onConfirm: function() {
        deps.pushUndo();
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
      }
    });
  };

  var resetSlide = function(idx) {
    deps.setConfirmDialog({
      message: "Reset Slide " + (idx + 1) + " to defaults?",
      onConfirm: function() {
        deps.pushUndo();
        setSeriesSlides(function(prev) {
          return prev.map(function(s, i) {
            if (i !== idx) return s;
            return makeDefaultSlide();
          });
        });
        setSlideAssets(function(prev) {
          var next = Object.assign({}, prev);
          delete next[idx];
          return next;
        });
      }
    });
  };

  var reorderSlide = function(fromIdx, toIdx) {
    if (fromIdx === toIdx || fromIdx == null || toIdx == null) return;
    var snapshotLen = seriesSlides.length;
    if (fromIdx < 0 || fromIdx >= snapshotLen || toIdx < 0 || toIdx >= snapshotLen) {
      setDragFrom(null);
      setDragOver(null);
      return;
    }
    deps.pushUndo();

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

    setSeriesSlides(function(prev) {
      if (fromIdx < 0 || fromIdx >= prev.length) return prev;
      if (toIdx < 0 || toIdx >= prev.length) return prev;
      var next = prev.slice();
      var moved = next.splice(fromIdx, 1)[0];
      next.splice(toIdx, 0, moved);
      return next;
    });

    var indexMap = buildIndexMap(snapshotLen);

    setSlideAssets(function(prev) {
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
      if (prev === fromIdx) return toIdx;
      if (indexMap[prev] != null) return indexMap[prev];
      return prev;
    });

    setDragFrom(null);
    setDragOver(null);
  };

  // --- Card management ---

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

  return {
    seriesSlides: seriesSlides, setSeriesSlides: setSeriesSlides,
    activeSlide: activeSlide, setActiveSlide: setActiveSlide,
    slideAssets: slideAssets, setSlideAssets: setSlideAssets,
    getAsset: getAsset, setAsset: setAsset, setScale: setScale,
    dragFrom: dragFrom, setDragFrom: setDragFrom,
    dragOver: dragOver, setDragOver: setDragOver,
    profilePicInputRef: profilePicInputRef,
    screenshotInputRef: screenshotInputRef,
    customBgInputRef: customBgInputRef,
    updateSlide: updateSlide, updateBgField: updateBgField,
    syncBgToAll: syncBgToAll, resetAllToDefault: resetAllToDefault,
    addSlide: addSlide, duplicateSlide: duplicateSlide,
    removeSlide: removeSlide, resetSlide: resetSlide, reorderSlide: reorderSlide,
    updateSlideCard: updateSlideCard, addSlideCard: addSlideCard, removeSlideCard: removeSlideCard,
    handleCustomUpload: handleCustomUpload,
    handleScreenshotUpload: handleScreenshotUpload,
    handleProfilePicUpload: handleProfilePicUpload,
    removeProfilePic: removeProfilePic,
    removeCustomBg: removeCustomBg,
    removeScreenshot: removeScreenshot
  };
}
