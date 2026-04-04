---
name: notion-meeting-prep
description: Surface open Action Items and recent email threads for a Meeting's attendees before a call. Use when the user wants a pre-call context brief showing open work and recent correspondence for every Contact attending the meeting.
---

# Notion Meeting Prep

Read `ops/notion-workspace/CLAUDE.md` first when that file exists in the workspace. It holds the current DB IDs, lifecycle rules, and review gate.

## Workflow

1. Resolve the Meeting from user input.
   - Accept a Notion URL, UUID, title search, or "next meeting" shortcut.
   - "Next meeting" queries the Meetings DB for the single nearest future Date. If multiple meetings share the same nearest Date, use `HARDENED_GATE` to disambiguate.
   - If title search returns multiple plausible matches, use `HARDENED_GATE` to ask the user to disambiguate. Do not choose arbitrarily.
   - Fetch the Meeting record: extract Meeting Title, Date, and Contacts relation.
2. Expand attendee context.
   - For each Contact in the Contacts relation: fetch Contact Name and Company relation.
   - Collect unique Companies from the Contact-to-Company chain.
3. Query open Action Items.
   - Filter: Status != Done, linked to any resolved Contact (via Action Items.Contact) OR any resolved Company (via Action Items.Company).
   - **Tag-based expansion**: If the Meeting Title or Company context suggests a business-unit focus (e.g., "Weekly Marketing Meeting"), also query Action Items where Tags includes the matching tag(s) (e.g., `Marketing`), even if they are not linked to any attendee Contact or Company. Include these under a "[Tag] - Related" group at the end.
   - Deduplicate items that match on both Contact and Company (or Contact/Company and Tag).
   - Group Contact-linked items under their Contact.
   - Group Company-only items (no Contact link to any attendee) under "[Company Name] - General".
   - Group Tag-only items (no Contact or Company link to any attendee) under "[Tag] - Related" at the end.
4. Query recent Emails.
   - Filter: Date within last 14 days, linked to any resolved Contact (via Emails.Contacts).
   - Group by Contact.
5. Write the Meeting Prep section to the Meeting page body.
   - Use the replace strategy defined in `references/prep-format.md`: find an existing `## Meeting Prep` heading, delete from that heading through all content until the next H2-level peer heading (skipping H3 subheadings that belong to the prep section), then write the new section at that position. If no existing prep section, append to the end.
   - Format follows the output template in `references/prep-format.md`.
6. Confirm the write landed by re-reading the Meeting page body.

## Guardrails

- Read-only CRM posture: do not create, edit, or delete any Contacts, Companies, Action Items, or Emails.
- Only write to the target Meeting page body.
- Do not change any Meeting properties (Record Status, Calendar Name, Contacts, etc.).
- "Next meeting" must resolve to exactly one upcoming meeting. If zero results, tell the user no upcoming meetings were found and suggest passing a URL or title instead.
- Do not query Google Calendar. Meeting resolution uses the Meetings DB only.
- This skill does not delegate to sub-agents.

## Gate Protocol

Use the shared gate taxonomy from `ops/notion-workspace/CLAUDE.md` and `ops/notion-workspace/docs/agent-sops.md`.

| Operation | Gate | Notes |
| --- | --- | --- |
| Resolve by URL or UUID, fetch meeting, expand attendees, query Action Items and Emails, write/replace prep section, confirm write | `UNGATED` | Only the target Meeting page body is modified. |
| Ambiguous title disambiguation, multiple "next meeting" candidates sharing the same nearest Date | `HARDENED_GATE` | Ask one compact decision-shaped question and re-ask if the reply is empty or unclear. |
| Any property change, Record Status change, or CRM record mutation (should not happen) | `GOVERNANCE_GATE` | Follow the existing Rules of Engagement. |

## Read Next

- Read [prep-format.md](references/prep-format.md) for the output template, replace logic, grouping rules, and fallback formatting.
