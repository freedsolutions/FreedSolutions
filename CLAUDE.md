# FreedSolutions Workflow Quickstart (Human Reference)

Copy-paste these commands step-by-step. Each step's output tells you exactly what to do next.

**Step 1 — Feature Prep (Browser Claude UI):**
```
FEATURE_PREP: Draft/update FEATURE_CARD.md to implementation-ready quality (goal, scope, out-of-scope, constraints, acceptance, risks). Return final markdown only.
```

**Step 2 — Claude Code Implement:**
```
CLAUDE_PHASE: Use agents/claude-feature-implementer.md with FEATURE_CARD.md.
```
Gate: output includes commit hash + `HANDOFF_TO_CODEX` + ready-to-paste Codex command.

**Step 3 — Codex Review/Patch:**
Paste the Codex command from Step 2 output (it has the commit hash baked in).
Gate: output includes `DO NOT PUSH YET` + full SMOKE_TEST.md contents for copy/paste.

**Step 4 — Browser Smoke:**
Copy the full SMOKE_TEST.md block from Step 3 output and paste it into a **new browser Claude extension thread**. DO NOT CLOSE OUT THE BROWSER.
Gate: output includes `RESULT: PASS|FAIL` + prescriptive feedback block.

**If smoke fails:** Copy the browser output (it's formatted as a patch request) and paste it back into the Codex thread from Step 3. Codex patches, re-outputs SMOKE_TEST.md, and you re-run Step 4.

**Push only after:** `RESULT: PASS`
```
git push origin main
```

---

# FreedSolutions Workflow Guide

## Purpose
This repository contains the LinkedIn carousel generator with editable modular source in `src/` and a generated single-file artifact in `linkedin-carousel.jsx`; this document is the canonical workflow contract for Claude/Codex agents and human contributors.

## Repo Truth
- `src/` is the editable source of behavior.
- `linkedin-carousel.jsx` is the generated artifact.
- `build.js` is the deterministic build script that regenerates `linkedin-carousel.jsx`.

## Lean Core Docs
Use only this minimal set for the default workflow:
- `CLAUDE.md` (workflow contract)
- `CHANGES.md` (process/behavior log)
- `FEATURE_CARD.md` (feature intent)
- `SMOKE_TEST.md` (browser handoff card)
- `scripts/prepare-smoke-handoff.js` (handoff metadata stamper)
- `agents/claude-feature-implementer.md` (Step 2: Claude implementation + commit)
- `agents/codex-commit-review-patcher.md` (Step 3: Codex review + patch + handoff finalization)
- `agents/browser-smoke-tester.md` (Step 4: browser smoke execution spec)
- `agents/README.md` (agent index)

## Feature Session Protocol (Default, Prescriptive, 4-Step)
Steps must run in this exact order with no skipping:
1. Step 1 (Browser Claude UI): draft/refine `FEATURE_CARD.md`.
2. Step 2 (Claude Code): implement + validate + commit + output Codex kickoff command.
3. Step 3 (Codex): review Claude commit + patch/recommit loop + output full SMOKE_TEST.md for copy/paste.
4. Step 4 (Browser Claude Extension): smoke test from pasted SMOKE_TEST.md contents.

If Step 4 fails: paste browser output back into Step 3 Codex thread for patch cycle, then re-run Step 4.

## Step Output Contracts (Required)

### Step 1 (`FEATURE_PREP`) output:
- Updated `FEATURE_CARD.md` content (final markdown)

### Step 2 (`CLAUDE_PHASE`) output — not complete until ALL are returned:
- Commit hash (`git rev-parse --short HEAD`)
- Files changed summary
- Validation summary (including `node build.js`)
- `CHANGES.md` entry (added during implementation)
- Known risk notes for Codex reviewer
- Exact gate line: `HANDOFF_TO_CODEX`
- **Ready-to-paste Codex command** (with hash baked in):
  ```
  CODEX_PHASE: Use agents/codex-commit-review-patcher.md to review and patch commit <ACTUAL_HASH>, then finalize SMOKE_TEST.md.
  ```

### Step 3 (`CODEX_PHASE`) output — not complete until ALL are returned:
- Final commit hash under test
- Files changed summary
- Validation summary (including `node build.js` if source changed)
- Commit-review summary (findings or explicit "no findings")
- `CHANGES.md` entry (only if patches changed behavior)
- Exact gate line: `DO NOT PUSH YET - Awaiting browser smoke RESULT`
- **Full SMOKE_TEST.md contents** printed in chat (copy/paste ready for Step 4):
  ```
  --- SMOKE_TEST.md (paste everything between the dashes into browser) ---
  <full file contents>
  --- END SMOKE_TEST.md ---
  ```

### Step 4 (Browser smoke) output — not complete until ALL are returned:
- `RESULT: PASS|FAIL`
- `SCENARIO_MATRIX` table
- `BLOCKERS`
- `FOLLOW_UP_FIXES` with minimal reproducible steps per failure
- **If FAIL, prescriptive feedback block** (copy/paste ready for Codex thread):
  ```
  SMOKE_FEEDBACK: The following failures were found during browser smoke testing of commit <hash>.
  Patch the issues below, rebuild, recommit, and re-output the full SMOKE_TEST.md contents for another smoke cycle.

  FAILURES:
  <numbered list of failures with reproduction steps>

  BLOCKERS:
  <blockers if any, or "None">
  ```

## Active Agent Specs
- `agents/claude-feature-implementer.md`: Step 2 — Claude implementation + commit handoff.
- `agents/codex-commit-review-patcher.md`: Step 3 — Codex review/patch loop + smoke handoff.
- `agents/browser-smoke-tester.md`: Step 4 — browser smoke checks from structured handoff card; no code edits.

## Browser Smoke Test Handoff (Human-in-the-Loop)
Use this when validating `linkedin-carousel.jsx` in a browser extension session with no repository context.

Rules:
- Browser sessions are context-isolated: always provide a structured handoff card.
- Browser extension flow is paste-only: paste the full SMOKE_TEST.md contents from Step 3 output.
- DO NOT CLOSE OUT THE BROWSER during the smoke session.
- For any step that requires the Windows file picker, browser Claude must pause before the action.
- For progress-blocking roadblocks where human help can unblock testing, browser Claude must pause.
- Upload pause token: `PAUSE_FOR_FILE_UPLOAD: <instruction>`
- Upload resume token: `UPLOAD_DONE: <what was uploaded>`
- Assistance pause token: `PAUSE_FOR_ASSISTANCE: <roadblock + requested human action>`
- Assistance resume token: `ASSISTANCE_DONE: <what was done>`
- Browser Claude must not assume completion until the corresponding resume token is received.

Smoke signoff gate:
- Commit is allowed before browser smoke test to enable review traceability.
- Push is blocked until smoke signoff is `RESULT: PASS` (or fixes are applied and re-tested).

Use `SMOKE_TEST.md` as the standard handoff card.

## Human Execution Checklist
1. Prepare `FEATURE_CARD.md` (Step 1 in browser Claude UI).
2. Run Claude Code phase:
   - `CLAUDE_PHASE: Use agents/claude-feature-implementer.md with FEATURE_CARD.md.`
3. Confirm Claude output includes commit hash + `HANDOFF_TO_CODEX` + ready-to-paste Codex command.
4. Paste the Codex command from Step 2 output into Codex.
5. Confirm Codex output includes `DO NOT PUSH YET` + full SMOKE_TEST.md contents in chat.
6. Copy the SMOKE_TEST.md block from Step 3 output and paste into a new browser Claude extension thread. DO NOT CLOSE OUT THE BROWSER.
7. During smoke, respond to:
   - `PAUSE_FOR_FILE_UPLOAD` with `UPLOAD_DONE`
   - `PAUSE_FOR_ASSISTANCE` with `ASSISTANCE_DONE`
8. Collect smoke output (`RESULT`, matrix, blockers, follow-up fixes).
9. If `RESULT: FAIL`:
   - Copy the prescriptive feedback block from browser output.
   - Paste it back into the Codex thread (Step 3).
   - Codex patches, rebuilds, recommits, and re-outputs SMOKE_TEST.md.
   - Re-run Step 6 with the new SMOKE_TEST.md.
10. Push to `origin/main` only after smoke returns `RESULT: PASS`.

Terminal-to-browser handoff checkpoint:
- If Step 3 output does not include full SMOKE_TEST.md contents, do not start browser smoke.
- Request the missing output in the Codex thread first.

## Required Commands
Step 2 commands (Claude Code):
1. `git status --short`
2. `node build.js`
3. `git diff -- src linkedin-carousel.jsx CLAUDE.md CHANGES.md FEATURE_CARD.md SMOKE_TEST.md agents scripts`
4. `git add <changed files>`
5. `git commit -m "<clear summary>"`
6. `git show --name-status --oneline -1`

Step 3 commands (Codex):
1. `git show --name-status --oneline <claude-commit-hash>`
2. Review + patch + commit loop until no material findings remain
3. `node build.js` (required if source changed)
4. `node scripts/prepare-smoke-handoff.js`
5. `cat SMOKE_TEST.md` (print full contents in output for copy/paste)

Post-smoke command (only after `RESULT: PASS`):
1. `git push origin main`

## Definition of Done
All of the following must be true:
- Artifact regenerated if any `src/*` changed.
- Focused smoke check completed for touched area.
- Browser smoke signoff recorded (`RESULT: PASS`) for interactive behavior changes.
- Docs updated if behavior or process changed.
- Working tree clean after commit.
- Remote updated on `origin/main`.

## Documentation Update Rules
- `CLAUDE.md`: update only when workflow/contracts/guardrails change.
- `CHANGES.md`: add entry when behavior or process changes. Owned by Step 2 (Claude Code). Step 3 (Codex) updates only if patches change behavior.
- Pure internal refactors with no behavior/process effect do not require a doc entry.

## Git Policy
- Direct push to `main`.
- Single atomic commit per task when applicable (source + generated artifact + docs in same commit).

## Hard Guardrails
- Do not edit generated artifact manually.
- Do not skip build after source change.
- Do not push without smoke-check + diff review.
- Do not skip pause/resume tokens in browser smoke sessions.
- Every step must output prescriptive text for the next step (no dead-end outputs).
