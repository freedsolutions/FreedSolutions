// ===================================================
// Inline Color Picker Component
// ===================================================

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

  var hasTypography = !!onFontFamilyChange;
  var isOpen = openPicker === pickerKey && !disabled;

  return (
    <div style={{ position: "relative" }} data-picker={pickerKey}>
      <button
        onClick={function(e) {
          if (disabled) return;
          e.stopPropagation();
          setOpenPicker(isOpen ? null : pickerKey);
        }}
        style={{
          width: SIZE.swatchBtn, height: SIZE.swatchBtn, borderRadius: RADIUS.sm,
          border: isOpen ? "2px solid " + CLR.primary : "1px solid " + SURFACE.border,
          background: value,
          cursor: disabled ? "default" : "pointer",
          padding: 0, display: "block"
        }}
      />
      {isOpen && (
        <div style={pickerDropdownStyle}>
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
            {INLINE_SWATCHES.map(function(c) {
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
          <div style={{ display: "flex", gap: SPACE[3], alignItems: "center" }}>
            <input type="color"
              value={value && value.charAt(0) === "#" ? value : "#ffffff"}
              onChange={function(e) { onChange(e.target.value); }}
              style={{ width: SIZE.colorInput, height: SIZE.colorInput, border: "1px solid " + SURFACE.border, borderRadius: RADIUS.sm, cursor: "pointer", background: "none", padding: 0 }}
            />
            <input value={value}
              onChange={function(e) { onChange(e.target.value); }}
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
        </div>
      )}
    </div>
  );
}