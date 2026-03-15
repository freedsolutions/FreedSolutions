# Proposal: Kill Pre-Stubs, Move to Unified Post-Meeting Agent

**Status:** Approved direction — Session 35 (March 15, 2026). Implementation prioritized for Session 36+.

---

## Problem Statement

The current Meeting Sync Agent creates **pre-stubs** in the Meetings DB the night before each meeting. Notion Calendar also natively syncs GCal events into the same DB. This creates two competing page-creation paths for the same meetings, leading to:

- **Orphan pages** when Adam starts AI notes without first linking the pre-existing stub (Phase C complexity)
- **A mandatory "Link existing page" workflow** before every meeting — friction that shouldn't exist
- **A complex reconciliation sweep** (Phase B) to catch reschedules, cancellations, and time changes across all future stubs
- **Three-phase nightly agent** (forward-looking + reconciliation + orphan detection) when the core value is CRM wiring, not page creation

## Key Insight

Adam confirmed:

- CRM wiring (Contacts, Companies, Series) does **not** need to happen before the meeting — same-night is fine
- Meeting prep (agenda, attendee context, open action items) is valuable but can be delivered as a **briefing** rather than written into pre-created DB pages — this is a future feature, not in scope for initial build
- The calendar view works natively via Notion Calendar's GCal integration — stubs aren't needed for visibility

**The stub is a vessel, not the source of intelligence.** GCal has the attendee list, event title, and timing. The agent can read GCal at any time — it doesn't need to copy that data into Notion before the meeting.

**The transcript page IS the meeting page.** When Adam starts AI transcription from the calendar invite, Notion Calendar creates a page directly in the Meetings DB. Without pre-stubs, there's no competing page to link — the transcript page is the canonical record. This eliminates the "Link existing page" friction entirely.

---

## Proposed Architecture: Unified Post-Meeting Agent

### What Changes

| Concern | Current (Pre-Stub) | Proposed (Post-Meeting) |
|---|---|---|
| Page creation | Agent creates stubs night before | Notion Calendar creates pages when AI notes start |
| CRM wiring | Done at stub creation (night before) | Done by unified post-meeting agent (same night) |
| Action Item parsing | Separate Agent 2, triggered independently | Step 2 of the same unified agent |
| Orphan detection | Phase C required | **Eliminated** — no stubs to orphan against |
| Reconciliation | Phase B sweeps all future stubs | **Eliminated** — no stubs to reconcile |
| Calendar view | Shows agent stubs + native GCal events (duplicates possible) | Shows only native GCal events (clean) |
| Meeting prep | None (stubs have no prep content) | Future: nightly briefing (not in scope for initial build) |
| "Link existing page" step | Required before every meeting | **Eliminated entirely** |

### What Stays the Same

- Contacts DB, Companies DB, Action Items DB — schema unchanged (updated in S35)
- Contact matching rules (email dedup, Secondary Email, Tertiary Email checks)
- Domain-based Company wiring (Domains + Additional Domains)
- Record Status lifecycle (Draft → Active → Inactive → Delete)
- Series Registry and Series Parent linking
- Contact & Company Review workflow
- Unwire Before Delete protocol (added in S35)

---

## Unified Post-Meeting Agent Design

The current Meeting Sync Agent (3 phases) and Post-Meeting Wiring Agent (separate) are replaced by a **single unified agent with two steps**:

**Why unified?** CRM wiring (Step 1) must complete before Action Item parsing (Step 2) — Action Items need Contact and Company relations that Step 1 creates. A single agent guarantees this ordering, eliminates sequencing issues, and reduces the instruction surface to one page.

**Why two steps, not two agents?** Each step remains independently understandable and debuggable. If Action Item parsing breaks, CRM wiring still completes up to that point. The separation is logical (in the instruction page), not operational (no separate triggers or handoffs).

### Multi-Calendar Support

The unified agent processes meetings from **all** of Adam's Google Calendars with the same wiring rules:

| Calendar | Google Account | Notes |
|----------|---------------|-------|
| Adam's primary | adam@freedsolutions.com | Main business calendar |
| Lynn's GCal | Separate account | |
| Shared GCal | Shared with Adam's account | Family / joint scheduling |
| Personal GCal | Separate or linked account | |
| Client GCals | Separate Google accounts per client | Requires OAuth per client account |

**Calendar Name property:** A `Calendar Name` (text) property will be added to the Meetings DB to track which calendar sourced each meeting. This enables calendar-based filtering in views and future per-calendar rules if needed. For Notion Calendar-created pages, the agent reads the Calendar Event ID to determine the source calendar and populates this field.

**Same wiring rules, all calendars.** Every meeting gets full CRM wiring (Contacts, Companies, Action Items) regardless of which calendar it came from. No per-calendar filtering or exclusions in the initial build.

**Client calendar access:** Client GCals are on separate Google accounts. The OAuth/API setup for multi-account access is an implementation detail to resolve during Phase 1 build.

### Step 1: Post-Meeting CRM Wiring (replaces Meeting Sync Phases A + B + C)

**Trigger:** Nightly at 10 PM ET (same schedule) + manual

**Scope:** All Meetings DB pages (from any calendar) modified since last successful run (up to 7-day rollback safety net) that are **not yet wired** (no Contacts relation populated).

**Lookback logic:** Agent Config stores the last successful run timestamp. The agent queries Meetings DB for pages where `Last Modified Date ≥ last successful run`. The 7-day max rollback catches edge cases (agent downtime, late-arriving transcriptions, Agent Config corruption). This is more robust than a fixed "today only" window.

**Workflow:**

1. Read last successful run timestamp from Agent Config
2. Query Meetings DB for pages modified since that timestamp with no Contacts wired
3. For each unwired page, read the corresponding GCal event (by Calendar Event ID on the Meetings DB page)
4. Extract attendee list from GCal event (catches attendees added after last poll)
5. Run Contact Matching Rules (same as today — email dedup, Secondary Email, Tertiary Email, domain-based Company wiring)
6. Wire Contacts, Companies, Series relations
7. Create Draft contacts / placeholder Companies for unknowns (same rules as today)
8. Update last successful run timestamp in Agent Config

**No-notes meetings:** The agent also checks GCal for meetings that happened in the lookback window but have no corresponding Meetings DB page. For these, it creates a minimal Draft record (title + date + contacts) so the CRM trail is complete. Record Status = Draft, consistent with all agent-created records.

### Step 2: Action Item Parsing (replaces Post-Meeting Wiring Agent)

**Runs immediately after Step 1 completes, same agent execution.**

**Scope:** All Meetings DB pages from Step 1 that have AI meeting notes content AND whose Action Items relation is empty (not yet processed).

**Workflow:** Same as current Post-Meeting Wiring Agent instructions:

1. Parse Action Items from the AI summary's "Action Items" heading
2. Apply Step 2b grouping rules (same-topic, same-contact, granularity threshold)
3. Route to Action Items DB with property mapping (Type auto-computes from Assignee)
4. Wire back to the meeting's Action Items relation

All existing rules carry forward: Contact matching from the meeting's Contacts (wired in Step 1), Company derivation, Assignee logic (Adam = Task, blank = Follow Up), Record Status = Draft, one deliverable = one page.

**Floppy integration (future):** This is where "Hey Floppy" voice commands from the transcription would be parsed — as a sub-step within Step 2, before or after the AI summary parsing. Design TBD per Floppy agent design doc.

---

## Future: Nightly Briefing (not in initial scope)

A meeting prep briefing feature is planned but not part of the initial build. When implemented, it would run as a separate step after the unified agent completes:

- Pull tomorrow's GCal events
- Look up attendees in Contacts DB
- For series meetings, pull last instance's Action Items
- Compile a daily briefing page with meeting context
- Format and location TBD

---

## Migration Plan

**Phase 1: Build the unified agent** (no disruption)
- Write the unified agent instruction page (Step 1 + Step 2)
- Add lookback logic and Agent Config timestamp tracking
- Test against real data without modifying existing system

**Phase 2: Run in parallel** (1 week)
- Run the unified agent alongside existing Meeting Sync + Post-Meeting Wiring
- Compare outputs — verify CRM wiring quality and Action Item parsing match
- Verify no-notes meeting Draft records are created correctly

**Phase 3: Cut over**
- Disable pre-stub creation (Phase A)
- Disable reconciliation (Phase B) and orphan detection (Phase C)
- Disable separate Post-Meeting Wiring Agent trigger
- Remove the "Link existing page" requirement from Adam's workflow
- Update all local docs (meeting-sync.md → unified agent doc, agent-sops.md, quick-sync.md)
- Update CLAUDE.md and Agent Registry

**Phase 4: Cleanup**
- Delete or archive existing future stubs
- Simplify the Meetings DB schema if any properties become unnecessary
- Archive old Meeting Sync and Post-Meeting Wiring instruction pages

---

## Risks and Tradeoffs

**Risk: Meetings with no AI notes get no Notion page.**
Mitigation: Step 1 includes a catch-all that creates Draft records for any GCal meeting in the lookback window without a corresponding Notion page. CRM trail stays complete.

**Risk: Late-arriving transcriptions miss the nightly window.**
Mitigation: The lookback logic (since last successful run, up to 7 days) catches late transcriptions on subsequent runs. No meeting falls through the cracks permanently.

**Risk: Calendar Event ID matching changes.**
Mitigation: Notion Calendar pages created from AI notes include the GCal event ID. The unified agent matches on this, same as today.

**Risk: Loss of future-stub reconciliation catches reschedules.**
Mitigation: Reschedule detection isn't needed if there are no stubs to be wrong. Notion Calendar reflects GCal in real time.

**Tradeoff: Slight delay in CRM wiring (same-day vs night-before).**
Adam confirmed this is acceptable. The wiring happens by 10 PM the same day the meeting occurs.

**Tradeoff: Meeting prep requires on-demand Claude request until briefing is built.**
The briefing feature is planned as a future addition. In the interim, Adam can ask Claude for meeting context on demand using the same GCal + CRM data.

---

## Decisions Made (Session 35)

1. **Direction approved** — kill pre-stubs, move to unified post-meeting agent
2. **Agent architecture** — single unified agent with two steps (CRM wiring → Action Items), not two separate agents
3. **Lookback** — since last successful run, 7-day max rollback, filtered by Last Modified Date
4. **No-notes meetings** — create Draft records for CRM trail completeness
5. **GCal matching** — Calendar Event ID is available on Meetings DB pages
6. **Briefing** — placeholder for future, not in initial scope
7. **Series** — still active, carry forward
8. **Last Contacted** — already removed from DB in prior session, references stripped
9. **Floppy** — future integration point within Step 2 (transcription parsing)
10. **Multi-calendar** — all calendars (Adam's, Lynn's, shared, personal, client) get same wiring rules. `Calendar Name` property added to Meetings DB. Client calendars are separate Google accounts (OAuth per account).
11. **Calendar Name** — new text property on Meetings DB to track source calendar
