# Notion Workspace Automation

> This project lives at `ops/notion-workspace/` within the FreedSolutions repo.
> It manages Adam Freed's CRM and operations automation system built on Notion.

## First Steps - Every Session

1. **Read the repo session handoff first** - `ops/notion-workspace/session-active.md` is the canonical active handoff for Claude Code and Codex work.
2. **Read local docs** - `ops/notion-workspace/docs/agent-sops.md` is the stable workflow reference, then read the workflow-specific doc that matches the task.
3. **Use the repo Codex skills for manual workflows** - `ops/notion-workspace/skills/` is the canonical source for the manual operator layer.
4. **Use standing approval for routine Notion work.** Ask questions only if the request is ambiguous, destructive, schema-changing, or a bulk record operation.

## Local Docs

Local `docs/` files are the source of truth for instruction content. Most workflow docs map to Notion instruction pages; local-only fallback and test docs stay in the repo.

For every doc that maps to a live Notion page, keep a visible banner directly under the H1:
`> Live Notion doc. This repo file is the source of truth for the mapped Notion page. Sync local changes to Notion in the same task.`

| File | Notion Page ID | Purpose | Last Sync |
|------|---------------|---------|-----------|
| `docs/agent-sops.md` | `323adb01-222f-81d7-bc47-c32cfea460f4` | Canonical operating model: agents, workflows, schema, runtime baseline, and manual operator rules | 2026-03-21 |
| `docs/post-meeting.md` | `324adb01-222f-8168-a207-d66e81884454` | Post-Meeting Agent: 4-step pipeline (CRM wiring -> Floppy -> Notes -> curated summary). Uses live `Calendar Name` options only. | 2026-03-21 |
| `docs/contact-company.md` | `323adb01-222f-8126-9db8-df77be5a326f` | Contact & Company Agent: nightly enrichment for Draft records plus Active QC gaps, with placeholder correction and backlog fairness rules | 2026-03-20 |
| `docs/merge-workflow.md` | `323adb01-222f-8111-89c7-c92eaac10ebb` | Merge and dedup workflows | 2026-03-20 |
| `docs/floppy-design.md` | - | Floppy voice-command CRM agent design doc (local only) | - |
| `docs/notetaker-crm.md` | `324adb01-222f-80ca-af0a-cd455329d8e8` | Notetaker CRM: paste into Notion Calendar AI settings | S56 |
| `docs/delete-unwiring.md` | `325adb01-222f-8103-b4d9-d5ce67f21de5` | Delete Unwiring Agent: clears relations on `Record Status = Delete` records | S54 |
| `docs/curated-notes.md` | `325adb01-222f-8148-b544-f592271f34e3` | Curated Notes Agent: manual-only QA reviewer for meetings, email runs, and CRM drift audits | 2026-03-20 |
| `docs/post-email.md` | `325adb01-222f-81d3-825a-d3e0c74c0e30` | Post-Email Agent: Gmail sweep -> CRM wiring -> schema-safe action items -> thread summary with partial-run recovery | 2026-03-21 |
| `docs/linkedin-messages.md` | - | Local-only fallback for manual LinkedIn DM recovery when notification-email intake is insufficient | - |
| `docs/test-playbooks.md` | - | Validation playbooks for agents, workflows, and Codex skill migration | - |

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

## Notion-Only Resources (access via MCP)

| Resource | Type | ID |
|----------|------|----|
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
6. **Never create new CRM DB records** unless explicitly instructed, except bounded `[TEST]` records or disposable audit pages required by the documented playbooks.
7. **Never change `Record Status`** (`Draft`/`Active`/`Inactive`/`Delete`) without explicit instruction, except when the local workflow doc explicitly prescribes that exact bounded state transition as part of a validated run, cleanup step, or terminal no-op classification.
8. **Log everything** - `ops/notion-workspace/session-active.md` is the session system of record.
9. **Dedup checks are mandatory** - always check Email + Secondary Email + Tertiary Email for contacts, Domains + Additional Domains for companies.
10. **UI steps require Adam's confirmation before marking complete.** Some tasks can only be done in the Notion UI (configuring agent triggers, pasting content too large for API, Settings changes). When a planning output or session priority includes a UI step: (a) explicitly list it as "Adam - UI step", (b) do NOT mark it complete until Adam confirms in the chat that it's done, (c) do not assume completion based on page existence or other indirect signals.
11. **Verify content on sync, not just existence.** When marking a Notion page as "in sync" with a local doc, verify the actual content matches - not just that the page exists.

## Standing Approval Scope

Routine Notion work is pre-authorized once Adam requests it. This includes:

- Reading mapped Notion pages and databases for context or verification
- Editing local `docs/` files and `ops/notion-workspace/CLAUDE.md`
- Pushing local instruction changes to their mapped Notion pages via MCP
- Updating `session-active.md` as part of normal session maintenance
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
- **Companies DB:** Company Name (title), Company Type (select: Tech Stack, Operator, Network, Personal), QC (formula), Domains, Additional Domains, States (default: "All"), Website, Contacts, Emails (rollup), Meetings (rollup), Action Items, Engagements, Tech Stack, Record Status, Company Notes
- **Action Items DB:** Task Name (title), Type (formula), Status, Priority, Record Status, Task Notes, Due Date, Created Date (created_time), Contact, Company, Assignee, Source Meeting, Source Email, Attach File, QC (formula)
- **Meetings DB:** Meeting Title (title), Calendar Event ID, Calendar Name, Date, Contacts, Companies (rollup), Action Items, Series, Instances, Is Series Parent, Series Status (rollup), Location, Record Status, QC (formula)
- **Emails DB:** Email Subject (title), Thread ID, From, Direction (formula), Date, Contacts, Companies (rollup), Action Items, Labels (multi_select), Source (select: Email - Freed Solutions, Email - Personal, LinkedIn - DMs), Record Status, Email Notes, QC (formula), Created Timestamp
- **Email routing labels:** On `adam@freedsolutions.com`, `Primitiv/PRI_Outlook` = forwarded Outlook intake, `Primitiv/PRI_Teams` = Teams notification intake, `LinkedIn` = LinkedIn message-notification intake, `DMC/DMC_GMail` = DMC routed company-mail intake. `Action Items` and any `Action Items/...` sublabel are temporary ignore labels for manual filing, not active intake lanes. Other company or project labels are metadata only unless explicitly promoted into routing. Labels are the canonical intake-route truth for the Freed Solutions mailbox. `adamjfreed@gmail.com` remains in live sweep scope, but its labels are out of scope for routing. Teams notifications currently keep the mailbox-derived `Source` until the live schema gains a dedicated Teams option.
- **Email fields** (Contacts): Email, Secondary Email, Tertiary Email - all checked for dedup
- **Domain fields** (Companies): Domains (primary), Additional Domains (merged/subsidiary) - both checked for dedup
- **Calendar Name** currently has live select options for `Adam - Business` and `Adam - Personal` only. Do not assume local placeholders such as `Manual` or `Pending` exist in the schema.
- **Delete handoff:** Claude sets Record Status = Delete + Notes field (Contact Notes / Company Notes / Task Notes) explaining why. Adam trashes from Delete view.
- **Agent Config:** Runtime state (timestamps) shared between agents. Not documentation - agents read/write during execution.

## End-of-Session Protocol

At the end of every session:

1. Update `ops/notion-workspace/session-active.md` with the next handoff.
2. Rely on git history as the session archive unless Adam explicitly wants a named snapshot file.
3. Retire or refresh any legacy Notion session pages only if that reduces confusion in the live workspace.

## Sync Convention

- Local `docs/` files are the source of truth for instruction content.
- When instructions change, edit the local file first, then push to Notion via MCP in the same task unless Adam explicitly asks for a local-only draft.
- Ephemeral/runtime data (agent config, CRM records, live automation state) lives in Notion only.
- To refresh a local doc from Notion: use MCP to read the page, overwrite the local file.
- Skill sources follow the same rule: edit the repo copy first, validate, then publish installed copies to `~/.codex/skills`.

## Codex Review Gate

For tasks that change local files in `ops/notion-workspace/`, use this order:

1. Edit the local source-of-truth files.
2. Push the mapped instruction docs to Notion via MCP when applicable.
3. Re-fetch the updated Notion pages and verify live content parity with the local docs.
4. Run the Codex review gate on the current worktree.
5. Only after the review passes or its findings are explicitly accepted, update `ops/notion-workspace/session-active.md`.
6. Then commit and push to `main`.

Do **not** update the canonical handoff before the Codex review gate unless Adam explicitly asks for a draft note before review.

## Planning Output (Repo Handoff)

`ops/notion-workspace/session-active.md` may contain a **Planning Output** section from Claude Code or Codex. When present:

1. Read it during First Steps.
2. Execute the listed changes using standing approval when they are already approved.
3. Mark changes as done in the session log only after the Codex review gate passes (or Adam explicitly accepts the findings).

The repo handoff remains the canonical shared mechanism for Claude Code and Codex work.

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

### P3 - Unify chat-notification intake under Post-Email

- Keep routed Gmail labels aligned with the workflow: `Primitiv/PRI_Outlook`, `Primitiv/PRI_Teams`, `LinkedIn`, and `DMC/DMC_GMail`
- Teach Post-Email to treat Teams and LinkedIn notifications as bot wrappers around human conversations, not bot-only terminal mail
- Keep `docs/linkedin-messages.md` as a manual fallback only for recovery or backfill when notification email content is insufficient
- Keep `adamjfreed@gmail.com` in live sweep scope while leaving its labels out of routing until Adam explicitly adds a personal-mailbox routing contract
- Long-term cleanup: add deterministic Gmail labels to every stable source or known domain so routing can converge toward fully automated inbox-zero handling

## Maintenance

When adding new agents, workflows, or databases, update:

1. The relevant doc in `ops/notion-workspace/docs/`
2. Agent SOPs in Notion (push from `docs/agent-sops.md`)

When changing a manual workflow skill:

1. Update the canonical repo skill under `ops/notion-workspace/skills/`
2. Validate it with `ops/notion-workspace/scripts/publish-codex-skills.ps1 -ValidateOnly`
3. Publish the installed copy to `~/.codex/skills`
