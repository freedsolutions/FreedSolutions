# <TENANT> BI Data Dictionary & Business Rules Register

The standing business rules for the <TENANT> Dutchie/Looker estate. This file is CANON:
a rule changes here first, then in the BI surface, then in the operator docs.

**Column contract** — `| # | Rule | Grain | Surface | Status | Since | Links | Record |`

- **Rule** — the standing rule only, present tense, ≤ 400 characters. No dates, quotes,
  counts, query ids, tile ids or narrative; a Product Line name escapes its pipes as `\|`.
- **Grain** — what one row of the rule is about: per product, per PL, per package.
- **Surface** — where it is enforced: tile ids, `export`, `api`, `config`. The impl cell.
- **Status** — `ACTIVE` · `RETIRED` · `DEFERRED` · `PROPOSED`. Never strike-through prose.
- **Since** — the date of the latest ruling. **Links** — `supersedes` / `superseded by` /
  `see Rnn`. **Record** — the kickoff file(s) carrying the evidence.

**Writing rules.** A rule cell is not a log. Every dated stamp, withdrawal, reinstatement,
count and "do not revisit" warning belongs in `DECISIONS.md` beside this file, or in the
kickoff it cites. Rule numbers are LABELS other documents cite: never renumber one, and
retire in place rather than reusing an id. Register order is the SOURCE order, not numeric.

**Operator layer:** `BI-SOP.md` is the single user-facing SOP and a MANDATORY sync surface;
`ITEM-CREATION-SOP.md` renders the intake config; the ripple runbook is BI-SOP §2.

Last updated: **<date>** — scaffolded from the `bi-change` client template. One stamp line: the chain of prior stamps belongs in `DECISIONS.md` under rule `DD`.

## 1. Taxonomy layers (who owns what)

<The architecture principle for this tenant: which taxonomies exist, which one is the anchor
key every other hangs off, and which mappings are invariants. One paragraph, then the table.>

| Layer | Nature | Job | Change cost |
|---|---|---|---|
| <layer> | <hardened / config / free text> | <what it is for> | <what a change costs> |

## 2. Business rules register

| # | Rule | Grain | Surface | Status | Since | Links | Record |
|---|---|---|---|---|---|---|---|

### Export-only rules register

A rule whose attribute has no field in the Looker model is canon like any other; it enforces
against the Catalog export (a runner under `scripts/`, per the lane contract in
`scripts/README.md`) and carries a Dutchie product-feedback ticket asking for the field.
`bi_impact_scan.js --stale` reports these rules as "no BI surface" info lines by design. Add a
row here whenever an attribute proves unreachable — the explore field-list read is the test.
Adding a rule = a row here (canon first), then one entry in the runner's table citing the R
number, then `--selftest`. Routing for every rule lives in `qc-surface-register.md`.

| Rule | Attribute | Export column | Check | Status |
|---|---|---|---|---|

## 2b. Bespoke dimensions

The business-definition layer — these definitions govern; expressions implement them. One
sub-heading per dimension, each stating what one row is, the canonical form, and what it
deliberately does NOT carry. A dimension enters here only after Adam signs it.

## 3. Expression canon

<The audit verdict: how many expressions, which are uniform estate-wide, and the intentional
variants that must NOT be unified — each with the reason the two bindings differ.>

## 4. Keeping it from drifting

The runbook is **BI-SOP §2** (single copy). Each QC lane carries its own operating rules, and
every lane, runner and cadence is routed by `qc-surface-register.md`.

Facts stay HERE only when they are canon rather than process. Two that always are:

1. The authority chain is **this document > intent files > live systems**.
2. **AI meeting summaries are CONTEXT, never the decision record** — mine them for the WHY and
   take the WHAT from the config export and Adam.
