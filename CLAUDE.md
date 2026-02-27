# FreedSolutions Workflow Guide

## Purpose
This repository contains the LinkedIn carousel generator with editable modular source in `src/` and a generated single-file artifact in `linkedin-carousel.jsx`; this document is the canonical workflow contract for Claude/Codex agents and human contributors.

## Repo Truth
- `src/` is the editable source of behavior.
- `linkedin-carousel.jsx` is the generated artifact.
- `build.js` is the deterministic build script that regenerates `linkedin-carousel.jsx`.

## Feature Session Protocol
Use this two-step trigger to keep planning and execution clean:
1. `FEATURE: <completed feature card>`
2. `IMPLEMENT`

When a session starts with `FEATURE:`:
1. Read `CLAUDE.md` and `FEATURE_CARD.md` first.
2. Inspect repo context before proposing implementation.
3. Ask clarifying questions for any ambiguity that changes scope or implementation.
4. Produce a decision-complete plan with files, steps, validation, and risks.
5. Stop and wait for `IMPLEMENT`.

When the user sends `IMPLEMENT`:
1. Execute the approved plan with minimal targeted edits.
2. Run relevant checks and validations.
3. Summarize changed files, behavior differences, and validation results.

## Optional Agent Specs
Use these when you want stricter role separation without changing the core workflow:
- `agents/planner.md`: discovery, clarifying questions, decision-complete plan.
- `agents/implementer.md`: execute an approved plan with minimal edits and validations.
- `agents/reviewer.md`: findings-first review with severity and file/line references.
- `agents/browser-smoke-tester.md`: run browser smoke checks from a structured handoff card; no code edits.

If using an agent spec, read `CLAUDE.md`, `FEATURE_CARD.md`, and that specific `agents/*.md` file at kickoff.

## Kickoff Shortcuts
- Planning kickoff: `FEATURE: Use FEATURE_CARD.md. Inspect repo, ask clarifying questions for ambiguity, produce a decision-complete plan, then wait for IMPLEMENT.`
- Execution kickoff: `IMPLEMENT`
- Review kickoff: `REVIEW: Findings first, ordered by severity, with file/line references.`
- Planner agent kickoff: `FEATURE: Use agents/planner.md and FEATURE_CARD.md.`
- Implementer agent kickoff: `IMPLEMENT: Use agents/implementer.md.`
- Reviewer agent kickoff: `REVIEW: Use agents/reviewer.md.`
- Browser smoke kickoff: `SMOKE: Use agents/browser-smoke-tester.md and SMOKE_TEST_HANDOFF_TEMPLATE.md.`

## Browser Smoke Test Handoff (Human-in-the-Loop)
Use this when validating `linkedin-carousel.jsx` in a browser extension session that has no repository context.

Rules:
- Browser sessions are context-isolated: always provide a structured handoff prompt/card.
- For any step that requires the Windows file picker, browser Claude must pause before the action.
- Pause token: `PAUSE_FOR_FILE_UPLOAD: <instruction>`
- Resume token from human: `UPLOAD_DONE: <what was uploaded>`
- Browser Claude must not assume upload completion until it receives the resume token.

Smoke signoff gate:
- Commit is allowed before browser smoke test to enable cross-agent review.
- Push is blocked until smoke signoff is reported as `RESULT: PASS` (or fixes are applied and re-tested).

Handoff checklist:
- Commit hash under test
- Scope under test (in/out)
- Required upload files
- Test scenarios
- Known risks to target

Use `SMOKE_TEST_HANDOFF_TEMPLATE.md` as the standard handoff card.

## Required End-to-End Flow
1. Restate request and constraints.
2. Plan impacted files.
3. Edit only `src/*` (never direct artifact edits).
4. Run `node build.js`.
5. Run focused validation for touched behavior.
6. Update docs when behavior or process changed.
7. Commit one atomic changeset.
8. Prepare a browser smoke handoff card with commit hash, scope, required uploads, scenarios, and known risks.
9. Run browser smoke via `agents/browser-smoke-tester.md` and record the result.
10. If smoke result is `FAIL`, return to implementation, then rebuild and re-test.
11. Push with `git push origin main` only after smoke result is `PASS`.

## Required Commands
Pre-smoke commands:
1. `git status --short`
2. `node build.js`
3. `git diff -- src linkedin-carousel.jsx CLAUDE.md CHANGES.md FEATURE_CARD.md agents`
4. `git add <changed files>`
5. `git commit -m "<clear summary>"`
6. `git rev-parse --short HEAD`

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
- Do not skip pause/resume tokens for file-picker steps in browser smoke sessions.
