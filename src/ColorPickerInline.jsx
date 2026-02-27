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
          width: 18, height: 18, borderRadius: 4,
          border: isOpen ? "2px solid #6366f1" : "1px solid #444",
          background: value,
          cursor: disabled ? "default" : "pointer",
          padding: 0, display: "block"
        }}
      />
      {isOpen && (
        <div style={pickerDropdownStyle}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(8, 1fr)", gap: 4, marginBottom: 8 }}>
            {INLINE_SWATCHES.map(function(c) {
              return (
                <button key={c} onClick={function() { onChange(c); }}
                  style={{
                    width: 20, height: 20, borderRadius: 4,
                    border: value === c ? "2px solid #fff" : "1px solid #444",
                    background: c, cursor: "pointer", padding: 0,
                    boxShadow: value === c ? "0 0 0 1px #6366f1" : "none"
                  }}
                />
              );
            })}
          </div>
          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <input type="color"
              value={value && value.charAt(0) === "#" ? value : "#ffffff"}
              onChange={function(e) { onChange(e.target.value); }}
              style={{ width: 24, height: 24, border: "1px solid #444", borderRadius: 4, cursor: "pointer", background: "none", padding: 0 }}
            />
            <input value={value}
              onChange={function(e) { onChange(e.target.value); }}
              style={{ flex: 1, padding: "4px 6px", borderRadius: 4, border: "1px solid #444", background: "#0e0e1a", color: "#bbb", fontSize: 11, fontFamily: "monospace" }}
            />
          </div>
          {onOpacityChange && (
            <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 8, paddingTop: 8, borderTop: "1px solid #3a3a50" }}>
              <span style={{ fontSize: 10, color: "#666", whiteSpace: "nowrap" }}>Opacity</span>
              <input type="range" min={0} max={100}
                value={opacityVal != null ? opacityVal : 100}
                onChange={function(e) { onOpacityChange(Number(e.target.value)); }}
                style={{ flex: 1 }}
              />
              <span style={{ fontSize: 10, color: "#555", width: 28, textAlign: "right" }}>
                {(opacityVal != null ? opacityVal : 100) + "%"}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}