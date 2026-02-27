// ===================================================
// SizeControl Component
// ===================================================
// Renders a font-size stepper with optional color picker and opacity.
// Props: text, sizeKey, min, max, extra, sizes, setSize, colorVal, colorSet,
//        colorPickerKey, openPicker, setOpenPicker, opacityVal, opacitySet

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
          <button onClick={function() { if (sizes[sizeKey] > min) setSize(sizeKey, sizes[sizeKey] - 1); }}
            style={{ minWidth: 28, minHeight: 28, border: "none", background: "transparent", color: "#555", cursor: "pointer", fontSize: 14, padding: 0, lineHeight: "28px" }}>{"\u2212"}</button>
          <input value={sizes[sizeKey]} onChange={function(e) { var v = parseInt(e.target.value, 10); if (!isNaN(v)) setSize(sizeKey, Math.max(min, Math.min(max, v))); }}
            style={{ width: 30, height: 28, border: "none", borderLeft: "1px solid #444", borderRight: "1px solid #444", background: "transparent", color: "#666", fontSize: 11, fontFamily: "monospace", textAlign: "center", padding: 0, outline: "none" }} />
          <button onClick={function() { if (sizes[sizeKey] < max) setSize(sizeKey, sizes[sizeKey] + 1); }}
            style={{ minWidth: 28, minHeight: 28, border: "none", background: "transparent", color: "#555", cursor: "pointer", fontSize: 14, padding: 0, lineHeight: "28px" }}>+</button>
        </div>
      </div>
    </div>
  );
}