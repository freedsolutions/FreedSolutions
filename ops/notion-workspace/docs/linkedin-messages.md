<!-- Notion Page ID: 328adb01-222f-8134-941a-c78d757869d6 -->

# LinkedIn Messages Workflow

Last synced: Session 59 (March 18, 2026)

# Overview

Manual workflow for capturing LinkedIn DM conversations into the CRM. Uses a browser agent (Chrome MCP) with Adam's signed-in LinkedIn session to read messages, create/reuse Contacts and Companies, and log conversation summaries to the Emails DB with `Source = LinkedIn - DMs`.

This workflow is **manual-only in v1** — Adam triggers it on demand. Its behavior is deterministic and timestamp-driven so it can later be automated without changing CRM rules.

**Three-phase roadmap:**
1. **Goal 1 (this doc): Message capture** — LinkedIn DMs → CRM records + notes
2. **Goal 2: Enrichment via LinkedIn** — upgrade Contact & Company Agent to use authenticated LinkedIn for profile lookups (replaces web search fallback)
3. **Goal 3: Connection invites** — send LinkedIn invites to confirmed CRM matches (Adam-in-the-loop approval)

---

# Prerequisites

- Adam is signed into LinkedIn in Chrome
- Chrome MCP (browser agent) is available
- Notion MCP is available for CRM read/write

---

# State Management

## Runtime Timestamp

- **Agent Config** field: `Last Successful LinkedIn Message Review` (ISO 8601)
- Separate from Post-Meeting / Post-Email timestamps — no shared state
- Updated only after a fully successful run
- If missing or malformed: default to 7 days ago (safety-net maximum)

---

# Step-by-Step Workflow

## Step 1: Read LinkedIn Messages

1. Open LinkedIn messaging via Chrome MCP.
2. Read conversations with activity since `Last Successful LinkedIn Message Review`.
3. For each conversation, extract:
   - **Participant name** (LinkedIn display name)
   - **Participant headline** (current role/company)
   - **Participant profile URL** (linkedin.com/in/...)
   - **Conversation snippet** — most recent messages (enough for a 1–3 sentence summary)
   - **Conversation date** — timestamp of most recent message

## Step 2: Contact Matching & Creation

For each LinkedIn conversation participant (excluding Adam):

### 2.1: Match by LinkedIn URL

1. Query Contacts DB for any record where **LinkedIn** field matches the participant's profile URL.
2. If matched → use this Contact. Proceed to Step 3.

### 2.2: Match by Name + Company (fuzzy)

If no LinkedIn URL match:

1. Search Contacts DB for records where **Contact Name** matches the participant's LinkedIn display name.
2. If a name match is found:
   - If the matched Contact has no LinkedIn URL → set the LinkedIn field to the participant's profile URL.
   - If the matched Contact has a DIFFERENT LinkedIn URL → create a new Draft Contact (possible different person with same name). Add note: `Possible duplicate: name matches [existing contact name] but LinkedIn URLs differ.`
3. If no name match → proceed to 2.3.

### 2.3: Create Draft Contact

If no match by LinkedIn URL or name:

- **Contact Name**: LinkedIn display name
- **Email**: leave blank (LinkedIn doesn't expose emails)
- **LinkedIn**: participant's profile URL
- **Role / Title**: participant's headline (if available)
- **Record Status**: `Draft`
- **Company**: attempt company matching (see 2.4)
- **Contact Notes**: `[YYYY-MM-DD] Created from LinkedIn DM conversation.`

### 2.4: Company Matching (for new Contacts)

1. Extract company name from participant's LinkedIn headline (e.g., "VP Sales at Acme Corp" → "Acme Corp").
2. Search Companies DB by **Company Name** (fuzzy match).
3. If a match is found → wire the Company relation.
4. If no match → leave Company blank. Do NOT create placeholder companies from LinkedIn data alone (no domain available for dedup).

---

## Step 3: Create Email Record (Message Stub)

For each LinkedIn conversation, create a page in the **Emails DB** (`f685a378-5a37-4517-9b0c-d2928be4af4d`):

- **Email Subject**: `LinkedIn DM: [Participant Name]` (or conversation topic if identifiable)
- **Thread ID**: LinkedIn conversation URL or unique conversation identifier (canonical identity for dedup)
- **From**: participant's LinkedIn profile URL (since there's no email address)
- **Date**: timestamp of the most recent message in the conversation
- **Source**: `LinkedIn - DMs`
- **Contacts**: wire to the matched/created Contact
- **Record Status**: `Draft`
- **Email Notes**: 1–3 sentence summary of the conversation

### Dedup Rule

Before creating, check if a record with the same **Thread ID** already exists in the Emails DB. If so, skip — do not overwrite.

---

## Step 4: Update Timestamp

After all conversations are processed successfully:

1. Update `Last Successful LinkedIn Message Review` in Agent Config to the current timestamp.
2. Log a summary: conversations processed, new Contacts created, existing Contacts matched, Email stubs created.

---

# Important Rules

1. **Never create duplicate records** — always dedup by LinkedIn URL (Contacts) and Thread ID (Emails) before creating.
2. **LinkedIn URL is the primary key for LinkedIn-sourced contacts.** Unlike email-sourced contacts (keyed by email), LinkedIn contacts may not have an email address.
3. **Do not create placeholder Companies from LinkedIn alone.** LinkedIn company names are unreliable for matching (no domain for dedup). Only wire to existing Companies with matching names.
4. **Draft everything** — all new records start as Draft. Only Adam promotes to Active.
5. **Append-only notes** — never overwrite existing Contact Notes or Email Notes.
6. **Failed runs do not advance the timestamp** — if the browser agent errors mid-run, the timestamp stays at its previous value so the next run reprocesses.
7. **No backfill on first run** — if the timestamp is missing, default to 7 days ago. Do not attempt to process the entire LinkedIn message history.

---

# Future: Goal 2 — Enrichment via LinkedIn

Upgrade the Contact & Company Agent (Step 2.5 in `contact-company.md`) to use authenticated LinkedIn access via Chrome MCP instead of web search fallback:

- For contacts missing a LinkedIn URL: search LinkedIn by name + company using Adam's signed-in session
- Confirm identity by matching role/title and company
- Set the LinkedIn URL field on confirmed matches
- Extract current role/title if the Contact's Role / Title field is blank

This builds the LinkedIn URL mapping needed for Goal 3.

---

# Future: Goal 3 — Connection Invites

For CRM contacts with a confirmed LinkedIn URL match where Adam is NOT already connected:

1. Present a batch of candidates to Adam for review
2. Adam approves/rejects each candidate
3. For approved candidates, the browser agent sends a LinkedIn connection request
4. Log the invite in Contact Notes: `[YYYY-MM-DD] LinkedIn connection invite sent.`

**High-confidence matching required** — only propose invites for contacts where:
- LinkedIn URL is confirmed (not guessed)
- Contact is Active (not Draft)
- Adam has had at least one meeting or email exchange with the contact

---

# Database References

| Database | Data Source ID | Usage |
| --- | --- | --- |
| Emails | `f685a378-5a37-4517-9b0c-d2928be4af4d` | LinkedIn DM stubs created here (Source = LinkedIn - DMs) |
| Contacts | `fd06740b-ea9f-401f-9083-ebebfb85653c` | Match/create contacts from LinkedIn participants |
| Companies | `796deadb-b5f0-4adc-ac06-28e94c90db0e` | Company matching (name-based, no domain) |
| Agent Config | `322adb01-222f-8114-b1b0-cc8971f1b61a` | Last Successful LinkedIn Message Review timestamp |
