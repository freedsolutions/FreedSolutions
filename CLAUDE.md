# FreedSolutions Workflow Guide

## Purpose
This repository contains the LinkedIn carousel generator with editable modular source in `src/` and a generated single-file artifact in `linkedin-carousel.jsx`; this document is the canonical workflow contract for Claude/Codex agents and human contributors.

## Repo Truth
- `src/` is the editable source of behavior.
- `linkedin-carousel.jsx` is the generated artifact.
- `build.js` is the deterministic build script that regenerates `linkedin-carousel.jsx`.

## Lean Core Docs
Use only this minimal set for the default workflow:
- `CLAUDE.md` (workflow contract)
- `CHANGES.md` (process/behavior log)
- `FEATURE_CARD.md` (feature intent)
- `SMOKE_TEST_HANDOFF_TEMPLATE.md` (browser handoff card)
- `scripts/prepare-smoke-handoff.js` (handoff metadata stamper)
- `agents/claude-feature-implementer.md` (Phase 1: Claude implementation + commit)
- `agents/codex-commit-review-patcher.md` (Phase 2: Codex review + patch + handoff finalization)
- `agents/browser-smoke-tester.md` (browser smoke execution spec)
- `agents/README.md` (agent index)

## Feature Session Protocol (Default, Prescriptive, Back-to-Back)
Phases must run in this exact order with no skipping:
1. Phase 1 (Claude Code): implement + validate + commit.
2. Phase 2 (Codex): review Claude commit + patch/recommit loop + finalize smoke handoff.
3. Phase 3 (Browser Claude Extension): smoke test only from provided handoff context.

Phase 1 kickoff command (Claude Code):
- `CLAUDE_PHASE: Use agents/claude-feature-implementer.md with FEATURE_CARD.md.`

Phase 2 kickoff command (Codex, immediately after Phase 1):
- `CODEX_PHASE: Use agents/codex-commit-review-patcher.md to review and patch commit <hash>, then finalize SMOKE_TEST_HANDOFF_TEMPLATE.md.`

Phase 3 kickoff command (Browser Claude, after Phase 2):
- `SMOKE: Use agents/browser-smoke-tester.md and SMOKE_TEST_HANDOFF_TEMPLATE.md.`

## Phase Output Contracts (Required)
Phase 1 (`CLAUDE_PHASE`) is not complete until all are returned:
- Commit hash (`git rev-parse --short HEAD`)
- Files changed summary
- Validation summary (including `node build.js`)
- Known risk notes for Codex reviewer
- Exact gate line: `HANDOFF_TO_CODEX`

Phase 2 (`CODEX_PHASE`) is not complete until all are returned:
- Final commit hash under test
- Files changed summary
- Validation summary (including `node build.js` if source changed)
- Commit-review summary (findings or explicit "no findings")
- Fully filled `SMOKE_TEST_HANDOFF_TEMPLATE.md` content
- Exact gate line: `DO NOT PUSH YET - Awaiting browser smoke RESULT`

## Active Agent Specs
- `agents/claude-feature-implementer.md`: Claude phase implementation + commit handoff.
- `agents/codex-commit-review-patcher.md`: Codex phase review/patch loop + handoff finalization.
- `agents/browser-smoke-tester.md`: browser smoke checks from a structured handoff card; no code edits.

Kickoff shortcut:
- `CLAUDE_PHASE: Use agents/claude-feature-implementer.md with FEATURE_CARD.md.`
- `CODEX_PHASE: Use agents/codex-commit-review-patcher.md to review and patch commit <hash>, then finalize SMOKE_TEST_HANDOFF_TEMPLATE.md.`
- `SMOKE: Use agents/browser-smoke-tester.md and SMOKE_TEST_HANDOFF_TEMPLATE.md.`

## Browser Smoke Test Handoff (Human-in-the-Loop)
Use this when validating `linkedin-carousel.jsx` in a browser extension session with no repository context.

Rules:
- Browser sessions are context-isolated: always provide a structured handoff card.
- For any step that requires the Windows file picker, browser Claude must pause before the action.
- For progress-blocking roadblocks where human help can unblock testing, browser Claude must pause.
- Upload pause token: `PAUSE_FOR_FILE_UPLOAD: <instruction>`
- Upload resume token: `UPLOAD_DONE: <what was uploaded>`
- Assistance pause token: `PAUSE_FOR_ASSISTANCE: <roadblock + requested human action>`
- Assistance resume token: `ASSISTANCE_DONE: <what was done>`
- Browser Claude must not assume completion until the corresponding resume token is received.

Browser final output contract:
- `RESULT: PASS|FAIL`
- `SCENARIO_MATRIX` table
- `BLOCKERS`
- `FOLLOW_UP_FIXES` with minimal reproducible steps per failure

Smoke signoff gate:
- Commit is allowed before browser smoke test to enable review traceability.
- Push is blocked until smoke signoff is `RESULT: PASS` (or fixes are applied and re-tested).

Use `SMOKE_TEST_HANDOFF_TEMPLATE.md` as the standard handoff card.

## Human Execution Checklist
1. Prepare `FEATURE_CARD.md` for the feature.
2. Run Claude Code phase:
   - `CLAUDE_PHASE: Use agents/claude-feature-implementer.md with FEATURE_CARD.md.`
3. Confirm Claude output includes commit hash + `HANDOFF_TO_CODEX`.
4. Run Codex phase immediately using Claude commit hash:
   - `CODEX_PHASE: Use agents/codex-commit-review-patcher.md to review and patch commit <hash>, then finalize SMOKE_TEST_HANDOFF_TEMPLATE.md.`
5. Confirm Codex output includes completed handoff card + `DO NOT PUSH YET - Awaiting browser smoke RESULT`.
6. Start browser smoke using `agents/browser-smoke-tester.md`.
7. During smoke, respond to:
   - `PAUSE_FOR_FILE_UPLOAD` with `UPLOAD_DONE`
   - `PAUSE_FOR_ASSISTANCE` with `ASSISTANCE_DONE`
8. Collect smoke output (`RESULT`, matrix, blockers, follow-up fixes).
9. If smoke fails, rerun Phase 2 (`CODEX_PHASE`) with blocker patch scope.
10. Push to `origin/main` only after smoke returns `RESULT: PASS`.

Terminal-to-browser handoff checkpoint:
- If terminal output does not include commit hash + filled smoke handoff card, do not start browser smoke.
- Request the missing handoff package in terminal first.

## Required Commands
Phase 1 commands (Claude Code):
1. `git status --short`
2. `node build.js`
3. `git diff -- src linkedin-carousel.jsx CLAUDE.md CHANGES.md FEATURE_CARD.md SMOKE_TEST_HANDOFF_TEMPLATE.md agents scripts`
4. `git add <changed files>`
5. `git commit -m "<clear summary>"`
6. `git show --name-status --oneline -1`

Phase 2 commands (Codex):
1. `git show --name-status --oneline <claude-commit-hash>`
2. Review + patch + commit loop until no material findings remain
3. `node build.js` (required if source changed)
4. `node scripts/prepare-smoke-handoff.js`
5. Return filled `SMOKE_TEST_HANDOFF_TEMPLATE.md` in terminal output

Post-smoke command (only after `RESULT: PASS`):
1. `git push origin main`

## Definition of Done
All of the following must be true:
- Artifact regenerated if any `src/*` changed.
- Focused smoke check completed for touched area.
- Browser smoke signoff recorded (`RESULT: PASS`) for interactive behavior changes.
- Docs updated if behavior or process changed.
- Working tree clean after commit.
- Remote updated on `origin/main`.

## Documentation Update Rules
- `CLAUDE.md`: update only when workflow/contracts/guardrails change.
- `CHANGES.md`: add entry when behavior or process changes.
- Pure internal refactors with no behavior/process effect do not require a doc entry.

## Git Policy
- Direct push to `main`.
- Single atomic commit per task when applicable (source + generated artifact + docs in same commit).

## Hard Guardrails
- Do not edit generated artifact manually.
- Do not skip build after source change.
- Do not push without smoke-check + diff review.
- Do not skip pause/resume tokens in browser smoke sessions.
