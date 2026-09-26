"""intake_notice.py - fill the tenant's new-items notice from the intake CSV; print the floor-sheet
command when the CSV carries a NEW_PL or NEW_BRAND row.

  python intake_notice.py --intake <intake-vN.csv> --tenant <CLAUDE.md> [--out-dir <dir>]
  (without --tenant: --template <notice.md> --operator "<name>" [--floor-sheet "<command>"])
  options: --item-qc-tag "<tag>"   the R83 tag the notice names (default `BI - Item QC`)
  python intake_notice.py --selftest

Created items = verdict NEW_ITEM_WITH_SIBLING with the new key read back (`new_sku`). The notice is
a DRAFT: the Operator adds recipients and sends; this script sends nothing. The floor sheet is the
tenant's own generator (`Floor sheet:` pointer); `<intake.csv>` in that command is replaced by the
intake path and the command is PRINTED, never run.

Flag table: NOT_READ_BACK  R101  DEFECT  an approved create row with no new_sku: a notice before the
read-back would announce an item nobody has seen (exit 1, nothing written).
"""
import os
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from intake_common import (DEFAULT_ITEM_QC_TAG, EXIT_ABORT, EXIT_DEFECT, EXIT_OK, Selftest, abort,  # noqa: E402
                           get_flag, new_path, read_csv, stamp, version_stem)
from intake_match import V3_COLS  # noqa: E402

NEW_LINE_VERDICTS = ("NEW_PL", "NEW_BRAND")


def fill(template, rows, operator, item_qc_tag=DEFAULT_ITEM_QC_TAG):
    """(text, created rows, new-line rows, defects)."""
    defects = [f"NOT_READ_BACK: {r.get('create_name_FINAL') or r.get('invoice_line')!r}" for r in rows
               if r.get("verdict") == "NEW_ITEM_WITH_SIBLING" and (r.get("approved") or "").upper() == "Y"
               and not (r.get("new_sku") or "").strip()]
    created = [r for r in rows if r.get("verdict") == "NEW_ITEM_WITH_SIBLING" and (r.get("new_sku") or "").strip()]
    newl = [r for r in rows if r.get("verdict") in NEW_LINE_VERDICTS]
    text = re.sub(r"<!--.*?-->\s*", "", template, flags=re.S)
    brands = sorted({r.get("lane_Brand") for r in created if r.get("lane_Brand")})
    first = (created or rows or [{}])[0]
    hand = []
    for r in created:
        nm = r.get("create_name_FINAL") or r.get("invoice_line")
        if "NO_ECOM_IMAGE" in (r.get("image_state") or ""):
            hand.append(f"- Product image: {nm} has no image. Please add one.")
        if not (r.get("online_title") or "").strip():
            hand.append(f"- Online title: {nm} has none yet.")
    out = []
    for ln in text.split("\n"):
        s = ln.strip()
        if s == "[[items]]":
            out += [f"- {r.get('create_name_FINAL')} - SKU {r.get('new_sku')}" for r in created]
        elif s == "[[needs-hand]]":
            out += hand or ["- Nothing."]
        elif s.startswith("[[new-line]]"):
            if newl:
                out.append(s[len("[[new-line]]"):].strip())
        else:
            out.append(ln)
    text = "\n".join(out)
    subs = {"<Brand>": " / ".join(brands) or "<Brand>", "<n>": str(len(created)),
            "<invoice number>": first.get("invoice_no") or "<invoice number>",
            "<invoice date>": first.get("invoice_date") or "<invoice date>", "<item QC tag>": item_qc_tag,
            "<Operator>": operator,
            "<new lines>": "; ".join(f"{r.get('lane_Brand') or ''} {r.get('invoice_line')}".strip() for r in newl)}
    for k, v in subs.items():
        text = text.replace(k, v)
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n", created, newl, defects


def main(argv):
    if "--selftest" in argv:
        return selftest()
    ip = get_flag(argv, "--intake")
    if not ip:
        print(__doc__)
        return EXIT_ABORT
    tenant = get_flag(argv, "--tenant")
    if tenant:
        import intake_pointers
        p = intake_pointers.load(tenant)["intake"]
        tpl, operator, floor = p["Notice template"], p["Operator"], p["Floor sheet"]
    else:
        tpl, operator, floor = get_flag(argv, "--template"), get_flag(argv, "--operator"), get_flag(argv, "--floor-sheet")
        if not (tpl and operator):
            abort("without --tenant pass --template and --operator")
    try:
        template = open(tpl, encoding="utf-8").read()
    except OSError:
        abort(f"notice template {tpl} unreadable")
    _, rows = read_csv(ip, V3_COLS, "--intake")
    text, created, newl, defects = fill(template, rows, operator, get_flag(argv, "--item-qc-tag", DEFAULT_ITEM_QC_TAG))
    if defects:
        print("DEFECT - no notice written:\n  " + "\n  ".join(defects))
        return EXIT_DEFECT
    if newl:
        cmd = (floor or "<no Floor sheet pointer>").replace("<intake.csv>", os.path.abspath(ip))
        print(f"NEW line(s) on this invoice: {len(newl)} - floor sheet command (review it, then run):\n  {cmd}\n")
    if not created:
        print("no created item carries a read-back SKU - no notice to draft")
        return EXIT_OK
    d_, stem = version_stem(ip)
    out = new_path(get_flag(argv, "--out-dir") or d_, f"{stem}-notice-{stamp()}", ".md")
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)
    left = sorted(set(re.findall(r"<[A-Za-z][^<>\n]{0,40}>", text)))
    print(text)
    print(f"wrote {out} ({len(created)} item(s))" + (f"; still for the Operator: {left}" if left else ""))
    return EXIT_OK


def selftest():
    t = Selftest("intake_notice")
    tpl = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates", "notice.md"),
               encoding="utf-8").read()
    rows = [{"verdict": "NEW_ITEM_WITH_SIBLING", "approved": "Y", "new_sku": "123", "create_name_FINAL": "A | P | W | 1g",
             "lane_Brand": "A", "invoice_no": "T-1", "invoice_date": "2026-09-20", "image_state": "0 images (NO_ECOM_IMAGE)",
             "online_title": "W 1g"},
            {"verdict": "EXISTS", "invoice_line": "A X preroll 1g"}]
    text, created, newl, d = fill(tpl, rows, "Pat Example")
    t.check("item line carries the SKU", "- A | P | W | 1g - SKU 123" in text)
    t.check("image gap listed", "Product image: A | P | W | 1g" in text)
    t.check("QUIET: new-line bullet dropped with no NEW_PL row", "New line:" not in text and not newl)
    t.check("no marker or comment survives", "[[" not in text and "<!--" not in text)
    t.check("operator and tag filled", "Questions to Pat Example" in text and DEFAULT_ITEM_QC_TAG in text)
    rows2 = rows + [{"verdict": "NEW_PL", "invoice_line": "A Haze cart 0.5g", "lane_Brand": "A"}]
    text2, _, newl2, _ = fill(tpl, rows2, "Pat Example")
    t.check("FIRES: new-line bullet kept with a NEW_PL row", "New line: A A Haze cart 0.5g" in text2 and len(newl2) == 1)
    bad = [dict(rows[0], new_sku="")]
    t.check("FIRES: NOT_READ_BACK on an approved row with no SKU", len(fill(tpl, bad, "x")[3]) == 1)
    return t.done()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
