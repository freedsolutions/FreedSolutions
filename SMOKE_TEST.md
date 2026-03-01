# Smoke Test Handoff Card

Paste this full card into a new browser Claude extension thread to run smoke tests.

## Metadata
- Commit hash under test: `PENDING`
- Branch: `main`
- Build confirmation: `node build.js` succeeded (yes, 2026-02-28)
- Artifact loaded confirmation: `linkedin-carousel.jsx` loaded in browser (`yes/no`)

## Scope
- In scope:
  - Live slide thumbnail navigation in the slide selector
  - Offscreen canvas thumbnail rendering for all slides
  - Thumbnail mini-previews (72×90 px) replacing numbered square buttons
  - Active slide accent border, inactive slide subtle border
  - Index badge overlay on each thumbnail
  - Fallback numbered squares when thumbnails not yet rendered
  - Thumbnail updates on slide property/asset changes
  - Thumbnail array sync on add/duplicate/remove/reorder
  - Drag-to-reorder with thumbnail elements
- Out of scope:
  - Main preview canvas rendering logic (unchanged)
  - PDF export logic changes
  - Preset serialization format changes
  - Undo/redo logic changes
  - Column 1 / Column 2 layout changes (beyond slide selector)

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
- On initial load, slide selector shows thumbnail(s) instead of plain numbered squares -> Expected: at least slide 1 displays a rendered mini-preview within ~200ms
- Each thumbnail is approximately 72×90 px (4:5 aspect ratio) -> Expected: thumbnails are noticeably taller than wide, matching canvas proportions
- Active slide thumbnail has a green accent border (`#22c55e`) -> Expected: active slide has a visible 2px solid green border
- Inactive slide thumbnails have a subtle 1px solid `#555` border -> Expected: non-active slides have thin gray borders
- Each thumbnail has a small index badge at top-left -> Expected: a small dark circle with white number (1, 2, 3...) overlays top-left of each thumbnail
- Edit heading text on active slide -> Expected: that slide's thumbnail updates to reflect the new heading within ~200ms
- Change background color on active slide -> Expected: thumbnail updates to show new background color
- Change accent color on active slide -> Expected: thumbnail updates to show new accent color
- Add a new slide -> Expected: a new thumbnail appears (initially may show numbered fallback, then renders within ~200ms)
- Duplicate a slide -> Expected: new thumbnail appears at the correct position showing the duplicated slide content
- Remove a slide -> Expected: thumbnail disappears, remaining thumbnails shift correctly with no stale images
- Drag-reorder slides -> Expected: thumbnails reorder correctly, each still showing its own content, no stale/mismatched images
- Upload a screenshot image on a slide -> Expected: that slide's thumbnail updates to show the screenshot
- Change to Cards mode and edit card text -> Expected: thumbnail updates to reflect card content
- With 3+ slides, rapidly edit text on active slide -> Expected: no visible jank or freezing; thumbnails update smoothly
- If a thumbnail fails to render (edge case) -> Expected: numbered fallback square appears instead
- Click on an inactive slide's thumbnail -> Expected: that slide becomes active; its border changes to green accent
- Main canvas preview still renders correctly alongside thumbnails -> Expected: no visual regression in the large preview panel
- The `+ Add` button is still present and correctly sized to match thumbnail height (90px) -> Expected: `+` button visible next to thumbnails

## Known Risk Focus
- Memory pressure from data URLs: 10 slides × ~30-50 KB JPEG each ≈ 300-500 KB; watch for accumulation on rapid preset switching
- Canvas taint from cross-origin images: try/catch guards thumbnail capture; fallback to numbered square on failure
- Drag ghost image: browser generates ghost from the thumbnail `<img>` element; verify it looks acceptable
- Initial render flash: all thumbnails start as `null`; numbered fallback squares appear briefly until first render cycle completes (< 100ms acceptable)
- Offscreen `toDataURL` on detached canvas: verified behavior in modern browsers

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
