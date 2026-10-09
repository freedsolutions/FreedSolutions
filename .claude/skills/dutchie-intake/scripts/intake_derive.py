"""intake_derive.py - the create-stop fields canon DERIVES, so the Operator never types them (R1-R3, R6, R7, R34, R42, R66, R129).

  python intake_derive.py --classes <fl-eq-classes.toml> [--mc <Master category>] [--grams <g>] [--unit g|mg] [--pack <n>]
  python intake_derive.py --selftest

The stop keeps only product facts the line or the vendor must supply. Everything a rule computes from those
facts is computed here, once, and cited by rule id in the intake row (`derived` column), the STOP text and
the plan row's provenance. `intake_match.py` calls it on every NEW_PL / NEW_BRAND copy; `intake_plan.py`
re-derives from the row's FINAL cells, so a Product grams correction at the stop moves Flower equiv with it.

The class map is the tenant's own file (pointer `FL EQ classes:` in `## Intake Pointers`, a TOML whose
`[master.<Master category>]` tables carry `fl_eq = "<class>"`). The skill names no Master category and no
tenant; the class vocabulary is the contract:

  product_g_x<k>     Flower equiv = Product grams x k            (R3; k = 1 is the flower class, k > 1 cites R1)
  thc_g_x<k>         Flower equiv = THC grams x k                (R3, R5) - only when the line PRINTS the dose in mg;
                                                                 a g-only line in this class stays at the stop
  composite          (g - conc) + conc x <concentrate factor>    (R1 R2 R3) - the concentrate grams are a product FACT
                                                                 (R2): `--conc-grams <line>=<g>`; absent, 30 % of the
                                                                 grams by default and the row STOPS on it (CONC_GRAMS_TO_SET)
  sentinel_<v>       Flower equiv = v                            (R6: the Topical sentinel)
  none               Flower equiv blank                          (R6: non-cannabis / no class)

The concentrate factor of the composite class is read from the map itself: the one `product_g_x<k>` with
k > 1 (two different k values = the map is ambiguous and the composite class stays at the stop).

Servings per Unit = the pack count the line prints (R34: the pack count IS Servings per Unit; R31: a single is
an explicit 1, never assumed) - a line that prints no count keeps the field at the stop.
CBD content = blank unless the Master category is the CBD one (R66) - on a CBD item the dose is a product fact
and stays at the stop.
The name's {Dose} segment (R42: `Ng`, `Nmg` or `N x Mpk`) takes its unit from the class (R7: the g-list is the
product-grams classes and the composite class; the THC-grams and sentinel classes are mg; `none` keeps the
unit the line printed) and its pack from the pack count (R34).
The vendor dose read (R129, `intake_match.dose_read`) rides in as `read`: a per-piece or package-total read of an mg
figure beside a count is cited on the row (`Product grams: 0.1g (R129: ...)`), and an mg figure with NO count on a
THC-grams-class line leaves the package total unsettled - Product grams, Flower equiv and the dose segment stay at the
stop (flag DOSE_UNREAD). The plan re-derives with no `read`: by then the Operator has settled the count.
"""
import os
import re
import sys
import tomllib

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from intake_common import EXIT_ABORT, EXIT_OK, Selftest, get_flag, grams_of, norm  # noqa: E402

CBD_MC = "CBD"             # R66 keys on the Master category named CBD; a tenant may override via `--cbd-mc`
DEFAULT_CONC_SHARE = 0.3   # R2: absent a label / COA value, 30 % concentrate to 70 % flower
FIELDS = ("Product grams", "Flower equiv", "Servings per Unit", "CBD content", "Dose")   # the derivable create-stop fields
STOP_FLAG = "CONC_GRAMS_TO_SET"   # R2 STOP: the composite class needs the concentrate grams
DOSE_STOP_FLAG = "DOSE_UNREAD"    # R129 STOP: an mg figure with no count on a THC-grams-class line - the total is unsettled

_PRODUCT = re.compile(r"^product_g_x(\d+(?:\.\d+)?)$")
_THC = re.compile(r"^thc_g_x(\d+(?:\.\d+)?)$")
_SENTINEL = re.compile(r"^sentinel_(\d+(?:\.\d+)?)$")


def fmt_g(x):
    """`2.8g`, `0.0001g`, `5.6g` - the spelling the Catalog export prints."""
    return f"{x:.6f}".rstrip("0").rstrip(".") + "g"


CAT_PREFIX = "cat:"   # a Category-level exception's key in the class / cap maps (R6, R130; intake_pointers.CAT_PREFIX)


def class_of(classes, mc, cat=None):
    """(class | None, the Category it came from | None): an enumerated Category exception first, else the master's."""
    if cat and (classes or {}).get(CAT_PREFIX + norm(cat)):
        return classes[CAT_PREFIX + norm(cat)], cat
    return ((classes or {}).get(norm(mc)) if mc else None), None


def cap_name(rd):
    """How a dose-read cite names its cap: the target Master category's (R130) or the generic no-map fallback."""
    cap = fmt_mg(rd["cap_mg"])
    return f"{rd['mc']} {cap} package cap (R130)" if rd.get("mc") else f"{cap} cap (generic fallback: no class-map cap)"


def load_classes(path):
    """{norm(Master category): class string}, plus {CAT_PREFIX + norm(Category): class} for each enumerated
    Category-level exception that names one (`[limit_exception."<Category>"]` fl_eq, R6 / R130), read BEFORE its
    master's (class_of). Raises ValueError on an unreadable file or a master table with no fl_eq."""
    with open(path, "rb") as f:
        data = tomllib.load(f)
    masters = data.get("master")
    if not isinstance(masters, dict) or not masters:
        raise ValueError(f"{path}: no [master.<Master category>] tables")
    out = {}
    for mc, body in masters.items():
        cls = (body or {}).get("fl_eq") if isinstance(body, dict) else None
        if not isinstance(cls, str) or not cls.strip():
            raise ValueError(f"{path}: [master.{mc}] has no fl_eq class")
        out[norm(mc)] = cls.strip()
    for cat, body in (data.get("limit_exception") or {}).items():
        cls = (body or {}).get("fl_eq") if isinstance(body, dict) else None
        if cls is not None and (not isinstance(cls, str) or not cls.strip()):
            raise ValueError(f"{path}: [limit_exception.{cat}] fl_eq is not a class string")
        if cls:
            out[CAT_PREFIX + norm(cat)] = cls.strip()
    return out


def class_kind(cls):
    """('product', k) | ('thc', k) | ('composite', None) | ('sentinel', v) | ('none', None) | (None, None) for an unknown class."""
    if cls == "composite":
        return "composite", None
    if cls == "none":
        return "none", None
    for kind, rx in (("product", _PRODUCT), ("thc", _THC), ("sentinel", _SENTINEL)):
        m = rx.match(cls or "")
        if m:
            return kind, float(m.group(1))
    return None, None


def conc_factor(classes):
    """The composite class's concentrate multiplier: the one product_g_x<k> with k > 1; None when absent or ambiguous."""
    ks = sorted({k for c in classes.values() for kind, k in [class_kind(c)] if kind == "product" and k and k > 1})
    return ks[0] if len(ks) == 1 else None


def fmt_mg(x):
    """`10 mg`, `2.5 mg` - the spelling the cites use."""
    return f"{x:.4f}".rstrip("0").rstrip(".") + " mg"


def derive(mc, grams, unit=None, pack=None, classes=None, conc=None, cbd_mc=CBD_MC, read=None, cat=None):
    """Pure. mc = the target Master category; grams = total Product grams (float or '1g'); unit = the unit the
    line printed ('g' | 'mg' | None); pack = the pack count the line printed (int or None); classes = the
    class map (None = no pointer); conc = concentrate grams the operator supplied (float / '0.3g' / None);
    read = the vendor dose read (intake_match.dose_read's dict; None = the plan's re-derive, the count settled).

    -> {"values": {lane column: value}, "cite": {field: text}, "stops": {field: why}, "flags": [...], "class": cls}
    A field in `values` is DERIVED and leaves the stop; a field in `stops` stays at the stop with its reason.
    """
    g = grams_of(grams) if isinstance(grams, str) else grams
    c_in = grams_of(conc) if isinstance(conc, str) else conc
    values, cite, stops, flags = {}, {}, {}, []
    cls, by_cat = class_of(classes, mc, cat)   # cat = the row's Category: an enumerated exception wins (R6, R130)
    via = f" by Category {by_cat} (R6 R130)" if by_cat else ""
    kind, k = class_kind(cls) if cls else (None, None)
    # --- the vendor dose read (R129) -----------------------------------------------------------------------
    rd = read or {}
    unsettled = kind == "thc" and rd.get("reading") == "single" and rd.get("unit") == "mg" and g is not None
    if unsettled:
        flags.append(DOSE_STOP_FLAG)
        stops["Product grams"] = (f"an mg figure with no pack count: {fmt_g(g)} is the figure read as the package total; if it is "
                                  f"per piece, set grams = piece x count and Servings per Unit from the label / COA (R129)")
    elif g is not None and rd.get("reading") == "package total":
        cite["Product grams"] = (f"{fmt_g(g)} (R129: package total: a per-piece read would be {fmt_mg(rd['over_mg'])} over the "
                                 f"{cap_name(rd)}; {fmt_mg(rd['piece_mg'])[:-3]} mg x {rd['count']})")
    elif g is not None and rd.get("reading") == "per piece" and rd.get("unit") == "mg":
        cite["Product grams"] = (f"{fmt_g(g)} (R129: per piece: {fmt_mg(rd['piece_mg'])[:-3]} mg x {rd['count']} = "
                                 f"{fmt_mg(g * 1000.0)} " + (f"fits the {cap_name(rd)})" if rd.get("cap_mg") is not None
                                                             else f"- {rd.get('mc')} carries no package cap (R130))"))
    # --- Flower equiv (R1-R3, R6) --------------------------------------------------------------------------
    if classes is None:
        stops["Flower equiv"] = "no `FL EQ classes` pointer: the lane cannot derive it"
    elif not mc:
        stops["Flower equiv"] = "no Master category on the row"
    elif cls is None:
        stops["Flower equiv"] = f"Master category {mc!r} has no fl_eq class in the map"
    elif kind is None:
        stops["Flower equiv"] = f"fl_eq class {cls!r} is unknown to the lane"
    elif kind == "none":
        values["lane_FlowerEquiv"], cite["Flower equiv"] = "", f"blank (R6: class none)"
    elif kind == "sentinel":
        values["lane_FlowerEquiv"], cite["Flower equiv"] = fmt_g(k), f"{fmt_g(k)} (R6: sentinel)"
    elif g is None:
        stops["Flower equiv"] = "no grams read from the line (DOSE_UNREAD)"
    elif kind == "product":
        values["lane_FlowerEquiv"] = fmt_g(g * k)
        cite["Flower equiv"] = f"{values['lane_FlowerEquiv']} ({'R1 R3' if k != 1 else 'R3'}: {cls}, grams {fmt_g(g)})"
    elif kind == "thc":
        if unsettled:
            stops["Flower equiv"] = "the package total is unsettled: an mg figure with no count (R129)"
        elif unit != "mg":
            stops["Flower equiv"] = f"class {cls} needs THC mg and the line prints none (R3 R5)"
        else:
            values["lane_FlowerEquiv"] = fmt_g(g * k)
            cite["Flower equiv"] = f"{values['lane_FlowerEquiv']} (R3 R5: {cls}{via}, THC {fmt_g(g)})"
    else:  # composite
        factor = conc_factor(classes)
        if factor is None:
            stops["Flower equiv"] = "composite class: the map has no single product_g_x<k> (k > 1) concentrate factor"
        else:
            c = c_in if c_in is not None else round(g * DEFAULT_CONC_SHARE, 6)
            if c < 0 or c > g:
                stops["Flower equiv"] = f"concentrate grams {fmt_g(c)} outside 0..{fmt_g(g)} (R4)"
            else:
                values["lane_FlowerEquiv"] = fmt_g((g - c) + c * factor)
                how = "operator" if c_in is not None else f"R2 default {int(DEFAULT_CONC_SHARE * 100)} %"
                cite["Flower equiv"] = (f"{values['lane_FlowerEquiv']} (R1 R2 R3: composite, grams {fmt_g(g)}, "
                                        f"conc {fmt_g(c)} {how})")
                if c_in is None:
                    flags.append(STOP_FLAG)
                    stops["concentrate grams"] = (f"a product fact (R2): the label / COA value, else the {int(DEFAULT_CONC_SHARE * 100)} % "
                                                  f"default stands - `--conc-grams <line_no>=<g>` re-derives")
    # --- Servings per Unit (R34, R31) -----------------------------------------------------------------------
    if pack is not None and pack >= 1:
        values["lane_ServingsPerUnit"], cite["Servings per Unit"] = str(int(pack)), f"{int(pack)} (R34: the pack count the line prints)"
    else:
        stops["Servings per Unit"] = "the line prints no pack count (R31: a single is an explicit 1, never assumed)"
    # --- CBD content (R66) ----------------------------------------------------------------------------------
    if mc and norm(mc) == norm(cbd_mc):
        stops["CBD content"] = "the CBD dose is a product fact on a CBD item (R66)"
    elif mc:
        values["lane_CBDContent"], cite["CBD content"] = "", f"blank (R66: Master category is not {cbd_mc})"
    # --- the name's {Dose} segment (R42 grammar, R7 unit by class, R34 pack) -------------------------------
    seg = None if unsettled else dose_segment(kind, g, unit, pack)
    if seg:
        values["dose_segment"], cite["Dose"] = seg, f"{seg} (R7 R42{' R34' if pack and pack > 1 else ''})"
    return {"values": values, "cite": cite, "stops": stops, "flags": flags, "class": cls}


def dose_segment(kind, g, unit=None, pack=None):
    """`0.5g x 5pk`, `10mg x 10pk`, `1g`, `100mg` - the R42 {Dose} segment. None when there are no grams."""
    if g is None:
        return None
    mg = (kind in ("thc", "sentinel")) or (kind in (None, "none") and unit == "mg")
    n = int(pack) if pack and pack > 1 else 1
    piece = g / n
    txt = f"{piece * 1000:.3f}".rstrip("0").rstrip(".") + "mg" if mg else fmt_g(piece)
    return f"{txt} x {n}pk" if n > 1 else txt


def describe(res):
    """The `derived` cell and the two STOP clauses: (derived text, [derived field names], [stop clauses])."""
    derived = "; ".join(f"{f}: {res['cite'][f]}" for f in FIELDS if f in res["cite"])
    stops = [f"{f} ({why})" for f, why in res["stops"].items()]
    return derived, [f for f in FIELDS if f in res["cite"]], stops


def parse_derived(derived_cell):
    """A `derived` cell -> {field: cite text}. The grammar is `Field: text; Field: text` over FIELDS; a cell written
    by another version, or blank, reads as {} - never as a derivation."""
    out = {}
    for m in re.finditer(r"(" + "|".join(re.escape(f) for f in FIELDS) + r"): (.*?)(?=; (?:"
                         + "|".join(re.escape(f) for f in FIELDS) + r"): |$)", derived_cell or ""):
        out[m.group(1)] = m.group(2)
    return out


def conc_of(derived_cell):
    """The concentrate grams a `derived` cell records, as a float; None when the cell names none."""
    m = re.search(r"conc (\d+(?:\.\d+)?)g", derived_cell or "")
    return float(m.group(1)) if m else None


SAMPLE_TOML = b"""
# synthetic class map (selftest only)
[master."Alpha Flower"]
fl_eq = "product_g_x1"
[master.Beta]
fl_eq = "product_g_x5.6"   # the concentrate class
[master.Gamma]
fl_eq = "thc_g_x56"
[master.Delta]
fl_eq = "composite"
[master.Epsilon]
fl_eq = "sentinel_0.0001"
[master.CBD]
fl_eq = "none"
[master.Zeta]
fl_eq = "none"
"""


def selftest():
    import tempfile
    t = Selftest("intake_derive")
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "classes.toml")
        open(p, "wb").write(SAMPLE_TOML)
        cl = load_classes(p)
        t.check("the class map parses, keyed by the normalized Master category", cl.get("alpha flower") == "product_g_x1" and cl["beta"] == "product_g_x5.6")
        bad = os.path.join(d, "bad.toml")
        open(bad, "wb").write(b'[master.Beta]\ntax = "Cannabis"\n')
        t.check("FIRES: a master with no fl_eq is refused", _raises(lambda: load_classes(bad)))
        open(bad, "wb").write(b'schema_version = 1\n')
        t.check("FIRES: a file with no master tables is refused", _raises(lambda: load_classes(bad)))
    t.check("the concentrate factor is the one product_g_x<k> with k > 1", conc_factor(cl) == 5.6)
    t.check("FIRES: two concentrate factors = none", conc_factor(dict(cl, eta="product_g_x4")) is None)
    # Flower equiv per class
    r = derive("Alpha Flower", "2.5g", "g", 5, cl)
    t.check("product_g_x1: Flower equiv = grams (R3), cited", r["values"]["lane_FlowerEquiv"] == "2.5g" and "R3" in r["cite"]["Flower equiv"]
            and "Flower equiv" not in r["stops"], str(r))
    r = derive("Beta", 1.0, "g", None, cl)
    t.check("product_g_x5.6: grams x 5.6 (R1 R3)", r["values"]["lane_FlowerEquiv"] == "5.6g" and "R1 R3" in r["cite"]["Flower equiv"], str(r))
    t.check("FIRES: 0.5g derives 2.8g, never the source's value", derive("Beta", "0.5g", "g", None, cl)["values"]["lane_FlowerEquiv"] == "2.8g")
    r = derive("Gamma", 0.1, "mg", 10, cl)
    t.check("thc_g_x56 on an mg line: THC grams x 56 (R3 R5)", r["values"]["lane_FlowerEquiv"] == "5.6g" and "R5" in r["cite"]["Flower equiv"], str(r))
    r = derive("Gamma", 0.1, "g", 10, cl)
    t.check("FIRES: thc class on a g-only line stays at the stop", "lane_FlowerEquiv" not in r["values"] and "THC mg" in r["stops"]["Flower equiv"], str(r))
    r = derive("Delta", 1.0, "g", None, cl)
    t.check("composite, no conc: 30 % default (R2) -> (0.7) + 0.3 x 5.6 = 2.38g, STOP flag on the concentrate grams",
            r["values"]["lane_FlowerEquiv"] == "2.38g" and STOP_FLAG in r["flags"] and "concentrate grams" in r["stops"]
            and "default 30 %" in r["cite"]["Flower equiv"], str(r))
    r = derive("Delta", 1.0, "g", None, cl, conc="0.5g")
    t.check("composite with operator conc: (0.5) + 0.5 x 5.6 = 3.3g, no STOP, cite says operator",
            r["values"]["lane_FlowerEquiv"] == "3.3g" and not r["flags"] and "concentrate grams" not in r["stops"]
            and "operator" in r["cite"]["Flower equiv"], str(r))
    t.check("FIRES: conc above the grams is refused (R4)", "Flower equiv" in derive("Delta", 1.0, "g", None, cl, conc=1.5)["stops"])
    t.check("FIRES: composite with no concentrate factor in the map stays at the stop",
            "Flower equiv" in derive("Delta", 1.0, "g", None, {"delta": "composite", "alpha": "product_g_x1"})["stops"])
    r = derive("Epsilon", 0.05, "mg", None, cl)
    t.check("sentinel: 0.0001g (R6) with or without grams", r["values"]["lane_FlowerEquiv"] == "0.0001g"
            and derive("Epsilon", None, None, None, cl)["values"]["lane_FlowerEquiv"] == "0.0001g", str(r))
    t.check("none: blank Flower equiv (R6)", derive("Zeta", 1.0, "g", None, cl)["values"]["lane_FlowerEquiv"] == "")
    t.check("QUIET: no class map -> Flower equiv stays at the stop, named", "pointer" in derive("Beta", 1.0, "g", None, None)["stops"]["Flower equiv"])
    t.check("QUIET: a Master category outside the map stays at the stop", "no fl_eq class" in derive("Omega", 1.0, "g", None, cl)["stops"]["Flower equiv"])
    t.check("QUIET: an unknown class word stays at the stop", "unknown" in derive("X", 1.0, "g", None, {"x": "magic"})["stops"]["Flower equiv"])
    t.check("QUIET: no grams in a grams class stays at the stop", "DOSE_UNREAD" in derive("Beta", None, None, None, cl)["stops"]["Flower equiv"])
    # Servings per Unit
    t.check("Servings = the printed pack count (R34)", derive("Beta", 2.5, "g", 5, cl)["values"]["lane_ServingsPerUnit"] == "5")
    t.check("QUIET: no pack count printed -> Servings stays at the stop (R31)", "Servings per Unit" in derive("Beta", 1.0, "g", None, cl)["stops"])
    # CBD content
    t.check("CBD content blank off the CBD master (R66)", derive("Beta", 1.0, "g", None, cl)["values"]["lane_CBDContent"] == "")
    t.check("FIRES: on the CBD master the dose stays at the stop", "CBD content" in derive("CBD", None, "mg", None, cl)["stops"]
            and "lane_CBDContent" not in derive("CBD", None, "mg", None, cl)["values"])
    # Dose segment
    t.check("Dose: g class, pack -> `0.5g x 5pk`", derive("Alpha Flower", 2.5, "g", 5, cl)["values"]["dose_segment"] == "0.5g x 5pk")
    t.check("Dose: g class single -> `1g`", derive("Beta", 1.0, "g", None, cl)["values"]["dose_segment"] == "1g")
    t.check("Dose: thc class -> mg per piece `10mg x 10pk` (R7)", derive("Gamma", 0.1, "mg", 10, cl)["values"]["dose_segment"] == "10mg x 10pk")
    t.check("Dose: sentinel class prints mg even on a g line", derive("Epsilon", 0.05, "g", None, cl)["values"]["dose_segment"] == "50mg")
    t.check("Dose: class none keeps the printed unit", derive("Zeta", 0.1, "mg", None, cl)["values"]["dose_segment"] == "100mg"
            and derive("Zeta", 3.5, "g", None, cl)["values"]["dose_segment"] == "3.5g")
    t.check("Dose: a pack count of 1 prints a bare single", dose_segment("product", 3.5, "g", 1) == "3.5g")
    # describe / conc_of
    d, fields, stops = describe(derive("Delta", 1.0, "g", 2, cl))
    t.check("describe: the derived cell names each field with its cite", d.startswith("Flower equiv: 2.38g (R1 R2 R3") and "Servings per Unit: 2 (R34" in d
            and fields == ["Flower equiv", "Servings per Unit", "CBD content", "Dose"], d)
    # the vendor dose read (R129)
    tot = {"total": 0.1, "reading": "package total", "unit": "mg", "count": 10, "piece_mg": 10.0, "cap_mg": 100, "over_mg": 900.0}
    r = derive("Gamma", 0.1, "mg", 10, cl, read=tot)
    t.check("R129: a package-total read is cited on Product grams, and the THC class derives on that total (0.1 g x 56)",
            r["cite"]["Product grams"] == "0.1g (R129: package total: a per-piece read would be 900 mg over the 100 mg cap (generic fallback: no class-map cap); 10 mg x 10)"
            and r["values"]["lane_FlowerEquiv"] == "5.6g" and r["values"]["dose_segment"] == "10mg x 10pk" and not r["flags"], str(r))
    pp = dict(tot, reading="per piece", over_mg=None)
    r = derive("Gamma", 0.1, "mg", 10, cl, read=pp)
    t.check("R129: a per-piece read is cited with the fit", r["cite"]["Product grams"] == "0.1g (R129: per piece: 10 mg x 10 = 100 mg fits the 100 mg cap (generic fallback: no class-map cap))", str(r["cite"]))
    rc = derive("Epsilon", 0.5, "mg", 2, dict(cl, **{CAT_PREFIX + "patch": "thc_g_x5.6"}), cat="Patch")
    t.check("R6 R130: an enumerated Category exception's class beats its master's sentinel - THC x 5.6, cited by Category",
            rc["values"].get("lane_FlowerEquiv") == "2.8g" and "by Category Patch (R6 R130)" in rc["cite"]["Flower equiv"], str(rc["cite"]))
    t.check("QUIET: another Category under the same master keeps the master's sentinel",
            derive("Epsilon", 0.5, "mg", 2, dict(cl, **{CAT_PREFIX + "patch": "thc_g_x5.6"}), cat="Balm")["values"]["lane_FlowerEquiv"] == "0.0001g")
    r3 = derive("Gamma", 0.1, "mg", 10, cl, read=dict(tot, mc="Gamma"))
    t.check("R130: a package-total read under a class-map cap names the Master category and its cap",
            r3["cite"]["Product grams"] == "0.1g (R129: package total: a per-piece read would be 900 mg over the Gamma 100 mg package cap (R130); 10 mg x 10)", str(r3["cite"]))
    r3 = derive("Gamma", 0.5, "mg", 2, cl, read={"total": 0.5, "reading": "per piece", "unit": "mg", "count": 2, "piece_mg": 250.0,
                                                "cap_mg": None, "over_mg": None, "mc": "Gamma"})
    t.check("R130: a master with no cap reads per piece and the cite says the master carries none",
            r3["cite"]["Product grams"] == "0.5g (R129: per piece: 250 mg x 2 = 500 mg - Gamma carries no package cap (R130))", str(r3["cite"]))
    d2, fields2, _ = describe(r)
    t.check("describe: Product grams leads the cell when the read is cited", d2.startswith("Product grams: 0.1g (R129") and fields2[0] == "Product grams"
            and parse_derived(d2)["Product grams"].startswith("0.1g (R129: per piece"), d2)
    sg = {"total": 0.1, "reading": "single", "unit": "mg", "count": None, "piece_mg": None, "cap_mg": 100, "over_mg": None}
    r = derive("Gamma", 0.1, "mg", None, cl, read=sg)
    t.check("FIRES (R129 STOP): an mg figure with no count on the THC class - DOSE_UNREAD, Product grams + Flower equiv at the stop, no dose segment",
            DOSE_STOP_FLAG in r["flags"] and "Product grams" in r["stops"] and "unsettled" in r["stops"]["Flower equiv"]
            and "lane_FlowerEquiv" not in r["values"] and "dose_segment" not in r["values"] and "Product grams" not in r["cite"], str(r))
    t.check("QUIET: the same read on a product-grams class derives as before (the cap is an mg-class test)",
            "lane_FlowerEquiv" in derive("Beta", 0.1, "mg", None, cl, read=sg)["values"] and not derive("Beta", 0.1, "mg", None, cl, read=sg)["flags"])
    t.check("QUIET: the plan's re-derive (no read) on the THC class derives from the row's grams - the count is settled by then",
            derive("Gamma", 0.1, "mg", None, cl)["values"]["lane_FlowerEquiv"] == "5.6g" and "Product grams" not in derive("Gamma", 0.1, "mg", None, cl)["cite"])
    t.check("QUIET: a grams read carries no Product grams cite (R129 is an mg-line rule)",
            "Product grams" not in derive("Alpha Flower", 1.5, "g", 3, cl, read={"total": 1.5, "reading": "per piece", "unit": "g", "count": 3,
                                                                                    "piece_mg": None, "cap_mg": 100, "over_mg": None})["cite"])
    t.check("fmt_mg spells the mg cites", fmt_mg(10.0) == "10 mg" and fmt_mg(2.5) == "2.5 mg" and fmt_mg(900) == "900 mg")
    t.check("conc_of reads the concentrate grams back from the derived cell", conc_of(d) == 0.3 and conc_of("Flower equiv: 5.6g (R1 R3)") is None)
    pd = parse_derived(d)
    t.check("parse_derived splits the cell back into its fields", set(pd) == {"Flower equiv", "Servings per Unit", "CBD content", "Dose"}
            and pd["Servings per Unit"].startswith("2 (R34") and pd["Flower equiv"].startswith("2.38g (R1 R2 R3"), str(pd))
    t.check("QUIET: a blank or foreign cell parses as no derivation", parse_derived("") == {} and parse_derived("set at the stop") == {})
    t.check("describe: the stop clauses name the field and the why", any(s.startswith("concentrate grams (") for s in stops), str(stops))
    t.check("fmt_g spells the export's grams", fmt_g(5.6) == "5.6g" and fmt_g(0.0001) == "0.0001g" and fmt_g(2.0) == "2g")
    return t.done()


def _raises(fn):
    try:
        fn()
    except Exception:
        return True
    return False


def main(argv):
    if "--selftest" in argv:
        return selftest()
    p = get_flag(argv, "--classes")
    if not p:
        print(__doc__)
        return EXIT_ABORT
    try:
        cl = load_classes(p)
    except (OSError, ValueError, tomllib.TOMLDecodeError) as e:
        print(f"ABORT: {e}", file=sys.stderr)
        return EXIT_ABORT
    pack = get_flag(argv, "--pack")
    r = derive(get_flag(argv, "--mc"), get_flag(argv, "--grams"), get_flag(argv, "--unit"), int(pack) if pack else None, cl,
               conc=get_flag(argv, "--conc-grams"))
    print(f"class: {r['class']}  factor: {conc_factor(cl)}")
    for k, v in r["values"].items():
        print(f"  derived  {k:22} {v!r}")
    for f, why in r["stops"].items():
        print(f"  STOP     {f:22} {why}")
    for f in r["flags"]:
        print(f"  flag     {f}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
