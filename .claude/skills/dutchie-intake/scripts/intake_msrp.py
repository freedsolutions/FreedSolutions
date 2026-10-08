"""intake_msrp.py - the recommended MSRP for every new line at the pre-create STOP (read-only). R125.

The tenant's R125 states the rule (the anchor, the floor, PENDING until the business confirms; the confirmed
number is the lane Price, R50; Cost is the catalog Cost, never a case-deal price, R62). This script cites it
and implements its parameters: the $5 price points, the radius and the 20 % MSRP_SPREAD are parameters here,
not rule text.

  python intake_msrp.py --intake <intake-vN.csv> --tenant <CLAUDE.md>
                        [--active <catalog-active.csv>] [--min-rows <n>]
                        [--alias <line_no|*>=<word>] ... [--cost <line_no|*>=<catalog cost>] ...
                        [--no-live] [--wm-cache <dir>] [--no-archive]
                        [--out-dir <dir>]
  python intake_msrp.py --selftest

Which rows. A row is a NEW LINE - it needs a price nobody has set - when its verdict is NEW_PL,
NEW_BRAND or NEW_CATEGORY, when it carries NEW_LINE_FIELDS or CROSS_BRAND_COPY, or when it is a
STRAIN_MISSING row whose reason names a new line or a new brand (a NEW_PL that also lacks its Strain
record). A sibling copy or an un-retire keeps its lane's Price and is not read. Rows of one product
line (brand + form + size + process words; strains differ) get ONE recommendation.

The method. Two families of evidence; the tenant's `MSRP anchor:` pointer says which one sets the
number (default `market`); the other is printed beside it as the sanity check.
  Market, in order (the first with enough evidence):
  1. SAME PRODUCT - the brand (lane_Brand, the invoice line's first segment, any --alias) in the same
     form and size, at every store that lists it, any distance. Median within each store first, then
     the median across stores. Needs >= 2 stores.
  2. COMPARABLES - the same form, size and process words, every OTHER brand, stores inside the tenant's
     market radius only. Median within each store first, then across stores. Needs >= 3 stores.
  Own catalog:
  3. OWN LANES (the shelf) - the tenant's active lanes of the same form and size. Lanes at the line's
     cost (within 5 %) set it: the median Price of those that share the most process words with the line.
     No lane at that cost: the Price is interpolated between the nearest cheaper and dearer cost groups
     (one side only: cost x that group's median Price / Cost). The report shows the shelf position (how
     many lanes are priced below the number).
  With `MSRP anchor: own lanes` the order is 3, then 1-2; with `market` it is 1-2, then 3.
  FLOOR: `MSRP floor x cost:` (for example 2 = keystone) - the number is never below cost x floor; a
  line with no evidence at all gets the floor as its number.
  Rounding: to the nearest $5 shelf price point, a half rounds up ($27.50 -> $30, $27.40 -> $25), never
  under the floor.
  COST: the catalog Cost the business will set, `--cost <line_no|*>=<cost>` (a case-deal invoice price is
  not the catalog Cost: R62 / the vendor deal tag), else the landed unit cost, else the invoice unit cost.
  Never lane_Cost: on a new-line row that is the copy source's Cost. The report names the cost and its source.
  Regular prices only: an archive special price and a live on-sale price are never read as the price.
  One physical store counts once; the live read beats the archive for that store. The live feed rarely
  tags a brand, so in a store the brand is already found in, an untagged live row of the same form and
  size and process words whose name carries one of the brand's own strain words (read from its
  brand-matched rows) and no other brand's name is a same-store match, labelled STORE+STRAIN.

Sources (pointers in the tenant `## Intake Pointers`, never in this file):
  * `Market archive:` a dated dutchie.com menu harvest (menu_<store>.json + dispensaries_*.json), read
    one file at a time. dutchie.com scripted reads hit a Cloudflare challenge since 2026-09-23: this
    script never calls dutchie.com, and no lane works around the challenge.
  * Weedmaps public listing feed, live: listings in `Market box:` (S,W,N,E; default = a box of twice the
    radius), then each live menu, `urllib`, 0.4 s between calls, raw JSON cached under
    <Intake dir>/market/wm-<date>/ (a same-day re-run reads the cache). `--no-live` skips it.
  * The Catalog Active export (own lanes): --active, else <Exports dir>/latest/catalog-active.csv.
  * `Market center:` lat,lng and `Market radius mi:` define the comparables set.
  * `MSRP anchor:` `market` | `own lanes`; `MSRP floor x cost:` a number (both optional).
  * `Own store:` comma-separated tokens; a store whose id or name carries one is dropped BEFORE
    matching, and the read asserts zero own-store rows in the market detail (else DEFECT, exit 1).

Output: a NEW `<intake stem>-msrp-<ts>.md` beside the intake (or --out-dir): the STOP block, then per
line the same-product table, the comparables, the own lanes, the evidence counts and the flags. The
STOP block is also printed: it rides the STOP message. Every number is PENDING BUSINESS CONFIRMATION;
this script writes no Price.

Flags (R125, INFO - they never fail the run):
  MSRP_THIN          the basis that set the number has fewer than 3 stores (or lanes)
  MSRP_SPREAD        the recommendation and another market read (same product or comparables) that
                     did not set it differ by more than 20 %
  MSRP_FLOOR_RAISED  the basis read under cost x floor; the floor set the number
  MSRP_MARGIN_LOW    the margin at cost is below the lowest margin among the own lanes read
  MSRP_ARCHIVE_ONLY  no live source contributed to the basis
  MSRP_NO_EVIDENCE   no basis had any evidence: the Operator prices the line with the business
DEFECT (exit 1): OWN_STORE_IN_MARKET (R125: our own store excluded) - an own-store row reached the market detail.
ABORT (exit 2): a missing column, a missing pointer, an export under its row floor. An intake with no
new line is not an abort: exit 0 and says so.
"""
import glob
import json
import math
import os
import re
import statistics as st
import sys
import tempfile
import time
import urllib.request
from datetime import datetime

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import intake_common as C  # noqa: E402
import intake_pointers as PTR  # noqa: E402

INTAKE_REQUIRED = ["invoice_line", "unit_cost", "landed_unit_cost", "lane_Brand", "lane_MasterCategory",
                   "lane_Category", "lane_ProductGrams", "verdict", "flags", "sibling_reason"]
ACTIVE_REQUIRED = ["Product", "Master category", "Category", "Global SubCategory", "Product grams", "Cost",
                   "Price", "Brand"]
NEW_LINE_VERDICTS = ("NEW_PL", "NEW_BRAND", "NEW_CATEGORY")
NEW_LINE_FLAGS = ("NEW_LINE_FIELDS", "CROSS_BRAND_COPY")
MIN_SAME, MIN_COMPS, MIN_THIN, SPREAD, PACE = 2, 3, 3, 0.20, 0.4
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
WM_API = "https://api-g.weedmaps.com/discovery/v1"

# ---------------------------------------------------------------- text classifiers (generic, symmetric)
# The SAME classifiers read the invoice line, a market row and a catalog item, so a line and its market
# twin land in one class by construction. Order matters: a pre-roll that names a vape word is a pre-roll.
FORMS = [
    ("preroll", r"pre\s*-?\s*rolls?|prerolls?|\bjoints?\b|\bblunts?\b|\bcannons?\b"),
    ("vape", r"\bvapes?\b|vaporizers?|\bcarts?\b|cartridges?|\b510\b|\baio\b|all\s*-?\s*in\s*-?\s*one|disposables?|\bpods?\b"),
    ("edible", r"edibles?|gumm(?:y|ies)|chocolates?|\bchews?\b|\bmints?\b|beverages?|\bdrinks?\b|seltzers?|\bsoda\b|\btablets?\b|\blozenges?\b"),
    ("tincture", r"tinctures?|\bsprays?\b|\bdrops\b"),
    ("topical", r"topicals?|\blotions?\b|\bbalms?\b|\bsalves?\b|transdermal|\bpatch(?:es)?\b"),
    ("concentrate", r"concentrates?|\bwax\b|shatter|badder|budder|\bsugar\b|crumble|\bhash\b|rosin|\bresin\b|"
                    r"\bdiamonds?\b|\bsauce\b|\bkief\b|\brso\b"),
    ("flower", r"\bflower\b|\bbuds?\b|\beighths?\b|\bsmalls\b|\bshake\b|\bpopcorn\b|indica|sativa|hybrid"),
]
AIO = r"\baio\b|all\s*-?\s*in\s*-?\s*one|disposables?|\bdispo\b|ready\s*to\s*use"
POD = r"\bpods?\b"
# Process words: a comparable carries the SAME set as the line (none = none of them).
PROCESS = [
    ("liquid diamond", r"liquid\s*diamonds?"),
    ("live rosin", r"live\s*rosin"),
    ("live resin", r"live\s*resin"),
    ("cured resin", r"cured\s*resin"),
    ("rosin", r"\brosin\b"),
    ("resin", r"\bresin\b"),
    ("distillate", r"distillate|\bdisty\b"),
    ("infused", r"infused|\bdipped\b|caviar|moon\s*rocks?|\btwax\b"),
    ("kief", r"\bkief\b"),
    ("hash", r"\bhash\b"),
    ("diamonds", r"\bdiamonds?\b"),
]
OZ = {"1/8": 3.5, "1/4": 7.0, "1/2": 14.0, "1": 28.0}


def form_of(text):
    t = (text or "").lower()
    for name, rx in FORMS:
        if re.search(rx, t):
            if name == "vape":
                return "vape:aio" if re.search(AIO, t) else "vape:pod" if re.search(POD, t) else "vape:cart"
            return name
    return ""


def process_of(text):
    t = (text or "").lower()
    out = []
    for name, rx in PROCESS:
        if re.search(rx, t):
            out.append(name)
            t = re.sub(rx, " ", t)
    return tuple(sorted(out))


def strip_words(text, words):
    """The text with each brand word removed: a brand named `... Diamonds` is not a process word."""
    for w in sorted(words, key=lambda x: -len(x or "")):   # longest first: `Zeta Diamonds` before `Zeta`
        if w and w.strip():
            text = re.sub(r"(?i)(?<![a-z0-9])" + re.escape(w.strip()) + r"(?![a-z0-9])", " ", text)
    return text


def size_of(text, form=""):
    """Total size: ('g', grams), or ('mg', mg) for an edible or a tincture. Packs multiply out."""
    t = (text or "").lower().replace(",", "")
    if form in ("edible", "tincture"):
        mg = [float(m) for m in re.findall(r"(\d+(?:\.\d+)?)\s*mg\b", t)]
        return ("mg", max(mg)) if mg else None
    m = re.search(r"total\s*(\d+(?:\.\d+)?)\s*g\b", t)
    if m:
        return ("g", float(m.group(1)))
    m = (re.search(r"(\d*\.?\d+)\s*g\s*[x×]\s*(\d{1,3})\b", t)
         or re.search(r"(\d*\.?\d+)\s*g\s*\(?\s*(\d{1,3})\s*-?\s*(?:pk|pack|ct|count)s?\b", t))
    if m:
        return ("g", round(float(m.group(1)) * int(m.group(2)), 3))
    m = re.search(r"\b(\d{1,3})\s*-?\s*(?:pk|pack|ct)?\s*[x×]\s*(\d*\.?\d+)\s*g\b", t)
    if m:
        return ("g", round(int(m.group(1)) * float(m.group(2)), 3))
    m = re.search(r"(?<![\d/])(1/8|1/4|1/2|1)\s*oz\b", t)
    if m:
        return ("g", OZ[m.group(1)])
    m = re.search(r"(?<![\d.])(\d*\.?\d+)\s*(?:g|gram|grams)\b", t)
    if m:
        return ("g", float(m.group(1)))
    return None


def same_size(a, b):
    return a is not None and b is not None and a[0] == b[0] and abs(a[1] - b[1]) < 1e-6


def size_label(s):
    return "" if not s else f"{s[1]:g}{s[0]}"


# ---------------------------------------------------------------- geography, stores, numbers
def miles(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 3958.8 * math.asin(math.sqrt(h))


def is_own(tokens, *ids):
    hay = " ".join(i or "" for i in ids).lower()
    return any(t and t in hay for t in tokens)


def store_key(name, city):
    return (" ".join(C.norm(name).split()[:2]), C.norm(city))


def money(x):
    return "-" if x is None else (f"${x:,.0f}" if abs(x - round(x)) < 0.005 else f"${x:,.2f}")


def pct(x):
    return "-" if x is None else f"{x:.0%}"


def snap(x):
    """The nearest $5 shelf price point; a half rounds up."""
    return None if x is None else float(5 * math.floor(x / 5 + 0.5))


def med(xs):
    return st.median(xs) if xs else None


# ---------------------------------------------------------------- market rows
def mrow(source, store_id, store, city, dist, name, brand_field, cls_text, size_text, price, fetched):
    return {"source": source, "store_id": store_id, "store": store, "city": city, "dist": dist, "name": name,
            "brand_field": brand_field, "form": form_of(cls_text),
            "process": process_of(strip_words(f"{name} {cls_text}", [brand_field])),
            "size_text": size_text, "price": price, "fetched": fetched}


def archive_rows(archive, center, own, log):
    """The dated dutchie.com harvest, one file at a time. Regular (rec) prices only."""
    coords = {}
    for fn in glob.glob(os.path.join(archive, "dispensaries_*.json")):
        for d in json.load(open(fn, encoding="utf-8")):
            g = ((d.get("location") or {}).get("geometry") or {}).get("coordinates")
            if g and len(g) == 2:
                coords[d.get("cName")] = (g[1], g[0])
    out, skipped, scanned, dates = [], [], 0, set()
    for fn in sorted(glob.glob(os.path.join(archive, "menu_*.json"))):
        if is_own(own, os.path.basename(fn)):
            skipped.append(os.path.basename(fn))
            continue
        d = json.load(open(fn, encoding="utf-8"))
        cn, nm, city = d.get("cName"), (d.get("name") or "").strip(), d.get("city") or ""
        if is_own(own, cn, nm):
            skipped.append(os.path.basename(fn))
            continue
        scanned += 1
        dates.add((d.get("fetched_at") or "")[:10])
        dist = round(miles(center, coords[cn]), 1) if cn in coords else None
        for p in d.get("items") or []:
            name = p.get("Name") or ""
            cls = f"{name} {p.get('type') or ''} {p.get('subcategory') or ''}"
            opts, rp = p.get("Options") or [], p.get("recPrices") or p.get("medicalPrices") or []
            for i, o in enumerate(opts):
                pr = C.num(rp[i]) if i < len(rp) else None
                if pr is None or pr <= 0:
                    continue
                stx = str(o) if size_of(str(o)) else name
                out.append(mrow("archive", cn, nm, city, dist, name, p.get("brandName") or "", cls, stx, pr,
                                d.get("fetched_at")))
    log.append(f"archive: {scanned} menus scanned, {len(skipped)} own-store file(s) dropped before matching "
               f"({', '.join(skipped) or 'none'}); dated {', '.join(sorted(x for x in dates if x)) or '?'}")
    return out, len(skipped)


def wm_get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(2.0 * (i + 1))


def wm_harvest(box, cache, own, log, get=wm_get, pace=PACE):
    """Listings in the box, then each live menu, as raw JSON in the cache; a cached file is never refetched.
    An own-store listing is dropped before its menu is fetched."""
    os.makedirs(cache, exist_ok=True)
    lf = os.path.join(cache, "listings.json")
    if os.path.exists(lf):
        listings = json.load(open(lf, encoding="utf-8"))
    else:
        listings, page = [], 1
        while True:
            d = get(f"{WM_API}/listings?filter[bounding_box]={box}&filter[plural_types][]=dispensaries"
                    f"&page_size=100&page={page}")
            ls = (d.get("data") or {}).get("listings") or []
            listings += ls
            if len(listings) >= ((d.get("meta") or {}).get("total_listings") or 0) or not ls:
                break
            page += 1
            time.sleep(pace)
        json.dump(listings, open(lf, "w", encoding="utf-8"))
    live = [x for x in listings if (x.get("menu_items_count") or 0) > 0 and x.get("type") == "dispensary"]
    dropped = [x["slug"] for x in live if is_own(own, x.get("slug"), x.get("name"))]
    errs = 0
    for x in live:
        fn = os.path.join(cache, f"menu_{x['slug']}.json")
        if x["slug"] in dropped or os.path.exists(fn):
            continue
        items, page, meta = [], 1, {}
        try:
            while True:
                d = get(f"{WM_API}/listings/dispensaries/{x['slug']}/menu_items?page_size=150&page={page}")
                meta = d.get("meta") or {}
                its = (d.get("data") or {}).get("menu_items") or []
                items += its
                if len(items) >= (meta.get("total_menu_items") or 0) or not its:
                    break
                page += 1
                time.sleep(pace)
        except Exception as e:   # one store's failure is counted, never fatal
            errs += 1
            log.append(f"weedmaps: {x['slug']} failed ({e.__class__.__name__})")
            continue
        json.dump({"slug": x["slug"], "meta": meta, "fetched_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                   "items": items}, open(fn, "w", encoding="utf-8"))
        time.sleep(pace)
    log.append(f"weedmaps live: {len(listings)} listings in the box, {len(live)} with live menus, {len(dropped)} own-store "
               f"listing(s) dropped before matching ({', '.join(dropped) or 'none'}), {errs} fetch error(s); cache {cache}")
    return listings, len(dropped)


def wm_rows(cache, center, own):
    lf = os.path.join(cache, "listings.json")
    listings = {x["slug"]: x for x in json.load(open(lf, encoding="utf-8"))} if os.path.exists(lf) else {}
    out = []
    for fn in sorted(glob.glob(os.path.join(cache, "menu_*.json"))):
        rec = json.load(open(fn, encoding="utf-8"))
        slug = rec.get("slug") or os.path.basename(fn)[5:-5]
        x = listings.get(slug, {})
        nm = x.get("name") or slug
        if is_own(own, slug, nm):
            continue
        lat, lng = x.get("latitude"), x.get("longitude")
        dist = round(miles(center, (lat, lng)), 1) if lat is not None and lng is not None else None
        for it in rec.get("items") or []:
            name = it.get("name") or ""
            brand = (it.get("brand_endorsement") or {}).get("brand_name") or ""
            cls = f"{name} {(it.get('category') or {}).get('name') or ''} {(it.get('edge_category') or {}).get('name') or ''}"
            prices = it.get("prices") or {}
            ents = [p for v in prices.values() if isinstance(v, list) for p in v] or (
                [it["price"]] if isinstance(it.get("price"), dict) else [])
            for p in ents:
                reg = C.num(p.get("original_price")) if p.get("on_sale") else None
                reg = reg if reg is not None else C.num(p.get("price"))
                if reg is None or reg <= 0:
                    continue
                lab = str(p.get("label") or p.get("units") or "")
                w = p.get("weight") or {}
                wt = f"{w.get('value')}{w.get('unit')}" if w.get("value") else ""
                stx = lab if size_of(lab) else wt if size_of(wt) else name
                out.append(mrow("live", slug, nm, x.get("city") or "", dist, name, brand, cls, stx, reg,
                                rec.get("fetched_at")))
    return out


# ---------------------------------------------------------------- the intake side
def is_new_line(r):
    flags = set(filter(None, (r.get("flags") or "").split(";")))
    if r.get("verdict") in NEW_LINE_VERDICTS or flags & set(NEW_LINE_FLAGS):
        return True
    why = (r.get("sibling_reason") or "").lower()
    return r.get("verdict") == "STRAIN_MISSING" and (why.startswith("new line under") or why.startswith("new brand"))


def aliases_of(r, extra):
    out = []
    for a in [r.get("lane_Brand", ""), (r.get("invoice_line") or "").split(" | ")[0]] + list(extra):
        a = (a or "").strip()
        residue = a.lower()
        for _, rx in FORMS:   # a segment that is only form words (`Prerolls`) is no brand word
            residue = re.sub(rx, " ", residue)
        if len(C.norm(residue)) >= 3 and C.norm(a) not in [C.norm(x) for x in out]:
            out.append(a)
    return out


def brand_hit(m, aliases):
    """'brand' when the source's brand field names an alias, 'name' when only the item name does."""
    bf, nm = C.norm(m["brand_field"]), C.norm(m["name"])
    if any(C.has_phrase(bf, a) for a in aliases):
        return "brand"
    if any(C.has_phrase(nm, a) for a in aliases):
        return "name"
    return ""


def group_lines(rows, alias_specs, cost_specs=()):
    groups = {}
    for i, r in enumerate(rows, 1):
        if not is_new_line(r):
            continue
        line = r.get("invoice_line", "")
        form = form_of(f"{line} {r.get('lane_MasterCategory', '')}")
        size = size_of(line, form) or size_of(r.get("lane_ProductGrams", ""), form)
        extra = [v for k, v in alias_specs if k in ("*", str(i), r.get("line_no", ""))]
        proc = process_of(strip_words(line, aliases_of(r, extra)))
        key = (C.norm(r.get("lane_Brand") or line.split(" | ")[0]), form, size, proc)
        g = groups.setdefault(key, {"rows": [], "brand": r.get("lane_Brand", "") or line.split(" | ")[0].strip(),
                                    "form": form, "size": size, "process": proc, "aliases": [], "costs": []})
        g["rows"].append(i)
        for a in aliases_of(r, extra):
            if C.norm(a) not in [C.norm(x) for x in g["aliases"]]:
                g["aliases"].append(a)
        given = [v for k, v in cost_specs if k in ("*", str(i), r.get("line_no", ""))]
        # lane_Cost is NOT read: on a new-line row it is the copy source's Cost, another lane's number.
        for src, c in (("--cost", C.num(given[-1]) if given else None), ("landed unit cost", C.num(r.get("landed_unit_cost"))), ("invoice unit cost", C.num(r.get("unit_cost")))):
            if c:
                g["costs"].append((c, src))
                break
    for g in groups.values():
        top = max((c for c, _ in g["costs"]), default=0)
        real = [(c, src) for c, src in g["costs"] if c >= 0.05 * top]   # a sample line ($0.01) is not the cost
        g["samples"], g["cost"] = len(g["costs"]) - len(real), med([c for c, _ in real])
        g["cost_src"] = ", ".join(sorted({src for _, src in real})) or "none"
    return list(groups.values())


# ---------------------------------------------------------------- the read
def strain_words(rows, aliases):
    """The brand's own strain words, read from its brand-matched rows: each name segment with the brand,
    form, process and size words removed; two or more letters-only words, or one of 5+ letters."""
    out = set()
    for r in rows:
        for seg in re.split(r"[|()\-]", strip_words(r["name"], aliases)):
            t = seg.lower()
            for _, rx in PROCESS + FORMS:   # process first: `liquid diamond` before the form word `diamonds`
                t = re.sub(rx, " ", t)
            t = re.sub(r"\d*\.?\d+\s*(?:g|mg|pk|ct|oz)\b|\bby\b|\bpack\b|\bpk\b|\bthread\b", " ", t)
            w = C.norm(re.sub(r"[^a-z\s]", " ", t))
            if (len(w.split()) >= 2 or len(w) >= 5) and len(w) >= 4:
                out.add(w)
    return sorted(out)


def store_medians(rows):
    by = {}
    for r in rows:
        by.setdefault((r["source"], r["store_id"]), []).append(r)
    return [{"source": src, "store_id": sid, "store": rs[0]["store"], "city": rs[0]["city"], "dist": rs[0]["dist"],
             "median": med([r["price"] for r in rs]), "n": len(rs), "prices": sorted({r["price"] for r in rs}),
             "conf": "HIGH" if any(r.get("hit") == "brand" for r in rs) else
                     "MEDIUM" if any(r.get("hit") == "name" for r in rs) else "STORE+STRAIN",
             "names": sorted({r["name"] for r in rs})[:3], "key": store_key(rs[0]["store"], rs[0]["city"])}
            for (src, sid), rs in by.items()]


def dedupe(stores):
    """One price per physical store: the live read beats the archive."""
    best = {}
    for s in sorted(stores, key=lambda s: s["source"] != "live"):
        best.setdefault(s["key"], s)
    return list(best.values())


def lanes_of(active, g):
    items = []
    for r in active:
        txt = f"{r.get('Product', '')} {r.get('Master category', '')} {r.get('Category', '')} {r.get('Global SubCategory', '')}"
        if form_of(txt) != g["form"]:
            continue
        if g["form"] in ("edible", "tincture"):
            sz = size_of(r.get("Product", ""), g["form"])
        else:
            sz = size_of(r.get("Product grams", ""), g["form"]) or size_of(r.get("Product", ""), g["form"])
        c, p = C.num(r.get("Cost")), C.num(r.get("Price"))
        if not same_size(sz, g["size"]) or not c or not p or c <= 0 or p <= 0:
            continue
        items.append({"brand": r.get("Brand", ""), "category": r.get("Category", ""), "cost": c, "price": p,
                      "process": process_of(txt)})
    lanes = {}
    for x in items:
        lanes.setdefault((x["brand"], x["category"], x["process"]), []).append(x)
    res = [{"brand": b, "category": c, "process": pr, "cost": med([x["cost"] for x in xs]),
            "price": med([x["price"] for x in xs]), "items": len(xs)} for (b, c, pr), xs in lanes.items()]
    for x in res:
        x["ratio"] = x["price"] / x["cost"]
    return res, "same form and size"


def shelf_price(lanes, cost, process):
    """(price, how) from the own shelf; None when no lane or no cost."""
    if not lanes or not cost:
        return None, "no lane or no cost"
    at = [x for x in lanes if abs(x["cost"] - cost) <= 0.05 * cost]
    if at:
        best = max(len(set(x["process"]) & set(process)) for x in at)
        pick = [x for x in at if len(set(x["process"]) & set(process)) == best]
        return med([x["price"] for x in pick]), ("beside " + ", ".join(f"{x['brand']} {x['category']} "
                                                                      f"{money(x['cost'])} / {money(x['price'])}" for x in pick))
    lo = [x for x in lanes if x["cost"] < cost]
    hi = [x for x in lanes if x["cost"] > cost]
    lo = [x for x in lo if x["cost"] == max(y["cost"] for y in lo)]
    hi = [x for x in hi if x["cost"] == min(y["cost"] for y in hi)]
    if lo and hi:
        pl, ph, cl, ch = med([x["price"] for x in lo]), med([x["price"] for x in hi]), lo[0]["cost"], hi[0]["cost"]
        return pl + (ph - pl) * (cost - cl) / (ch - cl), (f"between the {money(cl)}-cost lanes (median {money(pl)}) and "
                                                          f"the {money(ch)}-cost lanes (median {money(ph)})")
    side = lo or hi
    ratio = med([x["ratio"] for x in side])
    return cost * ratio, f"cost x {ratio:.2f}, the median Price / Cost of the nearest {money(side[0]['cost'])}-cost lanes"


def read_line(g, market, active, radius, own, anchor="market", keystone=None):
    sp, comps = [], []
    for m in market:
        if m["form"] != g["form"] or not same_size(size_of(m["size_text"], g["form"]), g["size"]):
            continue
        hit = brand_hit(m, g["aliases"])
        if hit:
            sp.append(dict(m, hit=hit))
        elif m["process"] == g["process"] and m["dist"] is not None and m["dist"] <= radius:
            comps.append(m)
    vocab = strain_words(sp, g["aliases"])
    stores = {store_key(m["store"], m["city"]) for m in sp}
    seen = {id(m) for m in sp}
    alias_n = {C.norm(a) for a in g["aliases"]}
    others = {b for b in {C.norm(m["brand_field"]) for m in market if m["brand_field"]} if len(b) >= 4 and b not in alias_n
              and not any(C.has_phrase(b, a) for a in g["aliases"])} if vocab else set()
    for m in market:
        if (id(m) not in seen and m["source"] == "live" and not m["brand_field"] and store_key(m["store"], m["city"]) in stores
                and m["form"] == g["form"] and same_size(size_of(m["size_text"], g["form"]), g["size"])
                and m["process"] == g["process"]
                and any(C.has_phrase(C.norm(m["name"]), w) for w in vocab)
                and not any(C.has_phrase(C.norm(m["name"]), b) for b in others)):
            sp.append(dict(m, hit="strain"))
            comps = [c for c in comps if c is not m]
    leak = [m for m in sp + comps if is_own(own, m["store_id"], m["store"])]
    sp_st, cp_st = dedupe(store_medians(sp)), dedupe(store_medians(comps))
    lanes, lanes_basis = lanes_of(active, g) if active else ([], "no Catalog export read")
    ratio = med([x["ratio"] for x in lanes])
    shelf, shelf_how = shelf_price(lanes, g["cost"], g["process"])
    sp_med, cp_med = med([s["median"] for s in sp_st]), med([s["median"] for s in cp_st])
    implied = shelf
    bases = []
    if len(sp_st) >= MIN_SAME:
        bases.append(("same product", sp_med, len(sp_st), any(s["source"] == "live" for s in sp_st)))
    elif len(cp_st) >= MIN_COMPS:
        bases.append(("comparables", cp_med, len(cp_st), any(s["source"] == "live" for s in cp_st)))
    own_basis = [("own lanes", implied, len(lanes), True)] if implied else []
    bases = own_basis + bases if anchor == "own lanes" else bases + own_basis
    floor_px = g["cost"] * keystone if keystone and g["cost"] else None
    if bases:
        basis, raw, n, live = bases[0]
    elif floor_px:
        basis, raw, n, live = "keystone floor", floor_px, 0, True
    else:
        basis, raw, n, live = "none", None, 0, False
    rec, flags = snap(raw), []
    if floor_px and rec is not None and rec < floor_px - 1e-9:
        if basis != "keystone floor":
            flags.append("MSRP_FLOOR_RAISED")
        rec = float(5 * math.ceil(floor_px / 5 - 1e-9))
    market_ref = sp_med if len(sp_st) >= MIN_SAME else cp_med if len(cp_st) >= MIN_COMPS else None
    if basis == "none":
        flags.append("MSRP_NO_EVIDENCE")
    else:
        if n < MIN_THIN:
            flags.append("MSRP_THIN")
        refs = [v for b, v in (("same product", sp_med if len(sp_st) >= MIN_SAME else None),
                               ("comparables", cp_med if len(cp_st) >= MIN_COMPS else None)) if v and b != basis]
        if any(abs(rec - v) / rec > SPREAD for v in refs):   # the number against every OTHER market read
            flags.append("MSRP_SPREAD")
        if not live:
            flags.append("MSRP_ARCHIVE_ONLY")
    shelf_pos = (sum(x["price"] < rec - 1e-9 for x in lanes), len(lanes)) if rec and lanes else None
    margin = (rec - g["cost"]) / rec if rec and g["cost"] else None
    floor = min(((x["price"] - x["cost"]) / x["price"] for x in lanes), default=None)
    if margin is not None and floor is not None and margin < floor - 1e-9:
        flags.append("MSRP_MARGIN_LOW")
    by_brand = {}
    for m in comps:
        by_brand.setdefault(m["brand_field"] or "(untagged)", {}).setdefault(m["store_id"], []).append(m["price"])
    top = sorted(((b, len(d), med([med(v) for v in d.values()])) for b, d in by_brand.items()),
                 key=lambda x: (-x[1], x[0]))
    return {"g": g, "sp": sorted(sp_st, key=lambda s: (s["dist"] is None, s["dist"] or 0)), "cp": cp_st,
            "sp_rows": len(sp), "cp_rows": len(comps), "sp_med": sp_med, "cp_med": cp_med,
            "cp_range": (min(s["median"] for s in cp_st), max(s["median"] for s in cp_st)) if cp_st else None,
            "lanes": sorted(lanes, key=lambda x: (-x["items"], x["brand"])), "lanes_basis": lanes_basis,
            "ratio": ratio, "implied": implied, "basis": basis, "raw": raw, "n": n, "rec": rec,
            "margin": margin, "flags": flags, "leak": leak, "top": top[:10], "floor": floor_px,
            "market_ref": market_ref, "shelf": shelf_pos, "shelf_how": shelf_how, "anchor": anchor}


# ---------------------------------------------------------------- the report
def label(g):
    return " ".join(x for x in [g["brand"] or "(brand unread)", g["form"].replace(":", " ") or "(form unread)",
                                size_label(g["size"]) or "(size unread)", "/".join(g["process"])] if x)


def stop_block(reads, intake_name):
    out = ["## MSRP - pending business confirmation (R125)", "",
           f"From `{intake_name}`. One recommendation per new line. The Operator confirms each number with the "
           "business, or replaces it, before the Price is set.", "",
           "| # | Line | Rows | Unit cost | MSRP | Margin | Basis | Evidence (same / comps / lanes) | Flags |",
           "|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(reads, 1):
        out.append(f"| {i} | {label(r['g'])} | {', '.join(map(str, r['g']['rows']))} | {money(r['g']['cost'])} | "
                   f"**{money(r['rec'])}** pending business confirmation | {pct(r['margin'])} | {r['basis']} | "
                   f"{len(r['sp'])} stores / {len(r['cp'])} stores / {len(r['lanes'])} lanes | "
                   f"{', '.join(r['flags']) or '-'} |")
    return "\n".join(out)


def report(reads, intake_path, log, own_dropped, params):
    name = os.path.basename(intake_path)
    L = [f"# MSRP read - {name} ({datetime.now():%Y-%m-%d})", "",
         "Read-only market read for the new lines at the pre-create STOP. No age gate was clicked, no Cloudflare "
         "challenge was touched, nothing was written to the catalog. Every number is **pending business confirmation**.",
         "", stop_block(reads, name), ""]
    for i, r in enumerate(reads, 1):
        g = r["g"]
        L += [f"## {i}. {label(g)}", "",
              f"- Intake rows: {', '.join(map(str, g['rows']))}"
              + (f" ({g['samples']} sample row(s) left out of the cost)" if g["samples"] else ""),
              f"- Brand words matched: {', '.join(g['aliases']) or '(none)'}",
              f"- Recommendation: **{money(r['rec'])}** from {r['basis']}"
              + (f" (raw {money(r['raw'])}, n = {r['n']})" if r["raw"] is not None else "")
              + (f"; margin {pct(r['margin'])} at {money(g['cost'])} ({g['cost_src']})" if r["margin"] is not None else "")
              + ". Pending business confirmation.",
              f"- Anchor: {r['anchor']}. Market reference: {money(r['market_ref'])}. Own-lane shelf: "
              + (f"{money(r['implied'])} ({r['shelf_how']})" if r["implied"] else "-")
              + f". Floor: {money(r['floor'])}."
              + (f" Shelf position: {r['shelf'][0]} of {r['shelf'][1]} similar lanes are priced below it." if r["shelf"] else ""),
              f"- Flags: {', '.join(r['flags']) or 'none'}", "",
              f"### Same-product prices ({len(r['sp'])} stores, {r['sp_rows']} price rows, median {money(r['sp_med'])})", ""]
        if r["sp"]:
            L += ["| Store | City (mi) | Store median | Prices | Items | Source | Match |", "|---|---|---|---|---|---|---|"]
            for s in r["sp"]:
                items = "; ".join(n.replace("|", "\\|") for n in s["names"])
                L.append(f"| {s['store']} | {s['city']} ({'?' if s['dist'] is None else s['dist']}) | {money(s['median'])} | "
                         f"{', '.join(money(p) for p in s['prices'])} | {items} | {s['source']} | {s['conf']} |")
        else:
            L.append("No store lists this brand in this form and size.")
        rng = "" if not r["cp_range"] else f", range {money(r['cp_range'][0])} to {money(r['cp_range'][1])}"
        L += ["", f"### Comparables inside {params['radius']:g} mi, this brand excluded ({len(r['cp'])} stores, "
                  f"{r['cp_rows']} price rows, median {money(r['cp_med'])}{rng})", ""]
        for src in ("live", "archive"):
            xs = [s["median"] for s in r["cp"] if s["source"] == src]
            if xs:
                L.append(f"- {src}: {len(xs)} stores, median {money(med(xs))}")
        if r["top"]:
            L.append("- Brands (stores / median across stores): "
                     + "; ".join(f"{b} {n} / {money(m)}" for b, n, m in r["top"]))
        if not r["cp"]:
            L.append("No comparable inside the radius.")
        L += ["", f"### Own lanes ({len(r['lanes'])} lanes, {r['lanes_basis']})", ""]
        if r["lanes"]:
            L += ["| Brand | Category | Process | Cost | Price | Price / Cost | Items |", "|---|---|---|---|---|---|---|"]
            for x in r["lanes"][:12]:
                L.append(f"| {x['brand']} | {x['category']} | {'/'.join(x['process']) or '-'} | {money(x['cost'])} | "
                         f"{money(x['price'])} | {x['ratio']:.2f} | {x['items']} |")
            L += ["", f"Shelf price at this line's cost: {money(r['implied'])} ({r['shelf_how']}). "
                      f"Median Price / Cost across the lanes: {r['ratio']:.2f}."]
        else:
            L.append("No active lane of this form and size.")
        L.append("")
    L += ["## Method, sources, coverage", "",
          "1. Same product first: the brand in the same form and size, every store, any distance; median within each "
          "store, then across stores (2 stores or more). 2. Comparables: the same form, size and process words, other "
          f"brands, inside {params['radius']:g} mi of {params['center'][0]},{params['center'][1]} (3 stores or more). "
          f"3. Own lanes: the lanes at the line's cost, else interpolated between the nearest cost groups. Anchor: {params.get('anchor', 'market')} (it sets the number; "
          "the other family is the sanity check). "
          + (f"Floor: cost x {params['keystone']:g}. " if params.get("keystone") else "No floor pointer. ")
          + "The nearest $5 price point, never under the floor. "
          "Regular prices only. One store counts once (live beats archive).", ""]
    L += [f"- {x}" for x in log]
    L += ["", "## Own-store exclusion assert", "",
          f"- Own-store tokens: {', '.join(params['own'])}. Dropped before matching: {own_dropped} store file(s) / listing(s).",
          f"- Own-store rows in the market detail: **{sum(len(r['leak']) for r in reads)}**."]
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- CLI
def market_params(ptr):
    raw = {k: (ptr["intake"].get(k) or "") for k in PTR.OPTIONAL_MARKET_KEYS}
    miss = [k for k in ("Market center", "Market radius mi", "Own store") if PTR.is_placeholder(raw[k])]
    if miss:
        C.abort(f"the tenant `## Intake Pointers` lacks {miss} (see templates/intake-pointers.md)")
    lat, lng = (float(x) for x in raw["Market center"].split(","))
    return {"center": (lat, lng), "radius": float(raw["Market radius mi"]),
            "box": None if PTR.is_placeholder(raw["Market box"]) else raw["Market box"].replace(" ", ""),
            "archive": None if PTR.is_placeholder(raw["Market archive"]) else raw["Market archive"],
            "own": [t.strip().lower() for t in raw["Own store"].split(",") if t.strip()],
            "anchor": "market" if PTR.is_placeholder(raw["MSRP anchor"]) else raw["MSRP anchor"].strip().lower(),
            "keystone": None if PTR.is_placeholder(raw["MSRP floor x cost"]) else float(raw["MSRP floor x cost"])}


def default_box(center, radius):
    dlat, dlng = radius * 2 / 69.0, radius * 2 / (69.0 * math.cos(math.radians(center[0])))
    return f"{center[0] - dlat:.2f},{center[1] - dlng:.2f},{center[0] + dlat:.2f},{center[1] + dlng:.2f}"


def run(intake_path, rows, active, params, archive_dir, wm_cache, alias_specs, out_dir, log=None, harvest=None,
        cost_specs=()):
    log = [] if log is None else log
    groups = group_lines(rows, alias_specs, cost_specs)
    if not groups:
        print("no new line in this intake (no NEW_PL / NEW_BRAND / NEW_CATEGORY / new-line STRAIN_MISSING row): "
              "nothing to price")
        return C.EXIT_OK, None
    market, dropped = [], 0
    if archive_dir:
        r, d = archive_rows(archive_dir, params["center"], params["own"], log)
        market += r
        dropped += d
    if wm_cache:
        if harvest:
            _, d = harvest(params["box"] or default_box(params["center"], params["radius"]), wm_cache, params["own"], log)
            dropped += d
        market += wm_rows(wm_cache, params["center"], params["own"])
    if not archive_dir and not wm_cache:
        log.append("no market source read (--no-archive and --no-live): own lanes only")
    log.append(f"market price rows read: {len(market)}; own lanes read from {len(active)} Catalog Active rows")
    reads = [read_line(g, market, active, params["radius"], params["own"], params.get("anchor", "market"),
                       params.get("keystone")) for g in groups]
    stem = os.path.splitext(os.path.basename(intake_path))[0]
    path = C.new_path(out_dir, f"{stem}-msrp-{C.stamp()}", ".md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(report(reads, intake_path, log, dropped, params))
    print(stop_block(reads, os.path.basename(intake_path)))
    print(f"\nwrote {path}")
    leak = sum(len(r["leak"]) for r in reads)
    if leak:
        print(f"DEFECT OWN_STORE_IN_MARKET: {leak} own-store row(s) reached the market detail")
        return C.EXIT_DEFECT, path
    return C.EXIT_OK, path


def main(argv):
    if "--selftest" in argv:
        return selftest()
    ip, tp = C.get_flag(argv, "--intake"), C.get_flag(argv, "--tenant")
    if not ip or not tp:
        print(__doc__)
        return C.EXIT_ABORT
    ptr = PTR.load(tp, strict=False)   # read-only: it needs its own keys, not the whole write contract
    bad = [x for x in ptr["problems"] if any(k in x for k in ("Intake dir", "Exports dir", "Market", "absent"))]
    if bad:
        C.abort("the tenant pointers this read needs are incomplete:\n  - " + "\n  - ".join(bad))
    params = market_params(ptr)
    _, rows = C.read_csv(ip, INTAKE_REQUIRED, "intake")
    ap = C.get_flag(argv, "--active") or os.path.join(ptr["intake"]["Exports dir"], "latest", "catalog-active.csv")
    if not os.path.isfile(ap):
        C.abort(f"no Catalog Active export at {ap} (pass --active)")
    _, active = C.read_csv(ap, ACTIVE_REQUIRED, "catalog active")
    floor = int(C.get_flag(argv, "--min-rows", "50"))
    if len(active) < floor:
        C.abort(f"{os.path.basename(ap)} has {len(active)} rows, under the {floor}-row floor (a filtered one-off?)")
    archive = None if "--no-archive" in argv else params["archive"]
    if archive and not os.path.isdir(archive):
        C.abort(f"`Market archive:` {archive} is not a folder")
    wm = None
    if "--no-live" not in argv:
        wm = C.get_flag(argv, "--wm-cache") or os.path.join(ptr["intake"]["Intake dir"], "market",
                                                           f"wm-{datetime.now():%Y-%m-%d}")
    specs = [tuple(s.split("=", 1)) for s in C.get_all(argv, "--alias") if "=" in s]
    costs = [tuple(s.split("=", 1)) for s in C.get_all(argv, "--cost") if "=" in s]
    out_dir = C.get_flag(argv, "--out-dir") or os.path.dirname(os.path.abspath(ip))
    return run(ip, rows, active, params, archive, wm, specs, out_dir, harvest=wm_harvest if wm else None,
               cost_specs=costs)[0]


# ---------------------------------------------------------------- selftest (offline: synthetic archive + cache)
CENTER = (42.36, -71.06)


def _item(name, brand, typ, opts, prices, special=None):
    return {"Name": name, "brandName": brand, "type": typ, "subcategory": "", "Options": opts,
            "recPrices": prices, "recSpecialPrices": special or [None] * len(prices)}


def _wmi(name, brand, cat, label_, price, orig=None):
    return {"name": name, "brand_endorsement": {"brand_name": brand} if brand else None,
            "category": {"name": cat}, "edge_category": {"name": cat},
            "prices": {"unit": [{"label": label_, "price": price, "original_price": orig or price,
                                 "on_sale": orig is not None}]}}


def _fixture(root, own_leak=False):
    arc, wm = os.path.join(root, "arc"), os.path.join(root, "wm")
    os.makedirs(arc)
    os.makedirs(wm)
    near, far = (42.37, -71.07), (42.90, -71.90)
    disp = [{"cName": c, "location": {"geometry": {"coordinates": [p[1], p[0]]}}} for c, p in
            [("s-a", near), ("s-b", near), ("s-c", near), ("s-d", near), ("s-far", far), ("ownco-metro", near)]]
    json.dump(disp, open(os.path.join(arc, "dispensaries_ma.json"), "w", encoding="utf-8"))
    menus = {
        "s-a": [_item("Zeta Diamonds | Gasolina | Liquid Diamond Cart 1g", "Zeta Gas", "Vaporizers", ["1g"], [30]),
                _item("Other LD Cart 1g Liquid Diamond", "Other", "Vaporizers", ["1g"], [34]),
                _item("Other Liquid Diamond AIO 1g", "Other", "Vaporizers", ["1g"], [55]),
                _item("Value Pack 0.5g x 5", "Valco", "Pre-Rolls", ["2.5g"], [20]),
                _item("Infused Pack 5pk", "Hotco", "Pre-Rolls", ["2.5g"], [60])],
        "s-b": [_item("Zeta | Frutas Liquid Diamond Cart", "Zeta Gas", "Vaporizers", ["1g"], [30], [15]),
                _item("Other Liquid Diamond Cart", "Other", "Vaporizers", ["1g"], [30]),
                _item("Value Pack", "Valco", "Pre-Rolls", ["2.5g"], [24])],
        "s-c": [_item("Gasolina Liquid Diamonds cart", "Zeta Gas", "Vaporizers", ["1g"], [20]),
                _item("Third Liquid Diamond cart", "Third", "Vaporizers", ["1g"], [26]),
                _item("Value Pack", "Valco", "Pre-Rolls", ["2.5g"], [26])],
        "s-d": [_item("Fourth Liquid Diamond cart", "Fourth", "Vaporizers", ["1g"], [28])],
        "s-far": [_item("Zeta Tres Leches Liquid Diamond cart", "Zeta Gas", "Vaporizers", ["1g"], [30]),
                  _item("Far Liquid Diamond cart", "Farco", "Vaporizers", ["1g"], [80])],
        "ownco-metro": [_item("Zeta Liquid Diamond cart", "Zeta Gas", "Vaporizers", ["1g"], [45]),
                         _item("Own Liquid Diamond cart", "Ownbrand", "Vaporizers", ["1g"], [45])],
    }
    for cn, items in menus.items():
        json.dump({"cName": cn, "name": cn.upper(), "city": "Town" + cn[-1], "fetched_at": "2026-09-02T10:00:00",
                   "items": items}, open(os.path.join(arc, f"menu_{cn}.json"), "w", encoding="utf-8"))
    listings = [{"slug": "wm-a", "name": "S-A", "city": "Towna", "latitude": near[0], "longitude": near[1],
                 "menu_items_count": 2, "type": "dispensary"},
                {"slug": "wm-b", "name": "S-B", "city": "Townb", "latitude": near[0], "longitude": near[1],
                 "menu_items_count": 1, "type": "dispensary"},
                {"slug": "wm-c", "name": "Elsewhere", "city": "Townx", "latitude": near[0], "longitude": near[1],
                 "menu_items_count": 1, "type": "dispensary"},
                {"slug": "ownco-group", "name": "OwnCo Group", "city": "Metro", "latitude": near[0],
                 "longitude": near[1], "menu_items_count": 1, "type": "dispensary"}]
    json.dump(listings, open(os.path.join(wm, "listings.json"), "w", encoding="utf-8"))
    json.dump({"slug": "wm-a", "fetched_at": "2026-10-08T10:00:00",
               "items": [_wmi("ZETA GAS | Frutas Liquid Diamond Cart", None, "Vape", "1g", 22.5, 32),
                         _wmi("Value pack", "Valco", "Pre-Rolls", "2.5g", 21)]},
              open(os.path.join(wm, "menu_wm-a.json"), "w", encoding="utf-8"))
    # S-B carries the brand: one true untagged live twin ($31) and two decoys the strain match must refuse -
    # another brand's name in the item ($30, a comparable), and other process words ($98).
    json.dump({"slug": "wm-b", "items": [_wmi("Frutas Liquid Diamond Cart", None, "Vape", "1g", 31),
                                         _wmi("Frutas Liquid Diamond Cart by Third", None, "Vape", "1g", 30),
                                         _wmi("Frutas Distillate Cart", None, "Vape", "1g", 98)]},
              open(os.path.join(wm, "menu_wm-b.json"), "w", encoding="utf-8"))
    json.dump({"slug": "wm-c", "items": [_wmi("Frutas Liquid Diamond Cart", None, "Vape", "1g", 33)]},
              open(os.path.join(wm, "menu_wm-c.json"), "w", encoding="utf-8"))
    if own_leak:   # the breaker: an own-store menu under a slug and name no own-store token sees
        json.dump({"slug": "hq-flagship", "items": [_wmi("Zeta Liquid Diamond cart", "Zeta Gas", "Vape", "1g", 45)]},
                  open(os.path.join(wm, "menu_hq-flagship.json"), "w", encoding="utf-8"))
    return arc, wm


def _intake():
    base = {k: "" for k in INTAKE_REQUIRED}
    return [
        dict(base, invoice_line="Zeta Diamonds | Zeta - Gasolina - Vape Product - 1g | Carts & Vapes 510 Thread | Liquid Diamond",
             unit_cost="12.50", lane_Brand="Zeta", verdict="NEW_CATEGORY"),
        dict(base, invoice_line="Zeta Diamonds | Zeta - Frutas - Vape Product - 1g | Carts & Vapes 510 Thread | Liquid Diamond",
             unit_cost="12.50", lane_Brand="Zeta", verdict="NEW_PL", flags="NEW_LINE_FIELDS"),
        dict(base, invoice_line="Zeta Diamonds | Zeta - Frutas - Vape Product - 1g (sample) | Carts & Vapes | Liquid Diamond",
             unit_cost="0.01", lane_Brand="Zeta", verdict="NEW_CATEGORY"),
        dict(base, invoice_line="Zeta Diamonds | Zeta - Pina - 0.5g 5-Pack (PR) | Prerolls Whole Flower", unit_cost="12.50",
             lane_Brand="Zeta", lane_ProductGrams="1g", lane_MasterCategory="Pre-Roll", verdict="STRAIN_MISSING",
             sibling_reason="new line under 'Zeta': no lane at 2.5g Pre-Roll; nearest ..."),
        dict(base, invoice_line="Zeta Diamonds | Zeta - Motores - 1g (PR)", unit_cost="4", lane_Brand="Zeta",
             lane_MasterCategory="Pre-Roll", verdict="STRAIN_MISSING", sibling_reason="lane zeta | pre roll single | 1: ..."),
        dict(base, invoice_line="Acme | Acme OG Flower 3.5g", unit_cost="15", lane_Brand="Acme", verdict="NEW_ITEM_WITH_SIBLING"),
        dict(base, invoice_line="Newco | Newco Tincture 300mg", unit_cost="20", lane_Brand="Newco", verdict="NEW_BRAND"),
    ]


def _active():
    def a(product, mc, cat, grams, cost, price, brand):
        return {"Product": product, "Master category": mc, "Category": cat, "Global SubCategory": "",
                "Product grams": grams, "Cost": cost, "Price": price, "Brand": brand}
    return [a("Jet | Cart | Live Resin Gelato | 1g", "Vape", "Live Resin Cart", "1g", "15", "35", "Jet"),
            a("Rov | Cart | Cured Resin Haze | 1g", "Vape", "Cured Resin Cart", "1g", "15", "40", "Rov"),
            a("Hs | Pre-Roll | Pack Blue | 2.5g", "Pre-Roll", "Pre-Roll Pack", "2.5g", "10", "25", "Hs"),
            a("Nh | Pre-Roll | Pack Red | 2.5g", "Pre-Roll", "Pre-Roll Pack", "2.5g", "15", "35", "Nh"),
            a("Qc | Pre-Roll | Single | 1g", "Pre-Roll", "Pre-Roll Single", "1g", "4", "8", "Qc")]


def selftest():
    t = C.Selftest("intake_msrp")
    t.check("form: a 510 cart line is vape:cart", form_of("Carts & Vapes 510 Thread Vape | Liquid Diamond") == "vape:cart")
    t.check("form: an AIO is never a cart", form_of("Other LD AIO 1g Vaporizers") == "vape:aio")
    t.check("form: a pre-roll pack is a preroll", form_of("Prerolls Whole Flower") == "preroll")
    t.check("process: Liquid Diamonds is ONE process word, never also 'diamonds'",
            process_of("Liquid Diamonds cart") == ("liquid diamond",))
    t.check("process: whole flower is the empty set", process_of("Prerolls Whole Flower 0.5g") == ())
    t.check("size: 0.5g 5-Pack multiplies out to 2.5g", size_of("Zeta - Pina - 0.5g 5-Pack (PR)") == ("g", 2.5))
    t.check("size: 'pack total 2.5g' wins", size_of("x 0.5g x 5pk | pack total 2.5g") == ("g", 2.5))
    t.check("size: 1/8 oz = 3.5g", size_of("1/8 oz") == ("g", 3.5))
    t.check("size: an edible reads its mg", size_of("100mg per unit (10mg x 10pk)", "edible") == ("mg", 100.0))
    t.check("snap: the nearest $5, a half up ($27.50 -> 30, $27.40 -> 25, $32.49 -> 30)",
            (snap(27.5), snap(27.4), snap(32.49)) == (30.0, 25.0, 30.0))
    rows = _intake()
    sel = [i for i, r in enumerate(rows, 1) if is_new_line(r)]
    t.check("rows: NEW_CATEGORY / NEW_PL / NEW_BRAND / a new-line STRAIN_MISSING are read; a sibling row is not",
            sel == [1, 2, 3, 4, 7], str(sel))
    groups = group_lines(rows, [])
    gl = {label(g): g for g in groups}
    cart_g = gl.get("Zeta vape cart 1g liquid diamond", {})
    t.check("one recommendation per line: 3 cart rows -> 1 group", len(groups) == 3 and cart_g.get("rows") == [1, 2, 3],
            str(list(gl)))
    t.check("a $0.01 sample row is left out of the cost", cart_g.get("cost") == 12.5 and cart_g["cost_src"] == "invoice unit cost")
    t.check("--cost sets the catalog cost and names its source",
            [g for g in group_lines(rows, [], [("*", "15")]) if g["form"] == "vape:cart"][0]["cost"] == 15.0)
    t.check("brand words: lane_Brand + the line's first segment", cart_g.get("aliases") == ["Zeta", "Zeta Diamonds"])
    t.check("brand words: --alias adds one", "Zeta Gas" in group_lines(rows, [("*", "Zeta Gas")])[0]["aliases"])
    own = ["ownco"]
    params = {"center": CENTER, "radius": 15.0, "box": None, "archive": None, "own": own}
    with tempfile.TemporaryDirectory() as root:
        arc, wm = _fixture(root)
        log = []
        code, path = run(os.path.join(root, "x-v2.csv"), rows, _active(), params, arc, wm, [], root, log)
        txt = open(path, encoding="utf-8").read()
        market = archive_rows(arc, CENTER, own, [])[0] + wm_rows(wm, CENTER, own)
        reads = [read_line(g, market, _active(), 15.0, own) for g in groups]
        cart = next(r for r in reads if r["g"]["form"] == "vape:cart")
        pack = next(r for r in reads if r["g"]["form"] == "preroll")
        tinc = next(r for r in reads if r["g"]["form"] == "tincture")
        t.check("same product: 4 stores (live beats archive at S-A and S-B), median $30",
                len(cart["sp"]) == 4 and cart["rec"] == 30.0 and cart["basis"] == "same product",
                f"{len(cart['sp'])} {cart['rec']} {cart['basis']}")
        t.check("a live on-sale price reads its ORIGINAL price", any(s["source"] == "live" and s["median"] == 32 for s in cart["sp"]))
        t.check("strain words come from the brand's own rows (Gasolina, Frutas, Tres Leches)",
                {"gasolina", "frutas", "tres leches"} <= set(strain_words([m for m in market if brand_hit(m, cart_g["aliases"])],
                                                                          cart_g["aliases"])))
        t.check("STORE+STRAIN: an untagged live Frutas cart at a brand store is the brand (S-B live beats its archive)",
                any(s["store_id"] == "wm-b" and s["conf"] == "STORE+STRAIN" for s in cart["sp"]), str([(s["store_id"], s["conf"]) for s in cart["sp"]]))
        sb = next((s for s in cart["sp"] if s["store_id"] == "wm-b"), {})
        t.check("QUIET: the strain match refuses another brand's item and other process words (S-B reads $31 only)",
                sb.get("prices") == [31.0], str(sb.get("prices")))
        t.check("QUIET: an untagged Frutas cart at a store the brand is NOT in stays a comparable",
                not any(s["store_id"] == "wm-c" for s in cart["sp"]) and any(s["store_id"] == "wm-c" for s in cart["cp"]))
        t.check("an archive special price is never the price", all(15 not in s["prices"] for s in cart["sp"]))
        t.check("the far store counts for the same product (any distance)", any(s["store_id"] == "s-far" for s in cart["sp"]))
        cp_ids = sorted(s["store_id"] for s in cart["cp"])
        t.check("comparables: other brands, inside the radius, carts only (no AIO, no far store, not the brand)",
                cp_ids == ["s-a", "s-c", "s-d", "wm-b", "wm-c"] and cart["cp_med"] == 30.0, f"{cp_ids} {cart['cp_med']}")
        t.check("pack: no same product -> comparables (infused pack out; live $21 beats its archive twin), $24 -> $25",
                pack["basis"] == "comparables" and pack["rec"] == 25.0
                and sorted(s["median"] for s in pack["cp"]) == [21.0, 24.0, 26.0],
                f"{pack['basis']} {pack['rec']} {[s['median'] for s in pack['cp']]}")
        t.check("own lanes: two pack lanes at 2.5g; 12.50 sits between the $10 lane ($25) and the $15 lane ($35) -> $30",
                len(pack["lanes"]) == 2 and pack["implied"] == 30.0 and "between" in pack["shelf_how"], f"{pack['implied']} {pack['shelf_how']}")
        g15 = dict(cart_g, cost=15.0, process=("live resin",))
        at15 = read_line(g15, market, _active(), 15.0, own, anchor="own lanes")
        t.check("own lanes: a lane AT the cost sets it, the most shared process words first (Jet live resin $35, not Rov $40)",
                at15["implied"] == 35.0 and at15["rec"] == 35.0 and "Jet" in at15["shelf_how"], f"{at15['implied']} {at15['shelf_how']}")
        t.check("own lanes: one side only -> cost x that group's median Price / Cost", "cost x 2.50" in cart["shelf_how"], cart["shelf_how"])
        t.check("FIRES: MSRP_NO_EVIDENCE on a line with no market and no lane",
                tinc["flags"] == ["MSRP_NO_EVIDENCE"] and tinc["rec"] is None)
        t.check("QUIET: the cart carries no flag", cart["flags"] == [], str(cart["flags"]))
        t.check("FIRES: MSRP_MARGIN_LOW when the margin is under every own lane's", "MSRP_MARGIN_LOW" in pack["flags"],
                str(pack["flags"]))
        arc_only = read_line(cart_g, archive_rows(arc, CENTER, own, [])[0], _active(), 15.0, own)
        t.check("FIRES: MSRP_ARCHIVE_ONLY when no live store is in the basis", "MSRP_ARCHIVE_ONLY" in arc_only["flags"])
        hit = [m for m in market if brand_hit(m, cart_g["aliases"])]
        two = [dict(m, price=60.0) for m in hit if m["store_id"] in ("s-b", "s-far")] + \
              [m for m in market if not brand_hit(m, cart_g["aliases"])]
        thin = read_line(cart_g, two, _active(), 15.0, own)
        t.check("FIRES: MSRP_THIN + MSRP_SPREAD on a 2-store basis far from the comparables",
                len(thin["sp"]) == 2 and {"MSRP_THIN", "MSRP_SPREAD"} <= set(thin["flags"]), f"{thin['rec']} {thin['flags']}")
        a_own = read_line(cart_g, market, _active(), 15.0, own, anchor="own lanes")
        t.check("anchor own lanes: 12.50 x 2.50 = 31.25 -> $30, the market printed beside it",
                a_own["basis"] == "own lanes" and a_own["rec"] == 30.0 and a_own["market_ref"] == 30.5, f"{a_own['rec']} {a_own['market_ref']}")
        t.check("shelf position: 0 of 2 lanes priced below $30 (the bottom of the shelf)", a_own["shelf"] == (0, 2),
                str(a_own["shelf"]))
        k = read_line(pack["g"], market, _active(), 15.0, own, keystone=2.4)
        t.check("FIRES: MSRP_FLOOR_RAISED - $25 comparables under cost 12.50 x 2.4 = $30 -> $30",
                k["rec"] == 30.0 and "MSRP_FLOOR_RAISED" in k["flags"], f"{k['rec']} {k['flags']}")
        k2 = read_line(pack["g"], market, _active(), 15.0, own, keystone=2.3)
        t.check("the floor rounds UP to a price point ($28.75 -> $30, never $25)", k2["rec"] == 30.0, str(k2["rec"]))
        t.check("QUIET: no floor flag when the basis clears the floor",
                "MSRP_FLOOR_RAISED" not in read_line(pack["g"], market, _active(), 15.0, own, keystone=2.0)["flags"])
        kf = read_line(tinc["g"], market, _active(), 15.0, own, keystone=2.0)
        t.check("no evidence + a floor: the floor is the number (20 x 2 = $40), basis named",
                kf["rec"] == 40.0 and kf["basis"] == "keystone floor" and "MSRP_NO_EVIDENCE" not in kf["flags"], str(kf["flags"]))
        t.check("own store dropped before matching: exit 0, the assert reads 0",
                code == 0 and "Own-store rows in the market detail: **0**" in txt)
        t.check("the own-store archive file is named in the log", any("ownco-metro" in x for x in log))
        t.check("the report carries the STOP block, marked pending", "pending business confirmation" in txt and "| 1 |" in txt)
        p2 = run(os.path.join(root, "x-v2.csv"), rows, _active(), params, arc, wm, [], root, [])[1]
        t.check("a re-run writes a NEW file", p2 != path and os.path.exists(path))
    with tempfile.TemporaryDirectory() as root:
        arc, wm = _fixture(root, own_leak=True)
        loud = run(os.path.join(root, "x-v2.csv"), rows, _active(), dict(params, own=["ownco", "hq-flag"]),
                   arc, wm, [], root, [])[0]
        leaked = read_line(cart_g, wm_rows(wm, CENTER, own), [], 15.0, ["hq-flag"])
        t.check("FIRES: OWN_STORE_IN_MARKET when an own-store row reaches the detail (the drop bypassed)",
                len(leaked["leak"]) == 1)
        t.check("QUIET: a token that names the store drops it before matching (exit 0)", loud == 0)
    calls = []

    def fake(url):
        calls.append(url)
        if "/listings?" in url:
            return {"data": {"listings": [{"slug": "a", "type": "dispensary", "menu_items_count": 3},
                                          {"slug": "ownco-x", "type": "dispensary", "menu_items_count": 3}]},
                    "meta": {"total_listings": 2}}
        n = int(re.search(r"page=(\d+)", url).group(1))
        return {"data": {"menu_items": [{"name": f"i{n}"}, {"name": f"j{n}"}] if n == 1 else [{"name": "k"}]},
                "meta": {"total_menu_items": 3}}
    with tempfile.TemporaryDirectory() as root:
        wm_harvest("1,2,3,4", root, own, [], get=fake, pace=0)
        m = json.load(open(os.path.join(root, "menu_a.json"), encoding="utf-8"))
        t.check("weedmaps: a menu paginates to its total; the own-store menu is never fetched",
                len(m["items"]) == 3 and not any("ownco" in c for c in calls), str(calls))
        n = len(calls)
        wm_harvest("1,2,3,4", root, own, [], get=fake, pace=0)
        t.check("weedmaps: a same-day re-run reads the cache (no request)", len(calls) == n)
    fd, p = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("a,b\n1,2\n")
    try:
        C.read_csv(p, INTAKE_REQUIRED, "intake")
        t.check("ABORT on a missing intake column", False)
    except SystemExit as e:
        t.check("ABORT on a missing intake column", e.code == C.EXIT_ABORT)
    finally:
        os.remove(p)
    return t.done()


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
