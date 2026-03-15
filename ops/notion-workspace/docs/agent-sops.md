<!-- Notion Page ID: 323adb01-222f-81d7-bc47-c32cfea460f4 -->
# Agent SOPs

The living reference document for Adam's Notion workspace automation system. Used by both Adam and Claude (in any interface — chat, Claude Code terminal, or Claude App) to maintain continuity across sessions.

Last updated: Session 38 (March 15, 2026)

---

# Session Management

## How Sessions Work

Each work session with Claude is numbered sequentially. Sessions may happen in the Claude.ai chat interface, the Claude App, or Claude Code in VSCode terminal. Regardless of interface, the same two Notion pages serve as the handoff mechanism:

**Session — Active** (stable URL, content overwritten each session):

Session — Active

**Session — Archive** (stable URL, content appended each session):

Session — Archive

The Active page always contains the latest session's handoff — what happened last time, current system status, priorities for the current session, schema reference, DB IDs, and the opening prompt.

The Archive page contains the full history of every session, organized by phase, with a detailed entry per session.

## End-of-Session Protocol

At the end of every session, regardless of interface:

1. Add a session summary line to the **System Evolution Arc** section of the Archive page
2. Add a detailed session entry to the Archive page (under the appropriate phase heading)
3. Duplicate the Active page → move the duplicate as a child page under the Archive page
4. Overwrite the Active page with the next session's handoff content (new summary, new priorities, updated schema, new opening prompt)

## Starting a New Session

Claude Code reads `CLAUDE.md` from the project root automatically — no prompt pasting needed. For Claude App chat sessions, copy the kickoff prompt from `CLAUDE.md` into the chat.

---

# Agent Registry

All agents are instruction pages under the Automation Hub. Each page contains the full workflow, business rules, safety rails, and database references for that agent.

| Agent | Instruction Page | Trigger | Status |
| --- | --- | --- | --- |
| Post-Meeting Agent | Post-Meeting Agent Instructions | Nightly 10 PM ET + manual | Active |
| Meeting Sync | [DEPRECATED] Meeting Sync Instructions | Disabled | Deprecated — replaced by Post-Meeting Agent (S37). Cutover complete (S37b). |
| Post-Meeting Wiring | [DEPRECATED] Post-Meeting Wiring Instructions | Disabled | Deprecated — replaced by Post-Meeting Agent (S37). Cutover complete (S37b). |
| Quick Sync | [DEPRECATED] Quick Sync Instructions | Disabled | Deprecated — replaced by Post-Meeting Agent (S37). Cutover complete (S37b). |
| Contact & Company Review | Contact & Company Review Instructions | Manual (after other syncs) | Active |

## Notetaker Profiles

Custom instruction profiles for Notion Calendar's AI notetaker. Each profile is pasted into the notetaker's custom instructions field and optimizes the AI summary for a specific meeting type.

| Profile | Local Doc | Purpose | Status |
| --- | --- | --- | --- |
| CRM-Optimized | `docs/notetaker-crm.md` | Default for business meetings. Structures Action Items for Post-Meeting Agent parsing. Surfaces "Hey Floppy" commands (Layer 1). | Active |
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
- **Display Name** (formula) — Contact Name + Pronouns when present
- **Wiring Check** (formula) — missing Email → missing Company → missing Role / Title → ✅
- **Email** — primary business email (used for calendar matching and dedup)
- **Secondary Email** — alternate email (personal, old domain, etc.)
- **Tertiary Email** — third email if needed
- **Phone** — phone number
- **Pronouns** — pronouns
- **Nickname** — informal name or alias
- **LinkedIn** — LinkedIn profile URL
- **Company** (relation → Companies DB)
- **Role / Title** — job title or role
- **Record Status** (select: Draft/Active/Inactive/Delete)
- **Contact Notes** — freeform notes about the contact
- All agent dedup rules must check ALL email fields (Email, Secondary Email, Tertiary Email)

## Companies DB Properties

- **Company Name** (title) — official company name
- **Company Type** (select: Tech Stack, Operator, Network, Personal) — categorizes the company's relationship
- **Wiring Check** (formula) — missing Domains → missing Company Type → ✅
- **Domains** — primary business domains (comma-separated, no spaces). Used for agent matching: email domain → company lookup
- **Additional Domains** — merged/subsidiary/alternate domains (comma-separated, no spaces, domains only — no full email addresses)
- **States** — operating states (default: "All" when not explicitly known)
- **Website** — company website URL
- **Contacts** (relation → Contacts DB)
- **Action Items** (relation → Action Items DB)
- **Engagements** (relation)
- **Tech Stack** (relation)
- **Record Status** (select: Draft/Active/Inactive/Delete)
- **Company Notes** — freeform notes about the company
- All agent dedup rules must check BOTH domain fields (Domains, Additional Domains)

## Action Items DB Properties

- **Task Name** (title) — concise imperative description of the action item
- **Type** (formula) — auto-computed: Assignee = Adam → "Task", otherwise → "Follow Up"
- **Icon** (formula) — 📝 for Task, ☝️ for Follow Up
- **Status** (status: Not started, In progress, Done)
- **Priority** (select: High/Low/Backburner)
- **Record Status** (select: Draft/Active/Inactive/Delete)
- **Task Notes** — full context, sub-tasks, meeting reference
- **Due Date** (date)
- **Assign Date** (created_time) — auto-populates with page creation date
- **Contact** (relation → Contacts DB)
- **Company** (relation → Companies DB)
- **Assignee** (person)
- **Source Meeting** (relation → Meetings DB)
- **Attach File** — file attachment
- **Wiring Check** (formula) — missing Company when Contact set, missing Source Meeting

## Meetings DB Properties

- **Meeting Title** (title) — event title from GCal (stripped of FW:/Fwd: prefixes)
- **Calendar Event ID** (text) — GCal event ID, canonical identity for matching
- **Calendar Name** (text) — source calendar display name, populated by the Post-Meeting Agent. Also serves as the "processed" signal (empty = not yet wired by agent)
- **Date** (date) — event start + end, stored in Eastern timezone (not UTC)
- **Contacts** (relation → Contacts DB) — attendees wired via email matching
- **Companies** (rollup) — derived from Contacts' Company relations
- **Action Items** (relation → Action Items DB) — parsed from AI meeting notes
- **Series** (relation → Meetings DB, self) — links instances to their Series Parent
- **Instances** (relation → Meetings DB, self) — reciprocal of Series
- **Is Series Parent** (checkbox) — true only on the Series Parent page, not instances
- **Location** (text) — event location from GCal, captured when present
- **Record Status** (select: Draft/Active/Inactive/Delete) — added Session 36. Draft used for agent-created no-notes meeting records. Not set on Notion Calendar pages.

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
