# Feature: Left Pane UI Cleanup — Slides + Background

## Slides Section
- Move "Duplicate Slide" button **inside** the Slides frame (the bordered `#10101a` container)
- Place it on the same row as the "SLIDES" header label, right-aligned with standard margin
- Shorten button text to "Duplicate"
- Remove the old standalone Duplicate button container above the Slides frame
- Keep the separator line; Slides frame moves up to normal margin spacing after separator

## Background Section
- Move "Sync All" button to the **right side** of the "BACKGROUND" header row (same line)
- "Sync All" should be visually stacked above "Reset All" (right-aligned in header)
- Remaining buttons become a single row: `[Reset]  [Reset All]`
- Goal: eliminate dead space from the old 2×2 grid with an empty cell

## Out of Scope
- No functional changes to any button behavior
- No changes to color pickers, upload boxes, or other sections
