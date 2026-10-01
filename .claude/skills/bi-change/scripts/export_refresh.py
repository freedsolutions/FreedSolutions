#!/usr/bin/env python3
"""Export refresh: the FILE half of a Backoffice export pull.

A lane pulls the exports in the browser (the platform KB holds the pull recipe); the files land in a
download folder under whatever name the platform gave them. This tool does everything after that:

  1. CLASSIFY each file by its CSV header (never by its name). An unknown header is skipped and named.
  2. SPLIT the two catalog exports (same header) by ProductId overlap with the newest frozen active and
     retired files. A tie or a weak match ABORTS; pass --active / --retired to state it.
  3. GUARD: the header must equal the newest frozen file of that kind exactly, and the row count must sit
     inside --row-guard of it (a filtered one-off export is the failure this catches).
  4. FREEZE a copy into the exports dir as `<date><letter>-<slug>.csv`. One letter per run; never overwrite.
     A file already frozen (same SHA-256) is not frozen twice.
  5. PLACE the set into the drop dir (the folder a person reads from) as `<date>-<Label>.csv`.
  6. RETIRE the previous version of each placed kind in the drop dir: sent to the Recycle Bin, and only
     when a byte-identical frozen copy exists (one is frozen first if not). Nothing is hard-deleted.

Dry-run by default: it prints the plan and writes nothing. `--apply` executes it.

  python export_refresh.py --exports-dir <dir> --drop-dir <dir> [files ...]
  python export_refresh.py --exports-dir <dir> --drop-dir <dir> --src <download dir> --since-minutes 120
  python export_refresh.py --selftest
"""
import argparse
import csv
import datetime as dt
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# kind -> (slug in the exports dir, label in the drop dir, the header columns that identify it)
KINDS = {
    "catalog":    (None, None, ["ProductId", "SKU", "Available", "Product", "Is cannabis"]),
    "inventory":  ("inventory", "Inventory", ["Available", "SKU", "Product", "Room", "Package ID"]),
    "categories": ("categories", "Categories", ["Tax category", "Master category", "Category", "Global Category"]),
    "strains":    ("strains", "Strains", ["Strain name", "Type", "Abbreviation", "Description"]),
    "brands":     ("brands", "Brands", ["Display name", "Associated global brand", "Brand id"]),
    "discounts":  ("discounts", "Discounts", ["ID", "Name", "Status", "Code", "Type", "Start", "End"]),
    "rooms":      ("rooms", "Rooms", ["Name", "Room Types", "External ID", "Location type"]),
    "tags":       ("tags", "Tags", ["Tag"]),
}
CATALOG = {"active": ("catalog-active", "Catalog - Active"), "retired": ("catalog-retired", "Catalog - Retired")}
DATED = re.compile(r"^(\d{4}-\d{2}-\d{2})([a-z]?)-(.+)\.csv$", re.I)


class Abort(Exception):
    pass


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_header(p):
    with open(p, newline="", encoding="utf-8-sig") as f:
        return next(csv.reader(f), [])


def row_count(p):
    with open(p, newline="", encoding="utf-8-sig") as f:
        return max(sum(1 for _ in csv.reader(f)) - 1, 0)


def classify(header):
    """Longest identifying prefix wins, so `Tag` (one column) cannot swallow a wider export."""
    best = None
    for kind, (_, _, sig) in KINDS.items():
        if header[:len(sig)] == sig and (kind != "tags" or len(header) == 1):
            if best is None or len(sig) > len(KINDS[best][2]):
                best = kind
    return best


def product_ids(p):
    with open(p, newline="", encoding="utf-8-sig") as f:
        return {r["ProductId"] for r in csv.DictReader(f)}


def newest_frozen(exports_dir, slug):
    """Newest frozen file of a slug by its (date, letter) name, not by mtime."""
    best = None
    for f in Path(exports_dir).glob("*.csv"):
        m = DATED.match(f.name)
        if m and m.group(3).lower() == slug:
            key = (m.group(1), m.group(2).lower())
            if best is None or key > best[0]:
                best = (key, f)
    return best[1] if best else None


def split_catalog(path, exports_dir, forced=None):
    if forced:
        return forced
    fa, fr = newest_frozen(exports_dir, "catalog-active"), newest_frozen(exports_dir, "catalog-retired")
    if not fa or not fr:
        raise Abort(f"{Path(path).name}: no frozen catalog pair to compare against; pass --active / --retired")
    ids = product_ids(path)
    if not ids:
        raise Abort(f"{Path(path).name}: catalog export has no rows")
    sa, sr = len(ids & product_ids(fa)) / len(ids), len(ids & product_ids(fr)) / len(ids)
    if sa >= 0.80 and sr < 0.20:
        return "active"
    if sr >= 0.80 and sa < 0.20:
        return "retired"
    raise Abort(f"{Path(path).name}: cannot tell active from retired (overlap active {sa:.0%}, retired {sr:.0%}); "
                f"pass --active / --retired")


def next_letter(exports_dir, date):
    used = set()
    for f in Path(exports_dir).glob(f"{date}*.csv"):
        m = DATED.match(f.name)
        if m:
            used.add(m.group(2).lower())
    if not used:
        return ""
    for c in "abcdefghijklmnopqrstuvwxyz":
        if c not in used:
            return c
    raise Abort(f"no free letter left for {date}")


def frozen_copy_of(exports_dir, digest, cache):
    if not cache:
        for f in Path(exports_dir).glob("*.csv"):
            cache.setdefault(sha256(f), f)
    return cache.get(digest)


def recycle(path):
    """Send to the Recycle Bin (Windows). Never a hard delete."""
    if os.name != "nt":
        raise Abort("retire needs the Windows Recycle Bin; run with --no-retire on this platform")
    quoted = str(path).replace("'", "''")
    cmd = ("Add-Type -AssemblyName Microsoft.VisualBasic; "
           f"[Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile('{quoted}','OnlyErrorDialogs','SendToRecycleBin')")
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd], capture_output=True, text=True)
    if r.returncode != 0 or Path(path).exists():
        raise Abort(f"could not recycle {path}: {r.stderr.strip()[:200]}")


def plan(files, exports_dir, drop_dir, date, row_guard=(0.5, 2.0), forced=None, retire=True):
    """Returns (steps, notes). A step is a dict; nothing is written here."""
    forced = forced or {}
    notes, items, cache = [], [], {}
    seen = {}
    for p in files:
        p = Path(p)
        header = read_header(p)
        kind = classify(header)
        if kind is None:
            notes.append(f"SKIPPED {p.name}: header not recognised ({', '.join(header[:4])}…)")
            continue
        if kind == "catalog":
            which = split_catalog(p, exports_dir, forced.get(str(p)))
            slug, label = CATALOG[which]
        else:
            slug, label = KINDS[kind][0], KINDS[kind][1]
        if slug in seen:
            raise Abort(f"two files of kind {slug}: {seen[slug].name} and {p.name}")
        seen[slug] = p
        prior = newest_frozen(exports_dir, slug)
        rows = row_count(p)
        if prior:
            if read_header(prior) != header:
                raise Abort(f"{p.name}: header differs from the newest frozen {prior.name} — a column moved; stop and read it")
            pr = row_count(prior)
            if pr and not (row_guard[0] * pr <= rows <= row_guard[1] * pr):
                raise Abort(f"{p.name}: {rows} rows vs {pr} in {prior.name} — outside the row guard; a filtered export?")
        items.append({"src": p, "slug": slug, "label": label, "rows": rows, "sha": sha256(p),
                      "prior": prior.name if prior else None})
    if not items:
        return [], notes
    letter = None
    steps = []
    for it in items:
        already = frozen_copy_of(exports_dir, it["sha"], cache)
        if already:
            it["frozen"] = already
            steps.append({"do": "already-frozen", "src": it["src"], "as": already})
        else:
            if letter is None:
                letter = next_letter(exports_dir, date)
            target = Path(exports_dir) / f"{date}{letter}-{it['slug']}.csv"
            if target.exists():
                raise Abort(f"freeze target exists: {target.name}")
            it["frozen"] = target
            steps.append({"do": "freeze", "src": it["src"], "to": target})
    if drop_dir:
        for it in items:
            target = Path(drop_dir) / f"{date}-{it['label']}.csv"
            olds = []
            for f in Path(drop_dir).glob(f"*-{it['label']}.csv"):
                m = re.match(r"^\d{4}-\d{2}-\d{2}[a-z]?-" + re.escape(it["label"]) + r"\.csv$", f.name, re.I)
                if m and not (f.resolve() == target.resolve() and sha256(f) == it["sha"]):
                    olds.append(f)
            for old in sorted(olds):
                if not retire:
                    notes.append(f"KEPT (no retire) {old.name}")
                    continue
                digest = sha256(old)
                if not frozen_copy_of(exports_dir, digest, cache) and digest != it["sha"]:
                    m = re.match(r"^(\d{4}-\d{2}-\d{2})", old.name)
                    odate = m.group(1)
                    ol = next_letter(exports_dir, odate) or "a"
                    while (Path(exports_dir) / f"{odate}{ol}-{it['slug']}.csv").exists():
                        ol = chr(ord(ol) + 1)
                    ft = Path(exports_dir) / f"{odate}{ol}-{it['slug']}.csv"
                    steps.append({"do": "freeze-old", "src": old, "to": ft})
                    cache[digest] = ft
                steps.append({"do": "retire", "src": old})
            if target.exists() and sha256(target) == it["sha"]:
                steps.append({"do": "already-placed", "src": it["src"], "as": target})
            else:
                steps.append({"do": "place", "src": it["src"], "to": target})
    return steps, notes


def execute(steps, recycler=recycle):
    for s in steps:
        if s["do"] in ("freeze", "freeze-old", "place"):
            if Path(s["to"]).exists():
                raise Abort(f"refusing to overwrite {s['to']}")
            shutil.copy2(s["src"], s["to"])
            if sha256(s["to"]) != sha256(s["src"]):
                raise Abort(f"copy is not byte-identical: {s['to']}")
        elif s["do"] == "retire":
            recycler(s["src"])


def show(steps, notes):
    for s in steps:
        tgt = s.get("to") or s.get("as") or ""
        print(f"  {s['do']:<15} {Path(s['src']).name}" + (f"  ->  {tgt}" if tgt else ""))
    for n in notes:
        print("  " + n)


def selftest():
    fails, ran = [], []

    def check(name, cond):
        print(("  PASS  " if cond else "  FAIL  ") + name)
        ran.append(name)
        if not cond:
            fails.append(name)

    def write(p, header, rows):
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, quoting=csv.QUOTE_ALL)
            w.writerow(header)
            w.writerows(rows)

    cat_h = ["ProductId", "SKU", "Available", "Product", "Is cannabis", "Type"]
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        ex, drop, dl, bin_ = td / "exports", td / "drop", td / "dl", td / "bin"
        for d in (ex, drop, dl, bin_):
            d.mkdir()
        act = [[str(i), f"s{i}", "1", f"item {i}", "Yes", "Q"] for i in range(100)]
        ret = [[str(i), f"s{i}", "0", f"item {i}", "Yes", "Q"] for i in range(1000, 1300)]
        write(ex / "2026-01-01-catalog-active.csv", cat_h, act)
        write(ex / "2026-01-01-catalog-retired.csv", cat_h, ret)
        write(ex / "2026-01-01-strains.csv", KINDS["strains"][2], [["A", "Hybrid", "A", "A"]] * 10)
        shutil.copy2(ex / "2026-01-01-catalog-active.csv", drop / "2026-01-01-Catalog - Active.csv")
        write(drop / "2025-12-30-Strains.csv", KINDS["strains"][2], [["old", "Hybrid", "old", "old"]] * 9)

        check("classify: each known header maps to its kind",
              all(classify(sig + ["x"] * (0 if k == "tags" else 1)) == k for k, (_, _, sig) in KINDS.items()))
        check("classify: an unknown header is None", classify(["Foo", "Bar"]) is None)
        check("classify: a wider export is not mistaken for the one-column tag file", classify(["Tag", "Other"]) != "tags")

        new_act = dl / "export (1).csv"
        write(new_act, cat_h, act + [["5000", "s", "1", "new item", "Yes", "Q"]])
        new_ret = dl / "export (2).csv"
        write(new_ret, cat_h, ret)
        check("catalog split: active by overlap", split_catalog(new_act, ex) == "active")
        check("catalog split: retired by overlap", split_catalog(new_ret, ex) == "retired")
        mixed = dl / "mixed.csv"
        write(mixed, cat_h, act[:50] + ret[:50])
        try:
            split_catalog(mixed, ex)
            check("catalog split: a tie aborts", False)
        except Abort:
            check("catalog split: a tie aborts", True)

        filtered = dl / "filtered.csv"
        write(filtered, cat_h, act[:10])
        try:
            plan([filtered], ex, drop, "2026-01-02")
            check("row guard: a filtered export aborts", False)
        except Abort as e:
            check("row guard: a filtered export aborts", "row guard" in str(e))
        drift = dl / "drift.csv"
        write(drift, cat_h + ["New column"], [r + ["x"] for r in act])
        try:
            plan([drift], ex, drop, "2026-01-02")
            check("header guard: a moved column aborts", False)
        except Abort as e:
            check("header guard: a moved column aborts", "header differs" in str(e))

        junk = dl / "junk.csv"
        write(junk, ["Foo", "Bar"], [["1", "2"]])
        new_str = dl / "strains.csv"
        write(new_str, KINDS["strains"][2], [["B", "Indica", "B", "B"]] * 11)
        steps, notes = plan([new_act, new_ret, junk, new_str], ex, drop, "2026-01-02")
        dos = [s["do"] for s in steps]
        check("plan: an unknown file is skipped and named", any("junk.csv" in n for n in notes))
        check("plan: the unchanged retired export is already frozen, not frozen twice",
              any(s["do"] == "already-frozen" and Path(s["src"]).name == "export (2).csv" for s in steps))
        check("plan: the new active and strains files freeze under one letter-less set on a new date",
              sorted(Path(s["to"]).name for s in steps if s["do"] == "freeze") ==
              ["2026-01-02-catalog-active.csv", "2026-01-02-strains.csv"])
        check("plan: an old drop file with no frozen copy is frozen before it is retired",
              dos.index("freeze-old") < max(i for i, s in enumerate(steps) if s["do"] == "retire" and "Strains" in Path(s["src"]).name))
        check("plan: dry-run wrote nothing", not (ex / "2026-01-02-catalog-active.csv").exists())

        execute(steps, recycler=lambda p: shutil.move(str(p), str(bin_ / Path(p).name)))
        check("apply: frozen copies are byte-identical", sha256(ex / "2026-01-02-catalog-active.csv") == sha256(new_act))
        check("apply: the set is placed under the drop names",
              (drop / "2026-01-02-Catalog - Active.csv").exists() and (drop / "2026-01-02-Strains.csv").exists()
              and (drop / "2026-01-02-Catalog - Retired.csv").exists())
        check("apply: previous versions left the drop folder for the bin",
              not (drop / "2026-01-01-Catalog - Active.csv").exists() and (bin_ / "2025-12-30-Strains.csv").exists())
        check("apply: every retired file has a byte-identical frozen copy",
              all(any(sha256(f) == sha256(b) for f in ex.glob("*.csv")) for b in bin_.glob("*.csv")))
        steps2, _ = plan([new_act, new_ret, new_str], ex, drop, "2026-01-02")
        check("idempotent: a second run plans no write",
              all(s["do"] in ("already-frozen", "already-placed") for s in steps2))
        again = dl / "again.csv"
        write(again, cat_h, act + [["6000", "s", "1", "newer", "Yes", "Q"]])
        steps3, _ = plan([again], ex, drop, "2026-01-02")
        check("same-day re-pull takes the next letter",
              [Path(s["to"]).name for s in steps3 if s["do"] == "freeze"] == ["2026-01-02a-catalog-active.csv"])
        try:
            execute([{"do": "freeze", "src": new_act, "to": ex / "2026-01-02-catalog-active.csv"}])
            check("never overwrite: an existing target aborts", False)
        except Abort:
            check("never overwrite: an existing target aborts", True)
    print(f"\n{'PASS' if not fails else 'FAIL'} — {len(ran) - len(fails)}/{len(ran)}.")
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*")
    ap.add_argument("--exports-dir")
    ap.add_argument("--drop-dir")
    ap.add_argument("--src", help="download dir to scan when no files are given")
    ap.add_argument("--since-minutes", type=int, default=120)
    ap.add_argument("--date", default=dt.date.today().isoformat())
    ap.add_argument("--active", help="state which file is the ACTIVE catalog export")
    ap.add_argument("--retired", help="state which file is the RETIRED catalog export")
    ap.add_argument("--no-retire", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.exports_dir:
        ap.error("--exports-dir is required")
    files = [Path(f) for f in a.files]
    if not files and a.src:
        cutoff = dt.datetime.now().timestamp() - a.since_minutes * 60
        files = sorted(f for f in Path(a.src).glob("*.csv") if f.stat().st_mtime >= cutoff)
    if not files:
        print("no input files")
        return 1
    forced = {}
    if a.active:
        forced[str(Path(a.active))] = "active"
    if a.retired:
        forced[str(Path(a.retired))] = "retired"
    try:
        steps, notes = plan(files, a.exports_dir, a.drop_dir, a.date, forced=forced, retire=not a.no_retire)
        print(("APPLY" if a.apply else "DRY RUN (nothing written; pass --apply)") + f" — set {a.date}")
        show(steps, notes)
        if a.apply:
            execute(steps)
            print("done.")
    except Abort as e:
        print("ABORT: " + str(e))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
