# Smoke Test Handoff Card

Paste this full card into a new browser Claude extension thread to run smoke tests.

## Metadata
- Commit hash under test: `1dc647f`
- Branch: `main`
- Build confirmation: `node build.js` succeeded (yes, 2026-02-28)
- Artifact loaded confirmation: `linkedin-carousel.jsx` loaded in browser (`yes/no`)

## Scope
- In scope:
  - Typography controls (bold/italic toggles + font family selector) in all color swatch pop-ups
  - Per-slide typography state for Heading, Body, Cards, Brand Name, Top Corner, Bottom Corner
  - 5 system-safe font options: Helvetica Neue, Georgia, Courier New, Arial, Trebuchet MS
  - Canvas rendering updates to use dynamic font composition via `composeFont()`
  - Preset save/load round-trip for new typography properties
  - Undo support for typography mutations (automatic via existing snapshot system)
  - Decorator toggle relocation: accent bar / checkmark moved from Body/Cards toggle row to immediately before Text/Base color swatches
  - **Screenshot bounds frame removed**: solid border around uploaded screenshots on canvas is removed; clip-to-rounded-rect and image placement unchanged
  - **Paste screenshot support**: `Ctrl+V` / `Cmd+V` pastes a clipboard image as the active slide screenshot; auto-enables screenshot if OFF; skips when focus is in text inputs
- Out of scope:
  - Rich text within a single field (no per-word bold/italic)
  - Underline, text shadow, letter spacing
  - Font size changes (already handled by existing controls)
  - PDF export logic changes (naturally picks up canvas changes)
  - Custom/uploaded fonts

## Required Upload Checkpoints
- Profile image upload: `not-required`
- Custom background image upload: `not-required`
- Screenshot image upload: `required` (test both file upload and clipboard paste)

## Scenario Checklist
1. Slide operations
   - Add, edit, duplicate adjacent, delete, drag reorder
2. Presets
   - Save preset with typography changes
   - Load valid preset (with and without typography fields)
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

### Typography Controls Visibility
- Click the Heading color swatch -> Expected: popover opens with font selector dropdown and B/I toggle buttons above the swatch grid
- Click the Body/Cards text color swatch -> Expected: popover opens with font selector dropdown and B/I toggles above swatches
- Click the Brand Name color swatch -> Expected: popover opens with font selector + B/I toggles
- Click the Top Corner color swatch -> Expected: popover opens with font selector + B/I toggles
- Click the Bottom Corner color swatch -> Expected: popover opens with font selector + B/I toggles
- Click the Card Background color swatch -> Expected: popover opens with swatch grid only (NO font controls — card bg has no text)

### Bold Toggle
- In Heading popover, click B toggle -> Expected: canvas heading text toggles between bold and normal weight immediately
- Default heading should be bold (B toggle active/highlighted) -> Expected: B button shows highlighted state
- In Body mode, open Text color popover, click B -> Expected: body text on canvas becomes bold
- Default body should NOT be bold -> Expected: B button shows inactive/dim state
- In Cards mode, open Text color popover, click B -> Expected: card text on canvas becomes bold

### Italic Toggle
- In Heading popover, click I toggle -> Expected: canvas heading text becomes italic immediately
- Click I again -> Expected: heading reverts to non-italic
- Bold + Italic simultaneously -> Expected: heading renders bold italic on canvas
- In Body mode, click I -> Expected: body text on canvas becomes italic

### Font Family Selector
- In Heading popover, change font to Georgia -> Expected: canvas heading renders in Georgia serif font; text wrapping re-measures correctly
- Change heading font to Courier New -> Expected: heading renders in monospace; wrapping adjusts to wider character widths
- Change body font to Arial -> Expected: body text on canvas changes to Arial
- Change card text font to Trebuchet MS -> Expected: card text on canvas changes
- Change Brand Name font to Georgia -> Expected: footer badge text renders in Georgia

### Per-Slide Independence
- Set Slide 1 heading to Georgia bold italic -> switch to Slide 2 -> Expected: Slide 2 heading still uses default Helvetica Neue bold
- Go back to Slide 1 -> Expected: Georgia bold italic is preserved

### Canvas Layout Accuracy
- Change heading font to Courier New (wider characters) -> Expected: heading text wraps correctly at new character widths; accent bar position adjusts below last heading line
- Use **accent markers** in heading with Georgia font -> Expected: accent-colored words render correctly inline with normal words
- Type long body text with Georgia font -> Expected: wrapping breakpoints are accurate for Georgia metrics
- Cards with Courier New font -> Expected: card text wraps within card bounds; card heights adjust to fit

### Preset Round-Trip
- Set multiple typography options across slides -> Save preset -> Load the saved preset -> Expected: all font families, bold states, and italic states restore correctly
- Load a preset saved BEFORE this feature (older preset without typography fields) -> Expected: all elements default to Helvetica Neue, heading bold, others non-bold, none italic — no errors

### Undo
- Change heading font from Helvetica Neue to Georgia -> Ctrl+Z -> Expected: heading reverts to Helvetica Neue (undo captures full state)
- Toggle body bold on -> Ctrl+Z -> Expected: body reverts to non-bold

### Decorator Toggle Position
- In Body mode, look at the Body/Cards section layout -> Expected: order is BODY|CARDS toggle + font size stepper on one row, then decorator `—` button immediately before the Text color swatch on the next row
- In Cards mode, look at the Body/Cards section layout -> Expected: order is BODY|CARDS toggle + font size stepper on one row, then decorator `✓` button immediately before the Text color swatch on the next row
- The decorator toggle should NOT appear next to the BODY|CARDS text labels (old position)
- Click the `—` toggle in Body mode -> Expected: accent bar toggles on/off on canvas (same behavior as before, just new position)
- Click the `✓` toggle in Cards mode -> Expected: card checkmarks toggle on/off on canvas (same behavior as before, just new position)

### Popover UX
- Open any typography popover -> Expected: popover does not overflow or clip at typical viewport sizes
- Font dropdown, B/I toggles, swatches, hex input all visible and usable without scrolling

### Screenshot Bounds Frame Removed
- Upload a screenshot image via Choose File -> Expected: screenshot appears on canvas with NO visible border/frame stroke around it; image is clipped to rounded rectangle area
- Compare with empty screenshot placeholder (toggle ON, no upload) -> Expected: dashed placeholder outline still visible (this is the empty-state hint, not the bounds frame)

### Paste Screenshot Support
- Copy an image to clipboard (e.g., take a screenshot with Snipping Tool or copy an image from browser) -> click on the canvas area or anywhere outside text inputs -> press `Ctrl+V` -> Expected: image appears as the active slide screenshot; filename shows "pasted-image.png"; scale slider and "Uploaded" status appear
- Screenshot is OFF for the active slide -> paste an image -> Expected: screenshot auto-enables (turns ON) and the pasted image appears on canvas
- Screenshot is already ON with an existing upload -> paste a new image -> Expected: new pasted image replaces the previous one
- Focus in a textarea (e.g., Heading text field) -> paste text -> Expected: normal text paste works; no screenshot interference
- Focus in a text input -> paste text -> Expected: normal text paste works; no screenshot triggered
- Copy non-image content to clipboard -> click outside inputs -> press `Ctrl+V` -> Expected: nothing happens; no errors, no UI breakage
- Paste screenshot on Slide 1 -> switch to Slide 2 -> Expected: Slide 2 does not have the pasted screenshot (per-slide state)
- Switch back to Slide 1 -> Expected: pasted screenshot is still there

## Known Risk Focus
- Font metrics vary across families: wrapping and layout must re-measure with the active font
- `composeFont()` string syntax: style before weight before size before family
- Preset backward compatibility: 15 new per-slide properties default gracefully via `makeDefaultSlide()`
- Popover sizing: typography controls add ~35-40px of height to the popover
- Paste handler must not intercept text paste in focused input/textarea/select elements
- Clipboard API availability: `clipboardData.items` may not be present in all browsers; handler exits gracefully if absent

## Pass Criteria
- No functional breakage visible to end users.
- All scenarios above pass.
- Existing heading wrap -> accent bar dynamic positioning still works after font change.
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
