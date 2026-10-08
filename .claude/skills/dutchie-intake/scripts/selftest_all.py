"""selftest_all.py - prove the whole intake lane on synthetic fixtures, and prove every check can FAIL.

  python selftest_all.py [-v]

Three layers, exit 1 on any failure:
  1. every script's own `--selftest` (subprocess, PYTHONUTF8=1) must exit 0;
  2. FIXTURE CHECKS on `../fixtures/` (a fake tenant pointer, Active / Retired / Strains exports on
     Dutchie's real Catalog header, an Apex-layout text layer AND its markdown rendering (the shape a
     Drive read of the filed copy returns), a hand-typed lines CSV, a PO, and a
     post-create export with one intake row + one `Available` drift + one foreign cell). Each check is
     a predicate paired with a BREAKER - one named mutation of the fixture. The check passes only when
     the predicate is TRUE on the clean fixture AND FALSE on the broken one. A check that stays green
     on its breaker is reported INERT and fails the run: a gate can lie green;
  3. the CLI chain parse -> match -> exceptions -> certify -> notice -> receive, run as a user would,
     with every output in a temp folder (nothing is written under the skill or a tenant).
"""
import copy
import csv
import os
import shutil
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
FX = os.path.join(os.path.dirname(HERE), "fixtures")
sys.path.insert(0, HERE)
import intake_certify as IC  # noqa: E402
import intake_common as C  # noqa: E402
import intake_exceptions as IE  # noqa: E402
import intake_match as IM  # noqa: E402
import intake_notice as IN  # noqa: E402
import intake_parse as IP  # noqa: E402
import intake_plan as PL  # noqa: E402
import intake_pointers as PTR  # noqa: E402
import receive as RC  # noqa: E402

SCRIPTS = ["intake_pointers.py", "intake_parse.py", "intake_match.py", "intake_exceptions.py",
           "intake_plan.py", "intake_certify.py", "intake_notice.py", "intake_ui_run.py", "receive.py",
           "intake_msrp.py"]
# The batch runner lives in the sibling skill (one allowlist, one refusal set for every lane): its batch
# cases run here too, so the whole R124 chain - plan, gridBatch, certify - is proven by one command.
GRID_SELFTEST = os.path.join(os.path.dirname(os.path.dirname(HERE)), "dutchie-bi-looker", "scripts",
                             "backoffice_grid_write_selftest.js")
DROP = ("Status - Live",)
ENV = dict(os.environ, PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")
VERBOSE = "-v" in sys.argv


def fx(name):
    return os.path.join(FX, name)


def rows_of(name):
    with open(fx(name), encoding="utf-8-sig", newline="") as f:
        return [dict(r) for r in csv.DictReader(f)]


def hdr_of(name):
    with open(fx(name), encoding="utf-8-sig", newline="") as f:
        return next(csv.reader(f))


BASE = {
    "tenant": open(fx("tenant-CLAUDE.md"), encoding="utf-8").read(),
    "apex": open(fx("apex-invoice.txt"), encoding="utf-8").read(),
    "apex_md": open(fx("apex-invoice.md"), encoding="utf-8").read(),
    "generic": open(fx("generic-invoice.txt"), encoding="utf-8").read(),
    "tiered": open(fx("tiered-erp-invoice.txt"), encoding="utf-8").read(),
    "active": rows_of("catalog-active.csv"), "retired": rows_of("catalog-retired.csv"),
    "strains": IM.load_strains(fx("strains.csv")), "lines": rows_of("invoice-lines.csv"), "po": rows_of("po.csv"),
    "post": rows_of("certify-post.csv"), "hdr": hdr_of("catalog-active.csv"),
    "categories": rows_of("categories.csv"), "brands": rows_of("brands.csv"),
    "notice": open(os.path.join(os.path.dirname(HERE), "templates", "notice.md"), encoding="utf-8").read(),
}


def quiet(fn, *a, **k):
    """Run fn with stdout/stderr silenced; a SystemExit becomes ('ABORT', code)."""
    so, se = sys.stdout, sys.stderr
    with open(os.devnull, "w") as dn:
        sys.stdout = sys.stderr = dn
        try:
            return fn(*a, **k)
        except SystemExit as e:
            return ("ABORT", e.code)
        finally:
            sys.stdout, sys.stderr = so, se


def ctx(**over):
    """A deep copy of the fixture set with the named parts replaced."""
    c = copy.deepcopy(BASE)
    c.update(over)
    return c


def matched(c):
    return IM.match(c["lines"], c["active"], c["retired"], c["strains"], drop_tags=DROP,
                    categories=c.get("categories"), brands=c.get("brands"), line_brands=c.get("line_brands"),
                    line_categories=c.get("line_categories"), strain_types=c.get("strain_types"))[0]


def verdict_count(c, v):
    return sum(1 for r in matched(c) if r["verdict"] == v)


def row_for(c, prefix):
    return next(r for r in matched(c) if r["invoice_line"].startswith(prefix))


def exc(c):
    return IE.evaluate(matched(c), c["lines"], c["po"], 90, programs=c.get("programs"))


def fired_on(c, flag):
    return [e["line_no"] for e in exc(c)[1] if e["flag"] == flag]


def keyed(rows):
    return {r["SKU"]: r for r in rows}


def approved_intake(c):
    rows = matched(c)
    for r in rows:
        if r["verdict"] == "NEW_ITEM_WITH_SIBLING":
            r.update(approved="Y", new_sku="1004", new_productid="504")
    return rows


def cert(c, **kw):
    return IC.certify(c["hdr"], keyed(c["active"]), c["hdr"], keyed(c["post"]), "SKU", kw.pop("intake", approved_intake(c)), **kw)


def mut(c, part, pred, **changes):
    """Set fields on the first row of c[part] that satisfies pred."""
    r = next(x for x in c[part] if pred(x))
    r.update(changes)
    return c


def lines_with(**by_no):
    c = ctx()
    for no, ch in by_no.items():
        mut(c, "lines", lambda x, n=no: x["line_no"] == n.lstrip("L") and not x["order_level_kind"], **ch)
    return c


def parsed(text):
    try:
        r = quiet(IP.run_text, text)
    except ValueError:
        return None
    return None if isinstance(r, tuple) and r and r[0] == "ABORT" else r


KEYS = ["line_no", "description", "units_total", "unit_cost", "ext_cost", "expiry_date", "order_level_kind"]


def parse_equals_hand(text):
    p = parsed(text)
    if not p:
        return False
    rows = IP.fmt(p[2])
    got = [{k: str(r.get(k, "")) for k in KEYS} for r in rows]
    want = [{k: r.get(k, "") for k in KEYS} for r in BASE["lines"]]
    return got == want


def chain_source(txt):
    """parse_source when the PDF has no text layer and `txt` (a rendering file, or None) follows it."""
    d = tempfile.mkdtemp()
    try:
        pdf = IP.blank_pdf(os.path.join(d, "filed-invoice.pdf"))
        r = quiet(IP.run_chain, pdf, txt, fx("invoice-lines.csv"))
        return r[0] if r and r[0] != "ABORT" else None
    finally:
        shutil.rmtree(d, ignore_errors=True)


def reconciled(text):
    p = parsed(text)
    return bool(p) and IP.reconcile(p[2], p[1]["total"]) == []


def tiered_shape(text):
    """The tier-priced ERP layout: 3 product lines, units read from each line's package line (one on
    the next page), tier + line discounts on their line, the document discount at order level."""
    p = parsed(text)
    if not p or p[0] != "fernway":
        return False
    prod = [r for r in p[2] if not r["order_level_kind"]]
    line_d = [r for r in p[2] if r["order_level_kind"] == "discount" and r["is_order_level"] == "N"]
    order_d = [r for r in p[2] if r["is_order_level"] == "Y"]
    return ([r["units_total"] for r in prod] == [12, 24, 12] and all(r.get("package_id") for r in prod)
            and prod[1]["description"].endswith("All-In-One | 2.0g | Indica") and len(line_d) == 3 and len(order_d) == 1)


def row_guard_pick(min_rows):
    d = tempfile.mkdtemp()
    try:
        full = os.path.join(d, "2026-01-01-catalog-active.csv")
        short = os.path.join(d, "2026-01-02-catalog-active (2).csv")
        shutil.copy(fx("catalog-active.csv"), full)
        with open(short, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=BASE["hdr"])
            w.writeheader()
            w.writerow(BASE["active"][0])
        os.utime(full, (time.time() - 3600,) * 2)
        pick = quiet(C.freshest, d, ["*catalog*active*.csv"], min_rows, C.CATALOG_REQUIRED)
        return pick == full
    finally:
        shutil.rmtree(d, ignore_errors=True)


def aborts_on_missing_cost(drop):
    d = tempfile.mkdtemp()
    try:
        p = os.path.join(d, "a.csv")
        cols = [h for h in BASE["hdr"] if h != "Cost"] if drop else BASE["hdr"]
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(BASE["active"])
        return quiet(C.read_csv, p, C.CATALOG_REQUIRED) == ("ABORT", C.EXIT_ABORT)
    finally:
        shutil.rmtree(d, ignore_errors=True)


FU_BODY = "Acme Farms | Lime Sorbet"
FU_DESC = "Acme Farms | Lime Sorbet | Flavor Line | Pocket PRO | 2.0g | Hybrid"


def fu_ctx(desc=FU_DESC, second=False):
    """FORM_UNREAD fixture: the catalog item carries its form word (`Distillate AIO`) in segment 2 and an
    edition word (`Pocket Pro`) in a later segment; the vendor line names the edition, not the form."""
    item = dict(BASE["active"][0], SKU="1006", ProductId="506", Category="Vape", Strain="Lime Sorbet",
                Product="Acme Farms | Distillate AIO | Lime Sorbet | 2g | Pocket Pro",
                **{"Product grams": "2g", "Master category": "Vape"})
    extra = [item]
    if second:
        extra.append(dict(item, SKU="1007", ProductId="507", Product="Acme Farms | Distillate Cart | Lime Sorbet | 2g"))
    line = dict(BASE["lines"][0], line_no="7", description=desc, cases="1", units_total="24", case_cost="480.00",
                unit_cost="20.00", ext_cost="480.00", expiry_date="")
    return ctx(active=BASE["active"] + extra, lines=BASE["lines"] + [line])


def form_unread_exists(c):
    r = row_for(c, FU_BODY)
    return r["verdict"] == "EXISTS" and "FORM_UNREAD" in r["flags"].split(";") and r["copy_source_sku"] == "1006"


def form_named_not_exists(c):
    r = row_for(c, FU_BODY)
    return r["verdict"] != "EXISTS" and "FORM_UNREAD" not in r["flags"].split(";")


def stop_prints_form_unread(c):
    rows = matched(c)
    msg = IE.stop_message(rows, [], {"po_checked": True}, "Pat", "x-v2.csv")
    return any("Lime Sorbet" in ln and "| FORM_UNREAD |" in ln for ln in msg.splitlines())


def package_id_rides(lines):
    """Every product line's package_id arrives, unchanged and non-blank, on its intake row."""
    prod = [ln for ln in lines if not ln.get("order_level_kind")]
    rows = IM.match(lines, BASE["active"], BASE["retired"], BASE["strains"], drop_tags=DROP)[0]
    return (len(rows) == len(prod) and all(r["package_id"] for r in rows)
            and [r["package_id"] for r in rows] == [ln.get("package_id") for ln in prod])


def tiered_lines(drop_pkg=False):
    rows = copy.deepcopy(parsed(BASE["tiered"])[2])
    for r in rows:
        if drop_pkg:
            r.pop("package_id", None)
    return rows


def notice_text(rows):
    return IN.fill(BASE["notice"], rows, "Pat Example")


ACME_VAPE = dict(BASE["active"][3], SKU="1008", ProductId="508", Brand="Acme Farms", Strain="Blue Dream",
                 Product="Acme Farms | Live Resin Cart | Blue Dream | 1g", Tags="ITM - Protect",
                 **{"Product grams": "1g"})


def new_line_ctx(lane=False):
    """Line 5 (an Acme 0.5g live resin cart) when Acme carries a 1g cart in Vape: a new LINE, not a new
    category. lane=True adds the 0.5g lane, so the line has a sibling instead."""
    extra = [ACME_VAPE] + ([dict(ACME_VAPE, SKU="1005", ProductId="505", Product="Acme Farms | Live Resin Cart | Blue Dream | 0.5g",
                                 **{"Product grams": "0.5g"})] if lane else [])
    return ctx(active=BASE["active"] + extra)


def new_line_row(c):
    return row_for(c, "Acme Farms Northern Lights")


def new_line_created(rows):
    """The notice marks a created NEW_PL item for the business's QC."""
    for r in rows:
        if r["verdict"] == "NEW_PL":
            r.update(approved="Y", new_sku="1009", new_productid="509", create_name_FINAL="Acme Farms | Live Resin Cart | Northern Lights | 0.5g")
    return rows


BIRCH_1G = dict(BASE["active"][3], SKU="2101", ProductId="611", Product="Birch Labs | Distillate Cart | Blue Dream | 1g",
                Strain="Blue Dream", Tags="ITM - Discontinue", **{"Product grams": "1g", "Image URL": "img-birch.jpg"})
BIRCH_1G_B = dict(BIRCH_1G, SKU="2102", ProductId="612", Product="Birch Labs | Distillate Cart | OG Kush | 1g", Strain="OG Kush",
                  **{"Image URL": ""})
BIRCH_HALF = dict(BIRCH_1G, SKU="2103", ProductId="613", Product="Birch Labs | Distillate Cart | OG Kush | 0.5g", Strain="OG Kush",
                  **{"Product grams": "0.5g", "Image URL": ""})


def unretire_ctx(active_lane=False):
    """Line 8: a Birch 1g distillate cart. Birch carries 1g carts only RETIRED (two of them, plus a 0.5g in another
    lane), so the line we carried before comes back whole. active_lane=True un-retires one 1g cart up front."""
    line = dict(BASE["lines"][0], line_no="8", description="Birch Labs Gelato distillate cart 1g", cases="1", units_total="12",
                case_cost="180.00", unit_cost="15.00", ext_cost="180.00", expiry_date="", coa_url="")
    ret = BASE["retired"] + [BIRCH_1G, BIRCH_1G_B, BIRCH_HALF]
    act = BASE["active"] + ([dict(BIRCH_1G, Tags="ITM - Active")] if active_lane else [])
    if active_lane:
        ret = [r for r in ret if r["SKU"] != "2101"]
    return ctx(active=act, retired=ret, lines=BASE["lines"] + [line])


def unretire_row(c):
    return row_for(c, "Birch Labs Gelato")


def retired_match_row(c):
    return row_for(c, "Acme Farms Sour Diesel")


def line5(desc, **over):
    """The base fixture with line 5 (the Acme cart) re-described."""
    return ctx(lines=[dict(r, description=desc) if r["line_no"] == "5" and not r["order_level_kind"] else r for r in BASE["lines"]], **over)


def line3(desc, **over):
    return ctx(lines=[dict(r, description=desc) if r["line_no"] == "3" and not r["order_level_kind"] else r for r in BASE["lines"]], **over)


def gelato_is(c, **kv):
    r = row_for(c, "Acme Farms Gelato")
    return all(r.get(k) == v for k, v in kv.items())


FL = {"active": rows_of("flavor-led-active.csv"), "lines": rows_of("flavor-led-lines.csv"),
      "strains": IM.load_strains(fx("flavor-led-strains.csv"))}
FL_EXISTS = {"1": "4001", "2": "4002", "3": "4004", "4": "4005", "5": "4006", "6": "4007"}
FL_CREATE = "Acme Farms | Gummies | Mango Restore (1:1 THC:CBD) | 10mg x 10pk"


def fl_ctx(reader=True, flavor_cells=True, **over):
    """Flavor-led fixture: lines `<Brand> | (<S|I|H>) <Flavor> <Form>[ <ratio>] | ...` against bodies
    `<Flavor>[ <Effect>] (<Strain type or ratio>)`. reader=False runs the matcher without the layout
    reader (the pre-fix matcher); flavor_cells=False blanks every Flavor cell (the second read a flavored item has)."""
    c = copy.deepcopy(FL)
    c.update(reader=reader, **over)
    if not flavor_cells:
        for r in c["active"]:
            r["Flavor"] = ""
    return c


def fl_rows(c):
    real = IM.flavor_led
    if not c["reader"]:
        IM.flavor_led = lambda *a: None
    try:
        rows = IM.match(c["lines"], BASE["active"] + c["active"], [], c["strains"], drop_tags=DROP)[0]
    finally:
        IM.flavor_led = real
    return {ln["line_no"]: r for ln, r in zip(c["lines"], rows)}


def fl_body(c, sku, body):
    r = next(x for x in c["active"] if x["SKU"] == sku)
    r["Product"] = " | ".join(C.segs(r["Product"])[:2] + [body] + C.segs(r["Product"])[3:])
    return c


def fl_line(c, no, desc):
    next(x for x in c["lines"] if x["line_no"] == no)["description"] = desc
    return c


def fl_exists(c, nos=tuple(FL_EXISTS)):
    rows = fl_rows(c)
    return all(rows[n]["verdict"] == "EXISTS" and rows[n]["copy_source_sku"] == FL_EXISTS[n] for n in nos)


def fl_create_keeps_canon(c):
    r = fl_rows(c)["7"]
    return (r["verdict"] == "NEW_ITEM_WITH_SIBLING" and r["create_name_FINAL"] == FL_CREATE
            and r["strain"] == "Restore (1:1 THC:CBD)" and "CBD:THC" not in r["create_name_FINAL"] + r["online_title"])


GUMMY_SRC = dict(BASE["active"][3], SKU="3101", ProductId="711", Brand="Birch Labs", Strain="", Flavor="Lime",
                 Product="Birch Labs | Gummies | Lime | 100mg", Category="Gummies", Tags="Status - Live",
                 **{"Master category": "Edible", "Global SubCategory": "gummies", "Product grams": "0.1g",
                    "Online title": "Lime Gummies 100mg", "Online description": "Birch's lime gummies."})

# (name, predicate(ctx-or-arg) , clean arg, broken arg, what the breaker does)
# ---- R124: the plan file and the one certify (synthetic batch: fixtures/plan-*.csv) -------------------------
PFX = IC.plan_fixture()


def plan_of(guard_probed=True, intake_edit=None, copy_source=None):
    """build_plan on the plan fixtures; `guard_probed=False` SIMULATES the pre-P2 map (the breaker; P2 proved
    the retired guard read 2026-10-08, so the module's own map is the probed one)."""
    intake = copy.deepcopy(rows_of("plan-intake.csv"))
    if intake_edit:
        intake_edit(intake)
    if copy_source:
        intake[1]["copy_source_productid"] = copy_source
    kw = {"guard": PL._probed() if guard_probed else PL._unproven_retired()}
    return PL.build_plan(intake, rows_of("plan-pre-active.csv"), rows_of("plan-pre-retired.csv"),
                         rows_of("plan-strains.csv"), rows_of("plan-categories.csv"), rows_of("plan-brands.csv"), **kw)


def plan_flags(edit):
    """The fail flags of the one certify on the plan fixture after `edit(post_active, post_retired, plan)`."""
    return [f.split(":")[0] for f in IC.run_plan(PFX, edit)[1]]


def _pr(rows, pid):
    return next(r for r in rows if r["ProductId"] == pid)


def _mv(src, dst, pid):
    r = _pr(src, pid)
    src.remove(r)
    dst.append(r)


PLAN_BREAKERS = [
    ("ROW_REMOVED", "drop an untouched item from both post files", lambda a, r, p: a.remove(_pr(a, "602"))),
    ("C_FOREIGN_CELL", "another session moves a Price inside the window", lambda a, r, p: _pr(a, "602").update(Price="12")),
    ("PLAN_NOT_APPLIED", "a 429 that was not resumed: one planned Cost stays put", lambda a, r, p: _pr(a, "402").update(Cost="4")),
    ("CROSS_BRAND_RESIDUE_WORD", "the source brand's name left in the new item's description",
     lambda a, r, p: _pr(a, "802").update(**{"Online description": "Lime gummies from Brand B."})),
    ("UNRETIRE_PARTIAL", "one lane member stays in the Retired file", lambda a, r, p: _mv(a, r, "402")),
    ("UNRETIRE_FOREIGN", "a retired item outside the set comes back", lambda a, r, p: _mv(r, a, "403")),
    ("DUP_CREATE", "the copy ran twice under one planned name",
     lambda a, r, p: a.append(dict(_pr(a, "801"), ProductId="803", SKU="8003"))),
    ("TAG_NOT_READ_BACK", "the new-line tag never set on the create", lambda a, r, p: _pr(a, "802").update(Tags="")),
    ("TAG_EXTRA", "the old decision tag left beside the Active one",
     lambda a, r, p: _pr(a, "401").update(Tags="ITM - Active, ITM - Discontinue")),
]


CHECKS = [
    ("pointer contract complete", lambda t: PTR.validate(PTR.parse_text(t)) == [],
     BASE["tenant"], BASE["tenant"].replace("- Watermark: 500\n", ""), "delete the Watermark line"),
    ("pointer carries the Vendor deal tag", lambda t: PTR.validate(PTR.parse_text(t)) == []
     and PTR.parse_text(t)["intake"].get("Vendor deal tag") == "PKG - Vendor Deal",
     BASE["tenant"], BASE["tenant"].replace("- Vendor deal tag: `PKG - Vendor Deal`\n", ""),
     "delete the Vendor deal tag line"),
    ("pointer ladder neo > playwright > pane",
     lambda t: PTR.ladder(PTR.parse_text(t)["raw"]["bi:Write channel"]) == ["neo", "playwright", "pane"],
     BASE["tenant"], BASE["tenant"].replace("-> fallback `playwright` -> `pane`", ""), "cut the fallbacks"),
    ("apex text parses to the hand-typed lines", parse_equals_hand,
     BASE["apex"], BASE["apex"].replace("$15.00      12 Units", "$16.00      12 Units"), "change one unit price"),
    ("markdown rendering (--text) parses to the hand-typed lines", parse_equals_hand,
     BASE["apex_md"], BASE["apex_md"].replace("| $15.00 | 12 Units", "| $16.00 | 12 Units"), "change one unit price"),
    ("source chain: no-text PDF -> --text, parse_source says so",
     lambda t: chain_source(t) == "text:apex-invoice.md",
     fx("apex-invoice.md"), None, "no --text: the chain falls to --lines"),
    ("apex Total reconciles (TOTAL_MISMATCH quiet)", reconciled,
     BASE["apex"], BASE["apex"].replace("$1,805.00", "$1,806.00"), "move the Total by 1.00"),
    ("generic table parses 2 lines + shipping",
     lambda t: bool(parsed(t)) and len([r for r in parsed(t)[2] if not r["order_level_kind"]]) == 2,
     BASE["generic"], BASE["generic"].replace("Description", "Thing"), "remove the table header"),
    ("tiered ERP layout reconciles to Balance Due (TOTAL_MISMATCH quiet)", reconciled,
     BASE["tiered"], BASE["tiered"].replace("300.00     240.00", "310.00     240.00"), "move one BASE PRICE by 10.00"),
    ("tiered ERP layout: package-line units, wrap joins, discount grain", tiered_shape,
     BASE["tiered"], "\n".join(ln for ln in BASE["tiered"].split("\n") if not ln.strip().startswith("1A4000000000000000000013")),
     "delete the package line that sits on page 2"),
    ("EXISTS fires once", lambda c: verdict_count(c, "EXISTS") == 1,
     ctx(), mut(ctx(), "active", lambda r: r["SKU"] == "1001", Product="Acme Farms | Pre-Roll | Blue Dreams | 1g"),
     "rename the matched item's body"),
    ("RETIRED_MATCH fires once", lambda c: verdict_count(c, "RETIRED_MATCH") == 1,
     ctx(), ctx(retired=[]), "drop the retired export rows"),
    ("RETIRED_MATCH is the un-retire path: UNRETIRE action, the whole retired lane in unretire_set, Cost from the invoice, Active tag (R101)",
     lambda c: retired_match_row(c)["action"].startswith("UNRETIRE") and retired_match_row(c)["unretire_set"] == "401;402"
     and retired_match_row(c)["lane_Cost"] == "4.50" and retired_match_row(c)["tags"] == C.DEFAULT_ACTIVE_TAG
     and "UNRETIRE_FIELDS" in retired_match_row(c)["flags"].split(";"),
     ctx(retired=BASE["retired"] + [dict(BASE["retired"][0], SKU="9002", ProductId="402", Product="Acme Farms | Pre-Roll | Gelato | 1g", Strain="Gelato")]),
     ctx(retired=BASE["retired"] + [dict(BASE["retired"][0], SKU="9002", ProductId="402", Product="Acme Farms | Pre-Roll | Gelato | 0.5g",
                                         Strain="Gelato", **{"Product grams": "0.5g"})]),
     "the second retired item sits in another lane (0.5g): the set shrinks to one"),
    ("UNRETIRE_FIRST: a line fitting only a RETIRED lane copies the retired sibling after the whole lane comes back (R101)",
     lambda c: unretire_row(c)["verdict"] == "NEW_ITEM_WITH_SIBLING" and "UNRETIRE_FIRST" in unretire_row(c)["flags"].split(";")
     and unretire_row(c)["copy_source_sku"] == "2101" and unretire_row(c)["unretire_set"] == "611;612"
     and unretire_row(c)["tags"] == C.DEFAULT_ACTIVE_TAG and unretire_row(c)["action"].endswith("after the un-retire (R101)"),
     unretire_ctx(), unretire_ctx(active_lane=True), "one 1g cart is already active: an ordinary sibling copy, no un-retire"),
    ("NEW_ITEM_WITH_SIBLING fires once", lambda c: verdict_count(c, "NEW_ITEM_WITH_SIBLING") == 1,
     ctx(), ctx(strains={k: v for k, v in BASE["strains"].items() if k != "Gelato"}), "delete the Gelato strain record"),
    ("STRAIN_MISSING fires once", lambda c: verdict_count(c, "STRAIN_MISSING") == 1,
     ctx(), ctx(strains=dict(BASE["strains"], **{"Mystery Haze": {"type": "Sativa", "id": ""}})),
     "mint the Mystery Haze strain record"),
    ("NEW_CATEGORY is a taxonomy gap only: a directed Category absent from the categories export (R101)",
     lambda c: verdict_count(c, "NEW_CATEGORY") == 1 and new_line_row(c)["verdict"] == "NEW_CATEGORY",
     ctx(line_categories={"5": "Moon Cart"}),
     ctx(line_categories={"5": "Moon Cart"}, categories=BASE["categories"] + [{"Master category": "Vape", "Category": "Moon Cart",
                                                                                 "Global Subcategories": "cartridges"}]),
     "add Moon Cart to the taxonomy"),
    ("a brand's first item in an existing Category is NOT a stop: line 5 (Acme cart, Acme has no Vape item) is NEW_PL from the CLOSEST item by subcategory, any brand",
     lambda c: verdict_count(c, "NEW_CATEGORY") == 0 and new_line_row(c)["verdict"] == "NEW_PL"
     and new_line_row(c)["copy_source_sku"] == "2001" and "CROSS_BRAND_COPY" in new_line_row(c)["flags"].split(";")
     and new_line_row(c)["lane_Brand"] == "Acme Farms" and new_line_row(c)["lane_Vendor"] == "Northwind Distribution"
     and new_line_row(c)["lane_Price"] == "" and new_line_row(c)["online_title"] == "",
     ctx(), new_line_ctx(), "give Acme a 1g cart in Vape (a same-brand source: no cross-brand copy)"),
    ("CATEGORY_INFERRED (R33): the cross-brand source's Category word (distillate) is not in the line - a vendor fact to confirm",
     lambda c: "CATEGORY_INFERRED" in new_line_row(c)["flags"].split(";"),
     ctx(active=[dict(r, Category="Distillate Cart") if r["SKU"] == "2001" else r for r in BASE["active"]]),
     line5("Acme Farms Northern Lights Distillate Cart 0.5g", active=[dict(r, Category="Distillate Cart") if r["SKU"] == "2001" else r for r in BASE["active"]]),
     "the line prints the Category's own word (Distillate Cart)"),
    ("CATEGORY_UNREAD: a line naming no catalog form word has no copy source and asks for --line-category",
     lambda c: (lambda r: r["verdict"] == "NEW_PL" and "CATEGORY_UNREAD" in r["flags"].split(";") and r["copy_source_sku"] == ""
                and "--line-category 5=" in r["sibling_reason"])(new_line_row(c)),
     line5("Acme Farms Northern Lights Vape Product 0.5g"),
     line5("Acme Farms Northern Lights Vape Product 0.5g", line_categories={"5": "Cartridge"}),
     "the operator names the Category (Cartridge): placed, copied cross-brand, CATEGORY_DIRECTED"),
    ("CATEGORY_DIRECTED (R33): a directed Category in the taxonomy places the line and is flagged for the vendor's confirmation",
     lambda c: (lambda r: r["verdict"] == "NEW_PL" and "CATEGORY_DIRECTED" in r["flags"].split(";") and r["copy_source_sku"] == "2001"
                and r["lane_Category"] == "Cartridge")(new_line_row(c)),
     line5("Acme Farms Northern Lights Vape Product 0.5g", line_categories={"5": "Cartridge"}),
     line5("Acme Farms Northern Lights Vape Product 0.5g"), "no direction: the Category stays unread"),
    ("STRAIN_TYPE_CONFLICT (R26): a line stating a Type the Strain record does not carry is STRAIN_MISSING and lists the record's items",
     lambda c: (lambda r: r["verdict"] == "STRAIN_MISSING" and "STRAIN_TYPE_CONFLICT" in r["flags"].split(";")
                and r["strain_type"] == "Sativa" and "1001 'Acme Farms | Pre-Roll | Blue Dream | 1g'" in r["sibling_reason"])(row_for(c, "Acme Farms Gelato")),
     line3("Acme Farms Gelato preroll 1g - 100/case Sativa", active=[dict(r, Strain="Gelato") if r["SKU"] == "1001" else r for r in BASE["active"]]),
     line3("Acme Farms Gelato preroll 1g - 100/case Hybrid", active=[dict(r, Strain="Gelato") if r["SKU"] == "1001" else r for r in BASE["active"]]),
     "the line states the record's own Type (Hybrid)"),
    ("STRAIN_TYPE_RESEARCHED (R33): a researched Type rides the STRAIN_MISSING row with its source, never typed as a fact",
     lambda c: (lambda r: r["strain_type"] == "Sativa" and "per vendor sheet" in r["sibling_reason"]
                and "STRAIN_TYPE_RESEARCHED" in r["flags"].split(";"))(row_for(c, "Acme Farms Mystery Haze")),
     ctx(strain_types={"4": "Sativa@vendor sheet"}), ctx(), "no direction: the row asks for the research and types nothing"),
    ("NEW_PL fires once: a new line under a known brand, created from its nearest Vape item (R101)",
     lambda c: verdict_count(c, "NEW_PL") == 1 and new_line_row(c)["copy_source_sku"] == "1008"
     and new_line_row(c)["action"].startswith("CREATE"),
     new_line_ctx(), new_line_ctx(lane=True), "add the Acme 0.5g cart lane (a sibling exists)"),
    ("NEW_PL carries the new-line tag, never its source's decision tag (R83)",
     lambda c: new_line_row(c)["tags"] == C.DEFAULT_NEW_LINE_TAG and "NEW_LINE_FIELDS" in new_line_row(c)["flags"].split(";"),
     new_line_ctx(), new_line_ctx(lane=True), "the line gets a sibling (the copy takes the lane tag)"),
    ("a sibling copy takes its lane's ONE decision tag (R96)",
     lambda c: new_line_row(c)["tags"] == "ITM - Protect",
     new_line_ctx(lane=True), mut(new_line_ctx(lane=True), "active", lambda r: r["SKU"] == "1005", Tags="ITM - Discontinue"),
     "mix the lane (one member Discontinue)"),
    ("notice marks a created NEW_PL item for review", lambda rows: "NEW LINE, tagged `ITM - New PL`" in notice_text(rows)[0],
     new_line_created(matched(new_line_ctx())), new_line_created(matched(new_line_ctx(lane=True))), "the line has a sibling"),
    ("NEW_BRAND fires once", lambda c: verdict_count(c, "NEW_BRAND") == 1,
     ctx(), ctx(active=BASE["active"] + [dict(BASE["active"][3], SKU="3001", ProductId="701", Brand="Cedar Co",
                                                  Product="Cedar Co | Gummy | Lime | 0.1g", **{"Product grams": "0.1g"})]),
     "add a Cedar Co item"),
    ("NEW_BRAND is a CREATE once spelled (--line-brand, R121): Brand record first (R30), then a cross-brand copy under the new brand",
     lambda c: (lambda r: r["verdict"] == "NEW_BRAND" and r["action"].startswith("CREATE") and "BRAND_NAME_UNREAD" not in r["flags"]
                and "CROSS_BRAND_COPY" in r["flags"].split(";") and r["lane_Brand"] == "Cedar Co" and r["copy_source_sku"] == "3101"
                and r["tags"] == C.DEFAULT_NEW_LINE_TAG and "Brand record first" in r["sibling_reason"])(row_for(c, "Cedar Co")),
     ctx(active=BASE["active"] + [GUMMY_SRC], line_brands={"6": "Cedar Co"}),
     ctx(active=BASE["active"] + [GUMMY_SRC]), "no spelling: BRAND_NAME_UNREAD, no brand on the row"),
    ("BRAND_NAME_UNREAD: an unspelled new brand keeps its copy source but no brand, and is flagged (R121)",
     lambda c: (lambda r: r["verdict"] == "NEW_BRAND" and "BRAND_NAME_UNREAD" in r["flags"].split(";") and r["lane_Brand"] == ""
                and r["copy_source_sku"] == "3101")(row_for(c, "Cedar Co")),
     ctx(active=BASE["active"] + [GUMMY_SRC]), ctx(active=BASE["active"] + [GUMMY_SRC], line_brands={"6": "Cedar Co"}), "spell the brand"),
    ("a Brand record with no item (brands export) is a NEW_PL cross-brand copy, not a new brand",
     lambda c: (lambda r: r["verdict"] == "NEW_PL" and r["lane_Brand"] == "Dune Co" and "CROSS_BRAND_COPY" in r["flags"].split(";"))(row_for(c, "Cedar Co")),
     ctx(active=BASE["active"] + [GUMMY_SRC], line_brands={"6": "Dune Co"}),
     ctx(active=BASE["active"] + [GUMMY_SRC], line_brands={"6": "Dune Co"}, brands=[b for b in BASE["brands"] if b["Display name"] != "Dune Co"]),
     "drop Dune Co from the brands export: a new brand again"),
    ("--line-brand naming a catalog brand matches the line under it (a spelling the invoice got wrong)",
     lambda c: row_for(c, "AcmeFarms Gelato")["verdict"] == "NEW_ITEM_WITH_SIBLING" and row_for(c, "AcmeFarms Gelato")["copy_source_sku"] == "1001",
     line3("AcmeFarms Gelato preroll 1g", line_brands={"3": "Acme Farms"}), line3("AcmeFarms Gelato preroll 1g"),
     "no direction: the misspelt brand is nobody's"),
    ("sibling = the lane member WITH an image", lambda c: row_for(c, "Acme Farms Gelato")["copy_source_sku"] == "1001",
     ctx(), mut(ctx(), "active", lambda r: r["SKU"] == "1001", **{"Image URL": ""}), "clear the imaged sibling's image"),
    ("a dead record (R81) is never the sibling", lambda c: row_for(c, "Acme Farms Gelato")["copy_source_sku"] != "1003",
     ctx(), mut(ctx(), "active", lambda r: r["SKU"] == "1003", Tags=""), "un-tag the dead record"),
    ("lane fields + final name inherited from the sibling",
     lambda c: gelato_is(c, create_name_FINAL="Acme Farms | Pre-Roll | Gelato | 1g", lane_Cost="4.5",
                         online_title="Gelato Pre-Roll 1g", tags="ITM - Active"),
     ctx(), mut(ctx(), "active", lambda r: r["SKU"] == "1001", Cost="4.75"), "move the sibling's Cost"),
    ("row guard steps over a newer filtered one-off", row_guard_pick, 3, 1, "floor lowered to 1 row"),
    ("a missing column ABORTs (never read as blank)", aborts_on_missing_cost, True, False, "restore the column"),
    ("COST_DRIFT fires on line 3 (drift only) and line 4 (both)", lambda c: fired_on(c, "COST_DRIFT") == ["3", "4"],
     ctx(), lines_with(L3={"unit_cost": "4.50", "ext_cost": "450.00"}), "line 3 back to the lane Cost"),
    ("DEAL_UNDECIDED fires on line 2 (promo only) and line 4 (both)",
     lambda c: fired_on(c, "DEAL_UNDECIDED") == ["2", "4"],
     ctx(), mut(ctx(), "po", lambda r: r["po_line"] == "2", program="PKG - Vendor Deal"), "name a program on PO line 2"),
    ("line 4 carries BOTH flags with no discount printed (sealed R102: cost, not a discount line)",
     lambda c: "4" in fired_on(c, "COST_DRIFT") and "4" in fired_on(c, "DEAL_UNDECIDED"),
     ctx(), ctx(programs={"4": "margin"}), "rule a program for line 4 by --program"),
    ("control line 1 stays quiet on COST_DRIFT and DEAL_UNDECIDED",
     lambda c: "1" not in fired_on(c, "COST_DRIFT") + fired_on(c, "DEAL_UNDECIDED"),
     ctx(), lines_with(L1={"unit_cost": "3.00", "ext_cost": "300.00"}), "line 1 bought at 3.00"),
    ("EXPIRY_NEAR fires once, on line 1", lambda c: fired_on(c, "EXPIRY_NEAR") == ["1"],
     ctx(), lines_with(L1={"expiry_date": "2027-06-01"}), "push line 1's expiry out"),
    ("PO_MISMATCH fires once, on line 5", lambda c: fired_on(c, "PO_MISMATCH") == ["5"],
     ctx(), mut(ctx(), "po", lambda r: r["po_line"] == "5", units="12"), "fix the PO quantity"),
    ("PKG_TAG_DUE (R62) fires on lines 2 and 4", lambda c: fired_on(c, "PKG_TAG_DUE") == ["2", "4"],
     ctx(), mut(ctx(), "lines", lambda r: r["order_level_kind"] == "discount" and r["is_order_level"] == "N",
                ext_cost="-20.00"), "shrink the line discount"),
    ("R103 landed unit on line 2 = (370 + 450/1875 x 10) / 100",
     lambda c: abs(float(exc(c)[0][1]["landed_unit_cost"]) - (370 + 450 / 1875 * 10) / 100) < 1e-4,
     ctx(), mut(ctx(), "lines", lambda r: r["order_level_kind"] == "shipping", ext_cost="30.00"), "raise shipping"),
    ("LANDED_UNRECONCILED quiet on a clean invoice", lambda c: exc(c)[2] == [],
     ctx(), ctx(lines=[dict(r, ext_cost="0") if not r["order_level_kind"] else r for r in BASE["lines"]]),
     "zero every product ext_cost"),
    ("STOP message lists every exception and the approve column",
     lambda c: (lambda rows, ex: "| approved |" in IE.stop_message(rows, ex, {"po_checked": True}, "Pat", "x-v2.csv")
                and all(e["detail"].replace("|", "\\|") in IE.stop_message(rows, ex, {"po_checked": True}, "Pat", "x-v2.csv")
                        for e in ex) and len(ex) == 8)(*exc(c)[:2]),
     ctx(), mut(ctx(), "po", lambda r: r["po_line"] == "5", units="12"), "remove one exception"),
    ("certify A: 1 intake row, 0 mismatches", lambda c: cert(c)[2]["A"] == 1 and cert(c)[2]["A_mismatch"] == 0,
     ctx(), mut(ctx(), "post", lambda r: r["SKU"] == "1004", Price="12"), "post the new item at the wrong Price"),
    ("certify B: 1 Available drift, down", lambda c: cert(c)[2]["B"] == 1,
     ctx(), mut(ctx(), "post", lambda r: r["SKU"] == "1002", Available="12"), "Available goes UP"),
    ("certify C: 1 foreign cell", lambda c: cert(c)[2]["C"] == 1,
     ctx(), mut(ctx(), "post", lambda r: r["SKU"] == "2001", Price="30"), "revert the foreign write"),
    ("certify RED only for the foreign cell", lambda c: [f.split(":")[0] for f in cert(c)[1]] == ["C_FOREIGN_CELL"],
     ctx(), mut(ctx(), "post", lambda r: r["SKU"] == "1004", Tags=""), "drop the decision tag from the new item"),
    ("certify: the sibling is inert", lambda c: not any("SIBLING_NOT_INERT" in f for f in cert(c)[1]),
     ctx(), mut(ctx(), "post", lambda r: r["SKU"] == "1001", **{"Online title": "moved"}), "write to the sibling"),
    ("certify --no-create attributes the declared cell",
     lambda a: IC.certify(BASE["hdr"], keyed(BASE["active"]), BASE["hdr"],
                          keyed([dict(r, **({"Online title": "OG Kush Pre-Roll 1g (new)"} if r["SKU"] == "1002" else {}))
                                 for r in BASE["active"]]), "SKU", None, True, ["Online title"], a)[2]["C"] == 0,
     ["1002"], ["2001"], "declare the wrong row"),
    ("notice lists the created SKU", lambda rows: "- Acme Farms | Pre-Roll | Gelato | 1g - SKU 1004" in notice_text(rows)[0],
     approved_intake(ctx()), [dict(r, new_sku="") for r in approved_intake(ctx())], "blank the read-back SKU"),
    ("notice: NEW_PL + NEW_BRAND keep the new-line bullet", lambda rows: len(notice_text(rows)[2]) == 2,
     approved_intake(ctx()), [r for r in approved_intake(ctx()) if r["verdict"] not in ("NEW_PL", "NEW_BRAND")],
     "drop the new-line rows"),
    ("receive stub exits 2", lambda a: quiet(RC.main, a) == 2, [], ["--selftest"], "call the selftest path instead"),
    ("EXISTS + FORM_UNREAD: the line omits the form word the catalog carries (edition in a later segment)",
     form_unread_exists, fu_ctx(), fu_ctx(second=True), "add a second brand + body + grams candidate"),
    ("FORM_UNREAD stays off a line that names a form word: never EXISTS", form_named_not_exists,
     fu_ctx(FU_DESC.replace("Pocket PRO", "Cart")), fu_ctx(), "remove the form word from the line"),
    ("STOP message prints FORM_UNREAD on its verdict row", stop_prints_form_unread,
     fu_ctx(), fu_ctx(second=True), "add a second candidate (the row reads NEW_PL, flag absent)"),
    ("package_id rides parse -> lines -> intake row (tiered layout)", package_id_rides,
     tiered_lines(), tiered_lines(drop_pkg=True), "drop package_id from the lines (a pre-column lines CSV)"),
    ("flavor-led: every `(S|I|H) <Flavor> <Form> [ratio]` reorder EXISTS on its one item (strain letter, flavor, ratio read by layout)",
     lambda c: fl_exists(c) and fl_rows(c)["7"]["verdict"] != "EXISTS",
     fl_ctx(), fl_ctx(reader=False, flavor_cells=False),
     "run the matcher without the flavor-led layout reader AND with no Flavor cells (the two reads a flavored item has)"),
    ("flavor-led: the layout reader alone carries the match when the items have no Flavor cell",
     lambda c: fl_exists(c), fl_ctx(flavor_cells=False), fl_ctx(reader=False, flavor_cells=False),
     "no Flavor cells and no layout reader"),
    ("a flavored item is also matched on its Flavor cell when the line is not in the flavor-led layout",
     lambda c: fl_rows(c)["1"]["verdict"] == "EXISTS" and fl_rows(c)["1"]["copy_source_sku"] == "4001",
     fl_line(fl_ctx(), "1", "Acme Farms | Raspberry Gummies Sativa | Edibles & Drinks · Gummies | 100mg per unit (10mg x 10pk)"),
     fl_line(fl_ctx(flavor_cells=False), "1", "Acme Farms | Raspberry Gummies Sativa | Edibles & Drinks · Gummies | 100mg per unit (10mg x 10pk)"),
     "blank the Flavor cells: a line outside the layout has nothing to match on"),
    ("flavor-led: ratio cannabinoid order is unordered (CBD:THC == THC:CBD, CBC:CBG == CBG:CBC, THCv == THCV)",
     lambda c: fl_exists(c, ("3", "5", "6")),
     fl_ctx(), fl_body(fl_ctx(), "4004", "Pomegranate Restore (2:1 THC:CBD)"), "the catalog item's ratio counts change"),
    ("flavor-led: the strain letter must agree with a type-only body (Sour Cherry (Indica), never Cherry (Hybrid))",
     lambda c: fl_exists(c, ("2",)),
     fl_ctx(), fl_line(fl_ctx(), "2", FL["lines"][1]["description"].replace("(I)", "(H)")), "the line's letter becomes (H)"),
    ("flavor-led create: the name takes the catalog's ratio spelling + Strain record, never the invoice's order (R26)",
     fl_create_keeps_canon, fl_ctx(),
     fl_ctx(strains={k: v for k, v in FL["strains"].items() if k != "Restore (1:1 THC:CBD)"}),
     "delete the brand's Restore strain record"),
    ("receive --check join key is package_id, an intake CSV column",
     lambda cols: RC.CHECK_JOIN_KEY == "package_id" and RC.CHECK_JOIN_KEY in cols,
     IM.INTAKE_COLS, [c for c in IM.INTAKE_COLS if c != "package_id"], "remove package_id from the columns"),
    ("plan (R124): the synthetic batch plans 20 writes in step order with 0 refusals (P2 proven 2026-10-08)",
     lambda pr: len(pr[0]) == 20 and pr[1] == []
     and [PL.STEPS.index(r["step"]) for r in pr[0]] == sorted(PL.STEPS.index(r["step"]) for r in pr[0]),
     plan_of(), plan_of(intake_edit=lambda i: i[2].update(lane_CBDContent="5")),
     "a cross-brand copy that sets CBD content (CBDContent REFUSED, P7)"),
    ("plan: with the pre-P2 guard map every retired-item write refuses on probe P2 (6), nothing else",
     lambda pr: len(pr[1]) == 6 and {f["probe"] for f in pr[1]} == {"P2"}, plan_of(False), plan_of(True),
     "the module's own (probed) guard map"),
    ("plan: a dead R81 record is never a copy source", lambda pr: not any(f["reason"] == "DEAD_SOURCE" for f in pr[1]),
     plan_of(), plan_of(copy_source="404"), "point the sibling copy at the dead record"),
    ("plan: every row_sha1 verifies (an edited row is caught before any write)",
     lambda rows: all(PL.row_sha1(r) == r["row_sha1"] for r in rows),
     plan_of()[0], [dict(r, target="17") if r["seq"] == "12" else r for r in plan_of()[0]], "edit one target after the build"),
    ("plan: a cross-brand copy REPLACES the carried description with the new brand's words, never a blank clear",
     lambda pr: not any(f["reason"] == "CONTENT_UNWRITTEN" for f in pr[1])
     and any(r["field"] == "Online description" and r["target"] for r in pr[0]),
     plan_of(), plan_of(intake_edit=lambda i: i[2].update(online_description="")),
     "blank the new brand's description on the cross-brand intake row"),
    ("certify --plan: an un-retired row's link moving blank -> link is derived (the Retired export blanks it)",
     lambda fx_: (lambda rep, f, c: f == [] and c["C"] == 0)(*IC.run_plan(fx_)),
     PFX, dict(PFX, pr=[dict(r, **{"Brand catalog product": "Brand A Old Link"}) if r["ProductId"] == "401" else r
                        for r in PFX["pr"]]),
     "give the un-retired row a pre-batch link that then changes"),
    ("certify --plan GREEN: A = 19 planned + 2 derived, B 1, C 0",
     lambda e: (lambda rep, f, c: f == [] and c["A"] == 19 and c["A_derived"] == 2 and c["B"] == 1 and c["C"] == 0)(*IC.run_plan(PFX, e)),
     None, lambda a, r, p: _pr(a, "601").update(Available="45"), "Available goes UP on the sibling"),
] + [(f"certify --plan: {flag} quiet on the clean batch, fires on its breaker",
      (lambda fl: (lambda e: fl not in plan_flags(e)))(flag), None, brk, how) for flag, how, brk in PLAN_BREAKERS]


def run_checks():
    bad = []
    for name, pred, good, broken, how in CHECKS:
        try:
            g = bool(quiet(pred, good))
        except Exception as e:
            g = f"error {e.__class__.__name__}: {e}"
        try:
            b = bool(quiet(pred, broken))
        except Exception as e:
            b = f"error {e.__class__.__name__}: {e}"
        ok = g is True and b is False
        state = "PASS" if ok else ("INERT" if g is True and b is True else "FAIL")
        print(f"  {state:5} {name}  [breaker: {how}]" + ("" if ok else f"  clean={g} broken={b}"))
        if not ok:
            bad.append(name)
    return bad


def run(cmd, expect):
    r = subprocess.run([sys.executable] + cmd, capture_output=True, text=True, encoding="utf-8", env=ENV, cwd=HERE)
    ok = r.returncode == expect
    if VERBOSE or not ok:
        print((r.stdout + r.stderr).rstrip())
    print(f"  {'PASS' if ok else 'FAIL'}  {' '.join(os.path.basename(x) if os.sep in x or '/' in x else x for x in cmd[:1] + cmd[1:4])}"
          f" ... -> exit {r.returncode} (expect {expect})")
    return ok, r.stdout


def cli_chain():
    t = tempfile.mkdtemp(prefix="intake-selftest-")
    bad = []
    try:
        def step(label, cmd, expect):
            ok, out = run(cmd, expect)
            if not ok:
                bad.append(label)
            return out

        pdf = IP.blank_pdf(os.path.join(t, "filed-invoice.pdf"))
        step("parse (no-text PDF -> --text markdown)", ["intake_parse.py", "--pdf", pdf, "--text",
                                                         fx("apex-invoice.md"), "--out-dir", t], 0)
        lines = next(os.path.join(t, n) for n in os.listdir(t) if "-lines-" in n)
        step("match", ["intake_match.py", "--lines", lines, "--active", fx("catalog-active.csv"), "--retired",
                       fx("catalog-retired.csv"), "--strains", fx("strains.csv"), "--categories", fx("categories.csv"),
                       "--brands", fx("brands.csv"), "--out-dir", t, "--slug", "example", "--drop-tag", DROP[0]], 0)
        v1 = next(os.path.join(t, n) for n in os.listdir(t) if n.endswith("-v1.csv"))
        with open(v1, encoding="utf-8") as f:
            hdr = next(csv.reader(f))
        if hdr != IM.INTAKE_COLS or len(hdr) != 55 or hdr[-3:] != ["parse_source", "package_id", "unretire_set"] or hdr[:54] != IM.V3_COLS:
            bad.append("v4 header")
            print(f"  FAIL  intake CSV header is not the 55-column v4 ({len(hdr)} columns)")
        else:
            print("  PASS  intake CSV header is the 55-column v4 (the 54 v3 columns in place + unretire_set)")
        with open(lines, encoding="utf-8") as f:
            lhdr = next(csv.reader(f))
        ok = lhdr == IP.OUT_COLS and "package_id" in lhdr
        print(f"  {'PASS' if ok else 'FAIL'}  lines CSV header carries package_id ({len(lhdr)} columns)")
        if not ok:
            bad.append("lines header package_id")
        srcs = {r["parse_source"] for r in C.read_csv(v1, IM.INTAKE_COLS)[1]}
        ok = srcs == {"text:apex-invoice.md"}
        print(f"  {'PASS' if ok else 'FAIL'}  intake rows carry parse_source {sorted(srcs)}")
        if not ok:
            bad.append("parse_source")
        out = step("exceptions", ["intake_exceptions.py", "--intake", v1, "--lines", lines, "--po", fx("po.csv"),
                                  "--tenant", fx("tenant-CLAUDE.md")], 0)
        if "## STOP - pre-create review" not in out:
            bad.append("STOP message")
            print("  FAIL  the STOP message was not printed")
        v2 = next(os.path.join(t, n) for n in os.listdir(t) if n.endswith("-v2.csv"))
        _, rows = C.read_csv(v2, IM.INTAKE_COLS)
        for r in rows:
            if r["verdict"] == "NEW_ITEM_WITH_SIBLING":
                r.update(approved="Y", new_sku="1004", new_productid="504")
        v3 = C.next_version(t, C.version_stem(v2)[1])
        C.write_csv(v3, IM.INTAKE_COLS, rows)
        step("certify (RED on the one foreign cell)", ["intake_certify.py", "--pre", fx("catalog-active.csv"), "--post",
                                                       fx("certify-post.csv"), "--intake", v3], 1)
        step("notice", ["intake_notice.py", "--intake", v3, "--tenant", fx("tenant-CLAUDE.md")], 0)
        out = step("msrp (offline: own lanes only, the STOP block printed)",
                   ["intake_msrp.py", "--intake", v2, "--tenant", fx("tenant-CLAUDE.md"), "--active",
                    fx("catalog-active.csv"), "--min-rows", "1", "--no-live", "--no-archive", "--out-dir", t], 0)
        mf = [n for n in os.listdir(t) if "-msrp-" in n and n.endswith(".md")]
        ok = len(mf) == 1 and "pending business confirmation" in out and "## MSRP" in out
        print(f"  {'PASS' if ok else 'FAIL'}  the msrp read wrote ONE -msrp-<ts>.md and printed the pending STOP block")
        if not ok:
            bad.append("msrp output")
        step("receive stub", ["receive.py"], 2)
        pin = os.path.join(t, "plan-intake-v1.csv")
        shutil.copy(fx("plan-intake.csv"), pin)
        pargs = ["--intake", pin, "--active", fx("plan-pre-active.csv"), "--retired", fx("plan-pre-retired.csv"),
                 "--strains", fx("plan-strains.csv"), "--categories", fx("plan-categories.csv"), "--brands", fx("plan-brands.csv")]
        step("plan (GREEN: P2 proved the retired guard read; the CLI writes the plan file)", ["intake_plan.py"] + pargs, 0)
        if not any(n.endswith("-plan-v1.csv") for n in os.listdir(t)):
            bad.append("plan written")
            print("  FAIL  the GREEN plan must write <stem>-plan-v1.csv")
        else:
            print("  PASS  the GREEN plan wrote <stem>-plan-v1.csv")
        irows = copy.deepcopy(rows_of("plan-intake.csv"))
        irows[2]["lane_CBDContent"] = "5"
        rd = os.path.join(t, "refuse")
        os.makedirs(rd)
        pin2 = os.path.join(rd, "plan-intake-v1.csv")
        with open(pin2, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(irows[0].keys()))
            w.writeheader()
            w.writerows(irows)
        out = step("plan (REFUSED: a CBDContent write, probe P7 REFUSED)",
                   ["intake_plan.py"] + [pin2 if a == pin else a for a in pargs], 2)
        if "P7" not in out or any(n.endswith("-plan-v1.csv") for n in os.listdir(rd)) \
                or not any("-plan-refusals-" in n for n in os.listdir(rd)):
            bad.append("plan refusal")
            print("  FAIL  the refused plan must name P7, write no plan file and write a refusals CSV")
        else:
            print("  PASS  the refused plan names P7, wrote no plan file, wrote a refusals CSV")
        rows, _, _ = plan_of()
        planf = os.path.join(t, "plan-intake-plan-v1.csv")
        C.write_csv(planf, PL.PLAN_COLS, rows)
        cargs = ["--plan", planf, "--pre-active", fx("plan-pre-active.csv"), "--pre-retired", fx("plan-pre-retired.csv"),
                 "--post-retired", fx("plan-post-retired.csv"), "--out-dir", t]
        step("certify --plan GREEN (union of Active + Retired, _state)", ["intake_certify.py"] + cargs
             + ["--post-active", fx("plan-post-active.csv")], 0)
        step("certify --plan RED on a post pull where nothing landed", ["intake_certify.py", "--plan", planf,
             "--pre-active", fx("plan-pre-active.csv"), "--pre-retired", fx("plan-pre-retired.csv"),
             "--post-active", fx("plan-pre-active.csv"), "--post-retired", fx("plan-pre-retired.csv"), "--out-dir", t], 1)
        stray = [n for n in os.listdir(FX) if n not in FIXTURE_FILES]
        if stray:
            bad.append("wrote into fixtures/")
            print(f"  FAIL  files appeared under fixtures/: {stray}")
    finally:
        shutil.rmtree(t, ignore_errors=True)
    return bad


FIXTURE_FILES = set(os.listdir(FX))


def main():
    fails = []
    print("1. script selftests")
    for s in SCRIPTS:
        ok, _ = run([s, "--selftest"], 0)
        if not ok:
            fails.append(s)
    if os.path.isfile(GRID_SELFTEST):
        r = subprocess.run(["node", GRID_SELFTEST], capture_output=True, text=True, encoding="utf-8")
        last = [x for x in r.stdout.splitlines() if x.startswith(("PASS", "FAIL"))]
        print(f"  {'PASS' if r.returncode == 0 else 'FAIL'}  backoffice_grid_write_selftest.js (gridBatch) -> "
              f"{last[-1] if last else r.stderr.strip()[:200]}")
        if r.returncode != 0:
            fails.append("backoffice_grid_write_selftest.js")
    else:
        print(f"  FAIL  the batch runner's selftest is missing: {GRID_SELFTEST}")
        fails.append("backoffice_grid_write_selftest.js missing")
    print(f"\n2. fixture checks - each must pass clean AND fail on its breaker ({len(CHECKS)} checks)")
    fails += run_checks()
    print("\n3. CLI chain on the fixtures (temp output)")
    fails += cli_chain()
    for root, dirs, _ in os.walk(os.path.dirname(HERE)):
        for d in dirs:
            if d == "__pycache__":
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)
    print(f"\nselftest_all: {'GREEN' if not fails else 'RED'} - {len(fails)} failure(s)"
          + ("" if not fails else ":\n  - " + "\n  - ".join(fails)))
    return C.EXIT_DEFECT if fails else C.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
