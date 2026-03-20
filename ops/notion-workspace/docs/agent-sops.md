<!-- Notion Page ID: 323adb01-222f-81d7-bc47-c32cfea460f4 -->

# Agent SOPs

The canonical operating spec for Adam's Notion workspace automation system.

Last synced: Session 62 (March 20, 2026)

---

# Operating Model

Claude Code plus repo-backed Codex skills is the primary manual execution surface. Notion Custom Agents are bounded automation workers for scheduled or reactive workflows. Use the local docs in `ops/notion-workspace/docs/` as the source of truth and keep the mapped Notion instruction pages in sync with them.

Authority split:

- `docs/agent-sops.md`: canonical workflow, trigger, permission, schema, and session rules
- `CLAUDE.md`: bootstrap and execution contract for repo work
- `docs/claude-ai-context.md`: optional planning companion for chat surfaces
- `docs/notion-agent.md`: high-level mirror only, not the operational source of truth

---

# Session Management

## How Sessions Work

Each work session shares the same two Notion pages:

- Session - Active
- Session - Archive

The Active page contains the current handoff, priorities, and known runtime state. The Archive page holds the system evolution log plus snapshot pages from prior sessions.

## End-Of-Session Protocol

At the end of every session:

1. Append the one-line evolution note to Session - Archive.
2. Duplicate Session - Active and move the copy under Session - Archive.
3. Overwrite Session - Active with the next handoff.

## Starting A New Session

1. Read Session - Active.
2. Read `CLAUDE.md`.
3. Read `docs/agent-sops.md`.
4. Read any directly relevant workflow doc or skill source.

---

# Agent Registry

| Agent | Instruction Page | Trigger | Model | Status | Settings URL |
| --- | --- | --- | --- | --- | --- |
| Post-Meeting Agent | Post-Meeting Instructions | Nightly 10 PM ET + `Record Status = Active` on Meetings + `@mention` | Opus 4.6 | Live | [Settings](https://www.notion.so/agent/321adb01222f805f8182009253dc57a7?wfv=settings) |
| Post-Email Agent | Post-Email Instructions | Nightly 10:30 PM ET + `@mention` | Opus 4.6 | Live | [Settings](https://www.notion.so/agent/325adb01222f806da7960092bc6484d3?wfv=settings) |
| Contact & Company Agent | Contact & Company Instructions | Nightly 11 PM ET + `@mention` | Opus 4.6 | Live | [Settings](https://www.notion.so/agent/323adb01222f802cb5640092af74e84a?wfv=settings) |
| Delete Unwiring Agent | Delete Unwiring Instructions | `Record Status = Delete` on Meetings, Companies, Action Items, Contacts, and Emails + `@mention` | Opus 4.6 | Live | [Settings](https://www.notion.so/agent/325adb01222f80d2844a0092e63da4ea?wfv=settings) |
| Curated Notes Agent | Curated Notes Instructions | `@mention` only | Opus 4.6 | Active (manual QA reviewer) | [Settings](https://www.notion.so/agent/325adb01222f802e91290092cb71c17d?wfv=settings) |
| Meeting Sync | [DEPRECATED] Meeting Sync Instructions | Disabled | - | Deprecated | - |
| Post-Meeting Wiring | [DEPRECATED] Post-Meeting Wiring Instructions | Disabled | - | Deprecated | - |
| Quick Sync | [DEPRECATED] Quick Sync Instructions | Disabled | - | Deprecated | - |

Naming conventions:

- Custom Agent in Notion settings: `[Agent Name]`
- Instruction page in Notion: `[Short Name] Instructions`
- Local doc: `docs/[kebab-case].md`
- Skill source: `skills/[skill-name]/`

---

# Manual Workflows And Skills

## Workflow Docs

| Workflow | Purpose | URL |
| --- | --- | --- |
| LinkedIn Messages | Capture LinkedIn DMs into CRM via manual browser workflow | [LinkedIn Messages Instructions](https://www.notion.so/328adb01222f8134941ac78d757869d6) |
| Merge Workflow | Merge duplicates and run delete-safe cleanup | [Merge Workflow](https://www.notion.so/323adb01222f811189c7c92eaac10ebb) |

## Codex Skills

| Skill | Source Path | Purpose |
| --- | --- | --- |
| `notion-action-item` | `ops/notion-workspace/skills/notion-action-item/` | Execute a single Action Item end to end |
| `notion-agent-config` | `ops/notion-workspace/skills/notion-agent-config/` | Audit or update Custom Agent settings |
| `notion-agent-test` | `ops/notion-workspace/skills/notion-agent-test/` | Run agent and workflow tests |

Skill publish workflow:

1. Edit the canonical skill source in the repo.
2. Validate with `ops/notion-workspace/scripts/publish-codex-skills.ps1 -ValidateOnly`.
3. Publish to `~/.codex/skills` with `ops/notion-workspace/scripts/publish-codex-skills.ps1`.

---

# Trigger Configuration Reference

This section is the canonical desired state for Notion Custom Agent settings.

## Post-Meeting Agent

- Triggers:
  - Daily 10 PM ET
  - Meetings property trigger: `Record Status = Active`
  - `page-content-edit`: unchecked
  - `@mention`
- Notion page access:
  - Meetings -> Can edit content
  - Action Items -> Can edit content
  - Contacts -> Can edit content
  - Companies -> Can edit content
  - Agent Config -> Can edit
  - Post-Meeting Instructions -> Can edit
  - Agent SOPs -> Can view
- Connections:
  - Calendar: Adam - Business (Read), Adam - Personal (Read)
  - Mail: `adam@freedsolutions.com` (Read)
  - Web access: On
- Model: Opus 4.6
- Notes:
  - GCal sync-back is retired.
  - Manual `@mention` is for targeted rewiring, recovery, or explicitly requested curation on an already Active meeting.
  - Curated summary generation remains inside Post-Meeting, but the separate Curated Notes Agent now serves as the manual QA reviewer.

## Post-Email Agent

- Triggers:
  - Daily 10:30 PM ET
  - `@mention`
- Notion page access:
  - Post-Email Instructions -> Can edit
  - Emails -> Can edit content
  - Contacts -> Can edit content
  - Companies -> Can edit content
  - Action Items -> Can edit content
  - Agent Config -> Can edit
  - Agent SOPs -> Can view
- Connections:
  - Mail: `adam@freedsolutions.com` and `adamjfreed@gmail.com`
  - Current runtime scope may include inbox-modify and draft permissions. Workflow behavior remains read-heavy and must not send mail.
  - Web access: Off
  - No calendar access
- Model: Opus 4.6
- Notes:
  - Existing stubs must be eligible for recovery if prior runs stopped after partial work.
  - Bot-only threads may be summarized and skipped without creating CRM wiring or action items.
  - Runtime audit on March 20, 2026 found a revoked Notion-access entry where Agent Config should be. Repair the live page access if timestamps stop updating.

## Curated Notes Agent

- Triggers:
  - `@mention`
  - Property trigger: Off
- Notion page access:
  - Meetings -> Can edit content
  - Emails -> Can edit content
  - Action Items -> Can edit content
  - Contacts -> Can view
  - Companies -> Can view
  - Agent Config -> Can edit
  - Curated Notes Instructions -> Can edit
  - Agent SOPs -> Can view
- Connections:
  - Calendar: Read only
  - Web access: On
  - No mail required by default
- Model: Opus 4.6
- Role contract:
  - Manual QA reviewer
  - Audit and report first
  - No new CRM records by default
  - No `Record Status` changes by default
  - No bulk repair unless explicitly requested in the prompt

## Contact & Company Agent

- Triggers:
  - Daily 11 PM ET
  - `@mention`
- Notion page access:
  - Contact & Company Instructions -> Can edit
  - Companies -> Can edit content
  - Contacts -> Can edit content
  - Agent Config -> Can edit
  - Agent SOPs -> Can view
- Connections:
  - Web access: On
  - Calendar: Read only
  - Mail runtime may currently allow broader mailbox scope than the workflow needs. The workflow must not send mail or mutate inbox state as part of enrichment.
- Model: Opus 4.6
- Notes:
  - Queue fairness matters. Old Draft and QC-gap records must not starve behind newer ones.
  - Placeholder correction is allowed when evidence is stronger than the placeholder default.

## Delete Unwiring Agent

- Triggers:
  - Meetings property trigger: `Record Status = Delete`
  - Companies property trigger: `Record Status = Delete`
  - Action Items property trigger: `Record Status = Delete`
  - Contacts property trigger: `Record Status = Delete`
  - Emails property trigger: `Record Status = Delete`
  - `page-content-edit`: unchecked on all
  - `@mention`
- Notion page access:
  - Delete Unwiring Instructions -> Can edit
  - Meetings -> Can edit content
  - Companies -> Can edit content
  - Action Items -> Can edit content
  - Contacts -> Can edit content
  - Emails -> Can edit content
  - Agent Config -> Can edit
  - Agent SOPs -> Can view
- Connections:
  - Web access: Off
  - No calendar
  - No mail
- Model: Opus 4.6

---

# Database Quick Reference

| Database | Data Source ID |
| --- | --- |
| Contacts | `fd06740b-ea9f-401f-9083-ebebfb85653c` |
| Companies | `796deadb-b5f0-4adc-ac06-28e94c90db0e` |
| Action Items | `319adb01-222f-8059-bd33-000b029a2fdd` |
| Meetings | `31fadb01-222f-80c0-acf7-000b401a5756` |
| Agent Config | `322adb01-222f-8114-b1b0-cc8971f1b61a` |
| Emails | `f685a378-5a37-4517-9b0c-d2928be4af4d` |

**Adam's Notion User ID:** `30cd872b-594c-81b7-99dc-0002af0f255a`

## Meetings DB Automation

There is a Notion database automation, not a Custom Agent, on page creation in Meetings:

- set `Record Status` to `Draft`
- set the page icon to `🗓️`

---

# Schema Conventions

## Lifecycle State

All five source databases use the same `Record Status` select:

- `Draft`
- `Active`
- `Inactive`
- `Delete`

Only Adam promotes records to `Active`. Agents create Draft records and may participate in delete-safe cleanup only when explicitly instructed by the workflow.

## Contacts

- Dedup across `Email`, `Secondary Email`, and `Tertiary Email`
- `Company` is the primary operational relation
- `LinkedIn`, `Phone`, `Pronouns`, and `Role / Title` are fill-in fields and may be updated by enrichment workflows

## Companies

- `Domains` holds primary operational domains
- `Additional Domains` holds merged, subsidiary, alternate, or legacy domains
- Both domain fields are used for matching and dedup
- Placeholder companies default to `States = All`, but enrichment may replace that placeholder value when stronger evidence exists

## Meetings

- `Calendar Event ID` is the canonical event identity
- `Calendar Name` is a select with current live options:
  - `Adam - Business`
  - `Adam - Personal`
- If a meeting cannot yet be matched to a configured calendar, leave `Calendar Name` blank and log the recovery state instead of inventing a non-existent select option

## Action Items

- Every Action Item should have a reliable `Company` whenever a trustworthy fallback exists
- `Due Date` should be set whenever the source text contains an explicit or relative deadline that can be resolved

## Emails

- `Thread ID` is the canonical email-thread identity
- `Source` must be populated
- Existing email stubs may be healed in place when prior runs only completed part of the workflow

---

# Rules Of Engagement

1. Read Session - Active first, then the canonical local docs.
2. Standing approval applies to routine Notion work once Adam requests it.
3. Pause only for ambiguity, destructive actions, schema changes, lifecycle changes, new CRM record creation outside a documented workflow, or large migrations.
4. Never create duplicate CRM records.
5. Never change `Record Status` outside the explicit workflow rules or Adam's direct instruction.
6. Verify live parity after pushing a local doc to Notion.
7. Keep docs, skills, and runtime behavior aligned. Do not accept silent drift as normal.

## Kickoff Conventions

Claude Code is the default execution surface. Start from the repo and use the skill source that best fits the task.

- For Action Item execution: use `notion-action-item`
- For Custom Agent audits and config work: use `notion-agent-config`
- For testing: use `notion-agent-test`

Optional planning chat surfaces can still help think through a problem, but they are not the authoritative workflow owner and do not replace the repo-backed source files.

---

# Maintenance

Update this document whenever:

- a new agent is added or repurposed
- a trigger, access pattern, or connection changes
- a schema convention changes
- a new manual workflow becomes repeatable enough to deserve a skill
- the session or review loop changes
