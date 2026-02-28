# FEATURE CARD

Feature: Column 2 text input UX overhaul + visual polish

Goal:
Improve text editing ergonomics across all Column 2 fields, add canvas text wrapping where appropriate, separate Body/Cards decorator toggles, and apply minor visual/default updates.

In scope:

1. Auto-expanding textareas — all Column 2 text fields
   - Convert every `<input>` in Column 2 (Brand Name, Label, Heading, Card inputs) to auto-expanding `<textarea>` elements.
   - Body textarea already exists but should also auto-expand.
   - Textareas grow line-by-line as content is typed (no internal scrollbar during growth).
   - Cap maximum height at a viewport-relative value (e.g. `max-height: 50vh`) before engaging a scrollbar.
   - Replace the current fixed `rows={2}` on the Body textarea with dynamic sizing.
   - All converted textareas must suppress Enter-key newlines where the field is semantically single-value (Label, Brand Name). Heading, Body, and Card textareas allow newlines.

2. Canvas text wrapping — Heading, Body, Cards only
   - Ensure canvas rendering supports word-wrap for Heading, Body, and Card text.
   - Body likely already wraps — verify and leave as-is if so.
   - Heading and Card renderers must wrap within their respective bounding boxes.
   - Label and Brand Name are explicitly excluded from wrapping; they remain single-line on canvas.

3. Card inputs — multi-line support
   - Each Card input becomes an auto-expanding textarea (same behavior as item 1).
   - Cards support multiple lines of text per card in the editor.
   - Canvas card renderer must handle multi-line/wrapped text within each card.
   - If wrapped card text exceeds the card's vertical bounding box, clip or truncate gracefully — do not overflow into adjacent cards or off-canvas.

4. Separate decorator toggles for Body and Cards
   - **Body mode**: Show existing `—` (hyphen/accent bar) toggle. Controls whether the accent divider bar renders under the Heading on canvas. Independent state per slide. Default: ON.
   - **Cards mode**: Show a new `✓` (checkmark) toggle. Controls whether checkmark icons render on each card on canvas. Independent state per slide. Default: ON.
   - Only the toggle relevant to the active mode (Body or Cards) is visible in the UI.
   - The two toggles are independent — toggling one does not affect the other.
   - Store as separate per-slide state properties (e.g. `showAccentBar`, `showCardChecks`).
   - Initialize both in `makeDefaultSlide()` with default ON.

5. Default accent color update
   - Change the default accent color from `#22c55e` (green) to `#a5b4fc` (soft indigo).
   - Update the `GREEN` constant or equivalent default wherever it seeds the initial accent color for new slides.
   - Existing references to `GREEN` for non-accent purposes (e.g. UI toggle buttons, "Download All" border) must remain green — only change the default slide accent.

6. Column 1 visual separator
   - Add a horizontal line divider above the Screenshot section in Column 1.
   - Match existing separator styling if any exists elsewhere in Column 1; otherwise use a subtle `1px solid #333` or similar low-contrast rule consistent with the dark theme.

Out of scope:
- No changes to PDF export logic.
- No changes to background controls, canvas background rendering, or drag-to-reorder behavior.
- No new dependencies.
- No build script/order changes unless a new `src/*` file is required.
- Label and Brand Name canvas rendering remain single-line (no wrapping).

Constraints:
- Follow existing code patterns: functional state updates, per-slide state objects, confirm dialogs for destructive actions, `pushUndo()` before mutations.
- Auto-expand textarea implementation should be lightweight (resize on input via scrollHeight measurement, no third-party library).
- New per-slide state properties (`showAccentBar`, `showCardChecks`) must be initialized in `makeDefaultSlide()` and handled in preset save/load so they round-trip correctly. Treat as optional on load with default ON fallback so older presets without these fields still load cleanly.
- Canvas wrapping for Heading and Cards must respect existing font size controls and layout math (margin, available width).
- Accent bar Y-position must be recalculated dynamically based on wrapped heading height, not a fixed single-line offset.

Risks:
- **Heading wrap + accent bar layout**: The accent bar currently draws at a fixed offset below the heading. Multi-line heading wrapping changes that height, so bar placement must become dynamic. If missed, the bar will overlap body text or float too high.
- **Card vertical overflow**: Multi-line card text could exceed the card's bounding box. Without explicit clip/truncate logic, text could bleed into adjacent cards or off-canvas.
- **Preset backward compatibility**: New per-slide state fields (`showAccentBar`, `showCardChecks`) will be absent in presets saved before this change. Load logic must default these to ON if missing, not `undefined`/falsy.
- **Textarea scroll behavior**: Auto-expand via `scrollHeight` can behave inconsistently if `box-sizing`, `padding`, or `border` aren't accounted for. Implementation should reset `height` to `auto` before reading `scrollHeight` to avoid ratcheting.

Acceptance:
- All Column 2 text fields auto-expand as text is typed, up to ~50vh, then scrollbar engages.
- Label and Brand Name textareas suppress Enter key (no newlines).
- Heading, Body, and Card text wraps correctly on canvas preview.
- Each Card input supports multiple lines in the editor and renders wrapped text on canvas.
- Card text that exceeds vertical bounds is clipped, not overflowed.
- Body mode shows only the `—` accent bar toggle; Cards mode shows only the `✓` checkbox toggle.
- Toggling one decorator does not affect the other; both default to ON for new slides.
- Accent bar position adjusts dynamically when heading wraps to multiple lines.
- Default accent color for new slides/sessions is `#a5b4fc`.
- UI elements (toggles, buttons) that were previously green remain green.
- A horizontal separator appears above the Screenshot section in Column 1.
- Loading a preset saved before this feature still works (new fields default to ON).
- `Ctrl+Z` undo behavior is unaffected for all existing and new interactions.
- `node build.js` succeeds with no regressions in existing behavior.