<!-- Notion Page ID: 323adb01-222f-81d7-bc47-c32cfea460f4 -->
# Agent SOPs

The living reference document for Adam's Notion workspace automation system. Used by both Adam and Claude (in any interface — chat, Claude Code terminal, or Claude App) to maintain continuity across sessions.

Last updated: Session 32 (March 14, 2026)

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

| Agent | Trigger | URL |
| --- | --- | --- |
| Meeting Sync | Nightly 10 PM ET + manual | Untitled |
| Post-Meeting Wiring | After meetings with AI notes | Untitled |
| Quick Sync | Manual trigger | Untitled |
| Contact & Company Review | Manual (after other syncs) | Untitled |

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

All 3 source DBs (Contacts, Companies, Action Items) use a single `Record Status` select with 4 options:

- **Draft** (gray) — Agent-created, pending Adam's review
- **Active** (green) — Approved and live, operational record
- **Inactive** (yellow) — Soft-deleted (deactivated duplicates, merged placeholders)
- **Delete** (red) — Flagged for Adam to hard-delete from Notion

Migrated from Approved + Active checkboxes in Session 32. Agents set new records to Draft. Only Adam moves records to Active. Agents may set records to Inactive or Delete per merge/dedup workflows.

## Email Fields (Contacts)

- **Email** — primary business email (used for calendar matching and dedup)
- **Secondary Email** — alternate email (personal, old domain, etc.)
- **Tertiary Email** — third email if needed
- All agent dedup rules must check ALL email fields

## Domain Fields (Companies)

- **Domains** — primary business domains (comma-separated, no spaces). Used for agent matching: email domain → company lookup
- **Additional Domains** — merged/subsidiary/alternate domains (comma-separated, no spaces, domains only — no full email addresses)
- All agent dedup rules must check BOTH domain fields

## Delete Handoff Pattern

Claude (in any interface) cannot archive/trash individual Notion pages via MCP tools. When a record needs to be deleted:

1. Claude sets Record Status = Delete
2. Claude adds a Notes flag explaining why (e.g., "MERGED → Formul8. Ready for HARD DELETE per merge workflow")
3. Adam periodically sweeps the Inactive/Delete view and trashes flagged records

---

# Rules of Engagement

These apply to every Claude session, regardless of interface:

1. **Read the Active handoff FIRST** — it has everything needed for context
2. **Ask clarification questions BEFORE making changes**
3. **For migrations or bulk operations:** audit current state → present plan → get Adam's approval → execute in phases with verification
4. **Never create new DB records** unless explicitly instructed
5. **Never change lifecycle state** (Approved/Active/Record Status) without explicit instruction
6. **Log everything** — the session handoff is the system of record
7. **Dedup checks are mandatory** — always check Email + Secondary Email + Tertiary Email for contacts, Domains + Additional Domains for companies

---

# Maintenance

This document should be updated whenever:

- A new agent instruction page is created → add to Agent Registry table
- A new workflow document is created → add to Workflow Documents table
- A new database is created → add to Database Quick Reference table
- Schema conventions change (e.g., Record Status migration) → update Schema Conventions section
- Rules of engagement evolve → update Rules section
- The kickoff prompt needs adjustment → update `CLAUDE.md` in the project repo
