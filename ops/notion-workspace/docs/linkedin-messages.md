<!-- Notion Page ID: 328adb01-222f-8134-941a-c78d757869d6 -->

# LinkedIn Messages Workflow

Last updated: March 20, 2026

This workflow is **manual-only**. It captures LinkedIn DMs into the CRM without guessing identity.

---

# Goal

Each LinkedIn conversation should map to:

- one Email record in the Emails DB with `Source = LinkedIn - DMs`
- one Contact relation, matched safely by LinkedIn URL or high-confidence identity confirmation

---

# Runtime state

Preferred runtime key:

- `Last Successful LinkedIn Message Review`

If the key is missing from Agent Config:

- default to 7 days ago
- log the missing runtime key explicitly
- do not treat the absence as success or as permission to backfill all history

---

# Step 1: Read recent conversations

Using the signed-in browser session:

1. Open LinkedIn Messages.
2. Read conversations with activity since the runtime timestamp.
3. Extract:
   - conversation URL or thread identifier
   - participant display name
   - participant headline
   - participant profile URL
   - latest message text
   - latest conversation timestamp

---

# Step 2: Match or create the Contact safely

## 2.1: Match by LinkedIn URL

This is the primary key. If a Contact already has the same LinkedIn URL, reuse it.

## 2.2: Match by name plus company evidence

If no LinkedIn URL match exists:

1. Search Contacts for the same or normalized contact name.
2. Only treat an existing Contact as the same person when the company or headline evidence also aligns.
3. If the name matches but the company evidence is weak or conflicting, do **not** auto-set the LinkedIn URL. Report ambiguity instead.

## 2.3: Create a Draft Contact

Create a new Draft Contact only when:

- the LinkedIn URL is unique
- no confident existing Contact match exists

Set:

- Contact Name
- Record Status = Draft
- LinkedIn = participant profile URL
- Company only when an existing Company confidently matches the headline
- Contact Notes = `Created by LinkedIn DM capture from [conversation URL]`

Do **not** create placeholder Companies from LinkedIn alone.

---

# Step 3: Create or update the Email record

Thread identity is the conversation URL or stable LinkedIn thread ID.

## 3.1: New thread

Create a Draft Email record with:

| Property | Value |
|---|---|
| Email Subject | `LinkedIn DM - [Participant Name]` |
| Thread ID | conversation identifier |
| From | participant profile URL |
| Date | timestamp of the latest message |
| Contacts | linked Contact |
| Source | `LinkedIn - DMs` |
| Record Status | `Draft` |
| Email Notes | concise current-state summary |

## 3.2: Existing thread

Do **not** skip an existing Thread ID blindly.

If the Email record already exists:

- update `Date` when a newer message is present
- refresh `Email Notes` to reflect the current state
- confirm the Contacts relation still points at the correct Contact

This workflow is incremental. Existing conversation records must stay current.

---

# Hard rules

1. LinkedIn URL is the strongest identity key for LinkedIn-sourced contacts.
2. Same-name matches without company or headline confirmation are ambiguous, not safe wins.
3. Do not create placeholder Companies from LinkedIn alone.
4. Failed runs do not advance the runtime timestamp.
5. Missing runtime state defaults to a 7-day window and an explicit drift note.
