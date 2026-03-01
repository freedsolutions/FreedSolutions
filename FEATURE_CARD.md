# FEATURE CARD

Feature: Screenshot layout expansion, edge-to-edge screenshots, accent bar margin tie-in, Top Corner case freedom, font swap, and auto-overwrite screenshots

Goal:
Give users more control over screenshot real estate and layout density. Add a toggle that expands the screenshot footprint by compressing body/cards content, allow screenshots to bleed to the slide edge when scaled up, tie accent bar/checkmark vertical position to the expansion toggle, remove forced uppercase on Top Corner text, replace the Georgia font with a smoother alternative, and auto-overwrite existing screenshots on upload or paste without a confirmation prompt.

---

## In scope

### 1. "Expand Screenshots" toggle in Body/Cards section
- Add a new on/off toggle button in the Body/Cards section header row (next to the existing Body/Cards mode toggle) that enables a larger vertical footprint for the screenshot area.
- When ON: compress the body/cards content zone (reduce the minimum `ssY` threshold and/or increase the body start position) so the screenshot container gets more vertical space.
- When OFF (default): current layout behavior is preserved exactly.
- New per-slide state property: `expandScreenshot` (boolean, default `false`).
- Initialize in `makeDefaultSlide()` and handle in preset save/load with `false` fallback.
- Toggle must call `pushUndo()` before mutating state.

### 2. Tie Accent Bar / Checkmark to the expansion toggle
- When "Expand Screenshots" is ON, shift the accent bar (Body mode) and card checkmarks (Cards mode) upward to reduce vertical spacing between the heading and the body/cards content. This frees additional vertical pixels for the screenshot below.
- This adjustment applies to the canvas rendering positions only (`renderSlideContent.js`), not to the settings panel layout.
- The shift must not collapse natural inter-section line spacing — it only tightens the gap between heading and body/cards by a controlled amount (e.g., reduce the `ty + 100` body offset and `ty + 10` accent bar offset proportionally).
- When "Expand Screenshots" is OFF, accent bar and checkmarks render at their current positions (no change).

### 3. Edge-to-edge screenshots (no margins when scaled up)
- When a screenshot is scaled up beyond the content-width boundary, allow it to render to the full slide edges (X = 0, width = canvas width) instead of being clipped to `pad` (80px) margins.
- The clipping rectangle in `drawScreenshot()` should expand from `(pad, ssY, maxW, ssH)` to `(0, ssY, W, ssH)` when the scaled image dimensions exceed the current content-width box.
- Alternatively, provide a per-slide toggle or tie this behavior to the "Expand Screenshots" toggle from feature 1 — if expand is ON, screenshots use full-width bounds.
- The 12px `roundRect` clip radius should be set to 0 for edge-to-edge mode (sharp edges at slide boundary).

### 4. Remove forced uppercase on Top Corner text
- Remove the `.toUpperCase()` call in `drawTopCorner()` (`overlays.js`, line 47) so the text renders exactly as the user types it.
- The default text in `makeDefaultSlide()` can remain `"LABEL"` (uppercase by convention), but users can now type mixed-case or lowercase and have it respected.
- No changes to the input field, state shape, or settings panel — only the canvas rendering call.

### 5. Replace Georgia font with a smoother alternative
- Swap the Georgia entry in `FONT_OPTIONS` (`constants.js`) with a smoother serif or sans-serif system font.
- Recommended replacement: **Cambria** (`"Cambria, Georgia, serif"`) — a modern, smooth serif designed for on-screen readability, available on Windows/macOS.
- Alternative candidates if Cambria is unsuitable: **Palatino Linotype** (`"Palatino Linotype", "Book Antiqua", Palatino, serif`) or **Segoe UI** (`"Segoe UI", Tahoma, Geneva, sans-serif`).
- Update the `label` in `FONT_OPTIONS` to match the new font name.
- All existing slides using Georgia should gracefully fall back (CSS font stack includes Georgia as fallback if Cambria is unavailable).

### 6. Auto-overwrite existing screenshots on upload or paste
- When uploading or pasting a screenshot and the active slide already has a screenshot, replace it immediately without any confirmation dialog or warning.
- This applies to both the file-upload input handler (`handleScreenshotUpload`) and the global paste handler.
- Current behavior already calls `setAsset()` which replaces, but verify there is no `confirm()` or warning gate anywhere in the flow. If one exists, remove it. If none exists, confirm no regression introduces one.
- The undo stack still captures the previous state, so users can revert with `Ctrl+Z` if the replacement was unintended.

---

## Out of scope
- No changes to horizontal body/cards text layout or wrapping width (only vertical compression for feature 1).
- No new screenshot positioning controls (drag, offset) — only expansion of the available area and edge bleed.
- No changes to PDF export logic (canvas changes propagate automatically).
- No removal of other font options — only replacing Georgia.
- No changes to the screenshot scale slider behavior or range — only how the scaled result is clipped/rendered.
- No rich-text or per-word casing in Top Corner — entire text block is rendered as typed.
- No changes to Bottom Corner or other text sections for case behavior (only Top Corner is affected).

---

## Constraints
- Follow existing code patterns: functional state updates, per-slide state objects, `pushUndo()` before mutations, optional-field fallback on preset load.
- System/web-safe fonts only. No `@font-face`, no network font loading, no new dependencies.
- New per-slide state properties must be initialized in `makeDefaultSlide()` and round-trip correctly through preset save/load.
- Canvas layout math must remain deterministic — the "Expand Screenshots" toggle changes offsets by fixed amounts, not by dynamic text measurement.
- Edge-to-edge screenshot rendering must not draw outside the canvas bounds (0 to W horizontally, respect existing vertical bounds).
- The Top Corner uppercase removal must not affect any other text section's rendering.

---

## Risks

- **Vertical compression trade-off**: Compressing body/cards content for a larger screenshot footprint may cause text truncation or overlap on slides with long body text or many cards. Mitigation: only compress when the toggle is ON, and test with max-length content.
- **Edge-to-edge clipping interaction**: Expanding the screenshot clip region to full canvas width may interact with the global slide frame/border if one is rendered. Verify the screenshot layer draws under any global frame overlay.
- **Font fallback chain**: Replacing Georgia with Cambria depends on Cambria being available. The font stack must include Georgia as a fallback so existing content doesn't break on systems without Cambria. Canvas `measureText` will use whichever font is actually resolved, so layout should remain correct.
- **Preset backward compatibility**: New `expandScreenshot` property will be absent in older presets. Load logic must default to `false` (current behavior preserved).
- **Top Corner uppercase user expectation**: Users who relied on auto-uppercase may be surprised if they re-type text in lowercase. The default template text remains uppercase, so new slides look the same.

---

## Acceptance

1. **Expand Screenshots toggle** appears in the Body/Cards section header row and persists per-slide.
2. When toggle is ON, the screenshot container is visibly taller (more vertical space) compared to OFF.
3. When toggle is ON, accent bar (Body mode) and card checkmarks (Cards mode) shift upward to contribute vertical space, without collapsing natural line spacing.
4. When toggle is OFF, all layout matches current (pre-feature) behavior exactly.
5. Screenshots scaled beyond content width render edge-to-edge (full canvas width, no horizontal margins, no rounded corners at edges).
6. Top Corner text renders exactly as typed — mixed case, lowercase, and uppercase all display correctly.
7. Georgia font option is replaced with Cambria (or chosen alternative) in the font selector dropdown; existing slides using Georgia fall back gracefully.
8. Uploading or pasting a screenshot when one already exists replaces it immediately with no confirmation prompt.
9. `Ctrl+Z` undo works for all new state mutations (expand toggle, screenshot replacement).
10. Loading a preset saved before this feature works correctly (new fields default to current values).
11. `node build.js` succeeds with no regressions in existing behavior.
