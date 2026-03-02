# Feature: Upload frame spacing + filename overflow fix

## What
Two small UI tweaks to all three upload button frames (Background, Profile, Screenshot):

1. **Add ~3-4px margin** between the stacked elements inside each frame (label, spec text, upload button, filename). Currently 1-2px — too tight.
2. **Prevent filename from widening the frame.** Long filenames should truncate with ellipsis, never push the container wider.

## Constraints
- Keep frames at 88px fixed height — use existing dead space to absorb the extra margin.
- All three frames get the same treatment for consistency.
