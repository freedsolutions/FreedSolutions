# Notion Workspace Automation

> This project lives at `ops/notion-workspace/` within the FreedSolutions repo.
> It manages Adam Freed's CRM and operations automation system built on Notion.

## First Steps — Every Session

1. **Read local docs** — `ops/notion-workspace/docs/agent-sops.md` is the stable workflow reference.
2. **Read the Active Session Handoff** via Notion MCP — page ID `323adb01-222f-81f1-bd4b-d0383d39d47a`.
3. **Ask clarification questions BEFORE making changes.**

## Local Docs

Local `docs/` files are the **source of truth** for instruction content. Each file maps to a Notion page.

| File | Notion Page ID | Purpose |
|------|---------------|---------|
| `docs/agent-sops.md` | `323adb01-222f-81d7-bc47-c32cfea460f4` | Agents, workflows, databases, schema conventions |
| `docs/notion-agent-config.md` | `321adb01-222f-8033-ad89-c3f889ae4dec` | Notion's built-in AI personality config |
| `docs/meeting-sync.md` | `321adb01-222f-81a7-8d9d-e02cd6e91ff9` | Agent 1: nightly 10 PM ET + manual |
| `docs/quick-sync.md` | `322adb01-222f-8196-99d8-c7f9a59cdb3b` | Manual calendar sync |
| `docs/post-meeting-wiring.md` | `321adb01-222f-81a3-8c57-d29c85ae7b63` | Agent 2: after meetings with AI notes |
| `docs/contact-company-review.md` | `323adb01-222f-8126-9db8-df77be5a326f` | Contact & Company Review after other syncs |
| `docs/merge-workflow.md` | `323adb01-222f-8111-89c7-c92eaac10ebb` | Merge/dedup workflows |

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
2. **Ask clarification questions BEFORE making changes.**
3. **For migrations or bulk operations:** audit current state → present plan → get Adam's approval → execute in phases with verification between each.
4. **Never create new DB records** unless explicitly instructed.
5. **Never change Record Status** (Draft/Active/Inactive/Delete) without explicit instruction.
6. **Log everything** — the session handoff is the system of record.
7. **Dedup checks are mandatory** — always check Email + Secondary Email + Tertiary Email for contacts, Domains + Additional Domains for companies.

## Key Schema Conventions

- **Record Status** (select on Contacts, Companies, Action Items): `Draft` → `Active` → `Inactive` → `Delete`
- **Email fields** (Contacts): Email, Secondary Email, Tertiary Email — all checked for dedup
- **Domain fields** (Companies): Domains (primary), Additional Domains (merged/subsidiary) — both checked for dedup
- **Delete handoff:** Claude sets Record Status = Delete + Notes explaining why. Adam trashes from Delete view.
- **Agent Config:** Runtime state (timestamps) shared between agents. Not documentation — agents read/write during execution.

## End-of-Session Protocol

At the end of every session, use Notion MCP tools to:

1. Add session summary to **Session Archive** (`323adb01-222f-81dd-a175-c17d8fd8c71a`) — System Evolution Arc line + detailed entry.
2. Duplicate the Active Handoff → move the duplicate as a child page under Session Archive.
3. Overwrite the Active Handoff (`323adb01-222f-81f1-bd4b-d0383d39d47a`) with the next session's content (new summary, new priorities, updated schema).

## Sync Convention

- Local `docs/` files are the **source of truth** for instruction content.
- When instructions change, edit the local file first, then push to Notion via MCP.
- Ephemeral/runtime data (sessions, agent config, CRM records) lives in Notion only.
- To refresh a local doc from Notion: use MCP to read the page, overwrite the local file.

## Maintenance

When adding new agents, workflows, or databases, update all three:
1. The relevant doc in `ops/notion-workspace/docs/`
2. Agent SOPs in Notion (push from `docs/agent-sops.md`)
3. Notion Agent page (push from `docs/notion-agent-config.md`)
