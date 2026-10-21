# Notion Workspace Automation

> **RETIRED 2026-10-21.** Adam no longer uses Notion. This file was `CLAUDE.md` and no longer auto-loads. Keep it as the DESIGN REFERENCE for the New Wave Cannabis CRM/PMO/automation build: the agent model, gate taxonomy (`UNGATED` / `HARDENED_GATE` / `GOVERNANCE_GATE`), schema conventions, dedup and sync principles. The session protocol, Notion sync, closeout gates and `session-active.md` below are historical; do not execute them.

> This project lives at `ops/notion-workspace/` within the FreedSolutions repo.
> It manages Adam Freed's CRM and operations automation system built on Notion.

## First Steps - Every Session

1. **Read the repo session handoff first** - `ops/notion-workspace/session-active.md` is the canonical active handoff for Claude Code and Codex work.
2. **Read local docs** - `ops/notion-workspace/docs/agent-sops.md` is the stable workflow reference, then read the workflow-specific doc that matches the task.
3. **Use the repo skills for manual workflows** - `freed-solutions/skills/` is the canonical source for the manual operator layer; the four `notion-*` / `pandoc-deliverable` skills are sourced from the TheoryWellness repo (see Codex Skills below).
4. **Use standing approval for routine Notion work.** Ask questions only if the request is ambiguous, destructive, schema-changing, or a bulk record operation.

## Local Docs

Local `docs/` files are the source of truth for instruction content. Most workflow docs map to Notion instruction pages; local-only fallback and test docs stay in the repo.

For every doc that maps to a live Notion page, keep a visible banner directly under the H1:
`> Live Notion doc. This repo file is the source of truth for the mapped Notion page. Sync local changes to Notion in the same task.`

| File | Notion Page ID | Purpose | Last Sync |
|------|---------------|---------|-----------|
| `docs/agent-sops.md` | `323adb01-222f-81d7-bc47-c32cfea460f4` | Canonical operating model: agents, workflows, schema, runtime baseline, and manual operator rules | 2026-04-05 (S76) |
| `docs/post-meeting.md` | `324adb01-222f-8168-a207-d66e81884454` | Post-Meeting Agent: 4-step pipeline (CRM wiring -> Floppy -> notes-driven action items with summary/transcript enrichment only + cross-contextual follow-up detection -> curated summary). Uses live `Calendar Name` options only. | 2026-04-05 (S78) |
| `docs/contact-company.md` | `323adb01-222f-8126-9db8-df77be5a326f` | Contact & Company Agent: nightly enrichment for Draft records plus Active QC gaps, with placeholder correction, domain cross-check, Source Type coherence, and backlog fairness rules | 2026-04-04 (S68) |
| `docs/notetaker-crm.md` | `324adb01-222f-80ca-af0a-cd455329d8e8` | Notetaker CRM: paste into Notion Calendar AI settings | 2026-04-04 (S69) |
| `docs/post-email.md` | `325adb01-222f-81d3-825a-d3e0c74c0e30` | Post-Email Agent: reasoning-only after script split — Email Notes summaries, cross-contextual matching, schema-safe action items | 2026-04-04 (S73) |
| `docs/follow-up.md` | `338adb01-222f-8177-88ba-f29b1e8998cc` | Follow-Up Agent: manual cross-contextual AI matching on @mention — checks all AI types, wires context, sets Review | 2026-04-04 (S73) |
| `docs/skills-registry.md` | — | Canonical inventory of all skills, sync workflow, and update tracking (repo-only) | 2026-04-05 (S76) |

## Codex Skills

Repo skill sources for Freed Solutions Claude/Codex work live under `freed-solutions/skills/`. Claude reads synced generated copies under `.claude/skills/` produced by `ops/notion-workspace/scripts/sync-claude-skill-wrappers.ps1`. Codex copies belong in `$CODEX_HOME/skills` (default: `~/.codex/skills`; Windows default: `C:\Users\adamj\.codex\skills`).

**Skills migrated to TheoryWellness (2026-05-22):** `notion-action-items`, `notion-agent-config`, `notion-meeting-prep`, and `pandoc-deliverable` previously lived in `ops/notion-workspace/skills/` here. They were moved to `c:\Users\adamj\Code\TheoryWellness\skills\` as canonical source and are now published to `~/.claude/skills/` (user-level), making them invocable from any Claude Code session — including this one — without per-repo wrappers. The Freed `mcp__notion` server still points at the Freed Notion workspace they operate against, so behavior is unchanged for Freed CRM work; only the source-file location moved. See `c:\Users\adamj\Code\TheoryWellness\CLAUDE.md` for the user-scope sync command.

Skills still canonical in this repo:

| Skill | Canonical Source | Purpose |
|------|------------------|---------|
| `cannabis-tech-sitemap` | `freed-solutions/skills/cannabis-tech-sitemap/` | Generate a Mermaid-based tech-stack sitemap + Option A/B/C scenario canvas from client discovery interview notes |
| `resume-builder` | `freed-solutions/skills/resume-builder/` | Tailor resume + cover letter + application answers for a specific job opening, using a base resume as the DOCX style anchor |

Other `freed-solutions/skills/` entries (`codex-review`, `create-skill`, `dutchie-bi-looker`, `freed-solutions-website`, `google-sheets-patterns`) follow the same pattern.

Publish or validate them with `ops/notion-workspace/scripts/publish-codex-skills.ps1`. Adding a new source root: append to `$sourceRoots` in both scripts; collision detection is built in.

The `Notion Page ID` values in the local-doc table above are the canonical page mapping. Individual repo docs may also carry a local `<!-- Notion Page ID: ... -->` comment for convenience, but that comment is optional and must never appear in a live Notion page.

## Session Files

The repo is the canonical home for session handoff docs.

| File or Path | Purpose |
|--------------|---------|
| `ops/notion-workspace/session-active.md` | Canonical active handoff, priorities, and next actions |

## Notion-Only Resources (access via MCP)

| Resource | Type | ID |
|----------|------|----|
| Agent Config | Page | `322adb01-222f-8114-b1b0-cc8971f1b61a` |
| Automation Hub | Page | `321adb01-222f-810f-8706-e53105950d86` |

## Database IDs

| Database | Data Source ID |
|----------|---------------|
| Contacts | `fd06740b-ea9f-401f-9083-ebebfb85653c` |
| Companies | `796deadb-b5f0-4adc-ac06-28e94c90db0e` |
| Action Items | `319adb01-222f-8059-bd33-000b029a2fdd` |
| Meetings | `31fadb01-222f-80c0-acf7-000b401a5756` |
| Emails | `f685a378-5a37-4517-9b0c-d2928be4af4d` |
| Domains | `9f8ea73a-a8d3-43fb-a2b6-7ff77ebd6e69` |

The IDs listed here are Notion Data Source IDs used by MCP and Custom Agents. The direct Notion API uses different database UUIDs — see `ops/local_db/config.yaml` for API-facing IDs.

**Adam's Notion User ID:** `30cd872b-594c-81b7-99dc-0002af0f255a`

## Rules of Engagement

1. **Read the repo active handoff first** - `ops/notion-workspace/session-active.md` has the canonical current-session context.
2. **Standing approval applies to routine Notion work and its normal follow-through.** If Adam asks to update, sync, harden, test, document, maintain, commit, or push `ops/notion-workspace`, execute the full read, edit, push, verify, review, log, commit, and push loop without asking for step-by-step permission when the work stays inside the documented workflow.
3. **Only pause for confirmation** when the task is ambiguous, destructive, schema-changing, touches `Record Status` outside an explicitly documented workflow or test path, creates non-test CRM DB records, or is a migration/bulk operation.
4. **For migrations or bulk operations:** audit current state -> present plan -> get Adam's approval -> execute in phases with verification between each.
5. **Use repo skill sources for manual operator work.** Task-specific manual workflows belong in `freed-solutions/skills/` (or the TheoryWellness repo for the four user-scope skills), not in ad hoc slash-command notes.
6. **Never create new CRM DB records** unless explicitly instructed, except bounded `[TEST]` records or disposable audit pages required by the documented playbooks.
7. **Never change `Record Status`** (`Draft`/`Active`) without explicit instruction. Agents create Draft records and never change Record Status. Archiving and deletion (trash) are Adam's UI-managed steps.
8. **Log everything** - `ops/notion-workspace/session-active.md` is the session system of record.
9. **Dedup checks are mandatory** - always check Email + Secondary Email + Tertiary Email for contacts, Domains DB records for companies.
10. **UI steps require Adam's confirmation before marking complete.** Some tasks can only be done in the Notion UI (configuring agent triggers, pasting content too large for API, Settings changes). When a planning output or session priority includes a UI step: (a) explicitly list it as "Adam - UI step", (b) do NOT mark it complete until Adam confirms in the chat that it's done, (c) do not assume completion based on page existence or other indirect signals.
11. **Verify content on sync, not just existence.** When marking a Notion page as "in sync" with a local doc, verify the actual content matches - not just that the page exists.
12. **Do not claim a clean close-out with a dirty tree.** Before saying the task is done, inspect `git status --short` and disclose any unrelated modified or untracked files instead of calling the worktree clean. If unrelated local changes are present, keep them out of the review conclusion by narrowing the review gate to the intended paths.

## Skill Gate Protocol

Repo-backed Notion skills use this shared gate taxonomy:

| Gate | Meaning |
|------|---------|
| `UNGATED` | Proceed without pausing. |
| `HARDENED_GATE` | Ask one compact decision-shaped question using native structured questioning when available; otherwise use a deterministic short chat halt. If the reply is empty, unclear, or ambiguous, re-ask before proceeding. Never treat silence as approval. |
| `GOVERNANCE_GATE` | Use the same pause mechanism as `HARDENED_GATE`, but only when the existing Rules of Engagement require a pause. |

When a repo-backed skill is executing autonomously, any repo/code mutation must go through `HARDENED_GATE` before the first edit, even when the broader workflow is standing-approved. This includes edits under `docs/`, `skills/`, `ops/notion-workspace/CLAUDE.md`, `ops/notion-workspace/session-active.md`, and repo scripts. Outside an autonomous skill run, the normal standing-approval rules still apply.

## Local Client Approval Baseline

- **Enforced, not described:** `ops/notion-workspace/scripts/test-approval-baseline.ps1` asserts the Claude allow-list baseline (`.claude/settings.json` shared and repo-tracked; `.claude/settings.local.json` workstation overlay, kept mirrored) and the Codex profiles in `~/.codex/config.toml` (`ops_notion_workspace_quiet` = approval never / workspace-write; `ops_notion_workspace` = on-failure fallback). `test-discovery-scope.ps1` asserts repo-scoped discovery. The baseline is in force only after both pass.
- **Rules the tests cannot see:** MCP permission entries have no `*` wildcard, so approve the server name itself; keep `playwright` in `.mcp.json` and the Notion server out of it (user-level client config only); workstation-only allowances go in `settings.local.json`, never the tracked file; discovery stays repo-rooted (`rg --files ops/notion-workspace`), never absolute paths or `..` escapes.
- **Launch Codex** with `ops/notion-workspace/scripts/start-codex-notion-workspace.cmd` (quiet lane, falls back to the safe profile) or `-safe.cmd`; both validate the profile first and fail fast without `~/.codex/config.toml`. Use `codex.cmd`, not bare `codex`.
- **Quiet mode is a client baseline only:** routine Playwright and MCP prompts are suppressed inside documented flows, but `HARDENED_GATE` / `GOVERNANCE_GATE` and the Playwright bounds (documented tools, workspace-scoped outputs, Notion + localhost domains) still apply.

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

Inside an autonomous repo-backed skill run, repo/code mutations still require `HARDENED_GATE` before the first edit. Once that gate is satisfied, continue the approved change set autonomously unless a later `GOVERNANCE_GATE` is triggered.

Pause and ask before proceeding only when any of the following are true:

- The request is ambiguous or conflicts with the local source-of-truth docs
- The change would modify database schema, views, automations, or agent architecture
- The change would create, merge, delete, or bulk-edit non-test CRM records
- The change would alter `Record Status` or other lifecycle controls outside the documented workflow or test path
- The operation is large enough that rollback would be difficult

## Key Schema Conventions

- **Record Status** (select on Contacts, Companies, Action Items, Meetings, Emails): `Draft` -> `Active`. Only two values. Archiving (Notion UI) is an orthogonal visibility layer - records are hidden from views but preserve all wiring and remain searchable by agents for dedup.
- **Contacts DB:** Contact Name (title), Display Name (formula), QC (formula), Email, Secondary Email, Tertiary Email, Phone, Pronouns, Nickname, LinkedIn, Company, Role / Title, Tags (multi_select: Marketing, Retail, Manufacturing, Supply Chain, Technology, HR, Finance, Executive, Operations, Admin, Wholesale, Compliance, Sender Bot, Personal), Record Status, Contact Notes
- **Companies DB:** Company Name (title), Company Type (select: Tech Stack, Operator, Network, Personal), QC (formula), 🌐 Domains (relation to Domains DB), States (multi_select: MA, MI, CT, NJ, FL, OH, PA, CA, All, AR, MO, MS, LA, TX; default: "All"), Website, Contacts, Emails (rollup), Meetings (rollup), Action Items, Engagements, Tech Stack, Record Status, Company Notes
- **Domains DB:** Domain (title), 💼 Companies (relation), Source Type (select: Primary, Additional, Sender-Level), Gmail Label (rich_text), Notes (rich_text), Record Status (select: Draft, Active), QC (formula). *Filter shape is derived from Source Type (Primary/Additional = domain-level, Sender-Level = full-email). Gmail Filter IDs are tracked locally in `ops/local_db/gmail_filter_ids.json`. Email record creation is driven by inbox state (Gmail filter behavior), not by a Domains DB property.*
- **Action Items DB:** Task Name (title), Type (formula), Status, Priority, Record Status, Task Notes, Due Date, Created Date (created_time), Contact, Company, Assignee, Source Meeting, Source Email, Files, QC (formula)
- **Action Items Tags:** Tag context comes from the Contact relation. Action Items do not have a Tags property — use the wired Contact's Tags for any tag-based filtering or grouping.
- **Action Items Status = Review:** Indicates a response was received on a Follow Up or Task that needs Adam's assessment. Agents set Review; Adam resolves it (Done, back to In Progress, or other action).
- **Meetings DB:** Meeting Title (title), Calendar Event ID, Calendar Name, Date, Contacts, Companies (rollup), Action Items, Series, Series Key, Instances, Is Series Parent, Series Status (rollup), Location, Record Status, QC (formula)
- **Emails DB:** Email Subject (title), Thread ID, Email URL (formula), Date, Contacts, Companies (rollup), Action Items, Labels (multi_select), Source (select: Email - Freed Solutions, Email - Personal), Record Status, Email Notes, QC (formula), Created Timestamp
- **Email routing labels:** On `adam@freedsolutions.com`, a top-level client label (e.g., `<Client A>`) routes all client-related mail (forwarded Outlook, Teams notifications, calendar invites). Dual-labeled threads: vendor labels like `Dutchie` (Looker reports) and `Intuit` (QB transactions) also carry the client label via `to:` filter overlap or explicit multi-label filter rules. `LinkedIn` = LinkedIn message-notification intake. Additional client labels (e.g., `<Client B>`) route company-mail intake per client. Other company or project labels are metadata only unless explicitly promoted into routing. Labels are the canonical intake-route truth for the Freed Solutions mailbox. `adamjfreed@gmail.com` remains in live sweep scope, but its labels are out of scope for routing. Teams notifications keep the mailbox-derived `Source`; the `Labels` multi_select carries the routing metadata instead of a dedicated Teams source option.
- **New source filter contract:** When a newly retained thread introduces a stable new Company or Contact source that should route future mail, dedup the CRM records first, then create or refresh the Gmail label using the existing live naming pattern: the top-level client label (e.g., `<Client A>`) or the exact stable company label Adam already uses when no child lane is needed. Add the matching option to `Emails.Labels`, default to company/domain filters, use sender-specific filters only for exceptions, and keep new filters label-first instead of auto-read by default.
- **Action Item provenance:** `Source Meeting` / `Source Email` capture where the work originated.
- **Page icon conventions:** New or repaired Meetings should use `🗓️`, Contacts `👤`, Emails `📧`, Action Items `🎬`, and Domains `🌐` unless an explicit manual exception already exists. Company page icons remain Adam-managed.
- **Email fields** (Contacts): Email, Secondary Email, Tertiary Email - all checked for dedup
- **Domain lookup** (Companies): Use the **Domains DB** for all domain matching and dedup. Each Domain record has a 💼 Companies relation and Source Type (Primary, Additional, Sender-Level). Full sender email addresses for platform companies (e.g., `workspace@google.com`) are stored as Sender-Level Domain records.
- **Calendar Name** currently has live select options for `Adam - Business` and `Adam - Personal` only. Do not assume local placeholders such as `Manual` or `Pending` exist in the schema.
- **Series Key** stores the Google `recurringEventId` on recurring Meetings and their Series Parent row. Same-title meetings without a `Series Key` stay standalone unless Adam explicitly asks for a manual repair.
- **Delete path:** Trash the record directly in Notion. No intermediate status — `Delete` has been removed from the schema. Notion automatically clears reciprocal relations on linked records. Permanent delete from Notion trash is Adam's manual step.
- **Email parity + cleanup contract:** Compare Gmail parity by exact `Thread ID`, not by subject line or Gmail message count. Archived Email rows still count as already processed for parity. The agent does not modify Gmail inbox state (no archiving, no marking read). Unresolved exceptions must be listed explicitly.
- **Concrete duplicate-prevention target:** The March 25 `Hoodie Analytics` / `David Winter` duplicate cluster is concrete evidence of a race-condition-class bug. Future Post-Email hardening must use in-run dedup-before-create or serialized Company/Contact creation across same-thread-family work.
- **Agent Config:** Runtime state (timestamps) shared between agents. Not documentation - agents read/write during execution.

## End-of-Session Protocol

At the end of every session:

1. Update `ops/notion-workspace/session-active.md` with the next handoff.
2. Rely on git history as the session archive unless Adam explicitly wants a named snapshot file.
3. Retire or refresh any legacy Notion session pages only if that reduces confusion in the live workspace.

## Sync Convention

- Local `docs/` files are the source of truth for instruction content.
- When instructions change, edit the local file first, then push to Notion via MCP in the same task unless Adam explicitly asks for a local-only draft. Do not paste the repo-only `<!-- Notion Page ID: ... -->` comment into the live Notion page.
- Save fetched live page bodies verbatim under `ops/notion-workspace/tmp/notion-sync-remote-YYYY-MM-DD-<doc>.md` when preparing a parity check. Do not hand-type, visually reconstruct, or whitespace-normalize the fetched `<content>` block before running `compare-notion-sync.ps1`.
- Treat `ops/notion-workspace/tmp/` as a scratch validation area only. Never stage or commit artifacts from that folder; `test-closeout-sanity.ps1` should fail closeout if any `ops/notion-workspace/tmp/` path is staged.
- If `compare-notion-sync.ps1` fails, treat the doc as out of sync until the mismatch is resolved or Adam explicitly accepts the remaining drift. Visual inspection is not a substitute for a failed parity check.
- Ephemeral/runtime data (agent config, CRM records, live automation state) lives in Notion only.
- To refresh a local doc from Notion: use MCP to read the page, overwrite the local file.
- Skill sources follow the same rule: edit the repo copy first, validate, then publish installed copies to `$CODEX_HOME/skills` (default: `~/.codex/skills`).

## Closeout Protocol

For tasks that change local files in `ops/notion-workspace/`:

1. Edit the local source-of-truth files.
2. Push the mapped instruction docs to Notion via MCP when applicable, omitting the repo-only `<!-- Notion Page ID: ... -->` comment from the published body.
3. Spot-check the live Notion page to confirm the content landed correctly.
4. Update `session-active.md`, commit, and push.

If an autonomous repo-backed skill is executing the change, satisfy the required `HARDENED_GATE` before the first repo mutation.

## Planning Output (Repo Handoff)

`ops/notion-workspace/session-active.md` may contain a **Planning Output** section from Claude Code or Codex. When present:

1. Read it during First Steps.
2. Execute the listed changes using standing approval when they are already approved.
3. Mark changes as done in the session log only after the Codex review gate passes (or Adam explicitly accepts the findings).

The repo handoff remains the canonical shared mechanism for Claude Code and Codex work.

## Maintenance

When adding new agents, workflows, or databases, update:

1. The relevant doc in `ops/notion-workspace/docs/`
2. Agent SOPs in Notion (push from `docs/agent-sops.md`)

When changing a manual workflow skill:

- **Skills migrated to TheoryWellness** (`notion-action-items`, `notion-agent-config`, `notion-meeting-prep`, `pandoc-deliverable`): edit source at `c:\Users\adamj\Code\TheoryWellness\skills\<name>\SKILL.md`, then re-sync to `~/.claude/skills/` per the user-scope sync command in `TheoryWellness/CLAUDE.md`. Wrapper update propagates to all Claude Code sessions (including this repo) on next session start.
- **Skills still canonical here** (under `freed-solutions/skills/`): update the source, validate with `ops/notion-workspace/scripts/publish-codex-skills.ps1 -ValidateOnly`, publish the Codex copy to `$CODEX_HOME/skills`, and sync the Claude copy in `.claude/skills/` with `ops/notion-workspace/scripts/sync-claude-skill-wrappers.ps1`.

