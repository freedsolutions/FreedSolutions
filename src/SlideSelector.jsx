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
    <div style={{ marginBottom: SPACE[5] }}>
      <div style={{ display: "flex", alignItems: "center", gap: SPACE[4], marginBottom: SPACE[4] }}>
        <label style={Object.assign({}, labelStyle, { marginBottom: 0 })}>SLIDES</label>
        <button onClick={duplicateSlide}
          disabled={seriesSlides.length >= MAX_SLIDES}
          style={panelBtn({ marginLeft: "auto", padding: "3px " + SPACE[4] + "px", fontSize: 10, cursor: seriesSlides.length >= MAX_SLIDES ? "default" : "pointer", opacity: seriesSlides.length >= MAX_SLIDES ? 0.4 : 1 })}>
          Duplicate
        </button>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: SPACE[3], marginBottom: 0 }}>
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
                style={{ width: "100%", height: SIZE.slideBtn, borderRadius: RADIUS.lg, border: isDragTarget ? "2px dashed " + CLR.primary : (isActive ? "2px solid " + GREEN : "2px solid " + SURFACE.muted), background: isDragTarget ? CLR.dragTarget : (isActive ? CLR.activeSlide : SURFACE.panel), color: isActive ? GREEN : SURFACE.inactive, cursor: isDragSource ? "grabbing" : "grab", fontSize: 18, fontWeight: 700, padding: 0, display: "flex", alignItems: "center", justifyContent: "center", opacity: isDragSource ? 0.4 : 1, transition: "opacity 0.15s, border 0.15s, background 0.15s" }}>
                {label}
              </button>
              {canRemove && (
                <button
                  onClick={function(e) { e.stopPropagation(); removeSlide(i); }}
                  onDragStart={function(e) { e.preventDefault(); e.stopPropagation(); }}
                  style={{ position: "absolute", top: -SPACE[2], right: -SPACE[2], width: SIZE.removeBadge, height: SIZE.removeBadge, borderRadius: RADIUS.lg, border: "none", background: CLR.removeBadgeBg, color: CLR.danger, cursor: "pointer", fontSize: 10, fontWeight: 700, padding: 0, display: "flex", alignItems: "center", justifyContent: "center", lineHeight: 1 }}>{"\u00d7"}</button>
              )}
            </div>
          );
        })}
        {seriesSlides.length < MAX_SLIDES && (
          <button onClick={addSlide}
            style={{ width: "100%", height: SIZE.slideBtn, borderRadius: RADIUS.lg, border: "2px dashed " + SURFACE.muted, background: SURFACE.panel, color: SURFACE.tertiary, cursor: "pointer", fontSize: 20, fontWeight: 700, padding: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>+</button>
        )}
      </div>
    </div>
  );
}