# CHANGES
Operational change log for behavior and workflow updates in this repo.
Add newest entries at the top.

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
