"""intake_parse.py - invoice PDF -> invoice lines CSV (one row per product line, line-level
adjustment and order-level credit / shipping / discount line).

  python intake_parse.py [--pdf <invoice.pdf>] [--text <rendering.txt|.md>] [--lines <hand.csv>]
                         [--layout auto|apex|fernway|generic_table] [--vendor "<name>"] [--total <amount>]
                         [--tenant <CLAUDE.md> | --out-dir <dir>] [--dump-text]
  python intake_parse.py --selftest

Sources, tried IN THIS ORDER; the first that yields product lines wins and the rest are not read:
  1. pypdf        the PDF's own text layer (if pypdf is importable)
  2. pdftotext    `pdftotext -layout` on PATH
  3. --text       a plain-text or markdown rendering produced upstream - the Drive connector's
                  read of the R104-filed copy, or an OCR pass. Markdown tables are flattened to
                  columns and `**` / `#` markup is dropped, then the SAME layout parsers run on it.
  4. --lines      the hand-typed CSV (needs invoice_no, invoice_date, vendor, line_no, description,
                  units_total, unit_cost; ext_cost is computed when blank; adjustment rows carry
                  order_level_kind + ext_cost; package_id is optional)
A PDF whose glyphs are drawn has NO text layer: 1 and 2 return only page footers and the chain
moves on. Nothing left -> ABORT (exit 2); it never guesses from an empty page. Every output row
carries `parse_source` (`pypdf:<file>`, `pdftotext:<file>`, `text:<file>`, `lines:<file>`), which
intake_match copies into the intake CSV so a certify reader knows the provenance.

`package_id`: every layout plugin emits it on each product row - the package tag(s) the invoice
prints for the line, `;`-joined - and a layout that prints none emits it blank. intake_match carries
it into the intake CSV; it is the documented `receive.py --check` join key.

A layout is picked by its FEATURES (`detect()` on the text: column headings, field labels), never by
the vendor name; `--layout <id>` forces one.

Sign convention: product ext_cost positive; shipping positive; credit and discount NEGATIVE. A
line-level discount shares its product line's line_no and has is_order_level = N (R103: it stays
on its line); an order-level row has is_order_level = Y and is spread pro-rata downstream.

Flag table (lane contract: cite the rule; exit 1 only on DEFECT):
  TOTAL_MISMATCH  R103  DEFECT  sum of every row's ext_cost != the invoice Total (landed cost
                                cannot be computed from an unreconciled invoice)
  BAD_LINE        R103  DEFECT  a product line with no units or no unit cost
Output: a NEW `<vendor>-<invoice>-lines-<timestamp>.csv` in the tenant Intake dir (or --out-dir).
"""
import csv
import importlib
import os
import re
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from intake_common import (EXIT_ABORT, EXIT_DEFECT, EXIT_OK, Selftest, abort, get_flag, new_path,  # noqa: E402
                           num, read_csv, slug, stamp, write_csv)
import parsers  # noqa: E402

OUT_COLS = ["invoice_no", "invoice_date", "vendor", "line_no", "description", "cases", "units_total",
            "case_cost", "unit_cost", "ext_cost", "potency_tac_pct", "container", "coa_url", "expiry_date",
            "is_order_level", "order_level_kind", "po_ref", "package_id", "parse_source"]
HAND_REQUIRED = ["invoice_no", "invoice_date", "vendor", "line_no", "description", "units_total", "unit_cost"]
KINDS = {"", "credit", "shipping", "discount"}
FOOTER = re.compile(r"^\s*Page \d+ of \d+\s*$", re.I)


def meaningful(text):
    return "\n".join(ln for ln in (text or "").split("\n") if ln.strip() and not FOOTER.match(ln)).strip()


def extract_text(pdf):
    """(text, extractor, tried) - the first extractor returning more than page footers, else
    (None, None, tried). Never aborts: the caller moves on to --text, then --lines."""
    tried = []
    try:
        import pypdf  # noqa: F401
        from pypdf import PdfReader
        t = "\n".join((p.extract_text(extraction_mode="layout") or "") for p in PdfReader(pdf).pages)
        tried.append("pypdf")
        if meaningful(t):
            return t, "pypdf", tried
    except ImportError:
        tried.append("pypdf (not installed)")
    except Exception as e:  # a malformed PDF must not hide the other extractor
        tried.append(f"pypdf ({e.__class__.__name__})")
    exe = shutil.which("pdftotext")
    if exe:
        r = subprocess.run([exe, "-layout", pdf, "-"], capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        tried.append("pdftotext")
        if meaningful(r.stdout):
            return r.stdout, "pdftotext", tried
    else:
        tried.append("pdftotext (not on PATH)")
    return None, None, tried


MD_SEP = re.compile(r"^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?$")


def normalize_text(text):
    """A markdown rendering -> the column-separated shape the layout parsers read. Table rows become
    cells joined by four spaces, separator rows go, `**` / `__` emphasis and heading hashes go.
    Layout text passes through unchanged (its column spacing is load-bearing)."""
    out = []
    for ln in (text or "").replace("\r\n", "\n").split("\n"):
        s_ = ln.replace("**", "").replace("__", "")
        st = s_.strip()
        if st.startswith("|") and st.endswith("|") and len(st) > 1:
            if MD_SEP.match(st):
                continue
            cells = [c.strip().replace("\x00", "|") for c in st.replace("\\|", "\x00")[1:-1].split("|")]
            out.append("    ".join(c for c in cells if c))
            continue
        out.append(re.sub(r"^\s*#{1,6}\s+", "", s_))
    return "\n".join(out)


def pick_layout(text, layout):
    if layout and layout != "auto":
        if layout not in parsers.ORDER:
            abort(f"--layout {layout!r} unknown; known: {parsers.ORDER}")
        return importlib.import_module("parsers." + layout)
    for name in parsers.ORDER:
        mod = importlib.import_module("parsers." + name)
        if mod.detect(text):
            return mod
    raise ValueError(f"no layout plugin recognises this text (tried {parsers.ORDER})")


def finish(header, rows, vendor_override=None):
    """Stamp header fields onto every row, normalise signs and kinds, fill ext_cost."""
    for r in rows:
        for k in ("invoice_no", "invoice_date", "vendor", "po_ref"):
            if not r.get(k):
                r[k] = header.get(k, "")
        r["package_id"] = r.get("package_id") or ""
        if vendor_override:
            r["vendor"] = vendor_override
        kind = (r.get("order_level_kind") or "").strip().lower()
        if kind not in KINDS:
            abort(f"line {r.get('line_no')}: order_level_kind {kind!r} not in {sorted(KINDS - {''})}")
        r["order_level_kind"] = kind
        # blank on an adjustment row = order-level; a LINE discount must say N explicitly
        r["is_order_level"] = (r.get("is_order_level") or ("Y" if kind else "N")).strip().upper()[:1]
        ext = num(r.get("ext_cost"))
        if kind:
            if ext is None:
                abort(f"adjustment line {r.get('line_no')} ({kind}) has no ext_cost")
            r["ext_cost"] = abs(ext) if kind == "shipping" else -abs(ext)
        elif ext is None:
            u, c = num(r.get("units_total")), num(r.get("unit_cost"))
            r["ext_cost"] = round(u * c, 2) if u is not None and c is not None else ""
    return rows


def reconcile(rows, total):
    """[(flag, detail)] DEFECTs."""
    out = []
    for r in rows:
        if r["order_level_kind"]:
            continue
        u, c = num(r.get("units_total")), num(r.get("unit_cost"))
        if u is None or u <= 0 or c is None:
            out.append(("BAD_LINE", f"line {r['line_no']} {r['description'][:70]!r}: units {r.get('units_total')!r}, "
                                    f"unit cost {r.get('unit_cost')!r}"))
    if total is not None:
        s = sum(num(r.get("ext_cost")) or 0 for r in rows)
        if abs(s - total) >= 0.01:
            out.append(("TOTAL_MISMATCH", f"rows sum {s:.2f} != invoice Total {total:.2f} (gap {s - total:+.2f})"))
    return out


def fmt(rows):
    for r in rows:
        for k in ("unit_cost",):
            v = num(r.get(k))
            if v is not None:
                r[k] = f"{v:.4f}".rstrip("0").rstrip(".") if abs(v * 100 - round(v * 100)) > 1e-9 else f"{v:.2f}"
        for k in ("ext_cost", "case_cost"):
            v = num(r.get(k))
            if v is not None:
                r[k] = f"{v:.2f}"
        for k in ("units_total", "cases"):
            v = num(r.get(k))
            if v is not None:
                r[k] = f"{v:g}"
    return rows


def run_text(text, layout="auto", vendor=None):
    """(layout name, header, rows). Raises ValueError when no layout yields product lines."""
    text = normalize_text(text)
    if not meaningful(text):
        raise ValueError("the text holds nothing but page footers")
    mod = pick_layout(text, layout)
    header, rows = mod.parse(text)
    if not [r for r in rows if not r.get("order_level_kind")]:
        raise ValueError(f"layout {mod.NAME}: no product lines found (check --dump-text)")
    return mod.NAME, header, finish(header, rows, vendor)


def run_hand(path, vendor=None, total=None):
    _, rows = read_csv(path, HAND_REQUIRED, "--lines")
    return "hand", {"total": total}, finish({}, rows, vendor)


def run_chain(pdf=None, txt=None, hand=None, layout="auto", vendor=None, total=None):
    """pypdf -> pdftotext -> --text -> --lines. Returns (parse_source, layout, header, rows, skipped)."""
    skipped = []
    if pdf:
        text, ext, tried = extract_text(pdf)
        if text is None:
            skipped.append(f"{os.path.basename(pdf)}: no text layer (tried {', '.join(tried)})")
        else:
            try:
                name, h, rows = run_text(text, layout, vendor)
                return f"{ext}:{os.path.basename(pdf)}", name, h, rows, skipped
            except ValueError as e:
                skipped.append(f"{ext}: {e}")
    if txt:
        try:
            name, h, rows = run_text(open(txt, encoding="utf-8").read(), layout, vendor)
            return f"text:{os.path.basename(txt)}", name, h, rows, skipped
        except ValueError as e:
            skipped.append(f"--text {os.path.basename(txt)}: {e}")
    if hand:
        name, h, rows = run_hand(hand, vendor, total)
        return f"lines:{os.path.basename(hand)}", name, h, rows, skipped
    abort("no source yielded product lines (" + "; ".join(skipped) + "). Pass --text <a rendering of the "
          "filed copy> or hand-type --lines <csv> with columns " + str(HAND_REQUIRED) + ".")


def main(argv):
    if "--selftest" in argv:
        return selftest()
    vendor = get_flag(argv, "--vendor")
    layout = get_flag(argv, "--layout", "auto")
    pdf, txt, hand = get_flag(argv, "--pdf"), get_flag(argv, "--text"), get_flag(argv, "--lines")
    if not (pdf or txt or hand):
        print(__doc__)
        return EXIT_ABORT
    out_dir = get_flag(argv, "--out-dir")
    tenant = get_flag(argv, "--tenant")
    if not out_dir and tenant:
        import intake_pointers
        out_dir = intake_pointers.load(tenant)["intake"]["Intake dir"]
    src = pdf or txt or hand
    out_dir = out_dir or os.path.dirname(os.path.abspath(src))
    if "--dump-text" in argv:
        text = extract_text(pdf)[0] if pdf else None
        if text is None and txt:
            text = open(txt, encoding="utf-8").read()
        print(normalize_text(text) if text else "(no text layer and no --text)")
        return EXIT_OK
    source, name, header, rows, skipped = run_chain(pdf, txt, hand, layout, vendor, num(get_flag(argv, "--total")))
    for r in rows:
        r["parse_source"] = source
    for k in skipped:
        print(f"  source skipped - {k}")
    print(f"parse_source {source}")
    defects = reconcile(rows, header.get("total"))
    fmt(rows)
    inv = rows[0].get("invoice_no") or "invoice"
    out = new_path(out_dir, f"{slug(rows[0].get('vendor'))}-{slug(inv)}-lines-{stamp()}", ".csv")
    write_csv(out, OUT_COLS, rows)
    prod = [r for r in rows if not r["order_level_kind"]]
    print(f"layout {name} | invoice {inv} {rows[0].get('invoice_date')} | vendor {rows[0].get('vendor')!r}")
    tot = header.get("total")
    n_line = sum(1 for r in rows if r["order_level_kind"] and r["is_order_level"] == "N")
    n_order = sum(1 for r in rows if r["is_order_level"] == "Y")
    print(f"product lines {len(prod)} | line adjustments {n_line} | order-level {n_order}"
          f" | Total {'n/a (none read)' if tot is None else format(tot, '.2f')}")
    print(f"{'flag':16} {'rule':5} {'class':7} count")
    for flag in ("TOTAL_MISMATCH", "BAD_LINE"):
        n = sum(1 for f, _ in defects if f == flag)
        print(f"{flag:16} R103  DEFECT  {'n/a' if flag == 'TOTAL_MISMATCH' and header.get('total') is None else n}")
    for f, d in defects:
        print(f"   {f}: {d}")
    print(f"wrote {out}")
    return EXIT_DEFECT if defects else EXIT_OK


APEX_SAMPLE = """INVOICE                                   INVOICE # T-100    DATE Sep 20, 2026    STATUS Submitted
FROM                      CONTACT
Example Wholesale         Pat Example
Shipping: TBD
            Name                                  Details                     Price     Quantity     Line
Brand A Kush preroll 1g - 10/case            Batch: K-1                    $45.00     1 Case     $45.00
                                             Potency: 20.1 % TAC                      10 Units
                                             Container Type: Tubed                      total
                                             Exp: 2026-12-01
Brand A Haze cart 0.5g                       Batch: H-1                    $15.00     4 Units    $60.00
                                             Discount: -$6.00
Subtotal                                                                                $105.00
Shipping                                                                                  $5.00
Credit                                                                                   -$4.00
Total                                                                                   $100.00
"""

GENERIC_SAMPLE = """Invoice # G-7
Date: 09/21/2026
From: Example Supply
Description                      Qty        Unit Price      Amount
Widget gummies 100mg             10         6.00            60.00
Widget tincture 1000mg           2          25.00           50.00
Subtotal                                                   110.00
Total                                                      110.00
"""


def selftest():
    t = Selftest("intake_parse")
    name, h, rows = run_text(APEX_SAMPLE)
    prod = [r for r in rows if not r["order_level_kind"]]
    t.check("apex detected", name == "apex", name)
    t.check("apex: 2 product lines", len(prod) == 2, str(len(prod)))
    t.check("apex: case cost / units -> unit cost 4.50", abs(num(prod[0]["unit_cost"]) - 4.5) < 1e-9, str(prod[0]["unit_cost"]))
    t.check("apex: unit-priced line keeps its unit cost", abs(num(prod[1]["unit_cost"]) - 15) < 1e-9)
    t.check("apex: expiry read", prod[0]["expiry_date"] == "2026-12-01", prod[0]["expiry_date"])
    t.check("apex: header", h["invoice_no"] == "T-100" and h["invoice_date"] == "2026-09-20" and h["vendor"] == "Example Wholesale",
            str(h))
    ld = [r for r in rows if r["order_level_kind"] == "discount" and r["is_order_level"] == "N"]
    t.check("apex: line discount stays on its line, negative", len(ld) == 1 and ld[0]["line_no"] == 2 and ld[0]["ext_cost"] == -6.0,
            str(ld))
    ol = {r["order_level_kind"]: r["ext_cost"] for r in rows if r["is_order_level"] == "Y"}
    t.check("apex: every row carries package_id, blank (the layout prints none)",
            all(r.get("package_id") == "" for r in rows) and "package_id" in OUT_COLS, str([r.get("package_id") for r in rows]))
    t.check("apex: shipping +5, credit -4 (header 'Shipping: TBD' ignored)", ol == {"shipping": 5.0, "credit": -4.0}, str(ol))
    t.check("QUIET: TOTAL_MISMATCH on a reconciled invoice", reconcile(rows, h["total"]) == [])
    _, h2, rows2 = run_text(APEX_SAMPLE.replace("$100.00", "$101.00"))
    t.check("FIRES: TOTAL_MISMATCH when the Total disagrees", [f for f, _ in reconcile(rows2, h2["total"])] == ["TOTAL_MISMATCH"])
    bad = [dict(r) for r in rows]
    bad[0]["units_total"] = ""
    t.check("FIRES: BAD_LINE on a line with no units", any(f == "BAD_LINE" for f, _ in reconcile(bad, None)))
    name, hg, rg = run_text(GENERIC_SAMPLE)
    t.check("generic_table detected", name == "generic_table", name)
    t.check("generic: every row carries package_id, blank", all(r.get("package_id") == "" for r in rg))
    t.check("generic: 2 lines, vendor, date", len(rg) == 2 and hg["vendor"] == "Example Supply" and hg["invoice_date"] == "2026-09-21",
            f"{len(rg)} {hg}")
    t.check("no text layer is refused", meaningful("Page 1 of 2\nPage 2 of 2") == "")
    import tempfile
    d = tempfile.mkdtemp()
    try:
        pdf, txt = blank_pdf(os.path.join(d, "blank.pdf")), os.path.join(d, "render.md")
        md = ("**INVOICE #** T-100 **DATE** Sep 20, 2026\n**FROM**\nExample Wholesale\n\n"
              "| Name | Details | Price | Quantity | Line |\n|---|---|---|---|---|\n"
              "| Brand A Kush preroll 1g - 10/case | Batch: K-1 Potency: 20.1 % TAC Container Type: Tubed | "
              "$45.00 | 1 Case 10 Units total | $45.00 |\n\n| Total | $45.00 |\n")
        with open(txt, "w", encoding="utf-8") as f:
            f.write(md)
        src, name, h, rows, skipped = run_chain(pdf, txt)
        t.check("chain: a no-text PDF falls through to --text", src == "text:render.md" and len(skipped) == 1,
                f"{src} {skipped}")
        t.check("markdown rendering: details read from the same row",
                rows[0]["units_total"] == 10 and rows[0]["container"] == "Tubed" and rows[0]["potency_tac_pct"] == "20.1",
                str(rows[0]))
        t.check("QUIET: TOTAL_MISMATCH on the markdown rendering", reconcile(rows, h["total"]) == [])
        r = quiet_abort(run_chain, pdf, None)
        t.check("FIRES: no source left ABORTs", r == EXIT_ABORT, str(r))
    finally:
        shutil.rmtree(d, ignore_errors=True)
    tmp = _tmp_csv(["invoice_no", "vendor"], [["X", "V"]])
    try:
        with open(os.devnull, "w") as dn:
            old, sys.stderr = sys.stderr, dn
            try:
                run_hand(tmp)
            finally:
                sys.stderr = old
                os.remove(tmp)
        t.check("FIRES: hand CSV missing a column aborts", False, "no abort")
    except SystemExit as e:
        t.check("FIRES: hand CSV missing a column aborts", e.code == EXIT_ABORT, str(e.code))
    return t.done()


def quiet_abort(fn, *a):
    """Exit code of fn when it aborts (stderr silenced), else None."""
    old = sys.stderr
    with open(os.devnull, "w") as dn:
        sys.stderr = dn
        try:
            fn(*a)
            return None
        except SystemExit as e:
            return e.code
        finally:
            sys.stderr = old


def blank_pdf(path):
    """A valid one-page PDF with NO text layer - the shape of a drawn-glyph invoice, for the chain tests."""
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>"]
    out, offs = bytearray(b"%PDF-1.4\n"), []
    for n, o in enumerate(objs, 1):
        offs.append(len(out))
        out += b"%d 0 obj\n" % n + o + b"\nendobj\n"
    x = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offs)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, x)
    with open(path, "wb") as f:
        f.write(bytes(out))
    return path


def _tmp_csv(hdr, rows):
    import tempfile
    fd, p = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(hdr)
        w.writerows(rows)
    return p


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
