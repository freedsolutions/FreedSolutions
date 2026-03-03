// ===================================================
// SizeControl Component
// ===================================================
// Renders a font-size stepper with optional color picker, opacity, and typography controls.
// Props: text, sizeKey, min, max, extra, sizes, setSize, colorVal, colorSet,
//        colorPickerKey, openPicker, setOpenPicker, opacityVal, opacitySet,
//        fontFamily, fontFamilySet, boldVal, boldSet, italicVal, italicSet

function SizeControl(props) {
  var text = props.text;
  var sizeKey = props.sizeKey;
  var min = props.min || 10;
  var max = props.max || 60;
  var extra = props.extra;
  var sizes = props.sizes;
  var setSize = props.setSize;
  var colorVal = props.colorVal;
  var colorSet = props.colorSet;
  var colorPickerKey = props.colorPickerKey;
  var openPicker = props.openPicker;
  var setOpenPicker = props.setOpenPicker;
  var opacityVal = props.opacityVal;
  var opacitySet = props.opacitySet;
  // Typography props (optional)
  var fontFamily = props.fontFamily;
  var fontFamilySet = props.fontFamilySet;
  var boldVal = props.boldVal;
  var boldSet = props.boldSet;
  var italicVal = props.italicVal;
  var italicSet = props.italicSet;
  var swatchLabel = props.swatchLabel;

  var hasTypography = !!fontFamilySet;

  if (!sizeKey) return <label style={labelStyle}>{text}{extra ? " " : ""}{extra}</label>;

  var cpOpen = colorPickerKey && openPicker === colorPickerKey;
  return (
    <div style={{ display: "flex", alignItems: "center", marginBottom: text ? SPACE[3] : 0, gap: text ? 0 : SPACE[3] }}>
      {text && <span style={{ fontWeight: 600, fontSize: 13, color: SURFACE.label, letterSpacing: 0.5, flex: 1 }}>{text}{extra ? " " : ""}{extra}</span>}
      <div style={{ display: "flex", alignItems: "center", gap: SPACE[3] }}>
        {colorPickerKey && (
          <div style={{ position: "relative" }} data-picker={colorPickerKey}>
            <button onClick={function(e) { e.stopPropagation(); setOpenPicker(cpOpen ? null : colorPickerKey); }}
              style={{ width: SIZE.swatchBtn, height: SIZE.swatchBtn, borderRadius: RADIUS.sm, border: cpOpen ? "2px solid " + CLR.primary : "1px solid " + SURFACE.border, background: colorVal || "#fff", cursor: "pointer", padding: 0, display: "block" }} />
            {cpOpen && (
              <div style={Object.assign({}, pickerDropdownStyle, { left: "auto", right: 0 })}>
                {hasTypography && (
                  <div style={{ marginBottom: SPACE[4], paddingBottom: SPACE[4], borderBottom: "1px solid " + SURFACE.panelBorder }}>
                    <select value={fontFamily || DEFAULT_FONT} onChange={function(e) { fontFamilySet(e.target.value); }}
                      style={{ width: "100%", padding: SPACE[2] + "px " + SPACE[3] + "px", borderRadius: RADIUS.sm, border: "1px solid " + SURFACE.border, background: SURFACE.inputDeep, color: SURFACE.label, fontSize: 11, marginBottom: SPACE[3], cursor: "pointer" }}>
                      {FONT_OPTIONS.map(function(f) {
                        return <option key={f.value} value={f.value} style={{ fontFamily: f.value }}>{f.label}</option>;
                      })}
                    </select>
                    <div style={{ display: "flex", gap: SPACE[2] }}>
                      <button onClick={function() { boldSet(!boldVal); }}
                        title="Bold"
                        style={{ flex: 1, padding: "3px 0", borderRadius: RADIUS.sm, border: "1px solid " + SURFACE.border, background: boldVal ? CLR.activeOverlay : SURFACE.input, color: boldVal ? CLR.primaryLight : SURFACE.dimmed, cursor: "pointer", fontSize: 12, fontWeight: 900, lineHeight: "16px" }}>B</button>
                      <button onClick={function() { italicSet(!italicVal); }}
                        title="Italic"
                        style={{ flex: 1, padding: "3px 0", borderRadius: RADIUS.sm, border: "1px solid " + SURFACE.border, background: italicVal ? CLR.activeOverlay : SURFACE.input, color: italicVal ? CLR.primaryLight : SURFACE.dimmed, cursor: "pointer", fontSize: 12, fontStyle: "italic", fontWeight: 600, lineHeight: "16px" }}>I</button>
                    </div>
                  </div>
                )}
                <div style={{ display: "grid", gridTemplateColumns: "repeat(8, 1fr)", gap: SPACE[2], marginBottom: SPACE[4] }}>
                  {INLINE_SWATCHES.map(function(c) {
                    var active = colorVal === c;
                    return (
                      <button key={c} onClick={function() { colorSet(c); }}
                        style={{ width: SIZE.swatch, height: SIZE.swatch, borderRadius: RADIUS.sm, border: active ? "2px solid " + SURFACE.white : "1px solid " + SURFACE.border, background: c, cursor: "pointer", padding: 0, boxShadow: active ? "0 0 0 1px " + CLR.primary : "none" }} />
                    );
                  })}
                </div>
                <div style={{ display: "flex", gap: SPACE[3], alignItems: "center" }}>
                  <input type="color" value={colorVal && colorVal.charAt(0) === "#" ? colorVal : "#ffffff"} onChange={function(e) { colorSet(e.target.value); }}
                    style={{ width: SIZE.colorInput, height: SIZE.colorInput, border: "1px solid " + SURFACE.border, borderRadius: RADIUS.sm, cursor: "pointer", background: "none", padding: 0 }} />
                  <input value={colorVal || ""} onChange={function(e) { colorSet(e.target.value); }}
                    style={{ flex: 1, padding: SPACE[2] + "px " + SPACE[3] + "px", borderRadius: RADIUS.sm, border: "1px solid " + SURFACE.border, background: SURFACE.inputDeep, color: SURFACE.label, fontSize: 11, fontFamily: "monospace" }} />
                </div>
                {opacitySet && (
                  <div style={{ display: "flex", alignItems: "center", gap: SPACE[3], marginTop: SPACE[4], paddingTop: SPACE[4], borderTop: "1px solid " + SURFACE.panelBorder }}>
                    <span style={{ fontSize: 10, color: SURFACE.dimmed, whiteSpace: "nowrap" }}>Opacity</span>
                    <input type="range" min={0} max={100} value={opacityVal != null ? opacityVal : 100} onChange={function(e) { opacitySet(Number(e.target.value)); }}
                      style={{ flex: 1 }} />
                    <span style={{ fontSize: 10, color: SURFACE.muted, width: SIZE.stepper, textAlign: "right" }}>{(opacityVal != null ? opacityVal : 100) + "%"}</span>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
        {swatchLabel && (
          <span style={{ fontSize: 11, color: SURFACE.secondary, fontWeight: 600, whiteSpace: "nowrap" }}>{swatchLabel}</span>
        )}
        <div style={{ display: "flex", alignItems: "center", gap: 0, background: SURFACE.input, borderRadius: RADIUS.sm, border: "1px solid " + SURFACE.border, height: SIZE.stepper, overflow: "hidden" }}>
          <button onClick={function() { if (sizes[sizeKey] > min) setSize(sizeKey, sizes[sizeKey] - 1); }}
            style={{ minWidth: SIZE.stepper, minHeight: SIZE.stepper, border: "none", background: "transparent", color: SURFACE.muted, cursor: "pointer", fontSize: 14, padding: 0, lineHeight: SIZE.stepper + "px" }}>{"\u2212"}</button>
          <input value={sizes[sizeKey]} onChange={function(e) { var v = parseInt(e.target.value, 10); if (!isNaN(v)) setSize(sizeKey, Math.max(min, Math.min(max, v))); }}
            style={{ width: SIZE.stepperInput, height: SIZE.stepper, border: "none", borderLeft: "1px solid " + SURFACE.border, borderRight: "1px solid " + SURFACE.border, background: "transparent", color: SURFACE.dimmed, fontSize: 11, fontFamily: "monospace", textAlign: "center", padding: 0, outline: "none" }} />
          <button onClick={function() { if (sizes[sizeKey] < max) setSize(sizeKey, sizes[sizeKey] + 1); }}
            style={{ minWidth: SIZE.stepper, minHeight: SIZE.stepper, border: "none", background: "transparent", color: SURFACE.muted, cursor: "pointer", fontSize: 14, padding: 0, lineHeight: SIZE.stepper + "px" }}>+</button>
        </div>
      </div>
    </div>
  );
}