# Smoke Test Handoff Card

Paste this full card into a new browser Claude extension thread to run smoke tests.

## Metadata
- Commit hash under test: `234b2c0`
- Branch: `main`
- Build confirmation: `node build.js` succeeded (yes, 2026-02-28)
- Artifact loaded confirmation: `linkedin-carousel.jsx` loaded in browser (`yes/no`)

## Scope
- In scope:
  - Auto-expanding textareas for all Column 2 text fields
  - Canvas text wrapping for Heading, Body, and Card text
  - Multi-line card input and rendering
  - Separate decorator toggles: accent bar (Body mode) and checkmark (Cards mode)
  - Default accent color changed to `#a5b4fc` (soft indigo)
  - Horizontal separator above Screenshot section in Column 1
- Out of scope:
  - PDF export logic changes
  - Preset serialization format changes (backward-compatible)
  - Background controls, canvas background rendering, drag-to-reorder behavior
  - Label and Brand Name canvas wrapping (remain single-line on canvas)

## Required Upload Checkpoints
- Profile image upload: `not-required`
- Custom background image upload: `not-required`
- Screenshot image upload: `not-required`

## Scenario Checklist
1. Slide operations
   - Add, edit, duplicate adjacent, delete, drag reorder
2. Presets
   - Save preset
   - Load valid preset
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
   - Screenshot image

## Feature-Specific Scenarios (Required)
- Type long text in Brand Name field -> Expected: textarea auto-expands line-by-line, no internal scrollbar until ~50vh
- Type long text in Top Corner field -> Expected: textarea auto-expands
- Type long text in Bottom Corner field -> Expected: textarea auto-expands
- Type long text in Heading field -> Expected: textarea auto-expands; canvas preview wraps heading text within bounding box
- Type multi-line text in Heading (press Enter) -> Expected: textarea grows; canvas renders each line with word-wrap
- Type long text in Body field -> Expected: textarea auto-expands (no fixed 2-row limit); canvas wraps body text
- Type multi-line text in Body (press Enter) -> Expected: canvas renders each line correctly
- Switch to Cards mode and type long text in a Card input -> Expected: textarea auto-expands; canvas wraps card text
- Type multi-line text in Card input (press Enter) -> Expected: textarea grows; canvas renders multi-line card text
- In Body mode, locate the accent bar toggle next to BODY|CARDS -> Expected: toggle is visible, defaults to ON
- Toggle accent bar OFF in Body mode -> Expected: canvas accent bar under heading disappears
- Switch to Cards mode -> Expected: accent bar toggle disappears, checkmark toggle appears (defaults to ON)
- Toggle checkmark OFF in Cards mode -> Expected: canvas card checkmark circles disappear, card text remains
- Toggle checkmark ON again -> Expected: checkmark circles reappear
- Switch back to Body mode -> Expected: checkmark toggle disappears, accent bar toggle reappears with its last state
- Create a new slide -> Expected: default accent color on canvas is soft indigo (`#a5b4fc`), not green
- Verify Body text default color is indigo on new slide -> Expected: `#a5b4fc`
- Locate Column 1 Screenshot section -> Expected: horizontal line divider appears above it
- Save preset with showCardChecks OFF, reload -> Expected: checkmark toggle restores to OFF state
- Ctrl+Z after toggling decorator -> Expected: undo still works (no regression)

## Known Risk Focus
- Auto-expanding textarea `ref` callback may not re-fire on React re-renders for card list items (key stability)
- `showCardChecks` backward-compat: old presets without the property should still show checkmarks (via `!== false` guard)
- Heading newline splitting must not break accent marker highlighting across lines
- Card newline splitting must not break accent marker highlighting within cards

## Pass Criteria
- No functional breakage visible to end users.
- All scenarios above pass.
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
