# FEATURE CARD

Feature: Two-pane layout — eliminate dead space by merging sidebar and editor into a single left column

Goal:
Replace the current 3-column layout (fixed sidebar | flexible editor | flexible preview) with a 2-pane layout (left pane | right preview pane) to eliminate the dead space that appears below the sidebar and editor columns. The left pane stacks the top-level settings (currently Col 1: presets, background, profile pic, slides, screenshot) above the per-slide editor (currently Col 2: footer, corners, heading, body/cards). Both panes should be roughly equal width.

---

## In scope

### 1. Merge Col 1 and Col 2 into a single left pane
- Replace the 3-child flex container (`flex: 0 0 240px` | `flex: 1 1 280px` | `flex: 1 1 360px`) with a 2-child flex container: left pane and right preview pane.
- Left pane contains two stacked sections (top and bottom) rendered as a single scrollable column:
  - **Top section** — top-level slide settings (in current order): Presets, Background, Profile Pic, Slides selector, Screenshot toggle/upload/scale.
  - **Bottom section** — per-slide editor panel (in current order): Slide header (Duplicate/Reset/Remove), Footer & Pic, Top Corner, Bottom Corner, Heading, Body/Cards, content textareas.
- Remove the fixed 240px width constraint on the former sidebar content so it can fill the left pane width naturally.

### 2. Equal-width 2-pane split
- Both panes should share available space roughly equally (e.g., `flex: 1 1 50%` each, or a similar approach).
- Maintain reasonable min-width constraints so neither pane collapses too small (e.g., ~380px left, ~360px right).
- Keep the preview pane sticky behavior (`position: sticky; top: 24px; alignSelf: flex-start`).

### 3. Preserve all existing functionality
- No controls, toggles, inputs, or features are added or removed — only repositioned.
- All existing inline styles, color schemes, spacing patterns, and component behavior remain intact.
- Undo/redo, preset save/load, screenshot upload/paste, PDF download — all unchanged.

### 4. Adapt the former sidebar sections to wider layout
- The Background section's internal 50/50 split (color controls left, photo upload right) should still work at the wider width.
- The Slides selector (flex-wrap numbered buttons) will naturally reflow to the wider container.
- Profile Pic and Screenshot sections expand to fill width gracefully.

---

## Out of scope
- No new features, controls, or settings panels.
- No changes to canvas rendering, PDF export, or slide data model.
- No changes to the Preview pane's internal layout or content.
- No responsive/mobile breakpoints (current app is desktop-only).
- No collapsible/accordion sections (vertical stacking only).
- No drag-to-resize pane divider.
- No changes to component files other than `App.jsx` (and the generated `linkedin-carousel.jsx` via build).

---

## Constraints
- Layout changes are confined to `src/App.jsx` — specifically the main flex container and column wrapper `<div>` elements.
- All styling remains inline (no external CSS, consistent with existing patterns).
- `node build.js` must succeed and regenerate `linkedin-carousel.jsx` cleanly.
- The stacked left pane must not introduce a nested scrollbar — the page-level scroll handles overflow naturally.

---

## Risks

- **Width reflow**: Former sidebar content (Presets, Background, Profile Pic) was designed for a narrow 240px column. At ~50% viewport width (~500-600px), these sections will be wider than before. The existing flex/inline layouts should handle this gracefully, but Background's internal 50/50 split and color picker sizing should be visually verified.
- **Vertical length**: Stacking all settings + editor content in one column makes the left pane taller. If it exceeds the viewport height, the user scrolls while the preview stays sticky — this is the intended behavior but should be confirmed.
- **Preview pane sizing**: Removing the `maxWidth: 520px` cap on the preview or adjusting it may be needed if the equal split makes it too wide or narrow. The 800x1000 canvas scales via `width: 100%` so it should adapt, but verify the aspect ratio looks correct.

---

## Acceptance

1. The app renders as a 2-pane layout: left pane (settings + editor stacked) and right pane (preview).
2. No dead space appears below the left pane — content flows continuously from top-level settings into per-slide editor.
3. Both panes are approximately equal width on a standard desktop viewport (1200-1400px).
4. All existing controls and features work identically to before (no functional regressions).
5. Preview pane remains sticky while scrolling the left pane content.
6. Background section's internal layout (color pickers, photo upload) renders cleanly at the wider width.
7. Slides selector buttons reflow naturally in the wider container.
8. `node build.js` succeeds with no errors.
9. Loading an existing preset produces the same visual output on the canvas (no rendering changes).
