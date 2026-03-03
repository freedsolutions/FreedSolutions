# Feature: Left Pane Layout Improvements

## Scope
1. **Slide grid: 5 → 2 columns** — Increase left pane preview slide thumbnails to fit 2 per row (within the existing 220px pane width).
2. **Larger delete badge** — Increase the × remove badge from 16px to 20px, with proportional font-size and offset adjustments.
3. **Larger Duplicate button** — Match the Duplicate button size to the standard `panelBtn()` size used by Save, Load, Sync All, Reset All.
4. **Move Sync All / Reset All into Slides frame** — Remove the standalone GLOBAL ACTIONS section and its surrounding dividers. Place the two buttons side-by-side inside the slides frame container, above the "SLIDES" header.
5. **Triple divider spacing** — Triple the margins on `dividerStyle()` (8px → 24px). Add matching spacing between PRESETS and the Slides frame.

## Out of scope
- Changing left pane width
- Changing slide thumbnail height
- Any canvas/rendering changes
