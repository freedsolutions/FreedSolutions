# FEATURE CARD

Feature: Typography controls (bold / italic + font selector) in color swatch pop-ups

Goal:
Give each text element per-slide typographic control — font family, bold, and italic — surfaced inside the existing color swatch pop-up for that element. This keeps related styling co-located ("everything about how this text looks lives in one popover") and avoids cluttering Column 2 with extra rows of controls.

---

## In scope

### 1. Expand color swatch pop-ups with typography controls
- Every color swatch pop-up (Heading, Body, Cards, Label, Brand Name — wherever a color picker popover exists today) gains:
  - **B / I toggle buttons** — a small row of two icon-style toggles (Bold, Italic) placed directly above or below the existing swatch grid inside the popover.
  - **Font selector dropdown** — a compact `<select>` with 4–6 font options, placed adjacent to the B/I row.
- The popover must remain usable at its current width. If space is tight, stack font selector above and B/I row below the swatches (or vice versa). Avoid making the popover dramatically larger.
- Each toggle is independent (bold + italic can be on simultaneously).
- All controls apply per-element, per-slide (e.g., Slide 1 Heading can be bold sans-serif while Slide 2 Heading is italic serif).

### 2. Per-slide state for typography properties
- Add new per-slide state properties for each styled text element. Naming convention example for Heading:
  - `headingFontFamily` — string, default `"Inter"` (or whatever the current hardcoded font is)
  - `headingBold` — boolean, default `false`
  - `headingItalic` — boolean, default `false`
- Repeat the pattern for Body, Cards, Label, and Brand Name (e.g., `bodyFontFamily`, `bodyBold`, `cardsFontFamily`, `labelBold`, etc.).
- Initialize all in `makeDefaultSlide()` with sensible defaults (current look = no bold, no italic, current font family).
- Handle in preset save/load: treat as optional on load with current-default fallback so older presets without these fields load cleanly.

### 3. Font family options
- Provide a small curated list (no external font loading complexity). Suggested set:
  - **Inter** (current default / clean sans-serif)
  - **Georgia** (classic serif)
  - **Courier New / monospace** (editorial / techy feel)
  - **Arial** (safe neutral sans-serif)
  - **Trebuchet MS** (slightly more personality, still system-available)
- All must be system/web-safe fonts that are reliably available in the browser *and* render correctly on `<canvas>` without `@font-face` loading. If the app currently loads a custom font (e.g., via Google Fonts), it can be included as an additional option, but the core set must not depend on network availability.
- The font selector should display each option name rendered in its own font (inline preview) if feasible within a `<select>`, or at minimum label them clearly.

### 4. Canvas rendering updates
- **Bold / Italic**: Compose the `ctx.font` string dynamically from the per-slide state. Example: `"bold italic 28px Inter"`. This is natively supported by canvas — no special drawing logic needed.
- **Font family**: Apply to `ctx.font` string before any `measureText` or `fillText` calls for the relevant element. All existing layout math (wrapping, bounding box, accent bar positioning) must re-measure after font change since different fonts have different metrics.

### 5. Undo integration
- `pushUndo()` before any typography state mutation (same pattern as existing color/text changes).

---

## Out of scope
- No rich-text *within* a single field (e.g., bolding one word in a sentence). All typography controls apply to the entire text element uniformly.
- No underline support (cut for complexity — canvas has no native text-decoration; would require custom draw logic per wrapped line).
- No font size changes in this feature (already handled by existing font-size controls).
- No text color changes in this feature (already handled by existing swatch).
- No changes to PDF export logic (PDF export should naturally pick up canvas changes since it screenshots the canvas, but no export-specific work).
- No custom/uploaded fonts.
- No text-shadow, letter-spacing, or other extended typographic properties.

---

## Constraints
- Follow existing code patterns: functional state updates, per-slide state objects, `pushUndo()` before mutations, confirm dialogs for destructive actions.
- Popover sizing must remain reasonable — the pop-up should not feel bloated. Target: no more than ~35–45px of additional height for the new controls.
- System/web-safe fonts only. No `@font-face` declarations, no network font loading, no new dependencies.
- New per-slide state properties must be initialized in `makeDefaultSlide()` and handled in preset save/load so they round-trip correctly. Treat as optional on load with current-default fallback so older presets without these fields still load cleanly.
- Canvas text measurement (`ctx.measureText`) must be called *after* setting the composed `ctx.font` string (including bold/italic/family) so wrapping breakpoints and layout are accurate for the active font.

---

## Risks

- **Font metrics vary across families**: Switching from Inter to Georgia changes character widths, ascenders, descenders, and line height. All layout that depends on text measurement (heading wrap → accent bar Y-position, card text overflow/clip, body text wrapping) must re-measure with the active font. If any layout uses hardcoded pixel offsets instead of measured values, font switching will break it.
- **Canvas font string parsing**: The `ctx.font` string has a specific syntax (`"italic bold 24px Inter"`). Order matters — style before weight before size before family. A malformed string silently falls back to the browser default, which is very hard to debug. Build a small helper function (e.g., `composeFont(family, size, bold, italic)`) and use it everywhere.
- **Preset backward compatibility**: New per-slide properties (~3 per text element × 5 elements = ~15 total) will be absent in presets saved before this change. Load logic must default all of them gracefully — same pattern as the `showAccentBar`/`showCardChecks` fields from the previous feature card.
- **Popover layout on small screens**: Adding controls to the popover could cause overflow or clipping if the popover is positioned near a viewport edge. Test with popovers that open near the bottom of Column 2.

---

## Acceptance

- All color swatch pop-ups include B/I toggles and a font family selector.
- Toggling Bold or Italic for any text element updates the canvas preview immediately.
- Changing font family for any text element updates the canvas preview immediately, with correct wrapping and layout.
- Each typography property is independent per element, per slide.
- Font selector offers 4–6 system-safe fonts; all render correctly on canvas.
- Existing heading wrap → accent bar dynamic positioning still works correctly after font change.
- Loading a preset saved before this feature still works (new fields default to current values).
- `Ctrl+Z` undo works for all new typography mutations.
- Popover remains visually clean and does not overflow at typical viewport sizes.
- `node build.js` succeeds with no regressions in existing behavior.