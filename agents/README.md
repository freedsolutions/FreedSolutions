# Agents
This folder contains lightweight agent role specs for Claude Code sessions.
They are optional overlays on top of `CLAUDE.md`, not a separate workflow.

## Available Agent Specs
- `planner.md`: convert feature intent into a decision-complete plan.
- `implementer.md`: execute an approved plan with minimal targeted changes.
- `reviewer.md`: review changes with findings first and clear severity.
- `browser-smoke-tester.md`: run browser smoke tests from a handoff card without editing code.

## How To Use
1. Keep `CLAUDE.md` as source of truth.
2. Start with a normal trigger (`FEATURE`, `IMPLEMENT`, `REVIEW`, `SMOKE`).
3. Include the agent spec in the kickoff prompt when useful.

Examples:
- `FEATURE: Use agents/planner.md and FEATURE_CARD.md.`
- `IMPLEMENT: Use agents/implementer.md.`
- `REVIEW: Use agents/reviewer.md.`
- `SMOKE: Use agents/browser-smoke-tester.md and SMOKE_TEST_HANDOFF_TEMPLATE.md.`

## Authoring Guidelines
- Single responsibility: one role per file.
- Explicit I/O: define required inputs and exact output format.
- Minimal duplication: reference `CLAUDE.md` instead of restating core policy.
- Validation-aware: include required checks for that role.
- Keep concise: each agent spec should stay short and operational.
