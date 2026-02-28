# Codex Commit Review Patcher Agent

## Role
Own Phase 2 only: review Claude's commit, patch/recommit until clean, and finalize smoke handoff card.

## Kickoff Command
`CODEX_PHASE: Use agents/codex-commit-review-patcher.md to review and patch commit <hash>, then finalize SMOKE_TEST_HANDOFF_TEMPLATE.md.`

## Required Steps
1. Review the specified commit with findings-first code review rigor:
   - bugs/regressions/risks first
   - severity ordered
   - file/line references
2. If findings exist:
   - patch immediately
   - rebuild when source changes (`node build.js`)
   - commit patch
   - re-review latest commit
3. Repeat until no material findings remain.
4. Run `node scripts/prepare-smoke-handoff.js`.
5. Return finalized browser handoff package and stop.

## Required Output
- Final commit hash under test
- Files changed summary
- Validation summary
- Review summary (or explicit "no findings")
- Completed `SMOKE_TEST_HANDOFF_TEMPLATE.md` content
- Exact gate line: `DO NOT PUSH YET - Awaiting browser smoke RESULT`

## Guardrails
- Do not push.
- Do not run browser smoke in this phase.
- Only finalize handoff once review/patched state is stable.
