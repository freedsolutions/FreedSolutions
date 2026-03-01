# Smoke Test Handoff Card

Paste this full card into a new browser Claude extension thread to run smoke tests.

## Metadata
- Commit hash under test: `ec3e758`
- Branch: `main`
- Build confirmation: `node build.js` succeeded (yes, 2026-03-01)
- Artifact loaded confirmation: `linkedin-carousel.jsx` loaded in browser (`yes/no`)

## Scope
- In scope:
  - **Per-slide profile picture**: Each slide can now have its own profile picture (or none), independent of other slides. Upload/remove affects only the active slide.
  - **Sync All expanded**: Sync All now copies background, profile, and screenshot settings from the active slide to all other slides.
  - **Reset expanded**: Reset now clears background, profile, and screenshot settings on the active slide to defaults.
  - **Preset round-trip**: Presets save/load per-slide profile images. Legacy presets with global profile apply it to slide 0.
- Out of scope:
  - No UI layout changes (the Background panel arrangement stays as-is)
  - No new UI controls or visual elements
  - No changes to PDF export logic beyond what naturally follows from per-slide profile data

## Required Upload Checkpoints
- Profile image upload: `required` (test per-slide independence)
- Custom background image upload: `not-required`
- Screenshot image upload: `optional` (verify Sync All and Reset cover screenshots)

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

### Per-Slide Profile Picture
- Upload a profile image on Slide 1 -> Expected: Profile pic appears in Slide 1's canvas footer. Slide 1's Profile card shows the uploaded image.
- Switch to Slide 2 -> Expected: Slide 2 shows no profile pic (Profile card shows "None"). Canvas footer on Slide 2 has no profile picture.
- Upload a different profile image on Slide 2 -> Expected: Slide 2's canvas footer shows the new profile pic. Slide 1 still shows its own profile pic when selected.
- Remove profile pic on Slide 1 -> Expected: Slide 1's canvas footer no longer shows a profile pic. Slide 2's profile pic is unaffected.
- Duplicate a slide with a profile pic -> Expected: The duplicated slide has the same profile pic as the source slide.

### Sync All Expanded Scope
- Set up Slide 1 with a profile pic, a specific background color, and screenshot ON -> Then click "Sync All" -> Expected: Confirmation dialog mentions "background, profile, and screenshot". After confirming, all slides have the same profile pic, background color, and screenshot settings as Slide 1.
- Verify that Sync All still copies all existing background fields (solidColor, bgType, geoEnabled, geoLines, frameEnabled, accentColor, borderColor, borderOpacity, footerBg) -> Expected: All background fields are synced.

### Reset Expanded Scope
- Set up a slide with a profile pic, non-default background, and screenshot ON -> Then click "Reset" -> Expected: Confirmation dialog mentions "background, profile, and screenshot". After confirming, background returns to defaults, profile pic is cleared (shows "None"), screenshot is OFF, and screenshot asset is removed.
- Verify that Reset on one slide does not affect other slides -> Expected: Other slides retain their settings.

### PDF Export with Per-Slide Profiles
- Upload profile pics on different slides -> Export "All slides" PDF -> Expected: Each slide in the PDF renders its own profile pic (or no profile pic if none was uploaded).
- Export "Current slide" PDF for a slide with a profile pic -> Expected: PDF shows the correct profile pic for that slide.

### Preset Round-Trip
- Set up slides with different profile pics per slide -> Save preset with images -> Load the saved preset -> Expected: Each slide has its profile pic restored correctly.
- Save preset without images -> Load -> Expected: Profile pics are not restored (shows "None" on all slides, but profilePicName may be present).

### All Existing Features Work
- Toggle Body/Cards mode -> Expected: mode switches correctly, canvas updates
- Change heading text -> Expected: canvas renders updated heading
- Change background color -> Expected: canvas renders updated background
- Upload screenshot -> Expected: screenshot renders on canvas
- Expand Screenshots toggle (if ON) -> Expected: edge-to-edge screenshot rendering still works
- Top Corner text renders exactly as typed (case freedom) -> Expected: no forced uppercase
- Font selector in color popovers -> Expected: font changes apply to canvas text
- Download Current Slide PDF -> Expected: PDF downloads successfully
- Save and Load preset -> Expected: round-trip preserves all settings

### No Visual Regressions
- Load an existing preset -> Expected: canvas output is consistent (no rendering changes except profile may default to none if old preset)
- Compare general look and feel -> Expected: dark theme, card styling, spacing all consistent with existing design

## Known Risk Focus
- **Profile data duplication**: Storing an `Image` object per slide increases memory if user uploads large images to many slides. Acceptable for typical 2-10 slide count.
- **Preset backward compatibility**: Old presets store profile as a global `profilePicRef`. Loading an old preset applies the global profile to slide 0 only. Other slides default to no profile. This is acceptable.
- **Sync All blast radius expanded**: Syncing now overwrites profile and screenshot on all slides — more destructive than before. Confirmation dialog mitigates. Matches user expectation that "Sync All" means all background-panel settings.
- **Canvas rendering path**: `drawCenteredFooter` now reads `slide.profileImg` from the slide object. Must verify all render paths (preview, PDF export).

## Pass Criteria
- Each slide can independently have its own profile picture.
- Uploading/removing a profile picture affects only the active slide.
- Canvas preview renders the correct per-slide profile picture in each slide's footer.
- Sync All copies background, profile, and screenshot from active slide to all slides.
- Reset clears background, profile, and screenshot on the active slide.
- Slide duplication copies profile data.
- PDF export renders per-slide profile pictures correctly.
- Preset save/load round-trips per-slide profile images.
- No functional regressions in any other feature area.
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
