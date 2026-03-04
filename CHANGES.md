# CHANGES
Operational change log for behavior and workflow updates in this repo.
Add newest entries at the top.

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
