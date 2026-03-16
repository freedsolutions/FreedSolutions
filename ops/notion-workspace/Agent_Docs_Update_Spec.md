# Agent Docs Update — Prescriptive Spec

> **Purpose:** Update all agent instruction docs, SOPs, and Notion pages to reflect the schema changes completed in the Schema Updates project. Run each phase in **Plan mode** first, review, then execute.

---

## Context: What Changed

The following schema changes were made and are now live in Notion:

| Change | Details |
|--------|---------|
| `Wiring Check` → `QC` | Renamed on all 4 DBs. Formula output: `TRUE` (pass) / `missing:fieldname` (fail) |
| `Icon` dropped | Removed from Action Items. Logic merged into Type formula |
| `Type` formula updated | Now outputs `📝 Task` (Adam assigned) / `☝️ Follow Up` (not Adam). Uses `contains(Assignee, "Adam Freed")` check |
| `Display Name` updated | Contacts: Nickname replaces first name + appends `(Pronouns)` when populated |
| `Meetings` dual relation | Added to Contacts (synced from Meetings → Contacts) |
| `Assign Date` → `Created Date` | Renamed on Action Items |
| `Created Date` added | New `created_time` property on Contacts, Companies, and Meetings |
| Set By changes | Role/Title, Phone, Pronouns, LinkedIn → Agent+Manual. Company Type, States, Website → Agent+Manual |
| QC rules defined | Each DB has explicit required fields; formula flags `missing:fieldname` per field |

### QC Rules by Database

**Contacts:** Contact Name, Record Status, Email, Company, Role/Title
**Companies:** Company Name, Record Status, Company Type, Domains, States, Website, Contacts
**Action Items:** Task Name, Record Status, Status, Priority, Task Notes, Due Date, Source Meeting
**Meetings:** Meeting Title, Record Status, Calendar Name, Calendar Event ID, Date

---

## File ↔ Notion Page Mapping

Each repo doc has a `<!-- Notion Page ID: ... -->` comment at the top. Claude Code edits the local MD file, then pushes the content to the mapped Notion page via MCP.

| Repo File | Notion Page ID | Notion Page Name |
|-----------|---------------|-----------------|
| `docs/agent-sops.md` | `323adb01-222f-81d7-bc47-c32cfea460f4` | Agent SOPs |
| `docs/unified-post-meeting.md` | `324adb01-222f-8168-a207-d66e81884454` | Post-Meeting Instructions |
| `docs/contact-company-review.md` | `323adb01-222f-8126-9db8-df77be5a326f` | Contact & Company Instructions |
| `docs/merge-workflow.md` | `323adb01-222f-8111-89c7-c92eaac10ebb` | Merge Workflow |
| `docs/notion-agent-config.md` | `321adb01-222f-8033-ad89-c3f889ae4dec` | Notion Agent |

**Workflow:** Edit local file → verify changes → push to Notion page via `notion-update-page` or equivalent MCP call.

---

## Phase 1 — Update `agent-sops.md` (Schema Conventions)

This is the living reference doc. Every other doc and agent derives from it. Update it first.

### 1A. Contacts DB Properties section

**Replace the entire Contacts DB Properties block** with:

- **Contact Name** (title) — full name of the contact
- **Record Status** (select: Draft/Active/Inactive/Delete)
- **Email** — primary business email (used for calendar matching and dedup)
- **Company** (relation → Companies DB)
- **Display Name** (formula) — if Nickname populated, replaces first name; appends (Pronouns) when present
- **QC** (formula) — `TRUE` when all required fields populated; `missing:fieldname` when any are empty. Required: Contact Name, Record Status, Email, Company, Role/Title
- **Contact Notes** — freeform notes (Agent appends via Floppy; Adam edits)
- **Role / Title** — job title or role (Agent + Manual)
- **Secondary Email** — alternate email (personal, old domain, etc.)
- **Tertiary Email** — third email if needed
- **Nickname** — informal name or alias (used by Display Name formula)
- **Phone** — phone number (Agent + Manual)
- **Pronouns** — pronouns (Agent + Manual; used in Display Name)
- **LinkedIn** — LinkedIn profile URL (Agent + Manual)
- **Meetings** (relation → Meetings DB, synced dual) — all meetings this contact attended
- **Created Date** (created_time) — auto-set on page creation
- All agent dedup rules must check ALL email fields (Email, Secondary Email, Tertiary Email)

### 1B. Companies DB Properties section

**Replace the entire Companies DB Properties block** with:

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
- **QC** (formula) — `TRUE` when all required fields populated; `missing:fieldname` when any are empty. Required: Company Name, Record Status, Company Type, Domains, States, Website, Contacts
- **Created Date** (created_time) — auto-set on page creation
- All agent dedup rules must check BOTH domain fields (Domains, Additional Domains)

### 1C. Action Items DB Properties section

**Replace the entire Action Items DB Properties block** with:

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
- **QC** (formula) — `TRUE` when all required fields populated; `missing:fieldname` when any are empty. Required: Task Name, Record Status, Status, Priority, Task Notes, Due Date, Source Meeting

### 1D. Meetings DB Properties section

**Replace the entire Meetings DB Properties block** with:

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
- **Location** (text) — event location from GCal
- **QC** (formula) — `TRUE` when all required fields populated; `missing:fieldname` when any are empty. Required: Meeting Title, Record Status, Calendar Name, Calendar Event ID, Date
- **Created Date** (created_time) — auto-set on page creation

### 1E. Update the "Last updated" line

Change the "Last updated" line at the top to reflect the current session.

### 1F. Push to Notion

After editing the local file, push the updated content to the Agent SOPs Notion page (`323adb01-222f-81d7-bc47-c32cfea460f4`).

---

## Phase 2 — Update `unified-post-meeting.md` (Post-Meeting Agent)

### 2A. Find-and-replace property name references

Perform these text replacements throughout the entire file:

| Find | Replace With |
|------|-------------|
| `Assign Date` | `Created Date` |
| `Wiring Check` | `QC` |

**Do NOT replace** any occurrences inside the "Cutover Checklist" section (historical record).

### 2B. Update the Action Item routing tables

In **Step 2.0.6** (Floppy routing table) and **Step 2.3** (AI Action Item routing table):
- Remove any row for `Icon` (it no longer exists)
- Confirm the `Type` row says `*(auto-computed from Assignee — do not set)*`
- Confirm `Created Date` replaces `Assign Date` in the visible properties columns

### 2C. Update the "Action Item Property Hardening" rules section

In the **Important Rules & Edge Cases** section, verify that rule references use `QC` not `Wiring Check`, and `Created Date` not `Assign Date`.

### 2D. Add Agent+Manual guidance for new fields

In the **Unknown Handling** section under Contact creation, update the paragraph about Role/Title, Phone, Pronouns, and LinkedIn to explicitly state these are **Agent + Manual** fields:

> **Role / Title, Phone, Pronouns, and LinkedIn** are Agent + Manual fields — populate when determinable from meeting context, email signatures, or web lookup. When uncertain, leave blank for Adam's manual review.

In the **Unknown Handling** section under Company creation, update Company Type, States, and Website guidance:

> **Company Type** — populate when clearly determinable (Agent + Manual). **States** — if Company Type is "Tech Stack", default to "All"; otherwise leave blank unless geography is clear (Agent + Manual). **Website** — populate from web lookup when confident (Agent + Manual).

### 2E. Push to Notion

After editing the local file, push the updated content to the Post-Meeting Instructions Notion page (`324adb01-222f-8168-a207-d66e81884454`).

---

## Phase 3 — Update `contact-company-review.md` (Contact & Company Agent)

### 3A. Find-and-replace property name references

| Find | Replace With |
|------|-------------|
| `Wiring Check` | `QC` |

### 3B. Update the "Contact Properties Updated by This Agent" table

Add these rows (Agent+Manual fields the enrichment agent should also populate):

| Property | Source | Update Rule |
|----------|--------|-------------|
| Phone | Enrichment provider / Web | Only if currently blank (Agent + Manual) |
| Pronouns | Enrichment provider / Web | Only if currently blank (Agent + Manual) |

### 3C. Update the "Company Properties Updated by This Agent" table

The existing table already covers Company Type, States, Website. No changes needed unless the update rules need the "(Agent + Manual)" annotation — add it for clarity.

### 3D. Push to Notion

After editing the local file, push the updated content to the Contact & Company Instructions Notion page (`323adb01-222f-8126-9db8-df77be5a326f`).

---

## Phase 4 — Update `merge-workflow.md`

### 4A. Update the Relation Map table

Add the `Meetings` relation to the Contacts row:

| Database | Relations to Clear on Record | Linked Records to Update (other side) |
|----------|------------------------------|---------------------------------------|
| **Contacts** | Company, Meetings | Remove contact from Meeting.Contacts, ActionItem.Contact |
| **Companies** | *(no outbound relations)* | Remove company from Contact.Company, ActionItem.Company |
| **Action Items** | Contact, Company, Source Meeting | Remove action item from Meeting.Action Items |
| **Meetings** | Action Items, Contacts | Remove meeting from ActionItem.Source Meeting, Contact.Meetings |

### 4B. Update Contact Merge Step 2

In the Contact Merge section, Step 2 ("Re-wire Meetings and Action Items"), confirm it mentions the `Meetings` dual relation — since Contacts now has a visible Meetings property, the unwire must clear both sides.

### 4C. Push to Notion

After editing the local file, push to the Merge Workflow Notion page (`323adb01-222f-8111-89c7-c92eaac10ebb`).

---

## Phase 5 — Update `notion-agent-config.md` (Notion Agent page)

### 5A. Update the "Core databases" bullet

Add the QC and Created Date context:

> - Contacts (👤), Companies (💼), Action Items (🎬), Meetings (🗓️)
> - All use `Record Status` select: Draft → Active → Inactive → Delete
> - All have `QC` formula: `TRUE` (pass) / `missing:fieldname` (fail)
> - All have `Created Date` (created_time, auto-set)

### 5B. Update the Memories section

Add a bullet noting the schema update:

> Schema hardening complete (Session 40+): Wiring Check → QC (TRUE/missing:X), Icon dropped and merged into Type, Assign Date → Created Date, Created Date added to all 4 DBs, Meetings ↔ Contacts dual relation, Display Name updated with Nickname/Pronouns, Agent+Manual fields expanded.

### 5C. Push to Notion

After editing the local file, push to the Notion Agent page (`321adb01-222f-8033-ad89-c3f889ae4dec`).

---

## Phase 6 — Verify consistency

After all pushes, do a final cross-check:

1. **Fetch each Notion page** and confirm the content matches the local file
2. **Search for stale references** in all local docs:
   - `grep -rn "Wiring Check" docs/` → should return zero hits (except deprecated files)
   - `grep -rn "Assign Date" docs/` → should return zero hits (except deprecated files and historical Cutover Checklist)
   - `grep -rn '"Icon"' docs/` → should return zero hits in active docs (except floppy-design.md historical references)
3. **Verify no broken references** — property names in agent routing tables match the live Notion schema

Report any remaining stale references found.

---

## Out of Scope (do not touch)

- **Deprecated files:** `meeting-sync.md`, `post-meeting-wiring.md`, `quick-sync.md` — these are historical. Do not update.
- **`floppy-design.md`** — design document, not operational. May reference old property names as historical context.
- **`curated-notes-design.md`** — draft design, not yet implemented.
- **`notetaker-crm.md`** — notetaker profile. Does not reference DB property names directly. No changes needed.
- **Views** — deferred to the Views Overhaul project.
- **CLAUDE.md** — update only if the session handoff format references stale property names. Otherwise leave for Adam to update during session management.

---

## Claude Code Workflow

Same approach as the Schema Updates project:

1. **Plan mode first** for each phase — show exactly which files will be edited and what content will change
2. **Review** — Adam approves the plan
3. **Execute** — edit local files, then push to Notion
4. **Verify** — fetch each Notion page to confirm content matches

One phase at a time. Do not batch. Phase 1 (Agent SOPs) must complete first because other docs reference it.
