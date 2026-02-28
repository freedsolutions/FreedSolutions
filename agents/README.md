# Agents
This folder contains lightweight agent role specs for the prescriptive Claude Code -> Codex -> Browser flow.

## Active Agent Specs
- `claude-feature-implementer.md`: Claude Code phase; implements `FEATURE_CARD.md`, validates, and commits.
- `codex-commit-review-patcher.md`: Codex phase; reviews Claude commit, patches/recommits until clean, and finalizes smoke handoff metadata.
- `browser-smoke-tester.md`: Browser phase; smoke tests from handoff card only (no code edits).

## How To Use (Back-to-Back Required)
1. Keep `CLAUDE.md` as workflow source of truth.
2. Run Claude Code phase:
   - `CLAUDE_PHASE: Use agents/claude-feature-implementer.md with FEATURE_CARD.md.`
3. Run Codex phase using Claude's commit hash:
   - `CODEX_PHASE: Use agents/codex-commit-review-patcher.md to review and patch commit <hash>, then finalize SMOKE_TEST.md.`
4. Run Browser smoke phase:
   - `SMOKE: In browser Claude extension, paste the full contents of SMOKE_TEST.md into a new thread and run smoke tests. DO NOT CLOSE OUT THE BROWSER.`

## Guardrails
- Phases must run in order with explicit handoff outputs at each gate.
- Claude and Codex phases stop before push.
- Browser phase does smoke testing only.
- Pause/resume tokens are required:
  - `PAUSE_FOR_FILE_UPLOAD` / `UPLOAD_DONE`
  - `PAUSE_FOR_ASSISTANCE` / `ASSISTANCE_DONE`
