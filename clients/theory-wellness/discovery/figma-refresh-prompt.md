# Prompt to paste into the Claude chat with the Theory Wellness Figma board

---

**Context:** This Figma board is the tech-stack sitemap for Theory Wellness, a vertically integrated multi-state cannabis operator. It documents their ~30 systems across Supply Chain, Production, Retail, Finance, Compliance, and HR. The board is the companion artifact for a formal discovery deliverable going to Eddie Benjamin (CPO) on Monday 4/20/26.

The board is currently current through Marie Preshong's 4/10 meeting. Three subsequent meetings need to be integrated:
- **Meeting 16: Liz Murphy (4/13)** — supply chain follow-up, introduced Option A/B/C tech-stack scenarios, flagged flower bracket system as consolidation constraint
- **Meeting 17: Connor Hansen (4/10)** — data infrastructure follow-up, surfaced Clasp (Apps Script SDLC) and make.com shadow IT in Finance
- **Meeting 18: Eddie Benjamin (4/15)** — discovery wrap-up, posted Director of BI & Automation role, endorsed centralized ticketing, expressed MCP-first preference

The reframe for Monday: shift the board from a current-state inventory into a **Phase 1 decision canvas** — explicit SaaS replacement candidates and MCP eligibility flagged, scenario options overlaid.

**Work to complete**, grouped by type. All text is copy-paste-ready; place and style per your judgment.

---

## 1. New nodes to add

### A. Wherefour IMS
- **Layer:** Supply Chain / Procurement, adjacent to Mainstem
- **Caption:** "Wherefour IMS — non-cannabis IMS evaluated as Mainstem + BOM sheet replacement. Integrates with Metronome + Dutchie. Alternate evaluated (and passed): Fishbowl."
- **Connections:** Dashed "replacement candidate" arrows to Mainstem node and to the BOM sheet cluster
- **Source:** Liz Murphy 4/13, Amber Cook 4/9

### B. make.com + Air Parser
- **Layer:** Finance, flagged as Shadow IT (use red or orange accent border)
- **Caption:** "make.com + Air Parser — shadow IT in Finance, no IT approval. Used by Ashley Wright for PDF renaming automation. Broader Finance adoption confirmed by Connor 4/10. Phase 1 decision: govern, absorb, or replace."
- **Source:** Connor Hansen 4/10, Ashley Wright 4/9 (independently surfaced)

### C. Clasp (Apps Script CLI)
- **Layer:** Developer tooling, attached to Google Apps Script
- **Caption:** "Clasp — Apps Script CLI, enables sandbox/production environment separation. Proper code-deployment hygiene inside the Sheets ecosystem. Connor Hansen uses it today."
- **Source:** Connor Hansen 4/10

### D. Director of BI & Automation (role node)
- **Layer:** Organization / Roles (top of board, or a dedicated Org layer if one exists)
- **Styling:** Role-node distinct from system nodes (e.g., different shape or color)
- **Caption:** "Director of Business Intelligence & Automation — role posted 4/15 on Indeed + LinkedIn. First concrete move toward centralized IT / Tech organization. Theory's answer to the four-way 'missing centralized IT' theme (surfaced independently by Matt Gerety, Shaun Seward, Greg Phillips, Alex Paulk; validated by Eddie Benjamin 4/15)."
- **Source:** Eddie Benjamin 4/15

### E. Centralized Ticketing (proposed node)
- **Layer:** Business Support / Operations
- **Styling:** Proposed / Phase 0 (dashed border, "Proposed" tag, distinct from active systems)
- **Caption:** "Centralized Ticketing — proposed, Phase 0 foundation. Four-way independent endorsement: Judge (Compliance 3/27), Connor Hansen (Data 4/10), Liz Murphy (Supply Chain 4/13), Eddie Benjamin (CPO 4/15). Scope: HR, IT, data requests, business support. Enables root-cause analysis, recurring-issue tracking, and prescriptive structure for AI to assist."
- **Connections:** Dashed lines from HR, IT, Data Requests, and Business Support
- **Source:** Multiple — Judge 3/27, Connor 4/10, Liz 4/13, Eddie 4/15

---

## 2. Option A / B / C scenario overlay

Add a legend (probably a corner of the board or a top banner) that defines three tech-stack scenarios. Then tag individual system nodes with the appropriate scenario treatment.

### Legend text

**Option A — Streamline**
- Color: green
- Definition: Minimal platform change. Keep Google Sheets ecosystem, layer Claude for cleanup and consolidation, sunset worst-offender sheets over time. ERP stays off the table.

**Option B — Targeted Replacement (recommended)**
- Color: blue
- Definition: Specific, bounded platform swaps at known weak points. Wherefour for Mainstem + BOM. Apex → Dutchie B2B as Dutchie matures. MCP-first architecture over Snowflake staging. Google Sheets remains the operational layer, but BOM, FG logs, and procurement move out. Dual approach (streamline + Claude) for everything else.

**Option C — Transformative**
- Color: orange
- Definition: Reopen ERP conversation (revisit Sage Intacct / Acumatica, evaluated and passed 2 years ago). Consolidate Sheets aggressively. Build proper analytics platform underneath. Claude as productivity accelerant on top of new foundation.

### Per-node scenario tags

Add small badges or colored accent to these nodes:

| Node | A (green) | B (blue, recommended) | C (orange) |
|---|---|---|---|
| Google Sheets | Retain | Retain as operational layer | Consolidate |
| Mainstem | Retain | Replace (Wherefour) | Replace (Wherefour or ERP) |
| Apex | Retain | Transition to Dutchie B2B | Replace (ERP) |
| BOM sheet | Retain | Replace (Wherefour) | Replace (ERP) |
| SQL Server | Retain | Retain + add MCP | Consolidate under new platform |
| Snowflake | Retain | Retain + MCP-first | Retain or replace |
| FG Tracking Logs | Retain | Move to proper IMS | Consolidate under new platform |
| Production Dashboard | Retain | Retain + connect to IMS | Rebuild on new platform |

---

## 3. Overlay annotations

### Flower bracket system constraint
- **Attach to:** Google Sheets cluster (specifically Production / Allocation sheets)
- **Caption text:** "Flower bracket system (TWX-style logic, built 2021): most complex single piece of logic in the Sheets ecosystem — e.g., TWX-1 = 0–2599g, 30%+ THC, 69% to eighths. Too intricate to migrate to Monday as-is. Any consolidation plan must answer 'what replaces the bracket system?' before claiming consolidation. Source: Liz Murphy 4/13."

### MCP-first architecture preference
- **Attach to:** Snowflake node (and/or as a banner overlay near the data-platform cluster)
- **Caption text:** "Eddie 4/15 preference: MCP access preferred over Snowflake staging where possible. Affects every third-party integration design in Phase 1."

---

## 4. Caption updates on existing nodes

Add or replace captions on these nodes with the following text:

### Mainstem
"Procurement POs. Data NOT in SQL Server. Manual monthly audits required against Dutchie. Wherefour is the leading replacement candidate. Source: Liz, Amber, Connor."

### Apex
"Wholesale B2B (outgoing). Being replaced by Dutchie B2B over the next 1–2 years as Dutchie's B2B matures. Co-manufacturing pieces may move to Wherefour (Phase 1 decision). Source: Liz, Eddie."

### Google Sheets cluster
"~18 new sheets created daily across the org (Matt Gerety). 'Plugs off of plugs' — powerful but undiscoverable (Mark Youngworth). Dashboards live in personal Google Drives across Connor, Liz, Dan (succession risk). BOM, FG Tracking Logs, Costing sheets NOT in SQL Server."

### Production Dashboard
"De facto software platform. Supply Chain, Production, Compliance all live here daily. Fed by SQL Server / Snowflake. Feeds Sean's allocation planning and Elizabeth's production tracking."

### SQL Server
"Data warehouse. API feeds from Dutchie / Metrc / Apex → master Google Sheets. Files corrupt roughly monthly (Connor + Amber independently confirmed). Claude integration via Snowflake in progress; API connection issue recently surfaced."

### Dutchie BI
"Reporting layer. Available in some states, not all. Reports take very long to load or don't load at all (Kass). Adoption limited. Could replace some Google Sheets if rolled out consistently."

### Evolve (UKG HRIS)
"New HRIS, targeting June 1 go-live. Most robust cannabis HRIS option available. 80–90% implementation complete. Fifth HRIS in 7 years — parallel data integrity challenge in HR. Owner: Alex Paulk."

### BDSA
"Competitive intelligence and market data. Onboarded ~4-6 months ago. Learning curve is the adoption barrier. API not integrated with Dutchie or allocation workflows. CannMenus under evaluation as alternative (offers MCP integration, map widget for store locator, automated menu scraping)."

---

## 5. Final step

After all edits, export the full board as a single-page PDF to:

`C:\Users\adamj\OneDrive\Documents\My Documents\Freed Solutions\Theory Wellness\Theory Wellness — Full Data & Systems Flow (refreshed 2026-04-20).pdf`

If the board is too dense for a single portrait page, export as landscape or a two-page spread.

---

## Acceptance criteria

The refresh is complete when:
- [ ] 5 new nodes added: Wherefour IMS, make.com + Air Parser, Clasp, Director of BI & Automation (role), Centralized Ticketing (proposed)
- [ ] Option A / B / C legend is on the board, with scenario badges on 8 system nodes (Google Sheets, Mainstem, Apex, BOM, SQL Server, Snowflake, FG Tracking Logs, Production Dashboard)
- [ ] Flower bracket system callout attached to the Sheets cluster
- [ ] MCP-first preference flag on or near Snowflake
- [ ] 8 existing node captions updated (Mainstem, Apex, Google Sheets cluster, Production Dashboard, SQL Server, Dutchie BI, Evolve, BDSA)
- [ ] PDF exported to the OneDrive path above

Estimated effort: 1.5–2 hours inside Figma. Everything in this prompt is copy-paste-ready — no creative writing required, just placement and styling per your judgment.
