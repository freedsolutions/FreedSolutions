---
name: build-test
description: Build the artifact with node build.js, then immediately smoke test. Combines build and smoke into one step for the SHIP loop. Stops on build failure.
argument-hint: "[what to test — passed to smoke, or blank for FEATURE_CARD.md scope]"
---

# Build + Smoke Test

Combines `node build.js` and a smoke test into a single command. This is the primary operation during the Phase 3 SHIP loop: edit source, build, verify.

## Usage

```
/build-test                     # Build, then smoke test against FEATURE_CARD.md scope
/build-test color picker works  # Build, then test specific behavior
/build-test full                # Build, then run full smoke checklist
```

## Step 1: Build

Run `node build.js` and capture output.

**If build fails:**
- Report the error output clearly
- Do NOT proceed to smoke testing
- Do NOT open a browser
- Suggest what to fix based on the error

**If build succeeds:**
- Report: "Build OK — linkedin-carousel.jsx regenerated."
- Proceed to Step 2

## Step 2: Pre-flight

Verify the server is reachable:
```
curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/preview.html
```
If not 200, stop and tell the user to start the server. Do NOT open the browser.

## Step 3: Smoke test

Follow the exact `/smoke` skill protocol:

1. **Determine scope** from the argument (or FEATURE_CARD.md, or standard checklist if neither available)
2. **Navigate** to `http://localhost:5173/preview.html`
3. **Wait** for the app heading to appear
4. **Interact** using `browser_snapshot` refs — never guess selectors
5. **Screenshot** each step (`smoke-01-*.png`, `smoke-02-*.png`, etc.)
6. **Console check** for errors
7. **ALWAYS close the browser** — no matter what happens

### Standard checklist (when scope is `full` or fallback)

1. App loads — heading visible, no error div
2. Canvas renders — non-zero dimensions
3. Slide text editing — type in heading/body, verify canvas updates
4. Slide navigation — click slide 2 if available
5. Add slide — click add, verify count increases
6. Download button — verify exists and clickable
7. No console errors

## Output format

```
BUILD + TEST
────────────
Build: PASS — linkedin-carousel.jsx regenerated

Smoke test scope: [FEATURE_CARD.md / description / full checklist]
[PASS] App loads (smoke-01-app-loaded.png)
[PASS] Canvas renders
[PASS] Feature: color picker opens and selects color
[PASS] No console errors

Result: ALL PASS
Screenshots: smoke-01-app-loaded.png, smoke-02-picker.png
Browser: closed
```

On build failure:
```
BUILD + TEST
────────────
Build: FAIL

Error:
  Missing source file: src/newComponent.jsx

Action: Add the file to src/ or remove it from ORDER in build.js
Smoke test: SKIPPED (build failed)
```
