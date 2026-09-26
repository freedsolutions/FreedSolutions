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
import intake_pointers as PTR  # noqa: E402
import receive as RC  # noqa: E402

SCRIPTS = ["intake_pointers.py", "intake_parse.py", "intake_match.py", "intake_exceptions.py",
           "intake_certify.py", "intake_notice.py", "receive.py"]
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
    return IM.match(c["lines"], c["active"], c["retired"], c["strains"], drop_tags=DROP)[0]


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
                Product="Acme Farms | Distillate AIO | Lime Sorbet | 2g | Pocket Pro", **{"Product grams": "2g"})
    extra = [item]
    if second:
        extra.append(dict(item, SKU="1007", ProductId="507", Product="Acme Farms | Distillate Cart | Lime Sorbet | 2g"))
    line = dict(BASE["lines"][0], line_no="7", description=desc, cases="1", units_total="24", case_cost="480.00",
                unit_cost="20.00", ext_cost="480.00", expiry_date="")
    return ctx(active=BASE["active"] + extra, lines=BASE["lines"] + [line])


def form_unread_exists(c):
    r = row_for(c, FU_BODY)
    return r["verdict"] == "EXISTS" and "FORM_UNREAD" in r["flags"].split(";") and r["copy_source_sku"] == "1006"


def form_named_stays_new_pl(c):
    r = row_for(c, FU_BODY)
    return r["verdict"] == "NEW_PL" and "FORM_UNREAD" not in r["flags"].split(";")


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


def gelato_is(c, **kv):
    r = row_for(c, "Acme Farms Gelato")
    return all(r.get(k) == v for k, v in kv.items())


# (name, predicate(ctx-or-arg) , clean arg, broken arg, what the breaker does)
CHECKS = [
    ("pointer contract complete", lambda t: PTR.validate(PTR.parse_text(t)) == [],
     BASE["tenant"], BASE["tenant"].replace("- Watermark: 500\n", ""), "delete the Watermark line"),
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
    ("NEW_ITEM_WITH_SIBLING fires once", lambda c: verdict_count(c, "NEW_ITEM_WITH_SIBLING") == 1,
     ctx(), ctx(strains={k: v for k, v in BASE["strains"].items() if k != "Gelato"}), "delete the Gelato strain record"),
    ("STRAIN_MISSING fires once", lambda c: verdict_count(c, "STRAIN_MISSING") == 1,
     ctx(), ctx(strains=dict(BASE["strains"], **{"Mystery Haze": {"type": "Sativa", "id": ""}})),
     "mint the Mystery Haze strain record"),
    ("NEW_PL fires once", lambda c: verdict_count(c, "NEW_PL") == 1,
     ctx(), ctx(active=BASE["active"] + [dict(BASE["active"][3], SKU="1005", ProductId="505", Brand="Acme Farms",
                                                  Product="Acme Farms | Live Resin Cart | Blue Dream | 0.5g",
                                                  Strain="Blue Dream")]),
     "add an Acme 0.5g cart lane"),
    ("NEW_BRAND fires once", lambda c: verdict_count(c, "NEW_BRAND") == 1,
     ctx(), ctx(active=BASE["active"] + [dict(BASE["active"][3], SKU="3001", ProductId="701", Brand="Cedar Co",
                                                  Product="Cedar Co | Gummy | Lime | 0.1g", **{"Product grams": "0.1g"})]),
     "add a Cedar Co item"),
    ("sibling = the lane member WITH an image", lambda c: row_for(c, "Acme Farms Gelato")["copy_source_sku"] == "1001",
     ctx(), mut(ctx(), "active", lambda r: r["SKU"] == "1001", **{"Image URL": ""}), "clear the imaged sibling's image"),
    ("a dead record (R81) is never the sibling", lambda c: row_for(c, "Acme Farms Gelato")["copy_source_sku"] != "1003",
     ctx(), mut(ctx(), "active", lambda r: r["SKU"] == "1003", Tags=""), "un-tag the dead record"),
    ("lane fields + final name inherited from the sibling",
     lambda c: gelato_is(c, create_name_FINAL="Acme Farms | Pre-Roll | Gelato | 1g", lane_Cost="4.5",
                         online_title="Gelato Pre-Roll 1g", tags="BI - Item QC"),
     ctx(), mut(ctx(), "active", lambda r: r["SKU"] == "1001", Cost="4.75"), "move the sibling's Cost"),
    ("row guard steps over a newer filtered one-off", row_guard_pick, 3, 1, "floor lowered to 1 row"),
    ("a missing column ABORTs (never read as blank)", aborts_on_missing_cost, True, False, "restore the column"),
    ("COST_DRIFT fires on line 3 (drift only) and line 4 (both)", lambda c: fired_on(c, "COST_DRIFT") == ["3", "4"],
     ctx(), lines_with(L3={"unit_cost": "4.50", "ext_cost": "450.00"}), "line 3 back to the lane Cost"),
    ("PROMO_UNDECIDED fires on line 2 (promo only) and line 4 (both)",
     lambda c: fired_on(c, "PROMO_UNDECIDED") == ["2", "4"],
     ctx(), mut(ctx(), "po", lambda r: r["po_line"] == "2", program="PKG - Promo"), "name a program on PO line 2"),
    ("line 4 carries BOTH flags with no discount printed (sealed R102: cost, not a discount line)",
     lambda c: "4" in fired_on(c, "COST_DRIFT") and "4" in fired_on(c, "PROMO_UNDECIDED"),
     ctx(), ctx(programs={"4": "margin"}), "rule a program for line 4 by --program"),
    ("control line 1 stays quiet on COST_DRIFT and PROMO_UNDECIDED",
     lambda c: "1" not in fired_on(c, "COST_DRIFT") + fired_on(c, "PROMO_UNDECIDED"),
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
     ctx(), mut(ctx(), "post", lambda r: r["SKU"] == "1004", Tags=""), "drop the item-QC tag from the new item"),
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
    ("FORM_UNREAD stays off a line that names a form word: NEW_PL holds", form_named_stays_new_pl,
     fu_ctx(FU_DESC.replace("Pocket PRO", "Cart")), fu_ctx(), "remove the form word from the line"),
    ("STOP message prints FORM_UNREAD on its verdict row", stop_prints_form_unread,
     fu_ctx(), fu_ctx(second=True), "add a second candidate (the row reads NEW_PL, flag absent)"),
    ("package_id rides parse -> lines -> intake row (tiered layout)", package_id_rides,
     tiered_lines(), tiered_lines(drop_pkg=True), "drop package_id from the lines (a pre-column lines CSV)"),
    ("receive --check join key is package_id, an intake CSV v3 column",
     lambda cols: RC.CHECK_JOIN_KEY == "package_id" and RC.CHECK_JOIN_KEY in cols,
     IM.V3_COLS, [c for c in IM.V3_COLS if c != "package_id"], "remove package_id from the v3 columns"),
]


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
                       fx("catalog-retired.csv"), "--strains", fx("strains.csv"), "--out-dir", t, "--slug", "example",
                       "--drop-tag", DROP[0]], 0)
        v1 = next(os.path.join(t, n) for n in os.listdir(t) if n.endswith("-v1.csv"))
        with open(v1, encoding="utf-8") as f:
            hdr = next(csv.reader(f))
        if hdr != IM.V3_COLS or len(hdr) != 54 or hdr[-2:] != ["parse_source", "package_id"]:
            bad.append("v3 header")
            print(f"  FAIL  intake CSV header is not the 54-column v3 ({len(hdr)} columns)")
        else:
            print("  PASS  intake CSV header is the 54-column v3 (45 v2 + 7 + parse_source + package_id)")
        with open(lines, encoding="utf-8") as f:
            lhdr = next(csv.reader(f))
        ok = lhdr == IP.OUT_COLS and "package_id" in lhdr
        print(f"  {'PASS' if ok else 'FAIL'}  lines CSV header carries package_id ({len(lhdr)} columns)")
        if not ok:
            bad.append("lines header package_id")
        srcs = {r["parse_source"] for r in C.read_csv(v1, IM.V3_COLS)[1]}
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
        _, rows = C.read_csv(v2, IM.V3_COLS)
        for r in rows:
            if r["verdict"] == "NEW_ITEM_WITH_SIBLING":
                r.update(approved="Y", new_sku="1004", new_productid="504")
        v3 = C.next_version(t, C.version_stem(v2)[1])
        C.write_csv(v3, IM.V3_COLS, rows)
        step("certify (RED on the one foreign cell)", ["intake_certify.py", "--pre", fx("catalog-active.csv"), "--post",
                                                       fx("certify-post.csv"), "--intake", v3], 1)
        step("notice", ["intake_notice.py", "--intake", v3, "--tenant", fx("tenant-CLAUDE.md")], 0)
        step("receive stub", ["receive.py"], 2)
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
