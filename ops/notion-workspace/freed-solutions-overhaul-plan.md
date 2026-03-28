# Freed Solutions CRM Overhaul Plan

**Date:** March 28, 2026
**Author:** Claude (Advisory session with Adam)
**Purpose:** Redirect the overhaul from infrastructure-first to value-first
**Timeframe:** 30 days to daily operational value

---

## Diagnosis

### What's working
- 3 Notion Custom Agents are live and running nightly (Post-Meeting, Post-Email, Contact & Company)
- All agents have cross-DB access to all 5 CRM databases
- 20+ Gmail filters are manually maintained and follow prescriptive business rules
- Agent instruction docs are well-structured and version-controlled in repo
- Schema is stable: Contacts, Companies, Action Items, Meetings, Emails all functional
- Floppy voice-command design is complete and integrated into Post-Meeting pipeline
- Notetaker CRM profile is active and producing structured meeting summaries

### What's not working
- **The agents don't do enough smart work.** Cross-contextual wiring — the logic that makes an incoming email update a related Action Item, or surfaces relevant context for meeting prep — isn't in the instructions yet.
- **Sessions are consumed by scaffolding, not business logic.** Parity checks, closeout protocols, sub-agent contracts, and sync rituals eat the time that should go toward writing the agent intelligence that creates daily value.
- **No daily rhythm exists.** Adam is still mostly building, not using. The "Monday morning" experience (open Notion, review smart Drafts, act on flagged follow-ups) has never been realized.
- **Two competing plans are unreconciled.** The 5-phase Workspace Hardening plan and the local-first SQLite migration overlap and partially conflict. Neither is sequenced toward the fastest path to daily value.

### Root cause
The overhaul has been vault-first: building protective infrastructure (gates, parity, sub-agent contracts, local DB architecture) before the system produces enough value to need protection. The correct sequence is: make it work → make it useful → make it robust → make it fast.

---

## Strategic Decisions

### FREEZE: Local-first SQLite migration
- `ops/local_db/` stays as-is. No new code.
- `freed-solutions-execution-checklist.md` is archived as a future-state reference, not an active execution plan.
- **Revisit trigger:** Mac Mini is procured and set up, AND the Notion agent instructions are producing daily value that would benefit from 3x/day processing.
- **Why:** The migration solves speed and scheduling problems. Adam's actual problem is logic completeness. Solving the wrong problem first means building a sync layer for agent logic that hasn't been written yet — then rewriting the sync when the logic changes.

### FREEZE: 5-phase Workspace Hardening plan
- Phases 2-5 from `session-active.md` Planning Output are deferred.
- Phase 1 (schema cleanup) has 2 items worth keeping — see Phase 1 below.
- **Why:** The Domains DB, gmail-filter-manager.ps1, API vs MCP routing contract, and Action Item self-relations are all valuable future work, but none of them are prerequisites for the cross-contextual wiring that creates daily value.

### SIMPLIFY: Repo scaffolding overhead
- Parity checks (`compare-notion-sync.ps1`) become optional, not required for closeout.
- Sub-agent contract (`docs/sub-agent-contract.md`) stays documented but is not required for current work.
- Closeout protocol drops to: edit local file → push to Notion → spot-check → commit → push. No saved artifacts, no deterministic parity, no multi-step validation chain.
- Gate taxonomy stays (UNGATED / HARDENED_GATE / GOVERNANCE_GATE) but the ceremony around it lightens.
- **Why:** These protections matter for a system in production with high-stakes data. Right now the system isn't producing daily value, so the overhead is protecting nothing while consuming the sessions needed to create value.

### BUILD: Cross-contextual agent intelligence
- This is where every session should go for the next 30 days.
- The agents already have the access they need. They need better instructions.

---

## Execution Plan

### Phase 0: Lighten the Load (1-2 sessions)

**Goal:** Remove scaffolding friction so every subsequent session goes toward business logic.

#### 0A. Update `CLAUDE.md` Codex Review Gate
- Replace the 10-step closeout with a 4-step version:
  1. Edit local source files
  2. Push mapped docs to Notion via MCP
  3. Spot-check the live page (visual, not deterministic parity)
  4. Commit and push
- Keep the full protocol documented in a `## Legacy Closeout Protocol` section for future re-enablement
- Drop the requirement for saved remote-body artifacts in `ops/notion-workspace/tmp/`

#### 0B. Update `session-active.md`
- Archive the 5-phase Planning Output section (move to a `## Archived Plans` section or remove entirely — git history preserves it)
- Replace P1-P4 priority queue with the new phases from this plan
- Trim the Current State section to only items that are still relevant (not historical breadcrumbs)

#### 0C. Simplify `session-active.md` Current State
- The Current State section is ~300 lines of historical session logs. This belongs in git history, not the active handoff.
- Reduce to: current system state (what's live, what's connected, what the schema looks like) + active priorities + known issues. Target: under 80 lines.

#### 0D. Update `docs/agent-sops.md`
- Remove or collapse the Skill Gate Protocol, Sub-Agent Delegation, and Kickoff Conventions sections into a single "Advanced: Sub-Agent & Skill Protocols" section that can be skimmed
- Keep the Agent Registry, Schema Conventions, and Rules of Engagement as the primary operating surface

---

### Phase 1: Essential Schema Cleanup (1-2 sessions)

**Goal:** Fix the 2 schema issues that actually affect agent output quality.

#### 1A. Remove stale `Inactive` status option
- Audit all 5 DBs for any records still using `Inactive`
- If none: Adam removes the option from each DB via Notion UI (GOVERNANCE_GATE)
- If some exist: document them, decide disposition, then remove

#### 1B. Clean up `Emails.Labels` — remove `INBOX` and system labels
- Audit the ~31 live options
- Remove Gmail system labels that leaked in (`INBOX`, etc.)
- Verify all active routed labels (`Primitiv/PRI_Outlook`, `Primitiv/PRI_Teams`, `LinkedIn`, `DMC/DMC_GMail`) have matching options
- This directly improves Post-Email agent output quality

#### 1C. Document `Companies.States` properly (UNGATED)
- Already identified as multi_select with 13 options
- Add to `CLAUDE.md` schema section
- Quick win — improves Contact & Company agent enrichment accuracy

**Deferred from original Phase 1:**
- `1E` Gmail Link formula — nice but not blocking daily value
- `1C` Engagements/Tech Stack documentation — backburnered DBs, not relevant yet

---

### Phase 2: Post-Email Cross-Contextual Wiring (3-5 sessions)

**Goal:** Make the Post-Email agent smart enough that Adam opens Notion on Monday morning and sees useful, correctly wired Draft Action Items from weekend emails.

This is the highest-value work in the entire plan. Every session here directly improves daily operational value.

#### 2A. Action Item matching logic
Add instructions to `docs/post-email.md` for the agent to:
- After CRM wiring (Step 2), before creating new Action Items (Step 3):
  - Query the Action Items DB for open items related to the same Contact and/or Company
  - Check for keyword overlap between the email thread subject/body and existing Action Item task names
  - If a match is found with high confidence:
    - Do NOT create a new Action Item
    - Instead, append to the existing Action Item's `Task Notes` with the email context and date
    - Wire the email to the Action Item via `Source Email` (add to the multi-relation)
    - If the email represents a response to something Adam was waiting on, update `Status` to flag it for review (e.g., a new status value or a note prefix)
  - If a match is found with low confidence:
    - Create a new Draft Action Item but include a note: "Possibly related to: [existing AI title] — review for merge"
  - If no match: create normally (existing behavior)

#### 2B. Follow-up detection
Add instructions for the agent to recognize incoming emails that close a loop:
- Pattern: Adam sent an email (or an Action Item exists with Type = "Follow Up") → a reply arrives from the counterparty
- Detection signals:
  - Thread ID matches an email already wired to an Action Item
  - Sender matches the Contact on an open Follow Up Action Item
  - Subject line overlap with an existing Action Item task name
- When detected:
  - Append the reply context to the Action Item's `Task Notes`
  - Add a prominent flag in `Task Notes`: `⚡ FOLLOW-UP RECEIVED [date] — review and close?`
  - Keep Status as-is (Adam decides whether to close)

#### 2C. Domain-aware intake classification
Add instructions for handling the two workstreams Adam described:
- **Known domains (existing Companies):** Wire normally. The agent already does this.
- **New domains (no Company match):**
  - Create Draft Company as today
  - But add a classification note in `Company Notes`: "NEW DOMAIN — review for routing tier: Active intake / Archive-only / Block"
  - If the domain is generic (gmail.com, etc.), skip company creation and wire to Contact only
  - Surface a Draft Action Item: "Review new domain: [domain] — set routing tier and Gmail filter"
  - This replaces the Domains DB concept with a lightweight Notion-native workflow

#### 2D. Test the cross-contextual wiring
- Manually create a test scenario:
  - Existing Action Item (Follow Up type) for Contact X at Company Y
  - Send yourself a test email from a secondary account that mimics a reply
  - Run the Post-Email agent manually (`@mention`)
  - Verify: no duplicate AI created, existing AI updated, follow-up flagged
- Run against 3-5 real retained emails from the existing corpus to validate wiring quality

#### 2E. Harden the label hygiene
- The existing P4 requirement: verify no system labels leak into Emails.Labels
- This is a small add-on to the Post-Email instructions, not a separate phase
- Add a hard rule to Step 1: "Before writing Labels to the Email record, filter out any Gmail system labels"

---

### Phase 3: Meeting Prep & Context Surfacing (2-3 sessions)

**Goal:** Before a meeting, Adam can see relevant Action Items and recent email threads involving the meeting attendees.

#### 3A. Design the meeting prep workflow
Two options (Adam should pick one):

**Option A — Agent-driven (add to Post-Meeting nightly run):**
- For meetings in the next 24-48 hours:
  - Query Contacts → find the attendees
  - Query Action Items → find open items involving those Contacts or their Companies
  - Query Emails → find recent threads (last 14 days) involving those Contacts
  - Write a "Meeting Prep" section to the meeting page body listing the relevant context
- Pro: automatic, no manual trigger needed
- Con: adds processing time to the nightly run, only updates once per day

**Option B — Skill-driven (new Codex skill):**
- A repo-backed skill Adam runs manually before a meeting
- Same query logic as Option A but on-demand
- Pro: faster iteration on the format, no nightly overhead
- Con: requires Adam to remember to run it

**Recommendation:** Start with Option B (skill). It's faster to build, easier to iterate on the output format, and avoids coupling meeting prep to the nightly agent schedule. Promote to Option A once the format stabilizes.

#### 3B. Build the meeting prep skill
- New skill: `ops/notion-workspace/skills/notion-meeting-prep/`
- Input: Meeting page ID or "next meeting" shortcut
- Steps:
  1. Fetch meeting attendees from the Meeting record
  2. Resolve to Contacts → Companies
  3. Query open Action Items for those Contacts/Companies
  4. Query recent Emails (14 days) for those Contacts
  5. Write a structured "Prep Notes" section to the meeting page
- Output format should be concise: "Open items with [Contact]: [list]. Recent threads: [list with dates]."

#### 3C. Test against real upcoming meetings
- Run the skill against 2-3 upcoming meetings with known attendees
- Validate that the surfaced context is actually useful, not noise
- Iterate on the output format based on what Adam finds helpful

---

### Phase 4: Contact & Company Enrichment Tuning (1-2 sessions)

**Goal:** New contacts and companies from email intake arrive enriched enough that Adam's review is fast.

#### 4A. Review current Contact & Company agent output
- Pull 10 recent Draft Contacts and 10 Draft Companies created by the agents
- Score each on: name accuracy, company wiring, role/title populated, LinkedIn found, phone found
- Identify the most common gaps

#### 4B. Tune enrichment instructions based on findings
- Update `docs/contact-company.md` with more specific guidance for the common gaps
- Likely areas:
  - Gmail signature parsing priority (strongest source for title, phone, LinkedIn)
  - Company website team page scraping
  - LinkedIn matching rules (when to set vs. when to flag)

#### 4C. Test enrichment quality
- Run the Contact & Company agent manually against the reviewed Drafts
- Compare before/after enrichment quality
- Iterate instructions until the gap rate is acceptable

---

### Phase 5: Domain & Filter Handoff Workflow (2-3 sessions)

**Goal:** When a new domain enters the CRM, Adam gets a clean handoff to decide its routing tier and Gmail filter.

This replaces the Domains DB concept from the original plan with a lighter Notion-native approach.

#### 5A. Design the handoff as Action Items, not a new DB
- When a new Company is created (by Post-Email or Contact & Company agent):
  - If the domain is genuinely new (not in any existing Company's Domains or Additional Domains):
  - Create a Draft Action Item: "Review new domain: [domain] from [Company Name]"
  - Task Notes should include:
    - The email thread that introduced it
    - Suggested routing tier based on context (Active intake if business contact, Archive-only if automated, Block if spam-adjacent)
    - Suggested Gmail filter rule (domain match, or sender match for generic domains)
  - Adam reviews the Draft, adjusts the suggestion, promotes to Active
  - Adam applies the Gmail filter manually (or via a future script)

#### 5B. Add the handoff logic to Post-Email instructions
- This is an extension of Phase 2C (new domain handling)
- The Action Item becomes the review surface — no new DB needed
- The Action Item `Task Notes` carry the filter specification

#### 5C. Document the manual Gmail filter step
- Create a lightweight checklist in `docs/domain-intake.md` (local only for now):
  - Review the Draft Action Item
  - Decide routing tier
  - Create or update Gmail filter (manual in Gmail settings)
  - Update Company record if needed (States, Additional Domains)
  - Mark Action Item complete
- This becomes the foundation for future automation (when the Mac Mini is ready and the gmail-filter-manager.ps1 makes sense)

---

### Phase 6: Stabilize & Prove Daily Value (ongoing)

**Goal:** Run the system for 2 weeks and measure whether the "Monday morning" experience is real.

#### 6A. Define success metrics
- Draft Action Items created per day (target: >0 on days with meetings or business email)
- Follow-up flags surfaced per week (target: at least 1-2 per week)
- Draft review time (target: <15 min per morning)
- New domain handoffs per week (target: review backlog stays under 5)

#### 6B. Run daily for 2 weeks
- Each morning: open Notion, review Drafts, promote or edit
- Track what's working and what's noise
- Note any wiring errors for instruction tuning

#### 6C. Decide on next infrastructure investment
After 2 weeks of daily use, the right next investment will be clear:
- If processing frequency is the bottleneck → Mac Mini + local agents (revisit SQLite plan)
- If agent output quality is the bottleneck → more instruction tuning
- If Gmail filter management is painful → build the gmail-filter-manager.ps1
- If meeting prep is valuable → promote from skill to nightly agent
- If the scaffolding simplification caused problems → selectively re-enable protections

---

## What This Plan Does NOT Include (And Why)

| Deferred Item | Why It's Deferred |
|---|---|
| SQLite local DB (`ops/local_db/`) | Solves speed, not logic. Revisit when Mac Mini is ready and agent logic is stable. |
| Domains DB in Notion (Phase 2A of old plan) | Replaced by Action Item-based handoff workflow. Less schema, same outcome. |
| `gmail-filter-manager.ps1` | Manual Gmail filter management works fine at current volume. Automate when it hurts. |
| Bidirectional Notion↔SQLite sync | The most complex piece of the old plan. Not needed until local DB exists. |
| API vs MCP routing contract | Relevant when local DB needs direct API. Currently all work goes through MCP and that's fine. |
| Action Item `Related Items` self-relation | Nice for linking tasks, but not a prerequisite for cross-contextual wiring. The wiring happens in agent logic, not schema. |
| Sub-agent parallel execution | Over-engineered for current volume. Single-threaded agent runs are fine. |
| Deterministic parity checks | Protecting sync integrity for a system that changes ~weekly. Visual spot-checks are sufficient. |

---

## Session Rhythm Going Forward

Each Claude Code / Codex session should follow this pattern:

1. **Read `session-active.md`** (should be <80 lines after Phase 0)
2. **Pick the next Phase/Step** from this plan
3. **Do the work** — edit instruction docs, push to Notion, test
4. **Lightweight closeout:** update `session-active.md` with what was done and what's next, commit, push
5. **No parity checks, no saved artifacts, no multi-step validation** unless something actually breaks

Target: **80%+ of session time goes to writing or testing agent instructions.** If scaffolding consumes more than 20% of a session, something is wrong.

---

## Relationship to Existing Docs

| Document | Action |
|---|---|
| `freed-solutions-execution-checklist.md` | Archive. Keep in repo for reference but remove from `CLAUDE.md` "Read first" list. |
| `session-active.md` | Rewrite in Phase 0. Dramatically shorter. |
| `CLAUDE.md` | Update closeout section in Phase 0. Remove execution checklist reference. |
| `docs/agent-sops.md` | Minor trim in Phase 0. Primary updates happen in Phases 2-5 as agent instructions evolve. |
| `docs/post-email.md` | Primary work target in Phase 2. This is where the cross-contextual intelligence lives. |
| `docs/post-meeting.md` | Stable for now. Meeting prep (Phase 3) adds a new skill, not changes to this doc. |
| `docs/contact-company.md` | Tuning target in Phase 4. |
| `docs/sub-agent-contract.md` | Stays documented. Not actively used until volume justifies delegation. |
| `docs/cards/*` | Stay as lightweight reference. No changes needed. |
| `.claude/plans/ancient-purring-dove.md` | Archive alongside the 5-phase plan it describes. |

---

## Decision Log

| Decision | Rationale | Reversible? |
|---|---|---|
| Freeze local-first SQLite migration | Solves speed not logic; Mac Mini not ready; agent instructions aren't written yet | Yes — revisit when Mac Mini is set up |
| Freeze 5-phase workspace hardening | Over-engineered for pre-daily-value state; most phases don't unblock cross-contextual wiring | Yes — cherry-pick items as needed |
| Simplify closeout to 4 steps | Overhead consuming sessions that should produce business logic | Yes — re-enable parity checks when system is in production |
| Replace Domains DB with Action Item handoff | Same routing-tier decision workflow without new schema; lighter to build and iterate | Yes — promote to Domains DB if volume overwhelms Action Items |
| Meeting prep as skill before agent | Faster iteration, no nightly coupling, manual trigger matches current usage pattern | Yes — promote to nightly agent when format stabilizes |
| Keep Notion as primary DB layer | Agents already work, Adam reviews in Notion, no sync layer needed yet | Yes — migrate when processing frequency demands it |
