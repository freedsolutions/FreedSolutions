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
from intake_common import EXIT_ABORT, EXIT_OK, Selftest, get_flag  # noqa: E402

INTAKE_HEAD, BI_HEAD = "## Intake Pointers", "## BI Change Pointers"
REQUIRED_INTAKE = ["Operator", "Mail label", "Drive invoices folder", "Intake dir", "Exports dir",
                   "Standard cost", "Expiry threshold days", "PO source", "Watermark",
                   "Notice template", "Floor sheet"]
REQUIRED_BI = ["Backoffice login", "Write channel"]
PATH_KEYS = ["Intake dir", "Exports dir", "Notice template", "Estate dir", "Scripts dir"]
CHANNELS = ["neo", "playwright", "pane"]
PO_SOURCES = ["apex", "vendor pdf", "none"]

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
