"""receive.py - phase 2 (Receiving) of the dutchie-intake lane. `--prep` is BUILT; `--enter`, `--check`, `--vendor`
are stubs that exit 2.

  python receive.py --prep --lines <lines.csv> --catalog <active.csv> --inventory <inventory.csv>
                    [--intake <intake-vN.csv>] [--manifest <manifest.csv>] [--item <line>=<ProductId>]...
                    [--program <line>=<disposition>]... --tenant <CLAUDE.md> [--out-dir <dir>] [--slug <s>]
  python receive.py --enter | --check | --vendor ...   phase 2 stubs; exit 2
  python receive.py --selftest

`--prep` writes a NEW receipt prep sheet `<slug>-receipt-prep-<date>-vN.csv`, ONE ROW PER METRC PACKAGE (R126), plus
`<slug>-receipt-prep-<date>-vN-questions.md`: every STOP as a question to settle BEFORE the receipt is entered. It reads
files only. It never opens Metrc, Dutchie or a browser, and it never writes a room, a tag or a cost.

Inputs (columns are checked; a missing one ABORTs, never reads as blank):
  --lines      the invoice lines CSV (intake_parse output or the hand-typed lines): line_no, description, units_total,
               unit_cost, ext_cost, is_order_level, order_level_kind. Order-level rows (credit / shipping) ride along.
  --catalog    the Catalog Active export: ProductId, SKU, Product, Master category, Cost, Tags.
  --inventory  the Inventory export frozen at receive time (the FIFO snapshot): SKU, Room, Available, Cost.
  --intake     optional intake CSV vN: per line `new_productid`, else `copy_source_productid` on EXISTS / RETIRED_MATCH,
               `create_name_FINAL`, `tags`, `lane_Cost`. Rows pair to product lines by `invoice_line` == description.
  --manifest   optional; the READ-ONLY Metrc manifest read typed to CSV (SKILL.md "Metrc manifest read"):
               package_id, line, metrc_item, qty, ship_cost [, vendor_batch, expiry, map_basis]. `line` is the reader's
               mapping from the PO / SO / invoice / manifest; blank = the runner PROPOSES one (a STOP to confirm).
               Without a manifest the sheet has one row per product line and a blank package id.
  --item <line>=<ProductId>   the item a line receives against (beats the intake CSV).
  --program <line>=<value>    the disposition the invoice or the vendor's email states (R127): `sample`, `display`,
               `deal`, `tier <n>`, `none`, `cost change`. Beats every default.

Decisions (rules cited per flag; the tenant's R numbers live in RULE below):
  * room: `Intake` on every package (R126). On-hand by room from the snapshot is FIFO guidance, never a room write.
  * `PKG - ` tag (R127; R62 R84 R97): the invoice / email decide, never the price alone. A marked sample -> the sample
    tag; a marked display -> the display tag; a printed line discount, or `--program deal` -> the vendor deal tag;
    `tier <n>` -> `PKG - Tier <n>` (R84, R72). An unmarked price <= SAMPLE_MAX, or an unmarked price below catalog Cost,
    is a STOP question; its proposed default is the deal tag on a tiered master category (flower / pre-roll), else a
    catalog cost change (no tag). A price above catalog Cost is a STOP: the catalog keeps the highest cost.
  * strip (R47): every `ITM - ` tag the item carries, except the new-line tag on a SELLABLE package. A sample or display
    package (the sample / display tag) strips the new-line tag too: it never carries it (R47, R83).
  * flip (R83, R126): a new-line item flips to the active tag after the receipt only when the receipt holds at least one
    SELLABLE package of that item; a sample-only receipt flips nothing and the sheet says "no flip - sample-only
    receipt" (a note, never a write here).
  * credit (R126): entered once in the receipt header; Dutchie blends it EQUALLY across the receipt's packages. The
    sheet prints that blend per package (and the R103 extended-cost landed unit for reference).
  * manifest (R126): per line, sum of ship $ == invoice ext, else DEFECT; sum of qty == invoice qty, else STOP unless
    qty is a whole multiple with the $ tied (APEX_UNIT_IS_CASE, INFO: a vendor "unit" was a case).

Exit: 0 clean (STOP / INFO never fail), 1 DEFECT, 2 ABORT.
"""
import os
import re
import sys
from datetime import date

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from intake_common import (EXIT_ABORT, EXIT_DEFECT, EXIT_OK, ITEM_PREFIX, PKG_PREFIX, DEFAULT_ACTIVE_TAG,  # noqa: E402
                           DEFAULT_NEW_LINE_TAG, Selftest, abort, fmt_money, get_all, get_flag, money_eq, new_path,
                           next_version, norm, num, read_csv, slug, tag_set, write_csv)

CHECK_JOIN_KEY = "package_id"   # the `--check` join key: an intake CSV v3 column, carried onto the prep sheet
RECEIVE_ROOM = "Intake"         # R126
SAMPLE_MAX = 0.05               # a "penny" unit cost: at or below this the line's disposition must be stated (R127)
R62_RATIO = 0.90                # R62, ruled
TIERED_MASTER = ("Flower", "Pre-Roll")   # where an unmarked lower price defaults to a tier deal (Adam 2026-10-08)
DEFAULT_SAMPLE_TAG, DEFAULT_DISPLAY_TAG = "PKG - Employee", "PKG - Display"   # R97 dispositions; tenant may rename

LINE_REQ = ["line_no", "description", "units_total", "unit_cost", "ext_cost", "is_order_level", "order_level_kind"]
CAT_REQ = ["ProductId", "SKU", "Product", "Master category", "Cost", "Tags"]
INV_REQ = ["SKU", "Room", "Available", "Cost"]
INTAKE_REQ = ["invoice_line", "verdict", "new_productid", "copy_source_productid", "create_name_FINAL", "tags", "lane_Cost"]
MAN_REQ = ["package_id", "line", "metrc_item", "qty", "ship_cost"]

# flag -> (rule, class). DEFECT exits 1; STOP is a question before the receipt; INFO is a note.
FLAGS = {
    "MANIFEST_COST_MISMATCH": ("R126", "DEFECT"), "MANIFEST_PACKAGE_UNMAPPED": ("R126", "DEFECT"),
    "MANIFEST_QTY_MISMATCH": ("R126 (R102: PO > Invoice > Physical)", "STOP"), "MANIFEST_LINE_MISSING": ("R126", "STOP"),
    "MAP_PROPOSED": ("R126", "STOP"), "MAP_UNRESOLVED": ("R126", "STOP"), "APEX_UNIT_IS_CASE": ("R126", "INFO"),
    "SAMPLE_MERGED": ("R127", "STOP"), "SAMPLE": ("R127 (R97)", "INFO"), "DISPLAY": ("R127 (R97)", "INFO"),
    "DEAL_PRINTED": ("R127 (R62 R84)", "INFO"), "TIER_RULED": ("R84 (R72)", "INFO"),
    "PENNY_UNMARKED": ("R127", "STOP"), "PRICE_DROP_UNMARKED": ("R127 (R62 R84)", "STOP"),
    "CATALOG_COST_RAISE": ("R127", "STOP"), "COST_UNKNOWN": ("R127", "STOP"), "ITEM_PENDING": ("R126", "STOP"),
    "CREDIT_TRIPS_R62": ("R62 (R126)", "STOP"), "CREDIT_BLEND_NEGATIVE": ("R126", "STOP"),
    "LANDED_UNRECONCILED": ("R103", "DEFECT"),
}
QUESTION = {
    "MANIFEST_QTY_MISMATCH": "The manifest quantity differs from the invoice. The vendor adjusts and reissues the invoice, or the package is rejected whole. Which?",
    "MANIFEST_LINE_MISSING": "This line has no Metrc package. Short ship, a later manifest, or a merged package?",
    "MAP_PROPOSED": "Confirm the proposed line for this package against the PO / SO / invoice, then type it in the manifest `line` cell.",
    "MAP_UNRESOLVED": "Which invoice line does this package belong to? Read the PO, SO, invoice and manifest and type the `line` cell.",
    "SAMPLE_MERGED": "The sample shipped inside the paid package. Ask the vendor to split it into its own package before the receipt.",
    "PENNY_UNMARKED": "Penny price with no marker. Is it a sample (`--program <line>=sample`), a display (`display`) or a promo unit (`deal`)? Check the invoice and the vendor's email.",
    "PRICE_DROP_UNMARKED": "Price below catalog Cost with no struck price or printed promo. A tier / deal (`deal`, `tier <n>`) or a real cost change (`cost change`)? Check the vendor's email.",
    "CATALOG_COST_RAISE": "Invoice price above catalog Cost. The catalog keeps the highest cost: raise the item's Cost (a PL-grain change, not this lane's write).",
    "COST_UNKNOWN": "No catalog Cost to compare against. Settle the item's agreed Cost first.",
    "ITEM_PENDING": "No Dutchie item for this line yet. Create it (or give `--item <line>=<ProductId>`) before the receipt.",
    "CREDIT_TRIPS_R62": "The blended credit lands this package at or below 0.90 x catalog Cost with no `PKG - ` tag (R62 would flag it). Tag it, or settle the credit another way.",
    "CREDIT_BLEND_NEGATIVE": "Dutchie's equal blend makes this package's cost negative. Enter the credit another way (vendor bill or a reissued invoice).",
}
PREP_COLS = ["row", "line", "invoice_item", "dutchie_productid", "dutchie_sku", "dutchie_name", "expected_qty",
             "unit_cost_invoice", "ext_cost", "landed_unit_cost", "blended_unit_cost", "catalog_cost",
             "on_hand_pkg_costs", "physical_count", "qty_match", "metrc_package_id", "metrc_item", "manifest_qty",
             "manifest_ship_cost", "map_basis", "expiry", "receive_room", "pkg_tags_to_apply", "tag_rule",
             "itm_tags_to_strip", "new_line_tag_on_package", "item_tag_flip", "on_hand_snapshot", "vendor_batch",
             "flags"]
STOPWORDS = {"mg", "g", "ct", "10ct", "100mg", "gummies", "gummy", "the", "and", "pk", "pack", "x", "1g", "thc", "cbd"}


def sort_key(n):
    m = re.match(r"(\d+)", str(n))
    return (int(m.group(1)) if m else 10 ** 9, str(n))


def parse_directions(argv, name):
    out = {}
    for d in get_all(argv, name):
        k, sep, v = d.partition("=")
        if not sep or not k.strip():
            abort(f"{name} {d!r}: expected <line>=<value>")
        out[k.strip()] = v.strip()
    return out


def marker(desc):
    """The invoice's own disposition word: `sample` / `display`, else ''."""
    d = norm(desc)
    if re.search(r"(?:^| )samples?(?: |$)", d):
        return "sample"
    if re.search(r"(?:^| )display(?: |$)", d):
        return "display"
    return ""


def tokens(s):
    return {w for w in norm(s).split() if w not in STOPWORDS and not re.fullmatch(r"[\d.]+", w)}


def propose_line(pkg, prod, used_qty):
    """Candidate lines for an unmapped package: same unit price (or the whole ext at a case multiple), qty still free.
    A unique best by item-word overlap is a PROPOSAL; the reader confirms it. Returns (line_no or '', basis)."""
    q, ship = num(pkg.get("qty")) or 0, num(pkg.get("ship_cost")) or 0
    unit = ship / q if q else None
    cands = []
    for ln in prod:
        lq, lu, le = num(ln.get("units_total")) or 0, num(ln.get("unit_cost")), num(ln.get("ext_cost"))
        free = lq - used_qty.get(ln["line_no"], 0)
        price_ok = unit is not None and lu is not None and abs(unit - lu) < 0.005 and q <= free + 1e-9
        case_ok = le is not None and abs(ship - le) < 0.005 and lq and q > lq and abs(q / lq - round(q / lq)) < 1e-9
        if price_ok or case_ok:
            cands.append((len(tokens(pkg.get("metrc_item")) & tokens(ln.get("description"))), ln["line_no"]))
    if not cands:
        return "", "no line at this unit price"
    cands.sort(reverse=True)
    if len(cands) == 1 or cands[0][0] > cands[1][0]:
        return cands[0][1], f"unit price + item words ({cands[0][0]} shared)"
    return "", "ambiguous: lines " + ", ".join(c[1] for c in cands if c[0] == cands[0][0])


def on_hand(inv, sku):
    rooms, costs = {}, set()
    for r in inv:
        if sku and r.get("SKU") == sku and (num(r.get("Available")) or 0) > 0:
            rooms[r["Room"]] = rooms.get(r["Room"], 0) + (num(r.get("Available")) or 0)
            c = num(r.get("Cost"))
            if c is not None:
                costs.add(c)
    snap = "; ".join(f"{k} {v:g}" for k, v in sorted(rooms.items())) or "none on hand"
    return snap, ";".join(f"{c:g}" for c in sorted(costs, reverse=True))


def prep(lines, catalog, inventory, intake=None, manifest=None, items=None, programs=None, deal_tag=None,
         sample_tag=DEFAULT_SAMPLE_TAG, display_tag=DEFAULT_DISPLAY_TAG, new_line_tag=DEFAULT_NEW_LINE_TAG,
         active_tag=DEFAULT_ACTIVE_TAG):
    """Pure. Returns (rows, exceptions, summary). exceptions: dicts flag, rule, class, row, line, detail."""
    if not deal_tag:
        abort("the vendor deal tag is ruled per tenant (pointer `Vendor deal tag`); none given")
    items, programs = items or {}, programs or {}
    prod = [ln for ln in lines if (ln.get("is_order_level") or "").upper() != "Y" and not (ln.get("order_level_kind") or "").strip()]
    order = [ln for ln in lines if (ln.get("is_order_level") or "").upper() == "Y" and (ln.get("order_level_kind") or "").strip()]
    disc = {}
    for ln in lines:
        if (ln.get("order_level_kind") or "") == "discount" and (ln.get("is_order_level") or "").upper() != "Y":
            disc[ln["line_no"]] = disc.get(ln["line_no"], 0.0) + abs(num(ln.get("ext_cost")) or 0)
    by_pid = {r["ProductId"]: r for r in catalog}
    ib = {}
    for r in intake or []:
        ib.setdefault(norm(r.get("invoice_line")), r)
    exc = []

    def add(flag, row, line, detail):
        rule, cls = FLAGS[flag]
        exc.append({"flag": flag, "rule": rule, "class": cls, "row": row, "line": line, "detail": detail})

    # 1. packages -> lines (the reader's `line` cell; else a proposal)
    pk_by_line, used_qty, mapped = {}, {}, []
    known = {ln["line_no"] for ln in prod}
    for p in manifest or []:
        p = dict(p)
        line = (p.get("line") or "").strip()
        basis = p.get("map_basis") or ("reader" if line else "")
        if line and line not in known:
            add("MANIFEST_PACKAGE_UNMAPPED", "", line, f"package {p['package_id']} names line {line}, which is not a product line")
            continue
        if not line:
            line, why = propose_line(p, prod, used_qty)
            if line:
                basis = f"PROPOSED: {why}"
                p["_proposed"] = why
            else:
                add("MAP_UNRESOLVED", "", "", f"package {p['package_id']} ({p.get('metrc_item')}): {why}")
                continue
        used_qty[line] = used_qty.get(line, 0) + (num(p.get("qty")) or 0)
        p["map_basis"] = basis
        pk_by_line.setdefault(line, []).append(p)
        mapped.append(p)

    # 2. the order-level blend: Dutchie spreads it EQUALLY across the receipt's packages (R126)
    o_all = sum(num(ln.get("ext_cost")) or 0 for ln in order)
    n_pk = len(mapped) if manifest else len(prod)
    share = o_all / n_pk if n_pk else 0.0
    base = sum(num(ln.get("ext_cost")) or 0 for ln in prod)

    rows = []
    new_line_items = {}   # item key -> True once a SELLABLE package of a new-line item is on this receipt (R83 R126)
    for ln in sorted(prod, key=lambda x: sort_key(x["line_no"])):
        no, desc = ln["line_no"], ln.get("description", "")
        units, unit, ext = num(ln.get("units_total")) or 0, num(ln.get("unit_cost")), num(ln.get("ext_cost")) or 0
        ir = ib.get(norm(desc), {})
        pid = items.get(no) or ir.get("new_productid") or (
            ir.get("copy_source_productid") if ir.get("verdict") in ("EXISTS", "RETIRED_MATCH") else "")
        cat = by_pid.get(pid, {}) if pid else {}
        if pid and not cat:
            abort(f"line {no}: ProductId {pid} is not in the Active export (retired or mistyped)")
        cost = num(cat.get("Cost")) if cat else num(ir.get("lane_Cost"))
        tags = tag_set(cat.get("Tags")) if cat else tag_set(ir.get("tags"))
        mc = cat.get("Master category", "")
        prog = (programs.get(no) or programs.get("*") or "").strip().lower()
        mk = marker(desc)
        landed_r103 = None
        if units and base > 0:
            landed_r103 = (ext - disc.get(no, 0.0) + ext / base * o_all) / units
        line_flags = []

        def lflag(flag, detail):
            line_flags.append(flag)
            add(flag, "", no, detail)

        # tag decision (R127): stated disposition > invoice marker > printed discount > price defaults
        pkg_tag, rule = "", ""
        if prog in ("sample",) or (not prog and mk == "sample"):
            pkg_tag, rule = sample_tag, "R127 sample (R97)"
            lflag("SAMPLE", f"{'stated' if prog else 'invoice marks'} a sample -> {sample_tag}, its own package")
        elif prog == "display" or (not prog and mk == "display"):
            pkg_tag, rule = display_tag, "R127 display (R97)"
            lflag("DISPLAY", f"{'stated' if prog else 'invoice marks'} a display unit -> {display_tag}")
        elif prog.startswith("tier"):
            n = prog.split()[-1]
            pkg_tag, rule = f"{PKG_PREFIX}Tier {n}", "R84 ruled tier (R72)"
            lflag("TIER_RULED", f"tier {n} ruled -> {pkg_tag}")
        elif prog == "deal" or (not prog and disc.get(no)):
            pkg_tag, rule = deal_tag, "R127 printed / stated deal (R62 R84)"
            lflag("DEAL_PRINTED", f"{'stated deal' if prog else f'line discount {disc[no]:.2f} printed'} -> {deal_tag}")
        elif prog in ("none", "cost change"):
            rule = f"R127 stated: {prog}"
        elif unit is not None and unit <= SAMPLE_MAX + 1e-9:
            rule = "R127: disposition owed"
            lflag("PENNY_UNMARKED", f"unit {unit:.2f} <= {SAMPLE_MAX:.2f} and neither the invoice nor a direction says sample, display or deal")
        if not prog and not pkg_tag and unit is not None and unit > SAMPLE_MAX + 1e-9:
            if cost is None:
                lflag("COST_UNKNOWN", "no catalog Cost (and no intake lane_Cost) to compare the invoice price with")
            elif unit < cost - 0.005:
                tiered = mc in TIERED_MASTER
                pkg_tag = deal_tag if tiered else ""
                rule = "R127 PROPOSED: " + ("tier deal on a tiered category" if tiered else "catalog cost change")
                lflag("PRICE_DROP_UNMARKED", f"unit {unit:.2f} < catalog Cost {cost:g} with no struck price or printed promo; "
                                             f"default {'`' + deal_tag + '`' if tiered else 'a catalog cost change, no tag'} ({mc or 'master category unknown'})")
        if unit is not None and cost is not None and unit > cost + 0.005 and prog != "cost change" and pkg_tag not in (sample_tag, display_tag):
            lflag("CATALOG_COST_RAISE", f"unit {unit:.2f} > catalog Cost {cost:g}: the catalog keeps the highest cost")
        if not pid:
            lflag("ITEM_PENDING", "no Dutchie ProductId for this line (create first, or --item)")
        sample_pkg = pkg_tag in (sample_tag, display_tag)   # a sample or display package is never sellable stock
        strip = sorted(t for t in tags if t.startswith(ITEM_PREFIX) and (t != new_line_tag or sample_pkg))
        new_line = new_line_tag in tags
        item_key = pid or f"line {no}"
        if new_line:
            new_line_items[item_key] = new_line_items.get(item_key, False) or not sample_pkg
        on_pkg = "" if not new_line else (f"no - {pkg_tag} package (R47)" if sample_pkg else "yes (R47 R83)")
        snap, pk_costs = on_hand(inventory, cat.get("SKU", ""))
        if not pid:
            snap = "new item"
        common = {"line": no, "invoice_item": desc, "dutchie_productid": pid or "PENDING (create in this lane)",
                  "dutchie_sku": cat.get("SKU", ""), "dutchie_name": cat.get("Product", "") or ir.get("create_name_FINAL", ""),
                  "unit_cost_invoice": fmt_money(unit), "catalog_cost": "" if cost is None else f"{cost:g}",
                  "landed_unit_cost": "" if landed_r103 is None else f"{landed_r103:.4f}", "on_hand_pkg_costs": pk_costs,
                  "receive_room": RECEIVE_ROOM, "pkg_tags_to_apply": pkg_tag or "none", "tag_rule": rule,
                  "itm_tags_to_strip": "; ".join(strip) or "none", "new_line_tag_on_package": on_pkg,
                  "on_hand_snapshot": snap, "expiry": ln.get("expiry_date", ""), "_item": item_key if new_line else ""}

        # manifest tie (R126)
        pks = pk_by_line.get(no, [])
        if manifest is not None:
            sq = sum(num(p.get("qty")) or 0 for p in pks)
            ss = sum(num(p.get("ship_cost")) or 0 for p in pks)
            case = False
            if not pks:
                merged = None
                if pkg_tag == sample_tag:
                    for other in prod:
                        if other["line_no"] == no:
                            continue
                        opid = items.get(other["line_no"]) or ib.get(norm(other.get("description")), {}).get("new_productid")
                        same = (opid and opid == pid) or norm(re.sub(r"\(?sample[^)]*\)?", "", desc)) == norm(other.get("description"))
                        if not same:
                            continue
                        oq = sum(num(p.get("qty")) or 0 for p in pk_by_line.get(other["line_no"], []))
                        if abs(oq - ((num(other.get("units_total")) or 0) + units)) < 1e-9:
                            merged = other["line_no"]
                if merged:
                    lflag("SAMPLE_MERGED", f"no package of its own; line {merged}'s package(s) carry {merged}'s qty + these {units:g}")
                    for e in exc:
                        if e["line"] == merged and e["flag"] in ("MANIFEST_QTY_MISMATCH", "MANIFEST_COST_MISMATCH"):
                            e["detail"] += f" (explained: line {no}'s sample merged in)"
                else:
                    lflag("MANIFEST_LINE_MISSING", f"no Metrc package maps to line {no} ({units:g} units)")
            else:
                if abs(ss - ext) >= 0.005:
                    merged_in = any(e["flag"] == "SAMPLE_MERGED" and f"line {no}'s" in e["detail"] for e in exc)
                    lflag("MANIFEST_COST_MISMATCH", f"manifest ship ${ss:.2f} vs invoice ext ${ext:.2f} ({ss - ext:+.2f})"
                          + (" (explained: a sample merged in)" if merged_in else ""))
                if abs(sq - units) >= 1e-9:
                    k = sq / units if units else 0
                    if abs(ss - ext) < 0.005 and units and k > 1 and abs(k - round(k)) < 1e-9:
                        case = True
                        lflag("APEX_UNIT_IS_CASE", f"invoice {units:g} unit(s) = manifest {sq:g}: 1 unit = {k:g}; rows take the manifest qty")
                    else:
                        lflag("MANIFEST_QTY_MISMATCH", f"manifest qty {sq:g} vs invoice {units:g}")
                for p in pks:
                    if p.get("_proposed"):
                        lflag("MAP_PROPOSED", f"package {p['package_id']} -> line {no} ({p['_proposed']})")
        if not pks:
            pks = [None]
        for k, p in enumerate(pks):
            rid = no if len(pks) == 1 else f"{no}{chr(ord('a') + k)}"
            q = (num(p.get("qty")) if p else None) or units
            pext = num(p.get("ship_cost")) if p else ext
            pext = ext if pext is None else pext
            u = pext / q if q else None
            blend = (pext + share) / q if q else None
            r = dict(common, row=rid, expected_qty=f"{q:g}", ext_cost=fmt_money(pext),
                     unit_cost_invoice=fmt_money(u if (p and case) else unit),
                     blended_unit_cost="" if blend is None or not order else f"{blend:.4f}",
                     metrc_package_id=(p or {}).get("package_id", ""), metrc_item=(p or {}).get("metrc_item", ""),
                     manifest_qty=(p or {}).get("qty", ""), manifest_ship_cost=(p or {}).get("ship_cost", ""),
                     map_basis=(p or {}).get("map_basis", ""), vendor_batch=(p or {}).get("vendor_batch", ""),
                     expiry=(p or {}).get("expiry") or common["expiry"])
            rflags = list(line_flags)
            if order and blend is not None:
                if pext + share < -0.005:
                    rflags.append("CREDIT_BLEND_NEGATIVE")
                    add("CREDIT_BLEND_NEGATIVE", rid, no, f"package ext {pext:.2f} + equal share {share:+.2f} = {pext + share:+.2f}")
                elif cost and pkg_tag == "" and blend <= R62_RATIO * cost + 1e-9:
                    rflags.append("CREDIT_TRIPS_R62")
                    add("CREDIT_TRIPS_R62", rid, no, f"blended unit {blend:.4f} <= {R62_RATIO:.2f} x catalog Cost {cost:g} and no `{PKG_PREFIX}` tag")
            r["flags"] = ";".join(dict.fromkeys(rflags))
            rows.append(r)
    # the flip (R83 R126) is per ITEM and needs the whole receipt: one sellable package of the item flips it
    flips = {}
    for k, sellable in new_line_items.items():
        flips[k] = (f"{new_line_tag} -> {active_tag} after the receipt (R126)" if sellable
                    else f"no flip - sample-only receipt; the item stays {new_line_tag} (R83 R126)")
    for r in rows:
        r["item_tag_flip"] = flips.get(r.pop("_item"), "")
    for ln in order:
        rows.append({"row": ln["line_no"], "line": ln["line_no"], "invoice_item": ln.get("description", ""),
                     "ext_cost": fmt_money(num(ln.get("ext_cost"))), "receive_room": "",
                     "flags": f"ORDER-LEVEL {ln['order_level_kind'].upper()}: enter once in the receipt header; Dutchie blends it "
                              f"equally across {n_pk} package(s) ({share:+.4f} each) (R126)"})
    if base <= 0 and abs(o_all) >= 0.005:
        add("LANDED_UNRECONCILED", "", "", f"order-level lines total {o_all:+.2f} but no product line carries ext_cost")
    summary = {"packages": len(mapped), "product_lines": len(prod), "order_level": o_all, "share": share,
               "manifest": manifest is not None, "product_ext": base, "new_line_tag": new_line_tag,
               "new_line_packages": sum(1 for r in rows if r.get("new_line_tag_on_package", "").startswith("yes")),
               "flips": dict(sorted(flips.items()))}
    return rows, exc, summary


def questions(exc, summary, stem):
    stops = [e for e in exc if e["class"] in ("STOP", "DEFECT")]
    out = [f"# Receipt prep - questions before the receipt ({stem})", "",
           f"Product lines {summary['product_lines']} · packages {summary['packages']}"
           + ("" if summary["manifest"] else " (no Metrc manifest yet: package ids blank; re-run when it is read)")
           + f" · order-level {summary['order_level']:+.2f}", "",
           "Nothing is entered in Dutchie until every row below is settled. A DEFECT means the receipt is not entered.", ""]
    if summary.get("flips"):
        out += [f"New-line items (R83 R126): packages carrying `{summary['new_line_tag']}` "
                f"{summary['new_line_packages']} (sellable packages only; R47)."]
        out += [f"- item {k}: {v}" for k, v in summary["flips"].items()] + [""]
    if not stops:
        return "\n".join(out + ["No STOP and no DEFECT. The sheet is ready for the receiver's physical count.", ""])
    out += ["| # | Flag | Class | Rule | Row / line | Detail | Question |", "|---|---|---|---|---|---|---|"]
    for i, e in enumerate(stops, 1):
        out.append(f"| {i} | {e['flag']} | {e['class']} | {e['rule']} | {e['row'] or e['line']} | "
                   f"{e['detail'].replace('|', chr(92) + '|')} | {QUESTION.get(e['flag'], 'Fix the input and re-run.')} |")
    return "\n".join(out + [""])


def run_prep(argv):
    lines_p, cat_p, inv_p = get_flag(argv, "--lines"), get_flag(argv, "--catalog"), get_flag(argv, "--inventory")
    if not (lines_p and cat_p and inv_p):
        abort("--prep needs --lines, --catalog and --inventory")
    tenant = get_flag(argv, "--tenant")
    deal_tag, sample_tag, display_tag = get_flag(argv, "--deal-tag"), DEFAULT_SAMPLE_TAG, DEFAULT_DISPLAY_TAG
    new_line_tag, active_tag = DEFAULT_NEW_LINE_TAG, DEFAULT_ACTIVE_TAG
    if tenant:
        import intake_pointers
        ptr = intake_pointers.load(tenant)["intake"]
        deal_tag = deal_tag or ptr.get("Vendor deal tag")
        sample_tag = ptr.get("Sample tag") or sample_tag
        display_tag = ptr.get("Display tag") or display_tag
        new_line_tag = ptr.get("New line tag") or new_line_tag
        active_tag = ptr.get("Active tag") or active_tag
    _, lines = read_csv(lines_p, LINE_REQ, "lines")
    _, catalog = read_csv(cat_p, CAT_REQ, "catalog")
    _, inv = read_csv(inv_p, INV_REQ, "inventory")
    intake = read_csv(get_flag(argv, "--intake"), INTAKE_REQ, "intake")[1] if get_flag(argv, "--intake") else None
    man = read_csv(get_flag(argv, "--manifest"), MAN_REQ, "manifest")[1] if get_flag(argv, "--manifest") else None
    rows, exc, summary = prep(lines, catalog, inv, intake, man, parse_directions(argv, "--item"),
                              parse_directions(argv, "--program"), deal_tag, sample_tag, display_tag, new_line_tag, active_tag)
    first = next((ln for ln in lines if ln.get("invoice_no")), {})
    s = get_flag(argv, "--slug") or slug(first.get("invoice_no") or os.path.splitext(os.path.basename(lines_p))[0])
    out_dir = get_flag(argv, "--out-dir") or os.path.dirname(os.path.abspath(lines_p))
    out = next_version(out_dir, f"{s}-receipt-prep-{get_flag(argv, '--asof') or date.today().isoformat()}")
    write_csv(out, PREP_COLS, rows)
    qpath = new_path(out_dir, os.path.splitext(os.path.basename(out))[0] + "-questions", ".md")
    text = questions(exc, summary, os.path.basename(out))
    with open(qpath, "w", encoding="utf-8") as f:
        f.write(text)
    counts = {}
    for e in exc:
        counts[e["class"]] = counts.get(e["class"], 0) + 1
    print(text)
    print(f"wrote {out} ({len(rows)} rows) and {qpath}")
    print("classes: " + (", ".join(f"{k} {v}" for k, v in sorted(counts.items())) or "none"))
    return EXIT_DEFECT if counts.get("DEFECT") else EXIT_OK


STUB = ("receive: `{0}` is phase 2, not built. See the receiving plan named in the tenant estate. "
        "Nothing was read or written.")


def check(prep_csv, receipt_detail_csv, tenant=None):
    """Phase 2 `--check`: prep sheet vs Receipt Detail export, joined on CHECK_JOIN_KEY. Not implemented."""
    raise NotImplementedError("receive --check is phase 2; see the receiving plan in the tenant estate")


def main(argv):
    if "--selftest" in argv:
        return selftest()
    if "--prep" in argv:
        return run_prep(argv)
    for mode in ("--enter", "--check", "--vendor"):
        if mode in argv:
            print(STUB.format(mode))
            return EXIT_ABORT
    print("receive: usage - receive.py --prep ... (see the header); --enter / --check / --vendor are stubs (exit 2)")
    return EXIT_ABORT


# ---------------------------------------------------------------- selftest (synthetic; no tenant, vendor or brand)
def _fixture():
    cat = [{"ProductId": "11", "SKU": "9011", "Product": "Acme | Gummies | Lemon (Sativa) | 10mg x 10pk",
            "Master category": "Edible", "Cost": "10", "Tags": "ITM - Active"},
           {"ProductId": "12", "SKU": "9012", "Product": "Acme | Pre-Roll | Haze | 1g", "Master category": "Pre-Roll",
            "Cost": "5", "Tags": "ITM - Active"},
           {"ProductId": "13", "SKU": "9013", "Product": "Acme | Vape | Mint | 1g", "Master category": "Vape",
            "Cost": "20", "Tags": "ITM - New PL; ITM - Protect"}]
    inv = [{"SKU": "9011", "Room": "Order Fulfillment", "Available": "6", "Cost": "10"},
           {"SKU": "9011", "Room": "Employee", "Available": "2", "Cost": "0.01"},
           {"SKU": "9012", "Room": "Vault", "Available": "0", "Cost": "5"}]

    def ln(no, desc, units, unit, **kw):
        return dict({"line_no": str(no), "description": desc, "units_total": str(units), "unit_cost": f"{unit:.2f}",
                     "ext_cost": f"{units * unit:.2f}", "is_order_level": "N", "order_level_kind": "", "expiry_date": ""}, **kw)
    lines = [ln(1, "Acme Lemon Gummies 100mg 10ct", 40, 10.0), ln(2, "Acme Haze Pre-Roll 1g", 100, 5.0),
             ln(3, "Acme Mint Vape 1g", 10, 20.0), ln(4, "Acme Mint Vape 1g (sample)", 5, 0.01)]
    man = [{"package_id": "PKG-A", "line": "1", "metrc_item": "Lemon Gummies", "qty": "20", "ship_cost": "200.00"},
           {"package_id": "PKG-B", "line": "1", "metrc_item": "Lemon Gummies", "qty": "20", "ship_cost": "200.00"},
           {"package_id": "PKG-C", "line": "2", "metrc_item": "Haze Pre-Roll", "qty": "100", "ship_cost": "500.00"},
           {"package_id": "PKG-D", "line": "3", "metrc_item": "Mint Vape", "qty": "10", "ship_cost": "200.00"},
           {"package_id": "PKG-E", "line": "4", "metrc_item": "Mint Vape sample", "qty": "5", "ship_cost": "0.05"}]
    items = {"1": "11", "2": "12", "3": "13", "4": "13"}
    return cat, inv, lines, man, items


def _run(cat, inv, lines, man, items, programs=None):
    rows, exc, summ = prep(lines, cat, inv, None, man, items, programs, "PKG - Vendor Deal")
    return rows, exc, summ


def _flags(res):
    return sorted((e["flag"], e["line"]) for e in res[1])


def selftest():
    import copy
    t = Selftest("receive")
    cat, inv, lines, man, items = _fixture()
    base = _run(cat, inv, lines, man, items)
    rows = {r["row"]: r for r in base[0]}
    t.check("CLEAN: the control receipt raises no STOP and no DEFECT",
            not [e for e in base[1] if e["class"] in ("STOP", "DEFECT")], str(_flags(base)))
    t.check("one row per Metrc package: line 1 splits into 1a / 1b", "1a" in rows and "1b" in rows and "1" not in rows
            and rows["1a"]["metrc_package_id"] == "PKG-A" and rows["1b"]["expected_qty"] == "20")
    t.check("every package is received into Intake", all(r["receive_room"] == "Intake" for r in base[0]))
    t.check("a marked sample takes the sample tag", rows["4"]["pkg_tags_to_apply"] == DEFAULT_SAMPLE_TAG
            and "SAMPLE" in rows["4"]["flags"])
    t.check("ITM strip keeps the new-line tag and strips the rest (R47)", rows["3"]["itm_tags_to_strip"] == "ITM - Protect"
            and rows["1a"]["itm_tags_to_strip"] == "ITM - Active")
    t.check("a new-line item prints the after-receipt flip", "ITM - Active after the receipt" in rows["3"]["item_tag_flip"]
            and rows["1a"]["item_tag_flip"] == "")
    t.check("on-hand snapshot by room (FIFO guidance), zero-stock rows ignored",
            rows["1a"]["on_hand_snapshot"] == "Employee 2; Order Fulfillment 6" and rows["2"]["on_hand_snapshot"] == "none on hand")
    t.check("price at catalog Cost: no tag", rows["2"]["pkg_tags_to_apply"] == "none" and rows["2"]["flags"] == "")

    def fires(flag, line, mutate, label, cls=None):
        c = copy.deepcopy((cat, inv, lines, man, items))
        prog = mutate(*c) or None
        res = _run(*c, programs=prog)
        hit = any(e["flag"] == flag and (line is None or e["line"] == line) for e in res[1])
        quiet = not any(e["flag"] == flag for e in base[1])
        t.check(f"{flag} fires on {label} and is quiet on the control", hit and quiet, str(_flags(res)))
        return res

    def ship(c, i, l, m, it, pid, v):
        next(p for p in m if p["package_id"] == pid)["ship_cost"] = v

    r = fires("MANIFEST_COST_MISMATCH", "2", lambda c, i, l, m, it: ship(c, i, l, m, it, "PKG-C", "480.00"), "a $20 short ship $")
    t.check("MANIFEST_COST_MISMATCH is a DEFECT", any(e["flag"] == "MANIFEST_COST_MISMATCH" and e["class"] == "DEFECT" for e in r[1]))

    def qty(c, i, l, m, it):
        next(p for p in m if p["package_id"] == "PKG-C")["qty"] = "90"
    fires("MANIFEST_QTY_MISMATCH", "2", qty, "a 10-unit short package")

    def unmapped(c, i, l, m, it):
        m[2]["line"] = "99"
    fires("MANIFEST_PACKAGE_UNMAPPED", "99", unmapped, "a package naming no line")

    def missing(c, i, l, m, it):
        del m[2]
    fires("MANIFEST_LINE_MISSING", "2", missing, "a line with no package")

    def merged(c, i, l, m, it):
        del m[4]
        p = next(p for p in m if p["package_id"] == "PKG-D")
        p["qty"], p["ship_cost"] = "15", "200.05"
    fires("SAMPLE_MERGED", "4", merged, "a sample merged into the paid package")

    def case(c, i, l, m, it):
        l[1].update(units_total="1", unit_cost="500.00", ext_cost="500.00")
    rc = fires("APEX_UNIT_IS_CASE", "2", case, "1 invoice unit = 100 on the manifest")
    t.check("APEX_UNIT_IS_CASE rows take the manifest qty and the per-pack cost",
            next(x for x in rc[0] if x["row"] == "2")["unit_cost_invoice"] == "5.00"
            and not any(e["flag"] == "MANIFEST_QTY_MISMATCH" for e in rc[1]))

    def blank_line(c, i, l, m, it):
        m[3]["line"] = ""
    rp = fires("MAP_PROPOSED", "3", blank_line, "a blank `line` cell with one price match")
    t.check("a proposal never clears the STOP class", any(e["flag"] == "MAP_PROPOSED" and e["class"] == "STOP" for e in rp[1]))

    def ambiguous(c, i, l, m, it):
        m[0]["line"] = ""
        l.append(dict(l[0], line_no="5", description="Acme Lemon Gummies 100mg 10ct"))
        it["5"] = "11"
    fires("MAP_UNRESOLVED", None, ambiguous, "two lines at the same price and words")

    def penny(c, i, l, m, it):
        l[3]["description"] = "Acme Mint Vape 1g"
    fires("PENNY_UNMARKED", "4", penny, "a penny line with no sample marker")

    def penny_deal(c, i, l, m, it):
        l[3]["description"] = "Acme Mint Vape 1g"
        return {"4": "deal"}
    rd = fires("DEAL_PRINTED", "4", penny_deal, "a promo unit at a penny (`--program deal`)")
    t.check("a stated deal on a penny line takes the vendor deal tag, not the sample tag",
            next(x for x in rd[0] if x["row"] == "4")["pkg_tags_to_apply"] == "PKG - Vendor Deal"
            and not any(e["flag"] == "PENNY_UNMARKED" for e in rd[1]))

    def drop_pr(c, i, l, m, it):
        l[1].update(unit_cost="4.00", ext_cost="400.00")
        m[2]["ship_cost"] = "400.00"
    rpr = fires("PRICE_DROP_UNMARKED", "2", drop_pr, "an unmarked lower price on pre-roll")
    t.check("an unmarked lower price on a tiered category defaults to the vendor deal tag",
            next(x for x in rpr[0] if x["row"] == "2")["pkg_tags_to_apply"] == "PKG - Vendor Deal")

    def drop_ed(c, i, l, m, it):
        l[0].update(unit_cost="9.00", ext_cost="360.00")
        m[0]["ship_cost"] = m[1]["ship_cost"] = "180.00"
    red = fires("PRICE_DROP_UNMARKED", "1", drop_ed, "an unmarked lower price on an edible")
    t.check("an unmarked lower price elsewhere defaults to a cost change, no tag",
            next(x for x in red[0] if x["row"] == "1a")["pkg_tags_to_apply"] == "none")

    def disc_line(c, i, l, m, it):
        l.append({"line_no": "1", "description": "promo", "units_total": "", "unit_cost": "", "ext_cost": "-40.00",
                  "is_order_level": "N", "order_level_kind": "discount"})
    fires("DEAL_PRINTED", "1", disc_line, "a printed line discount")

    def raise_(c, i, l, m, it):
        l[2].update(unit_cost="22.00", ext_cost="220.00")
        m[3]["ship_cost"] = "220.00"
    fires("CATALOG_COST_RAISE", "3", raise_, "a price above catalog Cost")

    def pending(c, i, l, m, it):
        del it["2"]
    fires("ITEM_PENDING", "2", pending, "a line with no ProductId")

    def credit(c, i, l, m, it):
        l.append({"line_no": "90", "description": "Credit", "units_total": "", "unit_cost": "", "ext_cost": "-50.00",
                  "is_order_level": "Y", "order_level_kind": "credit"})
    rcr = fires("CREDIT_BLEND_NEGATIVE", "4", credit, "a $50 credit blended equally onto a $0.05 sample package")
    r2 = next(x for x in rcr[0] if x["row"] == "2")
    t.check("the credit blends EQUALLY per package: (500 - 50/5) / 100", r2["blended_unit_cost"] == f"{(500 - 10) / 100:.4f}")
    t.check("the credit prints once, as its own order-level row",
            sum(1 for x in rcr[0] if x["row"] == "90" and "enter once" in x["flags"]) == 1)

    def credit_r62(c, i, l, m, it):
        l.append({"line_no": "90", "description": "Credit", "units_total": "", "unit_cost": "", "ext_cost": "-250.00",
                  "is_order_level": "Y", "order_level_kind": "credit"})
        l[3]["ext_cost"], m[4]["ship_cost"], l[3]["unit_cost"] = "100.00", "100.00", "20.00"
        l[3]["description"] = "Acme Mint Vape 1g"
    fires("CREDIT_TRIPS_R62", "2", credit_r62, "a credit pushing an untagged package to <= 0.90 x Cost")

    # R47 R83 R126: `ITM - New PL` rides only SELLABLE packages; the item flips only on a sellable package of it
    def nl(res, row):
        return next(x for x in res[0] if x["row"] == row)

    def pair(label, pred, good, broken, how):
        g, b = pred(_run(*good[:5], programs=good[5])), pred(_run(*broken[:5], programs=broken[5]))
        t.check(f"{label} [breaker: {how}]", g and not b, f"clean={g} broken={b}")

    def ctx(drop_lines=(), drop_pkgs=(), programs=None):
        c, i, l, m, it = copy.deepcopy((cat, inv, lines, man, items))
        return (c, i, [x for x in l if x["line_no"] not in drop_lines], [p for p in m if p["package_id"] not in drop_pkgs],
                it, programs)

    def mixed_ok(res):
        r3, r4 = nl(res, "3"), nl(res, "4")
        return ("ITM - Active after the receipt" in r3["item_tag_flip"] and r4["item_tag_flip"] == r3["item_tag_flip"]
                and r3["new_line_tag_on_package"].startswith("yes") and r4["new_line_tag_on_package"].startswith("no")
                and "ITM - New PL" in r4["itm_tags_to_strip"] and "ITM - New PL" not in r3["itm_tags_to_strip"]
                and res[2]["new_line_packages"] == 1)
    pair("MIXED receipt: the item flips; the sample package strips `ITM - New PL`, the sellable package keeps it",
         mixed_ok, ctx(), ctx(programs={"3": "sample"}), "the paid package is stated a sample too")

    def sample_only_ok(res):
        r4 = nl(res, "4")
        return (r4["item_tag_flip"].startswith("no flip - sample-only receipt") and res[2]["new_line_packages"] == 0
                and "ITM - New PL" in r4["itm_tags_to_strip"] and r4["new_line_tag_on_package"].startswith("no")
                and res[2]["flips"] == {"13": r4["item_tag_flip"]})
    pair("SAMPLE-ONLY new line: no flip, 0 packages carry `ITM - New PL`", sample_only_ok,
         ctx(("3",), ("PKG-D",)), ctx(("3",), ("PKG-D",), {"4": "none"}), "the sample line is stated sellable (`none`)")
    pair("DISPLAY-ONLY new line: no flip, 0 packages carry `ITM - New PL`", sample_only_ok,
         ctx(("3",), ("PKG-D",), {"4": "display"}), ctx(("3",), ("PKG-D",), {"4": "deal"}), "the line is stated a deal")

    def sellable_only_ok(res):
        r3 = nl(res, "3")
        return ("ITM - Active after the receipt" in r3["item_tag_flip"] and r3["itm_tags_to_strip"] == "ITM - Protect"
                and res[2]["new_line_packages"] == 1)
    pair("SELLABLE-ONLY receipt: flips as before; the package keeps `ITM - New PL`", sellable_only_ok,
         ctx(("4",), ("PKG-E",)), ctx(("4",), ("PKG-E",), {"3": "sample"}), "the only package is stated a sample")
    qtext = questions(base[1], base[2], "x")
    t.check("the questions file prints the new-line flip and the package count",
            "packages carrying `ITM - New PL` 1" in qtext and "item 13: ITM - New PL -> ITM - Active" in qtext)

    t.check("stub paths still refuse with exit 2",
            all(main([m]) == EXIT_ABORT for m in ("--enter", "--check", "--vendor")) and main([]) == EXIT_ABORT)
    return t.done()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
