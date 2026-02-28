// ===================================================
// useSlideManagement Hook
// ===================================================
// Manages slide CRUD, reorder, duplicate, card management, and image uploads.
// Params: deps object { pushUndo, setConfirmDialog }
// Returns: { seriesSlides, setSeriesSlides, activeSlide, setActiveSlide,
//   slideAssets, setSlideAssets, getAsset, setAsset, setScale,
//   dragFrom, setDragFrom, dragOver, setDragOver,
//   profilePicInputRef, screenshotInputRef, customBgInputRef,
//   profileImg, setProfileImg, profilePicName, setProfilePicName,
//   isCustomProfilePic, setIsCustomProfilePic,
//   updateSlide, updateBgField, syncBgToAll, resetBgToDefault,
//   addSlide, duplicateSlide, removeSlide, reorderSlide,
//   updateSlideCard, addSlideCard, removeSlideCard,
//   handleCustomUpload, handleScreenshotUpload, handleProfilePicUpload,
//   removeProfilePic, removeCustomBg, removeScreenshot }

function useSlideManagement(deps) {
  var profilePicInputRef = useRef(null);
  var screenshotInputRef = useRef(null);
  var customBgInputRef = useRef(null);

  var [isCustomProfilePic, setIsCustomProfilePic] = useState(false);
  var [seriesSlides, setSeriesSlides] = useState([makeDefaultSlide("Heading", "Body text")]);
  var [activeSlide, setActiveSlide] = useState(0);
  var [slideAssets, setSlideAssets] = useState({});
  var [dragFrom, setDragFrom] = useState(null);
  var [dragOver, setDragOver] = useState(null);
  var [profileImg, setProfileImg] = useState(null);
  var [profilePicName, setProfilePicName] = useState(null);

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

  // --- Slide CRUD ---

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
    deps.setConfirmDialog({
      message: "Apply Slide " + (activeSlide + 1) + "\u2019s background settings to all slides?",
      onConfirm: function() {
        deps.pushUndo();
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
    deps.setConfirmDialog({
      message: "Reset Slide " + (activeSlide + 1) + "\u2019s background to defaults?",
      onConfirm: function() {
        deps.pushUndo();
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
              accentColor: "#a5b4fc",
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
    profileImg: profileImg, setProfileImg: setProfileImg,
    profilePicName: profilePicName, setProfilePicName: setProfilePicName,
    isCustomProfilePic: isCustomProfilePic, setIsCustomProfilePic: setIsCustomProfilePic,
    updateSlide: updateSlide, updateBgField: updateBgField,
    syncBgToAll: syncBgToAll, resetBgToDefault: resetBgToDefault,
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
