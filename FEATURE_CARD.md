# Feature: Tweak UI Header Row

## Summary
Even out the top of the three-pane layout by moving the app title into the left column instead of spanning full-width above all panes.

## Changes

1. **Rename** "LinkedIn Carousel Generator" → "Carousel Generator" everywhere:
   - `<h2>` in `App.jsx`
   - `<title>` in `preview.html`

2. **Move the `<h2>`** from its current position (full-width row above the three-column flex container) into the top of the **left column**, above the PRESETS section. This removes the dedicated header row so all three panes start at the same vertical position.

3. **No other changes** — keep SLIDE N inside its card frame, keep PREVIEW label where it is, keep all existing styling/spacing otherwise intact.

## Goal
All three panes (left, center, right) align at the top of the page, evening out the UI.
