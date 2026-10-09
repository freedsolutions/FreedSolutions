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
"""
import json
import os
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from intake_common import EXIT_ABORT, EXIT_OK, PKG_PREFIX, Selftest, get_flag  # noqa: E402

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
# R129: the package THC cap (mg) the vendor dose read tests piece x count against; optional - absent, the skill's
# generic default (intake_common.DEFAULT_PACKAGE_THC_CAP_MG) stands.
OPTIONAL_CAP_KEY = "Package THC cap mg"
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


def validate(res):
    """List of human-readable problems; empty = the contract is complete."""
    probs = []
    for head, bucket, req in ((INTAKE_HEAD, "intake", REQUIRED_INTAKE), (BI_HEAD, "bi", REQUIRED_BI)):
        if not res["found"].get(head):
            probs.append(f"section `{head}` absent")
            continue
        for k in req:
            v = res[bucket].get(k)
            if v is None:
                probs.append(f"{head}: key `{k}` missing")
            elif is_placeholder(v):
                probs.append(f"{head}: key `{k}` is still a placeholder ({v!r})")
    for d in res["dupes"]:
        probs.append(f"duplicate key {d} (ambiguous - one line per key)")
    days = res["intake"].get("Expiry threshold days")
    if days is not None and not is_placeholder(days) and not re.fullmatch(r"\d+", days):
        probs.append(f"`Expiry threshold days` must be a whole number, got {days!r}")
    po = res["intake"].get("PO source")
    if po is not None and not is_placeholder(po) and po.lower() not in PO_SOURCES:
        probs.append(f"`PO source` must be one of {PO_SOURCES}, got {po!r}")
    deal = res["intake"].get("Vendor deal tag")
    if deal is not None and not is_placeholder(deal) and not deal.startswith(PKG_PREFIX):
        probs.append(f"`Vendor deal tag` must be a package tag (`{PKG_PREFIX}...`, R47), got {deal!r}")
    for k in OPTIONAL_TAG_KEYS:
        v = res["intake"].get(k)
        if v is not None and not is_placeholder(v) and (v.startswith(PKG_PREFIX) or " - " not in v):
            probs.append(f"`{k}` must be an item decision tag (`<prefix> - <word>`, never `{PKG_PREFIX}...`, R47), got {v!r}")
    a, n = res["intake"].get("Active tag"), res["intake"].get("New line tag")
    if a and n and a == n:
        probs.append("`Active tag` and `New line tag` name the same tag (R96 vs R83)")
    mk = {k: res["intake"].get(k) for k in OPTIONAL_MARKET_KEYS}
    mk = {k: v for k, v in mk.items() if v is not None and not is_placeholder(v)}
    if "Market center" in mk and not re.fullmatch(rf"\s*{_NUM}\s*,\s*{_NUM}\s*", mk["Market center"]):
        probs.append(f"`Market center` must be `lat,lng`, got {mk['Market center']!r}")
    if "Market radius mi" in mk and not re.fullmatch(r"\d+(?:\.\d+)?", mk["Market radius mi"]):
        probs.append(f"`Market radius mi` must be a number of miles, got {mk['Market radius mi']!r}")
    if "Market box" in mk and not re.fullmatch(rf"\s*{_NUM}(?:\s*,\s*{_NUM}){{3}}\s*", mk["Market box"]):
        probs.append(f"`Market box` must be `south,west,north,east`, got {mk['Market box']!r}")
    if "MSRP anchor" in mk and mk["MSRP anchor"].strip().lower() not in MSRP_ANCHORS:
        probs.append(f"`MSRP anchor` must be one of {MSRP_ANCHORS}, got {mk['MSRP anchor']!r}")
    if "MSRP floor x cost" in mk and not re.fullmatch(r"\d+(?:\.\d+)?", mk["MSRP floor x cost"]):
        probs.append(f"`MSRP floor x cost` must be a number (2 = keystone), got {mk['MSRP floor x cost']!r}")
    fl = res["intake"].get(OPTIONAL_CLASS_KEY)
    if fl is not None and not is_placeholder(fl) and not fl.lower().endswith(".toml"):
        probs.append(f"`{OPTIONAL_CLASS_KEY}` must name a .toml class map, got {fl!r}")
    cap = res["intake"].get(OPTIONAL_CAP_KEY)
    if cap is not None and not is_placeholder(cap) and not (re.fullmatch(r"\d+(?:\.\d+)?", cap) and float(cap) > 0):
        probs.append(f"`{OPTIONAL_CAP_KEY}` must be a positive number of mg (R129), got {cap!r}")
    wc = res["bi"].get("Write channel")
    if wc is not None and not is_placeholder(wc) and not ladder(res["raw"].get("bi:Write channel", wc)):
        probs.append(f"`Write channel` names no known channel {CHANNELS}")
    return probs


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
    t.check("QUIET: the package cap key is optional (the generic default stands, R129)", OPTIONAL_CAP_KEY not in r["intake"] and validate(r) == [])
    cp = SAMPLE.replace("## Change log", "- Package THC cap mg: 100   # R129: the adult-use cap per package\n\n## Change log", 1)
    rc = parse_text(cp)
    t.check("the package cap parses as a number with its comment stripped", validate(rc) == [] and rc["intake"][OPTIONAL_CAP_KEY] == "100", str(validate(rc)))
    t.check("FIRES: a cap that is not a positive number is refused",
            any("positive number" in p for p in validate(parse_text(cp.replace("cap mg: 100", "cap mg: one hundred"))))
            and any("positive number" in p for p in validate(parse_text(cp.replace("cap mg: 100", "cap mg: 0")))))
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
