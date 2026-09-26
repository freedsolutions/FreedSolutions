"""Generic tabular invoice: a header row naming Description / Qty / Unit price / Amount, one item per
line below it, then Subtotal / Shipping / Discount / Credit / Total. The fallback for any vendor
whose PDF carries a text layer and a plain table. No potency, container, COA or expiry: those
columns stay blank and the operator fills what the STOP needs.
"""
import re

from . import iso_date, money, totals

NAME = "generic_table"

HEADER = re.compile(r"(description|item|product).*(qty|quantity|units).*(amount|total|ext)", re.I)
NUM = r"-?\$?[\d,]+(?:\.\d+)?"
ROW = re.compile(r"^\s*(?P<desc>\S.*?)\s{2,}(?P<qty>" + NUM + r")\s{2,}(?P<unit>" + NUM + r")\s{2,}(?P<amt>" + NUM + r")\s*$")
STOP = re.compile(r"^\s*(Subtotal|Sub-total|Total\b)", re.I)


def detect(text):
    return any(HEADER.search(ln) for ln in text.split("\n"))


def parse(text):
    lines = text.replace("\r\n", "\n").split("\n")
    h = {"invoice_no": "", "invoice_date": "", "vendor": "", "po_ref": ""}
    m = re.search(r"Invoice\s*(?:#|No\.?|Number)\s*[:#]?\s*([A-Za-z0-9_.\-/]+)", text, re.I)
    if m:
        h["invoice_no"] = m.group(1)
    m = re.search(r"\bDate\s*:?\s*([A-Za-z]{3,9}\.? \d{1,2}, \d{4}|\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2})", text)
    if m:
        h["invoice_date"] = iso_date(m.group(1))
    m = re.search(r"\bPO\s*(?:#|No\.?|Number)\s*:?\s*([A-Za-z0-9_.\-/]+)", text, re.I)
    if m:
        h["po_ref"] = m.group(1)
    for i, ln in enumerate(lines):
        if re.match(r"^\s*(From|Vendor|Sold by)\b\s*:?\s*$", ln, re.I):
            nxt = next((x.strip() for x in lines[i + 1:i + 4] if x.strip()), "")
            h["vendor"] = re.split(r"\s{2,}", nxt)[0]
            break
        m2 = re.match(r"^\s*(From|Vendor|Sold by)\s*:\s*(\S.*)$", ln, re.I)
        if m2:
            h["vendor"] = re.split(r"\s{2,}", m2.group(2).strip())[0]
            break
    hi = next((i for i, ln in enumerate(lines) if HEADER.search(ln)), None)
    out, end = [], len(lines)
    if hi is not None:
        for j in range(hi + 1, len(lines)):
            ln = lines[j]
            if STOP.match(ln):
                end = j
                break
            r = ROW.match(ln)
            if not r:
                continue
            qty, unit, amt = money(r.group("qty")), money(r.group("unit")), money(r.group("amt"))
            out.append({"description": r.group("desc").strip(), "line_no": len(out) + 1, "cases": "",
                        "units_total": qty, "case_cost": "", "unit_cost": unit, "ext_cost": amt,
                        "is_order_level": "N", "order_level_kind": "", "package_id": ""})
    adj, subtotal, total = totals(lines[end:])
    for k, a in enumerate(adj, 1):
        out.append({"description": a["label"], "line_no": 900 + k, "ext_cost": a["amount"],
                    "is_order_level": "Y", "order_level_kind": a["kind"]})
    h["subtotal"], h["total"] = subtotal, total
    return h, out
