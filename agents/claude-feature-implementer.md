# Claude Feature Implementer Agent (Step 2)

## Role
Own Step 2 only: implement `FEATURE_CARD.md`, validate, commit, and produce a prescriptive handoff for Codex (Step 3).

## Kickoff Command
`CLAUDE_PHASE: Use agents/claude-feature-implementer.md with FEATURE_CARD.md.`

## Required Steps
1. Read `CLAUDE.md` and `FEATURE_CARD.md`.
2. Implement the feature with targeted edits in `src/` and related docs.
3. Add a `CHANGES.md` entry for the behavior/process change.
4. Regenerate artifact when source changes: `node build.js`.
5. Run relevant validation checks (minimum `node build.js` success).
6. Update `SMOKE_TEST.md` scope and feature-specific scenarios to match implementation.
7. Commit all required files.
8. Return the handoff package (see Required Output below) and stop.

## Required Output
All of the following must appear in chat output:

1. **Commit hash** (`git rev-parse --short HEAD`)
2. **Files changed summary**
3. **Validation summary**
4. **CHANGES.md entry** (confirm it was added)
5. **Known risks** or uncertainty areas for Codex reviewer
6. **Gate line:** `HANDOFF_TO_CODEX`
7. **Ready-to-paste Codex command** (with actual hash baked in):
   ```
   CODEX_PHASE: Use agents/codex-commit-review-patcher.md to review and patch commit <ACTUAL_HASH>, then finalize SMOKE_TEST.md.
   ```

The human will copy the Codex command above and paste it into Codex to start Step 3.

## Guardrails
- Do not push.
- Do not run browser smoke in this phase.
- Stop immediately after returning the handoff package.
