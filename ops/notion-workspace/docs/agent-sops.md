<!-- Notion Page ID: 323adb01-222f-81d7-bc47-c32cfea460f4 -->
# Agent SOPs

The living reference document for Adam's Notion workspace automation system. Used by both Adam and Claude (in any interface — chat, Claude Code terminal, or Claude App) to maintain continuity across sessions.

Last updated: Session 43b (March 16, 2026)

---

# Session Management

## How Sessions Work

Each work session with Claude is numbered sequentially. Sessions may happen in the Claude.ai chat interface, the Claude App, or Claude Code in VSCode terminal. Regardless of interface, the same two Notion pages serve as the handoff mechanism:

**Session — Active** (stable URL, content overwritten each session):

Session — Active

**Session — Archive** (stable URL, content appended each session):

Session — Archive

The Active page always contains the latest session's handoff — what happened last time, current system status, priorities for the current session, schema reference, DB IDs, and the opening prompt.

The Archive page contains the System Evolution Arc (one-liner per session) plus snapshot child pages (one per session). The snapshot IS the detailed session record.

## End-of-Session Protocol

At the end of every session, regardless of interface:

1. Append a one-liner to the **System Evolution Arc** section of the Archive page
2. Duplicate the Active page → move the duplicate as a child page under the Archive page (this snapshot is the detailed session record — no separate entry needed)
3. Overwrite the Active page with the next session's handoff content (new summary, new priorities, updated schema, new opening prompt)

## Starting a New Session

Claude Code reads `CLAUDE.md` from the project root automatically — no prompt pasting needed. For Claude App chat sessions, copy the kickoff prompt from `CLAUDE.md` into the chat.

---

# Agent Registry

All agents are instruction pages under the Automation Hub. Each page contains the full workflow, business rules, safety rails, and database references for that agent.

| Agent | Instruction Page | Trigger | Status |
| --- | --- | --- | --- |
| Post-Meeting Agent | Post-Meeting Agent Instructions | Nightly 10 PM ET + reactive (on Meeting Title update) + manual | Active |
| Meeting Sync | [DEPRECATED] Meeting Sync Instructions | Disabled | Deprecated — replaced by Post-Meeting Agent (S37). Cutover complete (S37b). |
| Post-Meeting Wiring | [DEPRECATED] Post-Meeting Wiring Instructions | Disabled | Deprecated — replaced by Post-Meeting Agent (S37). Cutover complete (S37b). |
| Quick Sync | [DEPRECATED] Quick Sync Instructions | Disabled | Deprecated — replaced by Post-Meeting Agent (S37). Cutover complete (S37b). |
| Contact & Company Review | Contact & Company Review Instructions | Manual (after other syncs) | Active |
| Delete Unwiring Agent | [Delete Unwiring Agent Instructions](https://www.notion.so/325adb01222f8103b4d9d5ce67f21de5) | Manual (automation pending) | Active (manual trigger) |

## Notetaker Profiles

Custom instruction profiles for Notion Calendar's AI notetaker. Each profile is pasted into the notetaker's custom instructions field and optimizes the AI summary for a specific meeting type.

| Profile | Local Doc | Purpose | Status |
| --- | --- | --- | --- |
| CRM-Optimized | `docs/notetaker-crm.md` | Default for business meetings. Structures Action Items for Post-Meeting Agent parsing. Surfaces "Hey Floppy" commands from voice AND typed notes (Layer 1). | Active |
| Strategy / Workshop | — | Longer brainstorm/planning sessions. Heavier on topic summaries. | Planned |
| 1:1 / Check-in | — | Quick syncs. Minimal structure, focus on decisions and follow-ups. | Planned |

**Why notetaker profiles matter:** The Post-Meeting Agent parses the `### Action Items` heading from the AI summary. Custom notetaker instructions ensure the AI produces summaries in the exact format the agent expects — improving parse accuracy, action item quality, and Floppy command surfacing (Layer 1).

**Naming convention:** Each agent has an **instruction page** under the Automation Hub containing its full workflow, business rules, and database references. The instruction page is named "[Agent Name] Instructions". The Notion Custom Agents (configured separately in Agent Config) reference these instruction pages.

**Adding new agents:** When a new agent instruction page is created, add it to this table, update `CLAUDE.md` in the project repo, and update the Notion Agent page.

---

# Workflow Documents

Manual workflows that are not automated agents but document repeatable procedures.

| Workflow | Purpose | URL |
| --- | --- | --- |
| Merge Workflow | Merge placeholder companies or duplicate contacts into canonical records | Untitled |

---

# Database Quick Reference

| Database | Data Source ID | Icon |
| --- | --- | --- |
| Contacts | `fd06740b-ea9f-401f-9083-ebebfb85653c` | 👤 |
| Companies | `796deadb-b5f0-4adc-ac06-28e94c90db0e` | 💼 |
| Action Items | `319adb01-222f-8059-bd33-000b029a2fdd` | ✅ |
| Meetings | `31fadb01-222f-80c0-acf7-000b401a5756` | 📅 |
| Agent Config | `322adb01-222f-8114-b1b0-cc8971f1b61a` | ⚙️ |

**Adam's Notion User ID:** `30cd872b-594c-81b7-99dc-0002af0f255a`

---

# Schema Conventions

## Lifecycle State: Record Status (select)

All 4 source DBs (Contacts, Companies, Action Items, Meetings) use a single `Record Status` select with 4 options:

- **Draft** (gray) — Agent-created, pending Adam's review
- **Active** (green) — Approved and live, operational record
- **Inactive** (yellow) — Soft-deleted (deactivated duplicates, merged placeholders)
- **Delete** (red) — Flagged for Adam to hard-delete from Notion

Migrated from Approved + Active checkboxes in Session 32. Agents set new records to Draft. Only Adam moves records to Active. Agents may set records to Inactive or Delete per merge/dedup workflows.

## Contacts DB Properties

- **Contact Name** (title) — full name of the contact
- **Record Status** (select: Draft/Active/Inactive/Delete)
- **Email** — primary business email (used for calendar matching and dedup)
- **Company** (relation → Companies DB)
- **Display Name** (formula) — if Nickname populated, replaces first name; appends (Pronouns) when present
- **QC** (formula) — Data quality signal with 3 possible states:
  - `wired:PropertyName` — Record Status = Delete but the named relation is still populated (e.g., `wired:Company`). Safe-to-delete check takes priority. First non-empty relation wins.
  - `missing:fieldname` — Record Status ≠ Delete and a required field is empty
  - `TRUE` — all checks pass (or Delete with all relations cleared)
  - Required fields (non-Delete): Contact Name, Record Status, Email, Company, Role/Title
  - Delete wiring check (in order): Company → Meetings
- **Contact Notes** — freeform notes (Agent appends via Floppy; Adam edits)
- **Role / Title** — job title or role (Agent + Manual)
- **Secondary Email** — alternate email (personal, old domain, etc.)
- **Tertiary Email** — third email if needed
- **Nickname** — informal name or alias (used by Display Name formula)
- **Phone** — US phone number, normalized to `(XXX) XXX-XXXX`. Strip dots, extra dashes, malformed parens on write. (Agent + Manual)
- **Pronouns** — pronouns (Agent + Manual; used in Display Name)
- **LinkedIn** — LinkedIn profile URL (Agent + Manual)
- **Meetings** (relation → Meetings DB, synced dual) — all meetings this contact attended
- **Created Timestamp** (created_time) — auto-set on page creation
- All agent dedup rules must check ALL email fields (Email, Secondary Email, Tertiary Email)

## Companies DB Properties

- **Company Name** (title) — official company name
- **Record Status** (select: Draft/Active/Inactive/Delete)
- **Company Type** (select: Tech Stack, Operator, Network, Personal) — Agent + Manual
- **Domains** — primary business domains (comma-separated). Used for agent matching
- **Additional Domains** — merged/subsidiary/alternate domains
- **States** (multi_select) — operating states (Agent + Manual; Tech Stack → "All")
- **Website** — company website URL (Agent + Manual)
- **Contacts** (relation → Contacts DB, synced from Contacts → Company)
- **Action Items** (relation → Action Items DB, synced from Action Items → Company)
- **Engagements** (relation)
- **Tech Stack** (relation)
- **Company Notes** — freeform notes (Agent appends via Floppy; Adam edits)
- **QC** (formula) — Data quality signal with 3 possible states:
  - `wired:PropertyName` — Record Status = Delete but the named relation is still populated (e.g., `wired:Contacts`). Safe-to-delete check takes priority. First non-empty relation wins.
  - `missing:fieldname` — Record Status ≠ Delete and a required field is empty
  - `TRUE` — all checks pass (or Delete with all relations cleared)
  - Required fields (non-Delete): Company Name, Record Status, Company Type, Domains, States, Website, Contacts
  - Delete wiring check (in order): Contacts → Action Items → Engagements → Tech Stack
- **Created Timestamp** (created_time) — auto-set on page creation
- All agent dedup rules must check BOTH domain fields (Domains, Additional Domains)

## Action Items DB Properties

- **Task Name** (title) — concise imperative description of the action item
- **Record Status** (select: Draft/Active/Inactive/Delete)
- **Type** (formula) — `📝 Task` when Assignee contains "Adam Freed"; `☝️ Follow Up` otherwise. Merged with former Icon property
- **Status** (status: Not started, In progress, Blocked, Done)
- **Priority** (select: High/Low/Backburner) — Agent defaults to Low when unknown
- **Task Notes** — full context, sub-tasks, meeting reference
- **Due Date** (date)
- **Contact** (relation → Contacts DB) — Tasks: requestor; Follow Ups: person to follow up with
- **Company** (relation → Companies DB, synced from Companies → Action Items)
- **Assignee** (person) — Tasks: Adam; Follow Ups: blank
- **Source Meeting** (relation → Meetings DB, synced from Meetings → Action Items)
- **Attach File** — file attachment (URLs from typed notes or AI summary)
- **Created Date** (created_time) — auto-set on page creation (renamed from Assign Date)
- **QC** (formula) — Data quality signal with 4 possible states:
  - `wired:PropertyName` — Record Status = Delete but the named relation is still populated (e.g., `wired:Contact`). Safe-to-delete check takes priority. First non-empty relation wins.
  - `missing:fieldname` — Record Status ≠ Delete and a required field is empty. `missing:task_status` uses `format()` wrapper (STATUS type requires it).
  - `past_due` — all required fields present AND Due Date < now() AND Status ≠ Done. Fires regardless of Record Status (except Delete, which routes to wired check first).
  - `TRUE` — all checks pass (or Delete with all relations cleared)
  - Required fields (non-Delete): Task Name, Record Status, Status (task), Priority, Due Date, Source Meeting
  - Delete wiring check (in order): Contact → Source Meeting
  - Note: Task Notes are NOT required. Status is checked via `empty(format(Status))` due to Notion STATUS type constraints.

## Meetings DB Properties

- **Meeting Title** (title) — event title from GCal
- **Record Status** (select: Draft/Active/Inactive/Delete)
- **Calendar Event ID** (text) — GCal event ID, canonical identity for matching
- **Calendar Name** (text) — source calendar display name; also "processed" signal
- **Date** (date) — event start + end, stored in Eastern timezone
- **Contacts** (relation → Contacts DB, synced dual) — attendees wired via email matching
- **Companies** (rollup) — derived from Contacts' Company relations
- **Action Items** (relation → Action Items DB, synced from Action Items → Source Meeting)
- **Series** (relation → Meetings DB, self) — links instances to their Series Parent
- **Instances** (relation → Meetings DB, self) — reciprocal of Series
- **Is Series Parent** (checkbox) — true only on the Series Parent page
- **Series Status** (rollup) — pulls Record Status from the linked Series Parent via the Series relation. Empty for standalone meetings. Used for cascade inactivation: when a Series Parent's Record Status = Inactive, all instances show Series Status = "Inactive" and are hidden from working views (Active, Weekly, Upcoming, Today) via filter.
- **Location** (text) — event location from GCal
- **QC** (formula) — Data quality signal with 3 possible states:
  - **Series Parent carve-out** — when `Is Series Parent = true`, always returns `TRUE` (Series Parents are reference records, not real meetings — no field validation applies)
  - `wired:PropertyName` — Record Status = Delete but the named relation is still populated (e.g., `wired:Contacts`). Safe-to-delete check takes priority. First non-empty relation wins.
  - `missing:fieldname` — Record Status ≠ Delete and a required field is empty
  - `TRUE` — all checks pass (or Delete with all relations cleared)
  - Required fields (non-Delete): Meeting Title, Record Status, Calendar Name, Calendar Event ID, Date
  - Delete wiring check (in order): Contacts → Action Items → Series → Instances
- **Created Timestamp** (created_time) — auto-set on page creation

## Delete Handoff Pattern

Claude (in any interface) cannot archive/trash individual Notion pages via MCP tools. When a record needs to be deleted:

1. **Unwire Before Delete** — Claude clears ALL relation properties on the record (Company, Contact, Source Meeting, Action Items, Contacts, Series, Instances — whichever apply to the database). Then clears the reciprocal relation on each formerly-linked record. Both sides must be explicitly unwired to prevent orphaned links. See the Relation Map in the [Merge Workflow](https://www.notion.so/323adb01222f811189c7c92eaac10ebb) for the full per-database breakdown.
2. Claude sets Record Status = Delete
3. Claude adds a Contact Notes / Company Notes / Task Notes flag explaining why (e.g., "MERGED → Formul8. Ready for HARD DELETE per merge workflow")
4. Adam periodically sweeps the Inactive/Delete view and trashes flagged records

---

# Rules of Engagement

These apply to every Claude session, regardless of interface:

1. **Read the Active handoff FIRST** — it has everything needed for context
2. **Standing approval applies to routine Notion work**. If Adam asks to update, sync, harden, document, or maintain the Notion workspace, execute the full read, edit, push, verify, and log loop without asking for step-by-step permission.
3. **Only pause for confirmation** when the task is ambiguous, destructive, schema-changing, touches lifecycle state, creates new CRM DB records, or is a migration/bulk operation
4. **For migrations or bulk operations:** audit current state → present plan → get Adam's approval → execute in phases with verification
5. **Never create new DB records** unless explicitly instructed
6. **Never change lifecycle state** (Approved/Active/Record Status) without explicit instruction. When Record Status is set to Delete (with explicit instruction), the **Unwire Before Delete** protocol in the Delete Handoff Pattern must be followed first
7. **Log everything** — the session handoff is the system of record
8. **Dedup checks are mandatory** — always check Email + Secondary Email + Tertiary Email for contacts, Domains + Additional Domains for companies

## Standing Approval Scope

Routine Notion work is pre-authorized once Adam requests it. This includes:

- Reading mapped Notion pages and databases for context or verification
- Editing local `docs/` files and `ops/notion-workspace/CLAUDE.md`
- Pushing local instruction changes to their mapped Notion pages via MCP
- Updating the Active Session Handoff and Session Archive as part of normal session maintenance
- Duplicating and moving session handoff pages during the documented end-of-session flow
- Adding logs, summaries, and verification notes needed to keep the workspace current

Pause and ask before proceeding only when any of the following are true:

- The request is ambiguous or conflicts with the local source-of-truth docs
- The change would modify database schema, views, automations, or agent architecture
- The change would create, merge, delete, or bulk-edit CRM records
- The change would alter `Record Status` or other lifecycle controls
- The operation is large enough that rollback would be difficult

---

# Maintenance

This document should be updated whenever:

- A new agent instruction page is created → add to Agent Registry table
- A new workflow document is created → add to Workflow Documents table
- A new database is created → add to Database Quick Reference table
- Schema conventions change (e.g., Record Status migration) → update Schema Conventions section
- Rules of engagement evolve → update Rules section
- The kickoff prompt needs adjustment → update `CLAUDE.md` in the project repo
