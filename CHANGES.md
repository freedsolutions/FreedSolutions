# CHANGES
Operational change log for behavior and workflow updates in this repo.
Add newest entries at the top.

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
