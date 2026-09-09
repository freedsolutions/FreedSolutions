<!-- Generated from "freed-solutions/skills/bi-change/templates/client/__tenant__/bi-estate/ITEM-CREATION-SOP.md". Edit the repo skill source and rerun ops/notion-workspace/scripts/sync-claude-skill-wrappers.ps1; do not edit this Claude copy directly. -->

# <TENANT> Dutchie — Item Creation SOP

**How to create a catalog item in Dutchie Backoffice, correctly, the first time.**
Field-by-field intake guidance driven by the signed attribute rules — what Dutchie's form
enforces, what it cannot enforce (and QC does), and what to leave alone.

**Last synced: <date>** (scaffolded from the `bi-change` client template.) · Source of truth:
`clients/<client>/<tenant>/bi-estate/ITEM-CREATION-SOP.md` (this file) · Shareable copies:
`renders/ITEM-CREATION-SOP.docx` / `.pdf`.

---

## 1 · How this document works

**Audience:** anyone creating items in Backoffice.

**Where the rules live:** this SOP is the PROCESS layer. The rules themselves live in
`DATA-DICTIONARY.md` and their history in `DECISIONS.md`; the tracked intake-field state lives
in `fields-config/`. Rules change there first and this document follows — the same ripple the
runbook (BI-SOP §2) governs. Cite a rule by number here; never restate one.

**Its paired WI** is `ITEM-CREATION-WI.md`: this file holds the full field detail and the why,
the WI is the card the team works from.

## 2 · Before you create anything

<What must be true before an item is created: the category exists, the brand is linked, the
attributes the rules require are known. One bullet each, each citing its rule.>

## 3 · The intake form, field by field

One sub-section per group of fields, in FORM ORDER, so the reader can work down the screen.
Each field: what to enter, which rule governs it, and what happens if it is wrong.

### 3.1 · Identity (the form forces these)
### 3.2 · Cannabis classification and compliance
### 3.3 · Commercial
### 3.4 · Merchandising
### 3.5 · Leave everything else alone

<The deliberate hides. A field hidden on purpose is a ruling, so name the rule that hid it.>

## 4 · Rules the form will not enforce

<The short memorisable list. Each is a rule the QC surface catches after the fact, which is
exactly why it has to be remembered at intake. Cite the rule and the QC surface that catches it.>

## 5 · After you create

<The verification pass: what to re-open, which QC tile or runner to check, and how soon.>

## 6 · Naming conventions

<The item-name grammar for this tenant, or a pointer to the registry and guide that carry it.
Names are canon like any other rule: the Dictionary rules, this section instructs.>

## Appendix A · Field-state quick reference

| Field | State | Rule | Note |
|---|---|---|---|

<One row per field on the Product Master form: Required / Optional / Hidden, verified against
the live config on a stated date. This table is the drift baseline for the intake-config lane.>

## Appendix B · Keeping this document true

- This file is the master; DOCX/PDF are renders. Never edit a render.
- Any intake-config or naming change updates the affected section **in the same pass** and bumps
  the header stamp (ripple runbook Step 5).
- `bi_impact_scan.js --stale` reports when this document's stamp is older than an estate harvest.
- Change log:
  - <date> — scaffolded from the `bi-change` client template.
