"""intake_match.py - invoice lines vs the catalog: one verdict per product line, the sibling to copy
from, and the intake CSV v5: 56 columns = the 45 v2 columns + verdict, sibling_reason, flags,
landed_unit_cost, po_line_ref, expiry_date, approved + parse_source (which source intake_parse read:
pypdf / pdftotext / text / lines, so a certify reader knows the provenance) + package_id (the
package tag(s) printed on the invoice line, `;`-joined; blank when the layout prints none)
+ unretire_set (v4: the retired items of a product line that comes back WHOLE, `;`-joined ProductIds,
SKU where the export has none; blank unless the row un-retires a line - R101)
+ image_source (v5: the create step's image-sourcing record, read by the notice - `sourced: <url>` /
`not found: <where the lane looked>` / `not attempted: <why>`; blank here, written at the create step).
`package_id` is optional on the lines CSV: a lines file written before the column reads blank.

  python intake_match.py --lines <lines.csv> --active <catalog-active.csv> --retired <catalog-retired.csv>
                         --strains <strains.csv> [--categories <categories.csv>] [--brands <brands.csv>]
                         [--tenant <CLAUDE.md>] [--out-dir <dir>] [--slug <name>]
  python intake_match.py --lines <lines.csv> --exports-dir <dir> --min-rows <n> [--min-rows-retired <n>] ...
  options: --brand "<Catalog Brand>"   force the brand for every line (a single-brand invoice)
           --line-brand <line_no>=<Brand>   the brand of ONE line, as the operator spells it (`*=` for every
                                       line): a catalog brand matches under it; a Brand record with no item
                                       is a NEW_PL copy; a name no record carries is a NEW_BRAND create (R121)
           --line-category <line_no>=<Category>  the Category of ONE line the matcher cannot read from its
                                       words (`*=` for every line); checked against the categories export
           --strain-type <line_no>=<Type>@<source>  the Strain Type the lane researched for a line whose
                                       assets do not print it (R33 chain); the source rides the STOP
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
The categories export (`Master category`, `Category`, ...) is the TAXONOMY `NEW_CATEGORY` reads; the brands
export (`Display name`, ...) says whether a Brand record exists with no item. Both are picked from
`--exports-dir` when present (`*categor*.csv`, `*brand*.csv`); without one the catalog's own values stand
in and the run says so. Every column read is required; a missing one ABORTs (exit 2).

Verdicts (one per product line; R101 = Copy-from-sibling is the create path; a product line we carried
before comes back WHOLE by un-retiring; any other new line duplicates the closest item by subcategory,
any brand; the lane creates a new brand; the operator STOP is a Category or Master category the
taxonomy lacks):
  EXISTS                  brand + body (name segment 3) + grams + form match ONE active item; or
                          brand + body + grams match ONE active item, the form test alone fails and
                          the line names NO form word at all -> EXISTS + FORM_UNREAD.
                          A flavor-led line `(S|I|H) <Flavor> <Form>[ <ratio>]` meets body
                          `<Flavor>[ <Effect>] (<type or ratio>)` by layout (`flavor_led`); the ratio
                          compares unordered (`ratio_key`), for matching only - never for a create name
  RETIRED_MATCH           the same match, on a retired item only -> UN-RETIRE: the item's product line
                          (the R50 lane) comes back whole; `unretire_set` lists every retired member;
                          Cost from the invoice, Price confirmed current, tag = the Active tag
  NEW_ITEM_WITH_SIBLING   no match; the R50 lane (Brand + Category + grams + Form word) has an active
                          member, and the strain is a Strain record -> copy from the sibling. When only a
                          RETIRED lane fits, the line we carried before comes back: the copy source is
                          the retired member, flagged UNRETIRE_FIRST, `unretire_set` = the whole lane
  STRAIN_MISSING          as above, but the lane is strain-bearing and no Strain record is named, or the
                          line's Strain Type conflicts with the record's (STRAIN_TYPE_CONFLICT)
  NEW_PL                  the brand exists (an item or a Brand record); no lane fits -> CREATE from the
                          brand's NEAREST active item in the Master category (same form word first,
                          then the closest grams); with none, the CLOSEST active item by subcategory in
                          the whole catalog (same Global SubCategory, then Category, then Master
                          category), any brand (CROSS_BRAND_COPY); tagged with the new-line tag (R83).
                          A line whose Category cannot be read has no copy source yet (CATEGORY_UNREAD)
  NEW_CATEGORY            the line's Category or Master category is ABSENT from the taxonomy (the
                          categories export) -> STOP: a new category is a configuration decision
  NEW_BRAND               no catalog brand, Brand record or direction names the line's brand -> CREATE:
                          the Brand record first (a live Global Brand read, R30; display name per R121,
                          as the operator spells it), then the line as a NEW_PL copy. With no spelling
                          (BRAND_NAME_UNREAD) the row has no brand yet and is never created as it stands
For EXISTS / RETIRED_MATCH the copy_source_* columns carry the MATCHED record, not a copy source.

Sibling = the lane member WITH an image first, then the newest ProductId, then the lowest SKU.
Lane fields (lane_*) are the sibling's own values: the copy inherits them. A NEW_PL row's lane fields are
the source item's, except Product grams (the line's dose) and Cost (the invoice unit cost); a CROSS-BRAND
source also gives up Brand (the line's), Vendor (the invoice's), Price (blank: the business sets it),
Online title / description and image (residue the certify diff proves gone).

Decision tag (R96): a sibling copy carries the ONE item-namespace tag every active member of its lane
carries; a mixed lane, or a member with none, reads the Active tag. The new-line tag is never copied onto
a sibling copy (R83). `--tag-override` is the business's direction and beats both. Every other
item-namespace tag the sibling carries is dropped from the copy. Anything brought back from retirement,
and a copy of it, reads the Active tag.

Flag table (flags column; none fails the run):
  AMBIGUOUS_MATCH       R101  STOP  two or more items match equally; the operator picks
  FORM_UNREAD           R101  STOP  EXISTS read without the form word: the line names no form word of
                                    the catalog (any brand's name segment 2, or a FORM_SYNONYMS token),
                                    and brand + body + grams hit exactly ONE active item.
                                    The operator confirms the matched item before receiving. Two or more
                                    such items, or a line that names another form word, is not EXISTS.
                                    No vendor word is added to FORM_SYNONYMS for this: the test is generic.
  LANE_AMBIGUOUS        R50   STOP  two or more lanes fit equally; no sibling chosen
  DOSE_UNREAD           R50   STOP  no grams / mg read from the line; the lane test ran without it
  FLAVOR_TO_SET         R101  STOP  the sibling carries a Flavor: set the new item's own at create
  OT_TEMPLATE_MISS      R101  INFO  the sibling's Online title does not contain its strain; write it by hand
  NEW_LINE_FIELDS       R101  STOP  a NEW_PL copy inherits a different lane: confirm or edit the name, Price,
                                    Flower equiv, Servings per Unit and Category / Type in the lane cells
  UNRETIRE_FIELDS       R101  STOP  RETIRED_MATCH: un-retire every item in `unretire_set`; Cost = the
                                    invoice, Price confirmed current, tag = the Active tag, on each
  UNRETIRE_FIRST        R101  STOP  the copy source is RETIRED: un-retire the lane (`unretire_set`) and read
                                    it back BEFORE this copy; the copy then reads the Active tag
  CROSS_BRAND_COPY      R101  STOP  the copy source is another brand's item: Brand, Vendor, name, Strain /
                                    Flavor, dose, Cost, Price, Online title / description and image are all
                                    rewritten; certify proves the source brand left no residue
  CATEGORY_UNREAD       R101  STOP  the line names no form word the catalog carries, so its Category is
                                    unknown: name it (`--line-category <line_no>=<Category>`) and re-run;
                                    the row has no copy source until then
  CATEGORY_DIRECTED     R33   STOP  the Category came from the operator's direction, not the line's words:
                                    confirm it against the vendor's own words
  CATEGORY_INFERRED     R33   STOP  the Category came from another brand's item and names a route word the
                                    line does not print (rosin / distillate ..., or resin beside an added-terpene
                                    mention): a vendor fact,
                                    confirmed through the R33 chain, never assumed. The feedstock word
                                    (live / cured) is not a route word: OIL_LIVE_DEFAULT decides it
  ROUTE_RESIN_DEFAULT   R33   INFO  a cross-brand placement whose only unprinted Category word is `Resin`, on a
                                    line that mentions no added terpenes (`terp`, `botanical`, `CDT`): Resin by
                                    default (Adam 2026-10-08). A terpene mention keeps CATEGORY_INFERRED (STOP)
  OIL_LIVE_DEFAULT      R79   INFO  the Category sits on a Live / Cured pair the taxonomy carries and the line
                                    prints neither word: the Live Category by default (Adam 2026-10-08). A
                                    line that prints `Cured` takes the Cured Category, never a note. Applies
                                    to a NEW_PL placement and to a Live / Cured lane tie
  BRAND_NAME_UNREAD     R121  STOP  NEW_BRAND with no spelling: pass `--line-brand <line_no>=<Display name>`
                                    (the market's word, R121) and re-run; nothing is created as it stands
  STRAIN_TYPE_CONFLICT  R128  STOP  the line's Strain Type does not agree with the named Strain record's (a
                                    coarser `Hybrid` agrees with a leaner `Indica-Hybrid` / `Sativa-Hybrid`).
                                    The row lists the record's items. Within the brand (the line's brand
                                    carries the record, or nobody does) it is a vendor ask, never a new
                                    record: our own text and public sources decide whether the doc or the
                                    record is wrong. Only a record that OTHER brands alone carry offers a NEW
                                    record `<Name> (<Type>)`: Strain names are unique (R26)
  STRAIN_TYPE_RESEARCHED R33  INFO  the Strain Type came from `--strain-type` with its source; it rides the
                                    STOP as a finding with a source, never as a fact the line printed
  BAD_LINE              R103  DEFECT a product line with no units or unit cost (exit 1)
"""
import os
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from intake_common import (CATALOG_REQUIRED, COL_RETIRED, DEFAULT_ACTIVE_TAG, DEFAULT_DEAD_TAG,  # noqa: E402
                           DEFAULT_NEW_LINE_TAG, ITEM_PREFIX, BRANDS_REQUIRED, CATEGORIES_REQUIRED,
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
V4_NEW = ["unretire_set"]
V4_COLS = V3_COLS + V4_NEW
V5_NEW = ["image_source"]   # the create step's image-sourcing record (ruled 2026-10-08); the notice reads it
V5_COLS = V4_COLS + V5_NEW
INTAKE_COLS = V5_COLS   # what this script writes; every reader requires V3_COLS, so a v3 or v4 file still reads
VERDICTS = ["EXISTS", "RETIRED_MATCH", "NEW_ITEM_WITH_SIBLING", "STRAIN_MISSING", "NEW_PL", "NEW_CATEGORY", "NEW_BRAND"]
FLAGS = [("AMBIGUOUS_MATCH", "R101", "STOP"), ("FORM_UNREAD", "R101", "STOP"), ("LANE_AMBIGUOUS", "R50", "STOP"),
         ("DOSE_UNREAD", "R50", "STOP"), ("FLAVOR_TO_SET", "R101", "STOP"), ("OT_TEMPLATE_MISS", "R101", "INFO"),
         ("NEW_LINE_FIELDS", "R101", "STOP"), ("UNRETIRE_FIELDS", "R101", "STOP"), ("UNRETIRE_FIRST", "R101", "STOP"),
         ("CROSS_BRAND_COPY", "R101", "STOP"), ("CATEGORY_UNREAD", "R101", "STOP"), ("CATEGORY_DIRECTED", "R33", "STOP"),
         ("CATEGORY_INFERRED", "R33", "STOP"), ("OIL_LIVE_DEFAULT", "R79", "INFO"), ("ROUTE_RESIN_DEFAULT", "R33", "INFO"), ("BRAND_NAME_UNREAD", "R121", "STOP"),
         ("STRAIN_TYPE_CONFLICT", "R128", "STOP"), ("STRAIN_TYPE_RESEARCHED", "R33", "INFO"),
         ("BAD_LINE", "R103", "DEFECT")]
LANE_MAP = {"lane_Category": "Category", "lane_Type": "Type", "lane_IsCannabis": "Is cannabis",
            "lane_MasterCategory": "Master category", "lane_GlobalCategory": "Global Category",
            "lane_GlobalSubCategory": "Global SubCategory", "lane_ProductGrams": "Product grams",
            "lane_FlowerEquiv": "Flower equiv", "lane_ServingsPerUnit": "Servings per Unit", "lane_Cost": "Cost",
            "lane_Price": "Price", "lane_Vendor": "Vendor", "lane_Brand": "Brand", "lane_CBDContent": "CBD content",
            "lane_Flavor": "Flavor", "lane_OnlineAvailable": "Is available online"}

# Vendor vocabulary -> one canonical token, so `preroll`, `pre-roll` and `Pre-Roll` compare equal.
# Industry words only (a 510-thread cartridge is a cart everywhere); never a vendor's own word.
FORM_SYNONYMS = {
    "preroll": ["pre roll", "pre rolls", "prerolls", "joint", "joints", "pr"],
    "cart": ["cartridge", "cartridges", "carts", "vape cart", "vape carts", "510", "510 thread"],
    "aio": ["all in one", "disposable", "disposables"],
    "gummy": ["gummies"],
    "tincture": ["tinctures"],
    "capsule": ["capsules", "caps"],
    "chocolate": ["chocolates"],
}
CORP = {"llc", "inc", "co", "corp", "ltd", "company", "the"}
STRAIN_TYPES = ("Sativa", "Indica", "Hybrid", "CBD")


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


def record_key(r):
    """The key `unretire_set` prints: ProductId, or the SKU on the 26-column shape that has none."""
    return (r.get("ProductId") or "").strip() or (r.get("SKU") or "").strip()


STRAIN_LETTERS = {"s": "Sativa", "i": "Indica", "h": "Hybrid"}
_LEAD_TYPE_RE = re.compile(r"(?:^|\|)\s*\((sativa|indica|hybrid|[sih])\)\s+([^|]+)", re.I)
_TYPE_WORD_RE = re.compile(r"(?<![a-z])(sativa|indica|hybrid)(?![a-z])|\(([sih])\)", re.I)
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


def line_type(desc):
    """The Strain Type a line prints (`Sativa`, `(S)`, ...), else ''. A printed word, never a guess."""
    m = _TYPE_WORD_RE.search(desc or "")
    if not m:
        return ""
    return m.group(1).capitalize() if m.group(1) else STRAIN_LETTERS[m.group(2).lower()]


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


def flavor_cell_hit(r, desc_n, stated, rkey=None):
    """A FLAVORED item (its Flavor cell is set) is the line's item when the line prints that Flavor and states no
    Strain Type that contradicts the item's (`S'mores Cheesecake` + `Hybrid` meets a Hybrid `S'mores Cheesecake (THC)`
    whose Strain Type is Hybrid). The body's own parenthesis is not required on the line: a vendor prints the
    flavor, not our composition paren."""
    flav = (r.get("Flavor") or "").strip()
    if not flav or not has_phrase(desc_n, flav):
        return False
    if ratio_key(r.get("Strain") or "") != rkey:   # a ratio item and a ratio line agree on the ratio, or neither prints one
        return False
    if not stated:
        return True
    return norm(stated) in (norm(r.get("Strain Type")), norm(r.get("Strain")))


def body_hits(rows, brand, desc_n, dtoks, g, fl=None, stated="", rkey=None):
    hits = []
    for r in rows:
        if norm(r.get("Brand")) != norm(brand):
            continue
        body = body_of(r.get("Product")) or r.get("Strain", "")
        if not body or not (body_hit(desc_n, body, fl) or (fl is None and flavor_cell_hit(r, desc_n, stated, rkey))):
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


def find_strain(desc_wo_brand_n, strains, flavored=False, stated="", rkey=None):
    """The Strain record the line names: the longest record phrase in the line, never a bare Strain Type word
    (`Indica` is a type the line prints, not a smokable's cultivar). On a FLAVORED lane (the source carries a
    Flavor) the type record IS the Strain when the line states the type, and it wins over any other phrase:
    the body is then `<Flavor> (<Type>)`, which the operator completes (FLAVOR_TO_SET). A line that prints a
    RATIO takes the ONE record with that ratio key (R26), never a cannabinoid word out of the ratio (`THC`)."""
    if rkey is not None:
        cands = [n for n in strains if ratio_key(n) == rkey]
        return cands[0] if len(cands) == 1 else None
    names = [n for n in strains if has_phrase(desc_wo_brand_n, n)]
    if flavored and stated and stated in strains:
        return stated
    real = [n for n in names if n not in STRAIN_TYPES]
    return max(real, key=len) if real else None


def line_strain(fl, live, brand, desc_n, strains, flavored=False, stated="", desc=None):
    """(Strain record, name body or None) a create carries. A flavor-led line reads its record from its
    layout only (`flavor_led_strain`): a ratio or stray token is never taken for a strain name."""
    if fl:
        return flavor_led_strain(fl, live, brand, strains)
    return find_strain(" ".join(desc_n.replace(norm(brand), " ").split()), strains, flavored, stated,
                       ratio_key(desc if desc is not None else desc_n)), None


def body_known(strain, fbody):
    """A name can be drafted when the body is known: a flavor-led body, or a Strain that is a cultivar / ratio
    record. A bare type record (`Hybrid`) on a flavored lane leaves the body `<Flavor> (<Type>)` to the operator."""
    return bool(fbody) or (bool(strain) and strain not in STRAIN_TYPES)


def new_strain_name(strain, typ):
    """The new record's name for a REAL Type difference (R26): Dutchie Strain names are unique, so it is
    `<Name> (<Type>)` - the bare name stays the existing record's (precedent: `Gelato (Indica)`)."""
    return f"{(strain or '').strip()} ({(typ or '').strip()})"


STRAIN_SOT_RULE = "R128"   # the Strain Type source-of-truth rule (minted 2026-10-08)
LEANERS = ("indica-hybrid", "sativa-hybrid")


def type_agrees(rec, stated):
    """A stated Type agrees with the record's when equal, or when it is the coarser `Hybrid` against a
    leaner (`Indica-Hybrid`, `Sativa-Hybrid`): the Global Catalog files leaners as Hybrid (STRAIN_SOT_RULE)."""
    return norm(rec) == norm(stated) or (norm(stated) == "hybrid" and norm(rec) in {norm(x) for x in LEANERS})


def strain_conflict(strain, strains, stated, everything, brand=None):
    """(record type, stated type, items on the record, other brands only) when the line states a Strain
    Type that does not agree with the named record's (R26 + STRAIN_SOT_RULE). `other brands only` = the
    record carries items and none is the line's brand: only then is a new `<Name> (<Type>)` record on the
    table; within a brand a name has ONE record, and a disagreeing doc is a vendor ask. None when nothing
    conflicts or nothing is stated."""
    rec = ((strains.get(strain) or {}).get("type") or "").strip()
    if not strain or not stated or not rec or type_agrees(rec, stated):
        return None
    mine = [r for r in everything if (r.get("Strain") or "") == strain]
    on = [f"{r.get('Brand', '')} {r.get('SKU', '')} {r.get('Product', '')!r}".strip() for r in mine]
    others_only = bool(mine) and bool(brand) and all(norm(r.get("Brand")) != norm(brand) for r in mine)
    return rec, stated, on, others_only


def conflict_reason(strain, conflict):
    """The STRAIN_TYPE_CONFLICT sentence: within the brand a vendor ask that our own text and public
    sources decide; across brands, a real difference is a new record named `<Name> (<Type>)`."""
    rec, said, on, others_only = conflict
    head = (f"; the line says {said!r} but Strain record {strain!r} is {rec!r}; items on the record: "
            f"{'; '.join(on) if on else 'none'} - ")
    if others_only:
        return head + (f"only other brands carry the record: a real Type difference is a NEW record named "
                       f"{new_strain_name(strain, said)!r} (Strain names are unique), a misalignment is fixed on "
                       f"their items ({STRAIN_SOT_RULE})")
    return head + (f"one record per name within a brand: a vendor ask, never a new record - our own text and "
                   f"public strain sources decide (agree with the record: the doc is the vendor's error; agree "
                   f"with the doc: re-type the record in place; split: the vendor's answer decides; "
                   f"{STRAIN_SOT_RULE})")


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


FEEDSTOCK = ("live", "cured")
_TERP_RE = re.compile(r"terp|botanical|\bcdt\b", re.I)   # an added-terpene mention: the Distillate class (R33)


def feedstock_default(cat, dtoks, tax):
    """(Category, defaulted) on the R79 Live / Cured axis. When `cat` sits on a pair the taxonomy carries
    (`Live <x>` AND `Cured <x>`), the line keys Cured only when it prints `Cured`, else Live (Adam 2026-10-08:
    "Always assume `Live` when 'Cured' is not explicitly stated"); `defaulted` = it printed neither. Any
    other Category (Distillate, Rosin, Live Distillate with no Cured twin - R94) passes through unchanged."""
    toks = (cat or "").split()
    if not toks or toks[0].lower() not in FEEDSTOCK:
        return cat, False
    rest = " ".join(toks[1:])
    live, cured = tax.get(norm("Live " + rest)), tax.get(norm("Cured " + rest))
    if not live or not cured:
        return cat, False
    if "cured" in dtoks:
        return cured[1], False
    return live[1], "live" not in dtoks


def swap_feedstock(form, cat):
    """The form word with its leading Live / Cured word set to the Category's (a Cured source's form word
    must not survive on a Live create); a form word with no feedstock word is unchanged."""
    f, c = (form or "").split(), (cat or "").split()
    if f and c and f[0].lower() in FEEDSTOCK and c[0].lower() in FEEDSTOCK:
        f[0] = c[0]
    return " ".join(f)


def feedstock_tiebreak(top, lanes, dtoks):
    """The ONE tied lane the R79 default picks: every tied lane's Category is `Live <x>` / `Cured <x>` on one
    `<x>`; the lane whose Category opens with `Cured` when the line prints it, else `Live`. None otherwise."""
    cats = {k: (lanes[k]["rows"][0].get("Category") or "").split() for k in top}
    if any(not c or c[0].lower() not in FEEDSTOCK for c in cats.values()):
        return None
    if len({" ".join(c[1:]).lower() for c in cats.values()}) != 1:
        return None
    want = "cured" if "cured" in dtoks else "live"
    pick = [k for k, c in cats.items() if c[0].lower() == want]
    return pick[0] if len(pick) == 1 else None


def lanes_of(rows, brand, dtoks, g):
    """{lane key: {'fs': form score, 'rows': members}} over `rows` for the brand at the line's grams."""
    lanes = {}
    for r in rows:
        if norm(r.get("Brand")) != norm(brand):
            continue
        if g is not None and not grams_eq(r.get("Product grams"), g):
            continue
        fs = form_score(form_word(r.get("Product")), dtoks)
        if fs > 0:
            lanes.setdefault(lane_key(r), {"fs": fs, "rows": []})["rows"].append(r)
    return lanes


def lane_members(rows, key):
    return [r for r in rows if lane_key(r) == key]


def place_line(live, brand, dtoks):
    """(Master category, Category, Global SubCategory, form word, why-not) for a line that fits no lane: the
    catalog items whose form word the line names, at the best score, the brand's own first. Nothing when
    no form word is read or the best candidates span two Master categories - the line cannot be placed."""
    scored = [(form_score(form_word(r.get("Product")), dtoks), r) for r in live]
    scored = [(s, r) for s, r in scored if s > 0]
    if not scored:
        return None, None, None, None, "the line names no form word the catalog carries"
    pool = [(s, r) for s, r in scored if norm(r.get("Brand")) == norm(brand)] or scored
    top = max(s for s, _ in pool)
    best = [r for s, r in pool if s == top]
    mcs = sorted({r.get("Master category", "") for r in best})
    if len(mcs) != 1 or not mcs[0]:
        return None, None, None, None, f"the form word read spans {len(mcs)} Master categories ({', '.join(m or 'blank' for m in mcs)})"
    forms = [form_word(r.get("Product")) for r in best]
    cats = [r.get("Category", "") for r in best]
    gscs = [r.get("Global SubCategory", "") for r in best]
    return (mcs[0], max(sorted(set(cats)), key=cats.count), max(sorted(set(gscs)), key=gscs.count),
            max(sorted(set(forms)), key=forms.count), "")


def taxonomy_of(categories, live, old):
    """{norm(Category): (Master category, Category, Global SubCategory)} - the categories export when given,
    else every (MC, Category) the catalog itself carries (the run prints which one stood in)."""
    tax = {}
    if categories:
        for c in categories:
            cat = (c.get("Category") or "").strip()
            if cat:
                tax[norm(cat)] = ((c.get("Master category") or "").strip(), cat,
                                  (c.get("Global Subcategories") or c.get("Global SubCategory") or "").strip())
        return tax
    for r in live + old:
        cat = (r.get("Category") or "").strip()
        if cat and norm(cat) not in tax:
            tax[norm(cat)] = ((r.get("Master category") or "").strip(), cat, (r.get("Global SubCategory") or "").strip())
    return tax


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


def closest_any_brand(live, mc, cat, gsc, dtoks, g):
    """The CLOSEST active item by subcategory in the whole catalog, any brand (R101): the same Global
    SubCategory first, then the same Category, then the same Master category; inside a tier the best form
    score, the closest grams, then the sibling order. None when the Master category has no active item."""
    pool = [r for r in live if r.get("Master category") == mc]

    def key(r):
        tier = 0 if (gsc and norm(r.get("Global SubCategory")) == norm(gsc)) else \
            1 if (cat and norm(r.get("Category")) == norm(cat)) else 2
        rg = grams_of(r.get("Product grams"))
        gap = abs(rg - g) if rg is not None and g is not None else float("inf")
        return (tier, -form_score(form_word(r.get("Product")), dtoks), gap,
                0 if r.get("Image URL") else 1, -pid_num(r), r.get("SKU", ""))
    return sorted(pool, key=key)[0] if pool else None


def base_row(line):
    """Every intake column present (blank), then the line's own cells."""
    row = {c: "" for c in INTAKE_COLS}
    row.update(_line_cells(line))
    return row


def _line_cells(line):
    return {"invoice_no": line.get("invoice_no", ""), "invoice_date": line.get("invoice_date", ""),
            "invoice_line": line.get("description", ""), "cases": line.get("cases", ""),
            "units_total": line.get("units_total", ""), "case_cost": line.get("case_cost", ""),
            "unit_cost": line.get("unit_cost", ""), "potency_tac_pct": line.get("potency_tac_pct", ""),
            "container": line.get("container", ""), "coa_url": line.get("coa_url", ""),
            "expiry_date": line.get("expiry_date", ""), "approved": "",
            "parse_source": line.get("parse_source", ""), "package_id": line.get("package_id") or "",
            "unretire_set": ""}


def fill_from(row, src):
    row["copy_source_sku"], row["copy_source_productid"] = src.get("SKU", ""), src.get("ProductId", "")
    row["copy_source_name"] = src.get("Product", "")
    for k, c in LANE_MAP.items():
        row[k] = src.get(c, "")


def direction(table, line_no):
    return (table or {}).get(str(line_no or "").strip()) or (table or {}).get("*")


def match(lines, active, retired, strains, brand_override=None, new_line_tag=DEFAULT_NEW_LINE_TAG,
          dead_tag=DEFAULT_DEAD_TAG, drop_tags=(), active_tag=DEFAULT_ACTIVE_TAG, prefix=ITEM_PREFIX,
          tag_overrides=None, categories=None, brands=None, line_brands=None, line_categories=None,
          strain_types=None):
    """Pure: (intake rows, defects). `strains` = {name: {'type':..., 'id':...}}. `tag_overrides` =
    {line_no or '*': tag} - the business's direction for a sibling copy's decision tag (R96).
    `categories` = the taxonomy rows (None: the catalog's own stand in); `brands` = the Brand records
    (Display name); `line_brands` / `line_categories` / `strain_types` = {line_no or '*': value} directions,
    a strain type as `<Type>@<source>`."""
    tag_overrides = tag_overrides or {}
    live = [r for r in active if not is_dead(r, dead_tag)]
    old = [r for r in retired if not is_dead(r, dead_tag)]
    everything = live + old
    vocab = form_vocab(live)
    brands_items = sorted({r["Brand"] for r in everything if r.get("Brand")}, key=len, reverse=True)
    brand_records = {norm(b.get("Display name")): (b.get("Display name") or "").strip() for b in (brands or [])
                     if (b.get("Display name") or "").strip()}
    tax = taxonomy_of(categories, live, old)
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
        at = f"{'?' if g is None else format(g, 'g')}g"
        vb = sorted({r["Brand"] for r in everything if r.get("Brand")
                     and (vendor_match(r.get("Vendor"), vend) or vendor_match(r["Brand"], vend))})
        named = [b for b in brands_items if has_phrase(desc_n, b)]
        directed = direction(line_brands, ln.get("line_no"))
        brand = directed or brand_override or (named[0] if named else (vb[0] if len(vb) == 1 else None))
        brand_is_new = bool(brand) and norm(brand) not in {norm(b) for b in brands_items}
        if brand_is_new and norm(brand) in brand_records:
            brand, brand_is_new = brand_records[norm(brand)], False   # a Brand record with no item yet
        stated0, rkey0 = line_type(desc), ratio_key(desc)
        hits = body_hits(live, brand, desc_n, dtoks, g, fl, stated0, rkey0) if brand and not brand_is_new else []
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
        rhits = body_hits(old, brand, desc_n, dtoks, g, fl, stated0, rkey0) if brand and not brand_is_new else []
        if rhits:
            if len(rhits) > 1:
                flags.append("AMBIGUOUS_MATCH")
            m = pick_sibling(rhits)
            fill_from(row, m)
            lane = lane_members(old, lane_key(m))
            flags.append("UNRETIRE_FIELDS")
            row.update(verdict="RETIRED_MATCH", action="UNRETIRE - the product line comes back whole (R101)",
                       strain=m.get("Strain", ""), strain_type=m.get("Strain Type", ""), tags=active_tag,
                       online_title=m.get("Online title", ""),
                       lane_Cost=ln.get("unit_cost", "") or row.get("lane_Cost", ""),
                       unretire_set=";".join(record_key(r) for r in lane),
                       sibling_reason=(f"retired {m.get('SKU')} {m.get('Product')!r}; its line "
                                       f"{' | '.join(lane_key(m))} comes back whole: un-retire {len(lane)} item(s) "
                                       f"({', '.join(f'{r.get('SKU', '')} {body_of(r.get('Product')) or r.get('Strain', '')}' for r in lane)}); "
                                       f"Cost {ln.get('unit_cost', '')} from the invoice (was {m.get('Cost', '')}), "
                                       f"confirm Price {m.get('Price', '')} current; tag `{active_tag}` on each; "
                                       f"the brand's other retired lines stay retired"))
            row["flags"] = ";".join(flags)
            out.append(row)
            continue
        if not brand:
            brand_is_new = True
        lanes = lanes_of(live, brand, dtoks, g) if not brand_is_new else {}
        from_retired = False
        if not lanes and not brand_is_new:
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
            lanes = lanes_of(old, brand, dtoks, g)
            from_retired = bool(lanes)
        if not lanes:
            # a NEW line: the brand (an item, a Brand record, a direction) carries nothing it fits
            cat_dir = direction(line_categories, ln.get("line_no"))
            if cat_dir:
                hit = tax.get(norm(cat_dir))
                if not hit:
                    row.update(verdict="NEW_CATEGORY", action="STOP - Category not in the taxonomy (R101)",
                               lane_Brand="" if brand_is_new else brand, lane_Category=cat_dir,
                               sibling_reason=f"Category {cat_dir!r} (the operator's direction) is absent from the "
                                              f"{'categories export' if categories else 'catalog (no categories export given)'}: "
                                              f"a new category is a configuration decision, not an intake step")
                    row["flags"] = ";".join(flags)
                    out.append(row)
                    continue
                mc, cat, gsc = hit
                form = cat
                flags.append("CATEGORY_DIRECTED")
                why = ""
            else:
                mc, cat, gsc, form, why = place_line(live, brand, dtoks)
                if mc and tax and norm(cat) not in tax:
                    row.update(verdict="NEW_CATEGORY", action="STOP - Category not in the taxonomy (R101)",
                               lane_Brand="" if brand_is_new else brand, lane_Category=cat,
                               sibling_reason=f"the line places in Category {cat!r} (read from the catalog's items), "
                                              f"which the categories export does not carry: refresh the export or rule the category")
                    row["flags"] = ";".join(flags)
                    out.append(row)
                    continue
            verdict = "NEW_BRAND" if brand_is_new else "NEW_PL"
            if brand_is_new and not brand:
                flags.append("BRAND_NAME_UNREAD")
            if not mc:
                flags.append("CATEGORY_UNREAD")
                row.update(verdict=verdict, lane_Brand=brand or "",
                           action=("STOP - category unread: name the line's Category (R101)"),
                           sibling_reason=(f"{'new brand' if brand_is_new else 'new line under ' + repr(brand)}: no lane at {at}; "
                                           f"{why}; pass --line-category {ln.get('line_no', '?')}=<Category> and re-run - "
                                           f"no copy source until the Category is known"
                                           + ("; no catalog brand named in the line and the vendor "
                                              f"{vend!r} carries {len(vb)} brand(s)" + (f" ({', '.join(vb)})" if vb else "")
                                              if brand_is_new and not brand else "")))
                row["flags"] = ";".join(flags)
                out.append(row)
                continue
            near = nearest_in_mc(live, brand, mc, dtoks, g) if brand and not brand_is_new else None
            cross = near is None
            if cross:
                near = closest_any_brand(live, mc, cat, gsc, dtoks, g)
            if near is None:
                flags.append("CATEGORY_UNREAD")
                row.update(verdict=verdict, lane_Brand=brand or "", lane_Category=cat or "", lane_MasterCategory=mc,
                           action="STOP - no active item in the Master category to copy (R101)",
                           sibling_reason=f"Master category {mc!r} has no active item in the catalog; no copy source")
                row["flags"] = ";".join(flags)
                out.append(row)
                continue
            fill_from(row, near)
            if cross:
                flags.append("CROSS_BRAND_COPY")
                row.update(lane_Brand=brand or "", lane_Vendor=vend, lane_Price="")
                if not cat_dir:
                    missing = [t for t in canon(cat).split() if t not in FEEDSTOCK and t not in dtoks]
                    if missing == ["resin"] and not _TERP_RE.search(desc):
                        flags.append("ROUTE_RESIN_DEFAULT")
                    elif missing:
                        flags.append("CATEGORY_INFERRED")
            fs_note = ""
            if not cat_dir:
                was = row.get("lane_Category", "")
                fs_cat, fs_def = feedstock_default(was, dtoks, tax)
                if norm(fs_cat) != norm(was):
                    hit = tax[norm(fs_cat)]
                    row.update(lane_Category=fs_cat, lane_MasterCategory=hit[0] or row.get("lane_MasterCategory", ""),
                               lane_GlobalSubCategory=hit[2] or row.get("lane_GlobalSubCategory", ""))
                    form = swap_feedstock(form, fs_cat)
                    fs_note = f"; Category {fs_cat!r}, not the source's {was!r}"
                if fs_def:
                    flags.append("OIL_LIVE_DEFAULT")
                    fs_note += "; the line prints neither Live nor Cured: the Live Category by default (R79)"
                elif fs_note:
                    fs_note += ": the line prints Cured (R79)"
            if cat_dir:
                row.update(lane_Category=cat, lane_MasterCategory=mc, lane_GlobalSubCategory=gsc or row.get("lane_GlobalSubCategory", ""))
            src_brand = near.get("Brand", "")
            stated = line_type(desc)
            strain, fbody = line_strain(fl, live, brand or src_brand, desc_n, strains,
                                        flavored=bool(near.get("Flavor")), stated=stated, desc=desc) if brand else (None, None)
            st_dir = direction(strain_types, ln.get("line_no")) or ""
            st_type, _, st_src = st_dir.partition("@")
            reason = ((f"new brand {brand!r}: create the Brand record first (live Global Brand read, R30; display name "
                       f"per R121); then " if brand_is_new else f"new line under {brand!r}: ")
                      + f"no lane at {at} {form}; "
                      + (f"closest active item by subcategory, any brand ({src_brand!r}), in Master category {mc!r}"
                         f"{' / ' + cat if cat else ''}{' / ' + gsc if gsc else ''}: " if cross
                         else f"nearest active item in Master category {mc!r}: ")
                      + f"{near.get('SKU')} {near.get('Product')!r}")
            if cat_dir:
                reason += f"; Category {cat!r} by the operator's direction - confirm against the vendor's words (R33)"
            elif cross and "CATEGORY_INFERRED" in flags:
                reason += f"; Category {cat!r} is the source's, and the line does not print its route words - a vendor fact (R33)"
            reason += fs_note
            if "ROUTE_RESIN_DEFAULT" in flags:
                reason += "; the line names no route and no added terpenes: Resin by default (R33)"
            if brand and near.get("Strain") and not strain:
                row.update(verdict="STRAIN_MISSING", action="STOP - mint the Strain record first (R101)",
                           strain_record="MISSING", strain_type=st_type.strip(),
                           sibling_reason=reason + "; no Strain record named in the line"
                           + (f"; Type {st_type.strip()!r} per {st_src.strip() or 'an unnamed source'} (STRAIN_TYPE_RESEARCHED)"
                              if st_type.strip() else
                              (f"; the line prints Type {stated!r}" if stated else
                               "; Type not printed: research the vendor assets, then the web (R33 chain) and pass "
                               f"--strain-type {ln.get('line_no', '?')}=<Type>@<source>")))
                if st_type.strip():
                    flags.append("STRAIN_TYPE_RESEARCHED")
                row["flags"] = ";".join(flags)
                out.append(row)
                continue
            conflict = strain_conflict(strain, strains, st_type.strip() or stated, everything, brand) if brand else None
            if conflict:
                said = conflict[1]
                flags.append("STRAIN_TYPE_CONFLICT")
                row.update(verdict="STRAIN_MISSING", action=f"STOP - Strain Type conflict: check the record's items (R26, {STRAIN_SOT_RULE})",
                           strain_record="CONFLICT", strain=strain, strain_type=said,
                           sibling_reason=reason + conflict_reason(strain, conflict))
                row["flags"] = ";".join(flags)
                out.append(row)
                continue
            flags.append("NEW_LINE_FIELDS")
            if near.get("Flavor"):
                flags.append("FLAVOR_TO_SET")
            s = strain or ""
            dose = "" if g is None else f"{g:g}g"
            seg0 = (brand or "") if cross else ((near.get("Product") or "").split(" | ")[0].strip() or brand)
            if s:
                flags.append("OT_TEMPLATE_MISS")
            row.update(verdict=verdict,
                       action=("CREATE - new brand, then copy closest by subcategory (R101)" if brand_is_new
                               else "CREATE - copy closest by subcategory, any brand (new line, R83)" if cross
                               else "CREATE - copy nearest (new line, R83)"),
                       sibling_reason=reason + "; set or confirm at the stop: name, Price, Flower equiv, "
                                               "Servings per Unit, Category / Type"
                       + ("; the copy gives up the source's Brand, Vendor, Price, Online title / description and image"
                          if cross else "")
                       + ("" if body_known(s, fbody) or not s else f"; name body = <Flavor> ({s}): the operator completes it"),
                       strain_record="LIVE" if s else "",
                       create_name_FINAL=" | ".join([seg0, form, fbody or s, dose]) if s and dose and seg0 and body_known(s, fbody) else "",
                       strain=s, strain_type=(strains.get(s) or {}).get("type", ""),
                       strain_id=(strains.get(s) or {}).get("id", ""), online_title="",
                       online_desc_chars=str(len(near.get("Online description") or "")),
                       online_desc_source=("source brand's template - REWRITE for the new brand's line; none of its words survive"
                                           if cross else
                                           "nearest item's template - rewrite for the new line (platform KB sourcing chain)"),
                       image_state=(("source brand's image carried - REMOVE (cross-brand residue)" if cross else
                                     "nearest item's image carried - keep only if generic brand art (platform KB Images)")
                                    if near.get("Image URL") else "0 images (NO_ECOM_IMAGE - a human supplies art)"),
                       lane_ProductGrams=dose or row.get("lane_ProductGrams", ""),
                       lane_Cost=ln.get("unit_cost", "") or row.get("lane_Cost", ""),
                       tags=copy_tags(near, drop_tags, prefix, new_line_tag))
            row["flags"] = ";".join(flags)
            out.append(row)
            continue
        best = max(v["fs"] for v in lanes.values())
        top = [k for k, v in lanes.items() if v["fs"] == best]
        fs_pick = feedstock_tiebreak(top, lanes, dtoks) if len(top) > 1 else None
        if fs_pick is not None:
            top = [fs_pick]
            if "live" not in dtoks and "cured" not in dtoks:
                flags.append("OIL_LIVE_DEFAULT")
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
        reason = (f"lane {' | '.join(top[0])}: {len(members)} {'retired' if from_retired else 'active'} member(s), "
                  f"{with_img} with an image; chose {sib.get('SKU')} ({'image' if sib.get('Image URL') else 'no image'}, "
                  f"ProductId {sib.get('ProductId') or 'n/a'})")
        if fs_pick is not None:
            reason += ("; the Live and Cured lanes tie: " + ("the line prints Cured" if "cured" in dtoks else
                       "the line prints Live" if "live" in dtoks else
                       "the line prints neither Live nor Cured, so the Live lane by default") + " (R79)")
        if from_retired:
            flags.append("UNRETIRE_FIRST")
            row["unretire_set"] = ";".join(record_key(r) for r in members)
            reason += (f"; the line we carried before comes back WHOLE: un-retire all {len(members)} "
                       f"({', '.join(f'{r.get('SKU', '')} {body_of(r.get('Product')) or r.get('Strain', '')}' for r in members)}) "
                       f"and read them back before this copy (R101)")
        stated = line_type(desc)
        strain, fbody = line_strain(fl, live if not from_retired else live + members, brand, desc_n, strains,
                                    flavored=bool(sib.get("Flavor")), stated=stated, desc=desc)
        strain_bearing = bool(sib.get("Strain"))
        if sib.get("Flavor"):
            flags.append("FLAVOR_TO_SET")
        st_dir = direction(strain_types, ln.get("line_no")) or ""
        st_type, _, st_src = st_dir.partition("@")
        if strain_bearing and not strain:
            row.update(verdict="STRAIN_MISSING", action="STOP - mint the Strain record first (R101)",
                       strain_record="MISSING", strain_type=st_type.strip(),
                       sibling_reason=reason + "; no Strain record named in the line"
                       + (f"; Type {st_type.strip()!r} per {st_src.strip() or 'an unnamed source'} (STRAIN_TYPE_RESEARCHED)"
                          if st_type.strip() else
                          (f"; the line prints Type {stated!r}" if stated else
                           "; Type not printed: research the vendor assets, then the web (R33 chain) and pass "
                           f"--strain-type {ln.get('line_no', '?')}=<Type>@<source>")))
            if st_type.strip():
                flags.append("STRAIN_TYPE_RESEARCHED")
            row["flags"] = ";".join(flags)
            out.append(row)
            continue
        conflict = strain_conflict(strain, strains, st_type.strip() or stated, everything, brand) if strain_bearing else None
        if conflict:
            said = conflict[1]
            flags.append("STRAIN_TYPE_CONFLICT")
            row.update(verdict="STRAIN_MISSING", action=f"STOP - Strain Type conflict: check the record's items (R26, {STRAIN_SOT_RULE})",
                       strain_record="CONFLICT", strain=strain, strain_type=said,
                       sibling_reason=reason + conflict_reason(strain, conflict))
            row["flags"] = ";".join(flags)
            out.append(row)
            continue
        s = strain or ""
        direct = tag_overrides.get(str(ln.get("line_no", "")).strip()) or tag_overrides.get("*")
        if direct:
            decision, why = direct, f"`{direct}` by the business's direction"
        elif from_retired:
            decision, why = active_tag, f"`{active_tag}`: anything brought back from retirement reads the Active tag"
        else:
            decision, why = decision_tag(members, prefix, active_tag, new_line_tag)
        reason += f"; tag {why}"
        ot = new_ot(sib, fbody or s, by_body=bool(fbody)) if s and body_known(s, fbody) else ""
        if s and not ot:
            flags.append("OT_TEMPLATE_MISS")
        if s and not body_known(s, fbody):
            reason += f"; name body = <Flavor> ({s}): the operator completes it"
        row.update(verdict="NEW_ITEM_WITH_SIBLING",
                   action="CREATE - copy item after the un-retire (R101)" if from_retired else "CREATE - copy item",
                   sibling_reason=reason,
                   strain_record="LIVE" if s else "", create_name_FINAL=new_name(sib, fbody or s) if s and body_known(s, fbody) else "",
                   strain=s, strain_type=(strains.get(s) or {}).get("type", ""),
                   strain_id=(strains.get(s) or {}).get("id", ""), online_title=ot,
                   online_desc_chars=str(len(sib.get("Online description") or "")),
                   online_desc_source="sibling template - replace the strain paragraph (platform KB sourcing chain)",
                   image_state=("sibling image carried - keep only if generic brand art (platform KB Images)"
                                if sib.get("Image URL") else "0 images (NO_ECOM_IMAGE - a human supplies art)"),
                   lane_Cost=(ln.get("unit_cost", "") or row.get("lane_Cost", "")) if from_retired else row.get("lane_Cost", ""),
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
    cats_p, brands_p = get_flag(argv, "--categories"), get_flag(argv, "--brands")
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
    if xdir and not cats_p:
        cats_p = freshest_or_none(xdir, ["*categor*.csv"], CATEGORIES_REQUIRED)
    if xdir and not brands_p:
        brands_p = freshest_or_none(xdir, ["*brand*.csv"], BRANDS_REQUIRED)
    if not strains:
        abort("the Strains export is required (--strains): without it STRAIN_MISSING would fire on every new item")
    _, a = read_csv(active, CATALOG_REQUIRED, "active export")
    r = []
    if retired:
        _, r = read_csv(retired, CATALOG_REQUIRED, "retired export")
    if a and COL_RETIRED in a[0]:
        r = r + [x for x in a if x.get(COL_RETIRED) == "Yes"]
        a = [x for x in a if x.get(COL_RETIRED) != "Yes"]
    cats = read_csv(cats_p, CATEGORIES_REQUIRED, "categories export")[1] if cats_p else None
    brs = read_csv(brands_p, BRANDS_REQUIRED, "brands export")[1] if brands_p else None
    return (active, retired, strains, cats_p, brands_p), a, r, load_strains(strains), cats, brs


def freshest_or_none(dir_, patterns, required):
    """The freshest matching file carrying the columns, or None - these two exports are optional."""
    try:
        names = os.listdir(dir_)
    except OSError:
        return None
    import fnmatch
    cands = sorted((os.path.join(dir_, n) for n in names if any(fnmatch.fnmatch(n.lower(), p.lower()) for p in patterns)),
                   key=os.path.getmtime, reverse=True)
    for c in cands:
        try:
            with open(c, encoding="utf-8-sig", newline="") as f:
                import csv
                hdr = next(csv.reader(f))
        except (OSError, StopIteration, UnicodeDecodeError):
            continue
        if all(col in hdr for col in required):
            return c
    return None


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


def parse_directions(specs, flag):
    """`<line_no>=<value>` / `*=<value>` -> {key: value}; an empty side ABORTs."""
    out = {}
    for spec in specs:
        k, sep, v = spec.partition("=")
        k, v = k.strip(), v.strip()
        if not sep or not k or not v:
            abort(f"{flag} {spec!r}: want <line_no>=<value> (or *=<value>)")
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
    paths, active, retired, strains, cats, brs = load_exports(argv, ptr)
    new_line_tag, active_tag = tag_options(argv, ptr)
    overrides = parse_overrides(get_all(argv, "--tag-override"), new_line_tag, get_flag(argv, "--dead-tag", DEFAULT_DEAD_TAG))
    rows, defects = match(lines, active, retired, strains, get_flag(argv, "--brand"), new_line_tag,
                          get_flag(argv, "--dead-tag", DEFAULT_DEAD_TAG), get_all(argv, "--drop-tag"),
                          active_tag, ITEM_PREFIX, overrides, categories=cats, brands=brs,
                          line_brands=parse_directions(get_all(argv, "--line-brand"), "--line-brand"),
                          line_categories=parse_directions(get_all(argv, "--line-category"), "--line-category"),
                          strain_types=parse_directions(get_all(argv, "--strain-type"), "--strain-type"))
    out_dir = get_flag(argv, "--out-dir") or (ptr["intake"]["Intake dir"] if ptr else os.path.dirname(os.path.abspath(lines_p)))
    tslug = get_flag(argv, "--slug") or (slug(os.path.basename(os.path.dirname(os.path.abspath(tenant)))) if tenant else "tenant")
    first = next((ln for ln in lines if not ln.get("order_level_kind")), lines[0] if lines else {})
    stem = f"{tslug}-intake-{slug(first.get('vendor'))}-{slug(first.get('invoice_no'))}-{first.get('invoice_date') or 'undated'}"
    out = next_version(out_dir, stem)
    write_csv(out, INTAKE_COLS, rows)
    print("inputs: " + " | ".join(f"{k} {os.path.basename(p) if p else 'NONE'} ({n})" for k, p, n in
                                  zip(("active", "retired", "strains", "categories", "brands"), paths,
                                      (len(active), len(retired), len(strains), len(cats or []), len(brs or [])))))
    if not retired:
        print("WARNING: no retired rows - RETIRED_MATCH cannot fire; a zero below proves nothing for it")
    if not cats:
        print("WARNING: no categories export - the catalog's own Categories stand in for the taxonomy; "
              "NEW_CATEGORY can only fire on a --line-category direction")
    if not brs:
        print("WARNING: no brands export - a Brand record with no item reads as a NEW brand")
    print(f"{'verdict':24} count")
    for v in VERDICTS:
        print(f"{v:24} {sum(1 for r in rows if r['verdict'] == v)}")
    print(f"\n{'flag':22} {'rule':5} {'class':7} count")
    for f, rule, cls in FLAGS:
        n = len(defects) if f == "BAD_LINE" else sum(1 for r in rows if f in r.get("flags", "").split(";"))
        print(f"{f:22} {rule:5} {cls:7} {n}")
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
    if not r.get("Master category"):
        r["Master category"] = "Pre-Roll"
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
    retired = [_item("9", "Acme | Pre-Roll | Sour Diesel | 1g", pid="9", Tags="ITM - Discontinue")]
    strains = {n: {"type": "Hybrid", "id": ""} for n in ("Blue Dream", "OG Kush", "Sour Diesel", "Gelato")}
    strains["Gelato"] = {"type": "Hybrid", "id": ""}

    def run(desc, vendor="Example Wholesale", act=active, ret=retired, st=strains, **kw):
        rows, _ = match([{"description": desc, "vendor": vendor, "units_total": "10", "unit_cost": "4.5", "line_no": "1"}],
                        act, ret, st, **kw)
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
    # --- RETIRED_MATCH = the un-retire path (R101: the line comes back WHOLE) ---
    r = run("Acme Sour Diesel pre-roll 1g")
    t.check("RETIRED_MATCH fires", r["verdict"] == "RETIRED_MATCH")
    t.check("RETIRED_MATCH is an UNRETIRE with UNRETIRE_FIELDS, Cost from the invoice, the Active tag",
            r["action"].startswith("UNRETIRE") and "UNRETIRE_FIELDS" in r["flags"].split(";")
            and r["lane_Cost"] == "4.5" and r["tags"] == DEFAULT_ACTIVE_TAG, f"{r['action']} {r['flags']} {r['tags']}")
    two_ret = retired + [_item("8", "Acme | Pre-Roll | Gelato | 1g", pid="8", Tags="ITM - Discontinue"),
                         _item("7", "Acme | Pre-Roll | Gelato | 0.5g", pid="7", Tags="ITM - Discontinue")]
    r = run("Acme Sour Diesel pre-roll 1g", ret=two_ret)
    t.check("FIRES: unretire_set = every retired member of the matched item's lane (1g), never the brand's other lanes (0.5g)",
            r["unretire_set"] == "9;8", r["unretire_set"])
    t.check("QUIET: unretire_set is blank on EXISTS", run("Acme Blue Dream preroll 1g")["unretire_set"] == "")
    # --- UNRETIRE_FIRST: a line that fits only a RETIRED lane copies the retired sibling after the un-retire ---
    only_ret = [_item("21", "Bolt | Distillate Cart | Blue Dream | 1g", pid="21", cat="Cartridge", Tags="ITM - Discontinue",
                      **{"Master category": "Vape", "Image URL": "b.jpg"}),
                _item("22", "Bolt | Distillate Cart | OG Kush | 1g", pid="22", cat="Cartridge", Tags="ITM - Discontinue",
                      **{"Master category": "Vape"}),
                _item("23", "Bolt | Distillate Cart | OG Kush | 0.5g", pid="23", cat="Cartridge", Tags="ITM - Discontinue",
                      **{"Master category": "Vape"})]
    r = run("Bolt Gelato distillate cart 1g", ret=retired + only_ret)
    t.check("UNRETIRE_FIRST: a line fitting only a retired lane is a copy of the retired sibling",
            r["verdict"] == "NEW_ITEM_WITH_SIBLING" and "UNRETIRE_FIRST" in r["flags"].split(";")
            and r["copy_source_sku"] == "21" and r["action"].endswith("after the un-retire (R101)"),
            f"{r['verdict']} {r['flags']} {r['copy_source_sku']}")
    t.check("UNRETIRE_FIRST lists the whole lane (both 1g carts) and not the 0.5g one; the copy reads the Active tag",
            r["unretire_set"] == "21;22" and r["tags"] == DEFAULT_ACTIVE_TAG, f"{r['unretire_set']} {r['tags']}")
    t.check("QUIET: UNRETIRE_FIRST off when an active lane fits",
            "UNRETIRE_FIRST" not in run("Acme Gelato preroll 1g")["flags"])
    r = run("Acme Gelato preroll 1g")
    t.check("NEW_ITEM_WITH_SIBLING fires", r["verdict"] == "NEW_ITEM_WITH_SIBLING", r["verdict"])
    t.check("sibling prefers the image over the newer id", r["copy_source_sku"] == "1", r["copy_source_sku"])
    t.check("QUIET: a dead record is never the sibling", r["copy_source_sku"] != "3")
    t.check("final name swaps segment 3 only", r["create_name_FINAL"] == "Acme | Pre-Roll | Gelato | 1g", r["create_name_FINAL"])
    t.check("online title swaps the strain only", r["online_title"] == "Gelato Pre-Roll 1g", r["online_title"])
    t.check("a copy of an untagged lane reads the Active tag, never the new-line tag (R96, R83)",
            r["tags"] == DEFAULT_ACTIVE_TAG, r["tags"])
    t.check("STRAIN_MISSING fires", run("Acme Mystery Haze preroll 1g")["verdict"] == "STRAIN_MISSING")
    # --- STRAIN_TYPE_CONFLICT (R26) and the researched type (R33) ---
    r = run("Acme Gelato preroll 1g Sativa")
    t.check("STRAIN_TYPE_CONFLICT: the line says Sativa, the Gelato record is Hybrid -> STRAIN_MISSING with the record's items",
            r["verdict"] == "STRAIN_MISSING" and "STRAIN_TYPE_CONFLICT" in r["flags"].split(";")
            and r["strain_record"] == "CONFLICT" and r["strain_type"] == "Sativa" and "none" in r["sibling_reason"],
            f"{r['verdict']} {r['flags']} {r['strain_type']}")
    t.check("STRAIN_TYPE_CONFLICT on a record no other brand carries: a vendor ask, one record per name, no new record",
            "a vendor ask, never a new record" in r["sibling_reason"] and "a NEW record named" not in r["sibling_reason"],
            r["sibling_reason"])
    other = active + [_item("4", "Bolt | Pre-Roll | Gelato | 0.5g", pid="14", Brand="Bolt", vendor="Bolt Wholesale")]
    r = run("Acme Gelato preroll 1g Sativa", act=other)
    t.check("STRAIN_TYPE_CONFLICT on a record only OTHER brands carry names the new record `<Name> (<Type>)` (R26)",
            "a NEW record named 'Gelato (Sativa)'" in r["sibling_reason"] and "vendor ask" not in r["sibling_reason"],
            r["sibling_reason"])
    mixed_rec = other + [_item("5", "Acme | Pre-Roll | Gelato | 0.5g", pid="15")]
    t.check("QUIET: once the line's own brand carries the record, no new record is offered (one record within a brand)",
            "a NEW record named" not in run("Acme Gelato preroll 1g Sativa", act=mixed_rec)["sibling_reason"])
    t.check("QUIET: a row with no conflict names no new record",
            "a NEW record named" not in run("Acme Gelato preroll 1g Hybrid")["sibling_reason"])
    lean = dict(strains, Gelato={"type": "Indica-Hybrid", "id": ""})
    t.check("a coarser `Hybrid` agrees with a leaner record (`Indica-Hybrid`): no conflict",
            "STRAIN_TYPE_CONFLICT" not in run("Acme Gelato preroll 1g Hybrid", st=lean)["flags"])
    t.check("FIRES: `Sativa` against an `Indica-Hybrid` record is still a conflict",
            "STRAIN_TYPE_CONFLICT" in run("Acme Gelato preroll 1g Sativa", st=lean)["flags"].split(";"))
    with_gelato =active + [_item("4", "Acme | Pre-Roll | Gelato | 0.5g", pid="14")]
    r = run("Acme Gelato preroll 1g (S)", act=with_gelato)
    t.check("STRAIN_TYPE_CONFLICT lists the items on the record", "Acme 4 'Acme | Pre-Roll | Gelato | 0.5g'" in r["sibling_reason"],
            r["sibling_reason"])
    t.check("QUIET: no conflict when the line's type agrees", run("Acme Gelato preroll 1g Hybrid")["verdict"] == "NEW_ITEM_WITH_SIBLING")
    t.check("QUIET: no conflict when the line prints no type", "STRAIN_TYPE_CONFLICT" not in run("Acme Gelato preroll 1g")["flags"])
    r = run("Acme Mystery Haze preroll 1g", strain_types={"1": "Sativa@vendor sheet p2"})
    t.check("STRAIN_TYPE_RESEARCHED: the direction's Type and source ride the STRAIN_MISSING row",
            r["strain_type"] == "Sativa" and "per vendor sheet p2" in r["sibling_reason"] and "STRAIN_TYPE_RESEARCHED" in r["flags"],
            f"{r['strain_type']} {r['flags']}")
    r = run("Acme Mystery Haze preroll 1g")
    t.check("QUIET: no direction -> the row asks for the research, types nothing", r["strain_type"] == "" and "--strain-type" in r["sibling_reason"])
    # --- NEW_PL: the copy source is the brand's nearest item, else the CLOSEST by subcategory, any brand ---
    r = run("Acme Gelato cart 0.5g")
    t.check("CATEGORY_UNREAD: a form word no catalog item carries cannot place the line -> NEW_PL with no copy source",
            r["verdict"] == "NEW_PL" and "CATEGORY_UNREAD" in r["flags"].split(";") and r["copy_source_sku"] == ""
            and r["action"].startswith("STOP"), f"{r['verdict']} {r['flags']} {r['copy_source_sku']!r}")
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
    t.check("FIRES: an empty direction ABORTs", _aborts(lambda: parse_directions(["3="], "--line-brand")))
    vape = active + [_item("7", "Acme | Live Resin Cart | Blue Dream | 1g", pid="17", cat="Live Resin Cart",
                           **{"Master category": "Vape", "Global SubCategory": "live-resin-cartridge", "Image URL": "c.jpg", "Tags": "ITM - Protect"}),
                     _item("8", "Bolt | Gummy | Mango | 100mg", pid="18", cat="Gummy", vendor="Bolt Wholesale",
                           **{"Master category": "Edible", "Global SubCategory": "gummies", "Brand": "Bolt", "Image URL": "g.jpg",
                              "Strain": "", "Flavor": "Mango",
                              "Online title": "Mango Gummy 100mg", "Online description": "Bolt's mango gummy."})]
    r = run("Acme Gelato cart 0.5g", act=vape)
    t.check("NEW_PL: a new line under a known brand is a CREATE from the brand's nearest item in the MC",
            r["verdict"] == "NEW_PL" and r["action"].startswith("CREATE") and r["copy_source_sku"] == "7",
            f"{r['verdict']} {r['action']} {r['copy_source_sku']}")
    t.check("NEW_PL carries the new-line tag and drops the nearest item's decision tag (R83)",
            r["tags"] == DEFAULT_NEW_LINE_TAG, r["tags"])
    t.check("NEW_PL raises NEW_LINE_FIELDS (STOP) for the inherited lane", "NEW_LINE_FIELDS" in r["flags"].split(";"))
    t.check("QUIET: a same-brand source is not a cross-brand copy", "CROSS_BRAND_COPY" not in r["flags"])
    t.check("NEW_PL: grams from the line, Cost from the invoice, a name draft in the nearest item's form",
            r["lane_ProductGrams"] == "0.5g" and r["lane_Cost"] == "4.5"
            and r["create_name_FINAL"] == "Acme | Live Resin Cart | Gelato | 0.5g",
            f"{r['lane_ProductGrams']} {r['lane_Cost']} {r['create_name_FINAL']!r}")
    r = run("Acme Mango gummy 100mg 10pk", act=vape)
    t.check("CROSS_BRAND_COPY: the brand has no item in the MC -> NEW_PL copies the closest by subcategory, any brand",
            r["verdict"] == "NEW_PL" and r["copy_source_sku"] == "8" and "CROSS_BRAND_COPY" in r["flags"].split(";")
            and r["action"].startswith("CREATE"), f"{r['verdict']} {r['copy_source_sku']} {r['flags']}")
    t.check("CROSS_BRAND_COPY gives up the source's Brand, Vendor, Price, Online title and image",
            r["lane_Brand"] == "Acme" and r["lane_Vendor"] == "Example Wholesale" and r["lane_Price"] == ""
            and r["online_title"] == "" and r["image_state"].startswith("source brand's image carried - REMOVE"),
            f"{r['lane_Brand']} {r['lane_Vendor']} {r['lane_Price']!r} {r['image_state']}")
    t.check("CROSS_BRAND_COPY keeps the source's Category / MC / GSC and the invoice Cost",
            r["lane_Category"] == "Gummy" and r["lane_MasterCategory"] == "Edible" and r["lane_Cost"] == "4.5",
            f"{r['lane_Category']} {r['lane_MasterCategory']} {r['lane_Cost']}")
    t.check("QUIET: CATEGORY_INFERRED off when the line prints the Category's words (gummy)",
            "CATEGORY_INFERRED" not in r["flags"])
    cured = vape + [_item("6", "Bolt | Cured Resin Cart | Mango | 0.5g", pid="16", cat="Cured Resin Cart", vendor="Bolt Wholesale",
                          **{"Master category": "Vape", "Global SubCategory": "cured-resin-cartridge", "Brand": "Bolt"})]
    r = run("Zed Mango 510 cart 0.5g botanical terpenes", act=cured, line_brands={"1": "Zed"})
    t.check("CATEGORY_INFERRED: a cross-brand source whose route word (resin) the line does not print, beside an added-terpene mention",
            "CATEGORY_INFERRED" in r["flags"].split(";") and "ROUTE_RESIN_DEFAULT" not in r["flags"] and r["copy_source_sku"] == "6",
            f"{r['flags']} {r['copy_source_sku']}")
    t.check("the feedstock word leaves the CATEGORY_INFERRED reason: the route word still names it",
            "route words" in r["sibling_reason"])
    r = run("Zed Mango 510 cart 0.5g", act=cured, line_brands={"1": "Zed"})
    t.check("ROUTE_RESIN_DEFAULT: no route word and no added terpenes -> Resin by default, an INFO note, no STOP (R33)",
            "ROUTE_RESIN_DEFAULT" in r["flags"].split(";") and "CATEGORY_INFERRED" not in r["flags"]
            and "Resin by default" in r["sibling_reason"], f"{r['flags']}")
    t.check("ROUTE_RESIN_DEFAULT is INFO, never a STOP", ("ROUTE_RESIN_DEFAULT", "R33", "INFO") in FLAGS)
    rosin_src = vape + [_item("6", "Bolt | Rosin Cart | Mango | 0.5g", pid="16", cat="Rosin Cart", vendor="Bolt Wholesale",
                              **{"Master category": "Vape", "Global SubCategory": "live-rosin-cartridge", "Brand": "Bolt"})]
    r = run("Zed Mango 510 cart 0.5g", act=rosin_src, line_brands={"1": "Zed"})
    t.check("QUIET: an unprinted route word other than resin (rosin) keeps CATEGORY_INFERRED, no Resin default",
            "CATEGORY_INFERRED" in r["flags"].split(";") and "ROUTE_RESIN_DEFAULT" not in r["flags"], f"{r['flags']} {r['copy_source_sku']}")
    r = run("Zed Mango 510 cart 0.5g", act=cured, line_brands={"1": "Zed"})
    t.check("'510' reads as a cart (industry word)", "cart" in canon("Vape Product 1g (510, Liquid Diamond)").split())
    # --- OIL_LIVE_DEFAULT (R79, Adam 2026-10-08): Live unless the line prints Cured ---
    t.check("OIL_LIVE_DEFAULT: a Cured source on a line printing neither word -> the Live Category, an INFO note",
            r["lane_Category"] == "Live Resin Cart" and "OIL_LIVE_DEFAULT" in r["flags"].split(";")
            and r["lane_GlobalSubCategory"] == "live-resin-cartridge" and "Live Category by default" in r["sibling_reason"],
            f"{r['lane_Category']} {r['flags']} {r['lane_GlobalSubCategory']}")
    t.check("OIL_LIVE_DEFAULT is INFO, never a STOP", ("OIL_LIVE_DEFAULT", "R79", "INFO") in FLAGS)
    r = run("Zed Mango resin 510 cart 0.5g", act=cured, line_brands={"1": "Zed"})
    t.check("QUIET: a line printing the route word (resin) is not CATEGORY_INFERRED; the feedstock defaults Live",
            "CATEGORY_INFERRED" not in r["flags"] and "OIL_LIVE_DEFAULT" in r["flags"].split(";")
            and r["lane_Category"] == "Live Resin Cart", f"{r['flags']} {r['lane_Category']}")
    r = run("Zed Gelato resin 510 cart 0.5g", act=cured, line_brands={"1": "Zed"})
    t.check("the Live default also rewrites a Cured source's form word in the drafted name",
            r["copy_source_sku"] == "6" and r["create_name_FINAL"] == "Zed | Live Resin Cart | Gelato | 0.5g",
            f"{r['copy_source_sku']} {r['create_name_FINAL']!r}")
    r = run("Zed Mango cured resin 510 cart 0.5g", act=cured, line_brands={"1": "Zed"})
    t.check("QUIET: a line printing Cured keeps the Cured Category, no default note, no inference",
            r["lane_Category"] == "Cured Resin Cart" and "OIL_LIVE_DEFAULT" not in r["flags"]
            and "CATEGORY_INFERRED" not in r["flags"], f"{r['lane_Category']} {r['flags']}")
    live_src = cured + [
        _item("5", "Bolt | Sauce Cart | Mango | 1g", pid="15", cat="Live Resin Cart", vendor="Bolt Wholesale",
              **{"Master category": "Vape", "Global SubCategory": "live-resin-cartridge", "Brand": "Bolt"})]
    r = run("Zed Gelato - Vape Product - 1g (510, Sauce)", act=live_src, line_brands={"1": "Zed"})
    t.check("OIL_LIVE_DEFAULT: a Live source on a line printing neither word stays Live, with the note (a form word with no route word)",
            r["copy_source_sku"] == "5" and r["lane_Category"] == "Live Resin Cart" and "OIL_LIVE_DEFAULT" in r["flags"].split(";"),
            f"{r['copy_source_sku']} {r['lane_Category']} {r['flags']}")
    r = run("Zed Gelato - Vape Product - 1g (510, Sauce)", act=live_src, line_brands={"1": "Zed"},
            categories=[{"Master category": "Vape", "Category": "Live Resin Cart", "Global Subcategories": "live-resin-cartridge"}])
    t.check("QUIET: with no Cured twin in the taxonomy there is no Live / Cured axis to default",
            "OIL_LIVE_DEFAULT" not in r["flags"], r["flags"])
    t.check("QUIET: a Category with no feedstock word passes through (Distillate never turns Live, R94)",
            feedstock_default("Distillate Cart", set(), {norm("Live Distillate Cart"): ("Vape", "Live Distillate Cart", ""),
                                                         norm("Distillate Cart"): ("Vape", "Distillate Cart", "")})
            == ("Distillate Cart", False))
    t.check("a Cured source's form word is set Live on a Live create", swap_feedstock("Cured Resin Cart", "Live Resin Cart")
            == "Live Resin Cart" and swap_feedstock("Sauce Cart", "Live Resin Cart") == "Sauce Cart")
    twins = active + [_item("21", "Acme | Resin Cart | Blue Dream | 1g", pid="21", cat="Live Resin Cart",
                            **{"Master category": "Vape", "Image URL": "l.jpg"}),
                      _item("22", "Acme | Resin Cart | OG Kush | 1g", pid="22", cat="Cured Resin Cart",
                            **{"Master category": "Vape", "Image URL": "c.jpg"})]
    r = run("Acme Gelato resin cart 1g", act=twins)
    t.check("OIL_LIVE_DEFAULT: a Live / Cured lane tie on a line printing neither word takes the Live lane",
            r["verdict"] == "NEW_ITEM_WITH_SIBLING" and r["copy_source_sku"] == "21" and "OIL_LIVE_DEFAULT" in r["flags"].split(";")
            and "LANE_AMBIGUOUS" not in r["flags"], f"{r['verdict']} {r['copy_source_sku']} {r['flags']}")
    r = run("Acme Gelato cured resin cart 1g", act=twins)
    t.check("QUIET: the same tie on a line printing Cured takes the Cured lane, no default note",
            r["copy_source_sku"] == "22" and "OIL_LIVE_DEFAULT" not in r["flags"], f"{r['copy_source_sku']} {r['flags']}")
    rosin = [dict(x, Category="Rosin Cart") if x["SKU"] == "22" else x for x in twins]
    t.check("QUIET: a tie that is not on the Live / Cured axis stays LANE_AMBIGUOUS",
            "LANE_AMBIGUOUS" in run("Acme Gelato resin cart 1g", act=rosin)["flags"])
    # --- NEW_CATEGORY = a taxonomy gap only; a directed Category is checked against the categories export ---
    cats = [{"Master category": "Pre-Roll", "Category": "Pre-Roll Single", "Global Subcategories": "Singles"},
            {"Master category": "Vape", "Category": "Live Resin Cart", "Global Subcategories": "Live Resin - Cartridge"},
            {"Master category": "Edible", "Category": "Gummy", "Global Subcategories": "Gummies"}]
    r = run("Acme Gelato cart 0.5g", act=vape, categories=cats, line_categories={"1": "Moon Cart"})
    t.check("NEW_CATEGORY: a directed Category absent from the taxonomy is the STOP",
            r["verdict"] == "NEW_CATEGORY" and "Moon Cart" in r["sibling_reason"], f"{r['verdict']} {r['sibling_reason']}")
    r = run("Acme Gelato cart 0.5g", act=vape, categories=cats, line_categories={"1": "Live Resin Cart"})
    t.check("QUIET: a directed Category IN the taxonomy places the line -> NEW_PL + CATEGORY_DIRECTED, nearest item copied",
            r["verdict"] == "NEW_PL" and "CATEGORY_DIRECTED" in r["flags"].split(";") and r["copy_source_sku"] == "7"
            and r["lane_Category"] == "Live Resin Cart", f"{r['verdict']} {r['flags']} {r['copy_source_sku']}")
    r = run("Acme Gelato thing 0.5g", act=vape, categories=cats, line_categories={"1": "Gummy"})
    t.check("a directed Category with no same-brand item copies cross-brand in that Category",
            r["verdict"] == "NEW_PL" and r["copy_source_sku"] == "8" and "CROSS_BRAND_COPY" in r["flags"], f"{r['verdict']} {r['copy_source_sku']}")
    stale = [c for c in cats if c["Category"] != "Live Resin Cart"]
    r = run("Acme Gelato cart 0.5g", act=vape, categories=stale)
    t.check("NEW_CATEGORY: a Category read from an item but missing from the categories export (stale export)",
            r["verdict"] == "NEW_CATEGORY" and "export does not carry" in r["sibling_reason"], r["verdict"])
    t.check("QUIET: with the catalog standing in for the taxonomy, an item's Category always exists",
            run("Acme Gelato cart 0.5g", act=vape)["verdict"] == "NEW_PL")
    t.check("NEW_PL: a strain-bearing new line with no Strain record is STRAIN_MISSING",
            run("Acme Mystery Haze cart 0.5g", act=vape)["verdict"] == "STRAIN_MISSING")
    # --- NEW_BRAND is a CREATE: the Brand record first, then the closest copy; a Brand record with no item is NEW_PL ---
    r = run("Zed Gelato preroll 1g", vendor="Other Co")
    t.check("NEW_BRAND fires with BRAND_NAME_UNREAD when nothing spells the brand; a copy source is still found",
            r["verdict"] == "NEW_BRAND" and "BRAND_NAME_UNREAD" in r["flags"].split(";") and r["copy_source_sku"] == "1"
            and r["lane_Brand"] == "" and r["action"].startswith("CREATE"), f"{r['verdict']} {r['flags']} {r['copy_source_sku']} {r['lane_Brand']!r}")
    r = run("Zed Gelato preroll 1g", vendor="Other Co", line_brands={"1": "Zed"})
    t.check("NEW_BRAND with --line-brand: a CREATE, cross-brand copy, Brand = the operator's spelling, name drafted",
            r["verdict"] == "NEW_BRAND" and "BRAND_NAME_UNREAD" not in r["flags"] and "CROSS_BRAND_COPY" in r["flags"]
            and r["lane_Brand"] == "Zed" and r["create_name_FINAL"] == "Zed | Pre-Roll | Gelato | 1g" and r["tags"] == DEFAULT_NEW_LINE_TAG,
            f"{r['verdict']} {r['flags']} {r['lane_Brand']} {r['create_name_FINAL']!r}")
    t.check("NEW_BRAND names the Brand record step (R30, R121) in its reason",
            "Brand record first" in r["sibling_reason"] and "R121" in r["sibling_reason"])
    r = run("Zed Gelato preroll 1g", vendor="Other Co", line_brands={"1": "Zed"}, brands=[{"Display name": "Zed"}])
    t.check("a Brand record with no item is NOT a new brand: NEW_PL, cross-brand copy under that brand",
            r["verdict"] == "NEW_PL" and r["lane_Brand"] == "Zed" and "CROSS_BRAND_COPY" in r["flags"], f"{r['verdict']} {r['lane_Brand']}")
    r = run("DoubleAcme Gelato preroll 1g", vendor="Other Co", line_brands={"1": "Acme"})
    t.check("--line-brand naming a catalog brand matches under it (a spelling the line got wrong)",
            r["verdict"] == "NEW_ITEM_WITH_SIBLING" and r["copy_source_sku"] == "1", f"{r['verdict']} {r['copy_source_sku']}")
    t.check("QUIET: the vendor names a single brand", run("Gelato preroll 1g")["verdict"] == "NEW_ITEM_WITH_SIBLING")
    t.check("DOSE_UNREAD fires", "DOSE_UNREAD" in run("Acme Gelato preroll")["flags"])
    two = active + [_item("4", "Acme | Pre-Roll | Blue Dream | 1g", pid="14")]
    t.check("AMBIGUOUS_MATCH fires on two equal items", "AMBIGUOUS_MATCH" in run("Acme Blue Dream preroll 1g", act=two)["flags"])
    _, d = match([{"description": "Acme Blue Dream preroll 1g", "vendor": "x", "units_total": "", "unit_cost": "4.5"}],
                 active, retired, strains)
    t.check("FIRES: BAD_LINE on a line with no units", len(d) == 1)
    t.check("v5 has 56 columns (45 + 7 + parse_source + package_id + unretire_set + image_source); every v3 column keeps its place",
            len(INTAKE_COLS) == 56 and len(V2_COLS) == 45 and INTAKE_COLS[:54] == V3_COLS
            and INTAKE_COLS[-4:] == ["parse_source", "package_id", "unretire_set", "image_source"], str(len(INTAKE_COLS)))
    t.check("image_source is blank on every verdict here (the create step writes it)",
            run("Acme Blue Dream preroll 1g")["image_source"] == "" and "image_source" in run("Acme Blue Dream preroll 1g"))
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
    t.check("QUIET: FORM_UNREAD off on two candidates -> an unplaced line is NEW_PL + CATEGORY_UNREAD (no copy source)",
            r["verdict"] == "NEW_PL" and "FORM_UNREAD" not in r["flags"] and "CATEGORY_UNREAD" in r["flags"].split(";")
            and r["copy_source_sku"] == "", f"{r['verdict']} {r['flags']}")
    r = run("Acme | Lime Sorbet | Flavor Line | Cart | 2.0g | Hybrid", act=aio)
    t.check("QUIET: FORM_UNREAD off when the line names another form word (cart) that no catalog form ends in -> NEW_PL + CATEGORY_UNREAD",
            r["verdict"] == "NEW_PL" and "FORM_UNREAD" not in r["flags"] and "CATEGORY_UNREAD" in r["flags"].split(";"), f"{r['verdict']} {r['flags']}")
    t.check("QUIET: FORM_UNREAD off on a full match", "FORM_UNREAD" not in run("Acme Blue Dream preroll 1g")["flags"])
    t.check("ratio_key: cannabinoid order + case are unordered",
            ratio_key("1:1 CBD:THC") == ratio_key("1:1 THC:CBD") and ratio_key("1:1:1 THC:CBC:CBG") == ratio_key("1:1:1 THC:CBG:CBC")
            and ratio_key("1:1 THC:THCv") == ratio_key("1:1 THC:THCV"))
    t.check("QUIET: ratio_key keeps the counts paired (2:1 CBD:THC != 2:1 THC:CBD)",
            ratio_key("2:1 CBD:THC") != ratio_key("2:1 THC:CBD") and ratio_key("10mg x 10pk") is None)
    fl = flavor_led("Acme | (I) Sour Cherry Gummies 1:1 CBD:THC | Edibles | 100mg", ["Gummies"])
    t.check("flavor_led: letter -> type, flavor minus form word and ratio", fl == ("Indica", "Sour Cherry", ratio_key("1:1 THC:CBD")), str(fl))
    t.check("QUIET: flavor_led off a line with no leading strain letter", flavor_led("Acme Sour Cherry Gummies (I)", ["Gummies"]) is None)
    choc = [_item("41", "Acme | Chocolates | Mint Cake (THC) | 0.1g", pid="41", cat="Chocolate", Strain="THC", Flavor="Mint Cake",
                  Tags="ITM - Discontinue", **{"Master category": "Edible", "Strain Type": "Hybrid"})]
    r = run("Acme Hybrid Fast-Acting Mint Cake chocolates 0.1g", ret=retired + choc)
    t.check("a flavored item matches on its Flavor cell: the line prints the flavor, not our paren -> RETIRED_MATCH",
            r["verdict"] == "RETIRED_MATCH" and r["copy_source_sku"] == "41", f"{r['verdict']} {r['copy_source_sku']}")
    t.check("QUIET: the Flavor match needs the stated type to agree (Sativa vs a Hybrid item)",
            run("Acme Sativa Mint Cake chocolates 0.1g", ret=retired + choc)["verdict"] != "RETIRED_MATCH")
    t.check("QUIET: no Flavor match on a different flavor", run("Acme Hybrid Lemon Cake chocolates 0.1g", ret=retired + choc)["verdict"] != "RETIRED_MATCH")
    t.check("QUIET: a ratio line never matches a plain flavored item on the Flavor cell",
            run("Acme Mint Cake 2:1 CBD:THC chocolates 0.1g", ret=retired + choc)["verdict"] != "RETIRED_MATCH")
    ratio = dict(strains, THC={"type": "Hybrid", "id": ""}, **{"Restore (4:1 CBD:THC)": {"type": "Hybrid", "id": ""}})
    gum = active + [_item("42", "Acme | Gummies | Mango (Hybrid) | 0.1g", pid="42", cat="Gummy", Strain="Hybrid", Flavor="Mango",
                          **{"Master category": "Edible"})]
    r = run("Acme Pomegranate 4:1 CBD:THC gummies 0.1g", act=gum, st=ratio)
    t.check("a ratio line takes the ONE record with that ratio key, never the bare `THC` record",
            r["strain"] == "Restore (4:1 CBD:THC)", r["strain"])
    r = run("Acme Pomegranate 4:1 THC:CBG gummies 0.1g", act=gum, st=ratio)
    t.check("QUIET: a ratio with no record is STRAIN_MISSING, not a cannabinoid word", r["verdict"] == "STRAIN_MISSING" and r["strain"] == "")
    typed = dict(strains, Indica={"type": "Indica", "id": ""}, Hybrid={"type": "Hybrid", "id": ""})
    r = run("Acme Moon Man preroll 1g Indica", st=typed)
    t.check("a bare Strain Type word is never a smokable's Strain: STRAIN_MISSING, the type stated",
            r["verdict"] == "STRAIN_MISSING" and r["strain"] == "" and "prints Type 'Indica'" in r["sibling_reason"],
            f"{r['verdict']} {r['strain']!r}")
    flav = active + [_item("31", "Acme | Chocolates | Mint Cake (Hybrid) | 0.1g", pid="31", cat="Chocolate", Strain="Hybrid",
                           Flavor="Mint Cake", **{"Master category": "Edible"})]
    r = run("Acme Hybrid Lemon Cake chocolates 0.1g", act=flav, st=typed)
    t.check("on a FLAVORED lane the stated type record IS the Strain; the body is owed to the operator (no name drafted)",
            r["verdict"] == "NEW_ITEM_WITH_SIBLING" and r["strain"] == "Hybrid" and r["create_name_FINAL"] == ""
            and "name body = <Flavor> (Hybrid)" in r["sibling_reason"] and "FLAVOR_TO_SET" in r["flags"],
            f"{r['verdict']} {r['strain']!r} {r['create_name_FINAL']!r}")
    r = run("Acme Hybrid Gelato chocolates 0.1g", act=flav, st=typed)
    t.check("the stated type wins over a longer cultivar phrase on a flavored lane", r["strain"] == "Hybrid", r["strain"])
    t.check("line_type reads a printed word or letter, never guesses",
            line_type("x Sativa y") == "Sativa" and line_type("x (I) y") == "Indica" and line_type("x Hybridize") == "" and line_type("x") == "")
    return t.done()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
