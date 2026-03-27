# Notion Custom Agent Browser UI Notes

## Right-side settings panel

Top to bottom:

1. Triggers
2. Instructions
3. Tools and access
4. Model
5. Advanced
6. Save button

## Trigger editing

- Property triggers open a modal.
- Re-check the data source, filter rules, and the `Trigger when page content edited` checkbox.
- Close the modal with Escape if you are backing out.

## Tools and access

- Web access: confirm the toggle state and any allowlist fields.
- Notion access: verify every page or DB entry and its permission level.
- Calendar and Mail: verify the connected account plus the exact permission level.

## Save discipline

- Notion does not reliably auto-save these edits.
- Save after each logical change set.
- Batch related drift fixes into one logical change set so one `HARDENED_GATE` can cover the bounded repair slice.
- Confirm the Save button returns to the inactive state before moving on.

## Audit checklist

- Trigger topology matches the local spec.
- Notion page access covers the required pages and no more.
- Calendar and Mail permissions follow least privilege.
- Model is pinned as expected.
- No revoked access entry remains in a required dependency slot.
- If routine support tools start surfacing local approval prompts, treat that as client-baseline drift instead of approving each step ad hoc.
