<!-- Notion Page ID: 323adb01-222f-81d7-bc47-c32cfea460f4 -->
# Agent SOPs
> Live Notion doc. This repo file is the source of truth for the mapped Notion page. Sync local changes to Notion in the same task.
The canonical operating spec for Adam's Notion workspace automation system.
Last synced: April 3, 2026 (Session 52: Routing Tier removal from docs, inbox-state model)
---
# Operating Model
Claude Code plus repo-backed Codex skills is the primary manual execution surface. Notion Custom Agents are bounded automation workers for scheduled or reactive workflows. Use the local docs in `ops/notion-workspace/docs/` as the source of truth and keep the mapped Notion instruction pages in sync with them.
Authority split:
- `docs/agent-sops.md`: canonical workflow, trigger, permission, schema, and session rules
- `CLAUDE.md`: bootstrap and execution contract for repo work
---
# Session Management
## How Sessions Work
Claude Code and Codex use the repo as the canonical session-handoff layer:
- `ops/notion-workspace/session-active.md`
The active file contains the current handoff, priorities, and known runtime state. Git history is the default archive. Legacy Notion session pages are not part of the normal operating loop for repo work.
## End-Of-Session Protocol
At the end of every session:
1. Overwrite `session-active.md` with the next handoff.
2. Rely on git history for archive and rollback by default.
3. Touch legacy Notion session pages only when retiring or cleaning up old scaffolding.
## Starting A New Session
1. Read `ops/notion-workspace/session-active.md`.
2. Read `CLAUDE.md`.
3. Read `docs/agent-sops.md`.
4. Read any directly relevant workflow doc or skill source.
---
# Agent Registry
<table header-row="true">
<tr>
<td>Agent</td>
<td>Instruction Page</td>
<td>Trigger</td>
<td>Model</td>
<td>Status</td>
<td>Settings URL</td>
</tr>
<tr>
<td>Post-Meeting Agent</td>
<td>Post-Meeting Instructions</td>
<td>Nightly 10 PM ET + `Record Status = Active` on Meetings + `@mention`</td>
<td>Opus 4.6</td>
<td>Live</td>
<td>[Settings](https://www.notion.so/agent/321adb01222f805f8182009253dc57a7?wfv=settings)</td>
</tr>
<tr>
<td>Post-Email Agent</td>
<td>Post-Email Instructions</td>
<td>Nightly 10:30 PM ET + `Record Status = Active` on Emails + `@mention`</td>
<td>Opus 4.6</td>
<td>Live</td>
<td>[Settings](https://www.notion.so/agent/325adb01222f806da7960092bc6484d3?wfv=settings)</td>
</tr>
<tr>
<td>Contact & Company Agent</td>
<td>Contact & Company Instructions</td>
<td>Nightly 11 PM ET + `@mention`</td>
<td>Opus 4.6</td>
<td>Live</td>
<td>[Settings](https://www.notion.so/agent/323adb01222f802cb5640092af74e84a?wfv=settings)</td>
</tr>
<tr>
<td>Curated Notes Agent</td>
<td>Curated Notes Instructions</td>
<td>`@mention` only</td>
<td>Opus 4.6</td>
<td>Active (manual QA reviewer)</td>
<td>[Settings](https://www.notion.so/agent/325adb01222f802e91290092cb71c17d?wfv=settings)</td>
</tr>
</table>
Naming conventions:
- Custom Agent in Notion settings: `[Agent Name]`
- Instruction page in Notion: `[Short Name] Instructions`
- Local doc: `docs/[kebab-case].md`
- Skill source: `skills/[skill-name]/`
---
# Manual Workflows And Skills
## Workflow Docs
<table header-row="true">
<tr>
<td>Workflow</td>
<td>Purpose</td>
<td>URL</td>
</tr>
<tr>
<td>LinkedIn Messages</td>
<td>Local fallback for manual LinkedIn DM recovery when notification-email intake is insufficient</td>
<td>`ops/notion-workspace/docs/linkedin-messages.md`</td>
</tr>
<tr>
<td>Merge Workflow</td>
<td>Merge duplicates and run delete-safe cleanup</td>
<td>[Merge Workflow](https://www.notion.so/323adb01222f811189c7c92eaac10ebb)</td>
</tr>
</table>
## Codex Skills
<table header-row="true">
<tr>
<td>Skill</td>
<td>Source Path</td>
<td>Purpose</td>
</tr>
<tr>
<td>`notion-active-session`</td>
<td>`ops/notion-workspace/skills/notion-active-session/`</td>
<td>Kick off the repo handoff, surface priorities, and route into the next scaffolding or workflow step</td>
</tr>
<tr>
<td>`notion-action-item`</td>
<td>`ops/notion-workspace/skills/notion-action-item/`</td>
<td>Execute a single Action Item end to end</td>
</tr>
<tr>
<td>`notion-agent-config`</td>
<td>`ops/notion-workspace/skills/notion-agent-config/`</td>
<td>Audit or update Notion Custom Agent settings against the local config spec</td>
</tr>
<tr>
<td>`notion-agent-test`</td>
<td>`ops/notion-workspace/skills/notion-agent-test/`</td>
<td>Run smoke or regression tests for Notion Custom Agents using the local playbooks</td>
</tr>
<tr>
<td>`notion-meeting-prep`</td>
<td>`ops/notion-workspace/skills/notion-meeting-prep/`</td>
<td>Surface open Action Items and recent emails for a Meeting's attendees before a call</td>
</tr>
</table>
Skill publish workflow:
1. Edit the canonical skill source in the repo.
2. Validate with `ops/notion-workspace/scripts/publish-codex-skills.ps1 -ValidateOnly`.
3. Publish to `$CODEX_HOME/skills` (default: `~/.codex/skills`) with `ops/notion-workspace/scripts/publish-codex-skills.ps1`.
4. Sync the Claude skill copy in `.claude/skills/` with `ops/notion-workspace/scripts/sync-claude-skill-wrappers.ps1`.
5. If a skill is renamed, treat it as a migration: remove or rename any stale `$CODEX_HOME/skills/<old-name>/` and `.claude/skills/<old-name>/` copies, then confirm the old path is gone before closing the task.
6. After a rename, run `ops/notion-workspace/scripts/test-skill-rename-cleanup.ps1 -OldName <old-name> -NewName <new-name>` and resolve any reported matches or stale paths unless Adam explicitly asked for a deprecated compatibility shim.
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
	- Meetings -\> Can edit content
	- Action Items -\> Can edit content
	- Contacts -\> Can edit content
	- Companies -\> Can edit content
	- Agent Config -\> Can edit
	- Post-Meeting Instructions -\> Can edit
	- Agent SOPs -\> Can view
- Connections:
	- Calendar: Adam - Business (Read), Adam - Personal (Read)
	- Mail: `adam@freedsolutions.com` (Read)
	- Web access: On
- Model: Opus 4.6
- Notes:
	- GCal sync-back is retired.
	- Manual `@mention` is for targeted rewiring, recovery, or explicitly requested curation on an already Active meeting.
	- Typed Notes are the primary non-Floppy Action Item source.
	- Floppy commands are the highest-confidence explicit signal and win any overlap; Adam will often use an end-of-meeting Floppy recap to summarize the Action Items that matter.
	- The AI summary and transcript may enrich note-derived items and provide bounded fallback recovery when Notes are sparse or empty, but they are not the default primary source when Notes are present.
	- Series wiring is recurrence-driven. When GCal returns `recurringEventId`, Post-Meeting stores that value in Meetings.`Series Key`, reuses or auto-creates a Series Parent, and sets the instance `Series` relation.
	- Same-title meetings without `recurringEventId` stay standalone. Legacy title-pattern Series matching is reference-only, not the automatic rule.
	- Curated summary generation remains inside Post-Meeting, but the separate Curated Notes Agent now serves as the manual QA reviewer.
## Post-Email Agent
- Triggers:
	- Daily 10:30 PM ET
	- Property trigger: `Record Status = Active` on Emails (fires Step 3 for newly promoted records)
	- `@mention`
	- Note: `Record Status = Active` on Emails gates Step 3 (new Action Item creation). Steps 1-2 (Email Notes + cross-contextual matching) run on all records regardless of status. This mirrors Post-Meeting: summary/wiring runs on Draft, Action Item creation runs on Active.
- Pre-processing script: `post_email_sweep.py` runs before the agent on the nightly schedule. It handles Gmail sweep, thread classification, Email/Contact/Company/Domain record creation and dedup, Date/Subject sync, and Agent Config Last Run updates. The agent receives pre-wired Email records and focuses on reasoning: Email Notes summaries, cross-contextual Action Item matching, and schema-safe Action Item creation.
- Notion page access:
	- Post-Email Instructions -\> Can edit
	- Emails -\> Can edit content
	- Action Items -\> Can edit content
	- Agent Config -\> Can view
	- Agent SOPs -\> Can view
- Connections:
	- Mail: runtime may show `adam@freedsolutions.com` and `adamjfreed@gmail.com`, and both are currently in scope for the live agent
	- Expected mail permission set is `Read` only. The agent does not modify Gmail inbox state (no archiving, no marking read). `Send` and `Draft` should stay off; treat any broader runtime scope as config drift and log it during agent audits.
	- Web access: Off
	- No calendar access
- Model: Opus 4.6
- Notes:
	- The agent's 4-step pipeline: (1) identify records needing attention (blank Email Notes or script stubs), (2) write Email Notes summaries + cross-contextual Action Item matching, (3) schema-safe Action Item creation on Active records, (4) CRM completion logging.
	- The agent trusts the script's CRM wiring. It does not re-wire Contacts or Companies. If wiring looks wrong, it logs the issue in Email Notes but does not modify relations.
	- The agent does NOT update Agent Config Last Run — the script handles this.
	- Routed Gmail labels are part of the intake contract for `adam@freedsolutions.com`: `Primitiv` for all Primitiv-related mail, `LinkedIn` for LinkedIn message notifications, and `DMC` for DMC routed company mail.
	- Teams and LinkedIn notifications are chat wrappers around human conversations, not bot-only terminal mail by default.
	- `Record Status = Active` on Emails gates Step 3 (Action Item creation). `@mention` runs also respect this gate.
	- Bot-only or alias-only threads may be summarized and skipped without creating action items. Leave them as `Draft` with an explicit `Email Notes` annotation; Adam archives terminal stubs from the UI.
## Curated Notes Agent
- Triggers:
	- `@mention`
	- Property trigger: Off
- Notion page access:
	- Meetings -\> Can edit content
	- Emails -\> Can edit content
	- Action Items -\> Can edit content
	- Contacts -\> Can view
	- Companies -\> Can view
	- Agent Config -\> Can edit
	- Curated Notes Instructions -\> Can edit
	- Agent SOPs -\> Can view
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
	- Contact & Company Instructions -\> Can edit
	- Companies -\> Can edit content
	- Contacts -\> Can edit content
	- Agent Config -\> Can edit
	- Agent SOPs -\> Can view
- Connections:
	- Web access: On
	- Calendar: Read only
	- Mail: keep least-privilege scope. The intended runtime is `adam@freedsolutions.com` with read-only access; re-verify during config audits.
	- The workflow must not send mail or mutate inbox state as part of enrichment.
- Model: Opus 4.6
- Notes:
	- Queue fairness matters. Old Draft and QC-gap records must not starve behind newer ones.
	- Placeholder correction is allowed when evidence is stronger than the placeholder default.
---
# Database Quick Reference
<table header-row="true">
<tr>
<td>Database</td>
<td>Data Source ID</td>
</tr>
<tr>
<td>Contacts</td>
<td>`fd06740b-ea9f-401f-9083-ebebfb85653c`</td>
</tr>
<tr>
<td>Companies</td>
<td>`796deadb-b5f0-4adc-ac06-28e94c90db0e`</td>
</tr>
<tr>
<td>Action Items</td>
<td>`319adb01-222f-8059-bd33-000b029a2fdd`</td>
</tr>
<tr>
<td>Meetings</td>
<td>`31fadb01-222f-80c0-acf7-000b401a5756`</td>
</tr>
<tr>
<td>Emails</td>
<td>`f685a378-5a37-4517-9b0c-d2928be4af4d`</td>
</tr>
<tr>
<td>Domains</td>
<td>`9f8ea73a-a8d3-43fb-a2b6-7ff77ebd6e69`</td>
</tr>
</table>
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
Only Adam promotes records to `Active`. Agents create Draft records and never change `Record Status`. To delete a record, trash it directly in Notion — there is no intermediate status. Notion automatically clears reciprocal relations. Permanent delete from Notion trash is Adam's manual step.
Archiving is Adam's UI-managed lifecycle step for records that should be hidden from active views but preserved with full wiring for future use. Archived records remain searchable by agents for dedup and contact matching.
## Contacts
- Dedup across `Email`, `Secondary Email`, and `Tertiary Email`
- New or repaired Contact pages should use the `👤` page icon for visual consistency
- `Company` is the primary operational relation
- `LinkedIn`, `Phone`, `Pronouns`, and `Role / Title` are fill-in fields and may be updated by enrichment workflows
## Normalization rules
These apply when writing or matching LinkedIn URLs, emails, or domains across any workflow.
- **LinkedIn URL**: canonical form is `https://www.linkedin.com/in/<slug>` (or `/company/<slug>` for companies). Strip query parameters, fragments, and trailing slashes before storing or comparing.
- **Email**: lowercase and trim whitespace before storing or comparing.
- **Domain**: extract hostname from a full URL (strip scheme, path, query). Compare against both `Domains` and `Additional Domains`.
## Companies
- `Domains` holds primary operational domains
- `Additional Domains` holds merged, subsidiary, alternate, or legacy domains — and may also hold **full sender email addresses** for platform companies where the domain itself is too broad for reliable matching (e.g., `workspace@google.com` instead of `google.com`)
- Both domain fields are used for matching and dedup
- When matching, check extracted domains against both fields first. If no domain match is found, also check the **full sender email address** against `Additional Domains` to catch platform-company sender-level entries
- `Emails` and `Meetings` are company-side rollups from `Contacts`; if those look empty, verify the `Meeting -> Contacts -> Contact -> Company` and `Email -> Contacts -> Contact -> Company` chains before assuming the source records failed to wire
- Placeholder companies default to `States = All`, but enrichment may replace that placeholder value when stronger evidence exists
## Meetings
- `Calendar Event ID` is the canonical event identity
- `Series Key` stores the Google `recurringEventId` on recurring instances and their Series Parent row
- Recurring meetings reuse or auto-create a Series Parent keyed by `Series Key`; parent rows intentionally keep `Calendar Event ID` blank
- Same-title meetings without `Series Key` stay standalone unless Adam explicitly requests a manual repair
- `Calendar Name` is a select with current live options:
	- `Adam - Business`
	- `Adam - Personal`
- If a meeting cannot yet be matched to a configured calendar, leave `Calendar Name` blank and log the recovery state instead of inventing a non-existent select option
## Action Items
- `Company` represents the owning or execution business context for the work item; it is not automatically the counterparty's employer
- `Contact` carries the counterparty person when one is involved
- `Source Meeting` / `Source Email` capture provenance for how the work entered the CRM
- `Source Email` is a multi-relation. One Action Item may legitimately relate to multiple Email threads when those threads all contribute useful provenance for the same work item.
- `Target Meeting` / `Target Email` capture optional future planning, presentation, or close-out context; leave them blank unless Adam or an explicit Action Item workflow asks to wire them
- For Adam-owned, pre-seeded, or otherwise internally-originated work, default `Company` to the source calendar, mailbox, or explicit business context unless the source text clearly names another beneficiary company or account
- Use the counterparty's company as `Company` only when the item is genuinely tracking that counterparty's commitment, deliverable, or follow-up
- Every Action Item should have a reliable `Company` whenever a trustworthy fallback exists
- `Due Date` should be set whenever the source text contains an explicit or relative deadline that can be resolved
- `Status = Review` indicates a response was received on a Follow Up or Task that needs Adam's assessment. Agents set Review; Adam resolves it (Done, back to In Progress, or other action).
- New or repaired Action Item pages should use the `🎬` page icon unless an explicit manual exception already exists
## Domains
- New or repaired Domain pages should use the `🌐` page icon
## Emails
- `Thread ID` is the canonical email-thread identity
- Compare parity and dedup by exact `Thread ID`, not subject lines or Gmail message counts
- Archived Email pages still count as already processed for parity and should suppress false “missing thread” conclusions
- `Source` must be populated
- Company-side visibility for emails comes from the `Companies.Emails` rollup via `Contacts -> Emails`, not from a direct Company relation on the Emails DB
- Existing email stubs may be healed in place when prior runs only completed part of the workflow
- Contextful notifications and share mail may still belong in the Emails DB even when the sender looks automated, as long as the thread preserves useful human relationship context
- Status-only meeting invite replies are skip/read with no Email record. Raw invite/update packets belong in a meeting-support bucket unless they materially help reconcile the correct Meeting/calendar or preserve useful context, while invite-thread mail with real human commentary may still belong in the Emails DB
- Bot-only or alias-only email stubs should be annotated in `Email Notes` so they are clearly terminal. They stay as `Draft` until Adam archives them from the UI
- Gmail read-state may change only after the thread is retained and wired, intentionally skipped, or classified as meeting-support-only. Truly unresolved exceptions stay unread and should be logged explicitly
- New or repaired Email pages should use the `📧` page icon for visual consistency
## Domains
- `Domain` (title) is the canonical domain or subdomain
- `💼 Companies` relation wires to the parent Company
- `Filter Shape` determines the `from:` criteria format (`Domain` = `*@domain`, `Sender` = `from:user@domain`, `None` = no filter)
- Email record creation is driven by inbox state (Gmail filter behavior), not by a Domains DB property. If Gmail's filter archived a labeled thread, the script creates a record. If the thread has no label and is archived, it is dismissed.
- One Domain record per domain/subdomain, even when multiple subdomains share a parent Company
- Agents creating new Companies must also create a corresponding Draft Domain record
---
# Rules of Engagement
1. Read `ops/notion-workspace/session-active.md` first, then the canonical local docs.
2. Standing approval applies to routine Notion work once Adam requests it, including the normal validate, test, sync, commit, and push follow-through for `ops/notion-workspace` when the work stays inside the documented workflow.
3. Pause only for ambiguity, destructive actions, schema changes, lifecycle changes outside a documented workflow or test path, new non-test CRM record creation outside a documented workflow, or large migrations.
4. Never create duplicate CRM records.
5. Never change `Record Status` outside the explicit workflow rules, documented test path, or Adam's direct instruction.
6. Verify live parity after pushing a local doc to Notion.
7. Keep docs, skills, and runtime behavior aligned. Do not accept silent drift as normal.
8. Every repo doc that maps to a live Notion page must include a visible `Live Notion doc` banner directly under the H1.
## Skill Gate Protocol
Repo-backed Notion skills use this shared gate taxonomy:
<table header-row="true">
<tr>
<td>Gate</td>
<td>Meaning</td>
</tr>
<tr>
<td>`UNGATED`</td>
<td>Proceed without pausing.</td>
</tr>
<tr>
<td>`HARDENED_GATE`</td>
<td>Ask one compact decision-shaped question using native structured questioning when available; otherwise use a deterministic short chat halt. If the reply is empty, unclear, or ambiguous, re-ask before proceeding. Never treat silence as approval.</td>
</tr>
<tr>
<td>`GOVERNANCE_GATE`</td>
<td>Use the same pause mechanism as `HARDENED_GATE`, but only when the existing Rules of Engagement require a pause.</td>
</tr>
</table>
Inside an autonomous repo-backed skill run, any repo/code mutation must go through `HARDENED_GATE` before the first edit, even when the broader workflow is standing-approved. This includes edits under `docs/`, `skills/`, `ops/notion-workspace/CLAUDE.md`, `ops/notion-workspace/session-active.md`, and repo scripts. Outside an autonomous skill run, the normal standing-approval rules still apply.
## Kickoff Conventions
Claude Code is the default execution surface. Start from the repo and use the skill source that best fits the task.
- For repo bootstrap, priority review, or planned scaffolding kickoff: use `notion-active-session`
- For Action Item execution: use `notion-action-item`
- For Custom Agent config audits or edits: use `notion-agent-config`
- For Custom Agent smoke or regression testing: use `notion-agent-test`
- For pre-call meeting context: use `notion-meeting-prep`
- For broader Notion workspace work without a matching skill: use Claude Code directly against the local docs and live Notion workspace
Optional planning chat surfaces can still help think through a problem, but they are not the authoritative workflow owner and do not replace the repo-backed source files.

## Sub-Agent Delegation

When Claude Code or Codex spawns sub-agents within a session, delegation follows the sub-agent contract in `docs/sub-agent-contract.md`. Key constraints:

- Maximum delegation depth is 1 (parent -> sub-agent, no further nesting).
- `GOVERNANCE_GATE` decisions are never delegated. Sub-agents return `needs_escalation` and the parent asks Adam.
- Parallel sub-agents must have disjoint write targets. For Notion DB record creation, serialize or dedup-before-create.
- Sub-agents load conventions from lightweight context cards under `docs/cards/` using one of four scaffold profiles: `explorer`, `crm-worker`, `validator`, `scaffolding-editor`.
- Every sub-agent returns a typed result envelope with status, findings, and mutations performed.

This contract does not apply to Notion Custom Agents (server-side) or to sequential user-invoked skill execution.
---
# Maintenance
Update this document whenever:
- a new agent is added or repurposed
- a trigger, access pattern, or connection changes
- a schema convention changes
- a new manual workflow becomes repeatable enough to deserve a skill
- the session or review loop changes
