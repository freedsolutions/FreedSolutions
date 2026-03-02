# FEATURE CARD

## What
Fix the Screenshot upload frame in the left pane so the scale slider fits within a fixed frame height, preventing layout jumps when toggling features or uploading images.

## Why
Currently the Profile and Screenshot frames sit side-by-side with `flex: 1`. When a screenshot is uploaded, a scale slider appears (lines 371-377 in App.jsx), growing the Screenshot frame's height. This pushes down everything below (Duplicate Slide button, slide list) and can visually squeeze the Profile frame. The UI "jumps" whenever the slider appears/disappears, which feels janky.

## Scope

### Uniform fixed-height upload frames (Background, Profile, Screenshot)
- All three upload frames (Background Tile, Profile, Screenshot) must share the same fixed height
- The height should account for the tallest possible state (upload button + filename + slider in the Screenshot frame)
- The slider, filename, and upload button should all fit within this reserved height — no conditional height growth
- All three frames should always be the same height regardless of their individual content state (empty, uploaded, uploaded+slider)
- Currently the Background tile sits in a separate row above Profile + Screenshot — the height must still match across both rows visually

### Layout stability
- The elements below the Profile/Screenshot row (divider, Duplicate Slide button, slide list) must not shift vertically when:
  - A screenshot is uploaded (slider appears)
  - A screenshot is removed (slider disappears)
  - A profile image is uploaded/removed
  - A background image is uploaded/removed
- Use `minHeight` or fixed `height` on each frame to reserve space
- The Background Tile frame must also remain stable and match the same height

### No functional changes
- The slider still appears only when a screenshot image is present
- Slider range (50–200%) and behavior unchanged
- Upload, remove, and filename display behavior unchanged

## Out of Scope
- No changes to the right pane (Preview + Download + Canvas)
- No changes to canvas rendering or slide data model
- No changes to the center pane (Slide Editor)
- No new features — purely a layout stability fix

## Risks
- Choosing a fixed height that's too small could clip content; too large wastes space — needs visual verification
- The reserved space when no screenshot is uploaded will show empty area in the Screenshot frame, which is acceptable for layout stability
