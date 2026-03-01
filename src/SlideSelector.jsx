// ===================================================
// SlideSelector Component
// ===================================================
// Renders numbered slide buttons with drag-to-reorder, remove overlay, and add/duplicate controls.
// Props: seriesSlides, activeSlide, setActiveSlide, dragFrom, setDragFrom,
//        dragOver, setDragOver, reorderSlide, addSlide, duplicateSlide, removeSlide

function SlideSelector(props) {
  var seriesSlides = props.seriesSlides;
  var activeSlide = props.activeSlide;
  var setActiveSlide = props.setActiveSlide;
  var dragFrom = props.dragFrom;
  var setDragFrom = props.setDragFrom;
  var dragOver = props.dragOver;
  var setDragOver = props.setDragOver;
  var reorderSlide = props.reorderSlide;
  var addSlide = props.addSlide;
  var duplicateSlide = props.duplicateSlide;
  var removeSlide = props.removeSlide;

  var canRemove = seriesSlides.length > 1;

  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
        <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>SLIDES</label>
      </div>
      <div style={{ display: "flex", gap: 8, marginBottom: 0, flexDirection: "column" }}>
        {seriesSlides.map(function(s, i) {
          var isActive = activeSlide === i;
          var isDragSource = dragFrom === i;
          var isDragTarget = dragOver === i && dragFrom !== i;
          var label = (i + 1).toString();
          return (
            <div key={i} style={{ position: "relative" }}>
              <button
                draggable
                onClick={function() { setActiveSlide(i); }}
                onDragStart={function(e) { setDragFrom(i); e.dataTransfer.effectAllowed = "move"; }}
                onDragOver={function(e) { e.preventDefault(); e.dataTransfer.dropEffect = "move"; setDragOver(i); }}
                onDragLeave={function() { if (dragOver === i) setDragOver(null); }}
                onDrop={function(e) { e.preventDefault(); if (dragFrom != null) { reorderSlide(dragFrom, i); } }}
                onDragEnd={function() { setDragFrom(null); setDragOver(null); }}
                style={{ width: "100%", height: 64, borderRadius: 8, border: isDragTarget ? "2px dashed #6366f1" : (isActive ? "2px solid " + GREEN : "2px solid #555"), background: isDragTarget ? "rgba(99,102,241,0.10)" : (isActive ? "rgba(34,197,94,0.15)" : "#1a1a30"), color: isActive ? GREEN : "#aaa", cursor: isDragSource ? "grabbing" : "grab", fontSize: 22, fontWeight: 700, padding: 0, display: "flex", alignItems: "center", justifyContent: "center", opacity: isDragSource ? 0.4 : 1, transition: "opacity 0.15s, border 0.15s, background 0.15s" }}>
                {label}
              </button>
              {canRemove && (
                <button
                  onClick={function(e) { e.stopPropagation(); removeSlide(i); }}
                  onDragStart={function(e) { e.preventDefault(); e.stopPropagation(); }}
                  style={{ position: "absolute", top: -4, right: -4, width: 16, height: 16, borderRadius: 8, border: "none", background: "rgba(100,100,100,0.7)", color: "#f87171", cursor: "pointer", fontSize: 10, fontWeight: 700, padding: 0, display: "flex", alignItems: "center", justifyContent: "center", lineHeight: 1 }}>{"\u00d7"}</button>
              )}
            </div>
          );
        })}
        {seriesSlides.length < MAX_SLIDES && (
          <button onClick={addSlide}
            style={{ width: "100%", height: 64, borderRadius: 8, border: "2px dashed #555", background: "#1a1a30", color: "#888", cursor: "pointer", fontSize: 24, fontWeight: 700, padding: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>+</button>
        )}
      </div>
    </div>
  );
}
