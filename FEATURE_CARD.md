# FEATURE CARD
Use this template to define a feature before sending a `FEATURE:` kickoff prompt.
Keep it short and concrete.

## Template
Feature: <short name>
Goal: <user outcome>
In scope: <what must change>
Out of scope: <what must not change>
Constraints: <limits, non-goals, performance, dependencies, UX constraints>
Acceptance: <2-5 concrete checks>

## Example
Feature: Slide-level subtitle toggle
Goal: Let users show/hide a subtitle line per slide.
In scope: Add per-slide toggle and subtitle input; render subtitle in canvas.
Out of scope: No new export format changes.
Constraints: No new dependencies; preserve existing layout spacing.
Acceptance:
- Subtitle toggle appears in editor.
- Subtitle renders only when enabled.
- Existing slides with no subtitle remain unchanged.
