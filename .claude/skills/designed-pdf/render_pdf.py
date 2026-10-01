#!/usr/bin/env python3
"""render_pdf.py - print an HTML file to PDF with headless Edge (or Chrome) and enforce a page budget.

Usage:
  python render_pdf.py <in.html> <out.pdf> [--pages N] [--min-scale S] [--browser PATH] [--timeout SEC]
  python render_pdf.py --selftest

Prints the page count (and the budget, if given) and the PRINT SCALE of every page. Exit codes:
  0  rendered, within budget (or no budget given), printed at full scale
  1  rendered, but the page count exceeds --pages
  2  render failed: no browser found, browser error, or no PDF written
  3  rendered, but a page printed below --min-scale (default 1.0): the browser shrank it

Why the scale check: when any element is wider than the page box (a nowrap chip or pill, a long
unbreakable string), headless Chromium SHRINKS THE WHOLE PAGE to fit instead of overflowing. The
page count still passes, the page still looks tidy, and every font is quietly smaller: a 8.4pt body
can print near 7.4pt. Nothing else in the render can see it.
How it is measured: a second print of a temporary copy of the HTML carries a position:fixed probe
exactly 1in wide; Chromium repeats a fixed element on every printed page and scales it with the
page, so each probe's printed width / 72pt is that page's scale. The probe copy is deleted and the
probe never reaches <out.pdf>. Needs PyMuPDF (`fitz`); without it the scale is reported as not
measured, loudly, and does not fail the render.

The browser runs with a throwaway profile in a temp dir, so a running Edge window never
interferes. Override the browser with --browser or the DESIGNED_PDF_BROWSER env var.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.request import pathname2url

CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def find_browser(explicit: str | None) -> str | None:
    """First existing browser: --browser, then $DESIGNED_PDF_BROWSER, then the known install paths, then PATH."""
    for c in [explicit, os.environ.get("DESIGNED_PDF_BROWSER")] + CANDIDATES:
        if c and Path(c).is_file():
            return str(Path(c))
    for name in ("msedge", "chrome", "google-chrome", "chromium"):
        found = shutil.which(name)
        if found:
            return found
    return None


def file_uri(path: Path) -> str:
    # pathname2url on Windows yields ///C:/dir/file.html; on POSIX /dir/file.html.
    url = pathname2url(str(path.resolve()))
    return "file:" + url if url.startswith("///") else "file://" + url


def page_count(pdf: Path) -> int:
    try:
        from pypdf import PdfReader  # type: ignore
        return len(PdfReader(str(pdf)).pages)
    except ImportError:
        data = pdf.read_bytes()
        return len(re.findall(rb"/Type\s*/Page(?![a-zA-Z])", data))


def render(html: Path, out: Path, browser: str, timeout: float) -> None:
    profile = Path(tempfile.mkdtemp(prefix="designed-pdf-"))
    try:
        cmd = [
            browser,
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            f"--user-data-dir={profile}",
            "--no-pdf-header-footer",
            f"--print-to-pdf={out}",
            file_uri(html),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        # Chromium logs harmless noise on stderr; only surface it when the PDF did not appear.
        deadline = time.time() + 5
        while time.time() < deadline and not (out.is_file() and out.stat().st_size > 0):
            time.sleep(0.2)
        if not (out.is_file() and out.stat().st_size > 0):
            tail = "\n".join((proc.stderr or "").strip().splitlines()[-8:])
            raise RuntimeError(f"browser exited {proc.returncode} and wrote no PDF\n{tail}")
    finally:
        for _ in range(5):  # the browser may hold the profile lock for a moment
            try:
                shutil.rmtree(profile)
                break
            except OSError:
                time.sleep(0.4)


PROBE_ATTR = "data-designed-pdf-scale-probe"
PROBE_RGB = (1.0, 0.0, 1.0)   # the probe copy only; never printed into the deliverable
PROBE = (f'<div {PROBE_ATTR} style="position:fixed;left:0;top:0;width:1in;height:0.1in;margin:0;padding:0;border:0;'
         'background:#ff00ff;-webkit-print-color-adjust:exact;print-color-adjust:exact;z-index:2147483647"></div>')
SCALE_TOL = 0.002   # Chromium rounds layout to device pixels; a true 1.000 can read 0.999


def probe_copy(html: Path) -> Path:
    """A temporary copy beside the original (so relative assets still resolve) with the probe as the FIRST child of
    <body>: placed last, it can open a trailing page of its own, and the probe copy must paginate as the original does."""
    text = html.read_text(encoding="utf-8")
    m = re.search(r"<body\b[^>]*>", text, re.I)
    text = text[:m.end()] + PROBE + text[m.end():] if m else PROBE + text
    fd, name = tempfile.mkstemp(prefix=f".{html.stem}.scale-probe-", suffix=".html", dir=str(html.parent))
    os.close(fd)
    p = Path(name)
    p.write_text(text, encoding="utf-8")
    return p


def probe_scales(pdf: Path) -> list[float] | None:
    """Per page: the printed width of the 1in probe / 72pt. None when PyMuPDF is missing or a page has no probe."""
    try:
        import fitz  # type: ignore  # PyMuPDF
    except ImportError:
        return None
    scales = []
    with fitz.open(str(pdf)) as doc:
        for page in doc:
            widths = [d["rect"].width for d in page.get_drawings()
                      if d.get("fill") and all(abs(a - b) < 0.02 for a, b in zip(d["fill"], PROBE_RGB))]
            if not widths:
                return None
            scales.append(max(widths) / 72.0)
    return scales


def measure_scale(html: Path, browser: str, timeout: float) -> list[float] | None:
    probe = probe_copy(html)
    out = probe.with_suffix(".pdf")
    try:
        render(probe, out.resolve(), browser, timeout)
        return probe_scales(out)
    finally:
        for f in (probe, out):
            try:
                f.unlink()
            except OSError:
                pass


def selftest(browser: str, timeout: float) -> int:
    """A page with an over-wide nowrap element must read under 1.0 and exit 3; its wrapped twin must read 1.0 and exit 0;
    the deliverable must carry no probe. Exit 1 on any failed assertion."""
    body = ("<p style='font:10pt sans-serif'>{}</p>")
    words = " ".join(["overwide"] * 60)
    fixtures = {
        "nowrap": f"<!doctype html><html><head><meta charset='utf-8'><style>@page{{size:Letter;margin:0.5in}}</style></head><body>"
                  f"{body.format(f'<span style=white-space:nowrap>{words}</span>')}</body></html>",
        "wrap": f"<!doctype html><html><head><meta charset='utf-8'><style>@page{{size:Letter;margin:0.5in}}</style></head><body>"
                f"{body.format(words)}</body></html>",
        "long": f"<!doctype html><html><head><meta charset='utf-8'><style>@page{{size:Letter;margin:0.5in}}</style></head><body>"
                + body.format(words) * 40 + "</body></html>",
    }
    tmp = Path(tempfile.mkdtemp(prefix="designed-pdf-selftest-"))
    bad = 0
    try:
        got = {}
        for name, src in fixtures.items():
            h = tmp / f"{name}.html"; h.write_text(src, encoding="utf-8")
            rc = main([str(h), str(tmp / f"{name}.pdf"), "--browser", browser, "--timeout", str(timeout)])
            got[name] = (rc, measure_scale(h, browser, timeout), probe_scales(tmp / f"{name}.pdf"))
        checks = [
            ("the over-wide nowrap page reads under 1.0", got["nowrap"][1] is not None and min(got["nowrap"][1]) < 1.0 - SCALE_TOL),
            ("...and exits 3", got["nowrap"][0] == 3),
            ("the wrapped twin reads 1.0", got["wrap"][1] is not None and min(got["wrap"][1]) >= 1.0 - SCALE_TOL),
            ("...and exits 0", got["wrap"][0] == 0),
            ("no probe reaches a deliverable PDF", all(got[k][2] is None for k in got)),
            ("a multi-page page: one probe per page, every page 1.0, exit 0",
             got["long"][0] == 0 and got["long"][1] is not None and page_count(tmp / "long.pdf") >= 2
             and len(got["long"][1]) == page_count(tmp / "long.pdf") and min(got["long"][1]) >= 1.0 - SCALE_TOL),
            ("a one-page page probes as one page", got["wrap"][1] is not None and len(got["wrap"][1]) == page_count(tmp / "wrap.pdf") == 1),
            ("--min-scale admits a stated lower bound", main([str(tmp / "nowrap.html"), str(tmp / "nowrap2.pdf"), "--browser", browser,
                                                             "--min-scale", f"{max(0.01, min(got['nowrap'][1]) - 0.05):.3f}"]) == 0),
        ]
        for label, ok in checks:
            print(("  ok    " if ok else "  FAIL  ") + label)
            bad += not ok
        print(f"selftest: {len(checks) - bad}/{len(checks)} passed" + ("" if not bad else f", {bad} FAILED"))
        return 1 if bad else 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Print HTML to PDF with headless Edge/Chrome; check the page budget and the print scale.")
    ap.add_argument("html", nargs="?", help="input .html file")
    ap.add_argument("pdf", nargs="?", help="output .pdf path")
    ap.add_argument("--pages", type=int, default=None, help="page budget; exit 1 if the render exceeds it")
    ap.add_argument("--min-scale", type=float, default=1.0,
                    help="lowest print scale allowed, default 1.0 (no shrink); exit 3 below it. Lower it only on purpose.")
    ap.add_argument("--browser", default=None, help="path to msedge.exe / chrome.exe")
    ap.add_argument("--timeout", type=float, default=120.0, help="seconds to wait for the browser (default 120)")
    ap.add_argument("--selftest", action="store_true", help="prove the scale check fails a shrunk page and passes its twin")
    args = ap.parse_args(argv)
    if args.selftest:
        browser = find_browser(args.browser)
        if not browser:
            print("ERROR: selftest needs a headless browser", file=sys.stderr)
            return 2
        return selftest(browser, args.timeout)
    if not (args.html and args.pdf):
        ap.error("html and pdf are required unless --selftest")

    html = Path(args.html)
    out = Path(args.pdf)
    if not html.is_file():
        print(f"ERROR: HTML not found: {html}", file=sys.stderr)
        return 2
    browser = find_browser(args.browser)
    if not browser:
        print("ERROR: no headless browser found. Install Edge or Chrome, or pass --browser / set DESIGNED_PDF_BROWSER.",
              file=sys.stderr)
        return 2

    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()  # never let a stale file pass as a fresh render
    try:
        render(html, out.resolve(), browser, args.timeout)
    except (RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"ERROR: render failed: {exc}", file=sys.stderr)
        return 2

    n = page_count(out)
    size = out.stat().st_size
    budget = f" (budget {args.pages})" if args.pages is not None else ""
    print(f"pages: {n}{budget}  size: {size:,} bytes  out: {out}")
    if args.pages is not None and n > args.pages:
        print(f"FAIL: {n} pages exceeds the budget of {args.pages}. Tighten spacing before cutting content.",
              file=sys.stderr)
        return 1
    try:
        scales = measure_scale(html, browser, args.timeout)
    except (RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"ERROR: scale probe render failed: {exc}", file=sys.stderr)
        return 2
    if scales is None:
        print("WARNING: print scale NOT MEASURED (PyMuPDF missing, or the probe did not print). "
              "A shrunk page would pass unseen: install pymupdf.", file=sys.stderr)
        return 0
    if len(scales) != n:
        print(f"ERROR: the scale probe copy printed {len(scales)} pages, the page {n}: the measure is not of this page", file=sys.stderr)
        return 2
    print("scale: " + " ".join(f"p{i}={s:.3f}" for i, s in enumerate(scales, 1)) + f"  (min {args.min_scale:.3f})")
    low = [(i, s) for i, s in enumerate(scales, 1) if s < args.min_scale - SCALE_TOL]
    if low:
        print(f"FAIL: {html} printed below scale {args.min_scale:.3f}: " + ", ".join(f"page {i} at {s:.3f}" for i, s in low)
              + ". An element is wider than the page box (a nowrap chip or pill, an unbreakable string): let it wrap or narrow it.",
              file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
