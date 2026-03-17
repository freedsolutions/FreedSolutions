<!-- Notion Page ID: 325adb01-222f-8103-b4d9-d5ce67f21de5 -->

# Delete Unwiring Instructions

Last synced: Session 52 (March 17, 2026)

# Agent Overview

**Agent Name:** Delete Unwiring Agent

**Trigger:** Notion DB automation — fires when Record Status is changed to Delete on Contacts, Companies, Action Items, Meetings, or Emails DB.

**Purpose:** Clear all relation properties on a record marked for deletion — both on the record itself and on each formerly-linked record (reciprocal unwiring). Ensures the record is fully detached before Adam hard-deletes it from the Delete view.

---

# Workflow

## Step 1: Identify the Record

Read the page that triggered the agent. Determine which DB it belongs to (Contacts, Companies, Action Items, or Meetings).

## Step 2: Check the Relation Map

Based on the DB, identify which relation properties need to be cleared and which reciprocal relations on linked records must also be unwired:

| Database | Relations to Clear on Record | Linked Records to Update (other side) |
|----------|------------------------------|---------------------------------------|
| **Contacts** | Company, Meetings, Emails | For each linked Meeting: remove this contact from Meeting.Contacts. For each linked Email: remove this contact from Email.Contacts |
| **Companies** | *(Contacts and Action Items are synced/inbound — clearing the outbound side on Contact/Action Item handles it)* | No outbound relations to clear on the Company itself, but verify no orphaned backlinks remain |
| **Action Items** | Contact, Source Meeting, Source Email | For each linked Meeting: remove this action item from Meeting.Action Items. For each linked Email: remove this action item from Email.Action Items |
| **Meetings** | Contacts, Action Items, Series, Instances | For each linked Contact: remove this meeting from Contact.Meetings. For each linked Action Item: remove this meeting from ActionItem.Source Meeting. For Series/Instances self-relations: clear both sides. |
| **Emails** | Contacts, Action Items | For each linked Contact: remove this email from Contact.Emails. For each linked Action Item: remove this action item from ActionItem.Source Email |

## Step 3: Clear All Relation Properties on the Record

Set each relation property listed in the Relation Map to empty/null on the triggering record.

## Step 4: Clear Reciprocal Relations on Linked Records

For each formerly-linked record, remove the specific page reference from the corresponding relation property. Both sides must be explicitly unwired to prevent orphaned links.

**Important:** Only remove the specific page reference — do not clear the entire relation property on the linked record.

## Step 5: Add a Notes Flag

Append to the appropriate Notes field:

`[YYYY-MM-DD] (via Delete Unwiring Agent) Relations cleared. Ready for hard delete.`

- Contacts: append to **Contact Notes**
- Companies: append to **Company Notes**
- Action Items: append to **Task Notes**
- Meetings: no notes field — the agent logs completion but does not append notes

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
- **Non-destructive on linked records.** When clearing reciprocal relations, only remove the specific page reference — do not clear the entire relation property on the linked record.

---

# Error Handling

- If a linked record can't be found (already deleted), log a warning and continue.
- If a relation property can't be cleared (permissions, API error), log the error and continue with remaining relations. Report all failures in the output summary.

---

# Output Summary

```
Delete Unwiring Agent — [Record Title] ([DB Name])
- Relations cleared on record: [list]
- Reciprocal relations updated: [count]
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
