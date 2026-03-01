# FEATURE CARD

Feature: Live Slide Thumbnail Navigation

Goal:
Replace the numbered square buttons in the slide selector with real-time rendered mini-previews of each slide, so the user can visually scan their entire carousel at a glance. This transforms the editing experience from "click blind numbers and guess" to "see every slide, click what you want to edit." Drag-to-reorder, duplicate, and remove controls carry over unchanged on top of the new thumbnails.

In scope:

1. Offscreen canvas thumbnail rendering
   - Create one shared offscreen `<canvas>` (not inserted into DOM) sized to the full `W×H` (800×1000).
   - On every render cycle, after painting the active slide to the main preview canvas, also render each slide to the offscreen canvas and capture a thumbnail via `canvas.toDataURL('image/jpeg', 0.5)`.
   - Store thumbnail data URLs in a `thumbUrls` state array (one entry per slide).
   - Debounce thumbnail generation to avoid jank — reuse the existing 40ms render debounce timer and append thumbnail passes after the active slide renders.
   - Skip re-rendering a thumbnail for a slide whose state + assets have not changed since the last capture (memoize by comparing a lightweight hash/fingerprint of the slide object plus its asset reference).

2. SlideSelector visual overhaul
   - Replace each numbered `<button>` with an `<img>` element sourced from `thumbUrls[i]`.
   - Thumbnail display size: 72 × 90 px (maintains the 800:1000 = 4:5 aspect ratio).
   - Active slide thumbnail gets a 2px solid accent-colored border (currently green `#22c55e`); inactive slides get a 1px solid `#555` border.
   - Slide number badge: small `12px` circle overlaid at top-left of each thumbnail showing the 1-based index, white text on semi-transparent dark background.
   - Fallback: if `thumbUrls[i]` is `null` (first paint, loading), render the existing numbered square as a placeholder until the thumbnail is ready.
   - Drag-to-reorder behavior and event handlers remain identical — the `<img>` wrapper div inherits all existing `draggable`, `onDragStart`, `onDragOver`, `onDrop`, `onDragEnd` handlers.
   - Remove `×` button stays in the same absolute-positioned top-right spot.
   - The `+ Add` button and `Duplicate` button remain visually unchanged.

3. Thumbnail refresh triggers
   - A slide's thumbnail re-renders when any of the following change: slide state object (any property), its screenshot asset (`slideAssets[i]`), `profileImg`, or `sizes`.
   - When a slide is added, duplicated, or reordered, the full thumbnail array is recalculated.
   - When a slide is removed, its entry is spliced from `thumbUrls` and indices shift accordingly.

4. Performance guardrails
   - Only one offscreen render pass runs at a time. If a new render is requested while one is in-flight, queue it (don't stack).
   - Thumbnail JPEG quality is 0.5 (low-res is fine at 72×90 display size; keeps memory footprint small).
   - If the carousel has 10 slides (max), the worst-case per-cycle is 10 offscreen paints + 10 `toDataURL` calls. At 40ms debounce this is acceptable, but if measured frame time exceeds 100ms, degrade to only re-rendering the active slide's thumbnail and lazily refreshing others on idle (`requestIdleCallback` or `setTimeout(…, 200)`).

Out of scope:
- No changes to the main preview canvas rendering logic.
- No changes to PDF export, preset save/load, or undo/redo.
- No changes to Column 2 (content editing) or Column 1 (settings) layout.
- No new dependencies.
- Thumbnail data is ephemeral (not serialized into presets).
- No animated transitions between thumbnail states.

Constraints:
- The offscreen canvas must use the same `renderSlideToCanvas()` function that powers the main preview — no separate rendering codepath.
- `thumbUrls` state array length must always equal `seriesSlides.length`. Guard against stale indices after add/remove/reorder.
- Thumbnail `<img>` elements must not cause layout shifts when they load. Set explicit `width` and `height` attributes and use a matching-size placeholder `<div>` during the null-URL fallback state.
- `pushUndo()` must NOT be called during thumbnail rendering — thumbnails are read-only visual representations with no state mutation.
- Offscreen canvas is created once via `document.createElement('canvas')` and stored in a `useRef`. Do not create a new canvas per render cycle.
- All thumbnail rendering happens inside `useCanvasRenderer` (or a new `useThumbnailRenderer` hook called from the same effect). Do not scatter rendering logic into UI components.
- Custom background images (`customBgImage`) on non-active slides must be available to the offscreen renderer. These are already stored in the slide objects as `Image` references, so no additional loading is needed.

Risks:
- **Memory pressure from data URLs**: 10 JPEG data URLs at ~30–50 KB each ≈ 300–500 KB. Acceptable, but if users toggle rapidly between presets (which replace all slides), stale URLs must be revoked or overwritten promptly to avoid accumulation.
- **Canvas taint from cross-origin images**: If a custom background `Image` was loaded from a cross-origin source (unlikely in this app since all images come from local `FileReader`), `toDataURL` would throw. Guard with a try/catch around thumbnail capture; on failure, fall back to the numbered placeholder for that slide.
- **Drag ghost image**: When dragging a thumbnail `<img>`, the browser generates a ghost from the element. This is fine and arguably better than the current numbered-box ghost. No special handling needed, but verify it looks acceptable.
- **Initial render flash**: On first mount, all `thumbUrls` are `null`. The fallback numbered squares appear briefly until the first render cycle completes. This is acceptable; the transition should be < 100ms.
- **`toDataURL` on offscreen canvas**: The offscreen canvas is never added to the DOM, but `getContext('2d')` and `toDataURL` work identically on detached canvases. Verified behavior in all modern browsers.

Acceptance:
- Each slide in the selector row displays a real-time rendered mini-preview instead of a plain number.
- Thumbnails are 72×90 px and maintain the 4:5 aspect ratio.
- The active slide's thumbnail has an accent-colored border; inactive slides have a subtle border.
- Each thumbnail shows a small index badge at top-left.
- Editing any slide property (text, color, background, screenshot) updates that slide's thumbnail within ~200ms.
- Adding, duplicating, reordering, and removing slides correctly updates the thumbnail array with no stale or mismatched images.
- Drag-to-reorder still works — thumbnails are draggable and drop targets behave identically to before.
- Fallback numbered squares appear if a thumbnail has not yet rendered (first paint or error).
- No visible jank or frame drops during normal editing with ≤ 10 slides.
- Main preview canvas rendering is not slowed by thumbnail generation.
- `Ctrl+Z` undo/redo behavior is unaffected.
- `node build.js` succeeds with no regressions.