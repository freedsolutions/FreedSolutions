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

## Kickoff Shortcuts
- Planning kickoff: `FEATURE: Use FEATURE_CARD.md. Inspect repo, ask clarifying questions for ambiguity, produce a decision-complete plan, then wait for IMPLEMENT.`
- Execution kickoff: `IMPLEMENT`
- Review kickoff: `REVIEW: Findings first, ordered by severity, with file/line references.`

## Required End-to-End Flow
1. Restate request and constraints.
2. Plan impacted files.
3. Edit only `src/*` (never direct artifact edits).
4. Run `node build.js`.
5. Run focused validation for touched behavior.
6. Update docs when behavior or process changed.
7. Commit one atomic changeset.
8. Push with `git push origin main`.

## Required Commands
Run these in order for normal implementation tasks:
1. `git status --short`
2. `node build.js`
3. `git diff -- src linkedin-carousel.jsx CLAUDE.md CHANGES.md FEATURE_CARD.md`
4. `git add <changed files>`
5. `git commit -m "<clear summary>"`
6. `git push origin main`

## Definition of Done
All of the following must be true:
- Artifact regenerated if any `src/*` changed.
- Focused smoke check completed for touched area.
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
