#!/usr/bin/env python3
"""render_pdf.py - print an HTML file to PDF with headless Edge (or Chrome) and enforce a page budget.

Usage:
  python render_pdf.py <in.html> <out.pdf> [--pages N] [--browser PATH] [--timeout SEC]

Prints the page count (and the budget, if given). Exit codes:
  0  rendered, within budget (or no budget given)
  1  rendered, but the page count exceeds --pages
  2  render failed: no browser found, browser error, or no PDF written

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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Print HTML to PDF with headless Edge/Chrome and check a page budget.")
    ap.add_argument("html", help="input .html file")
    ap.add_argument("pdf", help="output .pdf path")
    ap.add_argument("--pages", type=int, default=None, help="page budget; exit 1 if the render exceeds it")
    ap.add_argument("--browser", default=None, help="path to msedge.exe / chrome.exe")
    ap.add_argument("--timeout", type=float, default=120.0, help="seconds to wait for the browser (default 120)")
    args = ap.parse_args(argv)

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
    return 0


if __name__ == "__main__":
    sys.exit(main())
