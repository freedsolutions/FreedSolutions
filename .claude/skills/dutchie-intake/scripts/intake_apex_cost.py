"""intake_apex_cost.py - the Cost of a SAMPLE-ONLY new line, read from the vendor's Apex PO or catalog listing (R125).
No login, no write: it reads files and writes a NEW intake version.

  python intake_apex_cost.py --intake <intake-vN.csv> [--apex <apex-read.csv>]
                             [--program <row>=sample|display|none|deal] ... [--cost <row>=<unit cost>] ...
                             [--out-dir <dir>]
  python intake_apex_cost.py --selftest

R125 (the tenant's Dictionary states the rule; this script cites it): a new line whose EVERY package on the invoice is a
sample or a display takes its Cost from the vendor's Apex PO, else the vendor's Apex catalog listing for the same item,
named on the row; neither = STOP. The invoice's sample price is never the Cost, and a sibling brand's Cost (what a
cross-brand copy inherits) is NEVER the fallback.

Which rows. A row of a NEW LINE (intake_msrp.is_new_line: NEW_PL, NEW_BRAND, NEW_CATEGORY, NEW_LINE_FIELDS,
CROSS_BRAND_COPY, a new-line STRAIN_MISSING), grouped by product line exactly as the MSRP read groups them (brand +
form + size + process words). A row is a SAMPLE when `--program <row>=sample|display` says so, else when the invoice
line prints `sample` / `display` (the receive runner's marker), else when its invoice unit cost is <= 0.05 (the sample
price shape, R127). `--program <row>=none|deal|...` states a sellable row. The line is SAMPLE-ONLY when every row of
it is a sample; only those rows are read here. `<row>` is the intake row's number - the `#` of the STOP's verdict
table, the plan's `line_no`.

The Apex read (a session step, in the write channel, on the Operator's login, READ ONLY - never add to a cart, never
place or edit an order). For each sample-only row, the lane opens the vendor's Apex PO when one exists (the tenant's
`PO source: apex`), else searches the Apex marketplace for the same item (brand + product line + size) and reads the
vendor's listing, then TYPES what Apex prints into a NEW `<stem>-apex-read-<date>-vN.csv`:

  row, source, ref, item, read_date, price, per, units_per_case, unit_shown

  source          `po` | `catalog` | `none` (`none` = the lane looked and Apex has neither; `ref` says where it looked)
  ref             po: the Apex order / invoice number; catalog: the vendor as the listing names it; none: where looked
  item            the Apex line or listing name, as printed
  read_date       YYYY-MM-DD
  price           the Price figure Apex prints for the line or listing (no `$`)
  per             what that price is per, as printed: `case` (`$330 / Case`; a PO line whose Quantity reads `N Case`) or
                  `unit` (`$329 / Unit`; a PO line whose Quantity reads `N Unit`)
  units_per_case  the pack Apex prints (`30 U /case`, `30 units per case`, `1 Case 40 Units total` -> 40). On a `unit`
                  price: the sellable units ONE Apex unit holds - 1 normally, more when the Apex "Unit" is a case
                  (memory: an Apex "Unit" can be a case; the manifest qty proves it)
  unit_shown      the per-unit figure Apex prints beside the price, when it prints one (`at $11.00`, `$11/unit`)

Unit cost: per case -> price / units_per_case; per unit -> price, or price / units_per_case when one Apex unit holds
more than one (APEX_UNIT_IS_CASE). A PO read beats a catalog read for the same row. `--cost <row>=<unit>` is the
Operator's typed Cost (the answer to COST_UNKNOWN) and beats both.

Each sample-only row comes out with: `lane_Cost` = the Cost (blank when unknown - the sample price is not a Cost),
the flag, and - when a Cost is settled - the `derived` cell's `Cost:` entry naming its source and read date
(`Cost: 11.00 (R125: apex:catalog <item>, read 2026-10-11; $330.00 / case of 30)`). The MSRP read anchors on that Cost
(intake_msrp.py) and the plan carries the cite into the Cost row's provenance (intake_plan.py); a create row of a
sample-only line with no `Cost:` entry is REFUSED by the plan (COST_UNKNOWN): the copy would keep its source's Cost.

Flags (R125):
  COST_FROM_APEX      INFO  the Cost was read from the vendor's Apex PO or catalog listing; the source rides the row
  COST_UNKNOWN        STOP  a sample-only new line with no Apex PO or listing (or no read yet) and no typed Cost:
                            read Apex, or the Operator types `--cost <row>=<unit>`; never a sibling's Cost
  APEX_UNIT_IS_CASE   INFO  a `unit`-priced Apex line whose unit holds more than one sellable unit: divided
  APEX_PACK_UNREAD    STOP  a `case` price with no units_per_case: the pack size is unread, nothing is divided
  APEX_UNIT_MISMATCH  STOP  the computed unit differs from the per-unit figure Apex prints beside it: re-read
Exit: 0 written (STOP / INFO counts never fail) · 2 ABORT (a missing column, an unknown row, a bad value).
"""
import os
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import intake_common as C  # noqa: E402
import intake_msrp as M  # noqa: E402

SAMPLE_MAX = 0.05            # the sample price shape (receive.py's SAMPLE_MAX, R127)
INTAKE_REQUIRED = ["invoice_line", "unit_cost", "lane_Brand", "lane_MasterCategory", "lane_ProductGrams", "lane_Cost",
                   "verdict", "flags", "sibling_reason"]
APEX_COLS = ["row", "source", "ref", "item", "read_date", "price", "per", "units_per_case", "unit_shown"]
SOURCES, PERS = ("po", "catalog", "none"), ("case", "unit")
FLAGS = {"COST_FROM_APEX": ("R125", "INFO"), "COST_UNKNOWN": ("R125", "STOP"), "APEX_UNIT_IS_CASE": ("R125", "INFO"),
         "APEX_PACK_UNREAD": ("R125", "STOP"), "APEX_UNIT_MISMATCH": ("R125", "STOP")}


def marker(desc):
    """The invoice's own disposition word (`sample` / `display`), else '' - the receive runner's reading."""
    d = C.norm(desc)
    if re.search(r"(?:^| )samples?(?: |$)", d):
        return "sample"
    if re.search(r"(?:^| )display(?: |$)", d):
        return "display"
    return ""


def is_sample(r, row_no, programs=None):
    """True when intake row `row_no` is a sample or display package line (R127)."""
    prog = (programs or {}).get(str(row_no)) or (programs or {}).get("*")
    if prog:   # a stated disposition decides: sample / display, else sellable (`none`, `deal`, `tier <n>`, ...)
        return prog.strip().lower() in ("sample", "display")
    if marker(r.get("invoice_line")):
        return True
    u = C.num(r.get("unit_cost"))
    return u is not None and u <= SAMPLE_MAX + 1e-9


def line_key(r):
    """The product line of a new-line row - the MSRP read's grouping (brand + form + size + process words)."""
    line = r.get("invoice_line", "")
    form = M.form_of(f"{line} {r.get('lane_MasterCategory', '')}")
    size = M.size_of(line, form) or M.size_of(r.get("lane_ProductGrams", ""), form)
    proc = M.process_of(M.strip_words(line, M.aliases_of(r, [])))
    return (C.norm(r.get("lane_Brand") or line.split(" | ")[0]), form, size, proc)


def sample_only_rows(rows, programs=None):
    """{row_no: line label} for every row of a new line whose every row is a sample (1-based row numbers)."""
    groups = {}
    for i, r in enumerate(rows, 1):
        if M.is_new_line(r):
            groups.setdefault(line_key(r), []).append(i)
    out = {}
    for key, nos in groups.items():
        if all(is_sample(rows[n - 1], n, programs) for n in nos):
            label = " ".join(x for x in [rows[nos[0] - 1].get("lane_Brand") or key[0], key[1], M.size_label(key[2]) or "",
                                          "/".join(key[3])] if x)
            for n in nos:
                out[n] = label
    return out


def fmt_cost(x):
    """Cents always, up to 4 places when the division needs them: 11 -> 11.00, 9.5 -> 9.50, 8.33333 -> 8.3333."""
    s = f"{x:.4f}".rstrip("0")
    whole, _, frac = s.partition(".")
    return f"{whole}.{frac.ljust(2, '0')}"


def read_apex(path):
    _, rows = C.read_csv(path, APEX_COLS, "--apex")
    out = {}
    for k, a in enumerate(rows, 2):
        src, per = (a.get("source") or "").strip().lower(), (a.get("per") or "").strip().lower()
        if src not in SOURCES:
            C.abort(f"--apex line {k}: source {a.get('source')!r} is not one of {SOURCES}")
        if src != "none" and per not in PERS:
            C.abort(f"--apex line {k}: per {a.get('per')!r} is not one of {PERS}")
        if src != "none" and C.num(a.get("price")) is None:
            C.abort(f"--apex line {k}: price {a.get('price')!r} is not a number")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", (a.get("read_date") or "").strip()):
            C.abort(f"--apex line {k}: read_date {a.get('read_date')!r} is not YYYY-MM-DD")
        out.setdefault(str(a.get("row") or "").strip(), []).append(dict(a, source=src, per=per))
    return out


def unit_of(a):
    """(unit cost or None, flags, how) from one typed Apex read."""
    price, upc, shown = C.num(a.get("price")), C.num(a.get("units_per_case")), C.num(a.get("unit_shown"))
    flags = []
    if a["per"] == "case":
        if not upc or upc <= 0:
            return None, ["APEX_PACK_UNREAD"], f"${price:.2f} / case, pack size unread"
        unit, how = price / upc, f"${price:.2f} / case of {upc:g}"
    elif upc and upc > 1:
        unit, how = price / upc, f"${price:.2f} / Apex unit of {upc:g} (an Apex unit is a case)"
        flags.append("APEX_UNIT_IS_CASE")
    else:
        unit, how = price, f"${price:.2f} / unit"
    if shown is not None and abs(unit - shown) > 0.005:
        return None, flags + ["APEX_UNIT_MISMATCH"], f"{how} = {unit:.4f}, but Apex prints {shown:.2f} per unit"
    if unit <= SAMPLE_MAX + 1e-9:
        return None, flags, f"{how} = {unit:.4f}: a sample price, not a cost"
    return unit, flags, how


def settle(rows, apex=None, programs=None, typed=None):
    """Pure. (rows out, report lines). Sets lane_Cost, flags and the `derived` Cost entry on every sample-only row."""
    apex, typed = apex or {}, typed or {}
    so = sample_only_rows(rows, programs)
    out = [dict(r) for r in rows]
    unknown_rows = [k for k in apex if k not in {str(i) for i in range(1, len(rows) + 1)}]
    if unknown_rows:
        C.abort(f"--apex names row(s) {unknown_rows} - the intake has rows 1-{len(rows)}")
    report = []
    for n, label in sorted(so.items()):
        r = out[n - 1]
        flags = [f for f in (r.get("flags") or "").split(";") if f and f not in FLAGS]
        reads = apex.get(str(n), [])
        pick = sorted(reads, key=lambda a: SOURCES.index(a["source"]))
        cost, cite, src_txt = None, "", "none"
        for a in pick:
            if a["source"] == "none":
                continue
            unit, fl, how = unit_of(a)
            flags += [f for f in fl if f not in flags]
            if unit is not None:
                cost = unit
                src_txt = f"apex:{a['source']} {a.get('ref', '').strip()} {a.get('item', '').strip()}".strip()
                cite = (f"R125: apex:{a['source']} " + (a.get("ref", "").strip() + " " if a["source"] == "po" else "")
                        + f"{a.get('item', '').strip()}, read {a['read_date'].strip()}; {how}")
                break
            src_txt = f"apex:{a['source']} read refused: {how}"
        t = typed.get(str(n))
        if t is not None:
            cost, src_txt = t, "typed by the Operator at the stop"
            cite = "R125: typed by the Operator at the stop" + ("" if not pick else
                                                                f" (Apex read: {', '.join(a['source'] for a in pick)})")
        elif cost is not None:
            flags.append("COST_FROM_APEX")
        if cost is None:
            flags.append("COST_UNKNOWN")
            looked = "; ".join(f"{a['source']}: {a.get('ref', '').strip() or '-'}" for a in pick) or "no Apex read yet"
            src_txt = f"unknown ({looked})"
            r["lane_Cost"] = ""
        else:
            r["lane_Cost"] = fmt_cost(cost)
            d = [p for p in (r.get("derived") or "").split("; ") if p and not p.startswith("Cost: ")]
            r["derived"] = "; ".join(d + [f"Cost: {fmt_cost(cost)} ({cite})"])
        r["flags"] = ";".join(flags)
        report.append(dict(row=n, line=label, invoice_line=r.get("invoice_line", ""), sample_price=r.get("unit_cost", ""),
                           cost=r["lane_Cost"], source=src_txt,
                           flags=[f for f in flags if f in FLAGS]))
    # a line at the sample price shape that a direction states SELLABLE keeps its invoice Cost, and says so: the plan
    # refuses a sample-shaped create row with no `Cost:` entry (COST_UNKNOWN), so the direction must ride the row.
    for n in sorted(set(sample_only_rows(rows)) - set(so)):
        r = out[n - 1]
        prog = (programs or {}).get(str(n)) or (programs or {}).get("*") or ""
        d = [p for p in (r.get("derived") or "").split("; ") if p and not p.startswith("Cost: ")]
        r["derived"] = "; ".join(d + [f"Cost: {r.get('lane_Cost') or '-'} (R125: stated sellable, --program {n}={prog}; "
                                      "the invoice Cost stands)"])
    return out, report


def stop_block(report, intake_name):
    out = ["## Cost on a sample-only new line (R125)", "",
           f"From `{intake_name}`. Every package of these new lines is a sample or display: the invoice price is not the "
           "Cost, and a sibling brand's Cost is never the fallback. The Cost comes from the vendor's Apex PO or catalog "
           "listing; COST_UNKNOWN = the Operator types it (`--cost <row>=<unit>`).", ""]
    if not report:
        return "\n".join(out + ["No sample-only new line in this intake."])
    out += ["| # | Line | Invoice line | Sample price | Cost | Source | Flags |", "|---|---|---|---|---|---|---|"]
    esc = lambda s: str(s or "").replace("|", "\\|")  # noqa: E731
    for x in report:
        out.append(f"| {x['row']} | {esc(x['line'])} | {esc(x['invoice_line'])} | {x['sample_price'] or '-'} | "
                   f"{x['cost'] or '**unknown**'} | {esc(x['source'])} | {', '.join(x['flags']) or '-'} |")
    return "\n".join(out)


def directions(argv, name):
    out = {}
    for d in C.get_all(argv, name):
        k, sep, v = d.partition("=")
        if not sep or not k.strip():
            C.abort(f"{name} {d!r}: expected <row>=<value>")
        out[k.strip()] = v.strip()
    return out


def main(argv):
    if "--selftest" in argv:
        return selftest()
    ip = C.get_flag(argv, "--intake")
    if not ip:
        print(__doc__)
        return C.EXIT_ABORT
    hdr, rows = C.read_csv(ip, INTAKE_REQUIRED, "--intake")
    ap = C.get_flag(argv, "--apex")
    apex = read_apex(ap) if ap else {}
    typed = {}
    for k, v in directions(argv, "--cost").items():
        x = C.num(v)
        if x is None or x <= SAMPLE_MAX:
            C.abort(f"--cost {k}={v}: a Cost must be a number above the sample price ({SAMPLE_MAX})")
        typed[k] = x
    out, report = settle(rows, apex, directions(argv, "--program"), typed)
    d_, stem = C.version_stem(ip)
    path = C.next_version(C.get_flag(argv, "--out-dir") or d_, stem)
    cols = list(hdr) + [c for c in ("derived",) if c not in hdr]
    C.write_csv(path, cols, out)
    print(stop_block(report, os.path.basename(path)))
    counts = {f: sum(f in x["flags"] for x in report) for f in FLAGS}
    print("\n" + " | ".join(f"{f} ({FLAGS[f][1]}) {n}" for f, n in counts.items()))
    print(f"wrote {path}")
    return C.EXIT_OK


# ---------------------------------------------------------------- selftest (synthetic rows only)
def _row(line, unit, verdict="NEW_PL", brand="Zeta", mc="Edible", grams="0.1g", flags="NEW_LINE_FIELDS;CROSS_BRAND_COPY",
         lane_cost=""):
    return dict(invoice_line=line, unit_cost=unit, lane_Brand=brand, lane_MasterCategory=mc, lane_ProductGrams=grams,
                lane_Cost=lane_cost or unit, verdict=verdict, flags=flags, sibling_reason="", derived="")


def _apex(row, source, price="", per="case", upc="", shown="", ref="SO-1", item="Zeta Gummies 10pk", date="2026-10-11"):
    return {str(row): [dict(row=str(row), source=source, ref=ref, item=item, read_date=date, price=price, per=per,
                            units_per_case=upc, unit_shown=shown)]}


def selftest():
    t = C.Selftest("intake_apex_cost")
    rows = [_row("Zeta | Orbs - Lime Gummies - 100mg - 10ct | Edibles", "0.05", lane_cost="12"),
            _row("Zeta | Orbs - Plum Gummies - 100mg - 10ct | Edibles", "0.05", lane_cost="10"),
            _row("Acme | Mint Vape 1g | Vapes", "15.00", brand="Acme", mc="Vape", grams="1g"),
            _row("Acme | Mint Vape 1g (sample) | Vapes", "0.01", brand="Acme", mc="Vape", grams="1g"),
            _row("Beta | Kush Pre-Roll 1g | Pre-Rolls", "0.05", verdict="EXISTS", brand="Beta", mc="Pre-Roll", grams="1g",
                 flags="")]
    so = sample_only_rows(rows)
    t.check("the two Zeta penny rows are ONE sample-only line", set(so) == {1, 2} and so[1] == so[2], str(so))
    t.check("a MIXED line (a paid row beside its sample) is not sample-only", 3 not in so and 4 not in so, str(so))
    t.check("an EXISTS sample row is no new line", 5 not in so)
    t.check("`--program <row>=none` makes the line sellable", sample_only_rows(rows, {"1": "none"}) == {}, "")
    t.check("an invoice marker reads as a sample at any price",
            set(sample_only_rows([_row("Zeta | Lime Gummies (sample) | Edibles", "9.00")])) == {1})
    # the three branches
    apex = {}
    apex.update(_apex(1, "catalog", price="330", per="case", upc="30", shown="11.00", ref="Zeta Wholesale"))
    apex.update(_apex(2, "po", price="270", per="case", upc="30", ref="T-9"))
    apex["2"] += _apex(2, "catalog", price="300", per="case", upc="30")["2"]
    out, rep = settle(rows, apex)
    t.check("CATALOG: $330 / case of 30 -> Cost 11.00, COST_FROM_APEX, the listing named with its read date",
            out[0]["lane_Cost"] == "11.00" and "COST_FROM_APEX" in out[0]["flags"]
            and "Cost: 11.00 (R125: apex:catalog Zeta Gummies 10pk, read 2026-10-11; $330.00 / case of 30)" in out[0]["derived"],
            f"{out[0]['lane_Cost']} {out[0]['flags']} {out[0]['derived']}")
    t.check("PO beats catalog: $270 / case of 30 from PO T-9 -> 9.00",
            out[1]["lane_Cost"] == "9.00" and "apex:po T-9" in out[1]["derived"], out[1]["derived"])
    t.check("the sibling's Cost (12 / 10 on the rows) is never kept", out[0]["lane_Cost"] != "12" and out[1]["lane_Cost"] != "10")
    out2, rep2 = settle(rows, _apex(1, "none", ref="marketplace search `Zeta Lime`"))
    t.check("NONE: no PO, no listing -> COST_UNKNOWN STOP, lane_Cost blank (not the sample price, not the sibling's)",
            "COST_UNKNOWN" in out2[0]["flags"] and out2[0]["lane_Cost"] == "" and "Cost: " not in out2[0]["derived"],
            f"{out2[0]['flags']} {out2[0]['lane_Cost']!r}")
    t.check("no Apex read at all is COST_UNKNOWN too ('no Apex read yet')",
            "COST_UNKNOWN" in out2[1]["flags"] and "no Apex read yet" in rep2[1]["source"], rep2[1]["source"])
    out3, _ = settle(rows, _apex(1, "none"), typed={"1": 11.5})
    t.check("the Operator's typed Cost settles COST_UNKNOWN and is cited as typed",
            out3[0]["lane_Cost"] == "11.50" and "COST_UNKNOWN" not in out3[0]["flags"]
            and "typed by the Operator" in out3[0]["derived"], f"{out3[0]['flags']} {out3[0]['derived']}")
    out4, _ = settle(rows, _apex(1, "po", price="520", per="unit", upc="40"))
    t.check("an Apex `1 Unit` that is a case of 40 divides: 520 -> 13.00, APEX_UNIT_IS_CASE",
            out4[0]["lane_Cost"] == "13.00" and "APEX_UNIT_IS_CASE" in out4[0]["flags"], f"{out4[0]['lane_Cost']} {out4[0]['flags']}")
    out5, _ = settle(rows, _apex(1, "catalog", price="330", per="case"))
    t.check("a case price with no pack size is APEX_PACK_UNREAD + COST_UNKNOWN, nothing divided",
            "APEX_PACK_UNREAD" in out5[0]["flags"] and "COST_UNKNOWN" in out5[0]["flags"] and out5[0]["lane_Cost"] == "")
    out6, _ = settle(rows, _apex(1, "catalog", price="330", per="case", upc="30", shown="12.00"))
    t.check("the computed unit disagreeing with Apex's printed unit is APEX_UNIT_MISMATCH + COST_UNKNOWN",
            "APEX_UNIT_MISMATCH" in out6[0]["flags"] and "COST_UNKNOWN" in out6[0]["flags"])
    out7, _ = settle(rows, _apex(1, "catalog", price="0.05", per="unit", upc="1"))
    t.check("an Apex figure at the sample price is not a cost: COST_UNKNOWN", "COST_UNKNOWN" in out7[0]["flags"])
    t.check("a non-sample row is untouched", out[2] == rows[2] and out[4] == rows[4])
    out8, rep8 = settle(rows, {}, {"1": "none", "2": "none"})
    t.check("a sample-shaped line stated SELLABLE keeps its invoice Cost and the row says so (the plan reads the entry)",
            rep8 == [] and "R125: stated sellable, --program 1=none" in out8[0]["derived"] and out8[0]["lane_Cost"] == "12")
    re_run, _ = settle(out, apex)
    t.check("a re-run is idempotent (one Cost entry, flags not doubled)",
            re_run[0]["derived"].count("Cost: ") == 1 and re_run[0]["flags"].count("COST_FROM_APEX") == 1, re_run[0]["flags"])
    t.check("the STOP block names the source and marks an unknown Cost",
            "apex:catalog" in stop_block(rep, "x.csv") and "**unknown**" in stop_block(rep2, "x.csv"))
    t.check("fmt_cost keeps cents and 4-place units", fmt_cost(11) == "11.00" and fmt_cost(8.3333333) == "8.3333"
            and fmt_cost(9.5) == "9.50", f"{fmt_cost(11)} {fmt_cost(8.3333333)} {fmt_cost(9.5)}")
    return t.done()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
