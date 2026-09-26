"""intake_exceptions.py - the R102 intake exception flags, the R62 read and the R103 landed unit cost,
then the ONE pre-create STOP message.

  python intake_exceptions.py --intake <intake-vN.csv> --lines <lines.csv> [--po <po.csv>]
                              --tenant <CLAUDE.md> [--asof YYYY-MM-DD] [--out-dir <dir>]
  (without --tenant: --expiry-days <n> --operator "<name>" [--po-source apex|vendor pdf|none])
  --program <line_no>=<program>   rule a program for one product line (repeatable); a bare
                                  `--program <program>` rules it for every line. Overrides the PO.
  python intake_exceptions.py --selftest

Joins the intake rows to the parsed PRODUCT lines in order (intake_match writes one row per
product line, in line order) and ABORTs if a description disagrees. Writes a NEW version of the
intake CSV with `flags`, `landed_unit_cost`, `po_line_ref` and `expiry_date` filled, a NEW
`<stem>-exceptions-<timestamp>.csv`, and prints the STOP message (markdown) to stdout.

R103 landed unit cost: a line-level discount stays on its line (net ext = ext + discount) and marks
the line `PROMO_MARKER` (a marker only, not an exception); each order-level credit / shipping /
discount is spread pro-rata by the product line's ext_cost; landed unit = (net ext + share) / units.
Free goods (ext 0) take no share and keep their stated cost.

Flag table (rule, class; the R102 flags are STOP-class: they are listed in the STOP message and
never fail the runner - only a DEFECT exits 1):
  COST_DRIFT           R102 (see R50)            STOP    list unit cost != the lane Cost (penny exact,
                                                          R50) and no discount or credit explains it
  PROMO_UNDECIDED      R102 (see R62 R72 R84)    STOP    landed unit (R103, the cost the package is
                                                          received at) <= 0.90 x lane Cost (R62) AND no
                                                          ruled Promo, Tier or margin program (PO
                                                          `program` column or --program) - whether or
                                                          not any discount line is printed. May co-fire
                                                          with COST_DRIFT on the same line.
  EXPIRY_NEAR          R102                      STOP    expiry - as-of date < `Expiry threshold days`
  PO_MISMATCH          R102                      STOP    not on the PO, qty or unit cost differs, or a
                                                          PO line was not invoiced; n/a without --po
  PKG_TAG_DUE          R62 (see R72)             INFO    landed unit <= 0.90 x lane Cost: the package
                                                          needs a `PKG - ` tag at receiving
  LANDED_UNRECONCILED  R103                      DEFECT  landed ext does not sum to the invoice total
"""
import os
import sys
from datetime import date

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from intake_common import (EXIT_ABORT, EXIT_DEFECT, EXIT_OK, PKG_PREFIX, Selftest, abort, get_all, get_flag,  # noqa: E402
                           has_phrase, new_path, next_version, norm, num, read_csv, stamp, version_stem,
                           write_csv)
from intake_match import LINES_REQUIRED, V3_COLS  # noqa: E402

R62_RATIO = 0.90          # R62: package cost <= 0.90 x catalog cost, boundary inclusive (ruled, not tuned)
PO_REQUIRED = ["po_no", "po_line", "sku", "description", "units", "unit_cost"]
FLAGS = [("COST_DRIFT", "R102 (see R50)", "STOP"), ("PROMO_UNDECIDED", "R102 (see R62 R72 R84)", "STOP"),
         ("EXPIRY_NEAR", "R102", "STOP"), ("PO_MISMATCH", "R102", "STOP"), ("PKG_TAG_DUE", "R62 (see R72)", "INFO"),
         ("LANDED_UNRECONCILED", "R103", "DEFECT")]
RULE = {f: r for f, r, _ in FLAGS}
CLASS = {f: c for f, _, c in FLAGS}
EXC_COLS = ["flag", "rule", "class", "row", "line_no", "invoice_line", "verdict", "detail"]


def pair(intake, lines):
    prod = [ln for ln in lines if not (ln.get("order_level_kind") or "").strip()]
    if len(prod) != len(intake):
        abort(f"{len(intake)} intake rows vs {len(prod)} product lines - run intake_match on THIS lines file")
    for i, (r, ln) in enumerate(zip(intake, prod), 1):
        if norm(r.get("invoice_line")) != norm(ln.get("description")):
            abort(f"row {i}: intake line {r.get('invoice_line')!r} != parsed line {ln.get('description')!r}")
    return prod


def landed(prod, lines):
    """{line_no: dict(net_ext, disc, share_all, share_cd, landed_ext, landed_unit)}, order sums, defects."""
    disc = {}
    for ln in lines:
        if (ln.get("order_level_kind") or "") == "discount" and (ln.get("is_order_level") or "").upper() == "N":
            disc[ln["line_no"]] = disc.get(ln["line_no"], 0.0) + abs(num(ln.get("ext_cost")) or 0)
    order = [ln for ln in lines if (ln.get("is_order_level") or "").upper() == "Y" and ln.get("order_level_kind")]
    o_all = sum(num(ln.get("ext_cost")) or 0 for ln in order)
    o_cd = sum(num(ln.get("ext_cost")) or 0 for ln in order if ln["order_level_kind"] in ("credit", "discount"))
    base = sum(num(ln.get("ext_cost")) or 0 for ln in prod)
    out, defects = {}, []
    if base <= 0 and abs(o_all) >= 0.005:
        defects.append(f"order-level lines total {o_all:+.2f} but the product lines carry no ext_cost to spread it on")
    for ln in prod:
        ext = num(ln.get("ext_cost")) or 0
        units = num(ln.get("units_total")) or 0
        d = disc.get(ln["line_no"], 0.0)
        w = ext / base if base > 0 else 0.0
        le = ext - d + w * o_all
        out[ln["line_no"]] = {"net_ext": ext - d, "disc": d, "share_all": w * o_all, "share_cd": w * o_cd,
                              "landed_ext": le, "landed_unit": le / units if units else None}
    total_in = base - sum(disc.values()) + o_all
    total_out = sum(v["landed_ext"] for v in out.values())
    if abs(total_in - total_out) >= 0.01:
        defects.append(f"landed ext sums to {total_out:.2f}, invoice nets to {total_in:.2f}")
    return out, (base, sum(disc.values()), o_all), defects


def po_match(intake, prod, po):
    """{row index: (po line dict or None, [problems])}, [unmatched PO lines]."""
    used, res = set(), {}
    for i, (r, ln) in enumerate(zip(intake, prod)):
        sku = r.get("copy_source_sku") if r.get("verdict") in ("EXISTS", "RETIRED_MATCH") else ""
        hit = None
        for j, p in enumerate(po):
            if j in used:
                continue
            if sku and p.get("sku") and p["sku"] == sku:
                hit = j
                break
        if hit is None:
            dn = norm(ln.get("description"))
            for j, p in enumerate(po):
                if j not in used and p.get("description") and (norm(p["description"]) == dn or has_phrase(dn, p["description"])):
                    hit = j
                    break
        if hit is None:
            res[i] = (None, ["not on the PO"])
            continue
        used.add(hit)
        p, probs = po[hit], []
        if (num(p.get("units")) or 0) != (num(ln.get("units_total")) or 0):
            probs.append(f"qty invoice {ln.get('units_total')} vs PO {p.get('units')}")
        pu, iu = num(p.get("unit_cost")), num(ln.get("unit_cost"))
        if pu is not None and iu is not None and abs(pu - iu) >= 0.005:
            probs.append(f"unit cost invoice {iu:.2f} vs PO {pu:.2f}")
        res[i] = (p, probs)
    return res, [p for j, p in enumerate(po) if j not in used]


def program_for(i_line_no, po_line, programs):
    """The ruled program for a product line: --program (per line, then the bare all-lines value),
    else the PO line's `program` column, else ''."""
    programs = programs or {}
    return (programs.get(str(i_line_no)) or programs.get("*") or ((po_line or {}).get("program") or "")).strip()


def evaluate(intake, lines, po=None, expiry_days=90, asof=None, programs=None):
    """Pure. Returns (rows with filled columns, exceptions list, defects list, summary dict)."""
    prod = pair(intake, lines)
    lc, sums, defects = landed(prod, lines)
    pom, po_left = po_match(intake, prod, po) if po is not None else ({}, [])
    exc, rows = [], []
    for i, (r, ln) in enumerate(zip(intake, prod), 1):
        r = dict(r)
        flags = [f for f in (r.get("flags") or "").split(";") if f]
        v = lc[ln["line_no"]]
        units = num(ln.get("units_total")) or 0
        unit = num(ln.get("unit_cost"))
        lane = num(r.get("lane_Cost"))
        r["landed_unit_cost"] = "" if v["landed_unit"] is None else f"{v['landed_unit']:.4f}"
        r["expiry_date"] = ln.get("expiry_date") or r.get("expiry_date", "")

        def add(flag, detail):
            flags.append(flag)
            exc.append({"flag": flag, "rule": RULE[flag], "class": CLASS[flag], "row": i, "line_no": ln["line_no"],
                        "invoice_line": ln.get("description"), "verdict": r.get("verdict"), "detail": detail})

        promo = v["disc"] > 0
        if promo:
            flags.append("PROMO_MARKER")
        if lane is not None and unit is not None and abs(unit - lane) >= 0.005:
            net_unit_after_disc = (v["net_ext"] + v["share_cd"]) / units if units else None
            restored = net_unit_after_disc is not None and abs(net_unit_after_disc - lane) < 0.005
            if not restored:
                add("COST_DRIFT", f"list unit {unit:.2f} vs lane Cost {lane:.2f} ({unit - lane:+.2f}, "
                                  f"{(unit - lane) / lane * 100:+.1f}%)" + (f"; after discounts {net_unit_after_disc:.4f}"
                                                                           if promo or v["share_cd"] else ""))
        pl = pom.get(i - 1, (None, []))[0] if po is not None else None
        below = lane is not None and v["landed_unit"] is not None and v["landed_unit"] <= R62_RATIO * lane + 1e-9
        if below and not program_for(ln["line_no"], pl, programs):
            add("PROMO_UNDECIDED", f"landed unit {v['landed_unit']:.4f} <= {R62_RATIO:.2f} x lane Cost {lane:.2f} "
                                   f"and no Promo, Tier or margin program ruled"
                                   + (f" (line discount {v['disc']:.2f} printed)" if promo else " (no discount printed)")
                                   + f" - `{PKG_PREFIX}Promo` until a tier is proven (R84)")
        exp = r["expiry_date"]
        if exp:
            try:
                left = (date.fromisoformat(exp) - date.fromisoformat(asof or r.get("invoice_date"))).days
                if left < expiry_days:
                    add("EXPIRY_NEAR", f"expires {exp}: {left} day(s) after {asof or r.get('invoice_date')} "
                                       f"(threshold {expiry_days})")
            except ValueError:
                add("EXPIRY_NEAR", f"expiry {exp!r} unreadable - read the date off the invoice")
        if po is not None:
            p, probs = pom[i - 1]
            r["po_line_ref"] = f"{p['po_no']}:{p['po_line']}" if p else ""
            if probs:
                add("PO_MISMATCH", "; ".join(probs))
        if lane is not None and v["landed_unit"] is not None and v["landed_unit"] <= R62_RATIO * lane + 1e-9:
            add("PKG_TAG_DUE", f"landed unit {v['landed_unit']:.4f} <= {R62_RATIO:.2f} x lane Cost {lane:.2f} "
                               f"= {R62_RATIO * lane:.4f}: tag the package `{PKG_PREFIX}...` at receiving")
        r["flags"] = ";".join(dict.fromkeys(flags))
        rows.append(r)
    for p in po_left:
        exc.append({"flag": "PO_MISMATCH", "rule": RULE["PO_MISMATCH"], "class": "STOP", "row": "", "line_no": "",
                    "invoice_line": p.get("description"), "verdict": "",
                    "detail": f"on the PO ({p['po_no']}:{p['po_line']}, {p.get('units')} units), not invoiced"})
    for d in defects:
        exc.append({"flag": "LANDED_UNRECONCILED", "rule": "R103", "class": "DEFECT", "row": "", "line_no": "",
                    "invoice_line": "", "verdict": "", "detail": d})
    summary = {"product_ext": sums[0], "line_discounts": sums[1], "order_level": sums[2], "po_checked": po is not None}
    return rows, exc, defects, summary


def stop_message(rows, exc, summary, operator, intake_path):
    first = rows[0] if rows else {}
    out = [f"## STOP - pre-create review - {first.get('lane_Vendor') or 'vendor'} invoice {first.get('invoice_no', '')} "
           f"({first.get('invoice_date', '')})", "",
           f"{operator}: fill the `approved` column (Y or N) in `{os.path.basename(intake_path)}`, then reply `approved`.",
           "Nothing is created before that reply. Only rows with verdict NEW_ITEM_WITH_SIBLING and approved = Y are "
           "created, one Copy item each (R101).", "",
           "### Verdicts", "",
           "| # | Invoice line | Verdict | Sibling / match | Final name | Landed unit | Flags | approved |",
           "|---|---|---|---|---|---|---|---|"]
    esc = lambda s: str(s or "").replace("|", "\\|")  # noqa: E731
    for i, r in enumerate(rows, 1):
        src = f"{r.get('copy_source_sku', '')} {r.get('copy_source_name', '')}".strip()
        out.append(f"| {i} | {esc(r.get('invoice_line'))} | {r.get('verdict')} | {esc(src) or '-'} | "
                   f"{esc(r.get('create_name_FINAL')) or '-'} | {r.get('landed_unit_cost') or '-'} | "
                   f"{esc(r.get('flags')) or '-'} | {r.get('approved') or '__'} |")
    counts = {}
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    out += ["", "Counts: " + " / ".join(f"{k} {v}" for k, v in counts.items()), "", "### Exceptions", ""]
    if exc:
        out += ["| # | Flag | Rule | Row | Detail |", "|---|---|---|---|---|"]
        for k, e in enumerate(exc, 1):
            out.append(f"| {k} | {e['flag']} | {e['rule']} | {e['row'] or '-'} | {esc(e['detail'])} |")
    else:
        out.append("None.")
    if not summary["po_checked"]:
        out += ["", "PO_MISMATCH: n/a - no PO was supplied (a zero here would prove nothing)."]
    out += ["", "### What each verdict does with `approved`", "",
            "- NEW_ITEM_WITH_SIBLING + Y: created by Copy item from the named sibling, then read back.",
            "- EXISTS: nothing to create; the line is received against the matched item.",
            "- EXISTS + FORM_UNREAD (R101, STOP): matched on brand + body + grams only - the line names no form "
            "word. Confirm the matched item in the Sibling / match column before receiving.",
            "- RETIRED_MATCH: un-retire beats a duplicate (R101). Y = un-retire by hand; never a copy.",
            "- STRAIN_MISSING: mint the Strain record first, re-run `intake`, then approve.",
            "- NEW_PL / NEW_BRAND: never created by this lane (R101). Rule them outside the run.",
            "- Any row + N: skipped. A STOP flag stays on the row for the notice and the vendor thread."]
    return "\n".join(out)


def main(argv):
    if "--selftest" in argv:
        return selftest()
    ip, lp = get_flag(argv, "--intake"), get_flag(argv, "--lines")
    if not (ip and lp):
        print(__doc__)
        return EXIT_ABORT
    tenant = get_flag(argv, "--tenant")
    if tenant:
        import intake_pointers
        ptr = intake_pointers.load(tenant)["intake"]
        if "lane cost" not in ptr["Standard cost"].lower():
            abort(f"`Standard cost: {ptr['Standard cost']}` - only the lane Cost (R50) standard is implemented")
        days, operator, po_source = int(ptr["Expiry threshold days"]), ptr["Operator"], ptr["PO source"].lower()
    else:
        d, operator = get_flag(argv, "--expiry-days"), get_flag(argv, "--operator")
        if not (d and operator):
            abort("without --tenant pass --expiry-days and --operator (the thresholds are ruled, never defaulted)")
        days, po_source = int(d), (get_flag(argv, "--po-source", "none")).lower()
    _, intake = read_csv(ip, V3_COLS, "--intake")
    _, lines = read_csv(lp, LINES_REQUIRED, "--lines")
    pop = get_flag(argv, "--po")
    po = read_csv(pop, PO_REQUIRED, "--po")[1] if pop else None
    if po is None and po_source != "none":
        print(f"WARNING: `PO source: {po_source}` but no --po given - PO_MISMATCH is n/a on this run, not zero")
    programs = {}
    for v in get_all(argv, "--program"):
        k, _, prog = v.partition("=") if "=" in v else ("*", "", v)
        programs[k.strip()] = prog.strip()
    rows, exc, defects, summary = evaluate(intake, lines, po, days, get_flag(argv, "--asof"), programs)
    d_, stem = version_stem(ip)
    out_dir = get_flag(argv, "--out-dir") or d_
    out_intake = next_version(out_dir, stem)
    write_csv(out_intake, V3_COLS, rows)
    out_exc = new_path(out_dir, f"{stem}-exceptions-{stamp()}", ".csv")
    write_csv(out_exc, EXC_COLS, exc)
    print(f"{'flag':20} {'rule':24} {'class':7} count")
    for f, rule, cls in FLAGS:
        n = "n/a" if f == "PO_MISMATCH" and po is None else sum(1 for e in exc if e["flag"] == f)
        print(f"{f:20} {rule:24} {cls:7} {n}")
    print(f"product ext {summary['product_ext']:.2f} | line discounts -{summary['line_discounts']:.2f} | "
          f"order-level {summary['order_level']:+.2f}")
    print(f"wrote {out_intake}\nwrote {out_exc}\n")
    print(stop_message(rows, exc, summary, operator, out_intake))
    return EXIT_DEFECT if defects else EXIT_OK


def selftest():
    t = Selftest("intake_exceptions")

    def ln(no, desc, units, unit, ext, **kw):
        d = {"line_no": str(no), "description": desc, "units_total": str(units), "unit_cost": str(unit),
             "ext_cost": str(ext), "is_order_level": "N", "order_level_kind": "", "expiry_date": ""}
        d.update(kw)
        return d

    def ir(desc, lane, verdict="EXISTS", sku=""):
        return {"invoice_line": desc, "lane_Cost": lane, "verdict": verdict, "copy_source_sku": sku,
                "invoice_date": "2026-09-20", "flags": ""}

    lines = [ln(1, "A", 100, 4.5, 450, expiry_date="2026-10-01"), ln(2, "B", 100, 4.5, 450), ln(3, "C", 100, 5.0, 500),
             ln(4, "D", 50, 3.5, 175),
             {"line_no": "2", "description": "disc B", "ext_cost": "-80", "is_order_level": "N", "order_level_kind": "discount"},
             {"line_no": "901", "description": "Shipping", "ext_cost": "20", "is_order_level": "Y", "order_level_kind": "shipping"},
             {"line_no": "902", "description": "Credit", "ext_cost": "-10", "is_order_level": "Y", "order_level_kind": "credit"}]
    intake = [ir("A", "4.5", sku="1"), ir("B", "4.5", sku="2"), ir("C", "4.5", sku="3"), ir("D", "4.5", sku="4")]
    po = [{"po_no": "P", "po_line": "1", "sku": "1", "description": "A", "units": "100", "unit_cost": "4.5", "program": ""},
          {"po_no": "P", "po_line": "2", "sku": "2", "description": "B", "units": "90", "unit_cost": "4.5", "program": ""},
          {"po_no": "P", "po_line": "3", "sku": "3", "description": "C", "units": "100", "unit_cost": "5.0", "program": ""},
          {"po_no": "P", "po_line": "4", "sku": "4", "description": "D", "units": "50", "unit_cost": "3.5", "program": ""}]
    rows, exc, defects, _ = evaluate(intake, lines, po, 90)
    fired = lambda f: [e["line_no"] for e in exc if e["flag"] == f]  # noqa: E731
    t.check("COST_DRIFT fires on C (drift only) and D (both)", fired("COST_DRIFT") == ["3", "4"], str(fired("COST_DRIFT")))
    t.check("PROMO_UNDECIDED fires on B (promo only) and D (both)", fired("PROMO_UNDECIDED") == ["2", "4"],
            str(fired("PROMO_UNDECIDED")))
    t.check("QUIET: COST_DRIFT on B (list = lane; the discount is the promo)", "2" not in fired("COST_DRIFT"))
    t.check("QUIET: PROMO_UNDECIDED on C (above lane) and A (control)", not {"1", "3"} & set(fired("PROMO_UNDECIDED")))
    t.check("EXPIRY_NEAR fires on A only", fired("EXPIRY_NEAR") == ["1"], str(fired("EXPIRY_NEAR")))
    t.check("PO_MISMATCH fires on B only (qty)", fired("PO_MISMATCH") == ["2"], str(fired("PO_MISMATCH")))
    t.check("PKG_TAG_DUE fires on B and D", fired("PKG_TAG_DUE") == ["2", "4"], str(fired("PKG_TAG_DUE")))
    # landed: order-level +10 spread by ext 450/1575; B = (370 + 450/1575*10)/100
    t.check("R103 landed unit on B", abs(float(rows[1]["landed_unit_cost"]) - (370 + 450 / 1575 * 10) / 100) < 1e-4,
            rows[1]["landed_unit_cost"])
    t.check("QUIET: LANDED_UNRECONCILED on a clean invoice", defects == [])
    po2 = [dict(p) for p in po]
    po2[1]["program"] = PKG_PREFIX + "Promo"
    t.check("QUIET: PROMO_UNDECIDED on B once the PO names a program",
            [e["line_no"] for e in evaluate(intake, lines, po2, 90)[1] if e["flag"] == "PROMO_UNDECIDED"] == ["4"])
    t.check("QUIET: PROMO_UNDECIDED on D under a --program override",
            [e["line_no"] for e in evaluate(intake, lines, po, 90, programs={"4": "margin"})[1]
             if e["flag"] == "PROMO_UNDECIDED"] == ["2"])
    lines4 = [dict(x) for x in lines if x.get("order_level_kind") != "discount"]
    t.check("FIRES without any discount line printed (D still fires, B stops)",
            [e["line_no"] for e in evaluate(intake, lines4, po, 90)[1] if e["flag"] == "PROMO_UNDECIDED"] == ["4"])
    free = [ln(1, "A", 10, 0, 0), {"line_no": "901", "description": "Shipping", "ext_cost": "5", "is_order_level": "Y",
                                    "order_level_kind": "shipping"}]
    t.check("FIRES: LANDED_UNRECONCILED when no ext carries the order-level lines",
            bool(evaluate([ir("A", "4.5")], free, None, 90)[2]))
    lines3 = [dict(x) for x in lines]
    lines3[2]["unit_cost"], lines3[2]["ext_cost"] = "4.5", "450"
    t.check("QUIET: COST_DRIFT on C once C returns to the lane Cost (D still fires)",
            [e["line_no"] for e in evaluate(intake, lines3, po, 90)[1] if e["flag"] == "COST_DRIFT"] == ["4"])
    t.check("PO_MISMATCH is n/a without a PO", not [e for e in evaluate(intake, lines, None, 90)[1] if e["flag"] == "PO_MISMATCH"])
    return t.done()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
