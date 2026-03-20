# Automation Test Playbooks

Step-by-step validation procedures for Codex skills, Notion Custom Agents, and manual workflows.

---

## Codex skill validation

Run before publishing:

1. `python C:\Users\adamj\.codex\skills\.system\skill-creator\scripts\quick_validate.py ops/notion-workspace/skills/notion-action-item`
2. `python C:\Users\adamj\.codex\skills\.system\skill-creator\scripts\quick_validate.py ops/notion-workspace/skills/notion-agent-config`
3. `python C:\Users\adamj\.codex\skills\.system\skill-creator\scripts\quick_validate.py ops/notion-workspace/skills/notion-agent-test`
4. Publish with `ops/notion-workspace/scripts/publish-codex-skills.ps1`
5. Forward-test each skill on one realistic task without preloading the intended answer

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

### Verify

- [ ] Existing partial Email record is resumed, not duplicated
- [ ] Bot-only threads remain record-only with no Contacts or Action Items
- [ ] Bot-only threads are marked `Inactive` after explicit classification so they do not linger as Draft QC gaps
- [ ] Action Items never have blank Company
- [ ] Due Date fallback note is present when no deadline was stated
- [ ] Agent Config timestamp updates after success

---

## LinkedIn Messages workflow

### Trigger

- Manual run only

### Setup

Use:

- one new LinkedIn conversation
- one existing conversation with new messages
- one same-name ambiguous contact case

### Verify

- [ ] Existing Thread ID records update instead of being skipped
- [ ] LinkedIn URL is not written on ambiguous same-name matches
- [ ] Missing runtime timestamp defaults to a 7-day window and is logged
