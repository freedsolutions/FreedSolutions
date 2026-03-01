# FEATURE CARD

Feature: Per-slide profile picture + unified Reset/Sync All for all background settings

Goal:
Make the profile picture customizable per-slide (like all other background settings already are), then extend Reset and Sync All to cover all background-panel settings — including Profile and Screenshot — so the UI behavior is consistent and predictable.

---

## In scope

### 1. Per-slide profile picture

Currently, `profileImg` / `profilePicName` are global state in App.jsx (via `useSlideManagement.js`). Every slide renders the same profile picture in its footer.

**Change**: Move profile picture storage into the per-slide data model so each slide can have its own profile image (or none).

- Add `profileImg` (Image object | null) and `profilePicName` (string | null) to the slide factory defaults in `src/slideFactory.js`.
- Update `handleProfilePicUpload()` and `removeProfilePic()` in `src/useSlideManagement.js` to write to the active slide's fields instead of top-level state.
- Update canvas rendering (`drawCenteredFooter` in `src/canvas/backgrounds.js`) to read `profileImg` from the current slide object rather than a single global prop.
- Update the Background panel UI in `src/App.jsx` to read/write profile state from the active slide.
- Update preset save/load in `src/usePresets.js` to serialize per-slide profile data instead of a single global value.
- Remove the now-unused global `profileImg` / `setProfileImg` / `profilePicName` / `setProfilePicName` state.

### 2. Extend Sync All to include Profile and Screenshot

`syncBgToAll()` in `useSlideManagement.js` currently copies background visual properties from the active slide to all slides but excludes profile and screenshot settings.

**Change**: Sync All copies the active slide's full background-panel state to every other slide, including:
- All existing background fields (solidColor, bgType, customBgImage, etc.)
- Profile fields: `profileImg`, `profilePicName`
- Screenshot fields: `showScreenshot`, `expandScreenshot`
- Screenshot assets: copy the active slide's `slideAssets` entry to all other slide indices

### 3. Extend Reset to include Profile and Screenshot

`resetBgToDefault()` in `useSlideManagement.js` currently resets only background visual properties on the active slide.

**Change**: Reset also clears:
- Profile fields: `profileImg: null`, `profilePicName: null`
- Screenshot fields: `showScreenshot: false`, `expandScreenshot: false`
- Screenshot assets: remove the active slide's `slideAssets` entry

### 4. Rebuild artifact
- Run `node build.js` to regenerate `linkedin-carousel.jsx`.

---

## Out of scope
- No UI layout changes (the Background panel arrangement stays as-is).
- No new UI controls or visual elements.
- No changes to PDF export logic beyond what naturally follows from per-slide profile data.
- No changes to slide duplication logic beyond ensuring duplicated slides copy the profile fields.
- No migration of existing presets — new presets will save per-slide; old presets without per-slide profile will fall back to defaults on load.

---

## Constraints
- Changes confined to `src/slideFactory.js`, `src/useSlideManagement.js`, `src/App.jsx`, `src/canvas/backgrounds.js`, `src/usePresets.js`, and the generated `linkedin-carousel.jsx` via build.
- `node build.js` must succeed and regenerate `linkedin-carousel.jsx` cleanly.
- All existing functionality remains intact — slides that previously showed a global profile picture should still render correctly (per-slide defaults to null/no profile, user re-uploads per slide as desired).
- Confirmation dialogs for Sync All and Reset must reflect expanded scope (e.g., "Apply Slide N's background, profile, and screenshot settings to all slides?").

---

## Risks

- **Profile data duplication**: Storing an `Image` object per slide increases memory usage if the user uploads large images to many slides. Acceptable trade-off for the carousel's typical 2–10 slide count.
- **Preset backward compatibility**: Existing saved presets store profile as a global field. Loading an old preset into the new per-slide model will result in no profile on any slide (defaults to null). This is acceptable — user can re-upload. No migration needed.
- **Sync All blast radius expanded**: Syncing now overwrites profile and screenshot on all slides, which is more destructive than before. The confirmation dialog mitigates this, and the behavior matches user expectation that "Sync All" means *all* background-panel settings.
- **Canvas rendering regression**: Changing `drawCenteredFooter` to read profile from the slide object instead of a single prop requires careful plumbing to ensure the correct slide's profile is passed during rendering. Must verify all render paths (preview, PDF export, individual slide render).

---

## Acceptance

1. Each slide can have its own profile picture (or no profile picture), independent of other slides.
2. Uploading/removing a profile picture in the Background panel affects only the active slide.
3. The canvas preview renders the correct per-slide profile picture in each slide's footer.
4. **Sync All** copies all background-panel settings (colors, image, layers, frame, footer, profile, screenshot) from the active slide to every other slide, with a confirmation dialog that mentions the expanded scope.
5. **Reset** clears all background-panel settings (including profile and screenshot) on the active slide to defaults, with a confirmation dialog that mentions the expanded scope.
6. Slide duplication copies the source slide's profile and screenshot data to the new slide.
7. PDF export renders per-slide profile pictures correctly.
8. `node build.js` succeeds with no errors.
9. No functional regressions in any other feature area.
