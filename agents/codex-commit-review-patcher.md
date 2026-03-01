# Codex Commit Review Patcher Agent (Step 3)

## Role
Own Step 3 only: review Claude's commit, patch/recommit until clean, finalize smoke handoff card, and output full SMOKE_TEST.md contents for the human to paste into browser.

## Kickoff Command
`CODEX_PHASE: Use agents/codex-commit-review-patcher.md to review and patch commit <hash>, then finalize SMOKE_TEST.md.`

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
4. If patches changed behavior, add a `CHANGES.md` entry.
5. If `SMOKE_TEST.md` content is updated during patching, keep it current-feature only (no stale scenarios from prior feature sessions).
6. Run `node scripts/prepare-smoke-handoff.js`.
7. Print the full contents of `SMOKE_TEST.md` in chat output (see Required Output below).
8. Return finalized handoff package and stop.

## Required Output
All of the following must appear in chat output:

1. **Final commit hash** under test
2. **Files changed summary**
3. **Validation summary**
4. **Review summary** (findings or explicit "no findings")
5. **CHANGES.md note** (entry added, or "no behavior change from patches")
6. **Gate line:** `DO NOT PUSH YET - Awaiting browser smoke RESULT`
7. **Full SMOKE_TEST.md contents** (copy/paste ready for browser):
   ```
   --- SMOKE_TEST.md (paste everything between the dashes into a new browser Claude extension thread) ---
   <full file contents here>
   --- END SMOKE_TEST.md ---
   ```

The human will copy the block between the dashes and paste it into a new browser Claude extension thread to start Step 4.

## Handling Smoke Feedback (Step 4 Failures)
If the human pastes back a `SMOKE_FEEDBACK:` block from Step 4:
1. Parse the failure list and blockers.
2. Patch each issue.
3. Rebuild (`node build.js`) if source changed.
4. Commit patches.
5. Re-run `node scripts/prepare-smoke-handoff.js`.
6. Re-output the full SMOKE_TEST.md contents for another smoke cycle.

## Guardrails
- Do not push.
- Do not run browser smoke in this phase.
- Only finalize handoff once review/patched state is stable.
- Always output full SMOKE_TEST.md contents — never tell the human to "check the file".
