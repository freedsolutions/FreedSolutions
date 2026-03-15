# Curated Notes — Design Document

**Status:** Draft (Session 37, March 15 2026)
**Context:** This is Priority 2 from Session 37. The unified Post-Meeting Agent (Steps 1-3) handles automated CRM wiring, action item parsing, and GCal sync-back. Curated Notes closes the feedback loop: after Adam reviews Draft action items, the agent produces a structured permanent record.

---

## Problem

The current pipeline produces raw AI transcription → Draft action items → Adam reviews. But there's no curated permanent record after Adam's review. Meeting pages retain the raw AI summary, which is verbose and unstructured. This limits:

- **Searchability:** "What did we decide about X?" requires reading full transcripts
- **Meeting prep:** No structured prior-meeting summary for briefing
- **Contact intelligence:** No per-contact decision history
- **Decision audit trail:** Decisions are buried in transcription text

## Proposed Flow

```
AI Transcription → Step 1 (CRM Wiring) → Step 2 (Action Items as Draft)
                                            ↓
                                    Adam reviews Drafts
                                    (promotes to Active, deletes, modifies)
                                            ↓
                                    Curated Notes Agent detects review complete
                                            ↓
                                    Rewrites meeting page with structured content
                                            ↓
                                    Updates GCal description with curated summary
```

---

## Design Decisions

### 1. Trigger Mechanism

**Recommended: Nightly scan with Draft-complete check.**

- Run nightly (after the Post-Meeting Agent's 10 PM run, or as a separate later pass)
- Scan meetings from the past 48 hours where:
  - Action Items relation is populated (Step 2 ran)
  - **All** linked Action Items have Record Status ≠ Draft (Adam has reviewed every item)
- If any Action Item is still Draft → skip this meeting (Adam isn't done reviewing)
- If all Action Items are Active/Inactive/Delete → meeting is ready for curation

**Why not manual trigger?** Adam would have to remember to trigger after each review batch. Nightly scan is zero-friction.

**Why 48-hour window?** Gives Adam a day to review Drafts. Meetings older than 48h that still have Draft items are likely low-priority — the agent can catch them on subsequent runs.

**Edge case:** If Adam never reviews certain Drafts, those meetings never get curated. This is fine — curation is a reward for completing review, not a requirement.

### 2. Content Preservation

**Recommended: Archive original AI summary under a collapsed section, curated version on top.**

The meeting page content after curation:

```
## TL;DR
[2-3 sentence summary of key outcomes — written by the curation agent]

## Decisions Made
- [Decision 1 — extracted from discussion context, not from action items]
- [Decision 2]

## Action Items (Final)
- [Only Active items, with current status]
- [Reflects Adam's edits — renames, deletions, additions]

## Key Discussion Points
- [Structured summary of major topics discussed]
- [Preserves important context that isn't captured in action items]

---

<collapsed: Original AI Notes>
[Full original AI transcription summary — preserved for reference and search]
</collapsed>
```

**Why preserve the original?** The raw transcript has search value — names, topics, and details that the curated version may omit. Collapsing it keeps the page clean while preserving traceability.

### 3. GCal Description Update

**Recommended: Replace the Step 3 initial summary with the curated version.**

- Check for the sentinel `--- Meeting Summary (via Notion CRM) ---` in the GCal event description
- If found, replace the entire block (between the opening and closing `---` markers) with the curated version
- Add "(Reviewed)" indicator to the header: `--- Meeting Summary (via Notion CRM) [Reviewed] ---`
- Same format constraints as Step 3: plain text, ~1,500 char target
- If Step 3 never ran (sentinel not found), append the curated summary fresh

### 4. Template Design

The curated version uses **structured template with intelligent formatting** — not rigid fields, but consistent sections that the agent fills based on meeting content.

| Section | Source | Rules |
|---------|--------|-------|
| TL;DR | AI summary + finalized Action Items | 2-3 sentences. Focus on outcomes. |
| Decisions Made | AI summary discussion context | Extract explicit decisions. Omit if none. |
| Action Items (Final) | Action Items DB (Active status only) | Use final Task Names (Adam may have renamed). Include status. |
| Key Discussion Points | AI summary topic headings | Restructure into concise bullets. |
| Original AI Notes | Existing page content | Collapse/toggle. Do not modify. |

---

## Open Questions (for future sessions)

1. **Should curated notes update Contact Notes?** E.g., after curating a meeting with Jake Gleeson, add a summary line to Jake's Contact Notes. This would build per-contact intelligence over time but risks Contact Notes becoming too long.

2. **Batch vs. per-meeting curation?** Current design is per-meeting (each meeting curated independently). An alternative is batch curation — "Here are 5 meetings from this week, produce a weekly digest." This is a different feature (weekly briefing) and probably shouldn't be conflated with per-meeting curation.

3. **Integration with meeting prep briefing.** The curated notes become the input for future meeting prep ("Last time we met with DMC, we decided X"). The briefing feature (designed in the proposal as "Future: Nightly Briefing") would query curated meeting pages to produce next-day prep. This is a downstream consumer, not part of the curation agent itself.

4. **Curation agent as Step 4 vs. separate agent?** Could be Step 4 of the unified Post-Meeting Agent, but the timing is different — it runs after Adam's review, not on the same night as Steps 1-3. Likely better as a separate agent with its own trigger and instruction page.

---

## Implementation Prerequisites

- Post-Meeting Agent cutover complete (Adam's manual steps from checklist)
- At least one week of live Post-Meeting Agent runs to validate Step 1-3 pipeline
- Adam's feedback on the template design (does this structure match how he wants to search/reference meetings?)
