# Smoke Test Handoff Card

Paste this full card into a new browser Claude extension thread to run smoke tests.

## Metadata
- Commit hash under test: `2c002e1`
- Branch: `main`
- Build confirmation: `node build.js` succeeded (yes, 2026-03-01)
- Artifact loaded confirmation: `linkedin-carousel.jsx` loaded in browser (`yes/no`)

## Scope
- In scope:
  - **Expand Screenshots toggle**: New per-slide toggle in Body/Cards section header row; when ON, compresses body/cards content vertically so screenshot gets more space
  - **Accent bar / checkmark tie-in**: When expand is ON, accent bar and card checkmarks shift upward to contribute vertical space
  - **Edge-to-edge screenshots**: When expand is ON, screenshots render full canvas width (no horizontal margins, no rounded corners at edges)
  - **Top Corner case freedom**: Text renders exactly as typed — no forced uppercase
  - **Font swap**: Georgia replaced with Cambria (with Georgia fallback) in font selector
  - **Auto-overwrite screenshots**: Uploading or pasting a screenshot replaces existing one without confirmation prompt
- Out of scope:
  - Horizontal body/cards text layout changes
  - New screenshot positioning controls (drag, offset)
  - PDF export logic changes
  - Removal of other font options
  - Screenshot scale slider behavior changes
  - Rich-text or per-word casing in Top Corner
  - Bottom Corner or other text sections for case behavior

## Required Upload Checkpoints
- Profile image upload: `not-required`
- Custom background image upload: `not-required`
- Screenshot image upload: `required` (test both file upload and clipboard paste)

## Scenario Checklist
1. Slide operations
   - Add, edit, duplicate adjacent, delete, drag reorder
2. Presets
   - Save preset with expandScreenshot ON
   - Load valid preset (with and without expandScreenshot field)
   - Load invalid JSON/version and verify preset error location/message
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

### Expand Screenshots Toggle Visibility & State
- Look at the Body/Cards section header row -> Expected: BODY | CARDS labels, then a small expand button (arrow icon), then font size stepper
- Click the expand button -> Expected: button highlights (indigo tint), canvas re-renders with compressed body/cards content and larger screenshot area
- Click expand button again -> Expected: button dims, canvas reverts to normal layout
- Switch to a different slide -> Expected: expand state is per-slide (other slide may have different expand state)
- Switch back -> Expected: expand state preserved

### Accent Bar Tie-In (Body Mode, Expand ON)
- Set expand ON, Body mode, accent bar enabled -> Expected: accent bar renders closer to heading text than when expand is OFF
- Set expand OFF -> Expected: accent bar returns to its normal position (wider gap below heading)

### Card Checkmark Tie-In (Cards Mode, Expand ON)
- Set expand ON, Cards mode with checkmarks enabled -> Expected: cards start higher on the canvas, checkmark circles shift up accordingly
- Set expand OFF -> Expected: cards return to normal vertical position

### Edge-to-Edge Screenshots (Expand ON)
- Set expand ON, upload a screenshot -> Expected: screenshot renders full-width (edge-to-edge, no left/right padding), no rounded corners at slide edges
- Scale slider to 150% -> Expected: screenshot fills edge-to-edge with no horizontal clipping margins
- Set expand OFF -> Expected: screenshot reverts to padded layout with rounded corners (12px radius)

### Screenshot Area Expansion
- Set expand ON with body text -> Expected: screenshot area is visibly taller (starts at a lower minimum Y = 300 instead of 420)
- Set expand OFF -> Expected: screenshot area returns to normal size

### Top Corner Case Freedom
- Type mixed-case text in Top Corner field (e.g., "Hello World") -> Expected: canvas renders "Hello World" exactly (NOT "HELLO WORLD")
- Type all lowercase "label" -> Expected: canvas renders "label"
- Type all uppercase "LABEL" -> Expected: canvas renders "LABEL"
- Default text on new slide is "LABEL" -> Expected: renders as "LABEL" (default is uppercase by convention)

### Font Swap: Cambria Replaces Georgia
- Open any color swatch popover with font selector -> Expected: font dropdown shows "Cambria" instead of "Georgia"
- Select Cambria font for heading -> Expected: canvas renders heading in Cambria serif font; text wrapping re-measures correctly
- Existing slides using Georgia font stack -> Expected: graceful fallback (Cambria, Georgia, serif font stack)

### Auto-Overwrite Screenshots
- Upload a screenshot via Choose File while one already exists -> Expected: new screenshot replaces old immediately, no confirmation dialog
- Paste a screenshot (Ctrl+V with image in clipboard) while one already exists -> Expected: new pasted image replaces old immediately, no confirmation dialog
- After replacement, press Ctrl+Z -> Expected: undo restores previous screenshot state

### Per-Slide Independence
- Set Slide 1 expand ON, Slide 2 expand OFF -> switch between slides -> Expected: each slide renders with its own expand state
- Save preset with mixed expand states -> load preset -> Expected: per-slide expand states restored correctly

### Preset Round-Trip
- Set expandScreenshot ON on some slides -> Save preset -> Load preset -> Expected: expand states restored correctly per-slide
- Load a preset saved BEFORE this feature (no expandScreenshot field) -> Expected: defaults to OFF (current behavior), no errors

### Canvas Layout Accuracy
- Expand ON + long body text -> Expected: body text may be compressed but does not overlap heading or screenshot area
- Expand ON + many cards -> Expected: cards stack tighter, screenshot area below is larger
- Expand OFF -> Expected: all layout identical to pre-feature behavior

## Known Risk Focus
- Vertical compression trade-off: long body text + expand ON may truncate; toggle is off by default
- Edge-to-edge clipping: screenshot draws under border frame overlay
- Font fallback: Cambria availability depends on system; Georgia in fallback chain
- Preset backward compatibility: `expandScreenshot` absent from older presets defaults to `false`
- Top Corner uppercase user expectation: default template text remains uppercase

## Pass Criteria
- No functional breakage visible to end users.
- All scenarios above pass.
- Expand ON produces visibly more screenshot space than OFF.
- Top Corner text renders exactly as typed.
- Cambria appears in font selector and renders correctly on canvas.
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
