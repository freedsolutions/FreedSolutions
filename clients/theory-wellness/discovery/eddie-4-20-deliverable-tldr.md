# Eddie 4/20 Deliverable — TL;DR (Pre-Brief)

**Status:** Draft for Adam review — Apr 18, 2026
**Deliverable due:** Monday, Apr 20, 2026
**Audience:** Eddie Benjamin (CPO), Theory Wellness
**Source:** 18 discovery meetings (15 first-round + 3 closing) + Liz's "Useful Links" inventory + Figma tech-stack sitemap (30 systems, current through Marie's meeting)

---

## The Reframe

The SOW frames the engagement as "map workflows, identify AI/automation opportunities, deliver prioritized roadmap." Discovery surfaced a broader root issue — and Eddie himself validated it on 4/15:

> *"Current Claude rollout is 'layering on another tool' without proper foundation. File cabinet organized, shelves labeled, resources organized — before AI can serve as the company OS."*

The real Month-1 objective is **tech-stack decision waypoints with multi-year implications** — *"where do we want to land in 2–3 years?"* The Figma sitemap (30 systems) becomes a **decision canvas**, not just a current-state inventory — used to identify SaaS-with-MCP replacement opportunities.

The SOW is honored; this framing extends it, with Eddie's 4/15 explicit buy-in.

---

## Deliverable Shape (Eddie's Ask)

Three sections, per Eddie's 4/15 request: **broad categories**, **rough framework**, **questions for future conversations**.

### 1. Broad Categories

Six themes, cross-stakeholder validated. Convergence counts are the primary signal — these are what stakeholders independently surfaced without prompting.

**A. No Centralized IT / Tech Org — 4+ independent surfacings.**
Matt G, Shaun, Greg, Alex named it directly; Eddie validated 4/15. Director of BI & Automation posting (Indeed + LinkedIn, 4/15) is Theory's first concrete move. Downstream effects: shadow IT in Finance (make.com — Ashley + Connor 4/10 independently), security vendor fragmentation (Kass — Maine not even on same provider), AI governance vacuum. *This is the spine category — every other gap ladders up to it.*

**B. Disparate Data & Google Sheets Sprawl.**
~18 new sheets/day (Matt G). BOM, FG logs, Mainstem **not** in SQL Server. "L60" means different things to different teams (Amber + Marie — same meeting, different answers). Production Dashboard operates as a **de facto software platform**. Data trustworthiness crisis: a Supply Chain 2.0 sheet error went undetected for a full year (Avery, Connor 4/10 confirmed).

**C. Sophisticated Data Strategy on Unsophisticated Software.**
Eddie's framing — matches Amber/Connor/Liz/Adam exactly (four-way agreement at executive level). "Top 1–5% of cannabis industry for data sophistication, unsophisticated tech stack." Infrastructure is the load-bearing gap: slow internet at **all** Theory locations (Amber, Connor 4/10), underpowered hardware, monthly SQL file corruption, operations staff can't load 50-column sheets. **Executive data vision exists but cannot be executed at the ground-floor operational level.**

**D. "How" Before "What" — the methodology spine.**
Adam's in-meeting synthesis, cross-validated by Mark, Liz, Connor, Amber: *"Exec. data strategy is not properly executed across operational teams — the 'how' got too little focus; execs jumped into the deep end with the 'what'. Everything breaks down at the ground-floor ops level. Not enough time for training (the 'who')."* AI on broken systems amplifies noise — independent flags from Connor, Amber, Matt G.

**E. AI Already in Production, Unevenly.**
Shaun's Python/OCR COA pipeline. Dan's label-QC pipeline runs AI today. Connor's Snowflake + MCP in progress. Kass's Gemini for in-call notes. All valuable, **semi-coordinated** — strong pockets, no shared framework yet. Mark's defining stance: *"AI is a better Admin than Strategic Mind."* Mark's thesis: *"So much rich data, no one is using it — founders are wary of their data."* Centralized framework missing — Eddie self-acknowledged 4/15.

**F. Succession & Concentration Risk.**
Sean + Avery operate as complementary **"glue" roles** (Production↔Retail and 3rd-party↔In-house). Avery is the de facto demand planner filling a role that was eliminated — dollar-quantifiable AI replacement opportunity (Avery's *"don't need to hire someone new?"* framing). Connor wants an IT role over production — the org has people who'd staff a centralized function if it existed. Dashboards live in personal Google Drives across Connor, Liz, Dan.

### 2. Rough Framework (Year 1)

Three phases. Spine: Mark's *"framework first — where do we want to land?"* Pacing: **Crawl → Walk → Run**. Execution cycle (from Amber): **Design → Train/Buy-In → Execute → Review**.

**Phase 0 — Foundation (Crawl).** *The prerequisites to everything else.*
- **Centralized ticketing.** Four independent endorsements (Judge, Connor, Liz, Eddie) — strongest single-item convergence in the engagement. HR, IT, data requests, business support.
- **IT / Tech Org hire.** In flight via Director of BI & Automation role. This is the first concrete build.
- **Infrastructure remediation.** Internet + hardware + baseline training. Nothing else in the roadmap survives without this.
- **AI communication SOPs.** Shared vocabulary and use-case framework before tool sprawl accelerates (Liz 4/13 operating principle).

**Phase 1 — Tech-Stack Decision Waypoints (Walk).** *Month-1 deep-work; the Figma sitemap is the decision canvas.*
Option A / B / C scenarios (Liz 4/13 spine). The specific decisions that gate Years 2–3:
- **ERP vs. streamline-plus-Claude.** Marie's *"why invest if AI eliminates the need in 6–8 months?"* vs. stronger team-level ERP buy-in than 2 years ago. Resolve the executive-level firm ground.
- **Dutchie B2B roadmap vs. Apex.** Timing on the transition already in-flight.
- **Wherefour IMS evaluation** (Amber). Integrates with Metronome + Dutchie; Fishbowl already passed on.
- **MCP-first architecture vs. Snowflake staging.** Eddie 4/15 preference signal.
- **Sheets → Monday consolidation.** Flower bracket system (TWX-style 2021 logic) is the hard constraint — any plan has to answer *"what replaces the bracket system?"* before claiming consolidation.

**Phase 2 — Process & AI Rollout (Run).**
- **AI replaces unfilled roles where dollar-quantifiable.** Avery's Monday-morning manual demand forecasting is the most obvious candidate.
- **Master data harmonization.** Production owns internal MDM, Compliance owns 3PI/wholesale — the split must be reconciled in any centralized strategy.
- **AP requisition-to-payment lifecycle.** Marie's #1 priority — 1,700 emails/month per state, fragmented across QBO/IES/Mineral Tree.
- **Ticketing analytics feedback.** Frequent-flyer patterns → SOPs → AI prescription (ticketing from Phase 0 pays off here).

### 3. Questions for Future Conversations

Grouped by category. These shape Phase 1; they are the conversation backbone for the next 30 days.

**IT / Tech Org**
- Scope of the Director of BI & Automation role: does it own centralized ticketing, MDM, and AI governance — or just BI + automation?
- Reporting line — direct to CPO, to CEO, or peer to Connor/Shaun/Alex?
- Relationship to embedded tech-savvy individuals (Shaun, Alex, Dan, Greg + Kass, Connor): dotted-line, hard-line, or org restructure?

**ERP vs. Dual-Path**
- Marie's personal ambivalence (*"not sure I would support ERP"*) vs. stronger team-level buy-in — where's the firm executive ground?
- Which Option (A / B / C) does Eddie want as the working assumption for Phase 1 discussions?
- What categorically requires ERP vs. what shifts to *"fix via Claude + streamline"*?

**Production / Supply Chain**
- Production → Allocation handoff — what's the trigger mechanism between FG status and the allocation sheets?
- Vault dwell time (5–7 days) — who owns the delay: procurement, retail, or space/capacity?
- Wholesale outgoing flow — what moves to Dutchie B2B, what stays in Apex through the transition?
- Co-manufacturing in Apex — which pieces are Wherefour candidates?
- BOM by product line vs. category (Dutchie BOM/VT pilot limitation) — pair with flower bracket system decision.

**Retail / Data**
- EOD reporting — who consumes the 13-store rollup, and what decisions does it actually drive?
- Promotion workflow — Sean recommends → marketing decides → Dutchie executes; Kass is the de facto discount owner per Eddie 4/6. Who owns the SOP?
- **Accessories / Apparel / Merch** — unowned category creating monthly GS-reconciliation overhead (Amber). Where does it live organizationally?

**Finance**
- Costing sheet integration into QB/IES — post-Fathom architecture?
- AP requisition-to-payment — consolidation path across the five state AP inboxes?
- Shadow IT in Finance (make.com + Air Parser) — govern or absorb into a central automation layer?

**AI Governance**
- Who sets the centralized framework Eddie self-flagged as missing on 4/15?
- When / how should teams use Claude — what's the shared vocabulary (Liz's AI-SOP concern)?
- Which production AI workflows (Shaun, Dan, Connor, Kass) become reference architectures vs. which are idiosyncratic one-offs?

---

## Tech Stack Sitemap (Companion Artifact)

The Figma flow — [Theory Wellness — Full Data & Systems Flow (30 Systems)](https://www.figma.com/board/6zlDpNDfVELmUBahiCdlaE/Theory-Wellness-%E2%80%94-Full-Data---Systems-Flow--30--Systems-) — is the visual backbone. Current through Marie's meeting (4/10).

Plan:
- **Refresh** with remaining meeting content (Avery, Amber, Kass, Marie/Kate/Ashley group, Liz follow-up 4/13, Connor follow-up 4/10, Eddie wrap-up 4/15).
- **Export as PDF** to bundle with the deliverable package.
- **Reframe usage:** not a current-state inventory — a **decision canvas**. Flag SaaS-replacement candidates with MCP eligibility marked. This turns the sitemap into a working tool for Phase 1's tech-stack decisions.

---

## SOW Alignment

The SOW scope is preserved:

| SOW Commitment | Delivered Via |
| --- | --- |
| Map technology landscape | Workflow Landscape section + Figma sitemap |
| Identify AI/automation opportunities | Categories E + F + Phase 2 roll-up |
| Deliver prioritized roadmap | Rough Framework (Phase 0 → Phase 2) |

What this reframe adds (with Eddie's 4/15 validation):
- Explicit **tech-stack decision waypoints** with multi-year implications.
- *"Where will we land in 2–3 years?"* as the Month-1 north star — not *"what tools should we buy?"*
- SaaS + MCP replacement as the sitemap's operational purpose, not documentation purpose.

---

## Open Items for Adam

- [ ] SOW reorder + "Shaun" spelling fix (sub-tasks on the AI page).
- [ ] Figma sitemap refresh — 7 meetings' worth of content to integrate before PDF export.
- [ ] Decide: include the Figma PDF in the Eddie deliverable package, or link-only?
- [ ] Decide on Phase 1 Options A/B/C — come in with a recommended working assumption, or leave fully open for Eddie?
- [ ] Decide: is the Director of BI & Automation JD framing something to nudge inside this deliverable, or keep strictly out-of-scope (tracked separately)?

---

**Next step:** Iterate this TL;DR with Adam. Once shape is locked, expand each category into 1–2 paragraphs + representative stakeholder quotes for the formal 4/20 deliverable. Pandoc → DOCX + PDF render pipeline is already working locally.
