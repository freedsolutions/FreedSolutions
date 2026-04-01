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
| `docs/agent-sops.md` | `323adb01-222f-81d7-bc47-c32cfea460f4` | Canonical operating model: agents, workflows, schema, runtime baseline, and manual operator rules | 2026-04-01 |
| `docs/post-meeting.md` | `324adb01-222f-8168-a207-d66e81884454` | Post-Meeting Agent: 4-step pipeline (CRM wiring -> Floppy -> notes-primary action items with summary/transcript fallback -> curated summary). Uses live `Calendar Name` options only. | 2026-03-29 |
| `docs/contact-company.md` | `323adb01-222f-8126-9db8-df77be5a326f` | Contact & Company Agent: nightly enrichment for Draft records plus Active QC gaps, with placeholder correction and backlog fairness rules | 2026-03-29 |
| `docs/merge-workflow.md` | `323adb01-222f-8111-89c7-c92eaac10ebb` | Merge and dedup workflows | 2026-03-22 |
| `docs/floppy-design.md` | - | Floppy voice-command CRM agent design doc (local only) | - |
| `docs/notetaker-crm.md` | `324adb01-222f-80ca-af0a-cd455329d8e8` | Notetaker CRM: paste into Notion Calendar AI settings | 2026-03-21 |
| `docs/curated-notes.md` | `325adb01-222f-8148-b544-f592271f34e3` | Curated Notes Agent: manual-only QA reviewer for meetings, email runs, and CRM drift audits | 2026-03-20 |
| `docs/post-email.md` | `325adb01-222f-81d3-825a-d3e0c74c0e30` | Post-Email Agent: Gmail sweep -> CRM wiring -> schema-safe action items -> thread summary with partial-run recovery | 2026-04-01 |
| `docs/linkedin-messages.md` | - | Local-only fallback for manual LinkedIn DM recovery when notification-email intake is insufficient | - |
| `docs/domain-intake.md` | - | Operator checklist for new domain routing-tier decisions from Post-Email intake | - |
| `docs/test-playbooks.md` | - | Validation playbooks for agents, workflows, and Codex skill migration | - |
| `docs/sub-agent-contract.md` | - | Sub-agent delegation contract: bootstrap, gates, results, depth limits, parallel execution, and scaffold profiles | - |

## Codex Skills

Repo skill sources live under `ops/notion-workspace/skills/`. They are the canonical source for both Codex and Claude. Installed Codex copies belong in `$CODEX_HOME/skills` (default: `~/.codex/skills`; Windows default: `C:\Users\adamj\.codex\skills`). Claude should use synced generated skill copies under `.claude/skills/` produced from the repo with `ops/notion-workspace/scripts/sync-claude-skill-wrappers.ps1`.

| Skill | Canonical Source | Purpose |
|------|------------------|---------|
| `notion-active-session` | `ops/notion-workspace/skills/notion-active-session/` | Kick off the repo handoff, surface priorities, and route the session into the next scaffolding or workflow step |
| `notion-action-item` | `ops/notion-workspace/skills/notion-action-item/` | Work a single Action Item end-to-end from CRM wiring through deliverable creation and bounded target updates |
| `notion-agent-config` | `ops/notion-workspace/skills/notion-agent-config/` | Audit or update Notion Custom Agent settings against the local config spec |
| `notion-agent-test` | `ops/notion-workspace/skills/notion-agent-test/` | Run smoke or regression tests for Notion Custom Agents using the local playbooks |
| `notion-meeting-prep` | `ops/notion-workspace/skills/notion-meeting-prep/` | Surface open Action Items and recent emails for a Meeting's attendees before a call |

Publish or validate them with `ops/notion-workspace/scripts/publish-codex-skills.ps1`.

The `Notion Page ID` values in the local-doc table above are the canonical page mapping. Individual repo docs may also carry a local `<!-- Notion Page ID: ... -->` comment for convenience, but that comment is optional and must never appear in a live Notion page.

## Session Files

The repo is the canonical home for session handoff docs.

| File or Path | Purpose |
|--------------|---------|
| `ops/notion-workspace/session-active.md` | Canonical active handoff, priorities, and next actions |

## Architecture Track

`ops/notion-workspace/freed-solutions-execution-checklist.md` documents the planned local-first CRM architecture under `ops/local_db/`. This execution brief is **currently frozen** pending completion of the cross-contextual agent instruction work. See `session-active.md` for active priorities.

- Do not start new `ops/local_db` work until the freeze is lifted.
- The checklist remains in the repo as a future-state reference.
- If a task appears to require local DB work, flag it and redirect to the Notion-native approach in the current priorities.

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
5. **Use repo skill sources for manual operator work.** Task-specific manual workflows belong in `ops/notion-workspace/skills/`, not in ad hoc slash-command notes.
6. **Never create new CRM DB records** unless explicitly instructed, except bounded `[TEST]` records or disposable audit pages required by the documented playbooks.
7. **Never change `Record Status`** (`Draft`/`Active`) without explicit instruction. Agents create Draft records and never change Record Status. Archiving and deletion (trash) are Adam's UI-managed steps.
8. **Log everything** - `ops/notion-workspace/session-active.md` is the session system of record.
9. **Dedup checks are mandatory** - always check Email + Secondary Email + Tertiary Email for contacts, Domains + Additional Domains for companies.
10. **UI steps require Adam's confirmation before marking complete.** Some tasks can only be done in the Notion UI (configuring agent triggers, pasting content too large for API, Settings changes). When a planning output or session priority includes a UI step: (a) explicitly list it as "Adam - UI step", (b) do NOT mark it complete until Adam confirms in the chat that it's done, (c) do not assume completion based on page existence or other indirect signals.
11. **Verify content on sync, not just existence.** When marking a Notion page as "in sync" with a local doc, verify the actual content matches - not just that the page exists.
12. **Do not claim a clean close-out with a dirty tree.** Before saying the task is done, inspect `git status --short` and disclose any unrelated modified or untracked files instead of calling the worktree clean. If unrelated local changes are present, keep them out of the review conclusion by narrowing the review gate to the intended paths.
13. **Sub-agent delegation follows `docs/sub-agent-contract.md`.** Never delegate `GOVERNANCE_GATE` decisions. Never exceed depth 1. Never spawn parallel sub-agents with overlapping write targets.

## Skill Gate Protocol

Repo-backed Notion skills use this shared gate taxonomy:

| Gate | Meaning |
|------|---------|
| `UNGATED` | Proceed without pausing. |
| `HARDENED_GATE` | Ask one compact decision-shaped question using native structured questioning when available; otherwise use a deterministic short chat halt. If the reply is empty, unclear, or ambiguous, re-ask before proceeding. Never treat silence as approval. |
| `GOVERNANCE_GATE` | Use the same pause mechanism as `HARDENED_GATE`, but only when the existing Rules of Engagement require a pause. |

When a repo-backed skill is executing autonomously, any repo/code mutation must go through `HARDENED_GATE` before the first edit, even when the broader workflow is standing-approved. This includes edits under `docs/`, `skills/`, `ops/notion-workspace/CLAUDE.md`, `ops/notion-workspace/session-active.md`, and repo scripts. Outside an autonomous skill run, the normal standing-approval rules still apply.

## Sub-Agent Delegation

When Claude Code or Codex spawns sub-agents (via the `Agent` tool or `codex exec`), follow the sub-agent delegation contract in `docs/sub-agent-contract.md`. Core rules:

- **Depth limit:** Maximum delegation depth is 1 (parent -> sub-agent, no further nesting).
- **Gate ceiling:** Sub-agents inherit at most `HARDENED_GATE`. `GOVERNANCE_GATE` decisions are never delegated — the sub-agent returns `needs_escalation` and the parent asks Adam.
- **Parallel safety:** Parallel sub-agents must have completely disjoint `write_paths`. For Notion DB record creation, the parent must assign disjoint source sets, run a post-collection dedup check, or serialize through one sub-agent.
- **Scaffold profiles:** Sub-agents load conventions from lightweight context cards under `docs/cards/` instead of parsing full docs. Four profiles are available: `explorer`, `crm-worker`, `validator`, `scaffolding-editor`.
- **Result contract:** Every sub-agent returns a typed JSON envelope with `status`, `summary`, `findings`, `mutations_performed`, and optional escalation or error detail.
- **Validator support:** Use `ops/notion-workspace/scripts/test-sub-agent-contract.ps1` for repo-stored manifest/result fixtures and parent-side preflight examples.

## Local Client Approval Baseline

The shared `UNGATED` / `HARDENED_GATE` / `GOVERNANCE_GATE` taxonomy is the repo workflow contract, not a local client-approval bypass. A task marked `UNGATED` means "no extra workflow pause" inside the documented process; Claude or Codex can still surface routine MCP approval prompts if the local session is launched without the expected client baseline.

For routine `ops/notion-workspace` work on this workstation:

- **Claude project baseline** lives in a repo-tracked `.claude/settings.json` plus the workstation overlay `.claude/settings.local.json`. Keep the shared Notion-workspace baseline entries aligned between both files: `mcp__notion`, `mcp__google-workspace`, `mcp__playwright`, the still-needed legacy `mcp__claude_ai_Notion__notion-{fetch,search,update-page,create-pages}` entries, `mcp__claude_ai_Gmail__gmail_read_message`, repo-scoped discovery shell commands, the minimal `Bash(grep *)` compatibility alias, `Bash(python scripts/codex_review.py *)`, and the exact script approvals for `compare-notion-sync.ps1`, `test-compare-notion-sync.ps1`, `test-closeout-sanity.ps1`, `test-closeout-sanity-guard.ps1`, `publish-codex-skills.ps1`, `sync-claude-skill-wrappers.ps1`, `test-approval-baseline.ps1`, `test-discovery-scope.ps1`, and `test-sub-agent-contract.ps1`. Claude MCP permissions do not support `*` wildcards, so approve the server name itself when the intent is "all tools from this MCP server." Keep unrelated workstation shell helpers, non-Notion project allowances, and any `additionalDirectories` out of `.claude/settings.json`; those belong in `.claude/settings.local.json` only. Workstation extras must not replace or omit the shared baseline entries from `.claude/settings.json`. `enableAllProjectMcpServers` should stay on, and `enabledMcpjsonServers` should include `playwright`.
- **Repo-scoped discovery only.** Launch discovery from the repo root and keep read-only shell enumeration scoped to repo paths. Prefer exact repo-scoped forms such as `rg --files ops/notion-workspace`, `rg --no-follow -F <text> ops/notion-workspace`, and repo-rooted file reads under `ops/notion-workspace`.
- **PowerShell fallback shape.** If `rg` is unavailable, use explicit repo-scoped PowerShell fallback commands such as `Get-ChildItem -Path ops/notion-workspace -Recurse -File -Force | Where-Object { -not ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) }` for enumeration and pipe that result into `Select-String -SimpleMatch -Pattern <text>` for text search. Do not recurse against absolute paths, parent directories, or uncontrolled roots.
- **Discovery path enforcement.** Kickoff discovery should normalize candidate paths against the repo root, reject absolute paths and `..` segments that escape the repo, refuse discovery when the repo root cannot be resolved cleanly, and validate the helper behavior with `ops/notion-workspace/scripts/test-discovery-scope.ps1`.
- **Claude allowlist maintenance.** Keep `.claude/settings.local.json` mirrored to the repo-tracked `.claude/settings.json` baseline and keep the shared shell entries no broader than necessary to cover repo-scoped discovery, the documented approval validators, closeout helpers, and the Codex review runner without extra prompts.
- **Project MCP surface** lives in `.mcp.json`. Keep `playwright` there. Do not add the Notion MCP server to `.mcp.json` unless the local client proves the same remote-server registration path is stable for project-scoped use; until then, Notion remains configured in the user's local client config.
- **Codex default baseline** should keep the dedicated `ops_notion_workspace_quiet` profile in `~/.codex/config.toml` at `approval_policy = "never"` and `sandbox_mode = "workspace-write"` for routine Notion-workspace sessions, while preserving the existing `mcp_servers` entries. Validate the exact profile values with `ops/notion-workspace/scripts/test-approval-baseline.ps1`.
- **Codex safe fallback baseline** should keep `ops_notion_workspace` in `~/.codex/config.toml` at `approval_policy = "on-failure"` and `sandbox_mode = "workspace-write"` for explicit safer runs that still surface local client approvals. Reuse the same top-level `mcp_servers`; do not duplicate or move them into either profile.
- **Preferred Windows launch paths** are `ops/notion-workspace/scripts/start-codex-notion-workspace.cmd` for the default quiet lane with an automatic fallback to the safe profile when the quiet profile is missing locally, `ops/notion-workspace/scripts/start-codex-notion-workspace-quiet.cmd` as a compatibility alias to the direct quiet lane, and `ops/notion-workspace/scripts/start-codex-notion-workspace-safe.cmd` for the explicit safer lane, or the equivalent `codex.cmd -p <profile> -C <repo-root>`. All repo launchers should validate the selected profile with `ops/notion-workspace/scripts/test-approval-baseline.ps1` before calling Codex. If `~/.codex/config.toml` itself is missing, fail fast with the remediation banner instead of silently dropping into an unknown profile. Keep using `codex.cmd`, not bare `codex`, so PowerShell execution-policy issues around `codex.ps1` do not reintroduce friction.
- **Playwright MCP baseline** is approval-free in the default repo launch lane. Routine `mcp__playwright` navigation, capture, and bounded UI actions inside documented Notion-workspace flows should not trigger extra local client approval prompts on this workstation.
- **Playwright bounds still apply.** Do not treat the quiet baseline as blanket approval for arbitrary browser eval, broad artifact writes, or out-of-workspace file access. Keep Playwright use inside the documented browser tools, repo/workspace-scoped outputs, and task-approved domains, normally the Notion workspace and localhost preview/test surfaces. Treat broader browsing as a task-specific decision, not as part of the standing baseline; only the normal repo workflow gates should pause the work.
- **Quiet mode is a client baseline only.** The default quiet Codex lane suppresses local client approval prompts, but it does not waive repo workflow gates. Repo/code mutations inside autonomous repo-backed skills still require `HARDENED_GATE`, and schema, destructive, bulk, or out-of-contract lifecycle moves still require `GOVERNANCE_GATE`.
- **Runtime proof remains explicit.** Treat the baseline as enforced only after `ops/notion-workspace/scripts/test-approval-baseline.ps1` passes and the short manual smoke in `docs/test-playbooks.md` confirms routine MCP work is approval-free while the normal repo gates still fire.

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
- **Contacts DB:** Contact Name (title), Display Name (formula), QC (formula), Email, Secondary Email, Tertiary Email, Phone, Pronouns, Nickname, LinkedIn, Company, Role / Title, Record Status, Contact Notes
- **Companies DB:** Company Name (title), Company Type (select: Tech Stack, Operator, Network, Personal), QC (formula), Domains (rich_text), Additional Domains (rich_text), States (multi_select: MA, MI, CT, NJ, FL, OH, PA, CA, All, AR, MO, MS, LA; default: "All"), Website, Contacts, Emails (rollup), Meetings (rollup), Action Items, Engagements, Tech Stack, Record Status, Company Notes. *Legacy fields — the Domains DB is the primary domain lookup. Domains and Additional Domains are retained during transition.*
- **Domains DB:** Domain (title), 💼 Companies (relation), Routing Tier (select: Label, Silent Label, Archive, Block, Draft Intake, None), Filter Shape (select: Domain, Sender, None), Gmail Label (rich_text), Gmail Filter ID (rich_text), Is Generic (checkbox), Source Type (select: Primary, Additional, Sender-Level), Notes (rich_text), Record Status (select: Draft, Active)
- **Action Items DB:** Task Name (title), Type (formula), Status, Priority, Record Status, Task Notes, Due Date, Created Date (created_time), Contact, Company, Assignee, Source Meeting, Source Email, Target Meeting, Target Email, Attach File, QC (formula)
- **Action Items Status = Review:** Indicates a response was received on a Follow Up or Task that needs Adam's assessment. Agents set Review; Adam resolves it (Done, back to In Progress, or other action).
- **Meetings DB:** Meeting Title (title), Calendar Event ID, Calendar Name, Date, Contacts, Companies (rollup), Action Items, Target Action Items, Series, Series Key, Instances, Is Series Parent, Series Status (rollup), Location, Record Status, QC (formula)
- **Emails DB:** Email Subject (title), Thread ID, From, Direction (formula), Date, Contacts, Companies (rollup), Action Items, Target Action Items, Labels (multi_select), Source (select: Email - Freed Solutions, Email - Personal, LinkedIn - DMs), Record Status, Email Notes, QC (formula), Created Timestamp
- **Email routing labels:** On `adam@freedsolutions.com`, `Primitiv` = all Primitiv-related mail (forwarded Outlook, Teams notifications, calendar invites). Dual-labeled threads: `Dutchie` (Looker reports) and `Intuit` (QB transactions) also carry the `Primitiv` label via `to:` filter overlap or explicit multi-label filter rules. `LinkedIn` = LinkedIn message-notification intake. `DMC` = DMC routed company-mail intake for the DMC client. `_Action Items` and any `_Action Items/...` sublabel are temporary ignore labels for manual filing, not active intake lanes. Other company or project labels are metadata only unless explicitly promoted into routing. Labels are the canonical intake-route truth for the Freed Solutions mailbox. `adamjfreed@gmail.com` remains in live sweep scope, but its labels are out of scope for routing. Teams notifications keep the mailbox-derived `Source`; the `Labels` multi_select carries the routing metadata instead of a dedicated Teams source option.
- **New source filter contract:** When a newly retained thread introduces a stable new Company or Contact source that should route future mail, dedup the CRM records first, then create or refresh the Gmail label using the existing live naming pattern: the top-level client label (for example `Primitiv` or `DMC`) or the exact stable company label Adam already uses when no child lane is needed. Add the matching option to `Emails.Labels`, default to company/domain filters, use sender-specific filters only for exceptions, keep new filters label-first instead of auto-read by default, and archive/read only after post-processing reaches terminal state.
- **Action Item provenance vs. target context:** `Source Meeting` / `Source Email` capture where the work originated. `Target Meeting` / `Target Email` capture the optional future touchpoint where Adam wants to review, present, or close out the work. Leave the target fields blank unless Adam or an explicit Action Item workflow asks to wire them.
- **Target-link rollout note:** `Target Meeting` / `Target Email` are live in Adam's workspace as of March 24, 2026. If an older environment or copied workspace is missing them, pause and add the schema before relying on target-link behavior.
- **Page icon conventions:** New or repaired Meetings should use `🗓️`, Contacts `👤`, Emails `📧`, Action Items `🎬`, and Domains `🌐` unless an explicit manual exception already exists. Company page icons remain Adam-managed.
- **Email fields** (Contacts): Email, Secondary Email, Tertiary Email - all checked for dedup
- **Domain fields** (Companies): Domains (primary), Additional Domains (merged/subsidiary/sender-level) - both checked for dedup. `Additional Domains` may also hold full sender email addresses for platform companies where the domain is too broad (e.g., `workspace@google.com` for Google). When matching, check domains first, then fall back to full sender email address against `Additional Domains`.
- **Calendar Name** currently has live select options for `Adam - Business` and `Adam - Personal` only. Do not assume local placeholders such as `Manual` or `Pending` exist in the schema.
- **Series Key** stores the Google `recurringEventId` on recurring Meetings and their Series Parent row. Same-title meetings without a `Series Key` stay standalone unless Adam explicitly asks for a manual repair.
- **Delete path:** Trash the record directly in Notion. No intermediate status — `Delete` has been removed from the schema. Notion automatically clears reciprocal relations on linked records. Permanent delete from Notion trash is Adam's manual step.
- **Email parity + cleanup contract:** Compare Gmail parity by exact `Thread ID`, not by subject line or Gmail message count. Archived Email rows still count as already processed for parity. Gmail read-state changes only after a thread reaches terminal state: retained and wired, intentionally skipped, or classified as meeting-support-only. Truly unresolved exceptions may remain unread, but they must be listed explicitly.
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

## Legacy Closeout Protocol

The full 10-step deterministic closeout below was the active protocol through March 28, 2026. It is preserved here for re-enablement if the system reaches a state where deterministic parity and multi-step validation are worth the overhead. The lightweight protocol above is the current default.

<details>
<summary>Full 10-step protocol (archived)</summary>

1. Edit the local source-of-truth files.
2. Push the mapped instruction docs to Notion via MCP when applicable, omitting the repo-only `<!-- Notion Page ID: ... -->` comment from the published body.
3. Re-fetch the updated Notion pages and first confirm the live page body does not contain the repo-only `<!-- Notion Page ID: ... -->` comment.
4. Save the fetched live page body to `ops/notion-workspace/tmp/notion-sync-remote-YYYY-MM-DD-<doc>.md` and run `ops/notion-workspace/scripts/compare-notion-sync.ps1 -LocalFile <repo doc> -RemoteFile <saved live body>` to verify deterministic sync parity.
5. If parity fails, stop. Do not mark the doc synced, do not replace the failed parity gate with visual verification, and do not update the handoff, commit, or push until the mismatch is resolved or Adam explicitly accepts the remaining drift.
6. If the task changed repo skill sources or `.claude/skills/`, run `ops/notion-workspace/scripts/sync-claude-skill-wrappers.ps1 -ValidateOnly` to confirm the Claude copies still mirror the canonical repo skills.
7. Run `ops/notion-workspace/scripts/test-closeout-sanity.ps1` and disclose any untracked-file warnings before close-out. Treat any mojibake findings as blocking.
8. Run the Codex review gate on the current worktree. If unrelated local changes are present, pass repeated `--pathspec <repo path or glob>` arguments so the review only covers the intended files.
9. Only after the review passes or its findings are explicitly accepted, update `ops/notion-workspace/session-active.md`.
10. Then commit and push to `main`.

</details>

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

1. Update the canonical repo skill under `ops/notion-workspace/skills/`
2. Validate it with `ops/notion-workspace/scripts/publish-codex-skills.ps1 -ValidateOnly`
3. Publish the installed copy to `$CODEX_HOME/skills` (default: `~/.codex/skills`)
4. Sync the Claude skill copy in `.claude/skills/` with `ops/notion-workspace/scripts/sync-claude-skill-wrappers.ps1`

When creating new scaffold profiles or context cards, update the manifest in `docs/sub-agent-contract.md` and verify that existing context cards under `docs/cards/` still reflect the current canonical source values.
