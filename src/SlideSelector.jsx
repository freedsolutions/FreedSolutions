// ===================================================
// SlideSelector Component
// ===================================================
// Renders slide thumbnails (or numbered fallback squares) with drag-to-reorder,
// remove overlay, and add/duplicate controls.
// Props: seriesSlides, activeSlide, setActiveSlide, dragFrom, setDragFrom,
//        dragOver, setDragOver, reorderSlide, addSlide, duplicateSlide, removeSlide,
//        thumbUrls

var THUMB_W = 72;
var THUMB_H = 90;

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
  var thumbUrls = props.thumbUrls || [];

  var canRemove = seriesSlides.length > 1;

  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
        <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>SLIDES</label>
        <button onClick={duplicateSlide}
          style={{
            padding: "2px 8px",
            borderRadius: 4,
            border: "1px solid #444",
            background: "#28283e",
            color: "#ccc",
            cursor: "pointer",
            fontSize: 9,
            fontWeight: 600,
            opacity: seriesSlides.length >= MAX_SLIDES ? 0.4 : 1
          }}>
          Duplicate
        </button>
      </div>
      <div style={{ display: "flex", gap: 6, marginBottom: 0, flexWrap: "wrap" }}>
        {seriesSlides.map(function(s, i) {
          var isActive = activeSlide === i;
          var isDragSource = dragFrom === i;
          var isDragTarget = dragOver === i && dragFrom !== i;
          var thumbUrl = thumbUrls[i] || null;
          var label = (i + 1).toString();

          var borderStyle = isDragTarget
            ? "2px dashed #6366f1"
            : (isActive ? "2px solid " + GREEN : "1px solid #555");

          return (
            <div key={i} style={{ position: "relative" }}>
              <div
                draggable
                onClick={function() { setActiveSlide(i); }}
                onDragStart={function(e) { setDragFrom(i); e.dataTransfer.effectAllowed = "move"; }}
                onDragOver={function(e) { e.preventDefault(); e.dataTransfer.dropEffect = "move"; setDragOver(i); }}
                onDragLeave={function() { if (dragOver === i) setDragOver(null); }}
                onDrop={function(e) { e.preventDefault(); if (dragFrom != null) { reorderSlide(dragFrom, i); } }}
                onDragEnd={function() { setDragFrom(null); setDragOver(null); }}
                style={{
                  width: THUMB_W,
                  height: THUMB_H,
                  borderRadius: 6,
                  border: borderStyle,
                  background: isDragTarget ? "rgba(99,102,241,0.10)" : (isActive ? "rgba(34,197,94,0.10)" : "#1a1a30"),
                  cursor: isDragSource ? "grabbing" : "grab",
                  opacity: isDragSource ? 0.4 : 1,
                  transition: "opacity 0.15s, border 0.15s, background 0.15s",
                  overflow: "hidden",
                  position: "relative",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  boxSizing: "border-box"
                }}>
                {thumbUrl ? (
                  <img
                    src={thumbUrl}
                    width={THUMB_W}
                    height={THUMB_H}
                    draggable={false}
                    style={{
                      display: "block",
                      width: THUMB_W,
                      height: THUMB_H,
                      objectFit: "cover",
                      borderRadius: 4,
                      pointerEvents: "none"
                    }}
                  />
                ) : (
                  <span style={{
                    fontSize: 16,
                    fontWeight: 700,
                    color: isActive ? GREEN : "#aaa"
                  }}>
                    {label}
                  </span>
                )}
                {/* Index badge */}
                <span style={{
                  position: "absolute",
                  top: 2,
                  left: 2,
                  width: 14,
                  height: 14,
                  borderRadius: 7,
                  background: "rgba(0,0,0,0.6)",
                  color: "#fff",
                  fontSize: 9,
                  fontWeight: 700,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  lineHeight: 1,
                  pointerEvents: "none"
                }}>
                  {label}
                </span>
              </div>
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
            style={{ width: THUMB_W, height: THUMB_H, borderRadius: 6, border: "2px dashed #555", background: "#1a1a30", color: "#888", cursor: "pointer", fontSize: 18, fontWeight: 700, padding: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>+</button>
        )}
      </div>
    </div>
  );
}