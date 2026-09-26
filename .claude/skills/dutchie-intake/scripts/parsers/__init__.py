"""Invoice layout plugins for intake_parse.py.

A plugin is a module in this folder exposing:
  NAME             short layout id (`--layout <NAME>`)
  detect(text)     True when the text layer looks like this layout - by layout FEATURES (headings,
                   field labels), never by the vendor name
  parse(text)      (header, lines): header = {invoice_no, invoice_date, vendor, po_ref, total, subtotal};
                   lines = dicts on intake_parse.OUT_COLS (product lines, line-level adjustments,
                   order-level credit / shipping / discount rows); every product row carries
                   `package_id` (the printed package tag(s), `;`-joined; "" when the layout has none)

Add a vendor format = one new module + one entry in ORDER. `auto` takes the first detect() hit,
so put the most specific layout first and the generic table last.
"""
import re
from datetime import datetime

ORDER = ["apex", "fernway", "generic_table"]

MONTHS = "%b %d, %Y", "%B %d, %Y", "%b. %d, %Y"


def iso_date(s):
    s = (s or "").strip().rstrip(".")
    for fmt in MONTHS + ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d", "%m-%d-%Y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return ""


def money(s):
    return float(s.replace(",", "").replace("$", ""))


ADJ = re.compile(r"^\s*(?P<label>Subtotal|Sub-total|Shipping|Delivery|Freight|Discount|Credit|Total)\b"
                 r"(?P<mid>[^$\d\n-]*)(?P<neg>-)?\s*\$?\s*(?P<neg2>-)?(?P<amt>[\d,]+\.\d{2})\s*$", re.I)
KIND = {"shipping": "shipping", "delivery": "shipping", "freight": "shipping",
        "discount": "discount", "credit": "credit"}


def totals(lines_after):
    """Order-level adjustments + subtotal + total from the text below the item table.
    Signs are normalised: shipping positive, credit and discount negative."""
    adj, subtotal, total = [], None, None
    for ln in lines_after:
        m = ADJ.match(ln)
        if not m:
            continue
        label = m.group("label").lower()
        amt = money(m.group("amt"))
        if label in ("subtotal", "sub-total"):
            subtotal = amt
        elif label == "total":
            total = amt
        else:
            kind = KIND[label]
            signed = amt if kind == "shipping" else -amt
            adj.append({"kind": kind, "label": (m.group("label") + m.group("mid")).strip(), "amount": signed})
    return adj, subtotal, total
