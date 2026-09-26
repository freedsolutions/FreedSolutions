"""intake_common.py - shared mechanics for the dutchie-intake runners (stdlib only).

Nothing here is a rule. It is the lane-contract plumbing every runner shares:
  * read a CSV and ABORT (exit 2) on a missing column, never read it as blank;
  * pick the freshest matching export under a ROW-COUNT guard (filtered one-offs share the
    name and header of a full pull; row count is the only thing that separates them);
  * write a NEW output path, never overwrite;
  * the Dutchie value helpers (`="x"` unwrap, grams, money, the item-name segments, the R50 lane key).

Exit codes, for every script in this skill:
  0 clean (STOP / INFO / BACKLOG counts never fail)   1 DEFECT   2 ABORT (input refused, usage, stub)
"""
import csv
import fnmatch
import os
import re
import sys
from datetime import datetime

sys.dont_write_bytecode = True

EXIT_OK, EXIT_DEFECT, EXIT_ABORT = 0, 1, 2

# The Catalog export (the BI tile export) header, as Dutchie writes it. Platform-generic.
CATALOG_COLS = [
    "ProductId", "SKU", "Available", "Product", "Is cannabis", "Type", "Master category", "Category",
    "Global Category", "Global SubCategory", "Flower equiv", "Product grams", "Servings per Unit",
    "CBD content", "Cost", "Price", "Brand", "Vendor", "Strain Type", "Strain", "Flavor",
    "Is available online", "Online title", "Image URL", "Online description", "Brand catalog product", "Tags",
]
# What intake_match reads. `ProductId` is optional: the 26-column shape has none.
CATALOG_REQUIRED = [c for c in CATALOG_COLS if c not in ("ProductId", "Available")]
STRAINS_REQUIRED = ["Strain name", "Type"]
COL_RETIRED = "Is retired"

DEFAULT_ITEM_QC_TAG = "BI - Item QC"     # R83: rides the copy, read back after create
DEFAULT_DEAD_TAG = "BI - Do Not Use"     # R81: a dead record is never a sibling
PKG_PREFIX = "PKG - "                    # R62 / R72 tag family


def abort(msg):
    print("ABORT: " + msg, file=sys.stderr)
    sys.exit(EXIT_ABORT)


def unwrap(v):
    """Product-export cells are Excel-quoted (`="value"`). Upload files and the Catalog export are not."""
    v = "" if v is None else str(v)
    if v.startswith('="') and v.endswith('"'):
        v = v[2:-1]
    return v.strip()


def num(v):
    try:
        return float(str(v).replace("$", "").replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def money_eq(a, b):
    a, b = num(a), num(b)
    return a is not None and b is not None and abs(a - b) < 0.005


def fmt_money(x, nd=2):
    return "" if x is None else f"{x:.{nd}f}"


def grams_of(v):
    """`1g`, `1`, `0.5g`, `100mg` -> grams as float; None when unreadable. The Catalog export prints
    `Product grams` as a STRING with a unit suffix; float() on it collapses dosed lines to 0."""
    s = unwrap(v).lower().replace(" ", "")
    if not s:
        return None
    m = re.fullmatch(r"(\d+(?:\.\d+)?)(mg|g)?", s)
    if not m:
        return None
    x = float(m.group(1))
    return x / 1000.0 if m.group(2) == "mg" else x


def grams_eq(a, b):
    ga, gb = grams_of(a), grams_of(b)
    return ga is not None and gb is not None and abs(ga - gb) < 1e-9


def segs(name):
    return [p.strip() for p in (name or "").split(" | ")]


def form_word(name):
    """Segment 2 of an item name `{Brand} | {Form} | {Body} | {Dose}[ | {Edition}]`."""
    p = segs(name)
    return p[1] if len(p) >= 2 else ""


def body_of(name):
    p = segs(name)
    return p[2] if len(p) >= 3 else ""


def norm(s):
    """Lowercase, punctuation to spaces, single-spaced. Phrase tests run on this form."""
    s = (s or "").lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9.]+", " ", s)
    return " ".join(s.split())


def has_phrase(text_norm, phrase):
    p = norm(phrase)
    return bool(p) and re.search(r"(?:^| )" + re.escape(p) + r"(?: |$)", text_norm) is not None


def tag_set(v):
    return {t.strip() for t in re.split(r"[,;]", unwrap(v)) if t.strip()}


def lane_key(row):
    """The R50 lane for sibling selection: Brand + Category + grams + Form word (name segment 2)."""
    g = grams_of(row.get("Product grams"))
    return (norm(row.get("Brand")), norm(row.get("Category")),
            "" if g is None else f"{g:g}", norm(form_word(row.get("Product"))))


def read_csv(path, required, label="input"):
    """Rows as dicts with unwrapped values. ABORT on a missing column or an empty file."""
    try:
        with open(path, encoding="utf-8-sig", newline="") as f:
            rdr = csv.DictReader(f)
            hdr = rdr.fieldnames or []
            rows = [{k: unwrap(v) for k, v in r.items() if k is not None} for r in rdr]
    except OSError as e:
        abort(f"{label} {path} unreadable ({e.__class__.__name__})")
    missing = [c for c in required if c not in hdr]
    if missing:
        abort(f"{label} {os.path.basename(path)} lacks column(s) {missing}; present: {hdr}")
    return hdr, rows


def shape(path, required):
    """(row count, missing columns) without loading the file."""
    try:
        with open(path, encoding="utf-8-sig", newline="") as f:
            rdr = csv.reader(f)
            hdr = next(rdr)
            return sum(1 for _ in rdr), [c for c in required if c not in hdr]
    except (StopIteration, OSError, csv.Error):
        return 0, ["<unreadable>"]


def freshest(dir_, patterns, min_rows, required, exclude=()):
    """Freshest file in dir_ matching any pattern (case-insensitive) that ALSO clears min_rows and
    carries every required column. Prints what it stepped over. ABORT when nothing qualifies.

    The row floor is load-bearing: a filtered one-off saved into the same folder has the same
    header and a newer mtime. `exclude` patterns stop an `*active*` glob returning a retired file."""
    if min_rows is None:
        abort("a freshest-file pick needs an explicit row floor (--min-rows); none is guessed")
    try:
        names = os.listdir(dir_)
    except OSError:
        abort(f"exports dir {dir_} unreadable")
    cands = [os.path.join(dir_, n) for n in names
             if any(fnmatch.fnmatch(n.lower(), p.lower()) for p in patterns)
             and not any(fnmatch.fnmatch(n.lower(), x.lower()) for x in exclude)]
    cands.sort(key=os.path.getmtime, reverse=True)
    for c in cands:
        n, missing = shape(c, required)
        if missing:
            print(f"  skipped {os.path.basename(c)} ({n} rows - lacks {missing[0]!r})")
        elif n < min_rows:
            print(f"  skipped {os.path.basename(c)} ({n} rows < {min_rows} floor - a filtered one-off)")
        else:
            return c
    abort(f"no file in {dir_} matching {list(patterns)} clears the {min_rows}-row floor")


def stamp():
    return datetime.now().strftime("%Y-%m-%d-%H%M%S")


def new_path(dir_, stem, ext):
    """A path that does not exist yet: <stem><ext>, else <stem>-2<ext>, -3 ... Never overwrites."""
    os.makedirs(dir_, exist_ok=True)
    p = os.path.join(dir_, stem + ext)
    i = 2
    while os.path.exists(p):
        p = os.path.join(dir_, f"{stem}-{i}{ext}")
        i += 1
    return p


def next_version(dir_, stem, ext=".csv"):
    """<stem>-vN<ext> with N one above the highest existing version (v1 when none)."""
    os.makedirs(dir_, exist_ok=True)
    rx = re.compile(re.escape(stem) + r"-v(\d+)" + re.escape(ext) + r"$")
    top = 0
    for n in os.listdir(dir_):
        m = rx.match(n)
        if m:
            top = max(top, int(m.group(1)))
    return os.path.join(dir_, f"{stem}-v{top + 1}{ext}")


def version_stem(path):
    """`x/abc-v3.csv` -> ('x', 'abc')."""
    d, b = os.path.split(path)
    b = os.path.splitext(b)[0]
    return d, re.sub(r"-v\d+$", "", b)


def write_csv(path, cols, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-") or "x"


def get_flag(args, name, default=None):
    """`--name value` from a raw argv list (repeatable flags use get_all)."""
    if name in args:
        i = args.index(name)
        if i + 1 >= len(args) or args[i + 1].startswith("--"):
            abort(f"{name} needs a value")
        return args[i + 1]
    return default


def get_all(args, name):
    return [args[i + 1] for i, a in enumerate(args) if a == name and i + 1 < len(args)]


class Selftest:
    """Tiny assertion ledger shared by every --selftest."""

    def __init__(self, name):
        self.name, self.ok, self.bad = name, 0, []

    def check(self, label, cond, detail=""):
        if cond:
            self.ok += 1
        else:
            self.bad.append(f"{label} {detail}".strip())
        print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  ({detail})" if detail and not cond else ""))

    def done(self):
        print(f"{self.name} selftest: {self.ok} passed, {len(self.bad)} failed")
        return EXIT_DEFECT if self.bad else EXIT_OK
