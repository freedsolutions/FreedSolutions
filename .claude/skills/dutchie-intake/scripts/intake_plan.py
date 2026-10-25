"""intake_plan.py - the ONE plan file an intake write batch runs from (R124). No login, no write.

  python intake_plan.py --intake <intake-vN.csv> --active <f> --retired <f> --strains <f>
                        --categories <f> --brands <f> [--out-dir <dir> | --tenant <CLAUDE.md>] [--dry-run]
                        [--fl-eq-classes <toml>]   (default: the tenant pointer `FL EQ classes:`)
                        [--pl-key <file.py>:<function>] [--discontinue-tag <tag>]   (default: the tenant pointers
                        `PL key:` / `Discontinue tag:`, else the generic key and `ITM - Discontinue`; R68)
                        --catalog-search <csv> [--catalog-state <stateLibrary>]   (default: the tenant pointer
                        `Catalog state:`; the global-link search the lane ran for every create, below)
                        [--catalog-records <json>]   (the batch-catalog-products read of the hits: R111 rung (a))
  python intake_plan.py --selftest

R124: the Operator approves one plan file that names every write - item, field, before-value, target. The
lane runs it as one paced batch (a live guard read per write, no per-item read-back) and proves it ONCE, at
the end, with `intake_certify.py --plan` on fresh Active + Retired exports. This script builds that file.

Input: the approved intake vN (rows with `approved = Y`) and the PRE-BATCH FREEZE - the Catalog Active and
Retired exports (both with `ProductId`), Strains, Categories, Brands. Every column read is required (ABORT).
Output: a NEW `<stem>-plan-vN.csv`, one row per write:

  seq, step, line_no, product_key, field, before, target, channel, depends_on, provenance, row_sha1

  step         in this order (R124, the kickoff's work item B): MINT_STRAIN, CREATE_BRAND, UNRETIRE_ALIGN,
               UNRETIRE, COPY, ALIGN, CONTENT, IMAGE_ADD, IMAGE_REMOVE, LINK. Order is the dependency.
  line_no      the intake row's 1-based position in the intake CSV.
  product_key  a ProductId; `new:<line_no>` for an item the COPY step creates; `strain:<name>` / `brand:<name>`
               for a record mint.
  field        the INTERNAL grid name (`Cost`, `StrainId`, ...) on the `grid` channel; the form control's
               label (`Tags`, `Online title`, `Online description`) on `item_form`; a synthetic name starting
               `_` for a write with no item field (`_state`, `_copy`, `_strain`, `_brand`, `_image_add`, `_images`,
               `_global_link`).
  before       the freeze value (for a copy: the copy SOURCE's value, which the copy inherits).
  target       the planned value. A record-bound field (StrainId, BrandId, ProductCategoryId, VendorId) is written
               `name:<label>`: the batch resolves it to exactly one live record id, never by guess.
  channel      the ONE named write path for the field (the write-path map below).
  depends_on   `;`-joined seqs this write needs first.
  row_sha1     sha1 of the other ten cells joined by U+001F; `gridBatch` recomputes every one in the page and
               refuses the plan on any mismatch (an edited row never runs).

The write-path map (kickoff 2026-10-08 §2 A). A row whose channel, field or guard read is not PROVEN is
REFUSED: the plan is not written, the refusals are (exit 2). An UNPROVEN row is a probe, never an assumption;
a probe result changes this table, with its cite, and nothing else does.

Copy dialog: `Copy online details` stays CHECKED on every copy (PROVEN, KB [PROBE 2026-10-08]; a dialog
setting, not a plan channel). A CROSS_BRAND_COPY then REPLACES the carried Online title and description with
the new brand's own words - `online_title` and the optional intake column `online_description`, written at
the STOP; a blank one is refused (CONTENT_UNWRITTEN), never planned as a clear - and deletes the copied image
(IMAGE_REMOVE). Global Category / Sub carry from the source.

Images (KB "Images"; the 2026-10-13 run). Copy item duplicates EVERY source image row under NEW blob file names, so
a created row's `Image URL` always moves and the certify declares it (the export cannot tell a copied row from own
art). A sibling copy carries the sibling's own label art (its strain printed on the device): a defect on the new
item. So a sibling copy whose source has an image plans IMAGE_ADD (the product's own art, create step 5 sourcing,
through the item form's Add image file input - it lands without a form Save) and then IMAGE_REMOVE of the copied
rows. A cross-brand copy plans IMAGE_REMOVE only (its new-brand art is step 5 after it). Every IMAGE_REMOVE is
guarded on the exact image-row list `get-product-extra-info` returns (`images[]` ids, read before the add): it
removes exactly the copied ids, by the `remove-product-image` replay `{...ctx, ProductImageId, ProductId}`. An
intake row with `image_keep = Y` (the Operator, at the STOP: the carried art is generic brand art, KB "Images")
plans no image row for that sibling copy.

Global link (operator ruling 2026-10-13: ALWAYS ATTEMPTED, a BEST GUESS - the business QCs after). Copy item drops
the source's brand-catalog link (seen 2026-10-13), so every create gets a link attempt, guarded on a null link. The
lane runs the search before it asks anything: `batch-catalog-products` on a sibling's `BrandCatalogProductId` (or the
brand's other linked items) gives `brandId`; `search-catalog-products` `{SearchTerm: <first strain/flavor word>,
BrandCatalogBrandIds: [brandId]}` (JSON:API, fields under `data[].attributes`) gives the candidates, typed into
`--catalog-search` (LINK_SEARCH_COLS, one row per candidate; a row with a blank `id` records a search with zero hits,
and a blank `brand_id` too says the brand has no global catalog brand). A create with no search row is REFUSED
(LINK_NOT_SEARCHED). The GBC name will often not match ours, so the plan GUESSES (link_decision): the PL's own naming
first - a linked sibling's record name with its strain / flavor word swapped for ours - then our own names; an exact
name is `exact`, else the closest Active in-state record that prints our strain / flavor word is a `best guess`; a
size that disagrees is never linked; a tie, or no such record, is `no match`. The LINK row is
`link-catalog-product` `{...ctx, BrandCatalogBrandId, BrandCatalogBrandName, BrandCatalogProductId,
BrandCatalogProductVersion: 0, ProductId}`. Each create's result prints in the summary as `global_link_result`;
step 7 writes it into the intake and the notice asks the business about every best guess and every no-match with
candidates. The Operator may override at the STOP in `global_link_pick` (a listed id, or `none`).

Online description, R111 rung (a) (K3, 2026-10-25). For a sibling copy whose link is an EXACT name, the plan reads
that record from `--catalog-records` (the batch-catalog-products read, by id) and compares every fact the record
states with ours: category / subcategory, weight (`options`, `suggestedWeightGrams`; never `weightGrams`, R99), dose,
pack and the strain / flavor word. All agree: `OD_RUNG ... rung (a)` - the record's description is the product
paragraph (taken whole when robust, a missing strain, flavor or effect part added; the sibling's template text
stays). Any disagreement, a best guess, an Operator pick or no link: `rung (b)`, the brand's assets. The lane runs
the plan `--dry-run` first, writes `online_description` and `online_desc_source` (the OD_RUNG text) in a NEW intake
version, then plans.

Derived fields (intake_derive.py; the intake row's `derived` cell, v6). A create row's Flower equiv, Servings per
Unit and CBD content that the lane DERIVED carry their rule cite into the plan row's provenance. Flower equiv is
RE-DERIVED here from the row's FINAL Product grams and Master category (the class map), so a grams correction at
the stop moves it; a row cell that disagrees is superseded and the provenance says so. A derived-blank CBD content
over a source value plans the clear - which the grid refuses (CBDContent UNPROVEN, P7): the refusal is the plan
telling the Operator the item form must clear it.

R68 (amended 2026-10-11): the Tags row of every create re-reads the item's PRODUCT LINE on the pre-batch freeze - the
active, live items under the same line key (the tenant's `PL key:` function, else intake_common.pl_key_default), with
this plan's un-retires counted as active and the copy keyed on its planned cells. When EVERY sibling (>= 1) carries the
discontinue tag, an undecided decision tag (Active or new-line) becomes the discontinue tag and the summary prints
PL_DISCONTINUED_CREATE (INFO): the line is discontinued; the buy is a recorded exception - PO reason owed. A mixed,
untagged or new line prints nothing; `ITM - Protect` (the deliberate keep, R48) stands.

A dead record (R81, the dead tag) is never a copy source and never un-retired. A RETIRED_MATCH (and an
UNRETIRE_FIRST copy) brings back its whole `unretire_set` (R101, the R50 lane): Cost = `lane_Cost` (the invoice),
Price = `lane_Price` (confirmed current at the STOP), the ONE decision tag (R96), then the un-retire.

Exit: 0 plan written (or a dry run with 0 refusals) · 2 refused or input refused (ABORT). Never 1: a plan has
no DEFECT, only refusals. The summary printed is the pre-create STOP's plan block: writes per step and channel.
"""
import hashlib
import json
import os
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from intake_common import (CATALOG_COLS, CATEGORIES_REQUIRED, CREATE_VERDICTS, DEFAULT_ACTIVE_TAG, DEFAULT_DEAD_TAG,  # noqa: E402
                           DEFAULT_DISCONTINUE_TAG, DEFAULT_NEW_LINE_TAG, EXIT_ABORT, EXIT_OK, ITEM_PREFIX, PL_DOSE,
                           line_state, pl_index, pl_key_default, STRAINS_REQUIRED, Selftest, abort, get_flag, grams_eq, grams_of, money_eq,
                           has_phrase, new_path, next_version, norm, num, read_csv, segs, stamp, strain_name_col, tag_set,
                           version_stem, write_csv)
from intake_match import V3_COLS  # noqa: E402
import intake_derive  # noqa: E402
import intake_apex_cost  # noqa: E402

# plan field -> (the derived-cell field name, the intake column it re-derives from)
DERIVED_FIELDS = {"FlowerEquivalent": "Flower equiv", "ServingSizePerUnit": "Servings per Unit", "CBDContent": "CBD content",
                  "Grams": "Product grams",   # R129: the vendor dose read (per piece / package total) rides the Grams row
                  "Cost": "Cost"}   # R125: a sample-only new line's Cost and its Apex source (intake_apex_cost.py)

PLAN_COLS = ["seq", "step", "line_no", "product_key", "field", "before", "target", "channel", "depends_on",
             "provenance", "row_sha1"]
HASH_COLS = PLAN_COLS[:-1]
SEP = "\x1f"
STEPS = ["MINT_STRAIN", "CREATE_BRAND", "UNRETIRE_ALIGN", "UNRETIRE", "COPY", "ALIGN", "CONTENT", "IMAGE_ADD",
         "IMAGE_REMOVE", "LINK"]
# The global-link search the lane ran per create (--catalog-search): one row per candidate record; a blank `id` = the
# search ran and returned zero hits. `line_no` = the intake row's 1-based position (the plan's line_no).
LINK_SEARCH_COLS = ["line_no", "search_term", "brand_id", "brand_name", "id", "name", "state", "status", "subcategory",
                    "size", "strain_type", "created"]
PROVEN, UNPROVEN = "PROVEN", "UNPROVEN"
REFUSAL_COLS = ["reason", "step", "line_no", "product_key", "field", "channel", "probe", "detail"]

# ---- The write-path map. Each entry: status, the probe that would prove it, the cite. -----------------------
CHANNELS = {
    "strain_mint": (PROVEN, "", "§2A row 1: update-strain replay, StrainId 0 - KB 'Minting a Strain record on the Strains page'"),
    "ui_brand_create": (UNPROVEN, "P5", "§2A row 2: KB 'Brand records' proves the rename call only"),
    "ui_brand_link": (UNPROVEN, "P5", "§2A row 3: KB trap 18 is a READ of the association"),
    "ui_copy": (PROVEN, "", "§2A row 4: UI Actions > Copy > Confirm copy product - KB 'Item creation by Copy item' "
                            "[PROBE 2026-09-13]; its request UNPROVEN (P1): certify maps the new row by its planned name"),
    "ui_unretire": (PROVEN, "", "§2A row 7: UI item page Actions > Unretire (10/8 run record); its request is "
                                "unretire-product with the whole 220-key form state (KB [PROBE 2026-10-08], P2) - a "
                                "UI fallback, never replayed"),
    "grid_bulk_unretire": (PROVEN, "", "§2A row 8: the grid's Bulk unretire = ONE GraphQL mutation "
                                       "UpdateProductRetiredStatus {lspId, productRetiredUpdates:[{productId, isRetired}]}, "
                                       "full-row read-back moved exactly IsRetired (KB [PROBE 2026-10-08], P3); "
                                       "gridBatch sends it after the guard read"),
    "grid": (PROVEN, "", "update-products-multiple - KB 'Path A′'; per field below"),
    "item_form": (PROVEN, "", "the item form, full navigation per item; per field below"),
    "image_remove": (PROVEN, "", "§2A row 20: remove-product-image replay {...ctx, ProductImageId, ProductId} - KB "
                                 "[PROBE 2026-09-26]; memory reference_dutchie_add_product_image_client_resize; a "
                                 "sibling copy's copied rows removed this way 2026-10-13"),
    "image_add_form": (PROVEN, "", "the item form's Online details > Add image file input (create step 5) - KB [PROBE "
                                   "2026-09-26], the app resizes in the browser; never an add-product-image replay; "
                                   "lands without a form Save (2026-10-13 run)"),
    "link_replay": (PROVEN, "", "§2A row 21: link-catalog-product / unlink-from-catalog-product replay - KB "
                                "'The global-catalog link picker' [PROBE 2026-09-15/16, 2026-09-22/23]; a copy linked "
                                "2026-10-13 moved ONLY BrandCatalogProductId"),
}
GRID_FIELDS = {
    "Name": (PROVEN, "", "§2A row 9: KB Path A′ [PROBE 2026-09-18/19]; helper allowlist"),
    "Cost": (PROVEN, "", "§2A row 10: KB Path A′ [PROBE 2026-09-28], active and retired; helper allowlist"),
    "Price": (PROVEN, "", "§2A row 10: KB Path A′ [PROBE 2026-09-28], active and retired; helper allowlist"),
    "FlowerEquivalent": (PROVEN, "", "§2A row 10: KB Path A′ [PROBE 2026-09-28]; helper allowlist"),
    "StrainId": (PROVEN, "", "§2A row 11: KB Path A′; helper allowlist (derives Strain Type)"),
    "Flavor": (PROVEN, "", "§2A row 12: KB Path A′ [PROBE 2026-09-19]; empty-value clear proven"),
    "BrandId": (PROVEN, "", "§2A row 13: helper allowlist provenance (UI save 2026-09-22)"),
    "ProductCategoryId": (PROVEN, "", "§2A row 14: KB Path A′ [PROBE 2026-09-28], inside one Master category"),
    "VendorId": (PROVEN, "", "§2A row 15: KB Path A′ [PROBE 2026-10-08] (P7), retired item, derives Vendor; helper allowlist"),
    "Grams": (PROVEN, "", "§2A row 16: KB Path A′ [PROBE 2026-10-08] (P7), retired item; helper allowlist"),
    "ServingSizePerUnit": (PROVEN, "", "§2A row 16: KB Path A′ [PROBE 2026-10-08] (P7), retired item; helper allowlist"),
    "CBDContent": (UNPROVEN, "P7", "§2A row 16: REFUSED 2026-10-08 - no retired item carries a value, so a probe "
                                   "could only be restored by an unproven clear; set it by the item form"),
    "IsOnlineProduct": (PROVEN, "", "§2A row 16: KB Path A′ [PROBE 2026-10-08] (P7): the modal posts \"Yes\" / \"No\"; "
                                    "helper allowlist"),
    "Tags": (PROVEN, "", "§2A row 17b: KB Path A′ [PROBE 2026-10-08] (P4): REPLACE - the target is the item's WHOLE tag "
                         "set, posted as TagIds; helper allowlist (gridBatch only)"),
}
FORM_FIELDS = {
    "Tags": (PROVEN, "", "§2A row 17: item form, real clicks - KB 'Retired products' [PROBE 2026-09-26]; "
                         "form-Save signature declared"),
    "Online title": (PROVEN, "", "§2A row 18: native setter + input/change - KB 'Online description on the product "
                                 "form' [PROBE 2026-09-15]; memory reference_dutchie_item_form_write_path"),
    "Online description": (PROVEN, "", "§2A row 18: native setter + input/change - KB 'Online description on the "
                                       "product form' [PROBE 2026-09-15]"),
}
CROSS_MC = (PROVEN, "", "§2A row 14: a cross-MC ProductCategoryId move re-derives Master category (KB [PROBE "
                        "2026-10-08], P6); Ecom category and tax categories did not move")
# The per-write guard read (§2A row 22). A write on an item whose guard is not proven is refused.
GUARD = {
    "active": (PROVEN, "", "§2A row 22: get-product-details-v2 {ctx, ProductId} - memory "
                           "reference_dutchie_item_form_save_drops_location_override (2026-09-25)"),
    "retired": (PROVEN, "", "§2A row 22: get-product-details-v2 on a RETIRED item returns the same 157-key record, "
                            "IsRetired true (KB [PROBE 2026-10-08], P2)"),
    "record": (PROVEN, "", "a record mint is guarded by the live list read (KB Path A′ get-strains)"),
    "image_rows": (PROVEN, "", "get-product-extra-info {ctx, ProductId}: the exact images[] id list, read before the "
                               "add; the remove takes exactly the copied ids (2026-10-13 run)"),
    "link_null": (PROVEN, "", "get-product-details-v2 {ctx, ProductId}: BrandCatalogProductId null - the copy drops "
                              "the source's link (2026-10-13 run); a live link is a STOP, never overwritten"),
}

# export column -> (field, channel, intake target column)
ROUTES = [("Cost", "Cost", "grid", "lane_Cost"), ("Price", "Price", "grid", "lane_Price"),
          ("Flower equiv", "FlowerEquivalent", "grid", "lane_FlowerEquiv"), ("Strain", "StrainId", "grid", "strain"),
          ("Flavor", "Flavor", "grid", "lane_Flavor"), ("Brand", "BrandId", "grid", "lane_Brand"),
          ("Category", "ProductCategoryId", "grid", "lane_Category"), ("Vendor", "VendorId", "grid", "lane_Vendor"),
          ("Product grams", "Grams", "grid", "lane_ProductGrams"),
          ("Servings per Unit", "ServingSizePerUnit", "grid", "lane_ServingsPerUnit"),
          ("CBD content", "CBDContent", "grid", "lane_CBDContent"),
          ("Is available online", "IsOnlineProduct", "grid", "lane_OnlineAvailable"),
          ("Tags", "Tags", "grid", "tags")]
# field -> the export column the certify reads it on (shared with intake_certify.py)
FIELD_COL = {f: c for c, f, _, _ in ROUTES}
# `_image_add` / `_images` map to no export cell: a created row's `Image URL` is declared (the copy's rows carry new
# blob names, so the export cannot tell copied art from own art); the image-row guard read is their proof.
FIELD_COL.update({"Name": "Product", "Online title": "Online title", "Online description": "Online description",
                  "_state": "_state", "_copy": "Product", "_global_link": "Brand catalog product"})
# a cell the COPY does not carry: the copy drops its source's brand-catalog link (seen 2026-10-13)
COPY_DROPS = ("Brand catalog product",)
# a planned field whose write moves another export cell by itself: declared, never a defect (R124)
DERIVES = {"StrainId": ["Strain Type"], "_state": ["Brand catalog product"],
           "ProductCategoryId": ["Master category"]}   # moves only on a cross-MC target (P6)
ID_FIELDS = {"StrainId", "BrandId", "ProductCategoryId", "VendorId"}
MONEY = {"Cost", "Price"}
GRAMS = {"FlowerEquivalent", "Grams"}
NUMBERS = {"ServingSizePerUnit", "CBDContent"}
CATALOG_REQUIRED_PLAN = CATALOG_COLS          # the 27-column export WITH ProductId (the batch binds by record)
BRANDS_REQUIRED = ["Display name"]


def row_sha1(r):
    return hashlib.sha1(SEP.join(str(r.get(c, "") if r.get(c) is not None else "") for c in HASH_COLS)
                        .encode("utf-8")).hexdigest()


def fmt_num(x):
    return ("%.4f" % x).rstrip("0").rstrip(".") if x is not None else ""


def plan_value(field, raw):
    """(value, ok). The plan's spelling of a cell value for `field`; ok False = not castable (a refusal)."""
    s = (raw or "").strip()
    if not s:
        return "", True
    if field in ID_FIELDS:
        return "name:" + s, True
    if field in MONEY or field in NUMBERS:
        x = num(s)
        return (fmt_num(x), True) if x is not None else (s, False)
    if field in GRAMS:
        g = grams_of(s)
        return (fmt_num(g), True) if g is not None else (s, False)
    return s, True


def same(field, a, b):
    a, b = (a or "").strip(), (b or "").strip()
    if field == "Tags":
        return tag_set(a) == tag_set(b)
    if not a or not b:
        return a == b
    if field in MONEY:
        return money_eq(a, b)
    if field in GRAMS or field in NUMBERS:
        x, y = num(a), num(b)
        return x is not None and y is not None and abs(x - y) < 1e-9
    return a == b


def tag_target(before_cell, decision_tag, prefix=ITEM_PREFIX):
    """The Tags cell after the write: every non-decision tag kept, the item namespace = the ONE tag (R96)."""
    keep = sorted(t for t in tag_set(before_cell) if not t.startswith(prefix))
    return ", ".join(keep + [decision_tag])


def keyed(rows, label):
    out = {}
    for r in rows:
        k = (r.get("ProductId") or "").strip()
        if not k:
            abort(f"{label}: a row has no ProductId - the batch binds by record id; export the 27-column shape")
        if k in out:
            abort(f"{label}: ProductId {k} appears twice")
        out[k] = r
    return out


def is_dead(r, dead_tag=DEFAULT_DEAD_TAG):
    return dead_tag in tag_set(r.get("Tags"))


def link_target(c):
    """A LINK row's target: the call's ids, then the record name LAST (the export prints the name)."""
    return f"id={c['id'].strip()};brand_id={c['brand_id'].strip()};brand_name={c['brand_name'].strip()};name={c['name'].strip()}"


def link_name(target):
    """The record name a LINK target carries (what `Brand catalog product` prints); a bare value passes through."""
    t = target or ""
    return t.split(";name=", 1)[1] if ";name=" in t else (t[len("name="):] if t.startswith("name=") else t)


def _toks(s):
    return set(norm(s).split())


def _jac(a, b):
    A, B = _toks(a), _toks(b)
    return len(A & B) / len(A | B) if A | B else 0.0


def link_templates(r, sibs):
    """The PL's own naming, translated: [(expected name, cite)]. A linked sibling of the same brand whose record name
    prints its strain / flavor word gives our expected name by swapping in our word (`Strain X Pre-Roll 1g` ->
    `Strain Q Pre-Roll 1g`). A sibling whose record does not print its word gives nothing (the GBC may not follow it)."""
    ours = (r.get("strain") or r.get("lane_Flavor") or "").strip()
    out, seen = [], set()
    for sb in sibs:
        link = (sb.get("Brand catalog product") or "").strip()
        w = (sb.get("Strain") or sb.get("Flavor") or "").strip()
        if not link or not w or not ours or norm(sb.get("Brand")) != norm(r.get("lane_Brand")) or sb.get("ProductId") in seen:
            continue
        seen.add(sb.get("ProductId"))
        pat = re.compile(r"(?<![A-Za-z0-9])" + re.escape(w) + r"(?![A-Za-z0-9])", re.I)
        if pat.search(link):
            out.append((pat.sub(ours, link), f"the PL's naming: sibling {sb.get('ProductId')} is linked to {link!r}"))
    return out


def link_near(cands, score, k=3):
    return "; ".join(f"{c.get('id')} | {c.get('name')} | {c.get('state')} | {c.get('status')}"
                     for c in sorted(cands, key=lambda c: -score(c)[0])[:k]) or "none"


def link_decision(r, cands, state_lib, templates=()):
    """The global-link BEST GUESS for one create (operator ruling 2026-10-13, refined the same day: the GBC name will
    often not match ours, so the lane guesses - "no match" included - and the business QCs after).
      ('link', record, 'exact' | 'best guess' | 'operator', why, nearest)   ('none', None, kind, why, nearest)
      ('refuse', reason code, detail, '', '')
    `cands` = this line's --catalog-search rows ([] = never searched); `templates` = link_templates() for the line.
    Only an Active record in the tenant's state library is ever linked; a size that disagrees is a different product.
    The name test runs against the PL's translated naming first, then our own names (invoice line, online title,
    create name): an exact name (case and punctuation ignored) is `exact`; else the closest name that prints our
    strain / flavor word is a `best guess` (a tie is `no match`). Subcategory or strain type disagreeing turns an
    exact name into a best guess. Every best guess and every no-match with hits is a question for the business."""
    if not cands:
        return ("refuse", "LINK_NOT_SEARCHED", "every create gets a global-link attempt (ruled 2026-10-13): the lane "
                "runs search-catalog-products for the line and types the hits (or one blank-id row for zero hits)", "", "")
    hits = [c for c in cands if (c.get("id") or "").strip()]
    own = [(r.get(c), f"our {c}") for c in ("invoice_line", "online_title", "create_name_FINAL") if norm(r.get(c))]
    expected = list(templates) + own

    def score(c):
        best = (0.0, "")
        for e, via in expected:
            v = 1.0 if norm(c.get("name")) == norm(e) else _jac(c.get("name"), e)
            if v > best[0]:
                best = (v, via)
        return best
    near = lambda pool: link_near(pool, score)  # noqa: E731
    pick = (r.get("global_link_pick") or "").strip()
    if pick.lower() == "none":
        return ("none", None, "none", "the Operator ruled no link at the plan STOP", "")
    if pick:
        got = [c for c in hits if c["id"].strip() == pick]
        if len(got) != 1:
            return ("refuse", "LINK_PICK_UNKNOWN", f"global_link_pick {pick!r} is not one of the line's listed candidates", "", "")
        return ("link", got[0], "operator", f"the Operator's pick at the plan STOP ({pick})", "")
    if not hits:
        brand = any((c.get("brand_id") or "").strip() for c in cands)
        return ("none", None, "no record", (f"zero hits for {cands[0].get('search_term')!r} under the brand" if brand else
                                            "the brand has no global catalog brand (no GBC entries)"), "")
    if not state_lib:
        return ("none", None, "no match", "no catalog state named (`Catalog state:` / --catalog-state)", near(hits))
    elig = [c for c in hits if norm(c.get("state")) == norm(state_lib) and norm(c.get("status")) == "active"]
    sized = [c for c in elig if not ((c.get("size") or "").strip() and (r.get("lane_ProductGrams") or "").strip()
                                     and not grams_eq(c["size"], r["lane_ProductGrams"]))]
    if not sized:
        return ("none", None, "no match", (f"no hit is Active in {state_lib}" if not elig else
                                           f"every Active {state_lib} hit is another size than ours "
                                           f"({r.get('lane_ProductGrams')})"), near(hits))

    def soft(c):
        d = []
        if (c.get("subcategory") or "").strip() and (r.get("lane_GlobalSubCategory") or "").strip() \
                and norm(c["subcategory"]) != norm(r["lane_GlobalSubCategory"]):
            d.append(f"its subcategory {c['subcategory']!r} is not ours ({r['lane_GlobalSubCategory']!r})")
        if (c.get("strain_type") or "").strip() and (r.get("strain_type") or "").strip() \
                and norm(c["strain_type"]) != norm(r["strain_type"]):
            d.append(f"its strain type {c['strain_type']!r} is not ours ({r['strain_type']!r})")
        return d
    exact = [c for c in sized if score(c)[0] == 1.0]
    if exact:
        c = sorted(exact, key=lambda c: (len(soft(c)), c.get("created") or ""))[0]
        why = f"exact name via {score(c)[1]}"
        if len(exact) > 1:
            return ("link", c, "best guess", f"{why}, but {len(exact)} records share the name: took the one with the fewest "
                    "disagreements, then the earliest created", near([x for x in exact if x is not c]))
        if soft(c):
            return ("link", c, "best guess", f"{why}, but " + " and ".join(soft(c)), "")
        return ("link", c, "exact", why, "")
    word = (r.get("strain") or r.get("lane_Flavor") or "").strip()
    pool = [c for c in sized if _toks(word) <= _toks(c.get("name"))] if word else [c for c in sized if score(c)[0] >= 0.6]
    if not pool:
        return ("none", None, "no match", (f"no Active {state_lib} record names {word!r}" if word else
                                           "no Active record's name is close to ours"), near(sized))
    ranked = sorted(pool, key=lambda c: -score(c)[0])
    top = ranked[0]
    if len(ranked) > 1 and score(top)[0] - score(ranked[1])[0] < 0.05:
        return ("none", None, "no match", f"a tie: {top.get('id')} and {ranked[1].get('id')} are equally close", near(ranked))
    why = f"the closest name (score {score(top)[0]:.2f} via {score(top)[1]})" + (" - " + " and ".join(soft(top)) if soft(top) else "")
    return ("link", top, "best guess", why, near(ranked[1:]))


def link_result(kind, conf, rec, why, nearest):
    """The `global_link_result` cell step 7 writes for the notice (one value per create)."""
    if kind == "link":
        head = "linked" if conf in ("exact", "operator") else "best guess"
        tail = "" if head == "linked" else (f"; other candidates: {nearest}" if nearest else "") + "; please confirm"
        return f"{head}: {rec['id']} | {rec['name']} - {why}{tail}"
    if conf == "none":
        return f"none: {why}"
    return f"{conf}: {why}" + (f"; nearest: {nearest}" if nearest else "")


OZ = {"1/8oz": 3.5, "1/4oz": 7.0, "1/2oz": 14.0, "1oz": 28.0}


def _rec_grams(a):
    """The grams a GBC record states: its `options` sizes and `suggestedWeightGrams`. Never `weightGrams` (R99: on the
    harvest that field is not grams)."""
    out = set()
    for o in a.get("options") or []:
        s = str(o).strip().lower().replace(" ", "")
        g = OZ.get(s, grams_of(s))
        if g:
            out.add(round(g, 4))
    g = num(a.get("suggestedWeightGrams"))
    if g:
        out.add(round(g, 4))
    return out


def _rec_mg(a):
    th = a.get("thcContent") or {}
    rng = th.get("range") or []
    if (th.get("unit") or "").upper() == "MILLIGRAMS" and rng and num(rng[0]):
        return num(rng[0])
    return num(a.get("suggestedDosageMg"))


def od_rung_a(r, kind, conf, rec, record):
    """R111 rung (a) for one create (K3, 2026-10-25): the linked GBC record's description is the product paragraph's
    first source, but ONLY on a link past the R98 gate. (fires, why). Fires only when the link is an EXACT name (a best
    guess, an Operator pick or no link falls to rung (b)), the record was read (`--catalog-records`), it carries a
    description, and every fact the record states agrees with ours: category / subcategory, weight, dose, pack and the
    strain / flavor word. A fact the record does not state is not compared."""
    if kind != "link" or conf != "exact":
        return False, f"rung (b): the link is {'a ' + conf if kind == 'link' else 'absent (' + conf + ')'}, not an exact name past the R98 gate"
    a = (record or {}).get("attributes", record) if record else None
    if not a:
        return False, f"rung (b): record {rec.get('id')} was not read (pass the batch-catalog-products read as --catalog-records)"
    if not (a.get("description") or "").strip():
        return False, f"rung (b): record {rec.get('id')} carries no description"
    dis, ok = [], []
    for fld, ours in (("category", r.get("lane_GlobalCategory")), ("subcategory", r.get("lane_GlobalSubCategory"))):
        theirs = (a.get(fld) or "").strip()
        if theirs and (ours or "").strip():
            (ok if norm(theirs) == norm(ours) else dis).append(f"{fld} {theirs!r}" + ("" if norm(theirs) == norm(ours) else f" vs ours {ours!r}"))
    gs, g = _rec_grams(a), grams_of(r.get("lane_ProductGrams"))
    if gs and g:
        (ok if round(g, 4) in gs else dis).append(f"weight {sorted(gs)}g" + ("" if round(g, 4) in gs else f" vs ours {g:g}g"))
    p = segs(r.get("create_name_FINAL"))
    m = PL_DOSE.match(p[3]) if len(p) > 3 else None
    our_pk = int(m.group(3)) if m and m.group(3) else 1
    our_mg = float(m.group(1)) * our_pk if m and m.group(2).lower() == "mg" else None
    rmg = _rec_mg(a)
    if rmg and our_mg:
        (ok if abs(rmg - our_mg) < 1e-6 else dis).append(f"dose {rmg:g}mg" + ("" if abs(rmg - our_mg) < 1e-6 else f" vs ours {our_mg:g}mg"))
    rpk = num(a.get("packSize")) or num(a.get("suggestedPackSize"))
    if rpk and m:
        (ok if int(rpk) == our_pk else dis).append(f"pack {int(rpk)}" + ("" if int(rpk) == our_pk else f" vs ours {our_pk}"))
    word = (r.get("strain") or r.get("lane_Flavor") or "").strip()
    if word:
        said = (a.get("suggestedStrainName") or "").strip()
        if said:
            (ok if norm(said) == norm(word) else dis).append(f"strain {said!r}" + ("" if norm(said) == norm(word) else f" vs ours {word!r}"))
        else:
            (ok if has_phrase(norm(a.get("name")), word) else dis).append(f"word {word!r}" + (" in the record name" if has_phrase(norm(a.get("name")), word) else " missing from the record name"))
    if dis:
        return False, f"rung (b): record {rec.get('id')} disagrees: " + "; ".join(dis)
    return True, f"rung (a): GBC record {rec.get('id')} | {a.get('name') or rec.get('name')} - every stated fact agrees ({'; '.join(ok) or 'none stated'})"


def load_catalog_records(path):
    """--catalog-records: the batch-catalog-products read the link search already makes. JSON:API `{data: [...]}`, a
    list of records, or a map id -> record; each record `{id, attributes}` or bare attributes. -> {id: attributes}."""
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    items = d.get("data", d) if isinstance(d, dict) else d
    items = items.values() if isinstance(items, dict) else items
    out = {}
    for x in items:
        a = x.get("attributes", x) if isinstance(x, dict) else {}
        rid = str(x.get("id") or a.get("id") or "").strip() if isinstance(x, dict) else ""
        if rid:
            out[rid] = a
    return out


def sibling_own_text(desc, peer_descs, floor=40):
    """The part of a sibling's Online description its line does NOT share: the sibling's own (strain) paragraph.
    Peers = the other active items of the same Brand + Category + Product grams. The text is compared with line
    breaks removed (the Catalog export drops them). The longest suffix shared with any peer is the line's template;
    what is left in front of it is the sibling's own text. No peer = nothing to tell template from own text, so the
    whole description counts as own. Returns '' when the own text is under `floor` chars (the template alone)."""
    flat = lambda s: (s or "").replace("\r", "").replace("\n", "").strip()
    s = flat(desc)
    if not s:
        return ""
    best = 0
    for p in peer_descs:
        q, k = flat(p), 0
        while k < min(len(s), len(q)) and s[-1 - k] == q[-1 - k]:
            k += 1
        best = max(best, k)
    own = s[:len(s) - best].strip()
    return own if len(own) >= floor else ""


def build_plan(intake, active, retired, strains, categories, brands, channels=None, grid_fields=None,
               form_fields=None, guard=None, dead_tag=DEFAULT_DEAD_TAG, prefix=ITEM_PREFIX, fl_eq_classes=None,
               pl_key_fn=pl_key_default, discontinue_tag=DEFAULT_DISCONTINUE_TAG, active_tag=DEFAULT_ACTIVE_TAG,
               new_line_tag=DEFAULT_NEW_LINE_TAG, link_search=None, catalog_state=None, catalog_records=None):
    """Pure. (plan rows, refusals, notes). The four maps default to this module's; a selftest passes a copy
    to simulate a probe result - the CLI has no flag that widens them. `fl_eq_classes` = the tenant's class map
    (intake_derive.load_classes); None = no re-derivation, the row's cells stand. `pl_key_fn` = the PRODUCT LINE key
    for the R68 line read on each create's Tags row (None skips it). `link_search` = the --catalog-search rows
    (None = no search: every create refuses LINK_NOT_SEARCHED); `catalog_state` = the tenant's stateLibrary;
    `catalog_records` = {id: attributes} from --catalog-records, read for R111 rung (a) (od_rung_a; None = not read)."""
    channels, grid_fields = channels or CHANNELS, grid_fields or GRID_FIELDS
    form_fields, guard = form_fields or FORM_FIELDS, guard or GUARD
    act, ret = keyed(active, "--active"), keyed(retired, "--retired")
    both = sorted(set(act) & set(ret))
    if both:
        abort(f"ProductId(s) {both[:5]} sit in both the Active and the Retired export - not one freeze")
    scol = strain_name_col(strains[0].keys(), "--strains") if strains else "Strain name"   # `Strain name` | `Name`
    strain_names = {norm(s.get(scol)): (s.get(scol) or "").strip() for s in strains}
    mc_of = {norm(c.get("Category")): (c.get("Master category") or "").strip() for c in categories}
    brand_names = {norm(b.get("Display name")) for b in brands} | {norm(r.get("Brand")) for r in active + retired}
    rows, refusals, notes = [], [], []
    state = {}                        # ProductId / new:<n> -> the planned cell values (an overlay on the freeze)

    def eff(key, col):
        if key in state and col in state[key]:
            return state[key][col]
        src = act.get(key) or ret.get(key) or {}
        return src.get(col, "")

    def refuse(reason, step, line_no, key, field, channel, probe, detail):
        refusals.append(dict(reason=reason, step=step, line_no=line_no, product_key=key, field=field,
                             channel=channel, probe=probe, detail=detail))

    def emit(step, line_no, key, field, before, target, channel, deps, scope, cite_extra=""):
        st, probe, cite = channels[channel]
        if channel == "grid":
            st, probe, cite = grid_fields.get(field, (UNPROVEN, "", f"`{field}` is not on the grid allowlist"))
        elif channel == "item_form":
            st, probe, cite = form_fields.get(field, (UNPROVEN, "", f"`{field}` has no proven form route"))
        if st != PROVEN:
            refuse("CHANNEL_UNPROVEN", step, line_no, key, field, channel, probe, cite)
        gst, gprobe, gcite = guard[scope]
        if gst != PROVEN:
            refuse("GUARD_UNPROVEN", step, line_no, key, field, channel, gprobe, f"{scope} item: {gcite}")
        r = dict(seq=str(len(rows) + 1), step=step, line_no=str(line_no), product_key=key, field=field,
                 before=before, target=target, channel=channel,
                 depends_on=";".join(str(d) for d in sorted(set(deps), key=int)),
                 provenance=(cite + ("; " + cite_extra if cite_extra else "")))
        rows.append(r)
        col = FIELD_COL.get(field)
        if col:
            state.setdefault(key, {})[col] = target
        return r["seq"]

    # R125: the rows of a SAMPLE-ONLY new line (every package a sample or display) - their Cost must be SETTLED (a `Cost:`
    # entry in the row's derived cell: the Apex PO / listing, or the Operator's typed Cost), never the copy source's.
    sample_only = intake_apex_cost.sample_only_rows(intake)
    approved = [(i + 1, r) for i, r in enumerate(intake) if (r.get("approved") or "").strip().upper() == "Y"]
    creates = [(n, r) for n, r in approved if r.get("verdict") in CREATE_VERDICTS]
    unret = [(n, r) for n, r in approved if r.get("verdict") == "RETIRED_MATCH"
             or (r.get("verdict") in CREATE_VERDICTS and "UNRETIRE_FIRST" in (r.get("flags") or "").split(";"))]
    for n, r in approved:
        if r.get("verdict") not in CREATE_VERDICTS + ("RETIRED_MATCH", "EXISTS"):
            refuse("NOT_PLANNABLE", "", n, "", "", "", "",
                   f"verdict {r.get('verdict')} is never written by this lane (R101): resolve it at the STOP")

    def one_tag(n, r, step, key):
        t = {x for x in tag_set(r.get("tags")) if x.startswith(prefix)}
        if len(t) != 1:
            refuse("TAG_NOT_ONE", step, n, key, "Tags", "item_form", "",
                   f"the intake row names {sorted(t) or 'no'} decision tag(s); R96 wants exactly one")
            return None
        return t.pop()

    # 1 MINT_STRAIN ------------------------------------------------------------------------------------------
    minted = {}
    for n, r in creates:
        s = (r.get("strain") or "").strip()
        if s and norm(s) not in strain_names and norm(s) not in minted:
            typ = (r.get("strain_type") or "").strip()
            if not typ:
                refuse("STRAIN_TYPE_UNKNOWN", "MINT_STRAIN", n, f"strain:{s}", "_strain", "strain_mint", "",
                       "a Strain record is minted with its Type (R26); the intake row has none")
            minted[norm(s)] = emit("MINT_STRAIN", n, f"strain:{s}", "_strain", "", f"name={s};type={typ}",
                                   "strain_mint", [], "record")
    # 2 CREATE_BRAND -----------------------------------------------------------------------------------------
    brand_rows = {}
    for n, r in creates:
        b = (r.get("lane_Brand") or "").strip()
        if r.get("verdict") == "NEW_BRAND" and b and norm(b) not in brand_names and norm(b) not in brand_rows:
            s1 = emit("CREATE_BRAND", n, f"brand:{b}", "_brand", "", b, "ui_brand_create", [], "record")
            s2 = emit("CREATE_BRAND", n, f"brand:{b}", "_brand_link", "", b, "ui_brand_link", [s1], "record")
            brand_rows[norm(b)] = s2
    # 3 UNRETIRE_ALIGN + 4 UNRETIRE ---------------------------------------------------------------------------
    member_line, member_targets, align_seqs = {}, {}, {}
    for n, r in unret:
        ids = [x.strip() for x in (r.get("unretire_set") or "").split(";") if x.strip()]
        if not ids:
            refuse("UNRETIRE_SET_EMPTY", "UNRETIRE_ALIGN", n, "", "", "", "", "the row brings a line back but names no set")
        tag = one_tag(n, r, "UNRETIRE_ALIGN", ";".join(ids))
        want = (r.get("lane_Cost", ""), r.get("lane_Price", ""), tag)
        for pid in ids:
            if pid in member_targets and member_targets[pid] != want:
                refuse("UNRETIRE_TARGET_CONFLICT", "UNRETIRE_ALIGN", n, pid, "", "", "",
                       f"two intake rows bring {pid} back with different Cost / Price / tag")
                continue
            member_targets[pid], member_line[pid] = want, n
    for pid, (cost, price, tag) in member_targets.items():
        n = member_line[pid]
        m = ret.get(pid)
        if m is None:
            refuse("UNRETIRE_NOT_RETIRED", "UNRETIRE_ALIGN", n, pid, "_state", "ui_unretire", "",
                   "not in the Retired freeze" + (" (it is ACTIVE)" if pid in act else " (absent from both)"))
            continue
        if is_dead(m, dead_tag):
            refuse("DEAD_RECORD", "UNRETIRE_ALIGN", n, pid, "_state", "ui_unretire", "",
                   "R81: a dead record is never brought back")
            continue
        seqs = []
        for col, field, tgt_raw in (("Cost", "Cost", cost), ("Price", "Price", price)):
            tgt, ok = plan_value(field, tgt_raw)
            bef, _ = plan_value(field, m.get(col))
            if not ok:
                refuse("VALUE_NOT_NUMERIC", "UNRETIRE_ALIGN", n, pid, field, "grid", "", f"target {tgt_raw!r}")
            if tgt and not same(field, bef, tgt):
                seqs.append(emit("UNRETIRE_ALIGN", n, pid, field, bef, tgt, "grid", [], "retired"))
        if tag and not same("Tags", m.get("Tags"), tag_target(m.get("Tags"), tag, prefix)):
            seqs.append(emit("UNRETIRE_ALIGN", n, pid, "Tags", m.get("Tags", ""), tag_target(m.get("Tags"), tag, prefix),
                             "grid", [], "retired"))
        align_seqs[pid] = (n, seqs)
    # every UNRETIRE_ALIGN row runs before the first UNRETIRE: the step order IS the dependency order
    for pid, (n, seqs) in list(align_seqs.items()):
        align_seqs[pid] = emit("UNRETIRE", n, pid, "_state", "retired", "active", "grid_bulk_unretire", seqs, "retired")
    # 5 COPY -------------------------------------------------------------------------------------------------
    copies, planned_names = {}, {}
    active_names = {(r.get("Product") or "").strip() for r in active}
    for n, r in creates:
        key, src_id = f"new:{n}", (r.get("copy_source_productid") or "").strip()
        name = (r.get("create_name_FINAL") or "").strip()
        if not src_id or not (r.get("lane_Brand") or "").strip() or not name:
            refuse("NOT_CREATABLE", "COPY", n, key, "_copy", "ui_copy", "",
                   "R101: a create row needs copy_source_productid, lane_Brand and create_name_FINAL")
            continue
        if name.endswith("(Copy)"):
            refuse("NAME_IS_COPY", "COPY", n, key, "_copy", "ui_copy", "", "never save a `(Copy)` name")
        if name in active_names:
            refuse("NAME_EXISTS", "COPY", n, key, "_copy", "ui_copy", "", f"an active item is already named {name!r}")
        if name in planned_names:
            refuse("DUP_NAME_PLANNED", "COPY", n, key, "_copy", "ui_copy", "",
                   f"line {planned_names[name]} plans the same name: certify maps a create by its exact name")
        planned_names[name] = n
        src = act.get(src_id) or ret.get(src_id)
        if src is None:
            refuse("SOURCE_UNKNOWN", "COPY", n, key, "_copy", "ui_copy", "", f"copy source {src_id} is in neither freeze")
            continue
        if is_dead(src, dead_tag):
            refuse("DEAD_SOURCE", "COPY", n, key, "_copy", "ui_copy", "", "R81: a dead record is never a copy source")
            continue
        deps = []
        if src_id in ret:
            if src_id not in align_seqs:
                refuse("SOURCE_RETIRED", "COPY", n, key, "_copy", "ui_copy", "",
                       f"copy source {src_id} is retired and no UNRETIRE row brings it back first (UNRETIRE_FIRST)")
                continue
            deps.append(align_seqs[src_id])
        b = norm(r.get("lane_Brand"))
        if b in brand_rows:
            deps.append(brand_rows[b])
        state[key] = {c: eff(src_id, c) for c in CATALOG_COLS}
        state[key].update({c: "" for c in COPY_DROPS})
        copies[n] = (key, src_id, emit("COPY", n, key, "_copy", src_id, name, "ui_copy", deps, "active"))
    # 6 ALIGN ------------------------------------------------------------------------------------------------
    # R68: the line index over the freeze AS THIS PLAN LEAVES IT - every active item plus every planned un-retire, each
    # with its planned cells (an un-retired member reads its planned tag), dead records out (pl_index).
    line_idx = None
    if pl_key_fn is not None:
        live = [{c: eff(pid, c) for c in CATALOG_COLS} for pid in act]
        live += [{c: eff(pid, c) for c in CATALOG_COLS} for pid in ret if (state.get(pid) or {}).get("_state") == "active"]
        line_idx = pl_index(live, pl_key_fn, dead_tag)
    for n, r in creates:
        if n not in copies:
            continue
        key, src_id, cseq = copies[n]
        for col, field, channel, icol in ROUTES:
            if field == "Tags":
                tag = one_tag(n, r, "ALIGN", key)
                if tag is None:
                    continue
                line_cite = ""
                if line_idx is not None:
                    it = {c: eff(key, c) for c in CATALOG_COLS}
                    it["Master category"] = mc_of.get(norm(it.get("Category")), it.get("Master category", ""))
                    st = line_state(it, line_idx, pl_key_fn, discontinue_tag)
                    if st["state"] == "discontinued":
                        was = tag
                        if tag in (active_tag, new_line_tag):
                            tag = discontinue_tag
                        line_cite = (f"R68: line `{st['key']}` is discontinued (all {st['siblings']} active sibling(s) carry "
                                     f"`{discontinue_tag}`); the create takes `{tag}`"
                                     + (f", not `{was}`" if was != tag else ""))
                        notes.append(f"PL_DISCONTINUED_CREATE (R68, INFO) line {n} {(r.get('create_name_FINAL') or '').strip()!r}: "
                                     f"line is discontinued; the buy is a recorded exception - PO reason owed. "
                                     f"Line `{st['key']}`: all {st['siblings']} active sibling(s) carry `{discontinue_tag}`; "
                                     f"the create's decision tag is `{tag}`" + (f" (the intake row named `{was}`)" if was != tag else ""))
                bef = eff(src_id, "Tags")
                tgt = tag_target(bef, tag, prefix)
                if not same("Tags", bef, tgt):
                    emit("ALIGN", n, key, "Tags", bef, tgt, channel, [cseq], "active", line_cite)
                continue
            bef, _ = plan_value(field, eff(src_id, col))
            tgt, ok = plan_value(field, r.get(icol))
            if not ok:
                refuse("VALUE_NOT_NUMERIC", "ALIGN", n, key, field, channel, "", f"target {r.get(icol)!r}")
                continue
            dcell = intake_derive.parse_derived(r.get("derived"))
            if field == "Cost" and (n in sample_only or "COST_UNKNOWN" in (r.get("flags") or "").split(";"))                     and ("Cost" not in dcell or "COST_UNKNOWN" in (r.get("flags") or "").split(";")):
                refuse("COST_UNKNOWN", "ALIGN", n, key, field, channel, "",
                       f"R125: line `{sample_only.get(n, '')}` is sample-only - its Cost comes from the vendor's Apex PO or "
                       f"catalog listing (intake_apex_cost.py --apex) or the Operator's typed Cost (--cost), never the "
                       f"invoice's sample price {r.get('unit_cost')!r} and never the copy source's Cost {bef!r}")
                continue
            cite_extra = ""
            if field in DERIVED_FIELDS and DERIVED_FIELDS[field] in dcell:
                cite_extra = f"derived {DERIVED_FIELDS[field]} {dcell[DERIVED_FIELDS[field]]}"
                if field == "FlowerEquivalent" and fl_eq_classes is not None:
                    # Re-derive from the row's FINAL grams (unit mg: a THC class the intake derived had its mg).
                    dv = intake_derive.derive(r.get("lane_MasterCategory"), r.get("lane_ProductGrams"), "mg", None,
                                              fl_eq_classes, conc=intake_derive.conc_of(r.get("derived")),
                                              cat=r.get("lane_Category"))   # an enumerated Category exception wins (R6 R130)
                    rv = dv["values"].get("lane_FlowerEquiv")
                    if rv is not None and not same(field, plan_value(field, rv)[0], tgt):
                        cite_extra += (f"; re-derived from Product grams {r.get('lane_ProductGrams')!r}: {rv} "
                                       f"(row cell {r.get(icol)!r} superseded)")
                        tgt = plan_value(field, rv)[0]
            if not tgt:
                # A blank lane cell is not a planned clear, except three: a blank Cost / Price on a create is a STOP
                # item, a cross-brand copy's carried Flavor is cleared (the one grid field whose clear is proven), and
                # a DERIVED blank (R66 CBD content off the CBD master) over a source value is a clear the plan must
                # name - the channel refuses it (P7), which is the Operator's instruction to clear it by the form.
                if bef and field in MONEY:
                    refuse("TARGET_BLANK", "ALIGN", n, key, field, channel, "",
                           f"{col} is blank on the intake row: set it at the STOP (NEW_LINE_FIELDS)")
                elif bef and field == "Flavor" and "CROSS_BRAND_COPY" in (r.get("flags") or "").split(";"):
                    emit("ALIGN", n, key, field, bef, "", channel, [cseq], "active", "cross-brand residue clear")
                elif bef and cite_extra:
                    emit("ALIGN", n, key, field, bef, "", channel, [cseq], "active", cite_extra + ": the source's value must clear")
                continue
            if same(field, bef, tgt):
                continue
            deps = [cseq]
            if field == "StrainId":
                s = tgt[len("name:"):]
                if norm(s) in minted:
                    deps.append(minted[norm(s)])
                elif norm(s) not in strain_names:
                    refuse("STRAIN_UNKNOWN", "ALIGN", n, key, field, channel, "", f"{s!r} is not a Strain record and no mint is planned")
            if field == "BrandId":
                b = tgt[len("name:"):]
                if norm(b) in brand_rows:
                    deps.append(brand_rows[norm(b)])
                elif norm(b) not in brand_names:
                    refuse("BRAND_UNKNOWN", "ALIGN", n, key, field, channel, "", f"{b!r} has no Brand record and no create is planned")
            if field == "ProductCategoryId":
                bc, tc = bef[len("name:"):], tgt[len("name:"):]
                if norm(tc) not in mc_of:
                    refuse("CATEGORY_UNKNOWN", "ALIGN", n, key, field, channel, "", f"{tc!r} is not in the Categories freeze (NEW_CATEGORY is a STOP)")
                elif mc_of.get(norm(bc)) != mc_of.get(norm(tc)) and CROSS_MC[0] != PROVEN:
                    refuse("CHANNEL_UNPROVEN", "ALIGN", n, key, field, channel, CROSS_MC[1],
                           f"{CROSS_MC[2]}: {mc_of.get(norm(bc))!r} -> {mc_of.get(norm(tc))!r}")
            emit("ALIGN", n, key, field, bef, tgt, channel, deps, "active", cite_extra)
    # 7 CONTENT  8 IMAGE_REMOVE  9 LINK ------------------------------------------------------------------------
    later = []
    for n, r in creates:
        if n not in copies:
            continue
        key, src_id, cseq = copies[n]
        xb = "CROSS_BRAND_COPY" in (r.get("flags") or "").split(";")
        # `Copy online details` stays CHECKED on every copy (PROVEN, KB 'Item creation by Copy item' [PROBE
        # 2026-10-08]; it is a dialog setting, not a plan channel), so the copy carries its source's title and
        # description. A sibling copy keeps them (the line's template). A CROSS_BRAND_COPY REPLACES both with the
        # new brand's own words - never a blank clear - and its copied image is deleted (IMAGE_REMOVE).
        for fld, icol in (("Online title", "online_title"), ("Online description", "online_description")):
            bef, tgt = eff(src_id, fld), (r.get(icol) or "").strip()
            if tgt and tgt != bef.strip():
                emit("CONTENT", n, key, fld, bef, tgt, "item_form", [cseq], "active",
                     "replaces the source brand's words" if xb else "")
            elif xb and not tgt and bef.strip():
                refuse("CONTENT_UNWRITTEN", "CONTENT", n, key, fld, "item_form", "",
                       f"a CROSS_BRAND_COPY replaces the source brand's {fld} with the new brand's own words "
                       f"(`{icol}` on the intake row, set at the STOP); a blank clear is not the ruled path")
            elif not xb and fld == "Online description" and not tgt:
                peers = [x.get("Online description", "") for pid, x in act.items() if pid != src_id
                         and all(norm(x.get(c)) == norm(eff(src_id, c)) for c in ("Brand", "Category", "Product grams"))]
                own = sibling_own_text(bef, peers)
                if own:
                    refuse("DESC_UNSOURCED", "CONTENT", n, key, fld, "item_form", "",
                           f"the sibling's Online description carries {len(own)} chars its line does not share "
                           f"({own[:70]!r}...): the sibling's own strain paragraph. The lane sources this product's "
                           f"words (create step 1b: brand asset, brand site, other Dutchie menus) into "
                           f"`online_description` before the STOP; the copy never keeps another product's text")
                else:
                    notes.append(f"line {n}: the sibling's Online description is the line's shared template "
                                 f"(no text of its own); kept")
        later.append((n, r, key, src_id, cseq, xb))
    # Copy item duplicates EVERY source image row under new blob names (2026-10-13). A sibling copy: the product's own
    # art first (IMAGE_ADD), then the copied rows out; a cross-brand copy: the copied rows out (its art is step 5).
    adds = {}
    for n, r, key, src_id, cseq, xb in later:
        img = eff(src_id, "Image URL")
        if xb or not img.strip():
            continue
        if (r.get("image_keep") or "").strip().upper() == "Y":
            notes.append(f"line {n}: `image_keep = Y` - the Operator ruled the sibling's carried art generic brand art "
                         f"(KB 'Images': leave it); no image row is planned")
            continue
        adds[n] = emit("IMAGE_ADD", n, key, "_image_add", img, "own art: create step 5 sourcing", "image_add_form",
                       [cseq], "image_rows", "a sibling copy carries the sibling's own label art (KB 'Images': a defect); "
                       "the product's own art lands first, through the file input, with no form Save")
    for n, r, key, src_id, cseq, xb in later:
        img = eff(src_id, "Image URL")
        if img.strip() and (xb or n in adds):
            emit("IMAGE_REMOVE", n, key, "_images", img, "", "image_remove", [cseq] + ([adds[n]] if n in adds else []),
                 "image_rows", "every COPIED row (new blob names, no CatalogImageId): exactly the images[] ids the copy "
                 "read showed before the add; the add's own row stays")
    # Global link, ALWAYS ATTEMPTED (ruled 2026-10-13): the copy drops its source's link, so every create gets the best
    # guess (`no match` included); the business QCs it after, through the notice. A cross-brand copy never keeps the
    # source brand's record (its own brand's search).
    by_line = {}
    for c in link_search or []:
        by_line.setdefault(str(c.get("line_no") or "").strip(), []).append(c)
    for n, r, key, src_id, cseq, xb in later:
        cands = by_line.get(str(n), [])
        sibs = []
        if line_idx is not None:
            try:
                sibs = list(line_idx.get(pl_key_fn({c: eff(key, c) for c in CATALOG_COLS}), []))
            except Exception:  # noqa: BLE001 - a key the function cannot read gives no siblings, never an abort here
                sibs = []
        src = act.get(src_id)
        if not xb and src is not None:
            sibs.append(src)
        kind, rec, conf, why, nearest = link_decision(r, cands, catalog_state, link_templates(r, sibs))
        name = (r.get("create_name_FINAL") or "").strip()
        if kind == "refuse":
            refuse(rec, "LINK", n, key, "_global_link", "link_replay", "", conf)
            continue
        if kind == "link" and (not (rec.get("brand_id") or "").strip() or not (rec.get("brand_name") or "").strip()):
            refuse("LINK_BRAND_UNKNOWN", "LINK", n, key, "_global_link", "link_replay", "",
                   f"candidate {rec.get('id')} carries no brand id / name (batch-catalog-products on a sibling's "
                   f"BrandCatalogProductId gives them)")
            continue
        if kind == "link":
            emit("LINK", n, key, "_global_link", "", link_target(rec), "link_replay", [cseq], "link_null",
                 f"{conf}: {why}; link-catalog-product {{...ctx, BrandCatalogBrandId, BrandCatalogBrandName, "
                 f"BrandCatalogProductId, BrandCatalogProductVersion: 0, ProductId}}")
        notes.append(f"LINK_RESULT line {n} {name!r}: {link_result(kind, conf, rec, why, nearest)}")
        if not xb:
            # R111 rung (a): the lane copies the `rung (a)` record's description into `online_description` and this
            # text into `online_desc_source` (a NEW intake version) before the real plan; a `rung (b)` line goes on
            # to the brand's assets. A cross-brand copy writes the new brand's words (CONTENT) and is not read here.
            rid = (rec or {}).get("id", "") if kind == "link" else ""
            notes.append(f"OD_RUNG line {n} {name!r}: " + od_rung_a(r, kind, conf, rec or {},
                                                                     (catalog_records or {}).get(rid))[1])
    if any(r["step"] == "COPY" for r in rows):
        notes.append("COPY keeps `Copy online details` CHECKED on every copy, cross-brand included (PROVEN: KB 'Item "
                     "creation by Copy item' [PROBE 2026-10-08] - unchecked, the copy blanks the Online title, description "
                     "and Global Category / Sub yet still copies the image); Global Category / Sub carry from the source. "
                     "A cross-brand copy's title and description are REPLACED by its CONTENT rows (the new brand's words), "
                     "its copied images deleted by IMAGE_REMOVE after the item's last form Save (so no Save carries them "
                     "back); the new brand's image ADD is create step 5 after it. A sibling copy adds its own art "
                     "(IMAGE_ADD) and then removes the copied rows. The copy drops its source's global link: every "
                     "create gets its own best-guess LINK row, or a `no match` result")
    for r in rows:
        r["row_sha1"] = row_sha1(r)
    order = [STEPS.index(r["step"]) for r in rows]
    assert order == sorted(order), "plan rows out of step order"
    return rows, refusals, notes


def summary(rows, refusals, notes):
    out = ["## Plan - the writes this batch makes (R124)", ""]
    out.append(f"- {len(rows)} planned write(s); {len(refusals)} refusal(s)")
    for s in STEPS:
        n = [r for r in rows if r["step"] == s]
        if n:
            ch = {}
            for r in n:
                ch[r["channel"]] = ch.get(r["channel"], 0) + 1
            out.append(f"- {s}: {len(n)} - " + ", ".join(f"{c} {k}" for c, k in sorted(ch.items())))
    chs = {}
    for r in rows:
        chs[r["channel"]] = chs.get(r["channel"], 0) + 1
    out.append("- per channel: " + ", ".join(f"{c} {k}" for c, k in sorted(chs.items())))
    if refusals:
        out += ["", "## Refused - the plan is NOT written (each is a probe or a STOP, never an assumption)", "",
                "| # | Reason | Step | Line | Key | Field | Channel | Probe | Detail |", "|---|---|---|---|---|---|---|---|---|"]
        for i, f in enumerate(refusals, 1):
            out.append(f"| {i} | {f['reason']} | {f['step']} | {f['line_no']} | {f['product_key']} | {f['field']} | "
                       f"{f['channel']} | {f['probe'] or '-'} | {f['detail'].replace('|', '/')} |")
        probes = sorted({f["probe"] for f in refusals if f["probe"]})
        if probes:
            out.append(f"\nProbes that would clear the channel refusals: {', '.join(probes)}")
    links = [x for x in dict.fromkeys(notes) if x.startswith("LINK_RESULT")]
    if links:
        out += ["", "## Global link per create - the best guess (step 7 writes each value into `global_link_result`; "
                "a best guess or a no-match with candidates is a question for the business in the notice)", ""]
        out += [f"- {x}" for x in links]
    rest = [x for x in dict.fromkeys(notes) if not x.startswith("LINK_RESULT")]
    if rest:
        out += ["", "## Notes (not writes)", ""] + [f"- {x}" for x in rest]
    return out


def tenant_keys(argv):
    """(need, optional): the `## Intake Pointers` keys this runner reads (intake_pointers.load_for). `Intake dir` only
    when a plan is written (no --dry-run) and no --out-dir names the folder."""
    from intake_match import TENANT_OPTIONAL
    need = ["Intake dir"] if not get_flag(argv, "--out-dir") and "--dry-run" not in argv else []
    return need, TENANT_OPTIONAL + ["Catalog state"]


def main(argv):
    if "--selftest" in argv:
        return selftest()
    paths = {k: get_flag(argv, "--" + k) for k in ("intake", "active", "retired", "strains", "categories", "brands")}
    if not all(paths.values()):
        print(__doc__)
        return EXIT_ABORT
    intake = read_csv(paths["intake"], V3_COLS + ["unretire_set"], "--intake")[1]
    active = read_csv(paths["active"], CATALOG_REQUIRED_PLAN, "--active")[1]
    retired = read_csv(paths["retired"], CATALOG_REQUIRED_PLAN, "--retired")[1]
    strains = read_csv(paths["strains"], STRAINS_REQUIRED, "--strains")[1]
    categories = read_csv(paths["categories"], CATEGORIES_REQUIRED, "--categories")[1]
    brands = read_csv(paths["brands"], BRANDS_REQUIRED, "--brands")[1]
    tenant = get_flag(argv, "--tenant")
    ptr = None
    if tenant:
        import intake_pointers
        ptr = intake_pointers.load_for(tenant, *tenant_keys(argv))
    from intake_match import line_options, load_fl_eq_classes, tag_options
    new_line_tag, active_tag = tag_options(argv, ptr)
    discontinue_tag, pl_key_fn, pl_key_src = line_options(argv, ptr)
    print(f"R68 line state: PL key {pl_key_src}; discontinue tag `{discontinue_tag}`")
    sp = get_flag(argv, "--catalog-search")
    link_search = read_csv(sp, LINK_SEARCH_COLS, "--catalog-search")[1] if sp else None
    catalog_state = get_flag(argv, "--catalog-state") or ((ptr or {}).get("intake", {}).get("Catalog state"))
    if catalog_state and re.fullmatch(r"<[^>]*>", catalog_state.strip()):
        catalog_state = None
    print(f"Global link: search {'`' + os.path.basename(sp) + '`' if sp else 'NONE (every create refuses LINK_NOT_SEARCHED)'}; "
          f"catalog state {catalog_state or 'NONE (nothing is linked: every create with hits is a `no match` question)'}")
    cr = get_flag(argv, "--catalog-records")
    catalog_records = load_catalog_records(cr) if cr else None
    print(f"R111 rung (a): records {'`' + os.path.basename(cr) + '` (' + str(len(catalog_records)) + ')' if cr else 'NOT READ (every create reads rung (b))'}")
    rows, refusals, notes = build_plan(intake, active, retired, strains, categories, brands,
                                       fl_eq_classes=load_fl_eq_classes(argv, ptr), pl_key_fn=pl_key_fn,
                                       discontinue_tag=discontinue_tag, active_tag=active_tag, new_line_tag=new_line_tag,
                                       link_search=link_search, catalog_state=catalog_state, catalog_records=catalog_records)
    print("\n".join(summary(rows, refusals, notes)))
    if "--dry-run" in argv:
        print("\ndry run: nothing written")
        return EXIT_ABORT if refusals else EXIT_OK
    out_dir = get_flag(argv, "--out-dir")
    if not out_dir and ptr:
        out_dir = ptr["intake"]["Intake dir"]
    d_, stem = version_stem(paths["intake"])
    out_dir = out_dir or d_
    if refusals:
        p = new_path(out_dir, f"{stem}-plan-refusals-{stamp()}", ".csv")
        write_csv(p, REFUSAL_COLS, refusals)
        print(f"\nREFUSED: no plan written; refusals -> {p}")
        return EXIT_ABORT
    p = next_version(out_dir, f"{stem}-plan")
    write_csv(p, PLAN_COLS, rows)
    print(f"\nwrote {p} ({len(rows)} rows)")
    return EXIT_OK


# ---------------------------------------------------------------------------------------------------------
# selftest: synthetic records only (Brand A, Brand B, Strain X ...); no tenant, vendor or brand name.

SHA_VECTOR = ({"seq": "1", "step": "ALIGN", "line_no": "3", "product_key": "new:3", "field": "Price",
               "before": "20", "target": "18", "channel": "grid", "depends_on": "5",
               "provenance": "§2A row 10 · Brand A | Gummies"},
              "134d396126fcd0c7bc03b49d0da22069df4e16f3")   # the SAME vector is asserted in backoffice_grid_write_selftest.js


def _item(pid, name, **kw):
    r = {c: "" for c in CATALOG_COLS}
    r.update({"ProductId": pid, "SKU": "S" + pid, "Product": name, "Master category": "Pre-Roll",
              "Category": "Pre-Roll Single", "Flower equiv": "1g", "Product grams": "1g", "Brand": "Brand A",
              "Vendor": "Vendor Shared", "Cost": "4.5", "Price": "11", "Tags": "ITM - Active"})
    r.update(kw)
    return r


def _fixture():
    active = [_item("601", "Brand A | Pre-Roll | Strain X | 1g", Strain="Strain X", **{"Online title": "Strain X Pre-Roll 1g",
                                                                                         "Image URL": "a.jpg"}),
              _item("701", "Brand B | Gummies | Mango | 100mg", Brand="Brand B", Flavor="Mango", Category="Gummies",
                    **{"Master category": "Edible", "Online title": "Brand B Mango", "Image URL": "b.jpg",
                       "Online description": "Mango from Brand B.", "Brand catalog product": "B Mango", "Cost": "9",
                       "Price": "20"})]
    retired = [_item("401", "Brand A | Pre-Roll | Strain Z | 1g", Cost="4", Tags="ITM - Discontinue"),
               _item("402", "Brand A | Pre-Roll | Strain W | 1g", Cost="4", Tags="ITM - Discontinue, PKG - Deal"),
               _item("404", "DNU | Brand A | Pre-Roll | Strain X | 1g", Tags="ITM - Do Not Use")]
    strains = [{"Strain name": s, "Type": "Hybrid"} for s in ("Strain X", "Strain Z", "Strain W")]
    cats = [{"Master category": "Pre-Roll", "Category": "Pre-Roll Single"}, {"Master category": "Edible", "Category": "Gummies"},
            {"Master category": "Edible", "Category": "Chocolates"}, {"Master category": "Vape", "Category": "Cart"}]
    brands = [{"Display name": "Brand A"}, {"Display name": "Brand B"}]
    base = {c: "" for c in V3_COLS + ["unretire_set"]}
    intake = [dict(base, verdict="RETIRED_MATCH", approved="Y", unretire_set="401;402", lane_Cost="4.25", lane_Price="11",
                   tags="ITM - Active", copy_source_productid="401", lane_Brand="Brand A"),
              dict(base, verdict="NEW_ITEM_WITH_SIBLING", approved="Y", copy_source_productid="601", lane_Brand="Brand A",
                   create_name_FINAL="Brand A | Pre-Roll | Strain Q | 1g", strain="Strain Q", strain_type="Sativa",
                   online_title="Strain Q Pre-Roll 1g", tags="ITM - Active", lane_Cost="4.5", lane_Price="11",
                   lane_Category="Pre-Roll Single", lane_FlowerEquiv="1g", lane_ProductGrams="1g", lane_Vendor="Vendor Shared"),
              dict(base, verdict="NEW_PL", approved="Y", flags="NEW_LINE_FIELDS;CROSS_BRAND_COPY", copy_source_productid="701",
                   lane_Brand="Brand A", create_name_FINAL="Brand A | Gummies | Lime | 100mg", lane_Flavor="Lime",
                   online_title="Lime Gummies", tags="ITM - New PL", lane_Cost="8", lane_Price="18", lane_Category="Gummies",
                   lane_Vendor="Vendor Shared", online_description="Lime gummies from Brand A."),
              dict(base, verdict="EXISTS", approved="Y", copy_source_productid="601")]
    ls = {c: "" for c in LINK_SEARCH_COLS}
    link = [dict(ls, line_no="2", search_term="Strain", brand_id="b-1", brand_name="Brand A", id="g-q1",
                 name="Strain Q Pre-Roll 1g", state="ST", status="Active", size="1g", strain_type="Sativa", created="2026-01-02"),
            dict(ls, line_no="2", search_term="Strain", brand_id="b-1", brand_name="Brand A", id="g-q2",
                 name="Strain Q Pre-Roll 0.5g", state="ST", status="Active", size="0.5g", created="2026-01-03"),
            dict(ls, line_no="2", search_term="Strain", brand_id="b-1", brand_name="Brand A", id="g-q3",
                 name="Strain Q Pre-Roll 1g", state="OT", status="Active", size="1g", created="2026-01-04"),
            dict(ls, line_no="3", search_term="Lime", brand_id="b-1", brand_name="Brand A")]   # zero hits
    return dict(intake=intake, active=active, retired=retired, strains=strains, categories=cats, brands=brands,
                link_search=link)


def _probed():
    """The module's own guard map: probe P2 proved the retired guard read 2026-10-08."""
    return dict(GUARD)


def _unproven_retired():
    """The breaker: the guard map as it read BEFORE probe P2 (a simulation only)."""
    g = dict(GUARD)
    g["retired"] = (UNPROVEN, "P2", "SIMULATED pre-P2 (selftest only)")
    return g


def _build(fx=None, **kw):
    f = fx or _fixture()
    kw.setdefault("link_search", f["link_search"])
    kw.setdefault("catalog_state", "ST")
    return build_plan(f["intake"], f["active"], f["retired"], f["strains"], f["categories"], f["brands"], **kw)


def selftest():
    t = Selftest("intake_plan")
    rows, ref, notes = _build(guard=_probed())
    t.check("GREEN: the fixture plans with 0 refusals once the retired guard is proven", ref == [], str(ref))
    steps = [r["step"] for r in rows]
    t.check("steps run in the kickoff's order (MINT_STRAIN .. LINK), never interleaved",
            [STEPS.index(s) for s in steps] == sorted(STEPS.index(s) for s in steps))
    t.check("each step kind is planned: MINT_STRAIN, UNRETIRE_ALIGN, UNRETIRE, COPY, ALIGN, CONTENT, IMAGE_ADD, IMAGE_REMOVE, LINK",
            {"MINT_STRAIN", "UNRETIRE_ALIGN", "UNRETIRE", "COPY", "ALIGN", "CONTENT", "IMAGE_ADD", "IMAGE_REMOVE", "LINK"}
            <= set(steps),
            str(sorted(set(steps))))
    by = {(r["product_key"], r["field"]): r for r in rows}
    seq = {r["seq"]: r for r in rows}
    t.check("un-retire: Cost from the invoice on each lane member, the tag swapped to the ONE Active tag (PKG kept)",
            by[("401", "Cost")]["target"] == "4.25" and by[("402", "Tags")]["target"] == "PKG - Deal, ITM - Active",
            by.get(("402", "Tags"), {}).get("target", ""))
    t.check("un-retire: Price already current -> no Price write", ("401", "Price") not in by)
    u = by[("401", "_state")]
    t.check("UNRETIRE depends on that item's UNRETIRE_ALIGN rows",
            set(u["depends_on"].split(";")) == {by[("401", "Cost")]["seq"], by[("401", "Tags")]["seq"]}, u["depends_on"])
    t.check("the dead record (R81) is never in the un-retire set", not any(r["product_key"] == "404" for r in rows))
    st = by[("new:2", "StrainId")]
    t.check("a new strain is minted first and the copy's StrainId write depends on the mint and the COPY",
            seq[st["depends_on"].split(";")[0]]["step"] in ("MINT_STRAIN", "COPY")
            and {seq[d]["step"] for d in st["depends_on"].split(";")} == {"MINT_STRAIN", "COPY"}
            and st["target"] == "name:Strain Q" and st["before"] == "name:Strain X", str(st))
    t.check("a record-bound field is planned by NAME (`name:`), never an invented id",
            by[("new:3", "BrandId")]["target"] == "name:Brand A")
    t.check("cross-brand: title and description REPLACED by the new brand's words, copied images removed, no own-art add "
            "before it (step 5 follows), no unlink (the copy drops the source's link)",
            by[("new:3", "Online description")]["target"] == "Lime gummies from Brand A."
            and by[("new:3", "Online title")]["target"] == "Lime Gummies"
            and ("new:3", "_images") in by and ("new:3", "_image_add") not in by
            and by[("new:3", "_images")]["channel"] == "image_remove")
    t.check("the sibling copy plans no description clear", ("new:2", "Online description") not in by)
    # --- a sibling's own strain paragraph is never kept (2026-10-23: three copies kept another strain's text) ---
    tmpl = " Brand A pre-rolls are hand-rolled from whole flower and finished by hand."
    fd = _fixture()
    fd["active"][0]["Online description"] = "Strain X: piney and sweet, with a long earthy finish." + tmpl
    fd["active"].append(_item("602", "Brand A | Pre-Roll | Strain Y | 1g", Strain="Strain Y",
                              **{"Online description": "Strain Y: bright citrus over a soft floral middle." + tmpl}))
    _, rd, _ = _build(fd, guard=_probed())
    t.check("FIRES DESC_UNSOURCED: a sibling copy with no `online_description` whose source carries text its line "
            "does not share (its own strain paragraph)",
            [x["reason"] for x in rd] == ["DESC_UNSOURCED"] and rd[0]["product_key"] == "new:2", str(rd))
    fd["intake"][1]["online_description"] = "Strain Q: sharp lemon zest and pine." + tmpl
    rq, rd2, _ = _build(fd, guard=_probed())
    bq = {(r["product_key"], r["field"]): r for r in rq}
    t.check("quiet once sourced: `online_description` set -> a CONTENT row writes the product's own words",
            rd2 == [] and bq[("new:2", "Online description")]["target"].startswith("Strain Q:"), str(rd2))
    fg = _fixture()
    fg["active"][0]["Online description"] = "Every Brand A pre-roll is hand-rolled from whole flower."
    fg["active"].append(_item("602", "Brand A | Pre-Roll | Strain Y | 1g", Strain="Strain Y",
                              **{"Online description": "Every Brand A pre-roll is hand-rolled\nfrom whole flower."}))
    _, rg, ng = _build(fg, guard=_probed())
    t.check("quiet on a shared template: the line's members carry the same text (line breaks ignored) -> kept, noted",
            rg == [] and any("shared template" in x for x in ng), str(rg))
    t.check("sibling_own_text: no peer -> the whole text is own; a peer with the same tail -> only the head",
            sibling_own_text("A" * 50, []) == "A" * 50
            and sibling_own_text("Head text that is specific to one strain here." + tmpl,
                                 ["Other head for another strain entirely." + tmpl]).startswith("Head text"))
    # --- images: Copy item duplicates every source image row; a sibling copy carries the sibling's label art ---
    ia, ir = by.get(("new:2", "_image_add")), by.get(("new:2", "_images"))
    t.check("IMAGES sibling: own art added FIRST (file input, no form Save), then the copied rows removed, the remove "
            "depending on the add and guarded on the exact images[] id list",
            ia is not None and ir is not None and ia["step"] == "IMAGE_ADD" and ia["channel"] == "image_add_form"
            and ia["seq"] in ir["depends_on"].split(";") and int(ia["seq"]) < int(ir["seq"])
            and "images[] ids" in ir["provenance"] and "ProductImageId" in ir["provenance"], f"{ia} {ir}")
    fk = _fixture()
    fk["intake"][1]["image_keep"] = "Y"
    rk, _, nk = _build(fk, guard=_probed())
    t.check("IMAGES breaker: `image_keep = Y` (generic brand art, KB 'Images') plans no sibling image row and says so",
            not any(r["product_key"] == "new:2" and r["step"].startswith("IMAGE") for r in rk)
            and any("image_keep = Y" in x for x in nk), str(nk))
    fi = _fixture()
    fi["active"][0]["Image URL"] = ""
    ri, _, _ = _build(fi, guard=_probed())
    t.check("IMAGES QUIET: a sibling source with no image plans no image row",
            not any(r["product_key"] == "new:2" and r["step"].startswith("IMAGE") for r in ri))
    # --- global link, ALWAYS ATTEMPTED, a BEST GUESS the business QCs after (ruled 2026-10-13) ---
    lk = by.get(("new:2", "_global_link"))
    t.check("LINK exact: the ONE exact-name Active in-state record is planned, guarded on a null link, its call ids in "
            "the target and the record name last (the export prints it)",
            lk is not None and lk["before"] == "" and lk["target"] == "id=g-q1;brand_id=b-1;brand_name=Brand A;name=Strain Q Pre-Roll 1g"
            and link_name(lk["target"]) == "Strain Q Pre-Roll 1g" and "; exact: exact name via our online_title;" in lk["provenance"]
            and "BrandCatalogProductVersion: 0" in lk["provenance"] and lk["depends_on"] == by[("new:2", "_copy")]["seq"], str(lk))
    t.check("LINK: every create prints its `global_link_result` in the summary (an exact link asks nothing; zero hits = "
            "`no record`, no row, no refusal)",
            ("new:3", "_global_link") not in by
            and any(x.startswith("LINK_RESULT line 2") and ": linked: g-q1 | Strain Q Pre-Roll 1g - exact" in x
                    and "please confirm" not in x for x in notes)
            and any(x.startswith("LINK_RESULT line 3") and ": no record: zero hits for 'Lime'" in x for x in notes)
            and "## Global link per create" in "\n".join(summary(rows, ref, notes)), str(notes))
    ls = {c: "" for c in LINK_SEARCH_COLS}

    def cand(i, name, **kw):
        return dict(dict(ls, line_no="2", search_term="Strain", brand_id="b-1", brand_name="Brand A", id=f"g-{i}", name=name,
                         state="ST", status="Active", size="1g", created=f"2026-01-0{i}"), **kw)

    def link_case(cands=None, edit=None, **kw):
        f = _fixture()
        if cands is not None:
            f["link_search"] = cands + [c for c in f["link_search"] if c["line_no"] != "2"]
        if edit:
            edit(f)
        rw, rf, nt = _build(f, guard=_probed(), **kw)
        res = next((x.split(": ", 1)[1] for x in nt if x.startswith("LINK_RESULT line 2")), "")
        return ({(r["product_key"], r["field"]): r for r in rw}.get(("new:2", "_global_link")), [x["reason"] for x in rf], res)
    # the PL's naming: the linked sibling 601 (Strain X) is `Brand A Strain X Joint 1g` in the GBC - ours translates to it
    gbc = [cand(1, "Brand A Strain Q Joint 1g"), cand(2, "Brand A Strain Q Joint 0.5g", **{"size": "0.5g"})]
    sib = lambda f: f["active"][0].update(**{"Brand catalog product": "Brand A Strain X Joint 1g"})  # noqa: E731
    lr, rf_, res = link_case(gbc, sib)
    t.check("LINK PL naming: a linked sibling's record name, its strain swapped for ours, finds the GBC name none of our "
            "own names match - an exact link",
            lr is not None and lr["target"].startswith("id=g-1;") and res.startswith("linked: g-1")
            and "the PL's naming: sibling 601" in res, f"{lr} {res}")
    lr, rf_, res = link_case(gbc)
    t.check("LINK PL naming breaker: with the sibling unlinked the same record is only a BEST GUESS (closest name) - linked, "
            "and the business is asked to confirm",
            lr is not None and lr["target"].startswith("id=g-1;") and res.startswith("best guess: g-1")
            and "please confirm" in res, res)
    for label, cands, edit, want in (
            ("a near name that prints our strain word", [cand(1, "Strain Q PR 1g")], None, "best guess: g-1"),
            ("several records share the exact name (a GBC duplicate)",
             [cand(1, "Strain Q Pre-Roll 1g"), cand(2, "Strain Q Pre-Roll 1g")], None, "best guess: g-1"),
            ("the exact name, but its strain type disagrees", [cand(1, "Strain Q Pre-Roll 1g", strain_type="Indica")], None,
             "best guess: g-1"),
            ("the exact name, but its subcategory is not ours", [cand(1, "Strain Q Pre-Roll 1g", subcategory="infused")],
             lambda f: f["intake"][1].update(lane_GlobalSubCategory="singles"), "best guess: g-1"),
            ("hits that never print our strain word", [cand(1, "Strain Z Pre-Roll 1g")], None, "no match: no Active ST record names 'Strain Q'"),
            ("a tie between two names equally close", [cand(1, "Strain Q Pre-Roll 1g Jar"), cand(2, "Strain Q Pre-Roll 1g Tin")],
             None, "no match: a tie"),
            ("the only name match is another size", [cand(1, "Strain Q Pre-Roll 1g", size="2g")], None, "no match: every Active ST hit is another size"),
            ("the only name match is archived", [cand(1, "Strain Q Pre-Roll 1g", status="Archived")], None, "no match: no hit is Active in ST"),
            ("the only name match is in another state", [cand(1, "Strain Q Pre-Roll 1g", state="OT")], None, "no match: no hit is Active in ST"),
            ("the brand has no GBC entries", [dict(ls, line_no="2", search_term="Strain")], None,
             "no record: the brand has no global catalog brand")):
        lr, rf_, res = link_case(cands, edit)
        linked = want.startswith("best guess")
        t.check(f"LINK {'BEST GUESS' if linked else 'NO MATCH'}: {label}",
                not rf_ and res.startswith(want) and (lr is not None) == linked
                and (("please confirm" in res) == linked), f"{lr} {rf_} {res}")
    lr, rf_, res = link_case(catalog_state=None)
    t.check("LINK NO MATCH: no catalog state named - nothing is linked, the hits are listed for the business",
            lr is None and res.startswith("no match: no catalog state") and "nearest: g-q" in res, res)
    lr, rf_, _ = link_case(link_search=None)
    # --- R111 rung (a): the exact-linked record's description, only when every stated fact agrees (K3, 2026-10-25) ---
    gq1 = {"id": "g-q1", "attributes": {"id": "g-q1", "name": "Strain Q Pre-Roll 1g", "category": "Pre-Rolls",
                                        "subcategory": "singles", "options": ["1g"], "weightGrams": 7,
                                        "description": "Strain Q, a bright sativa pre-roll."}}
    oda = lambda recs: [x for x in _build(catalog_records=recs, guard=_probed())[2] if x.startswith("OD_RUNG line 2")]  # noqa: E731
    o = oda({"g-q1": gq1["attributes"]})
    t.check("OD RUNG (a) FIRES: an exact link whose record states agreeing facts (weight 1g; the strain word in its name; "
            "`weightGrams` is never read) gives rung (a)",
            len(o) == 1 and ": rung (a): GBC record g-q1 | Strain Q Pre-Roll 1g - every stated fact agrees" in o[0]
            and "weight [1.0]g" in o[0], str(o))
    o = oda({"g-q1": dict(gq1["attributes"], options=["0.5g"])})
    t.check("OD RUNG (a) QUIET: the same record stating another weight falls to rung (b), naming the fact",
            len(o) == 1 and ": rung (b): record g-q1 disagrees: weight [0.5]g vs ours 1g" in o[0], str(o))
    o = oda(None)
    t.check("OD RUNG (a) QUIET: an exact link whose record was not read falls to rung (b)",
            len(o) == 1 and "rung (b): record g-q1 was not read" in o[0], str(o))
    r2 = _fixture()["intake"][1]
    f_, why_ = od_rung_a(r2, "link", "best guess", {"id": "g-q1"}, gq1)
    t.check("OD RUNG (a) QUIET: a BEST GUESS link with the same agreeing record falls to rung (b) (R98 gate not passed)",
            not f_ and why_.startswith("rung (b): the link is a best guess"), why_)
    gum = dict(r2, create_name_FINAL="Brand A | Gummies | Lime | 10mg x 10pk", strain="", lane_Flavor="Lime",
               lane_ProductGrams="", lane_GlobalCategory="Edible")
    rec_g = {"name": "Lime Gummies 10pk 100mg", "category": "Edible", "description": "Lime.",
             "thcContent": {"unit": "MILLIGRAMS", "range": [100]}, "suggestedPackSize": 10}
    f1, w1 = od_rung_a(gum, "link", "exact", {"id": "g-l"}, rec_g)
    f2, w2 = od_rung_a(gum, "link", "exact", {"id": "g-l"}, dict(rec_g, thcContent={"unit": "MILLIGRAMS", "range": [200]}))
    t.check("OD RUNG (a): dose and pack are read from our name's `N mg x M pk` (100 mg, 10 pk = the record) - a 200 mg "
            "record falls to rung (b)",
            f1 and "dose 100mg" in w1 and "pack 10" in w1 and not f2 and "dose 200mg vs ours 100mg" in w2, f"{w1} || {w2}")
    t.check("LINK FIRES: a create with no search refuses LINK_NOT_SEARCHED (the lane searches before it asks)",
            lr is None and rf_.count("LINK_NOT_SEARCHED") == 2, str(rf_))
    lr, rf_, res = link_case(None, lambda f: (f["link_search"][2].update(state="ST"), f["intake"][1].update(global_link_pick="g-q3")))
    t.check("LINK: the Operator's pick at the STOP overrides the guess", lr is not None and lr["target"].startswith("id=g-q3;")
            and res.startswith("linked: g-q3") and "Operator's pick" in res, res)
    lr, rf_, res = link_case(None, lambda f: f["intake"][1].update(global_link_pick="none"))
    t.check("LINK: the Operator's `none` - no row, no refusal", lr is None and not rf_ and res.startswith("none:"), f"{rf_} {res}")
    lr, rf_, _ = link_case(None, lambda f: f["intake"][1].update(global_link_pick="g-zz"))
    t.check("LINK FIRES: a pick that is not a listed candidate refuses LINK_PICK_UNKNOWN", rf_ == ["LINK_PICK_UNKNOWN"], str(rf_))
    lr, rf_, _ = link_case(None, lambda f: f["link_search"][0].update(brand_id=""))
    t.check("LINK FIRES: the record with no brand id refuses LINK_BRAND_UNKNOWN", rf_ == ["LINK_BRAND_UNKNOWN"], str(rf_))
    t.check("an EXISTS row plans no write", not any(r["line_no"] == "4" for r in rows))
    # --- R68 (amended 2026-10-11): the create re-reads its PRODUCT LINE on the freeze as the plan leaves it ---
    t.check("R68 QUIET on the base fixture: no line is wholly discontinued, no PL_DISCONTINUED_CREATE",
            not any("PL_DISCONTINUED_CREATE" in x for x in notes))

    def r68(active_tags, drop_unretire=True, intake_tag="ITM - Active", **kw):
        fx = _fixture()
        if drop_unretire:
            fx["intake"] = fx["intake"][1:]          # line 1 then is the sibling copy (no un-retire in the batch)
            fx["link_search"] = [dict(c, line_no=str(int(c["line_no"]) - 1)) for c in fx["link_search"]]
        fx["intake"][0]["tags"] = intake_tag
        fx["active"] = [dict(a, Tags=active_tags[i]) if i < len(active_tags) else a for i, a in enumerate(fx["active"])]
        fx["active"] += [_item(str(610 + i), f"Brand A | Pre-Roll | Strain S{i} | 1g", Tags=tg)
                         for i, tg in enumerate(active_tags[2:])]
        out = _build(fx, guard=_probed(), **kw)
        k = "new:1" if drop_unretire else "new:2"
        return out, {(r["product_key"], r["field"]): r for r in out[0]}.get((k, "Tags")), k
    (rw, rf, nt), tg, _ = r68(["ITM - Discontinue", "ITM - Active", "ITM - Discontinue"])
    t.check("R68 FIRES: every active sibling of the copy's line carries the discontinue tag -> the create takes it, "
            "no Tags write (the copy inherits it), PL_DISCONTINUED_CREATE printed with the owed PO reason",
            rf == [] and tg is None and any(x.startswith("PL_DISCONTINUED_CREATE (R68, INFO) line 1")
                                            and "the buy is a recorded exception - PO reason owed" in x
                                            and "(the intake row named `ITM - Active`)" in x for x in nt), str(nt))
    (rw, rf, nt), tg, _ = r68(["ITM - Discontinue", "ITM - Active", "ITM - Discontinue"], pl_key_fn=None)
    t.check("R68 breaker: the line read off, the same plan writes the stale Active tag over the copy's inherited one",
            tg is not None and tg["target"] == "ITM - Active" and not any("PL_DISCONTINUED_CREATE" in x for x in nt), str(tg))
    (rw, rf, nt), tg, _ = r68(["ITM - Active", "ITM - Active", "ITM - Discontinue"], intake_tag="ITM - Active")
    t.check("R68 QUIET: a MIXED line (one sibling tagged) prints nothing; the create keeps the Active tag",
            tg is None and not any("PL_DISCONTINUED_CREATE" in x for x in nt), str(nt))
    (rw, rf, nt), tg, _ = r68(["ITM - Active", "ITM - Active"])
    t.check("R68 QUIET: an UNTAGGED line prints nothing", not any("PL_DISCONTINUED_CREATE" in x for x in nt))
    (rw, rf, nt), tg, _ = r68(["ITM - Discontinue", "ITM - Active", "ITM - Discontinue"], intake_tag="ITM - Protect")
    t.check("R68: `ITM - Protect` (the deliberate keep, R48) stands - the Tags write targets it; the line is still printed",
            tg is not None and tg["target"] == "ITM - Protect" and "R68: line" in tg["provenance"]
            and any("PL_DISCONTINUED_CREATE" in x for x in nt), str(tg))
    (rw, rf, nt), tg, k = r68(["ITM - Discontinue", "ITM - Active"], drop_unretire=False)
    t.check("R68 QUIET: this plan's un-retires count as ACTIVE siblings (they come back on the Active tag): the line is mixed",
            not any("PL_DISCONTINUED_CREATE" in x for x in nt), str(nt))
    t.check("R68 QUIET: a NEW line (no sibling under its key) prints nothing - the cross-brand NEW_PL keeps the new-line tag",
            not any("line 3" in x and "PL_DISCONTINUED_CREATE" in x for x in nt)
            and any(r["product_key"] == "new:3" and r["field"] == "Tags" and "ITM - New PL" in r["target"] for r in rw))
    t.check("every row carries its provenance cite and a 40-hex row_sha1",
            all(r["provenance"] and re.fullmatch(r"[0-9a-f]{40}", r["row_sha1"]) for r in rows))
    # --- derived fields (R1-R3, R6, R34, R66): the cite rides the plan row; Flower equiv re-derives from the final grams
    classes = {"edible": "thc_g_x56", "pre-roll": "product_g_x1", "vape": "product_g_x5.6"}
    fd = _fixture()
    fd["intake"][2].update(lane_MasterCategory="Edible", lane_ProductGrams="0.1g", lane_FlowerEquiv="5.6g", lane_ServingsPerUnit="10",
                           derived="Flower equiv: 5.6g (R3 R5: thc_g_x56, THC 0.1g); Servings per Unit: 10 (R34: the pack count the line prints); "
                                   "CBD content: blank (R66: Master category is not CBD); Dose: 10mg x 10pk (R7 R42 R34)")
    fd["active"][1].update(**{"Flower equiv": "0.1g", "Servings per Unit": "1"})
    rows_d, ref_d, _ = _build(fd, guard=_probed(), fl_eq_classes=classes)
    byf = {(r["product_key"], r["field"]): r for r in rows_d}
    fe = byf.get(("new:3", "FlowerEquivalent"))
    t.check("a derived Flower equiv plans with its rule cite in the provenance",
            ref_d == [] and fe is not None and fe["target"] == "5.6" and "derived Flower equiv 5.6g (R3 R5" in fe["provenance"],
            f"{ref_d} {fe}")
    t.check("a derived Servings per Unit cites R34 in the provenance",
            "R34" in byf[("new:3", "ServingSizePerUnit")]["provenance"] and byf[("new:3", "ServingSizePerUnit")]["target"] == "10")
    fd["intake"][2]["derived"] = ("Product grams: 0.1g (R129: package total: a per-piece read would be 900 mg over the Edible 100 mg package cap (R130); 10 mg x 10); "
                                  + fd["intake"][2]["derived"])
    rows_g, _, _ = _build(fd, guard=_probed(), fl_eq_classes=classes)
    gr = next((r for r in rows_g if r["product_key"] == "new:3" and r["field"] == "Grams"), None)
    t.check("the Grams row carries the vendor dose read with its cite, naming the Master category and its cap (R129, R130)",
            gr is not None and gr["target"] == "0.1" and "derived Product grams 0.1g (R129: package total" in gr["provenance"]
            and "Edible 100 mg package cap (R130)" in gr["provenance"], str(gr))
    fd["intake"][2]["lane_ProductGrams"] = "0.05g"   # the Operator corrected the grams at the stop; FE cell is stale
    rows_d, ref_d, _ = _build(fd, guard=_probed(), fl_eq_classes=classes)
    fe = next(r for r in rows_d if r["product_key"] == "new:3" and r["field"] == "FlowerEquivalent")
    t.check("FIRES: a grams correction at the stop re-derives Flower equiv (0.05 x 56 = 2.8), superseding the stale cell",
            fe["target"] == "2.8" and "re-derived from Product grams '0.05g': 2.8g (row cell '5.6g' superseded)" in fe["provenance"], str(fe))
    rows_n, _, _ = _build(fd, guard=_probed())
    fe = next(r for r in rows_n if r["product_key"] == "new:3" and r["field"] == "FlowerEquivalent")
    t.check("QUIET: with no class map the row cell stands and the cite still rides", fe["target"] == "5.6" and "derived Flower equiv" in fe["provenance"])
    fd["active"][1]["CBD content"] = "25"   # a cross-brand source carrying CBD content; R66 derives blank off the CBD master
    rows_c, ref_c, _ = _build(fd, guard=_probed(), fl_eq_classes=classes)
    t.check("FIRES: a derived-blank CBD content over a source value plans the clear, which the grid refuses (P7) - the Operator clears it by the form",
            any(f["reason"] == "CHANNEL_UNPROVEN" and f["field"] == "CBDContent" and f["probe"] == "P7" for f in ref_c), str(ref_c))
    fd["intake"][2]["derived"] = ""
    rows_c, ref_c, _ = _build(fd, guard=_probed(), fl_eq_classes=classes)
    t.check("QUIET: with no derivation on the row, a blank CBD content is not a planned clear",
            not any(f["field"] == "CBDContent" for f in ref_c), str(ref_c))
    v, h = SHA_VECTOR
    got = row_sha1(v)
    t.check("row_sha1 = sha1 of the ten cells joined by U+001F (the vector gridBatch's selftest also checks)",
            got == hashlib.sha1(SEP.join(v[c] for c in HASH_COLS).encode("utf-8")).hexdigest() and got == h, got)
    # --- refusals: each must FIRE on its breaker -------------------------------------------------------------
    _, refm, _ = _build()
    t.check("GREEN: the module's OWN map plans the fixture with 0 refusals (P2 proved the retired guard 2026-10-08)",
            refm == [], str(refm[:2]))
    t.check("un-retire runs on the bulk-unretire mutation (P3) and the tag on the grid (P4, REPLACE), not the form",
            u["channel"] == "grid_bulk_unretire" and by[("402", "Tags")]["channel"] == "grid"
            and by[("402", "Tags")]["before"] == "ITM - Discontinue, PKG - Deal", str((u["channel"], by[("402", "Tags")])))
    _, ref0, _ = _build(guard=_unproven_retired())
    t.check("FIRES: with the retired guard UNPROVEN (pre-P2 breaker), every write on a RETIRED item is refused",
            ref0 and all(f["reason"] == "GUARD_UNPROVEN" and f["probe"] == "P2" for f in ref0)
            and {f["step"] for f in ref0} == {"UNRETIRE_ALIGN", "UNRETIRE"}, str(ref0[:2]))
    f1 = _fixture()
    f1["intake"][2]["lane_Vendor"] = "Vendor Other"
    rows1, r1, _ = _build(f1, guard=_probed())
    t.check("QUIET: a VendorId write plans by NAME (P7 proved it 2026-10-08)",
            r1 == [] and any(r["field"] == "VendorId" and r["target"] == "name:Vendor Other" for r in rows1), str(r1))
    f1b = _fixture()
    f1b["intake"][2]["lane_CBDContent"] = "5"
    _, r1b, _ = _build(f1b, guard=_probed())
    t.check("FIRES: a CBDContent write is refused (CHANNEL_UNPROVEN: P7 REFUSED, no restorable target)",
            any(f["reason"] == "CHANNEL_UNPROVEN" and f["field"] == "CBDContent" and f["probe"] == "P7" for f in r1b), str(r1b))
    f2 = _fixture()
    f2["intake"][2]["lane_Category"] = "Cart"
    rows2, r2, _ = _build(f2, guard=_probed())
    t.check("a cross-MC ProductCategoryId move plans (P6) and the certify declares Master category derived",
            r2 == [] and any(r["field"] == "ProductCategoryId" and r["target"] == "name:Cart" for r in rows2)
            and "Master category" in DERIVES.get("ProductCategoryId", []), str(r2))
    f2c = _fixture()
    f2c["intake"][2]["lane_Category"] = "Tincture Drops"
    _, r2c, _ = _build(f2c, guard=_probed())
    t.check("FIRES: a Category absent from the taxonomy is refused (NEW_CATEGORY is a STOP)",
            any(f["reason"] == "CATEGORY_UNKNOWN" for f in r2c), str(r2c))
    f2b = _fixture()
    f2b["intake"][2]["lane_Category"] = "Chocolates"
    rows2b, r2b, _ = _build(f2b, guard=_probed())
    t.check("QUIET: a same-MC Category move plans", r2b == [] and any(r["field"] == "ProductCategoryId" for r in rows2b), str(r2b))
    f3 = _fixture()
    f3["intake"][1]["copy_source_productid"] = "404"
    _, r3, _ = _build(f3, guard=_probed())
    t.check("FIRES: a dead R81 record is never a copy source (DEAD_SOURCE)", any(f["reason"] == "DEAD_SOURCE" for f in r3), str(r3))
    f4 = _fixture()
    f4["intake"][0]["unretire_set"] = "401;404"
    _, r4, _ = _build(f4, guard=_probed())
    t.check("FIRES: a dead R81 record in an un-retire set is refused (DEAD_RECORD)", any(f["reason"] == "DEAD_RECORD" for f in r4))
    f5 = _fixture()
    f5["intake"].append(dict(f5["intake"][2], verdict="NEW_BRAND", lane_Brand="Brand C",
                             create_name_FINAL="Brand C | Gummies | Lime | 100mg"))
    rows5, r5, _ = _build(f5, guard=_probed())
    s5 = {r["seq"]: r for r in rows5}
    b5 = next((r for r in rows5 if r["field"] == "BrandId" and r["target"] == "name:Brand C"), None)
    t.check("FIRES: a Brand record create is refused (P5) and its copy's BrandId depends on it",
            any(f["reason"] == "CHANNEL_UNPROVEN" and f["probe"] == "P5" for f in r5) and b5 is not None
            and "CREATE_BRAND" in {s5[d]["step"] for d in b5["depends_on"].split(";")}, str(r5))
    f6 = _fixture()
    f6["intake"][2]["create_name_FINAL"] = "Brand A | Pre-Roll | Strain Q | 1g"
    _, r6, _ = _build(f6, guard=_probed())
    t.check("FIRES: two creates planned under one name (certify could not tell them apart)",
            any(f["reason"] == "DUP_NAME_PLANNED" for f in r6))
    f7 = _fixture()
    f7["intake"][2]["lane_Price"] = ""
    _, r7, _ = _build(f7, guard=_probed())
    t.check("FIRES: a blank Price on a create is a STOP item, never a planned clear", any(f["reason"] == "TARGET_BLANK" for f in r7))
    f8 = _fixture()
    f8["intake"][1]["tags"] = "ITM - Active, ITM - Protect"
    _, r8, _ = _build(f8, guard=_probed())
    t.check("FIRES: two decision tags on one row (R96 exactly one)", any(f["reason"] == "TAG_NOT_ONE" for f in r8))
    f9 = _fixture()
    f9["intake"][2]["lane_Cost"] = "$eight"
    _, r9, _ = _build(f9, guard=_probed())
    t.check("FIRES: a number field that will not cast (it would post as null)", any(f["reason"] == "VALUE_NOT_NUMERIC" for f in r9))
    f10 = _fixture()
    f10["intake"][1]["strain_type"] = ""
    _, r10, _ = _build(f10, guard=_probed())
    t.check("FIRES: a strain mint with no Type", any(f["reason"] == "STRAIN_TYPE_UNKNOWN" for f in r10))
    f11 = _fixture()
    f11["intake"].append(dict(f11["intake"][0], verdict="STRAIN_MISSING"))
    _, r11, _ = _build(f11, guard=_probed())
    t.check("FIRES: an approved verdict this lane never writes (STRAIN_MISSING)", any(f["reason"] == "NOT_PLANNABLE" for f in r11))
    f12 = _fixture()
    f12["intake"][2]["online_description"] = ""
    rows12, r12, _ = _build(f12, guard=_probed())
    t.check("FIRES: a cross-brand copy with no new-brand description is refused, never planned as a blank clear",
            [f["reason"] for f in r12] == ["CONTENT_UNWRITTEN"] and r12[0]["field"] == "Online description"
            and not any(r["field"] == "Online description" and r["product_key"] == "new:3" for r in rows12), str(r12))
    t.check("the COPY note says `Copy online details` stays CHECKED (PROVEN, a dialog setting, not a channel)",
            any("CHECKED on every copy" in x and "PROVEN" in x for x in notes))
    out = "\n".join(summary(rows, ref0, notes))
    t.check("the summary prints writes per step and per channel, and names the probes that clear the refusals",
            "- UNRETIRE_ALIGN:" in out and "per channel:" in out and "P2" in out)
    return t.done()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
