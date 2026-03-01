# Automated UI Testing Plan (Playwright + Existing Workflow)

## 1. Objective
Introduce reliable, terminal-driven UI automation with Playwright without breaking the current 4-step workflow contract in `CLAUDE.md`.

Primary outcome:
- Add a stable automated regression gate.
- Keep browser smoke in place until parity is proven.
- Replace manual-only gating only after explicit exit criteria are met.

## 2. Current Workflow Truth (Must Stay Accurate During Migration)
- `src/` is editable source.
- `linkedin-carousel.jsx` is the generated artifact.
- `build.js` is the deterministic artifact build path and remains canonical.
- `SMOKE_TEST.md` is a per-feature handoff card, rewritten each session.
- Current push gate is browser smoke `RESULT: PASS` in Step 4.

This plan does not replace `build.js`, and it does not immediately remove Step 4 browser smoke.

## 3. Guiding Principles
1. Keep workflow contracts stable while adding automation.
2. Separate stable automated regression specs from session-specific smoke cards.
3. Prefer resilient selectors (test ids and roles), not DOM position selectors.
4. Roll out in phases with measurable exit criteria.
5. Keep rollback simple: manual smoke remains available until full confidence.

## 4. Target State

### Short-term (Hybrid Gate)
- Playwright suite runs in terminal for core flows.
- Browser Step 4 still runs for scenarios not yet automated or extension-specific behavior.
- Both signals are used for release confidence.

### Long-term (Automation-first Gate)
- Playwright becomes the primary required UI gate.
- Browser smoke becomes selective fallback or release-candidate verification.

## 5. Implementation Plan

### Phase 1: Test Infrastructure Bootstrap
1. Create `package.json` (tooling only; no change to `build.js` contract).
2. Install `@playwright/test` as a dev dependency.
3. Add Playwright config and scripts:
   - `test:ui` (full suite)
   - `test:ui:quick` (fast gate subset)
   - `test:ui:headed` (debug)
4. Add `.gitignore` entries for test artifacts:
   - `node_modules/`
   - `playwright-report/`
   - `test-results/`
   - `.playwright/` (if used)

Deliverables:
- `package.json`
- `playwright.config.*`
- updated `.gitignore`

### Phase 2: Deterministic Test Harness (No Workflow Breakage)
1. Add a local app harness for Playwright execution (served locally).
2. Keep harness purpose narrow: deterministic UI test runtime only.
3. Use Playwright `webServer` so tests run with one command.
4. Keep the existing artifact workflow untouched (`node build.js` still required when source changes).

Deliverables:
- `tests/` harness files
- `webServer` config in Playwright

### Phase 3: Stable Regression Spec Source
1. Introduce a stable automated test matrix document (new file), separate from `SMOKE_TEST.md`.
2. Map each automated test to a matrix row and owner area.
3. Keep `SMOKE_TEST.md` as session handoff only.

Suggested file:
- `UI_AUTOMATION_MATRIX.md`

Deliverables:
- stable regression matrix
- mapping from matrix rows to Playwright specs

### Phase 4: Baseline Coverage (Highest Risk First)
Automate core flows first:
1. App boot and critical control visibility.
2. Slide operations: add/edit/duplicate/delete/reorder.
3. Presets: save, load valid, load invalid.
4. Undo/redo shortcuts and typing focus guard.
5. PDF exports (download trigger/assertion).
6. Upload/paste flows that are automatable in Playwright.

Coverage notes:
- Use `data-testid` and accessible labels for stable locators.
- Avoid nth-child and layout-position selectors.
- Keep assertions behavior-focused, not style-fragile unless layout is the feature.

Deliverables:
- initial `tests/*.spec.*`
- locator hardening in UI where needed

### Phase 5: Workflow Integration (Hybrid)
Update workflow docs/contracts to add automation without breaking current gates:
1. `CLAUDE.md`
   - Add terminal automated test step in Step 2/Step 3 validation summaries.
   - Keep Step 4 browser smoke gate active.
2. Agent specs
   - `agents/claude-feature-implementer.md`: require reporting `test:ui:quick` result when applicable.
   - `agents/codex-commit-review-patcher.md`: same requirement after patches.
   - `agents/browser-smoke-tester.md`: unchanged role while hybrid period is active.
3. Gate language during hybrid period:
   - Required: Playwright quick gate pass (or explicit not-applicable reason).
   - Required: browser smoke `RESULT: PASS` until parity exit criteria are met.

Deliverables:
- updated `CLAUDE.md`
- updated agent docs
- updated handoff output contract language

### Phase 6: Exit Manual-First Gate (Only After Criteria)
Switch to automation-first only when all are true:
1. Scenario parity: all critical matrix scenarios automated.
2. Stability: agreed green-run threshold across recent cycles.
3. Flake rate below agreed threshold.
4. Team signoff recorded in docs.

Then update:
- Step 4 requirement from mandatory to conditional fallback.
- push gate language to automation-first.

## 6. Best Practice Guardrails
- Do not use `SMOKE_TEST.md` as the long-term automated spec source.
- Do not replace `build.js` with test tooling.
- Do not gate pushes on fragile selectors.
- Keep quick suite fast enough for frequent local execution.
- Always preserve a manual fallback path while maturing automation.

## 7. Risks and Mitigations
- Risk: Workflow churn while multiple agents operate.
  - Mitigation: land Phase 1-2 first; defer gate semantics until Phase 5.
- Risk: Flaky tests from unstable selectors.
  - Mitigation: add explicit test ids/roles before scaling suite size.
- Risk: False confidence from partial coverage.
  - Mitigation: maintain hybrid gate until Phase 6 criteria are met.

## 8. Definition of Done for This Plan
This plan is complete when:
1. Playwright runs from terminal with one command.
2. Stable automation matrix exists separate from `SMOKE_TEST.md`.
3. Core high-risk scenarios are automated and green.
4. Workflow docs clearly define hybrid gate behavior.
5. Exit criteria for reducing manual smoke are explicit and documented.

## 9. Immediate Next Steps
1. Approve this phased migration model.
2. Implement Phase 1 in a dedicated change set.
3. Implement Phase 2 harness.
4. Draft `UI_AUTOMATION_MATRIX.md`.
5. Start Phase 4 baseline tests with resilient locator strategy.
