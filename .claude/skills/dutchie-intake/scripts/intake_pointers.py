"""intake_pointers.py - read the tenant contract: `## Intake Pointers` + `## BI Change Pointers`.

  python intake_pointers.py --tenant <tenant CLAUDE.md> [--json]
  python intake_pointers.py --selftest

Every other runner in this skill calls `load(path)` through its own `--tenant` flag. The skill
names no tenant, no path and no person: all of that lives in the tenant's gitignored CLAUDE.md.

Accepted line shapes (both are in use):
  - Operator: <name>                     # comment after two spaces and a hash
  - **Write channel:** `neo` -> fallback `playwright` -> `pane` - prose after the value
When a value carries backticks, the FIRST backticked span is the value and the rest is prose.

Exit 0 when every required key is present and filled; 2 (ABORT) otherwise, naming each gap.
A value still written `<like this>` is a placeholder and counts as missing.

A runner that reads only SOME keys calls `load_for(path, need, optional)` instead of `load`: a gap in a key it reads
(or an absent `## Intake Pointers` block) ABORTs; any other gap is a WARNING line, never an abort (receive --prep
reads the tag pointers only; an unfilled `Drive invoices folder:` is not its business).
"""
import json
import os
import re
import sys
import tomllib

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from intake_common import EXIT_ABORT, EXIT_OK, PKG_PREFIX, Selftest, get_flag, norm  # noqa: E402

INTAKE_HEAD, BI_HEAD = "## Intake Pointers", "## BI Change Pointers"
REQUIRED_INTAKE = ["Operator", "Mail label", "Drive invoices folder", "Intake dir", "Exports dir",
                   "Standard cost", "Expiry threshold days", "PO source", "Watermark",
                   "Notice template", "Floor sheet", "Vendor deal tag"]
REQUIRED_BI = ["Backoffice login", "Write channel"]
PATH_KEYS = ["Intake dir", "Exports dir", "Notice template", "Estate dir", "Scripts dir", "Market archive", "FL EQ classes"]
CHANNELS = ["neo", "playwright", "pane"]
PO_SOURCES = ["apex", "vendor pdf", "none"]
OPTIONAL_TAG_KEYS = ["New line tag", "Active tag"]   # R83 / R96; absent = the skill's generic default
# R1-R3, R6: the tenant's fl_eq class map (a TOML of [master.<MC>] tables); optional - absent, Flower equiv stays
# at the create stop on every new line (intake_derive.py).
OPTIONAL_CLASS_KEY = "FL EQ classes"
# Keys a tenant contract may no longer carry, with the reason. A stale line is a contract gap, never silently read.
# R130: the package THC cap is per Master Category in the class map (`package_cap_mg`, read by load_caps below),
# not one tenant-wide pointer.
RETIRED_KEYS = {"Package THC cap mg": "RETIRED by R130: the dose read's cap is the Master Category's `package_cap_mg` "
                                      "in the class map the `FL EQ classes:` pointer names - delete the line"}
# R130: the per-master market limits the class map may carry beside `fl_eq` (all optional, absent = none).
CAP_KEYS = ("unit_cap_mg", "package_cap_mg")
# R130 (re-ruled 2026-10-09): an ENUMERATED Category-level exception - `[limit_exception."<Category>"]`, the shape of
# [plc_exception] - carries its own caps and fl_eq class, read BEFORE its master's. Keys are CAT_PREFIX + norm(Category).
CAT_PREFIX = "cat:"
# The MSRP read (intake_msrp.py). Optional here; intake_msrp ABORTs without center, radius and own store.
OPTIONAL_MARKET_KEYS = ["Market center", "Market radius mi", "Market box", "Market archive", "Own store",
                        "MSRP anchor", "MSRP floor x cost"]
MSRP_ANCHORS = ["market", "own lanes"]
_NUM = r"-?\d+(?:\.\d+)?"

LINE = re.compile(r"^\s*-\s+(?:\*\*)?(?P<key>[^:*`]+?)(?:\*\*)?:(?:\*\*)?\s*(?P<val>.*)$")


def _value(raw):
    raw = re.split(r"\s{2,}#", raw, maxsplit=1)[0].strip()
    ticks = re.findall(r"`([^`]*)`", raw)
    return (ticks[0].strip() if ticks else raw), raw


def _section(lines, head):
    out, on = [], False
    for ln in lines:
        if ln.startswith("## "):
            on = ln.strip() == head
            continue
        if on:
            out.append(ln)
    return out


def parse_text(text):
    """{'intake': {key: value}, 'bi': {...}, 'raw': {...}, 'dupes': [...], 'found': {head: bool}}"""
    lines = text.replace("\r\n", "\n").split("\n")
    res = {"intake": {}, "bi": {}, "raw": {}, "dupes": [], "found": {}}
    for head, bucket in ((INTAKE_HEAD, "intake"), (BI_HEAD, "bi")):
        body = _section(lines, head)
        res["found"][head] = any(ln.strip() == head for ln in lines)
        for ln in body:
            m = LINE.match(ln)
            if not m:
                continue
            key = m.group("key").strip()
            val, raw = _value(m.group("val"))
            if key in res[bucket]:
                res["dupes"].append(f"{head} / {key}")
            res[bucket][key] = val
            res["raw"][f"{bucket}:{key}"] = raw
    return res


def is_placeholder(v):
    return not v or re.fullmatch(r"<[^>]*>", v.strip()) is not None


def ladder(value):
    """`neo -> playwright -> pane` (or `|`, `,`, an arrow) -> ['neo', 'playwright', 'pane'], in order."""
    out = []
    for w in re.findall(r"\b(" + "|".join(CHANNELS) + r")\b", (value or "").lower()):
        if w not in out:
            out.append(w)
    return out


def problems_keyed(res):
    """[(key, problem)]: each contract gap with the key it is about (the section head for an absent section)."""
    probs = []
    for head, bucket, req in ((INTAKE_HEAD, "intake", REQUIRED_INTAKE), (BI_HEAD, "bi", REQUIRED_BI)):
        if not res["found"].get(head):
            probs.append((head, f"section `{head}` absent"))
            continue
        for k in req:
            v = res[bucket].get(k)
            if v is None:
                probs.append((k, f"{head}: key `{k}` missing"))
            elif is_placeholder(v):
                probs.append((k, f"{head}: key `{k}` is still a placeholder ({v!r})"))
    for d in res["dupes"]:
        probs.append((d.split(" / ", 1)[-1], f"duplicate key {d} (ambiguous - one line per key)"))
    days = res["intake"].get("Expiry threshold days")
    if days is not None and not is_placeholder(days) and not re.fullmatch(r"\d+", days):
        probs.append(("Expiry threshold days", f"`Expiry threshold days` must be a whole number, got {days!r}"))
    po = res["intake"].get("PO source")
    if po is not None and not is_placeholder(po) and po.lower() not in PO_SOURCES:
        probs.append(("PO source", f"`PO source` must be one of {PO_SOURCES}, got {po!r}"))
    deal = res["intake"].get("Vendor deal tag")
    if deal is not None and not is_placeholder(deal) and not deal.startswith(PKG_PREFIX):
        probs.append(("Vendor deal tag", f"`Vendor deal tag` must be a package tag (`{PKG_PREFIX}...`, R47), got {deal!r}"))
    for k in OPTIONAL_TAG_KEYS:
        v = res["intake"].get(k)
        if v is not None and not is_placeholder(v) and (v.startswith(PKG_PREFIX) or " - " not in v):
            probs.append((k, f"`{k}` must be an item decision tag (`<prefix> - <word>`, never `{PKG_PREFIX}...`, R47), got {v!r}"))
    a, n = res["intake"].get("Active tag"), res["intake"].get("New line tag")
    if a and n and a == n:
        probs.append(("Active tag", "`Active tag` and `New line tag` name the same tag (R96 vs R83)"))
    mk = {k: res["intake"].get(k) for k in OPTIONAL_MARKET_KEYS}
    mk = {k: v for k, v in mk.items() if v is not None and not is_placeholder(v)}
    if "Market center" in mk and not re.fullmatch(rf"\s*{_NUM}\s*,\s*{_NUM}\s*", mk["Market center"]):
        probs.append(("Market center", f"`Market center` must be `lat,lng`, got {mk['Market center']!r}"))
    if "Market radius mi" in mk and not re.fullmatch(r"\d+(?:\.\d+)?", mk["Market radius mi"]):
        probs.append(("Market radius mi", f"`Market radius mi` must be a number of miles, got {mk['Market radius mi']!r}"))
    if "Market box" in mk and not re.fullmatch(rf"\s*{_NUM}(?:\s*,\s*{_NUM}){{3}}\s*", mk["Market box"]):
        probs.append(("Market box", f"`Market box` must be `south,west,north,east`, got {mk['Market box']!r}"))
    if "MSRP anchor" in mk and mk["MSRP anchor"].strip().lower() not in MSRP_ANCHORS:
        probs.append(("MSRP anchor", f"`MSRP anchor` must be one of {MSRP_ANCHORS}, got {mk['MSRP anchor']!r}"))
    if "MSRP floor x cost" in mk and not re.fullmatch(r"\d+(?:\.\d+)?", mk["MSRP floor x cost"]):
        probs.append(("MSRP floor x cost", f"`MSRP floor x cost` must be a number (2 = keystone), got {mk['MSRP floor x cost']!r}"))
    fl = res["intake"].get(OPTIONAL_CLASS_KEY)
    if fl is not None and not is_placeholder(fl) and not fl.lower().endswith(".toml"):
        probs.append((OPTIONAL_CLASS_KEY, f"`{OPTIONAL_CLASS_KEY}` must name a .toml class map, got {fl!r}"))
    for k, why in RETIRED_KEYS.items():
        if k in res["intake"]:
            probs.append((k, f"`{k}` is {why}"))
    wc = res["bi"].get("Write channel")
    if wc is not None and not is_placeholder(wc) and not ladder(res["raw"].get("bi:Write channel", wc)):
        probs.append(("Write channel", f"`Write channel` names no known channel {CHANNELS}"))
    return probs


def validate(res):
    """List of human-readable problems; empty = the contract is complete."""
    return [m for _, m in problems_keyed(res)]


def split_problems(res, need, optional=()):
    """(blocking, warnings) for a runner that reads only `need` (each must be present and filled) and `optional`
    (read when present; a placeholder there blocks) from `## Intake Pointers`. A gap in any other key is a warning."""
    used = set(need) | set(optional)
    block, warn = [], []
    for k, m in problems_keyed(res):
        (block if k in used or k == INTAKE_HEAD else warn).append(m)
    for k in need:
        v = res["intake"].get(k)
        if k not in REQUIRED_INTAKE and (v is None or is_placeholder(v)):
            block.append(f"{INTAKE_HEAD}: key `{k}` " + ("missing" if v is None else f"is still a placeholder ({v!r})"))
    for k in optional:
        v = res["intake"].get(k)
        if v is not None and is_placeholder(v):
            block.append(f"{INTAKE_HEAD}: key `{k}` is still a placeholder ({v!r}); fill it or delete the line")
    return block, warn


def load_caps(path):
    """R130: {norm(Master category): package cap mg | None} from the tenant's class map (the TOML the
    `FL EQ classes:` pointer names), plus {CAT_PREFIX + norm(Category): ...} for each enumerated Category-level
    exception (`[limit_exception."<Category>"]`), which the dose read takes BEFORE its master's. None = no cap (the
    dose read reads it per piece). Returns None - no caps, the generic fallback stands - when NO table carries
    `package_cap_mg` (a map that predates R130). Raises ValueError on a cap that is not a positive number, or on a
    package cap below the table's own unit cap (a package holds at least one unit)."""
    with open(path, "rb") as f:
        data = tomllib.load(f)
    masters = data.get("master")
    if not isinstance(masters, dict) or not masters:
        raise ValueError(f"{path}: no [master.<Master category>] tables")
    excs = data.get("limit_exception") or {}
    if not isinstance(excs, dict):
        raise ValueError(f"{path}: [limit_exception] must be a table of [limit_exception.\"<Category>\"] tables")
    tables = [("master", k, v, norm(k)) for k, v in masters.items()] + \
             [("limit_exception", k, v, CAT_PREFIX + norm(k)) for k, v in excs.items()]
    if not any(isinstance(b, dict) and "package_cap_mg" in b for _, _, b, _ in tables):
        return None
    out = {}
    for kind, name, body, key in tables:
        body = body if isinstance(body, dict) else {}
        for k in CAP_KEYS:
            v = body.get(k)
            if v is not None and (isinstance(v, bool) or not isinstance(v, (int, float)) or v <= 0):
                raise ValueError(f"{path}: [{kind}.{name}] {k} = {v!r} is not a positive number of mg (R130)")
        u, p = body.get("unit_cap_mg"), body.get("package_cap_mg")
        if u is not None and p is not None and p < u:
            raise ValueError(f"{path}: [{kind}.{name}] package_cap_mg {p} is below unit_cap_mg {u} (R130)")
        out[key] = float(p) if p is not None else None
    return out


def load(path, strict=True):
    """Parsed pointers with paths resolved against the tenant file's folder, plus a `ladder` list.
    strict=True ABORTs on any contract gap; strict=False returns them under 'problems'."""
    try:
        text = open(path, encoding="utf-8").read()
    except OSError as e:
        print(f"ABORT: tenant file {path} unreadable ({e.__class__.__name__})", file=sys.stderr)
        sys.exit(EXIT_ABORT)
    res = parse_text(text)
    probs = validate(res)
    if probs and strict:
        print("ABORT: the tenant contract is incomplete:\n  - " + "\n  - ".join(probs), file=sys.stderr)
        sys.exit(EXIT_ABORT)
    base = os.path.dirname(os.path.abspath(path))
    for bucket in ("intake", "bi"):
        for k in PATH_KEYS:
            v = res[bucket].get(k)
            if v and not is_placeholder(v) and not os.path.isabs(v):
                res[bucket][k] = os.path.normpath(os.path.join(base, v))
    res["ladder"] = ladder(res["raw"].get("bi:Write channel", res["bi"].get("Write channel", "")))
    res["problems"] = probs
    return res


def load_for(path, need, optional=()):
    """`load` for a runner that reads only some keys (see split_problems): ABORT on a gap in a key it reads; print every
    other gap as a WARNING line and carry on."""
    res = load(path, strict=False)
    block, warn = split_problems(res, need, optional)
    for m in warn:
        print(f"WARNING: tenant contract: {m} (a key this runner does not read; not an abort)")
    if block:
        print("ABORT: the tenant contract has a gap in a key this runner reads:\n  - " + "\n  - ".join(block),
              file=sys.stderr)
        sys.exit(EXIT_ABORT)
    return res


def get(res, key, bucket="intake"):
    return res[bucket].get(key)


SAMPLE = """# Tenant

## BI Change Pointers
- **Estate dir:** `./bi-estate` - the estate
- **Backoffice login:** `https://<server>.backoffice.dutchie.com/` - login stop
- **Write channel:** `neo` (agent browser) -> fallback `playwright` -> `pane`. Reads: any channel.

## Intake Pointers
- Operator: Pat Example                  # the human at the pre-create STOP
- Mail label: Intake/Example
- Drive invoices folder: folder-id-0001
- Intake dir: ./intake
- Exports dir: ./exports
- Standard cost: lane Cost (R50)
- Expiry threshold days: 90
- PO source: apex
- Watermark: 1000
- Notice template: ./intake/notice.md
- Floor sheet: python scripts/floor_sheet.py <intake.csv>
- Vendor deal tag: `PKG - Vendor Deal`   # one-time vendor cost deal (R62), set at receiving

## Change log
- Operator: not-a-pointer (outside the block)
"""


def selftest():
    t = Selftest("intake_pointers")
    r = parse_text(SAMPLE)
    t.check("all required keys parsed", validate(r) == [], str(validate(r)))
    t.check("value after two-space hash comment", r["intake"]["Operator"] == "Pat Example", r["intake"]["Operator"])
    t.check("bold key + backticked value", r["bi"]["Estate dir"] == "./bi-estate")
    t.check("ladder order neo > playwright > pane", ladder(r["raw"]["bi:Write channel"]) == CHANNELS)
    t.check("a key outside the block is ignored", r["intake"]["Operator"] != "not-a-pointer (outside the block)")
    broken = SAMPLE.replace("- Watermark: 1000\n", "")
    t.check("FIRES: a missing key is named", any("Watermark" in p for p in validate(parse_text(broken))))
    ph = SAMPLE.replace("Operator: Pat Example", "Operator: <name>")
    t.check("FIRES: a placeholder counts as missing", any("placeholder" in p for p in validate(parse_text(ph))))
    dup = SAMPLE.replace("- Watermark: 1000\n", "- Watermark: 1000\n- Watermark: 2000\n")
    t.check("FIRES: a duplicate key is refused", any("duplicate" in p for p in validate(parse_text(dup))))
    bad = SAMPLE.replace("Expiry threshold days: 90", "Expiry threshold days: ninety")
    t.check("FIRES: a non-integer threshold is refused", any("whole number" in p for p in validate(parse_text(bad))))
    nod = SAMPLE.replace("- Vendor deal tag: `PKG - Vendor Deal`", "- Vendor deal tag: `Vendor Deal`")
    t.check("FIRES: a Vendor deal tag outside the package prefix is refused",
            any("package tag" in p for p in validate(parse_text(nod))))
    t.check("the Vendor deal tag value is the backticked span", r["intake"]["Vendor deal tag"] == "PKG - Vendor Deal")
    t.check("QUIET: the two tag keys are optional", "New line tag" not in r["intake"] and validate(r) == [])
    tg = SAMPLE.replace("## Change log", "- New line tag: `ITM - New PL`\n- Active tag: `ITM - Active`\n\n## Change log", 1)
    rt = parse_text(tg)
    t.check("the tag keys parse as backticked spans", validate(rt) == [] and rt["intake"]["New line tag"] == "ITM - New PL", str(validate(rt)))
    t.check("FIRES: a package tag as the new-line tag is refused",
            any("item decision tag" in p for p in validate(parse_text(tg.replace("`ITM - New PL`", "`PKG - New PL`")))))
    t.check("FIRES: one tag named for both keys is refused",
            any("same tag" in p for p in validate(parse_text(tg.replace("`ITM - New PL`", "`ITM - Active`")))))
    t.check("QUIET: the market keys are optional", "Market center" not in r["intake"] and validate(r) == [])
    mkt = SAMPLE.replace("## Change log", "- Market center: 42.36,-71.06\n- Market radius mi: 15\n"
                         "- Market box: 41.4,-72.1,42.9,-69.9\n- Own store: exampleco\n\n## Change log", 1)
    t.check("the market keys parse and validate", validate(parse_text(mkt)) == [] and
            parse_text(mkt)["intake"]["Market radius mi"] == "15", str(validate(parse_text(mkt))))
    t.check("FIRES: a market center that is not lat,lng is refused",
            any("Market center" in p for p in validate(parse_text(mkt.replace("42.36,-71.06", "downtown")))))
    t.check("FIRES: a market box short of four numbers is refused",
            any("Market box" in p for p in validate(parse_text(mkt.replace("41.4,-72.1,42.9,-69.9", "41.4,-72.1")))))
    t.check("FIRES: a radius that is not a number is refused",
            any("radius" in p for p in validate(parse_text(mkt.replace("radius mi: 15", "radius mi: fifteen")))))
    ms = mkt.replace("## Change log", "- MSRP anchor: own lanes\n- MSRP floor x cost: 2\n\n## Change log", 1)
    t.check("the MSRP anchor and floor parse and validate", validate(parse_text(ms)) == [], str(validate(parse_text(ms))))
    t.check("FIRES: an unknown MSRP anchor is refused",
            any("MSRP anchor" in p for p in validate(parse_text(ms.replace("anchor: own lanes", "anchor: vibes")))))
    t.check("FIRES: a floor that is not a number is refused",
            any("floor" in p for p in validate(parse_text(ms.replace("cost: 2", "cost: keystone")))))
    t.check("QUIET: the FL EQ classes key is optional", OPTIONAL_CLASS_KEY not in r["intake"] and validate(r) == [])
    fl = SAMPLE.replace("## Change log", "- FL EQ classes: ./category-qc/intent.toml   # R1-R3, R6: fl_eq per Master Category\n\n## Change log", 1)
    rf = parse_text(fl)
    t.check("the FL EQ classes value parses with its trailing comment stripped",
            validate(rf) == [] and rf["intake"][OPTIONAL_CLASS_KEY] == "./category-qc/intent.toml", str(rf["intake"].get(OPTIONAL_CLASS_KEY)))
    t.check("FIRES: a class map that is not a .toml is refused",
            any("class map" in p for p in validate(parse_text(fl.replace("intent.toml", "intent.csv")))))
    cp = SAMPLE.replace("## Change log", "- Package THC cap mg: 100   # R129: the adult-use cap per package\n\n## Change log", 1)
    t.check("FIRES (R130): the retired `Package THC cap mg:` pointer is a contract gap that names the class map",
            any("RETIRED by R130" in p and "package_cap_mg" in p for p in validate(parse_text(cp))), str(validate(parse_text(cp))))
    t.check("QUIET: without the retired line the contract is whole", validate(r) == [])
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        def caps_of(body):
            p = os.path.join(td, "m.toml")
            with open(p, "w", encoding="utf-8") as f:
                f.write(body)
            try:
                return load_caps(p)
            except ValueError as e:
                return ("ValueError", str(e))
        good = ('[master.Edible]\nfl_eq = "thc_g_x56"\nunit_cap_mg = 7\npackage_cap_mg = 70\n'
                '[master.Topical]\nfl_eq = "none"\n')
        t.check("load_caps (R130): a master's package cap reads as mg; a master with none reads None (per piece)",
                caps_of(good) == {"edible": 70.0, "topical": None}, str(caps_of(good)))
        t.check("load_caps: a map with no package_cap_mg anywhere is None (the generic fallback stands)",
                caps_of('[master.Edible]\nfl_eq = "thc_g_x56"\n') is None)
        t.check("FIRES: a cap that is not a positive number is refused",
                caps_of(good.replace("package_cap_mg = 70", "package_cap_mg = 0"))[0] == "ValueError"
                and caps_of(good.replace("package_cap_mg = 70", 'package_cap_mg = "70"'))[0] == "ValueError")
        t.check("FIRES: a package cap below the unit cap is refused",
                caps_of(good.replace("package_cap_mg = 70", "package_cap_mg = 5"))[0] == "ValueError")
        exc = good + '[limit_exception."Patch"]\nfl_eq = "thc_g_x5.6"\nunit_cap_mg = 50\npackage_cap_mg = 900\n'
        t.check("load_caps (R130): an enumerated Category exception reads under its own key, beside its master's",
                caps_of(exc) == {"edible": 70.0, "topical": None, CAT_PREFIX + "patch": 900.0}, str(caps_of(exc)))
        t.check("FIRES: a Category exception's bad cap is refused, naming the exception",
                caps_of(exc.replace("package_cap_mg = 900", "package_cap_mg = 9"))[0] == "ValueError"
                and "limit_exception.Patch" in caps_of(exc.replace("package_cap_mg = 900", "package_cap_mg = 9"))[1])
    drive_ph = SAMPLE.replace("Drive invoices folder: folder-id-0001", "Drive invoices folder: <Drive folder id>")
    blk, wrn = split_problems(parse_text(drive_ph), ["Vendor deal tag"], ["New line tag", "Active tag"])
    t.check("split_problems: a placeholder in a key the runner does not read is a WARNING, not a block",
            blk == [] and any("Drive invoices folder" in w for w in wrn), f"block={blk} warn={wrn}")
    vd = parse_text(drive_ph.replace("`PKG - Vendor Deal`", "`<PKG - tag>`"))
    t.check("FIRES: split_problems blocks on a placeholder in a key the runner reads",
            any("Vendor deal tag" in b for b in split_problems(vd, ["Vendor deal tag"])[0]))
    ot = parse_text(SAMPLE.replace("## Change log", "- New line tag: <tag>\n\n## Change log", 1))
    t.check("FIRES: a placeholder in an OPTIONAL key the runner reads blocks (never read as the tag)",
            any("New line tag" in b for b in split_problems(ot, [], ["New line tag"])[0])
            and split_problems(ot, [], [])[0] == [])
    nob = SAMPLE.replace("## BI Change Pointers", "## Something else")
    t.check("FIRES: an absent section is named", any("absent" in p for p in validate(parse_text(nob))))
    return t.done()


def main(argv):
    if "--selftest" in argv:
        return selftest()
    path = get_flag(argv, "--tenant")
    if not path:
        print(__doc__)
        return EXIT_ABORT
    res = load(path, strict=False)
    if "--json" in argv:
        print(json.dumps({k: res[k] for k in ("intake", "bi", "ladder", "problems")}, indent=1))
    else:
        for b in ("bi", "intake"):
            for k, v in res[b].items():
                print(f"  {b:6} {k:24} {v}")
        print(f"  write-channel ladder: {' -> '.join(res['ladder']) or '(none)'}")
    if res["problems"]:
        print("CONTRACT INCOMPLETE:\n  - " + "\n  - ".join(res["problems"]))
        return EXIT_ABORT
    print("contract complete")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
