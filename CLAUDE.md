# FreedSolutions — Workflow Contract

## Repo Truth
- `src/` is the editable source of behavior.
- `linkedin-carousel.jsx` is the generated artifact (never edit manually).
- `build.js` is the deterministic build script that regenerates the artifact.
- `preview.html` loads the built artifact in a local browser for preview (requires a local server).

## Architecture
This is a **LinkedIn carousel slide designer** — a single-page React app that renders to HTML5 Canvas for pixel-accurate slide export.

**Runtime model:**
- React 18.2.0 (UMD from CDN) + Babel Standalone 7.26.10 (browser JSX transform)
- `preview.html` pins these versions to match the Claude.ai artifact sandbox — do not upgrade without verifying sandbox parity
- No bundler, no transpiler, no module system — source files are concatenated by `build.js` into a single JSX artifact

**Zero-dependency constraint:**
- No `package.json`, no `node_modules`, no npm. Do not add them.
- `build.js` uses only Node.js built-ins (`fs`, `path`)
- `preview.html` loads React/Babel from unpkg CDN
- This constraint is intentional — the artifact must run identically in `preview.html` and when pasted into Claude.ai's artifact sandbox

## Tool Selection Rules
Claude Code has dedicated tools that are faster and never trigger permission prompts. Always prefer them:

| Instead of Bash...    | Use this tool | Why                                    |
|-----------------------|---------------|----------------------------------------|
| `cat`, `head`, `tail` | `Read`       | Better UX, no permission needed        |
| `echo "…" > file`    | `Write`       | Atomic writes, no shell quoting issues |
| `sed`, `awk`          | `Edit`        | Structural edits, not regex gambles    |
| `find`, `ls -R`       | `Glob`        | Faster, cross-platform                 |
| `grep`, `rg`          | `Grep`        | Optimized, permission-free             |

**Bash is the right choice for:** `node build.js`, `node scripts/*.js`, all `git` commands, `npx serve`, `npx playwright`, and quick one-liners where no dedicated tool exists (`wc -l`, `pwd`, `mkdir -p`).

## Source Manifest
`build.js` defines an explicit `ORDER` array that lists all 20 source files and their concatenation sequence. **This array is the single source of truth** for what ships in the artifact and in what order.

Dependencies flow top-to-bottom in `ORDER`: each file may reference symbols defined in files above it.

**Structure at a glance:**
| Layer | Files | Purpose |
|-------|-------|---------|
| Constants | `constants.js`, `layoutTokens.js` | Shared constants, design tokens, style helpers |
| Canvas | `canvas/*.js` (7 files) | Pure rendering: backgrounds, text, overlays, screenshots, slide composition |
| Data | `slideFactory.js`, `undoRedo.js`, `pdfBuilder.js` | Slide model, undo stack, PDF generation |
| UI components | `ColorPickerInline.jsx`, `SizeControl.jsx`, `SlideSelector.jsx` | Reusable React components |
| Hooks | `useSlideManagement.js`, `useCanvasRenderer.js`, `usePdfExport.js`, `usePresets.js` | State management, rendering, export, presets |
| App | `App.jsx` | Root component, layout, event wiring |

## Symbol GPS

Quick-reference of key symbols per source file. All symbols share global scope (concatenated artifact).

### Constants Layer
**`constants.js`** — Canvas dimensions, font system, geometric shapes
- `W` (800), `H` (1000) — canvas pixel dimensions
- `MARGIN`, `BORDER_RADIUS`, `BORDER_WIDTH` — frame geometry
- `CANVAS` — layout tokens object (padding, line heights, card/screenshot/footer geometry)
- `FONT_OPTIONS`, `DEFAULT_FONT` — typography system
- `GEO_SHAPES` — `[{id, label}]` for background pattern picker
- `composeFont(family, size, weight, italic)` → ctx.font string

**`layoutTokens.js`** — UI design system
- `SPACE`, `RADIUS`, `Z`, `SIZE` — spacing/radius/z-index/component-size scales
- `SURFACE` — UI surface color palette (dark theme, 20+ keys)
- `CLR` — semantic colors (primary, danger, overlays, shadows)
- Style helpers: `panelBtn()`, `toggleBtn(isOn)`, `uploadFrameStyle()`, `uploadBtnStyle(hasFile)`, `dividerStyle()`, `dialogOverlay()`, `dialogBox(maxWidth)`, `dialogBtn(isPrimary)`

### Canvas Layer (pure rendering, no React)
**`canvas/hexToRgba.js`** — `hexToRgba(hex, opacity)` → rgba string

**`canvas/backgrounds.js`** — Background rendering
- `renderBg(ctx, bgType, solidColor, customImg, geoLines, geoEnabled, geoOpacity, geoShape)` — top-level entry point
- `drawSolidBg(ctx, color)`, `drawCustomBg(ctx, img)`, `drawGeoBg(ctx, baseColor, lineColor, geoOpacity, geoShape)`
- Shape renderers: `drawGeoLines`, `drawGeoBokeh`, `drawGeoWaves`, `drawGeoStripes`, `drawGeoHex`

**`canvas/text.js`** — Text layout and rendering
- `wrapText(ctx, text, maxWidth, fontSize, fontWeight, fontFamily, fontItalic)` → string[]
- `extractAccentMarkers(text)` → `{cleanText, markers[]}` (parses `**bold**` markers)
- `renderLineWithAccents(ctx, line, x, y, fontSize, baseWeight, baseColor, accentColor, markers, lineOffset, fontFamily, fontItalic)`

**`canvas/overlays.js`** — Footer, corners, border frame
- `drawCenteredFooter(ctx, profileImg, name, borderBottom, footerBg, footerText, textSize, opacity, fontFamily, fontBold, fontItalic)`
- `drawTopCorner(ctx, text, color, opacity, size, fontFamily, fontBold, fontItalic, bgColor, bgOpacity)`
- `drawBottomCorner(ctx, text, color, opacity, size, fontFamily, fontBold, fontItalic, bgColor, bgOpacity)`
- `drawBorderFrame(ctx, top, bottom, hasFooter, strokeColor)`

**`canvas/screenshot.js`** — `drawScreenshot(ctx, screenshot, x, y, w, h, scale, edgeToEdge)`

**`canvas/renderSlideContent.js`** — `renderSlideContent(ctx, slide, screenshot, colors, sizes, scale, frameTop, frameBottom)` — lays out heading, body/cards, screenshot within frame bounds

**`canvas/renderSlide.js`** — `renderSlideToCanvas(ctx, slideIndex, seriesSlides, slideAssets)` — top-level orchestrator: bg → corners → content → frame → footer

### Data Layer
**`slideFactory.js`** — `makeDefaultSlide(title, body)` → full slide object (~80 properties with defaults)

**`undoRedo.js`** — `createUndoManager()` → `{pushSnapshot, undo, redo, canUndo, canRedo}` (max 20 snapshots)

**`pdfBuilder.js`** — PDF generation (hand-rolled encoder, no dependencies)
- `sanitizePrefix(raw)` → safe filename string
- `buildPdfFromJpegs(jpegPages, pageW, pageH)` → Blob

### UI Components (React)
**`ColorPickerInline.jsx`** — `ColorPickerInline` — swatch button + portal dropdown with color grid, opacity slider, typography controls, geo shape picker. Also: `drawShapeThumbnail(ctx, shapeId, w, h)`

**`SizeControl.jsx`** — `SizeControl` — font-size stepper with optional color picker, opacity, and typography controls

**`SlideSelector.jsx`** — `SlideSelector` — numbered slide buttons with drag-to-reorder, remove overlay, add/duplicate

### Hooks
**`useSlideManagement.js`** — `useSlideManagement(deps)` — slide CRUD, reorder, card management, image uploads. Returns 30+ functions/state values (see file header for full list).

**`useCanvasRenderer.js`** — `useCanvasRenderer(canvasRef, seriesSlides, slideAssets, activeSlide)` — 40ms debounced rendering. Returns `{renderSlide}`.

**`usePdfExport.js`** — `usePdfExport(canvasRef, renderSlide, seriesSlides, activeSlide, exportPrefix)` → `{pdfDownload, pdfError, downloadCurrentPDF, downloadAllPDF, clearPdfDownload}`

**`usePresets.js`** — `usePresets(deps)` — preset serialize/deserialize, export/import with legacy font migration. Defines `PRESET_SLIDE_KEYS` (60+ property keys), `normalizeLegacyFontFamily()`.

### App
**`App.jsx`** — Root component. Hoisted styles: `inputStyle`, `labelStyle`, `INLINE_SWATCHES`, `smallBtnStyle`, `pickerDropdownStyle`. Wires all hooks, renders three-column layout.

## LSP Configuration
- `jsconfig.json` configures TypeScript Language Server for navigation (hover, go-to-definition, find-references).
- `checkJs: false` — diagnostics disabled to avoid false positives from missing React types and global scope model.
- No `@types/react` — would require npm, violating zero-dep constraint. React API hover info unavailable by design.

## Workflow: Write → Build → See → Push

### 1. Write
Edit source files in `src/`.

**Adding a new source file:**
1. Create the file in `src/` (or `src/canvas/` for rendering code)
2. Add it to the `ORDER` array in `build.js` at the correct dependency position
3. Rebuild — the build will fail if a file is in `ORDER` but missing on disk, but will **silently exclude** a file that exists on disk but is not in `ORDER`

### 2. Build
```bash
node build.js
```
Required after any `src/` change. No exceptions.

### 3. See
Serve the repo root locally and open `preview.html` in a browser. The preview loads the built artifact directly — what you see is what ships. Refresh after each build.

```bash
npx serve . --listen 5173
# then open http://localhost:5173/preview.html
```

For visual/UX judgment calls on new features, use browser Claude as a second pair of eyes. Describe what changed and what to look at — no structured handoff card needed.

### 4. Push
```bash
git push origin main
```

## Feature Flow

### Phase 1 — Get the card

*Trigger A — In-session (feature described in chat):*
Adam describes the feature in Claude Code chat. Claude asks the number of scope/approach questions needed for alignment (typically ~2–6, but more when ambiguity/risk is high), then writes `FEATURE_CARD.md` (replacing the entire file).
Claude must send those questions to the user in plain chat (drafting internally does not count) and wait for answers before writing the card.
Do not use the `AskUserQuestion` tool for this gate.

*Trigger B — External card (card written elsewhere):*
Adam updates `FEATURE_CARD.md` outside this session and types `SHIP` in chat.

### Phase 2 — Explore & ask

Claude reads `FEATURE_CARD.md` and explores the relevant source files in the repo. Then asks the number of implementation questions needed for alignment (typically ~2–6, but more when ambiguity/risk is high) based on what it found (approach choices, ambiguities, edge cases, patterns to reuse or avoid). Once answered, the autonomous SHIP loop starts.
Claude must send questions as an explicit plain-chat message and pause for user answers. Preparing questions without sending them is not completion of this phase.
Do not use the `AskUserQuestion` tool for this gate.
If no questions are needed, Claude must explicitly send: `No blocking questions; proceeding with stated assumptions:` followed by a short assumptions list.
If any response payload is empty/unclear (for example, blank tool-return text), do not treat it as answered. Re-ask in plain chat and wait for a concrete user reply.

This is the single pause point before code changes begin.

### Phase 3 — SHIP loop (autonomous, no pausing)

> **Autonomy expectation:** This entire phase runs without user interaction. If an unexpected permission prompt appears, accept it, complete the phase, and report the unexpected prompt in the handoff so settings can be updated.

> **Pre-flight checklist** (all must be true before starting):
> - Local server running on `:5173` (`npx serve . --listen 5173`)
> - Playwright MCP available and responsive
> - Git working tree clean (`git status` shows no uncommitted changes)
> - `FEATURE_CARD.md` present with current feature scope

**Implement:**
- Read `FEATURE_CARD.md` scope and `CLAUDE.md` guardrails
- Make targeted edits in `src/`
- If a new source file was created, add it to `ORDER` in `build.js`
- Run `node build.js` — fix any build errors before continuing

**Self-review:**
- Review own diff against `FEATURE_CARD.md` scope (anything missing? anything out of scope?)
- Review code quality: bugs, regressions, risks — severity ordered
- Patch issues, rebuild, repeat until clean

**Smoke test (via Playwright MCP):**
Use `/smoke` (test only) or `/build-test` (build + test) skills for structured smoke testing. These skills handle pre-flight checks, navigation, interaction, screenshots, and mandatory browser cleanup automatically. Available skills:
- `/smoke-preflight` — validate prerequisites (server, build freshness, git state, Playwright)
- `/smoke [description]` — run smoke test (defaults to FEATURE_CARD.md scope, or pass `full` for standard checklist)
- `/smoke-close` — guarantee clean browser teardown (auto-invocable safety net)
- `/smoke-deep [area]` — extended 12-step test (color pickers, geo shapes, toggles, sizes, slide CRUD with confirm dialogs)
- `/build-test [description]` — build artifact then immediately smoke test

Manual Playwright MCP usage is still permitted when skills don't cover the scenario. Core rules remain:
- Always close the Playwright page/context/browser after each smoke-test attempt (pass or fail)
- If issues found: close Playwright first, then patch, rebuild, and re-test in a fresh Playwright browser session
- If Playwright MCP is unavailable or the local server isn't running, stop and ask the user to fix it before continuing

**Commit gate (final step before review):**
- Run `node scripts/archive-smoke-artifacts.js` to file away Playwright MCP logs, `test-results/` output, and all untracked root image artifacts (any `.png/.jpg/.jpeg/.webp/.gif` name)
- Add `CHANGES.md` entry if behavior changed
- Verify `git status` reflects only intended task files
- Commit all changed files atomically (source + artifact + docs)
- Report commit hash (`git rev-parse --short HEAD`) in the handoff
- Do NOT push

### Phase 4 — Your review (post-commit only)
Claude Code pauses only after the Commit gate is complete. Review the diff. Then either:
- Request patches: describe what to fix, Claude Code patches and re-runs from self-review onward
- Push: `git push origin main`

## Project Files

**Docs** (update per Documentation Update Rules below):
| File | Purpose | Updated when |
|------|---------|-------------|
| `CLAUDE.md` | Workflow contract | Workflow/process changes |
| `CHANGES.md` | Behavior/process changelog | Behavior or process changes |
| `CHANGES_ARCHIVE.md` | Archived changelog entries | When `CHANGES.md` is trimmed |
| `FEATURE_CARD.md` | Current feature scope | Replaced each new feature session |

**Code artifacts** (rarely touched directly):
| File | Purpose | Updated when |
|------|---------|-------------|
| `build.js` | Deterministic concatenation build | New source file added to `ORDER` |
| `preview.html` | Local browser preview harness | React/Babel version pin changes |
| `linkedin-carousel.jsx` | Generated artifact — never edit | Every build |

## Git Policy
- Direct push to `main`.
- Single atomic commit per task (source + artifact + docs together).
- Working tree clean after commit.
- Review handoff must include the local commit hash.
- Commit message style: imperative mood, sentence case, no trailing period. ~72 chars max. Use colons or `+` for multi-part summaries.
- Commit-time artifact hygiene is automated by `.githooks/pre-commit` (one-time setup per clone: `git config core.hooksPath .githooks`).

## Permission Preflight
- Local permissions (`settings.local.json`) grant unrestricted Bash access. Permission prompts should never appear during normal workflow.
- If a prompt does appear, it indicates configuration drift. Before requesting approval:
  1. Check `.claude/settings.local.json` then `.claude/settings.json`
  2. Verify the action is not in a `deny` list
  3. If allowed by config but still prompted, note the exact command for debugging
- Do not request broad or speculative approvals for actions you are not about to run.

## Hard Guardrails
- Do not edit `linkedin-carousel.jsx` manually — always regenerate via `node build.js`.
- Do not skip build after source change.
- Verify changes visually in `preview.html` before pushing UI changes.
- Do not add `package.json`, `node_modules`, or npm dependencies — the repo is intentionally zero-dep.
- When adding a new source file, add it to `ORDER` in `build.js` — files not in `ORDER` are silently excluded from the artifact.
- Do not commit without a passing Playwright smoke test. If the smoke test cannot run, stop and ask.
- Do not proceed to Commit gate while any Playwright smoke-test browser window/session is still open.
- Do not commit raw Playwright MCP logs, `test-results/` artifacts, or untracked root image artifacts; archive them via `node scripts/archive-smoke-artifacts.js`.
- Do not hand off for user review until a local commit is created and its hash is reported.
- If an unexpected permission prompt appears during Phase 3, accept it and report it in the handoff. Do not stop the SHIP loop for permission debugging.
- Do not start Phase 3 code changes until the Phase 1/2 question message has been sent and answered (or a no-blockers assumptions message has been sent).
- Do not use `AskUserQuestion` for Phase 1/2 alignment gates; ask in plain chat and wait for explicit user responses.

## Documentation Update Rules
- `CLAUDE.md`: update only when workflow/contracts change.
- `CHANGES.md`: add entry when behavior or process changes. Pure refactors with no behavior effect skip this. When `CHANGES.md` exceeds ~300 lines, move the older half of entries to `CHANGES_ARCHIVE.md`.
