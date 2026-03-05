---
name: smoke-deep
description: Extended smoke test covering color pickers, geo shapes, toggles, size controls, slide CRUD with confirm dialogs, and translucent swatch behavior. Runs after /smoke or /build-test for deeper regression coverage.
argument-hint: "[blank for full deep checklist, or specific area like 'color picker']"
---

# Deep Smoke Test Runner

Extended Playwright MCP smoke test that covers interaction areas beyond the standard 7-step `/smoke` checklist. Use this for deeper regression coverage before commits or after significant changes.

## Usage

```
/smoke-deep                  # Run the full 12-step deep checklist
/smoke-deep color picker     # Test only color picker interactions
/smoke-deep slide crud       # Test only slide CRUD with confirm dialogs
```

## Pre-flight (always first)

Before any browser interaction, verify the server is reachable:
```
curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/preview.html
```
If not 200/301, stop immediately and tell the user to start the server. Do NOT open a browser.

## Deep checklist

Steps 1-7 match the standard `/smoke full` checklist. Steps 8-12 extend coverage.

1. **App loads**: Navigate to preview.html, verify heading "Carousel Generator" appears, no error div
2. **Canvas renders**: Verify canvas has non-zero dimensions with content visible
3. **Slide text editing**: Type in heading and body fields, verify canvas updates
4. **Slide navigation**: Add a slide, click slide 2, verify "SLIDE 2" shown
5. **Add slide**: Verify slide count increased and "All Slides" button enabled
6. **Download button**: Verify "Current Slide" button exists and is clickable
7. **No console errors**: Check `browser_console_messages` level "error" (ignore favicon 404)
8. **Color picker**: Open the Layer color picker (click the swatch button next to "Layer"), click a color swatch, verify hex input updates and canvas re-renders
9. **Geo shape**: While Layer picker is open, click "Bokeh" (or another shape), verify canvas pattern changes, then close the picker
10. **Slide CRUD**: Click "Duplicate" button, handle the custom confirm dialog (click "Confirm"), verify slide count increases. Then click "Remove" on the new slide, confirm removal, verify count returns to original
11. **Toggle control**: Click "Footer & Pic" OFF toggle to turn it ON, verify "Brand Name" text and footer controls appear, verify canvas shows footer
12. **Size control**: Click the heading size "+" button twice, verify the size input value increases (e.g., 48 -> 50)

## Execution protocol

### Navigate and wait
1. `browser_navigate` to `http://localhost:5173/preview.html`
2. Wait for the app heading to appear in the snapshot
3. If the app fails to load, screenshot, close browser, report FAIL

### Interact and verify
1. Use `browser_snapshot` to get the accessibility tree before each interaction
2. Use element refs from snapshots for all clicks and inputs -- never guess selectors
3. Take `browser_take_screenshot` after each meaningful interaction
4. Name screenshots: `deep-01-app-loaded.png`, `deep-02-text.png`, etc.

### Confirm dialog handling
This app uses **custom modal overlays** (not native browser dialogs) for destructive actions (duplicate, remove, reset, sync-to-all). When a confirm dialog appears:
1. It shows in the `browser_snapshot` as a paragraph with the action text and Cancel/Confirm buttons
2. Click the "Confirm" button ref from the snapshot
3. Do NOT use `browser_handle_dialog` -- these are React-rendered modals, not native dialogs

### Opacity slider interaction
To set a slider value programmatically (e.g., opacity), use `browser_evaluate` with the native input value setter:
```js
(el) => {
  const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
  setter.call(el, '40');
  el.dispatchEvent(new Event('input', { bubbles: true }));
  el.dispatchEvent(new Event('change', { bubbles: true }));
}
```

### Console check
After all interactions, run `browser_console_messages` with level "error". The only expected error is `favicon.ico 404` -- flag anything else.

### CRITICAL: Always close the browser
**No matter what happens** -- pass, fail, error, timeout -- you MUST close the browser before reporting results:
```
browser_close
```
This is a hard requirement. Never skip this step.

## Failure handling

If any step fails:
1. Take a screenshot of the current state
2. Check console messages for errors
3. Close the browser (CRITICAL -- do this before reporting)
4. Report which step failed and why, with screenshot path

## Output format

```
DEEP SMOKE TEST
───────────────
Scope: [full deep checklist / specific area]

Standard checks:
[PASS] App loads (deep-01-app-loaded.png)
[PASS] Canvas renders
[PASS] Text editing (deep-02-text.png)
[PASS] Slide navigation
[PASS] Add slide
[PASS] Download button
[PASS] No console errors

Extended checks:
[PASS] Color picker: swatch selected, hex updated (deep-03-color.png)
[PASS] Geo shape: Bokeh pattern visible (deep-04-shape.png)
[PASS] Slide CRUD: duplicate + remove with confirm dialogs (deep-05-crud.png)
[PASS] Toggle: Footer & Pic ON, footer visible (deep-06-toggle.png)
[PASS] Size control: heading 48 -> 50

Result: ALL PASS (12/12)
Screenshots: deep-01 through deep-06
Browser: closed
```

Always end with `Browser: closed` confirmation.
