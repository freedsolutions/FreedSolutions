# Session Active

Canonical active handoff for `ops/notion-workspace`.

Last updated: April 15, 2026 (Session 80)
Owner: Claude Code

## System State

- Pipeline: Script 9:30 PM, Post-Meeting 10 PM, Post-Email 10:30 PM, C&C 11 PM
- Agents: Post-Meeting, Post-Email, C&C (nightly), Follow-Up (@mention only)
- CRM totals: 189 Contacts, 72 Companies, 105 Domains, 267 Emails, 196 Meetings, 237 Action Items
- Draft queues: 2 Draft AIs, 13 Draft Emails
- Gmail infra: 190 filters, 87 labels, 91 domain-matched (S80 added 32 to-side mirror filters for approved company domains)
- Tag coverage: 189/189 Active Contacts tagged (100%)
- Last sync: CLAUDE.md (S77), agent-sops.md (S76), post-email.md (S79), post-meeting.md (S78), contact-company.md (S68), notetaker-crm.md (S69), follow-up.md (S73), skills-registry.md (S76)
- Lightweight closeout active (no parity checks)
- Known issue: Notion DB default overrides `Record Status = Active` on API-created pages to Draft — must patch after create (discovered S66A)

## Success Metrics (2-week eval: Apr 5 - Apr 19)

| Metric | Target | Baseline (Apr 4) | How to Measure |
|--------|--------|-------------------|----------------|
| Draft AIs created per day | >0 on meeting/email days | 2 (Apr 4 evening) | Query AIs by Created Date |
| Follow-up flags per week (Status = Review) | >= 1-2 | 0 (just deployed) | "Needs My Attention" view |
| Morning draft review time | <15 min | TBD (Adam self-report) | Self-report after 1 week |
| New domain backlog | <5 unreviewed Drafts | 0 Draft Domains | Count Draft Domains |
| Pipeline errors per nightly | 0 | 0 (clean runs) | Agent Config + script logs |
| Email Notes coverage | 100% of processed records | 0 stubs remaining | Query Emails with blank Email Notes or markers |
| Cross-contextual match accuracy | 0 false positive duplicates | N/A (first week) | Spot-check weekly |

## Backlog

- SQLite migration: local-first thread content capture (requires Mac Mini + daily value proven)
- Monitor: today's 8:19 AM missed-run recovery fired (proving `StartWhenAvailable=True` / `WakeToRun=True` work) but exited with `-2147020576`. Adam reran manually at 11:04 AM successfully. If the error recurs on the next auto-recovery, investigate `run_nightly_sweep.cmd` behavior under wake-from-sleep.
- Edge cases deferred from S80 filter audit (Adam to investigate manually): `Notion` (`*notion.so` wildcard semantics), `Intuit` (dp.intuit.com subdomain + intuit.com), `Primitiv` (`teams.mail.microsoft` — looks truncated). Platform-domain labels (Alignable, Anthropic/claude.com, Calendly, Distru, Dutchie Looker, GitHub, LinkedIn, monday.com, UPS) intentionally left from-only since Adam doesn't send outbound to those domains.

## Last Session

S80 — Gmail filter to/from gap audit + Post-Email sweep hardening. (1) Added `ops/local_db/audit_filter_to_from_gaps.py` to enumerate live Gmail filters grouped by label and flag labels with from-side tokens missing a matching to-side filter; 42 labels flagged (40 domain-level, 2 sender-level correctly one-way). (2) `ops/local_db/patch_filter_to_mirrors.py` created 32 to-side mirror filters (`to:*@<domain>` + `removeLabelIds: SPAM`) for Adam-approved "real-correspondence" domains across 28 labels (Ads-N-Motion, Advanced Psychotherapy, AIQ, CannaPlanners, DA Advisory, Dope SEO, Edge, ePropel, Fat Nugs, Fireflies, Formul8 incl. Drucker/staqs, GMP Collective, Gold Standard, Happier Valley Comedy, Hoodie Analytics, iFLYTEK ×2, Illumify, LLYC, Lunar Moth, Mercor, Orfao Tech, PandaDoc ×2, Parallel/netacare, Ryan Spelts, Seed, SmartSource, Surfside, The Other Magazine). Post-patch audit confirms 0 approved gaps remaining; filter count 160 → 190. (3) `post_email_sweep.py` — `fetch_thread_metadata` now builds an email→display-name map by parsing `From/To/Cc/Bcc` headers (stdlib `email.utils.getaddresses`), and `_build_name_map` returns it unchanged so `create_draft_contact` picks up real Gmail sender names; email-root fallback retained only when no header name exists. (4) Bot-only classifier guard in `wire_crm_for_thread` — when `participant_emails` is empty after alias/bot-prefix strip, pre-strip senders are now checked against Contacts by Email/Secondary Email/Tertiary Email; matches are wired to the Email record without creating new Drafts. Verified with live sweep (19 threads, 4 Emails + 5 Contacts + 3 Companies + 3 Domains created, 0 errors): ASTM D37 thread created 5 new Contacts all with real From-header display names ("Anke Ginzburg", "Klaas Eleveld", "Myrtle Clarke", "Gobbi, Sara", "Sundace Farms, Terry Grajczyk (D37.90 Secretary)"); LinkedIn verification-code thread hit the new bot-only guard log path ("no Contact match on pre-strip sender") and correctly skipped.
