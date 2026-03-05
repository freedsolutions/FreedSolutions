# Feature: Add "Dots" Geometric Background Pattern

## Summary
Add a new "Dots" pattern to the geometric background shape picker. Renders filled circles in the geo color layer, sized large enough to be clearly visible.

## Scope

### Add
- New `GEO_SHAPES` entry: `{ id: "dots", label: "Dots" }`
- New `drawGeoDots(ctx, baseColor, lineColor, geoOpacity)` function in `canvas/backgrounds.js`
- Wire into `drawGeoBg` switch/dispatch
- New thumbnail case in `drawShapeThumbnail` in `ColorPickerInline.jsx`

### Do not change
- Existing patterns (lines, bokeh, waves, stripes, hex)
- Any UI layout, controls, or state management
- Any rendering logic outside the new pattern

## Design Constraints
- Dots must be filled circles (not stroked outlines)
- Use the geo color layer (`lineColor` with `geoOpacity`) for fill
- Dots should be clearly visible — minimum ~18-24px radius range
- Scattered/grid placement similar to how other patterns tile the canvas
- Background base color rendered first (same as other patterns)

## Files Touched
1. `src/constants.js` — add entry to `GEO_SHAPES` array
2. `src/canvas/backgrounds.js` — add `drawGeoDots` function + wire into `drawGeoBg`
3. `src/ColorPickerInline.jsx` — add dots case to `drawShapeThumbnail`
4. `src/globals.d.ts` — no new exported symbols needed (internal function)

## LSP Demo Notes
This feature is intentionally chosen to demonstrate LSP-assisted workflow. During implementation, Claude Code will:
- Use `workspaceSymbol` to locate cross-file symbols instead of grep
- Narrate LSP usage inline as it works
- Summarize LSP value at the end
