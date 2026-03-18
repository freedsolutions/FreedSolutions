<!-- Notion Page ID: 323adb01-222f-81d7-bc47-c32cfea460f4 -->

# Agent SOPs

The living reference document for Adam's Notion workspace automation system. Used by both Adam and Claude (in any interface — chat, Claude Code terminal, or Claude App) to maintain continuity across sessions.

Last synced: Session 57 (March 18, 2026)

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

All agents have an instruction page under the Automation Hub containing the full workflow, business rules, safety rails, and database references. Notion Custom Agents (configured separately in Agent Config) reference these instruction pages.

| Agent | Instruction Page | Trigger | Model | Status | Settings URL |
| --- | --- | --- | --- | --- | --- |
| Post-Meeting Agent | Post-Meeting Instructions | Nightly 10 PM ET + Record Status → Active (Meetings DB) + manual | Opus 4.6 | Live | [Settings](https://www.notion.so/agent/321adb01222f805f8182009253dc57a7?wfv=settings) |
| Meeting Sync | [DEPRECATED] Meeting Sync Instructions | Disabled | — | Deprecated — replaced by Post-Meeting Agent (S37). Cutover complete (S37b). | — |
| Post-Meeting Wiring | [DEPRECATED] Post-Meeting Wiring Instructions | Disabled | — | Deprecated — replaced by Post-Meeting Agent (S37). Cutover complete (S37b). | — |
| Quick Sync | [DEPRECATED] Quick Sync Instructions | Disabled | — | Deprecated — replaced by Post-Meeting Agent (S37). Cutover complete (S37b). | — |
| Contact & Company Review | Contact & Company Instructions | Manual (@mention only) | Opus 4.6 | Active (manual) | [Settings](https://www.notion.so/agent/323adb01222f802cb5640092af74e84a?wfv=settings) |
| Delete Unwiring Agent | Delete Unwiring Instructions | Record Status → Delete (5 source DBs) + manual | Opus 4.6 | Live | [Settings](https://www.notion.so/agent/325adb01222f80d2844a0092e63da4ea?wfv=settings) |
| Curated Notes Agent | Curated Notes Instructions | Disabled (was: Record Status = Active, Meetings DB) | Opus 4.6 | Deprecated (folded into Post-Meeting Agent S57) | [Settings](https://www.notion.so/agent/325adb01222f802e91290092cb71c17d?wfv=settings) |
| Post-Email Agent | Post-Email Instructions | Nightly ~10:30 PM ET (after Post-Meeting Agent) + manual | Opus 4.6 | Live | [Settings](https://www.notion.so/agent/325adb01222f806da7960092bc6484d3?wfv=settings) |

Naming conventions:

- Custom Agent (Notion settings): [Agent Name] — e.g., "Delete Unwiring Agent"
- Instruction page (Notion, child of Automation Hub): [Short Name] Instructions — e.g., "Delete Unwiring Instructions"
- Local doc (repo): docs/[kebab-case].md — e.g., docs/delete-unwiring.md
- Model: lock all agents to a specific model (currently Opus 4.6) for consistent multi-step behavior

Adding new agents: When a new agent is created:

1. Create the instruction page under Automation Hub with title [Agent Name] Instructions
2. Create the local doc at docs/[kebab-case].md with matching content
3. Add to the Agent Registry table in docs/agent-sops.md
4. Add to the Local Docs table in CLAUDE.md
5. Update the Notion Agent page (docs/notion-agent.md) Active agents section
6. Push all changed docs to Notion and verify
7. Configure the Custom Agent in Notion settings (name, instruction page reference, model, trigger)

## Notetaker Profiles

Custom instruction profiles for Notion Calendar's AI notetaker. Each profile is pasted into the notetaker's custom instructions field and optimizes the AI summary for a specific meeting type.

| Profile | Local Doc | Purpose | Status |
| --- | --- | --- | --- |
| Notetaker CRM | `docs/notetaker-crm.md` | Default for business meetings. Structures Action Items for Post-Meeting Agent parsing. Surfaces "Hey Floppy" commands from voice AND typed notes (Layer 1). | Active |
| Strategy / Workshop | — | Longer brainstorm/planning sessions. Heavier on topic summaries. | Planned |
| 1:1 / Check-in | — | Quick syncs. Minimal structure, focus on decisions and follow-ups. | Planned |

**Why notetaker profiles matter:** The Post-Meeting Agent parses the `### Action Items` heading from the AI summary. Custom notetaker instructions ensure the AI produces summaries in the exact format the agent expects — improving parse accuracy, action item quality, and Floppy command surfacing (Layer 1).

## Trigger Configuration Reference

Prescriptive spec for the Notion UI Custom Agent settings. Each agent's triggers, page access, connections, and model are documented here. Any future agent config changes must update this section. Audit cadence: verify all agents against this spec whenever a new agent is added, an agent is renamed, or a DB is created.

### Post-Meeting Agent

- **Triggers:** Daily 10 PM | Property updated: Meetings → Record Status = Active (page-content-edit: UNCHECKED) | @mention
- **Notion Page Access:**
  - Meetings → Can edit content
  - Action Items → Can edit content
  - Contacts → Can edit content
  - Companies → Can edit content
  - Agent Config → Can edit
  - Post-Meeting Instructions → Can edit
  - Agent SOPs → Can view
- **Connections:** Calendar adam@freedsolutions.com (Adam-Business: Read and write; Adam-Personal: Read — pending Adam sharing personal calendar to this account) | Mail adam@freedsolutions.com (Read and draft) | Web access: On
- **Model:** Opus 4.6
- **Note:** S57 trigger overhaul — reactive "Meeting Title edited" trigger retired (caused duplicate stubs). Replaced with Record Status → Active. Nightly 10 PM remains as safety net for Draft pages (Steps 1–3 only). Active trigger runs full pipeline (Steps 1–4 including Curated Notes, folded from standalone Curated Notes Agent).

### Post-Email Agent

- **Triggers:** Daily 10:30 PM | @mention
- **Notion Page Access:**
  - Post-Email Instructions → Can edit
  - Emails → Can edit content
  - Contacts → Can edit content
  - Companies → Can edit content
  - Action Items → Can edit content
  - Agent SOPs → Can view
  - Agent Config → Can edit
- **Connections:** Mail adam@freedsolutions.com (Read) | Web access: Off | NO calendar
- **Model:** Opus 4.6

### Curated Notes Agent — DEPRECATED (S57)

- **Status:** Deprecated — logic folded into Post-Meeting Agent Step 4 (S57). Trigger should be **disabled** in Notion UI (not deleted — available for rollback).
- **Former Triggers:** Property updated: Meetings → Record Status = Active (page-content-edit: UNCHECKED) | @mention
- **Notion Page Access:**
  - Meetings → Can edit content
  - Action Items → Can edit content
  - Curated Notes Instructions → Can edit
  - Agent SOPs → Can view
  - Agent Config → Can edit
- **Connections:** Calendar adam@freedsolutions.com (Adam-Business: Read) | Web access: On | NO mail
- **Model:** Opus 4.6

### Contact & Company Agent

- **Triggers:** @mention only (NO scheduled, NO property-change, NO calendar-event triggers)
- **Notion Page Access:**
  - Contact & Company Instructions → Can edit
  - Companies → Can edit content
  - Contacts → Can edit content
  - Agent Config → Can edit
  - Agent SOPs → Can view
- **Connections:** Web access: On | Calendar: adam@freedsolutions.com (Adam-Business: Read) | NO mail
- **Model:** Opus 4.6

### Delete Unwiring Agent

- **Triggers:** Property updated on EACH of 5 DBs → Record Status = Delete (page-content-edit: UNCHECKED on all): Meetings | Companies | Action Items | Contacts | Emails | @mention
- **Notion Page Access:**
  - Delete Unwiring Instructions → Can edit
  - Contacts → Can edit content
  - Companies → Can edit content
  - Action Items → Can edit content
  - Meetings → Can edit content
  - Emails → Can edit content
  - Agent Config → Can edit
  - Agent SOPs → Can view
- **Connections:** Web access: Off | NO calendar | NO mail
- **Model:** Opus 4.6

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
| Emails | `f685a378-5a37-4517-9b0c-d2928be4af4d` | 📧 |

**Adam's Notion User ID:** `30cd872b-594c-81b7-99dc-0002af0f255a`

## Meetings DB Automation

A Notion DB automation (not an agent — no credits) runs on "Page added to Meetings":
- Sets **Record Status** to Draft
- Sets **page icon** to 🗓️

This ensures every new meeting page starts in Draft with a consistent icon. The Post-Meeting Agent's Step 1.3 has a safety-net check for pages that pre-date the automation.

---

# Schema Conventions

## Lifecycle State: Record Status (select)

All 5 source DBs (Contacts, Companies, Action Items, Meetings, Emails) use a single `Record Status` select with 4 options:

- **Draft** (gray) — Agent-created, pending Adam's review
- **Active** (green) — Reviewed and operational
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
  - Delete wiring check (in order): Company → Meetings → Emails
- **Contact Notes** — freeform notes (Agent appends via Floppy; Adam edits)
- **Role / Title** — job title or role (Agent + Manual)
- **Secondary Email** — alternate email (personal, old domain, etc.)
- **Tertiary Email** — third email if needed
- **Nickname** — informal name or alias (used by Display Name formula)
- **Phone** — US phone number, normalized to `(XXX) XXX-XXXX`. Strip dots, extra dashes, malformed parens on write. (Agent + Manual)
- **Pronouns** — pronouns (Agent + Manual; used in Display Name)
- **LinkedIn** — LinkedIn profile URL (Agent + Manual)
- **Meetings** (relation → Meetings DB, synced dual) — all meetings this contact attended
- **Emails** (relation → Emails DB, synced dual) — all email threads involving this contact
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
- **Source Email** (relation → Emails DB, synced from Emails → Action Items)
- **Attach File** — file attachment (URLs from typed notes or AI summary)
- **Created Date** (created_time) — auto-set on page creation (renamed from Assign Date)
- **QC** (formula) — Data quality signal with 4 possible states:
  - `wired:PropertyName` — Record Status = Delete but the named relation is still populated (e.g., `wired:Contact`). Safe-to-delete check takes priority. First non-empty relation wins.
  - `missing:fieldname` — Record Status ≠ Delete and a required field is empty. `missing:task_status` uses `format()` wrapper (STATUS type requires it).
  - `past_due` — all required fields present AND Due Date < today() AND Status ≠ Done. Fires regardless of Record Status (except Delete, which routes to wired check first).
  - `TRUE` — all checks pass (or Delete with all relations cleared)
  - Required fields (non-Delete): Task Name, Record Status, Status (task), Priority, Due Date, Contact, Source Meeting
  - Delete wiring check (in order): Contact → Company → Source Meeting
  - Note: Task Notes are NOT required. Status is checked via `empty(format(Status))` due to Notion STATUS type constraints.

## Meetings DB Properties

- **Meeting Title** (title) — event title from GCal
- **Record Status** (select: Draft/Active/Inactive/Delete)
- **Calendar Event ID** (text) — GCal event ID, canonical identity for matching
- **Calendar Name** (select: Adam - Business, Adam - Personal, Manual, Pending) — source calendar; also "processed" signal
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
  - Required fields (non-Delete): Meeting Title, Record Status, Calendar Name, Calendar Event ID, Date, Contacts
  - `missing:Contacts` — Record Status ≠ Delete, not a Series Parent, and Contacts relation is empty. With the solo-event wiring rule, every meeting should have at least one Contact (Adam). An empty Contacts field means something went wrong. Label is `missing:Contacts` (not `missing:Companies`) because Companies is a derived rollup — fixing Contacts fixes Companies.
  - Delete wiring check (in order): Contacts → Action Items → Series → Instances
- **Created Timestamp** (created_time) — auto-set on page creation

## Emails DB Properties

- **Email Subject** (title) — Gmail thread subject line
- **Record Status** (select: Draft/Active/Inactive/Delete)
- **Thread ID** (text) — Gmail thread ID, canonical identity for dedup
- **From** (text) — sender email of the first message in the thread
- **Direction** (formula) — Outbound if From matches Adam's aliases, Inbound otherwise
- **Date** (date) — thread start date (first message timestamp)
- **Contacts** (relation → Contacts DB, synced dual) — participants wired via email matching
- **Companies** (rollup) — derived from Contacts' Company relations
- **Action Items** (relation → Action Items DB, synced from Action Items → Source Email)
- **Labels** (multi_select) — Gmail user-created labels (system labels excluded)
- **Email Notes** (text) — AI-generated 1–2 sentence thread summary
- **QC** (formula) — Data quality signal with 3 possible states:
  - `wired:PropertyName` — Record Status = Delete but the named relation is still populated (e.g., `wired:Contacts`). Safe-to-delete check takes priority. First non-empty relation wins.
  - `missing:fieldname` — Record Status ≠ Delete and a required field is empty
  - `TRUE` — all checks pass (or Delete with all relations cleared)
  - Required fields (non-Delete): Email Subject, Record Status, Thread ID, From, Date, Contacts
  - Delete wiring check (in order): Contacts → Action Items
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
2. **Standing approval applies to routine Notion work**. If Adam asks to update, sync, harden, document, or maintain the Notion workspace, execute the full read, edit, push, verify, review, and log loop without asking for step-by-step permission.
3. **Only pause for confirmation** when the task is ambiguous, destructive, schema-changing, touches lifecycle state, creates new CRM DB records, or is a migration/bulk operation
4. **For migrations or bulk operations:** audit current state → present plan → get Adam's approval → execute in phases with verification
5. **Never create new DB records** unless explicitly instructed
6. **Never change lifecycle state** (Record Status: Draft/Active/Inactive/Delete) without explicit instruction. When Record Status is set to Delete (with explicit instruction), the **Unwire Before Delete** protocol in the Delete Handoff Pattern must be followed first
7. **Log everything** — the session handoff is the system of record
8. **Dedup checks are mandatory** — always check Email + Secondary Email + Tertiary Email for contacts, Domains + Additional Domains for companies
9. **UI steps require Adam's confirmation before marking complete.** Some tasks can only be done in the Notion UI (configuring agent triggers, pasting content too large for API, Settings changes). When a planning output or session priority includes a UI step: (a) explicitly list it as "Adam — UI step", (b) do NOT mark it complete until Adam confirms in the chat that it's done, (c) do not assume completion based on page existence or other indirect signals. If there are no UI steps, Claude closes the loop by verifying via MCP.
10. **Verify content on sync, not just existence.** When marking a Notion page as "in sync" with a local doc, verify the actual content matches — not just that the page exists. This is especially important for pages created Notion-first that later get a local source-of-truth file.

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

## Kickoff Conventions

**Claude Code (terminal):** Use the custom slash command `/notion`. It reads `CLAUDE.md`, fetches the Active session page, and orients automatically. Behavior adapts to Claude Code's mode:

- **Plan mode** → presents session briefing, asks what to tackle, discusses before executing
- **Edit mode** → executes current session priorities with standing approval, pauses only per Rules of Engagement

Additional context after `/notion` scopes the task in either mode (e.g., `/notion fix the QC formula`).

**Claude.ai (planning chat):** Attach `CLAUDE.md` + relevant repo docs. Say "Fetch the Active session page and let's plan" or "...and let's review [topic]."

No session numbers in kickoff prompts. The Active page heading contains the session number — Claude reads it and orients automatically.

**Codex review gate for Notion workspace doc changes:** When a task changes local files under `ops/notion-workspace/`, use this order: edit local source-of-truth files → push mapped docs to Notion → re-fetch and verify live parity → run Codex review on the current worktree → update the Session — Active log → commit and push. Do not update the session log before the Codex review gate unless Adam explicitly asks for a pre-review draft note.

**Commit convention:** After completing any task that changes local files (docs, configs, CLAUDE.md), commit and push to main. Concise commit message per logical task. Don't batch unrelated changes. Plan mode doesn't commit (nothing to commit). Edit mode commits after each completed task.

---

# Maintenance

This document should be updated whenever:

- A new agent instruction page is created → add to Agent Registry table
- A new workflow document is created → add to Workflow Documents table
- A new database is created → add to Database Quick Reference table
- Schema conventions change (e.g., Record Status migration) → update Schema Conventions section
- Rules of engagement evolve → update Rules section
- The kickoff prompt needs adjustment → update `CLAUDE.md` in the project repo
