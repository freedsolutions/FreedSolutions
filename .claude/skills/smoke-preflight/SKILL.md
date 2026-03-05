---
name: smoke-preflight
description: Validate that all prerequisites for smoke testing are met — localhost server, build freshness, git state, Playwright MCP, and FEATURE_CARD.md presence.
---

# Smoke Pre-flight Validation

Run all prerequisite checks before smoke testing. Report pass/fail for each check.

## Checks (run all, report all)

### 1. Server reachable
Run `curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/preview.html` and verify it returns 200.
- FAIL action: Tell the user to start the server with `npx serve . --listen 5173`

### 2. Built artifact exists and is fresh
Check that `linkedin-carousel.jsx` exists. Then compare its modification time against all source files in build.js ORDER using `node -e` to read ORDER and stat each file.
- FAIL if artifact is missing or older than any source file
- FAIL action: Tell the user to run `node build.js`

### 3. Git working tree state
Run `git status --porcelain`. Report whether the tree is clean or has uncommitted changes. This is informational (not a blocker) — just report the state clearly.

### 4. FEATURE_CARD.md present
Check that `FEATURE_CARD.md` exists and is non-empty.
- FAIL action: Warn that smoke tests won't have feature scope context (not a hard blocker).

### 5. Playwright MCP responsive
Attempt to list browser tabs with `browser_tabs` action `list`. If it responds (even with an error about no browser), Playwright MCP is available.
- FAIL action: Tell the user to check MCP server configuration.

## Output format

```
SMOKE PREFLIGHT
───────────────
[PASS] Server: localhost:5173 responding (HTTP 200)
[PASS] Build: linkedin-carousel.jsx newer than all source files
[INFO] Git: 2 uncommitted changes (M src/App.jsx, ? src/newfile.js)
[WARN] Feature card: FEATURE_CARD.md not found
[PASS] Playwright: MCP responsive

Result: READY
```

Status levels:
- **PASS** — check passed
- **FAIL** — hard blocker, must fix before testing
- **WARN** — non-blocking issue, proceed with caution
- **INFO** — informational only

If any check is FAIL, set result to **BLOCKED**. Otherwise set result to **READY**.
