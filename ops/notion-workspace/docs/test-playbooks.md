# Automation Test Playbooks

Step-by-step validation procedures for Codex skills, Notion Custom Agents, and manual workflows.

---

## Codex skill validation

Run before publishing:

1. `python "$CODEX_HOME/skills/.system/skill-creator/scripts/quick_validate.py" ops/notion-workspace/skills/notion-action-item`
2. Publish with `ops/notion-workspace/scripts/publish-codex-skills.ps1`
3. Confirm the installed copy in `$CODEX_HOME/skills/notion-action-item/SKILL.md` reflects the repo contract before treating the publish as complete. On this workstation, the default resolves to `C:\Users\adamj\.codex\skills\notion-action-item\SKILL.md`.
4. Forward-test each skill on one realistic task without preloading the intended answer

### notion-action-item regression checks

- Run once with a complete pre-loaded context bundle and once with only a URL or UUID for the same Action Item; confirm the pre-execution summary matches after any minimal refresh.
- Run once with a title search that returns multiple matching Action Items and confirm the skill stops for disambiguation instead of choosing one arbitrarily.
- Run once with a pre-loaded context bundle missing a required field and confirm the skill fetches the missing data before any risky action.
- Run once with a pre-loaded context bundle containing stale status or relations and confirm the skill refreshes the minimum required field set before execution.
- Run once with a pre-loaded context bundle containing stale notes or attachments and confirm only the stale fields are refreshed before execution.
- Run once with a pre-loaded context bundle that has no capture timestamp and confirm copied notes, relations, and attachments are treated as stale and refreshed as needed.
- Run once with a pre-loaded context bundle whose page ID does not exist, or whose supplied URL/UUID points at a different Action Item, and confirm the skill reports the mismatch and stops before execution.
- Run once with a standard Notion URL or UUID and confirm the pre-execution summary matches the classic fetch-first path.

## Notion sync parity

Run for every repo doc changed in the session that maps to a live Notion instruction page:

1. Confirm the local doc's embedded `<!-- Notion Page ID: ... -->` comment, when present, matches the mapped page ID listed in `ops/notion-workspace/CLAUDE.md`.
2. Push the updated local doc to the mapped Notion page.
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
