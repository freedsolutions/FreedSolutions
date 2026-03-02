// ---------------------------------------
// Main Component
// ---------------------------------------

// Hoisted styles (module-scope to avoid per-render allocations)
var inputStyle = { width: "100%", padding: SPACE[4] + "px " + SPACE[6] + "px", borderRadius: RADIUS.lg, border: "1px solid " + SURFACE.border, background: SURFACE.input, color: SURFACE.white, fontSize: 14, boxSizing: "border-box" };
var labelStyle = { display: "block", marginBottom: SPACE[3], fontWeight: 600, fontSize: 13, color: SURFACE.label, letterSpacing: 0.5 };
var INLINE_SWATCHES = ["#ffffff", "#1a1a2e", "#333333", "#22c55e", "#a5b4fc", "#f59e0b", "#fb7185", "#22d3ee", "#a78bfa", "#38bdf8", "#d97706", "#fef3c7", "#e0f2fe", "#e0e7ff", "#f0fdf4", "#9ca3af"];
var smallBtnStyle = { padding: SPACE[1] + "px " + SPACE[4] + "px", borderRadius: RADIUS.sm, border: "1px solid " + SURFACE.border, background: SURFACE.input, color: SURFACE.text, cursor: "pointer", fontSize: 9, fontWeight: 600 };
var pickerDropdownStyle = { position: "absolute", top: "100%", left: 0, zIndex: Z.dropdown, marginTop: SPACE[2], background: SURFACE.panel, border: "1px solid " + SURFACE.border, borderRadius: RADIUS.xl, padding: SPACE[5], width: SIZE.pickerWidth, boxShadow: CLR.shadow };

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
    <div style={{ fontFamily: '"Helvetica Neue", Helvetica, Arial, sans-serif', background: SURFACE.page, height: "100vh", overflow: "hidden", color: SURFACE.body, padding: SIZE.pagePadV + "px " + SIZE.pagePadH + "px", boxSizing: "border-box" }}>
      <div style={{ margin: "0 auto", height: "100%", display: "flex", flexDirection: "column" }}>

        <div style={{ display: "grid", gridTemplateColumns: SIZE.leftPane + "px 1fr minmax(0," + SIZE.rightPaneMax + "px)", gridTemplateAreas: '"sidebar editor preview"', gap: SIZE.columnGap, flex: 1, minHeight: 0 }}>

        {/* -- LEFT COLUMN: Presets + Background + Slides -- */}
        <div style={{ gridArea: "sidebar", display: "flex", flexDirection: "column" }}>
          {/* Frozen top: Presets */}
          <div style={{ flexShrink: 0 }}>
            <h2 style={{ color: SURFACE.white, margin: "0 0 " + SPACE[5] + "px 0", fontSize: 18 }}>Carousel Generator</h2>
            {/* --- DOWNLOAD --- */}
            <div style={{ marginBottom: SPACE[3] }}>
              <label style={Object.assign({}, labelStyle, { marginBottom: SPACE[3], whiteSpace: "nowrap" })}>DOWNLOAD</label>
              <div style={{ display: "flex", alignItems: "center", gap: SPACE[4] }}>
                <button onClick={downloadCurrentPDF}
                  style={{ flex: 1, padding: SPACE[3] + "px " + SPACE[5] + "px", borderRadius: RADIUS.md, border: "none", background: CLR.primary, color: SURFACE.white, fontSize: 11, fontWeight: 700, cursor: "pointer", whiteSpace: "nowrap", lineHeight: 1.3 }}>
                  {"Current Slide"}
                </button>
                <button onClick={downloadAllPDF}
                  disabled={seriesSlides.length <= 1}
                  style={{ flex: 1, padding: SPACE[3] + "px " + SPACE[5] + "px", borderRadius: RADIUS.md, border: "2px solid " + GREEN, background: "transparent", color: GREEN, fontSize: 11, fontWeight: 700, cursor: seriesSlides.length > 1 ? "pointer" : "default", opacity: seriesSlides.length > 1 ? 1 : 0.4, whiteSpace: "nowrap", lineHeight: 1.3 }}>
                  {"All Slides"}
                </button>
              </div>
              <div style={{ display: "flex", gap: SPACE[4], minHeight: 18 }}>
                <div style={{ flex: 1 }}>
                  {pdfDownload && !pdfDownload.name.includes("-all.") && (
                    <div style={{ display: "flex", alignItems: "center", gap: SPACE[2], marginTop: SPACE[1] }}>
                      <a href={pdfDownload.url} download={pdfDownload.name}
                        onClick={function() { setTimeout(clearPdfDownload, 1500); }}
                        style={{ fontSize: 10, color: CLR.primaryLight, textDecoration: "underline", flex: 1, wordBreak: "break-all" }}>
                        {"Save " + pdfDownload.name}
                      </a>
                      <button onClick={clearPdfDownload}
                        style={{ background: "none", border: "none", color: SURFACE.subtle, cursor: "pointer", fontSize: 13, padding: "0 " + SPACE[1] + "px", lineHeight: 1 }}>
                        {"\u00d7"}
                      </button>
                    </div>
                  )}
                  {pdfError && !pdfDownload && (
                    <span style={{ fontSize: 10, color: CLR.error, marginTop: SPACE[1], display: "block" }}>{pdfError}</span>
                  )}
                </div>
                <div style={{ flex: 1 }}>
                  {pdfDownload && pdfDownload.name.includes("-all.") && (
                    <div style={{ display: "flex", alignItems: "center", gap: SPACE[2], marginTop: SPACE[1] }}>
                      <a href={pdfDownload.url} download={pdfDownload.name}
                        onClick={function() { setTimeout(clearPdfDownload, 1500); }}
                        style={{ fontSize: 10, color: CLR.primaryLight, textDecoration: "underline", flex: 1, wordBreak: "break-all" }}>
                        {"Save " + pdfDownload.name}
                      </a>
                      <button onClick={clearPdfDownload}
                        style={{ background: "none", border: "none", color: SURFACE.subtle, cursor: "pointer", fontSize: 13, padding: "0 " + SPACE[1] + "px", lineHeight: 1 }}>
                        {"\u00d7"}
                      </button>
                    </div>
                  )}
                </div>
              </div>
              <input value={exportPrefix}
                onChange={function(e) { setExportPrefix(e.target.value); }}
                placeholder="linkedin-slide"
                style={{ width: "100%", padding: SPACE[3] + "px " + SPACE[5] + "px", borderRadius: RADIUS.md, border: "1px solid " + SURFACE.border, background: SURFACE.input, color: SURFACE.text, fontSize: 11, boxSizing: "border-box", fontFamily: "monospace" }} />
            </div>
            <div style={dividerStyle()} />
            {/* --- PRESETS --- */}
            <div style={{ marginBottom: SPACE[3], minHeight: 36 }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr auto auto", gap: SPACE[2], alignItems: "center", marginBottom: SPACE[2] }}>
                <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>PRESETS</label>
                <button onClick={function() { presets.setPresetError(""); presets.setPresetName(exportPrefix || ""); presets.setPresetDialog({ type: "save" }); }}
                  style={panelBtn()}>
                  Save
                </button>
                <button onClick={function() { presets.setPresetError(""); if (presets.presetInputRef.current) presets.presetInputRef.current.click(); }}
                  style={panelBtn()}>
                  Load
                </button>
                <input ref={presets.presetInputRef} type="file" accept=".json" onChange={presets.handlePresetUpload} style={{ display: "none" }} />
              </div>
              {presets.presetDownload && (
                <div style={{ display: "flex", alignItems: "center", gap: SPACE[2], marginTop: SPACE[1] }}>
                  <a href={presets.presetDownload.url} download={presets.presetDownload.name}
                    onClick={function() { setTimeout(presets.clearPresetDownload, 1500); }}
                    style={{ fontSize: 10, color: CLR.primaryLight, textDecoration: "underline", flex: 1, wordBreak: "break-all" }}>
                    {"Save " + presets.presetDownload.name}
                  </a>
                  <button onClick={presets.clearPresetDownload}
                    style={{ background: "none", border: "none", color: SURFACE.subtle, cursor: "pointer", fontSize: 13, padding: "0 " + SPACE[1] + "px", lineHeight: 1 }}>
                    {"\u00d7"}
                  </button>
                </div>
              )}
              {presets.presetError && (
                <div style={{ marginTop: SPACE[1], padding: "3px " + SPACE[3] + "px", borderRadius: RADIUS.md, background: CLR.errorBg, border: "1px solid " + CLR.errorBorder, color: CLR.errorLight, fontSize: 10, display: "flex", alignItems: "center", gap: SPACE[2] }}>
                  <span style={{ flex: 1 }}>{presets.presetError}</span>
                  <button onClick={function() { presets.setPresetError(""); }}
                    style={{ background: "none", border: "none", color: CLR.errorLight, cursor: "pointer", fontSize: 13, padding: "0 " + SPACE[1] + "px", lineHeight: 1 }}>{"\u00d7"}</button>
                </div>
              )}
            </div>
            <div style={{ borderTop: "1px solid " + SURFACE.border, marginTop: SPACE[5], marginBottom: SPACE[5] }} />

            {/* --- BACKGROUND --- */}
            <div style={{ marginBottom: SPACE[7] }}>
              <label style={Object.assign({}, labelStyle, { marginBottom: SPACE[4] })}>BACKGROUND</label>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: SPACE[2] }}>
                <button onClick={slideMgmt.resetBgToDefault} style={panelBtn()}>Reset</button>
                <button onClick={slideMgmt.syncBgToAll} style={panelBtn({ whiteSpace: "nowrap" })}>Sync All</button>
                <button onClick={slideMgmt.resetAllBgToDefault} style={panelBtn()}>Reset All</button>
              </div>
            </div>
            {/* Toggles + BG upload side by side */}
            <div style={{ display: "flex", gap: SPACE[4], marginBottom: SPACE[5] }}>
              {/* Left: toggle rows */}
              <div style={{ flex: 1, minWidth: 0 }}>
                {/* Accent */}
                <div style={{ display: "flex", alignItems: "center", gap: SPACE[5], marginBottom: SPACE[6] }}>
                  <label style={{ fontSize: 14, color: SURFACE.subtle, fontWeight: 600, width: 50 }}>Accent</label>
                  <ColorPickerInline pickerKey="accent" value={currentSlide.accentColor || "#fff"} onChange={function(c) { updateBgField("accentColor", c); }} openPicker={openPicker} setOpenPicker={setOpenPicker} />
                </div>
                {/* Base */}
                <div style={{ display: "flex", alignItems: "center", gap: SPACE[5], marginBottom: SPACE[6], opacity: isCustomBg ? 0.35 : 1 }}>
                  <label style={{ fontSize: 14, color: SURFACE.subtle, fontWeight: 600, width: 50 }}>Base</label>
                  <ColorPickerInline pickerKey="solidColor" value={currentSlide.solidColor || "#fff"} onChange={function(c) { updateBgField("solidColor", c); }} openPicker={openPicker} setOpenPicker={setOpenPicker} disabled={isCustomBg} />
                </div>
                {/* Layer */}
                <div style={{ display: "flex", alignItems: "center", gap: SPACE[5], marginBottom: SPACE[2], opacity: isCustomBg ? 0.35 : 1 }}>
                  <label style={{ fontSize: 14, color: SURFACE.subtle, fontWeight: 600, width: 50 }}>Layer</label>
                  <button onClick={function() { if (!isCustomBg) updateBgField("geoEnabled", !currentSlide.geoEnabled); }}
                    style={toggleBtn(!isCustomBg && currentSlide.geoEnabled, { minWidth: SIZE.toggleSm, padding: "1px 5px", fontSize: 8, cursor: isCustomBg ? "default" : "pointer" })}>
                    {(!isCustomBg && currentSlide.geoEnabled) ? "ON" : "OFF"}
                  </button>
                  <div style={{ opacity: (isCustomBg || !currentSlide.geoEnabled) ? 0.5 : 1 }}>
                    <ColorPickerInline pickerKey="geoLines" value={currentSlide.geoLines} onChange={function(c) { updateBgField("geoLines", c); }} openPicker={openPicker} setOpenPicker={setOpenPicker} disabled={isCustomBg || !currentSlide.geoEnabled} />
                  </div>
                </div>
              </div>
              {/* Right: BACKGROUND upload */}
              <div style={uploadFrameStyle({ flex: "0 0 " + SIZE.uploadBgWidth + "px", padding: SPACE[2] + "px " + SPACE[3] + "px" })}>
                <label style={{ fontSize: 11, color: SURFACE.label, fontWeight: 600, marginBottom: 3 }}>BACKGROUND</label>
                <span style={{ fontSize: 11, color: SURFACE.muted, marginBottom: SPACE[2] }}>800×1000px</span>
                <input ref={slideMgmt.customBgInputRef} type="file" accept="image/*" onChange={function(e) { slideMgmt.handleCustomUpload(e); }} style={{ display: "none" }} />
                <div style={uploadBtnStyle(currentSlide.customBgImage)}
                  onClick={function() { if (!isCustomBg) updateBgField("bgType", "custom"); if (slideMgmt.customBgInputRef.current) slideMgmt.customBgInputRef.current.click(); }}>
                  {currentSlide.customBgImage ? (
                    <>
                      <span style={{ fontSize: 11, color: GREEN, lineHeight: 1, fontWeight: 700 }}>{"\u2713"}</span>
                      <button onClick={function(e) { e.stopPropagation(); slideMgmt.removeCustomBg(); }}
                        style={{ background: "none", border: "none", color: CLR.danger, cursor: "pointer", fontSize: 14, padding: 0, lineHeight: 1, fontWeight: 700 }}>{"\u00d7"}</button>
                    </>
                  ) : (
                    <span style={{ fontSize: 9, color: SURFACE.text, fontWeight: 600 }}>Upload</span>
                  )}
                </div>
                {currentSlide.customBgName && (
                  <span style={{ fontSize: 11, color: SURFACE.dimmed, marginTop: 3, maxWidth: "100%", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", display: "block", textAlign: "center" }}>{currentSlide.customBgName}</span>
                )}
              </div>
            </div>

            {/* Profile + Screenshot side by side */}
            <div style={{ display: "flex", gap: SPACE[3], marginBottom: SPACE[5] }}>
              {/* PROFILE */}
              <div style={uploadFrameStyle({ flex: 1, minWidth: 0 })}>
                <label style={{ fontSize: 11, color: SURFACE.label, fontWeight: 600, marginBottom: 3 }}>PROFILE</label>
                <span style={{ fontSize: 11, color: SURFACE.muted, marginBottom: SPACE[2] }}>84×84px</span>
                <input ref={slideMgmt.profilePicInputRef} type="file" accept="image/*" onChange={slideMgmt.handleProfilePicUpload} style={{ display: "none" }} />
                <div style={uploadBtnStyle(currentSlide.profileImg)}
                  onClick={function() { if (slideMgmt.profilePicInputRef.current) slideMgmt.profilePicInputRef.current.click(); }}>
                  {currentSlide.profileImg ? (
                    <>
                      <span style={{ fontSize: 11, color: GREEN, lineHeight: 1, fontWeight: 700 }}>{"\u2713"}</span>
                      <button onClick={function(e) { e.stopPropagation(); slideMgmt.removeProfilePic(); }}
                        style={{ background: "none", border: "none", color: CLR.danger, cursor: "pointer", fontSize: 14, padding: 0, lineHeight: 1, fontWeight: 700 }}>{"\u00d7"}</button>
                    </>
                  ) : (
                    <span style={{ fontSize: 9, color: SURFACE.text, fontWeight: 600 }}>Upload</span>
                  )}
                </div>
                {currentSlide.profilePicName && (
                  <span style={{ fontSize: 11, color: SURFACE.dimmed, marginTop: 3, maxWidth: "100%", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", display: "block", textAlign: "center" }}>{currentSlide.profilePicName}</span>
                )}
              </div>
              {/* SCREENSHOT */}
              {currentSlide && (
                <div style={uploadFrameStyle({ flex: 1, minWidth: 0 })}>
                  <label style={{ fontSize: 11, color: SURFACE.label, fontWeight: 600, marginBottom: 3 }}>SCREENSHOT</label>
                  <input ref={slideMgmt.screenshotInputRef} type="file" accept="image/*" onChange={function(e) { slideMgmt.handleScreenshotUpload(activeSlide, e); }} style={{ display: "none" }} />
                  <div style={{ display: "flex", alignItems: "center", gap: SPACE[3] }}>
                    <div style={Object.assign({}, uploadBtnStyle(getAsset(activeSlide).image), { flex: 1, minWidth: 0 })}
                      onClick={function() { if (slideMgmt.screenshotInputRef.current) slideMgmt.screenshotInputRef.current.click(); }}>
                      {getAsset(activeSlide).image ? (
                        <>
                          <span style={{ fontSize: 11, color: GREEN, lineHeight: 1, fontWeight: 700 }}>{"\u2713"}</span>
                          <button onClick={function(e) { e.stopPropagation(); slideMgmt.removeScreenshot(activeSlide); }}
                            style={{ background: "none", border: "none", color: CLR.danger, cursor: "pointer", fontSize: 14, padding: 0, lineHeight: 1, fontWeight: 700 }}>{"\u00d7"}</button>
                        </>
                      ) : (
                        <span style={{ fontSize: 9, color: SURFACE.text, fontWeight: 600 }}>Upload</span>
                      )}
                    </div>
                    {getAsset(activeSlide).image && (
                      <button onClick={function() { updateSlide(activeSlide, "expandScreenshot", !currentSlide.expandScreenshot, true); }}
                        title={currentSlide.expandScreenshot ? "Contract screenshot area" : "Expand screenshot area"}
                        style={{ background: "none", border: "none", color: CLR.primary, cursor: "pointer", fontSize: 14, padding: 0, lineHeight: 1, fontWeight: 700, flexShrink: 0 }}>{currentSlide.expandScreenshot ? "\u2921" : "\u2922"}</button>
                    )}
                  </div>
                  {getAsset(activeSlide).name && (
                    <span style={{ fontSize: 11, color: SURFACE.dimmed, marginTop: 3, maxWidth: "100%", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", display: "block", textAlign: "center" }}>{getAsset(activeSlide).name}</span>
                  )}
                  {getAsset(activeSlide).image && (
                    <div style={{ display: "flex", alignItems: "center", gap: SPACE[1], marginTop: SPACE[1], width: "100%" }}>
                      <input type="range" min={50} max={200} value={Math.round(getAsset(activeSlide).scale * 100)} onChange={function(e) { setScale(activeSlide, Number(e.target.value) / 100); }}
                        style={{ flex: 1, minWidth: 0 }} />
                      <span style={{ fontSize: 7, color: SURFACE.secondary, minWidth: 20, textAlign: "right" }}>{Math.round(getAsset(activeSlide).scale * 100) + "%"}</span>
                    </div>
                  )}
                </div>
              )}
            </div>

            <div style={{ borderTop: "1px solid " + SURFACE.border, marginTop: SPACE[5], marginBottom: SPACE[5] }} />
          </div>
          {/* Scrollable bottom: Slides list */}
          <div style={{ flex: 1, overflowY: "auto", minHeight: 0 }}>
            <div style={{ background: SURFACE.panelDeep, border: "1px solid " + SURFACE.uploadBorder, borderRadius: RADIUS.xl, padding: SPACE[6] }}>
              <SlideSelector seriesSlides={seriesSlides} activeSlide={activeSlide} setActiveSlide={setActiveSlide}
                dragFrom={slideMgmt.dragFrom} setDragFrom={slideMgmt.setDragFrom} dragOver={slideMgmt.dragOver} setDragOver={slideMgmt.setDragOver}
                reorderSlide={slideMgmt.reorderSlide} addSlide={slideMgmt.addSlide} duplicateSlide={slideMgmt.duplicateSlide}
                removeSlide={slideMgmt.removeSlide} />
            </div>
          </div>
        </div>

        {/* -- CENTER PANE: Slide Editor -- */}
        <div style={{ gridArea: "editor", display: "flex", flexDirection: "column", minWidth: 0 }}>

          {/* Scrollable: Slide Editor */}
          <div style={{ flex: 1, overflowY: "auto", minHeight: 0 }}>

          {/* --- SLIDE EDITOR --- */}
          {currentSlide && (
            <div style={{ background: SURFACE.panel, borderRadius: RADIUS.xl, padding: SPACE[6], border: "1px solid " + SURFACE.panelBorder, marginBottom: SPACE[6] }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: SPACE[5] }}>
                <span style={{ color: SURFACE.tertiary, fontSize: 14, fontWeight: 700 }}>
                  {"SLIDE " + (activeSlide + 1)}
                </span>
                <div style={{ flex: 1 }} />
                <div style={{ display: "flex", gap: SPACE[3] }}>
                  <button onClick={slideMgmt.duplicateSlide}
                    style={{ background: "none", border: "1px solid " + SURFACE.border, color: SURFACE.text, cursor: seriesSlides.length >= MAX_SLIDES ? "default" : "pointer", fontSize: 11, padding: "3px " + SPACE[5] + "px", borderRadius: RADIUS.md, opacity: seriesSlides.length >= MAX_SLIDES ? 0.4 : 1 }}>Duplicate</button>
                  <button onClick={function() { slideMgmt.resetSlide(activeSlide); }}
                    style={{ background: "none", border: "1px solid " + SURFACE.border, color: SURFACE.text, cursor: "pointer", fontSize: 11, padding: "3px " + SPACE[5] + "px", borderRadius: RADIUS.md }}>Reset</button>
                  {seriesSlides.length > 1 && (
                    <button onClick={function() { slideMgmt.removeSlide(activeSlide); }}
                      style={{ background: "none", border: "1px solid " + CLR.dangerBorder, color: CLR.danger, cursor: "pointer", fontSize: 11, padding: "3px " + SPACE[5] + "px", borderRadius: RADIUS.md }}>Remove</button>
                  )}
                </div>
              </div>

              {/* -- Frame toggle (per-slide) -- */}
              <div style={{ display: "flex", alignItems: "center", gap: SPACE[4], marginBottom: SPACE[2], marginTop: SPACE[2] }}>
                <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>FRAME</label>
                <button onClick={function() { updateBgField("frameEnabled", !currentSlide.frameEnabled); }}
                  style={toggleBtn(currentSlide.frameEnabled)}>
                  {currentSlide.frameEnabled ? "ON" : "OFF"}
                </button>
                {currentSlide.frameEnabled && (
                  <div style={{ display: "flex", alignItems: "center", gap: SPACE[2], marginLeft: SPACE[2] }}>
                    <ColorPickerInline pickerKey="border" value={currentSlide.borderColor || "#fff"} onChange={function(c) { updateBgField("borderColor", c); }} openPicker={openPicker} setOpenPicker={setOpenPicker} opacityVal={currentSlide.borderOpacity} onOpacityChange={function(v) { updateBgField("borderOpacity", v); }} />
                  </div>
                )}
              </div>

              <div style={dividerStyle()} />

              {/* -- Footer & Pic toggle (per-slide) -- */}
              <div style={{ display: "flex", alignItems: "center", gap: SPACE[4], marginBottom: SPACE[2], marginTop: SPACE[2] }}>
                <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>FOOTER & PIC</label>
                <button onClick={function() { updateSlide(activeSlide, "showBrandName", !currentSlide.showBrandName); }}
                  style={toggleBtn(currentSlide.showBrandName)}>
                  {currentSlide.showBrandName ? "ON" : "OFF"}
                </button>
                {currentSlide.showBrandName && (
                  <>
                    <div style={{ display: "flex", alignItems: "center", gap: SPACE[2], marginLeft: SPACE[2] }}>
                      <ColorPickerInline pickerKey={"s-" + activeSlide + "-footerBase"} value={currentSlide.footerBg || "#ffffff"} onChange={function(c) { updateSlide(activeSlide, "footerBg", c); }} openPicker={openPicker} setOpenPicker={setOpenPicker} />
                      <span style={{ fontSize: 11, color: SURFACE.secondary, fontWeight: 600 }}>Base</span>
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
                <div style={{ marginBottom: SPACE[4], paddingLeft: SPACE[4], borderLeft: "2px solid " + SURFACE.muted }}>
                  <textarea value={currentSlide.brandNameText} onChange={function(e) { updateSlide(activeSlide, "brandNameText", e.target.value); var el = e.target; el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; }} onKeyDown={function(e) { if (e.key === "Enter") e.preventDefault(); }} placeholder="Brand name..." rows={1}
                    ref={function(el) { if (el) { el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; } }}
                    style={Object.assign({}, inputStyle, { marginBottom: SPACE[3], fontSize: 12, resize: "none", overflow: "hidden", maxHeight: "50vh", overflowY: "auto" })} />
                </div>
              )}

              {/* -- Top Corner toggle (per-slide) -- */}
              <div style={dividerStyle()} />
              <div style={{ display: "flex", alignItems: "center", gap: SPACE[4], marginBottom: SPACE[2], marginTop: SPACE[2] }}>
                <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>TOP CORNER</label>
                <button onClick={function() { updateSlide(activeSlide, "showTopCorner", !currentSlide.showTopCorner); }}
                  style={toggleBtn(currentSlide.showTopCorner)}>
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
                <div style={{ marginBottom: SPACE[4], paddingLeft: SPACE[4], borderLeft: "2px solid " + SURFACE.muted }}>
                  <textarea value={currentSlide.topCornerText} onChange={function(e) { updateSlide(activeSlide, "topCornerText", e.target.value); var el = e.target; el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; }} onKeyDown={function(e) { if (e.key === "Enter") e.preventDefault(); }} placeholder="Top corner..." rows={1}
                    ref={function(el) { if (el) { el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; } }}
                    style={Object.assign({}, inputStyle, { marginBottom: SPACE[2], fontSize: 12, resize: "none", overflow: "hidden", maxHeight: "50vh", overflowY: "auto" })} />
                </div>
              )}

              {/* -- Bottom Corner toggle (per-slide) -- */}
              <div style={dividerStyle()} />
              <div style={{ display: "flex", alignItems: "center", gap: SPACE[4], marginBottom: SPACE[2], marginTop: SPACE[2] }}>
                <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>BOTTOM CORNER</label>
                <button onClick={function() { updateSlide(activeSlide, "showBottomCorner", !currentSlide.showBottomCorner); }}
                  style={toggleBtn(currentSlide.showBottomCorner)}>
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
                <div style={{ marginBottom: SPACE[4], paddingLeft: SPACE[4], borderLeft: "2px solid " + SURFACE.muted }}>
                  <textarea value={currentSlide.bottomCornerText} onChange={function(e) { updateSlide(activeSlide, "bottomCornerText", e.target.value); var el = e.target; el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; }} onKeyDown={function(e) { if (e.key === "Enter") e.preventDefault(); }} placeholder="Bottom corner..." rows={1}
                    ref={function(el) { if (el) { el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; } }}
                    style={Object.assign({}, inputStyle, { marginBottom: SPACE[2], fontSize: 12, resize: "none", overflow: "hidden", maxHeight: "50vh", overflowY: "auto" })} />
                </div>
              )}

              {/* -- Heading toggle (per-slide) -- */}
              <div style={dividerStyle()} />
              <div style={{ display: "flex", alignItems: "center", gap: SPACE[4], marginBottom: SPACE[2], marginTop: SPACE[2] }}>
                <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>HEADING</label>
                <button onClick={function() { updateSlide(activeSlide, "showHeading", !currentSlide.showHeading); }}
                  style={toggleBtn(currentSlide.showHeading)}>
                  {currentSlide.showHeading ? "ON" : "OFF"}
                </button>
                {!currentSlide.showCards ? (
                  <button onClick={function() { if (currentSlide.showHeading) updateSlide(activeSlide, "showAccentBar", !currentSlide.showAccentBar, true); }}
                    title="Accent bar"
                    style={Object.assign({}, smallBtnStyle, { padding: SPACE[1] + "px " + SPACE[3] + "px", background: (currentSlide.showHeading && currentSlide.showAccentBar !== false) ? CLR.activeOverlay2 : SURFACE.input, color: (currentSlide.showHeading && currentSlide.showAccentBar !== false) ? CLR.primaryLight : SURFACE.dimmed, cursor: currentSlide.showHeading ? "pointer" : "default", lineHeight: "14px", opacity: currentSlide.showHeading ? 1 : 0.35 })}>
                    {"\u2501"}
                  </button>
                ) : (
                  <button onClick={function() { updateSlide(activeSlide, "showCardChecks", !(currentSlide.showCardChecks !== false), true); }}
                    title="Card checkmarks"
                    style={Object.assign({}, smallBtnStyle, { padding: SPACE[1] + "px " + SPACE[3] + "px", background: (currentSlide.showCardChecks !== false) ? CLR.activeOverlay2 : SURFACE.input, color: (currentSlide.showCardChecks !== false) ? CLR.primaryLight : SURFACE.dimmed, lineHeight: "14px" })}>
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
                <div style={{ marginBottom: SPACE[4], paddingLeft: SPACE[4], borderLeft: "2px solid " + SURFACE.muted }}>
                  <textarea value={currentSlide.title} onChange={function(e) { updateSlide(activeSlide, "title", e.target.value); var el = e.target; el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; }} placeholder="Heading..." rows={1}
                    ref={function(el) { if (el) { el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; } }}
                    style={Object.assign({}, inputStyle, { marginBottom: SPACE[2], fontSize: 12, resize: "none", overflow: "hidden", maxHeight: "50vh", overflowY: "auto" })} />
                </div>
              )}

              {/* Body | Cards toggle */}
              <div style={dividerStyle()} />
              <div style={{ display: "flex", alignItems: "center", marginTop: SPACE[2], marginBottom: SPACE[3], gap: SPACE[2] }}>
                <span onClick={function() { updateSlide(activeSlide, "showCards", false); }}
                  style={{ fontWeight: 600, fontSize: 13, color: !currentSlide.showCards ? GREEN : SURFACE.muted, letterSpacing: 0.5, cursor: "pointer" }}>BODY</span>
                <span style={{ color: SURFACE.pipeSep, margin: "0 " + SPACE[2] + "px", fontSize: 14 }}>|</span>
                <span onClick={function() { updateSlide(activeSlide, "showCards", true); }}
                  style={{ fontWeight: 600, fontSize: 13, color: currentSlide.showCards ? GREEN : SURFACE.muted, letterSpacing: 0.5, cursor: "pointer" }}>CARDS</span>
                <div style={{ display: "flex", alignItems: "center", gap: SPACE[2], marginLeft: SPACE[2], opacity: currentSlide.showCards ? 1 : 0.35 }}>
                  <ColorPickerInline pickerKey={"s-" + activeSlide + "-cardbg"} value={currentSlide.cardBgColor || "#ffffff"} onChange={function(c) { updateSlide(activeSlide, "cardBgColor", c); }} openPicker={openPicker} setOpenPicker={setOpenPicker} disabled={!currentSlide.showCards} />
                  <span style={{ fontSize: 11, color: SURFACE.secondary, fontWeight: 600 }}>Base</span>
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
                    style={Object.assign({}, inputStyle, { fontSize: 13, resize: "none", overflow: "hidden", maxHeight: "50vh", overflowY: "auto" })} />
                </div>
              )}

              {/* Cards content */}
              {currentSlide.showCards && (
                <div>
                  {currentSlide.cards.map(function(c, i) {
                    return (
                      <div key={i} style={{ display: "flex", gap: SPACE[4], marginBottom: SPACE[3], alignItems: "center" }}>
                        <textarea value={c} onChange={function(e) { slideMgmt.updateSlideCard(activeSlide, i, e.target.value); var el = e.target; el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; }} placeholder={"Card " + (i + 1) + "..."} rows={1}
                          ref={function(el) { if (el) { el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; } }}
                          style={Object.assign({}, inputStyle, { padding: SPACE[3] + "px " + SPACE[5] + "px", fontSize: 12, resize: "none", overflow: "hidden", maxHeight: "50vh", overflowY: "auto" })} />
                        {currentSlide.cards.length > 1 && (
                          <button onClick={function() { slideMgmt.removeSlideCard(activeSlide, i); }} style={{ background: "none", border: "none", color: CLR.danger, cursor: "pointer", fontSize: 18, padding: SPACE[2] }}>{"\u00d7"}</button>
                        )}
                      </div>
                    );
                  })}
                  {currentSlide.cards.length < 5 && (
                    <button onClick={function() { slideMgmt.addSlideCard(activeSlide); }} style={{ background: SURFACE.input, border: "1px dashed " + SURFACE.border, color: SURFACE.tertiary, padding: SPACE[3] + "px " + SPACE[6] + "px", borderRadius: RADIUS.lg, cursor: "pointer", fontSize: 12, marginTop: SPACE[2] }}>+ Add Card</button>
                  )}
                </div>
              )}
              {/* Accent color hint */}
              <div style={{ marginTop: SPACE[7], marginBottom: SPACE[3], textAlign: "center" }}>
                <span style={{ fontSize: 14, color: SURFACE.muted }}>**word** = accent color</span>
              </div>
            </div>
          )}

          </div>
        </div>

          {/* -- RIGHT PANE: Canvas preview -- */}
          <div style={{ gridArea: "preview", display: "flex", flexDirection: "column", minWidth: 0, minHeight: 0 }}>
            <canvas ref={canvasRef} width={W} height={H}
              style={{ maxWidth: "100%", minHeight: 0, flex: "0 1 auto", borderRadius: RADIUS.xxl, border: "1px solid " + SURFACE.canvasBorder, display: "block", objectFit: "contain", aspectRatio: W + "/" + H }} />
          </div>
        </div>
      </div>

      {/* Confirm dialog overlay */}
      {confirmDialog && (
        <div style={dialogOverlay()}
          onClick={function() { setConfirmDialog(null); }}>
          <div style={Object.assign({}, dialogBox(SIZE.dialogSm), { textAlign: "center" })}
            onClick={function(e) { e.stopPropagation(); }}>
            <p style={{ color: SURFACE.text, fontSize: 13, margin: "0 0 " + SPACE[7] + "px 0", lineHeight: 1.4 }}>{confirmDialog.message}</p>
            <div style={{ display: "flex", gap: SPACE[5], justifyContent: "center" }}>
              <button onClick={function() { setConfirmDialog(null); }}
                style={dialogBtn(false)}>
                Cancel
              </button>
              <button onClick={function() { confirmDialog.onConfirm(); setConfirmDialog(null); }}
                style={dialogBtn(true)}>
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Save Preset dialog overlay */}
      {presets.presetDialog && presets.presetDialog.type === "save" && (
        <div style={dialogOverlay()}
          onClick={function() { presets.setPresetDialog(null); }}>
          <div style={Object.assign({}, dialogBox(SIZE.dialogMd), { textAlign: "left" })}
            onClick={function(e) { e.stopPropagation(); }}>
            <p style={{ color: SURFACE.text, fontSize: 14, fontWeight: 600, margin: "0 0 " + SPACE[6] + "px 0" }}>Save Preset</p>
            <label style={{ fontSize: 11, color: SURFACE.tertiary, display: "block", marginBottom: SPACE[2] }}>Preset name</label>
            <input value={presets.presetName} onChange={function(e) { presets.setPresetName(e.target.value); }}
              placeholder="My Carousel"
              style={inputStyle} />
            <div style={{ display: "flex", alignItems: "center", gap: SPACE[4], marginTop: SPACE[6], marginBottom: SPACE[7] }}>
              <button onClick={function() { presets.setPresetIncludeImages(!presets.presetIncludeImages); }}
                style={toggleBtn(presets.presetIncludeImages)}>
                {presets.presetIncludeImages ? "ON" : "OFF"}
              </button>
              <span style={{ fontSize: 12, color: SURFACE.subtle }}>Include images (larger file)</span>
            </div>
            <div style={{ display: "flex", gap: SPACE[5], justifyContent: "flex-end" }}>
              <button onClick={function() { presets.setPresetDialog(null); }}
                style={dialogBtn(false)}>
                Cancel
              </button>
              <button onClick={function() { presets.downloadPreset(presets.presetName, presets.presetIncludeImages); presets.setPresetDialog(null); }}
                style={dialogBtn(true)}>
                Save
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
