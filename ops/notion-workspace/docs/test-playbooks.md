# Automation Test Playbooks

Step-by-step validation procedures for Codex skills, Notion Custom Agents, and manual workflows.

---

## Codex skill validation

Run before publishing:

1. Validate the changed repo skills with `ops/notion-workspace/scripts/publish-codex-skills.ps1 -ValidateOnly`.
2. Publish the changed Codex copies with `ops/notion-workspace/scripts/publish-codex-skills.ps1`.
3. Sync the Claude skill copies with `ops/notion-workspace/scripts/sync-claude-skill-wrappers.ps1`.
4. Validate the Claude skill copies with `ops/notion-workspace/scripts/sync-claude-skill-wrappers.ps1 -ValidateOnly`.
5. Confirm the installed copy in `$CODEX_HOME/skills/<skill-name>/SKILL.md` reflects the repo contract. On this workstation, the default resolves to `C:\Users\adamj\.codex\skills\<skill-name>\SKILL.md`.
6. Confirm `.claude/skills/<skill-name>/` mirrors the repo skill directory, including `SKILL.md` plus any `references/`, `agents/`, `scripts/`, or `assets/` files the skill needs.
7. Forward-test each changed skill on one realistic task without preloading the intended answer.

## Local client approval baseline

Validate the local client baseline any time a Notion-workspace change touches Claude project config, Codex local config, or the expected launch path:

1. Confirm `.claude/settings.json` and `.claude/settings.local.json` stay aligned on the Notion-workspace MCP allowlist, including `mcp__notion__*`, `mcp__google-workspace__*`, `mcp__playwright__*`, and any still-used legacy MCP namespaces not covered by those wildcards.
2. Confirm the Claude project baseline also allowlists the safe read-only shell discovery patterns used by kickoff and repo discovery, especially `Get-ChildItem`, `Get-Content`, `rg`, and `Select-String`.
3. Confirm `enableAllProjectMcpServers` stays enabled for Claude project runs and `enabledMcpjsonServers` still includes `playwright`.
4. Confirm `.mcp.json` remains the project-managed server surface and currently lists only `playwright`. Do not add Notion there until the project-scoped remote registration path is proven stable in the local client.
5. Confirm `~/.codex/config.toml` defines the dedicated `ops_notion_workspace` profile with `approval_policy = "on-failure"` and `sandbox_mode = "workspace-write"`, without changing the global default posture for unrelated repos.
6. Confirm `ops/notion-workspace/scripts/start-codex-notion-workspace.cmd` still launches Codex through the dedicated profile.

### Local client approval regression checks

- In Claude local, verify one safe `mcp__notion__*` read no longer triggers an unexpected client approval prompt when launched against the approved project baseline.
- In Claude local, verify `Get-ChildItem`, `Get-Content`, `Select-String`, and `rg` repo reads all run without unexpected client approval prompts when launched against the approved project baseline.
- Verify repo text discovery defaults to fixed-string matching, such as `rg -F` or `Select-String -SimpleMatch`, unless regex mode is explicitly required for the task.
- Temporarily remove or bypass `rg` and confirm kickoff discovery can fall back to `Select-String -SimpleMatch` or an equivalent read-only shell search path without leaving the allowlisted workflow.
- Run kickoff discovery from the repo root and from a non-repo working directory; confirm the workflow still scopes reads to the repo path and does not broaden into unrelated filesystem traversal.
- Attempt discovery with an absolute path or a `..` escape and confirm the workflow rejects the path instead of broadening the read scope.
- If a safe local fixture is available, include a symlink that points outside the repo and confirm the discovery path does not follow it.
- If `rg` is unavailable, verify the fallback discovery path uses repo-scoped PowerShell forms such as `Get-ChildItem -Path ops/notion-workspace -Recurse -File -Force | Where-Object { -not ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) } | Select-String -SimpleMatch -Pattern ...` rather than broad recursive reads.
- In Codex, run one session through the normal default startup and one through `ops/notion-workspace/scripts/start-codex-notion-workspace.cmd`; confirm the profile-backed launch removes the extra routine MCP approval prompts that the default launch still surfaces.
- In the profile-backed Codex session, run one safe Notion fetch and one bounded documented Notion-workspace action; confirm routine MCP reads or bounded playbook writes stay approval-free while repo gate prompts still appear where the contract requires them.
- Confirm the first repo edit in an autonomous repo-backed skill still stops at `HARDENED_GATE`.
- Confirm schema, destructive, bulk, or out-of-contract lifecycle work still stops at `GOVERNANCE_GATE`.
- Confirm non-workspace shell escalation behavior is unchanged.
- Confirm non-allowlisted or write-oriented shell actions still prompt for approval instead of piggybacking on the discovery baseline.

### notion-action-item regression checks

- Run once with a complete pre-loaded context bundle and once with only a URL or UUID for the same Action Item; confirm the pre-execution summary matches after any minimal refresh.
- Run once with a title search that returns multiple matching Action Items and confirm the skill stops for disambiguation instead of choosing one arbitrarily.
- Run once with a pre-loaded context bundle missing a required field and confirm the skill fetches the missing data before any risky action.
- Run once with a pre-loaded context bundle containing stale status or relations and confirm the skill refreshes the minimum required field set before execution.
- Run once with a pre-loaded context bundle containing stale notes or attachments and confirm only the stale fields are refreshed before execution.
- Run once with a pre-loaded context bundle that has no capture timestamp and confirm copied notes, relations, and attachments are treated as stale and refreshed as needed.
- Run once with a pre-loaded context bundle whose page ID does not exist, or whose supplied URL/UUID points at a different Action Item, and confirm the skill reports the mismatch and stops before execution.
- Run once with a standard Notion URL or UUID plus an explicit execution request and confirm the pre-execution summary matches the classic fetch-first path while bounded target note/content/`Status` updates do not require an extra approval loop.
- Run once with an attempted `Record Status` change outside a documented workflow or test path and confirm the skill triggers `GOVERNANCE_GATE` instead of applying it.
- Run once with unclear outbound recipients or outbound content and confirm the skill triggers the shared `HARDENED_GATE`.
- Run once with an empty or ambiguous gate response and confirm the skill re-asks before proceeding.

### notion-active-sesson regression checks

- Invoke the skill with a kickoff request such as "Review `ops/notion-workspace` and propose the next scaffolding updates"; confirm it reads `session-active.md`, `CLAUDE.md`, and `docs/agent-sops.md` before branching wider.
- Confirm the skill uses local or parallel repo discovery by default and does not assume delegation support.
- Confirm the kickoff summary names the active priorities, likely touched files, and validation path instead of returning a vague backlog dump.
- Confirm the skill asks only the minimum high-impact questions and does so through the shared `HARDENED_GATE` model, using native structured questioning when available and a deterministic chat halt otherwise.
- Confirm the skill uses `HARDENED_GATE` before repo file edits by naming the intended files and change types.
- Run once with an empty or ambiguous gate response and confirm the skill re-asks before proceeding.
- Confirm the skill does not recreate the retired Notion session-handoff ritual or invent a second handoff surface.

### notion-agent-config regression checks

- Run the skill on a no-op audit of one live agent and confirm it reads `docs/agent-sops.md` before opening the browser.
- Confirm it uses the documented direct Settings URL instead of wandering through the Notion sidebar.
- Confirm it captures current-state evidence and reports drift explicitly instead of silently changing unclear settings.
- Confirm clear safe runtime repairs can proceed without a new approval loop, while unclear drift triggers `HARDENED_GATE`.

### notion-agent-test regression checks

- Run the skill on one bounded `[TEST]` scenario and confirm it follows the matching section in `docs/test-playbooks.md`.
- Confirm it checks Recent Activity plus downstream Notion state instead of relying on a single signal.
- Confirm the final report includes trigger method, pass/fail checkpoints, issues found, and cleanup status.
- Confirm bounded `[TEST]` setup, cleanup, and reporting stay `UNGATED`, while out-of-playbook moves would trigger `HARDENED_GATE` or `GOVERNANCE_GATE`.

## Notion sync parity

Run for every repo doc changed in the session that maps to a live Notion instruction page:

1. Confirm the local doc's embedded `<!-- Notion Page ID: ... -->` comment, when present, matches the mapped page ID listed in `ops/notion-workspace/CLAUDE.md`.
2. Push the updated local doc to the mapped Notion page, omitting the repo-only `<!-- Notion Page ID: ... -->` comment from the published body.
3. Re-fetch the live page via MCP immediately after the update.
4. Assert the live page body does not contain the repo-only `<!-- Notion Page ID: ... -->` comment. If it does, treat the sync as failed.
5. Save the fetched live page body to a temp file and run `ops/notion-workspace/scripts/compare-notion-sync.ps1 -LocalFile <repo doc> -RemoteFile <saved live body>`.
6. Resolve any drift before marking the doc synced in `CLAUDE.md` or the handoff.

---

## Post-Meeting Agent

### Trigger

- Scheduled nightly sweep
- Property change: Meetings -> `Record Status = Active`
- Manual `@mention`

### Setup

1. Create or identify a `[TEST]` meeting page with transcription-like content and typed notes.
2. For property-trigger testing, leave the page in `Draft`.
3. For duplicate protection testing, create a matching no-notes scenario in the same date window.

### Fire

- **Active-path test**: set `Record Status = Active`
- **Nightly-path proxy**: use `Run agent` or wait for the nightly sweep
- **Manual test**: `@Post-Meeting Agent` on the page

### Verify

- [ ] CRM wiring block added once
- [ ] Contacts and Companies wired correctly
- [ ] No duplicate no-notes meeting created
- [ ] Curated summary added only on Active/manual path
- [ ] Agent Config `Last Successful Run` updated

### Cleanup

Set test records to `Delete` only after verifying downstream unwiring expectations.

---

## Curated Notes Agent

### Trigger

- Manual `@mention` only

### Setup

Use one meeting page, one email page, or a mixed audit page containing explicit record links.

### Fire

Mention the agent with a bounded audit request such as:
`@Curated Notes Agent Audit this meeting for duplicate risk, partial runs, and schema drift.`

### Verify

- [ ] The response is an audit report, not a new CRM record
- [ ] No `Record Status` changes occur
- [ ] No new Action Items, Contacts, or Companies are created
- [ ] Findings reference concrete evidence from the reviewed records

### Cleanup

Remove only disposable test notes if needed.

---

## Delete Unwiring Agent

### Trigger

Property change: `Record Status = Delete` on any of the five source DBs

### Setup

1. Create a `[TEST]` record with live relations.
2. Document the expected reciprocal relations before firing.

### Fire

Set the test record to `Delete`.

### Verify

- [ ] All direct relations clear
- [ ] Reciprocal relations clear
- [ ] Notes explain why the record is ready for hard delete
- [ ] QC converges to `TRUE`

### Cleanup

Adam hard-deletes from the UI when appropriate.

---

## Contact & Company Agent

### Trigger

- Scheduled nightly run
- Manual `@mention`

### Setup

Use:

- a Draft contact with sparse fields
- a placeholder company that still has a raw domain name
- an Active record with a QC gap that has been waiting in backlog

### Verify

- [ ] Placeholder company corrected when evidence exists
- [ ] `States = All` corrected when better evidence exists
- [ ] Verified alternate domains appended to `Additional Domains`
- [ ] Older unresolved records are not starved by newer ones
- [ ] Company mismatch cases are flagged, not silently rewired

---

## Post-Email Agent

### Trigger

- Scheduled about 10:30 PM ET
- Manual `@mention`

### Setup

Cover these cases:

- bot-only thread
- generic-domain thread
- existing Thread ID with missing `Email Notes`
- thread with an action item but no explicit due date
- `Primitiv/PRI_Outlook` forwarded email
- `Primitiv/PRI_Teams` notification with a real follow-up
- `LinkedIn` notification with enough participant detail to wire CRM safely
- `DMC/DMC_GMail` routed company-mail thread that should process as standard email
- `adamjfreed@gmail.com` thread with personal-mailbox labels that should still process as standard email
- `Action Items`-labeled manual-queue thread that should remain untouched

Before running the workflow, verify the live mail connections keep least privilege. `Send` and `Draft` should stay off. If inbox-modify is available, use it only for marking terminal threads read; if it is unavailable, log the drift and confirm the workflow still avoids send or draft behavior.

### Verify

- [ ] Existing partial Email record is resumed, not duplicated
- [ ] Bot-only threads remain record-only with no Contacts or Action Items
- [ ] Bot-only threads are marked `Inactive` after explicit classification so they do not linger as Draft QC gaps
- [ ] Teams and LinkedIn notification wrappers are not misclassified as bot-only just because the sender is automated
- [ ] Routed labels are preserved on the Email record
- [ ] `DMC/DMC_GMail` routes into normal CRM email processing rather than being treated like a chat-notification wrapper
- [ ] `adamjfreed@gmail.com` stays in sweep scope, but its labels do not trigger routing or skip behavior
- [ ] `Action Items` or `Action Items/...` queue labels are ignored, left unread, and do not create or update CRM records
- [ ] Terminally processed threads are marked read, while ambiguous threads stay unread
- [ ] Action Items never have blank Company
- [ ] Due Date fallback note is present when no deadline was stated
- [ ] Agent Config timestamp updates after success

---

## LinkedIn Messages fallback workflow

### Trigger

- Manual recovery only

### Setup

Use:

- one Gmail-thread-backed LinkedIn conversation where notification email was insufficient
- one existing CRM conversation with new LinkedIn messages
- one same-name ambiguous contact case

### Verify

- [ ] Existing Thread ID records update instead of being skipped
- [ ] LinkedIn URL is not written on ambiguous same-name matches
- [ ] The workflow is only used as fallback after notification-email intake proved insufficient or unavailable
