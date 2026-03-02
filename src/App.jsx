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
      exportPrefix: exportPrefix
    };
  };

  var restoreSnapshot = function(snap) {
    setSeriesSlides(snap.seriesSlides);
    setSlideAssets(snap.slideAssets);
    setSizes(snap.sizes);
    setActiveSlide(snap.activeSlide);
    setExportPrefix(snap.exportPrefix);
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
  var canvasRenderer = useCanvasRenderer(canvasRef, seriesSlides, slideAssets, sizes, activeSlide);
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
    setSizes: setSizes,
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
    <div style={{ fontFamily: '"Helvetica Neue", Helvetica, Arial, sans-serif', background: "#000000", height: "100vh", overflow: "hidden", color: "#e0e0e0", padding: "28px 48px", boxSizing: "border-box" }}>
      <div style={{ margin: "0 auto", height: "100%", display: "flex", flexDirection: "column" }}>

        <div style={{ display: "flex", gap: 48, flex: 1, minHeight: 0, alignItems: "stretch" }}>

        {/* -- LEFT COLUMN: Presets + Background + Slides -- */}
        <div style={{ flex: "0 0 220px", minWidth: 220, maxWidth: 220, display: "flex", flexDirection: "column" }}>
          {/* Frozen top: Presets */}
          <div style={{ flexShrink: 0 }}>
            <h2 style={{ color: "#fff", margin: "0 0 10px 0", fontSize: 18 }}>Carousel Generator</h2>
            {/* --- PRESETS --- */}
            <div style={{ marginBottom: 6, minHeight: 66 }}>
              <label style={Object.assign({}, labelStyle, { marginBottom: 6 })}>PRESETS</label>
              <div style={{ display: "flex", gap: 4, marginBottom: 4 }}>
                <button onClick={function() { presets.setPresetError(""); presets.setPresetName(exportPrefix || ""); presets.setPresetDialog({ type: "save" }); }}
                  style={{ flex: 1, padding: "5px 8px", borderRadius: 6, border: "1px solid #444", background: "#28283e", color: "#ccc", cursor: "pointer", fontSize: 11, fontWeight: 700 }}>
                  Save
                </button>
                <button onClick={function() { presets.setPresetError(""); if (presets.presetInputRef.current) presets.presetInputRef.current.click(); }}
                  style={{ flex: 1, padding: "5px 8px", borderRadius: 6, border: "1px solid #444", background: "#28283e", color: "#ccc", cursor: "pointer", fontSize: 11, fontWeight: 700 }}>
                  Load
                </button>
                <input ref={presets.presetInputRef} type="file" accept=".json" onChange={presets.handlePresetUpload} style={{ display: "none" }} />
              </div>
              {presets.presetDownload && (
                <div style={{ display: "flex", alignItems: "center", gap: 4, marginTop: 2 }}>
                  <a href={presets.presetDownload.url} download={presets.presetDownload.name}
                    onClick={function() { setTimeout(presets.clearPresetDownload, 1500); }}
                    style={{ fontSize: 10, color: "#a5b4fc", textDecoration: "underline", flex: 1, wordBreak: "break-all" }}>
                    {"Save " + presets.presetDownload.name}
                  </a>
                  <button onClick={presets.clearPresetDownload}
                    style={{ background: "none", border: "none", color: "#999", cursor: "pointer", fontSize: 13, padding: "0 2px", lineHeight: 1 }}>
                    {"\u00d7"}
                  </button>
                </div>
              )}
              {presets.presetError && (
                <div style={{ marginTop: 2, padding: "3px 6px", borderRadius: 6, background: "#3a1a1a", border: "1px solid #7f1d1d", color: "#fca5a5", fontSize: 10, display: "flex", alignItems: "center", gap: 4 }}>
                  <span style={{ flex: 1 }}>{presets.presetError}</span>
                  <button onClick={function() { presets.setPresetError(""); }}
                    style={{ background: "none", border: "none", color: "#fca5a5", cursor: "pointer", fontSize: 13, padding: "0 2px", lineHeight: 1 }}>{"\u00d7"}</button>
                </div>
              )}
            </div>
            <div style={{ borderTop: "1px solid #444", marginTop: 10, marginBottom: 10 }} />

            {/* --- BACKGROUND --- */}
            <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>BACKGROUND</label>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 4, marginBottom: 8 }}>
              <button onClick={slideMgmt.syncBgToAll}
                style={{ padding: "5px 8px", borderRadius: 6, border: "1px solid #444", background: "#28283e", color: "#ccc", cursor: "pointer", fontSize: 11, fontWeight: 700, whiteSpace: "nowrap" }}>
                Sync All
              </button>
              <button onClick={slideMgmt.resetBgToDefault}
                style={{ padding: "5px 8px", borderRadius: 6, border: "1px solid #444", background: "#28283e", color: "#ccc", cursor: "pointer", fontSize: 11, fontWeight: 700 }}>
                Reset
              </button>
              <div />
              <button onClick={slideMgmt.resetAllBgToDefault}
                style={{ padding: "5px 8px", borderRadius: 6, border: "1px solid #444", background: "#28283e", color: "#ccc", cursor: "pointer", fontSize: 11, fontWeight: 700 }}>
                Reset All
              </button>
            </div>
            {/* Toggles + BG upload side by side */}
            <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
              {/* Left: toggle rows */}
              <div style={{ flex: 1, minWidth: 0 }}>
                {/* Accent */}
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 12 }}>
                  <label style={{ fontSize: 11, color: "#999", fontWeight: 600, width: 38 }}>Accent</label>
                  <ColorPickerInline pickerKey="accent" value={currentSlide.accentColor || "#fff"} onChange={function(c) { updateBgField("accentColor", c); }} openPicker={openPicker} setOpenPicker={setOpenPicker} />
                </div>
                {/* Base */}
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 12, opacity: isCustomBg ? 0.35 : 1 }}>
                  <label style={{ fontSize: 11, color: "#999", fontWeight: 600, width: 38 }}>Base</label>
                  <ColorPickerInline pickerKey="solidColor" value={currentSlide.solidColor || "#fff"} onChange={function(c) { updateBgField("solidColor", c); }} openPicker={openPicker} setOpenPicker={setOpenPicker} disabled={isCustomBg} />
                </div>
                {/* Layer */}
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 0, opacity: isCustomBg ? 0.35 : 1 }}>
                  <label style={{ fontSize: 11, color: "#999", fontWeight: 600, width: 38 }}>Layer</label>
                  <button onClick={function() { if (!isCustomBg) updateBgField("geoEnabled", !currentSlide.geoEnabled); }}
                    style={{ minWidth: 32, padding: "1px 5px", borderRadius: 20, border: "none", background: (!isCustomBg && currentSlide.geoEnabled) ? GREEN : "#555", color: "#fff", cursor: isCustomBg ? "default" : "pointer", fontSize: 8, fontWeight: 600 }}>
                    {(!isCustomBg && currentSlide.geoEnabled) ? "ON" : "OFF"}
                  </button>
                  <div style={{ opacity: (isCustomBg || !currentSlide.geoEnabled) ? 0.5 : 1 }}>
                    <ColorPickerInline pickerKey="geoLines" value={currentSlide.geoLines} onChange={function(c) { updateBgField("geoLines", c); }} openPicker={openPicker} setOpenPicker={setOpenPicker} disabled={isCustomBg || !currentSlide.geoEnabled} />
                  </div>
                </div>
              </div>
              {/* Right: BACKGROUND upload */}
              <div style={{ flex: "0 0 107px", height: 88, background: "#0f0f1a", border: "1px solid #343447", borderRadius: 8, padding: "4px 6px", display: "flex", flexDirection: "column", alignItems: "center", boxSizing: "border-box", overflow: "hidden" }}>
                <label style={{ fontSize: 11, color: "#bbb", fontWeight: 600, marginBottom: 3 }}>BACKGROUND</label>
                <span style={{ fontSize: 11, color: "#555", marginBottom: 4 }}>800×1000px</span>
                <input ref={slideMgmt.customBgInputRef} type="file" accept="image/*" onChange={function(e) { slideMgmt.handleCustomUpload(e); }} style={{ display: "none" }} />
                <div style={{ width: "100%", height: 24, borderRadius: 5, border: "1px solid " + (currentSlide.customBgImage ? GREEN : "#444"), background: "#111119", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", gap: 15 }}
                  onClick={function() { if (!isCustomBg) updateBgField("bgType", "custom"); if (slideMgmt.customBgInputRef.current) slideMgmt.customBgInputRef.current.click(); }}>
                  {currentSlide.customBgImage ? (
                    <>
                      <span style={{ fontSize: 11, color: GREEN, lineHeight: 1, fontWeight: 700 }}>{"\u2713"}</span>
                      <button onClick={function(e) { e.stopPropagation(); slideMgmt.removeCustomBg(); }}
                        style={{ background: "none", border: "none", color: "#f87171", cursor: "pointer", fontSize: 14, padding: 0, lineHeight: 1, fontWeight: 700 }}>{"\u00d7"}</button>
                    </>
                  ) : (
                    <span style={{ fontSize: 9, color: "#ccc", fontWeight: 600 }}>Upload</span>
                  )}
                </div>
                {currentSlide.customBgName && (
                  <span style={{ fontSize: 11, color: "#666", marginTop: 3, maxWidth: "100%", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", display: "block", textAlign: "center" }}>{currentSlide.customBgName}</span>
                )}
              </div>
            </div>

            {/* Profile + Screenshot side by side */}
            <div style={{ display: "flex", gap: 6, marginBottom: 10 }}>
              {/* PROFILE */}
              <div style={{ flex: 1, minWidth: 0, height: 88, background: "#0f0f1a", border: "1px solid #343447", borderRadius: 8, padding: "4px 8px", display: "flex", flexDirection: "column", alignItems: "center", boxSizing: "border-box", overflow: "hidden" }}>
                <label style={{ fontSize: 11, color: "#bbb", fontWeight: 600, marginBottom: 3 }}>PROFILE</label>
                <span style={{ fontSize: 11, color: "#555", marginBottom: 4 }}>84×84px</span>
                <input ref={slideMgmt.profilePicInputRef} type="file" accept="image/*" onChange={slideMgmt.handleProfilePicUpload} style={{ display: "none" }} />
                <div style={{ width: "100%", height: 24, borderRadius: 5, border: "1px solid " + (currentSlide.profileImg ? GREEN : "#444"), background: "#111119", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", gap: 15 }}
                  onClick={function() { if (slideMgmt.profilePicInputRef.current) slideMgmt.profilePicInputRef.current.click(); }}>
                  {currentSlide.profileImg ? (
                    <>
                      <span style={{ fontSize: 11, color: GREEN, lineHeight: 1, fontWeight: 700 }}>{"\u2713"}</span>
                      <button onClick={function(e) { e.stopPropagation(); slideMgmt.removeProfilePic(); }}
                        style={{ background: "none", border: "none", color: "#f87171", cursor: "pointer", fontSize: 14, padding: 0, lineHeight: 1, fontWeight: 700 }}>{"\u00d7"}</button>
                    </>
                  ) : (
                    <span style={{ fontSize: 9, color: "#ccc", fontWeight: 600 }}>Upload</span>
                  )}
                </div>
                {currentSlide.profilePicName && (
                  <span style={{ fontSize: 11, color: "#666", marginTop: 3, maxWidth: "100%", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", display: "block", textAlign: "center" }}>{currentSlide.profilePicName}</span>
                )}
              </div>
              {/* SCREENSHOT */}
              {currentSlide && (
                <div style={{ flex: 1, minWidth: 0, height: 88, background: "#0f0f1a", border: "1px solid #343447", borderRadius: 8, padding: "4px 8px", display: "flex", flexDirection: "column", alignItems: "center", boxSizing: "border-box", overflow: "hidden" }}>
                  <label style={{ fontSize: 11, color: "#bbb", fontWeight: 600, marginBottom: 3 }}>SCREENSHOT</label>
                  <input ref={slideMgmt.screenshotInputRef} type="file" accept="image/*" onChange={function(e) { slideMgmt.handleScreenshotUpload(activeSlide, e); }} style={{ display: "none" }} />
                  <div style={{ width: "100%", height: 24, borderRadius: 5, border: "1px solid " + (getAsset(activeSlide).image ? GREEN : "#444"), background: "#111119", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", gap: 15 }}
                    onClick={function() { if (slideMgmt.screenshotInputRef.current) slideMgmt.screenshotInputRef.current.click(); }}>
                    {getAsset(activeSlide).image ? (
                      <>
                        <span style={{ fontSize: 11, color: GREEN, lineHeight: 1, fontWeight: 700 }}>{"\u2713"}</span>
                        <button onClick={function(e) { e.stopPropagation(); slideMgmt.removeScreenshot(activeSlide); }}
                          style={{ background: "none", border: "none", color: "#f87171", cursor: "pointer", fontSize: 14, padding: 0, lineHeight: 1, fontWeight: 700 }}>{"\u00d7"}</button>
                      </>
                    ) : (
                      <span style={{ fontSize: 9, color: "#ccc", fontWeight: 600 }}>Upload</span>
                    )}
                  </div>
                  {getAsset(activeSlide).name && (
                    <span style={{ fontSize: 11, color: "#666", marginTop: 3, maxWidth: "100%", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", display: "block", textAlign: "center" }}>{getAsset(activeSlide).name}</span>
                  )}
                  {getAsset(activeSlide).image && (
                    <div style={{ display: "flex", alignItems: "center", gap: 2, marginTop: 2, width: "100%" }}>
                      <input type="range" min={50} max={200} value={Math.round(getAsset(activeSlide).scale * 100)} onChange={function(e) { setScale(activeSlide, Number(e.target.value) / 100); }}
                        style={{ flex: 1, minWidth: 0 }} />
                      <span style={{ fontSize: 7, color: "#777", minWidth: 20, textAlign: "right" }}>{Math.round(getAsset(activeSlide).scale * 100) + "%"}</span>
                    </div>
                  )}
                </div>
              )}
            </div>

            <div style={{ borderTop: "1px solid #444", marginTop: 10, marginBottom: 10 }} />
            <div style={{ marginBottom: 10 }}>
              <button onClick={slideMgmt.duplicateSlide}
                style={{ width: "100%", padding: "6px 8px", borderRadius: 8, border: "1px solid #444", background: "#28283e", color: "#ccc", cursor: seriesSlides.length >= MAX_SLIDES ? "default" : "pointer", fontSize: 10, fontWeight: 700, opacity: seriesSlides.length >= MAX_SLIDES ? 0.4 : 1, textAlign: "center" }}>
                Duplicate Slide
              </button>
            </div>
          </div>
          {/* Scrollable bottom: Slides list */}
          <div style={{ flex: 1, overflowY: "auto", minHeight: 0 }}>
            <div style={{ background: "#10101a", border: "1px solid #343447", borderRadius: 10, padding: 12 }}>
              <SlideSelector seriesSlides={seriesSlides} activeSlide={activeSlide} setActiveSlide={setActiveSlide}
                dragFrom={slideMgmt.dragFrom} setDragFrom={slideMgmt.setDragFrom} dragOver={slideMgmt.dragOver} setDragOver={slideMgmt.setDragOver}
                reorderSlide={slideMgmt.reorderSlide} addSlide={slideMgmt.addSlide} duplicateSlide={slideMgmt.duplicateSlide}
                removeSlide={slideMgmt.removeSlide} />
            </div>
          </div>
        </div>

        {/* -- CENTER PANE: Slide Editor -- */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>

          {/* Scrollable: Slide Editor */}
          <div style={{ flex: 1, overflowY: "auto", minHeight: 0 }}>

          {/* --- SLIDE EDITOR --- */}
          {currentSlide && (
            <div style={{ background: "#1a1a30", borderRadius: 10, padding: 14, border: "1px solid #3a3a50", marginBottom: 14 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                <span style={{ color: "#888", fontSize: 14, fontWeight: 700 }}>
                  {"SLIDE " + (activeSlide + 1)}
                </span>
                <span style={{ fontSize: 10, color: "#666", marginLeft: 16, marginRight: 4 }}>Expand</span>
                <button onClick={function() { updateSlide(activeSlide, "expandScreenshot", !currentSlide.expandScreenshot, true); }}
                  title="Expand screenshot area"
                  style={{ padding: "3px 8px", borderRadius: 4, border: "1px solid #444", background: currentSlide.expandScreenshot ? "rgba(165,180,252,0.2)" : "#28283e", color: currentSlide.expandScreenshot ? "#a5b4fc" : "#666", cursor: "pointer", fontSize: 11, fontWeight: 700, lineHeight: "16px" }}>
                  {"\u2922"}
                </button>
                <span style={{ fontSize: 10, color: "#555", marginLeft: 14 }}>**word** = accent color</span>
                <div style={{ flex: 1 }} />
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

              {/* -- Frame toggle (per-slide) -- */}
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4, marginTop: 4 }}>
                <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>FRAME</label>
                <button onClick={function() { updateBgField("frameEnabled", !currentSlide.frameEnabled); }}
                  style={{ minWidth: 44, padding: "3px 12px", borderRadius: 20, border: "none", background: currentSlide.frameEnabled ? GREEN : "#555", color: "#fff", cursor: "pointer", fontSize: 11, fontWeight: 600 }}>
                  {currentSlide.frameEnabled ? "ON" : "OFF"}
                </button>
                {currentSlide.frameEnabled && (
                  <div style={{ display: "flex", alignItems: "center", gap: 4, marginLeft: 4 }}>
                    <ColorPickerInline pickerKey="border" value={currentSlide.borderColor || "#fff"} onChange={function(c) { updateBgField("borderColor", c); }} openPicker={openPicker} setOpenPicker={setOpenPicker} opacityVal={currentSlide.borderOpacity} onOpacityChange={function(v) { updateBgField("borderOpacity", v); }} />
                  </div>
                )}
              </div>

              <div style={{ borderTop: "1px solid #2a2a40", marginTop: 8, marginBottom: 8 }} />

              {/* -- Footer & Pic toggle (per-slide) -- */}
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4, marginTop: 4 }}>
                <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>FOOTER & PIC</label>
                <button onClick={function() { updateSlide(activeSlide, "showBrandName", !currentSlide.showBrandName); }}
                  style={{ minWidth: 44, padding: "3px 12px", borderRadius: 20, border: "none", background: currentSlide.showBrandName ? GREEN : "#555", color: "#fff", cursor: "pointer", fontSize: 11, fontWeight: 600 }}>
                  {currentSlide.showBrandName ? "ON" : "OFF"}
                </button>
                {currentSlide.showBrandName && (
                  <>
                    <div style={{ display: "flex", alignItems: "center", gap: 4, marginLeft: 4 }}>
                      <ColorPickerInline pickerKey={"s-" + activeSlide + "-footerBase"} value={currentSlide.footerBg || "#ffffff"} onChange={function(c) { updateSlide(activeSlide, "footerBg", c); }} openPicker={openPicker} setOpenPicker={setOpenPicker} />
                      <span style={{ fontSize: 11, color: "#777", fontWeight: 600 }}>Base</span>
                    </div>
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
              <div style={{ borderTop: "1px solid #2a2a40", marginTop: 8, marginBottom: 8 }} />
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
              <div style={{ borderTop: "1px solid #2a2a40", marginTop: 8, marginBottom: 8 }} />
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
              <div style={{ borderTop: "1px solid #2a2a40", marginTop: 8, marginBottom: 8 }} />
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4, marginTop: 4 }}>
                <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>HEADING</label>
                <button onClick={function() { updateSlide(activeSlide, "showHeading", !currentSlide.showHeading); }}
                  style={{ minWidth: 44, padding: "3px 12px", borderRadius: 20, border: "none", background: currentSlide.showHeading ? GREEN : "#555", color: "#fff", cursor: "pointer", fontSize: 11, fontWeight: 600 }}>
                  {currentSlide.showHeading ? "ON" : "OFF"}
                </button>
                {!currentSlide.showCards ? (
                  <button onClick={function() { if (currentSlide.showHeading) updateSlide(activeSlide, "showAccentBar", !currentSlide.showAccentBar, true); }}
                    title="Accent bar"
                    style={{ padding: "2px 6px", borderRadius: 4, border: "1px solid #444", background: (currentSlide.showHeading && currentSlide.showAccentBar !== false) ? "rgba(165,180,252,0.2)" : "#28283e", color: (currentSlide.showHeading && currentSlide.showAccentBar !== false) ? "#a5b4fc" : "#666", cursor: currentSlide.showHeading ? "pointer" : "default", fontSize: 9, fontWeight: 700, lineHeight: "14px", opacity: currentSlide.showHeading ? 1 : 0.35 }}>
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
              <div style={{ borderTop: "1px solid #2a2a40", marginTop: 8, marginBottom: 8 }} />
              <div style={{ display: "flex", alignItems: "center", marginTop: 4, marginBottom: 6, gap: 4 }}>
                <span onClick={function() { updateSlide(activeSlide, "showCards", false); }}
                  style={{ fontWeight: 600, fontSize: 13, color: !currentSlide.showCards ? GREEN : "#555", letterSpacing: 0.5, cursor: "pointer" }}>BODY</span>
                <span style={{ color: "#2a2a3e", margin: "0 4px", fontSize: 14 }}>|</span>
                <span onClick={function() { updateSlide(activeSlide, "showCards", true); }}
                  style={{ fontWeight: 600, fontSize: 13, color: currentSlide.showCards ? GREEN : "#555", letterSpacing: 0.5, cursor: "pointer" }}>CARDS</span>
                <div style={{ display: "flex", alignItems: "center", gap: 4, marginLeft: 4, opacity: currentSlide.showCards ? 1 : 0.35 }}>
                  <ColorPickerInline pickerKey={"s-" + activeSlide + "-cardbg"} value={currentSlide.cardBgColor || "#ffffff"} onChange={function(c) { updateSlide(activeSlide, "cardBgColor", c); }} openPicker={openPicker} setOpenPicker={setOpenPicker} disabled={!currentSlide.showCards} />
                  <span style={{ fontSize: 11, color: "#777", fontWeight: 600 }}>Base</span>
                </div>
                <div style={{ flex: 1 }} />
                <SizeControl sizeKey={currentSlide.showCards ? "cardText" : "body"} min={12} max={100} sizes={sizes} setSize={setSize}
                  colorVal={currentSlide.showCards ? (currentSlide.cardTextColor || "#333333") : (currentSlide.bodyColor || "#ffffff")}
                  colorSet={function(c) { updateSlide(activeSlide, currentSlide.showCards ? "cardTextColor" : "bodyColor", c); }}
                  colorPickerKey={"s-" + activeSlide + (currentSlide.showCards ? "-cardtext" : "-body")} openPicker={openPicker} setOpenPicker={setOpenPicker}
                  fontFamily={currentSlide.showCards ? currentSlide.cardFontFamily : currentSlide.bodyFontFamily}
                  fontFamilySet={function(v) { updateSlide(activeSlide, currentSlide.showCards ? "cardFontFamily" : "bodyFontFamily", v, true); }}
                  boldVal={currentSlide.showCards ? currentSlide.cardBold : currentSlide.bodyBold}
                  boldSet={function(v) { updateSlide(activeSlide, currentSlide.showCards ? "cardBold" : "bodyBold", v, true); }}
                  italicVal={currentSlide.showCards ? currentSlide.cardItalic : currentSlide.bodyItalic}
                  italicSet={function(v) { updateSlide(activeSlide, currentSlide.showCards ? "cardItalic" : "bodyItalic", v, true); }} />
              </div>

              {/* Body content */}
              {!currentSlide.showCards && (
                <div>
                  <textarea value={currentSlide.body} onChange={function(e) { updateSlide(activeSlide, "body", e.target.value); var el = e.target; el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; }} rows={3}
                    ref={function(el) { if (el) { el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; } }}
                    style={{ width: "100%", padding: "8px 12px", borderRadius: 8, border: "1px solid #444", background: "#28283e", color: "#fff", fontSize: 13, boxSizing: "border-box", resize: "none", overflow: "hidden", maxHeight: "50vh", overflowY: "auto" }} />
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
                </div>
              )}
            </div>
          )}

          </div>
        </div>

          {/* -- RIGHT PANE: Preview header row + filename + canvas -- */}
          <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0, minHeight: 0, maxWidth: 480 }}>
            {/* PREVIEW label */}
            <label style={Object.assign({}, labelStyle, { marginBottom: 6, whiteSpace: "nowrap", flexShrink: 0 })}>PREVIEW</label>
            {/* Download buttons row */}
            <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
              <button onClick={downloadCurrentPDF}
                style={{ flex: 1, padding: "5px 10px", borderRadius: 6, border: "none", background: "#6366f1", color: "#fff", fontSize: 11, fontWeight: 700, cursor: "pointer", whiteSpace: "nowrap", lineHeight: 1.3 }}>
                {"Download Current Slide (pdf)"}
              </button>
              <button onClick={downloadAllPDF}
                disabled={seriesSlides.length <= 1}
                style={{ flex: 1, padding: "5px 10px", borderRadius: 6, border: "2px solid " + GREEN, background: "transparent", color: GREEN, fontSize: 11, fontWeight: 700, cursor: seriesSlides.length > 1 ? "pointer" : "default", opacity: seriesSlides.length > 1 ? 1 : 0.4, whiteSpace: "nowrap", lineHeight: 1.3 }}>
                {"Download All Slides (pdf)"}
              </button>
            </div>
            {/* Download link + error row (below buttons, positioned under the pressed button) */}
            <div style={{ display: "flex", gap: 8, minHeight: 18, marginBottom: 8, flexShrink: 0 }}>
              <div style={{ flex: 1 }}>
                {pdfDownload && !pdfDownload.name.includes("-all.") && (
                  <div style={{ display: "flex", alignItems: "center", gap: 4, marginTop: 2 }}>
                    <a href={pdfDownload.url} download={pdfDownload.name}
                      onClick={function() { setTimeout(clearPdfDownload, 1500); }}
                      style={{ fontSize: 10, color: "#a5b4fc", textDecoration: "underline", flex: 1, wordBreak: "break-all" }}>
                      {"Save " + pdfDownload.name}
                    </a>
                    <button onClick={clearPdfDownload}
                      style={{ background: "none", border: "none", color: "#999", cursor: "pointer", fontSize: 13, padding: "0 2px", lineHeight: 1 }}>
                      {"\u00d7"}
                    </button>
                  </div>
                )}
                {pdfError && !pdfDownload && (
                  <span style={{ fontSize: 10, color: "#ef4444", marginTop: 2, display: "block" }}>{pdfError}</span>
                )}
              </div>
              <div style={{ flex: 1 }}>
                {pdfDownload && pdfDownload.name.includes("-all.") && (
                  <div style={{ display: "flex", alignItems: "center", gap: 4, marginTop: 2 }}>
                    <a href={pdfDownload.url} download={pdfDownload.name}
                      onClick={function() { setTimeout(clearPdfDownload, 1500); }}
                      style={{ fontSize: 10, color: "#a5b4fc", textDecoration: "underline", flex: 1, wordBreak: "break-all" }}>
                      {"Save " + pdfDownload.name}
                    </a>
                    <button onClick={clearPdfDownload}
                      style={{ background: "none", border: "none", color: "#999", cursor: "pointer", fontSize: 13, padding: "0 2px", lineHeight: 1 }}>
                      {"\u00d7"}
                    </button>
                  </div>
                )}
              </div>
            </div>
            {/* Filename input */}
            <input value={exportPrefix}
              onChange={function(e) { setExportPrefix(e.target.value); }}
              placeholder="linkedin-slide"
              style={{ width: "100%", padding: "5px 10px", borderRadius: 6, border: "1px solid #444", background: "#28283e", color: "#ccc", fontSize: 11, boxSizing: "border-box", fontFamily: "monospace", marginBottom: 8, flexShrink: 0 }} />
            {/* Canvas */}
            <canvas ref={canvasRef} width={W} height={H}
              style={{ maxWidth: "100%", minHeight: 0, flex: "0 1 auto", borderRadius: 12, border: "1px solid #222", display: "block", objectFit: "contain", aspectRatio: W + "/" + H }} />
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
