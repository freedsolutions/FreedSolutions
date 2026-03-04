// ===================================================
// Inline Color Picker Component
// ===================================================

function drawShapeThumbnail(ctx, shapeId, w, h) {
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = SURFACE.inputDeep;
  ctx.fillRect(0, 0, w, h);
  var c = SURFACE.dimmed;
  if (shapeId === "lines") {
    // Simplified spheres + lines
    ctx.fillStyle = "rgba(102,102,102,0.3)";
    ctx.beginPath(); ctx.arc(2, 8, 6, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.arc(26, 22, 5, 0, Math.PI * 2); ctx.fill();
    ctx.strokeStyle = "rgba(102,102,102,0.4)";
    ctx.lineWidth = 0.5;
    var tl = [[0, 2, 28, 18], [4, 0, 24, 28], [0, 14, 28, 6], [10, 0, 0, 20], [18, 0, 28, 22]];
    for (var i = 0; i < tl.length; i++) {
      ctx.beginPath(); ctx.moveTo(tl[i][0], tl[i][1]); ctx.lineTo(tl[i][2], tl[i][3]); ctx.stroke();
    }
  } else if (shapeId === "bokeh") {
    // Scattered translucent circles at varying sizes
    var orbs = [
      { x: 5, y: 6, r: 4, a: 0.3 }, { x: 20, y: 4, r: 3, a: 0.25 },
      { x: 12, y: 16, r: 6, a: 0.2 }, { x: 24, y: 18, r: 4.5, a: 0.25 },
      { x: 3, y: 24, r: 5, a: 0.2 }, { x: 17, y: 25, r: 3, a: 0.35 },
      { x: 8, y: 12, r: 2.5, a: 0.3 },
    ];
    for (var oi = 0; oi < orbs.length; oi++) {
      var ob = orbs[oi];
      ctx.fillStyle = "rgba(102,102,102," + ob.a + ")";
      ctx.beginPath(); ctx.arc(ob.x, ob.y, ob.r, 0, Math.PI * 2); ctx.fill();
    }
  } else if (shapeId === "waves") {
    ctx.strokeStyle = "rgba(102,102,102,0.4)";
    ctx.lineWidth = 0.5;
    var waveYs = [5, 11, 17, 23];
    for (var wi = 0; wi < waveYs.length; wi++) {
      ctx.beginPath();
      for (var wx = 0; wx <= w; wx += 2) {
        var wy = waveYs[wi] + Math.sin(wx * 0.3 + wi * 1.5) * 2.5;
        if (wx === 0) ctx.moveTo(wx, wy); else ctx.lineTo(wx, wy);
      }
      ctx.stroke();
    }
  } else if (shapeId === "stripes") {
    ctx.strokeStyle = "rgba(102,102,102,0.4)";
    ctx.lineWidth = 0.6;
    for (var d = -28; d < 56; d += 6) {
      ctx.beginPath(); ctx.moveTo(d, 0); ctx.lineTo(d - h, h); ctx.stroke();
    }
  } else if (shapeId === "hex") {
    var s = 8;
    var colSt = s * 1.5;
    var rowSt = Math.sqrt(3) * s;
    ctx.strokeStyle = "rgba(102,102,102,0.4)";
    ctx.lineWidth = 0.4;
    ctx.beginPath();
    for (var col = 0; col * colSt < w + s; col++) {
      for (var row = 0; row * rowSt < h + s; row++) {
        var cx = col * colSt;
        var cy = row * rowSt + (col % 2 !== 0 ? rowSt / 2 : 0);
        for (var a = 0; a < 6; a++) {
          var angle = Math.PI / 3 * a;
          var px = cx + s * Math.cos(angle);
          var py = cy + s * Math.sin(angle);
          if (a === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
        }
        ctx.closePath();
      }
    }
    ctx.stroke();
  }
}

function ColorPickerInline(props) {
  var pickerKey = props.pickerKey;
  var value = props.value || "#ffffff";
  var onChange = props.onChange;
  var openPicker = props.openPicker;
  var setOpenPicker = props.setOpenPicker;
  var disabled = props.disabled || false;
  var opacityVal = props.opacityVal;
  var onOpacityChange = props.onOpacityChange;
  // Typography props (optional)
  var fontFamily = props.fontFamily;
  var onFontFamilyChange = props.onFontFamilyChange;
  var bold = props.bold;
  var onBoldChange = props.onBoldChange;
  var italic = props.italic;
  var onItalicChange = props.onItalicChange;
  // Layer shape props (optional)
  var geoShape = props.geoShape;
  var onShapeChange = props.onShapeChange;

  // Customizable swatches + transparent option (used by Layer picker)
  var swatches = props.swatches || INLINE_SWATCHES;
  var allowTransparent = props.allowTransparent || false;

  var hasTypography = !!onFontFamilyChange;
  var isTransparentValue = value === "transparent";
  var isOpen = openPicker === pickerKey && !disabled;

  var swatchBtnRef = useRef(null);
  var thumbCanvasRefs = useRef({});

  // Draw shape thumbnails when picker opens
  useEffect(function() {
    if (!isOpen || !onShapeChange) return;
    // Small delay to let portal mount
    var raf = requestAnimationFrame(function() {
      GEO_SHAPES.forEach(function(shape) {
        var canvas = thumbCanvasRefs.current[shape.id];
        if (!canvas) return;
        var tctx = canvas.getContext("2d");
        drawShapeThumbnail(tctx, shape.id, 28, 28);
      });
    });
    return function() { cancelAnimationFrame(raf); };
  }, [isOpen, onShapeChange]);

  // Compute portal position from swatch button
  var portalStyle = null;
  if (isOpen && swatchBtnRef.current) {
    var rect = swatchBtnRef.current.getBoundingClientRect();
    portalStyle = {
      position: "fixed",
      top: rect.bottom + SPACE[2],
      left: Math.max(4, rect.right - SIZE.pickerWidth),
      zIndex: Z.dropdown,
      background: SURFACE.panel,
      border: "1px solid " + SURFACE.border,
      borderRadius: RADIUS.xl,
      padding: SPACE[5],
      width: SIZE.pickerWidth,
      boxShadow: CLR.shadow
    };
  }

  var popout = isOpen && portalStyle ? (
    <div data-picker-portal={pickerKey} style={portalStyle}>
      {hasTypography && (
        <div style={{ marginBottom: SPACE[4], paddingBottom: SPACE[4], borderBottom: "1px solid " + SURFACE.panelBorder }}>
          <select value={fontFamily || DEFAULT_FONT} onChange={function(e) { onFontFamilyChange(e.target.value); }}
            style={{ width: "100%", padding: SPACE[2] + "px " + SPACE[3] + "px", borderRadius: RADIUS.sm, border: "1px solid " + SURFACE.border, background: SURFACE.inputDeep, color: SURFACE.label, fontSize: 11, marginBottom: SPACE[3], cursor: "pointer" }}>
            {FONT_OPTIONS.map(function(f) {
              return <option key={f.value} value={f.value} style={{ fontFamily: f.value }}>{f.label}</option>;
            })}
          </select>
          <div style={{ display: "flex", gap: SPACE[2] }}>
            <button onClick={function() { onBoldChange(!bold); }}
              title="Bold"
              style={{ flex: 1, padding: "3px 0", borderRadius: RADIUS.sm, border: "1px solid " + SURFACE.border, background: bold ? CLR.activeOverlay : SURFACE.input, color: bold ? CLR.primaryLight : SURFACE.dimmed, cursor: "pointer", fontSize: 12, fontWeight: 900, lineHeight: "16px" }}>B</button>
            <button onClick={function() { onItalicChange(!italic); }}
              title="Italic"
              style={{ flex: 1, padding: "3px 0", borderRadius: RADIUS.sm, border: "1px solid " + SURFACE.border, background: italic ? CLR.activeOverlay : SURFACE.input, color: italic ? CLR.primaryLight : SURFACE.dimmed, cursor: "pointer", fontSize: 12, fontStyle: "italic", fontWeight: 600, lineHeight: "16px" }}>I</button>
          </div>
        </div>
      )}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(8, 1fr)", gap: SPACE[2], marginBottom: SPACE[4] }}>
        {allowTransparent && (
          <button onClick={function() { onChange("transparent"); }}
            title="None (transparent)"
            style={{
              width: SIZE.swatch, height: SIZE.swatch, borderRadius: RADIUS.sm,
              border: isTransparentValue ? "2px solid " + SURFACE.white : "1px solid " + SURFACE.border,
              background: "linear-gradient(45deg, #ccc 25%, transparent 25%), linear-gradient(-45deg, #ccc 25%, transparent 25%), linear-gradient(45deg, transparent 75%, #ccc 75%), linear-gradient(-45deg, transparent 75%, #ccc 75%)",
              backgroundSize: "8px 8px",
              backgroundPosition: "0 0, 0 4px, 4px -4px, -4px 0",
              cursor: "pointer", padding: 0,
              boxShadow: isTransparentValue ? "0 0 0 1px " + CLR.primary : "none"
            }}
          />
        )}
        {swatches.map(function(c) {
          return (
            <button key={c} onClick={function() { onChange(c); }}
              style={{
                width: SIZE.swatch, height: SIZE.swatch, borderRadius: RADIUS.sm,
                border: value === c ? "2px solid " + SURFACE.white : "1px solid " + SURFACE.border,
                background: c, cursor: "pointer", padding: 0,
                boxShadow: value === c ? "0 0 0 1px " + CLR.primary : "none"
              }}
            />
          );
        })}
      </div>
      <div style={{ display: "flex", gap: SPACE[3], alignItems: "center", opacity: isTransparentValue ? 0.4 : 1 }}>
        <input type="color"
          value={!isTransparentValue && value && value.charAt(0) === "#" ? value : "#a0a0af"}
          onChange={function(e) { onChange(e.target.value); }}
          disabled={isTransparentValue}
          style={{ width: SIZE.colorInput, height: SIZE.colorInput, border: "1px solid " + SURFACE.border, borderRadius: RADIUS.sm, cursor: isTransparentValue ? "default" : "pointer", background: "none", padding: 0 }}
        />
        <input value={isTransparentValue ? "none" : value}
          onChange={function(e) { if (!isTransparentValue) onChange(e.target.value); }}
          disabled={isTransparentValue}
          style={{ flex: 1, padding: SPACE[2] + "px " + SPACE[3] + "px", borderRadius: RADIUS.sm, border: "1px solid " + SURFACE.border, background: SURFACE.inputDeep, color: SURFACE.label, fontSize: 11, fontFamily: "monospace" }}
        />
      </div>
      {onOpacityChange && (
        <div style={{ display: "flex", alignItems: "center", gap: SPACE[3], marginTop: SPACE[4], paddingTop: SPACE[4], borderTop: "1px solid " + SURFACE.panelBorder }}>
          <span style={{ fontSize: 10, color: SURFACE.dimmed, whiteSpace: "nowrap" }}>Opacity</span>
          <input type="range" min={0} max={100}
            value={opacityVal != null ? opacityVal : 100}
            onChange={function(e) { onOpacityChange(Number(e.target.value)); }}
            style={{ flex: 1 }}
          />
          <span style={{ fontSize: 10, color: SURFACE.muted, width: SIZE.stepper, textAlign: "right" }}>
            {(opacityVal != null ? opacityVal : 100) + "%"}
          </span>
        </div>
      )}
      {onShapeChange && (
        <div style={{ marginTop: SPACE[4], paddingTop: SPACE[4], borderTop: "1px solid " + SURFACE.panelBorder }}>
          <span style={{ fontSize: 10, color: SURFACE.dimmed, display: "block", marginBottom: SPACE[3] }}>Pattern</span>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: SPACE[2] }}>
            {GEO_SHAPES.map(function(shape) {
              var isActive = (geoShape || "lines") === shape.id;
              return (
                <button key={shape.id}
                  onClick={function() { onShapeChange(shape.id); }}
                  title={shape.label}
                  style={{
                    width: "100%", aspectRatio: "1", borderRadius: RADIUS.sm,
                    border: isActive ? "2px solid " + CLR.primaryLight : "1px solid " + SURFACE.border,
                    background: isActive ? CLR.activeOverlay : "transparent",
                    cursor: "pointer", padding: 1, display: "flex", alignItems: "center", justifyContent: "center"
                  }}>
                  <canvas
                    ref={function(el) { thumbCanvasRefs.current[shape.id] = el; }}
                    width={28} height={28}
                    style={{ width: 28, height: 28, borderRadius: 2, display: "block" }}
                  />
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  ) : null;

  return (
    <div style={{ position: "relative" }} data-picker={pickerKey}>
      <button
        ref={swatchBtnRef}
        onClick={function(e) {
          if (disabled) return;
          e.stopPropagation();
          setOpenPicker(isOpen ? null : pickerKey);
        }}
        style={{
          width: SIZE.swatchBtn, height: SIZE.swatchBtn, borderRadius: RADIUS.sm,
          border: isOpen ? "2px solid " + CLR.primary : "1px solid " + SURFACE.border,
          backgroundColor: isTransparentValue ? "transparent" : value,
          backgroundImage: isTransparentValue
            ? "linear-gradient(45deg, #ccc 25%, transparent 25%), linear-gradient(-45deg, #ccc 25%, transparent 25%), linear-gradient(45deg, transparent 75%, #ccc 75%), linear-gradient(-45deg, transparent 75%, #ccc 75%)"
            : "none",
          backgroundSize: "8px 8px",
          backgroundPosition: "0 0, 0 4px, 4px -4px, -4px 0",
          cursor: disabled ? "default" : "pointer",
          padding: 0, display: "block"
        }}
      />
      {popout && createPortal(popout, document.body)}
    </div>
  );
}