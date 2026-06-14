# Theory Wellness — Stakeholder Interview Notes
### Data, Systems & AI Discovery Engagement
**Freed Solutions | March 23 – April 23, 2026**

---

## Interview Schedule (per SOW)

| # | Stakeholder | Role | Date | Status |
|---|-------------|------|------|--------|
| 1 | Eddie Benjamin | Chief Production Officer | Mar 23 | ✅ Kickoff |
| 2 | Connor Hansen | Operations Data Manager | Mar 24 | ✅ Complete |
| 3 | Judge (Matt Judge) | Chief Compliance Officer | Mar 27 | ✅ Complete |
| — | + Shaun Seward | Compliance Associate | Mar 27 | ✅ (group) |
| — | + Corey (C Patterson) | Compliance / Operations | Mar 27 | ✅ (group) |
| — | + Kate (K Powers) | Compliance Manager | Mar 27 | ✅ (group) |
| 4 | Elizabeth Murphy | VP, Supply Chain & Production | Mar 30, 11:00 AM | ✅ Complete |
| 5 | Mark Youngworth | Chief Commercial Officer (Retail, Wholesale, Marketing) | Mar 30, 11:45 AM | ✅ Complete |
| 6 | Dan Killian | Operations / Labeling & Automation | Mar 31, 9:00 AM | ✅ Complete |
| 7 | Alex Paulk | Manager of HR Technology & Services | Mar 31, 11:15 AM | ✅ Complete |
| 8 | Shaun Seward | Compliance Associate | Mar 31, 1:00 PM | ✅ Complete (quick-hit) |
| 9 | Matt Gerety | VP of Retail | Mar 31, 3:00 PM | ✅ Complete |
| 10 | Sean McGonagle | Supply & Demand Planning Analyst | Apr 3, 10:00 AM | ✅ Complete |
| 11 | Greg Phillips | Retail Ops / De Facto IT | Apr 3, 10:45 AM | ✅ Complete |
| 12 | Kass Kazimierczak | Retail Operations | Apr 7, 9:00 AM | ✅ Complete |
| 13 | Avery Ferrusi | Manager of Cannabis Procurement (MA/ME/VT/OH/NJ) | Apr 8, 11:00 AM | ✅ Complete |
| 14 | Amber Cook | Director of Procurement | Apr 9, 9:00 AM | ✅ Complete |
| 15 | Marie Preshong | SVP Controller, Accounting & Payroll | Apr 10, 9:30 AM | ✅ Complete |
| — | + Kate Gray | Director of Accounting | Apr 10, 9:30 AM | ✅ (group) |
| — | + Ashley Wright | Senior Accountant | Apr 10, 9:30 AM | ✅ (group) |
| — | — | — | — | **— Closing Sequence —** |
| 16 | Elizabeth Murphy | VP, Supply Chain & Production (follow-up) | Apr 13, 4:00 PM | ✅ Complete |
| 17 | Connor Hansen | Operations Data Manager (follow-up) | Apr 10, 12:15 PM | ✅ Complete |
| 18 | Eddie Benjamin | Review & Alignment (final) | Apr 15, 8:30 AM | ✅ Complete |

**Calendly Pre-Meeting Q&A Highlights:**
- **Mark Youngworth:** Data-driven, uses dashboards heavily. Frustrated with limited export/interconnectivity — wants true BI capabilities.
- **Dan Killian:** Labeling nearly fully automated; plans to move to full-time coding. Wants more data access for broader automations.
- **Shaun Seward:** Wholesale order processing, COA automation, METRC transfer verification.
- **Marie Preshong:** SVP Controller, Accounting & Payroll (booked solo — Eddie had suggested grouping with Kate & Ashley).
- **Alex Paulk:** Manager of HR Technology & Services. Booked Mar 31 at 11:15 AM.

**📝 Marie Preshong Note:** Canceled her Mar 31 Calendly booking. Adam is handling the reschedule directly.

**📝 Avery (Third-Party Purchasing) Note:** New stakeholder identified by Sean McGonagle. Manages all third-party wholesale purchasing, heavy BDSA user. Adam to check with Eddie on whether to schedule a session.

**📝 Sean McGonagle Correction:** Originally assumed to be compliance/automation (confused with Shaun Seward). Actual role: Supply & Demand Planning Analyst — allocations, not compliance.

---

## Meeting 1: Eddie Benjamin — Kickoff
**Date:** Mar 23, 2026 | 11:00 AM – 12:00 PM ET
**Attendees:** Eddie Benjamin, Adam Freed

### TL;DR
Kickoff for the Data, Systems & AI Discovery engagement. Project runs Mar 23 – Apr 23 with up to 10 stakeholder interviews. Eddie is primary POC. First half covered project methodology; second half covered project prep and specifics where Eddie described team members and overall data flow.

### Key Takeaways
- Eddie described the Theory Wellness team structure and overall data flow across the organization
- Up to 10 stakeholder interviews planned over the engagement period
- Eddie emphasized that the final deliverable should go beyond AI synthesis — wants genuine strategic thinking about frameworks and highest-impact opportunities
- Mid-point check requested: high-level systems map + initial opportunity list after initial interviews
- Connor meeting should happen first to get data/systems context before department head interviews
- Engagement goal: map technology landscape, identify AI and automation opportunities, deliver prioritized roadmap

### Interview Groupings (Eddie's Direction)
- **Retail Group (1 meeting):** Kass Kazimierczak, Greg Phillips, Matt Gerety
- **Finance Group (1 meeting):** Marie Preshong, Kate, Ashley (Kate & Ashley not on intro email)
- **Connor first, Eddie last** — bookend approach

---

## Meeting 2: Connor Hansen — Data Systems Deep-Dive
**Date:** Mar 24, 2026 | 2:30 – 3:15 PM ET
**Attendees:** Connor Hansen, Adam Freed

### TL;DR
Deep-dive data discovery with Connor Hansen (Operations Data Manager). Connor walked through the full technology stack and highlighted ad-hoc reporting overload and data governance gaps. Information-gathering session — no immediate action items. Adam will circle back after department head interviews.

### Technology Stack

**Core Systems:**
- **Dutchie** — POS, seed-to-sale, inventory, catalog (retail + cannabis items + non-cannabis direct materials and finished goods)
- **Metric** — State compliance/tracking
- **Apex** — Wholesale data, B2B sales/inventory (kept separate from SQL per Eddie's direction)
- **Mainstem** — Procurement and purchase orders for raw materials/components
- **SQL Server** — Central data warehouse fed by API calls from Dutchie, Metric, Apex
- **Snowflake** — Mirroring SQL data; has integrated MCP server for Claude AI agent
- **Google Sheets** — Master sheets, dashboards, BOM, finished goods logs
- **QuickBooks** — Financial/accounting (Apex commonly used for QB integration)

**Data Flow:**
```
Dutchie / Metric / Apex → API → SQL Server → Master Sheets (Google) → Dashboards (Google)
                                    ↓
                               Snowflake → MCP → Claude AI Agent
```

**Apex is NOT in SQL Server** — kept separate per Eddie. Apex used for wholesale data reconciliation against Dutchie (sync delays between the two).

**Mainstem is NOT in SQL Server** — procurement/PO data lives in its own spreadsheet.

### Primary Source-of-Truth Data in Google Sheets (not fed from SQL)
1. **Bill of Materials (BOM)** — comprehensive product cost engine tracking components, labor, packaging. Managed by Jake. Flat assembly structure (not hierarchical sub-assemblies). Dutchie has BOM functionality now but no API access to it.
2. **Finished Goods Tracking Logs** — Google Form where departments log daily production → feeds spreadsheet
3. **Apex wholesale data** — sales and inventory reconciliation spreadsheet

### Connor's Role & Pain Points
- Builds and maintains virtually all data-connected dashboards across the organization
- Building ~3 dashboards per day; consuming all bandwidth
- Limited time to "swim upstream" and address root data quality issues
- Most dashboards live in Connor's personal drive (not shared drives) — succession risk
- Constant ad-hoc requests from across the organization

### AI Agent Status
- Recently switched from Gemini to Claude
- Connor loading CSV data into Snowflake, building skills in Claude
- Agent was successfully building reports from Snowflake data until recent API connection issue (appears to be Anthropic-side header passing issue)
- Eddie and leadership highly supportive of AI initiative
- Connor noted specific Claude pain points as an opportunity area (details to be explored in follow-up)

### Integration Challenges
- Apex API has restrictive rate limits and poor DX compared to Dutchie
- No visibility into whether Apex costs flow through to production systems
- Apex commonly used for QuickBooks integration (stronger out-of-box than Dutchie)

### Software Opportunities
- **Wherefore ERP** — could replace Mainstem + BOM spreadsheet + manufacturing workflows. Handles BOM management, costing, finished good tracking. Integrates with Dutchie, Metric, QuickBooks. Supports co-manufacturing (currently in Apex). Would inform which systems to invest in vs. migrate away from.
- If Wherefore adopted → never need to pursue Dutchie BOM functionality
- Long-term platform decisions need to be made before building automations on current systems

### Biggest Opportunities Identified
1. **Free Connor's bandwidth** — AI agent handling ad-hoc reporting; let Connor focus on data quality/infrastructure
2. **Data organization & governance** — centralize spreadsheets, establish folder structure, enable self-service access
3. **Reduce noise** — enable users to find/build their own reports vs. requesting everything from Connor
4. **Upstream data management** — better scaffolding improves AI agent outputs and data integrity

---

## Meeting 3: Judge + Compliance Team
**Date:** Mar 27, 2026 | 1:00 – 1:45 PM ET
**Attendees:** Matt Judge (CCO), Corey (C Patterson), Shaun Seward, Kate (K Powers), Adam Freed

### TL;DR
Group interview with the full Compliance department. Judge (10 years, CCO) leads a team of Corey (7 years, operations/compliance/inventory/licensing), Shaun Seward (6-7 months, compliance associate/wholesale/automation/Python), and Kate (5 years, compliance manager/investigations/SOPs). Department has built sophisticated automated workflows (Python scripts for COA scraping, Metric API integration, testing-to-menu pipeline) and wants to expand their system to other departments. Key themes: eliminate manual data entry, scale for 3 new wholesale-only markets with no additional headcount, consolidate from Monday.com to Google ecosystem.

### Team Roles

| Person | Title | Tenure | Focus Areas |
|--------|-------|--------|-------------|
| Matt Judge ("Judge") | Chief Compliance Officer | 10 years | Strategy, regulatory, oversight, research |
| Corey (C Patterson) | Operations/Compliance | 7 years | Inventory systems, APIs, testing, logistics, licensing |
| Shaun Seward | Compliance Associate | 6-7 months | Python scripts, COA automation, Metric API, wholesale processing |
| Kate (K Powers) | Compliance Manager | 5 years | Day-to-day team mgmt, investigations, SOPs for new states |

### Automated Wholesale & Testing Workflows

**Shaun's Python Pipeline (most sophisticated automation in the org):**
1. Script logs into Metric → pulls upcoming transfers
2. User selects transfers to process
3. Downloads COAs from Metric
4. OCR scrapes cannabinoid data from COAs
5. Pulls pesticide/potency data from Metric API (JSON)
6. Google service account pushes formatted data into backend spreadsheet
7. Backend sheet imported into MA testing sheet → formatted for menu upload CSVs

**Wholesale Order Processing:**
- Lives in **Monday.com** — tracks transport dates, processing checks
- Procurement manager places orders, creates "approved order sheets" with costs, strain types
- Compliance department has taken over creating assets/descriptions for wholesale products
- "Directory sheet" maintains links to vendor Dropbox/shared drives for product assets

**Internal Testing:**
- Automated years ago — no longer manually creating PMs for internal product (handled by production)
- Only manual PM creation for wholesale products
- **MDM split:** Production handles master data management for internal products; Compliance owns it for all third-party/wholesale items (3PI)

### Tech Stack & System Fragmentation

**Concurrent Systems Problem:**
- Compliance built their world around **Google Sheets**
- Procurement, HR, other departments use **Monday.com**
- Overlap creates operational complexity and duplicate subscription costs
- Compliance team would consolidate everything into Google "100 percent"

**Primary Systems Used:**
- Dutchie, Metric, Google Sheets, Monday.com
- Google Forms (internal) + Monday forms (varies by department)
- Adobe (licensing document organization)
- Email is massive — Judge receives 200+ emails/day

### Pain Points & Manual Processes

1. **Product master creation for wholesale** — manual, requires coordinating COAs, Metric data, approved order sheets, and asset/description sourcing
2. **Investigations** — major time sink; searching across Dutchie reports, Metric, voided transactions, return products to find single missing items. Kate often compares Dutchie vs. Metric sales to catch double-posting variants
3. **License renewals** — each city/state has own portals and forms; inherently manual but fairly organized
4. **Email volume & spam** — significant burden; working on filters
5. **Research department** — compliance handles regulatory/legislative research for Eddie and company, plus hemp-side inquiries. Judge framed this as the "Eddie Enablers" — they either enable or shut down Eddie's ideas based on regulatory feasibility.
6. **Asset sourcing** — getting images and descriptions from third-party wholesale vendors remains a struggle

### Expansion & Resource Constraints (CRITICAL)

- **3 new wholesale-only markets** coming in next 1.5 years: New Jersey, Ohio, Vermont
- **No plans to add compliance headcount**
- New markets = 100% of item flow is compliance department's responsibility (vs. current vertical markets where production handles a portion)
- Judge's goal: **eliminate all manual data entry** — team manages processes and monitors automated systems

### Automation Opportunities Discussed

1. **Ticketing system** — for compliance, HR, facilities, IT. Would enable tracking recurring issues, root cause analysis, KPI measurement, and substantiating workload. Judge expressed strong interest.
2. **SOP automation** — AI-maintained SOPs that update with regulatory changes. Claude formats better than ChatGPT for this. Kate has used AI but wasn't satisfied with ChatGPT formatting consistency.
3. **Master data management** — foundation for everything else. 3 new market launches = natural opportunity to build right from the start.
4. **Dutchie AI platform** — monitoring to avoid duplicating work Dutchie will solve natively (especially for investigations)
5. **Email governance** — organizational rules for email usage to enable AI assistants

### Key Quotes & Signals
- Judge: Goal is to get to where "my team is just managing the processes, watching the computers, essentially, making sure they're doing their job right"
- Compliance team has been driving automation internally (not just Eddie) — Dan and Connor originally built bots under compliance, then moved to Eddie's department
- Shaun's Python/OCR pipeline is the most advanced automation in the org — strong technical capability to build on
- Team strongly prefers Google ecosystem consolidation over Monday.com

---

## Meeting 4: Elizabeth Murphy — VP, Supply Chain & Production
**Date:** Mar 30, 2026 | 11:00 – 11:45 AM ET
**Attendees:** Elizabeth Murphy, Adam Freed

### TL;DR
Discovery session mapping Theory's full digital workflow and pain points from supply chain/production perspective. Elizabeth's domain spans Dutchie (retail POS + manufacturing conversions), Metric (cultivation), a central Google Sheets Production Dashboard fed by SQL/Snowflake, Mainstem (procurement POs), and Apex (wholesale B2B). Critical gaps: no centralized demand planning, fragmented ERP assembled from spreadsheets, Elizabeth building ~3 dashboards daily and consuming all bandwidth. Confirmed Wherefore ERP and Dutchie B2B as platform replacement opportunities.

### Elizabeth's Role & Background
- With Theory since the beginning of rec sales — predates Eddie joining the company (10+ years)
- Has touched compliance, operations, supply chain, production
- Primary focus: data integrity throughout the company and connecting disparate systems
- Collaborates closely with Judge's compliance team on product creation and single-source-of-truth initiatives

### Digital Workflow — Production/Supply Chain Lens

**Cultivation:**
- Metric used exclusively for cultivation tracking (not Dutchie)
- Cultivation schedules are manual Google Sheets (days in veg, flower cycles) — not tied to any system

**Production Dashboard (central hub):**
- Used daily by supply chain, production, compliance, Eddie
- Contains: Metric flower data, failed inventory, wholesale procurement data (manual), Dutchie API sales, product masters, production targets, inventory calculations, DOH goals
- Essentially functions as software — people live in this sheet

**Manufacturing Flow (Dutchie):**
- Uses conversions (not bombs/assemblies) to track: components → bulk → finished goods (bulk + packaging/labels)
- All direct materials and components created in Dutchie with costs
- BOM sheet compiles component costs to derive finished good cost → flows back to Dutchie as reporting engine
- Separate costing sheet calculates labor, testing, and transportation costs per recipe (everything except overhead — working on adding)
- BOM structure is flat assembly, maintained by Jake

**Procurement:**
- Elizabeth's team controls all POs and approvals — flows to AP after execution
- Mainstem handles PO processing (not in SQL Server — separate spreadsheet)
- Dutchie-Mainstem integration available but "hasn't played nice" — duplicate entry required
- Same issue with Apex integration

### Demand Planning Gap (CRITICAL)
- No formal demand planning system exists
- Monthly targets set manually: current inventory → DOH goal × sales
- Push system (supply chain/Elizabeth set targets) rather than pull (sales-driven)
- Allocation based on historical sales — creates blind spots for lost wholesale sales
- Elizabeth described this as "the really broken piece" — needs replacement with actual demand planning tool

### Pain Points — Production/Supply Chain Specific
- **Google Sheets scale limitations** — data load hitting size constraints when consolidating budget, forecast, production, sales, promotions
- **Dashboards in personal drive** — succession risk (same pattern as Connor)
- **~3 ad-hoc dashboards/day** — consuming all bandwidth, limiting upstream data quality work
- **No centralized tool** connecting all planning elements — requires multi-reference approach
- **Duplicate entry** across Apex and Mainstem due to broken integrations
- **MA regulatory constraint** — Metric packages limited to max 3 containers per tag — every finished goods package gets individual tag — warehouse logistics nightmare

### Software Opportunities Confirmed
- **Wherefore ERP** — would replace Mainstem + BOM sheet + manufacturing workflows. Dutchie/Metric/QuickBooks integration. Elizabeth not opposed.
- **Dutchie B2B** — will likely replace Apex in next couple years. All retailer/cultivator data already in Dutchie.
- **Platform migration risk** — don't invest in automations on systems being replaced
- Elizabeth offered to provide comprehensive end-to-end seed-to-sale process mapping for next phase

---

## Meeting 5: Mark Youngworth — Chief Commercial Officer
**Date:** Mar 30, 2026 | 11:45 AM – 12:30 PM ET
**Attendees:** Mark Youngworth, Adam Freed

### TL;DR
Strategy-heavy discovery session with Mark Youngworth (CCO). 30 years multi-unit retail (Dunkin' Brands, Ascend), joined Theory Memorial Day 2025. Key theme: Theory has powerful but disorganized data infrastructure ("plugs off of plugs") and a production-driven model that needs to flip to sales-driven. Both agreed that "how" problems (data management, process, governance) must come before AI. Mark wants AI for business value (M&A, pricing, segmentation) — not email summaries. Strong strategic alignment with Adam's approach.

### Mark's Background
- CCO: leads retail, wholesale, and marketing (sales P&L, brand building)
- 18 years at Dunkin' Brands (marketing/operations, domestic + international)
- 5 years at Ascend — early MA cannabis; opened Friend Street, Newton; brought in Lowell Smokes, Miss Grass, Edie Parker brand partnerships
- Joined Theory ~Memorial Day 2025 (consulting with Brandon/Nick since prior November on hemp CPG business)

### Key Insights

**Production vs. Sales Misalignment:**
- Theory historically production-driven — "Eddie produces what he wants, then they sell it"
- Mark: "No standard business should use production to drive sales. You use sales to drive production."
- Lack of demand planning creates inventory backlog — same strains at different test levels sitting in vault while new batches arrive
- Vision: real-time visibility into pipeline, inventory, and velocity to trigger promotions automatically before new batches arrive

**Data Access Gap:**
- Mark cannot quickly access top-selling SKU data across dispensaries without manual Dutchie work
- Retail team operates transactionally rather than strategically due to lack of accessible data
- No onboarding or directory for Google Sheets — "you find out over time by accident"
- Described sheets as "plugs off of plugs" like A Christmas Story circuit breaker

**AI Strategy Concerns:**
- Wants AI for business value: M&A decisions, site selection, production efficiency, pricing optimization, labor management, consumer segmentation
- Current consumer segmentation is only 4 segments across entire customer base — called this "obscene"
- "If our endgame is using AI to take meeting notes or cut a headcount, holy shit, are we messed up"
- Progress over perfection — but "progress without vision is a mess" — treadmill activities (motion without movement)

**"How vs. What" Alignment:**
- Strong alignment with Adam's framework: orgs focus on "what" problems (dashboards, reports) when real issues are "how" problems (data management, software usage, meeting structure)
- AI on top of broken systems amplifies noise
- "Everyone is really quick to want to celebrate AI and it's like the poster board is upside down" (Subaru monkey analogy)

### Cannabis Market Context (from Mark)
- Every rec market follows same curve: green rush → supply-demand balance → oversupply/price competition
- MA now in commodity/promotion-driven phase
- Vapes outselling flower in the West; MA flower down YoY, vapes up; youngest consumers prefer vapes
- Great Barrington dropped from $30M annually as neighboring states opened rec
- Chicopee facing saturation from better-located competitors

### Team Structure Clarified
- **Matt Gerety** (retail ops) — reports to Mark
- **Greg** and **Kass** — report to Matt Gerety
- Mark will coordinate with Matt Gerety on whether Greg/Kass need separate discovery calls
- Brandon and Nick are founders/owners

---

## Meeting 6: Dan Killian — Operations / Labeling & Automation
**Date:** Mar 31, 2026 | 9:00 – 9:45 AM ET
**Attendees:** Dan Killian, Adam Freed

### TL;DR
Dan manages automation, labeling systems, and data dashboards. Over 4 years he automated label creation from manual Adobe InDesign to autonomous data merge scripts. Confirmed the same tech stack patterns (Dutchie, Metrc, SQL Server, Google Sheets as lightweight ERP) and identical pain points: ~3 dashboards/day, personal drive succession risk, no time for upstream data quality.

### Key Findings
- **Label automation journey:** Manual Adobe InDesign → data merge scripts → now fully autonomous (scripts check email for COAs, upload testing data, prepare label CSVs, generate barcodes via custom Adobe Extend Scripts)
- **Barcode structure:** Batch ID as parent with product-specific suffixes; MA regs drive structure per product category
- **Dan took over from Connor** on labeling/testing bots when their roles diverged; Connor moved to broader data/reporting
- **Tracker ecosystem:** Liz requested label CSV trackers — Dan was building an entire tracker ecosystem before scope expanded
- **Same patterns as Connor/Elizabeth:** ~3 dashboards/day, personal drive storage, limited time for upstream data quality
- **Google Sheets = lightweight ERP + database** — works until AI deployment at scale
- **Opportunity:** AI agent for ad-hoc reporting to free Dan for infrastructure and data quality work

---

## Meeting 7: Alex Paulk — Manager of HR Technology & Services
**Date:** Mar 31, 2026 | 11:15 AM – 12:00 PM ET
**Attendees:** Alex Paulk, Adam Freed

### TL;DR
Discovery session covering HR's tech landscape. Alex is a self-taught systems thinker who builds workarounds (Google Forms ATS, Monday.com automations) but expressed cautious AI skepticism due to training overhead and data security concerns (SSNs, bank accounts). Major themes: Evolve (UKG) HRIS implementation targeting June 1, Theory has changed HRIS 5 times in 7 years, and no centralized IT function.

### Key Findings
- **Role:** Manager of HR Tech & Services under Ken Langdon (VP of HR). 6 years at Theory (specialist → generalist → current role). Manages email/Drive admin, Monday.com hiring boards, benefits, licensing, HRIS implementation.
- **Evolve (UKG) implementation:** 80–90% complete, targeting June 1 go-live across all markets. Most robust HRIS in cannabis space.
- **HRIS churn:** Theory has changed HRIS 5 times in 7 years — constant data integrity challenges. People Guru/UHC integration consumed 7+ months in 2023 due to coding errors.
- **No formal ATS:** Built Google Form + approvals extension workaround with recruiter Marcy.
- **Monday.com:** Alex built and expanded from 1 to 15 location-specific hiring boards, now consolidating to 1. Automations turn off unpredictably.
- **Employee licensing:** Tracked via spreadsheets across MA (IIN), ME (IIC), OH, VT. Payroll-integrated renewal reimbursement ($52/mo for ME renewals added to paychecks proactively).
- **AI concerns:** Training overhead, data security (PII), governance in shared Claude environment. Recognizes it's coming but wants "measure twice, cut once."
- **Org insight:** Ken's goal is to break out of standard HR org chart by leveraging Alex as tech thinker. Alex is "the glue" — takes on work to help others, sometimes to own detriment.

---

## Meeting 8: Shaun Seward — Compliance Associate (1:1 Follow-Up)
**Date:** Mar 31, 2026 | 1:00 – 1:45 PM ET
**Attendees:** Shaun Seward, Adam Freed

### TL;DR
Deeper 1:1 following the Judge group meeting. Shaun detailed his Python automation architecture: browser automation (not Metrc API) to avoid fees, lab-agnostic dynamic scripts, Maine fully automated for both internal and wholesale testing. Key finding: AI models tested for COA extraction but rejected — never 100% accurate and compliance requires precision. Also identified PM creation as next automation target.

### Key Findings
- **Started October 2025** — first role in cannabis, but strong Python/automation background
- **Python pipeline architecture:** Uses browser automation (mimics web browser via Python libraries + cookies) rather than Metrc API to avoid potential API fees. VS Code + GitHub repos.
- **Lab-agnostic design:** Scripts dynamically adapt to different COA formats without needing separate bots per lab. Internal testing (Cat Labs in ME, Keisha in MA) much easier — controlled formats.
- **Maine fully automated** for both internal and wholesale testing data
- **AI for COA extraction tested and rejected** — never 100% accurate; compliance requires precision. OCR/PDF scraping is brittle but unavoidable.
- **Master data challenge:** Same analyte spelled differently across labs, capitalization inconsistencies, percent vs mg/g units. Harmonization needed.
- **PM creation opportunity:** High-volume manual data entry. Vendors name products differently in Metrc vs. Theory's naming. Enough cross-referenced data exists to train a model.
- **Took over from Dan Killian** on testing automation — Dan shifted to labeling. Goal was same-day fix capability vs. weeks-long delays.
- **Interested in:** Claude Code integration in VS Code, agent swarming capabilities

---

## Meeting 9: Matt Gerety — VP of Retail
**Date:** Mar 31, 2026 | 3:00 – 3:45 PM ET
**Attendees:** Matt Gerety, Adam Freed

### TL;DR
Discovery session with Matt Gerety (VP of Retail, joined Jan 2025 from Target/Under Armour). Theory in "messy middle" — 15 stores, expanding to Virginia (5 licenses). No store-level P&Ls, no sales-based scheduling, pricing was uniform across all locations for 8 years. Greg Phillips serves as de facto IT/data person for retail. Strong alignment on need for centralized BI function.

### Key Findings
- **Background:** 18 years at Target + Under Armour. Consolidated VP of Retail and VP of Retail Ops roles. Theory's "Retail 2.0" hire.
- **"Messy middle":** Transitioning from startup (2 stores) to scaled ops (15+ stores, VA expansion with 5 licenses)
- **No store-level P&Ls:** Company-level only. Cannot determine profitability by location (concern about Augusta, ME).
- **Revenue targets based on "feelings and gut"** — first time in 8 years creating projections from retail + wholesale forecasts
- **Pricing:** Same prices across ALL locations for 8 years (GB to Medford) without accounting for transport costs or local economics. Now implementing store-specific pricing via BDSA data, but all manual.
- **BDSA:** Recently invested in competitive intelligence platform — first structured external data source. API could feed centralized database.
- **Labor/scheduling gap:** Evolve handles time and attendance but not sales-based scheduling optimization. 12 different internet providers across 13 stores before recent Comcast consolidation.
- **Greg Phillips:** De facto IT/data person for retail and most offices (except Bridgewater/Main Grove production). All data requests flow through Greg.
- **IT waste examples:** Bridgewater store pays $900/mo for WiFi with 6 unused phone lines
- **Culture insight:** Many Theory leaders started as cannabis consultants — only worked at Theory. Brandon/Nick historically protective of data sharing with external vendors.
- **Vision:** Centralized data intelligence/BI function as new IT-led business unit

---

## Meeting 10: Sean McGonagle — Supply & Demand Planning Analyst
**Date:** Apr 3, 2026 | 10:00 – 10:45 AM ET
**Attendees:** Sean McGonagle, Adam Freed

### TL;DR
Discovery session exploring allocation workflows and digital tools. Sean manages batch-level product allocations across all Theory stores in MA and ME using Google Sheets, performing allocations twice weekly. Collaborates with Avery (third-party purchasing) to fill menu gaps. Key opportunity: consolidate fragmented data sources and add forecasting/pre-allocation capabilities upstream. Sean's role is "system glue" between production and retail.

### Key Findings
- **Role:** Supply & Demand Planning Analyst, started mid-to-late January 2025. Manages allocations for all MA and ME stores. Wholesale treated as additional "storefront" for allocation purposes.
- **Primary tool:** Massachusetts Allocations and Menu Health Google Sheet — batch-level tracking across categories (flower, pre-rolls, vapes, concentrates, beverages, etc.)
- **Allocation cadence:** Twice weekly (formerly once weekly). Targets ~30 DOH for larger categories. Uses L7 sales data.
- **Workflow:** Hand-keys allocations → script generates date-stamped summary → emails to inventory teams for execution
- **Menu Health:** Separate sheet tracking variety goals by store and category (indica/sativa/hybrid). Gaps coordinated with Avery for third-party fills.
- **Dutchie usage:** Daily reference for strain types, inventory discrepancies, cross-referencing sheet data
- **Production Dashboard:** Uses for pipeline visibility, but no pre-allocation capability for products still in production
- **Avery (third-party purchasing):** Heavy BDSA user; fills menu gaps when production can't meet variety goals. Adam flagged potential session with Avery (ask Eddie first).
- **Background:** Came from clothing retail where pre-allocation drove procurement (pull model). Cannabis is push model — allocate what you have.
- **Pain points:** Must check 5 different places to make one decision. No forecasting layer connecting production schedule to allocation planning. No pre-allocation for pipeline products.

### Net-New Context (not previously captured)
- **Sean McGonagle is NOT compliance** — he's supply chain / demand planning. Completely different role than was assumed.
- **Batch-level allocations** are atypical for most industries — adds significant complexity
- **Avery** is a new stakeholder not on Eddie's original list — manages all third-party purchasing
- **Capacity planning friction:** Store managers push back on Sean's allocation reports saying they can't fit more inventory (ties to Greg's vault space pain point)

---

## Meeting 11: Greg Phillips — Retail Operations / De Facto IT
**Date:** Apr 3, 2026 | 10:45 – 11:30 AM ET
**Attendees:** Greg Phillips, Adam Freed

### TL;DR
Discovery session with Greg Phillips, 7-year Theory veteran who serves as the de facto IT person for retail and most offices. Greg uses Google Sheets as "scrap paper" — solves problems and moves on rather than building robust systems. Key pain points: Dutchie ecomm admin vs. back office disconnect, discount reporting complexity, EOD report inconsistency, and vault capacity planning. Confirmed the no-centralized-IT theme and siloed tech-savvy individuals pattern.

### Key Findings
- **Background:** 7 years at Theory. Started as budtender in 2017 (BioTrak era → LeafLogix → Dutchie). Progressed through inventory, loss prevention, audit, retail ops, implementation.
- **Current focus:** New site openings + ongoing management. Currently remodeling Chicopee and Great Barrington toward back-of-house kiosk model (Kiosk Pro just implemented in Chicopee yesterday).
- **De facto IT role:** Handles IT issues, security vendor changes, network problems, back office reporting for retail. Gets pulled into compliance/security/other departments due to tenure + cross-functional knowledge.
- **Greg's Sheet philosophy:** Uses Google Sheets as "scrap paper" — pulls data, solves problem, moves on. Doesn't build robust long-term solutions. Connor helps build more permanent solutions when Greg identifies gaps.
- **Dutchie pain points:**
  - Biggest disconnect: ecomm admin vs. back office reporting
  - Kiosk data limited (Mac ID only, no detailed location tracking), slow exports
  - Dutchie BI only available for MA — can't replicate across states
- **Discount reporting:** Translating discount data back to plain-language campaigns is painful. A 7-item meal deal across 7 stores = 49 line items requiring manual math. Retail ops absorbed discount reporting since VP of Marketing left 2 months ago.
- **EOD reports:** Manually gathered from 13 store managers with 50-80% completeness. Brittle communication system.
- **Vault capacity planning:** Ongoing friction between retail vault space, production space, and product flow. Managers push back on allocation reports saying they can't fit more. No formal area constraints in breadth/depth planning (ties to Sean's allocation work).
- **Retail Hub:** Living calendar and shared space for retail ops team + district managers (Kayla Cholo, Ryan Vero). Standardizing folder structures across stores is a challenge.
- **BDSA:** Recently started using for forecasting but not integrated with anything.
- **Security integration:** New Minnesota vendor will pull Dutchie data to link camera footage with specific transactions.

---

## Meeting 12: Kass Kazimierczak — Retail Operations
**Date:** Apr 7, 2026 | 9:00 – 9:45 AM ET
**Attendees:** Kass Kazimierczak, Adam Freed

### TL;DR
Discovery session with Kass, Retail Operations. She and Greg Phillips form Theory's de facto retail field IT team. Covered multi-state tech stack (different compliance systems per state), security/network fragmentation, Google Workspace clutter, and failed Monday.com adoption. Strong alignment on the "who and how before what" framework. Kass will send a systems inventory document via email as a follow-up artifact.

### Key Findings
- **Role:** Retail Operations. Partners with Greg Phillips as Theory's retail field IT — confirming the no-centralized-IT theme.
- **State-specific compliance systems (NEW):**
  - **NH:** BioTrack + iHeartJane (regulatory requirement)
  - **OH:** OARRS
  - **VT:** VCCB
  - **MA/ME:** Dutchie as primary
  - Each state layer adds complexity and fragmentation
- **BDSA adoption:** Onboarded ~4-6 months ago for competitive pricing and wholesale analysis. Learning curve remains a barrier to full adoption.
- **CannMenus (alternative under consideration):** Offers MCP integration for AI agent access, map widget for store locator, automated menu scraping/alerts (similar to LitAlerts). Potential BDSA alternative worth evaluating.
- **Monday.com adoption FAILED:** Team tried it for task management; reverted to Google Sheets due to learning curve. Adds weight to the "Google ecosystem consolidation" theme.
- **SoLink pilot (Minnesota):** AI-camera variance investigation integrated with Dutchie. Being evaluated for org-wide rollout.
- **Training & SOP stack:**
  - **LMS via Evolve** — training content delivery
  - **Scribe** for SOP documentation (pushing for enterprise adoption)
- **Weedmaps / Leafly:** Only used for 90-day new-store SEO presence. Minimal ongoing operational value.
- **Security fragmentation (CRITICAL):** Systems vary by state AND by store. Maine stores are not even on the same provider. No centralized security vendor.
- **Google Workspace clutter:** Major pain point. Orphaned email groups, unknown document owners, no centralized directory. Ties directly to the "how we work" shadow project theme.
- **Communication structure:** Google Chat per store + email groups. Bud tenders get Theory email accounts.
- **Dutchie BI:** Available in some states but not all — adoption is limited. Could replace some Google Sheets if rolled out consistently.
- **Philosophical alignment:** Strong agreement on "who and how must precede what" — org structure and data governance before tools and AI. Master data management as foundation.

### Follow-Up Notes (via email, Apr 7 — "Notes")
Kass sent her prep/review notes from the call. Captured in full below.

**Systems Used (per Kass's notes):**
- **Dutchie:** POS, Backoffice, and Ecommerce are the most used
  - Some states have BI reporting but "have not found the benefit yet" — reports take very long to load or don't load at all
  - Working to get into a **Zebra handheld device beta** with Dutchie for audits, pre-order packing, and inventory tasks. Kass used a similar device in a previous job and is trying to bring that vision to Theory.
- **BioTrack + iHeartJane (NH):** Running under a **managed services agreement**. "iHeartJane menu is lacking — not as robust as Dutchie ecomm, and BioTrack doesn't offer good information for the online menu to pull from."
- **Weedmaps & Leafly:** Prioritized during new store openings (SEO/maps/searches). Typically not maintained past 90 days, but exceptions exist — e.g., **online ordering is still live in Kittery**.
- **State Tracking Systems:** Metrc, OARRS (Ohio), VCCB (Vermont)
- **BDSA wishlist (from Kass):**
  - Integrate BDSA with Dutchie
  - Compare popular/top-selling products against live menus to flag opportunities
  - Flag stores selling Theory's products at lower prices than Theory's own retail
- **Security & Network stack (specific vendors):** Interface/Vector, SoLink (MN only), ME Fire & Security, Hik-connect, Comcast
- **Monday.com:** Tried for large project planning and gantt chart view — pivoted to a Google Sheet replacement (link provided). "A lot of manual labor."
- **LMS:** Where all trainings are posted and taken. Joint ownership between retail trainer, HR, and Compliance.
- **Scribe:** Creates step-by-step process documentation with screenshots — used for training and best practices.

**Google Stack — "HEAVY reliance on Google products" (Kass's words)**

*Bookmarked Sheets she shared:*
- **Pricing Guides** — used by all vertically integrated stores
- **New Store Ordering** — "needs lots of improvements"
- **Ops Guidebook** — used to brainstorm ideas and house needed info for her team
- **Monday.com replacement sheet** — the sheet that absorbed Monday.com's project planning

*Google Docs:*
- Heaviest use for meeting and site visit notes
- Very manual process, but helpful for meeting prep
- **In-call notes typically taken by Gemini** (NEW — shows existing AI note-taking adoption in retail)
- Site visit notes are very manual and hard to maintain

*Google Forms:*
- Submission for strain descriptions
- Inventory issues
- Closing in Retail
- Store Audits (WIP)

**Pain Points & Wishlists (direct from Kass):**
- **Google clutter:** "Google is very cluttered with old sheets, SOPs, shared drives, etc. that make it difficult to streamline processes across multiple sites/states."
  - Tried to create a new retail shared drive as "source of truth" for all stores, but can't fully commit because they don't know what else exists out there that could be deleted/archived
  - Wishlist: "Start with a clean slate by gathering everything, assessing what is useful and not useful, and curating/creating updated best practices"
- **Quote of the meeting:** *"We drive the train and build the tracks very often, and haven't given ourselves enough time to clean up our Google suite."*
- **Same cluttered feeling in IT, Security, and Network** — all need clean slate + streamlined process, no time to uproot thoroughly
- **Need an IT department.** "Our team, mainly Greg, supports the company's needs with all IT-related hardware and software, which is difficult to maintain at the standard I/we would like because we are focused on so much more than IT."
- **Email-heavy company.** Keeping up on inboxes is challenging when traveling or on-site. "Haven't found the right script that helps me manage the inbox well."

### Cross-Context Note (from Eddie email, Apr 6)
- Eddie confirmed Kass "does an enormous amount of dutchie-related work. (probably the primary person who messes around with discounts / pricing settings, etc)." This positions her as the de facto owner of the Dutchie promotions/discounts workflow that Matt G and Sean flagged as painful and opaque.

---

## Meeting 13: Avery Ferrusi — Manager of Cannabis Procurement
**Date:** Apr 8, 2026 | 11:00 AM – 12:00 PM ET
**Attendees:** Avery Ferrusi, Adam Freed

### TL;DR
Discovery session with Avery, Theory's cannabis procurement manager/buyer covering MA, ME, VT, OH, NJ (Minnesota coming next). Avery **effectively operates as both buyer AND demand planner** — the former demand planner role was left unfilled and he absorbed it. Covered his weekly demand planning workflow (Connor's Supply Chain 2.0 sheets, BDSA, Monday, Dutchie), vendor negotiation process, and three major pain points: need for AI-powered demand planning, data trustworthiness issues, and retail execution delays (5-7 day vault dwell time). Every PO requires CEO Brandon Pollack's email approval. Avery hasn't used AI much personally but is excited — learned about Theory's Claude AI project days before the call.

### Background & Role
- **6+ years at Theory.** Career path: budtender (2019) → inventory specialist → allocation coordinator → current procurement role.
- **Manages buying for 5 states:** MA, ME, VT, OH, NJ. **Minnesota coming next.**
- **Scope:** Both finished goods wholesale purchasing AND raw materials (bulk flower, distillate, trim) for production.
- **Critical structural gap:** The former demand planner role was left unfilled. Avery absorbed those responsibilities on top of his buying work. He IS Theory's cannabis demand planner.
- **Executive approval gate:** Every PO requires CEO Brandon Pollack approval via email summary — includes strain lists, pricing, days of supply projections.

### Weekly Workflow (Monday = Demand Planning Day)
1. Reviews **Menu Health sheets** across 15+ locations (grading inventory against goals — e.g., 10+ half ounces = meeting goal)
2. Pulls data from **Connor's Supply Chain 2.0 Google Sheets** (SKU-level sales rates, days on hand, sold-out tracking per state)
3. Cross-references **BDSA** market data to identify top-selling competitor products and validate buying decisions
4. Checks **Monday boards** for logistics/delivery status
5. Uses **Dutchie** for spot-checking and forward-facing menu/catalog view
6. Identifies gaps → determines purchase quantities by category and store
7. Reaches out to vendors, negotiates, assembles orders
8. Sends executive summaries to Brandon and leadership for approval

### Vendor Relationships & Negotiation
- **Negotiation factors:** strain selection, testing levels, harvest/expiration dates, existing inventory overlap, price points
- **Repeat MA/ME partners with established discount structures:** Jeter, Fernway, Vanguard — reduces negotiation overhead
- **Mike** (Avery's hire) supports OH and NJ — handles menu pulls and initial vendor outreach
- **Reciprocal buying relationships** are common (Theory buys from wholesale partners who also buy Theory product)

### Key Pain Points
- **Biggest need: AI-powered demand planning.** Wants a system that auto-generates purchase recommendations (quantities by category/store) instead of manually reading every line of spreadsheets every Monday morning.
- **Data trustworthiness issues:**
  - Sales rate calculations sometimes incorrectly count zero-sales days for brand-new products (not yet launched days)
  - **A supply chain sheet error went undetected for a full year.** When discovered and corrected, it required full reallocation across stores.
- **Retail execution delays:** Products purchased and delivered often sit in vault **5-7 days** before hitting the menu due to staffing/space constraints. Avery can buy correctly but retail can't execute on time.
- **No shelf space calculation in allocation model.** Breadth and depth are tracked, but physical area constraints are not — reinforces Sean's vault capacity finding.

### Market & Pricing Dynamics
- **MA moving to two-ounce purchase limit** — will materially increase buying pressure
- **Theory dropped flower pricing to three tiers:** $15 / $20 / $25 eighths — moving old inventory but requiring more frequent restocking
- **Value focus in low-income markets:** Trenton NJ, Columbus OH
- **$100/lb flower COG possible** with automation + better cultivation (Avery's prediction)
- **VT border market:** Theory's southern Vermont locations compete with Massachusetts pricing

### AI & Technology Discussion
- Cannabis has the **most robust CPG data set** but industry doesn't use it properly
- Historical data has limited value due to rapid market changes
- Avery hasn't used AI much personally but is excited to try it for job time-savers
- Theory recently started a **Claude AI project**; Avery learned about it **days before this call** — suggests internal AI communication gaps
- **Master data management identified as foundational need** before effective AI implementation (reinforces theme from Shaun + Dan)
- Adam's framing: AI is powerful enough to solve "stupid stuff" in Theory's fragmented software landscape but poor implementation creates more noise (email/Slack examples)

### Org Structure Notes (from Avery's lens)
- **Amber Cook handles NON-cannabis procurement** per Avery — packaging, labeling, accessories. ⚠️ *This partially contradicts Amber's own framing in her intro email ("all things procurement while Avery is focused on cannabis procurement"). Need to clarify with Amber tomorrow — likely Amber has directorial oversight of all procurement while personally owning non-cannabis day-to-day.*
- **Connor Hansen:** Builds all data-connected dashboards and maintains supply chain sheets
- **Sean McGonagle:** Allocation and menu health reporting
- **Matt Gerety:** VP of Retail
- **Greg Phillips:** Involved in operational discussions
- **Mike:** Avery's OH/NJ support hire

### Production & Compliance Collaboration
- Avery works closely with production on bulk raw material purchasing — understands COG across markets
- **Product catalog management** (descriptions, images) currently handled by Compliance team but **ownership is under discussion**
- **Dutchie rolling out a beta** to auto-populate vendor-provided images and descriptions — reduces manual catalog work (NEW integration datapoint)

---

## Meeting 14: Amber Cook — Director of Procurement
**Date:** Apr 9, 2026 | 9:00 – 9:45 AM ET
**Attendees:** Amber Cook, Adam Freed

### TL;DR
Discovery session with Amber Cook, Theory's Director of Procurement covering non-cannabis procurement (packaging, labeling, accessories, direct/indirect materials). Amber brings **11 years of regulated cannabis experience** and deep supply chain/demand planning expertise (Amazon, Thrasio — managed $400M brand and 120 containers every 4 months across 16 countries). Her assessment: Theory is **data-sophisticated (top 5% in cannabis) but execution-constrained** by hardware, internet, and training gaps. Three critical revelations: (1) slow internet at ALL locations kills data tool adoption, (2) SQL files corrupt at least monthly, (3) Dutchie is fundamentally inadequate for manufacturing/inventory management — they're piloting BOM/assemblies in VT with scaling issues.

### Background & Role
- **11 years** in regulated cannabis, **20+ years** total industry experience. Started at NETA where she worked closely with Eddie.
- **Prior roles:** Demand planning at hotels, Staples (PCs), Amazon, Thrasio ($400M brand, 120 containers/4 months, 16 countries).
- **At Theory 3 years.** Brought in by former VP of Supply Chain Jackie to tackle data issues.
- **Scope:** Non-cannabis procurement — packaging, labeling, accessories, direct/indirect materials. Two contractors (one based in Pakistan) handle non-cannabis procurement; US-based lead handles cannabis items (Avery).
- **1,000+ POs** managed, mix of direct and indirect materials.
- **Amber conducts quarterly lunch-and-learns** company-wide to teach Google Sheets, system usage, and identify operational pain points.

### Critical Infrastructure Constraints (NEW THEME)
- **Slow internet at ALL Theory locations** — 990 Elm Street, 1037 corporate office. Impacts productivity org-wide.
- **Underpowered hardware:** No one has laptops powerful enough to run multiple dashboards simultaneously. Complex Sheets with thousands of rows cause laptops to slow or crash.
- **Monthly SQL file corruption.** Connor connected Amber's Claude to Snowflake specifically to prevent this.
- **Operations staff walk around with laptops** trying to view 50-column sheets on poor internet — data tools get abandoned.
- **Executive vision around data exists but cannot be executed** at the operational level due to hardware, internet, and training constraints.
- **Data tools are primarily used by leadership** (Amber, Connor, Liz) who communicate insights to their teams, rather than teams accessing data directly.

### Inventory Control & Dutchie Limitations
- **Biggest issue is inventory control:** warehouse not maintaining sell-out in Dutchie when moving items, causing surprise depletions.
- **Dutchie built for POS and ecomm, NOT manufacturing.** Manufacturing and cultivation modules never receive same focus as front-of-house.
- **Piloting Dutchie BOM/assemblies in Vermont** — has scaling issues (cannot scale batch sizes up, must use 1 unit or 1,000 units).
- BOM by category function not robust enough — Amber would prefer BOM by product line rather than broad categories like "flower."
- **Evaluated Fishbowl.** Adam recommended **Wherefour** as non-cannabis IMS integrating with Metronome and Dutchie.
- Open orders throw off reorder points; recipe changes may not reach data team for months — over/under buying.
- Dutchie conversion process (plus/minus conversions warehouse to rooms) throws off end-of-month usage tracking.

### Data Standardization & Planning
- **L60 definition varies across teams** — "last month + 9 days" vs actual last 60 days — inconsistent average daily sales and reporting.
- **Same meeting, different answers to same question** due to lack of centralized data definitions.
- Amber advocates for **52-week planning** (currently monthly) to enable faster demand planning and consistent parameters.
- **Vermont projections missing** from planning process entirely despite active operations.
- **No interim visibility** into company performance — leaders don't know how Theory tracks against revenue/bonus KPIs until annual review. Too late to pivot by the time issues are identified.
- **Rebranding project** (ongoing 1+ year) forcing small batch orders that increase COGS and hurt profit.

### AI & Technology Strategy
- Amber **actively experimenting with Claude** for automated month-over-month MRP analysis and problem identification.
- Connor connected Amber's Claude to Snowflake to prevent file corruption.
- Amber concerned: plugging AI into current ecosystem without addressing core infrastructure will "short circuit it."
- Adam's approach confirmed: work in both directions — continue AI integration while rebuilding core ecosystem.
- **Key data resources identified:** Amber, Connor, Eddie, Liz.

### Role Clarification (Resolved)
Amber's scope: **non-cannabis procurement + supply chain/demand planning oversight.** Per Avery (Apr 8), Avery handles all cannabis procurement. Per Amber's own framing: "all things procurement" = directorial oversight of both cannabis and non-cannabis, with day-to-day non-cannabis ownership. The apparent contradiction from the intro email is resolved — it's a scope difference between oversight (Amber) and execution (Avery).

### Follow-Up Artifact (4/9)
Amber forwarded Liz Gargone's "Useful Links! (6/27)" email cataloging ~35 procurement/production source-of-truth links. Full inventory logged under **Workflow Landscape — Supply Chain & Production Source-of-Truth Inventory**. Amber's framing: Component Tool + Accessory Tool = primary non-cannabis sources; Supply Chain Retail Sheets drive cannabis decisions. Stated #1 pain: data integrity from BoMs & Dutchie, and no single place to manage pipelines.

---

## Meeting 15: Marie Preshong + Kate Gray + Ashley Wright — Finance / Accounting
**Date:** Apr 10, 2026 | 9:30 – 10:15 AM ET
**Attendees:** Marie Preshong, Kate Gray, Ashley Wright, Adam Freed

### TL;DR
Group discovery session with Theory's finance/accounting team. Marie (SVP Controller, 8 years at Theory) brought Kate Gray (Director of Accounting, 3.5 years) and Ashley Wright (Senior Accountant, 2 years). Key system: **Intuit Enterprise Solutions (IES)** — elevated QuickBooks Online with consolidation across 8 state entities and 13-14 dispensary locations, but significant limitations on dimensions, budget-to-actual, and cost center functionality. **Top 3 priorities:** (1) IES functionality enhancement, (2) AP requisition-to-payment workflow consolidation, (3) elevating partner departments to accounting's automation level. Critical historical context: Theory spent a **full year researching ERP (Sage Intacct, Acumatica) ~2 years ago** but killed it on price and organizational buy-in. Buy-in is stronger now. Marie posed the defining question: **"Why invest in a major ERP if AI capabilities may eliminate the need within 6-8 months?"**

### Team Structure
- **Marie Preshong:** SVP Accounting, Corporate Controller, VP of Payroll. **8 years** at Theory. Team of 4 senior accountants, 1 director, 1 staff accountant.
- **Kate Gray:** Director of Accounting. **3.5 years** at Theory. Background in public accounting (audit and tax). Oversees 8 state entities and 13-14 dispensary locations.
- **Ashley Wright:** Senior Accountant. **2 years** at Theory. Previously at Air Wellness. Built a PDF renamer using **make.com + Air Parser** — shows automation aptitude.

### Current Technology Stack (Finance-Specific)
- **Intuit Enterprise Solutions (IES):** Elevated QuickBooks Online with consolidation. Significant limitations on dimensions, budget-to-actual reporting, department/location cost center functionality.
- **Fathom:** Reporting layer partnered with QBO, but treats Theory with same limitations as IES.
- **Excel Sync:** Extension pulling data between Excel and QBO/IES, struggles with dimension handling.
- **Mineral Tree:** ACH payments and approvals (approvers don't live in QBO/IES).
- **MainSTEM → IES sync:** Planned but not yet implemented.
- **Apex → SQL Server:** Separate data flow for wholesale B2B, requires manual monthly audits against Dutchie.
- **Monday.com:** Used for some project/task management, inconsistent adoption.
- **Claude AI:** Recently introduced for data analysis and report generation.

### Google Sheets Ecosystem (Finance)
- **15+ highly impactful live sheets** shared with other departments: contracts, insurance policies, licensing, rent, utilities, landlord contact info, taxes.
- Sheets maintained as visibility tool for partners AND control mechanism for accounting — significant redundancy with IES data.
- Cash tracking updated daily during high-volume periods (420 prep), weekly normally.
- Freight trackers for non-cannabis state-to-state product movement.
- Manual updates required for every lease renewal, insurance policy change, contract modification.
- Team spends significant time pulling data and manipulating format for presentations/system uploads.

### Key Pain Points
- **AP requisition-to-payment lifecycle = #1 priority.** Ideal: requisition → approved → PO created → shared with vendor → delivered → invoiced → coded → paid as single transaction. Currently fragmented across multiple systems with extensive manual touchpoints.
- **Each state has own AP inbox handling 1,700 emails monthly.**
- **No interim performance visibility** — leaders don't know tracking against revenue/bonus KPIs until annual review (confirms Amber's identical finding).
- **L60 definition variance** — different teams calculate metrics differently (confirms Amber's finding).

### ERP History (Critical Context)
- Theory spent a **full year researching ERP solutions** (~2 years ago): Sage Intacct, Acumatica.
- **Killed by price + organizational buy-in.** Team responded by maximizing IES capabilities, pushing partner tools to limits.
- Marie acknowledged current approach is "band-aiding rather than solving root issues."
- **ERP buy-in is STRONGER now** than 2 years ago due to department elevation efforts and increased data-sharing maturity across procurement, production, compliance.

### The Defining Question
Marie: **"Why invest in a major ERP if AI capabilities may eliminate the need within 6-8 months?"**
Adam: on the fence — even lead engineers at AI-driven cannabis companies don't fully agree with their CEOs on ERP replacement feasibility.
- Software landscape changing rapidly (new Claude models); long-term platform decisions are difficult.
- Need decision waypoints rather than binary ERP-or-not framing.

### Department Positioning
- Marie: "No old school mentality" — team pushed every tool to maximum potential.
- Accounting and finance positioned at **top of organizational funnel alongside IT** as universal touchpoints.
- Department serves as **"glue function"** connecting disparate systems across org.
- Kate wants **reporting packages as easy as a button click** — time should be spent speaking to results and fixing problems, not creating reports.
- Ashley will compile list of core Google Sheets (sheet name, primary purpose, duration of use, supporting departments) — **follow-up artifact pending.**

---

## Meeting 17: Connor Hansen — Follow-Up
**Date:** Apr 10, 2026 | 12:15 – 1:00 PM ET
**Attendees:** Connor Hansen, Adam Freed

### TL;DR
Closing-sequence follow-up with Connor. Confirmed and reinforced the infrastructure constraints Amber surfaced (slow internet, hardware, monthly SQL corruption). Elaborated on Connor's Google Sheets technical debt (Clasp + Apps Script with sandbox/prod environments, year-long undetected supply chain error). Clarified the pressure dynamic: Eddie is pushing AI integration rapidly while Connor lacks bandwidth to even check the existing sheets for errors. Strong philosophical alignment on "fix the ecosystem AND integrate AI in parallel." Connor's career preference is IT over production. Connor emailed the supply chain sheet name list post-call as the artifact for Liz follow-up.

### Key Findings

**Theory Positioning (confirms Amber)**
- Top 5% sophistication for cannabis data strategy; ahead of 80-99% of competitors with Snowflake environment + Claude MCP.
- Bottlenecked by hardware, internet speed, and training gaps — exact same framing as Amber, independently confirmed.
- Data consumers are very sophisticated but the software tech stack (outside Snowflake/Claude) is unsophisticated.

**Google Sheets Technical Debt (deeper than first round)**
- Connor inherited some sheets, built others under time pressure with a "quick and dirty" approach.
- **Eddie expects Connor to spend hours daily checking sheets for errors; Connor has no bandwidth** to do it.
- The supply chain data error that went undetected for a year (also surfaced by Avery) — Connor confirmed it required full reallocation when corrected.
- Formula errors in Google Sheets go undetected; teams must manually verify against Dutchie.
- **NEW tooling datapoint:** Connor uses **Clasp** for Google Apps Script with **sandbox/production environment separation** for code deployment. Real SDLC discipline buried inside the spreadsheet world — should be highlighted in any "current state of in-house tech maturity" framing.

**Infrastructure Crisis Confirmed (reinforces Theme 13)**
- Sheets with thousands of rows cause crashes and formula errors.
- SQL files corrupt monthly.
- On-site internet at 990 Elm Street and 1037 corporate is extremely slow.
- "Processing speed is the biggest bottleneck."

**Connor as Single Point of Failure**
- Cross-departmental sheet ecosystem (production, finance, retail, supply chain) means if Connor leaves, dashboard infrastructure has no backup.
- Same succession risk pattern as Liz and Dan, but Connor's surface area is the largest.

**Connor's Career Direction (NEW)**
- Marketing degree by training; self-taught in data/tech over 3 years at Theory.
- **Would prefer an IT role over a production role.** Enjoys helping people be more efficient but is spread too thin.
- Current work is "80% solutions but creates noise"; ideal would be unwinding Google Sheets and rebuilding in a more dynamic environment.
- Connor's framing: needs to shift from **"fingers in holes of the ship"** to **"building a neighborhood."**

**AI Implementation Pressure**
- Eddie is pushing rapid AI integration after months of slower development — "feels chaotic to Connor."
- Adam's framing landed: bidirectional approach (continue AI integration AND rebuild core ecosystem) rather than plugging AI into existing chaos.
- Recommended near-term win: **Claude Code in VS Code with Playwright MCP could audit Google Sheets formulas and identify errors automatically** — addresses Eddie's "check the sheets daily" expectation without burning Connor's time.

**Ticketing & Internal Comms (reinforces Theme 6 + Judge)**
- No communication SOPs or ticketing systems for internal requests across HR, finance, IT, or data.
- Most internal communication via standard email — creates noise and lacks structure.
- Connor sees ticketing as the way to add prescription, enable analytics on frequent flyers, and create SOPs around internal comms. Independent confirmation of Judge's same pitch.

**Shadow IT Signal (NEW)**
- **Finance is using make.com without IT approval** — concrete evidence of the no-centralized-IT theme manifesting as ungoverned tooling adoption.
- Pairs with Ashley Wright's make.com + Air Parser PDF renamer mention from the finance meeting (Apr 10 AM). Same vendor, two independent surfacings within the same day — finance has clearly adopted make.com as a de facto automation platform without governance.

### Quotes
- Connor: "fingers in holes of the ship" → needs to become "building a neighborhood."
- Adam framing Connor accepted: AI on top of broken systems will "short circuit it."

### Adam's Background (shared during the call, captured for context)
- Started at NETA in 2015 as budtender → inventory coordinator → learned Google Sheets from Eddie's code.
- Differs from Eddie's approach by focusing on data quality and spelling accuracy from day one.
- Advocates "who and how" over "what" — ERP implementation should focus on people and processes before technology.
- Emphasizes radical candor: care personally, challenge directly.

### Follow-Up Artifact (Post-Meeting Email)
Connor sent the supply chain sheet name inventory by email after the call — this is the artifact for the Liz follow-up:
- Supply Chain 2.0 MA
- Supply Chain 2.0 ME
- Supply Chain 2.0 VT
- Supply Chain 2.0 OH - Sherwood
- Supply Chain 2.0 OH - Columbus
- Supply Chain 2.0 NJ

These match the **Supply Chain Retail Sheets** row in Amber's "Useful Links!" inventory and the per-state demand planning workflow Avery walked through. Confirms Connor as the owner of this layer, with Avery as primary downstream consumer (Monday demand planning) and Sean as the allocation-side consumer.

### Next Steps Discussion
- Connor will send the supply chain sheet names (✅ done — see above).
- Adam continuing Theory discovery calls through 4/20 with a plan for May work by end of month.

---

## Meeting 16: Elizabeth Murphy — Follow-Up
**Date:** Apr 13, 2026 | 4:00 – 4:45 PM ET
**Attendees:** Liz Murphy, Adam Freed

### TL;DR
Closing-sequence follow-up with Liz, walking end-to-end through Theory's production, procurement, and supply chain data ecosystem across Google Sheets, Monday.com, and Excel. The headline decision: alignment on a **dual approach** — connect and streamline the existing data sources while introducing Claude — rather than pursuing a full ERP implementation. Liz will prepare a refreshed "Useful Links" inventory for Adam's AI agent context (delivered same-day via email as a PDF with ~50+ Sheets/Monday links). Option A/B/C tech-stack scenarios and centralized IT/data become the spine of the Eddie final on ~4/15.

### Production Dashboards & Scheduling
- **Cultivation schedules** track strain timing and table allocation across Massachusetts and Maine facilities
- **Production Summary** rolls up departmental targets vs. actuals across Vapes & Concentrates, Flower & Preroll, Edibles & Beverages, and Infusions
- **Production dashboards** live in Google Sheets with Summary / Sales / Pipeline tabs per category; the flower dashboard explicitly includes a strain-pipeline view (drawing → awaiting testing → programmed in retail → passed in vault) so the team can anticipate overstock before new batches land
- **Scheduling** primarily lives in **Monday.com** boards tracking batch schedules, lab sample status, label status, and vault transfer dates. **Exception: flower processing** stays in Google Sheets because of the bracket system below
- **Flower bracket system (2021, Liz-built, Google Sheets):** e.g., `TWX-1` = 0–2599g, 30%+ THC, 69% to eighths. Auto-populates requested quantities by grade and sales velocity. **Too intricate to migrate to Monday** despite repeated platform improvements — the workflow reality, not just a preference. This is the most complex single piece of logic in Liz's ecosystem.

### Procurement & Supply Chain Tools (as Liz described them)
- **Product Development** maintains the master **BOM** database feeding internal costs and MRPs
- **Allocations & Menu Health** sheets (shared with Sean) drive what to allocate where based on days-on-hand goals and SKU-variety targets
- **Amber's procurement tools** tie directly into BOMs + production dashboards to calculate needs from targets, sales, and forecasted trends
- **Supply Chain sheets are built per-store and track ALL cannabis procurement needs** — not just Theory-produced products. This is an important distinction from how Connor described Supply Chain 2.0 (which focuses on Theory SKUs); Liz's layer sits above and includes 3PI purchases from Avery
- **Accessories dashboard** maintains minimum inventory levels, daily sales tracking, and reorder points
- **Incoming order tracking** for cannabis (MA + ME) and accessories runs through Monday.com boards; the team is connected to Mainstem data feed and Apex

### Pain Points & Opportunity Areas
- **Too many reference points** creating fragmented sources of truth: Google Sheets, Monday.com, Excel power pivot, BDSA, Snowflake/Claude, and Dutchie canned reports
- **Retail ops cross-references Google Sheets against Dutchie reports** to validate accuracy — direct demonstration of the no-single-source-of-truth pattern
- **Liz's #1 priority:** connect and streamline data sources to reduce manual data pulls and format manipulation for presentations or system uploads
- **Theory characterization (Liz's words):** top **1–5% sophisticated data consumer** in cannabis with a **very unsophisticated tech stack** and no centralized IT; every department has its own tech person working in a siloed ecosystem. Independently matches Amber's "top 5%" and Connor's "top 5%" framing — three independent surfacings of the same diagnosis.

### AI Project Philosophy & Approach (Liz's view)
- Adam's bidirectional framing (deploy Claude via Snowflake **while** reworking underlying ecosystem and processes) landed as the operating approach
- **Training Claude to replicate manual workarounds** (e.g., Excel dimension mapping) creates token costs without solving root problems; the goal is **eliminating sheets and processes, not automating them**
- Liz stressed **education on AI capabilities as critical** to prevent teams from deviating from standard processes — AI without shared vocabulary fragments workflows faster than it consolidates them
- **Connor's "chaotic" characterization of the Claude rollout was explicitly validated:** helpful but adding noise without a prescriptive communication structure around when/how to use it
- Liz's hope: Claude could replace many sheets at enterprise level — "how to get there" remains the open collaborative question

### Software & ERP Conversation
- Theory evaluated **Sage Intacct** and **Acumatica** ~2 years ago but didn't proceed due to cost + organizational buy-in — independently confirms Marie's ERP history finding
- "Homegrown ERP" pattern across cannabis: best-of-breed tools + Google Sheets/Excel filling the gaps
- **Wherefour** raised as a potential software option worth evaluating that could replace multiple tools (reinforces Adam's recommendation to Amber)
- Open question: whether to lean fully into **Dutchie for BOMs and assembly flows** vs. a separate platform — pairs with Amber's VT Dutchie BOM/assemblies pilot scaling issues
- Decision: **full ERP implementation is unlikely**; the team will focus on defining **Option A / Option B / Option C tech-stack scenarios** so in-flight work aligns with the eventual landing spot rather than creating rework

### Decisions Made
1. **Dual approach** (streamline existing data sources + introduce Claude) rather than full ERP
2. **Team education + process standardization** are critical success factors before scaling AI adoption
3. **Focus on centralizing IT/data infrastructure** and defining the tech-stack landscape (Options A/B/C) **before** rolling out AI tooling at scale

### Project Priorities & Next Steps
- **Knowing the destination is critical** (Adam): decisions on where to land (ERP for finance/procurement, AI-driven infrastructure, or hybrid) must be made at project waypoints to avoid rework
- **Liz preparing list of core Google Sheets** with sheet name, primary purpose, duration of use, and supporting departments for Adam's AI-agent context (✅ delivered same-day via email as a PDF — see below)
- **Adam meeting with Eddie Wednesday (~4/15 AM)** to discuss high-level threads: centralized IT/data needs, tech-stack landscape decisions, and balancing "move fast" Claude adoption with structured process/communication approach

### Follow-Up Artifact — "Useful Links as of 4.9.26" PDF (attached to Meeting Stub)
Liz attached a PDF inventory with hyperlinks to the current Google Sheets and Monday.com boards. The hyperlink targets are Theory-internal (Adam has access; this doc only captures the categorized index below).

**Dutchie Login:** BackOffice

**Production:** Production Summary for MA and ME
- **MA Production Dashboards:** Vapes & Concentrates · Edibles & Beverages · Infusions · Flower & Preroll
- **ME Production Dashboards:** Flower & Preroll · Edibles & Beverages · Vapes & Concentrates · Infusion
- **MA Production Schedules:** MA Infusions · MA Concentrate Packaging · MA Vape Packaging · MA Preroll · MA Flower · MA Harvest
- **ME Production Schedules:** ME Infusions · ME Canning · ME Extraction Packaging (Vapes + Concentrates) · ME Processing Schedule (Flower & Preroll)
- **Product Development:** BOM · Recipes

**Supply Chain:** Deal Planning · MA Allocations · ME Allocations · MA Retail Price Guide · ME Retail Price Guide · VT Retail Price Guide
- **Menu Health (per-state):** Maine · Massachusetts · Vermont · New Jersey · Ohio
- **Procurement:** Component Tool · PO Template · **MRP Template/Tracker** · **MRP Order Tracking — Procurement** · **Accessories & Warehouse Transfers** · **MA Non-Cannabis Order Tracking** · **ME Non-Cannabis Order Tracking** · **VT Non-Cannabis Order Tracking** · ERG Guidance · **Stock Transfer SOP** · **Bulk CSV Upload for Non-Cannabis Goods** · **Accessory Sale Guide** · **Accessory Dashboard**
- **Supply Chain Retail Sheets (per-state):** MA · ME · VT · NJ · OH-Sherwood · OH-Columbus · 2025 Accessories Dashboard
- **Inbound Transportation Schedules:** MA · ME · VT · OH · NJ

**What's new vs. Amber's 4/9 "Useful Links" inventory:**
- 3 Retail Price Guides (MA/ME/VT) — new category
- Menu Health broken out per-state (NJ and OH now explicitly included — 5 states total)
- Procurement section expanded from 3 items (Component Tool, PO Template, ERG Guidance) to 13 items, adding the full MRP + non-cannabis order tracking + accessories management stack
- 2025 Accessories Dashboard added to Supply Chain Retail Sheets
- Note: Liz's PDF does NOT include the VT Monday.com production dashboard (being rebuilt) or the Monday boards for MA/ME production schedules from Amber's inventory — this is a curated forward-looking cut, not an all-systems snapshot

---

## Meeting 18: Eddie Benjamin — Discovery Wrap-Up
**Date:** Apr 15, 2026 | 8:30 – 9:15 AM ET
**Attendees:** Eddie Benjamin, Adam Freed

### TL;DR
Discovery phase officially closed. All 15 stakeholder interviews + 2 closing follow-ups complete. **Eddie's ask: a formal overview document by Monday 4/20** — broad categories, questions for future conversations, and a rough framework — **explicitly NOT final solutions or exact system recommendations.** Eddie self-acknowledged that the current Claude rollout is "layering on another tool" without proper foundation — strong client agreement on Adam's diagnosis. Eddie also posted the **Director of Business Intelligence and Automation** role on Indeed and LinkedIn — captured here as a Theory org-direction signal (the role itself is tracked as a separate Task).

### Decisions Made
- **Deliverable scope (4/20):** Broad overview document — categories, questions, rough framework. **Not** final solutions, exact system picks, or vendor recommendations. Detailed conversations on specific data systems and software live in future phases.
- **Core recommendation reaffirmed:** Rebuild data + tech foundation **simultaneously** with AI implementation, rather than layering AI onto the current ecosystem

### Action Items (Adam → Adam)
1. Deliver the Theory Wellness project overview document by Monday 4/20

### Key Discussion Points

**Eddie's self-assessment of current Claude rollout (notable client validation)**
- Claude is being deployed as a tool for everyone to use **without a centralized framework**
- Sean (Compliance) being introduced to Claude for Python scripts; Marie (Finance) proposing centralized accounting inbox routed to Claude
- Eddie acknowledged: this is "layering on another tool" rather than building a true company operating system
- Recognizes the need for "**file cabinet organized, shelves labeled, resources organized**" before AI can serve as the company OS — direct echo of Adam's "fix data foundation in parallel" framing
- This is the strongest possible client signal that the foundation-first recommendation will land at the executive level

**Major themes Eddie validated**
- No centralized IT
- Disparate data sets and Google Sheets
- Accuracy concerns
- Every department has its own "tech person"
- Communication systems (email lacks organizational SOPs) is a top opportunity area common to all companies
- Plugging Claude into Theory's current state without addressing upstream issues will create "another tool" that adds noise rather than clarity

**Systems & infrastructure**
- **Centralized ticketing system** for HR, IT, data requests, and business support — Eddie endorsed; provides root cause analysis, recurring-issue tracking, and prescriptive structure for AI to assist (independent endorsement after Judge + Connor + Liz raised it)
- **Theory's current state:** top 1–5% of cannabis industry for data sophistication, unsophisticated tech stack — Eddie's framing matches Amber, Connor, Liz exactly (now four-way agreement at executive level)
- **Wherefore** mentioned again as candidate to replace Google Sheets and close MRP/manufacturing gaps
- **MCP access preferred over staging all third-party data in Snowflake** where possible — important architectural principle for the deliverable

**Adam's methodology framing (recapped for Eddie)**
- Focus on "how we work" (systems, processes, organization) not just "what we do" (tools, outputs)
- Build from the **middle of the ecosystem outward** — foundation while plugging in AI, not just layering
- Balance Eddie's "quick wins" philosophy with Adam's "get the scale right" approach
- Reference: ERP horror story — client wasted millions implementing the wrong system without proper foundation

**Eddie's three framing questions for the deliverable**
1. Will Adam put this into a document?
2. What's the timing?
3. What questions does Adam need answered?

→ Answers: Yes; Monday 4/20; the deliverable itself will be structured as categories + questions for future conversations.

### Director of BI & Automation Role (org-direction signal only)
Eddie posted the role on Indeed and LinkedIn during the call; chose this title over one with explicit "AI" — signals positioning the role as broader than just an AI lead. Captured here purely as a **Theory org-direction signal** (the role is the org's first concrete move toward the centralized data/IT function flagged across discovery). Adam's review/response on the JD is tracked as a **separate Task**, not as part of this engagement.

---

## Workflow Landscape

> This section compiles what's been captured across 15 first-round interviews + Connor's 4/10 follow-up + Liz's 4/13 follow-up. Liz's end-to-end walkthrough validated and extended the earlier pictures. Remaining open questions feed into the Eddie final (~4/15).

### Supply Chain & Production Source-of-Truth Inventory (Amber, 4/9/26 — initial snapshot)

Source: Liz Gargone "Useful Links! (6/27/25)" fwd by Amber. Categorized view:

| Category | System | States | # Links | Notes |
|---|---|---|---|---|
| Dutchie BackOffice | Dutchie | All | 1 | Login entry point |
| Production Dashboards | Google Sheets | MA, ME | 8 | 4 categories × 2 states (Vapes/Conc, Edibles/Bev, Infusions, Flower/Preroll) |
| Production Dashboards | Monday.com | VT | 1 | Being rebuilt |
| MA Production Schedules | Mixed (Monday ×3, Sheets ×2) | MA | 5 | Infusions/Extraction/Preroll on Monday; Flower/Harvest on Sheets |
| ME Production Schedules | Mixed (Sheets ×3, Monday ×2) | ME | 5 | Vapes/Concentrates on Monday; rest on Sheets. Bill Greer owns flower/preroll detail |
| Product Development | Google Sheets | All | 3 | BOM, Recipes, Timeline |
| Deal Planning | Google Sheets | All | 1 | — |
| Procurement | Sheets + Doc | All | 3 | Component Tool (final BETA), PO Template, ERG Guidance |
| Supply Chain Retail Sheets | Google Sheets | MA, ME, VT, NJ, OH-Sherwood, OH-Columbus (+OH Menu Goals) | 7 | Primary cannabis purchase-decision layer. **Confirmed by Connor 4/10** as the Supply Chain 2.0 sheet family he owns |
| Inbound Transportation | Monday.com | MA, ME, VT, OH, NJ | 5 | 100% Monday.com |
| WIP Supply Chain | Google Sheets | — | 2 | Allocations & Menu Health, 2025 Accessories Dashboard |

**Observations:**
- Sheets vs. Monday.com split is structural, not random: Transportation = 100% Monday; Production Dashboards = 100% Sheets; Schedules = mixed by category and state
- BOM link here = same sheet Connor flagged (Jake-managed, flat assembly, not in Dutchie API). Confirms BOM is the cross-functional chokepoint across Connor, Liz, Amber, Avery
- Component Tool in "final BETA" — built in-house, likely candidate for either expansion or ERP replacement
- OH = only state with a separate "Menu Goals" sheet — suggests ad-hoc tooling layered onto a market without stable process
- VT Production = Monday.com (being rebuilt) — inconsistency Liz flagged herself

### Software Systems (Current State)

| System | Function | Owner/Power User | Notes |
|--------|----------|------------------|-------|
| Dutchie | POS, Backoffice, Ecommerce, manufacturing conversions, retail menus | Greg, Sean, Kass, retail teams | Core POS in MA/ME. POS + Backoffice + Ecomm most used (Kass). Also reference for strain types, inventory |
| Dutchie BI | Reporting layer | Kass flagged | Some states have it, "have not found the benefit yet — reports take very long to load or do not load at all" (Kass) |
| Zebra Handheld (beta) | Audits, pre-order packing, inventory tasks | Kass (championing) | Working to get into beta with Dutchie — Kass used a similar device in a previous job |
| Dutchie Catalog Auto-Populate (beta) | Auto-populates vendor-provided images and descriptions | Avery / Compliance | Rolling out — reduces manual catalog work. Product catalog ownership currently Compliance but under discussion |
| BioTrack + iHeartJane | Compliance + menu (NH only) | Kass/Greg | **Managed services agreement.** iHeartJane menu is "lacking — not as robust as Dutchie ecomm"; BioTrack "doesn't offer good information for the online menu to pull from" |
| OARRS | Compliance system (OH only) | Kass/Greg | State-specific compliance layer |
| VCCB | Compliance system (VT only) | Kass/Greg | State-specific compliance layer |
| Metrc | Cultivation tracking, compliance, COAs | Compliance (Judge, Shaun, Kate) | MA regulatory backbone; API feeds SQL Server |
| Apex | Wholesale B2B (outgoing) | Elizabeth, Avery | Being replaced by Dutchie B2B in next couple years |
| Mainstem | Procurement POs | Elizabeth | Data NOT in SQL Server; Wherefore could replace |
| SQL Server | Data warehouse | Connor, Dan | API feeds from Dutchie/Metrc/Apex → master sheets. Files corrupt monthly per Connor + Amber |
| Snowflake | Analytics, MCP for Claude AI | Connor | Hit API connection issue recently; Claude integration in progress |
| Google Sheets | Lightweight ERP, dashboards, master data | Everyone | ~18 sheets created daily per Matt G; backbone of operations. Kass: "HEAVY reliance on Google products" |
| Clasp (Apps Script CLI) | Code deployment for Google Apps Script with sandbox/prod environments | Connor Hansen | NEW (Connor 4/10) — actual SDLC discipline buried inside the spreadsheet ecosystem. Underappreciated maturity datapoint |
| Google Docs | Meeting + site visit notes | Kass, retail team | Manual but helpful; site visit notes hard to maintain |
| Google Forms | Strain descriptions, inventory issues, closing in retail, store audits (WIP) | Kass | Submission forms feeding back to sheets |
| Gemini (Google AI) | In-call note-taking | Kass / retail | Already in active use for meeting notes — existing AI adoption datapoint |
| Monday.com | HR hiring boards only | Alex Paulk | HR: 15 boards → consolidating to 1. Retail tried it for project planning + gantt chart views and REVERTED to Google Sheets — "a lot of manual labor" (Kass) |
| QuickBooks | Accounting/finance | Marie (TBD) | Apex commonly used for QB integration |
| Evolve (UKG) | HRIS — payroll, benefits, T&A, LMS | Alex Paulk | New; 80-90% complete, targeting June 1 go-live. Also used for training content (LMS) |
| LMS (via Evolve) | Training delivery | Retail Trainer / HR / Compliance | Joint ownership across 3 functions |
| BDSA | Competitive intelligence, market data | Matt Gerety, Avery, Kass | Onboarded ~4-6 months ago. Learning curve is a barrier. API not integrated. Kass wishlist: Dutchie integration, top-seller gap analysis, competitor pricing alerts |
| CannMenus | Potential BDSA alternative (under evaluation) | Kass | MCP integration, map widget for store locator, automated menu scraping/alerts |
| Scribe | SOP documentation w/ step-by-step screenshots | Kass (pushing for enterprise) | Used for training + best practices |
| Interface / Vector | Security/alarm provider | Kass/Greg | Part of fragmented security stack |
| SoLink | AI-camera variance investigation | Kass (pilot in MN) | Integrated with Dutchie. Org-wide rollout pending evaluation |
| ME Fire & Security | Maine-specific security vendor | Kass/Greg | Why Maine stores aren't on the same provider as others |
| Hik-connect | Camera/security system | Kass/Greg | Part of fragmented security stack |
| Comcast | Internet/network | Greg | Consolidated down from 12 providers across 13 stores |
| Weedmaps | 90-day new-store SEO (exceptions exist) | Kass/Greg | Minimal ongoing value; **Kittery exception** — online ordering still live |
| Leafly | 90-day new-store SEO | Kass/Greg | Minimal ongoing operational value (similar to Weedmaps) |
| Google Chat | Per-store communication | Retail (Kass/Greg) | Combined with email groups for store-level comms |
| Adobe InDesign | Label creation (data merge) | Dan Killian | Custom barcode generator via Adobe Extend Scripts |
| Kiosk Pro | In-store kiosk ordering | Greg Phillips | Just launched in Chicopee; rollout pending |
| VS Code + GitHub | Python script repos | Shaun Seward | All automation code version-controlled |
| Intuit Enterprise Solutions (IES) | Elevated QBO with consolidation across 8 state entities | Marie / Kate Gray | Significant limitations on dimensions, budget-to-actual, cost centers. Fathom + Excel Sync as workarounds |
| Fathom | Financial reporting layer | Marie / Kate | Partners with QBO but inherits IES limitations |
| Excel Sync | QBO/IES → Excel data bridge | Marie / Kate | Struggles with dimension handling |
| Mineral Tree | ACH payments and approvals | Marie / Kate | Approvers don't live in QBO/IES — separate workflow |
| Wherefour | Non-cannabis IMS (recommended by Adam) | Amber (evaluating) | Integrates with Metronome + Dutchie. Alternative to Fishbowl (evaluated and passed) |
| make.com + Air Parser | PDF renaming automation | Ashley Wright | Built by Ashley at Theory — shows automation aptitude in finance. Connor 4/10 confirms make.com is being used in Finance **without IT approval** — shadow-IT signal |

### Key Google Sheets (Identified)

| Sheet | Purpose | Owner | Fed By | Feeds |
|-------|---------|-------|--------|-------|
| Production Dashboard | Pipeline visibility — supply chain, production, compliance use daily | Connor/Elizabeth | SQL Server / Snowflake | Sean (allocation planning), Elizabeth (production tracking) |
| Supply Chain 2.0 Sheets (MA, ME, VT, OH-Sherwood, OH-Columbus, NJ) | SKU-level sales rates, days on hand, sold-out tracking per state — core demand planning tool. **Connor 4/10 confirmed names + ownership** | Connor Hansen | Dutchie data via SQL Server | Avery (Monday demand planning across 5 states), Sean (allocation) |
| Menu Health (multi-state) | Weekly snapshot across 15+ locations, grading inventory against goals (e.g., 10+ half ounces = meeting goal) | Sean / Avery | Dutchie, Supply Chain 2.0 | Avery (purchasing decisions), Sean (allocation gaps) |
| Testing Database | All testing data entry + compliance QC | Dan/Shaun | Scripts (auto from labs) or manual entry | Label CSVs, Dutchie menu uploads |
| MA Allocations & Menu Health | Batch-level allocation + variety goals for MA stores | Sean McGonagle | Dutchie data, manual hand-keying | Allocation summary script → inventory teams |
| ME Allocations & Menu Health | Same as MA, identical structure | Sean McGonagle | Same | Same |
| BOM Sheets | Bill of materials | Elizabeth | Manual / Apex | NOT in SQL Server — static sheets |
| FG Tracking Logs | Finished goods tracking | Elizabeth/Dan | Manual | NOT in SQL Server — static sheets |
| Costing Sheets | Recipe-level costing (labor, testing, transport) | Elizabeth | Multiple manual sources | Nearly complete; adding overhead |
| Licensing Spreadsheets | Employee licensing across MA/ME/OH/VT | Alex Paulk | Manual | Payroll (renewal reimbursements) |
| Label CSVs | Formatted data for InDesign label merge | Dan Killian | Testing DB + Dutchie data | Adobe InDesign → printed labels |
| Directory Sheet | Vendor Dropbox/shared drive links for product assets | Compliance | Manual | Wholesale item creation |
| Approved Order Sheet | Wholesale order data from procurement | Procurement manager | Monday.com | Compliance processing |
| Connor's Ad-Hoc Dashboards | ~3/day built on request | Connor Hansen | SQL Server, various | Requesting departments |
| Dan's Ad-Hoc Dashboards | ~3/day built on request | Dan Killian | Various; personal drive | Requesting departments |
| Retail Hub | Living calendar + shared resource space | Greg Phillips | Manual | District managers, store teams |

### Automations & Scripts (Identified)

**Shaun Seward — Compliance (Python/OCR Pipeline)**
- Python scripts log into Metrc via browser automation (mimics browser + cookies, avoids API fees)
- Scrapes COAs → extracts cannabinoid/terpene data → populates Google Sheets testing templates → CSV upload to Dutchie menus
- Lab-agnostic design — dynamically adapts to different COA formats
- Maine fully automated (internal + wholesale); expanding to NJ and other markets
- AI models tested for COA extraction but rejected — compliance requires 100% accuracy
- Internal labs (Cat Labs in ME, Keisha in MA) easier; wholesale/3PI labs are the brittle pain point

**Dan Killian — Labeling & Testing (Scripts)**
- Scripts automatically check email for new COAs, upload testing data to Google Sheets testing DB
- Separate scripts prepare label CSVs for InDesign data merge
- Custom barcode generator built in Adobe Extend Scripts (third-party InDesign plugin couldn't be automated)
- Monday.com → Google Sheets data pull scripts
- Evolved from manual tools to autonomous systems running without human intervention
- Tracker ecosystem (for Liz) adds to workload

**Sean McGonagle — Allocations (Script)**
- Allocation summary generator: script creates date-stamped file with tabs per store location
- Emailed to all inventory teams for execution
- No pre-allocation capability for pipeline products — only finished goods

**Connor Hansen — Data Infrastructure**
- API feeds from Dutchie/Metrc/Apex → SQL Server → Google Sheets master data
- Snowflake + MCP for Claude AI agent (hit API connection issue)
- Builds and maintains most data-connected dashboards across the organization
- Helps build robust Sheet solutions when Greg or others identify gaps
- **Uses Clasp for Google Apps Script with sandbox/production environment separation** (NEW from 4/10 follow-up) — proper code-deployment hygiene inside the Sheets ecosystem

**Alex Paulk — HR (Monday.com Automations)**
- Monday.com automations for hiring board workflows (email triggers on status changes)
- Google Form + Approvals extension as ATS workaround (with recruiter Marcy)
- Automations turn off unpredictably in Monday.com

### Data Flow Summary (Simplified)

```
Labs (COAs) ──→ [Shaun's Python/OCR] ──→ Testing DB (GSheet) ──→ Label CSVs ──→ InDesign (Dan)
                                            ↓
Dutchie ────────────────────── CSV menu upload
   ↑
Dutchie + Metrc + Apex ──→ [API] ──→ SQL Server ──→ Google Sheets (master) ──→ Dashboards
                                         ↓
                                    Snowflake ──→ Claude AI (MCP) [connection issue]

Production Dashboard (GSheet) ←── SQL/Snowflake
   ↓
Sean's Allocations (GSheet) ──→ [Script] ──→ Allocation Summary ──→ Email to inventory teams
   ↓
Menu Health (GSheet) ←─ Avery (3PI purchasing via BDSA)

Monday.com (HR hiring) ←─ [Alex automations] ──→ Email triggers
Mainstem (procurement POs) ←── NOT connected to SQL Server
BOM + FG Logs (GSheet) ←── NOT connected to SQL Server
Evolve/UKG (HRIS) ←── Standalone (new, not yet integrated)
BDSA (market data) ←── Standalone (not integrated)
QuickBooks ←── Apex integration only
```

### Remaining Gaps (For Eddie Final + Post-Discovery Work)

Resolved or covered in Liz's 4/13 walkthrough:
- ✓ Seed-to-sale full process flow — walked end-to-end; supplementary PDF inventory delivered
- ✓ Supply Chain 2.0 sheet structure — per-state inventory (Supply Chain Retail Sheets row) confirmed; Liz's layer sits above Connor's Supply Chain 2.0 and includes all cannabis procurement (3PI + Theory), not just Theory SKUs
- ✓ Cross-market differences — dashboards/schedules are categorically consistent; VT production is the outlier (Monday rebuild); Menu Health now explicitly covers all 5 states
- ✓ Demand planning vision — dual approach (streamline + Claude) confirmed, no full ERP; decision waypoints rather than binary

Still open for Eddie final or post-discovery execution:
- **Production → Allocation handoff:** trigger/signal mechanism between finished goods status and allocation sheets — covered conceptually, not explicitly mapped
- **Wholesale outgoing flow:** Apex → retail/wholesale allocation detail
- **Costing integration:** how costing sheets connect to QB/IES financial reporting
- **Co-manufacturing in Apex:** how this works today and what should move to Wherefour
- **EOD reporting flow:** who consumes, what decisions it drives
- **Promotion workflow:** Sean recommends → marketing decides → Dutchie execution path (Kass as de facto discount/pricing owner per Eddie 4/6)
- **Vault capacity data:** still no system of record; Avery's 5–7 day dwell time + Sean's capacity pushback remain unresolved
- **Option A / B / C tech-stack scenarios:** to be defined at the Eddie final as the project spine

---

## Emerging Themes (Across All Interviews)

### 1. Current State — Technology Landscape
- **Core stack:** Dutchie → Metric → SQL Server → Google Sheets → Dashboards
- **Satellite systems:** Apex (wholesale), Mainstem (procurement), Monday.com (project mgmt), Snowflake (AI/analytics)
- **State-specific compliance layers (from Kass):** BioTrack + iHeartJane in NH, OARRS in OH, VCCB in VT — each state adds regulatory tech complexity on top of core stack
- **Key gap:** Apex and Mainstem data NOT in SQL Server; BOM and finished goods logs are static Google Sheets
- **Fragmentation:** Monday.com vs. Google Sheets split creates operational complexity
- **Dutchie usage:** Retail POS + manufacturing conversions (not bombs/assemblies). Metric for cultivation only.
- **Production Dashboard** is a de facto software platform — supply chain, production, compliance all live in it daily

### 2. Data Governance & Organization
- Dashboards in personal drives (Connor, Elizabeth, AND Dan) — succession risk across 3+ people
- No centralized file structure, no directory, no onboarding for sheets (Mark: "you find out by accident")
- Ad-hoc report requests overwhelming multiple people (~3 dashboards/day for Connor, Elizabeth, AND Dan)
- Sheets described as "plugs off of plugs" — powerful but undiscoverable and unscalable
- Matt Gerety: ~18 different sheets created daily across org, leading to inconsistent data
- Each department has its own systems and conventions
- HRIS churn (5 changes in 7 years) creates parallel data integrity challenge in HR

### 3. AI & Automation Readiness
- Strong internal capability (Shaun's Python pipeline, Dan's label automation, Connor's Snowflake/MCP, Connor's Clasp/Apps Script SDLC)
- Leadership support from Eddie and above; Mark wants AI for strategic business value (not email summaries)
- Recent Gemini → Claude migration; Shaun interested in Claude Code + agent swarming
- API connection issue blocking current AI agent progress
- Need upstream data quality and structure before AI can be fully effective
- **AI on broken systems amplifies noise** — consensus across Mark, Elizabeth, Judge, Connor, Dan, Matt G, Amber
- **AI for COA extraction tested and rejected by Shaun** — never 100% accurate, compliance requires precision. OCR/PDF scraping is brittle but unavoidable.
- Alex Paulk (HR) cautiously skeptical — concerns about training overhead, PII security in shared Claude environment
- Matt Gerety: Theory operates revenue targets based on "feelings and gut" — AI needs data foundations first
- **Connor 4/10:** Eddie pushing AI rapidly creates pressure; Connor finds it chaotic. Bidirectional approach (AI integration AND ecosystem rebuild) is the only sustainable path. Near-term win: **Claude Code + Playwright MCP to audit Sheets formulas**.
- **Liz 4/13 (operating principle):** **Training Claude to replicate manual workarounds** (e.g., Excel dimension mapping) creates token cost without solving root problems. The goal is **eliminating sheets and processes, not automating them.** Liz independently validated Connor's "chaotic" characterization of the current Claude rollout — helpful but adding noise without a prescriptive communication structure around when/how to use it.
- **Three-way agreement on "how" before "what":** Mark (CCO), Liz (VP Supply Chain), Connor, Amber, and Adam all independently land on: fix the data/process foundation in parallel with AI deployment, don't bolt AI onto broken systems. This is the strongest cross-stakeholder consensus in the engagement.

### 4. Scaling Challenge
- 3 new wholesale-only markets with no new headcount
- Compliance dept will absorb 100% of item flow in new markets
- Manual data entry must be eliminated before expansion
- Master data setup for new markets = opportunity to build right
- MA regulatory constraint: max 3 containers per Metric tag — individual tagging burden

### 5. Software Consolidation Opportunity
- **Wherefore ERP** could replace Mainstem + BOM sheet + some Apex functions
- **Wherefour IMS (recommended by Adam to Amber):** Non-cannabis IMS integrating with Metronome + Dutchie. Fishbowl was evaluated and passed.
- **Dutchie B2B** will likely replace Apex in next couple years (confirmed by Elizabeth and Adam)
- **Dutchie BOM/Assemblies pilot in VT (from Amber):** Has scaling issues — cannot scale batch sizes, BOM by category not robust enough (needs BOM by product line)
- **Evolve (UKG)** — new HRIS targeting June 1 go-live. Most robust option in cannabis. Replaces 5th HRIS in 7 years.
- **BDSA** — new competitive intelligence platform for retail. API could feed centralized database.
- Monday.com → Google consolidation desired by compliance (Alex Paulk heavily invested in Monday for HR though)
- Dutchie expanding capabilities (global catalog, BOM, AI) — need to track what they'll solve natively
- **Platform migration risk:** don't build automations on systems being replaced (need long-term platform decisions first)
- **ERP History (from Marie):** Theory spent a FULL YEAR researching ERP (Sage Intacct, Acumatica) ~2 years ago. Killed by price + organizational buy-in. Team responded by maximizing IES + partner tools. Marie: current approach is "band-aiding rather than solving root issues." **Buy-in is STRONGER now** than 2 years ago.
- **Marie's defining question:** "Why invest in a major ERP if AI capabilities may eliminate the need within 6-8 months?" Adam: on the fence. Need decision waypoints, not binary ERP-or-not framing.
- **Liz's link inventory (via Amber 4/9)** quantifies the Sheets ↔ Monday.com split: Inbound Transportation is 100% Monday across all 5 states, Production Dashboards are 100% Sheets, and Production Schedules are mixed by category/state. This isn't preference drift — it's two parallel systems each owning distinct operational domains with no bridge. Consolidation decision is bigger than compliance's Monday→Google preference; it's a supply-chain-wide architecture call.
- **Decision from Liz 4/13:** Full ERP implementation is **unlikely**. The operating approach is a **dual path** — streamline existing data sources + introduce Claude — framed as **Option A / Option B / Option C tech-stack scenarios** with explicit waypoints. This is the project spine going into the Eddie final.
- **Flower bracket system (Liz 4/13):** The 2021-built TWX-style bracket logic (e.g., `TWX-1` = 0–2599g, 30%+ THC, 69% to eighths) is **too intricate to migrate to Monday.com**. It's the most complex single piece of logic in the Sheets ecosystem and a real operational constraint on "just move it to Monday." Any consolidation plan has to answer "what replaces the bracket system" before it can claim to consolidate.
- **Sage Intacct + Acumatica eval (Liz 4/13):** Independently confirms Marie's ERP-history account. Three-way corroboration (Marie, Amber, Liz) on the same prior evaluation.

### 6. "How We Work" (Shadow Project)
- Email governance needed org-wide (no company rules, 200+ emails/day for Judge)
- SOP automation potential (new markets + regulatory changes)
- Ticketing system for support functions (compliance, HR, facilities, IT) — pitched independently by Judge AND Connor
- Process documentation as AI learning layer
- Mark: "progress without vision is treadmill activity — motion without movement"
- Alex Paulk: "measure twice, cut once" alignment — cautious but engaged
- **Google Workspace clutter (Kass):** Orphaned email groups, unknown document owners, no centralized directory — major retail pain point
- **Scribe adoption (Kass):** Used for SOP documentation but adoption is limited; opportunity for enterprise rollout
- **No internal comms SOPs (Connor 4/10):** Most internal requests happen via standard email, creating noise. Connor sees ticketing as the way to add prescription, enable analytics on frequent flyers, and create SOPs around internal comms.
- **AI-specific SOPs needed (Liz 4/13):** Education on AI capabilities is a critical success factor — without shared vocabulary, AI fragments workflows faster than it consolidates them. Teams will otherwise deviate from standard processes once they have a general-purpose tool. Pair this with ticketing/internal comms work.
- **Eddie endorsed centralized ticketing (4/15):** For HR, IT, data requests, and business support. Provides root cause analysis, recurring-issue tracking, and prescriptive structure for AI to assist. **Four independent endorsements** (Judge, Connor, Liz, Eddie) — strongest cross-stakeholder agreement of the engagement. Treat as a foundational deliverable recommendation, not just an option.
- **Eddie's self-acknowledgment (4/15):** Current Claude rollout is "layering on another tool" without proper foundation. Recognizes the need for "file cabinet organized, shelves labeled, resources organized" before AI can serve as the company OS. **This is the strongest possible client signal that the foundation-first recommendation will land at the executive level.**

### 7. Production vs. Sales Misalignment (from Elizabeth + Mark + Matt G + Avery)
- Theory historically production-driven (Eddie produces, then they sell) — needs to flip to sales-driven
- No formal demand planning system — manual monthly targets based on inventory → DOH × sales
- Allocation based on historical sales — blind spots for lost wholesale opportunities
- Vision: real-time pipeline visibility to trigger promotions before new batches arrive
- Current consumer segmentation is only 4 segments — Mark called this "obscene"
- Matt G: no store-level P&Ls. Revenue targets based on "feelings and gut." Pricing was uniform across ALL locations for 8 years.
- **Avery IS Theory's demand planner by default.** The former demand planner role was left unfilled and Avery absorbed those responsibilities on top of cannabis buying across 5 states. Monday mornings are spent manually forecasting state-by-state instead of executing on auto-generated recommendations.
- **Every PO requires CEO approval via email summary** (Brandon Pollack) — creates a bottleneck even when data supports the decision.

### 8. Fragmented ERP & Data Trustworthiness (from Elizabeth + Avery + Marie + Connor)
- Theory's "ERP" is assembled from Google Sheets + disconnected software
- Demand planning gap is the most critical piece — Elizabeth called it "the really broken piece"
- Costing nearly complete (labor, testing, transport per recipe — working on adding overhead)
- Duplicate entry across Apex and Mainstem due to broken integrations
- **Data trustworthiness crisis (from Avery, confirmed by Connor 4/10):** A Supply Chain 2.0 sheet data error **went undetected for a full year.** When discovered and corrected, it required full reallocation across stores. Connor independently confirmed the same incident. Also: sales rate calculations sometimes incorrectly count zero-sales days for brand-new products, throwing off forecasts.
- **Eddie's expectation gap:** Eddie expects Connor to spend hours daily checking sheets for errors; Connor has zero bandwidth to do it. Errors compound silently.
- **L60 definition variance (from Amber + Marie):** Different teams calculate "last 60 days" differently — "last month + 9 days" vs actual last 60 days — same meeting, different answers to same question.
- **IES limitations (from Marie):** Intuit Enterprise Solutions has significant gaps on dimensions, budget-to-actual, department/location cost centers. Fathom and Excel Sync are workarounds, not solutions.
- **AP requisition-to-payment lifecycle (Marie's #1 priority):** Ideal flow is requisition → approved → PO → vendor → delivered → invoiced → coded → paid. Currently fragmented across multiple systems. Each state has own AP inbox handling **1,700 emails monthly.**
- **No interim performance visibility (from Amber + Marie):** Leaders don't know how Theory tracks against revenue/bonus KPIs until annual review. Too late to pivot.
- **MainSTEM → IES sync planned but not yet implemented.** Apex → SQL Server requires manual monthly audits against Dutchie.
- This is the clearest case made so far for the "fix the data before adding AI" framing — people are making Monday buying decisions against numbers nobody has audited.

### 9. No Centralized IT Function (confirmed across all interviews)
- Tech-savvy individuals embedded in departments: Shaun (compliance), Alex (HR), Dan (labeling/production), Connor (data/reporting), Greg + Kass (retail field IT)
- Each operates in their own ecosystem with their own tools and conventions
- **Greg + Kass partnership:** Together they form Theory's de facto retail field IT team — confirmed by Kass directly
- Matt G's vision: centralized data intelligence/BI function as new IT-led business unit
- IT waste examples: Bridgewater store $900/mo WiFi with 6 unused phone lines; 12 internet providers across 13 stores before Comcast consolidation
- **Security fragmentation (CRITICAL, from Kass):** Security systems vary by state AND by store. Maine stores are not even on the same provider. No centralized security vendor.
- **SoLink pilot (Kass):** AI-camera variance investigation integrated with Dutchie, being evaluated in MN for org-wide rollout
- AI governance, skill ownership, onboarding/offboarding flows not yet solved — becomes HR + compliance problem
- **Connor career signal (4/10):** Connor would prefer an IT role over a production role — direct evidence the org has people who *want* to staff a centralized IT function, but no role exists for them to grow into
- **Shadow IT confirmed (Connor 4/10):** Finance is using **make.com without IT approval**. Pairs with Ashley Wright's make.com + Air Parser PDF renamer. Two independent 4/10 surfacings of the same vendor in the same department — finance has adopted make.com as a de facto automation platform with no governance
- **Director of BI & Automation role posted (Eddie 4/15):** On Indeed and LinkedIn. Eddie chose this title over one with explicit "AI" — signals positioning the role as broader than just an AI lead. **The role is the org's first concrete move toward the centralized data/IT function** Matt Gerety, Connor, and Kass all flagged as missing.

### 10. Master Data Harmonization (from Shaun S. + Dan)
- Same analyte spelled differently across labs, capitalization inconsistencies, percent vs mg/g units
- Wholesale testing is the larger pain point — various third-party labs with different formats
- Vendor naming in Metrc doesn't match Theory's naming conventions for PMs
- Lab-agnostic dynamic scripts needed — Shaun designed for this but OCR is inherently brittle
- Barcode structure (batch ID + product suffix) driven by MA regs, differs per product category
- **MDM ownership split:** Production handles master data for internal products; Compliance owns 3PI/wholesale master data. This split must be accounted for in any centralized MDM strategy.
- Foundation must be solved before AI can operate effectively on testing/compliance data

### 11. Allocation & Capacity Planning Gap (from Sean M. + Greg + Avery)
- Batch-level allocations are atypical for industry — adds significant complexity vs. traditional retail
- No pre-allocation capability for products in production pipeline — only finished goods allocatable
- No forecasting layer connecting production schedule to allocation planning
- Cannabis operates as push model (produce then allocate) vs. pull model (demand drives production) — Sean came from clothing retail pull model
- Must check 5 different places to make one allocation decision — consolidation is the biggest opportunity
- **Vault capacity friction:** Store managers push back on allocation reports saying they can't fit more inventory. No formal area constraints in breadth/depth planning. No good data on box sizes vs. physical space.
- **Vault dwell time crisis (from Avery):** Products purchased and delivered often sit in the vault **5-7 days before hitting the menu** due to staffing/space constraints. Avery can buy correctly but retail can't execute on time — the capacity gap is retail-side, not procurement-side.
- **No shelf space calculation in allocation model (confirmed by Avery):** Breadth and depth tracked, but physical area constraints are not. Same gap Sean described from the production side.
- Sean serves as "system glue" between production and retail — provides preliminary recommendations, lets departments make final calls
- **Avery = de facto demand planner** filling a role that was eliminated, using Connor's Supply Chain 2.0 + BDSA + manual cross-referencing.

### 12. Retail Data & Reporting Gaps (from Greg, Matt G, Kass)
- Dutchie ecomm admin vs. back office reporting is the biggest retail disconnect
- Kiosk data limited (Mac ID only); as Theory moves to kiosk model, this gap grows
- **Dutchie BI only in some states — not all.** Limited adoption. Could replace some Google Sheets if rolled out consistently (Kass)
- Discount reporting is painful: 7-item meal deal × 7 stores = 49 line items requiring manual math
- EOD reports from 13 store managers are 50-80% complete — brittle communication system
- Greg uses Sheets as "scrap paper" (solve and move on) vs. Connor who builds persistent solutions
- BDSA exists but is siloed — not connected to Dutchie operational data or allocation workflows
- **Monday.com FAILED retail adoption (Kass):** Team tried it for task management, reverted to Google Sheets due to learning curve
- **CannMenus under evaluation (Kass):** Potential BDSA alternative with MCP integration, map widget, automated menu scraping
- **Weedmaps / Leafly:** Only used for 90-day new-store SEO — minimal ongoing value

### 13. Infrastructure & Hardware Constraints (from Amber + Connor 4/10)
- **Slow internet at ALL Theory locations** (990 Elm, 1037 corporate) — so bad it impacts productivity org-wide and causes data tools to be abandoned. **Independently confirmed by Connor 4/10.**
- **Underpowered hardware:** No one has laptops powerful enough to run multiple dashboards. Complex Sheets with thousands of rows cause crashes. **Confirmed by Connor 4/10 — "processing speed is the biggest bottleneck."**
- **Monthly SQL file corruption.** Connor connected Amber's Claude to Snowflake specifically to prevent this. Connor 4/10 confirmed this happens roughly monthly.
- **Operations staff walk around with laptops** trying to view 50-column sheets on poor internet — data tools never adopted at operational level.
- **Executive vision around data exists but cannot be executed** at the operational level due to hardware, internet, and training constraints.
- **Data tools primarily used by leadership** (Amber, Connor, Liz) who communicate insights to their teams. Teams don't access data directly.
- **Production managers focus on immediate needs** ("I need to make 10,000 pre-rolls") when data tools are too slow to load.
- **Lack of standardized training** on basic Google Sheets skills, system usage (CSV vs Excel, how to use MainSTEM).
- This theme is **foundational** — no amount of software consolidation, AI integration, or data governance will matter if the physical infrastructure can't support it. Must be addressed in parallel. Two independent surfacings (Amber 4/9, Connor 4/10) within 24 hours raise its priority.

---

## Outstanding Items

### All First-Round Interviews Complete ✅
- 15 of 15 first-round interviews complete (including Amber and Marie group session).

### Closing Sequence Status
- ✅ **Connor Hansen (follow-up) — Apr 10.** Notes incorporated into Meeting 17 section + Themes 8/9/13 + Software Systems table + Outstanding Items.
- ✅ **Elizabeth Murphy (follow-up) — Apr 13.** Full end-to-end walkthrough + updated "Useful Links" PDF delivered same-day. Notes incorporated into Meeting 16 section + Themes 3/5/6 + Remaining Gaps + Outstanding Items.
- ✅ **Eddie Benjamin (discovery wrap-up) — Apr 15.** Discovery phase officially closed. Deliverable scope set (broad overview, NOT exact solutions) due Monday 4/20. Notes incorporated into Meeting 18 section + Themes/Outstanding Items.

### Open Action Item (Adam, post-discovery)
1. **Deliver the Theory Wellness overview document by Monday 4/20** — categories, questions for future conversations, rough framework. Explicitly NOT final solutions or vendor picks.

### Follow-Up Artifacts Pending
- **Ashley Wright (Finance):** Will compile list of core Google Sheets with sheet name, primary purpose, duration of use, and supporting departments. Cross-reference against Google Sheets table when received.
- **Amber's "Useful Links" email:** Referenced during Apr 9 session — wire up email "Fwd: Useful Links! (6/27)" for additional context.
- **Kass's Systems Inventory:** ✅ Received and incorporated.
- **Connor's Supply Chain 2.0 sheet names:** ✅ Received and incorporated (4/10 post-call email).
- **Liz's updated "Useful Links as of 4.9.26" PDF:** ✅ Received 4/13 and incorporated as the `Meeting 16` Follow-Up Artifact subsection.

### Key Findings to Carry Into Eddie Final
- **Amber role clarification:** ✅ Resolved.
- **Dutchie BOM/assemblies pilot (VT):** Has scaling issues — needs product-line-level BOM, not just category. Pair with Wherefour eval.
- **Infrastructure crisis:** Internet + hardware + training gaps are foundational blockers. **Three independent surfacings** (Amber 4/9, Connor 4/10, Liz 4/13 implicit via "unsophisticated tech stack" framing) — raise this to top-tier priority. Must be addressed in parallel with software/AI work.
- **ERP question (resolved operationally):** Marie asked "Why invest in ERP if AI eliminates the need in 6-8 months?" — Liz's 4/13 answer is the operating posture: **no full ERP, dual approach with Option A/B/C waypoints.** This is the strategic spine for the Eddie final.
- **AP req-to-payment lifecycle:** Marie's #1 priority. Currently fragmented across multiple systems.
- **No interim KPI visibility** — confirmed by Amber, Marie, and echoed by Liz (manual data pulls + format manipulation is the daily tax).
- **Shadow IT in finance:** make.com being used without IT approval — captured 4/10 from both Ashley and Connor independently. Concrete evidence that the no-centralized-IT theme is producing ungoverned tooling adoption.
- **Connor as career-IT signal:** Connor wants an IT role over a production role. The org has people who would staff a centralized IT/data function if it existed.
- **Near-term automation win for Eddie:** Claude Code in VS Code with Playwright MCP could audit Google Sheets formulas and identify errors automatically — directly addresses Eddie's "check the sheets daily for errors" expectation without burning Connor's time.
- **Flower bracket system (NEW from Liz 4/13):** Any Sheets → Monday consolidation plan must explicitly answer "what replaces the bracket system" — otherwise consolidation stalls on a real operational constraint, not just preference.
- **AI education + process standardization (NEW from Liz 4/13):** Critical success factors. Without shared vocabulary around when/how to use Claude, AI fragments workflows. Pair with ticketing/internal comms work.

---

*Document compiled: March 28, 2026*
*Last updated: April 17, 2026 (Eddie 4/15 discovery wrap-up integrated: Meeting 18 section added; deliverable scope set — broad overview, not exact solutions, due Monday 4/20; Eddie self-acknowledged current Claude rollout is "layering on another tool" — strongest client validation of foundation-first recommendation; centralized ticketing now has four independent endorsements (Judge, Connor, Liz, Eddie); Themes 6/9 enriched; Outstanding Items reduced to the single post-discovery action item. Director of BI & Automation role posting captured as a Theory org-direction signal only — Adam's JD review and the unrelated hemp-beverage favor are tracked as separate Tasks outside this engagement. Previous updates: 2026-04-14 — Liz 4/13 follow-up + Useful Links PDF inventory; 2026-04-11 — Connor 4/10 follow-up + Clasp + make.com shadow-IT.)*
*Discovery phase officially closed. 15 of 15 first-round interviews + 2 closing follow-ups + Eddie wrap-up = 18 of 18 sessions complete. Open: 4/20 overview deliverable.*
