"""intake_plan.py - the ONE plan file an intake write batch runs from (R124). No login, no write.

  python intake_plan.py --intake <intake-vN.csv> --active <f> --retired <f> --strains <f>
                        --categories <f> --brands <f> [--out-dir <dir> | --tenant <CLAUDE.md>] [--dry-run]
                        [--fl-eq-classes <toml>]   (default: the tenant pointer `FL EQ classes:`)
  python intake_plan.py --selftest

R124: the Operator approves one plan file that names every write - item, field, before-value, target. The
lane runs it as one paced batch (a live guard read per write, no per-item read-back) and proves it ONCE, at
the end, with `intake_certify.py --plan` on fresh Active + Retired exports. This script builds that file.

Input: the approved intake vN (rows with `approved = Y`) and the PRE-BATCH FREEZE - the Catalog Active and
Retired exports (both with `ProductId`), Strains, Categories, Brands. Every column read is required (ABORT).
Output: a NEW `<stem>-plan-vN.csv`, one row per write:

  seq, step, line_no, product_key, field, before, target, channel, depends_on, provenance, row_sha1

  step         in this order (R124, the kickoff's work item B): MINT_STRAIN, CREATE_BRAND, UNRETIRE_ALIGN,
               UNRETIRE, COPY, ALIGN, CONTENT, IMAGE_REMOVE, LINK. Order is the dependency.
  line_no      the intake row's 1-based position in the intake CSV.
  product_key  a ProductId; `new:<line_no>` for an item the COPY step creates; `strain:<name>` / `brand:<name>`
               for a record mint.
  field        the INTERNAL grid name (`Cost`, `StrainId`, ...) on the `grid` channel; the form control's
               label (`Tags`, `Online title`, `Online description`) on `item_form`; a synthetic name starting
               `_` for a write with no item field (`_state`, `_copy`, `_strain`, `_brand`, `_images`, `_global_link`).
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

Derived fields (intake_derive.py; the intake row's `derived` cell, v6). A create row's Flower equiv, Servings per
Unit and CBD content that the lane DERIVED carry their rule cite into the plan row's provenance. Flower equiv is
RE-DERIVED here from the row's FINAL Product grams and Master category (the class map), so a grams correction at
the stop moves it; a row cell that disagrees is superseded and the provenance says so. A derived-blank CBD content
over a source value plans the clear - which the grid refuses (CBDContent UNPROVEN, P7): the refusal is the plan
telling the Operator the item form must clear it.

A dead record (R81, the dead tag) is never a copy source and never un-retired. A RETIRED_MATCH (and an
UNRETIRE_FIRST copy) brings back its whole `unretire_set` (R101, the R50 lane): Cost = `lane_Cost` (the invoice),
Price = `lane_Price` (confirmed current at the STOP), the ONE decision tag (R96), then the un-retire.

Exit: 0 plan written (or a dry run with 0 refusals) · 2 refused or input refused (ABORT). Never 1: a plan has
no DEFECT, only refusals. The summary printed is the pre-create STOP's plan block: writes per step and channel.
"""
import hashlib
import os
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from intake_common import (CATALOG_COLS, CATEGORIES_REQUIRED, CREATE_VERDICTS, DEFAULT_DEAD_TAG, EXIT_ABORT,  # noqa: E402
                           EXIT_OK, ITEM_PREFIX, Selftest, abort, get_flag, grams_of, money_eq, new_path,
                           next_version, norm, num, read_csv, stamp, tag_set, version_stem, write_csv)
from intake_match import V3_COLS  # noqa: E402
import intake_derive  # noqa: E402

# plan field -> (the derived-cell field name, the intake column it re-derives from)
DERIVED_FIELDS = {"FlowerEquivalent": "Flower equiv", "ServingSizePerUnit": "Servings per Unit", "CBDContent": "CBD content",
                  "Grams": "Product grams"}   # R129: the vendor dose read (per piece / package total) rides the Grams row

PLAN_COLS = ["seq", "step", "line_no", "product_key", "field", "before", "target", "channel", "depends_on",
             "provenance", "row_sha1"]
HASH_COLS = PLAN_COLS[:-1]
SEP = "\x1f"
STEPS = ["MINT_STRAIN", "CREATE_BRAND", "UNRETIRE_ALIGN", "UNRETIRE", "COPY", "ALIGN", "CONTENT", "IMAGE_REMOVE",
         "LINK"]
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
    "image_remove": (PROVEN, "", "§2A row 20: remove-product-image replay - KB [PROBE 2026-09-26]; memory "
                                 "reference_dutchie_add_product_image_client_resize"),
    "link_replay": (PROVEN, "", "§2A row 21: link-catalog-product / unlink-from-catalog-product replay - KB "
                                "'The global-catalog link picker' [PROBE 2026-09-15/16, 2026-09-22/23]"),
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
FIELD_COL.update({"Name": "Product", "Online title": "Online title", "Online description": "Online description",
                  "_state": "_state", "_copy": "Product", "_images": "Image URL", "_global_link": "Brand catalog product"})
# a planned field whose write moves another export cell by itself: declared, never a defect (R124)
DERIVES = {"StrainId": ["Strain Type"], "_state": ["Brand catalog product"],
           "ProductCategoryId": ["Master category"]}   # moves only on a cross-MC target (P6)
ID_FIELDS = {"StrainId", "BrandId", "ProductCategoryId", "VendorId"}
MONEY = {"Cost", "Price"}
GRAMS = {"FlowerEquivalent", "Grams"}
NUMBERS = {"ServingSizePerUnit", "CBDContent"}
CATALOG_REQUIRED_PLAN = CATALOG_COLS          # the 27-column export WITH ProductId (the batch binds by record)
STRAINS_REQUIRED = ["Strain name", "Type"]
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


def build_plan(intake, active, retired, strains, categories, brands, channels=None, grid_fields=None,
               form_fields=None, guard=None, dead_tag=DEFAULT_DEAD_TAG, prefix=ITEM_PREFIX, fl_eq_classes=None):
    """Pure. (plan rows, refusals, notes). The four maps default to this module's; a selftest passes a copy
    to simulate a probe result - the CLI has no flag that widens them. `fl_eq_classes` = the tenant's class map
    (intake_derive.load_classes); None = no re-derivation, the row's cells stand."""
    channels, grid_fields = channels or CHANNELS, grid_fields or GRID_FIELDS
    form_fields, guard = form_fields or FORM_FIELDS, guard or GUARD
    act, ret = keyed(active, "--active"), keyed(retired, "--retired")
    both = sorted(set(act) & set(ret))
    if both:
        abort(f"ProductId(s) {both[:5]} sit in both the Active and the Retired export - not one freeze")
    strain_names = {norm(s.get("Strain name")): (s.get("Strain name") or "").strip() for s in strains}
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
        copies[n] = (key, src_id, emit("COPY", n, key, "_copy", src_id, name, "ui_copy", deps, "active"))
    # 6 ALIGN ------------------------------------------------------------------------------------------------
    for n, r in creates:
        if n not in copies:
            continue
        key, src_id, cseq = copies[n]
        for col, field, channel, icol in ROUTES:
            if field == "Tags":
                tag = one_tag(n, r, "ALIGN", key)
                if tag is None:
                    continue
                bef = eff(src_id, "Tags")
                tgt = tag_target(bef, tag, prefix)
                if not same("Tags", bef, tgt):
                    emit("ALIGN", n, key, "Tags", bef, tgt, channel, [cseq], "active")
                continue
            bef, _ = plan_value(field, eff(src_id, col))
            tgt, ok = plan_value(field, r.get(icol))
            if not ok:
                refuse("VALUE_NOT_NUMERIC", "ALIGN", n, key, field, channel, "", f"target {r.get(icol)!r}")
                continue
            dcell = intake_derive.parse_derived(r.get("derived"))
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
                notes.append(f"line {n}: the sibling's Online description is kept; its strain paragraph is a UI tail, not a planned write")
        later.append((n, r, key, src_id, cseq, xb))
    for n, r, key, src_id, cseq, xb in later:
        img = eff(src_id, "Image URL")
        if xb and img.strip():
            emit("IMAGE_REMOVE", n, key, "_images", img, "", "image_remove", [cseq], "active",
                 "every carried image: the ids come from the item's own read at run time")
    for n, r, key, src_id, cseq, xb in later:
        link = eff(src_id, "Brand catalog product")
        if xb and link.strip():
            emit("LINK", n, key, "_global_link", link, "", "link_replay", [cseq], "active", "unlink the source brand's global product")
    if any(r["step"] == "COPY" for r in rows):
        notes.append("COPY keeps `Copy online details` CHECKED on every copy, cross-brand included (PROVEN: KB 'Item "
                     "creation by Copy item' [PROBE 2026-10-08] - unchecked, the copy blanks the Online title, description "
                     "and Global Category / Sub yet still copies the image); Global Category / Sub carry from the source. "
                     "A cross-brand copy's title and description are REPLACED by its CONTENT rows (the new brand's words), "
                     "its copied image deleted by IMAGE_REMOVE after the item's last form Save (so no Save carries it "
                     "back), its source link removed by LINK; the new brand's image ADD is a UI tail after the certify")
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
    if notes:
        out += ["", "## Notes (not writes)", ""] + [f"- {x}" for x in dict.fromkeys(notes)]
    return out


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
        ptr = intake_pointers.load(tenant)
    from intake_match import load_fl_eq_classes
    rows, refusals, notes = build_plan(intake, active, retired, strains, categories, brands,
                                       fl_eq_classes=load_fl_eq_classes(argv, ptr))
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
    return dict(intake=intake, active=active, retired=retired, strains=strains, categories=cats, brands=brands)


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
    return build_plan(f["intake"], f["active"], f["retired"], f["strains"], f["categories"], f["brands"], **kw)


def selftest():
    t = Selftest("intake_plan")
    rows, ref, notes = _build(guard=_probed())
    t.check("GREEN: the fixture plans with 0 refusals once the retired guard is proven", ref == [], str(ref))
    steps = [r["step"] for r in rows]
    t.check("steps run in the kickoff's order (MINT_STRAIN .. LINK), never interleaved",
            [STEPS.index(s) for s in steps] == sorted(STEPS.index(s) for s in steps))
    t.check("each step kind is planned: MINT_STRAIN, UNRETIRE_ALIGN, UNRETIRE, COPY, ALIGN, CONTENT, IMAGE_REMOVE, LINK",
            {"MINT_STRAIN", "UNRETIRE_ALIGN", "UNRETIRE", "COPY", "ALIGN", "CONTENT", "IMAGE_REMOVE", "LINK"} <= set(steps),
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
    t.check("cross-brand: title and description REPLACED by the new brand's words, carried image removed, link unlinked",
            by[("new:3", "Online description")]["target"] == "Lime gummies from Brand A."
            and by[("new:3", "Online title")]["target"] == "Lime Gummies"
            and ("new:3", "_images") in by and ("new:3", "_global_link") in by)
    t.check("the sibling copy plans no residue clears", ("new:2", "_images") not in by and ("new:2", "Online description") not in by)
    t.check("an EXISTS row plans no write", not any(r["line_no"] == "4" for r in rows))
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
