---
name: dutchie-intake
description: Run a vendor invoice through the Dutchie intake lane — pull, intake (parse, catalog match, R102 exception flags, landed cost), one pre-create stop, Copy-item create, attributed-diff certify, new-items notice. Use when an invoice or PO lands, the Operator asks to intake, create or certify new items, or types /dutchie-intake.
---

<!-- Generated from "freed-solutions/skills/dutchie-intake/SKILL.md". Edit the repo skill source and rerun ops/notion-workspace/scripts/sync-claude-skill-wrappers.ps1; do not edit this Claude copy directly. -->

# Dutchie Intake

The Procurement -> item-creation lane for a Dutchie tenant, as one command per stage. Sibling of
`bi-change`: same tenant pointer model, same lane contract, same write-channel ladder, same tone.
`bi-change` stays the governance kernel (canon, gates, tiles, docs); this skill never mints or
restates a rule, it cites the tenant's R numbers. Everything tenant-specific (labels, folder ids,
paths, thresholds, the Operator's name) comes from the tenant `CLAUDE.md`; nothing here names a client.

## Invocation

```
/dutchie-intake pull                                  mail label -> Drive + inbox/manifest.jsonl
/dutchie-intake intake <invoice.pdf | lines.csv>      parse -> match -> exceptions -> MSRP read -> the ONE STOP
/dutchie-intake create <intake-vN.csv>                freeze -> ONE plan file -> approval -> ONE paced batch (R124)
/dutchie-intake certify --plan <plan.csv> <pre-active> <pre-retired> <post-active> <post-retired>
/dutchie-intake certify <pre.csv> <post.csv> <intake-vN.csv> [--no-create --allow <col>]   (hand writes)
/dutchie-intake notice <intake-vN.csv>                draft the notice; print the floor-sheet command
/dutchie-intake receive                               phase 2 stub - exits 2
```

## When to Use

- A vendor invoice (or PO) lands in the tenant's mail label or inbox folder.
- The Operator asks to intake an invoice, create the new items it carries, or certify a create.
- Items were created by hand and need the certify or the notice after the fact (`--no-create`).
- Skip for a catalog-wide change, a rule change or a tile: that is `bi-change`.

## Inputs

- **Tenant `CLAUDE.md`** (required): `## Intake Pointers` + `## BI Change Pointers` (below).
- **Invoice** (required for `intake`): the PDF as filed by `pull`, a text dump, or a hand-typed lines CSV.
- **Exports** (required): Catalog Active + Retired and Strains (plus Categories and Brands for a plan). The
  LANE pulls them in the write channel - the pre-batch freeze and the post pull (R124) - by the KB recipe
  "Export pull per kind" and the neo download workaround, then freezes them with the `Export refresh` pointer
  (`export_refresh.py --apply`); never the Claude pane (it swallows downloads). The Operator's clicks are the
  fallback. Explicit paths, or the freshest in `Exports dir` under a row floor.
  Optional, picked from the same folder when present: the **Categories** export (the taxonomy `NEW_CATEGORY`
  reads) and the **Brands** export (a Brand record may exist with no item). Without them the catalog's own
  values stand in and the run says so.
- **PO** (optional): CSV `po_no, po_line, sku, description, units, unit_cost[, program]`.

## The tenant contract

Two blocks in the gitignored tenant `CLAUDE.md`. Paste `templates/intake-pointers.md` for the first;
the second is the `bi-change` block the tenant already has.

```
## Intake Pointers
- Operator: <name>                 - Mail label: <Gmail label>       - Drive invoices folder: <folder id>
- Intake dir: <abs path>           - Exports dir: <abs path>         - Standard cost: lane Cost (R50)
- Expiry threshold days: <n>       - PO source: <apex | vendor pdf | none>
- Watermark: <product_id>          - Notice template: <abs path>     - Floor sheet: <command>
- Vendor deal tag: <PKG - tag>
- Export QC / Inventory QC: (the BI Change Pointers lines)
- Market center / Market radius mi / Own store (+ optional Market box, Market archive, MSRP anchor, MSRP floor x cost)
## BI Change Pointers   (read here: Backoffice login, Write channel)
```

`python scripts/intake_pointers.py --tenant <CLAUDE.md>` validates it; every runner calls the same
parser through `--tenant` and ABORTs on a missing key or a value still written `<like this>`.
The Operator's name comes from `Operator:`, never from this file.

## Pipeline

```
mail label --pull--> Drive <Client>/Invoices/<Vendor>/<YYYY>/ + <Intake dir>/inbox/ + manifest.jsonl
invoice.pdf --intake_parse--> lines.csv --intake_match--> intake-v1.csv --intake_exceptions--> intake-v2.csv
   + -exceptions-<ts>.csv --intake_msrp--> -msrp-<ts>.md (new lines only)
   + the STOP message (MSRP pending business confirmation)  ==> Operator fills `approved`, resolves every STOP flag
   --lane pulls the pre-batch freeze (Active, Retired, Strains, Categories, Brands; export_refresh --apply)
   --intake_plan--> <stem>-plan-vN.csv + plan summary  ==> Operator approves the plan (the ONE STOP)
   --create (write channel, Operator's login): gridBatch + UI steps, paced--> -plan-vN-progress-<ts>.jsonl
   --lane pulls Active + Retired--> intake_certify --plan (ONE certify, the union)--> -certify-<ts>.md
   --intake_notice--> -notice-<ts>.md
```

Every output is a NEW file (a new `-vN`, or a timestamp): delivered files are the Operator's, and a
run never overwrites one. Exit codes for every script: 0 clean (STOP / INFO counts never fail),
1 DEFECT, 2 ABORT (input refused, usage, stub).

## Modes

**`pull`** - a session procedure over the connectors; no script, no browser.
1. Read `Mail label`, `Drive invoices folder`, `Intake dir`. Load `<Intake dir>/inbox/manifest.jsonl`.
2. Google Workspace connector `gmail_search` on the label with `has:attachment filename:pdf`. Skip
   every message whose id is already in the manifest: the mode is idempotent on `message_id`.
3. Per new message: `gmail_downloadAttachment`. The bytes arrive base64; decode and write them
   UNCHANGED to `<Intake dir>/inbox/<vendor>/<filename>`; compute the sha1.
4. Drive connector: find `<Client>/Invoices/<Vendor>/<YYYY>/` under the folder id; create each missing
   level with `create_file`, mime `application/vnd.google-apps.folder`, parent = the level above.
   Upload the PDF with `create_file` into the year folder. Read the Drive copy back and compare sha1.
   Filed BEFORE parse; the estate keeps the local mirror (R104). PO and COAs file beside it.
5. Append one JSON line per file: `message_id, vendor, invoice_no, drive_file_id, local_path, sha1,
   pulled_at`. `invoice_no` may be blank until `intake` reads it.
`pull` never puts the invoice, its number or its bytes in a URL or a query string: content goes
through connector bodies only.

**`intake`** - no login, no write.
1. `intake_parse.py --pdf <file> [--text <rendering>] [--lines <csv>] --tenant <CLAUDE.md>`. Sources
   are tried in this order and the first that yields product lines wins:
   **pypdf text layer -> `pdftotext -layout` -> `--text` -> `--lines`.** A PDF whose glyphs are drawn
   has NO text layer, so the first two return only page footers and the chain moves on. For `--text`,
   read the R104-filed copy with the Drive connector (`read_file_content`) or take an OCR pass, and
   save the plain text or markdown under `<Intake dir>/inbox/`; markdown tables are flattened and the
   SAME layout parsers run on it. `--lines` is the hand-typed CSV (columns in the script header).
   Nothing left = ABORT. The source used is written to every row as `parse_source` (`pypdf:`,
   `pdftotext:`, `text:`, `lines:` + file name) and carried into the intake CSV, so a certify reader
   knows the provenance. Layouts are plugins in `scripts/parsers/`, tried in this order: `apex`,
   `fernway`, `generic_table`. A parser is detected by layout features (column headings, field
   labels), never by the vendor name; a new vendor format is one module. Every parser emits
   `package_id` on each product line (the printed package tag(s), `;`-joined; blank when the layout
   has none). `TOTAL_MISMATCH` (R103) is a DEFECT.
2. `intake_match.py --lines <lines.csv> --tenant <CLAUDE.md> --min-rows <n>` (or explicit
   `--active --retired --strains [--categories --brands]`). One verdict per product line: EXISTS, RETIRED_MATCH,
   NEW_ITEM_WITH_SIBLING, STRAIN_MISSING, NEW_PL, NEW_CATEGORY, NEW_BRAND. The sibling is the active member of the
   R50 lane (Brand + Category + grams + Form word, name segment 2) with an image, else the newest.
   Dead records (R81) are never matched or copied. Lane fields are the sibling's own values.
   **The create path (R101, as the tenant's Dictionary states it):** a product line we carried before comes
   back by UN-RETIRING it, whole; any other new line duplicates the closest item by subcategory, any brand; the
   lane creates a new brand; the operator STOP is a Category or Master category the taxonomy lacks.
   **RETIRED_MATCH** is the un-retire path, never a copy: the matched item's whole R50 lane (every retired
   member - the brand's OTHER retired lines stay retired) is listed in `unretire_set`; Cost comes from the
   invoice, Price is confirmed current, the tag becomes the Active tag (`UNRETIRE_FIELDS`, STOP). A line that
   fits only a RETIRED lane is a sibling copy of the retired member, flagged `UNRETIRE_FIRST`: the lane comes
   back whole and is read back BEFORE the copy, which reads the Active tag. Directions the Operator can give:
   `--line-brand <line_no>=<Brand>` (a catalog brand matches under it; a Brand record with no item is a NEW_PL
   copy; a name no record carries is a NEW_BRAND create, spelled per R121), `--line-category <line_no>=<Category>`
   (a line whose words name no catalog form word: `CATEGORY_UNREAD` until given; checked against the taxonomy),
   `--strain-type <line_no>=<Type>@<source>` (a Type the lane researched; it rides the STOP with its source).
   A bare Strain Type word in a line (`Indica`) is never read as the Strain; on a flavored lane the type record
   is the Strain and the body `<Flavor> (<Type>)` is the Operator's to complete. A ratio line takes the ONE
   record with that ratio key, never a cannabinoid word out of it. A Type the line states that differs from the
   named record's is `STRAIN_TYPE_CONFLICT` (R128; a coarser `Hybrid` agrees with a leaner `Indica-Hybrid` /
   `Sativa-Hybrid`): the row lists the record's items. Within a brand a name has ONE record, so a disagreeing
   doc is a vendor ask - our own text and public sources decide whether the doc or the record is wrong. Only a
   record that other brands alone carry offers a NEW record `<Name> (<Type>)` - Dutchie Strain names are unique,
   so the bare name stays the existing record's (precedents `Gelato (Indica)`, `Honeydew (Sativa)`).
   When brand + body + grams hit exactly ONE active item and only the Form test fails (the line names
   no form word at all), the verdict is EXISTS with the STOP-class flag `FORM_UNREAD` (R101): the
   Operator confirms the match. Two or more candidates, or a line that names a form word, stays
   NEW_PL (or NEW_CATEGORY). No vendor word goes into the generic form-synonym table.
   **Flavor-led lines.** A line segment that leads with a strain-type letter, `(S|I|H) <Flavor> <Form>[ <ratio>]`,
   is read by layout: it matches a body `<Flavor>[ <Effect word>] (<Strain type or ratio>)` on the same
   flavor and, when the line prints a ratio, the same ratio with cannabinoid order unordered and case
   ignored (`1:1 CBD:THC` == `1:1 THC:CBD`); with no ratio, the letter must name the body's type. The
   unordered read is for MATCHING only: a create takes the brand's one Strain record with that ratio and
   keeps the catalog's spelling (R26), never the invoice's order. The intake CSV v3 has 54 columns;
   the last two are `parse_source` and `package_id`.
   **Tags (R96, R83).** A sibling copy carries its lane's decision tag: the ONE item-namespace tag every
   active member carries; a mixed lane reads the Active tag; `--tag-override <line_no>=<tag>` (or `*=`) is
   the business's direction and beats both. **NEW_PL** - a line that fits no lane under a brand we carry
   (an item or a Brand record) - is a CREATE from the brand's nearest active item in the Master category its
   form word places it in (same form word first, then the closest grams) or, when the brand has none there,
   from the CLOSEST active item by subcategory in the whole catalog (same Global SubCategory, then Category,
   then Master category), any brand (`CROSS_BRAND_COPY`: the copy gives up the source's Brand, Vendor, Price,
   Online title / description and image, and certify proves none of it survived). Tagged with the new-line tag
   and flagged `NEW_LINE_FIELDS` (STOP): the copy inherits a different lane, so the Operator sets or confirms
   name, Price, Flower equiv, Servings per Unit and Category / Type in the lane cells at the one stop. Grams
   come from the line, Cost from the invoice. A Category not read from the line's own words is flagged for the
   vendor's confirmation (`CATEGORY_DIRECTED` by direction, `CATEGORY_INFERRED` from another brand's item whose
   Category names a route word the line does not print - rosin, distillate, or resin beside an added-terpene
   mention; R33). A missing `Resin` alone, on a line that mentions no added terpenes, is Resin by default (INFO
   `ROUTE_RESIN_DEFAULT`, R33). Live vs cured is never
   a vendor question (R79): on a Live / Cured Category pair the taxonomy carries, a line that does not print
   `Cured` takes the Live Category - in a NEW_PL placement and in a Live / Cured lane tie - with the INFO note
   `OIL_LIVE_DEFAULT`; `Cured` printed takes the Cured Category. **NEW_CATEGORY** is
   the one STOP: the line's Category or Master category is absent from the taxonomy (a configuration decision).
   **NEW_BRAND** is a CREATE: the Brand record first (a live Global Brand read, R30; the display name as the
   Operator spells it, R121), then the line as a NEW_PL cross-brand copy; with no spelling (`BRAND_NAME_UNREAD`)
   nothing is created as it stands. Tag names: the tenant's optional `New line tag:` / `Active tag:` pointers,
   else `--new-line-tag` / `--active-tag`, else the generic defaults in `intake_common.py`. The intake CSV is
   v4: 55 columns, the 54 v3 columns in place plus `unretire_set`.
3. `intake_exceptions.py --intake <v1> --lines <lines.csv> [--po <po.csv>] --tenant <CLAUDE.md>`:
   R102 `COST_DRIFT` (list unit vs lane Cost, quiet when a discount or credit explains it),
   `DEAL_UNDECIDED` (landed unit <= 0.90 x lane Cost, R62, and no ruled Vendor Deal, Tier or margin
   program - PO `program` column or `--program <line>=<program>` - whether or not a discount line is
   printed; may co-fire with `COST_DRIFT`), `EXPIRY_NEAR`, `PO_MISMATCH`; the R62 INFO read
   `PKG_TAG_DUE`; R103 `landed_unit_cost`. Writes `-v2` + `-exceptions-<ts>.csv`, prints the STOP.
4. **MSRP read (R125)** - a standard step whenever v2 carries a new line (NEW_PL, NEW_BRAND, NEW_CATEGORY, a
   `NEW_LINE_FIELDS` or `CROSS_BRAND_COPY` row, or a STRAIN_MISSING row whose reason names a new line):
   `intake_msrp.py --intake <v2> --tenant <CLAUDE.md> [--cost <line_no|*>=<catalog cost>]`. Read-only, no
   login. One recommendation per product line (brand + form + size + process words), from two families of
   evidence: the MARKET (the same product at every store that lists it, median within each store then across
   stores; else the comparables - same form, size and process words, other brands - inside the tenant's
   radius) and the OWN SHELF (the tenant's active lanes of the same form and size: the lanes at the line's
   cost, else interpolated between the nearest cost groups). The tenant's `MSRP anchor:` says which family
   sets the number; the other is printed beside it as the sanity check. `MSRP floor x cost:` is a floor
   (2 = keystone). The nearest $5 price point, never under the floor. Cost: the catalog Cost the business will
   set (`--cost`, when the invoice price is a case deal), else the landed unit cost - never `lane_Cost`, which
   on a new line is the copy source's. Sources: the live public listing feed (cached per day under
   `<Intake dir>/market/`) and the dated `Market archive:`; dutchie.com scripted reads hit a Cloudflare
   challenge since 2026-09-23 - read the archive only, never work around the challenge. The tenant's own
   store (`Own store:`) is dropped BEFORE matching and the report asserts zero own-store rows (else DEFECT).
   Writes a NEW `<v2 stem>-msrp-<ts>.md` (per line: same-product table, comparables, own lanes, evidence
   counts, flags) and prints the STOP block. It writes no Price: the Operator sets the confirmed number in the
   lane cells at the stop (the confirmed number is the lane Price, R50). R125 states the rule; the $5 points,
   the radius and the 20 % `MSRP_SPREAD` are this script's parameters.
5. Send the STOP message (below), with the MSRP block, and stop.

**`create`** - the only Dutchie write, run as ONE batch from ONE approved plan file (R124). Operator's login.
Rows: `approved = Y` creates (`NEW_ITEM_WITH_SIBLING`, `NEW_PL`, `NEW_BRAND`) and un-retires (`RETIRED_MATCH`,
and the lane of a row flagged `UNRETIRE_FIRST`), in a version written AFTER the Operator's reply. A row with
no `copy_source_productid` or no `lane_Brand` is refused by the plan (re-run `intake` with the direction).
1. **Pre-batch freeze.** The lane pulls Catalog Active + Retired, Strains, Categories and Brands (Inputs) and
   freezes them. The freeze predates the first write, or the certify has no baseline.
2. **Plan.** `intake_plan.py --intake <vN> --active --retired --strains --categories --brands --tenant
   <CLAUDE.md>` writes a NEW `<stem>-plan-vN.csv`, one row per write: `seq, step, line_no, product_key, field,
   before, target, channel, depends_on, provenance, row_sha1`. Steps run in this order, which is the
   dependency: MINT_STRAIN, CREATE_BRAND, UNRETIRE_ALIGN, UNRETIRE, COPY, ALIGN, CONTENT, IMAGE_REMOVE, LINK.
   A record-bound field (Strain, Brand, Category, Vendor) is planned by name and bound to ONE live record id
   at run time. A row whose channel or guard read is UNPROVEN in the write-path map is REFUSED: no plan file,
   a refusals CSV, exit 2. An UNPROVEN row is a logged-in probe, never an assumption (probes P2-P7 landed
   2026-10-08: the retired guard read, the bulk-unretire mutation, grid Tags = REPLACE, the cross-MC Category
   move, VendorId / Grams / Servings / Online-available; CBDContent stays refused). A dead record (R81) is
   never a source and never un-retired.
3. **The ONE STOP is the plan approval.** The plan summary (writes per step and per channel, the refusals,
   the notes) goes to the Operator with the verdict and exception tables. No write before the reply. An
   approval that changes a row means a rebuilt plan (`-plan-vN+1`), never an edited one: `gridBatch`
   recomputes every `row_sha1` and refuses an edited row before the first request.
4. **Login stop** (below), then **the batch, paced** - no per-item read-back; the certify proves the result:
   grid rows by `gridBatch(plan, {dryRun: false, done, keyMap, ids})` (skill `dutchie-bi-looker`,
   `backoffice_grid_write.js`: one allowlist and one refusal set for every lane; a dry run first - N planned,
   0 refusals, zero requests) - it also sends each UNRETIRE row as the grid's bulk-unretire mutation, guarded on
   the record's `IsRetired`; UI rows (strain mint, COPY, CONTENT, the `ui_unretire` fallback) by a neo `run` script
   that `scripts/intake_ui_run.py emit --plan <plan> --seq <n> [--keymap <k>] [--live]` prints (it loads
   `scripts/intake_ui_rows.js` into the page: a FULL navigation per row, `Copy online details` asserted CHECKED,
   every form Save inspected BEFORE it leaves and blocked when a key the row does not touch would move). Run
   `intake_ui_run.py harvest --product <id>` once per tab first; `intake_ui_run.py record` writes each result to
   the progress JSONL and a COPY's new ProductId into the keyMap. Write channel (below) holds the pacing rules.
   **Un-retires first** (R101): per `unretire_set` member its UNRETIRE_ALIGN rows (Cost = `lane_Cost`, the
   invoice; Price confirmed current; the ONE decision tag, old one removed), then the un-retire (the grid's
   bulk-unretire mutation; Actions > Unretire is the UI fallback); the whole
   line comes back, the brand's other retired lines stay retired. **A new brand next** (`NEW_BRAND`): a live
   Global Brand read (R30); the Brand record created, linked to the Global Brand when it exists, display name =
   `lane_Brand` (R121). Then each COPY row is ONE write-channel call: open the
   source by ProductId -> Actions > Copy -> in `Confirm copy product` replace the whole name with
   `create_name_FINAL` (a blank name means the Operator writes it at the stop; never save a `(Copy)` name) ->
   keep `Copy online details` CHECKED on EVERY copy, sibling or cross-brand (ruled 2026-10-08: unchecked, the
   copy blanks the Online title, description and Global Category / Sub, yet the source brand's image still
   copies) -> Confirm -> Brand and Vendor on a cross-brand copy (`lane_Brand`, `lane_Vendor`) -> Strain (modal
   picker: type, take the exact option, check the type shown under it) and Flavor when flagged `FLAVOR_TO_SET`
   -> Online title and description (a sibling copy: replace the strain paragraph only; a `CROSS_BRAND_COPY`:
   replace both with the new brand's own words, none of the source's survive) -> images per the KB (a
   `CROSS_BRAND_COPY`: delete the copied image before Save) -> Save. Global Category / Sub carry from the
   source on every copy. In the batch the plan carries these as rows: Brand, Vendor (proven P7), Strain and Flavor are
   ALIGN grid rows; the cross-brand title and description are CONTENT rows whose target is the new brand's
   words (`online_title`, and `online_description` added at the STOP; a blank one refuses `CONTENT_UNWRITTEN`);
   the copied image is an IMAGE_REMOVE row run after the item's last form Save. The new ProductId goes into
   `keyMap` (where probe P1 shows it, else the item page URL). The copy inherits its source's tags: the plan
   sets the ONE decision tag the intake row's `tags` cell names and removes the source's - a grid `Tags` row whose
   target is the item's WHOLE tag set (grid Tags REPLACE, KB [PROBE 2026-10-08]), sent as TagIds from the live
   `get-tags` read the runtime passes in `ids.Tags`.
5. **Progress to disk** after every call: `<stem>-plan-vN-progress-<ts>.jsonl` (seq, status, live before,
   time). A resume reads the live rows and that log, never a page-side done-list. A STOP (`GUARD_MISMATCH`, a
   refusal, a 401) ends the batch: record it, fall down the ladder, never retry blind.
6. **Post pull + ONE certify** (below). Then write `new_sku`, `new_productid`, `verified`, `action = CREATED`
   from the certify's create map into a NEW intake version for the notice.
Platform mechanics: `dutchie-bi-looker/references/dutchie-platform-kb.md`, "Item creation by Copy item".

**`certify`** - ONE certify per batch, at the end (R124). After the last write the lane pulls Catalog Active
+ Retired (same recipe, frozen) and runs `intake_certify.py --plan <plan.csv> --pre-active <f> --pre-retired
<f> --post-active <f> --post-retired <f>`. It keys the UNION of the two files on ProductId with a synthetic
`_state` cell (`active` / `retired`), so an un-retire is ONE planned cell. A = every planned cell at its
target, plus the declared derived cells (Strain Type from StrainId; an un-retired row's `Brand catalog
product` moving blank -> link, because the Retired export prints that column blank - that direction only; a
created row's global link). B = `Available`, down only. C = every other moved cell, reported, never waived:
exit 1. A created row maps to its COPY row by the exact planned name (`DUP_CREATE` on two). Controls, each
with a fixture breaker: `ROW_REMOVED`, `C_FOREIGN_CELL`, `PLAN_NOT_APPLIED`, `UNRETIRE_PARTIAL`,
`UNRETIRE_FOREIGN`, `TAG_NOT_READ_BACK` / `TAG_EXTRA`, `CROSS_BRAND_RESIDUE` (whole cell) and
`CROSS_BRAND_RESIDUE_WORD` (the source brand's name or a source-only name word in Product, Online title or
Online description), `PLAN_SHA_MISMATCH`, `PLAN_BEFORE_MISMATCH`. An identical post pull is a cache, not a
result: pull again later. The single-pair mode (`--pre --post --intake`, `--no-create --allow "<col>" [--rows
...]`) stays for hand-made writes on existing items. The report goes to the kickoff's Status; C cells go to
the plan lane.

**`notice`** - `intake_notice.py --intake <vN> --tenant <CLAUDE.md>` fills the tenant's template
(a copy of `templates/notice.md`). It refuses (DEFECT) while an approved row lacks its read-back
SKU. A created NEW_PL item is marked on its line for the business's review. A NEW_PL / NEW_CATEGORY /
NEW_BRAND row prints the `Floor sheet:` command; review it, then run it. The Operator
adds recipients and sends; this skill sends nothing.

**`receive`** - phase 2, not built. `receive.py` exits 2 and points at the receiving plan in the
tenant estate; its intended signatures (`--prep`, `--enter`, `--check`, `--vendor`) are in its header.
The `--check` join key is `package_id` (intake CSV v3 -> prep sheet -> Receipt Detail package tag).

## The ONE human stop (pre-create)

Nothing is created before the Operator's reply. Everything that needs no ruling and no login runs
first. The message has three parts printed by `intake_exceptions.py`, plus a fourth printed by
`intake_msrp.py` whenever the intake carries a new line:

1. **Verdict table** - `# | Invoice line | Verdict | Sibling / match | Final name | Landed unit |
   Flags | approved`, one row per product line, plus the verdict counts.
2. **Exceptions table** - `# | Flag | Rule | Row | Detail`, every R102 flag and the R62 read, each
   with its R number. `PO_MISMATCH` reads `n/a` when no PO was given, never zero.
3. **The approve column** - the Operator fills `approved` (Y / N) in the named intake CSV version and
   replies. What Y does per verdict is printed with it: NEW_ITEM_WITH_SIBLING, NEW_PL and NEW_BRAND + Y are
   created (a NEW_BRAND after its Brand record); RETIRED_MATCH + Y un-retires the whole line (R101);
   NEW_CATEGORY and STRAIN_MISSING are never created by this lane.
4. **MSRP - pending business confirmation (R125)** - `# | Line | Rows | Unit cost | MSRP | Margin | Basis |
   Evidence (same / comps / lanes) | Flags`, one row per new line, each number marked *pending business
   confirmation*. The Operator confirms it with the business (or replaces it) and writes the confirmed Price
   into the lane cells (`NEW_LINE_FIELDS`). The flags are INFO: `MSRP_THIN`, `MSRP_SPREAD` (the number is
   more than 20 % from a market read that did not set it), `MSRP_FLOOR_RAISED`, `MSRP_MARGIN_LOW`,
   `MSRP_ARCHIVE_ONLY`, `MSRP_NO_EVIDENCE` (price it by hand with the business).

Re-read the CSV the Operator saved before `create`; a peer relay of the approvals is not the record.
Under R124 the plan summary (`intake_plan.py`) rides this stop: the Operator's approval of the plan
file is the go-ahead for every write in the batch, and nothing else is (create mode, step 3).

## Login stop

Open `Backoffice login` in the first channel of the ladder. If a password field is present, stop and
notify (the `PushNotification` tool when available, else the chat): *"Login needed in <channel> at
<url> - reply done."* Never type, read, store or relay credentials, from any source. Resume only on
the Operator's reply. Keep the stop cheap: every login-free step runs before it.

## Write channel

The `Write channel` pointer is an ordered ladder (for example `neo` -> `playwright` -> `pane`); reads
may use any channel. Rules the gate cannot see:
- An intake write batch runs from ONE approved plan file (R124): a guard read of the one item before each
  write (the field equals its planned before, else `GUARD_MISMATCH` STOPS the batch; equal to the target is
  `AT_TARGET`, skipped), NO per-item read-back, one UI item per call with a full navigation per form. Pace and
  back-off live in the neo runtime, never a page-side timer: at most 30 writes (60 requests) a minute; HTTP 429
  = not applied (back off; the guard read re-runs); a timed-out write is done-unknown (the next guard read
  decides); a 401 or a memory floor stops the batch.
- MUI Autocomplete fields (Strain, Flavor) need real keystrokes, which do not arrive while the window
  is hidden: use a VISIBLE tab.
- Plain text fields take the native value setter plus bubbling `input` and `change` events; use the
  on-page preview as proof before Save.
- The one certify on the post pull is the read-back (R124); no item is read back one by one. The POS public
  API is not a create route (no internal-name field).

## Traps (pointers, not restated)

Memory: `feedback_freshest_export_needs_row_guard` · `feedback_rules_before_profiling` (90 and 0.90
are ruled) · `feedback_name_substring_match_is_not_evidence` · `feedback_batched_guarded_writes_wedge_the_pane`
· `reference_dutchie_item_form_write_path` · `reference_dutchie_item_form_save_drops_location_override`
· `reference_claude_browser_pane_swallows_downloads` · `reference_neo_download_workaround`
· `feedback_handoff_expectations_go_stale` · the delivered-review-files memory (regenerate to new versions) ·
`feedback_generator_out_paths_clobber` · `reference_dutchie_export_grams_string` ·
`feedback_python_windows_cp1252_default` · `feedback_vendor_asks_surface_in_thread` ·
`feedback_bi_change_gate_inert_check` · `feedback_no_client_info_in_skills` ·
`reference_weedmaps_menu_feed_benchmark` · `reference_dutchie_public_menu_feed` ·
`feedback_exclude_own_store_from_market_sweep`.
KB: "Item creation by Copy item" (name set in the modal, ecom template, images, chaining copies).

## Lane contract

By pointer: the tenant's QC surface register, section "The lane contract and the cadence table".
Every script here obeys it: cites its R numbers per flag · freshest input under a row-count guard ·
`--selftest` (every flag fires on a synthetic row, stays quiet on its control) · a NEW timestamped
output · exit 1 only on DEFECT · abort on a missing column.

## Close-out

1. Status line + certify verdict in the tenant's kickoff; the certify `.md` named there.
2. Tenant `CLAUDE.md`: ONE change-log line pointing at the record.
3. Memory: one line only if the run taught something not derivable from the docs.
4. Browser phase ends: close the browser, then release any holder lock; delete `.playwright-mcp/` files.
5. Commit skill-side changes only; the tenant tree is never committed or named in a tracked file.

## Scripts and proofs

`scripts/`: `intake_pointers.py` · `intake_parse.py` (+ `parsers/`) · `intake_match.py` ·
`intake_exceptions.py` · `intake_msrp.py` (the MSRP read at the STOP) · `intake_plan.py` (the R124 plan file) · `intake_certify.py` · `intake_notice.py` ·
`intake_ui_run.py` + `intake_ui_rows.js` (the neo `run` driver for the plan's UI rows) · `receive.py` (stub) ·
`intake_common.py` (shared plumbing). Python 3 stdlib only; run with `PYTHONUTF8=1`.
The batch runner is `gridBatch` in `dutchie-bi-looker/scripts/backoffice_grid_write.js`.

After ANY edit here run both, and both must pass:
- `python scripts/selftest_all.py` - every script's `--selftest` and the `gridBatch` cases of
  `backoffice_grid_write_selftest.js`, then 83 fixture checks on `fixtures/` (the R124 batch rides
  `fixtures/plan-*.csv`), each proven to FAIL on a named breaker (a check that stays green on its breaker
  is reported INERT), then the CLI chain in a temp folder.
- `node .claude/skills/bi-change/scripts/skill_leak_proof.js` - no client name, path or tenant id.
Then re-sync the wrapper: `powershell -ExecutionPolicy Bypass -File ops/notion-workspace/scripts/sync-claude-skill-wrappers.ps1`.
