# Smoke Test Handoff Card

Copy this card into a new browser Claude thread when running artifact smoke tests.

## Metadata
- Commit hash under test: `<short-hash>`
- Branch: `main`
- Build confirmation: `node build.js` succeeded (`yes/no`, timestamp optional)
- Artifact loaded confirmation: `linkedin-carousel.jsx` loaded in browser (`yes/no`)

## Scope
- In scope:
  - `<behavior 1>`
  - `<behavior 2>`
- Out of scope:
  - `<excluded behavior 1>`

## Required Upload Checkpoints
- Profile image upload: `<required/not-required>`
- Custom background image upload: `<required/not-required>`
- Screenshot image upload: `<required/not-required>`

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
   - Confirm no trigger while typing in `input/textarea/select`
4. PDF export
   - Current slide PDF
   - All slides PDF
5. Upload-dependent flows
   - Profile image
   - Custom background image
   - Screenshot image

## Feature-Specific Scenarios (Required)
- Add checks copied from current feature acceptance criteria.
- Example format:
  - `<scenario>` -> Expected: `<result>`
  - `<scenario>` -> Expected: `<result>`

## Known Risk Focus
- `<risk area 1>`
- `<risk area 2>`

## Pass Criteria
- No functional breakage visible to end users.
- All scenarios above pass.
- Any failure includes reproducible steps and impact.

## Browser Behavior Contract (Paste Exactly)
1. You have no repo context. Test only what is in the loaded artifact.
2. Before every step requiring Windows file picker, output `PAUSE_FOR_FILE_UPLOAD: <instruction>` and stop.
3. Wait for user message `UPLOAD_DONE: <details>` before continuing.
4. If you hit a progress-blocking roadblock where human help can speed things up, output `PAUSE_FOR_ASSISTANCE: <roadblock + requested human action>` and stop.
5. Wait for user message `ASSISTANCE_DONE: <details>` before continuing.
6. At end, output:
   - `RESULT: PASS|FAIL`
   - Scenario matrix table (Scenario / Expected / Actual / Status)
   - `BLOCKERS`
   - `FOLLOW_UP_FIXES` with minimal reproduction steps for each failure
