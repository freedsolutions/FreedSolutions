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
- `agents/browser-smoke-tester.md` (browser smoke execution spec)
- `agents/README.md` (agent index)

## Feature Session Protocol
Use this two-step trigger to keep planning and execution clean:
1. `FEATURE: <completed feature card>`
2. `IMPLEMENT`

When a session starts with `FEATURE:`:
1. Read `CLAUDE.md` and `FEATURE_CARD.md` first.
2. Inspect repo context before proposing implementation.
3. Ask clarifying questions for ambiguities that change scope or implementation.
4. Produce a decision-complete plan with files, steps, validation, and risks.
5. Stop and wait for `IMPLEMENT`.

When the user sends `IMPLEMENT`:
1. Execute the approved plan with minimal targeted edits.
2. Run relevant checks and validations.
3. Commit approved changes (no push).
4. Produce a complete smoke handoff package for browser testing.
5. Summarize changed files, behavior differences, validation results, and handoff package.

## IMPLEMENT Output Contract (Required)
`IMPLEMENT` is not complete until all items below are returned:
- Commit hash (`git rev-parse --short HEAD`)
- Files changed summary
- Validation summary (including `node build.js`)
- Fully filled `SMOKE_TEST_HANDOFF_TEMPLATE.md` content with:
  - Feature-specific scenarios derived from the feature card acceptance criteria
  - Any known risk focus for the smoke run
- Explicit statement: `DO NOT PUSH YET - Awaiting browser smoke RESULT`

## Active Agent Spec
- `agents/browser-smoke-tester.md`: browser smoke checks from a structured handoff card; no code edits.

Kickoff shortcut:
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
2. Run planning (`FEATURE:`) and lock an approved implementation plan.
3. Run implementation (`IMPLEMENT`) in terminal and apply code changes.
4. Run build and local validation in terminal.
5. Commit source/artifact/docs changes as one atomic commit.
6. Run post-commit review and capture findings/risks.
7. Fill `SMOKE_TEST_HANDOFF_TEMPLATE.md` with the commit hash and scope.
8. Start browser smoke using `agents/browser-smoke-tester.md`.
9. During smoke, respond to:
   - `PAUSE_FOR_FILE_UPLOAD` with `UPLOAD_DONE`
   - `PAUSE_FOR_ASSISTANCE` with `ASSISTANCE_DONE`
10. Collect smoke output (`RESULT`, matrix, blockers, follow-up fixes).
11. If smoke fails, return to terminal implementation and repeat from step 3.
12. Push to `origin/main` only after smoke returns `RESULT: PASS`.

Terminal-to-browser handoff checkpoint:
- If terminal output does not include commit hash + filled smoke handoff card, do not start browser smoke.
- Request the missing handoff package in terminal first.

## Required Commands
Pre-smoke commands:
1. `git status --short`
2. `node build.js`
3. `git diff -- src linkedin-carousel.jsx CLAUDE.md CHANGES.md FEATURE_CARD.md SMOKE_TEST_HANDOFF_TEMPLATE.md agents`
4. `git add <changed files>`
5. `git commit -m "<clear summary>"`
6. `git rev-parse --short HEAD`
7. Fill and return `SMOKE_TEST_HANDOFF_TEMPLATE.md` in terminal output

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
