# FEATURE CARD

## What
Relocate the Background section (currently at the top of the center pane) into the left-hand pane and reorganize the left pane layout so it contains all global controls at the top and slides at the bottom.

## Why
The center pane's top area is cluttered with background/profile/screenshot controls that aren't per-slide editing. Moving them to the left pane groups all global/background controls together, frees the center pane to start directly with the Slide Editor, and gives the slide editor more vertical space.

## Scope

### Left pane restructure (widen from 136px to ~220px)
New top-to-bottom order:
1. **PRESETS** label + Save | Load buttons (existing, stays)
2. Horizontal divider
3. **BACKGROUND** label
4. **Sync All | Reset** buttons (moved from center pane)
5. **Accent** color picker + **Upload** button (side by side on same row)
6. **Base** color picker
7. **Layer** toggle + color picker
8. **Frame** toggle + color picker + opacity
9. **Profile** section | **Screenshot** section (side by side, moved from center pane)
10. Horizontal divider
11. **Duplicate Slide** button — single row of text (shorten from two-line "Duplicate\nSlide" to one-line "Duplicate Slide"), narrower width
12. **Slides** label + slide thumbnails
13. Numbered slide buttons (1, 2, ...) + Add (+) button
14. Space for additional slides with vertical scroll

### Center pane restructure
- Remove the frozen top section (Background + Profile + Screenshot boxes + divider)
- The Slide Editor ("SLIDE 1" panel) moves up to be the first/top element
- No other changes to the slide editor content

### Specific adjustments
- Left pane `flex-basis` increases from 136px to ~220px
- "Duplicate Slide" button: single line of text, not two-line "Duplicate\nSlide"
- Slide list area remains scrollable
- All existing functionality preserved — just relocated

## Out of Scope
- No changes to the right pane (Preview + Download + Canvas)
- No changes to slide editor fields (heading, body, cards, corners, footer)
- No new features — purely a layout reorganization
- No changes to canvas rendering or data model

## Risks
- The wider left pane reduces horizontal space for the center and right panes — may need to verify canvas preview doesn't get too squeezed
- Background color pickers need to fit in the narrower left pane width vs the old horizontal center-pane layout — may need to stack vertically
- Profile and Screenshot upload boxes side-by-side in ~220px might be tight — may need compact styling
