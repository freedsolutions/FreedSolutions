"""receive.py - phase 2 (Receiving) of the dutchie-intake lane. `--prep` is BUILT; `--enter`, `--check`, `--vendor`
are stubs that exit 2.

  python receive.py --prep --lines <lines.csv> --catalog <active.csv> --inventory <inventory.csv>
                    [--intake <intake-vN.csv>] [--manifest <manifest.csv>] [--item <line>=<ProductId>]...
                    [--program <line>=<disposition>]... --tenant <CLAUDE.md> [--out-dir <dir>] [--slug <s>]
                    [--vendor-record <Dutchie vendor>] [--txn-id <final invoice no | SO no>]
                    [--cases <rows.json>] [--party-key <k>]...
                    [--payload <new.json> [--cite <line>=<text>]... [--apex-item <line>=<Apex name>]...
                     [--receipt-date <YYYY-MM-DD>] [--invoice-no <no>] [--apex-invoice <no>]]
  python receive.py --enter | --check | --vendor ...   phase 2 stubs; exit 2
  python receive.py --selftest

`--prep` writes a NEW receipt prep sheet `<slug>-receipt-prep-<date>-vN.csv`, ONE ROW PER METRC PACKAGE (R126), plus
`<slug>-receipt-prep-<date>-vN-questions.md`: every STOP as a question to settle BEFORE the receipt is entered. It reads
files only. It never opens Metrc, Dutchie or a browser, and it never writes a room, a tag or a cost.

Inputs (columns are checked; a missing one ABORTs, never reads as blank):
  --lines      the invoice lines CSV (intake_parse output or the hand-typed lines): line_no, description, units_total,
               unit_cost, ext_cost, is_order_level, order_level_kind. Order-level rows (credit / shipping) ride along.
  --catalog    the Catalog Active export: ProductId, SKU, Product, Master category, Cost, Tags.
  --inventory  the receive-time Inventory snapshot (the FIFO snapshot): SKU, Room, Available, Cost. The default is the
               CSV `receive_snapshot.py` writes from the POS API; the frozen Inventory export is the fallback.
  --intake     optional intake CSV vN: per line `new_productid`, else `copy_source_productid` on EXISTS / RETIRED_MATCH.
               Rows pair to product lines by `invoice_line` == description, each row at most once. The intake gives the
               ITEM ID only: once an item id is known (`--item`, `new_productid`, the EXISTS / RETIRED_MATCH source),
               catalog Cost and the item's tags come from `--catalog` by ProductId, never from the intake's `lane_Cost`
               or `tags` cells. An intake row that pairs to no product line is INTAKE_ROW_UNPAIRED; a product line no
               intake row pairs to (and no `--item`) is LINE_NO_INTAKE_ROW. Both STOP; neither reads as ITEM_PENDING.
  --manifest   optional; the READ-ONLY Metrc manifest read typed to CSV (SKILL.md "Metrc manifest read"):
               package_id, line, metrc_item, qty, ship_cost [, uom, vendor_batch, expiry, map_basis]. `qty` and `uom` are
               what Metrc prints (Operator ruling 2026-10-18): `uom` `g` on flower, pre-rolls, kief and infused flower /
               pre-rolls, `ea` on every other category. A `g` package counts qty / the unit size its `metrc_item` names
               (`Preroll - 0.5g - X` -> 0.5; `5 x 0.5g` -> 2.5); no readable size is MANIFEST_GRAMS_UNSIZED (never a
               guess). A blank `uom` (or `ea`) on a gram-based item, or `g` on a unit-based one, is MANIFEST_UOM_UNREAD.
               Another `uom` value ABORTs. `line` is the reader's
               mapping from the PO / SO / invoice / manifest: the product `line_no` (6 on BOTH packages of a line that
               ships as two; the runner labels the rows 6a / 6b itself). A typed `6a` / `6b` reads as line 6; an `<n><letter>`
               whose `<n>` is not a product line stays MANIFEST_PACKAGE_UNMAPPED. Blank = the runner PROPOSES a line (a
               STOP to confirm). Without a manifest the sheet has one row per product line and a blank package id.
  --item <line>=<ProductId>   the item a line receives against (beats the intake CSV).
  --program <line>=<value>    the disposition the invoice or the vendor's email states (R127): `sample`, `display`,
               `deal`, `tier <n>`, `none`, `cost change`. Beats every default. A sample the vendor states only in an
               email is `--program <line>=sample`.
  --vendor-record / --txn-id  the receive-form header values (below); default the lines' `vendor` / `invoice_no` cells.
  --cases <rows.json> / --party-key <k>   the vendor's OPEN cases (below), the saved rows of the read-only SELECT.
  --payload    also write the receipt-inputs payload: the same inputs as ONE JSON object for the warehouse ingest
               (keys slug, receipt_date, invoice_no, vendor_record, txn_id, apex_invoice, lines, manifest, intake_rows,
               bindings). Rows go as read (every column, `uom` included); manifest / intake_rows are null when not
               given; a binding per line named by --item / --program / --cite / --apex-item. The ingest is stricter than
               the runner, so --payload refuses (ABORT, nothing written) a disposition without its `--cite <line>=<the
               invoice text or the email id>`, a disposition outside the R127 list, a binding to no line of the receipt,
               an item on `*`, a slug that is not lowercase words, and an existing file. `--receipt-date` defaults to
               `--asof`, else today (the warehouse dates its sheet and reads its catalog and stock on that day);
               `--invoice-no` defaults to the lines' `invoice_no` cell, else `--txn-id`. The runner never sends it.

Receive form header (printed at the top of the questions file; platform KB "Receive inventory from a pending Metrc
transfer [PROBE 2026-10-09]" in dutchie-bi-looker/references/dutchie-platform-kb.md):
  * Vendor and Room (`Intake`, R126) are header values that flow down to every row.
  * Transaction ID (Operator ruling 2026-10-09): the vendor's final invoice number when it exists, else the sales-order
    number until one arrives; the mapping that lands in the accounting system is open. The receive form has no
    Transaction ID field (same KB section): a record value on this sheet, never a form field.
  * Count (Operator ruling 2026-10-09): staff verify the drop against Metrc and fix any count issue BEFORE the transfer
    lands as pending in Dutchie. The sheet defaults `physical_count` = the package count (the manifest qty; a `g`
    package counts grams / its unit size) and `qty_match` = Y on every mapped package; no count question is asked.
  * Expiry (Operator ruling 2026-10-23, replaces 2026-10-09): the Metrc lab testing expiration (LTE) from the
    manifest read's `expiry` cell. Dutchie prefills it on the pending-transfer row, but only a CALENDAR pick persists
    at the page Save (same KB section): pick it on every row, then read every row's product and expiry back from the
    saved order before Receive.

Decisions (rules cited per flag; the tenant's R numbers live in RULE below):
  * room: `Intake` on every package (R126). On-hand by room from the snapshot is FIFO guidance, never a room write.
  * `PKG - ` tag (R127; R62 R84 R97): the invoice / email decide, never the price alone. A marked sample -> the sample
    tag; a marked display -> the display tag; a printed line discount, or `--program deal` -> the vendor deal tag;
    `tier <n>` -> `PKG - Tier <n>` (R84, R72). An unmarked price <= SAMPLE_MAX, or an unmarked price below catalog Cost,
    is a STOP question; its proposed default is the deal tag on a tiered master category (flower / pre-roll), else a
    catalog cost change (no tag). A price above catalog Cost is a STOP: the catalog keeps the highest cost. An on-hand
    package cost ABOVE the new unit cost is never a question when the new cost equals catalog Cost: price compression
    is normal (R62 keeps the highest cost on the catalog; only an unmarked LOWER price is asked). `on_hand_pkg_costs`
    is information only. With no item id yet, no price is compared (the pending flag carries the line).
  * strip (R47): every `ITM - ` tag the item carries, except the new-line tag on a SELLABLE package. A sample or display
    package (the sample / display tag) strips the new-line tag too: it never carries it (R47, R83).
  * flip (R83, R126): read from the item's CURRENT catalog tags (only an item carrying the new-line tag can flip; an
    intake row's `tags` cell is never read). A new-line item flips to the active tag after the receipt only when the
    receipt holds at least one SELLABLE package of that item; a sample-only receipt flips nothing and the sheet says "no flip - sample-only
    receipt" (a note, never a write here).
  * discontinued buy (R68, R48): a line whose item carries the discontinue tag (pointer `Discontinue tag`, default
    `ITM - Discontinue`) is DISCONTINUED_BUY, an INFO note: a buy into a discontinued item or line (an MOQ, a
    high-testing batch) is a RECORDED EXCEPTION. The item keeps its tag; the operator writes the reason in the
    sheet's `exception_reason` cell (pre-filled `OWED: ...`) and on the PO. A sample or display package is not a buy
    and stays quiet. The questions file lists every such line; it never blocks the receipt.
  * credit (R126): entered once in the receipt header; Dutchie blends it EQUALLY across the receipt's packages. The
    sheet prints that blend per package (and the R103 extended-cost landed unit for reference).
  * Buy-Get deal (R103, R84): the invoice prices a Buy-Get deal on ONE line (the free case at a penny). The lane reads a
    deal when the same item sits on a paid line AND a penny line (<= SAMPLE_MAX), or a line discount names the deal
    (`buy 4 get 1`, `b4g1`, `bogo`, `free case`). A sample or display line, and a line stated anything but `deal`,
    stays out. It BLENDS: blended unit = (sum of the deal lines' ext - their line discounts) / (sum of the deal's
    package units), rounded to the cent; every package of the deal gets `cost_entered` = that unit and the vendor
    deal tag, and the LAST package takes the remainder so the deal ties to the invoice to the penny (a remainder that
    will not divide to a 4-place unit is BUY_GET_UNTIED, a STOP). The questions file prints the deal math. A penny line with no paid line of its item is
    never blended (a lone penny line keeps its own price and its R127 question). An unmarked penny line inside a deal
    stays PENNY_UNMARKED (R127: asked before intake) with the blend as its proposed default; `--program <line>=deal`,
    or a deal word on the invoice, settles it. The invoice total and catalog Cost are unchanged (R62).
  * cost_entered: the unit cost typed on each package row - the deal's blended unit, else the package's invoice unit.
  * manifest (R126): per line, sum of ship $ == invoice ext, else DEFECT; sum of qty == invoice qty, else STOP unless
    qty is a whole multiple with the $ tied (APEX_UNIT_IS_CASE, INFO: a vendor "unit" was a case). The qty is the
    package COUNT (a `g` package: grams / the unit size). A Metrc item size that differs from the invoice line's size or
    the item's grams (`Product grams`, else its name) is MANIFEST_ITEM_SIZE_MISMATCH, a STOP: a wrong-item ship, never a
    short count. Dutchie converts Metrc grams by the PICKED item's grams, so a wrong-size item halves or doubles the
    count (platform KB "Metrc package quantity is in the item's unit of measure"). A qty that is not a finite number
    (`inf`, `nan`) on any package is unreadable: MANIFEST_QTY_UNREAD (or MANIFEST_GRAMS_UNSIZED on a `g` package), a
    STOP with no count and no qty tie, never a crash; such a package never blends a Buy-Get deal.

Open cases (the read of `intake_cases.py stop`, reused: the same SELECT, fingerprint, block and flags). The header
credit (R126) and the Buy-Get blend (R103) are where a receipt puts a credit into package cost, so the questions file
prints the vendor's open cases (CREDIT_DUE first, with the OPENED detail) and names each open CREDIT_DUE case beside the
header credit and beside each Buy-Get deal. No login here, in two calls:
  1. without `--cases`, on a tenant with a `Case store:` pointer: writes a NEW `<sheet stem>-open-cases-<ts>.sql` (ONE
     read-only SELECT) and asks CASES_UNREAD. The lane runs that SELECT through its OWN read-only warehouse route (the
     tenant's reader role), never the case writer runner, and saves the rows as returned to a `.json` file.
  2. `--cases <rows.json>` with the SAME vendor arguments: prints the block. The vendor = every `vendor` cell of
     `--lines`, every `lane_Vendor` cell of `--intake`, `--vendor-record`, and `--party-key`. A read with another
     fingerprint ABORTs before any file is written.
No `Case store:` pointer (or no `--tenant`) = a quiet INFO CASE_STORE_ABSENT; `--cases` without the pointer ABORTs.
Flags: CASE_CREDIT_DUE STOP, CASE_OPEN INFO, VENDOR_PARTY_UNMATCHED STOP, CASES_UNREAD STOP, CASE_READ_FAILED STOP,
CASE_STORE_ABSENT INFO (intake_cases.py STOP_FLAGS).

Exit: 0 clean (STOP / INFO never fail), 1 DEFECT, 2 ABORT.
"""
import hashlib
import json
import math
import os
import re
import sys
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from intake_common import (EXIT_ABORT, EXIT_DEFECT, EXIT_OK, ITEM_PREFIX, PKG_PREFIX, DEFAULT_ACTIVE_TAG,  # noqa: E402
                           DEFAULT_DISCONTINUE_TAG, DEFAULT_NEW_LINE_TAG, Selftest, abort, fmt_money, get_all, get_flag, money_eq, new_path,
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
    "INTAKE_ROW_UNPAIRED": ("R126", "STOP"), "LINE_NO_INTAKE_ROW": ("R126", "STOP"),
    "CREDIT_TRIPS_R62": ("R62 (R126)", "STOP"), "CREDIT_BLEND_NEGATIVE": ("R126", "STOP"),
    "LANDED_UNRECONCILED": ("R103", "DEFECT"), "DISCONTINUED_BUY": ("R68 (R48)", "INFO"),
    "BUY_GET_BLEND": ("R103 (R84)", "INFO"), "BUY_GET_UNTIED": ("R103", "STOP"),
    "TIER_LIST_COST": ("R127 (R50)", "INFO"), "MANIFEST_COST_UNREAD": ("R126", "INFO"),
    "MANIFEST_ITEM_SIZE_MISMATCH": ("R126", "STOP"), "MANIFEST_UOM_UNREAD": ("R126", "STOP"),
    "MANIFEST_GRAMS_UNSIZED": ("R126", "STOP"), "MANIFEST_QTY_UNREAD": ("R126", "STOP"),
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
    "INTAKE_ROW_UNPAIRED": "This intake row's `invoice_line` matches no product line. Is it the intake for another invoice / SO, or does its line read differently? Fix the pairing or drop `--intake`, then re-run.",
    "LINE_NO_INTAKE_ROW": "No intake row pairs to this line, so no item id is known. Give `--item <line>=<ProductId>` (or an intake row whose `invoice_line` equals the line), then re-run.",
    "CREDIT_TRIPS_R62": "The blended credit lands this package at or below 0.90 x catalog Cost with no `PKG - ` tag (R62 would flag it). Tag it, or settle the credit another way.",
    "BUY_GET_UNTIED": "The deal's remainder does not divide to a 4-place unit on its last package, so the entered total misses the invoice. Enter the last package's cost so its total is the deal total less the other packages, or settle the remainder with the vendor.",
    "CREDIT_BLEND_NEGATIVE": "Dutchie's equal blend makes this package's cost negative. Enter the credit another way (vendor bill or a reissued invoice).",
    "MANIFEST_ITEM_SIZE_MISMATCH": "The Metrc item's size differs from the invoice line or the item's grams: a wrong-item ship, not a short count. Ask the vendor (reissue the invoice for the size shipped, or reject the package) before the receipt. WARNING: Dutchie converts Metrc grams to units by the PICKED item's grams, so receiving into the wrong-size item halves or doubles the on-hand count.",
    "MANIFEST_UOM_UNREAD": "The manifest unit does not fit the item. Flower, pre-rolls, kief and infused flower / pre-rolls are `g` in Metrc; every other category is `ea`. Read the unit from the Incoming grid (the Packages export prints a bare number) and type it in the `uom` cell, then re-run.",
    "MANIFEST_GRAMS_UNSIZED": "A `g` package whose Metrc item names no unit size (or whose grams do not divide by it), so its count is unknown. The runner never guesses a size. Read the size from Metrc or the vendor, then re-run.",
    "MANIFEST_QTY_UNREAD": "The manifest qty is not a readable number (`inf` / `nan`), so the package count is unknown. Read the qty from Metrc and type it in the `qty` cell, then re-run.",
    # the vendor's open cases (intake_cases.py STOP_FLAGS)
    "CASE_CREDIT_DUE": "An open CREDIT_DUE case on this vendor. Read its detail and its ruling (Open cases, above) before you enter a header credit or a Buy-Get blend: the case says whether a credit on this receipt goes into package cost.",
    "VENDOR_PARTY_UNMATCHED": "No vendor party matches the vendor's names, so no case on this vendor can be seen. Re-run with `--party-key <key>`, or confirm that the vendor has no party yet.",
    "CASES_UNREAD": "The open-cases read has not run. Run the `-open-cases-` SQL file read-only through the lane's reader route, save the rows, and re-run with `--cases <rows.json>`.",
    "CASE_READ_FAILED": "The open-cases read returned an error, or found no org. Check the `Case store:` pointer and run the read again.",
}
# a case flag that leaves the vendor's cases unseen: no CREDIT_DUE case can be checked beside a credit
CASES_BLIND = ("CASES_UNREAD", "VENDOR_PARTY_UNMATCHED", "CASE_READ_FAILED")
PREP_COLS = ["row", "line", "invoice_item", "dutchie_productid", "dutchie_sku", "dutchie_name", "expected_qty",
             "unit_cost_invoice", "ext_cost", "landed_unit_cost", "blended_unit_cost", "cost_entered", "deal", "catalog_cost",
             "on_hand_pkg_costs", "physical_count", "qty_match", "metrc_package_id", "metrc_item", "manifest_qty",
             "manifest_ship_cost", "map_basis", "expiry", "receive_room", "pkg_tags_to_apply", "tag_rule",
             "itm_tags_to_strip", "new_line_tag_on_package", "item_tag_flip", "on_hand_snapshot", "vendor_batch",
             "exception_reason", "flags"]
EXCEPTION_OWED = "OWED: why this discontinued item was bought (MOQ, a high-testing batch, ...) - also on the PO (R68)"
TENANT_OPTIONAL = ["Sample tag", "Display tag", "New line tag", "Active tag", "Discontinue tag"]   # the pointers --prep reads when present
KB_RECEIVE = ('platform KB "Receive inventory from a pending Metrc transfer [PROBE 2026-10-09]" '
              '(dutchie-bi-looker/references/dutchie-platform-kb.md)')
# a line discount (or a line) whose words name a Buy-Get deal (R103): `buy 4 get 1`, `b4g1`, `bogo`, `free case`
DEAL_WORDS = re.compile(r"\b(?:buy\s*\d*\s*[-,/]?\s*get\s*\d*(?:\s*free)?|b\d+g\d+|bogo|free\s+(?:case|unit|pack|item)s?)\b",
                        re.IGNORECASE)
STOPWORDS = {"mg", "g", "ct", "10ct", "100mg", "gummies", "gummy", "the", "and", "pk", "pack", "x", "1g", "thc", "cbd"}
# a parser's line-level price-tier row (parsers/fernway.py: "Price tier discount 20% (Price Class X): ...") - list cost
TIER_DISC_RE = re.compile(r"^\s*price tier discount\b", re.I)
# the gram-based Metrc categories (Operator ruling 2026-10-18): flower, pre-rolls, kief and infused flower / pre-rolls.
# EVERY other category is unit-based (`ea`). Read on the item's Category, else its Master category, else the words.
GRAM_BASED = re.compile(r"\b(?:flower|buds?|pre ?rolls?|prerolls?|blunts?|kief)\b", re.I)
MAN_UOMS = ("", "g", "ea")
# a unit size in grams: `5 x 0.5g` / `0.5g x 5` (a pack = n x size), else ONE `0.5g`. A pack COUNT word beside a
# size (`0.5g 5pk` is 0.5 g each, `2.5g 5pk` is 2.5 g in all) is ambiguous: no size, never a guess.
SIZE_PACK = re.compile(r"(?<![\w.])(\d+)\s*x\s*(\d*\.?\d+)\s*g(?:rams?)?\b", re.I)
SIZE_PACK_R = re.compile(r"(?<![\w.])(\d*\.?\d+)\s*g(?:rams?)?\s*x\s*(\d+)\b", re.I)
SIZE_ONE = re.compile(r"(?<![\w.])(\d*\.?\d+)\s*g(?:rams?)?\b", re.I)
PACK_COUNT = re.compile(r"(?<![\w.])\d+\s*-?\s*(?:pk|pack|ct|count)\b", re.I)


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


def unit_grams(text):
    """The unit size in grams a name states: `Preroll - 0.5g - X` -> 0.5; a `5 x 0.5g` pack -> 2.5. None when no
    size, when the name states two different sizes, or when a pack count sits beside a size (`0.5g 5pk`): each or
    in all is not readable from the name (never a guess)."""
    s = str(text or "")
    packs = {round(int(n) * float(g), 6) for n, g in SIZE_PACK.findall(s)}
    packs |= {round(float(g) * int(n), 6) for g, n in SIZE_PACK_R.findall(s)}
    if packs:
        return packs.pop() if len(packs) == 1 else None
    if PACK_COUNT.search(s):
        return None
    ones = {round(float(g), 6) for g in SIZE_ONE.findall(s)}
    return ones.pop() if len(ones) == 1 and next(iter(ones)) > 0 else None


def item_grams(cat):
    """The catalog item's net grams: `Product grams` when the export carries it, else the size its name states."""
    g = cat.get("Product grams")
    if g not in (None, ""):
        return num(g) if num(g) else unit_grams(g)
    return unit_grams(cat.get("Product"))


def gram_based(cat, *words):
    """Metrc carries this item in grams (Operator 2026-10-18). The item's Category, else its Master category; a
    Master category of `Infused` reads the item name; with no item, the Metrc item and invoice words."""
    if cat:
        if (cat.get("Category") or "").strip():
            return bool(GRAM_BASED.search(norm(cat["Category"])))
        mc = norm(cat.get("Master category"))
        return bool(GRAM_BASED.search(mc) or (mc == "infused" and GRAM_BASED.search(norm(cat.get("Product")))))
    return any(GRAM_BASED.search(norm(w)) for w in words)


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
        case_ok = (le is not None and abs(ship - le) < 0.005 and lq and q > lq and math.isfinite(q / lq)
                   and abs(q / lq - round(q / lq)) < 1e-9)
        if price_ok or case_ok:
            cands.append((len(tokens(pkg.get("metrc_item")) & tokens(ln.get("description"))), ln["line_no"]))
    if not cands:
        return "", "no line at this unit price"
    cands.sort(reverse=True)
    if len(cands) == 1 or cands[0][0] > cands[1][0]:
        return cands[0][1], f"unit price + item words ({cands[0][0]} shared)"
    return "", "ambiguous: lines " + ", ".join(c[1] for c in cands if c[0] == cands[0][0])


def _dec(x):
    return Decimal(str(x if x is not None else 0))


def _cents(d):
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _unit_str(d):
    """A unit cost to type: cents when the value is cent-exact, else 4 places (a remainder that does not divide)."""
    return f"{_cents(d):.2f}" if d == _cents(d) else f"{d.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP):.4f}"


def buy_get_groups(prod, pids, programs, disc, disc_named, pk_by_line):
    """R103: the Buy-Get deals on this invoice. Returns one dict per deal (lines, confirmed, gross, discount, total,
    units, packages, basis, blended). A deal = the lines of ONE item (ProductId, else the description without its deal
    words) that are neither a sample nor a display and are stated nothing but `deal`, when they hold a paid line AND a
    penny line, or one of them carries a line discount naming the deal. Units are the deal's PACKAGE units (the
    manifest qty, else the invoice units), so a vendor "unit" that is a case still blends per sellable unit."""
    by_item = {}
    for ln in sorted(prod, key=lambda x: sort_key(x["line_no"])):
        no, desc = ln["line_no"], ln.get("description", "")
        prog = (programs.get(no) or programs.get("*") or "").strip().lower()
        mk = marker(desc)
        if prog in ("sample", "display") or (not prog and mk in ("sample", "display")) or (prog and prog != "deal"):
            continue
        key = pids.get(no) or "desc:" + norm(DEAL_WORDS.sub(" ", desc))
        by_item.setdefault(key, []).append(ln)
    out = []
    for key, lns in by_item.items():
        units = [num(x.get("unit_cost")) for x in lns]
        penny = any(u is not None and u <= SAMPLE_MAX + 1e-9 for u in units)
        paid = any(u is not None and u > SAMPLE_MAX + 1e-9 for u in units)
        named = [x["line_no"] for x in lns if x["line_no"] in disc_named]
        if not ((penny and paid) or named):
            continue
        nos = [x["line_no"] for x in lns]
        gross = sum((_dec(num(x.get("ext_cost"))) for x in lns), Decimal(0))
        less = sum((_dec(disc.get(no, 0.0)) for no in nos), Decimal(0))
        pk_units, n_pk = Decimal(0), 0
        for x in lns:
            pks = pk_by_line.get(x["line_no"]) or []
            if pks:
                pk_units += sum((_dec(num(p.get("qty")) or 0) for p in pks), Decimal(0))
                n_pk += len(pks)
            else:
                pk_units += _dec(num(x.get("units_total")) or 0)
                n_pk += 1
        if not pk_units.is_finite() or pk_units <= 0:   # an unreadable package count (inf / nan) never blends
            continue
        stated = [x["line_no"] for x in lns if (programs.get(x["line_no"]) or programs.get("*") or "").strip().lower() == "deal"]
        worded = [x["line_no"] for x in lns if DEAL_WORDS.search(x.get("description") or "")]
        basis = "a line discount names the deal" if named else "the same item on a paid line and a penny line"
        out.append({"lines": nos, "item": key, "confirmed": bool(stated or named or worded), "gross": gross,
                    "discount": less, "total": gross - less, "units": pk_units, "packages": n_pk, "basis": basis,
                    "blended": _cents((gross - less) / pk_units)})
    return out


def man_qty(p):
    """The manifest qty as Metrc printed it: `50 g` on a gram package, else the typed number."""
    if not p:
        return ""
    return f"{p['_raw_qty']} g" if p.get("_uom") == "g" else p.get("_raw_qty", p.get("qty", ""))


def man_basis(p):
    """The reader's map basis, plus the runner's gram conversion when it made one."""
    if not p:
        return ""
    b = p.get("map_basis", "")
    if p.get("_size"):
        b = "; ".join(x for x in (b, f"{p['_raw_qty']} g / {p['_size']:g} g = {p['qty']}") if x)
    return b


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
         active_tag=DEFAULT_ACTIVE_TAG, discontinue_tag=DEFAULT_DISCONTINUE_TAG):
    """Pure. Returns (rows, exceptions, summary). exceptions: dicts flag, rule, class, row, line, detail."""
    if not deal_tag:
        abort("the vendor deal tag is ruled per tenant (pointer `Vendor deal tag`); none given")
    items, programs = items or {}, programs or {}
    prod = [ln for ln in lines if (ln.get("is_order_level") or "").upper() != "Y" and not (ln.get("order_level_kind") or "").strip()]
    order = [ln for ln in lines if (ln.get("is_order_level") or "").upper() == "Y" and (ln.get("order_level_kind") or "").strip()]
    disc, disc_named, tier = {}, set(), {}
    for ln in lines:
        if (ln.get("order_level_kind") or "") == "discount" and (ln.get("is_order_level") or "").upper() != "Y":
            if TIER_DISC_RE.match(ln.get("description") or ""):
                # a vendor's standing price-tier discount IS the list cost (Operator ruling 2026-10-13): it nets into the
                # line's unit, and it is never a deal, never a deal tag
                tier[ln["line_no"]] = tier.get(ln["line_no"], 0.0) + abs(num(ln.get("ext_cost")) or 0)
                continue
            disc[ln["line_no"]] = disc.get(ln["line_no"], 0.0) + abs(num(ln.get("ext_cost")) or 0)
            if DEAL_WORDS.search(ln.get("description") or ""):
                disc_named.add(ln["line_no"])
    if tier:
        net = []
        for ln in prod:
            t = tier.get(ln["line_no"])
            if t:
                units0, ext0 = num(ln.get("units_total")) or 0, num(ln.get("ext_cost")) or 0
                ln = dict(ln, ext_cost=f"{ext0 - t:.2f}", _tier=f"{t:.2f}",
                          unit_cost=f"{(ext0 - t) / units0:.4f}" if units0 else ln.get("unit_cost"))
            net.append(ln)
        prod = net
    by_pid = {r["ProductId"]: r for r in catalog}
    exc = []

    def add(flag, row, line, detail):
        rule, cls = FLAGS[flag]
        exc.append({"flag": flag, "rule": rule, "class": cls, "row": row, "line": line, "detail": detail})

    # 0. intake rows -> product lines by description, each row at most once. The intake gives the ITEM ID only.
    pair, taken = {}, set()
    for ln in sorted(prod, key=lambda x: sort_key(x["line_no"])):
        key = norm(ln.get("description"))
        for i, r in enumerate(intake or []):
            if i not in taken and norm(r.get("invoice_line")) == key:
                pair[ln["line_no"]] = r
                taken.add(i)
                break
    for i, r in enumerate(intake or []):
        if i not in taken:
            add("INTAKE_ROW_UNPAIRED", "", "", f"intake row {r.get('invoice_line')!r} (verdict {r.get('verdict') or '?'}) "
                                              "pairs to no product line by description; nothing is read from it")

    def resolve(no):
        """(ProductId, source): --item > intake new_productid > the EXISTS / RETIRED_MATCH source; ('', '') = none."""
        ir = pair.get(no, {})
        if items.get(no):
            return items[no], "--item"
        if ir.get("new_productid"):
            return ir["new_productid"], "intake new_productid"
        if ir.get("verdict") in ("EXISTS", "RETIRED_MATCH") and ir.get("copy_source_productid"):
            return ir["copy_source_productid"], f"intake {ir['verdict']} match"
        return "", ""
    pids = {ln["line_no"]: resolve(ln["line_no"])[0] for ln in prod}

    # 1. packages -> lines (the reader's `line` cell; else a proposal)
    pk_by_line, used_qty, mapped = {}, {}, []
    known = {ln["line_no"] for ln in prod}
    for p in manifest or []:
        p = dict(p)
        # Metrc carries a gram-based item in grams (Operator 2026-10-18): `uom` g -> count = grams / the unit size the
        # Metrc item names. No size (or grams that do not divide) keeps the typed qty and is a STOP, never a guess.
        uom = (p.get("uom") or "").strip().lower()
        if uom not in MAN_UOMS:
            abort(f"manifest package {p.get('package_id')}: uom {p.get('uom')!r} is not `g` or `ea` (blank = not read)")
        p["_uom"], p["_raw_qty"] = uom, p.get("qty", "")
        if uom == "g":
            grams, size = num(p.get("qty")), unit_grams(p.get("metrc_item"))
            n = grams / size if grams is not None and size else None
            if n is not None and math.isfinite(n) and n > 0 and abs(n - round(n)) < 1e-6:
                p["qty"], p["_size"] = f"{round(n):d}", size
            else:
                p["_unsized"] = (f"Metrc item {p.get('metrc_item')!r} names no single unit size" if not size
                                 else f"{p.get('qty')} g does not divide by the {size:g} g unit size")
        elif num(p.get("qty")) is not None and not math.isfinite(num(p.get("qty"))):
            # a non-finite count (`inf` / `nan`) is unreadable, as a non-finite gram qty is: no count, no qty tie, a
            # STOP - never a crash in the case-multiple test, never a silent nan pass
            p["_unread"] = f"qty {p.get('qty')!r} is not a finite number"
        line = (p.get("line") or "").strip()
        basis = p.get("map_basis") or ("reader" if line else "")
        m = re.fullmatch(r"(\d+)\s*[A-Za-z]", line)
        if line and line not in known and m and m.group(1) in known:
            line = m.group(1)   # a typed `6a` / `6b` is line 6: the runner labels a split line's rows itself
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

    # 3. Buy-Get deals (R103): blended over every package of the deal, each tagged; the last package takes the remainder
    deals = buy_get_groups(prod, pids, programs, disc, disc_named, pk_by_line)
    deal_of = {}
    for k, g in enumerate(deals, 1):
        g.update(id=f"BG{k}", left=g["packages"], placed=Decimal(0), entered=Decimal(0), rows=[])
        for no in g["lines"]:
            deal_of[no] = g

    rows = []
    new_line_items = {}   # item key -> True once a SELLABLE package of a new-line item is on this receipt (R83 R126)
    for ln in sorted(prod, key=lambda x: sort_key(x["line_no"])):
        no, desc = ln["line_no"], ln.get("description", "")
        units, unit, ext = num(ln.get("units_total")) or 0, num(ln.get("unit_cost")), num(ln.get("ext_cost")) or 0
        ir = pair.get(no, {})
        pid = pids[no]
        cat = by_pid.get(pid, {}) if pid else {}
        if pid and not cat:
            abort(f"line {no}: ProductId {pid} is not in the Active export (retired or mistyped)")
        # catalog Cost and the item's CURRENT tags come from the catalog by ProductId, never from intake lane cells
        cost = num(cat.get("Cost")) if cat else None
        tags = tag_set(cat.get("Tags")) if cat else set()
        mc = cat.get("Master category", "")
        prog = (programs.get(no) or programs.get("*") or "").strip().lower()
        mk = marker(desc)
        landed_r103 = None
        dg = deal_of.get(no)
        if dg and base > 0:
            landed_r103 = (float(dg["total"]) + float(dg["gross"]) / base * o_all) / float(dg["units"])
        elif units and base > 0:
            landed_r103 = (ext - disc.get(no, 0.0) + ext / base * o_all) / units
        line_flags = []

        def lflag(flag, detail):
            line_flags.append(flag)
            add(flag, "", no, detail)

        if ln.get("_tier"):
            lflag("TIER_LIST_COST", f"price-tier discount {ln['_tier']} netted into the line: unit {unit:.2f}, ext {ext:.2f} "
                                    "(the tier price is the list cost; no deal tag)")

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
        elif unit is not None and unit <= SAMPLE_MAX + 1e-9 and not (dg and dg["confirmed"]):
            rule = "R127: disposition owed"
            lflag("PENNY_UNMARKED", f"unit {unit:.2f} <= {SAMPLE_MAX:.2f} and neither the invoice nor a direction says sample, display or deal"
                  + (f"; the same item is on line(s) {', '.join(x for x in dg['lines'] if x != no)} at a paid price, so the "
                     f"sheet PROPOSES a Buy-Get blend (R103): confirm `--program {no}=deal`, or state `sample`" if dg else ""))
        if dg:
            pkg_tag = deal_tag
            rule = ("R103 Buy-Get blend (R84)" if dg["confirmed"] else "R103 PROPOSED: Buy-Get blend (R84) - confirm the penny line")
            lflag("BUY_GET_BLEND", f"{dg['id']} lines {'+'.join(dg['lines'])} ({dg['basis']}): {float(dg['units']):g} units, deal total "
                                   f"${dg['total']:.2f}, blended unit ${dg['blended']:.2f} over {dg['packages']} package(s), "
                                   f"each `{deal_tag}`; the last package takes the remainder")
        if pid and not prog and not pkg_tag and unit is not None and unit > SAMPLE_MAX + 1e-9:
            if cost is None:
                lflag("COST_UNKNOWN", f"item {pid} has no catalog Cost to compare the invoice price with")
            elif unit < cost - 0.005:
                tiered = mc in TIERED_MASTER
                pkg_tag = deal_tag if tiered else ""
                rule = "R127 PROPOSED: " + ("tier deal on a tiered category" if tiered else "catalog cost change")
                lflag("PRICE_DROP_UNMARKED", f"unit {unit:.2f} < catalog Cost {cost:g} with no struck price or printed promo; "
                                             f"default {'`' + deal_tag + '`' if tiered else 'a catalog cost change, no tag'} ({mc or 'master category unknown'})")
        if unit is not None and cost is not None and unit > cost + 0.005 and prog != "cost change" and pkg_tag not in (sample_tag, display_tag):
            lflag("CATALOG_COST_RAISE", f"unit {unit:.2f} > catalog Cost {cost:g}: the catalog keeps the highest cost")
        if not pid and intake is not None and not ir:
            lflag("LINE_NO_INTAKE_ROW", f"no intake row's invoice_line pairs to {desc!r} and no --item: no item id, so no "
                                        "catalog Cost, tag or flip is read for this line")
        elif not pid:
            why = (f"its intake row reads verdict {ir.get('verdict') or '?'} with no new_productid" if ir
                   else "no --item and no intake CSV")
            lflag("ITEM_PENDING", f"no Dutchie ProductId for this line ({why}); catalog Cost, tags and the flip are read "
                                  "once the item is known (create first, or --item)")
        sample_pkg = pkg_tag in (sample_tag, display_tag)   # a sample or display package is never sellable stock
        disc_buy = bool(pid) and discontinue_tag in tags and not sample_pkg
        if disc_buy:
            lflag("DISCONTINUED_BUY", f"item {pid} carries `{discontinue_tag}`: a buy into a discontinued item is a recorded "
                                      "exception (R68). The item keeps the tag; write the reason in `exception_reason` "
                                      "and on the PO")
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
                  "on_hand_snapshot": snap, "expiry": ln.get("expiry_date", ""), "_item": item_key if new_line else "",
                  "exception_reason": EXCEPTION_OWED if disc_buy else ""}

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
                        opid = pids.get(other["line_no"])
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
                # the unit and the size, per package (Operator 2026-10-18; platform KB "Metrc package quantity is in
                # the item's unit of measure")
                inv_size, pid_size = unit_grams(desc), (item_grams(cat) if cat else None)
                for p in pks:
                    pk, gb, mi = p["package_id"], gram_based(cat, p.get("metrc_item"), desc), p.get("metrc_item")
                    if gb and p["_uom"] != "g":
                        lflag("MANIFEST_UOM_UNREAD", f"package {pk}: {'a bare qty' if not p['_uom'] else '`ea`'} "
                                                     f"{p['_raw_qty']} on a gram-based item: Metrc carries it in grams; "
                                                     "the qty reads as a count until `uom` is typed")
                    elif not gb and p["_uom"] == "g":
                        lflag("MANIFEST_UOM_UNREAD", f"package {pk}: `g` on a unit-based item (every category but flower, "
                                                     "pre-rolls, kief and infused flower / pre-rolls is `ea`)")
                    if p.get("_unsized"):
                        lflag("MANIFEST_GRAMS_UNSIZED", f"package {pk}: {p['_raw_qty']} g, {p['_unsized']}; its count is "
                                                        "unknown, so the qty tie is not made")
                    if p.get("_unread"):
                        lflag("MANIFEST_QTY_UNREAD", f"package {pk}: {p['_unread']}; its count is unknown, so the qty tie "
                                                     "is not made")
                    ms, off = unit_grams(mi), []
                    if ms and inv_size and abs(inv_size - ms) > 1e-6:
                        off.append(f"the invoice line is {inv_size:g} g")
                    if ms and pid_size and abs(pid_size - ms) > 1e-6:
                        off.append(f"item {pid} is {pid_size:g} g")
                    if off:
                        conv = ""
                        if p["_uom"] == "g" and pid_size and num(p["_raw_qty"]) is not None:
                            conv = (f"; Dutchie would receive {p['_raw_qty']} g as {num(p['_raw_qty']) / pid_size:g} "
                                    f"unit(s) of the {pid_size:g} g item")
                        lflag("MANIFEST_ITEM_SIZE_MISMATCH", f"package {pk}: Metrc item {mi!r} is {ms:g} g but "
                                                             + " and ".join(off) + " - a wrong-item ship" + conv)
                unsized = any(p.get("_unsized") or p.get("_unread") for p in pks)
                unread = any(num(p.get("ship_cost")) is None for p in pks)
                if unread:
                    lflag("MANIFEST_COST_UNREAD", f"manifest ship $ not read for {sum(1 for p in pks if num(p.get('ship_cost')) is None)} "
                                                  f"package(s): the $ tie is not made; rows take the invoice unit")
                elif abs(ss - ext) >= 0.005:
                    merged_in = any(e["flag"] == "SAMPLE_MERGED" and f"line {no}'s" in e["detail"] for e in exc)
                    lflag("MANIFEST_COST_MISMATCH", f"manifest ship ${ss:.2f} vs invoice ext ${ext:.2f} ({ss - ext:+.2f})"
                          + (" (explained: a sample merged in)" if merged_in else ""))
                if not unsized and abs(sq - units) >= 1e-9:
                    k = sq / units if units else 0
                    if not unread and abs(ss - ext) < 0.005 and units and k > 1 and abs(k - round(k)) < 1e-9:
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
            entered_unit = u if (p and case) else unit
            entered_ext = pext
            deal_cell = ""
            if dg and q:
                dg["left"] -= 1
                qd = _dec(q)
                if dg["left"] == 0:   # the remainder rides the deal's last package so the deal ties to the penny
                    eu = (dg["total"] - dg["placed"]) / qd
                    deal_cell = f"{dg['id']}: lines {'+'.join(dg['lines'])}, blended {dg['blended']:.2f}; REMAINDER package"
                else:
                    eu = dg["blended"]
                    deal_cell = f"{dg['id']}: lines {'+'.join(dg['lines'])}, blended {dg['blended']:.2f}"
                dg["placed"] += dg["blended"] * qd
                eu_s = _unit_str(eu)
                dg["entered"] += Decimal(eu_s) * qd
                dg["rows"].append((rid, (p or {}).get("package_id", ""), f"{q:g}", eu_s))
                entered_unit, entered_ext = float(eu_s), float(Decimal(eu_s) * qd)
            blend = (entered_ext + share) / q if q else None
            r = dict(common, row=rid, expected_qty=f"{q:g}", ext_cost=fmt_money(pext),
                     unit_cost_invoice=fmt_money(u if (p and case) else unit),
                     cost_entered=(dg["rows"][-1][3] if dg and q else fmt_money(entered_unit)), deal=deal_cell,
                     blended_unit_cost="" if blend is None or not order else f"{blend:.4f}",
                     metrc_package_id=(p or {}).get("package_id", ""), metrc_item=(p or {}).get("metrc_item", ""),
                     manifest_qty=man_qty(p), manifest_ship_cost=(p or {}).get("ship_cost", ""),
                     map_basis=man_basis(p), vendor_batch=(p or {}).get("vendor_batch", ""),
                     expiry=(p or {}).get("expiry") or common["expiry"],
                     # staff settle the count against Metrc before the transfer lands as pending (Operator 2026-10-09)
                     # a `g` package counts grams / its unit size; an unsized one has no count yet (a STOP)
                     physical_count="" if not p or p.get("_unsized") or p.get("_unread") else p.get("qty", ""),
                     qty_match="Y" if p and not (p.get("_unsized") or p.get("_unread")) else "")
            rflags = list(line_flags)
            if order and blend is not None:
                if entered_ext + share < -0.005:
                    rflags.append("CREDIT_BLEND_NEGATIVE")
                    add("CREDIT_BLEND_NEGATIVE", rid, no, f"package ext {entered_ext:.2f} + equal share {share:+.2f} = {entered_ext + share:+.2f}")
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
    for g in deals:
        if abs(g["entered"] - g["total"]) >= Decimal("0.005"):
            add("BUY_GET_UNTIED", "", "+".join(g["lines"]), f"{g['id']}: entered ${g['entered']:.4f} vs the deal's invoice "
                                                              f"${g['total']:.2f} - the last package's 4-place unit cannot carry the remainder")
    summary = {"packages": len(mapped), "product_lines": len(prod), "order_level": o_all, "share": share,
               "blend_packages": n_pk,
               "order_lines": [{"line": ln["line_no"], "description": ln.get("description", ""),
                                "kind": ln["order_level_kind"], "ext": num(ln.get("ext_cost")) or 0.0} for ln in order],
               "manifest": manifest is not None, "product_ext": base, "new_line_tag": new_line_tag,
               "new_line_packages": sum(1 for r in rows if r.get("new_line_tag_on_package", "").startswith("yes")),
               "flips": dict(sorted(flips.items())), "discontinue_tag": discontinue_tag,
               "discontinued_buys": [e for e in exc if e["flag"] == "DISCONTINUED_BUY"],
               "buy_get": [{k: g[k] for k in ("id", "lines", "basis", "confirmed", "gross", "discount", "total", "units",
                                              "packages", "blended", "entered", "rows")} for g in deals],
               "deal_tag": deal_tag}
    return rows, exc, summary


def header_values(lines, vendor=None, txn=None):
    """The receive-form header values: Vendor (`--vendor-record`, else the lines' `vendor` cell), Room (R126) and the
    Transaction ID (`--txn-id`, else the lines' `invoice_no` cell: the final invoice no., else the SO no.)."""
    first = lambda col: next((ln.get(col, "").strip() for ln in lines if (ln.get(col) or "").strip()), "")  # noqa: E731
    return {"vendor": vendor or first("vendor"), "room": RECEIVE_ROOM, "txn": txn or first("invoice_no")}


# the receipt-inputs payload (`--payload`): the inputs of ONE receipt as the warehouse ingest procedure takes them.
# The ingest is stricter than the runner (a disposition needs its cite; a binding names a line), so the emitter
# refuses what the ingest would refuse, before anything is written.
PAYLOAD_KEYS = ["slug", "receipt_date", "invoice_no", "vendor_record", "txn_id", "apex_invoice", "lines", "manifest",
                "intake_rows", "bindings"]
PAYLOAD_PROGRAM = re.compile(r"^(?:sample|display|deal|none|cost change|tier \S+)$")
PAYLOAD_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def receipt_payload(lines, intake, manifest, items, programs, cites, apex_items, slug_, receipt_date, invoice_no="",
                    vendor_record="", txn_id="", apex_invoice=""):
    """Pure. The receipt-inputs payload (a dict, PAYLOAD_KEYS order): the rows exactly as --prep read them (every
    column, cells as read), the manifest / intake rows or None when not given, and one binding per line named by
    --item / --program / --cite / --apex-item (`*` = a disposition on every line). ABORTs on what the ingest refuses."""
    if not PAYLOAD_SLUG.fullmatch(slug_ or ""):
        abort(f"--payload: slug {slug_!r} is not lowercase words joined by `-` (the ingest refuses it); give --slug")
    try:
        date.fromisoformat(receipt_date or "")
    except ValueError:
        abort(f"--payload: receipt date {receipt_date!r} is not YYYY-MM-DD; give --receipt-date")
    inv_no = (invoice_no or next((ln.get("invoice_no", "").strip() for ln in lines if (ln.get("invoice_no") or "").strip()), "")
              or (txn_id or "").strip())
    if not inv_no:
        abort("--payload: no invoice number (the lines carry no `invoice_no` cell and no --txn-id); the ingest needs one")
    nos = {(ln.get("line_no") or "").strip() for ln in lines}
    keys = sorted(set(items) | set(programs) | set(cites) | set(apex_items), key=sort_key)
    bindings = []
    for k in keys:
        if k != "*" and k not in nos:
            abort(f"--payload: line {k!r} (--item / --program / --cite / --apex-item) is not a line of this receipt")
        if k == "*" and (items.get(k) or apex_items.get(k)):
            abort("--payload: `*` binds a disposition to every line; an item or an Apex item binds one line")
        prog = (programs.get(k) or "").strip()
        if prog and not PAYLOAD_PROGRAM.fullmatch(prog.lower()):
            abort(f"--payload: line {k} disposition {prog!r} is not sample, display, deal, none, cost change or tier <n> (R127)")
        if prog and not (cites.get(k) or "").strip():
            abort(f"--payload: line {k} disposition {prog!r} has no --cite {k}=<the invoice text or the email id> (R127)")
        bindings.append({"line": k, "item": items.get(k, ""), "program": prog, "cite": cites.get(k, ""),
                         "apex_item": apex_items.get(k, "")})
    rows = lambda rs: None if rs is None else [dict(r) for r in rs]  # noqa: E731
    return {"slug": slug_, "receipt_date": receipt_date, "invoice_no": inv_no, "vendor_record": vendor_record or "",
            "txn_id": txn_id or "", "apex_invoice": apex_invoice or "", "lines": rows(lines), "manifest": rows(manifest),
            "intake_rows": rows(intake), "bindings": bindings}


def payload_inputs(pl):
    """The inverse the warehouse applies (gold.receipt_prep): (lines, intake, manifest, items, programs) from a
    payload - an item / a disposition per binding when it is not blank. The selftest proves payload -> prep() = --prep."""
    items = {b["line"]: b["item"] for b in pl["bindings"] if b.get("item")}
    programs = {b["line"]: b["program"] for b in pl["bindings"] if b.get("program")}
    return pl["lines"], pl["intake_rows"], pl["manifest"], items, programs


def header_block(h):
    """The receive form header, printed before any question (KB_RECEIVE; Operator rulings 2026-10-09)."""
    return ["## Receive form header", "",
            f"- Vendor: {h.get('vendor') or 'NOT READ - give --vendor-record <the Dutchie vendor record>'}"
            " (set once in the header; it flows down to every row)",
            f"- Room: {h.get('room') or RECEIVE_ROOM} (R126; set once in the header; it flows down to every row)",
            f"- Transaction ID: {h.get('txn') or 'NOT READ - give --txn-id'} - the vendor's final invoice number when it "
            "exists, else the sales-order number until one arrives (the mapping that lands in the accounting system is "
            "open). The receive form has no Transaction ID field: a record value, never a form field.",
            "- Count: staff verify the drop against Metrc and fix any count issue BEFORE the transfer lands as pending; "
            "the sheet sets physical_count = the package count (the manifest qty; a gram package counts grams / its unit "
            "size) and qty_match = Y on every mapped package. No count question.",
            "- Expiry: the Metrc lab testing expiration (LTE), the `expiry` column. Dutchie prefills it on each row, but "
            "only a date chosen in the field's calendar persists at Save: pick it on every row.",
            "- After the page Save, before Receive: read every row's product and expiry back from the saved order (a row "
            "can come back re-bound to another row's product, or with its expiry dropped).",
            f"- Source: {KB_RECEIVE}.", ""]


def open_cases(state, org=None, shown=(), keys=(), sql_path=None):
    """Pure. The vendor's open cases for the questions file, from intake_cases.stop_block on the saved read (`state` =
    None no store, 'unread', {'error'} or {'row'}). Returns {text, exc (the case flags as exceptions), credit_due (the
    open CREDIT_DUE cases, oldest first), blind (the flag that leaves the cases unseen, or '')}."""
    import intake_cases as CS
    text, flags = CS.stop_block(state, org, shown, keys, None, sql_path, "re-run `receive.py --prep` with `--cases`",
                                "- At this receipt: the case says whether a credit belongs in package cost - the header "
                                "credit (R126) and a Buy-Get blend (R103). Read it before you enter either.")
    rule = {f: r for f, r, _ in CS.STOP_FLAGS}
    exc = [{"flag": f, "rule": rule[f], "class": CS.STOP_CLASS[f], "row": "", "line": "", "detail": d} for f, d in flags]
    cd = []
    if any(f == "CASE_CREDIT_DUE" for f, _ in flags):
        cd = [c for c in sorted(state["row"]["cases"], key=CS._case_order) if c.get("case_type") == "CREDIT_DUE"]
    return {"text": text, "exc": exc, "credit_due": cd, "blind": next((f for f, _ in flags if f in CASES_BLIND), "")}


def credit_case_lines(cases, where):
    """The lines that name each open CREDIT_DUE case beside a credit `where` the receipt enters (or say none is seen)."""
    if not cases:
        return []
    out = [f"- Open CREDIT_DUE case {c['case_id']} ({c.get('title') or '-'}; "
           f"{'ruling in mail ' + str(c.get('ruled_at') or '')[:10] if c.get('ruling') else 'no ruling in mail'}): "
           f"read its detail (Open cases, above) before you enter {where}. The case says whether this credit goes "
           "into package cost (STOP CASE_CREDIT_DUE)." for c in cases["credit_due"]]
    if cases["blind"]:
        out.append(f"- {cases['blind']}: the vendor's open cases are not seen, so no CREDIT_DUE case can be checked "
                   f"beside {where}.")
    return out


def questions(exc, summary, stem, header=None, cases=None):
    """The questions file. `cases` = open_cases(...) (None = no case read at all; the unit checks)."""
    stops = [e for e in exc if e["class"] in ("STOP", "DEFECT")]
    out = [f"# Receipt prep - questions before the receipt ({stem})", "",
           f"Product lines {summary['product_lines']} · packages {summary['packages']}"
           + ("" if summary["manifest"] else " (no Metrc manifest yet: package ids blank; re-run when it is read)")
           + f" · order-level {summary['order_level']:+.2f}", ""]
    if header is not None:
        out += header_block(header)
    out += ["Nothing is entered in Dutchie until every row below is settled. A DEFECT means the receipt is not entered.", ""]
    if summary.get("flips"):
        out += [f"New-line items (R83 R126): packages carrying `{summary['new_line_tag']}` "
                f"{summary['new_line_packages']} (sellable packages only; R47)."]
        out += [f"- item {k}: {v}" for k, v in summary["flips"].items()] + [""]
    if summary.get("discontinued_buys"):
        out += [f"Discontinued buys (R68): these lines receive an item tagged `{summary['discontinue_tag']}`. Each is a "
                "RECORDED EXCEPTION, never a block: the item keeps the tag; fill `exception_reason` on the sheet and "
                "name the reason on the PO."]
        out += [f"- line {e['line']}: {e['detail']}" for e in summary["discontinued_buys"]] + [""]
    if cases is not None:
        out += [cases["text"], ""]
    # a CREDIT_DUE case and a blind read never come together: the section prints on a credit line or an open case
    if summary.get("order_lines") or (cases and cases["credit_due"]):
        out.append("Header credit (R126): entered ONCE in the receipt header; Dutchie blends it EQUALLY across the "
                   "receipt's packages.")
        for o in summary.get("order_lines") or []:
            out.append(f"- line {o['line']} {o['description'] or o['kind']} {o['ext']:+.2f} ({o['kind']}): "
                       f"{summary['share']:+.4f} per package across {summary.get('blend_packages', 0)} package(s)")
        if not summary.get("order_lines"):
            out.append("- This receipt enters no header credit.")
        out += credit_case_lines(cases, "this header credit") + [""]
    if summary.get("buy_get"):
        out += [f"Buy-Get deals (R103): blended over every package of the deal, each `{summary.get('deal_tag', '')}`; "
                "`cost_entered` is what each package row takes. The invoice total and catalog Cost do not change."]
        for g in summary["buy_get"]:
            last = g["rows"][-1] if g["rows"] else ("", "", "", "")
            out.append(f"- {g['id']} lines {'+'.join(g['lines'])} ({g['basis']}"
                       + ("" if g["confirmed"] else "; PROPOSED until the penny line is confirmed") + f"): units {float(g['units']):g} · "
                       f"ext ${g['gross']:.2f}" + (f" - line discount ${g['discount']:.2f}" if g["discount"] else "")
                       + f" = ${g['total']:.2f} · blended unit ${g['blended']:.2f} · packages {g['packages']} · remainder on "
                       f"{last[1] or 'row ' + str(last[0])} at ${last[3]} · entered ${g['entered']:.2f} = invoice ${g['total']:.2f}")
            out += [f"  - row {r[0]} {r[1] or '(no package id yet)'}: {r[2]} x ${r[3]}" for r in g["rows"]]
        out += credit_case_lines(cases, "a Buy-Get blend (the blend puts the deal's discount into package cost, R103)")
        out.append("")
    if not stops:
        return "\n".join(out + ["No STOP and no DEFECT. The sheet is ready for entry.", ""])
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
    new_line_tag, active_tag, discontinue_tag = DEFAULT_NEW_LINE_TAG, DEFAULT_ACTIVE_TAG, DEFAULT_DISCONTINUE_TAG
    import intake_cases as CS
    org = None
    if tenant:
        import intake_pointers
        # --prep reads the tag pointers and the case store only: a gap there ABORTs, any other gap is a WARNING line
        res = intake_pointers.load_for(tenant, [] if deal_tag else ["Vendor deal tag"],
                                       TENANT_OPTIONAL + [intake_pointers.OPTIONAL_CASE_KEY])
        ptr, org = res["intake"], CS.store_org(res)
        deal_tag = deal_tag or ptr.get("Vendor deal tag")
        sample_tag = ptr.get("Sample tag") or sample_tag
        display_tag = ptr.get("Display tag") or display_tag
        new_line_tag = ptr.get("New line tag") or new_line_tag
        active_tag = ptr.get("Active tag") or active_tag
        discontinue_tag = ptr.get("Discontinue tag") or discontinue_tag
    _, lines = read_csv(lines_p, LINE_REQ, "lines")
    _, catalog = read_csv(cat_p, CAT_REQ, "catalog")
    _, inv = read_csv(inv_p, INV_REQ, "inventory")
    intake = read_csv(get_flag(argv, "--intake"), INTAKE_REQ, "intake")[1] if get_flag(argv, "--intake") else None
    man = read_csv(get_flag(argv, "--manifest"), MAN_REQ, "manifest")[1] if get_flag(argv, "--manifest") else None
    items, programs = parse_directions(argv, "--item"), parse_directions(argv, "--program")
    first = next((ln for ln in lines if ln.get("invoice_no")), {})
    s = get_flag(argv, "--slug") or slug(first.get("invoice_no") or os.path.splitext(os.path.basename(lines_p))[0])
    day = get_flag(argv, "--asof") or date.today().isoformat()
    pl_path, payload = get_flag(argv, "--payload"), None
    if pl_path:
        # built and checked BEFORE prep() and before any file is written: a refusal writes nothing
        if os.path.exists(pl_path):
            abort(f"--payload {pl_path} exists; a payload is never overwritten - name a new file")
        payload = receipt_payload(lines, intake, man, items, programs, parse_directions(argv, "--cite"),
                                  parse_directions(argv, "--apex-item"), s, get_flag(argv, "--receipt-date") or day,
                                  get_flag(argv, "--invoice-no") or "", get_flag(argv, "--vendor-record") or "",
                                  get_flag(argv, "--txn-id") or "", get_flag(argv, "--apex-invoice") or "")
    # the vendor's open cases: read and checked BEFORE any file is written (a stale or foreign read writes nothing)
    cases_p, case_args = get_flag(argv, "--cases"), None
    if not org:
        if cases_p:
            abort("--cases needs the tenant's `Case store: <ORG_CODE> via <runner.ps1>` pointer (the read is scoped by "
                  "its org code)")
        state = None
    else:
        names, keys, shown = CS.vendor_inputs([ln.get("vendor") for ln in lines] + [r.get("lane_Vendor") for r in intake or []]
                                              + [get_flag(argv, "--vendor-record")], get_all(argv, "--party-key"),
                                              "receive --prep (give --vendor-record or --party-key)")
        case_args = (org, names, keys, shown)
        state = (CS.stop_state(org, names, keys, cases_p, "re-run --prep without --cases and run the new SQL")
                 if cases_p else "unread")
    rows, exc, summary = prep(lines, catalog, inv, intake, man, items, programs, deal_tag, sample_tag, display_tag,
                              new_line_tag, active_tag, discontinue_tag)
    out_dir = get_flag(argv, "--out-dir") or os.path.dirname(os.path.abspath(lines_p))
    out = next_version(out_dir, f"{s}-receipt-prep-{day}")
    write_csv(out, PREP_COLS, rows)
    if payload is not None:
        text_pl = json.dumps(payload, ensure_ascii=False, indent=1) + "\n"
        with open(pl_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text_pl)
        print(f"wrote payload {pl_path} ({len(payload['lines'])} line(s), "
              f"{'no manifest' if payload['manifest'] is None else str(len(payload['manifest'])) + ' package(s)'}, "
              f"{len(payload['bindings'])} binding(s); md5 {hashlib.md5(text_pl.encode('utf-8')).hexdigest()})")
    if case_args:
        org, names, keys, shown = case_args
        sql_path = None
        if state == "unread":
            sql_path = CS.write_stop_sql(out_dir, os.path.splitext(os.path.basename(out))[0], org, names, keys)
            print(f"wrote {sql_path} (fingerprint {CS.stop_fingerprint(org, names, keys)})\n"
                  "Run it READ ONLY through the lane's warehouse read route; save the rows as "
                  f"{os.path.splitext(sql_path)[0]}.json; then re-run --prep with the same arguments and --cases "
                  "<that file>.\n")
        cases = open_cases(state, org, shown, keys, sql_path)
    else:
        cases = open_cases(None)
    exc = exc + cases["exc"]
    qpath = new_path(out_dir, os.path.splitext(os.path.basename(out))[0] + "-questions", ".md")
    text = questions(exc, summary, os.path.basename(out),
                     header_values(lines, get_flag(argv, "--vendor-record"), get_flag(argv, "--txn-id")), cases)
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
    # Metrc carries the pre-roll in grams (100 g of a 1g pre-roll = 100) and the rest in `ea` (Operator 2026-10-18)
    man = [{"package_id": "PKG-A", "line": "1", "metrc_item": "Lemon Gummies", "qty": "20", "uom": "ea", "ship_cost": "200.00"},
           {"package_id": "PKG-B", "line": "1", "metrc_item": "Lemon Gummies", "qty": "20", "uom": "ea", "ship_cost": "200.00"},
           {"package_id": "PKG-C", "line": "2", "metrc_item": "Preroll - 1g - Haze", "qty": "100", "uom": "g", "ship_cost": "500.00"},
           {"package_id": "PKG-D", "line": "3", "metrc_item": "Mint Vape", "qty": "10", "uom": "ea", "ship_cost": "200.00"},
           {"package_id": "PKG-E", "line": "4", "metrc_item": "Mint Vape sample", "qty": "5", "uom": "ea", "ship_cost": "0.05"}]
    items = {"1": "11", "2": "12", "3": "13", "4": "13"}
    return cat, inv, lines, man, items


def _run(cat, inv, lines, man, items, programs=None):
    rows, exc, summ = prep(lines, cat, inv, None, man, items, programs, "PKG - Vendor Deal")
    return rows, exc, summ


def _mut(f):
    """A deep copy of the fixture with one mutation applied: (cat, inv, lines, man, items)."""
    import copy
    c = copy.deepcopy(_fixture())
    f(*c)
    return c


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

    def unread(c, i, l, m, it):
        ship(c, i, l, m, it, "PKG-C", "")
    r = fires("MANIFEST_COST_UNREAD", "2", unread, "a package whose ship $ was not read")
    t.check("an unread ship $ is INFO, never a $0.00 MANIFEST_COST_MISMATCH; the row takes the invoice unit",
            not any(e["flag"] == "MANIFEST_COST_MISMATCH" for e in r[1])
            and {x["row"]: x for x in r[0]}["2"]["cost_entered"] == "5.00", str(_flags(r)))

    # a vendor's standing price-tier discount is the LIST cost (Operator 2026-10-13): line 2 lists at 6.25, tier 20% -> 5.00
    def tiered(c, i, l, m, it, label="Price tier discount 20% (Price Class P1): Acme Haze Pre-Roll 1g"):
        l[1]["unit_cost"], l[1]["ext_cost"] = "6.25", "625.00"
        l.append({"line_no": "2", "description": label, "units_total": "", "unit_cost": "", "ext_cost": "-125.00",
                  "is_order_level": "N", "order_level_kind": "discount", "expiry_date": ""})
    r = fires("TIER_LIST_COST", "2", tiered, "a printed price-tier discount")
    r2 = {x["row"]: x for x in r[0]}["2"]
    t.check("a price-tier discount nets into the unit: cost_entered 5.00 = catalog Cost, no tag, no raise, no deal, $ ties",
            r2["cost_entered"] == "5.00" and r2["pkg_tags_to_apply"] == "none"
            and not any(e["flag"] in ("CATALOG_COST_RAISE", "DEAL_PRINTED", "MANIFEST_COST_MISMATCH") for e in r[1]),
            f"{r2['cost_entered']} {r2['pkg_tags_to_apply']} {_flags(r)}")
    r = _run(*_mut(lambda c, i, l, m, it: tiered(c, i, l, m, it, "Line discount: Acme Haze Pre-Roll 1g")))
    t.check("BREAKER: the same discount NOT labelled a price tier stays a printed deal (DEAL_PRINTED, deal tag)",
            ("DEAL_PRINTED", "2") in _flags(r) and ("TIER_LIST_COST", "2") not in _flags(r), str(_flags(r)))

    def qty(c, i, l, m, it):
        next(p for p in m if p["package_id"] == "PKG-C")["qty"] = "90"
    fires("MANIFEST_QTY_MISMATCH", "2", qty, "a 10-unit short package")

    # Metrc carries a gram-based item in grams (Operator 2026-10-18). A wrong-size ship: the invoice bills 100 x 1g
    # pre-rolls; Metrc ships `Preroll - 0.5g` x 50 g = 100 pre-rolls at the same $. Not a short count: a wrong item.
    def half_g(c, i, l, m, it, qty_="50", uom="g", item="Preroll - 0.5g - Haze"):
        next(p for p in m if p["package_id"] == "PKG-C").update(metrc_item=item, qty=qty_, uom=uom)
    rw = fires("MANIFEST_ITEM_SIZE_MISMATCH", "2", half_g, "50 g of a 0.5g pre-roll billed as 100 x 1g")
    rw2 = next(x for x in rw[0] if x["row"] == "2")
    t.check("the wrong-size ship reads 50 g / 0.5 g = 100 = the invoice qty: no MANIFEST_QTY_MISMATCH; a STOP that "
            "names Dutchie's conversion by the picked item's grams",
            not any(e["flag"] == "MANIFEST_QTY_MISMATCH" for e in rw[1]) and rw2["expected_qty"] == "100"
            and rw2["manifest_qty"] == "50 g" and rw2["physical_count"] == "100"
            and any(e["flag"] == "MANIFEST_ITEM_SIZE_MISMATCH" and e["class"] == "STOP"
                    and "is 0.5 g but the invoice line is 1 g and item 12 is 1 g" in e["detail"]
                    and "Dutchie would receive 50 g as 50 unit(s) of the 1 g item" in e["detail"] for e in rw[1]),
            str(_flags(rw)))
    def size_detail(res):
        return next((e["detail"] for e in res[1] if e["flag"] == "MANIFEST_ITEM_SIZE_MISMATCH"), "")
    leg_item = _run(*_mut(lambda c, i, l, m, it: (half_g(c, i, l, m, it), l[1].update(description="Acme Haze Pre-Roll"))))
    leg_inv = _run(*_mut(lambda c, i, l, m, it: (half_g(c, i, l, m, it), it.pop("2"))))
    t.check("each leg fires alone: the item's grams (invoice names no size), the invoice size (no item yet)",
            "item 12 is 1 g" in size_detail(leg_item) and "invoice line" not in size_detail(leg_item)
            and "the invoice line is 1 g" in size_detail(leg_inv) and "item 12" not in size_detail(leg_inv),
            f"{size_detail(leg_item)!r} / {size_detail(leg_inv)!r}")
    rq = questions(rw[1], rw[2], "x")
    t.check("the questions file asks the vendor (wrong-item ship) and warns that Dutchie converts by the picked item",
            "wrong-item ship" in rq and "Dutchie converts Metrc grams to units by the PICKED item's grams" in rq)
    rold = _run(*_mut(lambda c, i, l, m, it: half_g(c, i, l, m, it, uom="")))
    t.check("BREAKER: the old reading (a bare 50 typed as a count) is a false short ship; the bare qty is MANIFEST_UOM_UNREAD",
            ("MANIFEST_QTY_MISMATCH", "2") in _flags(rold) and ("MANIFEST_UOM_UNREAD", "2") in _flags(rold), str(_flags(rold)))
    rok = _run(*_mut(lambda c, i, l, m, it: half_g(c, i, l, m, it, qty_="100", item="Preroll - 1g - Haze")))
    t.check("CONTROL: 100 g of the billed 1g pre-roll is quiet (no size, unit or qty flag)",
            not [e for e in rok[1] if e["flag"].startswith("MANIFEST_")], str(_flags(rok)))
    fires("MANIFEST_UOM_UNREAD", "2", lambda c, i, l, m, it: half_g(c, i, l, m, it, qty_="100", uom="", item="Preroll - 1g - Haze"),
          "a bare qty (no `uom`) on a pre-roll")
    fires("MANIFEST_UOM_UNREAD", "2", lambda c, i, l, m, it: half_g(c, i, l, m, it, qty_="100", uom="ea", item="Preroll - 1g - Haze"),
          "`ea` on a pre-roll")
    fires("MANIFEST_UOM_UNREAD", "3", lambda c, i, l, m, it: m[3].update(uom="g", metrc_item="Mint Vape 1g"),
          "`g` on a vape (unit-based)")
    # 50 g against 100 invoice units: a qty tie on the typed grams WOULD fire, so its absence is the proof
    ru = fires("MANIFEST_GRAMS_UNSIZED", "2", lambda c, i, l, m, it: half_g(c, i, l, m, it, item="Haze Pre-Roll"),
               "a `g` package whose Metrc item names no size")
    t.check("an unsized `g` package is never guessed: no qty tie (50 g vs 100 units stays quiet), no count on the row",
            not any(e["flag"] == "MANIFEST_QTY_MISMATCH" for e in ru[1])
            and next(x for x in ru[0] if x["row"] == "2")["physical_count"] == "", str(_flags(ru)))
    fires("MANIFEST_GRAMS_UNSIZED", "2", lambda c, i, l, m, it: half_g(c, i, l, m, it, qty_="100", item="Preroll - 0.3g - Haze"),
          "grams that do not divide by the unit size (100 g / 0.3 g)")
    fires("MANIFEST_GRAMS_UNSIZED", "2", lambda c, i, l, m, it: half_g(c, i, l, m, it, qty_="inf", item="Preroll - 1g - Haze"),
          "a non-finite gram qty (`inf`: no count, no crash)")

    def pack(c, i, l, m, it):
        l[1].update(description="Acme Haze Pre-Roll 5 x 0.5g", units_total="50", unit_cost="10.00", ext_cost="500.00")
        next(x for x in c if x["ProductId"] == "12").update(Product="Acme | Pre-Roll | Haze | 0.5g 5pk", Cost="10",
                                                           **{"Product grams": "2.5g"})
        half_g(c, i, l, m, it, qty_="125", item="Preroll Pack - 5 x 0.5g - Haze")
    rpk = _run(*_mut(pack))
    t.check("a pack: 125 g of a 5 x 0.5g pack (2.5 g) = 50 packs, ties to the invoice's 50, sizes agree",
            next(x for x in rpk[0] if x["row"] == "2")["expected_qty"] == "50"
            and not [e for e in rpk[1] if e["flag"].startswith("MANIFEST_")], str(_flags(rpk)))
    t.check("unit_grams reads one size or a pack, never a guess",
            [unit_grams(x) for x in ("Preroll - 0.5g - Haze #5", "Preroll Pack - 5 x 0.5g - X", "X 0.5g x 5",
                                     "Flower - 3.5 g - Kush", "Monkey x Tina 0.5g Pre-Roll", "X 0.5g 5pk", "X 2.5g 5pk",
                                     "Lemon Gummies 100mg 10ct", "Haze 1g / 0.5g", "b4g1 promo", "")]
            == [0.5, 2.5, 2.5, 3.5, 0.5, None, None, None, None, None, None])
    t.check("item grams: `Product grams` beats the name (a `0.5g 5pk` name reads no size; its 2.5g cell does)",
            item_grams({"Product": "X | 0.5g 5pk", "Product grams": "2.5g"}) == 2.5
            and item_grams({"Product": "X | 0.5g 5pk"}) is None and item_grams({"Product": "X | 1g"}) == 1.0)
    t.check("gram-based reads the Category, else the Master category (Infused reads the name), else the words",
            gram_based({"Category": "Infused Pre-Roll Single", "Master category": "Infused"})
            and gram_based({"Category": "Bud", "Master category": "Flower"})
            and gram_based({"Master category": "Infused", "Product": "X | Infused Pre-Roll 1g"})
            and gram_based({}, "Preroll - 0.5g - X") and gram_based({"Master category": "Kief"})
            and not gram_based({"Master category": "Vaporizer", "Product": "Flower Vape 1g"})
            and not gram_based({"Category": "Gummies", "Master category": "Edible", "Product": "Elderflower Gummies"})
            and not gram_based({"Master category": "Infused", "Product": "X | Infused Chocolate"}))
    try:
        _run(*_mut(lambda c, i, l, m, it: m[0].update(uom="oz")))
        bad_uom = False
    except SystemExit as e:
        bad_uom = e.code == EXIT_ABORT
    t.check("a `uom` that is not g / ea ABORTs (never read as a count)", bad_uom)

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

    # manifest `line` cell: the product line_no; a typed `<n><letter>` reads as line <n> (the runner labels rows itself)
    def split_typed(c, i, l, m, it):
        m[0]["line"], m[1]["line"] = "1a", "1b"
    c = copy.deepcopy((cat, inv, lines, man, items))
    split_typed(*c)
    rs = _run(*c)
    t.check("a typed `1a` / `1b` manifest line reads as line 1: rows 1a / 1b, no MANIFEST_PACKAGE_UNMAPPED",
            {"1a", "1b"} <= {x["row"] for x in rs[0]} and not any(e["flag"] == "MANIFEST_PACKAGE_UNMAPPED" for e in rs[1]),
            str(_flags(rs)))

    def split_bad(c, i, l, m, it):
        m[0]["line"] = "9a"
    rb = fires("MANIFEST_PACKAGE_UNMAPPED", "9a", split_bad, "a typed `9a` whose 9 is not a product line")
    t.check("an `<n><letter>` whose <n> is not a line stays a DEFECT",
            any(e["flag"] == "MANIFEST_PACKAGE_UNMAPPED" and e["class"] == "DEFECT" for e in rb[1]))
    t.check("physical_count = the package count and qty_match = Y on every mapped package (count settled against Metrc); "
            "the pre-roll's 100 g / 1 g prints manifest_qty `100 g`, count 100",
            all(r["physical_count"] == r["expected_qty"] and r["qty_match"] == "Y" for r in base[0] if r.get("metrc_package_id"))
            and rows["1a"]["physical_count"] == "20" and rows["2"]["manifest_qty"] == "100 g"
            and rows["2"]["physical_count"] == "100" and rows["2"]["map_basis"].endswith("100 g / 1 g = 100"))

    # the intake gives the item id only: catalog Cost and the CURRENT tags come from the catalog by ProductId
    def intake_of(lines_, verdict="EXISTS", pid_of=None, **cells):
        pid_of = pid_of if pid_of is not None else items
        return [dict({"invoice_line": x["description"], "verdict": verdict, "new_productid": "",
                      "copy_source_productid": pid_of.get(x["line_no"], ""), "create_name_FINAL": "", "tags": "",
                      "lane_Cost": ""}, **cells) for x in lines_ if x["line_no"] in pid_of]

    def via_intake(cat_=None, intake_=None, items_=None, lines_=None):
        lines_ = lines_ or lines
        return prep(lines_, cat_ or cat, inv, intake_ if intake_ is not None else intake_of(lines_, lane_Cost="99",
                    tags="ITM - New PL"), man, items_ if items_ is not None else {}, None, "PKG - Vendor Deal")
    ri = via_intake()
    r1a = next(x for x in ri[0] if x["row"] == "1a")
    t.check("an EXISTS intake row resolves the item; catalog_cost is the catalog's, never the intake lane_Cost",
            r1a["dutchie_productid"] == "11" and r1a["catalog_cost"] == "10"
            and not any(e["flag"] in ("PRICE_DROP_UNMARKED", "CATALOG_COST_RAISE") for e in ri[1]), str(_flags(ri)))
    cat12 = copy.deepcopy(cat)
    cat12[0]["Cost"] = "12"
    t.check("FIRES: the catalog Cost (not the lane cell) is what the price is compared with [breaker: catalog Cost 12]",
            any(e["flag"] == "PRICE_DROP_UNMARKED" and e["line"] == "1" for e in via_intake(cat12)[1]))
    t.check("an intake `tags` cell never flips an item: the flip reads the item's CURRENT catalog tags (R83)",
            r1a["item_tag_flip"] == "" and set(ri[2]["flips"]) == {"13"}, str(ri[2]["flips"]))
    catnl = copy.deepcopy(cat)
    catnl[0]["Tags"] = "ITM - New PL"
    t.check("FIRES: an item the catalog tags new-line flips [breaker: catalog item 11 carries the new-line tag]",
            "11" in via_intake(catnl)[2]["flips"])
    pend = via_intake(intake_=intake_of(lines, verdict="NEW_PL", lane_Cost="12", tags="ITM - New PL"))
    t.check("a pending line (intake row, no item id) reads no lane_Cost and no tag: ITEM_PENDING names the verdict, "
            "no PRICE_DROP_UNMARKED, no flip",
            any(e["flag"] == "ITEM_PENDING" and "verdict NEW_PL" in e["detail"] for e in pend[1])
            and not any(e["flag"] == "PRICE_DROP_UNMARKED" for e in pend[1]) and set(pend[2]["flips"]) <= {"13"},
            str(_flags(pend)))
    stray = intake_of(lines) + [{"invoice_line": "Some Other Vendor Item 1g", "verdict": "EXISTS", "new_productid": "",
                                 "copy_source_productid": "12", "create_name_FINAL": "", "tags": "", "lane_Cost": ""}]
    ru = via_intake(intake_=stray)
    t.check("INTAKE_ROW_UNPAIRED: an intake row pairing to no product line is its own STOP, printed in the questions",
            any(e["flag"] == "INTAKE_ROW_UNPAIRED" and e["class"] == "STOP" for e in ru[1])
            and "INTAKE_ROW_UNPAIRED" in questions(ru[1], ru[2], "x")
            and not any(e["flag"] == "INTAKE_ROW_UNPAIRED" for e in via_intake(intake_=intake_of(lines))[1]))
    short = [x for x in intake_of(lines) if x["invoice_line"] != lines[1]["description"]]
    rl = via_intake(intake_=short)
    t.check("LINE_NO_INTAKE_ROW: a product line no intake row pairs to is its own STOP, never ITEM_PENDING",
            ("LINE_NO_INTAKE_ROW", "2") in _flags(rl) and ("ITEM_PENDING", "2") not in _flags(rl)
            and "LINE_NO_INTAKE_ROW" in questions(rl[1], rl[2], "x")
            and ("LINE_NO_INTAKE_ROW", "2") not in _flags(via_intake(intake_=short, items_={"2": "12"})))

    # R62: an on-hand package cost ABOVE the new unit cost is price compression when new cost == catalog Cost
    inv_hi = copy.deepcopy(inv) + [{"SKU": "9013", "Room": "Order Fulfillment", "Available": "3", "Cost": "22"}]
    rh = prep(lines, cat, inv_hi, None, man, items, None, "PKG - Vendor Deal")
    t.check("QUIET: an on-hand pkg cost above the new cost (new == catalog Cost) raises no question",
            next(x for x in rh[0] if x["row"] == "3")["on_hand_pkg_costs"] == "22"
            and not any(e["line"] == "3" and e["class"] in ("STOP", "DEFECT") for e in rh[1]), str(_flags(rh)))
    l18 = copy.deepcopy(lines)
    l18[2].update(unit_cost="18.00", ext_cost="180.00")
    m18 = copy.deepcopy(man)
    m18[3]["ship_cost"] = "180.00"
    t.check("FIRES: the same shape with the new cost BELOW catalog Cost and no deal marked is PRICE_DROP_UNMARKED",
            ("PRICE_DROP_UNMARKED", "3") in _flags(prep(l18, cat, inv_hi, None, m18, items, None, "PKG - Vendor Deal")))

    hq = questions(base[1], base[2], "x", header_values([dict(lines[0], vendor="Acme Supply", invoice_no="SO-1001")]))
    t.check("the questions header prints Vendor, Room and the Transaction ID (receive form header values)",
            "- Vendor: Acme Supply" in hq and "- Room: Intake" in hq and "- Transaction ID: SO-1001" in hq
            and "physical_count = the package count" in hq and "Expiry: the Metrc lab testing expiration" in hq
            and "read every row's product and expiry back" in hq and "blank on entry" not in hq)
    t.check("FIRES: an unread vendor / transaction id is named, never blank",
            "Vendor: NOT READ" in questions(base[1], base[2], "x", header_values(lines))
            and "- Transaction ID: INV-9" in questions(base[1], base[2], "x", header_values(lines, txn="INV-9")))

    # R68 (R48): a buy into a discontinued item is a recorded exception - an INFO note and an owed reason, never a block
    def disc(c, i, l, m, it):
        next(x for x in c if x["ProductId"] == "12")["Tags"] = "ITM - Discontinue"
    rdb = fires("DISCONTINUED_BUY", "2", disc, "a line receiving an item tagged `ITM - Discontinue`")
    t.check("DISCONTINUED_BUY is INFO: no STOP, no DEFECT, the receipt stays clean",
            any(e["flag"] == "DISCONTINUED_BUY" and e["class"] == "INFO" for e in rdb[1])
            and not [e for e in rdb[1] if e["class"] in ("STOP", "DEFECT")], str(_flags(rdb)))
    t.check("the flagged row owes an exception_reason; the control rows leave it blank",
            nl(rdb, "2")["exception_reason"].startswith("OWED") and "DISCONTINUED_BUY" in nl(rdb, "2")["flags"]
            and all(r.get("exception_reason", "") == "" for r in base[0]))
    t.check("the item keeps its tag: the item-flip column stays empty on a discontinued buy",
            nl(rdb, "2")["item_tag_flip"] == "")
    qd = questions(rdb[1], rdb[2], "x")
    t.check("the questions file lists the discontinued buy (and the control lists none)",
            "Discontinued buys (R68)" in qd and "- line 2: item 12 carries `ITM - Discontinue`" in qd
            and "Discontinued buys" not in questions(base[1], base[2], "x"))

    def disc13(c, i, l, m, it):
        next(x for x in c if x["ProductId"] == "13")["Tags"] = "ITM - Discontinue"
    g13 = _mut(disc13)
    pair("a sample package of a discontinued item is not a buy: line 3 (sellable) fires, line 4 (sample) is quiet",
         lambda res: ("DISCONTINUED_BUY", "3") in _flags(res) and ("DISCONTINUED_BUY", "4") not in _flags(res),
         tuple(g13) + (None,), tuple(_mut(disc13)) + ({"4": "none"},), "the sample line is stated sellable (`none`)")
    renamed = [dict(x, Tags="ITM - Stop Buy") if x["ProductId"] == "12" else x for x in cat]
    t.check("FIRES: the tenant pointer renames the tag [breaker: the default name on a renamed tag is quiet]",
            ("DISCONTINUED_BUY", "2") in _flags(prep(lines, renamed, inv, None, man, items, None, "PKG - Vendor Deal",
                                                    discontinue_tag="ITM - Stop Buy"))
            and ("DISCONTINUED_BUY", "2") not in _flags(prep(lines, renamed, inv, None, man, items, None, "PKG - Vendor Deal")))
    t.check("a pending line (no item id) reads no tag, so never fires",
            not any(e["flag"] == "DISCONTINUED_BUY" for e in
                    prep(lines, [dict(x, Tags="ITM - Discontinue") for x in cat], inv, None, man, {}, None, "PKG - Vendor Deal")[1]))

    # R103 (amended 2026-10-11): a Buy-Get deal priced on ONE invoice line is BLENDED over every package of the deal,
    # each tagged; the last package takes the remainder so the deal ties to the invoice to the penny. Synthetic
    # buy-4-get-1: 4 paid cases of 10 at 18.37 + 1 free case of 10 at 0.01 (+ a marked 1-unit sample beside it).
    bg_cat = cat + [{"ProductId": "14", "SKU": "9014", "Product": "Acme | Flower | Kush | 3.5g", "Master category": "Flower",
                     "Cost": "18.37", "Tags": "ITM - Active"}]

    def kush(units, pid, line, ship, item="Flower - 3.5g - Kush"):
        """A flower package as Metrc prints it: grams (units x 3.5 g), `uom` g."""
        return {"package_id": pid, "line": line, "metrc_item": item, "qty": f"{units * 3.5:g}", "uom": "g", "ship_cost": ship}

    def bg_ln(no, desc, units, unit, **kw):
        return dict({"line_no": no, "description": desc, "units_total": str(units), "unit_cost": f"{unit:.2f}",
                     "ext_cost": f"{units * unit:.2f}", "is_order_level": "N", "order_level_kind": "", "expiry_date": ""}, **kw)

    def bg(paid=18.37, programs=None, drop_paid=False, extra=()):
        ls = [bg_ln("1", "Acme Kush Flower 3.5g", 40, paid), bg_ln("2", "Acme Kush Flower 3.5g", 10, 0.01),
              bg_ln("3", "Acme Kush Flower 3.5g (sample)", 1, 0.01)] + list(extra)
        mf = [kush(10, f"BG-{k}", "1", f"{10 * paid:.2f}") for k in range(1, 5)]
        mf += [kush(10, "BG-5", "2", "0.10"), kush(1, "BG-S", "3", "0.01", "Flower - 3.5g - Kush sample")]
        if drop_paid:
            ls = [x for x in ls if x["line_no"] != "1"]
            mf = [p for p in mf if p["line"] != "1"]
        return prep(ls, bg_cat, inv, None, mf, {"1": "14", "2": "14", "3": "14"},
                    {"2": "deal"} if programs is None else programs, "PKG - Vendor Deal")

    DEAL_ROWS = ("1a", "1b", "1c", "1d", "2")

    def rows_of(res):
        return {x["row"]: x for x in res[0]}

    def entered_total(rw):
        return sum(Decimal(rw[k]["cost_entered"]) * Decimal(rw[k]["expected_qty"]) for k in DEAL_ROWS if k in rw)

    def bg_ok(res):
        rw = rows_of(res)
        if not all(k in rw for k in DEAL_ROWS + ("3",)):
            return False
        return ([rw[k]["cost_entered"] for k in DEAL_ROWS] == ["14.70"] * 4 + ["14.69"]
                and all(rw[k]["pkg_tags_to_apply"] == "PKG - Vendor Deal" for k in DEAL_ROWS)
                and entered_total(rw) == Decimal("734.90")
                and rw["3"]["pkg_tags_to_apply"] == DEFAULT_SAMPLE_TAG and rw["3"]["cost_entered"] == "0.01"
                and not [e for e in res[1] if e["class"] in ("STOP", "DEFECT")])

    def bpair(label, pred, good, broken, how):
        g, b = pred(good), pred(broken)
        t.check(f"{label} [breaker: {how}]", g and not b, f"clean={g} broken={b}")

    bg_clean = bg()
    bpair("BUY-4-GET-1: 5 packages at the blended 14.70, the remainder 14.69 on the last, 734.90 ties to the invoice, all 5 "
          "`PKG - Vendor Deal`; the sample beside it stays `PKG - Employee` at 0.01", bg_ok, bg_clean, bg(drop_paid=True),
          "the paid line is gone (a lone penny line)")
    bpair("a lone penny line is never blended: PENNY_UNMARKED (R127) at its own price, no BUY_GET_BLEND",
          lambda res: (("PENNY_UNMARKED", "2") in _flags(res) and not any(e["flag"] == "BUY_GET_BLEND" for e in res[1])
                       and rows_of(res)["2"]["cost_entered"] == "0.01" and rows_of(res)["2"]["pkg_tags_to_apply"] == "none"),
          bg(drop_paid=True, programs={}), bg(programs={}), "a paid line of the same item beside it")
    bpair("a lone penny line stated `deal` keeps its own price (nothing to blend over)",
          lambda res: (("DEAL_PRINTED", "2") in _flags(res) and rows_of(res)["2"]["cost_entered"] == "0.01"
                       and not any(e["flag"] == "BUY_GET_BLEND" for e in res[1])),
          bg(drop_paid=True), bg_clean, "the paid line is back")

    def one_remainder(res):
        rw = rows_of(res)
        diff = [k for k in DEAL_ROWS if rw[k]["cost_entered"] != res[2]["buy_get"][0]["blended"].to_eng_string()]
        return diff == ["2"] and rw["2"]["deal"].endswith("REMAINDER package") and entered_total(rw) == res[2]["buy_get"][0]["total"]
    bpair("the remainder lands on ONE package, the deal's last, and the deal still ties", one_remainder, bg_clean,
          bg(paid=18.36), "a deal whose blend divides to the cent (18.36: 734.50 / 50 = 14.69, no remainder)")
    t.check("CONTROL: a cent-exact deal ties with every package at the blended unit",
            [rows_of(bg(paid=18.36))[k]["cost_entered"] for k in DEAL_ROWS] == ["14.69"] * 5
            and entered_total(rows_of(bg(paid=18.36))) == Decimal("734.50"))
    bpair("the tag rides EVERY package of the deal, never only the penny one",
          lambda res: all(rows_of(res)[k]["pkg_tags_to_apply"] == "PKG - Vendor Deal" for k in DEAL_ROWS), bg_clean,
          bg(programs={"2": "sample"}), "the penny line is stated a sample (no deal: the paid cases carry no tag)")
    bpair("an unmarked penny line inside a deal is still asked: PENNY_UNMARKED, the blend PROPOSED",
          lambda res: (any(e["flag"] == "PENNY_UNMARKED" and e["line"] == "2" and "PROPOSES a Buy-Get blend" in e["detail"]
                           for e in res[1]) and rows_of(res)["2"]["tag_rule"].startswith("R103 PROPOSED")
                       and rows_of(res)["1a"]["cost_entered"] == "14.70"),
          bg(programs={}), bg_clean, "`--program 2=deal` settles it")
    t.check("a deal word on the penny line itself confirms the deal (no question)",
            not any(e["flag"] == "PENNY_UNMARKED" for e in
                    prep([bg_ln("1", "Acme Kush Flower 3.5g", 40, 18.37), bg_ln("2", "Acme Kush Flower 3.5g - buy 4 get 1", 10, 0.01)],
                         bg_cat, inv, None, None, {"1": "14", "2": "14"}, {}, "PKG - Vendor Deal")[1]))

    def named(words):
        ls = [bg_ln("1", "Acme Kush Flower 3.5g", 50, 18.37),
              {"line_no": "1", "description": words, "units_total": "", "unit_cost": "", "ext_cost": "-183.70",
               "is_order_level": "N", "order_level_kind": "discount"}]
        mf = [kush(10, f"ND-{k}", "1", "183.70") for k in range(1, 6)]
        return prep(ls, bg_cat, inv, None, mf, {"1": "14"}, None, "PKG - Vendor Deal")
    bpair("a line discount NAMING the deal blends the line over its 5 packages (14.70 x4 + 14.68, ties 734.80)",
          lambda res: ([x["cost_entered"] for x in res[0]] == ["14.70"] * 4 + ["14.68"]
                       and ("BUY_GET_BLEND", "1") in _flags(res)
                       and all(x["pkg_tags_to_apply"] == "PKG - Vendor Deal" for x in res[0])),
          named("Buy 4 Get 1 free case"), named("Promo discount"), "the discount names no deal (package-specific, R62)")
    t.check("DEAL_WORDS reads `b4g1`, `BOGO`, `Buy 4, Get 1 Free`, `free case`; not `sugar free` or `buyer`",
            all(DEAL_WORDS.search(w) for w in ("b4g1", "BOGO promo", "Buy 4, Get 1 Free", "1 free case"))
            and not any(DEAL_WORDS.search(w) for w in ("Sugar Free Gummies", "buyer credit", "Getaway 1g")))
    def untied(last_qty):
        ls = [bg_ln("1", "Acme Kush Flower 3.5g", 7, 10.0), bg_ln("2", "Acme Kush Flower 3.5g", last_qty, 0.01)]
        mf = [kush(7, "U-1", "1", "70.00"), kush(last_qty, "U-2", "2", f"{last_qty * 0.01:.2f}")]
        return prep(ls, bg_cat, inv, None, mf, {"1": "14", "2": "14"}, {"2": "deal"}, "PKG - Vendor Deal")
    bpair("BUY_GET_UNTIED (STOP) fires when the remainder cannot divide on a big last package (1,000 units: 79.96 vs 80.00)",
          lambda res: any(e["flag"] == "BUY_GET_UNTIED" and e["class"] == "STOP" for e in res[1]),
          untied(1000), untied(10), "a 10-unit last package: 41.26 / 10 = 4.126, ties")
    qbg = questions(bg_clean[1], bg_clean[2], "x")
    t.check("the questions file prints the deal math (lines, units, ext, blended unit, packages, remainder, the tie)",
            "Buy-Get deals (R103)" in qbg and "BG1 lines 1+2" in qbg and "units 50 " in qbg and "ext $734.90" in qbg
            and "blended unit $14.70" in qbg and "packages 5" in qbg and "remainder on BG-5 at $14.69" in qbg
            and "entered $734.90 = invoice $734.90" in qbg and "Buy-Get deals" not in questions(base[1], base[2], "x"))
    t.check("CONTROL: a package outside any deal enters its own invoice unit (cost_entered = unit_cost_invoice, deal blank)",
            all(r["cost_entered"] == r["unit_cost_invoice"] and r["deal"] == "" for r in base[0] if r.get("metrc_package_id")))
    t.check("CONTROL: the credit blend reads the entered (blended) ext on a deal package",
            (lambda res: rows_of(res)["1a"]["blended_unit_cost"] == f"{(147.0 - 60 / 6) / 10:.4f}")(
                bg(extra=[{"line_no": "90", "description": "Credit", "units_total": "", "unit_cost": "", "ext_cost": "-60.00",
                           "is_order_level": "Y", "order_level_kind": "credit"}])))

    # a qty that is not a finite number is unreadable on ANY package (the `g` leg above): no count, no tie, no crash.
    # PKG-D's $ ties line 3, so `inf` reached round(inf) in the case-multiple test (OverflowError) before the fix.
    def ea_q(q, uom="ea", line_="3"):
        return lambda c, i, l, m, it: m[3].update(qty=q, uom=uom, line=line_)
    rinf = fires("MANIFEST_QTY_UNREAD", "3", ea_q("inf"), "an `inf` qty on an `ea` package whose $ ties (was OverflowError)")
    t.check("an unreadable `ea` qty is a STOP with no count and no qty tie (no MANIFEST_QTY_MISMATCH, no APEX_UNIT_IS_CASE)",
            not any(e["flag"] in ("MANIFEST_QTY_MISMATCH", "APEX_UNIT_IS_CASE") for e in rinf[1])
            and any(e["flag"] == "MANIFEST_QTY_UNREAD" and e["class"] == "STOP" and "'inf' is not a finite number" in e["detail"]
                    for e in rinf[1])
            and nl(rinf, "3")["physical_count"] == "" and nl(rinf, "3")["qty_match"] == "", str(_flags(rinf)))
    fires("MANIFEST_QTY_UNREAD", "3", ea_q("nan", uom=""), "a `nan` bare qty (was a silent pass: nan ties nothing)")
    try:
        crash = ""
        for q in ("inf", "-inf", "nan", "1e400"):
            for uom in ("", "ea", "g"):
                for line_ in ("3", ""):
                    _run(*_mut(ea_q(q, uom, line_)))
        _run(*_mut(lambda c, i, l, m, it: m[2].update(qty="inf", line="")))   # the proposal's case-multiple test
        bgi = bg(extra=())
        mf_bad = prep([bg_ln("1", "Acme Kush Flower 3.5g", 40, 18.37), bg_ln("2", "Acme Kush Flower 3.5g", 10, 0.01)], bg_cat,
                      inv, None, [kush(40, "I-1", "1", "734.80"), dict(kush(10, "I-2", "2", "0.10"), qty="inf")],
                      {"1": "14", "2": "14"}, {"2": "deal"}, "PKG - Vendor Deal")
    except (OverflowError, ValueError, ArithmeticError) as e:
        crash, mf_bad, bgi = f"{type(e).__name__}: {e}", ([], [], {}), ([], [], {})
    t.check("no non-finite qty (inf / -inf / nan / 1e400; blank, ea, g; mapped or proposed) crashes --prep",
            crash == "", crash)
    t.check("a Buy-Get deal holding an unreadable package does not blend (no BUY_GET_BLEND; the STOP names the package) "
            "[breaker: the same deal with a readable qty blends]",
            not any(e["flag"] == "BUY_GET_BLEND" for e in mf_bad[1]) and ("MANIFEST_GRAMS_UNSIZED", "2") in _flags(mf_bad)
            and any(e["flag"] == "BUY_GET_BLEND" for e in bgi[1]), str(_flags(mf_bad)))

    # --payload: the receipt-inputs payload for the warehouse ingest. Proven by the inverse the warehouse applies:
    # payload -> (lines, intake, manifest, items, programs) -> prep() equals the sheet --prep wrote.
    import contextlib
    import csv as _csv
    import io
    import json as _json
    import tempfile
    progs = {"4": "sample", "*": "none"}
    cites = {"4": "invoice line 4 reads (sample)", "*": "email 2026-01-02 from the vendor"}
    pl = receipt_payload(lines, None, man, items, progs, cites, {"1": "Acme Lemon 10pk"}, "inv-9", "2026-01-02",
                         vendor_record="Acme Supply", txn_id="INV-9")
    t.check("the payload carries every ingest key, in order, and the rows as read (manifest `uom` included)",
            list(pl) == PAYLOAD_KEYS and pl["lines"] == lines and pl["manifest"] == man and pl["intake_rows"] is None
            and [p["uom"] for p in pl["manifest"]] == ["ea", "ea", "g", "ea", "ea"] and pl["invoice_no"] == "INV-9"
            and pl["receipt_date"] == "2026-01-02" and pl["vendor_record"] == "Acme Supply", str(list(pl)))
    t.check("one binding per line named (line order, `*` last), each with item, disposition, cite and Apex item",
            [b["line"] for b in pl["bindings"]] == ["1", "2", "3", "4", "*"]
            and pl["bindings"][0] == {"line": "1", "item": "11", "program": "", "cite": "", "apex_item": "Acme Lemon 10pk"}
            and pl["bindings"][3] == {"line": "4", "item": "13", "program": "sample", "cite": cites["4"], "apex_item": ""}
            and pl["bindings"][4]["program"] == "none", str(pl["bindings"]))
    li, ii, mi, iti, pri = payload_inputs(_json.loads(_json.dumps(pl)))
    t.check("payload -> inputs -> prep() = prep() on the runner's inputs (rows, exceptions)",
            prep(li, cat, inv, ii, mi, iti, pri, "PKG - Vendor Deal")[:2] == prep(lines, cat, inv, None, man, items, progs,
                                                                                 "PKG - Vendor Deal")[:2])

    def refused(**kw):
        a = dict(lines=lines, intake=None, manifest=man, items=items, programs={}, cites={}, apex_items={}, slug_="inv-9",
                 receipt_date="2026-01-02", txn_id="INV-9")
        a.update(kw)
        err = io.StringIO()
        try:
            with contextlib.redirect_stderr(err):
                receipt_payload(**a)
        except SystemExit as e:
            return e.code == EXIT_ABORT and err.getvalue()
        return False
    t.check("--payload refuses what the ingest refuses: a disposition with no cite, a disposition outside R127, a "
            "binding to no line, an item on `*`, a bad slug, a bad date, no invoice number",
            "has no --cite 4=" in (refused(programs={"4": "sample"}) or "")
            and "is not sample, display" in (refused(programs={"4": "promo"}, cites={"4": "x"}) or "")
            and "is not a line of this receipt" in (refused(items=dict(items, **{"9": "11"})) or "")
            and "`*` binds a disposition" in (refused(items=dict(items, **{"*": "11"})) or "")
            and "is not lowercase words" in (refused(slug_="INV 9") or "")
            and "is not YYYY-MM-DD" in (refused(receipt_date="01/02/2026") or "")
            and "no invoice number" in (refused(txn_id="") or ""))
    t.check("CONTROL: the same bindings with their cites build (an intake list rides as rows)",
            refused(programs={"4": "sample"}, cites={"4": "x"}) is False
            and receipt_payload(lines, [{"invoice_line": "x"}], None, {}, {}, {}, {}, "a", "2026-01-02",
                                txn_id="T")["intake_rows"] == [{"invoice_line": "x"}])
    with tempfile.TemporaryDirectory() as td:
        def put(name, rows_):
            path = os.path.join(td, name)
            with open(path, "w", encoding="utf-8", newline="") as f:
                w = _csv.DictWriter(f, fieldnames=list(dict.fromkeys(k for r in rows_ for k in r)))
                w.writeheader()
                w.writerows(rows_)
            return path
        lp = put("acme-lines.csv", [dict(x, invoice_no="INV-9") for x in lines])
        argv = ["--prep", "--lines", lp, "--catalog", put("cat.csv", cat), "--inventory", put("inv.csv", inv),
                "--manifest", put("man.csv", man), "--deal-tag", "PKG - Vendor Deal", "--asof", "2026-01-02",
                "--out-dir", td] + [x for k, v in items.items() for x in ("--item", f"{k}={v}")]
        pp = os.path.join(td, "inv-9-payload.json")
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            try:
                main(argv + ["--program", "4=sample", "--payload", pp])
                no_cite = False
            except SystemExit as e:
                no_cite = e.code == EXIT_ABORT
            wrote_none = not [n for n in os.listdir(td) if "receipt-prep" in n] and not os.path.exists(pp)
            code = main(argv + ["--program", "4=sample", "--cite", "4=invoice reads (sample)", "--payload", pp])
            try:
                main(argv + ["--payload", pp])
                again = False
            except SystemExit as e:
                again = e.code == EXIT_ABORT
        sheet = os.path.join(td, "inv-9-receipt-prep-2026-01-02-v1.csv")
        with open(pp, encoding="utf-8") as f:
            cli = _json.load(f)
        with open(sheet, encoding="utf-8", newline="") as f:
            got = [r for r in _csv.DictReader(f)]
        li, ii, mi, iti, pri = payload_inputs(cli)
        again_rows = prep(li, cat, inv, ii, mi, iti, pri, "PKG - Vendor Deal")[0]
        t.check("CLI: --program without --cite ABORTs and writes NO sheet and no payload [control: with the cite it writes both]",
                no_cite and wrote_none and code == EXIT_OK and os.path.exists(sheet) and "wrote payload" in out.getvalue())
        t.check("CLI: the payload file names the sheet's slug and date and reads back to the sheet --prep wrote, cell for cell",
                cli["slug"] == "inv-9" and cli["receipt_date"] == "2026-01-02" and cli["invoice_no"] == "INV-9"
                and [{c: str(r.get(c, "")) for c in PREP_COLS} for r in again_rows] == got)
        t.check("CLI: an existing payload file is never overwritten (ABORT)", again)

    t.check("stub paths still refuse with exit 2",
            all(main([m]) == EXIT_ABORT for m in ("--enter", "--check", "--vendor")) and main([]) == EXIT_ABORT)
    return t.done()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
