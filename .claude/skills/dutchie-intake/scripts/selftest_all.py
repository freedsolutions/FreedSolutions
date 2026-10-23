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
  3. the CLI chain parse -> match -> exceptions -> certify -> notice -> receive --prep, run as a user would,
     with every output in a temp folder (nothing is written under the skill or a tenant).
"""
import copy
import csv
import json
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
import intake_apex_cost as AC  # noqa: E402
import intake_cases as CS  # noqa: E402
import intake_certify as IC  # noqa: E402
import intake_derive as ID  # noqa: E402
import intake_common as C  # noqa: E402
import intake_exceptions as IE  # noqa: E402
import intake_match as IM  # noqa: E402
import intake_msrp as MS  # noqa: E402
import intake_notice as IN  # noqa: E402
import intake_parse as IP  # noqa: E402
import intake_plan as PL  # noqa: E402
import intake_pointers as PTR  # noqa: E402
import receive as RC  # noqa: E402

SCRIPTS = ["intake_pointers.py", "intake_parse.py", "intake_match.py", "intake_exceptions.py",
           "intake_plan.py", "intake_certify.py", "intake_notice.py", "intake_ui_run.py", "receive.py",
           "intake_msrp.py", "intake_derive.py", "intake_apex_cost.py", "intake_cases.py"]
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


def rows_of_path(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
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
    "fl_eq": ID.load_classes(fx("fl-eq-classes.toml")),   # the synthetic class map the fixture tenant points at
    "caps": PTR.load_caps(fx("fl-eq-classes.toml")),      # R130: the same map's per-master package caps
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
                    line_categories=c.get("line_categories"), strain_types=c.get("strain_types"),
                    fl_eq_classes=c.get("fl_eq"), conc_grams=c.get("conc_grams"),
                    package_cap_mg=c.get("cap_mg", C.DEFAULT_PACKAGE_THC_CAP_MG), package_caps=c.get("caps"),
                    pl_key_fn=c.get("pl_key_fn", C.pl_key_default))[0]


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


def pack_line_ctx():
    """Line 5 printed as a 3-pack of 0.5g carts: 1.5g total, no lane -> NEW_PL from the 1g cart, pack count 3."""
    c = new_line_ctx()
    c["lines"] = [dict(ln, description=ln["description"] + " 3-pack") if ln["line_no"] == "5" else ln for ln in c["lines"]]
    return c


def cbd_source_ctx(master="Vape"):
    """The NEW_PL copy source carries a CBD content; its Master category is `master`."""
    c = new_line_ctx()
    c["active"] = [dict(r, **{"CBD content": "25", "Master category": master}) if r["SKU"] == "1008" else r for r in c["active"]]
    return c


def cert_derived(c):
    """Certify the NEW_PL create against a post export that prints the derived Flower equiv (2.8g) - or, when c is
    the string "break", the source's 1.2g: the A-population compare must fail on that cell."""
    broken = c == "break"
    c = new_line_ctx() if broken else c
    rows = matched(c)
    row = next(r for r in rows if r["verdict"] == "NEW_PL")
    row.update(approved="Y", new_sku="1009", new_productid="509")
    post = {r["SKU"]: dict(r) for r in c["active"]}
    new = dict(next(r for r in c["active"] if r["SKU"] == "1008"), SKU="1009", ProductId="509",
               Product=row["create_name_FINAL"] or "Acme Farms | Live Resin Cart | Northern Lights | 0.5g",
               **{"Product grams": "0.5g", "Flower equiv": "1.2g" if broken else "2.8g", "Tags": C.DEFAULT_NEW_LINE_TAG})
    post["1009"] = new
    rep, fails, counts = IC.certify(c["hdr"], keyed(c["active"]), c["hdr"], post, "SKU", rows)[:3]
    return {"rep": rep, "fails": fails, "counts": counts}


def new_line_created(rows):
    """The notice marks a created NEW_PL item for the business's QC."""
    for r in rows:
        if r["verdict"] == "NEW_PL":
            r.update(approved="Y", new_sku="1009", new_productid="509", create_name_FINAL="Acme Farms | Live Resin Cart | Northern Lights | 0.5g")
    return rows


def new_lines_created(rows, approved="Y"):
    """Every NEW_PL / NEW_BRAND row approved and created (final name + read-back ids); approved="N" leaves the
    rows in the file un-created, which is what the notice's new-line paragraph must never name."""
    for i, r in enumerate(rows):
        if r["verdict"] in ("NEW_PL", "NEW_BRAND"):
            r.update(approved=approved, create_name_FINAL=r.get("create_name_FINAL") or f"Brand {i} | Cart | Body {i} | 1g",
                     new_sku=f"20{i:02d}" if approved == "Y" else "", new_productid=f"60{i:02d}" if approved == "Y" else "")
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


FC_LINES = rows_of("flavor-cell-lines.csv")


def fc_ctx(guard=True):
    """Flavor-cell fixture on the flavor-led catalog: lines OUTSIDE the flavor-led layout, so a flavored item meets
    them on its Flavor cell. Line 1 prints a LONGER flavor (`Raspberry Lemonade`) than item 4001's `Raspberry`;
    line 2 prints `Raspberry` whole after a sub-line word; line 3 prints `Pomegranate Restore`, item 4004's Flavor
    plus its body word. guard=False runs the matcher without the layout guard (flavor_run_ok: the pre-fix matcher)."""
    c = fl_ctx()
    c.update(lines=copy.deepcopy(FC_LINES), guard=guard)
    return c


def fc_rows(c):
    real = IM.flavor_run_ok
    if not c["guard"]:
        IM.flavor_run_ok = lambda *a: True
    try:
        return fl_rows(c)
    finally:
        IM.flavor_run_ok = real


def fc_is(c, no, sku):
    """Line `no` is EXISTS on `sku`; sku=None = the line is NOT EXISTS on any item."""
    r = fc_rows(c)[no]
    return r["verdict"] != "EXISTS" if sku is None else (r["verdict"] == "EXISTS" and r["copy_source_sku"] == sku)


SG = {"active": rows_of("spelling-grain-active.csv"), "lines": rows_of("spelling-grain-lines.csv"),
      "strains": IM.load_strains(fx("spelling-grain-strains.csv")), "brands": rows_of("spelling-grain-brands.csv")}
# The three reads the 2026-10-08 batch lacked, each switched off by its breaker (the pre-fix matcher):
#   brand = brands compare as norm (spaces count); pack = no pack test (grams alone); fold = no accent folding.
SG_OFF = {"brand": [(IM, "brand_key", C.norm), (IM, "has_brand", C.has_phrase)],
          "pack": [(IM, "item_pack", lambda r: None)],
          "fold": [(C, "fold", lambda t: t or "")]}


def sg_ctx(off=None):
    """Spelling + pack-grain fixture: lines whose brand drops its space (`TwinOak`), a direction spelled apart
    from its Brand record (`Red Fern` / `RedFern`), a 1g single beside a 0.5g x 2pk at the same grams, and
    accents on one side only (`Piña Verde` / `Pina Verde`, `Jalapeno Haze` / `Jalapeño Haze`). `off` names the
    read the breaker switches off (SG_OFF)."""
    c = copy.deepcopy(SG)
    c["off"] = off
    return c


def sg_rows(c):
    saved = [(m, n, getattr(m, n)) for m, n, _ in SG_OFF.get(c["off"], [])]
    for m, n, v in SG_OFF.get(c["off"], []):
        setattr(m, n, v)
    try:
        rows = IM.match(c["lines"], c["active"], [], c["strains"], drop_tags=DROP, brands=c["brands"],
                        line_brands={"2": "Red Fern"})[0]
    finally:
        for m, n, v in saved:
            setattr(m, n, v)
    return {ln["line_no"]: r for ln, r in zip(c["lines"], rows)}


def sg_is(c, no, verdict, sku=None, **kv):
    r = sg_rows(c)[no]
    return r["verdict"] == verdict and (sku is None or r["copy_source_sku"] == sku) and all(r.get(k) == v for k, v in kv.items())


SL = {"lines": rows_of("sub-line-lines.csv"), "strains": IM.load_strains(fx("sub-line-strains.csv"))}
# The two layout reads the 10/8 SO line 11 lacked, each switched off by its breaker (the pre-fix matcher):
#   lead = no brand slot (a catalog brand named anywhere on the line is its brand); run = a flavored lane takes any
#   Strain-record phrase; slot = every column's lead is a brand slot, with or without a brand leading a line there.
SL_OFF = {"lead": [(IM, "lead_of", lambda d: None)], "run": [(IM, "whole_run", lambda *a: True)],
          "slot": [(IM, "brand_slots", lambda lines, known: {((ln.get("invoice_no") or "").strip(), IM.brand_key(lo[0]))
                                                             for ln in lines for lo in [IM.lead_of(ln.get("description"))] if lo})]}


def sl_ctx(off=None, lines="sub-line", line_brands=None):
    """Sub-line fixture on the flavor-led catalog: lines `Acme Farms | <lead> - <Flavor> Gummies - 100mg - 10ct`. Lines
    1 and 3 lead with the brand (the invoice's brand slot); line 2 leads with `Pebbles`, another brand's line word,
    and prints `Raspberry Lemonade`, inside which sits Strain record `Lemonade`; line 3 prints `Lemonade` whole.
    lines="flavor-cell" runs the flavor-cell lines (a sub-line lead `Juniper` with no brand in any line's slot).
    `off` names the read the breaker switches off (SL_OFF); `line_brands` = --line-brand directions."""
    c = fl_ctx()
    c.update(lines=copy.deepcopy(SL["lines"] if lines == "sub-line" else FC_LINES), off=off, line_brands=line_brands or {})
    if lines == "sub-line":
        c["strains"] = SL["strains"]
    return c


def sl_rows(c):
    saved = [(m, n, getattr(m, n)) for m, n, _ in SL_OFF.get(c["off"], [])]
    for m, n, v in SL_OFF.get(c["off"], []):
        setattr(m, n, v)
    try:
        rows = IM.match(c["lines"], BASE["active"] + c["active"], [], c["strains"], drop_tags=DROP,
                        line_brands=c["line_brands"])[0]
    finally:
        for m, n, v in saved:
            setattr(m, n, v)
    return {ln["line_no"]: r for ln, r in zip(c["lines"], rows)}


def sl_slot_unread(c):
    """Line 2's `Pebbles` lead reads no brand (NEW_BRAND, BRAND_NAME_UNREAD, the reason names the word), while lines 1
    and 3 under the same column still read the brand: 1 EXISTS on 4001, 3 copies the brand's gummy lane."""
    r = sl_rows(c)
    return (r["2"]["verdict"] == "NEW_BRAND" and "BRAND_NAME_UNREAD" in r["2"]["flags"].split(";")
            and r["2"]["lane_Brand"] == "" and "'Pebbles' leads the product segment" in r["2"]["sibling_reason"]
            and r["1"]["verdict"] == "EXISTS" and r["1"]["copy_source_sku"] == "4001"
            and r["3"]["verdict"] == "NEW_ITEM_WITH_SIBLING" and r["3"]["lane_Brand"] == "Acme Farms")


def sl_strain_whole_run(c):
    """Directed to a new brand, line 2 copies a flavored gummy and takes NO Strain record out of `Raspberry Lemonade`
    (STRAIN_MISSING); line 3 prints `Lemonade` as its whole run and takes the record."""
    r = sl_rows(c)
    return (r["2"]["verdict"] == "STRAIN_MISSING" and r["2"]["strain"] == "" and "Lemonade" not in r["2"]["create_name_FINAL"]
            and r["3"]["strain"] == "Lemonade" and r["3"]["create_name_FINAL"] == "Acme Farms | Gummies | Lemonade | 10mg x 10pk")


GUMMY_SRC = dict(BASE["active"][3], SKU="3101", ProductId="711", Brand="Birch Labs", Strain="", Flavor="Lime",
                 Product="Birch Labs | Gummies | Lime | 100mg", Category="Gummies", Tags="Status - Live",
                 **{"Master category": "Edible", "Global SubCategory": "gummies", "Product grams": "0.1g",
                    "Online title": "Lime Gummies 100mg", "Online description": "Birch's lime gummies."})



def gummy_ctx(desc="Cedar Co Mango gummies 100mg 10pk", brand=True, **over):
    """Line 6 re-described, with the Edible gummy source in the catalog: a NEW_BRAND copy (brand=True spells
    Cedar Co) or whatever the line's own brand words match (brand=False). The THC-grams class is the fixture map's
    Edible -> thc_g_x56; R129's vendor dose read is tested here."""
    c = ctx(active=BASE["active"] + [GUMMY_SRC], **over)
    if brand:
        c["line_brands"] = {"6": "Cedar Co"}
    c["lines"] = [dict(ln, description=desc) if ln["line_no"] == "6" else ln for ln in c["lines"]]
    return c


def caps_with(**mc_caps):
    """The fixture map's package caps with named masters replaced (R130 breakers): caps_with(edible=50)."""
    return dict(BASE["caps"], **mc_caps)


MC_SRC = {   # R130: one synthetic source item + its taxonomy row per mg master the per-MC dose read is tested on
    "Tincture": ("Tinctures", "tinctures", "Tincture"),
    "Beverage": ("Drinks", "drinks", "Drink"),
    "Topical": ("Balms", "balms", "Balm"),
    "Transdermal": ("Transdermal", "transdermal-patches", "Patch", "Topical"),   # a Category exception under Topical
}


def without_exception(cat):
    """The fixture map's classes and caps with the enumerated Category exception `cat` removed (the R130 breaker)."""
    k = ID.CAT_PREFIX + C.norm(cat)
    return {"fl_eq": {a: v for a, v in BASE["fl_eq"].items() if a != k}, "caps": {a: v for a, v in BASE["caps"].items() if a != k}}


def mc_line_ctx(desc, mc, **over):
    """Line 6 re-described as a NEW_BRAND (Cedar Co) line in Master category `mc` (or the Category MC_SRC names
    under its master), with a Birch Labs source item there to copy across brands; the dose read takes the package
    cap of the Category exception, else the master, from the fixture class map (R130)."""
    cat, gsc, form, *own = MC_SRC[mc]
    mc = own[0] if own else mc
    src = dict(GUMMY_SRC, SKU="3201", ProductId="721", Product=f"Birch Labs | {form} | Lime | 100mg", Category=cat,
               **{"Master category": mc, "Global SubCategory": gsc})
    tax_row = dict(BASE["categories"][0], **{"Master category": mc, "Category": cat, "Global Subcategories": gsc})
    c = ctx(active=BASE["active"] + [src], categories=BASE["categories"] + [tax_row], **over)
    c["line_brands"] = {"6": "Cedar Co"}
    c["lines"] = [dict(ln, description=desc) if ln["line_no"] == "6" else ln for ln in c["lines"]]
    return c


def line6_row(c):
    return next(r for r in matched(c) if r["invoice_line"].startswith("Cedar Co"))


def gummy_row(c):
    return next(r for r in matched(c) if r["invoice_line"].split(" | ")[0].lower().endswith("gummies") or "gummies" in r["invoice_line"].lower())


def mg_pack_ctx():
    """pack_line_ctx with line 5 printed in mg (`500mg 3-pack`): the same pack under the cap test."""
    c = new_line_ctx()
    c["lines"] = [dict(ln, description=ln["description"].replace("0.5g", "500mg") + " 3-pack") if ln["line_no"] == "5" else ln for ln in c["lines"]]
    return c


# (name, predicate(ctx-or-arg) , clean arg, broken arg, what the breaker does)
# ---- R124: the plan file and the one certify (synthetic batch: fixtures/plan-*.csv) -------------------------
PFX = IC.plan_fixture()


def plan_of(guard_probed=True, intake_edit=None, copy_source=None, strains=None, link=True):
    """build_plan on the plan fixtures; `guard_probed=False` SIMULATES the pre-P2 map (the breaker; P2 proved
    the retired guard read 2026-10-08, so the module's own map is the probed one). `strains` replaces the table.
    `link=False` drops the global-link search (fixtures/plan-catalog-search.csv) - the LINK_NOT_SEARCHED breaker."""
    intake = copy.deepcopy(rows_of("plan-intake.csv"))
    if intake_edit:
        intake_edit(intake)
    if copy_source:
        intake[1]["copy_source_productid"] = copy_source
    kw = {"guard": PL._probed() if guard_probed else PL._unproven_retired(), "catalog_state": "ST",
          "link_search": rows_of("plan-catalog-search.csv") if link else None}
    return PL.build_plan(intake, rows_of("plan-pre-active.csv"), rows_of("plan-pre-retired.csv"),
                         rows_of("plan-strains.csv") if strains is None else strains, rows_of("plan-categories.csv"),
                         rows_of("plan-brands.csv"), **kw)


def strains_as(header):
    """The strains fixture's rows written under `header` (positional: the same four columns, renamed), loaded through
    the matcher's reader. ('ABORT', 2) when the reader refuses the file."""
    d = tempfile.mkdtemp()
    try:
        p = os.path.join(d, "strains.csv")
        old = hdr_of("strains.csv")
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, quoting=csv.QUOTE_ALL)
            w.writerow(header)
            w.writerows([r[c] for c in old] for r in rows_of("strains.csv"))
        return quiet(IM.load_strains, p)
    finally:
        shutil.rmtree(d, ignore_errors=True)


STRAINS_OLD = ["Strain name", "Type", "Abbreviation", "Description"]
STRAINS_NEW = ["Name", "Type", "Abbreviation", "Description"]       # the platform rename (KB [PROBE 2026-10-11])


def plan_strains(name_col, blank=False, extra=()):
    """The plan's strain table keyed on `name_col` (+ extra synthetic records); `blank` empties every name."""
    rows = [{(name_col if k == "Strain name" else k): ("" if blank and k == "Strain name" else v) for k, v in r.items()}
            for r in rows_of("plan-strains.csv")]
    return rows + [{name_col: ("" if blank else n), "Type": t, "Abbreviation": "", "Description": ""} for n, t in extra]


def plan_mints(strains):
    p = plan_of(strains=strains)
    return p if isinstance(p, tuple) and p and p[0] == "ABORT" else [r["product_key"] for r in p[0] if r["step"] == "MINT_STRAIN"]


def pick_strains(header):
    """True when `freshest` picks a one-row Strains file carrying `header` (the one-of required name column)."""
    d = tempfile.mkdtemp()
    try:
        p = os.path.join(d, "s-strains.csv")
        with open(p, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows([header, ["a", "Hybrid", "a", "a"]])
        return quiet(C.freshest, d, ["*strain*.csv"], 1, C.STRAINS_REQUIRED) == p
    finally:
        shutil.rmtree(d, ignore_errors=True)


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
    ("pointer ladder neo > pane",
     lambda t: PTR.ladder(PTR.parse_text(t)["raw"]["bi:Write channel"]) == ["neo", "pane"],
     BASE["tenant"], BASE["tenant"].replace("-> fallback `pane`", ""), "cut the fallback"),
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
    # --- the derived create-stop fields (R1-R3, R6, R7, R34, R42, R66) ---
    ("DERIVED Flower equiv on the NEW_PL copy: 0.5g x 5.6 = 2.8g (R1 R3), cited in `derived`, off the stop list",
     lambda c: new_line_row(c)["lane_FlowerEquiv"] == "2.8g" and "Flower equiv: 2.8g (R1 R3: product_g_x5.6" in new_line_row(c)["derived"]
     and "Flower equiv (" not in new_line_row(c)["sibling_reason"],
     new_line_ctx(), dict(new_line_ctx(), fl_eq=None), "no class map (no `FL EQ classes` pointer): the source's value carries and the stop names it"),
    ("the STOP names Flower equiv with the reason when the lane cannot derive it",
     lambda c: "Flower equiv (no `FL EQ classes` pointer" in new_line_row(c)["sibling_reason"],
     dict(new_line_ctx(), fl_eq=None), new_line_ctx(), "the class map is present (derived, not at the stop)"),
    ("a single with no printed pack count keeps Servings per Unit at the stop (R31)",
     lambda c: "Servings per Unit (the line prints no pack count" in new_line_row(c)["sibling_reason"],
     new_line_ctx(), pack_line_ctx(), "the line prints `3-pack` (R34 derives it)"),
    ("a pack line derives Servings per Unit (R34), the total grams, Flower equiv on the total and the name's `0.5g x 3pk` (R42)",
     lambda c: (lambda r: r["lane_ServingsPerUnit"] == "3" and r["lane_ProductGrams"] == "1.5g" and r["lane_FlowerEquiv"] == "8.4g"
                and r["create_name_FINAL"].endswith("| 0.5g x 3pk"))(new_line_row(c)),
     pack_line_ctx(), new_line_ctx(), "the single line (no pack count)"),
    ("CBD content derived blank off the CBD master (R66), even when the copy source carries one",
     lambda c: new_line_row(c)["lane_CBDContent"] == "" and "CBD content: blank (R66" in new_line_row(c)["derived"],
     cbd_source_ctx(), cbd_source_ctx(master="CBD"), "the source sits in the CBD master (the dose is a product fact: stays at the stop)"),
    ("on the CBD master the CBD dose stays at the stop, named",
     lambda c: "CBD content (the CBD dose is a product fact" in new_line_row(c)["sibling_reason"],
     cbd_source_ctx(master="CBD"), cbd_source_ctx(), "the source is off the CBD master"),
    ("certify A-population: a created item's Flower equiv must equal the DERIVED target (grams compare)",
     lambda c: not any("MISMATCH Flower equiv:" in line for line in cert_derived(c)["rep"]),
     new_line_ctx(), "break", "the post export prints the source's 1.2g instead of the derived 2.8g"),
    # --- the vendor dose read (R129): per piece when piece x count fits the package cap, else the package total ---
    ("R129: `100mg 10pk` on a THC-grams class is the PACKAGE total - 0.1 g, Servings 10, `10mg x 10pk`, Flower equiv 5.6g, DOSE_READ_TOTAL + the cite",
     lambda c: (lambda r: r["lane_ProductGrams"] == "0.1g" and r["lane_ServingsPerUnit"] == "10" and r["lane_FlowerEquiv"] == "5.6g"
                and "Dose: 10mg x 10pk (R7 R42 R34)" in r["derived"] and "DOSE_READ_TOTAL" in r["flags"].split(";")
                and "Product grams: 0.1g (R129: package total: a per-piece read would be 900 mg over the Edible 100 mg package cap (R130); 10 mg x 10)" in r["derived"])(gummy_row(c)),
     gummy_ctx(), gummy_ctx("Cedar Co Mango gummies 10mg x 10pk"), "the figure fits the cap: per piece, no flag, no package-total cite"),
    ("R129: an mg figure that fits the cap is per piece (`10mg x 10pk`): 0.1 g, no flag, the fit cited",
     lambda c: (lambda r: r["lane_ProductGrams"] == "0.1g" and "DOSE_READ_TOTAL" not in r["flags"].split(";")
                and "Product grams: 0.1g (R129: per piece: 10 mg x 10 = 100 mg fits the Edible 100 mg package cap (R130))" in r["derived"])(gummy_row(c)),
     gummy_ctx("Cedar Co Mango gummies 10mg x 10pk"), gummy_ctx("Cedar Co Mango gummies 10mg x 10pk", caps=caps_with(edible=50)),
     "the class map's Edible cap is 50 mg (R130): the same line reads as the package total"),
    ("R129: `5mg - 10ct` is per piece - 0.05 g, `5mg x 10pk`, Flower equiv 2.8g",
     lambda c: (lambda r: r["lane_ProductGrams"] == "0.05g" and "Dose: 5mg x 10pk" in r["derived"] and r["lane_FlowerEquiv"] == "2.8g")(gummy_row(c)),
     gummy_ctx("Cedar Co Mango gummies 5mg - 10ct"), gummy_ctx("Cedar Co Mango gummies 500mg - 10ct"),
     "500 mg x 10 breaks the cap: package total 0.5 g, `50mg x 10pk`, Flower equiv 28g"),
    ("R129 STOP: an mg figure with NO count on a THC-grams-class new line keeps DOSE_UNREAD; Product grams, Flower equiv and the dose stay at the stop, named",
     lambda c: (lambda r: "DOSE_UNREAD" in r["flags"].split(";") and "Product grams (an mg figure with no pack count" in r["sibling_reason"]
                and "Flower equiv:" not in r["derived"] and "Dose:" not in r["derived"] and r["lane_ProductGrams"] == "0.1g")(gummy_row(c)),
     gummy_ctx("Cedar Co Mango gummies 100mg"), gummy_ctx(), "the line prints the count (10pk): the read settles, no STOP"),
    ("R129 leaves the grams read alone: `0.5g 3-pack` is per piece, 1.5 g, no cap test, no Product grams cite",
     lambda c: (lambda r: r["lane_ProductGrams"] == "1.5g" and "Product grams:" not in r["derived"] and "DOSE_READ_TOTAL" not in r["flags"].split(";"))(new_line_row(c)),
     pack_line_ctx(), mg_pack_ctx(), "the same pack printed in mg (500mg 3-pack) is an mg read, cited (Vape carries no cap, R130)"),
    ("R129 repairs the EXISTS read: `Birch Labs Lime gummies 100mg 10pk` matches the 0.1 g catalog item (the per-piece read, 1 g, could not)",
     lambda c: (lambda r: r["verdict"] == "EXISTS" and r["copy_source_sku"] == "3101")(gummy_row(c)),
     gummy_ctx("Birch Labs Lime gummies 100mg 10pk", brand=False), gummy_ctx("Birch Labs Lime gummies 100mg 10pk", brand=False, caps=caps_with(edible=2000)),
     "a 2000 mg Edible cap reads the line per piece (1 g): no 1 g item exists"),
    # --- R130: the dose read's cap is the TARGET Master category's, from the class map (R129 amended) ---
    ("R130: Edible `100mg - 10ct` is the package total against Edible's cap - 0.1 g, `10mg x 10pk`, the cite names Edible",
     lambda c: (lambda r: r["lane_ProductGrams"] == "0.1g" and "Dose: 10mg x 10pk" in r["derived"]
                and "over the Edible 100 mg package cap (R130)" in r["derived"] and "DOSE_READ_TOTAL" in r["flags"].split(";"))(gummy_row(c)),
     gummy_ctx("Cedar Co Mango gummies 100mg - 10ct"), gummy_ctx("Cedar Co Mango gummies 100mg - 10ct", caps=caps_with(edible=None)),
     "Edible carries no cap in the map: per piece, 1 g, no flag"),
    ("R130: Tincture `500mg 2pk` is per piece - 1 g fits Tincture's cap; `500mg x 2pk`, no flag, the cite names Tincture",
     lambda c: (lambda r: r["lane_ProductGrams"] == "1g" and "Dose: 500mg x 2pk" in r["derived"]
                and "fits the Tincture 10000 mg package cap (R130)" in r["derived"] and "DOSE_READ_TOTAL" not in r["flags"].split(";"))(line6_row(c)),
     mc_line_ctx("Cedar Co Lime tincture 500mg 2pk", "Tincture"), mc_line_ctx("Cedar Co Lime tincture 500mg 2pk", "Tincture", caps=caps_with(tincture=100)),
     "a 100 mg Tincture cap: the same line reads as the package total, 0.5 g, flagged"),
    ("R130: Beverage `5mg - 4ct` is per piece - 0.02 g fits Beverage's multipack cap; `5mg x 4pk`",
     lambda c: (lambda r: r["lane_ProductGrams"] == "0.02g" and "Dose: 5mg x 4pk" in r["derived"]
                and "fits the Beverage 100 mg package cap (R130)" in r["derived"] and "DOSE_READ_TOTAL" not in r["flags"].split(";"))(line6_row(c)),
     mc_line_ctx("Cedar Co Lime drink 5mg - 4ct", "Beverage"), mc_line_ctx("Cedar Co Lime drink 5mg - 4ct", "Beverage", caps=caps_with(beverage=5)),
     "the Beverage cap set to its unit cap (5 mg): 5 mg x 4 breaks it, package total"),
    ("R130: Topical `250mg - 2ct` is per piece - Topical carries no cap; 0.5 g, `250mg x 2pk`, no flag, the sentinel FL EQ (R6)",
     lambda c: (lambda r: r["lane_ProductGrams"] == "0.5g" and "Topical carries no package cap (R130)" in r["derived"]
                and r["lane_FlowerEquiv"] == "0.0001g" and "DOSE_READ_TOTAL" not in r["flags"].split(";"))(line6_row(c)),
     mc_line_ctx("Cedar Co Lime balm 250mg - 2ct", "Topical"), mc_line_ctx("Cedar Co Lime balm 250mg - 2ct", "Topical", caps=caps_with(topical=100)),
     "give Topical a 100 mg cap: package total 0.25 g, flagged"),
    ("R130 re-rule: Tincture `6000mg 2pk` breaks the 10000 mg multipack ceiling - package total 6 g, `3000mg x 2pk`, flagged",
     lambda c: (lambda r: r["lane_ProductGrams"] == "6g" and "Dose: 3000mg x 2pk" in r["derived"]
                and "over the Tincture 10000 mg package cap (R130)" in r["derived"] and "DOSE_READ_TOTAL" in r["flags"].split(";"))(line6_row(c)),
     mc_line_ctx("Cedar Co Lime tincture 6000mg 2pk", "Tincture"), mc_line_ctx("Cedar Co Lime tincture 6000mg 2pk", "Tincture", caps=caps_with(tincture=20000)),
     "a 20000 mg ceiling: per piece, 12 g, no flag"),
    ("R130 + R6 re-rule: a Transdermal line reads against the CATEGORY exception (per piece to 10000 mg) and derives concentrate EQ on THC grams",
     lambda c: (lambda r: r["lane_Category"] == "Transdermal" and r["lane_ProductGrams"] == "0.2g" and r["lane_FlowerEquiv"] == "1.12g"
                and "fits the Transdermal 10000 mg package cap (R130)" in r["derived"] and "by Category Transdermal (R6 R130)" in r["derived"]
                and "DOSE_READ_TOTAL" not in r["flags"].split(";"))(line6_row(c)),
     mc_line_ctx("Cedar Co Lime patch 20mg - 10ct", "Transdermal"),
     mc_line_ctx("Cedar Co Lime patch 20mg - 10ct", "Transdermal", **without_exception("Transdermal")),
     "drop the Transdermal exception: the line rides Topical (no cap, the 0.0001 g sentinel)"),
    ("R129 amended: an EXISTS gummy read as the package total carries NO DOSE_READ_TOTAL (quiet on an existing item)",
     lambda c: (lambda r: r["verdict"] == "EXISTS" and "DOSE_READ_TOTAL" not in r["flags"].split(";"))(gummy_row(c)),
     gummy_ctx("Birch Labs Lime gummies 100mg 10pk", brand=False), gummy_ctx("Cedar Co Mango gummies 100mg 10pk"),
     "the same read on a NEW_BRAND create row: flagged for the COA check"),
    ("R130 no-map fallback: a class map with no caps (or none at all) reads every mg line against the generic default",
     lambda c: (lambda r: r["lane_ProductGrams"] == "0.1g" and "cap (generic fallback: no class-map cap)" in r["derived"]
                and "DOSE_READ_TOTAL" in r["flags"].split(";"))(gummy_row(c)),
     gummy_ctx(caps=None), gummy_ctx(caps=None, cap_mg=2000), "the fallback raised to 2000 mg (`--package-cap-mg`): per piece, 1 g"),
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
     lambda c: row_for(c, "Akme Farms Gelato")["verdict"] == "NEW_ITEM_WITH_SIBLING" and row_for(c, "Akme Farms Gelato")["copy_source_sku"] == "1001",
     line3("Akme Farms Gelato preroll 1g", line_brands={"3": "Acme Farms"}), line3("Akme Farms Gelato preroll 1g"),
     "no direction: the misspelt brand is nobody's (a spacing alone is no misspelling: brand_key)"),
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
    ("notice: created NEW_PL + NEW_BRAND items keep the new-line bullet", lambda rows: len(notice_text(rows)[2]) == 2,
     new_lines_created(approved_intake(ctx())), new_lines_created(approved_intake(ctx()), approved="N"),
     "set approved = N on the new-line rows (not created)"),
    ("notice: the new-line paragraph names a created item by its final name, never an invoice line (2026-10-08)",
     lambda rows: (lambda tx: "New line: " in tx
                   and all(r["create_name_FINAL"] in tx for r in rows if r["verdict"] in ("NEW_PL", "NEW_BRAND"))
                   and not any(r["invoice_line"] in tx for r in rows if r["verdict"] in ("NEW_PL", "NEW_BRAND")))(notice_text(rows)[0]),
     new_lines_created(approved_intake(ctx())), new_lines_created(approved_intake(ctx()), approved="N"),
     "set approved = N on the new-line rows (an un-created row is not a new line)"),
    ("notice: a created item with no image needs a hand (2026-10-08)",
     lambda rows: "Product image:" in notice_text(rows)[0] and "- Nothing." not in notice_text(rows)[0],
     [dict(r, image_state="deleted (source art)") for r in approved_intake(ctx())],
     [dict(r, image_state="deleted (source art)", image_source="https://example.test/art.jpg") for r in approved_intake(ctx())],
     "record a sourced image (image_source = the page URL)"),
    ("notice: image_source `not found:` prints where the lane looked",
     lambda rows: "We looked at the brand site and two Dutchie menus and found none" in notice_text(rows)[0],
     [dict(r, image_state="deleted (source art)", image_source="not found: the brand site and two Dutchie menus")
      for r in approved_intake(ctx())],
     [dict(r, image_state="deleted (source art)", image_source="not attempted: no browser") for r in approved_intake(ctx())],
     "sourcing not attempted (the item fires with that reason instead)"),
    ("receive with no mode exits 2", lambda a: quiet(RC.main, a) == 2, [], ["--selftest"], "call the selftest path instead"),
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
    ("flavor cell: a LONGER flavor on the line (`Raspberry Lemonade`) never EXISTS on the item whose Flavor is its prefix "
     "(`Raspberry`); the whole flavor still EXISTS",
     lambda c: fc_is(c, "1", None) and fc_is(c, "2", "4001"), fc_ctx(), fc_ctx(guard=False),
     "no layout guard: the line merely CONTAINING the Flavor takes the item"),
    ("flavor cell: the line's flavor phrase may run on into the item's own body words (`Pomegranate Restore` on "
     "`Pomegranate Restore (1:1 THC:CBD)`) - EXISTS",
     lambda c: fc_is(c, "3", "4004"), fc_ctx(), fl_body(fc_ctx(), "4004", "Pomegranate (1:1 THC:CBD)"),
     "the item's body drops `Restore`: the line's phrase is longer than anything the item names"),
    ("brand slot: a non-brand word leading the product segment where the invoice's other lines under the column lead "
     "with the brand (`Pebbles - ...`) reads NO brand - NEW_BRAND + BRAND_NAME_UNREAD, never the column's brand",
     sl_slot_unread, sl_ctx(), sl_ctx("lead"),
     "no brand slot: the column's catalog brand, named anywhere on the line, is the line's brand"),
    ("brand slot: a sub-line lead with NO brand in any line's slot on the invoice (`Juniper - Raspberry`) stays the "
     "column brand's - EXISTS",
     lambda c: sl_rows(c)["2"]["verdict"] == "EXISTS" and sl_rows(c)["2"]["copy_source_sku"] == "4001",
     sl_ctx(lines="flavor-cell"), sl_ctx("slot", lines="flavor-cell"),
     "every column's lead is a slot, without a brand leading any line there"),
    ("flavored lane: a Strain record must be the WHOLE word run it sits in - `Lemonade` out of `Raspberry Lemonade` "
     "is a flavor word (STRAIN_MISSING); `Lemonade Gummies` takes the record",
     sl_strain_whole_run, sl_ctx(line_brands={"2": "Cedar Co"}), sl_ctx("run", line_brands={"2": "Cedar Co"}),
     "no run guard: the longest record phrase anywhere in the line is the Strain"),
    ("brand spelling: `TwinOak` on the line is catalog brand `Twin Oak` (space- and case-insensitive) - EXISTS",
     lambda c: sg_is(c, "1", "EXISTS", "6003"), sg_ctx(), sg_ctx("brand"),
     "brands compare as norm: the space counts, the line names no brand"),
    ("brand spelling: a direction `Red Fern` is the Brand record `RedFern` (no item) - NEW_PL under the record's spelling, never NEW_BRAND",
     lambda c: sg_is(c, "2", "NEW_PL", lane_Brand="RedFern"), sg_ctx(), sg_ctx("brand"),
     "brands compare as norm: `Red Fern` is nobody's, a new brand"),
    ("pack grain: a 1g single never EXISTS on the 0.5g x 2pk at the same grams; it copies the 1g single lane",
     lambda c: sg_is(c, "3", "NEW_ITEM_WITH_SIBLING", "6003", create_name_FINAL="Twin Oak | Pre-Roll | Lemon Haze | 1g")
     and sg_is(c, "4", "EXISTS", "6001") and sg_is(c, "5", "EXISTS", "6002"),
     sg_ctx(), sg_ctx("pack"), "no pack test: grams alone match the 1g line to the 0.5g x 2pk"),
    ("accents fold: `Piña Verde` on the line names the Strain record `Pina Verde` (never STRAIN_MISSING)",
     lambda c: sg_is(c, "6", "NEW_ITEM_WITH_SIBLING", strain="Pina Verde"), sg_ctx(), sg_ctx("fold"),
     "no accent folding: `pi a verde` names no record"),
    ("accents fold: `Jalapeno Haze` on the line is the item `Jalapeño Haze` - EXISTS",
     lambda c: sg_is(c, "7", "EXISTS", "6004"), sg_ctx(), sg_ctx("fold"),
     "no accent folding: the body reads `jalape o haze`"),
    ("receive --check join key is package_id, an intake CSV column",
     lambda cols: RC.CHECK_JOIN_KEY == "package_id" and RC.CHECK_JOIN_KEY in cols,
     IM.INTAKE_COLS, [c for c in IM.INTAKE_COLS if c != "package_id"], "remove package_id from the columns"),
    ("plan (R124): the synthetic batch plans 22 writes in step order with 0 refusals (P2 proven 2026-10-08)",
     lambda pr: len(pr[0]) == 22 and pr[1] == []
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
    ("plan: every create gets a global-link attempt - the sibling links its ONE exact-name Active record, the zero-hit "
     "cross-brand line is a `no record` result; no search at all refuses LINK_NOT_SEARCHED",
     lambda pr: not any(f["reason"] == "LINK_NOT_SEARCHED" for f in pr[1])
     and [r["product_key"] for r in pr[0] if r["step"] == "LINK"] == ["new:2"]
     and any(x.startswith("LINK_RESULT line 3") and ": no record:" in x for x in pr[2]),
     plan_of(), plan_of(link=False), "drop the catalog search file"),
    ("plan: a sibling copy adds its own art (IMAGE_ADD) and then removes the copied rows; image_keep = Y plans neither",
     lambda pr: [r["step"] for r in pr[0] if r["product_key"] == "new:2" and r["step"].startswith("IMAGE")]
     == ["IMAGE_ADD", "IMAGE_REMOVE"],
     plan_of(), plan_of(intake_edit=lambda i: i[1].update(image_keep="Y")), "the Operator marks the carried art generic"),
    ("certify --plan GREEN: A = 18 planned + 4 derived, B 1, C 0",
     lambda e: (lambda rep, f, c: f == [] and c["A"] == 18 and c["A_derived"] == 4 and c["B"] == 1 and c["C"] == 0)(*IC.run_plan(PFX, e)),
     None, lambda a, r, p: _pr(a, "601").update(Available="45"), "Available goes UP on the sibling"),
] + [(f"certify --plan: {flag} quiet on the clean batch, fires on its breaker",
      (lambda fl: (lambda e: fl not in plan_flags(e)))(flag), None, brk, how) for flag, how, brk in PLAN_BREAKERS]

# The Strains export header (2026-10-11): Dutchie renamed `Strain name` -> `Name`. ONE normaliser
# (intake_common.strain_name_col) resolves it for every reader; neither column = ABORT, never a blank name (R26 R75).
CHECKS += [
    ("STRAINS_HEADER: the old `Strain name` header loads the strain table",
     lambda h: strains_as(h) == BASE["strains"], STRAINS_OLD, ["Strain", "Type", "Abbreviation", "Description"],
     "misspell the name column `Strain`"),
    ("STRAINS_HEADER: the new `Name` header (fixture strains-name-header.csv) loads to the SAME dict as the old one",
     lambda p: (lambda got, hdr: hdr == STRAINS_NEW and got == BASE["strains"])(quiet(IM.load_strains, p), hdr_of(os.path.basename(p))),
     fx("strains-name-header.csv"), fx("strains.csv"), "read the OLD-header fixture instead (the header check is the point)"),
    ("STRAINS_HEADER: a file with NEITHER name column ABORTS (exit 2), never reads a blank name",
     lambda h: strains_as(h) == ("ABORT", C.EXIT_ABORT), ["Title", "Type", "Abbreviation", "Description"], STRAINS_NEW,
     "give the file the new `Name` header"),
    ("STRAINS_HEADER: a `Name` column on a NON-strains file is not a strains table (the other three columns decide)",
     lambda h: strains_as(h) == ("ABORT", C.EXIT_ABORT) and quiet(C.strain_name_col, h) == ("ABORT", C.EXIT_ABORT),
     ["Name", "Type", "Status", "Code"], STRAINS_NEW, "restore Abbreviation + Description beside `Name`"),
    ("STRAINS_HEADER: the freshest-file pick takes a `Name`-header Strains export (one-of required column)",
     lambda h: pick_strains(h),
     STRAINS_NEW, ["Title", "Type", "Abbreviation", "Description"], "a header with no name column at all"),
    ("STRAINS_HEADER: intake_plan reads strain records from a `Name`-keyed table (no MINT_STRAIN for a known strain)",
     lambda s: plan_mints(s) == [], plan_strains("Name", extra=[("Strain Q", "Sativa")]),
     plan_strains("Name", blank=True, extra=[("Strain Q", "Sativa")]), "every name cell read as blank"),
    ("STRAINS_HEADER: intake_plan ABORTS on a strain table with neither name column",
     lambda s: plan_mints(s) == ("ABORT", C.EXIT_ABORT), plan_strains("Title"), plan_strains("Name"),
     "key the table on `Name`"),
]


RCX = {"lines": rows_of("receive-lines.csv"), "catalog": rows_of("receive-catalog.csv"),
       "inventory": rows_of("receive-inventory.csv"), "manifest": rows_of("receive-manifest.csv")}
RC_ITEMS = {"1": "11", "2": "12", "3": "13", "4": "13"}
# R103 (amended 2026-10-11): a synthetic buy-4-get-1 - 4 paid cases of 10 at 18.37 (BG-1..4), the free case at 0.01
# (BG-5, stated `deal`), and a marked 1-unit sample of the same item beside it (BG-S).
BGX = {"lines": rows_of("receive-buyget-lines.csv"), "catalog": rows_of("receive-catalog.csv"),
       "inventory": rows_of("receive-inventory.csv"), "manifest": rows_of("receive-buyget-manifest.csv"),
       "items": {"1": "14", "2": "14", "3": "14"}, "programs": {"2": "deal"}}
BG_ROWS = ("1a", "1b", "1c", "1d", "2")


def bg_ctx(drop_line=None, programs=None):
    c = copy.deepcopy(BGX)
    if drop_line:
        c["lines"] = [r for r in c["lines"] if r["line_no"] != drop_line]
        c["manifest"] = [r for r in c["manifest"] if r["line"] != drop_line]
    if programs is not None:
        c["programs"] = programs
    return c


def bg_blended(rw):
    """Every package of the deal at the blended unit (the remainder on the last), all tagged, the deal tied."""
    if not all(k in rw for k in BG_ROWS):
        return False
    total = sum(float(rw[k]["cost_entered"]) * float(rw[k]["expected_qty"]) for k in BG_ROWS)
    return ([rw[k]["cost_entered"] for k in BG_ROWS] == ["14.70"] * 4 + ["14.69"] and abs(total - 734.90) < 0.005
            and all(rw[k]["pkg_tags_to_apply"] == "PKG - Vendor Deal" for k in BG_ROWS))


def rc_prep(c):
    """receive --prep on a receive fixture context -> (rows by row id, [(flag, class, line)])."""
    rows, exc, _ = RC.prep(c["lines"], c["catalog"], c["inventory"], c.get("intake"), c["manifest"],
                           c.get("items", RC_ITEMS), c.get("programs"), "PKG - Vendor Deal")
    return {r["row"]: r for r in rows}, [(e["flag"], e["class"], e["line"]) for e in exc]


def rc_intake(verdict="EXISTS", skip=(), extra=(), items=None, **cells):
    """The receive fixture with an intake CSV (one row per product line, `invoice_line` == description) and NO --item:
    the item id comes from the intake (EXISTS -> copy_source_productid). `cells` overwrite the lane cells (the lies
    the runner must not read)."""
    c = copy.deepcopy(RCX)
    c["intake"] = [dict({"invoice_line": ln["description"], "verdict": verdict, "new_productid": "",
                         "copy_source_productid": RC_ITEMS[ln["line_no"]], "create_name_FINAL": "", "tags": "",
                         "lane_Cost": ""}, **cells)
                   for ln in c["lines"] if ln["line_no"] in RC_ITEMS and ln["line_no"] not in skip] + list(extra)
    c["items"] = items or {}
    return c


def rc_with(c, kind, pred, **changes):
    for r in c[kind]:
        if pred(r):
            r.update(changes)
    return c


def rc_tenant(placeholders):
    """(blocking, warnings) for receive --prep's pointer read on the fixture tenant with the named lines placeholdered."""
    text = BASE["tenant"]
    for line, ph in placeholders:
        text = text.replace(line, ph)
    return PTR.split_problems(PTR.parse_text(text), ["Vendor deal tag"], RC.TENANT_OPTIONAL)


DRIVE_PH = ("Drive invoices folder: fixture-folder-id", "Drive invoices folder: <Drive folder id>")
DEAL_PH = ("Vendor deal tag: `PKG - Vendor Deal`", "Vendor deal tag: `<PKG - tag>`")
STRAY_INTAKE = {"invoice_line": "Some Other Vendor Item 1g", "verdict": "EXISTS", "new_productid": "",
                "copy_source_productid": "12", "create_name_FINAL": "", "tags": "", "lane_Cost": ""}


def rc_mut(kind, pred, **changes):
    c = copy.deepcopy(RCX)
    for r in c[kind]:
        if pred(r):
            r.update(changes)
    return c


def rc_drop(kind, pred):
    c = copy.deepcopy(RCX)
    c[kind] = [r for r in c[kind] if not pred(r)]
    return c


def rc_only(line, pkg, programs=None):
    """The fixture receipt with one new-line row and its package removed (+ stated dispositions)."""
    c = copy.deepcopy(RCX)
    c["lines"] = [r for r in c["lines"] if r["line_no"] != line]
    c["manifest"] = [r for r in c["manifest"] if r["package_id"] != pkg]
    c["programs"] = programs
    return c


def rc_new_pl(rw):
    """(rows keeping `ITM - New PL`, the flip text of item 13's rows) - R47 R83 R126."""
    nl = [r for r in rw.values() if r.get("new_line_tag_on_package", "").startswith("yes")]
    return len(nl), {r["item_tag_flip"] for r in rw.values() if r.get("dutchie_productid") == "13"}


RECEIVE_CHECKS = [
    ("receive --prep: one row per Metrc package (line 1 ships as PKG-A + PKG-B -> rows 1a / 1b)",
     lambda c: (lambda rw: "1a" in rw and "1b" in rw and "1" not in rw)(rc_prep(c)[0]),
     RCX, rc_drop("manifest", lambda r: r["package_id"] == "PKG-B"), "drop the second package (it becomes a qty gap)"),
    ("receive --prep: the manifest ties - no DEFECT on the clean receipt",
     lambda c: not [f for f in rc_prep(c)[1] if f[1] == "DEFECT"],
     RCX, rc_mut("manifest", lambda r: r["package_id"] == "PKG-C", ship_cost="480.00"), "ship $ on PKG-C $20 short"),
    ("receive --prep: a sample merged into its paid package is a STOP (SAMPLE_MERGED)",
     lambda c: ("SAMPLE_MERGED", "STOP", "4") in rc_prep(c)[1],
     (lambda c: (c.update(manifest=[dict(r, qty="15", ship_cost="200.05") if r["package_id"] == "PKG-D" else r
                                    for r in c["manifest"] if r["package_id"] != "PKG-E"]), c)[1])(copy.deepcopy(RCX)),
     RCX, "give the sample its own package"),
    ("receive --prep: every package goes to Intake; the item's ITM tags strip except the new-line tag (R47)",
     lambda c: (lambda rw: all(r["receive_room"] == "Intake" for r in rw.values() if r["line"] != "90")
                and rw["3"]["itm_tags_to_strip"] == "ITM - Protect")(rc_prep(c)[0]),
     RCX, rc_mut("catalog", lambda r: r["ProductId"] == "13", Tags="ITM - New PL; ITM - Protect; ITM - Discontinue"),
     "a second ITM tag on the item (it must strip too)"),
    ("receive --prep: the order-level credit prints once and blends equally per package (R126)",
     lambda c: (lambda rw: rw.get("90", {}).get("flags", "").startswith("ORDER-LEVEL CREDIT")
                and rw["2"]["blended_unit_cost"] == f"{(500 - 10 / 5) / 100:.4f}")(rc_prep(c)[0]),
     RCX, rc_drop("lines", lambda r: r["line_no"] == "90"), "drop the credit line"),
    ("receive --prep: SAMPLE-ONLY new line - no flip, 0 packages carry `ITM - New PL` (R47 R83 R126)",
     lambda c: (lambda n, f: n == 0 and len(f) == 1 and next(iter(f)).startswith("no flip - sample-only receipt"))(
         *rc_new_pl(rc_prep(c)[0])),
     rc_only("3", "PKG-D"), rc_only("3", "PKG-D", {"4": "none"}), "the sample line is stated sellable"),
    ("receive --prep: MIXED receipt - the item flips; only the sellable package keeps `ITM - New PL` (R47 R83 R126)",
     lambda c: (lambda rw: rc_new_pl(rw)[0] == 1 and rw["3"]["new_line_tag_on_package"].startswith("yes")
                and "ITM - New PL" in rw["4"]["itm_tags_to_strip"]
                and rc_new_pl(rw)[1] == {"ITM - New PL -> ITM - Active after the receipt (R126)"})(rc_prep(c)[0]),
     RCX, dict(copy.deepcopy(RCX), programs={"3": "sample"}), "the paid package is stated a sample too"),
    ("receive --prep: SELLABLE-ONLY receipt - flips as before; the package keeps `ITM - New PL` (R83 R126)",
     lambda c: (lambda n, f: n == 1 and f == {"ITM - New PL -> ITM - Active after the receipt (R126)"})(
         *rc_new_pl(rc_prep(c)[0])),
     rc_only("4", "PKG-E"), rc_only("4", "PKG-E", {"3": "display"}), "the only package is stated a display"),
    ("receive --prep tenant read: a placeholder in a key it does not read (Drive folder) is a WARNING, never an abort",
     lambda ph: (lambda b, w: b == [] and any("Drive invoices folder" in x for x in w))(*rc_tenant(ph)),
     [DRIVE_PH], [DRIVE_PH, DEAL_PH], "the Vendor deal tag (a key --prep reads) is a placeholder too"),
    ("receive --prep: a typed `1a` / `1b` manifest line reads as line 1 (rows 1a / 1b, no MANIFEST_PACKAGE_UNMAPPED)",
     lambda c: (lambda rw, fl: "1a" in rw and "1b" in rw and not any(f[0] == "MANIFEST_PACKAGE_UNMAPPED" for f in fl))(
         *rc_prep(c)),
     rc_with(rc_with(copy.deepcopy(RCX), "manifest", lambda r: r["package_id"] == "PKG-A", line="1a"),
             "manifest", lambda r: r["package_id"] == "PKG-B", line="1b"),
     rc_with(rc_with(copy.deepcopy(RCX), "manifest", lambda r: r["package_id"] == "PKG-A", line="9a"),
             "manifest", lambda r: r["package_id"] == "PKG-B", line="1b"), "type `9a` (no line 9) on PKG-A"),
    ("receive --prep: an `<n><letter>` whose <n> is not a product line stays a DEFECT (MANIFEST_PACKAGE_UNMAPPED)",
     lambda c: ("MANIFEST_PACKAGE_UNMAPPED", "DEFECT", "9a") in rc_prep(c)[1],
     rc_mut("manifest", lambda r: r["package_id"] == "PKG-A", line="9a"),
     rc_mut("manifest", lambda r: r["package_id"] == "PKG-A", line="1a"), "type `1a` instead"),
    ("receive --prep: physical_count = the package count and qty_match = Y on every mapped package (no count question)",
     lambda c: (lambda mp: bool(mp) and all(r["physical_count"] == r["expected_qty"] and r["qty_match"] == "Y" for r in mp))(
         [r for r in rc_prep(c)[0].values() if r.get("metrc_package_id")]),
     RCX, dict(copy.deepcopy(RCX), manifest=None), "no manifest read (no mapped package)"),
    ("receive --prep: an intake-resolved item reads catalog Cost by ProductId, never the intake lane_Cost",
     lambda c: (lambda rw, fl: rw["1a"]["dutchie_productid"] == "11" and rw["1a"]["catalog_cost"] == "10"
                and not any(f[0] in ("PRICE_DROP_UNMARKED", "CATALOG_COST_RAISE") for f in fl))(*rc_prep(c)),
     rc_intake(lane_Cost="99"), rc_with(rc_intake(lane_Cost="99"), "catalog", lambda r: r["ProductId"] == "11", Cost="12"),
     "the CATALOG Cost of item 11 is 12 (the price drop is then real)"),
    ("receive --prep: the flip reads the item's CURRENT catalog tags, never the intake `tags` cell (R83)",
     lambda c: not any(r["item_tag_flip"] for r in rc_prep(c)[0].values() if r.get("dutchie_productid") == "11"),
     rc_intake(tags="ITM - New PL"),
     rc_with(rc_intake(tags="ITM - New PL"), "catalog", lambda r: r["ProductId"] == "11", Tags="ITM - New PL"),
     "the catalog tags item 11 new-line"),
    ("receive --prep: a pending line (intake row, no item id) compares no lane_Cost and flips nothing",
     lambda c: (lambda rw, fl: ("ITEM_PENDING", "STOP", "1") in fl and not any(f[0] == "PRICE_DROP_UNMARKED" for f in fl)
                and not any(r.get("item_tag_flip") for r in rw.values()))(*rc_prep(c)),
     rc_intake("NEW_PL", lane_Cost="12", tags="ITM - New PL"),
     rc_with(rc_intake("NEW_PL", lane_Cost="12", tags="ITM - New PL", items={"1": "11"}), "catalog",
             lambda r: r["ProductId"] == "11", Cost="12"), "--item 1=11 and the catalog Cost of 11 is 12"),
    ("receive --prep: an intake row pairing to no product line is INTAKE_ROW_UNPAIRED (STOP)",
     lambda c: ("INTAKE_ROW_UNPAIRED", "STOP", "") in rc_prep(c)[1],
     rc_intake(extra=[STRAY_INTAKE]), rc_intake(), "drop the stray intake row"),
    ("receive --prep: a product line no intake row pairs to is LINE_NO_INTAKE_ROW (STOP), never ITEM_PENDING",
     lambda c: (lambda fl: ("LINE_NO_INTAKE_ROW", "STOP", "2") in fl and not any(f[0] == "ITEM_PENDING" and f[2] == "2" for f in fl))(
         rc_prep(c)[1]),
     rc_intake(skip=("2",)), rc_intake(), "give line 2 its intake row"),
    ("receive --prep: an on-hand pkg cost ABOVE the new cost is no question when new == catalog Cost (R62)",
     lambda c: (lambda rw, fl: rw["3"]["on_hand_pkg_costs"] == "22"
                and not any(f[2] == "3" and f[1] in ("STOP", "DEFECT") for f in fl))(*rc_prep(c)),
     dict(copy.deepcopy(RCX), inventory=RCX["inventory"] + [{"SKU": "9013", "Room": "Vault", "Available": "3", "Cost": "22"}]),
     rc_with(rc_with(dict(copy.deepcopy(RCX), inventory=RCX["inventory"] + [{"SKU": "9013", "Room": "Vault", "Available": "3",
                                                                              "Cost": "22"}]),
                     "lines", lambda r: r["line_no"] == "3", unit_cost="18.00", ext_cost="180.00"),
             "manifest", lambda r: r["package_id"] == "PKG-D", ship_cost="180.00"),
     "the new cost is 18, BELOW catalog Cost 20, no deal marked"),
    ("receive --prep: the questions header prints Vendor, Room and the Transaction ID (receive form header)",
     lambda ls: (lambda q: "- Vendor: Acme Supply" in q and "- Room: Intake" in q and "- Transaction ID: SO-1001" in q)(
         RC.questions([], {"product_lines": 4, "packages": 5, "manifest": True, "order_level": 0.0}, "x",
                      RC.header_values(ls))),
     RCX["lines"], [{k: v for k, v in r.items() if k not in ("vendor", "invoice_no")} for r in RCX["lines"]],
     "lines with no vendor / invoice_no cells"),
    ("receive --prep: Metrc grams on a pre-roll count by the unit size (100 g / 1 g = 100; manifest_qty `100 g`), quiet",
     lambda c: (lambda rw, fl: rw["2"]["expected_qty"] == "100" and rw["2"]["manifest_qty"] == "100 g"
                and not any(f[0].startswith("MANIFEST_") for f in fl))(*rc_prep(c)),
     RCX, rc_mut("manifest", lambda r: r["package_id"] == "PKG-C", uom=""), "the `uom` cell is blank (a bare qty)"),
    ("receive --prep: a wrong-size ship (50 g of a 0.5g pre-roll billed 100 x 1g) is MANIFEST_ITEM_SIZE_MISMATCH (STOP), "
     "never a MANIFEST_QTY_MISMATCH short ship (Operator 2026-10-18)",
     lambda c: (lambda rw, fl: ("MANIFEST_ITEM_SIZE_MISMATCH", "STOP", "2") in fl and rw["2"]["expected_qty"] == "100"
                and not any(f[0] == "MANIFEST_QTY_MISMATCH" for f in fl))(*rc_prep(c)),
     dict(copy.deepcopy(RCX), manifest=rows_of("receive-wrongsize-manifest.csv")), RCX, "the billed 1g pre-roll ships"),
    ("receive --prep: a bare qty on a gram-based item is MANIFEST_UOM_UNREAD (STOP); the old count reading misfires a "
     "short ship",
     lambda c: (lambda fl: ("MANIFEST_UOM_UNREAD", "STOP", "2") in fl and ("MANIFEST_QTY_MISMATCH", "STOP", "2") in fl)(
         rc_prep(c)[1]),
     rc_with(dict(copy.deepcopy(RCX), manifest=rows_of("receive-wrongsize-manifest.csv")), "manifest",
             lambda r: r["package_id"] == "PKG-C", uom=""),
     dict(copy.deepcopy(RCX), manifest=rows_of("receive-wrongsize-manifest.csv")), "type `uom` g"),
    ("receive --prep: a `g` package whose Metrc item names no size is MANIFEST_GRAMS_UNSIZED (STOP), never guessed",
     lambda c: (lambda rw, fl: ("MANIFEST_GRAMS_UNSIZED", "STOP", "2") in fl and rw["2"]["physical_count"] == ""
                and not any(f[0] == "MANIFEST_QTY_MISMATCH" for f in fl))(*rc_prep(c)),
     rc_mut("manifest", lambda r: r["package_id"] == "PKG-C", metrc_item="Haze Pre-Roll", qty="50"), RCX,
     "the item names `1g`"),
    ("receive --prep R103: a buy-4-get-1 blends over EVERY package of the deal (14.70 x4, remainder 14.69 on the last; "
     "734.90 ties to the invoice; all 5 `PKG - Vendor Deal`)",
     lambda c: bg_blended(rc_prep(c)[0]), BGX, bg_ctx(drop_line="1"), "the paid cases are gone (a lone penny line)"),
    ("receive --prep R103: the marked sample beside the deal stays `PKG - Employee` at its own price (R127)",
     lambda c: (lambda rw: rw["3"]["pkg_tags_to_apply"] == "PKG - Employee" and rw["3"]["cost_entered"] == "0.01"
                and rw["3"]["deal"] == "")(rc_prep(c)[0]),
     BGX, bg_ctx(programs={"2": "deal", "3": "deal"}), "the sample line is stated part of the deal"),
    ("receive --prep R103: an unmarked penny line inside a deal is still asked (PENNY_UNMARKED STOP), the blend proposed",
     lambda c: ("PENNY_UNMARKED", "STOP", "2") in rc_prep(c)[1] and bg_blended(rc_prep(c)[0]),
     bg_ctx(programs={}), BGX, "`--program 2=deal` states the deal"),
]


def runner_tenant(keys, placeholders):
    """(blocking, warnings) for a runner's own pointer read (its tenant_keys) on the fixture tenant with the named
    lines placeholdered - the read intake_pointers.load_for makes."""
    text = BASE["tenant"]
    for line, ph in placeholders:
        text = text.replace(line, ph)
    return PTR.split_problems(PTR.parse_text(text), *keys)


def drive_warn_only(keys):
    """The check: on the given placeholders the runner's read does not block, and the Drive gap is a WARNING."""
    return lambda ph: (lambda b, w: b == [] and any("Drive invoices folder" in x for x in w))(*runner_tenant(keys, ph))


INTAKE_PH = ("Intake dir: ./intake-out", "Intake dir: <abs path>")
EXPORTS_PH = ("Exports dir: ./", "Exports dir: <abs path>")
NOTICE_PH = ("Notice template: ../templates/notice.md", "Notice template: <abs path>")
OWN_PH = ("Own store: exampleco", "Own store: <token>")
# Each runner names the keys it reads (tenant_keys -> intake_pointers.load_for). An unfilled `Drive invoices folder` -
# read only by the pull procedure, which files the invoice to Drive - is a WARNING to every runner; a placeholder in a
# key the runner DOES read still blocks it.
RUNNER_KEYS = [("parse", IP.tenant_keys([]), INTAKE_PH), ("match", IM.tenant_keys([]), EXPORTS_PH),
               ("exceptions", IE.tenant_keys([]), DEAL_PH), ("plan", PL.tenant_keys([]), INTAKE_PH),
               ("certify", IC.tenant_keys([]), INTAKE_PH), ("notice", IN.tenant_keys([]), NOTICE_PH),
               ("msrp", MS.tenant_keys([]), OWN_PH)]
POINTER_CHECKS = [(f"{name} tenant read: the Drive folder placeholder is a WARNING, never an abort", drive_warn_only(keys),
                   [DRIVE_PH], [DRIVE_PH, br], f"the `{br[0].split(':')[0]}` line (a key {name} reads) is a placeholder too")
                  for name, keys, br in RUNNER_KEYS]
POINTER_CHECKS += [
    ("pull gate (the Drive filer): a whole contract passes; the Drive folder placeholder BLOCKS it",
     lambda ph: runner_tenant(PTR.PROCEDURE_KEYS["pull"], ph) == ([], []),
     [], [DRIVE_PH], "the Drive folder is a placeholder"),
    ("no runner's tenant_keys names `Drive invoices folder` (only the pull gate reads it)",
     lambda extra: not any("Drive invoices folder" in k[0] + list(k[1]) for k in [r[1] for r in RUNNER_KEYS] + extra),
     [], [PTR.PROCEDURE_KEYS["pull"]], "count the pull gate as a runner"),
]


# R68 (amended 2026-10-11): a create into a PRODUCT LINE whose every active item carries the discontinue tag is tagged
# with it at create and flagged PL_DISCONTINUED_CREATE (INFO); a mixed, an untagged and a NEW line print nothing. Line 3
# (Gelato) copies into the Acme pre-roll line (live 501 + 502; 503 is a dead record, R81, in no line); line 5 is a
# NEW_PL cartridge whose `Cartridge | 0.5g | Acme Farms` line has no sibling.
DISC = C.DEFAULT_DISCONTINUE_TAG


def r68_line(*tags):
    """The fixture with the two live Acme pre-roll siblings' decision tags set (Status - Live kept beside them)."""
    c = ctx()
    for sku, tg in zip(("1001", "1002"), tags):
        mut(c, "active", lambda r, s=sku: r["SKU"] == s, Tags=", ".join(x for x in ("Status - Live", tg) if x))
    return c


def r68_row(c, prefix):
    r = row_for(c, prefix)
    return "PL_DISCONTINUED_CREATE" in r["flags"].split(";"), r["tags"]


def acme_cart(c, grams="1g", tag=DISC):
    """Add a live Acme Farms cartridge of `grams` carrying `tag` (same Category as line 5's NEW_PL placement)."""
    base = next(r for r in c["active"] if r["SKU"] == "2001")
    c["active"].append(dict(base, ProductId="611", SKU="2011", Product=f"Acme Farms | Distillate Cart | Blue Dream | {grams}",
                            Brand="Acme Farms", Strain="Blue Dream", **{"Product grams": grams, "Tags": tag}))
    return c


CHECKS += [
    ("R68 FIRES: a create into a wholly-discontinued line takes the discontinue tag + PL_DISCONTINUED_CREATE (INFO)",
     lambda c: r68_row(c, "Acme Farms Gelato") == (True, DISC),
     r68_line(DISC, DISC), r68_line(DISC, C.DEFAULT_ACTIVE_TAG), "one sibling on the Active tag (a MIXED line)"),
    ("R68 QUIET: a MIXED line (one sibling tagged) prints nothing and the create reads the Active tag",
     lambda c: r68_row(c, "Acme Farms Gelato") == (False, C.DEFAULT_ACTIVE_TAG),
     r68_line(DISC, C.DEFAULT_ACTIVE_TAG), r68_line(DISC, DISC), "tag the other sibling too (a wholly-discontinued line)"),
    ("R68 QUIET: an UNTAGGED line (no sibling carries the tag) prints nothing",
     lambda c: r68_row(c, "Acme Farms Gelato")[0] is False,
     ctx(), r68_line(DISC, DISC), "tag both siblings"),
    ("R68 QUIET: a NEW line (no sibling under its key) keeps the new-line tag, even beside a discontinued line of the brand",
     lambda c: r68_row(c, "Acme Farms Northern Lights") == (False, C.DEFAULT_NEW_LINE_TAG),
     acme_cart(r68_line(DISC, DISC), "1g"), acme_cart(r68_line(DISC, DISC), "0.5g"),
     "the brand's discontinued cartridge is 0.5g, the same line as the create"),
    ("R68: the tenant's `PL key:` function decides the line, not the skill's default (Category | Brand reads the 1g cart)",
     lambda fn: r68_row(dict(acme_cart(ctx(), "1g"), pl_key_fn=fn), "Acme Farms Northern Lights")[0] is True,
     IM.line_options([], PTR.load(fx("tenant-CLAUDE.md")))[1], C.pl_key_default,
     "the skill's default key (it reads the dose: 0.5g is a NEW line)"),
]


# R125 (amended 2026-10-11): a SAMPLE-ONLY new line takes its Cost from the vendor's Apex PO, else the Apex catalog listing;
# neither = COST_UNKNOWN (STOP), and a sibling brand's Cost is never the fallback. Plan fixture row 3 is a NEW_PL cross-brand
# copy of Brand B's 701 (Cost 9); here its invoice price is the sample price shape (0.05), so the line is sample-only.
APEX_PO = dict(source="po", ref="T-77", item="Brand A Lime Gummies 10pk", price="330", per="case", units_per_case="30",
               unit_shown="")                                                     # -> 11.00
APEX_CAT = dict(source="catalog", ref="Brand A Wholesale", item="Lime Gummies - 100mg - 10ct", price="300", per="case",
                units_per_case="30", unit_shown="10.00")                          # -> 10.00
APEX_NONE = dict(source="none", ref="marketplace search `Brand A Lime`", item="", price="", per="", units_per_case="",
                 unit_shown="")


def apex_intake(*reads, unit="0.05"):
    """The plan fixture's intake with row 3 at `unit`, run through intake_apex_cost.settle with the typed `reads`."""
    rows = copy.deepcopy(rows_of("plan-intake.csv"))
    rows[2]["unit_cost"] = unit
    apex = {"3": [dict(a, row="3", read_date="2026-10-11") for a in reads]} if reads else {}
    return AC.settle(rows, apex)[0]


def plan_on(intake):
    return PL.build_plan(intake, rows_of("plan-pre-active.csv"), rows_of("plan-pre-retired.csv"), rows_of("plan-strains.csv"),
                         rows_of("plan-categories.csv"), rows_of("plan-brands.csv"), guard=PL._probed(),
                         link_search=rows_of("plan-catalog-search.csv"), catalog_state="ST")


def apex_cost_row(intake):
    """(the create's planned Cost row or None, COST_UNKNOWN refused on row 3) for an intake."""
    rows, ref, _ = plan_on(intake)
    return (next((r for r in rows if r["product_key"] == "new:3" and r["field"] == "Cost"), None),
            any(f["reason"] == "COST_UNKNOWN" and str(f["line_no"]) == "3" for f in ref))


def apex_planned(target, *needles):
    def pred(intake):
        row, refused = apex_cost_row(intake)
        return (row is not None and not refused and row["target"] == target
                and all(n in row["provenance"] for n in needles))
    return pred


def apex_certify(post_cost):
    """The ONE certify on a plan whose create Cost came from Apex (PO, 11.00): post item 802 carries `post_cost`."""
    fx_ = IC.plan_fixture()
    fx_["plan"] = plan_on(apex_intake(APEX_PO))[0]
    _pr(fx_["qa"], "802")["Cost"] = post_cost
    return IC.run_plan(fx_)[1]


CHECKS += [
    ("R125 PO: an Apex PO at $330 / case of 30 plans the create's Cost at 11, its provenance naming apex:po + the read date",
     apex_planned("11", "derived Cost 11.00 (R125: apex:po T-77", "read 2026-10-11; $330.00 / case of 30"),
     apex_intake(APEX_PO), apex_intake(), "no Apex read: the plan refuses the Cost (COST_UNKNOWN)"),
    ("R125 PO beats catalog: with both read, the PO's 11 is the Cost, never the listing's 10",
     apex_planned("11", "apex:po T-77"), apex_intake(APEX_CAT, APEX_PO), apex_intake(APEX_CAT), "the PO read dropped"),
    ("R125 CATALOG: no PO - the vendor's listing at $300 / case of 30 ($10.00 / unit printed) plans Cost 10, apex:catalog",
     apex_planned("10", "R125: apex:catalog Lime Gummies - 100mg - 10ct, read 2026-10-11"),
     apex_intake(APEX_CAT), apex_intake(dict(APEX_CAT, unit_shown="11.00")),
     "Apex prints $11.00 / unit beside it: APEX_UNIT_MISMATCH, nothing settled"),
    ("R125 NONE: no PO and no listing -> COST_UNKNOWN (STOP) on the row, lane_Cost blank, the plan refuses the create's Cost "
     "(never the sample price, never Brand B's 9)",
     lambda i: ("COST_UNKNOWN" in i[2]["flags"].split(";") and i[2]["lane_Cost"] == ""
                and apex_cost_row(i) == (None, True)),
     apex_intake(APEX_NONE), apex_intake(APEX_NONE, APEX_CAT), "a listing found beside the empty PO search"),
    ("R125 guard: a sample-only create row that never ran the Apex step is REFUSED by the plan (COST_UNKNOWN)",
     lambda i: apex_cost_row(i)[1], [dict(r, unit_cost="0.05") if k == 2 else r for k, r in enumerate(rows_of("plan-intake.csv"))],
     rows_of("plan-intake.csv"), "row 3 is a paid line (invoice 8): not sample-only"),
    ("R125 certify: the Apex Cost is a PLANNED cell (certify GREEN); the copy source's Cost surviving is PLAN_NOT_APPLIED",
     lambda c: apex_certify(c) == [], "11", "9", "the created item kept Brand B's Cost 9"),
]


def rows_json(name):
    with open(fx(name), encoding="utf-8") as f:
        return json.load(f)


def open_cases(mutate=None, error=None):
    """The STOP's part 7 on the fixture read (`open-cases-rows.json`), after one named mutation of its row."""
    if error is not None:
        return CS.stop_block({"error": error}, "EXAMPLE", ["Northwind Distribution"])
    row = copy.deepcopy(rows_json("open-cases-rows.json")[0])
    if mutate:
        mutate(row)
    return CS.stop_block({"row": row}, "EXAMPLE", ["Northwind Distribution"], [], rows_of("invoice-lines.csv"))


def _retype(row, case_id, case_type):
    next(c for c in row["cases"] if c["case_id"] == case_id)["case_type"] = case_type


CHECKS += [
    ("open cases at the STOP: the vendor's CREDIT_DUE case prints FIRST with its detail text and fires CASE_CREDIT_DUE",
     lambda b: ("CASE_CREDIT_DUE", "case 9 CREDIT_DUE AWAITING_VENDOR") in b[1]
     and b[0].index("**Case 9 - CREDIT_DUE") < b[0].index("**Case 4 - ") and "stays OUT of package cost" in b[0],
     open_cases(), open_cases(lambda r: _retype(r, 9, "OTHER")), "the credit case filed as OTHER"),
    ("open cases at the STOP: a vendor no party matches is VENDOR_PARTY_UNMATCHED, never a silent `no case`",
     lambda b: "VENDOR_PARTY_UNMATCHED" not in [k for k, _ in b[1]] and "Party: `northwind-distribution`" in b[0],
     open_cases(), open_cases(lambda r: r.update(parties=[], cases=[])), "no party matched the vendor's names"),
    ("open cases at the STOP: a warehouse with no `cases` schema is a quiet INFO (no STOP-class flag)",
     lambda b: [CS.STOP_CLASS[k] for k, _ in b[1]] == ["INFO"],
     open_cases(error='ERROR: relation "cases.cases" does not exist'), open_cases(error="connection timed out"),
     "the read failed for another reason (CASE_READ_FAILED, STOP)"),
]


def rc_questions(c, state="rows", mutate=None):
    """receive --prep's questions file on a receive fixture context, with the vendor's open cases: the fixture read
    (`open-cases-rows.json`, after one named mutation of its row), 'unread', or None (no case store)."""
    _, exc, summ = RC.prep(c["lines"], c["catalog"], c["inventory"], c.get("intake"), c["manifest"],
                           c.get("items", RC_ITEMS), c.get("programs"), "PKG - Vendor Deal")
    if state == "rows":
        row = copy.deepcopy(rows_json("open-cases-rows.json")[0])
        if mutate:
            mutate(row)
        state = {"row": row}
    cases = RC.open_cases(state, "EXAMPLE", ["Northwind Distribution"], [], "x-open-cases.sql") if state else RC.open_cases(None)
    return RC.questions(exc + cases["exc"], summ, "x", None, cases)


def section(text, head):
    """The paragraph of the questions file that starts with `head` (up to the next blank line), else ''."""
    i = text.find(head)
    return text[i:text.find("\n\n", i)] if i >= 0 else ""


def _resolve_credit(row):
    row["cases"] = [c for c in row["cases"] if c["case_type"] != "CREDIT_DUE"]


CHECKS += [
    ("receipt questions: an open CREDIT_DUE case is named beside the header credit (R126) and asked as a STOP",
     lambda q: "line 90 Credit for returned stock -10.00" in section(q, "Header credit (R126)")
     and "Open CREDIT_DUE case 9 " in section(q, "Header credit (R126)") and "| CASE_CREDIT_DUE | STOP |" in q,
     rc_questions(RCX), rc_questions(RCX, mutate=lambda r: _retype(r, 9, "OTHER")), "the credit case filed as OTHER"),
    ("receipt questions: an open CREDIT_DUE case is named beside the Buy-Get blend (R103)",
     lambda q: "Open CREDIT_DUE case 9 " in section(q, "Buy-Get deals (R103)"),
     rc_questions(bg_ctx()), rc_questions(bg_ctx(), mutate=_resolve_credit), "the CREDIT_DUE case is not in the read"),
    ("receipt questions: the open cases print CREDIT_DUE first with the OPENED detail; a clean deal receipt is not "
     "`ready for entry` while one is open",
     lambda q: 0 <= q.find("**Case 9 - CREDIT_DUE") < q.find("**Case 4 - SIZE_MISMATCH") and "stays OUT of package cost" in q
     and "No STOP and no DEFECT" not in q,
     rc_questions(bg_ctx()), rc_questions(bg_ctx(), mutate=lambda r: _retype(r, 9, "OTHER")), "the credit case filed as OTHER"),
    ("receipt questions: no Case store pointer is a quiet INFO - no case STOP, no case named beside the credit",
     lambda q: "INFO CASE_STORE_ABSENT" in q and "| CASE" not in q and "CASES_UNREAD" not in q,
     rc_questions(RCX, None), rc_questions(RCX, "unread"), "a case store whose read has not run"),
    ("receipt questions: an unread case store says beside the header credit that no CREDIT_DUE case can be checked",
     lambda q: "CASES_UNREAD: the vendor's open cases are not seen" in section(q, "Header credit (R126)"),
     rc_questions(RCX, "unread"), rc_questions(rc_drop("lines", lambda r: r["line_no"] == "90"), "unread"),
     "no credit line on the receipt (no header credit to name it beside)"),
]

def run_checks():
    bad = []
    for name, pred, good, broken, how in CHECKS + RECEIVE_CHECKS + POINTER_CHECKS:
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


def drive_ph_tenant(dirpath):
    """A copy of the fixture tenant under `dirpath` with `Drive invoices folder` a placeholder (the fixture's relative
    paths made absolute; `Intake dir` stays relative, so it lands in `dirpath/intake-out`). Returns its path."""
    os.makedirs(os.path.join(dirpath, "intake-out"), exist_ok=True)
    text = BASE["tenant"].replace(*DRIVE_PH)
    for a, b in (("Exports dir: ./", "Exports dir: " + FX),
                 ("Notice template: ../templates/notice.md",
                  "Notice template: " + os.path.join(os.path.dirname(FX), "templates", "notice.md")),
                 ("FL EQ classes: ./fl-eq-classes.toml", "FL EQ classes: " + fx("fl-eq-classes.toml")),
                 ("PL key: ./pl_key_example.py", "PL key: " + fx("pl_key_example.py"))):
        text = text.replace(a, b)
    p = os.path.join(dirpath, "CLAUDE.md")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)
    return p


def pull_gate(tenant):
    """(exit code, stderr) of the pull procedure's pointer gate: intake_pointers.py --tenant <t> --for pull."""
    r = subprocess.run([sys.executable, "intake_pointers.py", "--tenant", tenant, "--for", "pull"], capture_output=True,
                       text=True, encoding="utf-8", env=ENV, cwd=HERE)
    return r.returncode, r.stderr


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
                       "--brands", fx("brands.csv"), "--out-dir", t, "--slug", "example", "--drop-tag", DROP[0],
                       "--fl-eq-classes", fx("fl-eq-classes.toml")], 0)
        v1 = next(os.path.join(t, n) for n in os.listdir(t) if n.endswith("-v1.csv"))
        td = os.path.join(t, "tenant-key")
        out = step("match --tenant (R68: the `PL key:` pointer names the line key)",
                   ["intake_match.py", "--lines", lines, "--active", fx("catalog-active.csv"), "--retired",
                    fx("catalog-retired.csv"), "--strains", fx("strains.csv"), "--tenant", fx("tenant-CLAUDE.md"),
                    "--out-dir", td, "--slug", "example", "--drop-tag", DROP[0]], 0)
        if "R68 line state: PL key" not in out or "pl_key_example.py:pl_of" not in out:
            bad.append("match PL key pointer")
            print("  FAIL  match --tenant must print the R68 line key it read from the `PL key:` pointer")
        else:
            print("  PASS  match --tenant prints the R68 line key from the `PL key:` pointer")
        with open(v1, encoding="utf-8") as f:
            hdr = next(csv.reader(f))
        if (hdr != IM.INTAKE_COLS or len(hdr) != 57 or hdr[-5:] != ["parse_source", "package_id", "unretire_set", "image_source", "derived"]
                or hdr[:54] != IM.V3_COLS):
            bad.append("v6 header")
            print(f"  FAIL  intake CSV header is not the 57-column v6 ({len(hdr)} columns)")
        else:
            print("  PASS  intake CSV header is the 57-column v6 (the 54 v3 columns in place + unretire_set + image_source + derived)")
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
        # part 7 of the STOP: the vendor's open cases (its own folder: the receive steps count `-cases-` files in t)
        oc = os.path.join(t, "open-cases")
        os.makedirs(oc)
        octen = os.path.join(oc, "tenant-cases.md")
        with open(fx("tenant-CLAUDE.md"), encoding="utf-8") as fh:
            fh_text = fh.read()
        with open(octen, "w", encoding="utf-8") as fh:
            fh.write(fh_text.replace("- Watermark: 500\n", "- Watermark: 500\n- Case store: EXAMPLE via ./case_write.ps1\n"))
        sargs = ["intake_cases.py", "stop", "--intake", v2, "--lines", lines, "--out-dir", oc]
        out = step("stop: no Case store pointer is a quiet INFO", sargs + ["--tenant", fx("tenant-CLAUDE.md")], 0)
        ok = "CASE_STORE_ABSENT" in out and not os.listdir(oc)[1:]
        print(f"  {'PASS' if ok else 'FAIL'}  no case store: INFO CASE_STORE_ABSENT, exit 0, nothing written")
        if not ok:
            bad.append("stop without a case store")
        out = step("stop: the case store with no read yet (CASES_UNREAD + ONE SELECT file)", sargs + ["--tenant", octen], 0)
        fp = out.split("(fingerprint ", 1)[1].split(")", 1)[0] if "(fingerprint " in out else ""
        osql = [n for n in os.listdir(oc) if n.endswith(".sql")]
        ok = "STOP CASES_UNREAD" in out and len(osql) == 1 and len(fp) == 12
        print(f"  {'PASS' if ok else 'FAIL'}  the unread store prints CASES_UNREAD and writes ONE read-only SELECT")
        if not ok:
            bad.append("stop unread")
        res = rows_json("open-cases-rows.json")
        res[0]["read_fp"] = fp
        rpath = os.path.join(oc, "rows.json")
        with open(rpath, "w", encoding="utf-8") as fh:
            json.dump(res, fh)
        out = step("stop --result: the vendor's open cases at the STOP", sargs + ["--tenant", octen, "--result", rpath], 0)
        ok = ("CASE_CREDIT_DUE          STOP  1" in out and "CASE_OPEN                INFO  1" in out
              and out.index("**Case 9 - CREDIT_DUE") < out.index("**Case 4 - SIZE_MISMATCH")
              and "stays OUT of package cost" in out and any(n.endswith(".md") for n in os.listdir(oc)))
        print(f"  {'PASS' if ok else 'FAIL'}  the STOP lists the CREDIT_DUE case first with its detail, then the other open case")
        if not ok:
            bad.append("stop open cases")
        res[0]["read_fp"] = "000000000000"
        with open(rpath, "w", encoding="utf-8") as fh:
            json.dump(res, fh)
        step("stop --result: another vendor's read (fingerprint) ABORTs", sargs + ["--tenant", octen, "--result", rpath], 2)
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
        # The Drive folder unfilled (a key only the pull procedure reads): every runner warns and runs; pull ABORTs.
        pt = os.path.join(t, "drive-ph")
        ten_ph = drive_ph_tenant(pt)
        pdo = os.path.join(pt, "out")
        os.makedirs(pdo)

        def drive_warns(name, cmd):
            out = step(f"{name} --tenant with the Drive folder a placeholder (WARNING, exit 0)", cmd, 0)
            if "WARNING: tenant contract" not in out or "Drive invoices folder" not in out:
                bad.append(f"{name} Drive warning")
                print(f"  FAIL  {name} must print a WARNING naming `Drive invoices folder` and run on")
        drive_warns("parse", ["intake_parse.py", "--pdf", pdf, "--text", fx("apex-invoice.md"), "--tenant", ten_ph])
        drive_warns("match", ["intake_match.py", "--lines", lines, "--active", fx("catalog-active.csv"), "--retired",
                              fx("catalog-retired.csv"), "--strains", fx("strains.csv"), "--tenant", ten_ph,
                              "--out-dir", pdo, "--slug", "example", "--drop-tag", DROP[0]])
        drive_warns("exceptions", ["intake_exceptions.py", "--intake", v1, "--lines", lines, "--po", fx("po.csv"),
                                   "--tenant", ten_ph, "--out-dir", pdo])
        drive_warns("notice", ["intake_notice.py", "--intake", v3, "--tenant", ten_ph, "--out-dir", pdo])
        drive_warns("msrp", ["intake_msrp.py", "--intake", v2, "--tenant", ten_ph, "--active", fx("catalog-active.csv"),
                             "--min-rows", "1", "--no-live", "--no-archive", "--out-dir", pdo])
        step("intake_pointers --tenant (the whole-contract check) stays strict on the Drive placeholder",
             ["intake_pointers.py", "--tenant", ten_ph], 2)
        for label, ten_, expect in (("a whole contract", fx("tenant-CLAUDE.md"), 0),
                                    ("the Drive folder a placeholder", ten_ph, 2)):
            rc, err = pull_gate(ten_)
            ok = rc == expect and (expect == 0 or "Drive invoices folder" in err)
            print(f"  {'PASS' if ok else 'FAIL'}  pull gate (--for pull) on {label} -> exit {rc} (expect {expect})"
                  + ("" if expect == 0 else ", naming `Drive invoices folder`"))
            if not ok:
                bad.append(f"pull gate {label}")
        step("receive with no mode (usage)", ["receive.py"], 2)
        rargs = ["receive.py", "--prep", "--lines", fx("receive-lines.csv"), "--catalog", fx("receive-catalog.csv"),
                 "--inventory", fx("receive-inventory.csv"), "--tenant", fx("tenant-CLAUDE.md"), "--out-dir", t,
                 "--slug", "rcv", "--asof", "2026-01-01"] + sum([["--item", f"{k}={v}"] for k, v in RC_ITEMS.items()], [])
        step("receive --prep (manifest ties; STOP questions only)", rargs + ["--manifest", fx("receive-manifest.csv")], 0)
        if not any(n.startswith("rcv-receipt-prep-2026-01-01-v1") and n.endswith("-questions.md") for n in os.listdir(t)):
            bad.append("receive questions file")
            print("  FAIL  receive --prep must write <slug>-receipt-prep-<date>-v1.csv and its -questions.md")
        badman = os.path.join(t, "manifest-short.csv")
        mrows = rows_of("receive-manifest.csv")
        mrows[2]["ship_cost"] = "480.00"
        C.write_csv(badman, list(mrows[0].keys()), mrows)
        step("receive --prep DEFECT (manifest ship $ does not tie)", rargs + ["--manifest", badman], 1)
        out = step("receive --prep wrong-size ship (STOP, exit 0)", rargs + ["--manifest", fx("receive-wrongsize-manifest.csv")], 0)
        ok = ("MANIFEST_ITEM_SIZE_MISMATCH" in out and "MANIFEST_QTY_MISMATCH" not in out
              and "Dutchie converts Metrc grams to units by the PICKED item's grams" in out)
        print(f"  {'PASS' if ok else 'FAIL'}  the wrong-size questions ask the vendor and warn of Dutchie's gram conversion")
        if not ok:
            bad.append("receive wrong-size questions")
        # the after-receipt branch: staff received the wrong-size package first -> ONE case, a SQL file + ONE command
        wsprep = max((n for n in os.listdir(t) if n.startswith("rcv-receipt-prep-2026-01-01-v") and n.endswith(".csv")),
                     key=lambda n: int(n.rsplit("-v", 1)[1][:-4]))
        cten = os.path.join(t, "tenant-cases.md")
        with open(fx("tenant-CLAUDE.md"), encoding="utf-8") as fh:
            ctext = fh.read().replace("- Watermark: 500\n", "- Watermark: 500\n- Case store: EXAMPLE via ./case_write.ps1\n")
        with open(cten, "w", encoding="utf-8") as fh:
            fh.write(ctext)
        cargs = ["intake_cases.py", "open", "--prep", os.path.join(t, wsprep), "--tenant", cten, "--out-dir", t]
        step("cases open: a thread with no subject ABORTs (the anchor note is the subject)",
             cargs + ["--received", "PKG-C", "--thread", "<a.b@mail.example.com>"], 2)
        out = step("cases open: the wrong-size package was received first (one case)",
                   cargs + ["--received", "PKG-C", "--thread", "<a.b@mail.example.com>", "--subject", "Re: Haze size"], 0)
        sqls = [n for n in os.listdir(t) if "-cases-" in n and n.endswith(".sql")]
        with open(os.path.join(t, sqls[0]) if sqls else os.devnull, encoding="utf-8") as fh:
            csql = fh.read()
        ok = ("OPEN SIZE_MISMATCH (MANIFEST_ITEM_SIZE_MISMATCH) package PKG-C" in out and len(sqls) == 1
              and "-Md5 " in out and "case_write.ps1" in out
              and "'GMAIL_THREAD', '<a.b@mail.example.com>', 'Haze size'" in csql)
        print(f"  {'PASS' if ok else 'FAIL'}  the received wrong-size package opens ONE SIZE_MISMATCH case + ONE command; "
              "the anchor thread note is the bare subject")
        if not ok:
            bad.append("cases open after receipt")
        out = step("cases open: the same STOP before the receipt (no case)", cargs + ["--received", "PKG-Z"], 0)
        ok = "no case" in out and "not received" in out and len([n for n in os.listdir(t) if n.endswith(".sql")]) == 1
        print(f"  {'PASS' if ok else 'FAIL'}  a STOP on a package not yet received stays a question in the run")
        if not ok:
            bad.append("cases quiet before receipt")
        step("cases open without a Case store pointer ABORTs", ["intake_cases.py", "open", "--prep", os.path.join(t, wsprep),
                                                              "--tenant", fx("tenant-CLAUDE.md"), "--received", "PKG-C"], 2)
        # the receipt's questions name the vendor's open cases (the `stop` read, reused); its own folder: the steps
        # above count `.sql` files in t
        rc_d = os.path.join(t, "receipt-cases")
        os.makedirs(rc_d)
        rcargs = [cten if a == fx("tenant-CLAUDE.md") else (rc_d if a == t else a) for a in rargs]
        rcargs += ["--manifest", fx("receive-manifest.csv")]
        out = step("receive --prep on a case store with no read yet (CASES_UNREAD + ONE SELECT file)", rcargs, 0)
        fp = out.split("(fingerprint ", 1)[1].split(")", 1)[0] if "(fingerprint " in out else ""
        rsql = [n for n in os.listdir(rc_d) if n.endswith(".sql")]
        ok = ("STOP CASES_UNREAD" in out and len(rsql) == 1 and rsql[0].startswith("rcv-receipt-prep-2026-01-01-v1-open-cases-")
              and len(fp) == 12 and "CASES_UNREAD: the vendor's open cases are not seen" in out)
        print(f"  {'PASS' if ok else 'FAIL'}  the unread store asks CASES_UNREAD beside the header credit and writes ONE SELECT")
        if not ok:
            bad.append("receive cases unread")
        res = rows_json("open-cases-rows.json")
        res[0]["read_fp"] = fp
        rrows = os.path.join(t, "receipt-case-rows.json")
        with open(rrows, "w", encoding="utf-8") as fh:
            json.dump(res, fh)
        step("receive --prep --cases: the vendor's open cases in the questions file", rcargs + ["--cases", rrows], 0)
        rq = max((n for n in os.listdir(rc_d) if n.endswith("-questions.md")), key=lambda n: int(n.split("-v")[-1].split("-")[0]))
        with open(os.path.join(rc_d, rq), encoding="utf-8") as fh:
            qtext = fh.read()
        ok = (rq.startswith("rcv-receipt-prep-2026-01-01-v2") and qtext.index("**Case 9 - CREDIT_DUE") < qtext.index("**Case 4 - ")
              and "stays OUT of package cost" in qtext and "Open CREDIT_DUE case 9 " in section(qtext, "Header credit (R126)")
              and "| CASE_CREDIT_DUE | STOP |" in qtext)
        print(f"  {'PASS' if ok else 'FAIL'}  the questions file lists the CREDIT_DUE case first and names it beside the header credit")
        if not ok:
            bad.append("receive cases questions")
        before = sorted(os.listdir(rc_d))
        res[0]["read_fp"] = "000000000000"
        with open(rrows, "w", encoding="utf-8") as fh:
            json.dump(res, fh)
        step("receive --prep --cases: another vendor's read (fingerprint) ABORTs", rcargs + ["--cases", rrows], 2)
        step("receive --prep --cases without a Case store pointer ABORTs",
             [fx("tenant-CLAUDE.md") if a == cten else a for a in rcargs] + ["--cases", rrows], 2)
        ok = sorted(os.listdir(rc_d)) == before
        print(f"  {'PASS' if ok else 'FAIL'}  a refused case read writes no sheet, no questions file and no SQL")
        if not ok:
            bad.append("receive cases refusal wrote a file")
        bgargs =["receive.py", "--prep", "--lines", fx("receive-buyget-lines.csv"), "--catalog", fx("receive-catalog.csv"),
                  "--inventory", fx("receive-inventory.csv"), "--manifest", fx("receive-buyget-manifest.csv"), "--tenant",
                  fx("tenant-CLAUDE.md"), "--out-dir", t, "--slug", "bg", "--asof", "2026-01-01", "--program", "2=deal"]
        bgargs += sum([["--item", f"{k}={v}"] for k, v in BGX["items"].items()], [])
        out = step("receive --prep R103 buy-4-get-1 (stated deal; no STOP)", bgargs, 0)
        bgcsv = os.path.join(t, "bg-receipt-prep-2026-01-01-v1.csv")
        with open(bgcsv, encoding="utf-8-sig", newline="") as fh:
            bgrw = {r["row"]: r for r in csv.DictReader(fh)}
        ok = (bg_blended(bgrw) and "remainder on BG-5 at $14.69" in out and "entered $734.90 = invoice $734.90" in out
              and "No STOP and no DEFECT" in out)
        print(f"  {'PASS' if ok else 'FAIL'}  the buy-get sheet enters 14.70 x4 + 14.69, ties 734.90 and prints the deal math")
        if not ok:
            bad.append("receive buy-get sheet")
        for label, phs, expect in (("an unrelated placeholder (WARNING, exit 0)", [DRIVE_PH], 0),
                                   ("a placeholder in the Vendor deal tag it reads (ABORT)", [DRIVE_PH, DEAL_PH], 2)):
            tdir = os.path.join(t, f"tenant-{expect}")
            os.makedirs(tdir)
            ten = os.path.join(tdir, "CLAUDE.md")
            text = BASE["tenant"]
            for a, b in phs:
                text = text.replace(a, b)
            with open(ten, "w", encoding="utf-8") as fh:
                fh.write(text)
            out = step(f"receive --prep tenant with {label}",
                       [a if a != fx("tenant-CLAUDE.md") else ten for a in rargs] + ["--manifest", fx("receive-manifest.csv")],
                       expect)
            if expect == 0 and "WARNING: tenant contract" not in out:
                bad.append("receive tenant warning")
                print("  FAIL  an unrelated tenant placeholder must print a WARNING line")
        step("receive --check stub", ["receive.py", "--check", "a.csv", "b.csv"], 2)
        pin = os.path.join(t, "plan-intake-v1.csv")
        shutil.copy(fx("plan-intake.csv"), pin)
        pargs = ["--intake", pin, "--active", fx("plan-pre-active.csv"), "--retired", fx("plan-pre-retired.csv"),
                 "--strains", fx("plan-strains.csv"), "--categories", fx("plan-categories.csv"), "--brands", fx("plan-brands.csv"),
                 "--catalog-search", fx("plan-catalog-search.csv"), "--catalog-state", "ST"]
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
        # R125: intake_apex_cost.py as a user runs it - the typed Apex read in, a NEW intake version out
        ad = os.path.join(t, "apex")
        os.makedirs(ad)
        arows = [dict(r, unit_cost="0.05") if k == 2 else r for k, r in enumerate(rows_of("plan-intake.csv"))]
        ain = os.path.join(ad, "plan-intake-v1.csv")
        C.write_csv(ain, list(arows[0].keys()), arows)
        aread = os.path.join(ad, "apex-read.csv")
        C.write_csv(aread, AC.APEX_COLS, [dict(APEX_PO, row="3", read_date="2026-10-11")])
        out = step("apex cost (R125: the PO read settles the sample-only line)",
                   ["intake_apex_cost.py", "--intake", ain, "--apex", aread], 0)
        v2 = os.path.join(ad, "plan-intake-v2.csv")
        r3 = rows_of_path(v2)[2] if os.path.isfile(v2) else {}
        if r3.get("lane_Cost") == "11.00" and "COST_FROM_APEX" in r3.get("flags", "") and "apex:po T-77" in out:
            print("  PASS  the Apex step wrote -v2 with Cost 11.00, COST_FROM_APEX, and printed the source")
        else:
            bad.append("apex cost CLI")
            print(f"  FAIL  the Apex step must write -v2 with Cost 11.00 + COST_FROM_APEX: {r3.get('lane_Cost')!r} {r3.get('flags')!r}")
        out = step("apex cost (R125: no read -> COST_UNKNOWN, still exit 0)", ["intake_apex_cost.py", "--intake", ain], 0)
        if "COST_UNKNOWN (STOP) 1" not in out:
            bad.append("apex cost unknown CLI")
            print("  FAIL  no Apex read must print COST_UNKNOWN (STOP) 1")
        else:
            print("  PASS  no Apex read prints COST_UNKNOWN (STOP) 1")
        for name, cmd in (("plan", ["intake_plan.py"] + pargs + ["--tenant", ten_ph]),
                          ("certify --plan", ["intake_certify.py"] + [a for a in cargs if a not in ("--out-dir", t)]
                           + ["--post-active", fx("plan-post-active.csv"), "--tenant", ten_ph])):
            drive_warns(name, cmd)
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
    print(f"\n2. fixture checks - each must pass clean AND fail on its breaker ({len(CHECKS) + len(RECEIVE_CHECKS) + len(POINTER_CHECKS)} checks)")
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
