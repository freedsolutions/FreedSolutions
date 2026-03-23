<!-- Notion Page ID: 325adb01-222f-8103-b4d9-d5ce67f21de5 -->

# Delete Unwiring Instructions

> Live Notion doc. This repo file is the source of truth for the mapped Notion page. Sync local changes to Notion in the same task.

Last synced: March 22, 2026

# Agent Overview

**Agent Name:** Delete Unwiring Agent

**Status:** Retired (March 22, 2026)

**Reason:** Live testing confirmed that Notion's built-in trash automatically clears reciprocal synced-dual relations on linked records. The unwiring step is redundant — trashing a record directly produces the same clean result without agent intervention.

**Test record:** "Deeproots Partner" Contact — trashed with 4 active relations (3 Emails + 1 Company). All reciprocal relations, rollups, and QC formulas on linked records resolved cleanly after trash.

**Previous trigger:** Notion DB automation — fired when Record Status was changed to Delete on Contacts, Companies, Action Items, Meetings, or Emails DB. Property triggers have been removed; only `@mention` remains for manual re-activation if needed.

---

# Current Delete Path

1. Set `Record Status = Delete` on the record (or skip directly to trash).
2. Trash the record from the Delete view or directly.
3. Notion automatically clears all reciprocal synced-dual relations on linked records.
4. Permanent delete from Notion trash is Adam's manual step when ready.

---

# Relation Map (Reference)

This map remains useful for manual recovery or verification if trash behavior ever changes.

| Database | Relations on Record |
|----------|---------------------|
| **Contacts** | Company, Meetings, Emails |
| **Companies** | *(no outbound relations — Contacts and Action Items are inbound/synced)* |
| **Action Items** | Contact, Company, Source Meeting, Source Email |
| **Meetings** | Contacts, Action Items, Series, Instances |
| **Emails** | Contacts, Action Items |

All CRM relations are synced dual. Trashing a record auto-clears its references from linked records' relation properties, rollups, and QC formulas.

---

# Registration

- **Agent SOPs:** Listed in Agent Registry table — docs/agent-sops.md (Notion page: 323adb01-222f-81d7-bc47-c32cfea460f4)
- **Local source-of-truth:** docs/delete-unwiring.md in FreedSolutions repo
- **Status:** Retired. Property triggers removed. `@mention` only.
