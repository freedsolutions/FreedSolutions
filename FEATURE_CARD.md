# Feature: Add "Reset All" button + move BG Reset to header row

## What
1. **Move the existing Background "Reset" button** up so it sits on the same row as the "BACKGROUND" header label (currently it's in the `[Sync All] [Reset]` row below the header).
2. **Add a new "Reset All" button** in the spot the old Reset occupied — the row becomes `[Sync All] [Reset All]`.
3. **"Reset All" resets background/styling settings across ALL slides** to defaults (same fields as the current per-slide `resetBgToDefault`), but does NOT touch slide content (text, headings, etc.).

## Behavior
- "Reset" (now on the header row): unchanged behavior — resets the **active slide's** background, profile, and screenshot to defaults.
- "Reset All" (new, in the Sync All row): resets **every slide's** background, profile, and screenshot to defaults. Same confirmation dialog pattern. Does not touch text/content.

## Layout change
Before:
```
BACKGROUND
[Sync All] [Reset]
```

After:
```
BACKGROUND                [Reset]
[Sync All] [Reset All]
```

## Constraints
- Reuse existing `resetBgToDefault` logic, extended to loop all slides.
- Same confirmation dialog UX for Reset All.
- No content/text fields are touched by Reset All.
