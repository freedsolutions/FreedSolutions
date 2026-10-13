"""intake_notice.py - fill the tenant's new-items notice from the intake CSV; print the floor-sheet
command when the CSV carries an approved, created new-line item (NEW_PL / NEW_BRAND).

  python intake_notice.py --intake <intake-vN.csv> --tenant <CLAUDE.md> [--out-dir <dir>]
  (without --tenant: --template <notice.md> --operator "<name>" [--floor-sheet "<command>"])
  options: --new-line-tag "<tag>"  the R83 tag the notice names (default `ITM - New PL`; tenant `New line tag:`)
  python intake_notice.py --selftest

Created items = an approved create row: verdict in CREATE_VERDICTS and approved = Y. Each prints ONCE,
by its final create name (`create_name_FINAL`), with the new SKU / ProductId only when the row carries
them (the write-back of those ids is a manual step; a blank id never drops the item). The notice is
a DRAFT: the Operator adds recipients and sends; this script sends nothing. The floor sheet is the
tenant's own generator (`Floor sheet:` pointer); `<intake.csv>` in that command is replaced by the
intake path and the command is PRINTED, never run.

The "New line:" paragraph names ONLY created new-line items (verdict NEW_PL / NEW_BRAND, approved = Y),
never an approved = N row and never an invoice line: an un-created row is not a new line for the business.

Images (ruled 2026-10-08): a created item with no image needs a hand unless the lane sourced one. The
`image_state` cell is the image fact (blank, `NO_ECOM_IMAGE`, `deleted ...` or a planned `REMOVE` = no
image; a carried image that is kept = an image). The `image_source` cell is the sourcing record:
  sourced: <url>  or a bare http(s) URL   the image was added from that page - the item is CLEARED
  not found: <where the lane looked>      the item fires and prints where the lane looked
  not attempted[: <why>]  or blank        the item fires and says sourcing was not attempted

Global link (ruled 2026-10-13: ALWAYS ATTEMPTED, a best guess the business QCs after). The `global_link_result`
cell is the plan's per-create result (intake_plan.link_result; step 7 writes it):
  linked: <id> | <name> - <why>          an exact name (or the Operator's pick) - nothing to ask
  best guess: <id> | <name> - <why>...   linked as a guess - the business is asked to confirm it
  no match: <why>[; nearest: <records>]  not linked - the business is asked whether a record is this product
  no record: <why> / none: <why>         nothing in the global catalog / the Operator ruled no link - nothing to ask
  blank                                  the attempt was not recorded - it fires

Flag table: NOT_READ_BACK  R101  DEFECT  an approved create row with no new_sku: a notice before the
read-back would announce an item nobody has seen (exit 1, nothing written).
"""
import os
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from intake_common import (CREATE_VERDICTS, DEFAULT_NEW_LINE_TAG, EXIT_ABORT, EXIT_DEFECT, EXIT_OK,  # noqa: E402
                           Selftest, abort,
                           get_flag, new_path, read_csv, stamp, version_stem)
from intake_match import V3_COLS  # noqa: E402

# The verdicts that are a new line for the business. NEW_CATEGORY is never created by this lane (R101),
# so it can never be an approved create and never reaches the paragraph.
NEW_LINE_VERDICTS = ("NEW_PL", "NEW_CATEGORY", "NEW_BRAND")
IMAGE_SOURCE_COL = "image_source"   # optional column: a v4 intake file reads as blank = not attempted
LINK_COL = "global_link_result"     # a v3 column; blank = the link attempt was not recorded


def is_created(r):
    return r.get("verdict") in CREATE_VERDICTS and (r.get("approved") or "").strip().upper() == "Y"


def has_image(r):
    """True only when `image_state` says an image is on the item (a carried image that is kept)."""
    s = (r.get("image_state") or "").strip()
    if not s or "NO_ECOM_IMAGE" in s or s.lower().startswith("deleted") or "REMOVE" in s:
        return False
    return "carried" in s.lower() or "image" in s.lower()


def image_source(r):
    """(kind, detail): kind in sourced / not_found / not_attempted."""
    s = (r.get(IMAGE_SOURCE_COL) or "").strip()
    low = s.lower()
    if low.startswith(("http://", "https://")):
        return "sourced", s
    if low.startswith("sourced"):
        return "sourced", s.split(":", 1)[1].strip() if ":" in s else ""
    if low.startswith("not found"):
        return "not_found", s.split(":", 1)[1].strip() if ":" in s else ""
    if low.startswith("not attempted"):
        return "not_attempted", s.split(":", 1)[1].strip() if ":" in s else ""
    return "not_attempted", s or "no image_source recorded"


def item_name(r):
    return r.get("create_name_FINAL") or r.get("invoice_line") or "<unnamed item>"


def item_ids(r):
    ids = [f"SKU {r['new_sku']}" if (r.get("new_sku") or "").strip() else "",
           f"ProductId {r['new_productid']}" if (r.get("new_productid") or "").strip() else ""]
    return ", ".join(i for i in ids if i)


def needs_image(r):
    """None when the item has an image or a sourced one; else the notice bullet."""
    kind, detail = image_source(r)
    if kind == "sourced":
        return None
    if has_image(r):
        return None
    nm = item_name(r)
    if kind == "not_found":
        where = detail or "the brand's site and other Dutchie menus"
        return f"- Product image: {nm} has no image. We looked at {where} and found none. Please add one."
    why = f" ({detail})" if detail else ""
    return f"- Product image: {nm} has no image. Image sourcing was not attempted{why}. Please add one."


def needs_link(r):
    """None when the global link needs no question; else the notice bullet (a question for the business)."""
    s = (r.get(LINK_COL) or "").strip()
    nm, low = item_name(r), s.lower()
    if low.startswith(("linked:", "no record:", "none:")):
        return None
    if low.startswith("best guess:"):
        body = s.split(":", 1)[1].strip()
        body = body[:-len("; please confirm")] if body.endswith("; please confirm") else body
        return (f"- Global catalog link: {nm} is linked to our best guess, {body}. Please confirm it is this product, "
                f"or name the right one.")
    if low.startswith("no match:"):
        body = s.split(":", 1)[1].strip()
        why, _, nearest = body.partition("; nearest: ")
        return (f"- Global catalog link: {nm} is not linked ({why}). "
                + (f"Nearest records: {nearest}. Is one of them this product?" if nearest else
                   "Does the brand list it under another name?"))
    return f"- Global catalog link: {nm} - no link attempt was recorded ({s or 'blank global_link_result'}). Please check it."


def fill(template, rows, operator, new_line_tag=DEFAULT_NEW_LINE_TAG):
    """(text, created rows, created new-line rows, defects). A created NEW_PL item is marked for the business's QC."""
    created = [r for r in rows if is_created(r)]
    defects = [f"NOT_READ_BACK: {item_name(r)!r}" for r in created if not (r.get("new_sku") or "").strip()]
    newl = [r for r in created if r.get("verdict") in NEW_LINE_VERDICTS]
    text = re.sub(r"<!--.*?-->\s*", "", template, flags=re.S)
    brands = sorted({r.get("lane_Brand") for r in created if r.get("lane_Brand")})
    first = (created or rows or [{}])[0]
    hand = []
    for r in created:
        b = needs_image(r)
        if b:
            hand.append(b)
        if not (r.get("online_title") or "").strip():
            hand.append(f"- Online title: {item_name(r)} has none yet.")
        b = needs_link(r)
        if b:
            hand.append(b)
    out = []
    for ln in text.split("\n"):
        s = ln.strip()
        if s == "[[items]]":
            out += [f"- {item_name(r)}"
                    + (f" - SKU {r['new_sku']}" if (r.get("new_sku") or "").strip() else "")
                    + (f" - NEW LINE, tagged `{new_line_tag}`: please review" if r.get("verdict") == "NEW_PL" else
                       f" - NEW BRAND and NEW LINE, tagged `{new_line_tag}`: please review" if r.get("verdict") == "NEW_BRAND" else "")
                    for r in created]
        elif s == "[[needs-hand]]":
            out += hand or ["- Nothing."]
        elif s.startswith("[[new-line]]"):
            if newl:
                out.append(s[len("[[new-line]]"):].strip())
        else:
            out.append(ln)
    text = "\n".join(out)
    subs = {"<Brand>": " / ".join(brands) or "<Brand>", "<n>": str(len(created)),
            "<invoice number>": first.get("invoice_no") or "<invoice number>",
            "<invoice date>": first.get("invoice_date") or "<invoice date>", "<new line tag>": new_line_tag,
            "<item QC tag>": new_line_tag,   # the marker's name in a tenant template copied before 2026-10-03
            "<Operator>": operator,
            "<new lines>": "; ".join(item_name(r) + (f" ({item_ids(r)})" if item_ids(r) else "") for r in newl)}
    for k, v in subs.items():
        text = text.replace(k, v)
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n", created, newl, defects


def main(argv):
    if "--selftest" in argv:
        return selftest()
    ip = get_flag(argv, "--intake")
    if not ip:
        print(__doc__)
        return EXIT_ABORT
    tenant = get_flag(argv, "--tenant")
    if tenant:
        import intake_pointers
        p = intake_pointers.load(tenant)["intake"]
        tpl, operator, floor = p["Notice template"], p["Operator"], p["Floor sheet"]
        ptr_tag = p.get("New line tag")
    else:
        ptr_tag = None
        tpl, operator, floor = get_flag(argv, "--template"), get_flag(argv, "--operator"), get_flag(argv, "--floor-sheet")
        if not (tpl and operator):
            abort("without --tenant pass --template and --operator")
    try:
        template = open(tpl, encoding="utf-8").read()
    except OSError:
        abort(f"notice template {tpl} unreadable")
    hdr, rows = read_csv(ip, V3_COLS, "--intake")
    if IMAGE_SOURCE_COL not in hdr:
        print(f"note: {os.path.basename(ip)} has no `{IMAGE_SOURCE_COL}` column - every created item reads as "
              "image sourcing not attempted")
    text, created, newl, defects = fill(template, rows, operator, get_flag(argv, "--new-line-tag") or ptr_tag or DEFAULT_NEW_LINE_TAG)
    if defects:
        print("DEFECT - no notice written:\n  " + "\n  ".join(defects))
        return EXIT_DEFECT
    if newl:
        cmd = (floor or "<no Floor sheet pointer>").replace("<intake.csv>", os.path.abspath(ip))
        print(f"NEW line(s) created on this invoice: {len(newl)} - floor sheet command (review it, then run):\n  {cmd}\n")
    if not created:
        print("no approved create row on this intake - no notice to draft")
        return EXIT_OK
    d_, stem = version_stem(ip)
    out = new_path(get_flag(argv, "--out-dir") or d_, f"{stem}-notice-{stamp()}", ".md")
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)
    left = sorted(set(re.findall(r"<[A-Za-z][^<>\n]{0,40}>", text)))
    print(text)
    print(f"wrote {out} ({len(created)} item(s))" + (f"; still for the Operator: {left}" if left else ""))
    return EXIT_OK


def selftest():
    t = Selftest("intake_notice")
    tpl = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates", "notice.md"),
               encoding="utf-8").read()
    rows = [{"verdict": "NEW_ITEM_WITH_SIBLING", "approved": "Y", "new_sku": "123", "create_name_FINAL": "A | P | W | 1g",
             "lane_Brand": "A", "invoice_no": "T-1", "invoice_date": "2026-09-20", "image_state": "0 images (NO_ECOM_IMAGE)",
             "online_title": "W 1g", "global_link_result": "linked: g-1 | W 1g - exact name via our online_title"},
            {"verdict": "EXISTS", "invoice_line": "A X preroll 1g"}]
    text, created, newl, d = fill(tpl, rows, "Pat Example")
    t.check("item line carries the SKU", "- A | P | W | 1g - SKU 123" in text)
    t.check("image gap listed", "Product image: A | P | W | 1g" in text)
    t.check("QUIET: new-line bullet dropped with no NEW_PL row", "New line:" not in text and not newl)
    t.check("no marker or comment survives", "[[" not in text and "<!--" not in text)
    t.check("operator filled, no marker left", "Questions to Pat Example" in text and "<new line tag>" not in text
            and "<item QC tag>" not in text)
    # Defect 1 (2026-10-08): the "New line:" paragraph named every new-line row's invoice line, approved = N included.
    pl = {"verdict": "NEW_PL", "approved": "Y", "invoice_line": "A Haze cart 0.5g (invoice words)", "lane_Brand": "A",
          "create_name_FINAL": "A | Cart | Haze | 0.5g", "new_sku": "55", "new_productid": "9055",
          "image_state": "deleted (source art)", "online_title": "Haze 0.5g",
          "global_link_result": "linked: g-2 | Haze Cart 0.5g - exact name via our online_title"}
    cat_n = {"verdict": "NEW_CATEGORY", "approved": "N", "invoice_line": "A Haze cart 0.5g (case of 5) sample", "lane_Brand": "A"}
    pl_n = {"verdict": "NEW_PL", "approved": "N", "invoice_line": "A Fog cart 0.5g", "lane_Brand": "A"}
    text2, _, newl2, _ = fill(tpl, rows + [pl, cat_n, pl_n], "Pat Example")
    t.check("FIRES: the new-line paragraph names the created item by its final name, with its ids",
            "New line: A | Cart | Haze | 0.5g (SKU 55, ProductId 9055) - a new product line" in text2 and len(newl2) == 1, text2)
    t.check("QUIET: an approved = N new-line row never reaches the paragraph, and no invoice line does",
            "case of 5" not in text2 and "Fog" not in text2 and "(invoice words)" not in text2)
    t.check("QUIET: new-line rows that are all approved = N drop the paragraph",
            "New line:" not in fill(tpl, rows + [cat_n, pl_n], "Pat Example")[0])
    t.check("a blank id never drops the created item from the paragraph",
            "New line: A | Cart | Haze | 0.5g - a new product line" in fill(tpl, rows + [dict(pl, new_sku="", new_productid="")], "x")[0])
    rows3 = rows + [{"verdict": "NEW_BRAND", "invoice_line": "Zed Haze cart 0.5g", "lane_Brand": "Zed", "new_sku": "77",
                     "create_name_FINAL": "Zed | Cart | Haze | 0.5g", "approved": "Y", "image_state": "deleted (source art)",
                     "online_title": "Haze 0.5g", "global_link_result": "no record: the brand has no global catalog brand"}]
    text3, created3, _, _ = fill(tpl, rows3, "Pat")
    t.check("a created NEW_BRAND item is marked NEW BRAND and NEW LINE for the business's review",
            "- Zed | Cart | Haze | 0.5g - SKU 77 - NEW BRAND and NEW LINE" in text3 and len(created3) == 2, text3[:200])
    bad = [dict(rows[0], new_sku="")]
    t.check("FIRES: NOT_READ_BACK on an approved row with no SKU", len(fill(tpl, bad, "x")[3]) == 1)
    t.check("QUIET: a create verdict with approved = N is not a created item",
            fill(tpl, [dict(rows[0], approved="N")], "x")[1] == [])
    # Defect 2 (2026-10-08): "What still needs a hand" printed "Nothing." over five created rows whose image_state read
    # `deleted (...)`. An approved create with no image needs a hand unless an image was sourced.
    for state in ("deleted (no cart art)", "", "source brand's image carried - REMOVE (cross-brand residue)",
                  "0 images (NO_ECOM_IMAGE - a human supplies art)"):
        tx = fill(tpl, [dict(pl, image_state=state)], "x")[0]
        t.check(f"FIRES: needs an image on image_state {state!r}",
                "Product image: A | Cart | Haze | 0.5g has no image" in tx and "- Nothing." not in tx, tx)
    tx = fill(tpl, [dict(pl, image_state="sibling image carried - keep only if generic brand art (platform KB Images)")], "x")[0]
    t.check("QUIET: a carried image that is kept needs no hand", "Product image:" not in tx and "- Nothing." in tx, tx)
    # image_source: the sourcing record (ruled 2026-10-08: brand site first, then other Dutchie menus).
    tx = fill(tpl, [dict(pl, image_source="https://example.test/brand/haze-cart.jpg")], "x")[0]
    t.check("QUIET: a sourced image (bare URL) clears the item", "Product image:" not in tx and "- Nothing." in tx, tx)
    tx = fill(tpl, [dict(pl, image_source="sourced: https://example.test/menu/haze")], "x")[0]
    t.check("QUIET: a sourced image (`sourced: <url>`) clears the item", "Product image:" not in tx, tx)
    tx = fill(tpl, [dict(pl, image_source="not found: the brand's site (example.test), two other Dutchie menus")], "x")[0]
    t.check("FIRES: `not found:` names where the lane looked",
            "We looked at the brand's site (example.test), two other Dutchie menus and found none" in tx, tx)
    tx = fill(tpl, [dict(pl, image_source="not attempted: no browser in this lane")], "x")[0]
    t.check("FIRES: `not attempted:` says so, with the reason",
            "Image sourcing was not attempted (no browser in this lane)" in tx, tx)
    tx = fill(tpl, [pl], "x")[0]
    t.check("FIRES: a blank image_source reads as not attempted",
            "Image sourcing was not attempted (no image_source recorded)" in tx, tx)
    t.check("a sourced image never clears a missing online title",
            "Online title:" in fill(tpl, [dict(pl, image_source="https://example.test/a.jpg", online_title="")], "x")[0])
    # global link (ruled 2026-10-13): the plan's best guess is the business's question; an exact link asks nothing
    ok = dict(pl, image_source="sourced: https://example.test/a")
    for val in ("linked: g-2 | Haze Cart 0.5g - exact name via our online_title", "no record: zero hits for 'Haze' under the brand",
                "none: the Operator ruled no link at the plan STOP"):
        tx = fill(tpl, [dict(ok, global_link_result=val)], "x")[0]
        t.check(f"QUIET: `{val.split(':')[0]}:` asks the business nothing", "Global catalog link" not in tx and "- Nothing." in tx, tx)
    tx = fill(tpl, [dict(ok, global_link_result="best guess: g-3 | Haze Cartridge 0.5g - the closest name (score 0.60 via "
                                                 "our online_title); other candidates: g-4 | Haze Pod 0.5g | ST | Active; please confirm")], "x")[0]
    t.check("FIRES: a best guess asks the business to confirm it, naming the record and the other candidates",
            "Global catalog link: A | Cart | Haze | 0.5g is linked to our best guess, g-3 | Haze Cartridge 0.5g" in tx
            and "g-4 | Haze Pod 0.5g" in tx and "Please confirm it is this product" in tx and "; please confirm." not in tx, tx)
    tx = fill(tpl, [dict(ok, global_link_result="no match: a tie: g-3 and g-4 are equally close; nearest: g-3 | Haze A; g-4 | Haze B")], "x")[0]
    t.check("FIRES: a no-match with candidates lists them and asks whether one is this product",
            "is not linked (a tie: g-3 and g-4 are equally close). Nearest records: g-3 | Haze A; g-4 | Haze B. Is one" in tx, tx)
    tx = fill(tpl, [dict(ok, global_link_result="no match: no Active ST record names 'Haze'")], "x")[0]
    t.check("FIRES: a no-match with no candidates asks whether the brand lists it under another name",
            "Does the brand list it under another name?" in tx, tx)
    tx = fill(tpl, [dict(ok, global_link_result="")], "x")[0]
    t.check("FIRES: a blank global_link_result (the attempt was not recorded) needs a hand",
            "no link attempt was recorded" in tx and "- Nothing." not in tx, tx)
    return t.done()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
