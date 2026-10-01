#!/usr/bin/env python3
"""Publish docs: keep ONE folder a person reads from equal to the estate's current canonical documents.

The estate registers its business-facing documents in `<estate>/onepagers.json` (a designed PDF from a generator,
one current version each) and renders its technical documents into `<estate>/renders/`. This tool copies the CURRENT
set into an output folder and keeps that folder clean. It never runs a generator and never edits the estate.

  1. STATUS: run `bi_impact_scan.js --stale` and read each registered document's line. A document the scan calls
     BEHIND is HELD, with the scan's reasons.
  2. RETIRED WORDS: `onepagers.json` may carry `"retired_words": ["<word>", ...]` - a word canon no longer uses.
     A document whose HTML source (same base name as the delivered PDF) prints one is HELD. The rule-seal cannot see
     this: a page can print a category or tag NAME that no rule cell it cites spells out.
  3. PUBLISH each in-step document as `<out>/<delivered file name>`, only when the bytes differ.
  4. SUPERSEDE: another version of a published title in <out> (`<Title> - v<n>.pdf`) goes to the Recycle Bin, and
     only when a byte-identical copy exists under the tenant's `deliverables/`. Nothing is hard-deleted. A HELD
     title is not touched: its last published version stays, and the index says it is behind.
  5. REFERENCE (--reference): the technical renders (`<estate>/renders/*.pdf`) go to `<out>/Reference/`, and only
     when the scan reports no stale stamp, no render behind and no dictionary-ahead document.
  6. INDEX: `<out>/_Index.txt` (what is here, what is held and why) and `<out>/MANIFEST.json`.

A file in <out> this tool did not place and cannot match to a registered title is left alone and named.
Dry-run by default: it prints the plan and writes nothing. `--apply` executes it.

  python publish_docs.py --estate <estate dir> --out <dir> [--reference] [--apply]
  python publish_docs.py --selftest
"""
import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from export_refresh import Abort, put_view, recycle, sha256  # noqa: E402  (one copy of each, in the family)

HERE = Path(os.path.abspath(__file__)).parent
VERSIONED = re.compile(r"^(?P<base>.+) - v(?P<n>\d+)\.pdf$", re.I)
OK_LINE = re.compile(r"^ok\s+(\S+) \"")
BEHIND_LINE = re.compile(r"^\*\* ONE-PAGER BEHIND \*\* (\S+) \".*?\" \(delivered [^)]*\) — (.*?) -> regenerate")
COUNTS = re.compile(r"(\d+) stale stamp\(s\), (\d+) render\(s\) behind, (\d+) dictionary-ahead")
OWN = {"_Index.txt", "MANIFEST.json"}


def scan_status(estate):
    """({key: [] | [reasons]}, reference_ok, why_not) from `bi_impact_scan.js --stale`."""
    r = subprocess.run(["node", str(HERE / "bi_impact_scan.js"), "--estate", str(estate), "--stale"],
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode not in (0, 1) or "Canonical one-pagers" not in r.stdout:
        raise Abort("bi_impact_scan --stale did not run: " + (r.stderr or r.stdout).strip()[:300])
    status, ref_ok, why = {}, False, "the scan printed no summary line"
    for line in r.stdout.splitlines():
        m = OK_LINE.match(line)
        if m:
            status[m.group(1)] = []
        m = BEHIND_LINE.match(line)
        if m:
            status[m.group(1)] = [m.group(2)]
        if line.startswith("All documents current"):
            ref_ok, why = True, ""
        m = COUNTS.search(line)
        if m:
            s, rb, a = (int(x) for x in m.groups())
            ref_ok = (s, rb, a) == (0, 0, 0)
            why = "" if ref_ok else f"{s} stale stamp(s), {rb} render(s) behind, {a} dictionary-ahead"
    return status, ref_ok, why


def retired_hits(html, words):
    if not html.exists() or not words:
        return []
    text = html.read_text(encoding="utf-8", errors="replace")
    out = []
    for w in words:
        n = len(re.findall(r"(?<![A-Za-z])" + re.escape(w) + r"(?![A-Za-z])", text))
        if n:
            out.append(f"prints the retired word `{w}` ×{n}")
    return out


def plan(estate, out, reference=False, status_fn=scan_status):
    estate, out = Path(estate), Path(out)
    tenant = estate.parent
    reg_path = estate / "onepagers.json"
    if not reg_path.exists():
        raise Abort(f"no onepagers.json in {estate}")
    reg = json.loads(reg_path.read_text(encoding="utf-8"))
    status, ref_ok, ref_why = status_fn(estate)
    words = reg.get("retired_words", [])
    steps, notes, index = [], [], {"published": [], "held": [], "reference": [], "unmanaged": []}
    frozen = None
    current_names, titles = set(), {}

    for d in reg.get("docs", []):
        key, rel = d.get("key"), d.get("delivered") or ""
        src = tenant / rel
        reasons = []
        if key not in status:
            reasons.append("the stale scan printed no line for this key")
        else:
            reasons += status[key]
        if not rel or not src.exists():
            reasons.append(f"delivered file missing: {rel or '(none)'}")
        else:
            reasons += retired_hits(src.with_suffix(".html"), words)
        m = VERSIONED.match(Path(rel).name) if rel else None
        if m:
            titles[m.group("base").lower()] = key
        if reasons:
            index["held"].append({"key": key, "title": d.get("title"), "file": Path(rel).name, "why": reasons})
            continue
        current_names.add(src.name.lower())
        dst = out / src.name
        entry = {"key": key, "title": d.get("title"), "file": src.name, "delivered_on": d.get("delivered_on"),
                 "rules": d.get("rules", []), "sha256": sha256(src)}
        index["published"].append(entry)
        if not dst.exists() or sha256(dst) != entry["sha256"]:
            steps.append(("copy", src, dst))

    held_titles = {VERSIONED.match(h["file"]).group("base").lower() for h in index["held"] if VERSIONED.match(h["file"])}
    if out.exists():
        for f in sorted(out.iterdir()):
            if not f.is_file() or f.name in OWN or f.name.lower() in current_names:
                continue
            m = VERSIONED.match(f.name)
            base = m.group("base").lower() if m else None
            if base in held_titles:
                notes.append(f"kept (its title is HELD, so the last published version stays): {f.name}")
            elif base in titles:
                if frozen is None:
                    frozen = {sha256(p) for p in (tenant / "deliverables").glob("*.pdf")}
                if sha256(f) in frozen:
                    steps.append(("retire", f, None))
                else:
                    notes.append(f"kept (superseded, but no byte-identical copy under deliverables/): {f.name}")
            else:
                index["unmanaged"].append(f.name)

    if reference:
        if not ref_ok:
            notes.append(f"Reference/ HELD: {ref_why}")
        else:
            for src in sorted((estate / "renders").glob("*.pdf")):
                dst = out / "Reference" / src.name
                digest = sha256(src)
                index["reference"].append({"file": src.name, "sha256": digest})
                if not dst.exists() or sha256(dst) != digest:
                    steps.append(("copy", src, dst))
    for u in index["unmanaged"]:
        notes.append(f"left alone (not a registered title): {u}")
    return steps, notes, index


def index_text(index, today):
    lines = [f"Current documents - refreshed {today}", ""]
    for e in index["published"]:
        lines.append(f"  {e['file']}   (delivered {e['delivered_on']}; rules {', '.join(e['rules'])})")
    if index["held"]:
        lines += ["", "HELD - a new version is owed before this title is current:"]
        for h in index["held"]:
            lines.append(f"  {h['file'] or h['title']}: " + "; ".join(h["why"]))
    if index["reference"]:
        lines += ["", "Reference/ - the technical documents:"]
        lines += [f"  {r['file']}" for r in index["reference"]]
    return "\n".join(lines) + "\n"


def execute(steps, index, out, today, recycler=recycle):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for kind, a, b in steps:
        if kind == "copy":
            b.parent.mkdir(parents=True, exist_ok=True)
            put_view(a, b)
            if sha256(a) != sha256(b):
                raise Abort(f"copy verify failed: {b}")
        elif kind == "retire":
            recycler(a)
    (out / "_Index.txt").write_text(index_text(index, today), encoding="utf-8")
    (out / "MANIFEST.json").write_text(json.dumps({"generated": today, **index}, indent=1), encoding="utf-8")


def show(steps, notes, index):
    print(f"published set: {len(index['published'])} document(s); held: {len(index['held'])}; "
          f"reference: {len(index['reference'])} file(s)")
    for h in index["held"]:
        print(f"  HELD    {h['key']}: " + "; ".join(h["why"]))
    for kind, a, b in steps:
        print(f"  {kind:7s} {a.name}" + (f"  ->  {b}" if b else "  (to the Recycle Bin)"))
    if not steps:
        print("  nothing to copy or retire: the folder already holds the current set")
    for n in notes:
        print("  note:   " + n)


def selftest():
    fails, ran = [], []

    def check(name, cond):
        print(("  PASS  " if cond else "  FAIL  ") + name)
        ran.append(name)
        if not cond:
            fails.append(name)

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        est, dl, out, bin_ = td / "t" / "estate", td / "t" / "deliverables", td / "out", td / "bin"
        for d in (est / "renders", dl, out, bin_):
            d.mkdir(parents=True)

        def pdf(p, body):
            p.write_bytes(b"%PDF " + body.encode())

        for name, body in (("Alpha - v1.pdf", "a1"), ("Alpha - v2.pdf", "a2"), ("Beta - v3.pdf", "b3"),
                           ("Gamma - v1.pdf", "g1"), ("Delta - v2.pdf", "d2")):
            pdf(dl / name, body)
        (dl / "Gamma - v1.html").write_text("<p>The Oldword list. Oldwords is another word.</p>", encoding="utf-8")
        (dl / "Alpha - v2.html").write_text("<p>Nothing retired here: Oldwords only.</p>", encoding="utf-8")
        pdf(est / "renders" / "MANUAL.pdf", "m")
        docs = [{"key": k, "title": k.title(), "delivered": f"deliverables/{f}", "delivered_on": "2026-01-01", "rules": ["R1"]}
                for k, f in (("alpha", "Alpha - v2.pdf"), ("beta", "Beta - v3.pdf"), ("gamma", "Gamma - v1.pdf"),
                             ("delta", "Delta - v2.pdf"), ("gone", "Gone - v1.pdf"))]
        (est / "onepagers.json").write_text(json.dumps({"retired_words": ["Oldword"], "docs": docs}), encoding="utf-8")
        pdf(out / "Alpha - v1.pdf", "a1")           # superseded, frozen copy exists
        pdf(out / "Beta - v2.pdf", "b2-not-frozen")  # superseded, NO frozen copy
        pdf(out / "Delta - v1.pdf", "d1")           # its title is held
        pdf(out / "My own notes.pdf", "x")          # unmanaged

        def st(ref_ok):
            return lambda e: ({"alpha": [], "beta": [], "gamma": [], "delta": ["R9 text moved since the seal"], "gone": []},
                              ref_ok, "" if ref_ok else "0 stale stamp(s), 1 render(s) behind, 0 dictionary-ahead")

        steps, notes, index = plan(est, out, reference=True, status_fn=st(False))
        pub = {e["key"] for e in index["published"]}
        held = {h["key"]: " ".join(h["why"]) for h in index["held"]}
        check("in-step documents are published", pub == {"alpha", "beta"})
        check("a document the scan calls behind is held with the scan's reason", "text moved" in held.get("delta", ""))
        check("a document that prints a retired word is held", "Oldword" in held.get("gamma", ""))
        check("the retired-word test is whole-word (a longer word does not hold a page)", "alpha" in pub)
        check("a missing delivered file is held", "missing" in held.get("gone", ""))
        check("a superseded version with a frozen copy is retired", ("retire", out / "Alpha - v1.pdf", None) in steps)
        check("a superseded version with no frozen copy is kept and named",
              not any(k == "retire" and a.name == "Beta - v2.pdf" for k, a, _ in steps) and any("Beta - v2.pdf" in n for n in notes))
        check("a held title's last published version stays",
              not any(a.name == "Delta - v1.pdf" for _, a, _ in steps) and any("Delta - v1.pdf" in n for n in notes))
        check("a file that is not a registered title is left alone", index["unmanaged"] == ["My own notes.pdf"])
        check("Reference is held when the scan reports a render behind",
              not index["reference"] and any("Reference/ HELD" in n for n in notes))

        gone = []
        execute(steps, index, out, "2026-01-02", recycler=lambda p: (gone.append(p.name), p.rename(bin_ / p.name)))
        check("apply: current versions land byte-identical",
              sha256(out / "Alpha - v2.pdf") == sha256(dl / "Alpha - v2.pdf") and (out / "Beta - v3.pdf").exists())
        check("apply: only the frozen superseded version went to the bin", gone == ["Alpha - v1.pdf"])
        check("apply: the index names the held titles", "HELD" in (out / "_Index.txt").read_text(encoding="utf-8")
              and json.loads((out / "MANIFEST.json").read_text(encoding="utf-8"))["held"][0]["key"] in held)

        steps2, _, index2 = plan(est, out, reference=True, status_fn=st(True))
        check("second run: no document step, Reference now publishes",
              [(k, a.name) for k, a, _ in steps2] == [("copy", "MANUAL.pdf")] and len(index2["reference"]) == 1)
        execute(steps2, index2, out, "2026-01-02", recycler=lambda p: None)
        steps3, _, _ = plan(est, out, reference=True, status_fn=st(True))
        check("third run: nothing to do (idempotent)", steps3 == [])
        os.chmod(dl / "Alpha - v2.pdf", 0o444)
        pdf(out / "Alpha - v2.pdf", "tampered")
        steps4, _, index4 = plan(est, out, status_fn=st(True))
        execute(steps4, index4, out, "2026-01-03", recycler=lambda p: None)
        check("a changed copy in the folder is restored, and a read-only source does not lock the copy",
              sha256(out / "Alpha - v2.pdf") == sha256(dl / "Alpha - v2.pdf") and os.access(out / "Alpha - v2.pdf", os.W_OK))
        os.chmod(dl / "Alpha - v2.pdf", 0o666)

    print(f"\n{len(ran) - len(fails)} / {len(ran)} passed")
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--estate")
    ap.add_argument("--out")
    ap.add_argument("--reference", action="store_true", help="also publish the technical renders into <out>/Reference/")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.estate or not a.out:
        ap.error("--estate and --out are required")
    try:
        steps, notes, index = plan(a.estate, a.out, reference=a.reference)
        show(steps, notes, index)
        if a.apply:
            execute(steps, index, a.out, dt.date.today().isoformat())
            print("applied.")
        else:
            print("dry run: nothing written. Add --apply.")
    except Abort as e:
        print("ABORT: " + str(e))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
