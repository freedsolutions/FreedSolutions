# Feature: Break Layer Swatch Out of Base Picker

## Scope
1. **Promote Layer to standalone swatch** — Move the geometric overlay (Layer) color picker out of the Base color picker's dropdown into its own labeled swatch ("Layer") next to Accent and Base in the SlideN pane.
2. **Remove ON/OFF toggle** — The transparent/checkerboard option replaces the toggle. Selecting transparent disables the overlay; selecting any color enables it.
3. **Same dropdown style** — Layer picker uses the same ColorPickerInline dropdown pattern as Accent and Base (7 layer presets + transparent + custom color input).
4. **Dim when custom BG active** — Layer swatch dims (opacity 0.35) and is disabled when a custom background image is in use, matching Base behavior.
5. **Defaults unchanged** — geoEnabled: true, geoLines: "#a0a0af".

## Out of scope
- Changing the layer color presets
- Changing canvas rendering behavior
- Changing the data model
