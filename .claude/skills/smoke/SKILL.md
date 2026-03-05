---
name: smoke
description: Run a Playwright MCP smoke test against preview.html at localhost:5173. Navigates, interacts, screenshots, and reports pass/fail. Always closes the browser cleanly.
argument-hint: "[what to test, 'full' for checklist, or blank for FEATURE_CARD.md]"
---

# Smoke Test Runner

Run a Playwright MCP smoke test against the carousel designer at `http://localhost:5173/preview.html`.

## Usage

```
/smoke                          # Test against FEATURE_CARD.md scope
/smoke canvas renders correctly  # Test specific behavior
/smoke full                     # Run the full standard checklist
```

## Pre-flight (always first)

Before any browser interaction, verify the server is reachable:
```
curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/preview.html
```
If not 200, stop immediately and tell the user to start the server. Do NOT open a browser.

## Test scope

Determine what to test based on the argument:

1. **No argument**: Read `FEATURE_CARD.md` and test the features described in its Scope section. If FEATURE_CARD.md is missing, fall back to the standard checklist.
2. **Specific description** (e.g., "color picker opens"): Test exactly what was described.
3. **`full`**: Run the full standard checklist below.

## Standard checklist (used for `full` or as fallback)

1. **App loads**: Navigate to preview.html, wait for the app heading to appear, verify no error div is shown
2. **Canvas renders**: Verify the canvas element exists and has non-zero dimensions
3. **Slide text editing**: Find a text input (heading or body), type test text, verify canvas updates (take before/after screenshots)
4. **Slide navigation**: If multiple slides exist, click slide 2 in the slide selector, verify active slide changes
5. **Add slide**: Click the add slide button, verify slide count increases
6. **Download button**: Verify a download button exists and is clickable
7. **No console errors**: Check browser console for errors (warnings are acceptable)

## Execution protocol

### Navigate and wait
1. `browser_navigate` to `http://localhost:5173/preview.html`
2. `browser_wait_for` the app heading text (timeout: 10s)
3. If the app fails to load, take a screenshot, close the browser, and report FAIL

### Interact and verify
1. Use `browser_snapshot` to get the accessibility tree before each interaction
2. Use element refs from snapshots for all clicks and inputs — never guess selectors
3. Take a `browser_take_screenshot` after each meaningful interaction
4. Name screenshots descriptively: `smoke-01-app-loaded.png`, `smoke-02-text-edited.png`, etc.

### Console check
After all interactions, run `browser_console_messages` with level "error". Report any errors found.

### CRITICAL: Always close the browser
**No matter what happens** — pass, fail, error, timeout — you MUST close the browser before reporting results:
```
browser_close
```
This is a hard requirement. Never skip this step. If an interaction fails, close the browser FIRST, then report the failure.

### Archive smoke artifacts
After closing the browser, archive any root images and Playwright logs:
```
node scripts/archive-smoke-artifacts.js
```

## Failure handling

If any step fails:
1. Take a screenshot of the current state
2. Check console messages for errors
3. Close the browser (CRITICAL — do this before reporting)
4. Report which step failed and why
5. Include the screenshot path in the report

## Output format

```
SMOKE TEST
──────────
Scope: [FEATURE_CARD.md / specific description / full checklist]

[PASS] App loads (smoke-01-app-loaded.png)
[PASS] Canvas renders — 800x1000 canvas present
[FAIL] Text editing — heading input not found in snapshot
[PASS] No console errors

Result: FAIL (1 of 4 checks failed)
Screenshots: smoke-01-app-loaded.png, smoke-02-canvas.png
Browser: closed
Artifacts: archived
```

Always end with `Browser: closed` and `Artifacts: archived` confirmation.
