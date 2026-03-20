# Notion Workspace Automation

> This project lives at `ops/notion-workspace/` within the FreedSolutions repo.
> It manages Adam Freed's CRM and operations automation system built on Notion.

## First Steps - Every Session

1. **Read the repo session handoff first** - `ops/notion-workspace/session-active.md` is the canonical active handoff for Claude Code and Codex work.
2. **Check the Notion Session - Active page only as a pointer or drift check** via MCP - page ID `323adb01-222f-81f1-bd4b-d0383d39d47a`.
3. **Read local docs** - `ops/notion-workspace/docs/agent-sops.md` is the stable workflow reference, then read the workflow-specific doc that matches the task.
4. **Use the repo Codex skills for manual workflows** - `ops/notion-workspace/skills/` is the canonical source for the manual operator layer.
5. **Use standing approval for routine Notion work.** Ask questions only if the request is ambiguous, destructive, schema-changing, or a bulk record operation.

## Local Docs

Local `docs/` files are the source of truth for instruction content. Each file maps to a Notion page.

| File | Notion Page ID | Purpose | Last Sync |
|------|---------------|---------|-----------|
| `docs/agent-sops.md` | `323adb01-222f-81d7-bc47-c32cfea460f4` | Canonical operating model: agents, workflows, schema, runtime baseline, and manual operator rules | 2026-03-20 |
| `docs/notion-agent.md` | `321adb01-222f-8033-ad89-c3f889ae4dec` | Supporting mirror for Notion's built-in AI persona. Not authoritative for triggers, schema, or workflow rules. | 2026-03-20 |
| `docs/post-meeting.md` | `324adb01-222f-8168-a207-d66e81884454` | Post-Meeting Agent: 4-step pipeline (CRM wiring -> Floppy -> Notes -> curated summary). Uses live `Calendar Name` options only. | 2026-03-20 |
| `docs/contact-company.md` | `323adb01-222f-8126-9db8-df77be5a326f` | Contact & Company Agent: nightly enrichment for Draft records plus Active QC gaps, with placeholder correction and backlog fairness rules | 2026-03-20 |
| `docs/merge-workflow.md` | `323adb01-222f-8111-89c7-c92eaac10ebb` | Merge and dedup workflows | 2026-03-20 |
| `docs/_floppy-design.md` | - | Floppy voice-command CRM agent design doc (local only) | - |
| `docs/notetaker-crm.md` | `324adb01-222f-80ca-af0a-cd455329d8e8` | Notetaker CRM: paste into Notion Calendar AI settings | S56 |
| `docs/delete-unwiring.md` | `325adb01-222f-8103-b4d9-d5ce67f21de5` | Delete Unwiring Agent: clears relations on `Record Status = Delete` records | S54 |
| `docs/curated-notes.md` | `325adb01-222f-8148-b544-f592271f34e3` | Curated Notes Agent: manual-only QA reviewer for meetings, email runs, and CRM drift audits | 2026-03-20 |
| `docs/post-email.md` | `325adb01-222f-81d3-825a-d3e0c74c0e30` | Post-Email Agent: Gmail sweep -> CRM wiring -> schema-safe action items -> thread summary with partial-run recovery | 2026-03-20 |
| `docs/claude-ai-context.md` | `325adb01-222f-8144-9c87-e0412a17d5ef` | Claude.ai planning context. Manual execution authority now sits with Claude Code + Codex skills. | 2026-03-20 |
| `docs/linkedin-messages.md` | `328adb01-222f-8134-941a-c78d757869d6` | LinkedIn Messages workflow: DM capture with timestamp recovery, safe identity matching, and thread updates | 2026-03-20 |
| `docs/test-playbooks.md` | - | Validation playbooks for agents, workflows, and Codex skill migration | 2026-03-20 |

## Codex Skills

Repo skill sources live under `ops/notion-workspace/skills/`. Installed copies belong in `~/.codex/skills`.

| Skill | Canonical Source | Purpose |
|------|------------------|---------|
| `notion-action-item` | `ops/notion-workspace/skills/notion-action-item/` | Work a single Action Item end-to-end from CRM wiring through delivery and approval |
| `notion-agent-config` | `ops/notion-workspace/skills/notion-agent-config/` | Audit or update Notion Custom Agent browser settings against the local spec |
| `notion-agent-test` | `ops/notion-workspace/skills/notion-agent-test/` | Run smoke and regression tests for Notion Custom Agents and workflows |

Publish or validate them with `ops/notion-workspace/scripts/publish-codex-skills.ps1`.

## Session Files

The repo is the canonical home for session handoff docs.

| File or Path | Purpose |
|--------------|---------|
| `ops/notion-workspace/session-active.md` | Canonical active handoff, priorities, and next actions |
| `ops/notion-workspace/session-archive/` | Archived handoff snapshots and session-history support files |

## Notion-Only Resources (access via MCP)

| Resource | Type | ID |
|----------|------|----|
| Session - Active | Page | `323adb01-222f-81f1-bd4b-d0383d39d47a` |
| Session - Archive | Page | `323adb01-222f-81dd-a175-c17d8fd8c71a` |
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
| Emails | `f685a378-5a37-4517-9b0c-d2928be4af4d` |

**Adam's Notion User ID:** `30cd872b-594c-81b7-99dc-0002af0f255a`

## Rules of Engagement

1. **Read the repo active handoff first** - `ops/notion-workspace/session-active.md` has the canonical current-session context.
2. **Standing approval applies to routine Notion work and its normal follow-through.** If Adam asks to update, sync, harden, test, document, maintain, commit, or push `ops/notion-workspace`, execute the full read, edit, push, verify, review, log, commit, and push loop without asking for step-by-step permission when the work stays inside the documented workflow.
3. **Only pause for confirmation** when the task is ambiguous, destructive, schema-changing, touches `Record Status` outside an explicitly documented workflow or test path, creates non-test CRM DB records, or is a migration/bulk operation.
4. **For migrations or bulk operations:** audit current state -> present plan -> get Adam's approval -> execute in phases with verification between each.
5. **Use repo skill sources for manual operator work.** Task-specific manual workflows belong in `ops/notion-workspace/skills/`, not in ad hoc slash-command notes.
6. **`docs/notion-agent.md` is not a workflow authority.** If it conflicts with `CLAUDE.md`, `docs/agent-sops.md`, or the workflow docs, the local operating docs win.
7. **Never create new CRM DB records** unless explicitly instructed, except bounded `[TEST]` records or disposable audit pages required by the documented playbooks.
8. **Never change `Record Status`** (`Draft`/`Active`/`Inactive`/`Delete`) without explicit instruction, except when the local workflow doc explicitly prescribes that exact bounded state transition as part of a validated run, cleanup step, or terminal no-op classification.
9. **Log everything** - the session handoff is the system of record.
10. **Dedup checks are mandatory** - always check Email + Secondary Email + Tertiary Email for contacts, Domains + Additional Domains for companies.
11. **UI steps require Adam's confirmation before marking complete.** Some tasks can only be done in the Notion UI (configuring agent triggers, pasting content too large for API, Settings changes). When a planning output or session priority includes a UI step: (a) explicitly list it as "Adam - UI step", (b) do NOT mark it complete until Adam confirms in the chat that it's done, (c) do not assume completion based on page existence or other indirect signals.
12. **Verify content on sync, not just existence.** When marking a Notion page as "in sync" with a local doc, verify the actual content matches - not just that the page exists.

## Standing Approval Scope

Routine Notion work is pre-authorized once Adam requests it. This includes:

- Reading mapped Notion pages and databases for context or verification
- Editing local `docs/` files and `ops/notion-workspace/CLAUDE.md`
- Pushing local instruction changes to their mapped Notion pages via MCP
- Updating the Active Session Handoff and Session Archive as part of normal session maintenance
- Updating `session-active.md`, archiving prior handoffs under `session-archive/`, and refreshing the Notion Session - Active pointer when helpful
- Adding logs, summaries, and verification notes needed to keep the workspace current
- Updating repo skill sources and validating them locally
- Running documented smoke and regression tests with `[TEST]` records or disposable audit pages, including bounded cleanup
- Applying safe runtime repairs that bring live agent settings, runtime state, or individual records back into alignment with the local workflow docs
- Staging, committing, and pushing `ops/notion-workspace` changes after validation and review, so long as unrelated work is not swept into the change

Pause and ask before proceeding only when any of the following are true:

- The request is ambiguous or conflicts with the local source-of-truth docs
- The change would modify database schema, views, automations, or agent architecture
- The change would create, merge, delete, or bulk-edit non-test CRM records
- The change would alter `Record Status` or other lifecycle controls outside the documented workflow or test path
- The operation is large enough that rollback would be difficult

## Key Schema Conventions

- **Record Status** (select on Contacts, Companies, Action Items, Meetings, Emails): `Draft` -> `Active` -> `Inactive` -> `Delete`
- **Contacts DB:** Contact Name (title), Display Name (formula), QC (formula), Email, Secondary Email, Tertiary Email, Phone, Pronouns, Nickname, LinkedIn, Company, Role / Title, Record Status, Contact Notes
- **Companies DB:** Company Name (title), Company Type (select: Tech Stack, Operator, Network, Personal), QC (formula), Domains, Additional Domains, States (default: "All"), Website, Contacts, Action Items, Engagements, Tech Stack, Record Status, Company Notes
- **Action Items DB:** Task Name (title), Type (formula), Status, Priority, Record Status, Task Notes, Due Date, Created Date (created_time), Contact, Company, Assignee, Source Meeting, Source Email, Attach File, QC (formula)
- **Meetings DB:** Meeting Title (title), Calendar Event ID, Calendar Name, Date, Contacts, Companies (rollup), Action Items, Series, Instances, Is Series Parent, Series Status (rollup), Location, Record Status, QC (formula)
- **Emails DB:** Email Subject (title), Thread ID, From, Direction (formula), Date, Contacts, Companies (rollup), Action Items, Labels (multi_select), Source (select: Email - Freed Solutions, Email - Personal, LinkedIn - DMs), Record Status, Email Notes, QC (formula), Created Timestamp
- **Email fields** (Contacts): Email, Secondary Email, Tertiary Email - all checked for dedup
- **Domain fields** (Companies): Domains (primary), Additional Domains (merged/subsidiary) - both checked for dedup
- **Calendar Name** currently has live select options for `Adam - Business` and `Adam - Personal` only. Do not assume local placeholders such as `Manual` or `Pending` exist in the schema.
- **Delete handoff:** Claude sets Record Status = Delete + Notes field (Contact Notes / Company Notes / Task Notes) explaining why. Adam trashes from Delete view.
- **Agent Config:** Runtime state (timestamps) shared between agents. Not documentation - agents read/write during execution.

## End-of-Session Protocol

At the end of every session, use Notion MCP tools to:

1. Add session summary to **Session Archive** (`323adb01-222f-81dd-a175-c17d8fd8c71a`) - System Evolution Arc line + detailed entry.
2. Duplicate the Active Handoff -> move the duplicate as a child page under Session Archive.
3. Overwrite the Active Handoff (`323adb01-222f-81f1-bd4b-d0383d39d47a`) with the next session's content (new summary, new priorities, updated schema).

## Sync Convention

- Local `docs/` files are the source of truth for instruction content.
- When instructions change, edit the local file first, then push to Notion via MCP in the same task unless Adam explicitly asks for a local-only draft.
- Ephemeral/runtime data (sessions, agent config, CRM records) lives in Notion only.
- To refresh a local doc from Notion: use MCP to read the page, overwrite the local file.
- Skill sources follow the same rule: edit the repo copy first, validate, then publish installed copies to `~/.codex/skills`.

## Codex Review Gate

For tasks that change local files in `ops/notion-workspace/`, use this order:

1. Edit the local source-of-truth files.
2. Push the mapped instruction docs to Notion via MCP when applicable.
3. Re-fetch the updated Notion pages and verify live content parity with the local docs.
4. Run the Codex review gate on the current worktree.
5. Only after the review passes or its findings are explicitly accepted, update `ops/notion-workspace/session-active.md` and any optional Notion pointer note.
6. Then commit and push to `main`.

Do **not** update the canonical handoff before the Codex review gate unless Adam explicitly asks for a draft note before review.

## Planning Output (Repo Handoff)

`ops/notion-workspace/session-active.md` may contain a **Planning Output** section from Claude.ai, Claude Code, or Codex. When present:

1. Read it during First Steps.
2. Execute the listed changes using standing approval when they are already approved.
3. Mark changes as done in the session log only after the Codex review gate passes (or Adam explicitly accepts the findings).

The repo handoff remains the canonical shared mechanism for Claude Code and Codex work. The Notion Session - Active page is an optional pointer or status mirror only.

## Current Follow-Up Queue (March 20, 2026)

Keep this queue aligned with `ops/notion-workspace/session-active.md`. Remove completed items instead of letting stale audit work linger.

### P1 - Observe the next scheduled Post-Email run

- Confirm bot-only or alias-only terminal threads remain `Inactive`
- Confirm those terminal threads do not create Contacts, Companies, or Action Items on reprocessing
- Confirm `Post-Email Agent Last Run` advances after a successful nightly run

### P2 - Run the next Post-Meeting regression slice

- Active trigger on a representative meeting
- Manual recovery path on a partially processed meeting
- Duplicate no-notes protection
- Live `Calendar Name` schema assumptions stay accurate

### P3 - Resolve LinkedIn workflow posture after service removal

- `ops/linkedin-crm-service` is gone from the repo; do not assume that old service still exists
- If the LinkedIn Messages workflow remains active, run one manual smoke and replace the Agent Config placeholder timestamp
- If the workflow is being retired, archive or remove the remaining LinkedIn runtime references instead of leaving a placeholder path behind

## Maintenance

When adding new agents, workflows, or databases, update:

1. The relevant doc in `ops/notion-workspace/docs/`
2. Agent SOPs in Notion (push from `docs/agent-sops.md`)
3. `docs/notion-agent.md` only if the high-level AI persona or operating posture changes

When changing a manual workflow skill:

1. Update the canonical repo skill under `ops/notion-workspace/skills/`
2. Validate it with `ops/notion-workspace/scripts/publish-codex-skills.ps1 -ValidateOnly`
3. Publish the installed copy to `~/.codex/skills`
