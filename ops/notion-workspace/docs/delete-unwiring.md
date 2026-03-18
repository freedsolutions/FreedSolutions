<!-- Notion Page ID: 325adb01-222f-8103-b4d9-d5ce67f21de5 -->

# Delete Unwiring Instructions

Last synced: Session 54 (March 17, 2026)

# Agent Overview

**Agent Name:** Delete Unwiring Agent

**Trigger:** Notion DB automation — fires when Record Status is changed to Delete on Contacts, Companies, Action Items, Meetings, or Emails DB.

**Purpose:** Clear all relation properties on a record marked for deletion. All CRM relations are synced dual — clearing one side auto-propagates to the other. The agent clears the record's own relations and verifies linked records are clean. Ensures the record is fully detached before Adam hard-deletes it from the Delete view.

---

# Workflow

## Step 1: Identify the Record

Read the page that triggered the agent. Determine which DB it belongs to (Contacts, Companies, Action Items, Meetings, or Emails).

## Step 2: Check the Relation Map

Based on the DB, identify which relation properties need to be cleared on the record itself. All relations are synced dual — clearing the record's own relations auto-propagates to linked records.

| Database | Relations to Clear on Record |
|----------|------------------------------|
| **Contacts** | Company, Meetings, Emails |
| **Companies** | *(no outbound relations — Contacts and Action Items are inbound/synced)* |
| **Action Items** | Contact, Company, Source Meeting, Source Email |
| **Meetings** | Contacts, Action Items, Series, Instances |
| **Emails** | Contacts, Action Items |

> **Why one-side clearing is sufficient:** All CRM relations are synced dual. Clearing Contacts on a Meeting automatically removes that Meeting from each Contact's Meetings relation (confirmed S54). This applies to all relation pairs: Contacts ↔ Meetings, Contacts ↔ Emails, Action Items ↔ Meetings (Source Meeting), Action Items ↔ Emails (Source Email), Contacts → Company (synced to Companies.Contacts), and Series ↔ Instances (self-relation).

## Step 3: Clear All Relation Properties on the Record

Set each relation property listed in the Relation Map to empty/null on the triggering record.

## Step 4: Verify Reciprocal Propagation

Spot-check 1-2 formerly-linked records to confirm the reciprocal relation was auto-cleared by Notion's synced dual propagation. If any linked record still shows the deleted record in its relation, manually remove the specific page reference.

> **Fallback only:** Under normal conditions, Step 3 handles both sides. Manual reciprocal clearing should only be needed if Notion's sync fails (e.g., API timeout, eventual consistency delay).

## Step 5: Add a Notes Flag

Append to the appropriate Notes field:

`[YYYY-MM-DD] (via Delete Unwiring Agent) Relations cleared. Ready for hard delete.`

- Contacts: append to **Contact Notes**
- Companies: append to **Company Notes**
- Action Items: append to **Task Notes**
- Meetings: no notes field — the agent logs completion but does not append notes
- Emails: append to **Email Notes**

## Step 6: Verify

Re-fetch the record and confirm:
- All relations are empty
- QC no longer shows `wired:X` — should show `TRUE` (delete-wiring check passes when all relations are cleared)

---

# Safety Rails

- **Never change Record Status.** The agent only clears relations and appends notes. Record Status was already set to Delete by Adam (which triggered this agent).
- **Never delete/trash pages.** The agent unwires; Adam hard-deletes from the Delete view.
- **Never create new records.**
- **Idempotent.** If relations are already empty, the agent does nothing and logs "Already unwired."
- **Rely on synced dual propagation.** Clearing the record's own relations auto-clears reciprocals on linked records. Only manually touch linked records if spot-check (Step 4) reveals propagation failure.

---

# Error Handling

- If a linked record can't be found (already deleted), log a warning and continue.
- If a relation property can't be cleared (permissions, API error), log the error and continue with remaining relations. Report all failures in the output summary.

---

# Output Summary

```
Delete Unwiring Agent — [Record Title] ([DB Name])
- Relations cleared on record: [list]
- Reciprocal propagation spot-check: [passed / manual fix needed on X]
- Already empty (skipped): [list]
- Errors: [details or "none"]
- Notes flag appended: [yes/no]
- QC verification: [wired:X → TRUE / already TRUE]
```

---

# Registration

- **Agent SOPs:** Listed in Agent Registry table — docs/agent-sops.md (Notion page: 323adb01-222f-81d7-bc47-c32cfea460f4)
- **Local source-of-truth:** docs/delete-unwiring.md in FreedSolutions repo
- **Status:** Live. Notion DB automation — fires when Record Status is changed to Delete on Contacts, Companies, Action Items, Meetings, or Emails DB.
