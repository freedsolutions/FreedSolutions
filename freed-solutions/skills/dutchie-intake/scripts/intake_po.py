"""intake_po.py - the Dutchie PO: the reconciled order (`po` step after certify; `po-close` step after the receipt).

  python intake_po.py write --tenant <CLAUDE.md> --intake <intake-vN.csv> --vendor-id <id> --title <text>
                            --arrival <YYYY-MM-DD> --doc-link <url> [--number <int>] [--status Open|Submitted]
                            [--item <row>=<ProductId>]... [--out-dir <dir>] [--live]
  python intake_po.py close --tenant <CLAUDE.md> --po <purchaseOrderId> --receipt <receiveInventoryHistoryId>
                            [--accept-diff] [--out-dir <dir>] [--live]
  python intake_po.py --selftest

The PO is NOT the order of record and NOT the receive-form source (Operator 2026-10-23: a gain for checking and
close-out, not for entry). Receive entry still keys from the prep sheet (`receive.py --prep`). The PO gives a machine
diff of the receipt and a closed record of the order.

`write` (after certify, before the receipt; it rides the one pre-create STOP ask). ONE `POST /purchase-order`:
  * one line per ProductId: the intake rows that resolve to it, summed. ProductId = `--item <row>=<id>` (row = the
    1-based intake row) > `new_productid` > `copy_source_productid` on EXISTS / RETIRED_MATCH (receive.py's order).
    A row with no id ABORTs: a PO line needs an existing item, so the PO waits for the create.
  * quantity = `units_total`; subtotal = `unit_cost` x `units_total` (the purchased cost, R50; the API has no unit
    cost); `unitId` 1 (Quantity) on every line: a line stored with no unit fails a later header write (HTTP 500).
  * header: the vendor's Dutchie record (`--vendor-id`), `--title` (the vendor's document number), expected arrival
    (`--arrival`), `status` (Open; Submitted only for the open receive-form test), an integer `purchaseOrderNumber`
    (default: the digits of the intake `invoice_no`; it need not be unique), and the document link in
    `shippingInformation` (the API has no document or notes field).
  * a new PO without `status` and an integer number is HTTP 400 (nothing is created).
  Guards before the write (STOP, exit 2, nothing written): a PO with the same title already exists (one PO per
  document; the guard reads every PO created in the last 120 days); `GET /vendor/vendors` finds no record for the id,
  or its name differs from the intake's `lane_Vendor`. Then GET by id: every planned field must read back exact.

`close` (after the receipt read-back). Reads the PO and the receipt, then diffs them BY PRODUCTID: quantity and $
(PO line subtotal vs the sum of the receipt's `totalCost` for that ProductId; a product split over packages sums).
  * STOP (exit 1, no write): any diff (a short, an over, a substitution, a $ difference) - the Operator rules, then
    `--accept-diff` closes with the diff on record; the PO is already Closed; the receipt's vendor differs from the
    PO's; the receipt links a DIFFERENT PO; a stored PO line with a unit other than 1 (the header write would 500).
  * ONE write (sparse header; the stored lines are kept): `status` Closed + `dateReceived` = the receipt's
    `deliveredOn` (the Date received). GET back: status and dateReceived exact; every other header field and every
    line unchanged.
  * The record prints `receipt_purchaseOrderId`: the receipt's own PO link. OPEN TEST (Operator 2026-10-23): on the
    next PO receipt, write the PO as Submitted and check whether the receive-form PO picker lists it and the receipt
    links to it (an Open PO does not list). A non-null link equal to `--po` answers it.

Records (`--out-dir`, default the intake CSV's folder for `write` and the current folder for `close`): every
response is saved as a new file `po-<key>-<YYYY-MM-DD-HHMMSS>-<call>.json` (an existing name ABORTs; nothing is
overwritten), plus `...-record.json` holding the plan, the diff and the read-back verdict. Without `--live` the run
reads (the guard, the vendor, the PO and the receipt) and prints the planned body; it writes nothing to Dutchie.

The key: the tenant pointer `POS key:` names the variable; `receive_snapshot.py` reads it (environment, then
`~/.secrets/dutchie-pos.env`) and builds HTTP Basic. The key is never printed, written or put in a message.

Exit: 0 written and read back exact (or a clean dry run), 1 a diff / read-back defect, 2 ABORT or guard STOP.
"""
import csv
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from intake_common import EXIT_ABORT, EXIT_DEFECT, EXIT_OK, Selftest, abort, get_all, get_flag  # noqa: E402
import receive_snapshot as RS  # noqa: E402

PO_PATH, RCPT_PATH, VENDOR_PATH = "/purchase-order", "/inventory/receivedinventory", "/vendor/vendors"
USER_AGENT = "dutchie-intake-po/1.0"     # required: no User-Agent = HTTP 403
STATUSES = ("Open", "Submitted")          # what `write` may create; Closed is the close step's alone
UNIT_QUANTITY = 1
GUARD_DAYS = 120
CENT = 0.005


# ---------------------------------------------------------------- pure: plan, read-back, diff
def _num(x):
    try:
        return float(str(x).replace("$", "").replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def resolve_pid(row, override=""):
    """(ProductId, source) for one intake row. Same order as receive.py; ('', '') = none."""
    if override:
        return override, "--item"
    if (row.get("new_productid") or "").strip():
        return row["new_productid"].strip(), "intake new_productid"
    if row.get("verdict") in ("EXISTS", "RETIRED_MATCH") and (row.get("copy_source_productid") or "").strip():
        return row["copy_source_productid"].strip(), f"intake {row['verdict']} match"
    return "", ""


def plan_lines(intake, items=None):
    """Intake rows -> (PO lines, problems). One line per ProductId; rows that share one are summed."""
    items, lines, probs, order = items or {}, {}, [], []
    for n, r in enumerate(intake, 1):
        label = f"row {n} {(r.get('invoice_line') or '')[:50]!r}"
        pid, _ = resolve_pid(r, items.get(n, ""))
        if not pid:
            probs.append(f"{label}: no Dutchie ProductId (verdict {r.get('verdict') or '?'}); the PO waits for the "
                         "create, or give --item <row>=<ProductId>")
            continue
        if not pid.isdigit():
            probs.append(f"{label}: ProductId {pid!r} is not an integer")
            continue
        q, c = _num(r.get("units_total")), _num(r.get("unit_cost"))
        if q is None or q <= 0 or q != int(q):
            probs.append(f"{label}: units_total {r.get('units_total')!r} is not a positive whole count")
            continue
        if c is None or c < 0:
            probs.append(f"{label}: unit_cost {r.get('unit_cost')!r} is not a cost")
            continue
        if pid not in lines:
            lines[pid] = {"productId": int(pid), "unitId": UNIT_QUANTITY, "quantity": 0, "subtotal": 0.0, "rows": []}
            order.append(pid)
        ln = lines[pid]
        ln["quantity"] += int(q)
        ln["subtotal"] = round(ln["subtotal"] + q * c, 2)
        ln["rows"].append(n)
    return [lines[p] for p in order], probs


def po_number(intake, given=None):
    if given is not None:
        if not str(given).isdigit():
            abort(f"--number {given!r} is not an integer")
        return int(given)
    nos = {re.sub(r"\D", "", r.get("invoice_no") or "") for r in intake} - {""}
    if len(nos) != 1:
        abort(f"the intake carries {len(nos)} invoice numbers {sorted(nos)}; give --number <int>")
    return int(nos.pop())


def ship_info(title, lines, link):
    units = sum(ln["quantity"] for ln in lines)
    total = sum(ln["subtotal"] for ln in lines)
    return f"{title} ({len(lines)} lines, {units} units, ${total:,.2f}). Document: {link}"


def build_body(title, vendor_id, arrival, status, number, info, lines):
    return {"purchaseOrders": [{
        "title": title, "vendorId": vendor_id, "expectedArrivalDate": f"{arrival}T00:00:00", "status": status,
        "purchaseOrderNumber": number, "shippingInformation": info,
        "purchaseOrderItems": [{k: ln[k] for k in ("productId", "unitId", "quantity", "subtotal")} for ln in lines]}]}


def readback_diffs(po, body):
    """Every planned field that did not read back exact. [] = exact."""
    want, bad = body["purchaseOrders"][0], []
    for k in ("title", "vendorId", "status", "purchaseOrderNumber", "shippingInformation"):
        if po.get(k) != want[k]:
            bad.append({"field": k, "want": want[k], "got": po.get(k)})
    if not str(po.get("expectedArrivalDate") or "").startswith(want["expectedArrivalDate"][:10]):
        bad.append({"field": "expectedArrivalDate", "want": want["expectedArrivalDate"][:10],
                    "got": po.get("expectedArrivalDate")})
    got = {}
    for i in po.get("purchaseOrderItems") or []:
        got.setdefault(i.get("productId"), []).append(i)
    if sum(len(v) for v in got.values()) != len(want["purchaseOrderItems"]):
        bad.append({"field": "line count", "want": len(want["purchaseOrderItems"]),
                    "got": sum(len(v) for v in got.values())})
    for w in want["purchaseOrderItems"]:
        g = got.get(w["productId"]) or []
        g0 = g[0] if len(g) == 1 else None
        if not g0 or g0.get("quantity") != w["quantity"] or g0.get("unitId") != UNIT_QUANTITY or \
                abs(float(g0.get("subtotal") or 0) - w["subtotal"]) > CENT:
            bad.append({"field": f"line {w['productId']}", "want": {k: w[k] for k in ("quantity", "subtotal", "unitId")},
                        "got": [{k: x.get(k) for k in ("quantity", "subtotal", "unitId")} for x in g]})
    return bad


def receipt_diff(po, receipt):
    """PO vs receipt by ProductId -> (summary, diffs). qty and $ are summed per ProductId on both sides."""
    po_l, rc_l = {}, {}
    for i in po.get("purchaseOrderItems") or []:
        q, t = po_l.get(i["productId"], (0.0, 0.0))
        po_l[i["productId"]] = (q + float(i.get("quantity") or 0), round(t + float(i.get("subtotal") or 0), 2))
    for i in receipt.get("items") or []:
        q, t = rc_l.get(i["productId"], (0.0, 0.0))
        rc_l[i["productId"]] = (q + float(i.get("quantity") or 0), round(t + float(i.get("totalCost") or 0), 2))
    diffs = []
    for p in sorted(set(po_l) | set(rc_l)):
        a, b = po_l.get(p), rc_l.get(p)
        if a is None or b is None or abs(a[0] - b[0]) > 1e-9 or abs(a[1] - b[1]) > CENT:
            kind = "not received" if b is None else "not on the PO" if a is None else \
                "qty and $" if abs(a[0] - b[0]) > 1e-9 and abs(a[1] - b[1]) > CENT else \
                "qty" if abs(a[0] - b[0]) > 1e-9 else "$"
            diffs.append({"productId": p, "kind": kind, "po": a and {"qty": a[0], "usd": a[1]},
                          "receipt": b and {"qty": b[0], "usd": b[1]}})
    summary = {"po_lines": len(po_l), "receipt_rows": len(receipt.get("items") or []), "receipt_products": len(rc_l),
               "matched": len(set(po_l) & set(rc_l)) - sum(1 for d in diffs if d["po"] and d["receipt"]),
               "po_total": round(sum(v[1] for v in po_l.values()), 2),
               "receipt_total": round(sum(v[1] for v in rc_l.values()), 2)}
    return summary, diffs


def close_stops(po, receipt, po_id, diffs, accept_diff):
    stops = []
    if po.get("status") == "Closed":
        stops.append("the PO is already Closed")
    if po.get("vendorId") != receipt.get("vendorId"):
        stops.append(f"vendor differs: PO {po.get('vendorId')} vs receipt {receipt.get('vendorId')}")
    link = receipt.get("purchaseOrderId")
    if link not in (None, po_id):
        stops.append(f"the receipt links a different PO ({link})")
    odd = [i.get("productId") for i in po.get("purchaseOrderItems") or [] if i.get("unitId") != UNIT_QUANTITY]
    if odd:
        stops.append(f"stored line(s) with unitId != {UNIT_QUANTITY} {odd}: a header write re-merges them and fails "
                     "(HTTP 500); fix the unit in Backoffice first")
    if diffs and not accept_diff:
        stops.append(f"{len(diffs)} line diff(s): the Operator rules, then --accept-diff closes with the diff on record")
    if not receipt.get("deliveredOn"):
        stops.append("the receipt has no deliveredOn (Date received)")
    return stops


def received_at(receipt):
    return str(receipt.get("deliveredOn") or "")[:19]


def close_body(po, when):
    return {"purchaseOrders": [{"purchaseOrderId": po["purchaseOrderId"], "purchaseOrderNumber": po["purchaseOrderNumber"],
                                "status": "Closed", "dateReceived": when}]}


def close_readback(pre, post, when):
    bad = []
    if post.get("status") != "Closed":
        bad.append({"field": "status", "want": "Closed", "got": post.get("status")})
    if not str(post.get("dateReceived") or "").startswith(when):
        bad.append({"field": "dateReceived", "want": when, "got": post.get("dateReceived")})
    for k in sorted((set(pre) | set(post)) - {"status", "dateReceived", "purchaseOrderItems"}):
        if pre.get(k) != post.get(k):
            bad.append({"field": k, "want": pre.get(k), "got": post.get(k)})
    key = lambda p: sorted((i.get("purchaseOrderItemId"), i.get("productId"), i.get("quantity"), i.get("subtotal"),
                            i.get("unitId")) for i in p.get("purchaseOrderItems") or [])
    if key(pre) != key(post):
        bad.append({"field": "purchaseOrderItems", "want": "unchanged", "got": "changed"})
    return bad


# ---------------------------------------------------------------- I/O (the key never leaves auth_header)
class Api:
    def __init__(self, var, out_dir, key, stamp):
        self.var, self.out_dir, self.key, self.stamp, self.saved = var, out_dir, key, stamp, []

    def call(self, method, path, tag, params=None, body=None):
        url = RS.API_BASE + path + ("?" + urllib.parse.urlencode(params) if params else "")
        req = urllib.request.Request(url, data=None if body is None else json.dumps(body).encode("utf-8"), method=method)
        req.add_header("Authorization", RS.auth_header(self.var))
        req.add_header("Accept", "application/json")
        req.add_header("User-Agent", USER_AGENT)
        if body is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                raw = r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")[:400]
            self.save(tag + "-error", {"http": e.code, "body": msg})
            raise ApiError(f"HTTP {e.code} on {method} {path}: {msg}")
        except (urllib.error.URLError, OSError) as e:
            raise ApiError(f"{method} {path} failed ({e.__class__.__name__})")
        parsed = json.loads(raw) if raw.strip() else None
        self.save(tag, parsed)
        return parsed

    def save(self, tag, obj):
        os.makedirs(self.out_dir, exist_ok=True)
        p = os.path.join(self.out_dir, f"po-{self.key}-{self.stamp:%Y-%m-%d-%H%M%S}-{tag}.json")
        with open(p, "x", encoding="utf-8", newline="\n") as f:
            json.dump(obj, f, indent=1, ensure_ascii=False)
        self.saved.append(p)
        return p


class ApiError(Exception):
    pass


def _rows(got):
    if isinstance(got, list):
        return got
    if isinstance(got, dict):
        return got.get("data") or got.get("purchaseOrders") or [got]
    return []


def get_po(api, po_id, tag):
    rows = [r for r in _rows(api.call("GET", PO_PATH, tag, {"PurchaseOrderId": po_id, "IncludeItemDetails": "true"}))
            if r and r.get("purchaseOrderId") == po_id]
    if len(rows) != 1:
        raise ApiError(f"GET PO {po_id}: {len(rows)} record(s)")
    return rows[0]


def same_title(api, title, stamp):
    # PageNumber is 0-BASED (live read 2026-10-23: page 1 of a one-page list is empty, so a 1-based start reads no PO
    # and the guard passes on a duplicate)
    since = (stamp - timedelta(days=GUARD_DAYS)).strftime("%Y-%m-%dT00:00:00Z")
    rows, page = [], 0
    while True:
        got = _rows(api.call("GET", PO_PATH, f"guard-p{page}", {"FromDateCreated": since, "IncludeItemDetails": "false",
                                                                "PageNumber": page, "PageSize": 200}))
        rows += got
        if len(got) < 200:
            break
        page += 1
    return [r.get("purchaseOrderId") for r in rows if (r.get("title") or "").strip() == title.strip()]


def _load_tenant(tenant):
    import intake_pointers
    return intake_pointers.load_for(tenant, [RS.POS_KEY])["intake"][RS.POS_KEY]


def _int_flag(argv, name, required=True):
    v = get_flag(argv, name)
    if v is None:
        if required:
            abort(f"give {name}")
        return None
    if not str(v).isdigit():
        abort(f"{name} {v!r} is not an integer")
    return int(v)


def run_write(argv):
    tenant, src = get_flag(argv, "--tenant"), get_flag(argv, "--intake")
    title, arrival, link = get_flag(argv, "--title"), get_flag(argv, "--arrival"), get_flag(argv, "--doc-link")
    status, live, stamp = get_flag(argv, "--status", "Open"), "--live" in argv, datetime.now()
    vendor_id = _int_flag(argv, "--vendor-id")
    for name, v in (("--tenant", tenant), ("--intake", src), ("--title", title), ("--arrival", arrival),
                    ("--doc-link", link)):
        if not v:
            abort(f"give {name}")
    if status not in STATUSES:
        abort(f"--status {status!r}: a new PO is {' or '.join(STATUSES)} (Closed is the close step's)")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", arrival):
        abort(f"--arrival {arrival!r} is not YYYY-MM-DD")
    items = {}
    for spec in get_all(argv, "--item"):
        n, _, pid = spec.partition("=")
        if not n.isdigit() or not pid.isdigit():
            abort(f"--item {spec!r}: give <row>=<ProductId>, both integers")
        items[int(n)] = pid
    with open(src, encoding="utf-8-sig", newline="") as f:
        intake = list(csv.DictReader(f))
    if not intake:
        abort(f"{src} holds no rows")
    lines, probs = plan_lines(intake, items)
    if probs:
        abort(f"{len(probs)} intake row(s) cannot be a PO line; nothing written:\n  - " + "\n  - ".join(probs))
    body = build_body(title, vendor_id, arrival, status, po_number(intake, get_flag(argv, "--number")),
                      ship_info(title, lines, link), lines)
    lane_vendors = {(r.get("lane_Vendor") or "").strip() for r in intake} - {""}
    out_dir = get_flag(argv, "--out-dir") or os.path.dirname(os.path.abspath(src))
    api = Api(_load_tenant(tenant), out_dir, re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-"), stamp)
    rec = {"step": "po write", "live": live, "intake": os.path.abspath(src), "body": body,
           "rows": {str(ln["productId"]): ln["rows"] for ln in lines}}
    try:
        dup = same_title(api, title, stamp)
        vend = [v for v in _rows(api.call("GET", VENDOR_PATH, "vendor", {"vendorId": vendor_id}))
                if v and v.get("vendorId") == vendor_id]
    except ApiError as e:
        abort(f"{e}; nothing written")
    stops = []
    if dup:
        stops.append(f"PO_EXISTS: PO(s) {dup} already carry the title {title!r}; one PO per document")
    if len(vend) != 1:
        stops.append(f"VENDOR: no single Dutchie vendor record {vendor_id} ({len(vend)} found)")
    elif lane_vendors and {(vend[0].get("vendorName") or "").strip()} != lane_vendors:
        stops.append(f"VENDOR: record {vendor_id} is {vend[0].get('vendorName')!r}; the intake's lane_Vendor is "
                     f"{sorted(lane_vendors)}")
    rec.update(guard_same_title=dup, vendor=vend[:1], stops=stops)
    if stops or not live:
        rec["verdict"] = "STOP" if stops else "DRY RUN"
        print(json.dumps({k: rec[k] for k in ("verdict", "stops", "body")}, indent=1))
        print(f"record {api.save('record', rec)}")
        return EXIT_ABORT if stops else EXIT_OK
    try:
        res = api.call("POST", PO_PATH, "create", body=body)
    except ApiError as e:
        # a POST that throws is done-unknown until a GET says: re-read the guard
        after = same_title(api, title, stamp)
        rec.update(verdict="CREATE_UNKNOWN", error=str(e), after_guard=after)
        print(f"record {api.save('record', rec)}")
        abort(f"{e}. PO(s) with this title after the error: {after or 'none'}")
    ids = (res or {}).get("createdPurchaseOrderIds") or []
    if len(ids) != 1:
        rec.update(verdict="CREATE_UNVERIFIED", response=res)
        print(f"record {api.save('record', rec)}")
        abort(f"the create returned {ids!r}, not one new id")
    po = get_po(api, ids[0], f"readback-{ids[0]}")
    bad = readback_diffs(po, body)
    rec.update(po_id=ids[0], readback_diffs=bad, verdict="EXACT" if not bad else "READBACK_DIFF")
    print(json.dumps({"po_id": ids[0], "purchaseOrderNumber": po.get("purchaseOrderNumber"), "status": po.get("status"),
                      "vendorName": po.get("vendorName"), "lines": len(lines),
                      "units": sum(ln["quantity"] for ln in lines),
                      "total": round(sum(ln["subtotal"] for ln in lines), 2), "readback_exact": not bad, "diffs": bad},
                     indent=1))
    print(f"record {api.save('record', rec)}")
    return EXIT_OK if not bad else EXIT_DEFECT


def run_close(argv):
    tenant, live, accept = get_flag(argv, "--tenant"), "--live" in argv, "--accept-diff" in argv
    po_id, rc_id, stamp = _int_flag(argv, "--po"), _int_flag(argv, "--receipt"), datetime.now()
    if not tenant:
        abort("give --tenant")
    api = Api(_load_tenant(tenant), get_flag(argv, "--out-dir") or os.getcwd(), str(po_id), stamp)
    try:
        pre = get_po(api, po_id, "pre-close")
        rcs = [r for r in _rows(api.call("GET", RCPT_PATH, f"receipt-{rc_id}", {"receiveInventoryHistoryId": rc_id}))
               if r and r.get("receiveInventoryHistoryId") == rc_id]
    except ApiError as e:
        abort(f"{e}; nothing written")
    if len(rcs) != 1:
        abort(f"receipt {rc_id}: {len(rcs)} record(s); nothing written")
    rc = rcs[0]
    summary, diffs = receipt_diff(pre, rc)
    stops, when = close_stops(pre, rc, po_id, diffs, accept), received_at(rc)
    rec = {"step": "po close", "live": live, "po_id": po_id, "receipt_id": rc_id, "po_status": pre.get("status"),
           "receipt_purchaseOrderId": rc.get("purchaseOrderId"), "dateReceived": when, **summary, "diffs": diffs,
           "accepted_diff": bool(diffs and accept), "stops": stops}
    if stops or not live:
        rec["verdict"] = "STOP" if stops else "DRY RUN"
        print(json.dumps(rec, indent=1))
        print(f"record {api.save('record', rec)}")
        return EXIT_DEFECT if stops else EXIT_OK
    body = close_body(pre, when)
    try:
        res = api.call("POST", PO_PATH, "close", body=body)
    except ApiError as e:
        rec.update(verdict="CLOSE_UNKNOWN", error=str(e))
        print(f"record {api.save('record', rec)}")
        abort(f"{e}; GET the PO before any retry (a failed header write can still land)")
    post = get_po(api, po_id, "post-close")
    bad = close_readback(pre, post, when)
    rec.update(response=res, readback_diffs=bad, verdict="EXACT" if not bad else "READBACK_DIFF")
    print(json.dumps(rec, indent=1))
    print(f"record {api.save('record', rec)}")
    return EXIT_OK if not bad else EXIT_DEFECT


# ---------------------------------------------------------------- selftest (synthetic; no tenant, vendor or brand)
def _row(line, pid="", verdict="EXISTS", new="", qty="10", cost="5.00", inv="INV-0042", vendor="Acme Supply"):
    return {"invoice_no": inv, "invoice_line": line, "units_total": qty, "unit_cost": cost, "verdict": verdict,
            "copy_source_productid": pid, "new_productid": new, "lane_Vendor": vendor}


def _po(lines, status="Open", vendor=900, unit=UNIT_QUANTITY):
    return {"purchaseOrderId": 77, "purchaseOrderNumber": 42, "title": "INV-0042", "status": status, "vendorId": vendor,
            "vendorName": "Acme Supply", "expectedArrivalDate": "2026-01-02T00:00:00.0000000", "dateReceived": None,
            "shippingInformation": "x", "itemCount": len(lines),
            "purchaseOrderItems": [{"purchaseOrderItemId": 500 + n, "productId": p, "quantity": q, "subtotal": s,
                                    "unitId": unit} for n, (p, q, s) in enumerate(lines)]}


def _rc(items, vendor=900, link=None, delivered="2026-01-02T13:33:00.0000000"):
    return {"receiveInventoryHistoryId": 5, "vendorId": vendor, "purchaseOrderId": link, "deliveredOn": delivered,
            "items": [{"productId": p, "quantity": q, "totalCost": t} for p, q, t in items]}


def selftest():
    import tempfile
    t = Selftest("intake_po")
    intake = [_row("Acme Gummies Lemon", "11"), _row("Acme Gummies Lemon (deal)", "11", qty="2", cost="0"),
              _row("Acme Vape Mint 1g", verdict="NEW_ITEM_WITH_SIBLING", new="21", qty="24", cost="12.50"),
              _row("Acme Flower 3.5g", "13", verdict="RETIRED_MATCH", qty="6", cost="18.333")]
    lines, probs = plan_lines(intake)
    by = {ln["productId"]: ln for ln in lines}
    t.check("plan: a clean intake has no problem", probs == [], str(probs))
    t.check("plan: rows sharing a ProductId sum into one line", by[11]["quantity"] == 12 and by[11]["subtotal"] == 50.0
            and by[11]["rows"] == [1, 2], str(by.get(11)))
    t.check("plan: a created row reads new_productid", by[21]["quantity"] == 24 and by[21]["subtotal"] == 300.0)
    t.check("plan: a RETIRED_MATCH row reads its source; subtotal rounds to cents", by[13]["subtotal"] == 110.0,
            str(by.get(13)))
    t.check("plan: every line carries unitId 1", all(ln["unitId"] == 1 for ln in lines))
    _, pr = plan_lines([_row("Acme New Thing", verdict="NEW_PL")])
    t.check("plan: a row with no ProductId is a problem (the PO waits for the create)",
            len(pr) == 1 and "no Dutchie ProductId" in pr[0], str(pr))
    l2, pr2 = plan_lines([_row("Acme New Thing", verdict="NEW_PL")], {1: "31"})
    t.check("plan: --item <row>=<id> beats the intake", pr2 == [] and l2[0]["productId"] == 31, str(pr2))
    for label, bad, needle in (("a fractional count", _row("x", "11", qty="2.5"), "positive whole count"),
                               ("a zero count", _row("x", "11", qty="0"), "positive whole count"),
                               ("a blank cost", _row("x", "11", cost=""), "not a cost"),
                               ("a non-integer id", _row("x", "A11"), "not an integer")):
        _, p = plan_lines([bad])
        t.check(f"plan: {label} is a problem", len(p) == 1 and needle in p[0], str(p))
    t.check("number: the invoice digits", po_number(intake) == 42)
    t.check("number: --number beats the invoice", po_number(intake, "7") == 7)
    t.check("number: two invoice numbers ABORT", _exit_code(lambda: po_number(intake + [_row("y", "1", inv="B-9")]))
            == EXIT_ABORT)
    info = ship_info("INV-0042", lines, "https://example.invalid/doc")
    t.check("shippingInformation: title, counts, total and the link",
            info == "INV-0042 (3 lines, 42 units, $460.00). Document: https://example.invalid/doc", info)
    body = build_body("INV-0042", 900, "2026-01-02", "Open", 42, info, lines)
    hdr = body["purchaseOrders"][0]
    t.check("body: a new PO carries status and an integer number", hdr["status"] == "Open" and hdr["purchaseOrderNumber"] == 42)
    t.check("body: no row bookkeeping is sent", all(set(i) == {"productId", "unitId", "quantity", "subtotal"}
                                                    for i in hdr["purchaseOrderItems"]))
    # read-back: exact on the echo, and each field fires on its own mutation
    echo = dict(hdr, purchaseOrderId=77, expectedArrivalDate="2026-01-02T00:00:00.0000000",
                purchaseOrderItems=[dict(i, purchaseOrderItemId=600 + n) for n, i in enumerate(hdr["purchaseOrderItems"])])
    t.check("readback: the echo is exact", readback_diffs(echo, body) == [], str(readback_diffs(echo, body)))
    for label, mut in (("title", lambda p: p.update(title="other")),
                       ("vendor", lambda p: p.update(vendorId=901)),
                       ("status", lambda p: p.update(status="Closed")),
                       ("arrival", lambda p: p.update(expectedArrivalDate="2026-01-03T00:00:00")),
                       ("shippingInformation", lambda p: p.update(shippingInformation="")),
                       ("a line's qty", lambda p: p["purchaseOrderItems"][0].update(quantity=1)),
                       ("a line's subtotal", lambda p: p["purchaseOrderItems"][0].update(subtotal=1.0)),
                       ("a line's unit", lambda p: p["purchaseOrderItems"][0].update(unitId=0)),
                       ("a missing line", lambda p: p["purchaseOrderItems"].pop()),
                       ("an extra line", lambda p: p["purchaseOrderItems"].append(dict(p["purchaseOrderItems"][0])))):
        m = json.loads(json.dumps(echo))
        mut(m)
        t.check(f"readback: {label} fires", readback_diffs(m, body) != [])
    # close: diff by ProductId, summed over packages
    po = _po([(11, 12, 50.0), (21, 24, 300.0)])
    s, d = receipt_diff(po, _rc([(11, 7, 29.17), (11, 5, 20.83), (21, 24, 300.0)]))
    t.check("close diff: a product split over packages sums and matches", d == [] and s["matched"] == 2
            and s["receipt_rows"] == 3 and s["po_total"] == s["receipt_total"] == 350.0, str((s, d)))
    for label, items, kind in (("a short", [(11, 12, 50.0), (21, 20, 250.0)], "qty and $"),
                               ("a $ difference", [(11, 12, 50.0), (21, 24, 288.0)], "$"),
                               ("a qty difference at the same $", [(11, 13, 50.0), (21, 24, 300.0)], "qty"),
                               ("a line not received", [(11, 12, 50.0)], "not received"),
                               ("a substitution", [(11, 12, 50.0), (21, 24, 300.0), (31, 1, 5.0)], "not on the PO")):
        _, d = receipt_diff(po, _rc(items))
        t.check(f"close diff: {label} fires as {kind!r}", len(d) == 1 and d[0]["kind"] == kind, str(d))
    rc = _rc([(11, 12, 50.0), (21, 24, 300.0)])
    t.check("close: a clean pair has no stop", close_stops(po, rc, 77, [], False) == [])
    for label, p, r, diffs, acc, needle in (
            ("a Closed PO", _po([(11, 12, 50.0)], status="Closed"), rc, [], False, "already Closed"),
            ("another vendor", po, _rc([], vendor=901), [], False, "vendor differs"),
            ("a receipt linked to another PO", po, _rc([], link=78), [], False, "different PO"),
            ("a stored line with no unit", _po([(11, 12, 50.0)], unit=0), rc, [], False, "unitId"),
            ("a diff without --accept-diff", po, rc, [{"productId": 1}], False, "line diff"),
            ("a receipt with no Date received", po, _rc([], delivered=None), [], False, "deliveredOn")):
        st = close_stops(p, r, 77, diffs, acc)
        t.check(f"close stop: {label}", len(st) == 1 and needle in st[0], str(st))
    t.check("close: --accept-diff clears the diff stop", close_stops(po, rc, 77, [{"productId": 1}], True) == [])
    t.check("close: a receipt linked to THIS PO is no stop", close_stops(po, _rc([], link=77), 77, [], False) == [])
    when = received_at(rc)
    cb = close_body(po, when)["purchaseOrders"][0]
    t.check("close body: sparse header, no lines, Closed + the Date received",
            cb == {"purchaseOrderId": 77, "purchaseOrderNumber": 42, "status": "Closed",
                   "dateReceived": "2026-01-02T13:33:00"}, str(cb))
    post = dict(json.loads(json.dumps(po)), status="Closed", dateReceived="2026-01-02T13:33:00.0000000")
    t.check("close readback: status + date moved, nothing else", close_readback(po, post, when) == [])
    for label, mut in (("status", lambda p: p.update(status="Open")),
                       ("dateReceived", lambda p: p.update(dateReceived=None)),
                       ("another header field", lambda p: p.update(title="other")),
                       ("a line", lambda p: p["purchaseOrderItems"][0].update(quantity=1))):
        m = json.loads(json.dumps(post))
        mut(m)
        t.check(f"close readback: {label} fires", close_readback(po, m, when) != [])
    # records: never overwritten; the key is never in a record
    with tempfile.TemporaryDirectory() as d:
        api = Api("UNUSED_VAR", d, "inv-0042", datetime(2026, 1, 2, 3, 4, 5))
        p = api.save("record", {"a": 1})
        t.check("record: named po-<key>-<stamp>-<call>.json",
                os.path.basename(p) == "po-inv-0042-2026-01-02-030405-record.json", p)
        t.check("record: an existing record is never overwritten", _raises(lambda: api.save("record", {}), FileExistsError))
    t.check("write: Closed is not a create status", "Closed" not in STATUSES)

    # the guard pages from 0 and reads every page (a fake list of 201 POs; page n holds rows n*200 ..)
    class Fake:
        def __init__(self, rows):
            self.rows, self.pages = rows, []

        def call(self, method, path, tag, params=None, body=None):
            n = params["PageNumber"]
            self.pages.append(n)
            return self.rows[n * params["PageSize"]:(n + 1) * params["PageSize"]]
    pos = [{"purchaseOrderId": i, "title": f"T{i}"} for i in range(201)]
    f = Fake(pos)
    t.check("guard: a title on the first page is found (PageNumber is 0-based)",
            same_title(f, "T5", datetime(2026, 1, 2)) == [5] and f.pages == [0, 1], str(f.pages))
    t.check("guard: a title on a later page is found", same_title(Fake(pos), " T200 ", datetime(2026, 1, 2)) == [200])
    t.check("guard: no match is an empty list", same_title(Fake(pos[:3]), "T9", datetime(2026, 1, 2)) == [])
    return t.done()


def _raises(f, exc):
    try:
        f()
    except exc:
        return True
    return False


def _exit_code(f):
    import io
    old, sys.stderr = sys.stderr, io.StringIO()
    try:
        f()
    except SystemExit as e:
        return e.code
    finally:
        sys.stderr = old
    return None


def main(argv):
    if "--selftest" in argv:
        return selftest()
    if argv[:1] == ["write"]:
        return run_write(argv[1:])
    if argv[:1] == ["close"]:
        return run_close(argv[1:])
    print(__doc__)
    return EXIT_ABORT


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
