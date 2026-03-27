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
8. If a skill was renamed, run `ops/notion-workspace/scripts/test-skill-rename-cleanup.ps1 -OldName <old-name> -NewName <new-name> -RequireClaudeCopy -RequireInstalledCopy` after publish and sync.

## Close-out sanity

Run before the review gate whenever the session changed files under `ops/notion-workspace/` or `.claude/skills/`:

1. Run `ops/notion-workspace/scripts/test-closeout-sanity.ps1`.
2. Treat any mojibake findings as blocking. Fix the encoding issue before review, handoff, or commit.
3. If the script reports untracked files, either include them intentionally or disclose them as out-of-scope leftovers before claiming the task is clean.
4. If unrelated local changes remain in the worktree, run the review gate with repeated `--pathspec <repo path or glob>` arguments so the review only covers the intended files.
5. Use `-RequireCleanScope` only when the scoped tree is expected to be fully clean at the end of the task.

## Local client approval baseline

Validate the local client baseline any time a Notion-workspace change touches Claude project config, Codex local config, or the expected launch path:

1. Run `ops/notion-workspace/scripts/test-approval-baseline.ps1` and keep it green before relying on the quiet lane.
2. Confirm `.claude/settings.json` and `.claude/settings.local.json` stay aligned on the shared Notion-workspace baseline entries: `mcp__notion`, `mcp__google-workspace`, `mcp__playwright`, the still-needed legacy `mcp__claude_ai_Notion__notion-{fetch,search,update-page,create-pages}` entries, `mcp__claude_ai_Gmail__gmail_read_message`, the repo-scoped discovery shell patterns, and the script-specific approvals for `compare-notion-sync.ps1`, `test-closeout-sanity.ps1`, `publish-codex-skills.ps1`, and `sync-claude-skill-wrappers.ps1`. Claude MCP permissions do not support `*` wildcards.
3. Confirm the Claude project baseline also allowlists the safe read-only shell discovery patterns used by kickoff and repo discovery, especially `Get-ChildItem`, `Get-Content`, `rg`, and `Select-String`.
4. Confirm `enableAllProjectMcpServers` stays enabled for Claude project runs and `enabledMcpjsonServers` still includes `playwright`.
5. Confirm `.mcp.json` remains the project-managed server surface and currently lists only `playwright`. Do not add Notion there until the project-scoped remote registration path is proven stable in the local client.
6. Confirm `~/.codex/config.toml` keeps the dedicated `ops_notion_workspace_quiet` profile with `approval_policy = "never"` and `sandbox_mode = "workspace-write"` as the default repo lane, without changing the global default posture for unrelated repos.
7. Confirm `~/.codex/config.toml` also defines `ops_notion_workspace` with `approval_policy = "on-failure"` and `sandbox_mode = "workspace-write"` as the explicit safer fallback, while leaving the top-level `mcp_servers` block unchanged.
8. Confirm `ops/notion-workspace/scripts/start-codex-notion-workspace.cmd` prefers the quiet profile and falls back to the safer profile with a clear banner when the quiet profile is missing locally, exits non-zero with remediation when `~/.codex/config.toml` itself is missing, `ops/notion-workspace/scripts/start-codex-notion-workspace-quiet.cmd` remains a quiet compatibility alias, and `ops/notion-workspace/scripts/start-codex-notion-workspace-safe.cmd` launches through the safer profile after validating the selected profile with `test-approval-baseline.ps1`.

### Local client approval regression checks

- In Claude local, verify one safe Notion MCP read under the approved `mcp__notion` server no longer triggers an unexpected client approval prompt when launched against the approved project baseline.
- In Claude local, verify one safe `mcp__playwright__browser_tabs` or similar read-only Playwright call no longer triggers an unexpected client approval prompt when launched against the approved project baseline.
- In Claude local, verify `Get-ChildItem`, `Get-Content`, `Select-String`, and `rg` repo reads all run without unexpected client approval prompts when launched against the approved project baseline.
- Run `ops/notion-workspace/scripts/test-discovery-scope.ps1` to verify the shared repo-scope helper rejects absolute paths and `..` escapes before depending on kickoff discovery.
- Verify repo text discovery defaults to fixed-string matching, such as `rg -F` or `Select-String -SimpleMatch`, unless regex mode is explicitly required for the task.
- Temporarily remove or bypass `rg` and confirm kickoff discovery can fall back to `Select-String -SimpleMatch` or an equivalent read-only shell search path without leaving the allowlisted workflow.
- Run kickoff discovery from the repo root and from a non-repo working directory; confirm the workflow still scopes reads to the repo path and does not broaden into unrelated filesystem traversal.
- Attempt discovery with an absolute path or a `..` escape and confirm the workflow rejects the path instead of broadening the read scope.
- If a safe local fixture is available, include a symlink that points outside the repo and confirm the discovery path does not follow it.
- If `rg` is unavailable, verify the fallback discovery path uses repo-scoped PowerShell forms such as `Get-ChildItem -Path ops/notion-workspace -Recurse -File -Force | Where-Object { -not ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) } | Select-String -SimpleMatch -Pattern ...` rather than broad recursive reads.
- In Codex, run one session through the normal default startup, one through `ops/notion-workspace/scripts/start-codex-notion-workspace.cmd`, one through `ops/notion-workspace/scripts/start-codex-notion-workspace-quiet.cmd`, and one through `ops/notion-workspace/scripts/start-codex-notion-workspace-safe.cmd`; confirm the repo launchers default to the approval-free quiet MCP posture while the safe lane preserves the current `on-failure` behavior that generic startup may still surface.
- For each repo launcher, confirm stdout prints the active Codex profile and resolved repo root before Codex starts so the quiet-versus-safe lane is visible at launch time.
- Temporarily remove or rename `~/.codex/config.toml` on a safe local fixture and confirm `ops/notion-workspace/scripts/start-codex-notion-workspace.cmd` exits non-zero with the remediation banner instead of silently choosing an unknown profile.
- Temporarily remove or rename the quiet profile in `~/.codex/config.toml` on a safe local fixture and confirm `ops/notion-workspace/scripts/start-codex-notion-workspace.cmd` falls back to the safe profile with the remediation banner instead of failing hard.
- With `%APPDATA%\npm\codex.cmd` temporarily unavailable, confirm all three repo launchers fall back to `where codex.cmd`; if PATH discovery also fails, confirm they exit non-zero with the remediation message instead of silently launching bare `codex`.
- In the default repo-launch or explicit quiet Codex session, run one safe Playwright MCP call and one safe Notion fetch; confirm routine MCP reads stay approval-free.
- In the default repo-launch or explicit quiet Codex session, run one bounded Playwright UI action such as navigate, click, and capture; confirm the UI action remains approval-free while repo workflow gates still fire where the contract requires them.
- In the default repo-launch or explicit quiet Codex session, verify Playwright navigation stays inside the task-approved domains for the workflow, normally the Notion workspace or localhost fixtures, and treat any broader domain reach as out of baseline until the task explicitly requires it.
- In the default repo-launch or explicit quiet Codex session, run one Playwright artifact write that stays inside the repo or workspace and one attempted outside-path write; confirm the bounded write succeeds and the outside-path write is blocked by the workspace-write sandbox.
- In the default repo-launch or explicit quiet Codex session, run one bounded documented Notion-workspace write path such as `notion-update-page`; confirm the repeated local prompt to allow the Notion MCP server tool no longer appears while repo gate prompts still surface where the contract requires them.
- Confirm the first repo edit in an autonomous repo-backed skill still stops at `HARDENED_GATE`.
- Confirm schema, destructive, bulk, or out-of-contract lifecycle work still stops at `GOVERNANCE_GATE`.
- Confirm non-workspace shell escalation behavior is unchanged.
- In Claude local or the explicit Codex safe profile, confirm non-allowlisted or write-oriented shell actions still prompt for approval instead of piggybacking on the discovery baseline.

### notion-action-item regression checks

- Before running the target-link behavior checks, fetch the live `Action Items`, `Meetings`, and `Emails` data sources and confirm the schema still exposes `Target Meeting`, `Target Email`, and reciprocal `Target Action Items` with those exact property names.
- Run once with a complete pre-loaded context bundle and once with only a URL or UUID for the same Action Item; confirm the pre-execution summary matches after any minimal refresh.
- Run once with a title search that returns multiple matching Action Items and confirm the skill stops for disambiguation instead of choosing one arbitrarily.
- Run once with a pre-loaded context bundle missing a required field and confirm the skill fetches the missing data before any risky action.
- Run once with a pre-loaded context bundle containing stale status or relations and confirm the skill refreshes the minimum required field set before execution.
- Run once with a pre-loaded context bundle containing stale notes or attachments and confirm only the stale fields are refreshed before execution.
- Run once with a pre-loaded context bundle that has no capture timestamp and confirm copied notes, relations, and attachments are treated as stale and refreshed as needed.
- Run once with a pre-loaded context bundle whose page ID does not exist, or whose supplied URL/UUID points at a different Action Item, and confirm the skill reports the mismatch and stops before execution.
- Run once with a standard Notion URL or UUID plus an explicit execution request and confirm the pre-execution summary matches the classic fetch-first path while bounded target note/content/`Status` updates do not require an extra approval loop.
- Run once with target relations already wired and once without them for the same Action Item; confirm the pre-execution summary reports source and target context separately after the minimum refresh.
- Run once with stale or missing `Target Meeting` / `Target Email` details in a pre-loaded bundle and confirm the minimum refresh pulls the live target relations before risky work.
- Run once with an explicit request to wire or rewire `Target Meeting` or `Target Email` and confirm only those target relations change while `Record Status` stays untouched unless separately authorized.
- Run once with an attempted `Record Status` change outside a documented workflow or test path and confirm the skill triggers `GOVERNANCE_GATE` instead of applying it.
- Run once with unclear outbound recipients or outbound content and confirm the skill triggers the shared `HARDENED_GATE`.
- Run once with an empty or ambiguous gate response and confirm the skill re-asks before proceeding.

### notion-active-session regression checks

- Invoke the skill with a kickoff request such as "Review `ops/notion-workspace` and propose the next scaffolding updates"; confirm it reads `session-active.md`, `CLAUDE.md`, and `docs/agent-sops.md` before branching wider.
- When the request touches `ops/local_db`, direct Gmail or GCal ingestion, SQLite sync, or broader CRM architecture migration, confirm the skill also reads `ops/notion-workspace/freed-solutions-execution-checklist.md` and calls out any conflict with the current handoff before editing.
- Run `ops/notion-workspace/scripts/test-skill-rename-cleanup.ps1 -OldName <old-name> -NewName notion-active-session -RequireClaudeCopy -RequireInstalledCopy` and confirm it reports no lingering matches or stale skill paths when the rename is meant to be complete.
- Confirm the skill uses local or parallel repo discovery by default and does not assume delegation support.
- Confirm the kickoff summary names the active priorities, likely touched files, and validation path instead of returning a vague backlog dump.
- Confirm the skill asks only the minimum high-impact questions and does so through the shared `HARDENED_GATE` model, using native structured questioning when available and a deterministic chat halt otherwise.
- Confirm the skill bundles all currently known `HARDENED_GATE` items into one compact prompt instead of serial pauses.
- Confirm the skill uses `HARDENED_GATE` before repo file edits by naming the intended files and change types.
- Confirm the skill continues autonomously after the bounded slice is approved unless a new ambiguity or `GOVERNANCE_GATE` condition appears.
- Run once with an empty or ambiguous gate response and confirm the skill re-asks before proceeding.
- Confirm the skill does not recreate the retired Notion session-handoff ritual or invent a second handoff surface.
- Confirm the published Codex skill lives at `$CODEX_HOME/skills/notion-active-session/` and the stale retired-skill path is absent after a full rename.

### notion-agent-config regression checks

- Run the skill on a no-op audit of one live agent and confirm it reads `docs/agent-sops.md` before opening the browser.
- Confirm it uses the documented direct Settings URL instead of wandering through the Notion sidebar.
- Confirm it captures current-state evidence and reports drift explicitly instead of silently changing unclear settings.
- Confirm the skill bundles all currently known unclear drift into one compact `HARDENED_GATE` prompt instead of serial pauses.
- Confirm clear safe runtime repairs can proceed without a new approval loop, while unclear drift triggers `HARDENED_GATE`.
- Confirm the skill continues autonomously after the bounded repair slice is approved unless a new ambiguity or `GOVERNANCE_GATE` condition appears.

### notion-agent-test regression checks

- Run the skill on one bounded `[TEST]` scenario and confirm it follows the matching section in `docs/test-playbooks.md`.
- Confirm it checks Recent Activity plus downstream Notion state instead of relying on a single signal.
- Confirm the final report includes trigger method, pass/fail checkpoints, issues found, and cleanup status.
- Confirm the skill bundles all currently known off-playbook questions into one compact `HARDENED_GATE` prompt instead of serial pauses.
- Confirm bounded `[TEST]` setup, cleanup, and reporting stay `UNGATED`, while out-of-playbook moves would trigger `HARDENED_GATE` or `GOVERNANCE_GATE`.
- Confirm the skill continues autonomously after a bounded off-playbook slice is approved unless a new ambiguity or `GOVERNANCE_GATE` condition appears.

## Notion sync parity

Run for every repo doc changed in the session that maps to a live Notion instruction page:

1. Confirm the local doc's embedded `<!-- Notion Page ID: ... -->` comment, when present, matches the mapped page ID listed in `ops/notion-workspace/CLAUDE.md`.
2. Push the updated local doc to the mapped Notion page, omitting the repo-only `<!-- Notion Page ID: ... -->` comment from the published body.
3. Re-fetch the live page via MCP immediately after the update.
4. Assert the live page body does not contain the repo-only `<!-- Notion Page ID: ... -->` comment. If it does, treat the sync as failed.
5. Save the fetched live page body to a temp file verbatim from the MCP fetch output. Do not hand-type, visually reconstruct, or whitespace-normalize the fetched `<content>` block before running the parity helper.
6. Run `ops/notion-workspace/scripts/compare-notion-sync.ps1 -LocalFile <repo doc> -RemoteFile <saved live body>`.
7. If parity fails, stop. Do not downgrade the failure to "visually verified", and do not mark the doc synced in `CLAUDE.md` or the handoff until the mismatch is resolved or Adam explicitly accepts it.

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

### Notes-sparse fallback regression

- Create one `[TEST]` meeting whose typed Notes are intentionally sparse or empty but whose summary/transcript contains one or two clear, high-confidence commitments.
- Verify fallback-created Action Items are limited to those clear commitments and do not convert vague discussion into tasks.
- Verify every fallback-created Action Item includes both `Source: Summary/transcript fallback recovery` and an `Evidence:` line in `Task Notes`.
- Verify any overlapping Floppy command still wins dedup over a fallback-derived item.
- Verify Notes-derived items remain primary when meaningful typed Notes are present; summary/transcript fallback should enrich or recover, not silently replace Notes parsing.

### Series/calendar recovery regression

- When multiple meeting recovery candidates exist, prioritize **Adam - Personal** before **Adam - Business**.
- Personal lane:
  - one recurring `Therapy (remote)` case that should auto-create or reuse a parent
  - one recurring `Therapy (onsite)` case that should auto-create or reuse a separate parent
  - one standalone same-title Therapy case that should stay ungrouped because Google does not return `recurringEventId`
  - one missing-`Calendar Name` case
  - one shared-personal-calendar identity case
- Business lane:
  - one forwarded-title or `FW:` normalization case
  - one recurring-instance case where parent reuse must key off `Series Key`, not repeated title
  - one no-notes recurring case that should create the Meeting row and attach to the correct parent in the same pass
  - one "funky" business case with wrong or missing `Series`, `Series Key`, or `Calendar Name`
- For each case, capture the recovery worksheet before repair under `ops/notion-workspace/tmp/post-meeting-recovery-worksheet-YYYY-MM-DD.md`:
  - Meeting Title
  - calendar source
  - current `Calendar Event ID`
  - current `Calendar Name`
  - current `Series`
  - current `Series Key`
  - whether a `transcription` block exists
  - expected outcome
  - repair method
  - exception reason if unrecoverable
- Verify recurring instances with `recurringEventId` auto-create or reuse the correct Series Parent and persist the same `Series Key` on both parent and child rows.
- Verify same-title one-off meetings without `recurringEventId` stay standalone.
- Verify recoverable cases land with the correct `Calendar Name`, `Series`, and `Series Key`, while unrecoverable cases are logged explicitly instead of patched heuristically.

### Target-link follow-up after meeting recovery

- Run only after the series/calendar recovery lane is stable.
- Verify `Target Meeting` / `Target Email` remain explicit-only and are not populated by default Post-Meeting wiring.
- Verify the source-vs-target distinction still matches the current skill/runtime contract.
- Verify no schema change, lifecycle mutation, or bulk rewiring is implied by the follow-up check.

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

## Trash-First Cleanup

### Trigger

Manual cleanup on a disposable test record that is ready for the current trash-first delete path.

### Setup

1. Create a `[TEST]` record with live relations.
2. Document the expected reciprocal relations before firing.

### Fire

Trash the test record using the current delete workflow. Set `Record Status = Delete` first only when that record type or test path still expects the annotation before trash.

### Verify

- [ ] Linked records clear the trashed record from their relation properties
- [ ] Reciprocal rollups and QC formulas converge after trash
- [ ] Any required delete annotation is present before trash when the workflow calls for it

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
- same-thread-family or multi-message input that could race Company or Contact creation
- thread with an action item but no explicit due date
- `Primitiv/PRI_Outlook` forwarded email
- `Primitiv/PRI_Teams` notification with a real follow-up
- `LinkedIn` notification with enough participant detail to wire CRM safely
- contextful share-notification mail that should be kept without creating an Action Item
- meeting invite reply churn (`Accepted:`, `Declined:`, `Tentative:`) that should be skipped and marked read with no Email record
- raw invite or update packet that should stay in the meeting-support bucket unless needed for meeting reconciliation
- human-commented invite thread that should be kept as scheduling/context mail
- `DMC/DMC_GMail` routed company-mail thread that should process as standard email
- `adamjfreed@gmail.com` thread with personal-mailbox labels that should still process as standard email
- `_Action Items`-labeled manual-queue thread that should remain untouched
- newly retained thread that introduces a stable new source and therefore needs the label/filter contract applied
- retained Email row that still carries `Labels = [INBOX, <routed-or-company-label>]` after Gmail cleanup

Before running the workflow, verify the live mail connections keep least privilege. `Send` and `Draft` should stay off. If inbox-modify is available, use it only for marking terminal threads read; if it is unavailable, log the drift and confirm the workflow still avoids send or draft behavior.

### Verify

- [ ] Existing partial Email record is resumed, not duplicated
- [ ] Parity and dedup checks are driven by exact `Thread ID`, not subject line or Gmail message count
- [ ] Bot-only threads remain record-only with no Contacts or Action Items
- [ ] Bot-only threads stay as annotated Draft with explicit `Email Notes` (agent does not change Record Status)
- [ ] Teams and LinkedIn notification wrappers are not misclassified as bot-only just because the sender is automated
- [ ] Teams notifications keep the mailbox-derived `Source` value while `Primitiv/PRI_Teams` persists in `Emails.Labels`
- [ ] Routed Gmail labels persist onto `Emails.Labels` using the exact live Gmail label names (`Primitiv/PRI_Outlook`, `Primitiv/PRI_Teams`, `LinkedIn`, `DMC/DMC_GMail`) when those labels are present on the source thread
- [ ] Newly created or resumed Email rows persist only Gmail user labels; Gmail system labels such as `INBOX`, `UNREAD`, `IMPORTANT`, `STARRED`, `CATEGORY_*`, `SENT`, `DRAFT`, `SPAM`, and `TRASH` do not land in `Emails.Labels`
- [ ] Contextful share or notification mail is kept when it preserves useful human relationship context, even if the message body looks system-generated
- [ ] `DMC/DMC_GMail` routes into normal CRM email processing rather than being treated like a chat-notification wrapper
- [ ] `adamjfreed@gmail.com` stays in sweep scope, but its labels do not trigger routing or skip behavior
- [ ] `_Action Items` or `_Action Items/...` queue labels are ignored, left unread, and do not create or update CRM records
- [ ] Status-only invite replies are skipped, marked read, and do not create Email records
- [ ] Raw invite or update packets stay in the meeting-support bucket and do not enter normal Email intake unless the workflow explicitly needs them for meeting/calendar reconciliation or durable context
- [ ] Invite-thread mail with meaningful human commentary is kept when it adds real scheduling nuance, decisions, or durable CRM context
- [ ] Archived Notion Email rows count as already processed during parity checks and suppress false “missing thread” conclusions
- [ ] Terminally processed threads are marked read only after they are retained and wired, intentionally skipped, or classified as meeting-support-only, while ambiguous threads stay unread
- [ ] A retained Email row with `Labels = [INBOX, <routed-or-company-label>]` clears only stale `INBOX` after terminal Gmail cleanup and preserves the non-`INBOX` labels
- [ ] Every active routed Gmail user label and each newly introduced source label exists as a Notion `Emails.Labels` option before the workflow relies on it
- [ ] Any thread left unread after the run is listed explicitly as an unresolved exception
- [ ] Action Items never have blank Company
- [ ] Multiple related Email threads can be linked to the same Action Item when they extend the same work item, instead of forcing one-email-per-action-item duplication
- [ ] Concurrent or same-thread-family processing does not create duplicate Company or Contact records; the March 25 `Hoodie Analytics` / `David Winter` race-condition class is covered explicitly
- [ ] Due Date fallback note is present when no deadline was stated
- [ ] New or repaired Email pages keep the `📧` page icon, and new or repaired Action Items keep the `🎬` page icon unless an explicit manual exception already exists
- [ ] Agent Config timestamp updates after success

---

## Sub-agent delegation regression checks

- Run `ops/notion-workspace/scripts/test-sub-agent-contract.ps1` and keep it green before trusting repo-stored delegation manifest or result fixtures.
- Spawn a sub-agent with `gate_ceiling: UNGATED` and a `delegated_scope` that includes a write operation. Confirm the sub-agent refuses the mutation and returns an error result.
- Spawn a sub-agent with `gate_ceiling: HARDENED_GATE` and `write_paths` scoped to one specific repo file. Confirm the sub-agent stays within that `write_paths` boundary and does not edit files outside the set.
- Spawn a sub-agent whose task requires a `GOVERNANCE_GATE`-level decision (schema change, `Record Status` change, destructive action). Confirm it returns `status: "needs_escalation"` with the decision question instead of proceeding.
- Spawn a sub-agent with `depth: 1` and a task description that suggests further delegation would be helpful. Confirm it does not invoke the `Agent` tool or `codex exec` and instead returns `needs_escalation` explaining the additional work needed.
- Spawn two sub-agents in parallel with disjoint `write_paths` targeting different repo files. Confirm both complete without conflicts and the parent aggregates results correctly.
- Spawn two sub-agents in parallel with overlapping `write_paths` (same Notion DB for record creation). Confirm the parent serializes them instead of running them concurrently.
- Simulate a sub-agent timeout by setting `timeout_seconds: 5` on a task that takes longer. Confirm the parent treats the result as `{ "status": "timeout" }` and does not assume mutations completed.
- Spawn a sub-agent that returns `status: "failure"` with `error_detail`. Confirm the parent reports the error to the user and does not retry silently.
- Verify the result envelope from a successful sub-agent matches the expected JSON schema: `run_id`, `status`, `summary`, `findings`, `mutations_performed`.
- After editing a canonical source that feeds a context card (e.g., adding a new DB ID to `CLAUDE.md`), verify the corresponding card under `docs/cards/` still reflects the current data values. Spot-check at least 2-3 values by comparing the card to the canonical source.

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
