# LinkedIn Messages Workflow

Last updated: March 20, 2026

This workflow is **manual-only**. It is the fallback recovery path for LinkedIn DMs when Gmail notification intake is missing, insufficient, or needs manual backfill.

Primary intake for LinkedIn conversations should now arrive through the Post-Email workflow via Gmail notifications labeled `LinkedIn`.

This doc exists for the cases where the notification email does not carry enough identity, thread, or action detail and a signed-in browser review is still needed.

---

# Goal

Each LinkedIn conversation should map to:

- one Email record in the Emails DB with `Source = LinkedIn - DMs`
- one Contact relation, matched safely by LinkedIn URL or high-confidence identity confirmation

---

# Runtime posture

Primary runtime state belongs to the Post-Email workflow:

- `Post-Email Agent Last Run`

This fallback workflow does **not** own a separate scheduled timestamp.

Use it when:

- a `LinkedIn` notification email was too thin to wire safely
- a LinkedIn conversation needs manual recovery or backfill
- Adam explicitly requests a browser-based LinkedIn review

---

# Step 1: Open the target conversation

Using the signed-in browser session, open the specific LinkedIn conversation that needs recovery.

Sources for the target can include:

- a Gmail thread labeled `LinkedIn`
- a CRM Email record that still needs manual recovery
- an explicit LinkedIn thread URL provided by Adam

Then extract:
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

1. Primary LinkedIn intake should flow through Post-Email using Gmail notifications labeled `LinkedIn`.
2. LinkedIn URL is the strongest identity key for LinkedIn-sourced contacts.
3. Same-name matches without company or headline confirmation are ambiguous, not safe wins.
4. Do not create placeholder Companies from LinkedIn alone.
5. This fallback workflow does not own a separate scheduled timestamp.

---

# LinkedIn capability guardrails

These guardrails apply to any workflow or agent that touches LinkedIn data.

## Current capabilities

| Capability | Notes |
|---|---|
| LinkedIn notification email intake | Primary path via Post-Email and the `LinkedIn` Gmail label |
| Manual DM capture via browser session | This fallback workflow |
| LinkedIn-aware web search for enrichment | Contact & Company Agent, evidence source #4 |
| Manual or web-search enrichment fallback | Default path when LinkedIn data is insufficient |

## Not available — do not assume

| Capability | Why |
|---|---|
| Arbitrary contact lookup by email | Requires confirmed LinkedIn partner product access |
| People search by name + company | Requires confirmed LinkedIn partner product access |
| Browser scraping or automation | Out of scope |

## Design rules

1. Do not assume LinkedIn API access you have not confirmed.
2. Treat LinkedIn self-serve developer access as lower-capability by default.
3. If LinkedIn partner access is later approved, add it as a new enrichment source rather than weakening existing guardrails.
