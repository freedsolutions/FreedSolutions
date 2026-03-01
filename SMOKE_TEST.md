# Smoke Test Handoff Card

Paste this full card into a new browser Claude extension thread to run smoke tests.

## Metadata
- Commit hash under test: `PENDING`
- Branch: `main`
- Build confirmation: `node build.js` succeeded (yes, 2026-03-01)
- Artifact loaded confirmation: `linkedin-carousel.jsx` loaded in browser (`yes/no`)

## Scope
- In scope:
  - **2-pane layout**: Merged sidebar (Col 1) and editor (Col 2) into a single left pane; preview remains the right pane
  - **Equal-width split**: Both panes share available space roughly equally (`flex: 1 1 50%` each)
  - **Former sidebar sections at wider width**: Presets, Background, Profile Pic, Slides selector, Screenshot sections now render at ~50% viewport width instead of fixed 240px
  - **Sticky preview**: Preview pane retains sticky positioning while scrolling the left pane
  - **No functional changes**: All controls, toggles, inputs, and features are repositioned only — no behavior changes
- Out of scope:
  - New features, controls, or settings panels
  - Changes to canvas rendering, PDF export, or slide data model
  - Changes to preview pane internal layout or content
  - Responsive/mobile breakpoints
  - Collapsible/accordion sections
  - Drag-to-resize pane divider

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

### 2-Pane Layout Rendering
- Load the artifact in browser -> Expected: app renders with exactly 2 columns — a left pane (settings + editor stacked vertically) and a right pane (preview)
- No visible dead space between the top-level settings and the per-slide editor -> Expected: settings flow continuously into the slide editor with no large gap or empty column

### Equal-Width Panes
- On a standard desktop viewport (1200-1400px) -> Expected: both panes are approximately equal width (roughly 50/50 split)
- Resize browser window wider (1600px+) -> Expected: both panes grow proportionally, maintaining roughly equal width
- Resize browser window narrower (toward ~800px) -> Expected: panes respect min-width constraints (left ~380px, right ~360px); may trigger horizontal scroll below minimum

### Left Pane Content Order
- Inspect the left pane from top to bottom -> Expected: content appears in this order:
  1. Presets (Save/Load buttons)
  2. Background section (color controls + photo upload)
  3. Profile Pic section
  4. Slides selector (numbered buttons with drag reorder)
  5. Screenshot toggle/upload/scale
  6. Slide Editor panel (SLIDE N header, Duplicate/Reset/Remove, Footer & Pic, Corners, Heading, Body/Cards)
- No controls are missing compared to the 3-column layout

### Former Sidebar Sections at Wider Width
- Background section -> Expected: internal 50/50 split (color controls left, photo upload right) renders cleanly at the wider width; color picker dropdowns don't clip or overflow
- Slides selector -> Expected: numbered slide buttons reflow naturally in the wider container (more buttons per row)
- Profile Pic section -> Expected: expands to fill width gracefully
- Screenshot section -> Expected: scale slider and upload button fill width gracefully

### Sticky Preview Pane
- Add enough content to make the left pane scroll (e.g., add multiple slides, expand body text) -> Expected: scrolling the page keeps the preview pane fixed/sticky in the viewport
- Preview pane should not scroll with the left pane content -> Expected: preview stays anchored at `top: 24px`

### Preview Pane Sizing
- Canvas preview renders at natural width within its pane -> Expected: 800x1000 canvas scales via `width: 100%` and maintains correct 4:5 aspect ratio
- No maxWidth cap on preview pane -> Expected: preview pane grows with available space (no fixed 520px cap)

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
- Load an existing preset -> Expected: canvas output is identical to the 3-column layout version (no rendering changes)
- Compare general look and feel -> Expected: dark theme, card styling, spacing all consistent with existing design

## Known Risk Focus
- Width reflow: former sidebar content (Presets, Background, Profile Pic) was designed for 240px; now at ~500-600px. Background's internal 50/50 split and color picker sizing should be verified.
- Vertical length: stacking all settings + editor in one column makes the left pane taller. User scrolls while preview stays sticky — intended behavior.
- Preview pane sizing: removed the `maxWidth: 520px` cap; canvas scales via `width: 100%` so aspect ratio should be preserved.
- Min-width constraints: left pane at 380px + right pane at 360px + 20px gap = 760px minimum before horizontal scroll.

## Pass Criteria
- No functional breakage visible to end users.
- All scenarios above pass.
- App renders as exactly 2 panes (no 3-column layout remnants).
- No dead space between settings and editor in left pane.
- Both panes are approximately equal width on standard desktop.
- Preview pane remains sticky while scrolling left pane.
- All existing controls and features work identically to before.
- Loading an existing preset produces the same visual output on canvas.
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
