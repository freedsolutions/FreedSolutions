# CHANGES
Operational change log for behavior and workflow updates in this repo.
Add newest entries at the top.

## 2026-03-01 - Editor column responsiveness and decorator toggle placement polish
- What changed: Refined Column 2/3 layout behavior and moved the decorator toggle to align with heading controls.
  - **Decorator toggle relocation**: The accent/checkmark toggle now appears in the `HEADING` row next to the ON/OFF toggle, and was removed from the Body/Cards color swatch row.
  - **Column 2 min width**: Increased Slide Editor pane minimum width from `260` to `300` to prevent right-edge control overflow (notably `+` buttons) at narrower app widths.
  - **Column 3 growth behavior**: Preview pane now uses flexible sizing (`flex: 1 1 360px`, `minWidth: 320`, `maxWidth: 520`) instead of fixed auto width, so it grows alongside Column 2 on wide screens.
  - **Responsive preview canvas sizing**: Preview canvas style changed from fixed `360x450` CSS size to `width: 100%`, `height: auto` so it scales with Column 3 width while preserving aspect ratio.
- Why: Keep controls fully visible in the editor pane and improve horizontal space distribution between editor and preview on larger displays.
- Files: `src/App.jsx`, `linkedin-carousel.jsx`, `CHANGES.md`.
- Validation: `node build.js` succeeds and regenerated bundle reflects updated flex/canvas sizing.
- Notes/Risks: Preview can render larger than before on wide windows (bounded by `maxWidth: 520`); no canvas export/render math changes.

## 2026-03-01 - Normalize legacy Georgia preset fonts to Cambria stack
- What changed: Preset loading now maps legacy font values of `"Georgia, serif"` to `"Cambria, Georgia, serif"` for all `*FontFamily` slide fields.
- Why: Prevent the font dropdown from entering an unmatched value state when loading older presets saved before Georgia was replaced by Cambria.
- Files: `src/usePresets.js`, `linkedin-carousel.jsx`, `CHANGES.md`.
- Validation: `node build.js` succeeds; preset load path normalizes legacy Georgia values while preserving serif rendering.
- Notes/Risks: Mapping only runs during preset load and does not alter non-Georgia font values.

## 2026-03-01 - Screenshot expansion, edge-to-edge, accent bar tie-in, Top Corner case freedom, font swap
- What changed: Six layout and UX improvements in a single feature pass.
  - **Expand Screenshots toggle**: New per-slide `expandScreenshot` boolean (default `false`) with toggle button in Body/Cards section header row. When ON: body/cards content zone is compressed vertically, screenshot minimum Y threshold drops from 420 to 300, and screenshot renders edge-to-edge (full canvas width, 0px horizontal margin, no rounded corners at slide edge).
  - **Accent bar / checkmark tie-in**: When expand is ON, accent bar offset reduced from 10px to 0px; card start Y reduced from 45 to 20 (with heading) or 60 to 30 (without); body start Y reduced from 100 to 40 (with heading) or 60 to 30 (without).
  - **Edge-to-edge screenshots**: `drawScreenshot()` now accepts an `edgeToEdge` parameter; when true, clip radius is 0 and the clip/draw region uses `(0, ssY, W, ssH)` instead of `(pad, ssY, maxW, ssH)`.
  - **Top Corner case freedom**: Removed `.toUpperCase()` in `drawTopCorner()` so text renders exactly as typed.
  - **Font swap**: Replaced Georgia with Cambria in `FONT_OPTIONS` (`"Cambria, Georgia, serif"`); Georgia remains in fallback chain.
  - **Auto-overwrite screenshots**: Verified no confirmation prompt exists in upload or paste flows; behavior already correct.
- Why: Give users more control over screenshot real estate and layout density, remove forced uppercase on Top Corner text, and provide a smoother serif font alternative.
- Files: `src/slideFactory.js`, `src/usePresets.js`, `src/App.jsx`, `src/canvas/renderSlideContent.js`, `src/canvas/screenshot.js`, `src/canvas/overlays.js`, `src/constants.js`, `linkedin-carousel.jsx` (regenerated), `CHANGES.md`, `SMOKE_TEST.md`, `FEATURE_CARD.md`.
- Validation: `node build.js` succeeds. New `expandScreenshot` property in factory/preset/UI/canvas. `.toUpperCase()` removed from `drawTopCorner`. Cambria in `FONT_OPTIONS`. No `confirm()` in screenshot upload/paste paths.
- Notes/Risks: Vertical compression when expand is ON may cause text truncation on slides with long body text — mitigated by toggle being off by default. Edge-to-edge screenshot draws under border frame overlay. Cambria availability depends on system; Georgia in fallback chain. `expandScreenshot` absent from older presets defaults to `false` via `makeDefaultSlide()`.

## 2026-02-28 - Fix paste screenshot target slide race
- What changed: Pasted screenshot assignment now captures the active slide index at paste time instead of reading it later inside async image load callbacks.
  - In `App.jsx` paste handler, store `targetSlide` before `FileReader`/`Image` async work.
  - Use `targetSlide` for both auto-enabling `showScreenshot` and `setAsset(...)`.
  - Regenerated `linkedin-carousel.jsx` via build.
- Why: Prevent pasted screenshots from landing on the wrong slide if the user changes active slide immediately after pressing paste.
- Files: `src/App.jsx`, `linkedin-carousel.jsx`, `CHANGES.md`.
- Validation: `node build.js` succeeds; bundled artifact uses `targetSlide` in paste handler.
- Notes/Risks: Undo behavior remains unchanged from existing screenshot upload flow.

## 2026-02-28 - Remove screenshot bounds frame and add paste screenshot support
- What changed: Two addendum improvements to the screenshot feature.
  - **Screenshot bounds frame removed**: Removed the solid 1px `rgba(255,255,255,0.1)` border stroke drawn around uploaded screenshots on canvas in `drawScreenshot()`. The rounded-rect clip path and image placement are unchanged; only the visible border is removed.
  - **Paste screenshot support**: Added a global `paste` event listener in `App.jsx` that detects image data in the clipboard and loads it as the active slide screenshot. Uses the same `setAsset()` flow as file uploads. Auto-enables `showScreenshot` if it is currently OFF. Skips when focus is in `INPUT`, `TEXTAREA`, or `SELECT` elements to preserve normal text paste. Uses ref-based indirection (`activeSlideRef`, `seriesSlidesRef`, `slideMgmtRef`) so the listener registers once.
- Why: Remove visual clutter from screenshot rendering; let users paste screenshots from clipboard (Snipping Tool, browser copy, etc.) without needing the file picker.
- Files: `src/canvas/screenshot.js`, `src/App.jsx`, `linkedin-carousel.jsx` (regenerated), `SMOKE_TEST.md`, `FEATURE_CARD.md`, `CHANGES.md`.
- Validation: `node build.js` succeeds with 19 source files. Artifact confirms: no `ctx.stroke()` after `drawImage` in `drawScreenshot()`; paste handler registered with `addEventListener("paste")`; pasted images set via `setAsset()` with `"pasted-image.png"` filename.
- Notes/Risks: Paste handler depends on `clipboardData.items` API — exits gracefully if absent. The empty-state dashed placeholder outline (no screenshot uploaded) is preserved as a visual hint.

## 2026-02-28 - Relocate decorator toggles before color swatches
- What changed: Moved the accent bar (`—`) and checkmark (`✓`) decorator toggles from the Body/Cards toggle row to immediately before the Text/Base color swatches.
  - Previous layout: `Body/Cards toggle → decorator toggle → font size → color swatches → textarea`
  - New layout: `Body/Cards toggle → font size → decorator toggle → color swatches → textarea`
  - Font size stepper moved up into the Body/Cards toggle row (right-aligned).
  - Decorator toggle now shares a row with the Text and Base color swatches, appearing as the first element.
  - No state or behavior changes — only the DOM position within Column 2.
- Why: Group the decorator toggle with visual styling controls (color swatches) rather than with content structure controls (mode switch), creating a more natural editing flow.
- Files: `src/App.jsx`, `linkedin-carousel.jsx` (regenerated), `SMOKE_TEST.md`, `CHANGES.md`.
- Validation: `node build.js` succeeds with 19 source files. Artifact confirms new DOM order: Body/Cards toggle + font stepper, then decorator toggle + swatches.
- Notes/Risks: Pure layout change — no state, behavior, or canvas rendering modifications.

## 2026-02-28 - Fix undo snapshotting for typography controls
- What changed: Typography mutations now push undo snapshots before state updates, so `Ctrl+Z` reliably reverts font family, bold, and italic changes.
  - Updated typography setters in `src/App.jsx` for all five text elements (heading, body/cards, brand name, top corner, bottom corner) to call `updateSlide(..., true)`.
  - Regenerated `linkedin-carousel.jsx` via build so bundled output matches source.
- Why: The typography feature introduced new mutations without snapshot pushes, which made those changes non-undoable in normal editing flow.
- Files: `src/App.jsx`, `linkedin-carousel.jsx`.
- Validation: `node build.js` succeeds; grep confirms typography setters now pass snapshot flag `true`.
- Notes/Risks: This does not change legacy undo behavior for unrelated existing controls that still mutate without snapshots.

## 2026-02-28 - Typography controls (bold/italic + font selector) in color swatch pop-ups
- What changed: Added per-element typography controls — font family selector, bold toggle, and italic toggle — inside every color swatch pop-up.
  - Added `composeFont()` helper in `constants.js` to build valid `ctx.font` strings from family, size, weight, and italic parameters.
  - Added `FONT_OPTIONS` constant with 5 system-safe fonts: Helvetica Neue, Georgia, Courier New, Arial, Trebuchet MS.
  - Added 15 new per-slide state properties (3 per text element × 5 elements): `*FontFamily`, `*Bold`, `*Italic` for title, body, card, brandName, topCorner, bottomCorner.
  - Initialized all new properties in `makeDefaultSlide()` with backward-compatible defaults (current look preserved).
  - Added new properties to `PRESET_SLIDE_KEYS` for preset save/load round-trip; older presets without these fields load cleanly via `makeDefaultSlide()` fallback.
  - Extended `ColorPickerInline` component with optional typography props: `fontFamily`/`onFontFamilyChange`, `bold`/`onBoldChange`, `italic`/`onItalicChange`.
  - Extended `SizeControl` component with optional typography props: `fontFamily`/`fontFamilySet`, `boldVal`/`boldSet`, `italicVal`/`italicSet`.
  - Typography controls (font dropdown + B/I toggles) appear above the swatch grid inside the popover when typography props are provided.
  - Wired typography props for all 5 text elements in `App.jsx`: Heading, Body/Cards (context-aware), Brand Name, Top Corner, Bottom Corner.
  - Updated all canvas rendering to use `composeFont()`: `text.js` (`wrapText`, `renderLineWithAccents`), `renderSlideContent.js`, `overlays.js` (`drawCenteredFooter`, `drawTopCorner`, `drawBottomCorner`), `renderSlide.js`.
  - Canvas text measurement (`ctx.measureText`) now runs after setting the composed font with correct family/weight/italic, ensuring accurate wrapping and layout.
  - Undo support is automatic — typography state is part of `seriesSlides` captured in full snapshots.
- Why: Give users per-slide typographic control with font family, bold, and italic, co-located inside existing color popovers to avoid cluttering the UI.
- Files: `src/constants.js`, `src/slideFactory.js`, `src/usePresets.js`, `src/ColorPickerInline.jsx`, `src/SizeControl.jsx`, `src/App.jsx`, `src/canvas/text.js`, `src/canvas/renderSlideContent.js`, `src/canvas/overlays.js`, `src/canvas/renderSlide.js`, `linkedin-carousel.jsx` (regenerated), `CHANGES.md`, `SMOKE_TEST.md`.
- Validation: `node build.js` succeeds with 19 source files. Grep confirms: `composeFont` (12 occurrences), `FONT_OPTIONS` (3), `DEFAULT_FONT` (18), `titleFontFamily` (4), `bodyFontFamily` (5), `cardFontFamily` (5), `brandNameFontFamily` (4), `fontFamilySet` (8), `onFontFamilyChange` (4).
- Notes/Risks: Font metrics vary across families — all layout math (wrapping, accent bar positioning, card sizing) re-measures with the active font via `composeFont()`. Older presets without typography fields load cleanly because `makeDefaultSlide()` provides defaults and `PRESET_SLIDE_KEYS` iteration only copies present keys.

## 2026-02-28 - 4-step prescriptive workflow with hardened agent outputs
- What changed: Redesigned the workflow from 3 phases to 4 explicit steps, hardened every agent to output prescriptive next-step text, and consolidated human-facing docs.
  - Merged `WORKFLOW_QUICKSTART.txt` into the top of `CLAUDE.md` as a human-facing quickstart section; deleted the standalone file.
  - Deleted `SMOKE_TEST_HANDOFF_TEMPLATE.md` (legacy compatibility pointer); `SMOKE_TEST.md` is now the only handoff file.
  - Reframed workflow as 4 steps:
    1. Step 1 (Browser Claude UI): draft `FEATURE_CARD.md`
    2. Step 2 (Claude Code): implement + commit + output ready-to-paste Codex command with hash
    3. Step 3 (Codex): review/patch + output full SMOKE_TEST.md contents in chat for copy/paste
    4. Step 4 (Browser Extension): smoke test + output prescriptive feedback block on failure
  - Added smoke failure feedback loop: Step 4 outputs a `SMOKE_FEEDBACK:` block that gets pasted back into Step 3 Codex thread for patching.
  - Updated all agent specs (`claude-feature-implementer.md`, `codex-commit-review-patcher.md`, `browser-smoke-tester.md`) with explicit required output sections including prescriptive next-step text.
  - Codex agent now includes `Handling Smoke Feedback` section for processing pasted failure blocks.
  - `CHANGES.md` ownership clarified: Step 2 (Claude Code) owns entries; Step 3 (Codex) only adds entries if patches change behavior.
  - Removed legacy fallback from `scripts/prepare-smoke-handoff.js` (no longer searches for `SMOKE_TEST_HANDOFF_TEMPLATE.md`).
  - Added hard guardrail: "Every step must output prescriptive text for the next step (no dead-end outputs)."
- Why: Eliminate dead-end agent outputs that leave the human guessing what to do next. Every step now tells you exactly what to copy/paste for the next step.
- Files: `CLAUDE.md` (rewritten), `WORKFLOW_QUICKSTART.txt` (deleted), `SMOKE_TEST_HANDOFF_TEMPLATE.md` (deleted), `agents/claude-feature-implementer.md` (updated), `agents/codex-commit-review-patcher.md` (updated), `agents/browser-smoke-tester.md` (updated), `agents/README.md` (updated), `scripts/prepare-smoke-handoff.js` (updated), `CHANGES.md` (updated).
- Validation: `node scripts/prepare-smoke-handoff.js` succeeds with `SMOKE_TEST.md` only. No remaining references to deleted files in active workflow docs.
- Notes/Risks: Historical CHANGES.md entries still reference `SMOKE_TEST_HANDOFF_TEMPLATE.md` and `WORKFLOW_QUICKSTART.txt` — this is expected (changelog history).

## 2026-02-28 - Smoke handoff rename and paste-only browser kickoff
- What changed: Standardized smoke handoff naming and browser execution instructions.
  - Added `SMOKE_TEST.md` as the canonical smoke handoff card.
  - Updated workflow/agent command references to use `SMOKE_TEST.md`.
  - Updated Step 4 browser kickoff to paste-only:
    - `SMOKE: In browser Claude extension, paste the full contents of SMOKE_TEST.md into a new thread and run smoke tests. DO NOT CLOSE OUT THE BROWSER.`
  - Embedded browser smoke execution contract inside `SMOKE_TEST.md` so browser runs do not depend on loading repo files.
  - Converted `SMOKE_TEST_HANDOFF_TEMPLATE.md` into a one-cycle compatibility/deprecation pointer.
  - Updated `scripts/prepare-smoke-handoff.js` to resolve handoff files in this order:
    1) `SMOKE_TEST.md`
    2) `SMOKE_TEST_HANDOFF_TEMPLATE.md` (fallback)
- Why: Reduce handoff friction, match browser extension constraints (paste workflow), and make browser execution instructions explicit and self-contained.
- Files: `SMOKE_TEST.md` (added), `SMOKE_TEST_HANDOFF_TEMPLATE.md` (compatibility pointer), `scripts/prepare-smoke-handoff.js` (updated), `WORKFLOW_QUICKSTART.txt` (updated), `CLAUDE.md` (updated), `agents/README.md` (updated), `agents/codex-commit-review-patcher.md` (updated), `agents/terminal-feature-flow.md` (updated), `agents/browser-smoke-tester.md` (updated), `CHANGES.md` (updated).
- Validation: `node scripts/prepare-smoke-handoff.js` updates `SMOKE_TEST.md`; active workflow docs now reference paste-only browser kickoff and include `DO NOT CLOSE OUT THE BROWSER`.
- Notes/Risks: Legacy filename compatibility is temporary and should be removed after one release cycle.

## 2026-02-28 - Prescriptive Claude -> Codex -> Browser phase workflow
- What changed: Replaced the prior single-owner default with an explicit back-to-back three-phase workflow.
  - Updated `CLAUDE.md` to make phase order mandatory:
    - Phase 1 (Claude Code): implement + validate + commit
    - Phase 2 (Codex): review Claude commit + patch/recommit + finalize handoff
    - Phase 3 (Browser): smoke test only from provided handoff context
  - Added strict phase kickoff commands:
    - `CLAUDE_PHASE: Use agents/claude-feature-implementer.md with FEATURE_CARD.md.`
    - `CODEX_PHASE: Use agents/codex-commit-review-patcher.md to review and patch commit <hash>, then finalize SMOKE_TEST_HANDOFF_TEMPLATE.md.`
    - `SMOKE: Use agents/browser-smoke-tester.md and SMOKE_TEST_HANDOFF_TEMPLATE.md.`
  - Added phase-specific output contracts and gate lines (`HANDOFF_TO_CODEX`, `DO NOT PUSH YET - Awaiting browser smoke RESULT`).
  - Added new agent specs:
    - `agents/claude-feature-implementer.md`
    - `agents/codex-commit-review-patcher.md`
  - Updated `agents/README.md` to document the new mandatory sequence.
  - Marked `agents/terminal-feature-flow.md` as legacy (non-default).
- Why: Match actual operating model where Claude and Codex run distinct responsibilities sequentially before browser smoke.
- Files: `CLAUDE.md` (updated), `agents/README.md` (updated), `agents/claude-feature-implementer.md` (added), `agents/codex-commit-review-patcher.md` (added), `agents/terminal-feature-flow.md` (updated), `CHANGES.md` (updated).
- Validation: Verified docs now define one canonical default sequence with explicit phase gates and exact kickoff commands.
- Notes/Risks: Keep using `node scripts/prepare-smoke-handoff.js` in Phase 2 so smoke metadata tracks the final commit under test.

## 2026-02-28 - One-command SHIP flow and handoff metadata automation
- What changed: Added a single-command terminal delivery flow and automated smoke handoff metadata stamping.
  - Added `agents/terminal-feature-flow.md` as the execution spec for end-to-end terminal work:
    - implement from `FEATURE_CARD.md`
    - build and validate
    - commit
    - commit review
    - patch/recommit review loop
    - smoke handoff prep
  - Added `scripts/prepare-smoke-handoff.js` to update `SMOKE_TEST_HANDOFF_TEMPLATE.md` with:
    - current short commit hash from `git rev-parse --short HEAD`
    - build confirmation date stamp in `YYYY-MM-DD`
  - Updated `CLAUDE.md`:
    - new preferred kickoff trigger:
      - `SHIP: Use agents/terminal-feature-flow.md with FEATURE_CARD.md and produce a completed SMOKE_TEST_HANDOFF_TEMPLATE.md.`
    - added `SHIP` output contract (includes commit-review summary)
    - updated checklist and required commands to include `node scripts/prepare-smoke-handoff.js`
    - expanded active agent specs to include terminal + browser roles
  - Updated `agents/README.md` to register both agent specs and document the `SHIP` -> `SMOKE` sequence.
- Why: Remove repeated manual coordination steps and make feature delivery + smoke handoff startable from one command with consistent outputs.
- Files: `CLAUDE.md` (updated), `agents/README.md` (updated), `agents/terminal-feature-flow.md` (added), `scripts/prepare-smoke-handoff.js` (added), `CHANGES.md` (updated).
- Validation: Script parses and rewrites expected handoff lines; workflow docs now contain a single canonical kickoff command and updated required command list.
- Notes/Risks: `scripts/prepare-smoke-handoff.js` should run after commit so the handoff hash matches the exact commit under test.

## 2026-02-28 - Column 2 text UX overhaul, decorator toggles, canvas wrapping, visual polish
- What changed: Overhauled text editing UX and canvas rendering across Column 2, separated decorator controls, updated defaults, and added visual polish.
  - Converted all Column 2 text inputs (Brand Name, Top Corner, Bottom Corner, Heading, Card inputs) to auto-expanding `<textarea>` elements that grow line-by-line up to `max-height: 50vh`.
  - Replaced fixed `rows={2}` on Body textarea with dynamic auto-expanding behavior.
  - Added multi-line support for Heading canvas rendering: splits on `\n`, then wraps each line within bounding box.
  - Added multi-line support for Card canvas rendering: splits on `\n`, then wraps each line within card bounding box.
  - Separated decorator toggles: accent bar (`—`) toggle now appears only in Body mode; new checkmark (`✓`) toggle appears only in Cards mode. Both independent per-slide, default ON.
  - Added `showCardChecks` per-slide property to `makeDefaultSlide()` and `PRESET_SLIDE_KEYS` for preset round-trip.
  - Canvas card renderer conditionally renders checkmark circles based on `showCardChecks`.
  - Changed default accent color from `#22c55e` (green) to `#a5b4fc` (soft indigo) in `slideFactory.js` (`bodyColor`, `accentColor`) and `useSlideManagement.js` (`resetBgToDefault`).
  - Added horizontal divider (`1px solid #333`) above the Screenshot section in Column 1.
  - `GREEN` constant remains `#22c55e` for functional UI toggle backgrounds (ON buttons).
- Why: Improve text editing ergonomics, enable multi-line heading/card content, give users independent decorator control, and refresh default accent color.
- Files: `src/App.jsx`, `src/slideFactory.js`, `src/useSlideManagement.js`, `src/usePresets.js`, `src/canvas/renderSlideContent.js`, `linkedin-carousel.jsx` (regenerated), `CHANGES.md`, `FEATURE_CARD.md`.
- Validation: `node build.js` succeeds with 19 source files. Grep confirms: 6 `<textarea` elements in artifact, `showCardChecks` in factory/preset/canvas/UI, `#a5b4fc` default accent, heading `\n` split, card `\n` split, `#333` separator.
- Notes/Risks: `showCardChecks` defaults to `true` via `!== false` guard for backward-compat with presets that lack the property. Existing presets without `showCardChecks` will still show checkmarks.

## 2026-02-27 - Bug-hardening pass: constants, preset validation, reorder, undo listener, snapshots
- What changed: Centralized slide limits, hardened preset import, fixed reorder consistency, stabilized undo/redo listener, and defensively copied undo snapshots.
  - Added `MAX_SLIDES` constant to `src/constants.js`; replaced all hard-coded `10` slide-limit checks in `useSlideManagement.js`, `SlideSelector.jsx`, and `App.jsx`.
  - Added strict `validatePresetData()` in `usePresets.js`: rejects non-object/null slide entries, enforces `MAX_SLIDES` limit with clear error, validates shape before confirm dialog.
  - Wrapped `loadPresetData()` call in try/catch to surface failures as `presetError`.
  - Added `Image.onerror` handlers for profile, background, and screenshot data-url loads in preset loading.
  - Refactored `reorderSlide` in `useSlideManagement.js` so index map is built once from a single snapshot length and shared by `setSlideAssets` and `setActiveSlide`.
  - Stabilized undo/redo keydown listener in `App.jsx`: now uses ref-based indirection (`captureSnapshotRef`, `restoreSnapshotRef`) with a `[]` dependency array so the listener registers once instead of every render.
  - `captureSnapshot()` now shallow-copies `seriesSlides` (including each slide's `cards` array), `slideAssets` entries, and `sizes` to prevent reference fragility while preserving Image object references.
- Why: Reduce fragility from hard-coded limits, reject malformed preset files early, prevent silent image load failures, ensure reorder correctness, and eliminate unnecessary listener churn.
- Files: `src/constants.js`, `src/useSlideManagement.js`, `src/SlideSelector.jsx`, `src/App.jsx`, `src/usePresets.js`, `linkedin-carousel.jsx` (regenerated), `CHANGES.md`.
- Validation: `node build.js` succeeds. Grep confirms `MAX_SLIDES` usage, `onerror`/`validate` in presets, stable listener registration.
- Notes/Risks: `MAX_SLIDES` is a module-scope var consumed by build concatenation; changing it requires only one edit. Preset validation rejects (not truncates) oversized presets.

## 2026-02-27 - Enforced terminal handoff package before browser smoke
- What changed: Strengthened workflow contracts so terminal implementation must hand off commit + smoke card before browser testing starts.
  - Updated `CLAUDE.md` with a strict `IMPLEMENT Output Contract`.
  - Added required handoff artifacts: commit hash, validation summary, and fully filled `SMOKE_TEST_HANDOFF_TEMPLATE.md`.
  - Added terminal-to-browser checkpoint: do not begin browser smoke without the handoff package.
  - Updated pre-smoke command list to include returning the filled smoke card.
  - Updated `SMOKE_TEST_HANDOFF_TEMPLATE.md` with a required "Feature-Specific Scenarios" section derived from feature acceptance criteria.
- Why: Prevent recurring execution gaps where terminal flow stops before commit or before preparing browser smoke scenarios.
- Files: `CLAUDE.md` (updated), `SMOKE_TEST_HANDOFF_TEMPLATE.md` (updated), `CHANGES.md` (updated).
- Validation: Verified new contract text and required fields are present in both workflow and template docs.
- Notes/Risks: This is process-only; enforcement still depends on following the documented gate.

## 2026-02-27 - Lean workflow consolidation and assistance pause token
- What changed: Consolidated the handoff workflow into a lean, prescriptive docs set and added a browser roadblock pause/resume contract.
  - Updated `CLAUDE.md` to define the lean core docs, active browser smoke agent, explicit browser pause/resume contracts, and a prescriptive 12-step human execution checklist.
  - Added non-upload roadblock pause/resume tokens:
    - `PAUSE_FOR_ASSISTANCE: <roadblock + requested human action>`
    - `ASSISTANCE_DONE: <what was done>`
  - Updated `SMOKE_TEST_HANDOFF_TEMPLATE.md` to include assistance pause/resume handling and explicit `FOLLOW_UP_FIXES` output.
  - Updated `agents/browser-smoke-tester.md` to pause for both file upload and progress-blocking roadblocks.
  - Simplified `agents/README.md` to a single active agent spec (`browser-smoke-tester.md`).
  - Removed legacy agent specs:
    - `agents/planner.md`
    - `agents/implementer.md`
    - `agents/reviewer.md`
- Why: Reduce workflow complexity while preserving a repeatable, human-in-the-loop process for terminal implementation and browser smoke handoffs.
- Files: `CLAUDE.md` (updated), `SMOKE_TEST_HANDOFF_TEMPLATE.md` (updated), `agents/browser-smoke-tester.md` (updated), `agents/README.md` (updated), `agents/planner.md` (deleted), `agents/implementer.md` (deleted), `agents/reviewer.md` (deleted), `CHANGES.md` (updated).
- Validation: Verified required tokens and checklist entries exist; verified no stale references to deleted agent specs remain.
- Notes/Risks: This is a process/docs-only change. Execution quality still depends on complete smoke handoff cards and explicit human responses to pause tokens.

## 2026-02-27 - Browser smoke handoff workflow added
- What changed: Added an explicit terminal-to-browser smoke-test handoff workflow with human-in-the-loop pause/resume control for file uploads.
  - Updated `CLAUDE.md` with a new `Browser Smoke Test Handoff (Human-in-the-Loop)` section.
  - Added strict pause/resume tokens for Windows file picker steps:
    - `PAUSE_FOR_FILE_UPLOAD: <instruction>`
    - `UPLOAD_DONE: <what was uploaded>`
  - Added smoke gate contract: commit may occur before smoke testing; push is blocked until `RESULT: PASS`.
  - Updated required flow and commands to split pre-smoke vs post-smoke push behavior.
  - Added `agents/browser-smoke-tester.md` for browser-only smoke testing behavior and output format.
  - Added `SMOKE_TEST_HANDOFF_TEMPLATE.md` as the reusable handoff card.
  - Updated `agents/README.md` to register the new browser smoke tester spec.
- Why: Browser extension sessions are context-isolated and need explicit, repeatable test guidance and pause points for OS file dialogs.
- Files: `CLAUDE.md` (updated), `agents/README.md` (updated), `agents/browser-smoke-tester.md` (added), `SMOKE_TEST_HANDOFF_TEMPLATE.md` (added), `CHANGES.md` (updated).
- Validation: Verified docs reference the new smoke workflow, pause/resume tokens, gate timing, new agent spec, and reusable handoff template.
- Notes/Risks: This is a process-only change. Smoke quality still depends on accurate manual execution and complete handoff cards.

## 2026-02-27 - Pass 3: Complete extraction and redo hotkey fix
- What changed: Finished extracting App.jsx into focused hooks and components; fixed redo hotkey robustness.
  - Extracted `src/useSlideManagement.js` — slide CRUD, reorder, duplicate, card management, image uploads (360 lines).
  - Extracted `src/useCanvasRenderer.js` — canvas rendering with 40ms debounce (33 lines).
  - Extracted `src/usePdfExport.js` — PDF generation, download state, cleanup (95 lines).
  - Extracted `src/usePresets.js` — preset serialize/deserialize, export/import, stale-load guard (292 lines). `PRESET_SLIDE_KEYS` moved to module scope.
  - Extracted `src/SizeControl.jsx` — font-size stepper with optional color picker and opacity (75 lines). Replaces inline `sizeLabel` function.
  - Extracted `src/SlideSelector.jsx` — numbered slide buttons with drag-to-reorder (66 lines).
  - App.jsx reduced from 1454 to 719 lines (51% reduction).
  - Fixed redo hotkey: `e.key` is now normalized with `.toLowerCase()` so `Shift+Z` (uppercase) correctly triggers redo.
  - Used `pushUndoRef` (ref pattern) so hooks always call the latest `captureSnapshot` closure.
- Why: Reduce App.jsx complexity for maintainability; fix redo not triggering on some keyboard layouts.
- Files: `src/App.jsx` (rewritten), `src/useSlideManagement.js` (added), `src/useCanvasRenderer.js` (added), `src/usePdfExport.js` (added), `src/usePresets.js` (added), `src/SizeControl.jsx` (added), `src/SlideSelector.jsx` (added), `build.js` (updated ORDER, 19 files), `linkedin-carousel.jsx` (regenerated), `CHANGES.md` (updated).
- Validation: `node build.js` succeeds with 19 source files. All 6 extracted functions present exactly once in artifact. No duplicate state declarations. Redo hotkey fix confirmed via grep.
- Notes/Risks: Hooks use a `deps` object pattern; adding new dependencies requires updating both the hook signature and the caller. The `pushUndoRef` indirection adds a layer but ensures snapshot correctness across hook boundaries.

## 2026-02-27 - Pass 2: Extraction, stale-load guard, and undo/redo
- What changed: Extracted modules from App.jsx, added async load guard, and wired undo/redo.
  - Extracted `src/pdfBuilder.js` (PDF utility functions) and `src/ColorPickerInline.jsx` (reusable color picker component) from App.jsx. Replaced 6 inline color picker IIFEs with the shared component.
  - Added `presetLoadTokenRef` to guard async `Image.onload` callbacks against stale preset loads.
  - Added `src/undoRedo.js` (snapshot-based undo manager, capped at 20 entries).
  - Wired `pushUndo()` before 6 destructive operations: delete slide, duplicate slide, load preset, reset background, reorder slides, sync background to all.
  - Global `Ctrl+Z` / `Ctrl+Shift+Z` keyboard handler with input/textarea/select focus guard (preserves native text undo).
  - Snapshot scope: `seriesSlides`, `slideAssets`, `sizes`, `activeSlide`, `exportPrefix`, `profileImg`, `isCustomProfilePic`, `profilePicName`.
- Why: Reduce App.jsx complexity, prevent race conditions in async preset loading, and add user-facing undo/redo for destructive operations.
- Files: `src/App.jsx` (updated), `src/pdfBuilder.js` (added), `src/ColorPickerInline.jsx` (added), `src/undoRedo.js` (added), `build.js` (updated ORDER), `linkedin-carousel.jsx` (regenerated), `CHANGES.md` (updated).
- Validation: `node build.js` succeeds with 13 source files. Manual smoke test pending.
- Notes/Risks: Undo only captures snapshots before destructive ops (not per-field edits). Redo stack clears on any new destructive action. ColorPickerInline depends on module-scope `pickerDropdownStyle` and `INLINE_SWATCHES`.

## 2026-02-27 - Pass 1: Bug fixes and style hoist
- What changed: Fixed 3 bugs and hoisted inline styles to module scope.
  - Bug 1: Removed frozen `colors` state; render colors now derived from per-slide properties with hard fallbacks for backward-compat.
  - Bug 2: Slide duplicate/remove/reorder now use functional state updates to prevent stale-closure bugs. Duplicate inserts adjacent to source instead of appending.
  - Bug 3: Preset errors now use dedicated `presetError` state (not `pdfError`), displayed near the Presets UI, with proper lifecycle (clears on new file, successful parse, and successful load).
  - Hoisted `inputStyle`, `labelStyle`, `INLINE_SWATCHES`, `smallBtnStyle`, and `pickerDropdownStyle` to module scope to reduce per-render allocations.
- Why: Code review identified stale state, misplaced error messages, and unnecessary re-allocations.
- Files: `src/App.jsx` (updated), `src/canvas/renderSlide.js` (updated), `linkedin-carousel.jsx` (regenerated), `CHANGES.md` (updated).
- Validation: `node build.js` succeeds. Artifact regenerated. Manual smoke test pending.
- Notes/Risks: Preset backward-compat maintained via hard fallback colors. Duplicate now inserts at activeSlide+1 (UX change).

## 2026-02-27 - Added optional agent specs scaffold
- What changed: Added `agents/` docs (`README`, `planner`, `implementer`, `reviewer`) and linked them from `CLAUDE.md`.
- Why: Provide reusable role-based prompts while keeping `CLAUDE.md` as the core workflow source of truth.
- Files: `CLAUDE.md` (updated), `agents/README.md` (added), `agents/planner.md` (added), `agents/implementer.md` (added), `agents/reviewer.md` (added), `CHANGES.md` (updated).
- Validation: Confirmed agent docs are present, referenced in `CLAUDE.md`, and included in the workflow diff checklist.
- Notes/Risks: Agents are guidance-only; inconsistent trigger usage can reduce consistency.

## 2026-02-27 - Added feature session scaffold
- What changed: Added `FEATURE_CARD.md` template and a `FEATURE` -> `IMPLEMENT` session protocol in `CLAUDE.md`.
- Why: Standardize kickoff prompts without repeatedly pasting long instructions.
- Files: `CLAUDE.md` (updated), `FEATURE_CARD.md` (added), `CHANGES.md` (updated).
- Validation: Confirmed docs exist and protocol steps are explicit in `CLAUDE.md`.
- Notes/Risks: Protocol depends on contributors using the `FEATURE:` and `IMPLEMENT` triggers consistently.

## 2026-02-27 - Workflow docs consolidated
- What changed: Replaced overlapping workflow docs with `CLAUDE.md` as the single workflow contract, added `CHANGES.md`, and removed legacy checklist/handoff docs.
- Why: Streamline the plan -> edit -> build -> validate -> document -> commit -> push flow for Claude Code and human contributors.
- Files: `CLAUDE.md` (rewritten), `CHANGES.md` (added), `Checklist.md` (deleted), `CLAUDE-CODE-HANDOFF.md` (deleted).
- Validation: Confirmed markdown footprint is two files and stale references to removed docs are gone.
- Notes/Risks: Historical checklist detail was intentionally removed as part of consolidation.

## Entry Template
## YYYY-MM-DD - <short title>
- What changed:
- Why:
- Files:
- Validation:
- Notes/Risks:
