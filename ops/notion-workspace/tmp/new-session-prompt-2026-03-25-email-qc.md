# New Session Prompt - Email Coverage QC and Gap Audit

Use this as the opening prompt for the next Codex session.

```text
Repo: c:\Users\adamj\Code\FreedSolutions

This is a live operational Notion/Gmail CRM recovery and QC task. Work directly from the current workspace state, live Notion DBs, and Gmail.

Do NOT use /notion-active-session unless I explicitly ask.

Current date context: March 25, 2026.

Scope and posture:
- Reachable mailbox scope is adam@freedsolutions.com.
- Treat adamjfreed@gmail.com as a blocked follow-on lane unless I provide direct access or an export.
- We are not doing an Emails v2 cutover.
- We are not using ops/local_db as the production path for this recovery/QC pass.
- No schema changes without explicit approval.
- Do not create a new Emails DB.
- Reuse existing Contacts and Companies whenever possible.
- Preserve Gmail routed labels in Emails.Labels.
- _Action Items and _Action Items/_Behind remain hard-ignore lanes and must stay unread/non-mutating unless I explicitly revisit them later.

Live IDs:
- Emails DB: f685a378-5a37-4517-9b0c-d2928be4af4d
- Action Items DB: 319adb01-222f-8059-bd33-000b029a2fdd
- Meetings DB: 31fadb01-222f-80c0-acf7-000b401a5756
- Agent Config page: 322adb01-222f-8114-b1b0-cc8971f1b61a

Important state updates since the last backlog-completion pass:
- I deleted the archived duplicate of the Emails DB. The original live Emails DB is the only Emails DB now.
- I currently have about 175 Email records wired up in the live Emails DB. I also deleted roughly a dozen records during cleanup.
- The original rough estimate was about 201 unread emails, so we may still have gaps even though the unread backlog was driven to zero.
- There are only 3 emails currently showing unread in the inbox, and they appear to be newer Anthropic / Claude threads.
- I suspect some inbox mail may have been marked read in Gmail without being ported into the Emails DB.
- Every thread ID in the current inbox should be represented in the Emails DB. We need to check for any gaps.
- This phase is not about spinning up Action Items for stale/completed work. The primary value of this recovery was wiring up Contacts, Companies, and Email history.
- Once the Email corpus is 100 percent wired and QC'ed, I will kick off targeted Action Items separately.

Known policy changes / intent:
- We do want to track all email, even if some of it is noisy. I can filter or hide noise later in Notion.
- That means some earlier "skip as noise" assumptions should be revisited if they caused useful Contacts or Companies to be omitted.
- Specific company/contact gap hypotheses worth auditing:
  - PandaDoc
  - Fireflies
  - Google
  - Fat Nugs Magazine
- These may have been skipped earlier because they looked generic or bot-like, but I still want to know whether the CRM should include Contact stubs and Company coverage for them.

Read-state rules still apply:
- Terminal states are:
  1. Email record created and wired in Notion
  2. intentional skip
  3. meeting-support artifact handled outside normal Email intake
- Gmail should be read for every terminally processed thread.
- Only genuine unresolved exceptions should remain unread, and those must be tracked explicitly.
- _Action Items and _Action Items/_Behind are excluded from this read-clean requirement because they are intentional ignore lanes.

What the prior session already completed:
- The reachable unread backlog outside _Action Items* was processed to zero.
- Query used at closeout:
  is:unread -label:"_Action Items" -label:"_Action Items/_Behind"
  Result at closeout: 0
- Local ledger of processed waves:
  c:\Users\adamj\Code\FreedSolutions\ops\notion-workspace\tmp\backlog-wave-ledger-2026-03-24.md
- That ledger includes the terminal outcomes from the major backlog-completion waves and should be treated as historical context, not proof of full inbox parity.

Main goal for this new session:
Audit the live Emails DB against the current inbox and current Gmail state to prove whether coverage is actually complete, repair any remaining gaps, and QC Contact/Company wiring for generic senders that may have been skipped earlier.

Primary objectives:
1. Pull the exact live Emails DB Thread ID set from Notion.
2. Pull the exact current inbox thread ID set from Gmail for the reachable mailbox.
3. Compute:
   - inbox_thread_ids
   - notion_email_thread_ids
   - missing_from_emails_db = inbox_thread_ids - notion_email_thread_ids
   - represented_in_inbox = inbox_thread_ids intersect notion_email_thread_ids
4. Investigate the 3 currently unread Anthropic / Claude inbox threads:
   - determine whether they are already represented in the Emails DB
   - if missing, create Email records
   - if already represented and terminal, read-clean them
5. Audit Contact/Company coverage for generic senders and previously skipped platform mail:
   - PandaDoc
   - Fireflies
   - Google
   - Fat Nugs Magazine
6. Identify whether the live CRM should contain Contact stubs and Company records for those senders, or whether they are absent only because the relevant emails never entered the Emails DB.
7. Repair any safe, bounded gaps:
   - create missing Email records
   - reuse or create missing Contacts/Companies only when justified by actual retained email coverage
   - preserve Gmail labels in Emails.Labels
   - mark Gmail read for terminal threads after successful write/classification

Execution guidance:
- Prefer the live Emails DB as the source of truth for what is already wired.
- Do not rely on fuzzy semantic search for exact Thread ID parity. Use a helper view or another exact query method to check Thread ID presence.
- Treat the deleted archive DB as gone; do not rely on archived duplicate content anymore.
- Use the local ledger for historical context only.
- If you discover read-but-unported inbox threads, process them in bounded waves and keep explicit notes.
- Do not widen into Action Item cleanup yet unless I explicitly ask.
- Reuse existing Contacts and Companies first before creating anything new.
- If generic senders map to broad platforms, consider whether the Company already exists and whether a safe Contact stub is warranted.

What to report before and after fixes:
- Exact count of live Emails DB records
- Exact count of current inbox thread IDs audited
- Exact diff count for missing_from_emails_db
- Exact count of currently unread inbox threads
- Exact list of missing thread IDs and their subjects
- Exact list of Contact / Company gaps found for PandaDoc, Fireflies, Google, and Fat Nugs Magazine
- Exact count of records repaired in this session
- Any unresolved exceptions left unread, with reasons

Acceptance criteria:
- Every current inbox thread ID in the reachable mailbox is either:
  - represented in the live Emails DB, or
  - explicitly classified and repaired during the session
- The 3 currently unread Anthropic / Claude inbox threads are reconciled
- Any justified generic-sender Contact/Company gaps are repaired
- Gmail read-state is clean for all terminally processed reachable-mailbox threads outside _Action Items*
- Any remaining unread items are explicit unresolved exceptions only

Do not:
- create a new Emails DB
- change schema without explicit approval
- use ops/local_db as the live path
- bulk mutate Contacts/Companies unnecessarily
- blindly process _Action Items*
- lose track of read-state transitions
- assume zero unread means zero coverage gaps

Recommended first move:
- Inventory exact live Emails DB Thread IDs
- Inventory exact current inbox thread IDs
- Diff them
- Then inspect the 3 current Anthropic / Claude unread threads and the generic-sender company/contact gaps
```
