---
name: dutchie-intake
description: Run a vendor invoice through the Dutchie intake lane — pull, intake (parse, catalog match, R102 exception flags, landed cost), one pre-create stop, Copy-item create, attributed-diff certify, new-items notice. Use when an invoice or PO lands, the Operator asks to intake, create or certify new items, or types /dutchie-intake.
---

# Dutchie Intake

The Procurement -> item-creation lane for a Dutchie tenant, as one command per stage. Sibling of
`bi-change`: same tenant pointer model, same lane contract, same write-channel ladder, same tone.
`bi-change` stays the governance kernel (canon, gates, tiles, docs); this skill never mints or
restates a rule, it cites the tenant's R numbers. Everything tenant-specific (labels, folder ids,
paths, thresholds, the Operator's name) comes from the tenant `CLAUDE.md`; nothing here names a client.

## Invocation

```
/dutchie-intake pull                                  mail label -> Drive + inbox/manifest.jsonl
/dutchie-intake intake <invoice.pdf | lines.csv>      parse -> match -> exceptions -> the ONE STOP
/dutchie-intake create <intake-vN.csv>                approved rows only, one Copy item per call
/dutchie-intake certify <pre.csv> <post.csv> <intake-vN.csv> [--no-create --allow <col>]
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
- **Exports** (required): Catalog Active + Retired and Strains, the Operator's clicks, never a browser
  download (the pane swallows downloads). Explicit paths, or the freshest in `Exports dir` under a row floor.
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
- Export QC / Inventory QC: (the BI Change Pointers lines)
## BI Change Pointers   (read here: Backoffice login, Write channel)
```

`python scripts/intake_pointers.py --tenant <CLAUDE.md>` validates it; every runner calls the same
parser through `--tenant` and ABORTs on a missing key or a value still written `<like this>`.
The Operator's name comes from `Operator:`, never from this file.

## Pipeline

```
mail label --pull--> Drive <Client>/Invoices/<Vendor>/<YYYY>/ + <Intake dir>/inbox/ + manifest.jsonl
invoice.pdf --intake_parse--> lines.csv --intake_match--> intake-v1.csv --intake_exceptions--> intake-v2.csv
   + -exceptions-<ts>.csv + the STOP message  ==> Operator fills `approved`, replies
   --create (write channel, Operator's login)--> intake-v3.csv (read-back SKU / ProductId)
   --intake_certify (pre / post exports)--> -certify-<ts>.md  --intake_notice--> -notice-<ts>.md
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
   `--active --retired --strains`). One verdict per product line: EXISTS, RETIRED_MATCH,
   NEW_ITEM_WITH_SIBLING, STRAIN_MISSING, NEW_PL, NEW_BRAND. The sibling is the active member of the
   R50 lane (Brand + Category + grams + Form word, name segment 2) with an image, else the newest.
   Dead records (R81) are never matched or copied. Lane fields are the sibling's own values.
   When brand + body + grams hit exactly ONE active item and only the Form test fails (the line names
   no form word at all), the verdict is EXISTS with the STOP-class flag `FORM_UNREAD` (R101): the
   Operator confirms the match. Two or more candidates, or a line that names a form word, stays
   NEW_PL. No vendor word goes into the generic form-synonym table. The intake CSV v3 has 54 columns;
   the last two are `parse_source` and `package_id`.
3. `intake_exceptions.py --intake <v1> --lines <lines.csv> [--po <po.csv>] --tenant <CLAUDE.md>`:
   R102 `COST_DRIFT` (list unit vs lane Cost, quiet when a discount or credit explains it),
   `PROMO_UNDECIDED` (landed unit <= 0.90 x lane Cost, R62, and no ruled Promo, Tier or margin
   program - PO `program` column or `--program <line>=<program>` - whether or not a discount line is
   printed; may co-fire with `COST_DRIFT`), `EXPIRY_NEAR`, `PO_MISMATCH`; the R62 INFO read
   `PKG_TAG_DUE`; R103 `landed_unit_cost`. Writes `-v2` + `-exceptions-<ts>.csv`, prints the STOP.
4. Send the STOP message (below) and stop.

**`create`** - the only Dutchie write. Operator's login. Only rows with `verdict =
NEW_ITEM_WITH_SIBLING` and `approved = Y`, in a version written AFTER the Operator's reply.
1. Freeze the baseline first: the Operator exports Active; an export that replaces a file in place is
   copied aside before any write.
2. Login stop (below). Then per row, ONE write-channel call: open the sibling by ProductId ->
   Actions > Copy -> in `Confirm copy product` replace the whole name with `create_name_FINAL` ->
   Confirm -> Strain (modal picker: type, take the exact option, check the type shown under it) and
   Flavor when flagged `FLAVOR_TO_SET` -> Online title and description (replace the strain paragraph
   only) -> images per the KB -> Save.
3. Read back after a reload: ProductId, SKU, name, Strain, Tags. The item-QC tag (R83) rides the copy;
   it is READ BACK, never assumed, and added if absent. Check for an inherited location-override row.
4. Write `new_sku`, `new_productid`, `verified`, `action = CREATED` into a NEW intake version. One
   Status line per item. A failure stops the run: fall down the ladder and record it; never retry blind.
Platform mechanics: `dutchie-bi-looker/references/dutchie-platform-kb.md`, "Item creation by Copy item".

**`certify`** - `intake_certify.py --pre <frozen> --post <after> --intake <vN>` (`--key ProductId` on
the Product export). Every changed cell lands in A (the created rows, each field equal to its target),
B (`Available`, down only) or C (foreign, reported, never waived). Siblings must be inert. Exit 1 on
any C cell or A mismatch. `--no-create --allow "<col>" [--rows ...]` certifies hand-made writes on
existing items instead. The certify report goes to the kickoff's Status; C cells go to the plan lane.

**`notice`** - `intake_notice.py --intake <vN> --tenant <CLAUDE.md>` fills the tenant's template
(a copy of `templates/notice.md`). It refuses (DEFECT) while an approved row lacks its read-back
SKU. A NEW_PL / NEW_BRAND row prints the `Floor sheet:` command; review it, then run it. The Operator
adds recipients and sends; this skill sends nothing.

**`receive`** - phase 2, not built. `receive.py` exits 2 and points at the receiving plan in the
tenant estate; its intended signatures (`--prep`, `--enter`, `--check`, `--vendor`) are in its header.
The `--check` join key is `package_id` (intake CSV v3 -> prep sheet -> Receipt Detail package tag).

## The ONE human stop (pre-create)

Nothing is created before the Operator's reply. Everything that needs no ruling and no login runs
first. The message, printed by `intake_exceptions.py`, has exactly three parts:

1. **Verdict table** - `# | Invoice line | Verdict | Sibling / match | Final name | Landed unit |
   Flags | approved`, one row per product line, plus the verdict counts.
2. **Exceptions table** - `# | Flag | Rule | Row | Detail`, every R102 flag and the R62 read, each
   with its R number. `PO_MISMATCH` reads `n/a` when no PO was given, never zero.
3. **The approve column** - the Operator fills `approved` (Y / N) in the named intake CSV version and
   replies. What Y does per verdict is printed with it: only NEW_ITEM_WITH_SIBLING + Y is created;
   RETIRED_MATCH is an un-retire by hand (R101); NEW_PL / NEW_BRAND / STRAIN_MISSING are never
   created by this lane.

Re-read the CSV the Operator saved before `create`; a peer relay of the approvals is not the record.

## Login stop

Open `Backoffice login` in the first channel of the ladder. If a password field is present, stop and
notify (the `PushNotification` tool when available, else the chat): *"Login needed in <channel> at
<url> - reply done."* Never type, read, store or relay credentials, from any source. Resume only on
the Operator's reply. Keep the stop cheap: every login-free step runs before it.

## Write channel

The `Write channel` pointer is an ordered ladder (for example `neo` -> `playwright` -> `pane`); reads
may use any channel. Rules the gate cannot see:
- One Copy item per call. Never batch guarded writes; no timer polls in a hidden tab.
- MUI Autocomplete fields (Strain, Flavor) need real keystrokes, which do not arrive while the window
  is hidden: use a VISIBLE tab.
- Plain text fields take the native value setter plus bubbling `input` and `change` events; use the
  on-page preview as proof before Save.
- Read back before any Status line. The POS public API is not a create route (no internal-name field).

## Traps (pointers, not restated)

Memory: `feedback_freshest_export_needs_row_guard` · `feedback_rules_before_profiling` (90 and 0.90
are ruled) · `feedback_name_substring_match_is_not_evidence` · `feedback_batched_guarded_writes_wedge_the_pane`
· `reference_dutchie_item_form_write_path` · `reference_dutchie_item_form_save_drops_location_override`
· `reference_claude_browser_pane_swallows_downloads` · `reference_neo_download_workaround`
· `feedback_handoff_expectations_go_stale` · the delivered-review-files memory (regenerate to new versions) ·
`feedback_generator_out_paths_clobber` · `reference_dutchie_export_grams_string` ·
`feedback_python_windows_cp1252_default` · `feedback_vendor_asks_surface_in_thread` ·
`feedback_bi_change_gate_inert_check` · `feedback_no_client_info_in_skills`.
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
`intake_exceptions.py` · `intake_certify.py` · `intake_notice.py` · `receive.py` (stub) ·
`intake_common.py` (shared plumbing). Python 3 stdlib only; run with `PYTHONUTF8=1`.

After ANY edit here run both, and both must pass:
- `python scripts/selftest_all.py` - every script's `--selftest`, then 44 fixture checks on
  `fixtures/`, each proven to FAIL on a named breaker (a check that stays green on its breaker is
  reported INERT), then the CLI chain in a temp folder.
- `node .claude/skills/bi-change/scripts/skill_leak_proof.js` - no client name, path or tenant id.
Then re-sync the wrapper: `powershell -ExecutionPolicy Bypass -File ops/notion-workspace/scripts/sync-claude-skill-wrappers.ps1`.
