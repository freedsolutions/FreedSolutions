# Feature: Base Swatch for All Text Sections

## What
Add a "Base" swatch to every text-content section in the Slide N editor. The Base draws a full-content-width solid-color rectangle behind text on the canvas. Defaults to transparent.

## Sections
- **Body/Cards** — Un-grey existing Base swatch; dynamically switches between `bodyBgColor` (body mode) and `cardBgColor` (cards mode)
- **Heading** — New `headingBgColor` property + Base swatch below Text swatch
- **Top Corner** — New `topCornerBgColor` property + Base swatch below Text swatch
- **Bottom Corner** — New `bottomCornerBgColor` property + Base swatch below Text swatch
- **Footer & Pic** — Already has Base (`footerBg`), no changes

## Shape & Controls
- Full content-width rectangle: `MARGIN` to `W - MARGIN`, no rounded corners
- Solid color + transparent toggle only (no opacity slider)
- All new properties default to `"transparent"`

## Acceptance
- Base swatch visible and functional in all 5 sections
- Transparent toggle works (checkerboard pattern)
- Body mode Base swatch is no longer greyed out
- Cards mode Base still controls `cardBgColor` as before
- syncBgToAll propagates all Base colors
- Presets serialize/deserialize all Base colors
