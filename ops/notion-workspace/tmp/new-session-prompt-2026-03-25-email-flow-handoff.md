# New Session Prompt - Email Flow Decision, Action Item Wiring, and Post-Email Hardening

Use this as the opening prompt for the next Codex or Claude session.

```text
Repo: c:\Users\adamj\Code\FreedSolutions

Start by reading the canonical repo handoff:
- ops/notion-workspace/session-active.md

Current date context: March 25, 2026.

This is live operational Notion/Gmail CRM work against the current workspace state, live Notion DBs, and Gmail.

Do not widen into unrelated dirty-worktree lanes unless I explicitly ask.
Do not use ops/local_db as the production path for this email-flow follow-up.
Do not create a new Emails DB.
Do not change schema without explicit approval.

Useful live IDs:
- Emails DB: f685a378-5a37-4517-9b0c-d2928be4af4d
- Action Items DB: 319adb01-222f-8059-bd33-000b029a2fdd
- Meetings DB: 31fadb01-222f-80c0-acf7-000b401a5756
- Agent Config page: 322adb01-222f-8114-b1b0-cc8971f1b61a

Mailbox and routing scope:
- Reachable mailbox scope is adam@freedsolutions.com
- adamjfreed@gmail.com remains in sweep scope, but its labels are non-routing
- Gmail labels are the upstream source of truth for routing
- _Action Items and _Action Items/... remain ignore lanes, not active intake lanes

What the last session completed:
- Audited current Gmail inbox parity against the live Emails DB
- Gmail inbox snapshot at audit time:
  - 21 unique inbox thread IDs
  - 24 inbox messages
  - 0 unread inbox threads
- Live visible Emails DB count:
  - 175 before repair
  - 181 after repair
- Inbox parity result:
  - 14 current inbox thread IDs were already represented in the live Emails DB
  - 6 true live gaps were repaired by creating new live Email rows
  - 1 current generic Accepted calendar packet was treated as meeting-support-only rather than restored as a normal live Email record
- Two threads that had existed only in the deleted archive Emails DB were re-created in the live Emails DB:
  - [Action required] Set up billing for your Google Workspace account
  - iFLYTEK Global order confirmed
- Sender coverage repaired during QC:
  - created company: Intuit
  - created contacts: Google Workspace Team, PandaDoc, Fred from Fireflies, Fat Nugs Magazine, Intuit Developer Group
- Generic-sender audit confirmed Google, PandaDoc, Fireflies, and Fat Nugs Magazine should keep sender stubs when their mail is retained in CRM

Important context from Adam:
- 13 generic Accepted calendar threads were intentionally archived in Notion
- That means active live Emails rows with INBOX do not necessarily equal Gmail inbox count

Primary open decision:
We need to decide and document the cleanup control plane.

Two candidate models:
1. Gmail-first control plane
   - Adam manages filters and inbox posture in Gmail
   - unresolved threads stay unread in Gmail
   - Post-Email ingests them and marks them read or archives them at terminal state
2. Notion-first retention plus later Gmail cleanup
   - every retained or terminal stub lands in Notion first
   - a separate cleanup flow later mirrors archive, label, or read-state decisions back into Gmail

Current working recommendation from the prior session:
- Gmail should remain the upstream routing and cleanup control plane
- Notion should remain the retained CRM record and downstream Action Item system
- Any reverse-sync from Notion into Gmail should be treated as a separate follow-on workflow, not implied current behavior

Important hardening note to preserve:
I asked whether duplicate Hoodie Analytics / David Winter records may have been caused by a race condition.
The answer was:

"That's a very plausible theory. All three Hoodie Analytics company records (and their corresponding David Winter contact records) were created within about 45 seconds of each other — 02:35:19, 02:35:34, and 02:36:02 on Mar 25. That timing strongly suggests the Post-Email Agent was processing multiple email messages from the same thread (or closely related threads) concurrently, and each processing path independently created its own Company + Contact pair before any of them could see the others' records.

The email thread I found (Re: Primitiv Group // Hoodie Product Finder) has Matt Shterenberg, David Winter, Adam, and Brian on it — so if the agent was processing multiple messages from that thread (or the original intro plus the reply) in parallel, each would have independently resolved new company needed and new contact needed without seeing the sibling records.

A dedup-before-create check scoped to the current batch (not just existing DB records) would catch this pattern, or serializing company/contact creation within a single run. Worth flagging for the next Post-Email Agent hardening pass."

That needs to stay explicit in the next handoff and follow-up work.

Follow-on work that still matters:
1. Decide and document Gmail-vs-Notion cleanup control plane
2. Wire the current retained Email corpus into Action Items and follow-ups
3. Harden Post-Email routed-label persistence on future automated runs
4. Add regression coverage for duplicate-prevention during concurrent email processing
5. Add explicit Icon rules to the additional databases that still need them, not just Meetings
6. Capture deterministic compare-notion-sync parity artifacts for the recent mapped-doc Notion re-syncs, or explicitly record the accepted exception

Known review findings still open:
- mapped-doc parity artifacts were not captured for the latest Notion re-syncs
- routed-label persistence still needs regression coverage
- duplicate-prevention still needs regression coverage
- cleanup control-plane decision is still unresolved
- docs still reference an untracked local script start-codex-notion-workspace-quiet.cmd

How to answer the product/process questions:
- Confirm whether the 14 active Notion rows with INBOX are expected to line up with Gmail after excluding archived Accepted packets and other intentional meeting-support-only threads
- Determine whether a future agent should mimic Notion-side triage changes back into Gmail
- Or, alternatively, confirm that Gmail should remain the only source for filters, archive posture, and unread/read staging while Notion only consumes and tracks retained CRM context

Acceptance criteria for this next session:
- The cleanup control-plane decision is explicit and documented
- Generic Accepted calendar packets and meeting-support-only mail have a documented behavior in both Gmail and Notion
- The next Post-Email hardening checklist explicitly includes:
  - routed-label persistence into Emails.Labels
  - dedup-before-create or serialized company/contact creation within a run
  - non-routing behavior for adamjfreed@gmail.com labels
  - ignore-lane behavior for _Action Items and children
- The handoff clearly captures the next lane for wiring retained emails into Action Items
- Icon-rule expansion is called out for the remaining relevant DBs

Recommended first move:
- Read ops/notion-workspace/session-active.md
- Confirm the intended Gmail-vs-Notion cleanup model
- Then work the retained Email corpus into Action Items and a concrete Post-Email hardening checklist
```
