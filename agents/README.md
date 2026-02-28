# Agents
This folder contains lightweight agent role specs for terminal delivery and browser smoke handoffs.

## Active Agent Specs
- `terminal-feature-flow.md`: one-command terminal flow from `FEATURE_CARD.md` through commit review and smoke handoff prep.
- `browser-smoke-tester.md`: run browser smoke tests from a handoff card without editing code.

## How To Use
1. Keep `CLAUDE.md` as workflow source of truth.
2. Run terminal implementation flow:
   - `SHIP: Use agents/terminal-feature-flow.md with FEATURE_CARD.md and produce a completed SMOKE_TEST_HANDOFF_TEMPLATE.md.`
3. Start browser smoke:
   - `SMOKE: Use agents/browser-smoke-tester.md and SMOKE_TEST_HANDOFF_TEMPLATE.md.`

## Guardrails
- Terminal flow stops before push.
- Browser flow does smoke testing only.
- Pause/resume tokens are required:
  - `PAUSE_FOR_FILE_UPLOAD` / `UPLOAD_DONE`
  - `PAUSE_FOR_ASSISTANCE` / `ASSISTANCE_DONE`
