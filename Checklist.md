# LinkedIn Carousel - Checklist

## Tweak Log (Session: 2026-02-25)

### Tweak 1: Filename Display (Profile Pic + Screenshot)
- **What**: Filename now shows below "Choose file" button and above status labels (Uploaded/Remove/No image)
- **Why**: Long filenames need room to wrap; previous layout had no filename display
- **Implementation**: Track `profilePicName` and `screenshotNames[idx]` state; render as `word-break: break-all` paragraph, 10px font, max-width 150px
- **Status**: Done

### Tweak 2: Profile Pic Scale - SKIPPED (by design)
- **What**: Considered adding a Scale slider to Profile Pic matching Screenshot's Scale control
- **Why skipped**: Profile pic renders at fixed 84-84px circle in the canvas footer - there's no bounding box to zoom within. Adding scale would mean clipping a circle from a larger draw area, adding complexity for marginal value. Screenshot has scale because it occupies a variable-height region with a clip rect.
- **Status**: Skipped - clean bolt-on later if needed

### Tweak 3: Kill Preset Headshots / Photo Backgrounds
- **What**: Removed entire headshot preset system
- **Removed**:
  - `FALLBACK_PRESETS` object (headshot entries + profileDefault)
  - `HEADSHOT_LABELS`, `HEADSHOT_OFFSETS`, `buildLookups()`
  - `MANIFEST_PATH` and manifest fetch `useEffect`
  - `headshotSrcs`, `headshotImages` state
  - Headshot image loading `useEffect`
  - Photo selector popup (3-2 grid of preset thumbnails)
  - `drawHeadshotBg()` function
  - `bgImageIndex` from slide model
  - `"headshot"` bgType - only `"solid"` and `"custom"` remain
- **Preserved**:
  - Custom background upload (Photo button -> upload file)
  - `drawCustomBg()` - cover-fit + dark overlay, same as headshot render but without offset metadata
  - Solid/Photo toggle buttons (Photo now means "upload your own")
  - Background thumbnail preview with custom image display
- **Status**: Done

### Tweak 4: Base64 Resolution
- **What**: With presets removed, there are zero Base64 blobs and zero external asset dependencies in the source
- **Image sources**: All user-uploaded at runtime via `FileReader.readAsDataURL`
  - Profile pic: user uploads -> `Image` object in state
  - Screenshot: user uploads per-slide -> `Image` object in `screenshots` map
  - Custom background: user uploads -> `Image` object stored on slide's `customBgImage`
- **Default profile pic**: App starts with no profile pic (circular preview shows "None" placeholder). User uploads one for the session. No persistence across sessions.
- **Future options** (not implemented):
  - "Set as default" via localStorage or persistent storage
  - Pull from LinkedIn API
  - Either is a clean bolt-on to current architecture
- **Status**: Done - Base64 fully resolved

### Tweak 5: Body/Cards Margin from Frame (Heading OFF)
- **What**: When heading is toggled off, body text and cards were flush against the top of the frame
- **Fix**: Increased no-heading offset from `ty + 20` -> `ty + 60` for body, `ty + sizes.heading * 0.5` -> `ty + 60` for cards
- **Status**: Done

### Tweak 6: Accent Bar Toggle
- **What**: Added per-slide `showAccentBar` toggle in the Heading UI row (visible when Heading is ON)
- **UI**: Small "Accent Bar" button next to the ON pill, between toggle and size stepper. Green tint when active, grey when off.
- **Canvas**: Accent bar draw gated behind `slide.showAccentBar !== false` (defaults true for backward compat)
- **Status**: Done

### Tweak 7: Custom Background - Remove "Custom loaded" Label + Add Filename
- **What**: Removed green "Custom loaded" text from bg thumbnail area. Added `customBgName` state tracking. Filename now displays below the Choose File button.
- **Status**: Done

### Tweak 8: Hidden File Inputs (All Three Upload Points)
- **What**: Replaced all native `<input type="file">` elements with hidden inputs + styled "Choose File" buttons
- **Why**: Native file inputs show the filename inline next to the button (browser-baked behavior, cannot be removed). Hidden input + custom button gives full control over where filename appears.
- **Applies to**: Profile Pic, Screenshot, Custom Background - all three now use `display: none` input + `useRef` + styled button
- **Refs added**: `screenshotInputRef`, `customBgInputRef` (profile already had `profilePicInputRef`)
- **Status**: Done

### Tweak 9: Footer Badge Renders Without Profile Pic
- **What**: The footer text badge (brand name bubble) now renders whenever `showBrandName` is ON, even if no profile pic is uploaded
- **Previous behavior**: Entire footer (badge + pic) was gated behind `profileImg` being truthy - no profile pic meant no badge at all
- **Fix**: Changed `if (slide.showBrandName && profileImg)` -> `if (slide.showBrandName)` at the `drawCenteredFooter` call site. The function already had an internal `if (profileImg)` guard around just the circle drawing, so the badge always rendered correctly once called.
- **Result**: Footer badge shows with brand name text; circular profile pic area simply doesn't appear until user uploads one. Frame gap and badge positioning are unchanged (both keyed off `showBrandName`, not `profileImg`).
- **Status**: Done

### Tweak 10: Consistent Column 1 Layout - No Photo Mode Bump
- **What**: The "Choose File" button below the background thumbnail only appeared when Photo mode was active, causing a layout shift (bump) when toggling between Solid and Photo.
- **Fix**: Upload area is always rendered with `visibility: hidden/visible` instead of conditional mount/unmount. Space is always reserved; controls only become visible in Photo mode.
- **Why not opacity?**: `visibility: hidden` still reserves layout space but prevents accidental clicks. `opacity: 0` would allow ghost clicks.
- **Status**: Done

### Tweak 11: Photo Upload Status + Profile Pic Space Reservation
- **What (Photo bg)**: Added "Uploaded - Remove/Replace" status to the custom background upload area for parity with Screenshot's upload status pattern. When a photo is loaded: green check + red - + "Replace" button. When empty: just "Choose File".
- **What (Profile Pic)**: Filename and status lines were conditionally mounted, causing a layout bump in the Slides section below. Now both always reserve space via `minHeight` + non-breaking space fallback.
- **Added**: `removeCustomBg()` handler - clears file input ref, `customBgName`, and sets `customBgImage` to null via `updateBgField`.
- **Status**: Done

### Tweak 12: Background Section - Pills Below Label, Thumbnail Flush Top
- **What**: Moved the Sync All/Per-Slide and Solid/Photo pill toggles from the right side of the BACKGROUND label row into the left zone of the 50/50 split (above Accent/Base controls). The background thumbnail now sits flush at the top of the right zone, directly under the BACKGROUND label.
- **Why**: Eliminated dead space in the bottom-right corner of the Background section. The thumbnail now justifies against the BACKGROUND header, and the left column flows naturally: pills -> color controls -> layer/frame toggles.
- **Layout before**: `BACKGROUND [pills]` -> `[controls] [thumbnail]` (thumbnail pushed down by pill row)
- **Layout after**: `BACKGROUND` -> `[pills + controls] [thumbnail]` (thumbnail at top of split)
- **Status**: Done - superseded by Tweak 13

### Tweak 13: Sync Pill Inline with Label + Custom Bg Status Line
- **What**: Split the two pill toggles. Sync All/Per-Slide moved back up inline with the BACKGROUND label (right-aligned, width 110px). Solid/Photo stays alone at top of the left zone inside the 50/50 split. Added "Uploaded - Remove" / "No image" status line below the custom bg filename, matching the Profile Pic pattern. Removed the inline icon pair from the Choose File button row (button now always reads "Choose File").
- **Why**: Sync All/Per-Slide is a section-level concern (applies to all bg fields) so it belongs at the section header level. Solid/Photo is a per-slide mode toggle so it belongs with the controls. Status line gives consistent upload feedback across all three upload points (Profile Pic, Screenshot, Custom Bg).
- **Layout**:
  ```
  BACKGROUND    [Sync|Per]
  [Solid|Photo] +----------+
  [Accent color] - thumbnail -
  [Base color]  +----------+
               [Choose File]
  [Layer  ON]   filename.jpg
  [Frame  ON]   Uploaded - Remove
  ```
- **Details**:
  - Choose File button: always says "Choose File" (no conditional "Replace" label)
  - Status div: `minHeight: 14`, `marginTop: 2` - reserves space in both Solid and Photo modes
  - Upload area visibility still toggled via `visibility: isCustomBg ? "visible" : "hidden"`
- **Status**: Done - superseded by Tweak 14

### Tweak 14: Final Background Layout Shuffle
- **What**: Restructured the BACKGROUND section into three tiers:
  1. **Sync All/Per-Slide** pill - full-width, above BACKGROUND label, as a global toggle
  2. **Left zone** (50/50 split): Accent + Base colors, Layer toggle, Frame toggle (no pills)
  3. **Right zone** (50/50 split): Solid/Photo pill -> Choose File + filename -> Thumbnail -> Uploaded - Remove status
- **Why**: Sync is a section-level concern so it sits above the label. Solid/Photo directly gates what the thumbnail shows, so it lives above it. Upload controls sit between the pill and thumbnail for logical flow (pick mode -> pick file -> see preview -> confirm/remove).
- **Layout**:
  ```
  [Sync All | Per-Slide]
  BACKGROUND
  [Accent color] [Solid|Photo]
  [Base color]   [Choose File]
                 filename.jpg
  [Layer  ON]   +----------+
  [Frame  ON]   - thumbnail -
                +----------+
                Uploaded - Remove
  ```
- **Details**:
  - Sync pill: full-width, `marginBottom: 6`, purple active state
  - Solid/Photo pill: right zone top, `width: 100%`, `marginBottom: 6`
  - Upload area: `visibility` toggled, `marginBottom: 4`, reserves space in Solid mode
  - Status area: below thumbnail, `marginTop: 4`, `visibility` toggled, `minHeight: 14`
- **Status**: Done

### Tweak 15: BACKGROUND Label Above Sync Pill + Vertical Spacing
- **What**: Flipped BACKGROUND label to sit above the Sync All/Per-Slide pill (was below). Increased vertical spacing throughout the left zone to fill the bottom-left void: Sync pill -> split (mb:10), Solid/Photo pill -> Accent (mb:20), group gap (8px), inter-group spacer (14px). Tightened upload area above thumbnail (mb:2, filename minHeight:10) to push thumbnail up. Frame inset in thumbnail increased from 5px to 15px.
- **Status**: Done

### Tweak 16: Duplicate Slide Button
- **What**: Added "Duplicate" button inline with SLIDES label. Deep-copies active slide (including `cards.slice()` for array independence) + copies screenshot/scale/name data to new index. Auto-selects the new slide. Max 10 guard + opacity dim.
- **Button style**: Matches small utility button pattern (`#28283e` bg, `#444` border, 9px font, 4px radius).
- **Status**: Done

### Tweak 17: Sync All - Pill Toggle Replaced with One-Shot Button
- **What**: Removed `bgSynced`/`setBgSynced` state and the full-width Sync All/Per-Slide pill toggle. Replaced with a small "Sync All" button inline with BACKGROUND label (same style as Duplicate button). `updateBgField` simplified to always update active slide only. New `syncBgToAll()` function does a one-shot push of 10 bg fields from active slide to all slides.
- **Why**: Persistent sync mode was confusing - users didn't realize edits propagated everywhere. Explicit one-shot action is clearer.
- **Status**: Done

### Tweak 18: Solid/Photo Pill Back to Purple
- **What**: Changed Solid/Photo pill active color from `#22c55e` (green) back to `#6366f1` (purple) to match the app's primary action color.
- **Status**: Done

### Tweak 19: Custom Bg Upload Bug Fix - Atomic State Update
- **What**: `handleCustomUpload` was calling `updateBgField("customBgImage", img)` then `updateBgField("bgType", "custom")` sequentially. Each triggered a separate `setSeriesSlides` with a stale closure, so the second call overwrote the image. Fixed by combining into a single `setSeriesSlides` call that sets both fields atomically.
- **Status**: Done (bug fix)

### Tweak 20: Confirm Dialogs - Custom React Modal
- **What**: `window.confirm()` is blocked in sandboxed iframes (Claude artifact environment). Replaced with a React-based confirm modal. State: `confirmDialog` holds `{ message, onConfirm }` or null. Overlay: fixed position, dark backdrop (click to dismiss), centered card (`#1a1a30` bg, `#444` border), Cancel (gray) + Confirm (purple) buttons.
- **Used by**: `syncBgToAll()` and `duplicateSlide()`.
- **Status**: Done

---

## Profile Pic Workflow Parity Checklist

| Item | v1 Behavior | Current Behavior | Pass? |
|------|------------|------------|-------|
| Section placement | Col 1, above SLIDES, below BACKGROUND | Same | Pass |
| Global across slides | Yes | Yes | Pass |
| Circular preview | 64px circle, right-aligned | Same | Pass |
| Status: no image | "Default" (showed default asset) | "No image" (no asset to load) | Delta |
| Status: uploaded | "Uploaded - Remove" | Same | Pass |
| Remove resets | Returns to default profile image | Returns to null (no image) | Delta |
| Re-upload after remove | Works immediately | Works immediately | Pass |
| File input ref clearing | Clears on remove | Same | Pass |
| Filename display | Not shown | Now shown below Choose File | New |
| Filename wrapping | N/A | word-break: break-all, max-width 150px | New |

### Known Deltas from v1
1. **No default profile image** - v1 loaded a default from Base64/URL; current version starts empty. This is intentional (no assets to bundle). Canvas footer simply won't render the profile circle until user uploads one.
2. **"No image" vs "Default"** - Status label changed to reflect that there's no fallback image.
3. **Photo background** - v1 had 6 preset headshots; current version only has custom upload. The Solid/Photo toggle and custom upload path are preserved.

---

## Background Behavior

| Feature | v1 | Current |
|---------|----|----|
| Solid bg | Yes | Yes |
| Geo layer (spheres + lines) | Yes | Yes |
| Preset headshot backgrounds | Yes (6 presets) | Removed |
| Custom photo background | Yes | Yes |
| Sync All (one-shot button, no persistent mode) | Yes (persistent toggle) | Yes (one-shot button) |
| Layer ON/OFF + color | Yes | Yes |
| Frame ON/OFF + color + opacity | Yes | Yes |
| Accent color | Yes | Yes |
| Base (solid) color | Yes | Yes |

## Canvas Output Parity
- Solid + geo rendering: identical
- Custom photo rendering: uses `drawCustomBg()` (cover-fit + 70% dark overlay) - same visual as v1's headshot render minus per-preset offsets
- Frame, footer, heading, body, cards, screenshot, top/bottom corner: all identical

---

## Phase 1 Refactor Log (Session: 2026-02-25)

### Phase 1, Item 1: Consolidate Screenshot State
- **What**: Replaced three separate `useState` maps (`screenshots`, `screenshotNames`, `screenshotScales`) with a single `slideAssets` map. Added `getAsset(idx)` and `setAsset(idx, patch)` helpers.
- **Shape**: `{ [slideIndex]: { image: Image|null, name: string|null, scale: number } }`
- **Rewrote**: `handleScreenshotUpload`, `removeScreenshot`, `setScale`, `duplicateSlide` (asset copy), `removeSlide` (reindex), `renderSlide` (read + dep array), Screenshot UI JSX (reads)
- **Status**: Done - zero remaining references to old state names (verified via grep)

### Phase 1, Item 2: Drag-to-Reorder Slides
- **What**: Added drag-and-drop reordering to the SLIDES button strip. New state: `dragFrom`, `dragOver`. New handler: `reorderSlide(fromIdx, toIdx)` with index-map-based remapping of `seriesSlides`, `slideAssets`, and `activeSlide`.
- **Visual cues**: Drag source at 40% opacity, drop target with dashed purple border + tinted background, grab/grabbing cursors, 150ms transitions.
- **Status**: Done

### Phase 1, Item 3: Export Prefix + Staggered Batch Download
- **What**: Added `exportPrefix` state (default "linkedin-slide") with a monospace input in the Preview column. Added `sanitizePrefix()` helper. Both `downloadCurrent` and `downloadAllSeries` now use `{prefix}-{NN}.png` naming (zero-padded, 1-based). `downloadAllSeries` uses recursive `setTimeout` chain at 300ms gaps to prevent browser throttling.
- **Status**: Done - superseded by Export Rework (PDF)

### Phase 1, Item 4: Debounce Canvas Render Effect
- **What**: Added `renderTimerRef` ref. Replaced immediate `useEffect(function() { render(); }, [render])` with a 40ms debounced version using `clearTimeout`/`setTimeout` + cleanup function.
- **Note**: Export functions call `renderSlide` directly (bypass debounce), which is correct for synchronous canvas capture.
- **Status**: Done

### Phase 1, Item 5: Download-All Timing Verification
- **What**: Manual testing step - verify 6+ slides all download in Chrome without silent drops or throttle warnings. Covered by Item 3's staggered implementation.
- **Status**: Superseded by Export Rework (PNG batch downloads replaced with PDF export)

---

## Export Rework: PNG -> PDF (Session: 2026-02-26)

### Export Rework, Item 1: Remove PNG Export + jsPDF/CDN Path
- **What**: Removed all PNG export handlers (`downloadCurrent`, `downloadAllSeries`, staggered `setTimeout` chain), sandbox detection (`isSandboxedIframe`), and manual download state/refs. Removed any jsPDF CDN loading (`loadJsPDF`, `window.jspdf`, dynamic `<script>` injection).
- **Why**: Claude artifact sandbox blocks runtime `<script>` injection. PNG batch exports used staggered downloads which were fragile in sandboxed contexts.
- **Status**: Done

### Export Rework, Item 2: Inline PDF Builder (No External Dependencies)
- **What**: Implemented `buildPdfFromJpegs(jpegPages, pageW, pageH)` - hand-rolled PDF byte stream constructor. Embeds JPEG canvas captures via `/Filter /DCTDecode`. Constructs valid `%PDF-1.4` with Catalog, Pages, per-page Page+Content+Image XObjects, xref table, and trailer. Returns `Blob` of type `application/pdf`.
- **Helpers added**: `decodeBase64ToBinary`, `extractJpegBinaryFromDataUrl`, `captureSlideJpegBinary` (quality 0.92).
- **Status**: Done

### Export Rework, Item 3: PDF Export Handlers
- **What**: `downloadCurrentPDF()` captures active slide -> 1-page PDF. `downloadAllPDF()` captures all slides -> multi-page PDF, restores preview to `activeSlide`. `clearPdfDownload()` revokes blob URL and resets state.
- **State**: `pdfDownload` (`{ name, url }` or null), `pdfError` (string), `pdfUrlRef` (ref for blob URL cleanup).
- **Naming**: `{prefix}-{NN}.pdf` (current), `{prefix}-all.pdf` (all).
- **Status**: Done

### Export Rework, Item 4: Sandbox-Safe UX
- **What**: Removed `window.open(blobUrl, "_blank")` - auto-open is blocked/suspicious in artifact sandbox. Export now shows a "Save {filename}" link only. User clicks to download. Blob URL remains until dismissed with the `x` button (or when replaced/unmounted). Added trust copy: "Generated locally in browser; no upload."
- **Status**: Done

### Export Rework, Item 5: Col 3 UI
- **What**: Two PDF buttons ("Download Current Slide (PDF)" + "Download All N Slides (PDF)"), one save link when `pdfDownload` exists, dismiss button (`x`), inline error text for `pdfError`, trust copy label. Filename prefix input preserved.
- **Status**: Done - pending user artifact testing

---

## Preset Save/Load Feature (Session: 2026-02-26)

### Preset Feature: JSON Export/Import
- **What**: Added full carousel preset save/load via JSON files. Saves all slides (content + visual config), font sizes, export prefix, and optionally all images as base64 data URLs.
- **Schema**: v1 JSON with `version`, `generator`, `name`, `createdAt`, `exportPrefix`, `sizes`, `slides[]`, `profilePicRef`, and `images{}` map. Non-serializable DOM Image objects replaced with string refs (`customBgRef`, `screenshotRef`, `profilePicRef`) pointing into the `images` map.
- **Save flow**: PRESETS section (top of Col 1) -> "Save" button -> modal dialog with name input + "Include images" ON/OFF toggle -> generates JSON blob -> shows "Save {filename}.json" link (sandbox-safe, same pattern as PDF export).
- **Load flow**: "Load" button -> hidden file input (`.json`) -> FileReader parses -> validates `version` + `slides` array -> counts missing images -> confirmation dialog ("replaces all current slides") -> `loadPresetData()` restores all state.
- **Image handling**: When "Include images" is ON, all images (profile pic, custom backgrounds, screenshots) embedded as base64 data URLs from `Image.src`. When OFF, `dataUrl` is `null` but filenames preserved. On load, images restored asynchronously via `new Image()` with functional state updaters (same pattern as existing upload handlers).
- **Load behavior**: Destructive replace-all with confirmation dialog. Empty slides array falls back to 1 default slide. Missing/unknown fields handled gracefully via `makeDefaultSlide()` defaults.
- **New state**: `presetDownload`, `presetDialog`, `presetName`, `presetIncludeImages`, `presetUrlRef`, `presetInputRef`
- **New functions**: `serializePreset()`, `loadPresetData()`, `downloadPreset()`, `clearPresetDownload()`, `handlePresetUpload()`, `PRESET_SLIDE_KEYS` constant
- **Files modified**: `src/App.jsx` only (no new files, no build.js changes)
- **Status**: Done - pending user artifact testing
