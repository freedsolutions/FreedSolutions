# Figma Sitemap Refresh — Post-Marie Checklist

**File:** [Theory Wellness — Full Data & Systems Flow (30 Systems)](https://www.figma.com/board/6zlDpNDfVELmUBahiCdlaE/Theory-Wellness-%E2%80%94-Full-Data---Systems-Flow--30--Systems-)
**Current state:** Complete through Marie Preshong + Kate Gray + Ashley Wright group session (4/10/26).
**Needs refresh with:** Meeting 17 (Connor 4/10 follow-up), Meeting 16 (Liz Murphy 4/13), Meeting 18 (Eddie Benjamin 4/15 wrap-up).
**Purpose of refresh:** Reframe the sitemap from a current-state inventory to a Phase 1 tech-stack **decision canvas** — SaaS replacement candidates + MCP eligibility flagged.

---

## New system nodes to add

### Wherefour IMS
- **Source:** Liz 4/13, Amber 4/9
- **Node placement:** Supply Chain / Procurement layer, adjacent to Mainstem
- **Relationship:** Replacement candidate for **Mainstem** and the **BOM sheet family** (flower bracket system is the constraint — see overlay below)
- **Integrations to depict:** Metronome, Dutchie
- **Alternate evaluated:** Fishbowl (passed)
- **Caption:** *"Wherefour IMS — non-cannabis IMS evaluated as Mainstem + BOM sheet replacement. Integrates with Metronome + Dutchie."*

### make.com + Air Parser
- **Source:** Ashley Wright 4/10, Connor 4/10 (independently surfaced)
- **Node placement:** Finance layer, flagged as Shadow IT (red/orange highlight)
- **Relationship:** Used by Ashley for PDF renaming automation; Connor confirmed broader Finance adoption without IT approval
- **Caption:** *"make.com + Air Parser — shadow IT in Finance. Govern, absorb, or replace decision in Phase 1."*

### Clasp (Apps Script SDLC)
- **Source:** Connor 4/10
- **Node placement:** Developer tooling layer, attached to Google Apps Script
- **Relationship:** Enables sandbox/production environment separation for Connor's Apps Script work; underappreciated SDLC maturity datapoint
- **Caption:** *"Clasp — Apps Script CLI; proper code-deployment hygiene inside the Sheets ecosystem."*

---

## Overlay annotations to add

### Option A / B / C scenario markers
- **Source:** Liz 4/13
- **Where to overlay:** Legend/key area of the sitemap — define the three scenarios once
- **Per-node markers:** For each system being evaluated, a small colored badge or tag indicating which scenario(s) replace or retain it
  - **Option A (Streamline):** green badge — retain
  - **Option B (Targeted Replacement, recommended):** blue badge — replace or enhance
  - **Option C (Transformative):** orange badge — replace or consolidate
- **Suggested tagging:**
  - Google Sheets → A: retain | B: retain as operational layer | C: consolidate
  - Mainstem → A: retain | B: replace (Wherefour) | C: replace (Wherefour or ERP)
  - Apex → A: retain | B: transition to Dutchie B2B | C: replace (ERP)
  - BOM sheet → A: retain | B: replace (Wherefour) | C: replace (ERP)
  - SQL Server → A: retain | B: retain + add MCP | C: consolidate under new analytics platform
  - Snowflake → A: retain | B: retain + MCP-first | C: retain or replace

### Flower bracket system (TWX logic)
- **Source:** Liz 4/13
- **Where to overlay:** Attach a callout note to the Google Sheets cluster (specifically the production/allocation sheets)
- **Caption:** *"Flower bracket system (TWX-style, built 2021): most complex single logic in the Sheets ecosystem. Too intricate to migrate to Monday as-is. Any consolidation plan must answer 'what replaces the bracket system?' before claiming consolidation."*

### Director of Business Intelligence & Automation role
- **Source:** Eddie 4/15 (posted on Indeed + LinkedIn)
- **Where to overlay:** Top-level org-chart area of the sitemap, or a dedicated "Org" layer if one exists
- **Node type:** Role node (not system node), distinct styling
- **Caption:** *"Director of BI & Automation — role posted 4/15. First concrete move toward centralized IT / Tech organization. Theory's answer to the four-way 'missing IT' theme (Matt G, Shaun, Greg, Alex, Eddie validated)."*

### Centralized ticketing system
- **Source:** Judge 3/27, Connor 4/10, Liz 4/13, Eddie 4/15 (four-way endorsement)
- **Where to overlay:** New node in the business-support layer, with dashed lines connecting to HR, IT, data requests, and business support sources
- **Node type:** Proposed / Phase 0 styling (dashed border, "proposed" tag)
- **Caption:** *"Centralized ticketing — four-way endorsement (Judge, Connor, Liz, Eddie). Phase 0 foundation. Enables root-cause analysis, recurring-issue tracking, and prescriptive structure for AI to assist."*

### MCP-first architecture preference
- **Source:** Eddie 4/15
- **Where to overlay:** Above or adjacent to the Snowflake node, as a connection-style overlay
- **Caption:** *"MCP-first preferred over Snowflake staging where possible (Eddie 4/15). Affects every third-party integration design in Phase 1."*

---

## Existing nodes that need caption/connection updates

### Mainstem
- **Add caption:** *"Not in SQL Server. Wherefour candidate. Manual monthly audits currently required against Dutchie."*

### Apex
- **Add caption:** *"Being replaced by Dutchie B2B over next 1–2 years (Liz + Eddie confirmed). Co-manufacturing pieces may move to Wherefour (Phase 1 decision)."*

### Google Sheets cluster
- **Add caption or overlay:** *"~18 new sheets created daily (Matt G). Some in personal drives (succession risk). BOM, FG logs, Costing not in SQL Server."*

### Production Dashboard
- **Add caption:** *"De facto software platform. Supply Chain, Production, Compliance all live here daily."*

### SQL Server
- **Add caption:** *"Monthly file corruption (Connor confirmed). Claude integration via Snowflake in progress; API connection issue recently."*

### Dutchie BI
- **Add caption:** *"Only available in some states. Reports slow to load or don't load at all (Kass). Could replace Google Sheets in some markets if rolled out consistently."*

### Evolve (UKG HRIS)
- **Add caption:** *"New HRIS, targeting June 1 go-live. Most robust cannabis HRIS option. Alex Paulk owns. 5th HRIS in 7 years."*

### BDSA
- **Add caption:** *"Competitive intelligence, market data. Not integrated with Dutchie. Learning curve is the adoption barrier. CannMenus under evaluation as alternative (MCP-integrated)."*

---

## Suggested order of operations for the refresh

1. Add the three new system nodes (Wherefour, make.com + Air Parser, Clasp). 15–20 min.
2. Add the Director of BI & Automation role + centralized ticketing proposed node. 10 min.
3. Define the three-scenario legend (Option A / B / C colored badges). 10 min.
4. Tag existing nodes with A/B/C badges. 20–30 min across 30 systems.
5. Add the flower bracket system callout + MCP-first overlay. 10 min.
6. Update captions on existing nodes (Mainstem, Apex, Google Sheets cluster, Production Dashboard, SQL Server, Dutchie BI, Evolve, BDSA). 15–20 min.

**Total estimated effort:** 1.5–2 hours in Figma.

---

## Export for the 4/20 deliverable

Once the refresh is complete:

1. **Figma → File → Export as PDF** (single page covering the full board).
2. **Save to** `C:\Users\adamj\OneDrive\Documents\My Documents\Freed Solutions\Theory Wellness\Theory Wellness — Full Data & Systems Flow (refreshed 2026-04-20).pdf`
3. **Tell me the file exists** and I'll handle inline embedding in the final DOCX + PDF deliverable (via page-as-image embed — pandoc doesn't embed PDF natively, but a rendered PNG of the Figma export works cleanly).

If the Figma export is a large single board that doesn't fit a portrait page, we can either:
- Include it as a landscape two-page spread in the final PDF
- Keep it link-only and add a "see the live Figma link above" callout at that point in the document

Either works. The inline option is stronger for Eddie's first read-through.
