# Session 43 — Claude Code Prompt

> **Interface:** Claude Code (VSCode terminal with Notion MCP access)
> **Prerequisite:** Read `CLAUDE.md` from project root, then fetch Session — Active (`323adb01-222f-81f1-bd4b-d0383d39d47a`).
> **Session context:** Phone normalization completed in S43 chat session. Views Overhaul completed manually. This prompt covers the remaining S43 work.

---

## Task 1: QC Formula Enhancements

### 1A: Past Due Rule (Action Items DB only)

**What:** Extend the QC formula on the Action Items DB to flag `past_due` when the item is overdue.

**Logic:**
- Flag `past_due` when: `Due Date < today` AND `Status ≠ "Done"`
- This applies regardless of Record Status (Draft, Active, Inactive all get flagged — only Delete is excluded by convention since those are being removed anyway)
- The `past_due` flag is **in addition to** existing `missing:fieldname` checks, not a replacement. A single item could show `missing:due_date` OR `past_due` OR `TRUE`.

**Steps:**
1. Fetch the Action Items DB data source (`collection://319adb01-222f-8059-bd33-000b029a2fdd`) to read the current QC formula via its `codeUrl` property (`formulaCode://319adb01-222f-8059-bd33-000b029a2fdd/QFdXQA`).
2. If the formula code can't be fetched directly, read the current QC formula from the Notion UI or infer from the documented required fields: Task Name, Record Status, Status, Priority, Task Notes, Due Date, Source Meeting.
3. Extend the formula to add the `past_due` condition. The formula should:
   - First check all existing `missing:fieldname` conditions (preserve current logic exactly)
   - Then, if all required fields pass, check if `Due Date < now()` AND `Status != "Done"` → return `"past_due"`
   - Only return `"TRUE"` if all fields pass AND the item is not past due
4. Push the updated formula to the Action Items DB via `notion-update-data-source` or equivalent.
5. Verify by fetching a known past-due Active item and confirming QC shows `past_due`.

**Current required fields for Action Items QC:** Task Name, Record Status, Status, Priority, Task Notes, Due Date, Source Meeting

### 1B: Delete Wiring Rule (All 4 DBs)

**What:** Extend the QC formula on all 4 CRM databases to flag `wired:PropertyName` when `Record Status = "Delete"` but relation properties are still populated.

**Logic per DB:**

| Database | Data Source ID | Relations to Check |
|----------|---------------|-------------------|
| Contacts | `fd06740b-ea9f-401f-9083-ebebfb85653c` | Company, Meetings |
| Companies | `796deadb-b5f0-4adc-ac06-28e94c90db0e` | Contacts, Action Items, Engagements, Tech Stack |
| Action Items | `319adb01-222f-8059-bd33-000b029a2fdd` | Contact, Source Meeting |
| Meetings | `31fadb01-222f-80c0-acf7-000b401a5756` | Contacts, Action Items, Series, Instances |

**Formula behavior:**
- When `Record Status = "Delete"`: check each relation property listed above. If ANY relation is non-empty, return `"wired:PropertyName"` (first non-empty relation found). If all relations are empty, return `"TRUE"` (clean for delete).
- When `Record Status ≠ "Delete"`: use existing QC logic (missing field checks + past_due for Action Items).
- The delete-wiring check takes **priority** over missing-field checks when Record Status = Delete. Rationale: if a record is marked for deletion, the most important QC signal is whether it's safe to delete (fully unwired), not whether it has all fields filled.

**Steps:**
1. Fetch each DB's data source to read the current QC formula.
2. For each DB, extend the formula:
   - Add a top-level check: `if Record Status = "Delete"` → run the wiring check (return `"wired:X"` or `"TRUE"`)
   - `else` → run existing QC logic unchanged
3. Push all 4 updated formulas.
4. Verify by fetching a record with Record Status = Delete that still has relations populated — confirm QC shows `wired:X`.

### 1C: Update Documentation

After formula changes are live:

1. **`docs/agent-sops.md`** — Update all 4 QC property descriptions in the Schema Conventions section to document the new behaviors:
   - Action Items QC: add `past_due` description
   - All 4 DBs QC: add `wired:PropertyName` description for Delete records
2. **Push `agent-sops.md` to Notion** (`323adb01-222f-81d7-bc47-c32cfea460f4`) and verify.
3. **`docs/notion-agent-config.md`** — Update the Memories section to note QC formula enhancements (Session 43).
4. **Push `notion-agent-config.md` to Notion** (`321adb01-222f-8033-ad89-c3f889ae4dec`) and verify.

---

## Task 2: Delete Unwiring Agent — Instruction Page

### What

Create a new agent instruction page: **Delete Unwiring Agent Instructions**. This agent will be triggered (in a future session) by a Notion DB automation when `Record Status` is changed to `"Delete"` on any of the 4 CRM databases. For now, build the instruction page so it's ready when the automation trigger is configured.

### Instruction Page Location

Create as a child page of the **Automation Hub** (`321adb01-222f-810f-8706-e53105950d86`).

### Agent Design

**Agent Name:** Delete Unwiring Agent
**Trigger (future):** Notion DB automation — fires when `Record Status` property is changed to `"Delete"` on Contacts, Companies, Action Items, or Meetings DB.
**Trigger (current):** Manual only (until automation is configured in a follow-up session).

**Workflow:**

1. **Identify the record** — Read the page that triggered the agent. Determine which DB it belongs to.
2. **Check the Relation Map** — Based on the DB, identify which relation properties need to be cleared:

| Database | Relations to Clear on Record | Linked Records to Update (other side) |
|----------|------------------------------|---------------------------------------|
| **Contacts** | Company, Meetings | For each linked Meeting: remove this contact from Meeting.Contacts |
| **Companies** | *(Contacts and Action Items are synced/inbound — clearing the outbound side on Contact/Action Item handles it)* | No outbound relations to clear on the Company itself, but verify no orphaned backlinks remain |
| **Action Items** | Contact, Source Meeting | For each linked Meeting: remove this action item from Meeting.Action Items |
| **Meetings** | Contacts, Action Items, Series, Instances | For each linked Contact: remove this meeting from Contact.Meetings. For each linked Action Item: remove this meeting from ActionItem.Source Meeting. For Series/Instances self-relations: clear both sides. |

3. **Clear all relation properties** on the record (set each to empty/null).
4. **Clear reciprocal relations** on each formerly-linked record (both sides must be explicitly unwired).
5. **Add a Notes flag** — Append to the appropriate Notes field (Contact Notes / Company Notes / Task Notes):
   `"[YYYY-MM-DD] (via Delete Unwiring Agent) Relations cleared. Ready for hard delete."`
   For Meetings (no notes field), the agent logs completion but doesn't append notes.
6. **Verify** — Re-fetch the record and confirm all relations are empty. Confirm QC no longer shows `wired:X` (should show `TRUE` for the delete-wiring check).

**Safety Rails:**
- **Never change Record Status.** The agent only clears relations and appends notes. Record Status was already set to Delete by Adam (which triggered this agent).
- **Never delete/trash pages.** The agent unwires; Adam hard-deletes from the Delete view.
- **Never create new records.**
- **Idempotent.** If relations are already empty, the agent does nothing and logs "Already unwired."
- **Non-destructive on linked records.** When clearing reciprocal relations, only remove the specific page reference — do not clear the entire relation property on the linked record.

**Error Handling:**
- If a linked record can't be found (already deleted), log a warning and continue.
- If a relation property can't be cleared (permissions, API error), log the error and continue with remaining relations. Report all failures in the output summary.

**Output Summary:**
```
Delete Unwiring Agent — [Record Title] ([DB Name])
- Relations cleared on record: [list]
- Reciprocal relations updated: [count]
- Already empty (skipped): [list]
- Errors: [details or "none"]
- Notes flag appended: [yes/no]
- QC verification: [wired:X → TRUE / already TRUE]
```

### Registration

After creating the instruction page:

1. **`docs/agent-sops.md`** — Add to the Agent Registry table:
   - Agent: Delete Unwiring Agent
   - Instruction Page: (link to new page)
   - Trigger: Manual (automation pending)
   - Status: Active (manual trigger)
2. **Also create `docs/delete-unwiring.md`** as the local source-of-truth file (same content as the Notion page). Add to the file mapping table in `CLAUDE.md`.
3. **Push agent-sops.md to Notion** and verify.
4. **Update `docs/notion-agent-config.md`** — Add the Delete Unwiring Agent to the Active agents section.
5. **Push notion-agent-config.md to Notion** and verify.
6. **Update `CLAUDE.md`** — Add `docs/delete-unwiring.md` to the Local Docs table with its Notion Page ID.
7. **Commit all local changes to main.**

---

## Task 3: EAG → Formul8 Company Merge

### What

Merge the **Elevated Advisory Group (EAG)** company into **Formul8**. EAG is a sub-brand/affiliate of Formul8. This follows the existing Merge Workflow documented in `docs/merge-workflow.md`.

### Record Details

**EAG (placeholder to merge):**
- Page ID: `323adb01-222f-810b-bbf9-c1851c99bbc9`
- Domains: `elevatedadvisors.co`
- Company Type: "Tech Stack" (incorrect — actually consulting)
- Contacts: Kevin Serwatowski (`323adb01-222f-81ce-b58b-f8dfe78bc5be`)
- Action Items: none
- Company Notes: "Cannabis consulting firm — extraction, processing, retail, cultivation consulting. Application writing, expert witness, operational auditing. 40+ years combined experience. Industry: Consulting (not in select options)."
- Record Status: Active

**Formul8 (canonical company):**
- Page ID: `31eadb01-222f-811b-b629-c527f22e8816`
- Domains: `formul8.ai, staqs.io`
- Additional Domains: `druckerdataworks.com`
- Company Type: "Network"
- Company Notes: "Strategic growth partner agreement"

### Execution Steps

Follow the Company Merge checklist from `docs/merge-workflow.md`:

1. **Add domain to Formul8's Additional Domains:**
   - Current: `druckerdataworks.com`
   - New: `druckerdataworks.com, elevatedadvisors.co`

2. **Append EAG's Company Notes to Formul8's Company Notes:**
   - Append: `"\n[2026-03-16] (merged from Elevated Advisory Group / EAG) Cannabis consulting firm — extraction, processing, retail, cultivation consulting. Application writing, expert witness, operational auditing. 40+ years combined experience."`

3. **Re-wire Kevin Serwatowski's Company relation** from EAG → Formul8:
   - Update Kevin's Company property to point to Formul8 (`31eadb01-222f-811b-b629-c527f22e8816`)

4. **Verify EAG is fully unwired** — After re-wiring Kevin, EAG should have no Contacts, no Action Items. Confirm all relation backlinks are empty.

5. **Set EAG Record Status to Delete:**
   - Set Record Status = "Delete"
   - Append to Company Notes: `"MERGED → Formul8. Ready for HARD DELETE per merge workflow."`

6. **Spot-check Formul8** — Fetch Formul8 and verify:
   - Additional Domains includes `elevatedadvisors.co`
   - Company Notes includes the merged EAG notes
   - Kevin Serwatowski appears in the Contacts relation

### Merge Workflow Doc Update

After executing the merge, update `docs/merge-workflow.md`:

**Add a new section: "Primary Domain vs. Additional Domains"** after the "Domain Field Reference" section. Content:

```markdown
# Primary Domain vs. Additional Domains — Decision Rules

When merging a company or discovering a new domain relationship, decide where the domain goes:

## Domains (Primary)
The `Domains` property contains the company's **primary business domains** — the domains used for day-to-day email and operations. These are what agents match against when wiring contacts to companies.

Rules:
- First domain listed is the **canonical** domain (used for display and conflict resolution)
- All domains in this field are actively used for email by the company's employees
- Example: `formul8.ai, staqs.io` — both are primary operational domains for Formul8

## Additional Domains (Merged/Subsidiary/Alternate)
The `Additional Domains` property contains domains that **belong to** the company but are not the primary operational domains. These are checked during dedup and contact wiring but are secondary.

Rules:
- Merged/absorbed company domains go here (e.g., `druckerdataworks.com` after Drucker Data Works merged into Formul8)
- Sub-brand or affiliate domains go here (e.g., `elevatedadvisors.co` as a Formul8 affiliate)
- Former/legacy domains go here (company rebranded but old domain still receives email)
- Domains where employees don't actively send email but that are associated with the company

## Decision Heuristic
Ask: "Do employees at this company send email from this domain today?"
- **Yes** → `Domains` (primary)
- **No, but the domain is associated with the company** → `Additional Domains`
- **No, and the domain is unrelated** → Do not add; may be a separate company

## Agent Behavior
Both `Domains` and `Additional Domains` are checked during:
- Contact → Company wiring (Post-Meeting Agent Step 1)
- Company dedup (Contact & Company Review Agent)
- Merge Workflow domain checks

The distinction is for Adam's operational clarity, not for agent matching logic. Agents treat both fields equally for matching purposes.
```

**Push merge-workflow.md to Notion** (`323adb01-222f-8111-89c7-c92eaac10ebb`) and verify.

---

## End-of-Session Protocol

After all 3 tasks are complete:

1. **Update Session — Active** (`323adb01-222f-81f1-bd4b-d0383d39d47a`) with Session 43 handoff content:
   - Session 43 Summary (phone normalization from chat + QC enhancements + Delete Unwiring Agent + EAG merge from terminal)
   - Session 44 Priorities (configure Delete Unwiring automation triggers, Merge Agent design, remaining Parked Items)
   - Updated System Status
   - Updated Database Quick Reference (if any changes)

2. **Update Session — Archive** (`323adb01-222f-81dd-a175-c17d8fd8c71a`):
   - Add Session 43 summary line to the System Evolution Arc
   - Add detailed Session 43 entry under the appropriate phase heading

3. **Duplicate Session — Active** → move duplicate as child of Session — Archive.

4. **Overwrite Session — Active** with Session 44 handoff.

5. **Commit all local changes to main.**

---

## Parked Items (Updated — carry forward to Session 44)

These were captured during the S43 chat session and should appear in the S44 priorities or parked items:

- **Automation: Delete Unwiring Agent trigger** — Configure Notion DB automations on all 4 DBs to fire when Record Status → Delete. Instruction page exists (built this session); automation trigger is the follow-up.
- **Automation: Merge Agent** — DB automation or Action Item checkbox trigger that prompts Adam on how to merge a contact or company. Could use checkboxes in Action Items to batch-merge Tasks/Follow Ups.
- **QC: Past Due view cleanup** — Adam can now remove the manual OR filter from the Review view since Past Due is baked into QC.
- Additional notetaker profiles (Strategy/Workshop, 1:1/Check-in)
- Multi-source Action Items (email, voice memos — not just meetings)
- Meeting Series architecture review (separate DB?)
- Additional Calendar Expansion — Add second calendar source with hardened Calendar Name selection
