# Agents
This folder contains lightweight agent role specs for browser smoke-test handoffs.

## Active Agent Spec
- `browser-smoke-tester.md`: run browser smoke tests from a handoff card without editing code.

## How To Use
1. Keep `CLAUDE.md` as workflow source of truth.
2. Prepare and fill `SMOKE_TEST_HANDOFF_TEMPLATE.md`.
3. Start browser smoke with:
   - `SMOKE: Use agents/browser-smoke-tester.md and SMOKE_TEST_HANDOFF_TEMPLATE.md.`

## Guardrails
- Browser agent does smoke testing only.
- Pause/resume tokens are required:
  - `PAUSE_FOR_FILE_UPLOAD` / `UPLOAD_DONE`
  - `PAUSE_FOR_ASSISTANCE` / `ASSISTANCE_DONE`
