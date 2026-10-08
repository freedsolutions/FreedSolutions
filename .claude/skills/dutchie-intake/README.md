<!-- Generated from "freed-solutions/skills/dutchie-intake/README.md". Edit the repo skill source and rerun ops/notion-workspace/scripts/sync-claude-skill-wrappers.ps1; do not edit this Claude copy directly. -->

# dutchie-intake

Invoice -> Dutchie item creation, one command per stage, one human stop. Generic: every tenant fact
lives in the tenant's gitignored `CLAUDE.md`. The workflow and the rules of the road are in `SKILL.md`.

## Pipeline

```
 mail label ──pull──▶ Drive <Client>/Invoices/<Vendor>/<YYYY>/  +  <Intake dir>/inbox/ + manifest.jsonl
                                  │
 invoice.pdf ──intake_parse──▶ lines.csv ──intake_match──▶ intake-v1 ──intake_exceptions──▶ intake-v2
 (or --text rendering, --lines)        (Active / Retired /           (R102 flags, R62 read,
                                            Strains exports)              R103 landed cost)
                                                                               │
                                          Operator fills `approved`, resolves the STOP flags
                                                                               │
          pre-batch freeze (the lane pulls Active, Retired, Strains, Categories, Brands; export_refresh --apply)
                                                                               │
          intake_plan ──▶ <stem>-plan-vN.csv + summary   ══ STOP: the Operator approves the plan (R124) ══
                                                                               │
          create (write channel, Operator's login): ONE paced batch - gridBatch (grid rows, a guard read per
          write, no read-back; the un-retire mutation) + the UI rows (intake_ui_run emit -> one neo `run` per
          row, intake_ui_rows.js in the page; record -> progress + keyMap) ──▶ -plan-vN-progress-<ts>.jsonl
              │   order = MINT_STRAIN, CREATE_BRAND, UNRETIRE_ALIGN, UNRETIRE, COPY, ALIGN, CONTENT, IMAGE_REMOVE, LINK
              ├──post pull (Active + Retired) ──intake_certify --plan ──▶ -certify-<ts>.md (ONE certify, A / B / C)
              └──intake_notice ──▶ -notice-<ts>.md  (+ floor-sheet command when a NEW_PL / NEW_BRAND item was created)
                                                     receive --prep ──▶ <slug>-receipt-prep-<date>-vN.csv + -questions.md (one row per Metrc package)
```

## Modes

| Mode | Script | Login | Output |
|---|---|---|---|
| `pull` | session procedure (Gmail + Drive connectors) | connector only | Drive copy, inbox mirror, `manifest.jsonl` |
| `intake` | `intake_parse.py` -> `intake_match.py` -> `intake_exceptions.py` -> `intake_msrp.py` (new lines only) | none | lines CSV, intake v1 + v2, exceptions CSV, `-msrp-<ts>.md`, STOP message |
| `create` | `intake_plan.py`, then `gridBatch` + `intake_ui_run.py` (UI rows) in the write channel | Operator's (batch only) | `-plan-vN.csv`, the progress JSONL, the keyMap |
| `certify` | `intake_certify.py --plan` (the batch); `--pre --post` / `--no-create` for hand writes | none | `-certify-<ts>.md` |
| `notice` | `intake_notice.py` | none | `-notice-<ts>.md` (a draft; the Operator sends) |
| `receive` | `receive.py --prep` (`--enter` / `--check` / `--vendor` stubs, exit 2) | none | `-receipt-prep-<date>-vN.csv` + `-questions.md` |

Exit codes everywhere: 0 clean, 1 DEFECT, 2 ABORT. Proof: `python scripts/selftest_all.py`.

## Files

| Path | What it is |
|---|---|
| `scripts/intake_pointers.py` | the tenant `## Intake Pointers` parser and validator |
| `scripts/intake_parse.py` + `scripts/parsers/` | invoice -> lines CSV (layout plugins) |
| `scripts/intake_match.py` | lines -> intake v1 (verdicts, lanes, `unretire_set`) |
| `scripts/intake_exceptions.py` | R102 flags, R62 read, R103 landed cost; the STOP message |
| `scripts/intake_msrp.py` | the recommended MSRP per new line (market + own shelf + floor), pending business confirmation |
| `scripts/intake_plan.py` | approved intake + the freeze -> the R124 plan file (refuses an UNPROVEN channel) |
| `scripts/intake_certify.py` | `--plan`: the ONE batch certify on the Active + Retired union; single-pair mode for hand writes |
| `scripts/intake_notice.py` | the new-items notice draft |
| `scripts/receive.py` | phase 2: `--prep`, the receipt prep sheet (other modes stubs) |
| `fixtures/receive-*.csv` | the synthetic receipt: a split package, a sample package, a new-line item, an order-level credit |
| `scripts/intake_common.py` | shared plumbing |
| `scripts/selftest_all.py` | every selftest + the `gridBatch` cases + the fixture checks + the CLI chain |
| `fixtures/plan-intake.csv` | the synthetic batch: an un-retire lane, a sibling copy, a cross-brand copy, an EXISTS row |
| `fixtures/plan-pre-active.csv`, `plan-pre-retired.csv` | the pre-batch freeze of that batch |
| `fixtures/plan-post-active.csv`, `plan-post-retired.csv` | the post pull with every planned cell landed |
| `fixtures/plan-strains.csv`, `plan-categories.csv`, `plan-brands.csv` | the records the plan binds by name |
| `../dutchie-bi-looker/scripts/backoffice_grid_write.js` | `gridBatch`, the batch runner (one allowlist for every lane) |

## Layouts and the intake CSV

- Invoice layouts are plugins in `scripts/parsers/`, tried in order: `apex`, `fernway`,
  `generic_table`. A parser is detected by layout features, never by the vendor name.
- Every parser emits `package_id` per product line (blank when the layout prints none). It rides into
  the intake CSV v3 (54 columns, ending `parse_source`, `package_id`) and is the `receive --check`
  join key.
- A line that names no form word, where brand + body + grams hit exactly one active item, reads
  `EXISTS` + `FORM_UNREAD` (a STOP flag): the Operator confirms the match.
- A flavor-led line, `(S|I|H) <Flavor> <Form>[ <ratio>]`, matches a body `<Flavor>[ <Effect>] (<type or
  ratio>)` by layout. Ratio cannabinoid order is unordered for the match only; a create name keeps the
  catalog's ratio spelling.
- The create path (R101): a product line carried before comes back by UN-RETIRING it whole (`RETIRED_MATCH`,
  or a sibling copy flagged `UNRETIRE_FIRST`; the set rides the v4 column `unretire_set`); any other new line
  copies the brand's nearest item in the Master category, else the CLOSEST item by subcategory, any brand
  (`CROSS_BRAND_COPY`, residue proven gone by certify); `NEW_BRAND` is a create (the Brand record first);
  `NEW_CATEGORY` fires only when the Category is absent from the Categories export. Directions: `--line-brand`,
  `--line-category`, `--strain-type <line_no>=<Type>@<source>`. The intake CSV is v5 (56 columns; v5 adds
  `image_source`, the create step's image-sourcing record that the notice reads).

## Plug in a tenant

1. Paste `templates/intake-pointers.md` into the tenant `CLAUDE.md` under `## BI Change Pointers`
   and fill every `<placeholder>`.
2. Copy `templates/notice.md` into the tenant and point `Notice template:` at the copy.
3. `python scripts/intake_pointers.py --tenant <tenant CLAUDE.md>` must print `contract complete`.
4. Create the mail label and the Drive `<Client>/Invoices/` root; put its folder id in the pointer.
5. First invoice: run `intake` with explicit export paths, read the STOP, and check the verdicts by
   hand before trusting a freshest-file pick.
