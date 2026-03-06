# CHANGES
Operational change log for behavior and workflow updates in this repo.
Add newest entries at the top.

## 2026-03-05 - Add Crosshatch + Diamonds geometric background patterns
- What changed: Added two new geo shape patterns. Crosshatch renders intersecting diagonal lines with subtle intersection node dots for a woven/fabric texture. Diamonds renders a tessellated grid of stroked diamond outlines with staggered row offset.
- Why: Expands the background pattern library to 9 options. Crosshatch specifically addresses the request for a textured look.
- Files: `src/constants.js` (GEO_SHAPES entries), `src/canvas/backgrounds.js` (drawGeoCrosshatch + drawGeoDiamonds + dispatcher), `src/ColorPickerInline.jsx` (thumbnails), `linkedin-carousel.jsx` (rebuilt), `CHANGES.md`.
- Validation: Smoke tested via Playwright — both patterns render correctly on canvas, shape picker shows all 9 patterns in 6+3 grid, no console errors.

## 2026-03-05 - Add "Dots" geometric background pattern
- What changed: Added a new "Dots" entry to the geo shape picker. Renders filled circles (radius 22px) in a staggered grid using the geo color layer with opacity support. Includes a thumbnail in the shape picker dropdown.
- Why: Expands the background pattern library with a clean, polka-dot style option. Also served as an LSP workflow demo.
- Files: `src/constants.js` (GEO_SHAPES entry), `src/canvas/backgrounds.js` (drawGeoDots + dispatcher), `src/ColorPickerInline.jsx` (thumbnail), `linkedin-carousel.jsx` (rebuilt), `FEATURE_CARD.md`, `CHANGES.md`.
- Validation: Smoke tested via Playwright — dots render as filled circles on canvas, shape picker shows all 7 patterns, no console errors.

## 2026-03-05 - Fix card checkmarks with transparent decorations + bottom corner base alignment
- What changed: (1) Card checkmarks now skip rendering entirely when decoration color is "transparent" — previously the checkmark stroke (using card bg color) still rendered even with transparent fill. (2) Bottom corner text+base bubble repositioned from `H - MARGIN + 12` to `H - MARGIN`, fixing a 12px offset that pushed the bubble partially off the canvas edge and misaligned it with the text.
- Why: Two visual bugs reported during smoke testing. The checkmark stroke was visible as a ghost artifact on cards when decorations were disabled. The bottom corner base bubble was a tiny sliver at the canvas edge instead of properly wrapping the text.
- Files: `src/canvas/renderSlideContent.js`, `src/canvas/overlays.js`, `src/canvas/renderSlide.js`, `linkedin-carousel.jsx` (rebuilt), `CHANGES.md`.
- Validation: Set decorations to transparent, switch to Cards — no checkmark visible. Set decorations to a color — checkmark renders normally. Enable bottom corner with white base — bubble properly wraps text at bottom-left, matching top corner alignment pattern.

## 2026-03-05 - Add LSP support + Symbol GPS to CLAUDE.md
- What changed: Added `jsconfig.json` for TypeScript Language Server integration (`checkJs: false`, `jsx: react`, `moduleResolution: bundler`). Added "Symbol GPS" section to CLAUDE.md with key symbols/signatures for all 20 source files. Added "LSP Configuration" section to CLAUDE.md documenting jsconfig purpose and constraints. Installed `typescript-language-server` globally.
- Why: LSP provides IDE-like code intelligence (hover, go-to-definition, find-references) for Claude Code sessions. The Symbol GPS section gives Claude instant awareness of the full symbol landscape at session start, reducing exploration overhead. Together they act as "GPS for the codebase" — LSP navigates, CLAUDE.md orients.
- Files: `jsconfig.json` (new), `CLAUDE.md`, `CHANGES.md`.
- Validation: Verify `jsconfig.json` doesn't break build (`node build.js`). Confirm Symbol GPS section is accurate against source files.

## 2026-03-05 - Add /smoke-deep extended smoke test skill
- What changed: Created `/smoke-deep` skill in `.claude/skills/smoke-deep/SKILL.md`. This extends the standard 7-step `/smoke` checklist with 5 additional interaction tests: color picker swatches, geo shape switching, slide CRUD with custom confirm dialog handling, toggle controls, and size stepper controls. Updated CLAUDE.md Phase 3 skills list to include `/smoke-deep`. Includes documented patterns for confirm dialog handling (React modals, not native dialogs) and opacity slider interaction via `browser_evaluate`.
- Why: The standard `/smoke full` checklist covers basic app health but misses significant interaction surface. Manual deep testing during this session revealed all these areas work correctly but had no repeatable skill to codify them.
- Files: `.claude/skills/smoke-deep/SKILL.md` (new), `CLAUDE.md`, `CHANGES.md`.
- Validation: Run `/smoke-deep` and verify all 12 steps pass. Verify skill appears in `/` autocomplete.

## 2026-03-04 - Add smoke testing skills for structured Playwright workflows
- What changed: Created 4 Claude Code custom skills in `.claude/skills/`: `/smoke-preflight` (pre-flight validation), `/smoke` (main test runner with standard checklist), `/smoke-close` (idempotent browser teardown), `/build-test` (build + smoke compound). Updated CLAUDE.md Phase 3 smoke test section to reference skills. Added `.gitignore` carve-out (`!.claude/skills/`) so skills are version-controlled.
- Why: Smoke testing was entirely ad-hoc — every cycle required manually writing Playwright MCP calls from scratch, with forgotten browser cleanup, inconsistent screenshots, and no replayable test definitions. Skills codify these repeated patterns into composable slash commands.
- Files: `.claude/skills/smoke-preflight/SKILL.md` (new), `.claude/skills/smoke/SKILL.md` (new), `.claude/skills/smoke-close/SKILL.md` (new), `.claude/skills/build-test/SKILL.md` (new), `.gitignore`, `CLAUDE.md`, `CHANGES.md`.
- Validation: Verify skills appear in `/` autocomplete. Run `/smoke-preflight` to confirm checks execute. Run `/smoke full` to confirm browser workflow. Run `/smoke-close` to confirm teardown.

## 2026-03-04 - Repo cleanup: fix doc drift + harden gitignore/settings/pre-commit + archive changelog
- What changed: Fixed CLAUDE.md source count (19 → 20) and manifest table (added layoutTokens.js). Added Phase 3 pre-flight checklist. Hardened .gitignore with defensive patterns (node_modules, IDE files, .env) and replaced prefix-based root image globs with extension-based globs. Removed cat/head/tail Bash permissions from settings.json (contradicts Tool Selection Rules). Archived pre-March CHANGES.md entries to CHANGES_ARCHIVE.md and added 300-line maintenance rule. Added scripts/validate-order.js to verify src/ ↔ ORDER parity, wired into .githooks/pre-commit.
- Why: Audit found documentation drift, missing defensive patterns, and process gaps from recent feature work.
- Files: `CLAUDE.md`, `.gitignore`, `.claude/settings.json`, `CHANGES.md`, `CHANGES_ARCHIVE.md` (new), `scripts/validate-order.js` (new), `.githooks/pre-commit`, `FEATURE_CARD.md`.
- Validation: `node build.js` succeeds (20 files). `node scripts/validate-order.js` passes. Temp file in src/ correctly blocked by validation. CHANGES.md under 330 lines.
- Notes/Risks: CHANGES_ARCHIVE.md is a new tracked file. validate-order.js blocks commits when src/ files are not in ORDER — intentionally strict.

## 2026-03-04 - Require Playwright browser shutdown after smoke tests
- What changed: Hardened `CLAUDE.md` smoke-test instructions to require explicit Playwright cleanup after every smoke-test attempt (pass or fail). Added guardrail language blocking Commit gate progression while any smoke-test Playwright window/session is still open.
- Why: Smoke-test browser sessions were closed inconsistently, which could leave stale windows/sessions open across retests and handoff.
- Files: `CLAUDE.md`, `CHANGES.md`.
- Validation: Verified Smoke test section now includes explicit close-out steps and Hard Guardrails now enforce browser/session closure before Commit gate.

## 2026-03-04 - Add Base background bubble to all text sections
- What changed: Every text-content section (Heading, Body/Cards, Top Corner, Bottom Corner) now has a "Base" color swatch that draws a rounded-corner background bubble behind the text. Defaults to transparent. Each Base swatch includes an opacity slider. The Body/Cards Base swatch is no longer greyed out — it dynamically switches between `bodyBgColor` (body mode) and `cardBgColor` (cards mode). Heading, Top Corner, and Bottom Corner sections now use a stacked Text+Base swatch layout with an inline size stepper, replacing the old `SizeControl` component. Bottom corner text repositioned slightly lower for better spacing under the frame.
- Why: Users needed per-section background control to improve text readability over busy slide backgrounds.
- Files: `src/slideFactory.js`, `src/canvas/overlays.js`, `src/canvas/renderSlide.js`, `src/canvas/renderSlideContent.js`, `src/App.jsx`, `src/useSlideManagement.js`, `src/usePresets.js`, `linkedin-carousel.jsx`, `FEATURE_CARD.md`, `CHANGES.md`.
- New slide properties: `headingBgColor`, `headingBgOpacity`, `bodyBgColor`, `bodyBgOpacity`, `cardBgOpacity`, `topCornerBgColor`, `topCornerBgOpacity`, `bottomCornerBgColor`, `bottomCornerBgOpacity`.

## 2026-03-04 - Permission hardening for autonomous workflow
- What changed: Replaced 30+ enumerated Bash permission patterns in `settings.local.json` with bare `Bash` catch-all for full Phase 3 autonomy. Cleaned `settings.json` to fix colon-syntax bugs (`echo:*` → `echo *`), consolidated 7 git subcommand patterns into `Bash(git *)`, removed `npm` permission (zero-dep project), added missing utilities (`cat`, `tail`, `wc`, `mkdir`, `pwd`, `which`). Fixed identical colon-syntax bugs in global `~/.claude/settings.json`. Added "Tool Selection Rules" section to `CLAUDE.md` prescribing dedicated tools over Bash equivalents. Simplified "Permission Preflight" section. Added Phase 3 autonomy expectation note.
- Why: Claude Code was periodically stopping during the autonomous SHIP loop to request Bash command permissions, breaking the oneshot workflow.
- Files: `.claude/settings.local.json`, `.claude/settings.json`, `~/.claude/settings.json`, `CLAUDE.md`, `CHANGES.md`.
- Validation: Start a new session and verify `node build.js`, `git status`, `echo "test"` run without permission prompts.

## 2026-03-04 - Archive all untracked root images (not prefix-based)
- What changed: Updated `scripts/archive-smoke-artifacts.js` so root image cleanup is no longer tied to filename prefixes. The script now archives all untracked root image files by extension (`.png/.jpg/.jpeg/.webp/.gif`), plus existing `.playwright-mcp/` and `test-results/` artifacts. Updated `CLAUDE.md` Commit gate and guardrail wording to reflect extension-based root image cleanup.
- Why: Claude can generate varying screenshot filenames; prefix matching was brittle and missed artifacts.
- Files: `scripts/archive-smoke-artifacts.js`, `CLAUDE.md`, `CHANGES.md`.
- Validation: Verified script includes git-untracked root image detection and workflow text references extension-based cleanup.
- Notes/Risks: Intentional new root images that are still untracked will also be archived unless they are staged first.

## 2026-03-04 - Split Accent swatch into Decorations + Accent
- What changed: The single "Accent" color swatch now splits into two independent swatches: "Decorations" (controls accent bar under title + card checkmark circles) and "Accent" (controls `**word**` bold text color only). Added `decorationColor` property to the slide model, render pipeline, sync-all, and preset serialization. Removed transparent option from the Accent swatch (Decorations retains it to hide bar/checkmarks).
- Why: Users need independent control over decorative element colors vs bold-word text accent color.
- Files: `src/slideFactory.js`, `src/canvas/renderSlide.js`, `src/canvas/renderSlideContent.js`, `src/App.jsx`, `src/useSlideManagement.js`, `src/usePresets.js`, `linkedin-carousel.jsx`, `CHANGES.md`.
- Validation: Smoke-tested in Playwright — verified independent color control, accent bar uses decoration color, `**word**` uses accent color, UI layout correct.

## 2026-03-04 - Merge Base + Layer swatches, add Solid shape
- What changed: Removed the Base swatch from the Background row and merged its fill-color functionality into the Layer swatch. The Layer popup now has dual-color sections (Fill + Pattern) stacked vertically, with the pattern section hidden when Solid is selected. Added "Solid" as the first entry in GEO_SHAPES — selecting it disables the geo pattern and shows only the fill color. The swatch button shows a diagonal split when a pattern is active or a solid fill when Solid is selected. Removed the transparent option from the Layer swatch.
- Why: Simplifies the Background row from 4 swatches to 3 and gives users unified control over both fill and pattern colors in one place.
- Files: `src/constants.js`, `src/ColorPickerInline.jsx`, `src/App.jsx`, `linkedin-carousel.jsx`, `CHANGES.md`.
- Validation: Smoke-tested in Playwright — verified dual-color popup, solid/pattern toggle, canvas rendering, and Frame/Accent swatches unaffected.

## 2026-03-04 - Disable AskUserQuestion path for alignment gates
- What changed: Hardened `CLAUDE.md` so Phase 1/2 alignment questions must be asked in plain chat only, explicitly disallowing `AskUserQuestion` for those gates. Added empty/unclear response handling rule: treat blank payloads as unanswered and re-ask in plain chat. Added matching hard guardrail. Removed `AskUserQuestion` from `.claude/settings.json` allow-list and local settings to prevent the buggy tool path from being selected.
- Why: `AskUserQuestion` was returning empty/ambiguous answer payloads in practice, causing false "answered" states and skipped alignment pauses.
- Files: `CLAUDE.md`, `.claude/settings.json`, `.claude/settings.local.json`, `CHANGES.md`.
- Validation: Verified Phase 1/2 now require plain-chat questions, guardrail language is present, and `AskUserQuestion` is absent from both permission allow-lists.
- Notes/Risks: If tooling behavior changes in the future, this can be revisited; plain-chat ask/wait is currently the most reliable path.

## 2026-03-04 - Automate smoke artifact filing on every commit
- What changed: Added `scripts/archive-smoke-artifacts.js` to file away Playwright MCP logs and smoke-test/layout screenshots into `.playwright-mcp/archive/<timestamp>/` and clear them from repo root/working artifact locations (`.playwright-mcp/`, `test-results/`, root `smoke-test*.png`, `slide-panel*.png`, `layer-*-test.png`, `final-layout.png`). Added tracked pre-commit hook `.githooks/pre-commit` to run this script automatically on every commit. Updated `CLAUDE.md` Commit gate, Git Policy, and Hard Guardrails to require and document this hygiene flow.
- Why: Keep commits clean and deterministic while preserving smoke artifacts for local debugging/history instead of scattering them in the repo root.
- Files: `scripts/archive-smoke-artifacts.js`, `.githooks/pre-commit`, `.gitattributes`, `CLAUDE.md`, `CHANGES.md`.
- Validation: Verified hook and script files exist, Commit gate references the script, and policy documents one-time `core.hooksPath` setup.
- Notes/Risks: Hook automation applies per clone once `git config core.hooksPath .githooks` is set; without that setup, the script must be run manually.

## 2026-03-04 - Add layer shape options + fix swatch pop-out clipping
- What changed: (1) Added 4 new geometric layer patterns — Bokeh (organic scattered circles), Waves (flowing curves), Diagonal Stripes, Hexagon Mesh (enlarged) — alongside the existing Lines pattern. A "Pattern" selector with canvas-rendered thumbnail icons appears below the opacity slider in the Layer pop-out. (2) Converted all swatch pop-outs (ColorPickerInline + SizeControl) from absolute positioning to React portals, fixing clipping caused by the sidebar's `overflowY: auto`. Updated outside-click handler to detect portal elements.
- Why: More visual variety for slide backgrounds; pop-outs were getting cut off on the left pane.
- Files: `src/constants.js`, `src/slideFactory.js`, `src/canvas/backgrounds.js`, `src/canvas/renderSlide.js`, `src/useSlideManagement.js`, `src/usePresets.js`, `src/ColorPickerInline.jsx`, `src/SizeControl.jsx`, `src/App.jsx`, `CHANGES.md`.
- Validation: Playwright smoke test confirmed all 5 patterns render on canvas, shape selector UI works, pop-outs no longer clip, transparent toggle disables layer, and original Lines pattern is backward-compatible.

## 2026-03-04 - Move Accent swatch from Heading to Background section
- What changed: Moved the Accent color swatch from the Heading section to the Background section, placed after Frame with a pipe separator. Accent swatch is now always visible (not conditional on Heading toggle). Moved the `**word** = accent color` hint text from the bottom of the pane to inline after the Accent label.
- Why: Better grouping — accent is a slide-level color concern like the other background swatches.
- Files: `src/App.jsx`, `CHANGES.md`.

## 2026-03-04 - Slide N panel: stack swatches, move Accent to Heading, default text
- What changed: (1) Footer & Pic section swatches now stack vertically — Text on top, Base underneath — with pipe separator removed. (2) Moved Accent color swatch from Background section to Heading section, stacked below Text swatch. Accent picker now supports transparent "none" selection that disables both the accent bar and inline accent text highlighting. Removed the dual-purpose Accent toggle button; Cards mode now shows a dedicated "Checks" button instead. (3) Changed Bottom Corner default text from "Brand Name" to "01 / ".
- Why: Better visual grouping of swatch controls and cleaner accent on/off UX.
- Files: `src/App.jsx`, `src/canvas/text.js`, `src/slideFactory.js`, `src/ColorPickerInline.jsx`, `CHANGES.md`.
- Validation: Playwright smoke test confirmed all three changes render correctly on canvas and in panel UI.

## 2026-03-03 - Enforce explicit question delivery before implementation
- What changed: Hardened `CLAUDE.md` so Phase 1/2 questions must be sent as an explicit chat message and answered before continuing. Added explicit rule that preparing questions internally does not satisfy the phase. Added a required no-question fallback message (`No blocking questions; proceeding with stated assumptions:` + assumptions list). Added a hard guardrail blocking Phase 3 code changes until this ask/wait gate is satisfied.
- Why: Agents could appear to prepare questions but still skip actually asking, causing misalignment before implementation.
- Files: `CLAUDE.md`, `CHANGES.md`.
- Validation: Verified explicit send-and-wait wording exists in Phase 1 and Phase 2, plus matching hard guardrail language.
- Notes/Risks: May add a brief pause before implementation, but reduces requirement misses and rework.

## 2026-03-03 - Phase-boundary permission recheck + cd wrapper allow
- What changed: Hardened permission workflow and config to reduce avoidable approval prompts between phases. `CLAUDE.md` Permission Preflight now requires phase-boundary rechecks, command-segment evaluation (`&&`, `|`, `;`), and retrying commands without `cd ... &&` wrappers before escalation. Also documented local settings precedence for overlapping keys. Added `Bash(cd *)` to `.claude/settings.json` allow-list so shell wrappers that emit standalone `cd` segments do not trigger unnecessary approvals.
- Why: Commands like `cd /... && git diff --stat` can be evaluated as separate segments; `git diff*` may be allowed while `cd` is not, causing noisy prompts even though the intended action is already permitted.
- Files: `CLAUDE.md`, `.claude/settings.json`, `CHANGES.md`.
- Validation: Verified new preflight bullets are present and `Bash(cd *)` is in the allow-list.
- Notes/Risks: `Bash(cd *)` only permits directory changes; subsequent command segments still require their own permission matches.

## 2026-03-03 - Slide pane UI tweaks
- What changed: (1) Merged Frame section into Background row as a transparent-toggle swatch with opacity slider, matching Layer pattern. (2) Added opacity slider to Layer swatch, backed by new `geoOpacity` slide field. (3) Upgraded Layer swatch from 7-color LAYER_SWATCHES to 16-color INLINE_SWATCHES. (4) Moved Footer & Pic, Top Corner, and Bottom Corner text inputs inline with their ON/OFF toggle row, eliminating the indented sub-row. (5) Fixed Heading textarea scrollbar by setting explicit lineHeight. (6) Left pane: moved "SLIDES" header above Sync All/Reset All, centered and renamed "Duplicate" to "Duplicate Slide".
- Why: Saves vertical space in the slide editor, consolidates related controls, and provides finer control over layer/frame opacity.
- Files: `src/App.jsx`, `src/SlideSelector.jsx`, `src/slideFactory.js`, `src/canvas/backgrounds.js`, `src/canvas/renderSlide.js`, `src/useSlideManagement.js`, `src/usePresets.js`, `FEATURE_CARD.md`, `CHANGES.md`.

## 2026-03-03 - Loosen fixed question cap to alignment-based guidance
- What changed: Updated `CLAUDE.md` Feature Flow so Phase 1 and Phase 2 no longer enforce a hard `1–3` question cap. The workflow now requires asking the number of questions needed for alignment, with rough guidance of typically `~2–6` and allowing more when ambiguity or risk is high.
- Why: A strict `1–3` cap was too tight for complex or ambiguous features and could force implementation without sufficient alignment.
- Files: `CLAUDE.md`, `CHANGES.md`.
- Validation: Verified both question-count lines in Phase 1 and Phase 2 now use alignment-based language with a rough range.
- Notes/Risks: Slightly more upfront questioning can increase kickoff time, but reduces downstream rework risk.

## 2026-03-03 - Make commit gate mandatory before user review
- What changed: Hardened `CLAUDE.md` so Phase 3 ends with an explicit `Commit gate (final step before review)` requiring intended-file check, atomic commit, and commit hash reporting (`git rev-parse --short HEAD`). Updated Phase 4 to be post-commit only, added Git Policy requirement that review handoff include the local commit hash, and added a guardrail blocking review handoff before commit+hash.
- Why: Ensure every review starts from a concrete local commit, so the only post-handoff outcomes are patching that commit path or pushing to GitHub.
- Files: `CLAUDE.md`, `CHANGES.md`.
- Validation: Verified the new Commit gate section, post-commit Phase 4 wording, Git Policy hash requirement, and guardrail are present.
- Notes/Risks: This is process enforcement via docs; compliance still depends on agents following the contract.

## 2026-03-03 - Enforce permission preflight before escalation requests
- What changed: Added a new `Permission Preflight (Before Any Escalation Request)` section to `CLAUDE.md` and wired it into guardrails. Agents must now check `.claude/settings.local.json` and `.claude/settings.json`, confirm whether a command is already allowed, and only request escalation when the exact action is not permitted.
- Why: Prevent unnecessary permission prompts and make escalation requests deterministic and policy-driven.
- Files: `CLAUDE.md`, `CHANGES.md`.
- Validation: Verified the new section and guardrail language are present and explicitly ordered as a pre-escalation gate.
- Notes/Risks: This is process enforcement via documentation; runtime compliance still depends on agents following the contract.

## 2026-03-03 - Layer swatch breakout + updateSlide batching fix
- What changed: The Layer (geometric overlay) color picker is now its own standalone swatch with label "Layer" next to Accent and Base in the SlideN pane, instead of being buried inside the Base picker dropdown. No ON/OFF toggle — the transparent checkerboard option serves as "off". ColorPickerInline gained two optional props (`swatches`, `allowTransparent`) for custom swatch grids with a transparent option. Also fixed a stale-closure batching bug in `updateSlide` (switched to functional updater form for `setSeriesSlides`) that caused consecutive field updates to overwrite each other.
- Why: Layer was hard to discover inside the Base dropdown. Breaking it out makes it a first-class control. The batching fix ensures any two rapid `updateBgField` calls compose correctly.
- Files: `src/ColorPickerInline.jsx`, `src/App.jsx`, `src/useSlideManagement.js`, `linkedin-carousel.jsx` (regenerated).

## 2026-03-03 - Per-slide font sizes + control relocation
- What changed: Font sizes (heading, body, cardText, topCorner, bottomCorner, brandName) are now per-slide instead of global. Each slide gets its own copy of sizes stored in the slide data model. Upload buttons (Background, Footer, Screenshot) and Accent/Base color swatches moved from the left pane to the "Slide N" editor pane. Left pane simplified to just Sync All and Reset All buttons plus the slide list. Sync All now syncs all visual settings (sizes, typography, colors, backgrounds, toggles) from the active slide to all others — text content and screenshots are not affected. Reset All now fully resets all slides to defaults. Single-slide Reset button removed from left pane (per-slide reset lives on the Slide N header). Preset save/load updated with per-slide size fields and legacy migration for old presets with global sizes. Undo/redo automatically covers sizes since they're now part of the slide data.
- Why: Per-slide sizes allow different typography on each slide. Relocating controls makes the left pane a global-actions panel while the Slide N pane owns all per-slide settings.
- Files: `src/slideFactory.js`, `src/canvas/renderSlide.js`, `src/useCanvasRenderer.js`, `src/usePresets.js`, `src/useSlideManagement.js`, `src/App.jsx`, `linkedin-carousel.jsx` (regenerated).

## 2026-03-02 - Bug fixes + canvas layout tokens
- What changed: Fixed `hexToRgba` returning invalid `rgba(...,NaN)` when opacity argument was omitted. Fixed `handleCustomUpload` using a stale `activeSlide` closure — custom background could land on the wrong slide if user switched slides during upload. Added `onerror` handlers to all three image upload functions (custom bg, screenshot, profile pic) so corrupt files log a warning instead of failing silently. Added zero-dimension guard in `drawCustomBg` to prevent `NaN` ratio calculations. Fixed `drawBottomCorner` using `"bold"` instead of `"700"` for font weight consistency. Extracted 35 hardcoded canvas layout values into a `CANVAS` object in `constants.js`.
- Why: Edge-case bugs caused silent failures or incorrect behavior. Canvas magic numbers made layout tuning fragile — now all values are named and centralized.
- Files: `src/canvas/hexToRgba.js`, `src/useSlideManagement.js`, `src/canvas/backgrounds.js`, `src/canvas/overlays.js`, `src/constants.js` (CANVAS tokens), `src/canvas/renderSlideContent.js`, `src/canvas/screenshot.js`, `linkedin-carousel.jsx` (regenerated).

## 2026-03-02 - Layout grid + design tokens
- What changed: Introduced `src/layoutTokens.js` with a shared design token system (SPACE, RADIUS, Z, SIZE, SURFACE, CLR) and style helper functions (panelBtn, toggleBtn, uploadFrameStyle, uploadBtnStyle, dividerStyle, dialogOverlay, dialogBox, dialogBtn). Replaced all ad-hoc magic numbers across App.jsx, ColorPickerInline.jsx, SizeControl.jsx, and SlideSelector.jsx with token references. Converted the three-column flex layout to CSS Grid with named grid areas (sidebar, editor, preview). Restructured BACKGROUND buttons from 2-column to label + 3-column equal-width grid.
- Why: Layout tweaks were finicky because every gap, margin, padding, color, and size was a standalone magic number. Changing one value required hunting across files. Now all spacing/sizing/color decisions flow from shared constants — changing `SPACE[4]` from 8 to 10 updates every standard gap at once.
- Files: `src/layoutTokens.js` (new), `build.js` (ORDER updated), `src/App.jsx`, `src/ColorPickerInline.jsx`, `src/SizeControl.jsx`, `src/SlideSelector.jsx`, `linkedin-carousel.jsx` (regenerated).

## 2026-03-01 - Upload frame spacing + filename overflow fix
- What changed: Increased margins between stacked elements (label, spec text, upload button, filename) in all three upload frames from 1-2px to 3-4px. Added `overflow: hidden` and `minWidth: 0` to prevent long filenames from widening the Profile and Screenshot frames.
- Why: Elements were too tightly packed; long filenames could push flex containers wider than intended.
- Files: `src/App.jsx`, `linkedin-carousel.jsx` (regenerated).

## 2026-03-01 - Rename header + align top row across all panes
- What changed: Renamed "LinkedIn Carousel Generator" → "Carousel Generator". Moved the header from a full-width row above all panes into the top of the left column. Increased outer container top padding so all three panes (left, center, right) start at the same vertical position. Updated browser tab title to "Carousel Generator".
- Why: Even out the UI — the center and right panes previously started lower than the header row, wasting vertical space.
- Files: `src/App.jsx`, `preview.html`, `linkedin-carousel.jsx` (regenerated).

## 2026-03-01 - Fix upload frame layout jumps: fixed-height Background/Profile/Screenshot frames
- What changed: All three upload frames (Background, Profile, Screenshot) now have a uniform fixed height of 88px with `box-sizing: border-box`. The Screenshot frame's scale slider fits within this reserved height instead of expanding the frame when an image is uploaded.
- Why: Uploading a screenshot caused the slider to appear, growing the Screenshot frame and pushing everything below it (Duplicate Slide, slide list) downward. The UI would jump whenever toggling uploads.
- Files: `src/App.jsx`, `linkedin-carousel.jsx` (regenerated).

## 2026-03-01 - Layout polish: pane balance, upload button, margins, 2-col slides
- What changed: Four layout tweaks to the left-pane reorganization.
  - **(i) Pane balance**: Center pane (Slide Editor) now uses `flex: 1`; right pane (Preview) capped at `maxWidth: 480` so they share space more evenly.
  - **(ii) Upload button**: Background upload moved from a 48px square beside Accent to a full-width 44px-tall bar below Frame, labeled "Upload Background".
  - **(iii) Margins**: BACKGROUND label now uses full `labelStyle` (13px, matching PRESETS/PREVIEW). Separator above BACKGROUND uses 8px margins. Accent/Base/Layer/Frame rows tightened to 2px gap.
  - **(iv) 2-col slides**: SlideSelector changed from vertical stack to `grid-template-columns: 1fr 1fr`, with buttons reduced to 44px height and 18px font. Fits 10 slides compactly.
- Why: User feedback — Preview was too large, Slide Editor too small, upload button was accidentally shrunk, and slides needed to fit 10 in the new narrower pane.
- Files: `src/App.jsx`, `src/SlideSelector.jsx`, `linkedin-carousel.jsx` (regenerated).

## 2026-03-01 - Relocate Background/Profile/Screenshot to left pane
- What changed: Background controls, Profile upload, and Screenshot upload moved from the center pane's frozen top section into the left pane. Left pane widened from 136px to 220px. Center pane now starts directly with the Slide Editor.
  - **(i) Left pane layout**: Top-to-bottom: Presets > divider > Background label + Sync All/Reset buttons + Accent (with Upload beside it) + Base + Layer + Frame > Profile/Screenshot side-by-side > divider > Duplicate Slide button > Slides list.
  - **(ii) Duplicate Slide**: Changed from two-line "Duplicate\nSlide" to single-line "Duplicate Slide".
  - **(iii) Center pane**: Removed entire frozen top section (Background/Profile/Screenshot boxes + divider). Slide Editor is now the first and only element.
  - **(iv) Compact uploads**: Profile and Screenshot boxes reduced to 44x44px and placed side-by-side. Background upload reduced to 48x48px.
- Why: Groups all global/background controls in the left pane, frees vertical space in the center pane for the slide editor.
- Files: `src/App.jsx` (layout restructure).

## 2026-03-01 - Framed-box header + Preview pane tightening
- What changed: Header sections are now framed boxes with consistent UI patterns. Preview pane restructured.
  - **(i) Framed boxes**: Background, Profile, and Screenshot are each wrapped in `#0f0f1a` bordered boxes with `8px` border-radius, giving consistent visual framing.
  - **(ii) Background 2-column stack**: Accent/Layer in column 1, Base/Frame in column 2 (vertical stacks). Upload button + ✓/× as column 3, all stacked vertically.
  - **(iii) Consistent Upload UI**: All three sections use the same pattern — "Upload\n(WxH)" 2-line button with ✓ and × stacked vertically beside it. No "Remove" text, no "No image" placeholders.
  - **(iv) Profile compact**: Circle preview (48px) centered under PROFILE label, Upload button + ✓/× below it.
  - **(v) Screenshot inline**: ON/OFF toggle in header, Scale slider + Upload button + ✓/× all on one row. Upload button sits to the right of the slider.
  - **(vi) Sync All/Reset full-height**: Buttons stretch to fill the full header height with `flex: 1`.
  - **(vii) Preview pane**: Filename prefix input moved to the PREVIEW header row (same line). Download buttons are single-line centered below. No multi-line button text. Removed `minWidth: 360` — pane sizes naturally.
  - **(viii) Outer margins**: Reduced padding to `10px 12px`, removed `maxWidth: 1520` cap, tightened column gap from `20px` to `14px`, title font reduced to `18px`.
- Why: The previous layout had inconsistent section styling, wasted vertical space with separate header rows for labels vs controls, and the Preview pane had unnecessary horizontal padding.
- Files: `src/App.jsx` (header + preview layout rewrite).

## 2026-03-01 - Compact single-row header: Background + Profile + Screenshot
- What changed: Collapsed the frozen header into one tight horizontal row with consistent patterns across all three sections.
  - **(i) Killed PHOTO BG card + Solid/Photo toggle**: Background photo upload is now just an "Upload (800x1000)" button in the BACKGROUND header row. Clicking it sets bgType to custom and opens the file picker in one action. Remove button appears inline after upload.
  - **(ii) Stacked Sync All / Reset**: Moved to a vertical stack on the left edge of the header row.
  - **(iii) Background controls compacted**: Accent/Base on one row, Layer+Frame on a second row (side by side instead of stacked). Labels shrunk to 11px.
  - **(iv) Profile section raised**: Header row with PROFILE label + "Upload (84x84)" button + x remove. Circle preview shrunk to 52px and sits directly below the header — no extra padding or bottom buttons.
  - **(v) Screenshot section raised**: Header row with SCREENSHOT label + ON/OFF pill + "Upload (800x1000)" + checkmark/remove. Scale slider appears inline below only when an image is uploaded. Killed "No image" placeholder text and dashed-border empty state.
  - **(vi) Consistent pattern**: All three sections use the same header style: label + Upload(dims) + status in one row, with content below only when needed.
- Why: The previous layout had three card-style boxes at different heights, a separate PHOTO BG toggle/label, and unnecessary empty states. The new layout is one compact row that maximizes vertical space for the slide editor below.
- Files: `src/App.jsx` (header layout rewrite).

## 2026-03-01 - Feature flow: SHIP command + Playwright MCP smoke testing
- What changed: Added prescriptive feature flow to `CLAUDE.md` defining the `SHIP` kick-off command and automatic implement → self-review → smoke test → commit loop.
  - **SHIP command**: Single command (`SHIP: Read CLAUDE.md and FEATURE_CARD.md, then implement the feature.`) kicks off the full feature cycle in Claude Code.
  - **Self-review step**: Claude Code reviews its own diff against `FEATURE_CARD.md` scope and code quality before proceeding to smoke test.
  - **Playwright MCP smoke test**: Claude Code uses Playwright MCP to open `preview.html`, verify the new feature works, and check for visual regressions. Patches and re-tests if issues found.
  - **Human review gate**: Claude Code commits but does not push — waits for human review before push.
- Why: Wire up the full feature cycle as a single kick-off command with automatic QC and visual verification, replacing the previous generic AI assistant context section.
- Files: `CLAUDE.md` (updated), `CHANGES.md` (updated).
- Validation: No source or artifact changes. Workflow-only update.
- Notes/Risks: Playwright MCP smoke test requires `npx serve . --listen 5173` running in a separate terminal. Smoke test is intentionally light — verifies new feature + quick visual check, not a full regression suite.

## 2026-03-01 - Header layout compaction + preview fit
- What changed: Compacted the Background header section and fixed Preview pane scrollbar issues.
  - **(i) Removed thumbnail preview**: Killed the background thumbnail (solid/photo preview with layer/frame overlays) to reclaim horizontal space.
  - **(ii) Photo BG card**: Moved Solid/Photo pill toggle out of the BACKGROUND header row into a card-style group (matching Profile/Screenshot cards). File upload controls (Choose File, status, remove) are grouped inside the card. When in Solid mode the card shows a "Switch to Photo mode" placeholder.
  - **(iii) Sync All + Reset relocated**: Pushed to the right edge of the BACKGROUND header row (was inline after the pill toggle).
  - **(iv) Horizontal card layout**: Profile and Screenshot cards moved from absolute-positioned right column into the main flex row alongside Accent/Base/Layer/Frame controls and the new Photo BG card.
  - **(v) Preview canvas viewport fit**: Canvas now uses `maxHeight: 100%` + `aspectRatio` constraint instead of `width: 100%; height: auto`, so it shrinks to fit available viewport height without scrollbars at 100% zoom.
  - **(vi) Download button labels**: Renamed "Download Current" to "Download Current Slide (pdf)" and "Download All N" to "Download All Slides (pdf)".
- Why: The previous layout wasted vertical space with the thumbnail and caused the Preview pane to overflow with scrollbars at 100% zoom. The card-style grouping for Photo BG is more consistent with the Profile/Screenshot card pattern.
- Files: `src/App.jsx` (layout restructure).

## 2026-03-01 - UI tightening and freeze pane overhaul
- What changed: Major layout overhaul to tighten the header area and freeze it so only the slide editor and preview canvas scroll.
  - **(i) Solid/Photo inline**: Moved Solid/Photo toggle into the BACKGROUND header row, saving one full row.
  - **(ii) Merged Accent+Base**: Combined onto a single row. Removed Footer color from Background section; it now lives in Footer & Pic.
  - **(iii) Inline swatches**: Moved Text/Base color swatches into BODY/CARDS and FOOTER & PIC section headers, eliminating dedicated swatch rows.
  - **(iv) Expanded Profile/Screenshot**: Wider right zone (126→144px), larger profile circle (48→64px).
  - **(v) Profile buttons redesign**: Replaced absolute "×" remove with [Upload] [✕ Remove] buttons below the profile circle.
  - **(vi) Dimension text moved**: "800×1000px" moved from bottom of page to Screenshot section header subtitle.
  - **(vii) PREVIEW header aligned**: Now uses same labelStyle as BACKGROUND/PRESETS headers.
  - **(viii) 3-tile download row**: Filename input + Download Current + Download All in a single horizontal row. Download All always visible (disabled when 1 slide).
  - **(ix) Enlarged Presets**: PRESETS header uses full labelStyle, Save/Load are larger buttons on separate row.
  - **(x) Freeze pane**: Viewport-height layout with frozen header region (Background, Profile/Screenshot, Preview controls) and independently scrollable bottom region (Slide editor, Slides list, Preview canvas) in each column.
- Why: Full-screen view had dead space above the slide editor. Freeze pane keeps settings visible while scrolling through slide content.
- Files: `src/App.jsx` (layout overhaul), `src/useSlideManagement.js` (removed `footerBg` from Sync All and Reset — now per-slide via Footer & Pic section).
- Notes/Risks: Footer background color is no longer synced by "Sync All" or reset by "Reset" in the Background section. It is now controlled per-slide from the Footer & Pic section. Color picker dropdowns in frozen sections use `position: absolute` with `zIndex: 60` — frozen divs have no overflow clipping to avoid dropdown cutoff.

## 2026-03-01 - Harden CLAUDE.md: architecture, source manifest, zero-dep and ORDER guardrails
- What changed: Added missing architectural context and guardrails to CLAUDE.md to prevent silent build failures and constraint violations.
  - **Architecture section**: Documents what the app is (LinkedIn carousel designer, canvas-based React), runtime model (React 18.2.0 UMD + Babel Standalone 7.26.10), version pins and why they're pinned (Claude.ai sandbox parity), and the zero-dependency constraint with its rationale.
  - **Source Manifest section**: Points at `build.js ORDER` as the single source of truth for what ships. Includes a layer-overview table (Constants → Canvas → Data → UI → Hooks → App) for orientation without duplicating the exact file list.
  - **New-file workflow**: Added guidance under the Write step and AI Assistant Context for adding new source files to `ORDER` in `build.js`. Calls out the asymmetric failure mode: build throws on a missing file, but silently excludes an orphan file not in `ORDER`.
  - **Project Files table**: Replaced "Lean Doc Set" with split tables for docs (CLAUDE.md, CHANGES.md) and code artifacts (build.js, preview.html, linkedin-carousel.jsx). Correctly classifies preview.html as code.
  - **Commit message style**: Added to Git Policy — imperative mood, sentence case, ~72 chars.
  - **Hard Guardrails**: Added zero-dep constraint (no package.json/node_modules/npm) and ORDER requirement for new files.
- Why: An AI assistant or new contributor had no documented context about the app's architecture, the zero-dep constraint, the React version pin, or the build ORDER requirement. Each gap could cause silent build failures or constraint violations.
- Files: `CLAUDE.md` (updated), `CHANGES.md` (updated).
- Validation: All file paths, version numbers, and commands in the updated CLAUDE.md match the actual repo. No build needed (docs-only change).
- Notes/Risks: CLAUDE.md grew from 75 to ~115 lines. Source manifest table references layer names, not individual files, to avoid drift from `build.js ORDER`.

## 2026-03-01 - Workflow simplification: preview.html + lean doc set
- What changed: Replaced 4-step orchestrated workflow (Claude Code → Codex → browser smoke) with simplified Write → Build → See → Push flow.
  - **Added `preview.html`**: Single HTML file that loads the built `linkedin-carousel.jsx` artifact in a local browser via Babel Standalone (JSX transform) and React 18.2.0 UMD from unpkg CDN. Rewrites bare ESM imports (`import { useState } from "react"`) into destructured globals (`var { useState } = React;`). Requires a local server (`npx serve . --listen 5173`). Zero npm dependencies.
  - **Replaced `CLAUDE.md`**: Rewritten from ~200-line 4-step contractual process with agent orchestration to ~70-line write/build/see/push workflow. AI assistants get simple context instead of rigid role specs.
  - **Deleted smoke infrastructure**: Removed `SMOKE_TEST.md`, all agent specs (`agents/`), and `scripts/prepare-smoke-handoff.js`. Browser smoke is no longer a mandatory gate — optional AI review replaces structured handoff cards.
  - **Deleted `FEATURE_CARD.md`**: Feature scoping now happens in the prompt, not a separate file.
  - **Lean doc set**: `CLAUDE.md`, `CHANGES.md`, `preview.html`. Down from 11 markdown files.
- Why: Workflow had more governance than a solo operator needs. Structured handoff cards, role-isolated agents, pause/resume tokens, and multi-step copy-paste orchestration added overhead without proportional value. Local preview provides faster feedback than AI-driven smoke testing.
- Files: `preview.html` (added), `CLAUDE.md` (rewritten), `FEATURE_CARD.md` (deleted), `SMOKE_TEST.md` (deleted), `agents/*` (deleted), `scripts/prepare-smoke-handoff.js` (deleted), `CHANGES.md` (updated).
- Validation: `preview.html` loads artifact when served locally (`npx serve . --listen 5173`). `node build.js` unaffected. No source or artifact changes.
- Notes/Risks: `preview.html` uses Babel Standalone for JSX transform (~1-2s load time for ~2776-line file). Requires local server (fetch fails on file:// due to CORS). React version pinned to 18.2.0 via CDN URL — update if Claude.ai sandbox version changes.

## 2026-03-01 - Per-slide profile picture + unified Reset/Sync All for all background settings
- What changed: Made profile picture per-slide and extended Reset/Sync All to cover all background-panel settings.
  - **Per-slide profile picture**: Moved `profileImg` and `profilePicName` from global state into per-slide data model in `slideFactory.js`. Updated `handleProfilePicUpload()` and `removeProfilePic()` in `useSlideManagement.js` to write to the active slide. Updated `renderSlideToCanvas` in `renderSlide.js` to read `slide.profileImg` instead of a global `profileImg` parameter. Removed global `profileImg`/`setProfileImg`/`profilePicName`/`setProfilePicName`/`isCustomProfilePic`/`setIsCustomProfilePic` state. Updated `useCanvasRenderer.js` to drop the `profileImg` parameter. Updated `App.jsx` profile UI to read/write from `currentSlide.profileImg`/`currentSlide.profilePicName`. Removed profile state from undo/redo snapshots (now captured as part of `seriesSlides`).
  - **Sync All expanded**: `syncBgToAll()` now copies profile fields (`profileImg`, `profilePicName`) and screenshot fields (`showScreenshot`, `expandScreenshot`, plus `slideAssets` entry) from the active slide to all slides. Confirmation dialog updated to mention "background, profile, and screenshot".
  - **Reset expanded**: `resetBgToDefault()` now clears profile fields (`profileImg: null`, `profilePicName: null`) and screenshot fields (`showScreenshot: false`, `expandScreenshot: false`, plus removing the `slideAssets` entry) on the active slide. Confirmation dialog updated to mention "background, profile, and screenshot".
  - **Preset serialization updated**: Profile images are now serialized per-slide using `profileRef` (pattern matches `customBgRef`). `profilePicName` added to `PRESET_SLIDE_KEYS`. Legacy presets with global `profilePicRef` are backward-compatible: global profile is applied to slide 0 on load.
  - **Slide duplication**: Naturally copies per-slide profile fields via `Object.assign`.
- Why: Make profile picture independently customizable per slide and make Reset/Sync All cover the full scope of the background panel for consistent, predictable UI behavior.
- Files: `src/slideFactory.js`, `src/useSlideManagement.js`, `src/useCanvasRenderer.js`, `src/canvas/renderSlide.js`, `src/App.jsx`, `src/usePresets.js`, `linkedin-carousel.jsx` (regenerated), `CHANGES.md`, `SMOKE_TEST.md`, `FEATURE_CARD.md`.
- Validation: `node build.js` succeeds with 19 source files. No global `profileImg` state remains. `slide.profileImg` used in canvas rendering. Per-slide profile in factory defaults. `syncBgToAll` copies profile + screenshot. `resetBgToDefault` clears profile + screenshot. Preset save/load uses per-slide `profileRef`. Legacy `profilePicRef` backward compat applied to slide 0.
- Notes/Risks: Storing an `Image` object per slide increases memory if user uploads large images to many slides; acceptable for typical 2-10 slide count. Existing presets without per-slide profile load cleanly (defaults to null via `makeDefaultSlide()`). Legacy presets with global `profilePicRef` apply profile to first slide only.

## 2026-03-01 - Unified page scroll + Background panel layout fixes
- What changed: Three layout polish fixes in `src/App.jsx`.
  - **Unified page scroll**: Removed `position: "sticky"` and `top: 24` from the Left pane (Slide Selector, line ~230) and Right pane (Preview, line ~731). Both panes retain `alignSelf: "flex-start"` so they align to the top of the flex row without stretching.
  - **Background panel dead space fix**: The right zone (Profile + Screenshot cards) was inside the three-zone flex row in the BACKGROUND section. Pulled it out using `position: absolute; top: 0; right: 0` relative to the BACKGROUND container (which now has `position: relative; paddingRight: 140`). This eliminates dead space below the cards caused by the taller left zone sibling.
  - **Scale slider overflow fix**: Added `overflow: "hidden"` to the Scale row flex container and `minWidth: 0` to the range input in the Screenshot card to prevent the slider + percentage label from overflowing the 126px-wide container.
- Why: User-requested polish: unified scrolling (no sticky panes), eliminate dead space in Background section, and fix Scale slider overflow.
- Files: `src/App.jsx`, `linkedin-carousel.jsx` (regenerated), `CHANGES.md`, `SMOKE_TEST.md`, `FEATURE_CARD.md`.
- Validation: `node build.js` succeeds with 19 source files. Zero `position: "sticky"` in App.jsx. BACKGROUND container has `position: relative; paddingRight: 140`. Right zone has `position: absolute; top: 0; right: 0`. Scale row has `overflow: "hidden"` and range input has `minWidth: 0`.
- Notes/Risks: Preview and slide selector now scroll off-screen — intended trade-off per user preference. Absolute positioning means Profile+Screenshot no longer contribute to flex row height; overflow unlikely given current card sizes (~200px vs left zone ~250px+).

## 2026-03-01 - Two-pane layout: merge sidebar and editor into single left column
- What changed: Replaced the 3-column layout (fixed sidebar | flexible editor | flexible preview) with a 2-pane layout (left pane | right preview pane) to eliminate dead space below the sidebar.
  - **Left pane**: Stacks top-level settings (Presets, Background, Profile Pic, Slides selector, Screenshot) above the per-slide editor (Slide header, Footer & Pic, Corners, Heading, Body/Cards) in a single scrollable column. Uses `flex: "1 1 50%"` with `minWidth: 380`.
  - **Right pane (preview)**: Uses `flex: "1 1 50%"` with `minWidth: 360`, retains `position: sticky; top: 24px; alignSelf: flex-start`. Removed the former `maxWidth: 520` cap so preview grows with available space.
  - **Removed fixed 240px width**: Former sidebar content no longer constrained to `flex: "0 0 240px"`; sections (Background 50/50 split, Slides selector, Profile Pic, Screenshot) reflow naturally at the wider width.
  - No controls, toggles, inputs, or features were added or removed — only repositioned.
- Why: Eliminate the persistent dead space that appeared below the sidebar and editor columns in the 3-column layout.
- Files: `src/App.jsx`, `linkedin-carousel.jsx` (regenerated), `CHANGES.md`, `SMOKE_TEST.md`, `FEATURE_CARD.md`.
- Validation: `node build.js` succeeds with 19 source files. Div balance matches original (verified programmatically). Layout produces 2 flex children inside the main container.
- Notes/Risks: Former sidebar sections (Presets, Background, Profile Pic) were designed for 240px width; at ~50% viewport (~500-600px) they will be wider. Background's internal 50/50 split and color picker sizing should be visually verified. Left pane is taller due to stacking — preview stays sticky while user scrolls. Min-width sum (380 + 360 + 20 gap = 760px) may cause horizontal scroll on very narrow windows.

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


For entries before 2026-03-01, see CHANGES_ARCHIVE.md

## Entry Template
## YYYY-MM-DD - <short title>
- What changed:
- Why:
- Files:
- Validation:
- Notes/Risks:
