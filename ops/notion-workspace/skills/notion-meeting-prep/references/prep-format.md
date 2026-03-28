# Meeting Prep Output Format

## Replace Strategy

The prep section occupies a predictable region of the Meeting page body so that re-runs replace rather than duplicate.

1. Scan the page body for an H2 heading block whose text starts with `Meeting Prep` (any trailing date is expected, e.g., `Meeting Prep (2026-03-28)`).
2. If found: delete every block from that heading forward, **stopping just before the next H2-level peer heading** (i.e., a `## ` heading that is not an `### ` subheading within the prep section). H3 headings like `### Jane Smith - Acme Corp` are part of the prep section and must be included in the deletion. If no subsequent H2 heading exists, delete to end of page.
3. Insert the new prep section at the position where the old one was removed.
4. If no existing `Meeting Prep` heading is found: append a divider and the new prep section to the end of the page body.

This keeps any prior content (curated summary, Post-Meeting notes, manual notes) intact both above and below the prep block. A `## Curated Notes` or other H2 section that follows the prep block will never be consumed by the replace.

## Output Template

```
---
## Meeting Prep (YYYY-MM-DD)
[N] open Action Items | [N] recent emails | [N] attendees

### [Contact Name] - [Company Name]
**Open Action Items ([count])**
- [Task Name] - [Status] | [Type] | [Company Name]
- ...

**Recent Emails ([count])**
- [Email Subject] - [Date] - [1-line from Email Notes]
- ...

### [Contact Name] - [Company Name]
...

### [Company Name] - General
**Open Action Items ([count])**
- [Task Name] - [Status] | [Type] | [Company Name]
- ...
```

## Field Mapping

| Output element | Source field | Notes |
| --- | --- | --- |
| Contact Name | Contacts.Contact Name (title) | |
| Company Name | Companies.Company Name (title) via Contact.Company | |
| Task Name | Action Items.Task Name (title) | |
| Status | Action Items.Status (select) | Show raw value. All non-Done statuses appear. |
| Type | Action Items.Type (formula) | Show computed value as-is. |
| Company (on AI bullet) | Action Items.Company -> Company Name | May differ from the Contact's company for cross-company items. |
| Email Subject | Emails.Email Subject (title) | |
| Date (on email bullet) | Emails.Date | Format as YYYY-MM-DD. |
| 1-line summary | Emails.Email Notes | First sentence or first ~80 chars. |

## Grouping Rules

1. **Contact-grouped items first.** One H3 per Contact, formatted as `[Contact Name] - [Company Name]`. If a Contact has no Company, use `[Contact Name] - (no company)`.
2. **Company-general group last.** Action Items linked to an attendee's Company but not linked to any attendee Contact appear under `[Company Name] - General` at the end. One H3 per such Company.
3. **Within each group:** Action Items sorted by Status (Blocked first, then In Progress, then Not Started), then alphabetically by Task Name. Emails sorted by Date descending (most recent first).
4. **Empty groups are explicit.** If a Contact has zero open Action Items, show `No open action items.` under the Action Items sub-heading. If zero recent emails, show `No recent emails (last 14 days).` Do not omit the Contact.
5. **Exclude Adam from attendee groups.** Adam is always a participant -- his own open AIs and emails are his existing context, not meeting prep. During attendee expansion, skip his Contact record. Identify Adam by Notion User ID `30cd872b-594c-81b7-99dc-0002af0f255a` or known emails `adam@freedsolutions.com`, `adamjfreed@gmail.com`, `adam@primitivgroup.com`. His Company (Freed Solutions) still participates in Company-level AI matching if other attendees share that Company, but Adam himself does not get a Contact group.

## Fallback Formatting

- **Email Notes empty:** format the email bullet as `[Subject] - [Date] - (no summary)` so Adam knows the note is missing, not that the email was empty.
- **Action Item Type empty:** omit the Type segment from the bullet rather than showing a blank.
- **Zero attendees on the Meeting:** write the prep section with a note: `No contacts linked to this meeting. Add attendees to the Contacts relation and re-run.`
