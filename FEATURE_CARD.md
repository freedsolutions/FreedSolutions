# Feature: Slide Pane UI Tweaks

## 1. Inline text inputs for Footer & Pic, Top Corner, Bottom Corner
Move each section's `<textarea>` up to be inline on the same row as the ON/OFF toggle (between toggle and color/font controls, taking available flex space). Remove the indented sub-row that currently holds the textarea.

**Fallback:** If horizontal space is too tight with all controls on one row, keep the textarea in its current position below the toggle row.

## 2. Textarea height fix
Ensure textareas (especially Heading) don't show a vertical scrollbar when content fits on one line. Verify `rows={1}` + auto-height logic sizes correctly. If #1 collapses the sub-rows for Footer/Corner sections, this may only apply to Heading.

## 3. Merge Frame into Background section
- Remove the standalone FRAME section (label + ON/OFF toggle + conditional picker).
- Add a new "Frame" swatch to the BACKGROUND row, placed to the right of the existing "Layer" swatch with the standard pipe separator and label.
- The Frame swatch replicates the Layer swatch pattern: uses `ColorPickerInline` with `allowTransparent={true}` and a swatch palette. Selecting "transparent" disables the frame; selecting a color enables it with that color.
- The Frame swatch dropdown includes its existing opacity slider (`opacityVal`/`onOpacityChange`).

## 4. Opacity slider on Layer swatch
Add `opacityVal` and `onOpacityChange` props to the Layer `ColorPickerInline` instance. Wire to a new `geoOpacity` slide field (default 1). The opacity slider in the dropdown should look/behave identically to Frame's opacity slider.

## 5. Left pane layout tweaks
- Move the "SLIDES" label to the top of the panel frame (above "Sync All" / "Reset All" buttons).
- Center the "Duplicate" button below the slide grid and rename it to "Duplicate Slide".
- Keep the separate "Duplicate" button in the center pane slide editor header as-is (dual functionality preserved).

## Out of scope
- No changes to canvas rendering logic.
- No changes to the center pane "Duplicate" / "Reset" / "Remove" header buttons.
- No changes to presets, PDF export, or undo/redo.
