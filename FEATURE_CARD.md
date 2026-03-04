# Feature: Move Accent swatch from Heading to Background section

## Summary
Move the Accent color swatch from the HEADING section to the BACKGROUND section, placing it to the right of the Frame swatch with a " | " separator.

## Scope
1. Remove the Accent swatch (`ColorPickerInline` with `pickerKey="accent"`) and its trailing " | " separator from the HEADING section
2. Add the Accent swatch after the Frame swatch in the BACKGROUND section, preceded by a " | " separator and followed by an "Accent" label
3. Make the Accent swatch always visible (no longer conditional on `showHeading` toggle)
4. Preserve all existing Accent swatch behavior (transparent support, accent bar toggling, etc.)

## Out of scope
- No changes to accent color logic or rendering
- No changes to other swatches or sections
