# FreedSolutions - CLAUDE Reference

## Project Overview

Purpose: single-repo workspace for generator artifacts. Current active generator is `linkedin-carousel.jsx`, built from modular sources in `src/`.

Current status:
- Modular React + Canvas architecture.
- Source files located in `src/`.
- Build artifact: `linkedin-carousel.jsx` (generated via `node build.js`).
- Runtime images are user uploads.

## Repository Layout

```
/FreedSolutions/
|- CLAUDE.md
|- Checklist.md
|- CLAUDE-CODE-HANDOFF.md
|- build.js                            (Deterministic concat script)
|- linkedin-carousel.jsx               (Build artifact - DO NOT EDIT DIRECTLY)
|- src/                                (Source directory)
|  |- App.jsx                          (Main component)
|  |- constants.js                     (Shared constants & React imports)
|  |- slideFactory.js                  (Default slide data)
|  |- canvas/                          (Canvas rendering modules)
|     |- backgrounds.js
|     |- hexToRgba.js
|     |- overlays.js
|     |- renderSlide.js
|     |- renderSlideContent.js
|     |- screenshot.js
|     |- text.js
```

## Build System

Execute `node build.js` to regenerate `linkedin-carousel.jsx`. The build order is defined in `build.js` to ensure proper dependency flow in the concatenated artifact.

## GitHub Workflow

- Primary remote: `origin` -> `https://github.com/freedsolutions/FreedSolutions.git`.
- Main branch: `main`.
- Make source edits in `src/` (especially `src/App.jsx` and `src/canvas/*`), then run `node build.js` to regenerate `linkedin-carousel.jsx`.
- Commit source + generated artifact together when behavior changes, so repo stays reproducible from a single commit.
- Before push: `git status`, `git diff`, and confirm `linkedin-carousel.jsx` matches the latest build output.
- Push with `git push origin main`.
- Verify remote state with `git ls-remote --heads origin` or GitHub commit list.

## Documentation Workflow

- `CLAUDE.md`: architecture, build/export behavior, and repo workflows (including GitHub process).
- `Checklist.md`: detailed tweak/change log for product behavior and UI decisions.
- Git-only operations (create repo, set remote, push) do not require `Checklist.md` updates unless they also change app behavior or handoff expectations.

## Generator Architecture (`src/App.jsx` + `src/canvas/*`)

High-level pattern:
1. React component (`App`) using `useState`, `useRef`, `useEffect`, `useCallback`.
2. Imperative Canvas 2D rendering at 800x1000.
3. Three-column editor UI:
- Col 1: background/profile/slides/screenshot controls.
- Col 2: per-slide content editor.
- Col 3: preview and export.

Canvas constants:
- `W = 800`, `H = 1000`, `MARGIN = 44`

## State Inventory (in `App.jsx`)

- `seriesSlides`: Array of slide content objects.
- `slideAssets`: Map of per-slide image assets (screenshots).
- `profileImg`: Global profile picture.
- `confirmDialog`: State for custom confirmation modals.
- `pdfDownload`: PDF export state (`{ name, url }` or `null`). URL is a blob URL.
- `pdfError`: String error message for failed PDF generation.
- `pdfUrlRef`: Ref tracking current blob URL for revocation on regenerate/unmount.

## Rendering Pipeline

`renderSlide(ctx, slideIndex)` orchestrates:
1. `renderBg` (Solid/Geo/Custom)
2. Frame bounds computation
3. `drawTopCorner`
4. `renderSlideContent` (Heading, Body/Cards, Screenshot)
5. `drawBorderFrame`
6. `drawCenteredFooter` (Brand + Profile Pic)
7. `drawBottomCorner`

## Export Behavior (PDF)

Exports use an inline PDF builder - no external libraries or CDN dependencies.

### Helpers (in `src/App.jsx`)
- `decodeBase64ToBinary(b64)` - `atob` wrapper.
- `extractJpegBinaryFromDataUrl(dataUrl)` - splits data URL at `base64,`, returns binary JPEG string.
- `buildPdfFromJpegs(jpegPages, pageW, pageH)` - constructs raw PDF bytes. Returns a `Blob` of type `application/pdf`. Uses `%PDF-1.4`, one Image XObject per page (`/Filter /DCTDecode`), proper xref/trailer.
- `captureSlideJpegBinary(ctx, idx)` - renders slide to canvas, captures JPEG at quality 0.92, returns binary string.

### Handlers
- `downloadCurrentPDF()` - captures active slide, builds 1-page PDF, creates blob URL, sets `pdfDownload` state.
- `downloadAllPDF()` - captures all slides in order, builds multi-page PDF, restores preview to `activeSlide`.
- `clearPdfDownload()` - revokes blob URL, clears `pdfDownload` state.

### UX pattern
- No auto-open (`window.open` removed - sandbox-hostile).
- User clicks "Save {filename}" link to download.
- Link auto-dismisses 1.5s after click (blob URL revoked via `clearPdfDownload`). Manual `×` dismiss also available.
- Trust copy: "Generated locally in browser; no upload."

### Naming
- `sanitizePrefix(raw)` trims input and replaces non `[a-zA-Z0-9_-]` chars with `_`.
- Empty prefix falls back to `linkedin-slide`.
- Current slide: `{prefix}-{NN}.pdf` (1-based, zero-padded).
- All slides: `{prefix}-all.pdf`.

## Metadata

- Last updated: February 26, 2026
- Primary Artifact: `linkedin-carousel.jsx`
- Source: `src/App.jsx`
- Approx lines (artifact): ~1,877
- Status: Functional

