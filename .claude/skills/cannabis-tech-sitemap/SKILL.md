---
name: cannabis-tech-sitemap
description: Generate a Phase 1 tech-stack decision canvas (Mermaid source + Figma rendering) for a vertically integrated cannabis MSO from stakeholder interview notes. Use when Adam has run a discovery engagement and needs the sitemap artifact for the deliverable.
---

<!-- Generated from "freed-solutions/skills/cannabis-tech-sitemap/SKILL.md". Edit the repo skill source and rerun ops/notion-workspace/scripts/sync-claude-skill-wrappers.ps1; do not edit this Claude copy directly. -->

# Cannabis Tech-Stack Sitemap

Extract the tech-stack landscape from discovery interview notes and produce a two-file sitemap artifact: a Mermaid source file that is the living source of truth, plus a Figma-rendered PDF produced via a Claude session with `Figma:generate_diagram`. Overlay standard scenario framing (Option A / B / C) and cannabis-specific flags (MCP eligibility, shadow IT, replacement candidates).

## When to Use

- Adam is wrapping a cannabis MSO discovery engagement and the deliverable needs a tech-stack sitemap.
- Stakeholder interview notes exist (usually at `clients/<client>/discovery/<client>-interview-notes.md`).
- The deliverable wants a Phase 1 decision canvas, not just a current-state inventory.

## Inputs

- **Interview notes path** (required): the running stakeholder interview notes MD file.
- **Client slug** (required): kebab-case client name (e.g., `acme-co`).
- **Output path for Mermaid source** (optional, default = `clients/<slug>/discovery/<slug>-tech-stack-mermaid.md`).
- **Output path for rendered PDF** (optional, default = OneDrive client folder).
- **Scenario framing** (optional): if the client's engagement already established scenario options (A / B / C or similar), use those names verbatim. Default: Streamline / Targeted Replacement / Transformative.

If the interview notes are missing or the engagement has not yet reached a Phase 1 framework, use `HARDENED_GATE` before generating.

## Standard Cannabis MSO Department Groupings

Most vertically integrated cannabis MSOs organize into these layers. Use them as the top-level subgraphs in the Mermaid source. Omit layers that aren't relevant for a given client; don't invent layers that the interviews didn't surface.

| Layer | Typical scope | Common system archetypes |
|---|---|---|
| **Compliance** | COAs, testing DB, state regulatory feeds | Python / OCR pipelines, Metrc scraping, testing Google Sheets |
| **Production & Labeling** | Barcode / label generation, QC, packaging | InDesign + Bartender, Google Apps Script, custom barcode gen |
| **Core POS & Inventory** | POS, ecommerce, backoffice, mfg conversions | Dutchie, Treez, Flowhub, LeafLogix (legacy), BioTrack (NH) |
| **State-Specific Compliance** | Per-state regulatory layers | OARRS (OH), VCCB (VT), BioTrack + iHeartJane (NH), Metrc (MA/ME/CA/NJ) |
| **Data Layer** | Data warehouse, MCP layer, AI agents | SQL Server, Snowflake, Claude (MCP), Clasp (Apps Script SDLC) |
| **Supply Chain & Procurement** | Demand planning, allocations, purchasing, logistics | Wherefour IMS, Apex, Mainstem, Monday.com (logistics), Google Sheets (allocations + menu health) |
| **Finance & Accounting** | GL, AP/AR, reporting, state entity consolidation | IES / QBO, Fathom, Excel Sync, Mineral Tree (ACH), state AP inboxes |
| **HR & Payroll** | HRIS, ATS, licensing, training | UKG Evolve, Paylocity, Monday (hiring), LMS |
| **Retail Operations** | Store-level tools, kiosks, pricing, field IT | Kiosk Pro, SoLink, Scribe, pricing guides, per-store Google Chat |
| **Market Data & Competitive Intelligence** | Competitor / menu tracking | BDSA, CannMenus (MCP-ready), Headset, Weedmaps / Leafly (SEO only) |
| **Organization / Roles** | Role nodes that own or propose systems | BI & Automation Director, de facto IT (often Retail Ops), Compliance lead |

## Standard Cannabis MSO System Archetypes

When the interview notes mention these generic categories, default to the following specific system mentions (unless the notes say otherwise):

- **POS:** Dutchie (most common across MSOs today), Treez, Flowhub
- **Seed-to-sale:** Metrc (most markets), BioTrack (NH), VCCB (VT), OARRS (OH)
- **ERP candidates:** Wherefour (non-cannabis, cannabis-friendly), Sage Intacct, Acumatica, NetSuite
- **IMS (lightweight ERP):** Wherefour (integrates with Metronome + Dutchie), Fishbowl (often evaluated and passed)
- **Wholesale B2B:** Apex (legacy, often being replaced), LeafLink, Dutchie B2B (maturing)
- **HRIS:** UKG Evolve (newer cannabis-friendly option), Paylocity, ADP, Zenefits
- **Market data:** BDSA (most common), Headset, CannMenus (emerging with MCP)
- **AI / automation layer:** Claude Code + MCP, OpenAI ChatGPT / Codex (earlier evolution), make.com + Zapier (often shadow IT in Finance)
- **Productivity backbone:** Google Workspace (almost universal), Microsoft 365 (less common in cannabis)

## Workflow

### 1. Extract systems from interview notes

Read the interview notes end-to-end. For each system mentioned, capture:
- System name
- Owner (person or department)
- Integrations mentioned (API, CSV, manual)
- Pain points flagged (corruption, missing data, no IT approval, etc.)
- Replacement candidates named in notes

Group by department. If a system appears in multiple department sections (common for Google Sheets), note it once in its primary home with cross-references.

### 2. Identify scenario framework

Check the interview notes for an explicit scenario framework in the closing meetings. Common pattern: a VP or Director articulates *Option A / Option B / Option C* in a follow-up meeting near the end of discovery (Liz Murphy did this at Theory 4/13). If no explicit framework exists, default to:

- **Option A — Streamline:** Keep current tools, layer AI / automation, sunset worst-offenders. No ERP, no major platform swaps.
- **Option B — Targeted Replacement:** Specific platform swaps at known weak points. Bounded scope. Usually the recommended default for cannabis MSOs given ERP track record.
- **Option C — Transformative:** Reopen ERP conversation. Consolidate aggressively. Build proper analytics platform.

Default recommendation for most cannabis MSO contexts: **Option B**. Honor any explicit client-team preference surfaced in the notes.

### 3. Apply standard overlays

Three overlay layers make the sitemap a decision canvas instead of documentation:

1. **Scenario treatment per node.** Color-badge each system node with A/B/C treatment (green/blue/orange). Tag nodes with specific handling: `Retain`, `Retain + add MCP`, `Replace (Wherefour)`, `Transition to Dutchie B2B`, `Consolidate`.

2. **SaaS replacement candidates.** Dashed arrows from replacement candidate to current system. Always include known cannabis-specific candidates (Wherefour → Mainstem + BOM, Dutchie B2B → Apex, CannMenus → BDSA).

3. **Cannabis-specific flags.**
   - **Shadow IT** (red/orange accent): anything used without IT approval. make.com + Air Parser in Finance is the most common pattern.
   - **MCP eligibility** / MCP-first preference: flag systems that offer MCP access (preferred) vs. those requiring Snowflake staging.
   - **Consolidation constraints**: callouts for logic too complex to migrate as-is (e.g., flower bracket systems built on top of Google Sheets — common in long-tenured cannabis operators).
   - **Data-in-SQL gaps**: dashed "NOT connected" lines for systems whose data doesn't reach the warehouse (common for BOM sheets, FG Tracking Logs, Mainstem).

### 4. Generate the Mermaid source

Write to `clients/<slug>/discovery/<slug>-tech-stack-mermaid.md`. Structure:

```markdown
# <Client> — Phase 1 Decision Canvas (Mermaid Source)
# Last updated: <date>
# Usage: Paste into a Claude session with Figma:generate_diagram access and say "regenerate" or "update X node" to iterate.

```mermaid
flowchart LR
    subgraph Legend["Option A/B/C Scenario Legend"]
        ...
    end

    subgraph Org["Organization / Roles"]
        ...
    end

    <Per-department subgraphs>

    <Connections>

    <Styles>
```
```

Follow the canonical reference under `clients/<slug>/discovery/<slug>-tech-stack-mermaid.md` (gitignored — lives in each local engagement folder) for:
- Subgraph naming and direction (`flowchart LR` for landscape; `TB` if the stack is simpler)
- Style color conventions (`#e8f5e9` green for Compliance, `#e3f2fd` blue for Core, etc.)
- Badge placement for scenarios (in node labels with colons)

### 5. Render to Figma

Use a Claude session (in the Claude.ai web UI or Claude Code with Figma MCP extensions) that has access to `Figma:generate_diagram`. Paste the Mermaid source or hand off the MD file path. Acceptance criteria:

- Single-page landscape export suitable for poster-size viewing or letter-page scaled thumbnail.
- Export as PDF to the client's OneDrive folder: `C:\Users\adamj\OneDrive\Documents\My Documents\Freed Solutions\<Client>\<Client> — Phase 1 Decision Canvas (30+ Systems, A_B_C Scenarios).pdf`.

### 6. Embed in the deliverable document

Convert the Figma PDF to PNG for inline embedding in the Markdown deliverable:

```bash
pdftoppm -r 50 -png "<Figma PDF>" "<output-prefix>"
```

50 DPI is usually enough for an inline thumbnail that scales to letter-page width without bloating the DOCX/PDF output. Higher DPI (100-150) if the canvas needs more detail at thumbnail size.

Embed in the deliverable MD:

```markdown
![<Client> Phase 1 Decision Canvas (30+ Systems, Option A/B/C Scenarios)](<client>-tech-stack-sitemap.png)

A full-resolution version is attached alongside this document as `<Client> — Phase 1 Decision Canvas ... .pdf`. The Mermaid source is versioned in the engagement repo and regenerates on demand.
```

### 7. Iterate via the Mermaid source

When the sitemap changes post-delivery, edit the Mermaid MD file, regenerate the Figma via another Claude session, re-convert to PNG, and re-render the deliverable. The Mermaid file is the single source of truth going forward — not the Figma board.

## Reference Implementation (generalized)

The first end-to-end exercise of this recipe lives locally under `clients/<slug>/discovery/<slug>-tech-stack-mermaid.md` (gitignored). When building a new sitemap, read the most recent prior engagement's Mermaid file + deliverable for a worked example. Notable moves from the canonical first run:

- ~10 department subgraphs (Legend, Org, External, Compliance, Labeling, Core, StateCompliance, Data, SheetsERP, Procurement, Finance, HR, RetailOps) — prune or combine to match the client's actual org
- ~30 nodes total
- Owner names embedded in subgraph titles (e.g., `Compliance — <Owner>`)
- Scenario treatment inline in node labels (e.g., `<System> — B: transition to <Replacement>`)
- Shadow IT flagged with a distinct red border
- Replacement candidates shown with dashed arrows from replacement to legacy
- Consolidation / constraint callouts with distinct colored borders

The full Mermaid source and rendered PDF are the reference artifacts this skill aims to reproduce for new clients.

## Guardrails

- **Do not invent systems.** Only include systems that appear in the interview notes or in the client's documented tech inventory.
- **Names over roles for ownership.** Use actual stakeholder names (e.g., "Shaun Seward") for owner attribution, not generic titles, when the notes provide them.
- **Respect confidentiality in overlays.** Shadow IT and organizational concentration-risk flags are legitimate overlays but should be discussed with the client before appearing in an externally-shared version.
- **Don't push to the client's Figma account.** Adam's own Figma account hosts the rendered boards. Client delivery is via exported PDF, not Figma link sharing, unless the client explicitly asks.
- **Mermaid source is the source of truth.** The Figma rendering is a view; the Mermaid file is the version-controlled artifact.

## Gate Protocol

| Operation | Gate | Notes |
|---|---|---|
| Extract systems from interview notes, write Mermaid source, render Figma, convert to PNG, embed in deliverable | `UNGATED` | Standard recipe, all sources are engagement-internal. |
| Deviate from standard department groupings or scenario framework (A / B / C) because the client's engagement surfaced a different structure | `UNGATED` with a one-line note explaining the deviation | Honor client-surfaced language. |
| Include systems not mentioned in the interview notes; include organizational-concentration-risk or shadow-IT flags in an externally-shared version without client awareness | `HARDENED_GATE` | Protect the client relationship and engagement confidentiality. |

## Known Limitations

- Figma rendering requires a separate Claude session with `Figma:generate_diagram` access. Claude Code in the terminal does not have that tool today; the Mermaid source is portable to any Mermaid-capable tool (Mermaid CLI, Notion, Obsidian, Mermaid Live Editor) if Figma isn't available.
- PDF exports from very wide Figma boards (Theory's was 92x60 inches) can be hard to read at letter-page scale. Consider splitting into multiple panels if the full board won't scale cleanly.
- Mermaid flowchart layout is deterministic per the Mermaid engine; large graphs sometimes produce awkward layouts. Iterate on subgraph grouping or flow direction (`LR` vs `TB`) to improve.
- Cannabis system archetypes shift over time. This skill's archetype list should be updated as new platforms emerge (e.g., if Dutchie B2B supersedes Apex more fully, reflect that in default recommendations).
