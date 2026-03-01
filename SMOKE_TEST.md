# Smoke Test Handoff Card

Paste this full card into a new browser Claude extension thread to run smoke tests.

## Metadata
- Commit hash under test: `1a4dfe5`
- Branch: `main`
- Build confirmation: `node build.js` succeeded (yes, 2026-03-01)
- Artifact loaded confirmation: `linkedin-carousel.jsx` loaded in browser (`yes/no`)

## Scope
- In scope:
  - **Unified page scroll**: Removed `position: sticky` from Left pane (Slide Selector) and Right pane (Preview) so all 3 panes scroll together with the page
  - **Background panel dead space fix**: Pulled the Profile + Screenshot cards out of the Background flex row via `position: absolute; top: 0; right: 0` relative to the BACKGROUND container, eliminating dead space below them
  - **Scale slider overflow fix**: Added `minWidth: 0` to the range input and `overflow: hidden` to the Scale row container to prevent overflow in the 126px-wide Screenshot card
- Out of scope:
  - New features, controls, or UI elements
  - Changes to canvas rendering, PDF export, or slide data model
  - Changes to any component other than `src/App.jsx` (and the generated `linkedin-carousel.jsx` via build)
  - Independent/inner scrollbars on any pane

## Required Upload Checkpoints
- Profile image upload: `not-required`
- Custom background image upload: `not-required`
- Screenshot image upload: `not-required`

## Scenario Checklist
1. Slide operations
   - Add, edit, duplicate adjacent, delete, drag reorder
2. Presets
   - Save preset, load valid preset, load invalid JSON and verify error
3. Undo/redo
   - Undo via `Ctrl/Cmd+Z`
   - Redo via `Ctrl/Cmd+Shift+Z`
   - Confirm no trigger while typing in `textarea/select`
4. PDF export
   - Current slide PDF
   - All slides PDF
5. Upload-dependent flows
   - Profile image
   - Custom background image
   - Screenshot image (file upload + paste)

## Feature-Specific Scenarios (Required)

### Unified Page Scroll
- Scroll the page down when the Center pane has enough content (e.g., multiple slides, expanded body text) -> Expected: All 3 panes (Left slide selector, Center editor, Right preview) scroll together with the page. No pane stays fixed/pinned.
- No pane has its own independent scrollbar -> Expected: Only the page-level scrollbar exists; no inner scrollbars on any pane.
- Left and Right panes still align to the top of the flex row -> Expected: Left pane (slide selector) and Right pane (preview) start at the top of the layout, not stretched full height.

### Background Panel Dead Space Fix
- Open the app and look at the BACKGROUND section -> Expected: The Profile card and Screenshot card sit flush with the top-right corner of the BACKGROUND section. No visible dead space below them.
- The left zone (Solid/Photo pill, Accent, Base, Layer, Frame, Footer) renders normally -> Expected: All color controls and toggles are visible and functional, no overlap with the Profile/Screenshot cards.
- The middle zone (BG thumbnail preview) renders normally -> Expected: Thumbnail displays correctly, no overlap or clipping.

### Scale Slider Overflow Fix
- Upload a screenshot and enable the Screenshot toggle -> Expected: The Scale slider and percentage label (e.g., "100%") stay entirely within the 126px-wide Screenshot card. No horizontal overflow or bleed.
- Drag the Scale slider from min (50%) to max (200%) -> Expected: Slider operates smoothly within bounds, percentage label updates correctly.

### All Existing Features Work
- Toggle Body/Cards mode -> Expected: mode switches correctly, canvas updates
- Change heading text -> Expected: canvas renders updated heading
- Change background color -> Expected: canvas renders updated background
- Upload profile image -> Expected: profile pic renders on canvas
- Upload screenshot -> Expected: screenshot renders on canvas
- Expand Screenshots toggle (if ON) -> Expected: edge-to-edge screenshot rendering still works
- Top Corner text renders exactly as typed (case freedom) -> Expected: no forced uppercase
- Font selector in color popovers -> Expected: font changes apply to canvas text
- Download Current Slide PDF -> Expected: PDF downloads successfully
- Save and Load preset -> Expected: round-trip preserves all settings

### No Visual Regressions
- Load an existing preset -> Expected: canvas output is identical to before (no rendering changes)
- Compare general look and feel -> Expected: dark theme, card styling, spacing all consistent with existing design

## Known Risk Focus
- **Preview not visible while editing**: With sticky removed, the preview canvas scrolls off-screen when the user scrolls down. This is the intended trade-off per user preference (unified scroll over sticky preview).
- **Slide selector not visible while scrolling**: Left slide selector also scrolls away. Acceptable per user preference.
- **Absolute positioning edge case**: Profile + Screenshot stack is absolutely positioned; if it becomes taller than the left zone, it could overflow the BACKGROUND panel. Unlikely given current card sizes (~200px total vs left zone ~250px+).
- **Scale slider fix is minimal**: `minWidth: 0` + `overflow: hidden` is standard flex overflow fix; low regression risk.

## Pass Criteria
- No functional breakage visible to end users.
- All scenarios above pass.
- All 3 panes scroll together with the page (no sticky behavior).
- No pane has its own independent scrollbar.
- Profile and Screenshot cards sit flush with top of BACKGROUND section (no dead space).
- Scale slider stays within Screenshot card bounds (no overflow).
- All existing controls and features work identically to before.
- Canvas preview renders correctly at same size/aspect ratio.
- Any failure includes reproducible steps and impact.

## Browser Execution Instructions (Embedded Agent Contract)
1. You have no repo context. Test only what is in the loaded artifact.
2. This is a paste-only flow in browser Claude extension. Do not rely on local file upload.
3. DO NOT CLOSE OUT THE BROWSER.
4. Before every step requiring Windows file picker, output `PAUSE_FOR_FILE_UPLOAD: <instruction>` and stop.
5. Wait for user message `UPLOAD_DONE: <details>` before continuing.
6. If you hit a progress-blocking roadblock where human help can speed things up, output `PAUSE_FOR_ASSISTANCE: <roadblock + requested human action>` and stop.
7. Wait for user message `ASSISTANCE_DONE: <details>` before continuing.
8. At end, output:
   - `RESULT: PASS|FAIL`
   - Scenario matrix table (Scenario / Expected / Actual / Status)
   - `BLOCKERS`
   - `FOLLOW_UP_FIXES` with minimal reproduction steps for each failure
