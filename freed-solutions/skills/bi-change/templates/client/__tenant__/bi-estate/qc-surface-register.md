# QC Surface Register — which canonized rules can be checked where

**Updated <date>** — scaffolded from the `bi-change` client template.

This answers one question per rule: **can a dashboard tile enforce this, and if not, what can?**
It is a routing document, not a rule document — every rule's *content* lives in
`DATA-DICTIONARY.md` and is cited, never restated here.

**Why it exists:** a spec written for an attribute that has no field in the reporting model is
always abandoned. Check this register before specifying any leg on an attribute no live tile
already uses.

---

## The three surfaces

| Surface | What it can see | Enforcement |
|---|---|---|
| **BI tile** (Looker `sql_server`) | the 19 explores' fields only | automated, on a dashboard, continuous |
| **Catalog export** (CSV) | every column Dutchie writes to the export | a script, run per sweep — no dashboard, no alert |
| **Internal API** | record-level fields absent from both | a script + a live session; slowest, most expensive |

A rule lands on the first surface that can see its attribute. Nothing here is a preference — it is
determined by where the field exists.

---

## 1 · Catalog-export only — no BI field exists

| Attribute | Rules | Verified absent | Runs where | Status |
|---|---|---|---|---|

## 2 · Internal API only — not in BI *or* the export

| Attribute | Rules | Why | Runs where |
|---|---|---|---|

## 3 · BI-enforceable — the default

Everything else.

## 4 · Script-side surface — every script the register rows cite

**CLASS is the load-bearing column:** a CONTROL is a standing check you may re-run to test a
rule; a GENERATOR builds a deliverable and proves nothing. Do not cite a generator as QC
evidence. Paths are relative to `clients/<client>/<tenant>/scripts/`.

| Script | Rules | Class | What it does |
|---|---|---|---|

## 5 · The lane contract and the cadence table

**The lane contract.** Every QC lane that runs outside BI is a runner that:

1. **cites the R numbers it enforces**, one entry per flag;
2. **defaults to the freshest matching input**, with a ROW-COUNT guard — a filtered one-off in
   the download folder carries the same name and column shape as a full export;
3. carries **`--selftest`** — every flag fires on a synthetic row and stays quiet on its control;
4. writes a **NEW timestamped output**, never overwrites;
5. **exits 1 on any DEFECT-class hit**; BACKLOG and INFO count and never fail the run;
6. **aborts on a missing or misspelt column** instead of reading it blank — a case slip
   manufactures false positives, not a silent zero.

`export_qc.py` is the reference implementation. A runner that breaks one of these six is not a
lane; fix the runner rather than the rule.

**The cadence table.** One row per lane. The tenant `CLAUDE.md` "Standing runs" line points
here and never restates a cadence.

| lane | runner | cadence | trigger | record |
|---|---|---|---|---|
| explore-catalog sync | `explore_catalog_harvest.js` → `explore_catalog_index.js` | weekly | + ad hoc before any leg on an attribute no live tile reads | <standing kickoff> |
| global-catalog scan | `gbc_scan.harvest.js` → `gbc_scan.py` | monthly | + after any bulk brand or link change | <kickoff> |
| export QC | `export_qc.py` (Active, then `--retired`) | per catalog sweep | `/bi-change qc` | <deliverables/> |
| inventory QC | `inventory_qc.py` | per catalog sweep | `/bi-change qc` | <deliverables/> |
| category config | `category-qc/qc.py` | on config change | a category, MC, Tax or PLC edit | <kickoff> |
| intake field config | `fields-config/` drift log | on config change | a Fields-Configure edit | <kickoff> |

---

## How to use this before specifying a leg

1. Is the attribute already read by a live tile? → it is BI-enforceable, proceed.
2. If not, **read the explore field list before writing a spec** — recipe in memory
   `reference_dutchie_bi_flavor_gap`: `GET /api/internal/core/4.0/lookml_models/sql_server/explores/<explore>`
   from `https://leaflogix.looker.com/embed/preload` with `X-CSRF-Token` + `X-Requested-With:
   XMLHttpRequest`. A bare fetch is a silent 403 with an empty body.
3. Absent from every explore → it belongs in §1 or §2. Add the row here, script the check, and park a
   product-feedback ticket. **Do not drop the rule** — canon carries rules the platform cannot
   enforce; that is the point of this register.

⚠ **A rule being unenforceable in BI does not make it less canonical.** Adam, 2026-09-04: *"you can
proceed to make these rules canon but don't worry about active QC or BI Tools (which is not an option
either way)."* The rule is the standard; the surface is an implementation detail that may change when
Dutchie ships a field.
