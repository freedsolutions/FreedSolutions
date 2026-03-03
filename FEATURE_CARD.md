# Feature: Per-Slide Font Sizes + Control Relocation

## Goal
Make font sizes per-slide (not global) and relocate controls so the left pane holds only global actions while the "Slide N" pane owns all per-slide settings.

## Per-Slide Font Sizes
- Move `sizes` state (heading, body, cardText, topCorner, bottomCorner, brandName) from global `App.jsx` state into the per-slide data model in `slideFactory.js`
- Each slide gets its own copy of sizes with defaults (heading: 48, body: 38, cardText: 22, topCorner: 13, bottomCorner: 16, brandName: 20)
- `resetSlide` resets sizes along with all other per-slide fields (it already calls `makeDefaultSlide()`)
- Update `SizeControl` and all canvas rendering to read sizes from the active slide
- Add sizes fields to `PRESET_SLIDE_KEYS` for preset save/load round-trip
- Undo/redo automatically covered (sizes become part of `seriesSlides` snapshots)

## Control Relocation: Left Pane → Slide N Pane
- **Move upload buttons** (Background, Profile/Footer, Screenshot) to the top of the "Slide N" pane, arranged side-by-side above the editor
- **Move Accent and Base color swatches** from the left pane Background section to the "Slide N" pane, above the "Frame" toggle
- Left pane retains: Presets, Sync All, Reset All, Slides list

## Simplify Reset/Sync Logic
- **Remove single-slide Reset button** from the left pane (per-slide reset lives on the Slide N pane via `resetSlide`)
- **Keep Sync All** on the left pane — syncs all per-slide settings from active slide to all others
- **Keep Reset All** on the left pane — resets all slides to defaults

## Out of Scope
- No new features or controls
- No changes to canvas rendering logic (other than reading sizes from slide instead of global)
- No changes to preset file format (just additional keys per slide)
