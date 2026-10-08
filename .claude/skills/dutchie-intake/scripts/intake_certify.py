"""intake_certify.py - the attributed full-row diff that certifies an intake write.

  python intake_certify.py --pre <export.csv> --post <export.csv> --intake <intake-vN.csv>
                           [--key SKU|ProductId] [--siblings <k1,k2 | file>] [--min-rows <n>]
                           [--tenant <CLAUDE.md> | --out-dir <dir>]
  python intake_certify.py --pre ... --post ... --no-create --allow "Online title" [--allow <col> ...]
                           [--rows <k1,k2 | file>] [--intake <intake.csv>]
  python intake_certify.py --plan <plan.csv> --pre-active <f> --pre-retired <f> --post-active <f> --post-retired <f>
                           [--min-rows <n>] [--tenant <CLAUDE.md> | --out-dir <dir>]
  python intake_certify.py --selftest

PLAN MODE (R124) - the ONE certify of an intake write batch. It keys the UNION of the Catalog Active + Retired
exports on ProductId, with a synthetic `_state` cell (`active` / `retired`), so an un-retire is ONE planned cell
(`_state`: retired -> active), not a removed row on one side and an unexpected one on the other. The pre pair is
the lane's own pull just before the batch, the post pair its own pull just after. Populations:
  A  every planned cell at its target, plus the cells the plan declares derived (Strain Type from StrainId; an
     un-retired row's `Brand catalog product` moving BLANK -> link, because the Retired export prints that column
     blank and the post row comes from the Active file - that direction only, a changed link is C; a created
     row's global link, whose carry by the copy is unproven). A created row maps to its COPY row by the EXACT planned name; every other cell of it
     must equal what the copy inherits from its source.
  B  `Available`, numeric, down only.       C  every other moved cell - reported, never waived (exit 1).
Plan-mode flags (DEFECT, exit 1): ROW_REMOVED · C_FOREIGN_CELL · PLAN_NOT_APPLIED (a planned cell or create that
did not land - a 429 not resumed) · A_MISMATCH · A_UNEXPECTED (an added row no COPY names) · DUP_CREATE (two
added rows with one planned name) · UNRETIRE_PARTIAL (a set member still retired) · UNRETIRE_FOREIGN (a retired
item outside every set came back) · TAG_NOT_READ_BACK / TAG_EXTRA (R96, both ways) · CROSS_BRAND_RESIDUE (whole
cell) · CROSS_BRAND_RESIDUE_WORD (the source brand's name or a source-only name word still printed in Product,
Online title or Online description; word-level, whitespace collapsed) · PLAN_SHA_MISMATCH · PLAN_BEFORE_MISMATCH
(the freeze did not predate the batch) · SOURCE_ABSENT · ROW_GUARD · COMPARATOR_INERT.

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
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from intake_common import (CREATE_VERDICTS, DEFAULT_ACTIVE_TAG, DEFAULT_NEW_LINE_TAG, EXIT_ABORT,  # noqa: E402
                           EXIT_DEFECT, EXIT_OK, ITEM_PREFIX, Selftest, abort,
                           get_all, get_flag, grams_eq, new_path, norm, num, read_csv, stamp, tag_set,
                           unwrap, version_stem)
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
# R101 cross-brand copy: a cell the new item may NOT share with its source brand's item. Brand and Vendor are
# already A-set targets; these are the carried payload the intake row cannot express as a target value.
RESIDUE_COLS = ("Image URL", "Online description", "Brand catalog product", "Online title")


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
            siblings=None, prefix=ITEM_PREFIX, min_rows=None):
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
        approved = [r for r in (intake or []) if r.get("verdict") in CREATE_VERDICTS
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
            if "Tags" in post_hdr:
                # R96 / R83: the ONE decision tag the intake row names (the line's tag, or the new-line tag on a
                # NEW_PL), read back both ways - a copy also inherits its source's tag, which must be gone.
                want_t = {x for x in tag_set(tgt.get("tags")) if x.startswith(prefix)}
                got_t = {x for x in tag_set(row.get("Tags")) if x.startswith(prefix)}
                for x in sorted(want_t - got_t):
                    fails.append(f"TAG_NOT_READ_BACK: {k} lacks `{x}` (R96 / R83)")
                for x in sorted(got_t - want_t):
                    fails.append(f"TAG_EXTRA: {k} carries `{x}`, which the intake row does not name (R96: exactly one)")
            if "CROSS_BRAND_COPY" in (tgt.get("flags") or "").split(";"):
                src = pre.get((tgt.get(srccol) or "").strip())
                if src is None:
                    fails.append(f"RESIDUE_UNCHECKED: {k} is a cross-brand copy but its source {tgt.get(srccol)!r} is not in the pre export")
                for col in RESIDUE_COLS:
                    if src is not None and col in post_hdr and (src.get(col) or "").strip() \
                            and (row.get(col) or "").strip() == (src.get(col) or "").strip():
                        fails.append(f"CROSS_BRAND_RESIDUE: {k} {col} still equals its source brand's ({tgt.get(srccol)}) - R101")
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


# ---------------------------------------------------------------------------------------------------------
# Plan mode (R124): ONE certify at the end of a batch, on the UNION of the Active + Retired exports.
# ---------------------------------------------------------------------------------------------------------

STATE = "_state"            # the synthetic cell: `active` / `retired` (which export the row came from)
NOT_CELLS = ("ProductId", "SKU")
# A created row's cell the copy MAY carry or not: the copy's carry of the global link is unproven (probe P1
# rides the first real copy), so it is declared, never a defect, unless the plan writes it.
CREATE_DECLARED = ("Brand catalog product",)
# A column the RETIRED export prints blank whatever the record holds (KB "Retired products"; found again by the
# intake session 2026-10-08): an un-retired row's cell moves blank -> link only because the post row now comes
# from the Active file. Declared derived of `_state` (intake_plan.DERIVES), in that ONE direction: a pre value
# that is not blank, then moves, is a write and lands in C.
RETIRED_BLANK_COLS = ("Brand catalog product",)


def union(active_rows, retired_rows, label):
    """{ProductId: row + _state}. A key in both files (or twice) is not one pull: ABORT."""
    out = {}
    for st, rows in (("active", active_rows), ("retired", retired_rows)):
        for r in rows:
            k = (r.get("ProductId") or "").strip()
            if not k:
                abort(f"{label}: a row has no ProductId - plan mode keys on ProductId")
            if k in out:
                abort(f"{label}: ProductId {k} appears twice across the Active + Retired pair (KEY_IN_BOTH)")
            out[k] = dict(r, **{STATE: st})
    return out


def cell_eq(field, export_val, plan_val):
    """An export cell against a plan value (`name:` stripped; money, grams and tags compared by meaning)."""
    from intake_plan import GRAMS as PG, MONEY as PM, NUMBERS as PN
    a, b = (export_val or "").strip(), (plan_val or "").strip()
    if b.startswith("name:"):
        b = b[len("name:"):]
    if field == "Tags":
        return tag_set(a) == tag_set(b)
    if not a or not b:
        return a == b
    if field in PM:
        x, y = num(a), num(b)
        return x is not None and y is not None and abs(x - y) < 0.005
    if field in PG:
        return grams_eq(a, b)
    if field in PN:
        x, y = num(a), num(b)
        return x is not None and y is not None and abs(x - y) < 1e-9
    return a == b


def _wnorm(s):
    """norm() keeps a dot for decimals (`3.5g`); a sentence-final dot is not part of a word."""
    return " ".join(re.sub(r"(?<!\d)\.|\.(?!\d)", " ", norm(s)).split())


def _words(s):
    return _wnorm(s).split()


def residue_words(src, planned_name, new_brand, cells):
    """Word-level residue of a cross-brand copy source in the new row's text cells (whitespace collapsed, case
    ignored - the export drops description line breaks): the source brand's name as a phrase, or a token of the
    source's name that the planned name and the new brand do not carry (3+ chars, not a bare number)."""
    own = set(_words(planned_name)) | set(_words(new_brand))
    only = sorted({w for w in _words(src.get("Product")) if w not in own and len(w) >= 3 and not w.isdigit()})
    hits = []
    for col, text in cells.items():
        t = _wnorm(text)
        sb = _wnorm(src.get("Brand"))
        if sb and sb != _wnorm(new_brand) and re.search(r"(?:^| )" + re.escape(sb) + r"(?: |$)", t):
            hits.append(f"{col}: the source brand {src.get('Brand')!r}")
        for w in only:
            if re.search(r"(?:^| )" + re.escape(w) + r"(?: |$)", t):
                hits.append(f"{col}: the source-only word {w!r}")
    return hits


def certify_plan(plan, pre_hdr, pre, post_hdr, post, min_rows=None, prefix=ITEM_PREFIX):
    """Pure. `pre` / `post` = union() of each pull. Returns (report lines, fails, counts)."""
    from intake_plan import DERIVES, FIELD_COL, row_sha1
    rep, fails = [], []
    counts = {"planned": 0, "A": 0, "A_derived": 0, "B": 0, "C": 0, "created": 0}
    cols = [c for c in pre_hdr if c in post_hdr and c not in NOT_CELLS] + [STATE]
    rep += ["## Row guard", "",
            f"- pre {len(pre)} rows ({sum(1 for r in pre.values() if r[STATE] == 'retired')} retired), post {len(post)} "
            f"rows ({sum(1 for r in post.values() if r[STATE] == 'retired')} retired); cells compared per row {len(cols)}"]
    if min_rows is not None and (len(pre) < min_rows or len(post) < min_rows):
        fails.append(f"ROW_GUARD: a union is under the {min_rows}-row floor (a filtered one-off?)")
    edited = [r.get("seq") for r in plan if row_sha1(r) != (r.get("row_sha1") or "")]
    if edited:
        fails.append(f"PLAN_SHA_MISMATCH: plan row(s) {edited[:10]} changed after the plan was built")
    if pre == post and plan:
        rep.append("- the post pull is IDENTICAL to the pre pull: a cache, not a result - pull again later")
    removed = sorted(set(pre) - set(post))
    if removed:
        fails.append(f"ROW_REMOVED: {len(removed)} pre key(s) absent from both post files: {removed[:10]}")
    added = set(post) - set(pre)
    # --- creates: an added ProductId maps to its COPY row by the exact planned name ----------------------------
    keymap, src_of, mapped = {}, {}, set()
    for c in [r for r in plan if r.get("field") == "_copy"]:
        hits = sorted(k for k in added if (post[k].get("Product") or "").strip() == (c.get("target") or "").strip())
        if len(hits) > 1:
            fails.append(f"DUP_CREATE: {len(hits)} added rows carry the planned name {c['target']!r}: {hits}")
        if not hits:
            fails.append(f"PLAN_NOT_APPLIED: the create {c['product_key']} {c['target']!r} is in neither post file")
            continue
        keymap[c["product_key"]] = hits[0]
        src_of[hits[0]] = (c.get("before") or "").strip()
        mapped.update(hits)
    if added - mapped:
        fails.append(f"A_UNEXPECTED: added key(s) no COPY row names: {sorted(added - mapped)}")
    planned, derived = {}, set()
    for r in plan:
        col = FIELD_COL.get(r.get("field"))
        key = keymap.get(r.get("product_key"), r.get("product_key"))
        if not col or str(key).startswith("new:"):
            continue
        planned[(key, col)] = r
        for d in DERIVES.get(r.get("field"), []):
            derived.add((key, d))
    counts["planned"] = len(planned)

    def judge(k, col, before_val, after_val, p):
        f = p["field"]
        if f != "_copy" and not cell_eq(f, before_val, p.get("before")):
            fails.append(f"PLAN_BEFORE_MISMATCH: {k} {col} was {before_val!r} in the pre pull, the plan says "
                         f"{p.get('before')!r} (the freeze must predate the batch)")
        if cell_eq(f, after_val, p.get("target")):
            counts["A"] += 1
            return
        if col == "Tags":
            want = {x for x in tag_set(p.get("target")) if x.startswith(prefix)}
            got = {x for x in tag_set(after_val) if x.startswith(prefix)}
            for x in sorted(want - got):
                fails.append(f"TAG_NOT_READ_BACK: {k} lacks `{x}` (R96 / R83)")
            for x in sorted(got - want):
                fails.append(f"TAG_EXTRA: {k} carries `{x}`, which the plan does not name (R96: exactly one)")
        if col == STATE:
            fails.append(f"UNRETIRE_PARTIAL: {k} is still in the Retired file (its lane comes back WHOLE, R101)")
        elif f != "_copy" and cell_eq(f, after_val, p.get("before")):
            fails.append(f"PLAN_NOT_APPLIED: {k} {col} still {after_val!r}; planned {p.get('target')!r} (seq {p.get('seq')})")
        else:
            fails.append(f"A_MISMATCH: {k} {col} = {after_val!r}; planned {p.get('target')!r} (seq {p.get('seq')})")

    C = []
    for k in sorted(set(pre) & set(post), key=lambda x: (len(x), x)):
        for col in cols:
            a, b = pre[k].get(col, ""), post[k].get(col, "")
            p = planned.get((k, col))
            if p:
                judge(k, col, a, b, p)
                continue
            if a == b:
                continue
            if (k, col) in derived and col in RETIRED_BLANK_COLS and (a or "").strip():
                # declared derived ONLY as blank -> link: a link that changed (or vanished) is a write
                C.append((k, col, a, b))
            elif (k, col) in derived:
                counts["A_derived"] += 1
            elif col == AVAILABLE and num(a) is not None and num(b) is not None and num(b) <= num(a):
                counts["B"] += 1
            elif col == STATE and a == "retired" and b == "active":
                fails.append(f"UNRETIRE_FOREIGN: {k} {pre[k].get('Product')!r} left the Retired file and no plan row "
                             f"brings it back (the brand's other retired lines stay retired, R101)")
                C.append((k, col, a, b))
            else:
                C.append((k, col, a, b))
    # --- created rows: every cell = its planned target, else what the copy inherits from its source ------------
    for k in sorted(mapped & set(keymap.values())):
        counts["created"] += 1
        sid = src_of.get(k, "")
        src = pre.get(sid)
        if src is None:
            fails.append(f"SOURCE_ABSENT: created {k} names copy source {sid!r}, which is not in the pre pull")
            continue
        for col in cols:
            b = post[k].get(col, "")
            p = planned.get((k, col))
            inherited = planned[(sid, col)]["target"] if (sid, col) in planned else src.get(col, "")
            if col == STATE:
                inherited = "active"
            if p:
                judge(k, col, inherited, b, p)
                continue
            if col == AVAILABLE:
                if num(b) not in (None, 0.0):
                    C.append((k, col, "<new>", b))
                continue
            if cell_eq("", b, inherited):
                continue
            if (k, col) in derived or col in CREATE_DECLARED:
                counts["A_derived"] += 1
            else:
                C.append((k, col, inherited, b))
        new_brand = planned.get((k, "Brand"))
        if new_brand and norm(src.get("Brand")) != norm(new_brand["target"][len("name:"):]):
            nb = new_brand["target"][len("name:"):]
            for col in RESIDUE_COLS:
                if col in post[k] and (src.get(col) or "").strip() and (post[k].get(col) or "").strip() == (src.get(col) or "").strip():
                    fails.append(f"CROSS_BRAND_RESIDUE: {k} {col} still equals its source brand's ({sid}) - R101")
            for h in residue_words(src, post[k].get("Product", ""), nb,
                                   {c: post[k].get(c, "") for c in ("Product", "Online title", "Online description")}):
                fails.append(f"CROSS_BRAND_RESIDUE_WORD: {k} {h} - R101")
    counts["C"] = len(C)
    if C:
        fails.append(f"C_FOREIGN_CELL: {len(C)} unplanned moved cell(s)")
    rep += ["", "## A - planned cells at target (+ declared derived)", "",
            f"- planned cells {counts['planned']}; at target {counts['A']}; declared derived moved {counts['A_derived']}; "
            f"created rows {counts['created']} (mapped by planned name: {dict(sorted(keymap.items()))})",
            "", "## B - sales drift (`Available`, down only)", "", f"- {counts['B']} cell(s)",
            "", "## C - unplanned moved cells (not waived)", "", f"- {len(C)} cell(s)"]
    rep += [f"    - {k} | {c}: {a!r} -> {b!r}   {post[k].get('Product', '')!r}" for k, c, a, b in C]
    touched = sorted({k for (k, _c) in planned if k in post}) or sorted(post)
    rep += ["", "## Falsification - the needle is a row this batch touched", ""]
    if touched:
        needle = touched[0]
        fake = copy.deepcopy(post[needle])
        col = next(c for c in cols if c not in (AVAILABLE, STATE))
        fake[col] = (fake.get(col) or "") + "#"
        fired = sum(1 for c in cols if (post[needle].get(c, "") or "") != (fake.get(c, "") or ""))
        rep.append(f"- needle {needle}: flipped `{col}` -> comparator saw {fired} cell(s): "
                   f"{'PASS (fires)' if fired == 1 else 'FAIL (inert)'}")
        if fired != 1:
            fails.append("COMPARATOR_INERT")
    else:
        fails.append("COMPARATOR_INERT: nothing to falsify on")
    rep += ["", "## Verdict", "", f"- {'GREEN' if not fails else 'RED'}"] + [f"- {f}" for f in fails]
    return rep, fails, counts


def main_plan(argv):
    from intake_plan import PLAN_COLS
    need = ["--plan", "--pre-active", "--pre-retired", "--post-active", "--post-retired"]
    p = {k: get_flag(argv, k) for k in need}
    if not all(p.values()):
        print(__doc__)
        return EXIT_ABORT
    plan = read_csv(p["--plan"], PLAN_COLS, "--plan")[1]
    h1, pa = read_csv(p["--pre-active"], ["ProductId"], "--pre-active")
    _, pr = read_csv(p["--pre-retired"], ["ProductId"], "--pre-retired")
    h2, qa = read_csv(p["--post-active"], ["ProductId"], "--post-active")
    _, qr = read_csv(p["--post-retired"], ["ProductId"], "--post-retired")
    mr = get_flag(argv, "--min-rows")
    rep, fails, counts = certify_plan(plan, h1, union(pa, pr, "pre"), h2, union(qa, qr, "post"),
                                      int(mr) if mr else None)
    tenant, out_dir = get_flag(argv, "--tenant"), get_flag(argv, "--out-dir")
    if not out_dir and tenant:
        import intake_pointers
        out_dir = intake_pointers.load(tenant)["intake"]["Intake dir"]
    d_, stem = version_stem(p["--plan"])
    out = new_path(out_dir or d_, f"{stem}-certify-{stamp()}", ".md")
    head = [f"# Intake batch certify (R124) - plan `{os.path.basename(p['--plan'])}`", "",
            f"Pre: `{os.path.basename(p['--pre-active'])}` + `{os.path.basename(p['--pre-retired'])}` · post: "
            f"`{os.path.basename(p['--post-active'])}` + `{os.path.basename(p['--post-retired'])}` · key ProductId + "
            f"`{STATE}` · run {stamp()}", ""]
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(head + rep) + "\n")
    print("\n".join(rep))
    print(f"\nA {counts['A']} of {counts['planned']} planned (+{counts['A_derived']} derived) · B {counts['B']} · "
          f"C {counts['C']} · created {counts['created']}")
    print(f"wrote {out}")
    return EXIT_DEFECT if fails else EXIT_OK


def main(argv):
    if "--selftest" in argv:
        return selftest()
    if "--plan" in argv:
        return main_plan(argv)
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
                                 ITEM_PREFIX, int(mr) if mr else None)
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
    new = {"SKU": "4", "Available": "0", "Product": "A | P | W | 1g", "Price": "11", "Tags": DEFAULT_ACTIVE_TAG}
    post_rows = copy.deepcopy(base) + [new]
    post_rows[1]["Available"] = "4"
    intake = [{"verdict": "NEW_ITEM_WITH_SIBLING", "approved": "Y", "new_sku": "4", "copy_source_sku": "1",
               "create_name_FINAL": "A | P | W | 1g", "lane_Price": "11", "tags": DEFAULT_ACTIVE_TAG}]
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
    t.check("FIRES: the decision tag not read back (R96)", any("TAG_NOT_READ_BACK" in f for f in certify(hdr, pre, hdr, p6, "SKU", intake)[1]))
    p7 = copy.deepcopy(post)
    p7["4"]["Tags"] = f"{DEFAULT_ACTIVE_TAG}, ITM - Protect"
    t.check("FIRES: a tag inherited from the copy source is TAG_EXTRA (R96 exactly one)",
            any("TAG_EXTRA" in f for f in certify(hdr, pre, hdr, p7, "SKU", intake)[1]))
    nl = [dict(intake[0], verdict="NEW_PL", tags=DEFAULT_NEW_LINE_TAG)]
    p8 = copy.deepcopy(post)
    p8["4"]["Tags"] = DEFAULT_NEW_LINE_TAG
    _, f9, c9 = certify(hdr, pre, hdr, p8, "SKU", nl)
    t.check("GREEN: an approved NEW_PL row is a create row with the new-line tag (R83)", f9 == [] and c9["A"] == 1, str(f9))
    t.check("FIRES: a NEW_PL row read back without the new-line tag",
            any("TAG_NOT_READ_BACK" in f for f in certify(hdr, pre, hdr, post, "SKU", nl)[1]))
    hdr_x = hdr + ["Image URL", "Brand"]

    def exx(rows):
        return {r["SKU"]: dict(zip(hdr_x, [r.get(c, "") for c in hdr_x])) for r in rows}
    src = {"SKU": "3", "Available": "3", "Product": "B | P | Z | 1g", "Price": "30", "Image URL": "b-brand.jpg", "Brand": "B",
           "Online title": "Z 1g"}
    xb = [dict(base[0], Brand="A"), dict(base[1], Brand="A"), src]
    newx = dict(new, Brand="A", **{"Image URL": "b-brand.jpg", "Online title": "Z 1g"})
    ix = [dict(intake[0], copy_source_sku="3", lane_Brand="A", flags="NEW_LINE_FIELDS;CROSS_BRAND_COPY", online_title="")]
    px = exx(copy.deepcopy(xb) + [newx])
    _, fx_, _ = certify(hdr_x, exx(xb), hdr_x, px, "SKU", ix)
    t.check("FIRES: a cross-brand copy still carrying the source brand's image is CROSS_BRAND_RESIDUE (R101)",
            any("CROSS_BRAND_RESIDUE" in f and "Image URL" in f for f in fx_), str(fx_))
    t.check("FIRES: the source's Online title on the copy is both an A mismatch (target blank) and residue",
            any("CROSS_BRAND_RESIDUE" in f and "Online title" in f for f in fx_) and any("A_MISMATCH" in f for f in fx_))
    px2 = copy.deepcopy(px)
    px2["4"]["Image URL"], px2["4"]["Online title"] = "a-brand.jpg", ""
    _, fx2, _ = certify(hdr_x, exx(xb), hdr_x, px2, "SKU", ix)
    t.check("QUIET: residue clears once the image and title moved off the source's values", not any("RESIDUE" in f or "A_MISMATCH" in f for f in fx2), str(fx2))
    ix3 = [dict(ix[0], flags="NEW_LINE_FIELDS")]
    t.check("QUIET: a same-brand copy keeping its sibling's image is not residue",
            not any("RESIDUE" in f for f in certify(hdr_x, exx(xb), hdr_x, px, "SKU", ix3)[1]))
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
    plan_selftest(t)
    return t.done()


def plan_fixture(online_title=None):
    """The synthetic R124 batch on ../fixtures/plan-*.csv (Brand A, Brand B, Strain X ...): the plan is built
    with the retired guard SIMULATED as proven (probe P2) - the CLI never can."""
    import intake_plan as PL
    fx = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fixtures")

    def rd(n):
        return read_csv(os.path.join(fx, n), [], n)
    hdr, pa = rd("plan-pre-active.csv")
    pr, qa, qr = rd("plan-pre-retired.csv")[1], rd("plan-post-active.csv")[1], rd("plan-post-retired.csv")[1]
    intake = rd("plan-intake.csv")[1]
    if online_title is not None:
        intake[2]["online_title"] = online_title
    rows, ref, _ = PL.build_plan(intake, pa, pr, rd("plan-strains.csv")[1], rd("plan-categories.csv")[1],
                                 rd("plan-brands.csv")[1], guard=PL._probed())
    return dict(plan=rows, refusals=ref, hdr=hdr, pa=pa, pr=pr, qa=qa, qr=qr)


def run_plan(fx, edit=None):
    """certify_plan on the fixture, after `edit(post_active_rows, post_retired_rows, plan)` mutates a copy."""
    qa, qr, plan = copy.deepcopy(fx["qa"]), copy.deepcopy(fx["qr"]), copy.deepcopy(fx["plan"])
    if edit:
        edit(qa, qr, plan)
    return certify_plan(plan, fx["hdr"], union(fx["pa"], fx["pr"], "pre"), fx["hdr"], union(qa, qr, "post"))


def _row(rows, pid):
    return next(r for r in rows if r["ProductId"] == pid)


def _move(src, dst, pid):
    r = _row(src, pid)
    src.remove(r)
    dst.append(r)


def plan_selftest(t):
    fx = plan_fixture()
    _, fails, c = run_plan(fx)
    t.check("PLAN GREEN: A = every planned cell (19) + 2 declared derived, B 1, C 0, exit 0",
            fails == [] and fx["refusals"] == [] and c["A"] == c["planned"] == 19 and c["A_derived"] == 2
            and c["B"] == 1 and c["C"] == 0, f"{fails} {c}")

    def fires(label, flag, edit, fx_=None):
        _, f, _ = run_plan(fx_ or fx, edit)
        t.check(f"FIRES {flag}: {label}", any(x.startswith(flag + ":") for x in f), str(f))

    fires("a pre key absent from both post files", "ROW_REMOVED", lambda a, r, p: a.remove(_row(a, "602")))
    fires("a foreign cell moved on an untouched item", "C_FOREIGN_CELL", lambda a, r, p: _row(a, "602").update(Price="12"))
    fires("a planned cell that did not move (a 429 that was not resumed)", "PLAN_NOT_APPLIED",
          lambda a, r, p: _row(a, "402").update(Cost="4"))
    fires("a planned create that never landed", "PLAN_NOT_APPLIED", lambda a, r, p: a.remove(_row(a, "801")))
    fires("a lane member still in the Retired file", "UNRETIRE_PARTIAL", lambda a, r, p: _move(a, r, "402"))
    fires("a retired item outside every set came back", "UNRETIRE_FOREIGN", lambda a, r, p: _move(r, a, "403"))
    fires("two added rows carry one planned name", "DUP_CREATE",
          lambda a, r, p: a.append(dict(_row(a, "801"), ProductId="803", SKU="8003")))
    fires("an added row no COPY row names", "A_UNEXPECTED",
          lambda a, r, p: a.append(dict(_row(a, "801"), ProductId="804", SKU="8004", Product="Brand A | Pre-Roll | Stray | 1g")))
    fires("the decision tag missing on a create", "TAG_NOT_READ_BACK", lambda a, r, p: _row(a, "802").update(Tags=""))
    fires("the old decision tag left beside the new one on an un-retire", "TAG_EXTRA",
          lambda a, r, p: _row(a, "401").update(Tags="ITM - Active, ITM - Discontinue"))
    fires("the source brand's image still on a cross-brand copy (whole cell)", "CROSS_BRAND_RESIDUE",
          lambda a, r, p: _row(a, "802").update(**{"Image URL": "img-b-mango.jpg"}))
    fires("a plan row edited after the build", "PLAN_SHA_MISMATCH", lambda a, r, p: p[11].update(target="17"))
    fires("a cell a create row inherits moved off its source", "C_FOREIGN_CELL", lambda a, r, p: _row(a, "801").update(Vendor="Vendor Other"))
    fires("a derived cell moved where the plan declares none", "C_FOREIGN_CELL",
          lambda a, r, p: _row(a, "602").update(**{"Strain Type": "Sativa"}))
    # the WORD residue: the plan itself carries a source-only word (the Operator's title kept "Mango"); the whole-cell
    # leg cannot see it and A is green, so ONLY the word leg fires - the case it exists for.
    fxw = plan_fixture(online_title="Mango Lime Gummies 100mg")

    def word_post(a, r, p):
        _row(a, "802")["Online title"] = "Mango Lime Gummies 100mg"
    _, fw, _ = run_plan(fxw, word_post)
    t.check("FIRES CROSS_BRAND_RESIDUE_WORD alone: a source-only name word in the new row's Online title",
            [x.split(":")[0] for x in fw] == ["CROSS_BRAND_RESIDUE_WORD"], str(fw))
    _, fw2, _ = run_plan(fx, lambda a, r, p: _row(a, "802").update(**{"Online description": "Lime gummies.  From BRAND B."}))
    t.check("FIRES CROSS_BRAND_RESIDUE_WORD: the source brand's name, case and whitespace ignored",
            any(x.startswith("CROSS_BRAND_RESIDUE_WORD:") and "source brand" in x for x in fw2), str(fw2))
    rep0, _, _ = run_plan(fx)
    t.check("the un-retired row's `Brand catalog product` blank -> link is declared derived, not C (Retired export blanks it)",
            not any("401 | Brand catalog product" in x for x in rep0) and (_row(fx["pr"], "401")["Brand catalog product"] == ""
                                                                       and _row(fx["qa"], "401")["Brand catalog product"] != ""))
    fxl = plan_fixture()
    fxl["pr"] = copy.deepcopy(fxl["pr"])
    _row(fxl["pr"], "401")["Brand catalog product"] = "Brand A Strain Z Old Link"
    _, fl, cl = run_plan(fxl)
    t.check("FIRES C_FOREIGN_CELL: an un-retired row whose link CHANGED (not blank -> link) is a write, never derived",
            any(x.startswith("C_FOREIGN_CELL:") for x in fl) and cl["C"] == 1 and cl["A_derived"] == 1, f"{fl} {cl}")
    fxb = plan_fixture()
    fxb["pa"] = copy.deepcopy(fxb["pa"])
    _row(fxb["pr"], "402")["Cost"] = "3.9"
    _, fb, _ = run_plan(fxb)
    t.check("FIRES PLAN_BEFORE_MISMATCH: the pre pull is not the freeze the plan was built on",
            any(x.startswith("PLAN_BEFORE_MISMATCH:") for x in fb), str(fb))
    try:
        union([{"ProductId": "1"}], [{"ProductId": "1"}], "t")
        t.check("ABORT: a key in both the Active and the Retired file", False)
    except SystemExit as e:
        t.check("ABORT: a key in both the Active and the Retired file", e.code == EXIT_ABORT)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
