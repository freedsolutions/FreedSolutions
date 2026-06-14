# Theory Wellness — Phase 1 Decision Canvas (Mermaid Source)
# Last updated: April 18, 2026
# Usage: Paste this into a Claude session and say "regenerate" or "update X node" to iterate via Figma:generate_diagram

```mermaid
flowchart LR
    subgraph Legend["Option A/B/C Scenario Legend"]
        direction TB
        LA["A: Streamline — Keep Sheets, layer Claude, sunset worst offenders"]
        LB["B: Targeted Replacement (recommended) — Bounded platform swaps at known weak points"]
        LC["C: Transformative — Reopen ERP, consolidate Sheets aggressively"]
    end

    subgraph Org["Organization / Roles"]
        BIDir["Director of BI & Automation (POSTED 4/15)"]
        Ticketing["Centralized Ticketing (PROPOSED — Phase 0)"]
    end

    subgraph External["External Sources"]
        Labs["Labs (COAs)"]
        BDSA["BDSA Market Data"]
        Vendors["3PI Vendors"]
        CannMenus["CannMenus (BDSA alt, MCP-ready)"]
    end

    subgraph Compliance["Compliance — Shaun Seward"]
        ShaunBot["Python/OCR Pipeline"]
        TestDB["Testing DB (GSheet)"]
    end

    subgraph Labeling["Labeling — Dan Killian"]
        LabelCSV["Label CSVs (GSheet)"]
        InDesign["Adobe InDesign + Barcode Gen"]
    end

    subgraph Core["Core Systems"]
        Dutchie["Dutchie (POS / Ecomm / Mfg)"]
        DutchieBI["Dutchie BI (limited states)"]
        DutchieBOM["Dutchie BOM/Assemblies (VT pilot — scaling issues)"]
        Metrc["Metrc (Cultivation)"]
        Apex["Apex (Wholesale B2B) — B: transition to Dutchie B2B"]
        Mainstem["Mainstem (Procurement POs) — B: replace w/ Wherefour"]
    end

    subgraph StateCompliance["State-Specific Compliance"]
        BioTrack["BioTrack + iHeartJane (NH)"]
        OARRS["OARRS (OH)"]
        VCCB["VCCB (VT)"]
    end

    subgraph Data["Data Layer — Connor Hansen"]
        SQL["SQL Server (corrupts monthly)"]
        Snowflake["Snowflake — Eddie: MCP-first over staging"]
        Claude["Claude AI (MCP)"]
        Clasp["Clasp (Apps Script CLI — sandbox/prod separation)"]
    end

    subgraph SheetsERP["Google Sheets ERP — A: retain / B: retain as ops layer / C: consolidate"]
        ProdDash["Production Dashboard"]
        SC2["Supply Chain 2.0 Sheets"]
        MenuHealth["Menu Health (15+ locations)"]
        BOM["BOM Sheets — B: replace w/ Wherefour"]
        FG["FG Tracking Logs — B: move to IMS"]
        Costing["Costing Sheets"]
        FlowerBracket["Flower Bracket System (TWX logic — migration constraint)"]
    end

    subgraph Procurement["Procurement — Avery + Amber"]
        Wherefour["Wherefour IMS (replacement candidate — Mainstem + BOM)"]
        SeanAlloc["Allocations (GSheet)"]
        AllocScript["Allocation Summary Script"]
        InvTeams["Inventory Teams"]
        MondayLogistics["Monday (Logistics)"]
    end

    subgraph Finance["Finance — Marie + Kate + Ashley"]
        IES["Intuit Enterprise (IES/QBO)"]
        Fathom["Fathom (Reporting)"]
        ExcelSync["Excel Sync"]
        MineralTree["Mineral Tree (ACH)"]
        MakeCom["make.com + Air Parser (SHADOW IT — govern/absorb/replace)"]
        FinSheets["15+ Finance Sheets"]
    end

    subgraph HR["HR — Alex Paulk"]
        Monday["Monday.com (Hiring)"]
        Evolve["Evolve / UKG (HRIS — June 1 go-live)"]
        Licensing["Licensing Sheets"]
    end

    subgraph RetailOps["Retail Ops — Greg + Kass"]
        RetailHub["Retail Hub (GSheet)"]
        KioskPro["Kiosk Pro"]
        SoLink["SoLink (MN pilot)"]
        Scribe["Scribe (SOPs)"]
        PricingGuides["Pricing Guides (GSheet)"]
        GoogleChat["Google Chat (per-store)"]
    end

    Labs -->|"COAs"| ShaunBot
    Metrc -->|"Browser Automation"| ShaunBot
    ShaunBot --> TestDB
    TestDB -->|"CSV Upload"| Dutchie
    TestDB --> LabelCSV
    LabelCSV --> InDesign

    Dutchie -->|"API"| SQL
    Metrc -->|"API"| SQL
    Apex -->|"API"| SQL
    Apex -->|"Manual Monthly Audit"| IES

    SQL --> Snowflake
    Snowflake -->|"MCP-first"| Claude
    SQL --> ProdDash
    SQL --> SC2
    Clasp -->|"Apps Script SDLC"| SheetsERP

    Mainstem -.->|"NOT connected"| SQL
    BOM -.->|"NOT connected"| SQL
    FG -.->|"NOT connected"| SQL
    Mainstem -.->|"Sync planned, not impl"| IES

    Wherefour -.->|"Replacement candidate"| Mainstem
    Wherefour -.->|"Replacement candidate"| BOM

    ProdDash --> SeanAlloc
    SC2 -->|"Monday forecasting"| Procurement
    Dutchie -->|"Reference"| SeanAlloc
    BDSA -->|"Market validation"| Procurement
    CannMenus -.->|"MCP integration"| Claude
    SeanAlloc --> AllocScript
    AllocScript -->|"Email"| InvTeams
    MenuHealth -->|"Gaps"| Vendors

    IES --> Fathom
    IES --> ExcelSync
    MineralTree -.->|"Approvers separate"| IES

    Dutchie --> DutchieBI
    Dutchie --> DutchieBOM
    Dutchie --> SoLink
    BioTrack -.->|"NH only"| Dutchie
    OARRS -.->|"OH only"| Dutchie
    VCCB -.->|"VT only"| Dutchie

    Monday -->|"Automations"| Licensing
    BIDir -.->|"Owns"| Data
    BIDir -.->|"Owns"| Ticketing
    Ticketing -.->|"HR, IT, Data, Biz Support"| Org

    style Legend fill:#f5f5f5,stroke:#333,stroke-width:2px
    style LA fill:#e8f5e9,stroke:#2d7a4f
    style LB fill:#e3f2fd,stroke:#1565c0
    style LC fill:#fff3e0,stroke:#e65100
    style Org fill:#fafafa,stroke:#333,stroke-width:2px
    style BIDir fill:#c8e6c9,stroke:#2e7d32,stroke-width:2px
    style Ticketing fill:#fff9c4,stroke:#f9a825,stroke-dasharray:5 5
    style External fill:#f9f9f9,stroke:#999
    style Compliance fill:#e8f5e9,stroke:#2d7a4f
    style Labeling fill:#fff3e0,stroke:#e65100
    style Core fill:#e3f2fd,stroke:#1565c0
    style StateCompliance fill:#fce4ec,stroke:#c62828
    style Data fill:#f3e5f5,stroke:#7b1fa2
    style SheetsERP fill:#fff8e1,stroke:#f9a825
    style Procurement fill:#e0f2f1,stroke:#00695c
    style Finance fill:#ede7f6,stroke:#4527a0
    style HR fill:#e0f7fa,stroke:#00838f
    style RetailOps fill:#fbe9e7,stroke:#bf360c
    style Wherefour fill:#b2dfdb,stroke:#00695c,stroke-width:2px,stroke-dasharray:5 5
    style MakeCom fill:#ffcdd2,stroke:#c62828,stroke-width:2px
    style Clasp fill:#e1bee7,stroke:#7b1fa2,stroke-width:2px
    style FlowerBracket fill:#ffecb3,stroke:#ff8f00,stroke-width:2px
    style CannMenus fill:#b2dfdb,stroke:#00695c,stroke-dasharray:5 5
```
