<!-- Notion Page ID: 323adb01-222f-81d7-bc47-c32cfea460f4 -->
# Agent SOPs
> Live Notion doc. This repo file is the source of truth for the mapped Notion page. Sync local changes to Notion in the same task.
The canonical operating spec for Adam's Notion workspace automation system.
Last synced: March 23, 2026
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
<td>Nightly 10:30 PM ET + `@mention`</td>
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
<td>Delete Unwiring Agent</td>
<td>Delete Unwiring Instructions</td>
<td>`@mention` only (property triggers removed March 22, 2026)</td>
<td>Opus 4.6</td>
<td>Retired</td>
<td>[Settings](https://www.notion.so/agent/325adb01222f80d2844a0092e63da4ea?wfv=settings)</td>
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
	- Curated summary generation remains inside Post-Meeting, but the separate Curated Notes Agent now serves as the manual QA reviewer.
## Post-Email Agent
- Triggers:
	- Daily 10:30 PM ET
	- `@mention`
- Notion page access:
	- Post-Email Instructions -\> Can edit
	- Emails -\> Can edit content
	- Contacts -\> Can edit content
	- Companies -\> Can edit content
	- Action Items -\> Can edit content
	- Agent Config -\> Can edit
	- Agent SOPs -\> Can view
- Connections:
	- Mail: runtime may show `adam@freedsolutions.com` and `adamjfreed@gmail.com`, and both are currently in scope for the live agent
	- Expected mail permission set is `Read` plus inbox-modify only for marking terminal threads read after successful processing. `Send` and `Draft` should stay off; treat any broader runtime scope as config drift and log it during agent audits.
	- Web access: Off
	- No calendar access
- Model: Opus 4.6
- Notes:
	- Existing stubs must be eligible for recovery if prior runs stopped after partial work.
	- Routed Gmail labels are part of the intake contract for `adam@freedsolutions.com`: `Primitiv/PRI_Outlook` for forwarded Outlook mail, `Primitiv/PRI_Teams` for Teams notifications, `LinkedIn` for LinkedIn message notifications, and `DMC/DMC_GMail` for DMC routed company mail.
	- `Action Items` and any `Action Items/...` child label are temporary manual-queue labels. Ignore them for automated intake until Adam explicitly enables a dedicated workflow.
	- Those routed Gmail labels are the canonical intake signal. `Source` should only use existing schema values; do not force a schema change just to mirror every label.
	- `adamjfreed@gmail.com` stays in live sweep scope, but its Gmail labels are currently out of scope for routing. Treat personal-mailbox messages as standard email unless Adam explicitly adds a mailbox-specific routing contract later.
	- Other Gmail labels, especially company or project labels, are metadata only unless they are deliberately promoted into a routed intake lane.
	- Long term, domain-aligned company labels are encouraged because they make inbox-zero routing and CRM automation more deterministic.
	- Teams and LinkedIn notifications are chat wrappers around human conversations, not bot-only terminal mail by default.
	- Bot-only or alias-only threads may be summarized and skipped without creating CRM wiring or action items. Leave them as `Draft` with an explicit `Email Notes` annotation; Adam archives terminal stubs from the UI.
	- Runtime audit on March 20, 2026 found a revoked Notion-access entry where Agent Config should be. Repair the live page access if timestamps stop updating.
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
## Delete Unwiring Agent
- Retired (March 22, 2026). Live testing confirmed Notion trash automatically clears reciprocal synced-dual relations. The unwiring step is redundant.
- Triggers:
	- All property triggers removed
	- `@mention` only (retained for manual re-activation if needed)
- Notion page access:
	- Delete Unwiring Instructions -\> Can edit
	- Meetings -\> Can edit content
	- Companies -\> Can edit content
	- Action Items -\> Can edit content
	- Contacts -\> Can edit content
	- Emails -\> Can edit content
	- Agent Config -\> Can edit
	- Agent SOPs -\> Can view
- Connections:
	- Web access: Off
	- No calendar
	- No mail
- Model: Opus 4.6
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
<td>Agent Config</td>
<td>`322adb01-222f-8114-b1b0-cc8971f1b61a`</td>
</tr>
<tr>
<td>Emails</td>
<td>`f685a378-5a37-4517-9b0c-d2928be4af4d`</td>
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
- `Delete`
Only Adam promotes records to `Active`. Agents create Draft records and never change `Record Status`. To delete a record, set `Record Status = Delete` and trash it — Notion automatically clears reciprocal relations. Permanent delete from Notion trash is Adam's manual step.
Archiving is Adam's UI-managed lifecycle step for records that should be hidden from active views but preserved with full wiring for future use. Archived records remain searchable by agents for dedup and contact matching.
## Contacts
- Dedup across `Email`, `Secondary Email`, and `Tertiary Email`
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
- `Calendar Name` is a select with current live options:
	- `Adam - Business`
	- `Adam - Personal`
- If a meeting cannot yet be matched to a configured calendar, leave `Calendar Name` blank and log the recovery state instead of inventing a non-existent select option
## Action Items
- `Company` represents the owning or execution business context for the work item; it is not automatically the counterparty's employer
- `Contact` carries the counterparty person when one is involved
- For Adam-owned, pre-seeded, or otherwise internally-originated work, default `Company` to the source calendar, mailbox, or explicit business context unless the source text clearly names another beneficiary company or account
- Use the counterparty's company as `Company` only when the item is genuinely tracking that counterparty's commitment, deliverable, or follow-up
- Every Action Item should have a reliable `Company` whenever a trustworthy fallback exists
- `Due Date` should be set whenever the source text contains an explicit or relative deadline that can be resolved
## Emails
- `Thread ID` is the canonical email-thread identity
- `Source` must be populated
- Company-side visibility for emails comes from the `Companies.Emails` rollup via `Contacts -> Emails`, not from a direct Company relation on the Emails DB
- Existing email stubs may be healed in place when prior runs only completed part of the workflow
- Bot-only or alias-only email stubs should be annotated in `Email Notes` so they are clearly terminal. They stay as `Draft` until Adam archives them from the UI
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
- For broader Notion workspace work without a matching skill: use Claude Code directly against the local docs and live Notion workspace
Optional planning chat surfaces can still help think through a problem, but they are not the authoritative workflow owner and do not replace the repo-backed source files.
---
# Maintenance
Update this document whenever:
- a new agent is added or repurposed
- a trigger, access pattern, or connection changes
- a schema convention changes
- a new manual workflow becomes repeatable enough to deserve a skill
- the session or review loop changes
