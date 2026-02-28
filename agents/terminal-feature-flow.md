# Terminal Feature Flow Agent (Legacy)

## Role
Legacy single-owner terminal flow retained for reference. The default workflow is now split:
- Phase 1 in Claude Code
- Phase 2 in Codex
- Phase 3 in Browser smoke

## One-Command Trigger
Use this exact command in terminal Claude/Codex:

`SHIP: Use agents/terminal-feature-flow.md with FEATURE_CARD.md and produce a completed SMOKE_TEST_HANDOFF_TEMPLATE.md.`

Do not use this as default. Prefer `CLAUDE_PHASE` then `CODEX_PHASE` as defined in `CLAUDE.md`.

## Operating Steps (Required)
1. Read `CLAUDE.md`, `FEATURE_CARD.md`, and relevant code context.
2. Implement the feature in `src/` using minimal targeted edits.
3. Run validation (`node build.js` minimum; add focused checks when relevant).
4. Commit all required files (source + regenerated artifact + docs).
5. Review the latest commit with a code-review mindset:
   - findings first, severity ordered, with file/line references
6. If findings exist:
   - patch immediately
   - rebuild if source changed
   - commit patch
   - repeat review until no material findings remain
7. Run `node scripts/prepare-smoke-handoff.js` to stamp handoff metadata.
8. Return the final handoff package and stop before push.

## Output Contract
Must include all:
- Final commit hash under test
- Files changed summary
- Validation summary
- Commit-review summary (or explicit "no findings")
- Completed `SMOKE_TEST_HANDOFF_TEMPLATE.md` content
- Exact gate line: `DO NOT PUSH YET - Awaiting browser smoke RESULT`

## Guardrails
- Do not manually edit `linkedin-carousel.jsx`; always regenerate via `node build.js`.
- Do not push in this flow.
- Keep commits atomic per patch cycle.
- If smoke fails later, return to this flow starting at implementation+patch.
