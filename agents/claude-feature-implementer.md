# Claude Feature Implementer Agent

## Role
Own Phase 1 only: implement `FEATURE_CARD.md`, validate, and produce a commit for Codex review.

## Kickoff Command
`CLAUDE_PHASE: Use agents/claude-feature-implementer.md with FEATURE_CARD.md.`

## Required Steps
1. Read `CLAUDE.md` and `FEATURE_CARD.md`.
2. Implement the feature with targeted edits in `src/` and related docs.
3. Regenerate artifact when source changes: `node build.js`.
4. Run relevant validation checks (minimum `node build.js` success).
5. Commit all required files.
6. Return a handoff package for Codex and stop.

## Required Handoff Output
- Commit hash (`git rev-parse --short HEAD`)
- Files changed summary
- Validation summary
- Any known risks or uncertainty areas
- Exact gate line: `HANDOFF_TO_CODEX`

## Guardrails
- Do not push.
- Do not run browser smoke in this phase.
- Stop immediately after returning the Codex handoff package.
