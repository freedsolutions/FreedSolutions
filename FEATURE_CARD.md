# Feature: Upload Button UI Refresh

## Problem
The three Upload buttons (Background, Footer, Screenshot) are nearly invisible against their frame backgrounds — button bg `#111119` vs frame bg `#0f0f1a`. Text is also small (9px) with no icon to signal interactivity.

## Scope
- Update all three Upload buttons with a subtle colored background (`#1e1e36`)
- Increase button height from 24→28px
- Add Unicode `↑` arrow icon before "Upload" text
- Bump text from 9px to 11px
- Tighten icon+text gap; keep wider gap for uploaded state
- Uploaded state (green checkmark + red ×) stays unchanged
- No hover/active effects

## Files
- `src/layoutTokens.js` — SIZE, SURFACE, uploadBtnStyle
- `src/App.jsx` — 3× upload button content spans

## Out of scope
- Hover/active states
- Uploaded-state styling changes
- Any logic or handler changes
