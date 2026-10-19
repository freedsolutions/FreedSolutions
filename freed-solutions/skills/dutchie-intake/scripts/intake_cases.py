"""intake_cases.py - the AFTER-RECEIPT branch's case writes: an exception that leaves the run becomes a case in the
tenant's case store, and the lane logs each step as a case event (Operator ruling 2026-10-19).

  python intake_cases.py open --prep <receipt-prep.csv> (--received <package_id>... | --received-csv <csv>)
                              --tenant <CLAUDE.md> [--owner <name>] [--actor <name>] [--status <s>] [--party-key <k>]
                              [--receipt <id>] [--manifest-no <no>] [--apex-order <id>] [--gmail <id>]
                              [--title-prefix <text>] [--out-dir <dir>]
  python intake_cases.py sql --ops <ops.json> --tenant <CLAUDE.md> [--out-dir <dir>]
  python intake_cases.py --selftest

It reads files and writes NEW files only. It never connects to the warehouse, never sends mail and never opens a
browser. The write is the tenant's: the `Case store:` pointer names the warehouse org code and the ONE-command guided
runner (`<ORG_CODE> via <runner.ps1>`). The runner checks the SQL file's md5, logs in as the agent's writer role inside
its own process, runs the file as a DRY RUN (rolled back), and writes only after the Operator types the word.

`open` - which exceptions open a case (Operator ruling 2026-10-19). A package that staff RECEIVED (it is in the
receive history, the warehouse receipt lines or the Inventory export: `--received` / `--received-csv`) while its prep
row still carries a STOP or DEFECT flag opens ONE case per package: the before-receipt stop was missed, so the
question leaves the run. Size and qty mismatches, a manifest cost mismatch and every other open STOP count. INFO flags
never open a case. A STOP on a package that is NOT received stays a question in the run (the before-receipt branch).
The case type is the most specific flag on the package (SIZE > QTY > PRICE > OTHER, `CASE_TYPE`); the OPENED detail
lists every open code. Links: the package, the item the package sits on, plus `--receipt`, `--manifest-no`,
`--apex-order`. The SQL skips (a NOTICE, not an error) a package that already has an open case of the same code, so a
re-run never opens a twin. `CREDIT_DUE` opens by an `ops` file (a credit that is promised but not on an invoice or a
credit memo yet); it never holds a release - the credit can land on the next order or a credit memo.

`sql` - turns an ops JSON into ONE psql file that calls the store's writer procedures (`open_case`, `add_link`,
`add_event`, `rule_case`, `set_status`) in ONE transaction, then reads the touched cases back; `-v dry=1` rolls back.
Ops (a list under "ops"):
  {"op": "open", "case_type", "title", "actor", "status"?, "owner"?, "source_rule"?, "detail"?, "gmail"?, "at"?,
   "party_key"?, "links": [{"type", "ref", "note"?}]}
  {"op": "link", "case_id", "type", "ref", "note"?}
  {"op": "event", "case_id", "event" (NOTE VENDOR_ASKED VENDOR_REPLIED DUTCHIE_FIXED RELEASED), "actor", "detail"?,
   "gmail"?, "at"?}                                        VENDOR_REPLIED needs "gmail"
  {"op": "rule", "case_id", "ruling", "ruled_by", "gmail", "at"?}      no mail, no ruling
  {"op": "status", "case_id", "status", "actor", "detail"?, "gmail"?, "at"?}   RESOLVED / CANCELLED close it for good
The checks repeat the store's own (case type, status, link type, event, the Gmail id shape `<left@right>` or
`<mailbox>:<hex id>`), so a bad op is refused here before any login. Text never carries the `$cases$` quote tag.

Exit: 0 clean (no case to open is clean), 2 ABORT (refused input, usage). Nothing here is a DEFECT.
"""
import hashlib
import json
import os
import re
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from intake_common import EXIT_ABORT, EXIT_OK, Selftest, abort, get_all, get_flag, new_path, read_csv, stamp  # noqa: E402

CASE_TYPES = ("SIZE_MISMATCH", "QTY_MISMATCH", "PRICE_MISMATCH", "CREDIT_DUE", "MISSING_DOC", "OTHER")
OPEN_STATUSES = ("OPEN", "HOLD", "AWAITING_RULING", "AWAITING_VENDOR")
STATUSES = OPEN_STATUSES + ("RESOLVED", "CANCELLED")
LINK_TYPES = ("GMAIL_THREAD", "GMAIL_MESSAGE", "DRIVE_FILE", "DUTCHIE_RECEIPT", "DUTCHIE_PACKAGE", "DUTCHIE_ITEM",
              "APEX_ORDER", "METRC_MANIFEST")
ADD_EVENTS = ("NOTE", "VENDOR_ASKED", "VENDOR_REPLIED", "DUTCHIE_FIXED", "RELEASED")
GMAIL_ID = re.compile(r"^(<[^<>@\s]+@[^<>@\s]+>|[a-z0-9._%+-]+@[a-z0-9-]+(\.[a-z0-9-]+)+:[0-9a-f]{10,24})$")
RULE_CODE = re.compile(r"^[A-Z][A-Z0-9_]+$")
CASE_STORE = re.compile(r"^(?P<org>[A-Z][A-Z0-9_]*)\s+via\s+(?P<runner>\S.*\.ps1)$")
QUOTE_TAG = "$cases$"
DEFAULT_ACTOR = "dutchie-intake"
# the receive.py flag -> the case type it opens, most specific first (the first hit on a package names the case)
CASE_TYPE = [
    ("SIZE_MISMATCH", ("MANIFEST_ITEM_SIZE_MISMATCH",)),
    ("QTY_MISMATCH", ("MANIFEST_QTY_MISMATCH", "MANIFEST_QTY_UNREAD", "MANIFEST_GRAMS_UNSIZED", "MANIFEST_UOM_UNREAD",
                      "SAMPLE_MERGED")),
    ("PRICE_MISMATCH", ("MANIFEST_COST_MISMATCH", "PRICE_DROP_UNMARKED", "PENNY_UNMARKED", "CATALOG_COST_RAISE",
                        "COST_UNKNOWN", "BUY_GET_UNTIED", "LANDED_UNRECONCILED", "CREDIT_TRIPS_R62",
                        "CREDIT_BLEND_NEGATIVE")),
]
PREP_REQ = ["row", "line", "invoice_item", "dutchie_productid", "dutchie_name", "metrc_package_id", "metrc_item", "flags"]
RECEIVED_COLS = ("package_id", "Package ID", "PackageId", "Package Id", "metrc_package_id")


def flag_classes():
    import receive
    return {k: v[1] for k, v in receive.FLAGS.items()}


def case_store(tenant):
    """(org code, runner path) from the tenant's `Case store:` pointer; ABORT when it is absent or misshapen."""
    import intake_pointers
    res = intake_pointers.load_for(tenant, [], ["Case store", "Operator"])
    v = (res["intake"].get("Case store") or "").strip()
    m = CASE_STORE.match(v)
    if not m:
        abort("the tenant has no `Case store: <ORG_CODE> via <runner.ps1>` pointer under `## Intake Pointers`"
              + (f" (got {v!r})" if v else "") + "; the case write needs the org code and the guided runner")
    runner = m.group("runner")
    if not os.path.isabs(runner):
        runner = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(tenant)), runner))
    return m.group("org"), runner, res["intake"].get("Operator")


def received_set(argv):
    got = {p.strip() for p in get_all(argv, "--received") if p.strip()}
    path = get_flag(argv, "--received-csv")
    if path:
        hdr, rows = read_csv(path, [], "received")
        col = next((c for c in RECEIVED_COLS if c in hdr), None)
        if not col:
            abort(f"--received-csv {path}: no package id column (one of {list(RECEIVED_COLS)})")
        got |= {r[col].strip() for r in rows if r.get(col, "").strip()}
    return got


def proposals(prep_rows, received, classes, owner, actor, status="AWAITING_RULING", title_prefix="", party_key=None,
              receipt=None, manifest_no=None, apex_order=None, gmail=None):
    """(ops, notes): one `open` op per RECEIVED package whose prep row carries a STOP or DEFECT."""
    ops, notes, seen = [], [], set()
    for r in prep_rows:
        pkg = (r.get("metrc_package_id") or "").strip()
        codes = [f for f in (r.get("flags") or "").split(";") if f and classes.get(f) in ("STOP", "DEFECT")]
        if not pkg or not codes:
            continue
        if pkg not in received:
            notes.append(f"package {pkg} (row {r['row']}): {', '.join(codes)} - not received; it stays a question in "
                         "the run (before-receipt branch)")
            continue
        if pkg in seen:
            continue
        seen.add(pkg)
        ctype, src = "OTHER", codes[0]
        for t, members in CASE_TYPE:
            hit = next((c for c in codes if c in members), None)
            if hit:
                ctype, src = t, hit
                break
        item = (r.get("dutchie_name") or r.get("invoice_item") or "").strip()
        title = f"{title_prefix + ' ' if title_prefix else ''}line {r['line']} {item}: {src} after receipt".strip()
        links = [{"type": "DUTCHIE_PACKAGE", "ref": pkg, "note": f"Metrc item {r.get('metrc_item', '')!s}".strip()}]
        if (r.get("dutchie_productid") or "").strip():
            links.append({"type": "DUTCHIE_ITEM", "ref": r["dutchie_productid"].strip(),
                          "note": f"the item the package was received into: {item}"})
        for t, v in (("DUTCHIE_RECEIPT", receipt), ("METRC_MANIFEST", manifest_no), ("APEX_ORDER", apex_order)):
            if v:
                links.append({"type": t, "ref": v})
        op = {"op": "open", "case_type": ctype, "title": title, "actor": actor, "status": status, "owner": owner,
              "source_rule": src, "links": links,
              "detail": (f"Received before the prep questions were settled; open codes: {', '.join(codes)}. "
                         "Every Dutchie write on this package waits for the ruling (after-receipt branch).")}
        if party_key:
            op["party_key"] = party_key
        if gmail:
            op["gmail"] = gmail
        ops.append(op)
    stray = sorted(received - {(r.get("metrc_package_id") or "").strip() for r in prep_rows})
    for p in stray:
        notes.append(f"received package {p} is not on this prep sheet (another receipt?) - no case from it")
    return ops, notes


def _need(o, k, i):
    v = o.get(k)
    if v is None or (isinstance(v, str) and not v.strip()):
        raise ValueError(f"op {i} ({o.get('op')}): `{k}` is required")
    return v


def _gmail_ok(v, where):
    if v is not None and not GMAIL_ID.match(v):
        raise ValueError(f"{where}: Gmail id {v!r} is neither an RFC Message-ID `<left@right>` nor `<mailbox>:<hex id>` "
                         "(lower-case mailbox, 10-24 hex)")


def validate(ops):
    """Raise ValueError on the first op the store would refuse (or this file cannot quote safely)."""
    if not isinstance(ops, list) or not ops:
        raise ValueError("`ops` must be a non-empty list")
    for i, o in enumerate(ops, 1):
        if not isinstance(o, dict):
            raise ValueError(f"op {i} is not an object")
        for k, v in o.items():
            for s in (v if isinstance(v, list) else [v]):
                for t in (s.values() if isinstance(s, dict) else [s]):
                    if isinstance(t, str) and QUOTE_TAG in t:
                        raise ValueError(f"op {i}: `{k}` carries the quote tag {QUOTE_TAG}")
        kind = o.get("op")
        if kind == "open":
            if _need(o, "case_type", i) not in CASE_TYPES:
                raise ValueError(f"op {i}: case_type {o['case_type']!r} is not one of {list(CASE_TYPES)}")
            _need(o, "title", i), _need(o, "actor", i)
            if o.get("status", "OPEN") not in OPEN_STATUSES:
                raise ValueError(f"op {i}: a case opens as one of {list(OPEN_STATUSES)}, not {o.get('status')!r}")
            if o.get("source_rule") is not None and not RULE_CODE.match(o["source_rule"]):
                raise ValueError(f"op {i}: source_rule {o['source_rule']!r} is not an exception code")
            _gmail_ok(o.get("gmail"), f"op {i}")
            for j, ln in enumerate(o.get("links") or [], 1):
                _check_link(ln, f"op {i} link {j}")
        elif kind == "link":
            _case_id(o, i)
            _check_link({"type": o.get("type"), "ref": o.get("ref")}, f"op {i}")
        elif kind == "event":
            _case_id(o, i)
            ev = _need(o, "event", i)
            if ev not in ADD_EVENTS:
                raise ValueError(f"op {i}: event {ev!r} is not written by `event` (one of {list(ADD_EVENTS)}; RULED is "
                                 "`rule`, OPENED is `open`, CLOSED is `status`)")
            _need(o, "actor", i)
            if ev == "VENDOR_REPLIED" and not o.get("gmail"):
                raise ValueError(f"op {i}: VENDOR_REPLIED cites the vendor's mail (`gmail`)")
            _gmail_ok(o.get("gmail"), f"op {i}")
        elif kind == "rule":
            _case_id(o, i)
            _need(o, "ruling", i), _need(o, "ruled_by", i)
            if not o.get("gmail"):
                raise ValueError(f"op {i}: a ruling cites the mail that carries it (no mail, no ruling)")
            _gmail_ok(o["gmail"], f"op {i}")
        elif kind == "status":
            _case_id(o, i)
            if _need(o, "status", i) not in STATUSES:
                raise ValueError(f"op {i}: status {o['status']!r} is not one of {list(STATUSES)}")
            _need(o, "actor", i)
            _gmail_ok(o.get("gmail"), f"op {i}")
        else:
            raise ValueError(f"op {i}: op {kind!r} is not one of open, link, event, rule, status")


def _case_id(o, i):
    v = o.get("case_id")
    if isinstance(v, bool) or not isinstance(v, int) or v <= 0:
        raise ValueError(f"op {i}: case_id must be a positive whole number, got {v!r}")


def _check_link(ln, where):
    if ln.get("type") not in LINK_TYPES:
        raise ValueError(f"{where}: link type {ln.get('type')!r} is not one of {list(LINK_TYPES)}")
    ref = ln.get("ref")
    if not isinstance(ref, str) or not ref.strip() or ref != ref.strip():
        raise ValueError(f"{where}: link ref {ref!r} must be a trimmed, non-empty id")
    if ln["type"].startswith("GMAIL_"):
        _gmail_ok(ref, where)


def q(v):
    if v is None:
        return "null"
    return "'" + str(v).replace("'", "''") + "'"


def ts(v):
    return "null" if not v else f"timestamptz {q(v)}"


def render(ops, org_code, source=""):
    """The psql text: ONE transaction, the procedures only, a read-back, and `-v dry=1` -> rollback."""
    body = []
    for i, o in enumerate(ops, 1):
        k = o["op"]
        body.append(f"  -- op {i}: {k}")
        if k == "open":
            pkg = next((ln["ref"] for ln in o.get("links") or [] if ln["type"] == "DUTCHIE_PACKAGE"), None)
            ind = "  "
            if o.get("party_key"):
                body.append(f"  v_party := null;\n  select party_id into v_party from ref.vendor_party "
                            f"where org_id = v_org and party_key = {q(o['party_key'])};\n"
                            f"  if v_party is null then raise exception 'cases: no party % in org %', "
                            f"{q(o['party_key'])}, v_org; end if;")
            else:
                body.append("  v_party := null;")
            if pkg:
                body.append(
                    "  v_case := null;\n"
                    "  select c.case_id into v_case from cases.cases c join cases.case_links l\n"
                    "      on l.org_id = c.org_id and l.case_id = c.case_id\n"
                    "   where c.org_id = v_org and c.status not in ('RESOLVED', 'CANCELLED')\n"
                    f"     and l.link_type = 'DUTCHIE_PACKAGE' and l.ref = {q(pkg)}\n"
                    f"     and c.source_rule is not distinct from {q(o.get('source_rule'))} limit 1;\n"
                    "  if v_case is not null then\n"
                    f"    raise notice 'cases: op {i} skipped: case % is already open on package %', v_case, {q(pkg)};\n"
                    "  else")
                ind = "    "
            body.append(
                f"{ind}v_case := null;\n"
                f"{ind}call cases.open_case(p_org_id => v_org, p_case_type => {q(o['case_type'])}, "
                f"p_title => {q(o['title'])}, p_actor => {q(o['actor'])}, p_party_id => v_party, "
                f"p_source_rule => {q(o.get('source_rule'))}, p_owner => {q(o.get('owner'))}, "
                f"p_status => {q(o.get('status', 'OPEN'))}, p_opened_at => {ts(o.get('at'))}, "
                f"p_detail => {q(o.get('detail'))}, p_gmail_message_id => {q(o.get('gmail'))}, p_case_id => v_case);")
            for ln in o.get("links") or []:
                body.append(f"{ind}call cases.add_link(v_org, v_case, {q(ln['type'])}, {q(ln['ref'])}, "
                            f"{q(ln.get('note'))}, v_x);")
            body.append(f"{ind}perform set_config('cases.touched', coalesce(current_setting('cases.touched', true), '') "
                        f"|| v_case || ',', true);\n{ind}raise notice 'cases: op {i} opened case %', v_case;")
            if pkg:
                body.append("  end if;")
            continue
        cid = int(o["case_id"])
        if k == "link":
            body.append(f"  call cases.add_link(v_org, {cid}, {q(o['type'])}, {q(o['ref'])}, {q(o.get('note'))}, v_x);")
        elif k == "event":
            body.append(f"  call cases.add_event(v_org, {cid}, {q(o['event'])}, {q(o['actor'])}, {q(o.get('detail'))}, "
                        f"{q(o.get('gmail'))}, {ts(o.get('at'))}, v_x);")
        elif k == "rule":
            body.append(f"  call cases.rule_case(v_org, {cid}, {q(o['ruling'])}, {q(o['ruled_by'])}, {q(o['gmail'])}, "
                        f"{ts(o.get('at'))}, v_x);")
        elif k == "status":
            body.append(f"  call cases.set_status(v_org, {cid}, {q(o['status'])}, {q(o['actor'])}, {q(o.get('detail'))}, "
                        f"{q(o.get('gmail'))}, {ts(o.get('at'))}, v_x);")
        body.append(f"  perform set_config('cases.touched', coalesce(current_setting('cases.touched', true), '') "
                    f"|| '{cid},', true);\n  raise notice 'cases: op {i} {k} on case {cid}';")
    head = [
        f"-- Case writes (dutchie-intake `intake_cases.py`){' from ' + source if source else ''}.",
        "-- Run ONLY through the tenant's guided case-write runner (md5 check, dry run, a typed word).",
        "--   psql <writer url> -X -P pager=off -v ON_ERROR_STOP=1 -v dry=1 -f <this file>   # rolls back",
        f"-- {len(ops)} op(s): " + ", ".join(o["op"] for o in ops),
        "",
        "\\set ON_ERROR_STOP on",
        "\\encoding UTF8",
        "begin;",
        "",
        f"do {QUOTE_TAG}",
        "declare",
        "  v_org   bigint;",
        "  v_party bigint;",
        "  v_case  bigint;",
        "  v_x     bigint;",
        "begin",
        f"  select org_id into v_org from security.organizations where org_code = {q(org_code)};",
        f"  if v_org is null then raise exception 'cases: no org %', {q(org_code)}; end if;",
    ]
    tail = [
        "end",
        f"{QUOTE_TAG};",
        "",
        "-- Read-back: every case this file touched.",
        "select c.case_id, c.status, c.owner, c.case_type, c.source_rule, c.ruling,",
        "       (select count(*) from cases.case_events e where e.org_id = c.org_id and e.case_id = c.case_id) as events,",
        "       (select count(*) from cases.case_links l where l.org_id = c.org_id and l.case_id = c.case_id) as links,",
        "       (select e.event || ' ' || e.actor from cases.case_events e where e.org_id = c.org_id and e.case_id = c.case_id",
        "         order by e.at desc, e.event_id desc limit 1) as last_event",
        "  from cases.cases c",
        " where c.case_id = any (string_to_array(nullif(rtrim(coalesce(current_setting('cases.touched', true), ''), ','),",
        "                        ''), ',')::bigint[])",
        " order by c.case_id;",
        "",
        "\\if :{?dry}",
        "  \\echo 'DRY RUN: rolling back.'",
        "  rollback;",
        "\\else",
        "  commit;",
        "\\endif",
        "",
    ]
    return "\n".join(head + body + tail)


def write_sql(ops, org_code, runner, out_dir, stem, source=""):
    validate(ops)
    text = render(ops, org_code, source)
    path = new_path(out_dir, stem, ".sql")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    md5 = hashlib.md5(text.encode("utf-8")).hexdigest()
    cmd = f'powershell -NoProfile -ExecutionPolicy Bypass -File "{runner}" -Sql "{path}" -Md5 {md5}'
    return path, md5, cmd


def run_open(argv):
    prep_p, tenant = get_flag(argv, "--prep"), get_flag(argv, "--tenant")
    if not (prep_p and tenant):
        abort("open needs --prep and --tenant")
    org, runner, operator = case_store(tenant)
    received = received_set(argv)
    if not received:
        abort("open needs the packages staff received: --received <package_id> (repeat) or --received-csv <csv>")
    _, rows = read_csv(prep_p, PREP_REQ, "prep sheet")
    owner = get_flag(argv, "--owner") or operator
    status = get_flag(argv, "--status") or "AWAITING_RULING"
    ops, notes = proposals(rows, received, flag_classes(), owner, get_flag(argv, "--actor") or DEFAULT_ACTOR, status,
                          get_flag(argv, "--title-prefix") or "", get_flag(argv, "--party-key"),
                          get_flag(argv, "--receipt"), get_flag(argv, "--manifest-no"), get_flag(argv, "--apex-order"),
                          get_flag(argv, "--gmail"))
    for n in notes:
        print(f"note: {n}")
    if not ops:
        print("no case: no RECEIVED package carries a STOP or DEFECT flag")
        return EXIT_OK
    try:
        validate(ops)
    except ValueError as e:
        abort(str(e))
    out_dir = get_flag(argv, "--out-dir") or os.path.dirname(os.path.abspath(prep_p))
    stem = os.path.splitext(os.path.basename(prep_p))[0] + f"-cases-{stamp()}"
    jpath = new_path(out_dir, stem, ".json")
    with open(jpath, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"ops": ops}, f, ensure_ascii=False, indent=1)
    path, md5, cmd = write_sql(ops, org, runner, out_dir, stem, os.path.basename(prep_p))
    for o in ops:
        print(f"OPEN {o['case_type']} ({o['source_rule']}) package "
              f"{next(ln['ref'] for ln in o['links'] if ln['type'] == 'DUTCHIE_PACKAGE')}: {o['title']}")
    print(f"wrote {jpath}\nwrote {path} (md5 {md5})\nThe Operator runs ONE command:\n  {cmd}")
    return EXIT_OK


def run_sql(argv):
    ops_p, tenant = get_flag(argv, "--ops"), get_flag(argv, "--tenant")
    if not (ops_p and tenant):
        abort("sql needs --ops and --tenant")
    org, runner, _ = case_store(tenant)
    try:
        with open(ops_p, encoding="utf-8-sig") as f:
            doc = json.load(f)
        ops = doc.get("ops") if isinstance(doc, dict) else None
        out_dir = get_flag(argv, "--out-dir") or os.path.dirname(os.path.abspath(ops_p))
        path, md5, cmd = write_sql(ops, org, runner, out_dir, os.path.splitext(os.path.basename(ops_p))[0],
                                   os.path.basename(ops_p))
    except (OSError, json.JSONDecodeError, ValueError) as e:
        abort(f"{ops_p}: {e}")
    print(f"wrote {path} ({len(ops)} op(s), md5 {md5})\nThe Operator runs ONE command:\n  {cmd}")
    return EXIT_OK


def selftest():
    t = Selftest("intake_cases")
    classes = flag_classes()
    prep = [
        {"row": "1", "line": "1", "invoice_item": "Gummies", "dutchie_productid": "11", "dutchie_name": "Gummies 10pk",
         "metrc_package_id": "PKG-A", "metrc_item": "Gummies", "flags": "DEAL_PRINTED"},
        {"row": "2", "line": "2", "invoice_item": "Haze 1g", "dutchie_productid": "22", "dutchie_name": "Haze 1g",
         "metrc_package_id": "PKG-C", "metrc_item": "Preroll - 0.5g - Haze", "flags": "PRICE_DROP_UNMARKED;MANIFEST_ITEM_SIZE_MISMATCH"},
        {"row": "3", "line": "3", "invoice_item": "Mint Vape", "dutchie_productid": "", "dutchie_name": "",
         "metrc_package_id": "PKG-D", "metrc_item": "Mint Vape", "flags": "MANIFEST_COST_MISMATCH"},
        {"row": "4", "line": "4", "invoice_item": "Kief", "dutchie_productid": "44", "dutchie_name": "Kief 1g",
         "metrc_package_id": "PKG-E", "metrc_item": "Kief", "flags": "ITEM_PENDING"},
    ]

    def opened(received):
        return proposals(prep, set(received), classes, "Pat", DEFAULT_ACTOR, receipt="900", manifest_no="M-1")

    ops, notes = opened({"PKG-C"})
    o = ops[0] if ops else {}
    t.check("FIRES: a received package with a size mismatch opens ONE SIZE_MISMATCH case", len(ops) == 1
            and o.get("case_type") == "SIZE_MISMATCH" and o.get("source_rule") == "MANIFEST_ITEM_SIZE_MISMATCH", str(ops))
    t.check("the size case outranks the price flag on the same package and its detail names both",
            "PRICE_DROP_UNMARKED" in o.get("detail", "") and "MANIFEST_ITEM_SIZE_MISMATCH" in o.get("detail", ""))
    t.check("the case links the package, the item and the receipt / manifest given",
            [ln["type"] for ln in o.get("links", [])] == ["DUTCHIE_PACKAGE", "DUTCHIE_ITEM", "DUTCHIE_RECEIPT",
                                                           "METRC_MANIFEST"], str(o.get("links")))
    t.check("the case opens AWAITING_RULING with the owner given", o.get("status") == "AWAITING_RULING" and o.get("owner") == "Pat")
    t.check("QUIET: STOP flags on packages NOT received stay questions in the run (a note each, no case)",
            not opened(set())[0] and sum("not received" in n for n in opened(set())[1]) == 3, str(opened(set())))
    t.check("QUIET: a received package with INFO flags only opens nothing", not opened({"PKG-A"})[0])
    ops_d = opened({"PKG-D"})[0]
    t.check("FIRES: a received manifest cost DEFECT opens a PRICE_MISMATCH case (no item link without an item)",
            len(ops_d) == 1 and ops_d[0]["case_type"] == "PRICE_MISMATCH"
            and "DUTCHIE_ITEM" not in [ln["type"] for ln in ops_d[0]["links"]], str(ops_d))
    ops_e = opened({"PKG-E"})[0]
    t.check("FIRES: any other open STOP on a received package opens an OTHER case",
            len(ops_e) == 1 and ops_e[0]["case_type"] == "OTHER" and ops_e[0]["source_rule"] == "ITEM_PENDING")
    t.check("one case per package, received packages off the sheet are a note",
            len(opened({"PKG-C", "PKG-D", "PKG-E", "PKG-Z"})[0]) == 3
            and any("PKG-Z" in n for n in opened({"PKG-Z"})[1]))

    good_ev = {"op": "event", "case_id": 7, "event": "NOTE", "actor": "Pat", "detail": "it's here"}

    def refused(op, needle):
        try:
            validate([op])
        except ValueError as e:
            return needle in str(e)
        return False

    t.check("QUIET: a well-formed open, link, event, rule and status pass", validate(
        [o, good_ev, {"op": "link", "case_id": 7, "type": "GMAIL_THREAD", "ref": "<a.b@mail.example.com>"},
         {"op": "rule", "case_id": 7, "ruling": "credit", "ruled_by": "Lee", "gmail": "pat@example.com:1a2b3c4d5e6f"},
         {"op": "status", "case_id": 7, "status": "RESOLVED", "actor": "Pat"}]) is None)
    t.check("REFUSED: RULED through `event`", refused(dict(good_ev, event="RULED"), "RULED is `rule`"))
    t.check("REFUSED: a ruling with no mail", refused({"op": "rule", "case_id": 7, "ruling": "x", "ruled_by": "Lee"},
                                                     "no mail, no ruling"))
    t.check("REFUSED: VENDOR_REPLIED with no mail", refused(dict(good_ev, event="VENDOR_REPLIED"), "vendor's mail"))
    t.check("REFUSED: a bare Gmail id", refused(dict(good_ev, gmail="1a2b3c4d5e6f"), "neither an RFC"))
    t.check("REFUSED: an upper-case mailbox", refused(dict(good_ev, gmail="Pat@example.com:1a2b3c4d5e6f"), "neither an RFC"))
    t.check("REFUSED: a case type the store lacks", refused(dict(o, case_type="WRONG_ITEM"), "case_type"))
    t.check("REFUSED: a case opened as RESOLVED", refused(dict(o, status="RESOLVED"), "opens as"))
    t.check("REFUSED: an unknown link type", refused({"op": "link", "case_id": 7, "type": "SLACK", "ref": "x"}, "link type"))
    t.check("REFUSED: an untrimmed link ref", refused({"op": "link", "case_id": 7, "type": "DRIVE_FILE", "ref": " x"}, "trimmed"))
    t.check("REFUSED: a case id that is not a whole number", refused(dict(good_ev, case_id="7"), "case_id"))
    t.check("REFUSED: text carrying the quote tag", refused(dict(good_ev, detail="x $cases$ y"), "quote tag"))
    t.check("REFUSED: a source rule that is not a code", refused(dict(o, source_rule="size mismatch"), "exception code"))

    sql = render([o, good_ev], "EXAMPLE", "prep.csv")
    t.check("SQL: one transaction, dry run rolls back, commit otherwise",
            sql.count("begin;") == 1 and "\\if :{?dry}" in sql and "rollback;" in sql and "commit;" in sql)
    t.check("SQL: quotes are doubled (it's -> it''s)", "'it''s here'" in sql)
    t.check("SQL: the open is guarded on an open case of the same code on the package",
            "already open on package" in sql and "'PKG-C'" in sql and "is not distinct from 'MANIFEST_ITEM_SIZE_MISMATCH'" in sql)
    t.check("SQL: only the store's procedures write (no INSERT / UPDATE / DELETE)",
            not re.search(r"\b(insert|update|delete)\b", sql, re.I) and sql.count("call cases.") == 1 + 4 + 1)
    t.check("SQL: the org is read by code, and the read-back covers the touched cases",
            "org_code = 'EXAMPLE'" in sql and "cases.touched" in sql and "order by c.case_id" in sql)

    with tempfile.TemporaryDirectory() as d:
        ten = os.path.join(d, "CLAUDE.md")
        import intake_pointers
        with open(ten, "w", encoding="utf-8") as f:
            f.write(intake_pointers.SAMPLE.replace("- Watermark: 1000\n",
                                                   "- Watermark: 1000\n- Case store: EXAMPLE via ./case_write.ps1\n"))
        org, runner, operator = case_store(ten)
        t.check("pointer: `Case store:` gives the org code and the runner, made absolute",
                org == "EXAMPLE" and runner == os.path.join(d, "case_write.ps1") and operator == "Pat Example")
        p1, m1, cmd = write_sql([o], org, runner, d, "x")
        p2, m2, _ = write_sql([o], org, runner, d, "x")
        t.check("write: a NEW file each time, the same md5 for the same ops, the command names runner + file + md5",
                p1 != p2 and m1 == m2 and runner in cmd and p1 in cmd and m1 in cmd)
        with open(p1, "rb") as f:
            t.check("write: the file on disk is the md5 printed", hashlib.md5(f.read()).hexdigest() == m1)
    return t.done()


def main(argv):
    if "--selftest" in argv:
        return selftest()
    if not argv or argv[0] not in ("open", "sql"):
        print(__doc__)
        return EXIT_ABORT
    return run_open(argv[1:]) if argv[0] == "open" else run_sql(argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
