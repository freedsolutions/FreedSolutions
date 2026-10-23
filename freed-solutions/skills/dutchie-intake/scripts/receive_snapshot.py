"""receive_snapshot.py - the receive-time Inventory snapshot, read from the Dutchie POS API (`receive` step 3).

  python receive_snapshot.py --tenant <CLAUDE.md> [--out-dir <dir>]
  python receive_snapshot.py --from-json <raw.json> [--out-dir <dir>]    re-derive the CSV from a frozen raw read
  python receive_snapshot.py --selftest

The default snapshot `receive.py --prep --inventory` reads (Operator 2026-10-23: "move to API reads"). ONE read-only
GET of `/reporting/inventory?includeRoomQuantities=true`, frozen as a dated record:
  `inventory-api-<YYYY-MM-DD>-<HHMMSS>.json`  the raw response, as returned
  `inventory-api-<YYYY-MM-DD>-<HHMMSS>.csv`   the derived snapshot, the Inventory export's shape: SKU, Room,
                                              Available, Cost (+ Package ID, ProductId for the record)
Both are new files (an existing name ABORTs; nothing is overwritten); the run prints the sha256 of each. Feed the
CSV to `receive.py --prep --inventory`. When the read fails (no key, HTTP error, a shape check below), nothing is
written and the run exits 2: freeze the Inventory export instead (the fallback, SKILL.md `receive` step 3).

Derivation, one row per package per room with stock:
  * SKU = the item's catalog `sku`; Room = `roomQuantities[].room`; Available = that room's `quantityAvailable`;
    Cost = the package `unitCost` (receipt line cost before the header credit; blank when the API has none).
  * A room with `quantityAvailable` <= 0 writes no row (the export lists rooms with stock only).
  * Shape checks (ABORT, nothing written): the response is not a list; a package with stock and no room split (the
    flag was dropped, or a new API shape); a room split whose sum differs from the package `quantityAvailable`; a
    package with stock and a blank `sku`. LIVE beats the spec: `/inventory` returns no rows on some keys, so the
    package feed is `/reporting/inventory`; a request with no `User-Agent` gets 403.
  * `productName` is the Online title, not the item Name, so it is not written; join on SKU / ProductId.

The key: the tenant pointer `POS key: <ENV VAR NAME>` (Intake Pointers) names the variable; the runner reads its
value from the environment, else from `~/.secrets/dutchie-pos.env` (one `NAME=value` per line), and an optional
integrator key from `<NAME>_INTEGRATOR`. HTTP Basic is built here (never the helper route that puts the key in a URL).
The key is never printed, written or put in a message. A missing key ABORTs naming the variable only.

Exit: 0 written, 2 ABORT (nothing written).
"""
import base64
import csv
import hashlib
import io
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from intake_common import EXIT_ABORT, EXIT_OK, Selftest, abort, get_flag  # noqa: E402

API_BASE = "https://api.pos.dutchie.com"
ENDPOINT = "/reporting/inventory"
PARAMS = {"includeRoomQuantities": "true"}
USER_AGENT = "dutchie-intake-receive-snapshot/1.0"   # required: no User-Agent = HTTP 403
SECRETS_FILE = os.path.join(os.path.expanduser("~"), ".secrets", "dutchie-pos.env")
POS_KEY = "POS key"                                  # the Intake Pointers line that names the variable
SNAP_COLS = ["SKU", "Room", "Available", "Cost", "Package ID", "ProductId"]
TOL = 1e-6


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _fmt(x):
    return "" if x is None else f"{x:g}"


def derive(items):
    """Pure. Raw `/reporting/inventory` rows (with room quantities) -> (snapshot rows, problems). Problems ABORT."""
    if not isinstance(items, list):
        return [], [f"the response is a {type(items).__name__}, not a list of packages"]
    rows, probs = [], []
    for it in items:
        pkg = it.get("packageId") or f"inventoryId {it.get('inventoryId')}"
        total = _num(it.get("quantityAvailable")) or 0.0
        rooms = it.get("roomQuantities") or []
        if total <= 0 and not rooms:
            continue
        if total > 0 and not rooms:
            probs.append(f"{pkg}: {total:g} available and no room split (roomQuantities empty)")
            continue
        split = sum(_num(r.get("quantityAvailable")) or 0.0 for r in rooms)
        if abs(split - total) > TOL:
            probs.append(f"{pkg}: room split sums to {split:g}, the package says {total:g}")
            continue
        sku = str(it.get("sku") or "").strip()
        if total > 0 and not sku:
            probs.append(f"{pkg}: {total:g} available and a blank sku")
            continue
        for r in rooms:
            q = _num(r.get("quantityAvailable")) or 0.0
            if q > 0:
                rows.append({"SKU": sku, "Room": r.get("room") or "", "Available": _fmt(q),
                             "Cost": _fmt(_num(it.get("unitCost"))), "Package ID": it.get("packageId") or "",
                             "ProductId": str(it.get("productId") or "")})
    rows.sort(key=lambda r: (r["SKU"], r["Package ID"], r["Room"]))
    return rows, probs


def csv_text(rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=SNAP_COLS, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


# ---------------------------------------------------------------- the key (never printed)
def read_key(name, environ=None, secrets_file=SECRETS_FILE):
    v = (os.environ if environ is None else environ).get(name, "").strip()
    if v:
        return v
    try:
        with open(secrets_file, encoding="utf-8") as f:
            for line in f:
                k, sep, val = line.strip().partition("=")
                if sep and not k.startswith("#") and k.strip() == name:
                    return val.strip().strip("'\"")
    except OSError:
        pass
    return ""


def auth_header(var, environ=None, secrets_file=SECRETS_FILE):
    loc = read_key(var, environ, secrets_file)
    if not loc:
        abort(f"no `{var}` in the environment or {secrets_file}; the Operator sets it (the lane never asks for its "
              "value). Freeze the Inventory export instead")
    integ = read_key(var + "_INTEGRATOR", environ, secrets_file)
    return "Basic " + base64.b64encode(f"{loc}:{integ}".encode("utf-8")).decode("ascii")


def fetch(var):
    """ONE read-only GET. Returns (raw text, parsed). Any failure ABORTs with the status and a body excerpt only."""
    url = API_BASE + ENDPOINT + "?" + urllib.parse.urlencode(PARAMS)
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", auth_header(var))
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", USER_AGENT)
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            raw = r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        abort(f"HTTP {e.code} on GET {ENDPOINT}: {e.read().decode('utf-8', 'replace')[:300]}. Freeze the Inventory "
              "export instead")
    except (urllib.error.URLError, OSError) as e:
        abort(f"GET {ENDPOINT} failed ({e.__class__.__name__}). Freeze the Inventory export instead")
    try:
        return raw, json.loads(raw)
    except ValueError:
        abort(f"GET {ENDPOINT} returned no JSON ({len(raw)} chars). Freeze the Inventory export instead")


def _write_new(path, text):
    with open(path, "x", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def run(argv):
    src, tenant, stamp = get_flag(argv, "--from-json"), get_flag(argv, "--tenant"), datetime.now()
    out_dir = get_flag(argv, "--out-dir")
    if src:
        with open(src, encoding="utf-8") as f:
            raw = f.read()
        parsed = json.loads(raw)
        stem = os.path.splitext(os.path.basename(src))[0]
        out_dir = out_dir or os.path.dirname(os.path.abspath(src))
    else:
        if not tenant:
            abort("give --tenant <CLAUDE.md> (its `POS key:` pointer names the key variable) or --from-json <raw.json>")
        import intake_pointers
        res = intake_pointers.load_for(tenant, [POS_KEY, "Exports dir"])
        out_dir = out_dir or res["intake"]["Exports dir"]
        stem = f"inventory-api-{stamp:%Y-%m-%d-%H%M%S}"
        raw, parsed = fetch(res["intake"][POS_KEY])
    rows, probs = derive(parsed)
    if probs:
        abort(f"the API read fails a shape check ({len(probs)}); nothing written. Freeze the Inventory export "
              "instead:\n  - " + "\n  - ".join(probs[:20]))
    os.makedirs(out_dir, exist_ok=True)
    csv_p = os.path.join(out_dir, stem + ".csv")
    json_p = None if src else os.path.join(out_dir, stem + ".json")
    for p in (csv_p, json_p):
        if p and os.path.exists(p):
            abort(f"{p} exists; a snapshot is never overwritten")
    if json_p:
        print(f"wrote {json_p} ({len(parsed)} package(s); sha256 {_write_new(json_p, raw)})")
    print(f"wrote {csv_p} ({len(rows)} row(s), {len({r['Package ID'] for r in rows})} package(s), "
          f"{len({r['SKU'] for r in rows})} SKU(s); sha256 {_write_new(csv_p, csv_text(rows))})")
    print(f"snapshot taken {stamp:%Y-%m-%d %H:%M:%S} local" if not src else f"re-derived from {src}")
    return EXIT_OK


# ---------------------------------------------------------------- selftest (synthetic; no tenant, vendor or brand)
def _pkg(pid, sku, total, cost, rooms):
    return {"packageId": pid, "inventoryId": 1, "productId": 7, "sku": sku, "quantityAvailable": total,
            "unitCost": cost, "productName": "Online Title", "roomQuantities":
            None if rooms is None else [{"roomId": i, "room": r, "quantityAvailable": q} for i, (r, q) in enumerate(rooms)]}


def selftest():
    import tempfile
    import receive
    t = Selftest("receive_snapshot")
    fx = [_pkg("P-MULTI", "9011", 8, 10.0, [("Order Fulfillment", 6), ("Vault", 2)]),
          _pkg("P-ZERO-ROOM", "9011", 3, 9.5, [("Order Fulfillment", 3), ("Quarantine", 0)]),
          _pkg("P-SOLD-OUT", "9012", 0, 5.0, []),
          _pkg("P-NO-COST", "9013", 1, None, [("Employee", 1)])]
    rows, probs = derive(fx)
    key = [(r["Package ID"], r["Room"], r["Available"], r["Cost"]) for r in rows]
    t.check("derive: no problem on the clean fixture", probs == [], str(probs))
    t.check("derive: a multi-room package writes one row per room",
            ("P-MULTI", "Order Fulfillment", "6", "10") in key and ("P-MULTI", "Vault", "2", "10") in key, str(key))
    t.check("derive: a room with zero available writes no row", not any(k[1] == "Quarantine" for k in key), str(key))
    t.check("derive: a sold-out package writes no row", not any(k[0] == "P-SOLD-OUT" for k in key), str(key))
    t.check("derive: a blank unitCost is a blank Cost cell", ("P-NO-COST", "Employee", "1", "") in key, str(key))
    t.check("derive: 4 rows, sorted by SKU / package / room", len(rows) == 4 and rows == sorted(
        rows, key=lambda r: (r["SKU"], r["Package ID"], r["Room"])), str(key))
    t.check("derive: the Online title (productName) is never written", "Online Title" not in csv_text(rows))
    # the CSV reads back through receive.py's own reader and on_hand() exactly as an Inventory export would
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "snap.csv")
        _write_new(p, csv_text(rows))
        _, inv = receive.read_csv(p, receive.INV_REQ, "inventory")
        t.check("on_hand: the multi-room SKU sums by room", receive.on_hand(inv, "9011") ==
                ("Order Fulfillment 9; Vault 2", "10;9.5"), str(receive.on_hand(inv, "9011")))
        t.check("on_hand: the sold-out SKU reads none on hand", receive.on_hand(inv, "9012") == ("none on hand", ""),
                str(receive.on_hand(inv, "9012")))
        t.check("on_hand: a blank Cost adds no cost", receive.on_hand(inv, "9013") == ("Employee 1", ""),
                str(receive.on_hand(inv, "9013")))
        t.check("write: an existing snapshot is never overwritten", _raises(lambda: _write_new(p, "x"), FileExistsError))
    # each shape check fires on its mutation and stays quiet on the control above
    for label, bad, needle in (
            ("stock and no room split", [_pkg("P1", "1", 2, 1.0, None)], "no room split"),
            ("a room split that does not sum", [_pkg("P2", "1", 5, 1.0, [("Vault", 2)])], "sums to 2"),
            ("stock and a blank sku", [_pkg("P3", "", 1, 1.0, [("Vault", 1)])], "blank sku")):
        _, pr = derive(bad)
        t.check(f"shape check: {label}", len(pr) == 1 and needle in pr[0], str(pr))
    t.check("shape check: a non-list response", derive({"Message": "x"})[1] != [])
    # the key: environment first, then the secrets file; never in a message
    with tempfile.TemporaryDirectory() as d:
        sf = os.path.join(d, "pos.env")
        with open(sf, "w", encoding="utf-8") as f:
            f.write("# comment\nTEST_POS_KEY=file-secret-value\nTEST_POS_KEY_INTEGRATOR='integ'\n")
        t.check("key: the environment beats the secrets file",
                read_key("TEST_POS_KEY", {"TEST_POS_KEY": "env-value"}, sf) == "env-value")
        t.check("key: the secrets file by name, quotes stripped",
                read_key("TEST_POS_KEY", {}, sf) == "file-secret-value" and read_key("TEST_POS_KEY_INTEGRATOR", {}, sf) == "integ")
        h = auth_header("TEST_POS_KEY", {}, sf)
        t.check("key: HTTP Basic is built client-side as key:integrator",
                base64.b64decode(h.split()[1]).decode() == "file-secret-value:integ")
        err = io.StringIO()
        old, sys.stderr = sys.stderr, err
        try:
            code = _exit_code(lambda: auth_header("ABSENT_POS_KEY", {}, sf))
        finally:
            sys.stderr = old
        t.check("key: a missing key ABORTs naming the variable only",
                code == EXIT_ABORT and "ABSENT_POS_KEY" in err.getvalue() and "file-secret-value" not in err.getvalue(),
                err.getvalue())
    t.check("request: the endpoint asks for room quantities", PARAMS.get("includeRoomQuantities") == "true")
    return t.done()


def _raises(f, exc):
    try:
        f()
    except exc:
        return True
    return False


def _exit_code(f):
    try:
        f()
    except SystemExit as e:
        return e.code
    return None


def main(argv):
    if "--selftest" in argv:
        return selftest()
    return run(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
