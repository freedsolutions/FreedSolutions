# Agents
This folder contains lightweight agent role specs for the prescriptive 4-step workflow.

## Active Agent Specs
- `claude-feature-implementer.md`: Step 2 — Claude Code implements `FEATURE_CARD.md`, validates, commits, and outputs a ready-to-paste Codex command.
- `codex-commit-review-patcher.md`: Step 3 — Codex reviews Claude commit, patches/recommits until clean, and outputs full SMOKE_TEST.md contents for copy/paste.
- `browser-smoke-tester.md`: Step 4 — browser smoke tests from pasted handoff card; outputs RESULT + prescriptive feedback block on failure.

## How To Use (4-Step Flow)
1. **Step 1** (Browser Claude UI): Draft `FEATURE_CARD.md`.
2. **Step 2** (Claude Code): Paste `CLAUDE_PHASE: Use agents/claude-feature-implementer.md with FEATURE_CARD.md.`
   - Output gives you the Codex command with hash baked in.
3. **Step 3** (Codex): Paste the Codex command from Step 2.
   - Output gives you full SMOKE_TEST.md contents to copy.
4. **Step 4** (Browser): Paste SMOKE_TEST.md contents into a new browser thread. DO NOT CLOSE OUT THE BROWSER.
   - If FAIL: output gives you a feedback block to paste back into Codex (Step 3).

## Guardrails
- Steps must run in order. Each step's output tells you exactly what to do next.
- Claude and Codex steps stop before push.
- Browser step does smoke testing only (no code edits).
- Pause/resume tokens are required:
  - `PAUSE_FOR_FILE_UPLOAD` / `UPLOAD_DONE`
  - `PAUSE_FOR_ASSISTANCE` / `ASSISTANCE_DONE`
