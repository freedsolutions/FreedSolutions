---
name: smoke-close
description: Guarantee clean Playwright browser teardown. Closes all tabs and browser. Use after failed tests, before commit gate, or whenever browser state is uncertain.
---

# Browser Teardown

Guarantee that all Playwright MCP browser sessions are fully closed. Safe to call multiple times — closing an already-closed browser is a no-op.

## Procedure

1. Attempt to list open tabs with `browser_tabs` action `list`
   - If this succeeds and shows tabs, there is an open browser
   - If this fails or errors, the browser may already be closed — that is fine

2. If tabs are open, call `browser_close` to shut down the browser

3. Verify closure by attempting `browser_tabs` action `list` again
   - If this errors or returns no tabs, closure is confirmed
   - If tabs still show, call `browser_close` again

4. Archive smoke artifacts:
   ```
   node scripts/archive-smoke-artifacts.js
   ```
   - Moves any root image files, Playwright logs, and test-results to `.playwright-mcp/archive/{timestamp}/`
   - Report the archive result in the output

5. Report result:

```
BROWSER CLEANUP
───────────────
Status: CLOSED (was open with N tab(s))
Artifacts: archived 3 artifact(s) to .playwright-mcp/archive/20260305-001800/
```
or
```
BROWSER CLEANUP
───────────────
Status: ALREADY CLOSED (no active session found)
Artifacts: clean (nothing to archive)
```

## When to use

- After a smoke test that may have failed mid-run
- Before starting a new smoke test cycle
- Before the commit gate (no open Playwright sessions allowed)
- When browser state is uncertain
