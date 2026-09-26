"""Apex Trading invoice layout (the text layer as `pdftotext -layout` or pypdf renders it).

The printed invoice is a table: Name | Details | Price | Quantity | Line. Per item:
  Name      the vendor's line description (may wrap)             -> description
  Details   `Batch:`, `(strain)`, `Potency: 33.7 % TAC`, `Container Type: Tubed`, optional
            `Exp:` / `Expiration Date:`, a COA link, and a line-level `Discount: -$x.xx`
  Price     the CASE cost when Quantity is in cases, the UNIT cost when it is in units
  Quantity  `1 Case` + `120 Units total` (or `12 Units`)
  Line      the extended cost
Below the table: Subtotal, then order-level Shipping / Discount / Credit rows, then Total.

The plugin reads both renderings: the layout text of a PDF text layer (details on the lines below
the Name) and a flattened markdown table from `--text` (details on the same line as the Name).

ASSUMPTION, stated rather than hidden: the one Apex invoice on hand when this plugin was written
has NO text layer (its glyphs are drawn, so both extractors return only the page footer). This
parser is written against the printed structure and proven on a synthetic text fixture; the first
Apex invoice that DOES carry a text layer must be run with `--dump-text` and this file corrected
before its output is trusted.
"""
import re

from . import iso_date, money, totals

NAME = "apex"

START = re.compile(r"^\s*(?P<left>\S.*?)\s{2,}(?:.*?\s{2,})?\$(?P<price>[\d,]+\.\d{2})\s+"
                   r"(?P<qty>\d+(?:\.\d+)?)\s+(?P<uom>Cases?|Units?)\b.*?\$(?P<line>[\d,]+\.\d{2})\s*$", re.I)
STOP = re.compile(r"^\s*(Subtotal|Sub-total|Total\b|Download All COAs|Make Checks Payable)", re.I)


def detect(text):
    return bool(re.search(r"\bINVOICE\b", text) and re.search(r"\bBatch:", text)
                and re.search(r"\bUnits?\b", text) and re.search(r"Container Type:|Potency:", text))


def _header(text):
    h = {"invoice_no": "", "invoice_date": "", "vendor": "", "po_ref": ""}
    m = re.search(r"INVOICE\s*#\s*([A-Za-z0-9_.\-/]+)", text)
    if m:
        h["invoice_no"] = m.group(1)
    m = re.search(r"\bDATE\s+([A-Z][a-z]{2,8}\.? \d{1,2}, \d{4})", text)
    if m:
        h["invoice_date"] = iso_date(m.group(1))
    m = re.search(r"\bPO\s*(?:#|No\.?|Number)\s*:?\s*([A-Za-z0-9_.\-/]+)", text)
    if m:
        h["po_ref"] = m.group(1)
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        if re.match(r"^\s*FROM\b", ln):
            for nxt in lines[i + 1:i + 4]:
                chunk = re.split(r"\s{2,}", nxt.strip())[0] if nxt.strip() else ""
                if chunk:
                    h["vendor"] = chunk
                    break
            break
    return h


def _block_fields(block, name_col_end, tail=""):
    """Details read from the start line's tail (a flattened markdown row carries them there) and
    from the lines below it (the layout rendering). Only the lines below can continue the Name."""
    f = {"potency": "", "container": "", "units": None, "expiry": "", "coa": "", "discount": 0.0, "cont": []}
    for n, ln in enumerate([tail] + list(block)):
        m = re.search(r"Potency:\s*([\d.]+)\s*%", ln)
        if m:
            f["potency"] = m.group(1)
        m = re.search(r"Container Type:\s*([A-Za-z][A-Za-z \-]*?)(?=\s{2,}|\s+[A-Z][A-Za-z ]*:|$)", ln)
        if m:
            f["container"] = m.group(1).strip()
        m = re.search(r"\b(\d+)\s+Units?\b", ln)
        if m and f["units"] is None:
            f["units"] = int(m.group(1))
        m = re.search(r"Exp(?:iration|iry)?(?:\s+Date)?:\s*([A-Za-z]{3,9}\.? \d{1,2}, \d{4}|\S+)", ln)
        if m:
            f["expiry"] = iso_date(m.group(1)) or m.group(1)
        m = re.search(r"(https?://\S+)", ln)
        if m and not f["coa"]:
            f["coa"] = m.group(1)
        m = re.search(r"Discount:\s*-?\s*\$([\d,]+\.\d{2})", ln)
        if m:
            f["discount"] += money(m.group(1))
        # A wrapped Name continues in the left column: text that starts inside the name column and
        # is not a Details key, a category line (`Prerolls · Whole Flower`) or a quantity word.
        left = ln[:name_col_end].strip() if n else ""
        if (left and ":" not in left and "·" not in left and "http" not in left
                and not re.search(r"\b(units?|total|grams|case)\b", left, re.I)):
            f["cont"].append(left)
    return f


def parse(text):
    h = _header(text)
    lines = text.replace("\r\n", "\n").split("\n")
    starts = [i for i, ln in enumerate(lines) if START.match(ln)]
    out = []
    end_items = len(lines)
    for n, i in enumerate(starts):
        m = START.match(lines[i])
        nxt = starts[n + 1] if n + 1 < len(starts) else len(lines)
        block = []
        for ln in lines[i + 1:nxt]:
            if STOP.match(ln):
                end_items = min(end_items, lines.index(ln, i))
                break
            block.append(ln)
        name_end = m.start("left") + len(m.group("left")) + 1
        f = _block_fields(block, name_end, lines[i][m.end("left"):])
        desc = " ".join([m.group("left").strip()] + f["cont"]).strip()
        price, qty, ext = money(m.group("price")), float(m.group("qty")), money(m.group("line"))
        is_case = m.group("uom").lower().startswith("case")
        if is_case:
            units = f["units"]
            if units is None:
                per = re.search(r"(\d+)\s*/\s*case", desc, re.I)
                units = int(per.group(1)) * qty if per else None
            cases = qty
            unit_cost = price * qty / units if units else None
        else:
            units, cases, unit_cost = qty, "", price
        line_no = len([r for r in out if not r["order_level_kind"]]) + 1
        out.append({"description": desc, "line_no": line_no, "cases": cases if cases != "" else "",
                    "units_total": units if units is not None else "", "case_cost": price if is_case else "",
                    "unit_cost": unit_cost if unit_cost is not None else "", "ext_cost": ext,
                    "potency_tac_pct": f["potency"], "container": f["container"], "coa_url": f["coa"],
                    "expiry_date": f["expiry"], "is_order_level": "N", "order_level_kind": "", "package_id": ""})
        if f["discount"]:
            out.append({"description": f"Line discount: {desc}", "line_no": line_no, "ext_cost": -f["discount"],
                        "is_order_level": "N", "order_level_kind": "discount"})
    tail = lines[end_items:] if starts else lines
    adj, subtotal, total = totals(tail)
    for k, a in enumerate(adj, 1):
        out.append({"description": a["label"], "line_no": 900 + k, "ext_cost": a["amount"],
                    "is_order_level": "Y", "order_level_kind": a["kind"]})
    h["subtotal"], h["total"] = subtotal, total
    return h, out
