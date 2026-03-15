# Notion Workspace Automation

> This project lives at `ops/notion-workspace/` within the FreedSolutions repo.
> It manages Adam Freed's CRM and operations automation system built on Notion.

## First Steps — Every Session

1. **Read local docs** — `ops/notion-workspace/docs/agent-sops.md` is the stable workflow reference.
2. **Read the Active Session Handoff** via Notion MCP — page ID `323adb01-222f-81f1-bd4b-d0383d39d47a`.
3. **Use standing approval for routine Notion work.** Ask questions only if the request is ambiguous, destructive, schema-changing, or a bulk record operation.

## Local Docs

Local `docs/` files are the **source of truth** for instruction content. Each file maps to a Notion page.

| File | Notion Page ID | Purpose |
|------|---------------|---------|
| `docs/agent-sops.md` | `323adb01-222f-81d7-bc47-c32cfea460f4` | Agents, workflows, databases, schema conventions |
| `docs/notion-agent-config.md` | `321adb01-222f-8033-ad89-c3f889ae4dec` | Notion's built-in AI personality config |
| `docs/unified-post-meeting.md` | `324adb01-222f-8168-a207-d66e81884454` | Post-Meeting Agent: unified CRM wiring + action item parsing (replaces Agent 1 + Agent 2) |
| `docs/meeting-sync.md` | `321adb01-222f-81a7-8d9d-e02cd6e91ff9` | [DEPRECATED] Meeting Sync — replaced by Post-Meeting Agent (S37) |
| `docs/quick-sync.md` | `322adb01-222f-8196-99d8-c7f9a59cdb3b` | [DEPRECATED] Quick Sync — replaced by Post-Meeting Agent (S37) |
| `docs/post-meeting-wiring.md` | `321adb01-222f-81a3-8c57-d29c85ae7b63` | [DEPRECATED] Post-Meeting Wiring — replaced by Post-Meeting Agent (S37) |
| `docs/contact-company-review.md` | `323adb01-222f-8126-9db8-df77be5a326f` | Contact & Company Review after other syncs |
| `docs/merge-workflow.md` | `323adb01-222f-8111-89c7-c92eaac10ebb` | Merge/dedup workflows |
| `docs/floppy-design.md` | — | Floppy voice-command CRM agent design doc (local only) |
| `docs/notetaker-crm.md` | — | CRM-optimized Notion Calendar AI notetaker instructions (local only, paste into Calendar settings) |

## Notion-Only Resources (access via MCP)

| Resource | Type | ID |
|----------|------|----|
| Session — Active | Page | `323adb01-222f-81f1-bd4b-d0383d39d47a` |
| Session — Archive | Page | `323adb01-222f-81dd-a175-c17d8fd8c71a` |
| Agent Config | Database | `322adb01-222f-8114-b1b0-cc8971f1b61a` |
| Automation Hub | Page | `321adb01-222f-810f-8706-e53105950d86` |

## Database IDs

| Database | Data Source ID |
|----------|---------------|
| Contacts | `fd06740b-ea9f-401f-9083-ebebfb85653c` |
| Companies | `796deadb-b5f0-4adc-ac06-28e94c90db0e` |
| Action Items | `319adb01-222f-8059-bd33-000b029a2fdd` |
| Meetings | `31fadb01-222f-80c0-acf7-000b401a5756` |
| Agent Config | `322adb01-222f-8114-b1b0-cc8971f1b61a` |

**Adam's Notion User ID:** `30cd872b-594c-81b7-99dc-0002af0f255a`

## Rules of Engagement

1. **Read the Active Handoff FIRST** — it has full context for the current session.
2. **Standing approval applies to routine Notion work.** If Adam asks to update, sync, harden, document, or maintain the Notion workspace, execute the full read, edit, push, verify, and log loop without asking for step-by-step permission.
3. **Only pause for confirmation** when the task is ambiguous, destructive, schema-changing, touches Record Status, creates new CRM DB records, or is a migration/bulk operation.
4. **For migrations or bulk operations:** audit current state → present plan → get Adam's approval → execute in phases with verification between each.
5. **Never create new DB records** unless explicitly instructed.
6. **Never change Record Status** (Draft/Active/Inactive/Delete) without explicit instruction.
7. **Log everything** — the session handoff is the system of record.
8. **Dedup checks are mandatory** — always check Email + Secondary Email + Tertiary Email for contacts, Domains + Additional Domains for companies.

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

## Key Schema Conventions

- **Record Status** (select on Contacts, Companies, Action Items, Meetings): `Draft` → `Active` → `Inactive` → `Delete`
- **Contacts DB:** Contact Name (title), Display Name (formula), Wiring Check (formula), Email, Secondary Email, Tertiary Email, Phone, Pronouns, Nickname, LinkedIn, Company, Role / Title, Record Status, Contact Notes
- **Companies DB:** Company Name (title), Company Type (select: Tech Stack, Operator, Network, Personal), Wiring Check (formula), Domains, Additional Domains, States (default: "All"), Website, Contacts, Action Items, Engagements, Tech Stack, Record Status, Company Notes
- **Action Items DB:** Task Name (title), Type (formula), Icon (formula), Status, Priority, Record Status, Task Notes, Due Date, Assign Date (created_time), Contact, Company, Assignee, Source Meeting, Attach File, Wiring Check (formula)
- **Meetings DB:** Meeting Title (title), Calendar Event ID, Calendar Name, Date, Contacts, Companies (rollup), Action Items, Series, Instances, Is Series Parent, Location, Record Status
- **Email fields** (Contacts): Email, Secondary Email, Tertiary Email — all checked for dedup
- **Domain fields** (Companies): Domains (primary), Additional Domains (merged/subsidiary) — both checked for dedup
- **Delete handoff:** Claude sets Record Status = Delete + Notes field (Contact Notes / Company Notes / Task Notes) explaining why. Adam trashes from Delete view.
- **Agent Config:** Runtime state (timestamps) shared between agents. Not documentation — agents read/write during execution.

## End-of-Session Protocol

At the end of every session, use Notion MCP tools to:

1. Add session summary to **Session Archive** (`323adb01-222f-81dd-a175-c17d8fd8c71a`) — System Evolution Arc line + detailed entry.
2. Duplicate the Active Handoff → move the duplicate as a child page under Session Archive.
3. Overwrite the Active Handoff (`323adb01-222f-81f1-bd4b-d0383d39d47a`) with the next session's content (new summary, new priorities, updated schema).

## Sync Convention

- Local `docs/` files are the **source of truth** for instruction content.
- When instructions change, edit the local file first, then push to Notion via MCP in the same task unless Adam explicitly asks for a local-only draft.
- Ephemeral/runtime data (sessions, agent config, CRM records) lives in Notion only.
- To refresh a local doc from Notion: use MCP to read the page, overwrite the local file.

## Maintenance

When adding new agents, workflows, or databases, update all three:
1. The relevant doc in `ops/notion-workspace/docs/`
2. Agent SOPs in Notion (push from `docs/agent-sops.md`)
3. Notion Agent page (push from `docs/notion-agent-config.md`)
