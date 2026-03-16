# Claude.ai Context

<!-- Notion Page ID: 325adb01-222f-8144-9c87-e0412a17d5ef -->

Lightweight CLAUDE.md equivalent for Claude.ai chat sessions. Read by the `notion-session` skill to orient Claude before planning work.

Local source-of-truth: `docs/claude-ai-context.md` (repo). Keep the Notion page in sync when the local file changes.

Last synced: Session 51 (March 16, 2026)

---

# Workspace Context

This workspace is a CRM and operations automation system for **Freed Solutions** (cannabis consulting). The system is managed through a structured session workflow with Claude and documented in the Automation Hub.

**Interfaces:**
- **Claude Code (terminal)** — executes code changes via `/notion` slash command. Reads local `CLAUDE.md` automatically.
- **Claude.ai (chat)** — plans and discusses changes. Reads this page via the `notion-session` skill.

Both interfaces share the same Session — Active page as the handoff mechanism.

**Owner:** Adam Freed
**Notion User ID:** `30cd872b-594c-81b7-99dc-0002af0f255a`

---

# Key Pages

| Page | ID | Purpose |
|---|---|---|
| Automation Hub | `321adb01-222f-810f-8706-e53105950d86` | Root page for all agent config and instructions |
| Agent SOPs | `323adb01-222f-81d7-bc47-c32cfea460f4` | Living reference — agents, workflows, schema, rules |
| Session — Active | `323adb01-222f-81f1-bd4b-d0383d39d47a` | Current session handoff (overwritten each session) |
| Session — Archive | `323adb01-222f-81dd-a175-c17d8fd8c71a` | System Evolution Arc + session snapshots |
| Agent Config | `322adb01-222f-8114-b1b0-cc8971f1b61a` | Runtime state (Last Successful Run timestamp) |
| Post-Meeting Instructions | `324adb01-222f-8168-a207-d66e81884454` | Post-Meeting Agent (4-step: CRM wiring → Floppy → AI parse → GCal sync) |
| Contact & Company Instructions | `323adb01-222f-8126-9db8-df77be5a326f` | Enrichment agent for Draft contacts/companies |
| Delete Unwiring Instructions | `325adb01-222f-8103-b4d9-d5ce67f21de5` | Clears relations before hard delete |
| Curated Notes Instructions | `325adb01-222f-8148-b544-f592271f34e3` | Curated meeting summary (trigger: Record Status → Active) |
| Post-Email Instructions | `325adb01-222f-81d3-825a-d3e0c74c0e30` | Post-Email Agent (4-step: Gmail sweep → CRM wiring → AI parse → summary) |
| CRM-Optimized Notetaker | `324adb01-222f-80ca-af0a-cd455329d8e8` | Notetaker profile for Notion Calendar AI |

---

# Database Quick Reference

| Database | Data Source ID | Icon |
|---|---|---|
| Contacts | `fd06740b-ea9f-401f-9083-ebebfb85653c` | 👤 |
| Companies | `796deadb-b5f0-4adc-ac06-28e94c90db0e` | 💼 |
| Action Items | `319adb01-222f-8059-bd33-000b029a2fdd` | ✅ |
| Meetings | `31fadb01-222f-80c0-acf7-000b401a5756` | 📅 |
| Agent Config | `322adb01-222f-8114-b1b0-cc8971f1b61a` | ⚙️ |
| Emails | `f685a378-5a37-4517-9b0c-d2928be4af4d` | 📧 |

**Record Status** (all 5 source DBs): Draft → Active → Inactive → Delete

**QC formula** (all 4 DBs): `TRUE` (pass) / `missing:fieldname` (fail) / `wired:PropertyName` (Delete-safe check) / `past_due` (Action Items only)

---

# Agent Registry

| Agent | Trigger | Status |
|---|---|---|
| Post-Meeting Agent | Nightly 10 PM ET + reactive (Meeting Title update) | Live |
| Contact & Company Review | Manual | Active (manual) |
| Delete Unwiring Agent | Manual (automation pending) | Active (manual) |
| Curated Notes Agent | Record Status → Active (Meetings DB) | Live |
| Post-Email Agent | Nightly ~10:30 PM ET (after Post-Meeting Agent) | Live |

**Model:** Opus 4.6 (all agents)

---

# Rules of Engagement (Chat Mode)

These rules apply to Claude.ai planning sessions:

1. **Read the Active handoff FIRST** — it has current priorities and system status.
2. **Planning mode by default.** Present the briefing, ask what to tackle, discuss before recommending execution.
3. **Code changes are planned here, executed in Claude Code.** When a plan is finalized, update the Session — Active page with the plan so Claude Code can pick it up.
4. **Only pause for confirmation** when the task is ambiguous, destructive, schema-changing, touches lifecycle state, creates new DB records, or is a migration/bulk operation.
5. **Never create new DB records** unless explicitly instructed.
6. **Never change lifecycle state** (Record Status) without explicit instruction.
7. **Fetch instruction pages on demand** — if discussing a specific agent, fetch its instruction page for full context rather than working from memory.
8. **UI steps require Adam's confirmation before marking complete.** Some tasks can only be done in the Notion UI (configuring agent triggers, pasting large content, Settings changes). When a planning output includes a UI step: (a) explicitly tag it as "Adam — UI step", (b) do NOT mark it complete until Adam confirms, (c) do not assume completion from indirect signals like page existence.
9. **Verify content on sync, not just existence.** When marking a page as "in sync" with a local doc, verify content matches — not just that the page exists.

**What Claude.ai CAN do directly:**
- Fetch and read any Notion page for review
- Search Notion workspace for context
- Draft instruction page content, agent designs, schema changes
- Update the Session Active page with new priorities
- Light Notion edits (updating text, appending notes) when appropriate

**What should go to Claude Code:**
- Multi-file local doc changes + git commits
- Bulk Notion operations (migrations, sweeps)
- Agent instruction page rewrites (local source-of-truth → push to Notion)
- Schema changes requiring formula updates

---

# Local Docs ↔ Notion Mapping

| Local File | Notion Page ID | Notes |
|---|---|---|
| `docs/agent-sops.md` | `323adb01-222f-81d7-bc47-c32cfea460f4` | Agent Registry, schema conventions |
| `docs/post-meeting.md` | `324adb01-222f-8168-a207-d66e81884454` | Post-Meeting Agent instructions |
| `docs/curated-notes.md` | `325adb01-222f-8148-b544-f592271f34e3` | Curated Notes Agent instructions |
| `docs/delete-unwiring.md` | `325adb01-222f-8103-b4d9-d5ce67f21de5` | Delete Unwiring Agent instructions |
| `docs/contact-company.md` | `323adb01-222f-8126-9db8-df77be5a326f` | Contact & Company Agent instructions |
| `docs/notetaker-crm.md` | `324adb01-222f-80ca-af0a-cd455329d8e8` | CRM-Optimized notetaker profile |
| `docs/post-email.md` | `325adb01-222f-81d3-825a-d3e0c74c0e30` | Post-Email Agent instructions |
| `docs/claude-ai-context.md` | `325adb01-222f-8144-9c87-e0412a17d5ef` | This file — Claude.ai planning context |

Local docs are the source of truth. Push changes to Notion after editing locally.

---

# Maintenance

Update this page whenever:
- A new agent is added → update Agent Registry table
- A new database is created → update Database Quick Reference
- A new local doc mapping is established → update Local Docs table
- Planning rules evolve → update Rules of Engagement section
- Session workflow changes → update as needed
