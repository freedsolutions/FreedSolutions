"""intake_match.py - invoice lines vs the catalog: one verdict per product line, the sibling to copy
from, and the intake CSV v3: 54 columns = the 45 v2 columns + verdict, sibling_reason, flags,
landed_unit_cost, po_line_ref, expiry_date, approved + parse_source (which source intake_parse read:
pypdf / pdftotext / text / lines, so a certify reader knows the provenance) + package_id (the
package tag(s) printed on the invoice line, `;`-joined; blank when the layout prints none).
`package_id` is optional on the lines CSV: a lines file written before the column reads blank.

  python intake_match.py --lines <lines.csv> --active <catalog-active.csv> --retired <catalog-retired.csv>
                         --strains <strains.csv> [--tenant <CLAUDE.md>] [--out-dir <dir>] [--slug <name>]
  python intake_match.py --lines <lines.csv> --exports-dir <dir> --min-rows <n> [--min-rows-retired <n>] ...
  options: --brand "<Catalog Brand>"   force the brand for every line (a single-brand invoice)
           --new-line-tag "<tag>"      the R83 tag a NEW_PL create carries (default `ITM - New PL`;
                                       tenant: `New line tag:` in `## Intake Pointers`)
           --active-tag "<tag>"        the R96 standard state (default `ITM - Active`; tenant: `Active tag:`)
           --tag-override <line_no>=<tag>  the business's direction for one line's copy (`*=` for every
                                       line); beats the line's own tag (R96). Repeatable.
           --dead-tag "<tag>"          the R81 dead-record tag; such rows are never matched or copied
           --drop-tag "<tag>"          a tag the copy must NOT keep (repeatable), e.g. a status tag
  python intake_match.py --selftest

Exports: explicit paths, or `--exports-dir` + `--min-rows` (the freshest file clearing the floor;
no floor is guessed). The active export may be the 87-column shape: `Is retired` then splits it.
Every column read is required; a missing one ABORTs (exit 2).

Verdicts (one per product line; R101 = Copy-from-sibling is the create path; a new line under a known
brand is created from the brand's nearest item; a new brand or category = STOP):
  EXISTS                  brand + body (name segment 3) + grams + form match ONE active item; or
                          brand + body + grams match ONE active item, the form test alone fails and
                          the line names NO form word at all -> EXISTS + FORM_UNREAD.
                          A flavor-led line `(S|I|H) <Flavor> <Form>[ <ratio>]` meets body
                          `<Flavor>[ <Effect>] (<type or ratio>)` by layout (`flavor_led`); the ratio
                          compares unordered (`ratio_key`), for matching only - never for a create name
  RETIRED_MATCH           the same match, on a retired item only - un-retire beats a duplicate (R101)
  NEW_ITEM_WITH_SIBLING   no match; the R50 lane (Brand + Category + grams + Form word) has an active
                          member, and the strain is a Strain record -> copy from the sibling
  STRAIN_MISSING          as above, but the lane is strain-bearing and no Strain record is named
  NEW_PL                  the brand exists; no lane fits; the line's form word places it in a Master
                          category the brand carries -> copy the brand's NEAREST active item there
                          (same form word first, then the closest grams), tagged with the new-line tag (R83)
  NEW_CATEGORY            the brand exists; no lane fits; the line's Master category cannot be read (no
                          catalog form word, or one spanning two) or the brand has no active item in it -> STOP
  NEW_BRAND               no catalog brand is named or implied by the vendor -> STOP (R101)
For EXISTS / RETIRED_MATCH the copy_source_* columns carry the MATCHED record, not a copy source.

Sibling = the lane member WITH an image first, then the newest ProductId, then the lowest SKU.
Lane fields (lane_*) are the sibling's own values: the copy inherits them. A NEW_PL row's lane fields are
the nearest item's, except Product grams (the line's dose) and Cost (the invoice unit cost).

Decision tag (R96): a sibling copy carries the ONE item-namespace tag every active member of its lane
carries; a mixed lane, or a member with none, reads the Active tag. The new-line tag is never copied onto
a sibling copy (R83). `--tag-override` is the business's direction and beats both. Every other
item-namespace tag the sibling carries is dropped from the copy.

Flag table (flags column; none fails the run):
  AMBIGUOUS_MATCH   R101  STOP  two or more items match equally; the operator picks
  FORM_UNREAD       R101  STOP  EXISTS read without the form word: the line names no form word of
                                the catalog (any brand's name segment 2, or a FORM_SYNONYMS token),
                                and brand + body + grams hit exactly ONE active item.
                                The operator confirms the matched item before receiving. Two or more
                                such items, or a line that names another form word, is not EXISTS
                                (NEW_PL when the form places it, else NEW_CATEGORY).
                                No vendor word is added to FORM_SYNONYMS for this: the test is generic.
  LANE_AMBIGUOUS    R50   STOP  two or more lanes fit equally; no sibling chosen
  DOSE_UNREAD       R50   STOP  no grams / mg read from the line; the lane test ran without it
  FLAVOR_TO_SET     R101  STOP  the sibling carries a Flavor: set the new item's own at create
  OT_TEMPLATE_MISS  R101  INFO  the sibling's Online title does not contain its strain; write it by hand
  NEW_LINE_FIELDS   R101  STOP  a NEW_PL copy inherits a different lane: confirm or edit the name, Price,
                                Flower equiv, Servings per Unit and Category / Type in the lane cells
  BAD_LINE          R103  DEFECT a product line with no units or unit cost (exit 1)
"""
import os
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from intake_common import (CATALOG_REQUIRED, COL_RETIRED, DEFAULT_ACTIVE_TAG, DEFAULT_DEAD_TAG,  # noqa: E402
                           DEFAULT_NEW_LINE_TAG, ITEM_PREFIX,
                           EXIT_ABORT, EXIT_DEFECT, EXIT_OK, STRAINS_REQUIRED, Selftest, abort, body_of,
                           form_word, freshest, get_all, get_flag, grams_eq, grams_of, has_phrase, lane_key,
                           next_version, norm, num, read_csv, slug, tag_set, write_csv)

LINES_REQUIRED = ["invoice_no", "invoice_date", "vendor", "line_no", "description", "cases", "units_total",
                  "case_cost", "unit_cost", "ext_cost", "potency_tac_pct", "container", "coa_url", "expiry_date",
                  "is_order_level", "order_level_kind", "po_ref", "parse_source"]
V2_COLS = ["invoice_no", "invoice_date", "invoice_line", "cases", "units_total", "case_cost", "unit_cost",
           "potency_tac_pct", "container", "coa_url", "action", "strain_record", "create_name_FINAL",
           "copy_source_sku", "copy_source_productid", "copy_source_name", "new_sku", "new_productid", "strain",
           "strain_type", "strain_id", "online_title", "online_desc_chars", "online_desc_source", "image_state",
           "tags", "global_link_result", "lane_Category", "lane_Type", "lane_IsCannabis", "lane_MasterCategory",
           "lane_GlobalCategory", "lane_GlobalSubCategory", "lane_ProductGrams", "lane_FlowerEquiv",
           "lane_ServingsPerUnit", "lane_Cost", "lane_Price", "lane_TaxedPrice", "lane_Vendor", "lane_Brand",
           "lane_CBDContent", "lane_Flavor", "lane_OnlineAvailable", "verified"]
V3_NEW = ["verdict", "sibling_reason", "flags", "landed_unit_cost", "po_line_ref", "expiry_date", "approved"]
V3_COLS = V2_COLS + V3_NEW + ["parse_source", "package_id"]
VERDICTS = ["EXISTS", "RETIRED_MATCH", "NEW_ITEM_WITH_SIBLING", "STRAIN_MISSING", "NEW_PL", "NEW_CATEGORY", "NEW_BRAND"]
FLAGS = [("AMBIGUOUS_MATCH", "R101", "STOP"), ("FORM_UNREAD", "R101", "STOP"), ("LANE_AMBIGUOUS", "R50", "STOP"), ("DOSE_UNREAD", "R50", "STOP"),
         ("FLAVOR_TO_SET", "R101", "STOP"), ("OT_TEMPLATE_MISS", "R101", "INFO"), ("NEW_LINE_FIELDS", "R101", "STOP"),
         ("BAD_LINE", "R103", "DEFECT")]
LANE_MAP = {"lane_Category": "Category", "lane_Type": "Type", "lane_IsCannabis": "Is cannabis",
            "lane_MasterCategory": "Master category", "lane_GlobalCategory": "Global Category",
            "lane_GlobalSubCategory": "Global SubCategory", "lane_ProductGrams": "Product grams",
            "lane_FlowerEquiv": "Flower equiv", "lane_ServingsPerUnit": "Servings per Unit", "lane_Cost": "Cost",
            "lane_Price": "Price", "lane_Vendor": "Vendor", "lane_Brand": "Brand", "lane_CBDContent": "CBD content",
            "lane_Flavor": "Flavor", "lane_OnlineAvailable": "Is available online"}

# Vendor vocabulary -> one canonical token, so `preroll`, `pre-roll` and `Pre-Roll` compare equal.
FORM_SYNONYMS = {
    "preroll": ["pre roll", "pre rolls", "prerolls", "joint", "joints"],
    "cart": ["cartridge", "cartridges", "carts", "vape cart", "vape carts"],
    "aio": ["all in one", "disposable", "disposables"],
    "gummy": ["gummies"],
    "tincture": ["tinctures"],
    "capsule": ["capsules", "caps"],
    "chocolate": ["chocolates"],
}
CORP = {"llc", "inc", "co", "corp", "ltd", "company", "the"}


def canon(text):
    t = " " + norm(text) + " "
    for c, syns in FORM_SYNONYMS.items():
        for s in sorted(syns, key=len, reverse=True):
            t = t.replace(" " + norm(s) + " ", " " + c + " ")
    return " ".join(t.split())


def form_score(form, dtoks):
    toks = canon(form).split()
    if not toks or toks[-1] not in dtoks:
        return 0.0
    return sum(1 for x in toks if x in dtoks) / len(toks)


_PACK_RE = re.compile(r"(?<![\d.])(\d{1,3})\s*(?:-\s*)?(?:pk|pack|ct|count|piece|pc)s?\b|(?<![\d.])(\d{1,3})\s*[x×]\s*(?=\d)", re.I)


def pack_count_of(desc):
    """The pack count a line prints (`3pk`, `3-pack`, `10 ct`, `3 x 0.5g`), else None."""
    m = _PACK_RE.search(desc or "")
    return None if not m else int(m.group(1) or m.group(2))


def dose_of(desc):
    """The line's TOTAL grams, the grain the catalog's `Product grams` carries. A pack line prints the
    per-piece weight (`0.5g x 3pk`), so the total is weight x count unless the line also prints the
    total itself (`1.5g (3 x 0.5g)`), in which case that printed total wins."""
    ws = [float(a) / 1000.0 if u.lower() == "mg" else float(a)
          for a, u in re.findall(r"(\d+(?:\.\d+)?)\s*(mg|g)\b", desc or "", re.I)]
    if not ws:
        return None
    n = pack_count_of(desc)
    if not n or n < 2:
        return ws[0]
    for w in ws:
        if any(abs(w - v * n) < 1e-6 for v in ws if v != w):
            return w
    return round(min(ws) * n, 4)


def vendor_tokens(v):
    return {t for t in norm(v).split() if t not in CORP}


def vendor_match(a, b):
    ta, tb = vendor_tokens(a), vendor_tokens(b)
    return bool(ta) and bool(tb) and (ta <= tb or tb <= ta)


def is_dead(r, dead_tag):
    return dead_tag in tag_set(r.get("Tags"))


def pid_num(r):
    return num(r.get("ProductId")) or 0


def pick_sibling(members):
    return sorted(members, key=lambda r: (0 if r.get("Image URL") else 1, -pid_num(r), r.get("SKU", "")))[0]


STRAIN_LETTERS = {"s": "Sativa", "i": "Indica", "h": "Hybrid"}
_LEAD_TYPE_RE = re.compile(r"(?:^|\|)\s*\((sativa|indica|hybrid|[sih])\)\s+([^|]+)", re.I)
_RATIO_RE = re.compile(r"(?<![\w.:])(\d+(?:\.\d+)?(?:\s*:\s*\d+(?:\.\d+)?)+)\s+([a-z]+(?:\s*:\s*[a-z]+)+)"
                       r"((?:\s*\+\s*[a-z]+)*)", re.I)
_PAREN_BODY_RE = re.compile(r"^(.*\S)\s*\(([^()]+)\)$")


def ratio_key(text):
    """The first cannabinoid ratio in `text` as an UNORDERED, case-insensitive key: `1:1 CBD:THC` ==
    `1:1 THC:CBD`, `THC:CBC:CBG` == `THC:CBG:CBC`, `THCv` == `THCV`; `+ <additive>` words ride the key.
    None when no ratio is printed or its counts do not pair. MATCHING only: a create name keeps the
    catalog's own spelling (R26), never the invoice's order."""
    m = _RATIO_RE.search(text or "")
    if not m:
        return None
    ns = [float(x) for x in re.split(r"\s*:\s*", m.group(1))]
    cs = [x.lower() for x in re.split(r"\s*:\s*", m.group(2))]
    if len(ns) != len(cs):
        return None
    return tuple(sorted(zip(cs, ns))), tuple(sorted(norm(x) for x in m.group(3).split("+") if x.strip()))


def flavor_led(desc, vocab):
    """A flavor-led line, read by layout: a segment that LEADS with a strain-type letter, `(S) <Flavor>
    <Form>[ <ratio>]`. Returns (strain type, flavor as printed, ratio key or None); None when the line has
    no such segment. The flavor = the words after the letter, minus the ratio and ONE trailing catalog
    form word (the longest that fits)."""
    m = _LEAD_TYPE_RE.search(desc or "")
    if not m:
        return None
    rest = m.group(2)
    rm = _RATIO_RE.search(rest)
    rkey = ratio_key(rest)
    if rm:
        rest = rest[:rm.start()] + " " + rest[rm.end():]
    words = rest.split()
    for f in sorted({canon(v) for v in vocab if canon(v)}, key=lambda v: len(v.split()), reverse=True):
        k = len(f.split())
        if len(words) > k and canon(" ".join(words[-k:])) == f:
            words = words[:-k]
            break
    flavor = " ".join(words)
    return (STRAIN_LETTERS[m.group(1)[0].lower()], flavor, rkey) if norm(flavor) else None


def flavor_led_hit(fl, body):
    """True when a catalog body `<Flavor>[ <Effect word>] (<Strain type or ratio>)` is the flavor-led
    line's item: the same flavor, and the parenthesis is the line's ratio (unordered) or, on a line that
    prints no ratio, its strain type. One effect word may follow the flavor on a ratio body only."""
    m = _PAREN_BODY_RE.match((body or "").strip())
    if not fl or not m:
        return False
    stype, flavor, rkey = fl
    head, paren, f = norm(m.group(1)), m.group(2), norm(flavor)
    if rkey is None:
        return head == f and norm(paren) == norm(stype)
    return ratio_key(paren) == rkey and (head == f or " ".join(head.split()[:-1]) == f)


def flavor_led_strain(fl, live, brand, strains):
    """(Strain record, name body) for a flavor-led create, both in the CATALOG's spelling: a type-only line
    takes the type record (`<Flavor> (Sativa)`); a ratio line takes the brand's ONE active Strain whose
    ratio key is the line's (`<Flavor> Restore (1:1 THC:CBD)`), never the invoice's order (R26).
    (None, None) when no Strain record, or two, fit."""
    stype, flavor, rkey = fl
    if rkey is None:
        cands = [stype]
    else:
        cands = sorted({r.get("Strain") for r in live if norm(r.get("Brand")) == norm(brand)
                        and r.get("Strain") and ratio_key(r.get("Strain")) == rkey})
    if len(cands) != 1 or cands[0] not in strains:
        return None, None
    s = cands[0]
    return s, (f"{flavor} {s}" if s.endswith(")") else f"{flavor} ({s})")


def body_hit(desc_n, body, fl):
    return has_phrase(desc_n, body) or flavor_led_hit(fl, body)


def body_hits(rows, brand, desc_n, dtoks, g, fl=None):
    hits = []
    for r in rows:
        if norm(r.get("Brand")) != norm(brand):
            continue
        body = body_of(r.get("Product")) or r.get("Strain", "")
        if not body or not body_hit(desc_n, body, fl):
            continue
        if g is not None and not grams_eq(r.get("Product grams"), g):
            continue
        fs = form_score(form_word(r.get("Product")), dtoks)
        if fs > 0:
            hits.append((len(norm(body)), fs, r))
    if not hits:
        return []
    top = max((h[0], h[1]) for h in hits)
    return [h[2] for h in hits if (h[0], h[1]) == top]


def form_vocab(rows):
    """Every form word the active catalog uses (name segment 2, any brand) + the canonical form tokens."""
    return sorted({form_word(r.get("Product")) for r in rows if form_word(r.get("Product"))} | set(FORM_SYNONYMS))


def form_unread_hit(rows, vocab, brand, desc_n, dtoks, g, fl=None):
    """The ONE active item that brand + body + grams hit when the line names NO form word at all;
    None when the grams are unread, the line names any form word of the catalog vocabulary (a named
    form that fits no lane is a new line, not an unread one), or zero / two or more items hit."""
    if g is None or any(form_score(f, dtoks) > 0 for f in vocab):
        return None
    own = [r for r in rows if norm(r.get("Brand")) == norm(brand)]
    hits = [r for r in own if (body_of(r.get("Product")) or r.get("Strain", ""))
            and body_hit(desc_n, body_of(r.get("Product")) or r.get("Strain", ""), fl)
            and grams_eq(r.get("Product grams"), g)]
    return hits[0] if len(hits) == 1 else None


def find_strain(desc_wo_brand_n, strains):
    best = None
    for name in strains:
        if has_phrase(desc_wo_brand_n, name) and (best is None or len(name) > len(best)):
            best = name
    return best


def line_strain(fl, live, brand, desc_n, strains):
    """(Strain record, name body or None) a create carries. A flavor-led line reads its record from its
    layout only (`flavor_led_strain`): a ratio or stray token is never taken for a strain name."""
    if fl:
        return flavor_led_strain(fl, live, brand, strains)
    return find_strain(" ".join(desc_n.replace(norm(brand), " ").split()), strains), None


def new_name(sib, strain):
    p = [x.strip() for x in (sib.get("Product") or "").split(" | ")]
    if len(p) < 4:
        return ""
    p[2] = strain
    return " | ".join(p)


def new_ot(sib, strain, by_body=False):
    """The sibling's Online title with its strain (or, `by_body`, its whole name body) swapped; "" = no fit."""
    ot = sib.get("Online title") or ""
    for old in ((body_of(sib.get("Product")),) if by_body else (sib.get("Strain") or "", body_of(sib.get("Product")))):
        if old and old in ot:
            return ot.replace(old, strain, 1)
    return ""


def decision_tag(members, prefix=ITEM_PREFIX, active_tag=DEFAULT_ACTIVE_TAG, new_line_tag=DEFAULT_NEW_LINE_TAG):
    """(tag, why) for a sibling copy (R96): the ONE item-namespace tag every active lane member carries; a
    mixed lane, or a member with none or two, reads the Active tag. The new-line tag never rides a copy (R83)."""
    vals = []
    for r in members:
        own = sorted(t for t in tag_set(r.get("Tags")) if t.startswith(prefix) and t != new_line_tag)
        vals.append(own[0] if len(own) == 1 else None)
    if vals and None not in vals and len(set(vals)) == 1:
        return vals[0], f"every active member of the lane carries `{vals[0]}`"
    seen = sorted({v for v in vals if v})
    return active_tag, ("mixed lane (" + ", ".join(f"`{v}`" for v in seen) + ")" if seen
                        else "no lane member carries one decision tag") + f": `{active_tag}`"


def copy_tags(src, drop_tags, prefix, decision):
    """The source's tags minus the dropped ones and every item-namespace tag, plus the ONE decision tag."""
    keep = {t for t in tag_set(src.get("Tags")) - set(drop_tags) if not t.startswith(prefix)}
    return ", ".join(sorted(keep | {decision}))


def place_line(live, brand, dtoks):
    """(Master category, form word, why-not) for a line that fits no lane: the catalog items whose form word
    the line names, at the best score, the brand's own first. No MC when no form word is read or the best
    candidates span two Master categories - the line cannot be placed, so it is not a new LINE."""
    scored = [(form_score(form_word(r.get("Product")), dtoks), r) for r in live]
    scored = [(s, r) for s, r in scored if s > 0]
    if not scored:
        return None, None, "the line names no form word the catalog carries"
    pool = [(s, r) for s, r in scored if norm(r.get("Brand")) == norm(brand)] or scored
    top = max(s for s, _ in pool)
    best = [r for s, r in pool if s == top]
    mcs = sorted({r.get("Master category", "") for r in best})
    if len(mcs) != 1 or not mcs[0]:
        return None, None, f"the form word read spans {len(mcs)} Master categories ({', '.join(m or 'blank' for m in mcs)})"
    forms = [form_word(r.get("Product")) for r in best]
    return mcs[0], max(sorted(set(forms)), key=forms.count), ""


def nearest_in_mc(live, brand, mc, dtoks, g):
    """The brand's active item in the Master category closest to the line: the same form word first, then
    the closest grams, then the sibling order (image, newest ProductId, lowest SKU). None = the brand has none."""
    own = [r for r in live if norm(r.get("Brand")) == norm(brand) and r.get("Master category") == mc]

    def key(r):
        rg = grams_of(r.get("Product grams"))
        gap = abs(rg - g) if rg is not None and g is not None else float("inf")
        return (-form_score(form_word(r.get("Product")), dtoks), gap,
                0 if r.get("Image URL") else 1, -pid_num(r), r.get("SKU", ""))
    return sorted(own, key=key)[0] if own else None


def base_row(line):
    return {"invoice_no": line.get("invoice_no", ""), "invoice_date": line.get("invoice_date", ""),
            "invoice_line": line.get("description", ""), "cases": line.get("cases", ""),
            "units_total": line.get("units_total", ""), "case_cost": line.get("case_cost", ""),
            "unit_cost": line.get("unit_cost", ""), "potency_tac_pct": line.get("potency_tac_pct", ""),
            "container": line.get("container", ""), "coa_url": line.get("coa_url", ""),
            "expiry_date": line.get("expiry_date", ""), "approved": "",
            "parse_source": line.get("parse_source", ""), "package_id": line.get("package_id") or ""}


def fill_from(row, src):
    row["copy_source_sku"], row["copy_source_productid"] = src.get("SKU", ""), src.get("ProductId", "")
    row["copy_source_name"] = src.get("Product", "")
    for k, c in LANE_MAP.items():
        row[k] = src.get(c, "")


def match(lines, active, retired, strains, brand_override=None, new_line_tag=DEFAULT_NEW_LINE_TAG,
          dead_tag=DEFAULT_DEAD_TAG, drop_tags=(), active_tag=DEFAULT_ACTIVE_TAG, prefix=ITEM_PREFIX,
          tag_overrides=None):
    """Pure: (intake rows, defects). `strains` = {name: {'type':..., 'id':...}}. `tag_overrides` =
    {line_no or '*': tag} - the business's direction for a sibling copy's decision tag (R96)."""
    tag_overrides = tag_overrides or {}
    live = [r for r in active if not is_dead(r, dead_tag)]
    old = [r for r in retired if not is_dead(r, dead_tag)]
    everything = live + old
    vocab = form_vocab(live)
    brands = sorted({r["Brand"] for r in everything if r.get("Brand")}, key=len, reverse=True)
    out, defects = [], []
    for ln in lines:
        if (ln.get("order_level_kind") or "").strip():
            continue
        row, flags = base_row(ln), []
        units, cost = num(ln.get("units_total")), num(ln.get("unit_cost"))
        if units is None or units <= 0 or cost is None:
            defects.append(f"BAD_LINE line {ln.get('line_no')}: {ln.get('description')!r}")
        desc = ln.get("description", "")
        desc_n, dtoks = norm(desc), set(canon(desc).split())
        g = dose_of(desc)
        fl = flavor_led(desc, vocab)
        if g is None:
            flags.append("DOSE_UNREAD")
        vend = ln.get("vendor", "")
        vb = sorted({r["Brand"] for r in everything if r.get("Brand")
                     and (vendor_match(r.get("Vendor"), vend) or vendor_match(r["Brand"], vend))})
        named = [b for b in brands if has_phrase(desc_n, b)]
        brand = brand_override or (named[0] if named else (vb[0] if len(vb) == 1 else None))
        if not brand:
            row.update(verdict="NEW_BRAND", action="STOP - new brand (R101)",
                       sibling_reason=(f"no catalog brand named in the line; vendor {vend!r} carries {len(vb)} brand(s)"
                                       + (f" ({', '.join(vb)})" if vb else "")))
            row["flags"] = ";".join(flags)
            out.append(row)
            continue
        hits = body_hits(live, brand, desc_n, dtoks, g, fl)
        if hits:
            if len(hits) > 1:
                flags.append("AMBIGUOUS_MATCH")
            m = pick_sibling(hits)
            fill_from(row, m)
            row.update(verdict="EXISTS", action="RECEIVE - exists", strain=m.get("Strain", ""),
                       strain_type=m.get("Strain Type", ""), online_title=m.get("Online title", ""),
                       tags=m.get("Tags", ""),
                       sibling_reason=f"matched {m.get('SKU')} {m.get('Product')!r}"
                                      + (f"; {len(hits)} equal candidates: " + ", ".join(h.get("SKU", "") for h in hits)
                                         if len(hits) > 1 else ""))
            row["flags"] = ";".join(flags)
            out.append(row)
            continue
        rhits = body_hits(old, brand, desc_n, dtoks, g, fl)
        if rhits:
            if len(rhits) > 1:
                flags.append("AMBIGUOUS_MATCH")
            m = pick_sibling(rhits)
            fill_from(row, m)
            row.update(verdict="RETIRED_MATCH", action="STOP - un-retire beats a duplicate (R101)",
                       strain=m.get("Strain", ""), strain_type=m.get("Strain Type", ""), tags=m.get("Tags", ""),
                       online_title=m.get("Online title", ""),
                       sibling_reason=f"retired {m.get('SKU')} {m.get('Product')!r}")
            row["flags"] = ";".join(flags)
            out.append(row)
            continue
        lanes = {}
        for r in live:
            if norm(r.get("Brand")) != norm(brand):
                continue
            if g is not None and not grams_eq(r.get("Product grams"), g):
                continue
            fs = form_score(form_word(r.get("Product")), dtoks)
            if fs > 0:
                lanes.setdefault(lane_key(r), {"fs": fs, "rows": []})["rows"].append(r)
        if not lanes:
            m = form_unread_hit(live, vocab, brand, desc_n, dtoks, g, fl)
            if m is not None:
                flags.append("FORM_UNREAD")
                fill_from(row, m)
                row.update(verdict="EXISTS", action="STOP - confirm the match: no form word read (R101)",
                           strain=m.get("Strain", ""), strain_type=m.get("Strain Type", ""),
                           online_title=m.get("Online title", ""), tags=m.get("Tags", ""),
                           sibling_reason=f"matched {m.get('SKU')} {m.get('Product')!r} on brand + body + grams; "
                                          f"the line names no form word (FORM_UNREAD)")
                row["flags"] = ";".join(flags)
                out.append(row)
                continue
            at = f"{'?' if g is None else format(g, 'g')}g"
            mc, form, why = place_line(live, brand, dtoks)
            near = nearest_in_mc(live, brand, mc, dtoks, g) if mc else None
            if near is None:
                row.update(verdict="NEW_CATEGORY", action="STOP - new category for the brand (R101)", lane_Brand=brand,
                           sibling_reason=f"brand {brand!r} has no active lane at {at} with a form word in the line; "
                                          + (why or f"it has no active item in Master category {mc!r}"))
                row["flags"] = ";".join(flags)
                out.append(row)
                continue
            fill_from(row, near)
            strain, fbody = line_strain(fl, live, brand, desc_n, strains)
            reason = (f"new line under {brand!r}: no lane at {at} {form}; nearest active item in Master category "
                      f"{mc!r}: {near.get('SKU')} {near.get('Product')!r}")
            if near.get("Strain") and not strain:
                row.update(verdict="STRAIN_MISSING", action="STOP - mint the Strain record first (R101)",
                           strain_record="MISSING", sibling_reason=reason + "; no Strain record named in the line")
                row["flags"] = ";".join(flags)
                out.append(row)
                continue
            flags.append("NEW_LINE_FIELDS")
            if near.get("Flavor"):
                flags.append("FLAVOR_TO_SET")
            s = strain or ""
            dose = "" if g is None else f"{g:g}g"
            seg0 = (near.get("Product") or "").split(" | ")[0].strip() or brand
            if s:
                flags.append("OT_TEMPLATE_MISS")
            row.update(verdict="NEW_PL", action="CREATE - copy nearest (new line, R83)",
                       sibling_reason=reason + "; set or confirm at the stop: name, Price, Flower equiv, "
                                               "Servings per Unit, Category / Type",
                       strain_record="LIVE" if s else "",
                       create_name_FINAL=" | ".join([seg0, form, fbody or s, dose]) if s and dose else "",
                       strain=s, strain_type=(strains.get(s) or {}).get("type", ""),
                       strain_id=(strains.get(s) or {}).get("id", ""), online_title="",
                       online_desc_chars=str(len(near.get("Online description") or "")),
                       online_desc_source="nearest item's template - rewrite for the new line (platform KB sourcing chain)",
                       image_state=("nearest item's image carried - keep only if generic brand art (platform KB Images)"
                                    if near.get("Image URL") else "0 images (NO_ECOM_IMAGE - a human supplies art)"),
                       lane_ProductGrams=dose or row.get("lane_ProductGrams", ""),
                       lane_Cost=ln.get("unit_cost", "") or row.get("lane_Cost", ""),
                       tags=copy_tags(near, drop_tags, prefix, new_line_tag))
            row["flags"] = ";".join(flags)
            out.append(row)
            continue
        best = max(v["fs"] for v in lanes.values())
        top = [k for k, v in lanes.items() if v["fs"] == best]
        if len(top) > 1:
            flags.append("LANE_AMBIGUOUS")
            row.update(verdict="NEW_ITEM_WITH_SIBLING", action="STOP - lane ambiguous (R50)", lane_Brand=brand,
                       sibling_reason="lanes tie: " + " / ".join(" | ".join(k) for k in top))
            row["flags"] = ";".join(flags)
            out.append(row)
            continue
        members = lanes[top[0]]["rows"]
        sib = pick_sibling(members)
        fill_from(row, sib)
        with_img = sum(1 for r in members if r.get("Image URL"))
        reason = (f"lane {' | '.join(top[0])}: {len(members)} active member(s), {with_img} with an image; "
                  f"chose {sib.get('SKU')} ({'image' if sib.get('Image URL') else 'no image'}, "
                  f"ProductId {sib.get('ProductId') or 'n/a'})")
        strain, fbody = line_strain(fl, live, brand, desc_n, strains)
        strain_bearing = bool(sib.get("Strain"))
        if sib.get("Flavor"):
            flags.append("FLAVOR_TO_SET")
        if strain_bearing and not strain:
            row.update(verdict="STRAIN_MISSING", action="STOP - mint the Strain record first (R101)",
                       strain_record="MISSING", sibling_reason=reason + "; no Strain record named in the line")
            row["flags"] = ";".join(flags)
            out.append(row)
            continue
        s = strain or ""
        direction = tag_overrides.get(str(ln.get("line_no", "")).strip()) or tag_overrides.get("*")
        decision, why = (direction, f"`{direction}` by the business's direction") if direction else \
            decision_tag(members, prefix, active_tag, new_line_tag)
        reason += f"; tag {why}"
        ot = new_ot(sib, fbody or s, by_body=bool(fbody)) if s else ""
        if s and not ot:
            flags.append("OT_TEMPLATE_MISS")
        row.update(verdict="NEW_ITEM_WITH_SIBLING", action="CREATE - copy item", sibling_reason=reason,
                   strain_record="LIVE" if s else "", create_name_FINAL=new_name(sib, fbody or s) if s else "",
                   strain=s, strain_type=(strains.get(s) or {}).get("type", ""),
                   strain_id=(strains.get(s) or {}).get("id", ""), online_title=ot,
                   online_desc_chars=str(len(sib.get("Online description") or "")),
                   online_desc_source="sibling template - replace the strain paragraph (platform KB sourcing chain)",
                   image_state=("sibling image carried - keep only if generic brand art (platform KB Images)"
                                if sib.get("Image URL") else "0 images (NO_ECOM_IMAGE - a human supplies art)"),
                   tags=copy_tags(sib, drop_tags, prefix, decision))
        row["flags"] = ";".join(flags)
        out.append(row)
    return out, defects


def load_strains(path):
    hdr, rows = read_csv(path, STRAINS_REQUIRED, "strains")
    idc = next((c for c in ("StrainId", "Strain id", "Id", "ID") if c in hdr), None)
    return {r["Strain name"]: {"type": r.get("Type", ""), "id": r.get(idc, "") if idc else ""}
            for r in rows if r.get("Strain name")}


def load_exports(argv, pointers):
    active, retired, strains = get_flag(argv, "--active"), get_flag(argv, "--retired"), get_flag(argv, "--strains")
    xdir = get_flag(argv, "--exports-dir") or (pointers["intake"]["Exports dir"] if pointers and not active else None)
    mr = get_flag(argv, "--min-rows")
    mr = int(mr) if mr else None
    if not active:
        if not xdir:
            abort("pass --active (+ --retired, --strains) or --exports-dir with --min-rows")
        print(f"picking the freshest exports in {xdir}")
        active = freshest(xdir, ["*catalog*active*.csv", "*catalog*.csv"], mr, CATALOG_REQUIRED, exclude=["*retired*"])
        if not retired:
            retired = freshest(xdir, ["*catalog*retired*.csv", "*retired*.csv"],
                               int(get_flag(argv, "--min-rows-retired", "1")), CATALOG_REQUIRED)
        if not strains:
            strains = freshest(xdir, ["*strain*.csv"], mr, STRAINS_REQUIRED)
    if not strains:
        abort("the Strains export is required (--strains): without it STRAIN_MISSING would fire on every new item")
    _, a = read_csv(active, CATALOG_REQUIRED, "active export")
    r = []
    if retired:
        _, r = read_csv(retired, CATALOG_REQUIRED, "retired export")
    if a and COL_RETIRED in a[0]:
        r = r + [x for x in a if x.get(COL_RETIRED) == "Yes"]
        a = [x for x in a if x.get(COL_RETIRED) != "Yes"]
    return (active, retired, strains), a, r, load_strains(strains)


def tag_options(argv, ptr):
    """(new-line tag, Active tag): the flag, else the tenant pointer, else the generic default."""
    pv = lambda k: (ptr or {}).get("intake", {}).get(k)  # noqa: E731
    return (get_flag(argv, "--new-line-tag") or pv("New line tag") or DEFAULT_NEW_LINE_TAG,
            get_flag(argv, "--active-tag") or pv("Active tag") or DEFAULT_ACTIVE_TAG)


def parse_overrides(specs, new_line_tag, dead_tag, prefix=ITEM_PREFIX):
    """`<line_no>=<tag>` / `*=<tag>` -> {key: tag}. A direction must be an item decision tag; the new-line
    tag and the dead tag are not a sibling copy's to carry (R83, R81): ABORT, never a silent pass."""
    out = {}
    for spec in specs:
        k, sep, v = spec.partition("=")
        k, v = k.strip(), v.strip()
        if not sep or not k or not v.startswith(prefix) or v in (new_line_tag, dead_tag):
            abort(f"--tag-override {spec!r}: want <line_no>=<{prefix}tag> (not the new-line or dead tag)")
        out[k] = v
    return out


def main(argv):
    if "--selftest" in argv:
        return selftest()
    lines_p = get_flag(argv, "--lines")
    if not lines_p:
        print(__doc__)
        return EXIT_ABORT
    tenant = get_flag(argv, "--tenant")
    ptr = None
    if tenant:
        import intake_pointers
        ptr = intake_pointers.load(tenant)
    _, lines = read_csv(lines_p, LINES_REQUIRED, "--lines")
    paths, active, retired, strains = load_exports(argv, ptr)
    new_line_tag, active_tag = tag_options(argv, ptr)
    overrides = parse_overrides(get_all(argv, "--tag-override"), new_line_tag, get_flag(argv, "--dead-tag", DEFAULT_DEAD_TAG))
    rows, defects = match(lines, active, retired, strains, get_flag(argv, "--brand"), new_line_tag,
                          get_flag(argv, "--dead-tag", DEFAULT_DEAD_TAG), get_all(argv, "--drop-tag"),
                          active_tag, ITEM_PREFIX, overrides)
    out_dir = get_flag(argv, "--out-dir") or (ptr["intake"]["Intake dir"] if ptr else os.path.dirname(os.path.abspath(lines_p)))
    tslug = get_flag(argv, "--slug") or (slug(os.path.basename(os.path.dirname(os.path.abspath(tenant)))) if tenant else "tenant")
    first = next((ln for ln in lines if not ln.get("order_level_kind")), lines[0] if lines else {})
    stem = f"{tslug}-intake-{slug(first.get('vendor'))}-{slug(first.get('invoice_no'))}-{first.get('invoice_date') or 'undated'}"
    out = next_version(out_dir, stem)
    write_csv(out, V3_COLS, rows)
    print("inputs: " + " | ".join(f"{k} {os.path.basename(p) if p else 'NONE'} ({n})" for k, p, n in
                                  zip(("active", "retired", "strains"), paths, (len(active), len(retired), len(strains)))))
    if not retired:
        print("WARNING: no retired rows - RETIRED_MATCH cannot fire; a zero below proves nothing for it")
    print(f"{'verdict':24} count")
    for v in VERDICTS:
        print(f"{v:24} {sum(1 for r in rows if r['verdict'] == v)}")
    print(f"\n{'flag':18} {'rule':5} {'class':7} count")
    for f, rule, cls in FLAGS:
        n = len(defects) if f == "BAD_LINE" else sum(1 for r in rows if f in r.get("flags", "").split(";"))
        print(f"{f:18} {rule:5} {cls:7} {n}")
    for d in defects:
        print("   " + d)
    print(f"wrote {out} ({len(rows)} rows)")
    return EXIT_DEFECT if defects else EXIT_OK


def _item(sku, product, **kw):
    r = {c: "" for c in CATALOG_REQUIRED}
    p = product.split(" | ")
    r.update({"SKU": sku, "ProductId": kw.pop("pid", ""), "Product": product, "Brand": p[0], "Category": kw.pop("cat", "Pre-Roll Single"),
              "Product grams": p[3] if len(p) > 3 else "", "Cost": "4.5", "Price": "11", "Strain": p[2] if len(p) > 2 else "",
              "Online title": f"{p[2]} Pre-Roll {p[3]}" if len(p) > 3 else "", "Vendor": kw.pop("vendor", "Example Wholesale")})
    r.update(kw)
    return r


def _aborts(fn):
    so, se = sys.stdout, sys.stderr
    try:
        with open(os.devnull, "w") as dn:
            sys.stdout = sys.stderr = dn
            fn()
    except SystemExit as e:
        return e.code == EXIT_ABORT
    finally:
        sys.stdout, sys.stderr = so, se
    return False


def selftest():
    t = Selftest("intake_match")
    active = [_item("1", "Acme | Pre-Roll | Blue Dream | 1g", pid="11", **{"Image URL": "a.jpg"}),
              _item("2", "Acme | Pre-Roll | OG Kush | 1g", pid="12"),
              _item("3", "Acme | Pre-Roll | Old Stock | 1g", pid="13", Tags=DEFAULT_DEAD_TAG, **{"Image URL": "d.jpg"})]
    retired = [_item("9", "Acme | Pre-Roll | Sour Diesel | 1g", pid="9")]
    strains = {n: {"type": "Hybrid", "id": ""} for n in ("Blue Dream", "OG Kush", "Sour Diesel", "Gelato")}

    def run(desc, vendor="Example Wholesale", act=active, ret=retired, st=strains):
        rows, _ = match([{"description": desc, "vendor": vendor, "units_total": "10", "unit_cost": "4.5"}], act, ret, st)
        return rows[0]

    t.check("EXISTS fires", run("Acme Blue Dream preroll 1g")["verdict"] == "EXISTS")
    t.check("QUIET: EXISTS needs the grams", run("Acme Blue Dream preroll 2g")["verdict"] != "EXISTS")
    t.check("dose_of: single = first weight", dose_of("Acme Blue Dream Pre-Roll 1g") == 1.0)
    t.check("dose_of: pack total = per-piece x count", dose_of("Acme Blue Dream Pre-Roll 0.5g x 3pk") == 1.5)
    t.check("dose_of: count before weight", dose_of("Acme Blue Dream 3-pack Pre-Roll 0.5g") == 1.5)
    t.check("dose_of: 10 ct", dose_of("Acme Blue Dream Pre-Roll 0.5g 10 ct") == 5.0)
    t.check("dose_of: printed total wins", dose_of("Acme Blue Dream Pre-Roll 1.5g (3 x 0.5g)") == 1.5)
    t.check("dose_of: mg dose, no pack", dose_of("Acme Gummy 100mg 10pk") == 0.1 * 10)
    t.check("dose_of: '1 x' is not a pack", dose_of("Acme Blue Dream 1 x 3.5g") == 3.5)
    t.check("pack_count_of: none on a single", pack_count_of("Acme Blue Dream Pre-Roll 1g") is None)
    t.check("RETIRED_MATCH fires", run("Acme Sour Diesel pre-roll 1g")["verdict"] == "RETIRED_MATCH")
    r = run("Acme Gelato preroll 1g")
    t.check("NEW_ITEM_WITH_SIBLING fires", r["verdict"] == "NEW_ITEM_WITH_SIBLING", r["verdict"])
    t.check("sibling prefers the image over the newer id", r["copy_source_sku"] == "1", r["copy_source_sku"])
    t.check("QUIET: a dead record is never the sibling", r["copy_source_sku"] != "3")
    t.check("final name swaps segment 3 only", r["create_name_FINAL"] == "Acme | Pre-Roll | Gelato | 1g", r["create_name_FINAL"])
    t.check("online title swaps the strain only", r["online_title"] == "Gelato Pre-Roll 1g", r["online_title"])
    t.check("a copy of an untagged lane reads the Active tag, never the new-line tag (R96, R83)",
            r["tags"] == DEFAULT_ACTIVE_TAG, r["tags"])
    t.check("STRAIN_MISSING fires", run("Acme Mystery Haze preroll 1g")["verdict"] == "STRAIN_MISSING")
    t.check("NEW_CATEGORY: a form word no catalog item carries cannot place the line",
            run("Acme Gelato cart 0.5g")["verdict"] == "NEW_CATEGORY")
    tagged = [dict(x, Tags=x["Tags"] or "ITM - Protect") for x in active]
    t.check("a copy takes the ONE tag every lane member carries (R96)",
            run("Acme Gelato preroll 1g", act=tagged)["tags"] == "ITM - Protect")
    mixed = [dict(x, Tags=("ITM - Discontinue" if x["SKU"] == "2" else x["Tags"] or "ITM - Protect")) for x in active]
    t.check("a mixed lane reads the Active tag", run("Acme Gelato preroll 1g", act=mixed)["tags"] == DEFAULT_ACTIVE_TAG)
    under_qc = [dict(x, Tags=x["Tags"] or DEFAULT_NEW_LINE_TAG) for x in active]
    t.check("QUIET: a lane still under new-line QC never passes the new-line tag to a copy",
            run("Acme Gelato preroll 1g", act=under_qc)["tags"] == DEFAULT_ACTIVE_TAG)
    keep = [dict(x, Tags=("Status - Live, " + (x["Tags"] or "ITM - Protect"))) for x in active]
    t.check("non-decision tags ride the copy; the decision tag is replaced, not added",
            run("Acme Gelato preroll 1g", act=keep)["tags"] == "ITM - Protect, Status - Live")
    rows_o, _ = match([{"description": "Acme Gelato preroll 1g", "vendor": "x", "units_total": "1", "unit_cost": "4.5",
                        "line_no": "3"}], tagged, retired, strains, tag_overrides={"3": "ITM - Discontinue"})
    t.check("the business's direction beats the lane's tag", rows_o[0]["tags"] == "ITM - Discontinue", rows_o[0]["tags"])
    rows_o, _ = match([{"description": "Acme Gelato preroll 1g", "vendor": "x", "units_total": "1", "unit_cost": "4.5",
                        "line_no": "4"}], tagged, retired, strains, tag_overrides={"3": "ITM - Discontinue"})
    t.check("QUIET: a direction for another line leaves this one on its lane's tag", rows_o[0]["tags"] == "ITM - Protect")
    t.check("FIRES: a direction naming the new-line tag ABORTs",
            _aborts(lambda: parse_overrides(["3=" + DEFAULT_NEW_LINE_TAG], DEFAULT_NEW_LINE_TAG, DEFAULT_DEAD_TAG)))
    t.check("QUIET: a decision-tag direction parses",
            parse_overrides(["*=ITM - Protect"], DEFAULT_NEW_LINE_TAG, DEFAULT_DEAD_TAG) == {"*": "ITM - Protect"})
    vape = active + [_item("7", "Acme | Live Resin Cart | Blue Dream | 1g", pid="17", cat="Vape",
                           **{"Master category": "Vape", "Image URL": "c.jpg", "Tags": "ITM - Protect"}),
                     _item("8", "Bolt | Gummy | Mango | 100mg", pid="18", cat="Gummy", vendor="Bolt Wholesale",
                           **{"Master category": "Edible"})]
    r = run("Acme Gelato cart 0.5g", act=vape)
    t.check("NEW_PL: a new line under a known brand is a CREATE from the brand's nearest item in the MC",
            r["verdict"] == "NEW_PL" and r["action"].startswith("CREATE") and r["copy_source_sku"] == "7",
            f"{r['verdict']} {r['action']} {r['copy_source_sku']}")
    t.check("NEW_PL carries the new-line tag and drops the nearest item's decision tag (R83)",
            r["tags"] == DEFAULT_NEW_LINE_TAG, r["tags"])
    t.check("NEW_PL raises NEW_LINE_FIELDS (STOP) for the inherited lane", "NEW_LINE_FIELDS" in r["flags"].split(";"))
    t.check("NEW_PL: grams from the line, Cost from the invoice, a name draft in the nearest item's form",
            r["lane_ProductGrams"] == "0.5g" and r["lane_Cost"] == "4.5"
            and r["create_name_FINAL"] == "Acme | Live Resin Cart | Gelato | 0.5g",
            f"{r['lane_ProductGrams']} {r['lane_Cost']} {r['create_name_FINAL']!r}")
    r = run("Acme Mango gummy 100mg 10pk", act=vape)
    t.check("NEW_CATEGORY: the MC is read (Edible) but the brand carries no item in it",
            r["verdict"] == "NEW_CATEGORY" and "Edible" in r["sibling_reason"], f"{r['verdict']} {r['sibling_reason']}")
    t.check("NEW_PL: a strain-bearing new line with no Strain record is STRAIN_MISSING",
            run("Acme Mystery Haze cart 0.5g", act=vape)["verdict"] == "STRAIN_MISSING")
    t.check("NEW_BRAND fires", run("Zed Gelato preroll 1g", vendor="Other Co")["verdict"] == "NEW_BRAND")
    t.check("QUIET: the vendor names a single brand", run("Gelato preroll 1g")["verdict"] == "NEW_ITEM_WITH_SIBLING")
    t.check("DOSE_UNREAD fires", "DOSE_UNREAD" in run("Acme Gelato preroll")["flags"])
    two = active + [_item("4", "Acme | Pre-Roll | Blue Dream | 1g", pid="14")]
    t.check("AMBIGUOUS_MATCH fires on two equal items", "AMBIGUOUS_MATCH" in run("Acme Blue Dream preroll 1g", act=two)["flags"])
    _, d = match([{"description": "Acme Blue Dream preroll 1g", "vendor": "x", "units_total": "", "unit_cost": "4.5"}],
                 active, retired, strains)
    t.check("FIRES: BAD_LINE on a line with no units", len(d) == 1)
    t.check("v3 has 54 columns (45 + 7 + parse_source + package_id)", len(V3_COLS) == 54 and len(V2_COLS) == 45
            and V3_COLS[-2:] == ["parse_source", "package_id"], str(len(V3_COLS)))
    r = match([{"description": "Acme Blue Dream preroll 1g", "vendor": "x", "units_total": "1", "unit_cost": "4.5",
                "parse_source": "text:x.md"}], active, retired, strains)[0][0]
    t.check("parse_source carried from the line", r["parse_source"] == "text:x.md", r["parse_source"])
    r = match([{"description": "Acme Blue Dream preroll 1g", "vendor": "x", "units_total": "1", "unit_cost": "4.5",
                "package_id": "PKG-A;PKG-B"}], active, retired, strains)[0][0]
    t.check("package_id carried from the line", r["package_id"] == "PKG-A;PKG-B", r["package_id"])
    t.check("QUIET: package_id blank when the line has none", run("Acme Blue Dream preroll 1g")["package_id"] == "")
    aio = active + [_item("5", "Acme | Distillate AIO | Lime Sorbet | 2g | Pocket Pro", pid="15", cat="Vape")]
    r = run("Acme | Lime Sorbet | Flavor Line | Pocket PRO | 2.0g | Hybrid", act=aio)
    t.check("FORM_UNREAD: no form word read, ONE brand + body + grams hit -> EXISTS",
            r["verdict"] == "EXISTS" and "FORM_UNREAD" in r["flags"].split(";") and r["copy_source_sku"] == "5",
            f"{r['verdict']} {r['flags']} {r['copy_source_sku']}")
    two_aio = aio + [_item("6", "Acme | Distillate Cart | Lime Sorbet | 2g", pid="16", cat="Vape")]
    r = run("Acme | Lime Sorbet | Flavor Line | Pocket PRO | 2.0g | Hybrid", act=two_aio)
    t.check("QUIET: FORM_UNREAD off on two candidates -> an unplaced line stays a STOP (NEW_CATEGORY)", r["verdict"] == "NEW_CATEGORY" and "FORM_UNREAD" not in r["flags"],
            f"{r['verdict']} {r['flags']}")
    r = run("Acme | Lime Sorbet | Flavor Line | Cart | 2.0g | Hybrid", act=aio)
    t.check("QUIET: FORM_UNREAD off when the line names another form word (cart) -> a STOP (NEW_CATEGORY)",
            r["verdict"] == "NEW_CATEGORY" and "FORM_UNREAD" not in r["flags"], f"{r['verdict']} {r['flags']}")
    t.check("QUIET: FORM_UNREAD off on a full match", "FORM_UNREAD" not in run("Acme Blue Dream preroll 1g")["flags"])
    t.check("ratio_key: cannabinoid order + case are unordered",
            ratio_key("1:1 CBD:THC") == ratio_key("1:1 THC:CBD") and ratio_key("1:1:1 THC:CBC:CBG") == ratio_key("1:1:1 THC:CBG:CBC")
            and ratio_key("1:1 THC:THCv") == ratio_key("1:1 THC:THCV"))
    t.check("QUIET: ratio_key keeps the counts paired (2:1 CBD:THC != 2:1 THC:CBD)",
            ratio_key("2:1 CBD:THC") != ratio_key("2:1 THC:CBD") and ratio_key("10mg x 10pk") is None)
    fl = flavor_led("Acme | (I) Sour Cherry Gummies 1:1 CBD:THC | Edibles | 100mg", ["Gummies"])
    t.check("flavor_led: letter -> type, flavor minus form word and ratio", fl == ("Indica", "Sour Cherry", ratio_key("1:1 THC:CBD")), str(fl))
    t.check("QUIET: flavor_led off a line with no leading strain letter", flavor_led("Acme Sour Cherry Gummies (I)", ["Gummies"]) is None)
    return t.done()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
