"""Tier-priced wholesale invoice layout (layout id `fernway`): an ERP print with a BASE PRICE and a YOUR
PRICE per line, the gap between them shown as a per-line price-tier discount under a named Price Class.

The printed table, one item per block:
  NO. | ITEM | QTY. | UOM | BASE PRICE | YOUR PRICE | PRICE DISC. AMT | PRICE DISC. % | LINE DISC |
  DISCCODE | EXTPRICE
  - NO. is the vendor's own line number (not always in print order); it becomes `line_no`.
  - ITEM wraps over one to three text lines (`... | Cart |` then `1.0g | Hybrid`); a word split at a
    hyphen (`All-` / `In-One`) is joined without a space.
  - The Metrc package line comes AFTER the item text, as its own text line: `<package tag>  24.0 EA`.
    It can land on the next page, below a repeated page header. Its EA count is the unit count of
    the line; QTY x UOM `CASE` alone does not say how many units a case holds.
Below the table: Gross Total, Price Tier Disc Amount, Your Gross, Line Discount, Document Discount,
Credit Memo Total, Balance Due, Terms Discount.

Output (sign convention of intake_parse): the product row carries the BASE (list) price -
`case_cost` = BASE PRICE, `ext_cost` = QTY x BASE PRICE, `unit_cost` = ext / units. The price-tier
discount and any LINE DISC are LINE-level discount rows (`is_order_level` N, R103: they stay on their
line). Document Discount and Credit Memo Total, when non-zero, are ORDER-level rows. The header
`total` is Balance Due, so TOTAL_MISMATCH checks every base price and every discount read.
`package_id` (the line's package tags, `;`-joined) is an intake_parse column and rides into the
intake CSV. Extra keys on each product row (`units_per_case`, `your_price`, `disc_pct`, `price_class`)
are for callers that want them; intake_parse writes only its own columns.

Detected by layout features (the `Invoice Nbr.` label and the BASE / YOUR / EXT PRICE headings),
never by the vendor name.

Two text shapes are read: the column layout (`pdftotext -layout`, pypdf layout mode) and a flattened
rendering where the numbers follow the item text on one line (a connector or OCR read).
"""
import re
from datetime import datetime

from . import iso_date, money

NAME = "fernway"

AMT = r"\(?-?[\d,]+\.\d{2}\)?"
TAIL = (r"(?P<qty>\d+(?:\.\d+)?)\s+(?P<uom>CASE|CS|EA|EACH|UNIT|UNITS|BOX|PK)\s+(?P<base>[\d,]+\.\d{2})\s+"
        r"(?P<your>[\d,]+\.\d{2})\s+(?P<pdisc>" + AMT + r")\s+(?P<pct>-?[\d.]+)\s*%\s+(?P<ldisc>" + AMT + r")\s+"
        r"(?:(?P<code>[A-Z][A-Z0-9_-]*)\s+)?(?P<ext>[\d,]+\.\d{2})\s*$")
START = re.compile(r"^\s*(?P<no>\d{1,3})\s+(?P<item>\S.*?)\s+" + TAIL, re.I)
TAIL_ONLY = re.compile(r"^\s*" + TAIL, re.I)
PENDING = re.compile(r"^\s*(?P<no>\d{1,3})\s+(?P<item>\S.*\|.*)$")
PKG = re.compile(r"^\s*(?P<tag>1A[0-9A-Z]{22})\s+(?P<ea>\d+(?:\.\d+)?)\s*EA\b", re.I)
COLHEAD = re.compile(r"^\s*NO\.\s+ITEM\b", re.I)
END = re.compile(r"Gross Total|NOTE:", re.I)
PAGEHEAD = re.compile(r"^\s*(Invoice\b|Date:|Due Date:|Customer ID:|Currency:|BILL TO|SHIP TO)", re.I)
CONT_MAX_INDENT = 12


def detect(text):
    return bool(re.search(r"Invoice\s+Nbr\.", text) and re.search(r"BASE\s*PRICE", text)
                and re.search(r"\bYOUR\s*PRICE", text) and re.search(r"EXT\s*PRICE", text))


def _amt(s):
    return abs(money(s.replace("(", "").replace(")", ""))) if s else 0.0


def _date(s):
    s = (s or "").strip()
    for fmt in ("%d-%b-%Y", "%d-%B-%Y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return iso_date(s)


def _join(desc, frag):
    frag = " ".join(frag.split())
    if not desc:
        return frag
    if desc.endswith("-") and frag[:1].isalpha():
        return desc + frag
    return desc + " " + frag


def _header(text):
    h = {"invoice_no": "", "invoice_date": "", "vendor": "", "po_ref": "", "terms": "", "price_class": "",
         "due_date": ""}
    m = re.search(r"Invoice\s+Nbr\.\s*:?\s*([A-Za-z0-9_.\-/]+)", text)
    if m:
        h["invoice_no"] = m.group(1)
    m = re.search(r"(?m)^\s*Date:\s*(\S+)", text)
    if m:
        h["invoice_date"] = _date(m.group(1))
    m = re.search(r"Due Date:\s*(\S+)", text)
    if m:
        h["due_date"] = _date(m.group(1))
    head = re.split(r"BILL TO", text, maxsplit=1)[0]
    m = re.search(r"(?m)^\s{0,3}([A-Z][\w&.,' -]*?\s(?:LLC|L\.L\.C\.|Inc\.?|Corp\.?|Co\.|Ltd\.?))\s*$", head)
    if m:
        h["vendor"] = m.group(1).strip()
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        if re.search(r"\bTERMS\b", ln) and re.search(r"Price Class", ln):
            val = next((x for x in lines[i + 1:i + 3] if x.strip()), "")
            if re.search(r"\S\s{2,}\S", ln):
                cols = [(mm.start(), mm.group(0).strip()) for mm in re.finditer(r"\S+(?: \S+)*", ln)]
                for k, (start, label) in enumerate(cols):
                    end = cols[k + 1][0] if k + 1 < len(cols) else len(val)
                    cell = val[max(0, start - 2):end].strip()
                    if label.upper().startswith("TERMS"):
                        h["terms"] = cell
                    elif label.lower().startswith("price class"):
                        h["price_class"] = cell
                    elif label.upper().startswith("CUSTOMER REF"):
                        h["po_ref"] = cell
            else:
                m2 = re.match(r"\s*((?:Net\s+\d+\s+Days?)|(?:Due on receipt)|COD)\s*(\S*)", val, re.I)
                if m2:
                    h["terms"], h["price_class"] = m2.group(1), m2.group(2)
            break
    return h


def _totals(text):
    def grab(label):
        m = re.search(label + r"\s*:?\s*(" + AMT + r")", text)
        return _amt(m.group(1)) if m else None
    t = {"gross": grab(r"Gross Total"), "tier_disc": grab(r"Price Tier Disc Amount"), "your_gross": grab(r"Your Gross"),
         "line_disc": grab(r"Line Discount"), "doc_disc": grab(r"Document Discount"),
         "credit": grab(r"Credit Memo Total"), "terms_disc": grab(r"Terms Discount")}
    m = re.search(r"Balance Due:\s*([\d,]+\.\d{2})", text) or re.search(r"([\d,]+\.\d{2})\s*Balance Due:", text)
    t["balance_due"] = money(m.group(1)) if m else None
    return t


def parse(text):
    h = _header(text)
    lines = text.replace("\r\n", "\n").replace("\f", "\n").split("\n")
    first = next((i for i, ln in enumerate(lines) if COLHEAD.match(ln)), 0)
    last = next((i for i in range(first, len(lines)) if END.search(lines[i])), len(lines))
    items, cur, pending, cont_open = [], None, None, False
    for ln in lines[first:last]:
        if not ln.strip():
            cont_open = False
            continue
        m = START.match(ln)
        if m:
            cur = {"no": m.group("no"), "desc": _join("", m.group("item").strip()), "m": m, "pkgs": []}
            items.append(cur)
            pending, cont_open = None, True
            continue
        m = TAIL_ONLY.match(ln)
        if m and pending:
            cur = {"no": pending["no"], "desc": pending["desc"], "m": m, "pkgs": []}
            items.append(cur)
            pending, cont_open = None, True
            continue
        m = PKG.match(ln)
        if m:
            if cur is not None:
                cur["pkgs"].append((m.group("tag").upper(), float(m.group("ea"))))
            cont_open = False
            continue
        if COLHEAD.match(ln) or PAGEHEAD.match(ln):
            cont_open = False
            continue
        m = PENDING.match(ln)
        if m and not pending:
            pending, cont_open = {"no": m.group("no"), "desc": _join("", m.group("item").strip())}, False
            continue
        if pending:
            pending["desc"] = _join(pending["desc"], ln)
            continue
        indent = len(ln) - len(ln.lstrip())
        if cur is not None and cont_open and indent <= CONT_MAX_INDENT:
            cur["desc"] = _join(cur["desc"], ln)
        else:
            cont_open = False
    out = []
    for it in items:
        m = it["m"]
        qty, base = float(m.group("qty")), money(m.group("base"))
        uom = m.group("uom").upper()
        ea = sum(e for _, e in it["pkgs"])
        units = ea if ea else (qty if uom in ("EA", "EACH", "UNIT", "UNITS") else None)
        ext = round(qty * base, 2)
        line_no = int(it["no"])
        out.append({"description": it["desc"], "line_no": line_no, "cases": qty if units != qty or uom == "CASE" else "",
                    "units_total": units if units is not None else "", "case_cost": base if uom != "EA" else "",
                    "unit_cost": ext / units if units else "", "ext_cost": ext, "potency_tac_pct": "", "container": "",
                    "coa_url": "", "expiry_date": "", "is_order_level": "N", "order_level_kind": "",
                    "package_id": ";".join(t for t, _ in it["pkgs"]),
                    "units_per_case": (units / qty) if units and qty and uom != "EA" else "",
                    "your_price": money(m.group("your")), "disc_pct": m.group("pct"), "price_class": h["price_class"],
                    "printed_ext": money(m.group("ext"))})
        pd, ld = _amt(m.group("pdisc")), _amt(m.group("ldisc"))
        if pd:
            out.append({"description": f"Price tier discount {m.group('pct')}%"
                                       + (f" (Price Class {h['price_class']})" if h["price_class"] else "")
                                       + f": {it['desc']}", "line_no": line_no, "ext_cost": -pd,
                        "is_order_level": "N", "order_level_kind": "discount"})
        if ld:
            out.append({"description": f"Line discount: {it['desc']}", "line_no": line_no, "ext_cost": -ld,
                        "is_order_level": "N", "order_level_kind": "discount"})
    t = _totals("\n".join(lines[last:]) if last < len(lines) else text)
    k = 900
    for key, kind, label in (("doc_disc", "discount", "Document Discount"), ("credit", "credit", "Credit Memo Total")):
        if t.get(key):
            k += 1
            out.append({"description": label, "line_no": k, "ext_cost": -t[key], "is_order_level": "Y",
                        "order_level_kind": kind})
    h["subtotal"] = t["gross"]
    h["total"] = t["balance_due"]
    h["totals"] = t
    return h, out
