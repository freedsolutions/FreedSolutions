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
  var [confirmDialog, setConfirmDialog] = useState(null);

  // Undo/redo
  var undoManagerRef = useRef(createUndoManager());
  var pushUndoRef = useRef(null);

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

  // Export prefix
  var [exportPrefix, setExportPrefix] = useState("linkedin-slide");

  // --- Slide management hook ---
  var slideMgmt = useSlideManagement({ pushUndo: function() { if (pushUndoRef.current) pushUndoRef.current(); }, setConfirmDialog: setConfirmDialog });

  var seriesSlides = slideMgmt.seriesSlides;
  var setSeriesSlides = slideMgmt.setSeriesSlides;
  var activeSlide = slideMgmt.activeSlide;
  var setActiveSlide = slideMgmt.setActiveSlide;
  var slideAssets = slideMgmt.slideAssets;
  var setSlideAssets = slideMgmt.setSlideAssets;
  var getAsset = slideMgmt.getAsset;
  var setScale = slideMgmt.setScale;
  var profileImg = slideMgmt.profileImg;
  var setProfileImg = slideMgmt.setProfileImg;
  var profilePicName = slideMgmt.profilePicName;
  var setProfilePicName = slideMgmt.setProfilePicName;
  var isCustomProfilePic = slideMgmt.isCustomProfilePic;
  var setIsCustomProfilePic = slideMgmt.setIsCustomProfilePic;

  // --- Undo/redo snapshot helpers ---

  var captureSnapshot = function() {
    return {
      seriesSlides: seriesSlides.map(function(s) {
        return Object.assign({}, s, { cards: s.cards ? s.cards.slice() : s.cards });
      }),
      slideAssets: Object.keys(slideAssets).reduce(function(acc, k) {
        acc[k] = Object.assign({}, slideAssets[k]);
        return acc;
      }, {}),
      sizes: Object.assign({}, sizes),
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

  // Keep pushUndoRef current so hooks always call the latest captureSnapshot
  pushUndoRef.current = function() {
    undoManagerRef.current.pushSnapshot(captureSnapshot());
  };

  // Stable refs for undo/redo keyboard handler
  var captureSnapshotRef = useRef(captureSnapshot);
  var restoreSnapshotRef = useRef(restoreSnapshot);
  captureSnapshotRef.current = captureSnapshot;
  restoreSnapshotRef.current = restoreSnapshot;

  // Global keyboard handler for undo/redo (registered once)
  useEffect(function() {
    var handler = function(e) {
      // Skip if focus is in an input, textarea, or select (preserve native text undo)
      var tag = e.target && e.target.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      var isCtrl = e.ctrlKey || e.metaKey;
      if (!isCtrl || (e.key && e.key.toLowerCase()) !== "z") return;
      e.preventDefault();
      if (e.shiftKey) {
        var redoSnap = undoManagerRef.current.redo(captureSnapshotRef.current());
        if (redoSnap) restoreSnapshotRef.current(redoSnap);
      } else {
        var undoSnap = undoManagerRef.current.undo(captureSnapshotRef.current());
        if (undoSnap) restoreSnapshotRef.current(undoSnap);
      }
    };
    document.addEventListener("keydown", handler);
    return function() { document.removeEventListener("keydown", handler); };
  }, []);

  // Stable refs for paste handler (registered once)
  var activeSlideRef = useRef(activeSlide);
  activeSlideRef.current = activeSlide;
  var seriesSlidesRef = useRef(seriesSlides);
  seriesSlidesRef.current = seriesSlides;
  var slideMgmtRef = useRef(slideMgmt);
  slideMgmtRef.current = slideMgmt;

  // Global paste handler for screenshot images (registered once)
  useEffect(function() {
    var handler = function(e) {
      // Skip if focus is in an input, textarea, or select (preserve normal text paste)
      var tag = e.target && e.target.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;

      // Check for image data in clipboard
      var items = e.clipboardData && e.clipboardData.items;
      if (!items) return;
      var imageItem = null;
      for (var i = 0; i < items.length; i++) {
        if (items[i].type.indexOf("image/") === 0) {
          imageItem = items[i];
          break;
        }
      }
      if (!imageItem) return;

      e.preventDefault();
      // Capture target slide at paste time so async load can't drift to another slide.
      var targetSlide = activeSlideRef.current;
      var blob = imageItem.getAsFile();
      if (!blob) return;
      var reader = new FileReader();
      reader.onload = function(ev) {
        var img = new Image();
        img.onload = function() {
          var mgmt = slideMgmtRef.current;
          var slides = seriesSlidesRef.current;
          // Auto-enable screenshot if not already on
          if (slides[targetSlide] && !slides[targetSlide].showScreenshot) {
            mgmt.updateSlide(targetSlide, "showScreenshot", true);
          }
          mgmt.setAsset(targetSlide, { name: "pasted-image.png", image: img });
        };
        img.src = ev.target.result;
      };
      reader.readAsDataURL(blob);
    };
    document.addEventListener("paste", handler);
    return function() { document.removeEventListener("paste", handler); };
  }, []);

  // --- Canvas rendering hook ---
  var canvasRenderer = useCanvasRenderer(canvasRef, seriesSlides, slideAssets, sizes, profileImg, activeSlide);
  var renderSlide = canvasRenderer.renderSlide;

  // --- PDF export hook ---
  var pdfExport = usePdfExport(canvasRef, renderSlide, seriesSlides, activeSlide, exportPrefix);
  var pdfDownload = pdfExport.pdfDownload;
  var pdfError = pdfExport.pdfError;
  var setPdfError = pdfExport.setPdfError;
  var downloadCurrentPDF = pdfExport.downloadCurrentPDF;
  var downloadAllPDF = pdfExport.downloadAllPDF;
  var clearPdfDownload = pdfExport.clearPdfDownload;

  // --- Presets hook ---
  var presets = usePresets({
    seriesSlides: seriesSlides, slideAssets: slideAssets, sizes: sizes,
    setSizes: setSizes, profileImg: profileImg, setProfileImg: setProfileImg,
    profilePicName: profilePicName, setProfilePicName: setProfilePicName,
    isCustomProfilePic: isCustomProfilePic, setIsCustomProfilePic: setIsCustomProfilePic,
    exportPrefix: exportPrefix, setExportPrefix: setExportPrefix,
    setSeriesSlides: setSeriesSlides, setSlideAssets: setSlideAssets,
    setActiveSlide: setActiveSlide, clearPdfDownload: clearPdfDownload,
    setPdfError: setPdfError,
    pushUndo: function() { if (pushUndoRef.current) pushUndoRef.current(); },
    setConfirmDialog: setConfirmDialog
  });

  // --- Convenience aliases ---
  var updateSlide = slideMgmt.updateSlide;
  var updateBgField = slideMgmt.updateBgField;
  var currentSlide = seriesSlides[activeSlide] || seriesSlides[0];
  var isCustomBg = currentSlide.bgType === "custom";

  return (
    <div style={{ fontFamily: '"Helvetica Neue", Helvetica, Arial, sans-serif', background: "#000000", minHeight: "100vh", color: "#e0e0e0", padding: 16 }}>
      <div style={{ maxWidth: 1520, margin: "0 auto" }}>
        <h2 style={{ color: "#fff", marginBottom: 16, fontSize: 20 }}>LinkedIn Carousel Generator</h2>

        <div style={{ display: "flex", gap: 20, alignItems: "flex-start" }}>

        {/* -- LEFT COLUMN: Slides -- */}
        <div style={{ flex: "0 0 136px", minWidth: 136, maxWidth: 136, position: "sticky", top: 24, alignSelf: "flex-start" }}>
          <div style={{ marginBottom: 10 }}>
            <button onClick={slideMgmt.duplicateSlide}
              style={{ width: "100%", padding: "6px 8px", borderRadius: 8, border: "1px solid #444", background: "#28283e", color: "#ccc", cursor: seriesSlides.length >= MAX_SLIDES ? "default" : "pointer", fontSize: 10, fontWeight: 700, opacity: seriesSlides.length >= MAX_SLIDES ? 0.4 : 1 }}>
              Duplicate
            </button>
          </div>
          <div style={{ background: "#10101a", border: "1px solid #343447", borderRadius: 10, padding: 12 }}>
            <SlideSelector seriesSlides={seriesSlides} activeSlide={activeSlide} setActiveSlide={setActiveSlide}
              dragFrom={slideMgmt.dragFrom} setDragFrom={slideMgmt.setDragFrom} dragOver={slideMgmt.dragOver} setDragOver={slideMgmt.setDragOver}
              reorderSlide={slideMgmt.reorderSlide} addSlide={slideMgmt.addSlide} duplicateSlide={slideMgmt.duplicateSlide}
              removeSlide={slideMgmt.removeSlide} />
          </div>
        </div>

        {/* -- CENTER PANE: Settings + Slide Editor -- */}
        <div style={{ flex: "1 1 0", minWidth: 420 }}>

        {/* --- Top Section: Settings --- */}
        <div>

          {/* --- PRESETS --- */}
          <div style={{ marginBottom: 14, position: "relative", paddingRight: 160 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
              <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>PRESETS</label>
              <button onClick={function() { presets.setPresetError(""); presets.setPresetName(exportPrefix || ""); presets.setPresetDialog({ type: "save" }); }}
                style={smallBtnStyle}>
                Save
              </button>
              <button onClick={function() { presets.setPresetError(""); if (presets.presetInputRef.current) presets.presetInputRef.current.click(); }}
                style={smallBtnStyle}>
                Load
              </button>
              <input ref={presets.presetInputRef} type="file" accept=".json" onChange={presets.handlePresetUpload} style={{ display: "none" }} />
            </div>
            {presets.presetDownload && (
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 4 }}>
                <a href={presets.presetDownload.url} download={presets.presetDownload.name}
                  onClick={function() { setTimeout(presets.clearPresetDownload, 1500); }}
                  style={{ fontSize: 11, color: "#a5b4fc", textDecoration: "underline", flex: 1, wordBreak: "break-all" }}>
                  {"Save " + presets.presetDownload.name}
                </a>
                <button onClick={presets.clearPresetDownload}
                  style={{ background: "none", border: "none", color: "#999", cursor: "pointer", fontSize: 14, padding: "0 2px", lineHeight: 1 }}>
                  {"\u00d7"}
                </button>
              </div>
            )}
            {presets.presetError && (
              <div style={{ marginTop: 4, padding: "4px 8px", borderRadius: 6, background: "#3a1a1a", border: "1px solid #7f1d1d", color: "#fca5a5", fontSize: 11, display: "flex", alignItems: "center", gap: 6 }}>
                <span style={{ flex: 1 }}>{presets.presetError}</span>
                <button onClick={function() { presets.setPresetError(""); }}
                  style={{ background: "none", border: "none", color: "#fca5a5", cursor: "pointer", fontSize: 14, padding: "0 2px", lineHeight: 1 }}>{"\u00d7"}</button>
              </div>
            )}
          </div>
          <div style={{ borderTop: "1px solid #444", marginBottom: 10 }} />

          {/* --- BACKGROUND --- */}
          <div style={{ marginBottom: 14 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
              <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>BACKGROUND</label>
              <button onClick={slideMgmt.syncBgToAll} style={smallBtnStyle}>
                Sync All
              </button>
              <button onClick={slideMgmt.resetBgToDefault} style={smallBtnStyle}>
                Reset
              </button>
            </div>

            {/* Background controls row */}
            <div style={{ display: "flex", gap: 14, alignItems: "stretch" }}>

              {/* Left zone: Solid/Photo pill + Accent / Base / Layer / Frame */}
              <div style={{ flex: "0 0 auto", display: "flex", flexDirection: "column" }}>

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
                    style={{ minWidth: 44, padding: "3px 8px", borderRadius: 20, border: "none", background: (!isCustomBg && currentSlide.geoEnabled) ? GREEN : "#555", color: "#fff", cursor: isCustomBg ? "default" : "pointer", fontSize: 11, fontWeight: 600 }}>
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
                    style={{ minWidth: 44, padding: "3px 8px", borderRadius: 20, border: "none", background: currentSlide.frameEnabled ? GREEN : "#555", color: "#fff", cursor: "pointer", fontSize: 11, fontWeight: 600 }}>
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

              {/* Middle zone: upload + thumbnail + status */}
              <div style={{ flex: "0 1 180px", minWidth: 130, position: "relative", display: "flex", flexDirection: "column", alignItems: "center" }}>

                {/* Photo upload - above thumbnail; visible only in Photo mode */}
                <div style={{ width: "100%", marginBottom: 2, visibility: isCustomBg ? "visible" : "hidden" }}>
                  <input ref={slideMgmt.customBgInputRef} type="file" accept="image/*" onChange={function(e) { slideMgmt.handleCustomUpload(e); }} style={{ display: "none" }} />
                  <button onClick={function() { if (slideMgmt.customBgInputRef.current) slideMgmt.customBgInputRef.current.click(); }}
                    style={{ padding: "3px 8px", borderRadius: 4, border: "1px solid #444", background: "#28283e", color: "#ccc", cursor: "pointer", fontSize: 10, fontWeight: 600 }}>
                    Choose File
                  </button>
                  <p style={{ fontSize: 9, color: "#666", margin: "2px 0 0 0", wordBreak: "break-all", lineHeight: 1.3, minHeight: 10 }}>{currentSlide.customBgName || "\u00a0"}</p>
                </div>

                {/* Thumbnail preview */}
                <div style={{ width: "100%", maxWidth: 110, aspectRatio: "4/5", borderRadius: 6, overflow: "hidden", border: "2px solid #444", background: "#111119", position: "relative" }}>
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
                        <button onClick={slideMgmt.removeCustomBg} style={{ background: "none", border: "none", color: "#f87171", cursor: "pointer", fontSize: 9, padding: 0 }}>{"\u00d7"} Remove</button>
                      </div>
                    ) : (
                      <span style={{ fontSize: 9, color: "#555" }}>No image</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Right zone: Profile Pic + Screenshot (stacked) */}
              <div style={{ flex: "0 0 126px", width: 126, minWidth: 126, paddingLeft: 6, borderLeft: "1px solid #333", display: "flex", flexDirection: "column", alignItems: "stretch", gap: 6, alignSelf: "flex-start" }}>
                {/* Profile card */}
                <div style={{ background: "#0f0f1a", border: "1px solid #343447", borderRadius: 8, padding: "6px 6px 5px", display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center", position: "relative" }}>
                  {profileImg && isCustomProfilePic && (
                    <button onClick={slideMgmt.removeProfilePic}
                      title="Remove profile image"
                      style={{ position: "absolute", top: 4, right: 5, background: "none", border: "none", color: "#f87171", cursor: "pointer", fontSize: 11, fontWeight: 700, padding: 0, lineHeight: 1 }}>
                      {"\u00d7"}
                    </button>
                  )}
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 6, marginBottom: 4 }}>
                    <label style={{ fontSize: 10, color: "#888", fontWeight: 600, letterSpacing: 0.5, marginBottom: 0 }}>PROFILE</label>
                    <span style={{ fontSize: 9, color: "#555" }}>84{"\u00d7"}84</span>
                  </div>
                  <input ref={slideMgmt.profilePicInputRef} type="file" accept="image/*" onChange={slideMgmt.handleProfilePicUpload} style={{ display: "none" }} />
                  <button onClick={function() { if (slideMgmt.profilePicInputRef.current) slideMgmt.profilePicInputRef.current.click(); }}
                    style={{ width: "100%", padding: "3px 6px", borderRadius: 4, border: "1px solid #444", background: "#28283e", color: "#ccc", cursor: "pointer", fontSize: 9, fontWeight: 600, marginBottom: 4 }}>
                    Choose
                  </button>
                  <div style={{ width: 48, height: 48, borderRadius: "50%", overflow: "hidden", border: "2px solid #444", background: "#111119", display: "flex", alignItems: "center", justifyContent: "center" }}>
                    {profileImg ? (
                      <img src={profileImg.src} alt="Profile pic" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                    ) : (
                      <span style={{ fontSize: 9, color: "#555" }}>None</span>
                    )}
                  </div>
                </div>

                {/* Screenshot card */}
                {currentSlide && (
                  <div style={{ background: "#0f0f1a", border: "1px solid #343447", borderRadius: 8, padding: "6px 6px", display: "flex", flexDirection: "column", position: "relative" }}>
                    {currentSlide.showScreenshot && getAsset(activeSlide).image && (
                      <button onClick={function() { slideMgmt.removeScreenshot(activeSlide); }}
                        title="Remove screenshot"
                        style={{ position: "absolute", top: 6, right: 6, background: "none", border: "none", color: "#f87171", cursor: "pointer", fontSize: 11, fontWeight: 700, padding: 0, lineHeight: 1 }}>
                        {"\u00d7"}
                      </button>
                    )}
                    <div style={{ display: "flex", alignItems: "center", gap: 4, marginBottom: 5, justifyContent: "space-between" }}>
                      <label style={{ fontSize: 9, color: "#888", fontWeight: 600, letterSpacing: 0.5, marginBottom: 0 }}>SCREENSHOT</label>
                      <button onClick={function() { var next = !currentSlide.showScreenshot; updateSlide(activeSlide, "showScreenshot", next); if (!next) { slideMgmt.removeScreenshot(activeSlide); } }}
                        style={{ minWidth: 40, padding: "2px 8px", borderRadius: 20, border: "none", background: currentSlide.showScreenshot ? GREEN : "#555", color: "#fff", cursor: "pointer", fontSize: 9, fontWeight: 600 }}>
                        {currentSlide.showScreenshot ? "ON" : "OFF"}
                      </button>
                    </div>
                    {currentSlide.showScreenshot ? (
                      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                        <input ref={slideMgmt.screenshotInputRef} type="file" accept="image/*" onChange={function(e) { slideMgmt.handleScreenshotUpload(activeSlide, e); }} style={{ display: "none" }} />
                        <button onClick={function() { if (slideMgmt.screenshotInputRef.current) slideMgmt.screenshotInputRef.current.click(); }}
                          style={{ width: "100%", padding: "4px 6px", borderRadius: 4, border: "1px solid #444", background: "#28283e", color: "#ccc", cursor: "pointer", fontSize: 9, fontWeight: 600 }}>
                          Choose File
                        </button>
                        {getAsset(activeSlide).name && (
                          <p style={{ fontSize: 9, color: "#666", margin: "0", wordBreak: "break-all", lineHeight: 1.25 }}>{getAsset(activeSlide).name}</p>
                        )}
                        {getAsset(activeSlide).image ? (
                          <div>
                            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                              <span style={{ fontSize: 10, color: GREEN }}>{"\u2713"} Uploaded</span>
                            </div>
                            <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 6 }}>
                              <span style={{ fontSize: 9, color: "#666" }}>Scale</span>
                              <input type="range" min={50} max={200} value={Math.round(getAsset(activeSlide).scale * 100)} onChange={function(e) { setScale(activeSlide, Number(e.target.value) / 100); }}
                                style={{ flex: 1 }} />
                              <span style={{ fontSize: 9, color: "#777", width: 32, textAlign: "right" }}>{Math.round(getAsset(activeSlide).scale * 100) + "%"}</span>
                            </div>
                          </div>
                        ) : (
                          <p style={{ fontSize: 9, color: "#555", margin: "0" }}>No image</p>
                        )}
                      </div>
                    ) : (
                      <div style={{ minHeight: 38, border: "1px dashed #333", borderRadius: 6, display: "flex", alignItems: "center", justifyContent: "center" }}>
                        <span style={{ fontSize: 9, color: "#555" }}>Enable to add image</span>
                      </div>
                    )}
                  </div>
                )}
              </div>

            </div>
          </div>

          {/* -- Divider before Slide Editor -- */}
          <div style={{ borderTop: "1px solid #444", marginTop: 10, marginBottom: 10 }} />
        </div>

          {/* --- Bottom Section: Slide Editor --- */}

          {/* --- SLIDE EDITOR --- */}
          {currentSlide && (
            <div style={{ background: "#1a1a30", borderRadius: 10, padding: 14, border: "1px solid #3a3a50", marginBottom: 14 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                <span style={{ color: "#888", fontSize: 12, fontWeight: 600 }}>
                  {"SLIDE " + (activeSlide + 1)}
                </span>
                <div style={{ display: "flex", gap: 6 }}>
                  <button onClick={slideMgmt.duplicateSlide}
                    style={{ background: "none", border: "1px solid #444", color: "#ccc", cursor: seriesSlides.length >= MAX_SLIDES ? "default" : "pointer", fontSize: 11, padding: "3px 10px", borderRadius: 6, opacity: seriesSlides.length >= MAX_SLIDES ? 0.4 : 1 }}>Duplicate</button>
                  <button onClick={function() { slideMgmt.resetSlide(activeSlide); }}
                    style={{ background: "none", border: "1px solid #444", color: "#ccc", cursor: "pointer", fontSize: 11, padding: "3px 10px", borderRadius: 6 }}>Reset</button>
                  {seriesSlides.length > 1 && (
                    <button onClick={function() { slideMgmt.removeSlide(activeSlide); }}
                      style={{ background: "none", border: "1px solid #f8717133", color: "#f87171", cursor: "pointer", fontSize: 11, padding: "3px 10px", borderRadius: 6 }}>Remove</button>
                  )}
                </div>
              </div>

              {/* -- Footer & Pic toggle (per-slide) -- */}
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4, marginTop: 4 }}>
                <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>FOOTER & PIC</label>
                <button onClick={function() { updateSlide(activeSlide, "showBrandName", !currentSlide.showBrandName); }}
                  style={{ minWidth: 44, padding: "3px 12px", borderRadius: 20, border: "none", background: currentSlide.showBrandName ? GREEN : "#555", color: "#fff", cursor: "pointer", fontSize: 11, fontWeight: 600 }}>
                  {currentSlide.showBrandName ? "ON" : "OFF"}
                </button>
                {currentSlide.showBrandName && (
                  <>
                    <div style={{ flex: 1 }} />
                    <SizeControl sizeKey="brandName" min={12} max={60} sizes={sizes} setSize={setSize}
                      colorVal={currentSlide.brandNameColor} colorSet={function(c) { updateSlide(activeSlide, "brandNameColor", c); }}
                      colorPickerKey={"s-" + activeSlide + "-bn"} openPicker={openPicker} setOpenPicker={setOpenPicker}
                      fontFamily={currentSlide.brandNameFontFamily} fontFamilySet={function(v) { updateSlide(activeSlide, "brandNameFontFamily", v, true); }}
                      boldVal={currentSlide.brandNameBold} boldSet={function(v) { updateSlide(activeSlide, "brandNameBold", v, true); }}
                      italicVal={currentSlide.brandNameItalic} italicSet={function(v) { updateSlide(activeSlide, "brandNameItalic", v, true); }} />
                  </>
                )}
              </div>
              {currentSlide.showBrandName && (
                <div style={{ marginBottom: 8, paddingLeft: 8, borderLeft: "2px solid #555" }}>
                  <textarea value={currentSlide.brandNameText} onChange={function(e) { updateSlide(activeSlide, "brandNameText", e.target.value); var el = e.target; el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; }} onKeyDown={function(e) { if (e.key === "Enter") e.preventDefault(); }} placeholder="Brand name..." rows={1}
                    ref={function(el) { if (el) { el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; } }}
                    style={Object.assign({}, inputStyle, { marginBottom: 6, fontSize: 12, resize: "none", overflow: "hidden", maxHeight: "50vh", overflowY: "auto" })} />
                </div>
              )}

              {/* -- Top Corner toggle (per-slide) -- */}
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4, marginTop: 4 }}>
                <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>TOP CORNER</label>
                <button onClick={function() { updateSlide(activeSlide, "showTopCorner", !currentSlide.showTopCorner); }}
                  style={{ minWidth: 44, padding: "3px 12px", borderRadius: 20, border: "none", background: currentSlide.showTopCorner ? GREEN : "#555", color: "#fff", cursor: "pointer", fontSize: 11, fontWeight: 600 }}>
                  {currentSlide.showTopCorner ? "ON" : "OFF"}
                </button>
                {currentSlide.showTopCorner && (<><div style={{ flex: 1 }} />
                  <SizeControl sizeKey="topCorner" min={8} max={60} sizes={sizes} setSize={setSize}
                    colorVal={currentSlide.topCornerColor} colorSet={function(c) { updateSlide(activeSlide, "topCornerColor", c); }}
                    colorPickerKey={"s-" + activeSlide + "-tc"} openPicker={openPicker} setOpenPicker={setOpenPicker}
                    opacityVal={currentSlide.topCornerOpacity} opacitySet={function(v) { updateSlide(activeSlide, "topCornerOpacity", v); }}
                    fontFamily={currentSlide.topCornerFontFamily} fontFamilySet={function(v) { updateSlide(activeSlide, "topCornerFontFamily", v, true); }}
                    boldVal={currentSlide.topCornerBold} boldSet={function(v) { updateSlide(activeSlide, "topCornerBold", v, true); }}
                    italicVal={currentSlide.topCornerItalic} italicSet={function(v) { updateSlide(activeSlide, "topCornerItalic", v, true); }} />
                </>)}
              </div>
              {currentSlide.showTopCorner && (
                <div style={{ marginBottom: 8, paddingLeft: 8, borderLeft: "2px solid #555" }}>
                  <textarea value={currentSlide.topCornerText} onChange={function(e) { updateSlide(activeSlide, "topCornerText", e.target.value); var el = e.target; el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; }} onKeyDown={function(e) { if (e.key === "Enter") e.preventDefault(); }} placeholder="Top corner..." rows={1}
                    ref={function(el) { if (el) { el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; } }}
                    style={Object.assign({}, inputStyle, { marginBottom: 4, fontSize: 12, resize: "none", overflow: "hidden", maxHeight: "50vh", overflowY: "auto" })} />
                </div>
              )}

              {/* -- Bottom Corner toggle (per-slide) -- */}
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4, marginTop: 4 }}>
                <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>BOTTOM CORNER</label>
                <button onClick={function() { updateSlide(activeSlide, "showBottomCorner", !currentSlide.showBottomCorner); }}
                  style={{ minWidth: 44, padding: "3px 12px", borderRadius: 20, border: "none", background: currentSlide.showBottomCorner ? GREEN : "#555", color: "#fff", cursor: "pointer", fontSize: 11, fontWeight: 600 }}>
                  {currentSlide.showBottomCorner ? "ON" : "OFF"}
                </button>
                {currentSlide.showBottomCorner && (<><div style={{ flex: 1 }} />
                  <SizeControl sizeKey="bottomCorner" min={10} max={60} sizes={sizes} setSize={setSize}
                    colorVal={currentSlide.bottomCornerColor} colorSet={function(c) { updateSlide(activeSlide, "bottomCornerColor", c); }}
                    colorPickerKey={"s-" + activeSlide + "-bc"} openPicker={openPicker} setOpenPicker={setOpenPicker}
                    opacityVal={currentSlide.bottomCornerOpacity} opacitySet={function(v) { updateSlide(activeSlide, "bottomCornerOpacity", v); }}
                    fontFamily={currentSlide.bottomCornerFontFamily} fontFamilySet={function(v) { updateSlide(activeSlide, "bottomCornerFontFamily", v, true); }}
                    boldVal={currentSlide.bottomCornerBold} boldSet={function(v) { updateSlide(activeSlide, "bottomCornerBold", v, true); }}
                    italicVal={currentSlide.bottomCornerItalic} italicSet={function(v) { updateSlide(activeSlide, "bottomCornerItalic", v, true); }} />
                </>)}
              </div>
              {currentSlide.showBottomCorner && (
                <div style={{ marginBottom: 8, paddingLeft: 8, borderLeft: "2px solid #555" }}>
                  <textarea value={currentSlide.bottomCornerText} onChange={function(e) { updateSlide(activeSlide, "bottomCornerText", e.target.value); var el = e.target; el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; }} onKeyDown={function(e) { if (e.key === "Enter") e.preventDefault(); }} placeholder="Bottom corner..." rows={1}
                    ref={function(el) { if (el) { el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; } }}
                    style={Object.assign({}, inputStyle, { marginBottom: 4, fontSize: 12, resize: "none", overflow: "hidden", maxHeight: "50vh", overflowY: "auto" })} />
                </div>
              )}

              {/* -- Heading toggle (per-slide) -- */}
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4, marginTop: 4 }}>
                <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>HEADING</label>
                <button onClick={function() { updateSlide(activeSlide, "showHeading", !currentSlide.showHeading); }}
                  style={{ minWidth: 44, padding: "3px 12px", borderRadius: 20, border: "none", background: currentSlide.showHeading ? GREEN : "#555", color: "#fff", cursor: "pointer", fontSize: 11, fontWeight: 600 }}>
                  {currentSlide.showHeading ? "ON" : "OFF"}
                </button>
                {!currentSlide.showCards ? (
                  <button onClick={function() { updateSlide(activeSlide, "showAccentBar", !currentSlide.showAccentBar, true); }}
                    title="Accent bar"
                    style={{ padding: "2px 6px", borderRadius: 4, border: "1px solid #444", background: (currentSlide.showAccentBar !== false) ? "rgba(165,180,252,0.2)" : "#28283e", color: (currentSlide.showAccentBar !== false) ? "#a5b4fc" : "#666", cursor: "pointer", fontSize: 9, fontWeight: 700, lineHeight: "14px" }}>
                    {"\u2501"}
                  </button>
                ) : (
                  <button onClick={function() { updateSlide(activeSlide, "showCardChecks", !(currentSlide.showCardChecks !== false), true); }}
                    title="Card checkmarks"
                    style={{ padding: "2px 6px", borderRadius: 4, border: "1px solid #444", background: (currentSlide.showCardChecks !== false) ? "rgba(165,180,252,0.2)" : "#28283e", color: (currentSlide.showCardChecks !== false) ? "#a5b4fc" : "#666", cursor: "pointer", fontSize: 9, fontWeight: 700, lineHeight: "14px" }}>
                    {"\u2713"}
                  </button>
                )}
                {currentSlide.showHeading && (
                  <>
                    <div style={{ flex: 1 }} />
                    <SizeControl sizeKey="heading" min={24} max={160} sizes={sizes} setSize={setSize}
                      colorVal={currentSlide.titleColor} colorSet={function(c) { updateSlide(activeSlide, "titleColor", c); }}
                      colorPickerKey={"s-" + activeSlide + "-title"} openPicker={openPicker} setOpenPicker={setOpenPicker}
                      fontFamily={currentSlide.titleFontFamily} fontFamilySet={function(v) { updateSlide(activeSlide, "titleFontFamily", v, true); }}
                      boldVal={currentSlide.titleBold} boldSet={function(v) { updateSlide(activeSlide, "titleBold", v, true); }}
                      italicVal={currentSlide.titleItalic} italicSet={function(v) { updateSlide(activeSlide, "titleItalic", v, true); }} />
                  </>
                )}
              </div>
              {currentSlide.showHeading && (
                <div style={{ marginBottom: 8, paddingLeft: 8, borderLeft: "2px solid #555" }}>
                  <textarea value={currentSlide.title} onChange={function(e) { updateSlide(activeSlide, "title", e.target.value); var el = e.target; el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; }} placeholder="Heading..." rows={1}
                    ref={function(el) { if (el) { el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; } }}
                    style={Object.assign({}, inputStyle, { marginBottom: 4, fontSize: 12, resize: "none", overflow: "hidden", maxHeight: "50vh", overflowY: "auto" })} />
                </div>
              )}

              {/* Body | Cards toggle */}
              <div style={{ display: "flex", alignItems: "center", marginTop: 12, marginBottom: 6, gap: 4 }}>
                <span onClick={function() { updateSlide(activeSlide, "showCards", false); }}
                  style={{ fontWeight: 600, fontSize: 13, color: !currentSlide.showCards ? GREEN : "#555", letterSpacing: 0.5, cursor: "pointer" }}>BODY</span>
                <span style={{ color: "#2a2a3e", margin: "0 4px", fontSize: 14 }}>|</span>
                <span onClick={function() { updateSlide(activeSlide, "showCards", true); }}
                  style={{ fontWeight: 600, fontSize: 13, color: currentSlide.showCards ? GREEN : "#555", letterSpacing: 0.5, cursor: "pointer" }}>CARDS</span>
                <button onClick={function() { updateSlide(activeSlide, "expandScreenshot", !currentSlide.expandScreenshot, true); }}
                  title="Expand screenshot area"
                  style={{ padding: "2px 6px", borderRadius: 4, border: "1px solid #444", background: currentSlide.expandScreenshot ? "rgba(165,180,252,0.2)" : "#28283e", color: currentSlide.expandScreenshot ? "#a5b4fc" : "#666", cursor: "pointer", fontSize: 9, fontWeight: 700, lineHeight: "14px", marginLeft: 6 }}>
                  {"\u2922"}
                </button>
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

              {/* Color swatch row */}
              <div style={{ display: "flex", gap: 16, marginTop: 6, marginBottom: 6, alignItems: "center" }}>
                {/* Text swatch - context-aware: bodyColor in Body mode, cardTextColor in Cards mode */}
                <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                  <ColorPickerInline pickerKey={"s-" + activeSlide + (currentSlide.showCards ? "-cardtext" : "-body")} value={currentSlide.showCards ? (currentSlide.cardTextColor || "#333333") : (currentSlide.bodyColor || "#ffffff")} onChange={function(c) { updateSlide(activeSlide, currentSlide.showCards ? "cardTextColor" : "bodyColor", c); }} openPicker={openPicker} setOpenPicker={setOpenPicker}
                    fontFamily={currentSlide.showCards ? currentSlide.cardFontFamily : currentSlide.bodyFontFamily}
                    onFontFamilyChange={function(v) { updateSlide(activeSlide, currentSlide.showCards ? "cardFontFamily" : "bodyFontFamily", v, true); }}
                    bold={currentSlide.showCards ? currentSlide.cardBold : currentSlide.bodyBold}
                    onBoldChange={function(v) { updateSlide(activeSlide, currentSlide.showCards ? "cardBold" : "bodyBold", v, true); }}
                    italic={currentSlide.showCards ? currentSlide.cardItalic : currentSlide.bodyItalic}
                    onItalicChange={function(v) { updateSlide(activeSlide, currentSlide.showCards ? "cardItalic" : "bodyItalic", v, true); }} />
                  <span style={{ fontSize: 11, color: "#777", fontWeight: 600 }}>Text</span>
                </div>
                {/* Base swatch (card bg) - greyed out in Body mode */}
                <div style={{ display: "flex", alignItems: "center", gap: 4, opacity: currentSlide.showCards ? 1 : 0.35 }}>
                  <ColorPickerInline pickerKey={"s-" + activeSlide + "-cardbg"} value={currentSlide.cardBgColor || "#ffffff"} onChange={function(c) { updateSlide(activeSlide, "cardBgColor", c); }} openPicker={openPicker} setOpenPicker={setOpenPicker} disabled={!currentSlide.showCards} />
                  <span style={{ fontSize: 11, color: "#777", fontWeight: 600 }}>Base</span>
                </div>
              </div>

              {/* Body content */}
              {!currentSlide.showCards && (
                <div>
                  <textarea value={currentSlide.body} onChange={function(e) { updateSlide(activeSlide, "body", e.target.value); var el = e.target; el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; }} rows={1}
                    ref={function(el) { if (el) { el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; } }}
                    style={{ width: "100%", padding: "8px 12px", borderRadius: 8, border: "1px solid #444", background: "#28283e", color: "#fff", fontSize: 13, boxSizing: "border-box", resize: "none", overflow: "hidden", maxHeight: "50vh", overflowY: "auto" }} />
                  <p style={{ fontSize: 11, color: "#555", marginTop: 2, marginBottom: 8 }}>**word** = accent color.</p>
                </div>
              )}

              {/* Cards content */}
              {currentSlide.showCards && (
                <div>
                  {currentSlide.cards.map(function(c, i) {
                    return (
                      <div key={i} style={{ display: "flex", gap: 8, marginBottom: 6, alignItems: "center" }}>
                        <textarea value={c} onChange={function(e) { slideMgmt.updateSlideCard(activeSlide, i, e.target.value); var el = e.target; el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; }} placeholder={"Card " + (i + 1) + "..."} rows={1}
                          ref={function(el) { if (el) { el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; } }}
                          style={{ width: "100%", padding: "6px 10px", borderRadius: 8, border: "1px solid #444", background: "#28283e", color: "#fff", fontSize: 12, boxSizing: "border-box", resize: "none", overflow: "hidden", maxHeight: "50vh", overflowY: "auto" }} />
                        {currentSlide.cards.length > 1 && (
                          <button onClick={function() { slideMgmt.removeSlideCard(activeSlide, i); }} style={{ background: "none", border: "none", color: "#f87171", cursor: "pointer", fontSize: 18, padding: 4 }}>{"\u00d7"}</button>
                        )}
                      </div>
                    );
                  })}
                  {currentSlide.cards.length < 5 && (
                    <button onClick={function() { slideMgmt.addSlideCard(activeSlide); }} style={{ background: "#28283e", border: "1px dashed #444", color: "#888", padding: "5px 12px", borderRadius: 8, cursor: "pointer", fontSize: 12, marginTop: 4 }}>+ Add Card</button>
                  )}
                  <p style={{ fontSize: 11, color: "#555", marginTop: 6, marginBottom: 4 }}>**word** = accent color.</p>
                </div>
              )}
            </div>
          )}

        </div>

          {/* -- RIGHT PANE: Preview -- */}
          <div style={{ flex: "1 1 0", minWidth: 360, position: "sticky", top: 24, alignSelf: "flex-start" }}>
            <p style={{ fontSize: 13, color: "#666", marginBottom: 8, fontWeight: 600, letterSpacing: 1 }}>PREVIEW</p>
            <div style={{ marginBottom: 8 }}>
              <label style={{ fontSize: 10, color: "#666", display: "block", marginBottom: 2 }}>Filename prefix</label>
              <input value={exportPrefix}
                onChange={function(e) { setExportPrefix(e.target.value); }}
                placeholder="linkedin-slide"
                style={{ width: "100%", padding: "6px 8px", borderRadius: 6, border: "1px solid #444", background: "#28283e", color: "#ccc", fontSize: 11, boxSizing: "border-box", fontFamily: "monospace" }} />
            </div>
            <button onClick={downloadCurrentPDF}
              style={{ marginTop: 0, width: "100%", padding: "12px 0", borderRadius: 8, border: "none", background: "#6366f1", color: "#fff", fontSize: 14, fontWeight: 700, cursor: "pointer" }}>
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
            {pdfError && (
              <p style={{ fontSize: 10, color: "#ef4444", marginTop: 4, margin: "4px 0 0 0" }}>{pdfError}</p>
            )}
            <canvas ref={canvasRef} width={W} height={H}
              style={{ width: "100%", height: "auto", borderRadius: 12, border: "1px solid #222", display: "block", marginTop: 10 }} />
            <p style={{ fontSize: 9, color: "#888", marginTop: 2, textAlign: "center" }}>Generated locally in browser; no upload.</p>
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
      {presets.presetDialog && presets.presetDialog.type === "save" && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 9999 }}
          onClick={function() { presets.setPresetDialog(null); }}>
          <div style={{ background: "#1a1a30", border: "1px solid #444", borderRadius: 10, padding: "20px 24px", maxWidth: 360, textAlign: "left", boxShadow: "0 8px 32px rgba(0,0,0,0.6)" }}
            onClick={function(e) { e.stopPropagation(); }}>
            <p style={{ color: "#ccc", fontSize: 14, fontWeight: 600, margin: "0 0 12px 0" }}>Save Preset</p>
            <label style={{ fontSize: 11, color: "#888", display: "block", marginBottom: 4 }}>Preset name</label>
            <input value={presets.presetName} onChange={function(e) { presets.setPresetName(e.target.value); }}
              placeholder="My Carousel"
              style={inputStyle} />
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 12, marginBottom: 16 }}>
              <button onClick={function() { presets.setPresetIncludeImages(!presets.presetIncludeImages); }}
                style={{ minWidth: 44, padding: "3px 12px", borderRadius: 20, border: "none",
                  background: presets.presetIncludeImages ? GREEN : "#555",
                  color: "#fff", cursor: "pointer", fontSize: 11, fontWeight: 600 }}>
                {presets.presetIncludeImages ? "ON" : "OFF"}
              </button>
              <span style={{ fontSize: 12, color: "#999" }}>Include images (larger file)</span>
            </div>
            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
              <button onClick={function() { presets.setPresetDialog(null); }}
                style={{ padding: "6px 18px", borderRadius: 6, border: "1px solid #444", background: "#28283e", color: "#999", cursor: "pointer", fontSize: 12, fontWeight: 600 }}>
                Cancel
              </button>
              <button onClick={function() { presets.downloadPreset(presets.presetName, presets.presetIncludeImages); presets.setPresetDialog(null); }}
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
