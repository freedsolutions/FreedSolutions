"""intake_certify.py - the attributed full-row diff that certifies an intake write.

  python intake_certify.py --pre <export.csv> --post <export.csv> --intake <intake-vN.csv>
                           [--key SKU|ProductId] [--siblings <k1,k2 | file>] [--min-rows <n>]
                           [--tenant <CLAUDE.md> | --out-dir <dir>]
  python intake_certify.py --pre ... --post ... --no-create --allow "Online title" [--allow <col> ...]
                           [--rows <k1,k2 | file>] [--intake <intake.csv>]
  python intake_certify.py --selftest

A blanket "0 changed cells on pre-existing rows" is unachievable between two real exports: a
trading day and other sessions' writes sit inside the window. So this gate ATTRIBUTES. Every
changed cell must land in a named population; an unattributed cell is the finding.

  A  intake population - create mode: exactly the approved NEW_ITEM_WITH_SIBLING rows, added, every
     field equal to its intake target (R101), the item-QC tag read back (R83).
     --no-create mode: the declared cells only - columns named by --allow, on the rows named by
     --rows (default: the intake's EXISTS matches; with no intake, any row).
  B  sales drift - `Available` only, numeric and monotonically DOWN.
  C  foreign writes - everything else. Reported, never waived. Exit 1.
PL-grain expansion: every sibling (the --siblings list, else each approved create row's copy source)
must be present in both exports and INERT apart from `Available`. A falsification pass flips one
cell on a copy of a touched row and requires the comparator to see exactly that one cell.

Flag table (all DEFECT -> exit 1): A_MISMATCH (R101) · A_MISSING / A_UNEXPECTED (R101) ·
TAG_NOT_READ_BACK (R83) · ROW_REMOVED · C_FOREIGN_CELL · SIBLING_NOT_INERT (R50) ·
NOT_READ_BACK (an approved row with no new key, R101) · ROW_GUARD · COMPARATOR_INERT.
Output: a NEW `<stem>-certify-<timestamp>.md`.
"""
import copy
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from intake_common import (DEFAULT_ITEM_QC_TAG, EXIT_ABORT, EXIT_DEFECT, EXIT_OK, Selftest, abort,  # noqa: E402
                           get_all, get_flag, grams_eq, new_path, num, read_csv, stamp, tag_set, unwrap,
                           version_stem)
from intake_match import V3_COLS  # noqa: E402

FIELD_MAP = {
    "Product": "create_name_FINAL", "Category": "lane_Category", "Type": "lane_Type",
    "Is cannabis": "lane_IsCannabis", "Master category": "lane_MasterCategory",
    "Global Category": "lane_GlobalCategory", "Global SubCategory": "lane_GlobalSubCategory",
    "Servings per Unit": "lane_ServingsPerUnit", "Cost": "lane_Cost", "Price": "lane_Price",
    "Brand": "lane_Brand", "Vendor": "lane_Vendor", "CBD content": "lane_CBDContent",
    "Flavor": "lane_Flavor", "Is available online": "lane_OnlineAvailable",
    "Strain": "strain", "Strain Type": "strain_type", "Online title": "online_title", "Tags": "tags",
}
GRAMS = {"Flower equiv": "lane_FlowerEquiv", "Product grams": "lane_ProductGrams"}
AVAILABLE = "Available"
NEWKEY = {"SKU": ("new_sku", "copy_source_sku"), "ProductId": ("new_productid", "copy_source_productid")}


def load(path, key, required, label):
    hdr, rows = read_csv(path, [key] + required, label)
    out = {}
    for r in rows:
        k = r.get(key, "")
        if k in out:
            abort(f"{label} {os.path.basename(path)}: key {key}={k!r} appears twice - not a keyed export")
        out[k] = r
    return hdr, out


def listarg(v):
    if not v:
        return None
    if os.path.isfile(v):
        return [x.strip() for x in open(v, encoding="utf-8").read().replace(",", "\n").split("\n") if x.strip()]
    return [x.strip() for x in v.split(",") if x.strip()]


def field_eq(col, got, want):
    if col == "Tags":
        return tag_set(got) == tag_set(want)
    if col in ("Cost", "Price"):
        a, b = num(got), num(want)
        if a is not None and b is not None:
            return abs(a - b) < 0.005
    return (got or "").strip() == (want or "").strip()


def diff_row(a, b, cols):
    return [c for c in cols if (a.get(c, "") or "") != (b.get(c, "") or "")]


def certify(pre_hdr, pre, post_hdr, post, key, intake=None, no_create=False, allow=(), rows_allowed=None,
            siblings=None, item_qc_tag=DEFAULT_ITEM_QC_TAG, min_rows=None):
    """Pure. Returns (report lines, fails list, counts dict)."""
    rep, fails = [], []
    shared = [c for c in pre_hdr if c in post_hdr and c != key]
    newcol, srccol = NEWKEY.get(key, ("new_sku", "copy_source_sku"))
    rep += ["## Row guard", "",
            f"- pre {len(pre)} rows, post {len(post)} rows; shared columns {len(shared)}; "
            f"pre-only {sorted(set(pre_hdr) - set(post_hdr))}; post-only {sorted(set(post_hdr) - set(pre_hdr))}"]
    if min_rows is not None and (len(pre) < min_rows or len(post) < min_rows):
        fails.append(f"ROW_GUARD: an export is under the {min_rows}-row floor (a filtered one-off?)")
    added, removed = set(post) - set(pre), set(pre) - set(post)
    if removed:
        fails.append(f"ROW_REMOVED: {len(removed)} key(s) {sorted(removed)[:10]}")
    counts = {"A": 0, "A_mismatch": 0, "B": 0, "C": 0, "sibling_moved": 0}
    rep += ["", "## A - intake population", ""]
    declared = set()
    if not no_create:
        approved = [r for r in (intake or []) if r.get("verdict") == "NEW_ITEM_WITH_SIBLING"
                    and (r.get("approved") or "").strip().upper() == "Y"]
        for r in approved:
            if not (r.get(newcol) or "").strip():
                fails.append(f"NOT_READ_BACK: approved row {r.get('create_name_FINAL')!r} has no {newcol}")
        want = {r[newcol].strip(): r for r in approved if (r.get(newcol) or "").strip()}
        if set(want) - added:
            fails.append(f"A_MISSING: intake keys not added: {sorted(set(want) - added)}")
        if added - set(want):
            fails.append(f"A_UNEXPECTED: added keys the intake does not name: {sorted(added - set(want))}")
        rep.append(f"- approved create rows {len(approved)}; added keys {sorted(added)}; removed {sorted(removed)}")
        for k in sorted(set(want) & added):
            row, tgt, probs = post[k], want[k], []
            for col, t in FIELD_MAP.items():
                if col in post_hdr and not field_eq(col, row.get(col), tgt.get(t)):
                    probs.append(f"{col}: export={row.get(col)!r} target={tgt.get(t)!r}")
            for col, t in GRAMS.items():
                if col in post_hdr and (row.get(col) or tgt.get(t)) and not grams_eq(row.get(col), tgt.get(t)):
                    probs.append(f"{col}: export={row.get(col)!r} target={tgt.get(t)!r}")
            if "Tags" in post_hdr and item_qc_tag not in tag_set(row.get("Tags")):
                fails.append(f"TAG_NOT_READ_BACK: {k} lacks `{item_qc_tag}` (R83)")
            counts["A"] += 1
            counts["A_mismatch"] += len(probs)
            rep.append(f"- {k} {row.get('Product')!r}: {len(FIELD_MAP) + len(GRAMS)} fields checked, "
                       f"{len(probs)} mismatch(es); image {'set' if row.get('Image URL') else 'EMPTY'}; "
                       f"link {'set' if row.get('Brand catalog product') else 'none'}")
            rep += [f"    - MISMATCH {p}" for p in probs]
        if counts["A_mismatch"]:
            fails.append(f"A_MISMATCH: {counts['A_mismatch']} field mismatch(es) on the intake rows (R101)")
    else:
        if added:
            fails.append(f"A_UNEXPECTED: --no-create run but {len(added)} key(s) were added: {sorted(added)}")
        if rows_allowed is None and intake:
            rows_allowed = [r.get(srccol) for r in intake if r.get("verdict") == "EXISTS" and r.get(srccol)]
        rep.append(f"- no-create mode: allowed columns {list(allow)}; rows "
                   f"{'ANY' if rows_allowed is None else sorted(rows_allowed)}")
        if not allow:
            fails.append("A_UNEXPECTED: --no-create needs at least one --allow column")
    common = sorted(set(pre) & set(post))
    changed = [(k, c, pre[k].get(c, ""), post[k].get(c, "")) for k in common for c in diff_row(pre[k], post[k], shared)]
    B, C, D = [], [], []
    for k, c, a, b in changed:
        if c == AVAILABLE and num(a) is not None and num(b) is not None and num(b) <= num(a):
            B.append((k, c, a, b))
        elif no_create and c in allow and (rows_allowed is None or k in rows_allowed):
            D.append((k, c, a, b))
        else:
            C.append((k, c, a, b))
    counts["A"] += len(D) if no_create else 0
    counts["B"], counts["C"] = len(B), len(C)
    if no_create:
        rep.append(f"- declared cells attributed: {len(D)}")
        rep += [f"    - {k} | {c}: {a!r} -> {b!r}" for k, c, a, b in D]
    rep += ["", "## B - sales drift (`Available`, down only)", "",
            f"- {len(B)} cell(s) on {len({k for k, *_ in B})} row(s)",
            "", "## C - foreign writes (not waived)", "", f"- {len(C)} cell(s)"]
    rep += [f"    - {k} | {c}: {a!r} -> {b!r}   {post[k].get('Product', '')!r}" for k, c, a, b in C]
    if C:
        fails.append(f"C_FOREIGN_CELL: {len(C)} unattributed cell(s)")
    sibs = siblings
    if sibs is None:
        # create mode: the copy sources of the approved create rows; no-create: the declared rows' matches
        src_rows = [r for r in (intake or []) if (r.get("verdict") == "NEW_ITEM_WITH_SIBLING"
                                                   and (r.get("approved") or "").strip().upper() == "Y")] \
            if not no_create else [r for r in (intake or []) if r.get("verdict") == "EXISTS"]
        sibs = sorted({(r.get(srccol) or "").strip() for r in src_rows if (r.get(srccol) or "").strip()})
    rep += ["", "## PL-grain expansion - siblings must be inert", "", f"- siblings {sibs}"]
    for s in sibs:
        if s not in pre or s not in post:
            fails.append(f"SIBLING_NOT_INERT: sibling {s} absent from an export")
            continue
        moved = [c for c in diff_row(pre[s], post[s], shared) if c != AVAILABLE]
        if moved:
            counts["sibling_moved"] += len(moved)
            fails.append(f"SIBLING_NOT_INERT: {s} moved {moved} (R50: the copy reads the sibling, never writes it)")
    needle = next((s for s in sibs if s in post), None) or (common[0] if common else None)
    rep += ["", "## Falsification - the needle is a row this change touched", ""]
    if needle is not None:
        fake = copy.deepcopy(post[needle])
        col = next((c for c in shared if c != AVAILABLE), None)
        fake[col] = (fake.get(col) or "") + "#"
        fired = len(diff_row(post[needle], fake, shared))
        rep.append(f"- needle {needle}: flipped `{col}` -> comparator saw {fired} cell(s): "
                   f"{'PASS (fires)' if fired == 1 else 'FAIL (inert)'}")
        if fired != 1:
            fails.append("COMPARATOR_INERT")
    else:
        rep.append("- no row to falsify on (both exports empty?)")
        fails.append("COMPARATOR_INERT: nothing to falsify on")
    rep += ["", "## Verdict", "", f"- {'GREEN' if not fails else 'RED'}"] + [f"- {f}" for f in fails]
    return rep, fails, counts


def main(argv):
    if "--selftest" in argv:
        return selftest()
    pre_p, post_p = get_flag(argv, "--pre"), get_flag(argv, "--post")
    ip = get_flag(argv, "--intake")
    no_create = "--no-create" in argv
    if not (pre_p and post_p and (ip or no_create)):
        print(__doc__)
        return EXIT_ABORT
    key = get_flag(argv, "--key", "SKU")
    if key not in NEWKEY:
        abort(f"--key must be one of {list(NEWKEY)}")
    required = [] if no_create else list(FIELD_MAP) + list(GRAMS)
    pre_hdr, pre = load(pre_p, key, [], "--pre")
    post_hdr, post = load(post_p, key, required, "--post")
    intake = read_csv(ip, V3_COLS, "--intake")[1] if ip else None
    mr = get_flag(argv, "--min-rows")
    rep, fails, counts = certify(pre_hdr, pre, post_hdr, post, key, intake, no_create, get_all(argv, "--allow"),
                                 listarg(get_flag(argv, "--rows")), listarg(get_flag(argv, "--siblings")),
                                 get_flag(argv, "--item-qc-tag", DEFAULT_ITEM_QC_TAG), int(mr) if mr else None)
    tenant = get_flag(argv, "--tenant")
    out_dir = get_flag(argv, "--out-dir")
    if not out_dir and tenant:
        import intake_pointers
        out_dir = intake_pointers.load(tenant)["intake"]["Intake dir"]
    if ip:
        d_, stem = version_stem(ip)
    else:
        d_, stem = os.path.dirname(os.path.abspath(post_p)), os.path.splitext(os.path.basename(post_p))[0]
    out = new_path(out_dir or d_, f"{stem}-certify-{stamp()}", ".md")
    head = [f"# Intake certify - {os.path.basename(pre_p)} -> {os.path.basename(post_p)}", "",
            f"Key `{key}` · mode {'no-create' if no_create else 'create'} · intake "
            f"`{os.path.basename(ip) if ip else 'none'}` · run {stamp()}", ""]
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(head + rep) + "\n")
    print("\n".join(rep))
    print(f"\nA {counts['A']} (mismatches {counts['A_mismatch']}) · B {counts['B']} · C {counts['C']} · "
          f"sibling cells moved {counts['sibling_moved']}")
    print(f"wrote {out}")
    return EXIT_DEFECT if fails else EXIT_OK


def selftest():
    t = Selftest("intake_certify")
    hdr = ["SKU", "Available", "Product", "Price", "Tags", "Online title"]

    def ex(rows):
        return {r["SKU"]: dict(zip(hdr, [r.get(c, "") for c in hdr])) for r in rows}

    base = [{"SKU": "1", "Available": "10", "Product": "A | P | X | 1g", "Price": "11"},
            {"SKU": "2", "Available": "5", "Product": "A | P | Y | 1g", "Price": "11", "Online title": "Y 1g"},
            {"SKU": "3", "Available": "3", "Product": "B | P | Z | 1g", "Price": "30"}]
    new = {"SKU": "4", "Available": "0", "Product": "A | P | W | 1g", "Price": "11", "Tags": DEFAULT_ITEM_QC_TAG}
    post_rows = copy.deepcopy(base) + [new]
    post_rows[1]["Available"] = "4"
    intake = [{"verdict": "NEW_ITEM_WITH_SIBLING", "approved": "Y", "new_sku": "4", "copy_source_sku": "1",
               "create_name_FINAL": "A | P | W | 1g", "lane_Price": "11", "tags": DEFAULT_ITEM_QC_TAG}]
    pre, post = ex(base), ex(post_rows)
    _, fails, c = certify(hdr, pre, hdr, post, "SKU", intake)
    t.check("GREEN: one intake row + one Available drift", fails == [] and c["A"] == 1 and c["B"] == 1, str(fails))
    p2 = copy.deepcopy(post)
    p2["3"]["Price"] = "32"
    _, f2, c2 = certify(hdr, pre, hdr, p2, "SKU", intake)
    t.check("FIRES: a foreign cell is C and fails", c2["C"] == 1 and any("C_FOREIGN" in f for f in f2))
    p3 = copy.deepcopy(post)
    p3["4"]["Price"] = "12"
    t.check("FIRES: an intake field off target is A_MISMATCH", any("A_MISMATCH" in f for f in certify(hdr, pre, hdr, p3, "SKU", intake)[1]))
    p4 = copy.deepcopy(post)
    p4["2"]["Available"] = "9"
    t.check("FIRES: Available going UP is not sales drift", certify(hdr, pre, hdr, p4, "SKU", intake)[2]["C"] == 1)
    p5 = copy.deepcopy(post)
    p5["1"]["Tags"] = "moved"
    t.check("FIRES: a sibling that moved is not inert", any("SIBLING_NOT_INERT" in f for f in certify(hdr, pre, hdr, p5, "SKU", intake)[1]))
    p6 = copy.deepcopy(post)
    p6["4"]["Tags"] = ""
    t.check("FIRES: the item-QC tag not read back (R83)", any("TAG_NOT_READ_BACK" in f for f in certify(hdr, pre, hdr, p6, "SKU", intake)[1]))
    un = [dict(intake[0], new_sku="")]
    t.check("FIRES: an approved row with no new key", any("NOT_READ_BACK" in f for f in certify(hdr, pre, hdr, post, "SKU", un)[1]))
    nc = copy.deepcopy(pre)
    nc["2"]["Online title"] = "Y Pre-Roll 1g"
    _, f7, c7 = certify(hdr, pre, hdr, nc, "SKU", None, True, ["Online title"], ["2"])
    t.check("no-create: a declared cell is attributed", f7 == [] and c7["A"] == 1, str(f7))
    _, f8, _ = certify(hdr, pre, hdr, nc, "SKU", None, True, ["Online title"], ["3"])
    t.check("FIRES: no-create, the cell on an undeclared row is C", any("C_FOREIGN" in f for f in f8))
    t.check("FIRES: a removed row", any("ROW_REMOVED" in f for f in certify(hdr, pre, hdr, {k: v for k, v in post.items() if k != "3"},
                                                                            "SKU", intake)[1]))
    return t.done()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
