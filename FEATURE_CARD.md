# FEATURE CARD

Feature: Unified page scroll + Background panel layout fixes

Goal:
Three related UI polish fixes: (1) unify scroll axes so all 3 panes scroll together, (2) eliminate dead space below Background controls by repositioning the Profile/Screenshot cards, and (3) fix the Scale slider overflow in the Screenshot card.

---

## In scope

### 1. Remove sticky from Left pane (Slide Selector)
- In `src/App.jsx` line ~230, remove `position: "sticky"` and `top: 24` from the Left column's style object.
- Keep `alignSelf: "flex-start"` so the pane still aligns to the top of the flex row (doesn't stretch).

### 2. Remove sticky from Right pane (Preview)
- In `src/App.jsx` line ~731, remove `position: "sticky"` and `top: 24` from the Right pane's style object.
- Keep `alignSelf: "flex-start"` so the pane still aligns to the top of the flex row.

### 3. Fix dead space below Background controls
The BACKGROUND section (line ~289) contains a three-zone flex row (line ~301):
- Left zone (line ~304): Solid/Photo pill + Accent/Base/Layer/Frame/Footer controls — tallest child
- Middle zone (line ~373): BG thumbnail preview
- Right zone (line ~423): Profile card + Screenshot card, `flex: "0 0 126px"`, `alignSelf: "flex-start"`

The left zone is the tallest sibling, creating visible dead space below the right zone's cards.

**Fix**: Pull the right zone (Profile + Screenshot) out of the three-zone flex row and position it at the top-right of the BACKGROUND panel container (line ~289). Use `position: absolute; top: 0; right: 0` on the right zone, relative to the BACKGROUND panel which gets `position: relative`. Add `paddingRight` to the panel to reserve space for the absolutely-positioned right zone so it doesn't overlap the header row or flex row content.

### 4. Fix Scale slider overflow in Screenshot card
In the Screenshot card (line ~483-487), the Scale row's range input with `flex: 1` plus the 32px percentage label overflows the 126px-wide container.

**Fix**: Add `minWidth: 0` to the range input (`<input type="range">` at line ~485) and `overflow: "hidden"` to the Scale row's flex container (line ~483). This constrains the flex child to respect the container bounds.

### 5. Rebuild artifact
- Run `node build.js` to regenerate `linkedin-carousel.jsx`.

---

## Out of scope
- No new features, controls, or UI elements.
- No changes to canvas rendering, PDF export, or slide data model.
- No changes to any component other than `src/App.jsx` (and the generated `linkedin-carousel.jsx` via build).
- No independent/inner scrollbars on any pane.

---

## Constraints
- Layout changes confined to `src/App.jsx` — inline style modifications only.
- `node build.js` must succeed and regenerate `linkedin-carousel.jsx` cleanly.
- All existing functionality remains intact.
- Do NOT change any canvas rendering logic, slide state, or feature behavior. Only adjust editor panel layout/styling.

---

## Risks

- **Preview not visible while editing**: With sticky removed, the preview canvas scrolls off-screen when the user scrolls down through Center pane settings. This is the intended trade-off per user preference — unified scroll over sticky preview.
- **Slide selector not visible**: The Left slide selector also scrolls away when the Center content is long. Acceptable per user preference.
- **Absolute positioning edge cases**: Moving the right zone to `position: absolute` means it no longer participates in flex row height calculation. If the Profile+Screenshot stack becomes taller than the left zone's content, it could overflow the BACKGROUND panel. This is unlikely given current card sizes (~200px total vs left zone ~250px+), but should be visually verified.
- **Scale slider fix is minimal**: Adding `minWidth: 0` + `overflow: hidden` is the standard flex overflow fix; low regression risk.

---

## Acceptance

1. All 3 panes scroll together with the page — no pane remains fixed/pinned.
2. No pane has its own independent scrollbar.
3. Left and Right panes still align to the top of the flex row (not stretched full height).
4. Profile and Screenshot cards sit flush with the top of the BACKGROUND section — no dead space below them.
5. Scale slider and percentage label stay within the 126px Screenshot card bounds — no overflow/bleed.
6. All existing controls and features work identically (no functional regressions).
7. `node build.js` succeeds with no errors.
8. Canvas preview renders correctly at the same size/aspect ratio as before.
