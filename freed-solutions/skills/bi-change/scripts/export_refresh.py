#!/usr/bin/env python3
"""Export refresh: the FILE half of a Backoffice export pull.

A lane pulls the exports in the browser (the platform KB holds the pull recipe); the files land in a
download folder under whatever name the platform gave them. This tool does everything after that:

  1. CLASSIFY each file by its CSV header (never by its name). An unknown header is skipped and printed in full.
     A kind may carry header ALIASES (a platform rename of a column): classification and the header guard compare
     the CANONICAL header, the frozen file keeps the header AS PULLED, and MANIFEST.json records the variant.
  2. SPLIT the two catalog exports (same header) by ProductId overlap with the newest frozen active and
     retired files. A tie or a weak match ABORTS; pass --active / --retired to state it.
  3. GUARD: the header must equal the newest frozen file of that kind (alias-for-alias), and the row count must sit
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
import stat
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
# kind -> {canonical column: [aliases]}. A platform RENAME of a column, never a new column. Classification and the
# header guard read the canonical header, so the rename neither skips the file nor trips the guard; the frozen file
# is never rewritten (it keeps the header as pulled) and MANIFEST.json says which variant each frozen file carries.
# Readers resolve the column themselves (one normaliser per codebase). Platform KB [PROBE 2026-10-11]: the Strains
# export's first column is now `Name` (was `Strain name`); the other three columns are unchanged and decide the kind.
ALIASES = {
    "strains": {"Strain name": ["Name"]},
}
CATALOG = {"active": ("catalog-active", "Catalog - Active"), "retired": ("catalog-retired", "Catalog - Retired")}
DATED = re.compile(r"^(\d{4}-\d{2}-\d{2})([a-z]?)-(.+)\.csv$", re.I)
LATEST, MANIFEST = "latest", "MANIFEST.json"


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


def canonical(header, kind):
    """The header with each of the kind's aliases read as its canonical column. An alias is read only under its own
    kind, and the kind's OTHER identifying columns still decide: `Name` leading a Rooms export stays a Rooms column."""
    amap = {a: c for c, al in ALIASES.get(kind, {}).items() for a in al}
    return [amap.get(h, h) for h in header]


def variant(header, kind):
    """{canonical: as pulled} for every alias this header carries in place of its canonical column; {} = canonical."""
    return {c: a for c, al in ALIASES.get(kind, {}).items() for a in al if a in header and c not in header}


def classify(header):
    """Longest identifying prefix wins, so `Tag` (one column) cannot swallow a wider export."""
    best = None
    for kind, (_, _, sig) in KINDS.items():
        if canonical(header, kind)[:len(sig)] == sig and (kind != "tags" or len(header) == 1):
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


def all_slugs():
    return [v[0] for v in CATALOG.values()] + [v[0] for v in KINDS.values() if v[0]]


def kind_of_slug(slug):
    return next((k for k, v in KINDS.items() if v[0] == slug), "catalog")


def put_view(src, dst):
    """Copy CONTENT into a view file. A frozen file may be read-only; `copy2` would carry that bit onto the view and
    the NEXT refresh could not overwrite it (2026-10-01). So: clear the bit on an existing target, copy the bytes only,
    then keep the source's mtime so the view still shows when the export was pulled."""
    dst = Path(dst)
    if dst.exists():
        os.chmod(dst, stat.S_IWRITE | stat.S_IREAD)
    shutil.copyfile(src, dst)
    st = os.stat(src)
    os.utime(dst, (st.st_atime, st.st_mtime))


def write_latest(exports_dir, mirror_dir=None, apply=True):
    """The `latest/` VIEW: one fixed name per kind (`<slug>.csv`) holding the newest frozen file, plus a
    MANIFEST.json that says which frozen file each one is. A view, so it is the one place this tool
    overwrites; the frozen files stay the record. `mirror_dir` gets the same files (an off-machine copy).
    Returns the manifest dict."""
    kinds = {}
    for slug in all_slugs():
        f = newest_frozen(exports_dir, slug)
        if f:
            kinds[slug] = {"frozen": f.name, "rows": row_count(f), "sha256": sha256(f),
                           "pulled_at": dt.datetime.fromtimestamp(f.stat().st_mtime).isoformat(timespec="seconds"),
                           "header_variant": variant(read_header(f), kind_of_slug(slug))}
    manifest = {"generated_at": dt.datetime.now().isoformat(timespec="seconds"),
                "note": "latest/<slug>.csv is a copy of the frozen file named here; the frozen file is the record. "
                        "header_variant = {canonical column: the alias the frozen file carries}; {} = canonical",
                "kinds": kinds}
    if not apply:
        return manifest
    import json
    targets = [Path(exports_dir) / LATEST] + ([Path(mirror_dir)] if mirror_dir else [])
    for t in targets:
        t.mkdir(parents=True, exist_ok=True)
        for slug, k in kinds.items():
            dst = t / f"{slug}.csv"
            if not dst.exists() or sha256(dst) != k["sha256"]:
                put_view(Path(exports_dir) / k["frozen"], dst)
                if sha256(dst) != k["sha256"]:
                    raise Abort(f"latest copy is not byte-identical: {dst}")
        (t / MANIFEST).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


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
            notes.append(f"SKIPPED {p.name}: header not recognised: {header}")
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
            ph = read_header(prior)
            if canonical(ph, kind) != canonical(header, kind):
                raise Abort(f"{p.name}: header differs from the newest frozen {prior.name} — a column moved; stop and read it")
            if ph != header:
                notes.append(f"HEADER VARIANT {p.name}: {variant(header, kind) or 'canonical'} (newest frozen {prior.name}: "
                             f"{variant(ph, kind) or 'canonical'}); frozen AS PULLED, readers take either")
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
        st_w, _ = plan([filtered], ex, None, "2026-01-02", row_guard=(0.05, 2.0))
        check("row guard: a stated wider guard admits the same file", [s["do"] for s in st_w] == ["freeze"])
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

        import json
        mirror = td / "mirror"
        m = write_latest(ex, mirror)
        lat = ex / LATEST
        check("latest: one fixed name per kind that has a frozen file",
              sorted(f.name for f in lat.glob("*.csv")) == ["catalog-active.csv", "catalog-retired.csv", "strains.csv"])
        check("latest: each file is byte-identical to the frozen file the manifest names",
              all(sha256(lat / f"{s}.csv") == sha256(ex / k["frozen"]) == k["sha256"] for s, k in m["kinds"].items()))
        check("latest: the manifest names the NEWEST frozen file by date and letter",
              m["kinds"]["catalog-active"]["frozen"] == "2026-01-02-catalog-active.csv"
              and json.loads((lat / MANIFEST).read_text(encoding="utf-8"))["kinds"]["strains"]["frozen"] == "2026-01-02-strains.csv")
        check("mirror: the off-machine folder holds the same files and manifest",
              sorted(f.name for f in mirror.iterdir()) == sorted(f.name for f in lat.iterdir())
              and all(sha256(mirror / f.name) == sha256(f) for f in lat.glob("*.csv")))
        execute(steps3)
        write_latest(ex, mirror)
        check("latest: a newer freeze replaces the view (the view is the one place that overwrites)",
              sha256(lat / "catalog-active.csv") == sha256(again) == sha256(mirror / "catalog-active.csv")
              and (ex / "2026-01-02-catalog-active.csv").exists())
        ro = ex / "2026-01-03-strains.csv"
        write(ro, KINDS["strains"][2], [["C", "Sativa", "C", "C"]] * 12)
        os.chmod(ro, stat.S_IREAD)
        write_latest(ex, mirror)
        newer = ex / "2026-01-04-strains.csv"
        write(newer, KINDS["strains"][2], [["D", "Hybrid", "D", "D"]] * 13)
        try:
            write_latest(ex, mirror)
            ok_ro = sha256(lat / "strains.csv") == sha256(newer) == sha256(mirror / "strains.csv") and os.access(lat / "strains.csv", os.W_OK)
        except PermissionError:
            ok_ro = False
        os.chmod(ro, stat.S_IWRITE | stat.S_IREAD)
        check("latest: a READ-ONLY frozen file does not make the view read-only (the next refresh overwrites)", ok_ro)
        check("latest: the view never feeds back into the freeze history",
              newest_frozen(ex, "catalog-active").name == "2026-01-02a-catalog-active.csv"
              and not any(DATED.match(f.name) for f in lat.glob("*.csv")))

        # Header ALIASES (2026-10-11): the platform renamed the Strains export's first column `Strain name` -> `Name`.
        renamed = ["Name"] + KINDS["strains"][2][1:]
        check("alias: the renamed Strains header classifies as strains", classify(renamed) == "strains")
        check("alias: a `Name`-led Rooms header is still rooms, not strains (the other columns decide)",
              classify(KINDS["rooms"][2]) == "rooms" and classify(["Name", "Kind", "Abbreviation", "Description"]) is None)
        check("alias: the variant names the alias; a canonical header has none",
              variant(renamed, "strains") == {"Strain name": "Name"} and variant(KINDS["strains"][2], "strains") == {})
        new_name = dl / "strains-renamed.csv"
        write(new_name, renamed, [["E", "Hybrid", "E", "E"]] * 14)
        st_a, notes_a = plan([new_name], ex, None, "2026-01-05")
        check("alias: the renamed file passes the header guard against a canonical frozen file and freezes",
              [Path(s["to"]).name for s in st_a if s["do"] == "freeze"] == ["2026-01-05-strains.csv"])
        check("alias: the plan names the header variant it froze",
              any(n.startswith("HEADER VARIANT strains-renamed.csv") and "'Name'" in n for n in notes_a))
        execute(st_a)
        check("alias: the frozen file keeps the header AS PULLED (byte-identical, never rewritten)",
              (ex / "2026-01-05-strains.csv").exists() and sha256(ex / "2026-01-05-strains.csv") == sha256(new_name)
              and read_header(ex / "2026-01-05-strains.csv") == renamed)
        m2 = write_latest(ex, mirror)
        check("alias: MANIFEST.json records the variant each frozen file carries",
              m2["kinds"]["strains"]["header_variant"] == {"Strain name": "Name"}
              and m2["kinds"]["catalog-active"]["header_variant"] == {}
              and json.loads((lat / MANIFEST).read_text(encoding="utf-8"))["kinds"]["strains"]["header_variant"]
              == {"Strain name": "Name"})
        moved = dl / "strains-moved.csv"
        write(moved, ["Name", "Kind", "Abbreviation", "Description"], [["F", "Hybrid", "F", "F"]] * 14)
        st_m, notes_m = plan([moved], ex, None, "2026-01-06")
        check("alias: a header matching no kind is skipped with the FULL header it saw",
              not st_m and any("['Name', 'Kind', 'Abbreviation', 'Description']" in n for n in notes_m))
        back = dl / "strains-back.csv"
        write(back, KINDS["strains"][2], [["G", "Hybrid", "G", "G"]] * 14)
        st_b, notes_b = plan([back], ex, None, "2026-01-06")
        check("alias: a pull back on the canonical header after an aliased one also passes the guard",
              [s["do"] for s in st_b] == ["freeze"] and any("HEADER VARIANT" in n for n in notes_b))
        extra = dl / "strains-extra.csv"
        write(extra, renamed + ["Notes"], [["H", "Hybrid", "H", "H", ""]] * 14)
        try:
            plan([extra], ex, None, "2026-01-06")
            check("alias: a genuinely moved column on an aliased kind still aborts", False)
        except Abort as e:
            check("alias: a genuinely moved column on an aliased kind still aborts", "header differs" in str(e))
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
    ap.add_argument("--row-guard", default="0.5,2.0",
                    help="allowed row-count ratio vs the newest frozen file, LO,HI (default 0.5,2.0). Widen it only for a "
                         "KNOWN cause — a bulk archive, a purge — and say the cause in the run record")
    ap.add_argument("--mirror-dir", help="an off-machine folder that receives a copy of the latest/ view")
    ap.add_argument("--refresh-latest", action="store_true", help="rebuild latest/ (and the mirror) from the frozen files; no input files")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.exports_dir:
        ap.error("--exports-dir is required")
    if a.refresh_latest:
        m = write_latest(a.exports_dir, a.mirror_dir, apply=a.apply)
        print(("APPLY" if a.apply else "DRY RUN (nothing written; pass --apply)") + " — latest view")
        for slug, k in m["kinds"].items():
            print(f"  latest/{slug}.csv  <-  {k['frozen']}  ({k['rows']} rows, pulled {k['pulled_at']})")
        return 0
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
        lo, hi = (float(x) for x in a.row_guard.split(","))
        steps, notes = plan(files, a.exports_dir, a.drop_dir, a.date, row_guard=(lo, hi), forced=forced,
                            retire=not a.no_retire)
        print(("APPLY" if a.apply else "DRY RUN (nothing written; pass --apply)") + f" — set {a.date}")
        show(steps, notes)
        if a.apply:
            execute(steps)
            m = write_latest(a.exports_dir, a.mirror_dir)
            print(f"  latest/ view refreshed: {len(m['kinds'])} kind(s)" + (f"; mirrored to {a.mirror_dir}" if a.mirror_dir else ""))
            print("done.")
        else:
            print("  latest/ view would be refreshed" + (f" and mirrored to {a.mirror_dir}" if a.mirror_dir else ""))
    except Abort as e:
        print("ABORT: " + str(e))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
