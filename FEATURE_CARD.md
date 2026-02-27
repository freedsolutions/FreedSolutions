# FEATURE CARD

Feature: Slide management UX patch

Goal:
Fix preset error persistence and add faster slide management controls with undo-safe behavior.

In scope:
1. Bug fix: Preset error message behavior
- Clear `presetError` on any new Presets action (Save click, Load click).
- Auto-dismiss `presetError` after 5 seconds using `setTimeout` with proper cleanup.
- Add explicit manual dismiss (`x`) for preset errors.
2. Column 1 slide buttons (`SlideSelector`)
- Add a small overlaid `x` remove button on each numbered slide button.
- Hide the `x` when only 1 slide exists.
- Clicking `x` calls `removeSlide(i)` and must not interfere with drag-to-reorder.
3. Column 2 slide editor header
- Add a `Reset` button next to existing `Remove`.
- Clicking `Reset` opens a confirm dialog and resets that one slide to `makeDefaultSlide()` while preserving slide position.
- Reset must also clear `slideAssets[activeSlide]` so screenshot/image state resets with the slide.
4. Undo coverage
- Ensure all three paths are undo-safe with `pushUndo()` before mutation:
  - Column 1 `x` remove (via `removeSlide(i)`)
  - Column 2 `Remove`
  - Column 2 `Reset` (new explicit `pushUndo()` requirement)

Out of scope:
- No changes to PDF export, canvas rendering, preset serialization, or background controls.
- No new dependencies.
- No build script/order changes unless a new `src/*` file is required.

Constraints:
- Follow existing code patterns: functional state updates, confirm dialogs for destructive actions, and `pushUndo()` before mutations.
- Keep Column 1 `x` visually unobtrusive and non-disruptive to drag UX.
- Keep reset semantics strict: replace only active slide with defaults and clear matching slide asset entry.

Acceptance:
- Preset error clears on Save/Load click, supports explicit manual dismiss, and auto-dismisses after 5 seconds.
- Column 1 slide buttons show `x` overlay; click removes slide with undo support.
- Column 2 `Reset` resets slide content to defaults with confirm dialog, clears active slide asset, and supports undo.
- `Ctrl+Z` restores state after Column 1 `x`, Column 2 `Remove`, and Column 2 `Reset`.
- `node build.js` succeeds with no regressions in existing behavior.
