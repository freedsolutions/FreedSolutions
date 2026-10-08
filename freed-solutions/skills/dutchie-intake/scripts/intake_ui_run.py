"""intake_ui_run.py - the neo `run` driver for the UI rows of an R124 plan. No login, no write by itself.

  python intake_ui_run.py emit --plan <plan.csv> --seq <n> [--keymap <keymap.json>] [--live] [--origin <url>]
  python intake_ui_run.py harvest [--origin <url>] [--product <ProductId>]
  python intake_ui_run.py record --plan <plan.csv> --seq <n> --result <result.json> --progress <progress.jsonl>
                                 [--keymap <keymap.json>]
  python intake_ui_run.py --selftest

`gridBatch` (dutchie-bi-looker) sends the grid rows itself and returns HANDOFF for the rest. A HANDOFF row on a
UI channel is run here, one row per neo `run` call:

  emit     prints ONE neo `run` script for plan row <seq>: it finds the session's own Backoffice tab, makes a
           FULL navigation to the row's item (never an SPA hop: platform KB), installs `intake_ui_rows.js` and
           calls the matching function. Paste it as the `code` of `mcp__browseros-neo__run`. dryRun unless --live.
             MINT_STRAIN / strain_mint   uiRowsMintStrain   (update-strain, StrainId 0, guarded on get-strains)
             COPY / ui_copy              uiRowsCopy         (source item page; `Copy online details` CHECKED)
             CONTENT / item_form         uiRowsContent      (new item page via the keyMap; ONE guarded Save)
             UNRETIRE / ui_unretire      uiRowsUnretire     (the UI fallback; the batch default is the grid mutation)
           Any other row is refused by name: a grid row is gridBatch's, a replay row (image_remove, link_replay)
           has its own KB recipe, a Brand create is UNPROVEN (P5), Tags run on the grid since P4.
  harvest  prints the one-time script that keeps the page's own record-read envelope for the tab (run it first).
  record   appends the run's result to the progress JSONL (seq, step, product_key, status, time) and, for a COPY
           that WROTE, writes `new:<line>` -> the new ProductId into the keyMap JSON that gridBatch reads.

The script re-hashes the row (`row_sha1`) before emitting it: an edited plan row is refused here too.
Exit: 0 ok · 2 refused or input refused.
"""
import json
import os
import sys
from datetime import datetime

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from intake_common import EXIT_ABORT, EXIT_OK, Selftest, abort, get_flag, read_csv  # noqa: E402
from intake_plan import PLAN_COLS, row_sha1  # noqa: E402

HELPER = os.path.join(HERE, "intake_ui_rows.js")
DEFAULT_ORIGIN = "https://<server>.backoffice.dutchie.com"
UI = {("MINT_STRAIN", "strain_mint"): "mint", ("COPY", "ui_copy"): "copy", ("CONTENT", "item_form"): "content",
      ("UNRETIRE", "ui_unretire"): "unretire"}
NOT_HERE = {
    "grid": "a grid row: gridBatch sends it",
    "grid_bulk_unretire": "a grid row: gridBatch sends the bulk-unretire mutation",
    "image_remove": "a replay row: remove-product-image by its KB recipe",
    "link_replay": "a replay row: link / unlink-from-catalog-product by its KB recipe",
    "ui_brand_create": "UNPROVEN (probe P5): the plan refuses it",
    "ui_brand_link": "UNPROVEN (probe P5): the plan refuses it",
}


class Refused(Exception):
    pass


def load_plan(path):
    _, rows = read_csv(path, PLAN_COLS, "--plan")
    return rows


def pick(rows, seq):
    hit = [r for r in rows if r["seq"] == str(seq)]
    if len(hit) != 1:
        raise Refused(f"SEQ_UNKNOWN: the plan has no single row seq {seq}")
    r = hit[0]
    if row_sha1(r) != r["row_sha1"]:
        raise Refused(f"PLAN_SHA_MISMATCH: seq {seq} does not hash to its row_sha1 - the plan was edited after approval")
    return r


def load_keymap(path):
    if not path or not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def resolve(r, keymap):
    key = r["product_key"]
    if key.startswith("new:"):
        if key not in keymap:
            raise Refused(f"NEW_KEY_UNRESOLVED: seq {r['seq']} writes {key}; no keyMap entry yet (its COPY has not been recorded)")
        return str(keymap[key])
    if not key.isdigit():
        raise Refused(f"KEY_NOT_A_PRODUCT: seq {r['seq']} product_key {key!r}")
    return key


def call_for(r, keymap, live):
    """(kind, url path or None, the JS call args) for one UI row."""
    kind = UI.get((r["step"], r["channel"]))
    if not kind:
        why = NOT_HERE.get(r["channel"]) or (
            "Tags run on the grid since probe P4 (REPLACE); a form Tags row is not emitted"
            if r["channel"] == "item_form" and r["field"] == "Tags" else f"step {r['step']} on {r['channel']} is not a UI row")
        raise Refused(f"NOT_A_UI_ROW: seq {r['seq']}: {why}")
    dry = not live
    if kind == "mint":
        parts = dict(p.split("=", 1) for p in r["target"].split(";") if "=" in p)
        if not parts.get("name") or not parts.get("type"):
            raise Refused(f"STRAIN_TARGET_UNREAD: seq {r['seq']} target {r['target']!r} is not name=<n>;type=<t>")
        return kind, None, {"name": parts["name"], "type": parts["type"], "dryRun": dry}
    if kind == "copy":
        src = r["before"].strip()
        if not src.isdigit():
            raise Refused(f"COPY_SOURCE_UNREAD: seq {r['seq']} before {src!r} is not a ProductId")
        name = r["target"].strip()
        if not name or name.endswith("(Copy)"):
            raise Refused(f"NAME_REFUSED: seq {r['seq']} never saves a blank or `(Copy)` name")
        return kind, f"/products/catalog/{src}", {"name": name, "sourceId": int(src), "dryRun": dry}
    pid = resolve(r, keymap)
    if kind == "content":
        fld = {"Online title": "title", "Online description": "description"}.get(r["field"])
        if not fld:
            raise Refused(f"NOT_A_UI_ROW: seq {r['seq']} CONTENT field {r['field']!r}")
        if not r["target"].strip():
            raise Refused(f"CONTENT_BLANK: seq {r['seq']} a blank target is a clear, not the ruled path")
        return kind, f"/products/catalog/{pid}", {"productId": int(pid), fld: r["target"], "dryRun": dry}
    return kind, f"/products/catalog/{pid}", {"productId": int(pid), "dryRun": dry}


FN = {"mint": "uiRowsMintStrain", "copy": "uiRowsCopy", "content": "uiRowsContent", "unretire": "uiRowsUnretire"}

PRELUDE = """// neo `run` script emitted by intake_ui_run.py - {label}
const ORIGIN = {origin};
const HELPER_SRC = {helper};
const mine = (await browser.pages.list()).filter(t => t.ownership === 'mine' && String(t.url).indexOf(ORIGIN) === 0);
const p = mine.length ? browser.page(mine[0].pageId) : await browser.open(ORIGIN + '/products/catalog');
"""

ROW = PRELUDE + """{goto}await p.evaluate((src) => {{ if (!window.uiRowsCopy) (new Function(src))(); return true; }}, HELPER_SRC);
const hasCtx = await p.evaluate(() => !!sessionStorage.getItem('__intakeUiRowsCtx'));
if (!hasCtx.value) return {{ ok: false, reason: 'MISSING_CONTEXT', detail: 'run the harvest script on this tab first' }};
const res = await p.evaluate((a) => window.{fn}(a), {args});
return Object.assign({{ seq: {seq}, step: {step}, product_key: {key} }}, res.value);
"""

GOTO = """await p.goto(ORIGIN + {path});
await p.waitForText('Basic information', {{ timeout: 15000 }});
"""

HARVEST = PRELUDE + """await p.goto(ORIGIN + '/products/catalog/' + {pid});
await p.waitForText('Basic information', {{ timeout: 15000 }});
await p.evaluate((src) => {{ if (!window.uiRowsCopy) (new Function(src))(); return true; }}, HELPER_SRC);
// read-only hop away and back so the page re-issues its record read AFTER the helper is installed; no Save follows
await p.evaluate(() => {{ history.pushState({{}}, '', '/products/strains'); dispatchEvent(new PopStateEvent('popstate')); }});
await p.waitForText('Strains', {{ timeout: 10000 }});
await p.evaluate((pid) => {{ history.pushState({{}}, '', '/products/catalog/' + pid); dispatchEvent(new PopStateEvent('popstate')); }}, {pid});
// wait in the page for the re-issued record read itself (the form heading is already on screen after the hop)
const h = await p.evaluate(async () => {{
  for (let i = 0; i < 40; i++) {{
    if (window.__intakeUiRows.rec.some(e => e.url.indexOf('get-product-details-v2') >= 0)) break;
    await new Promise(r => setTimeout(r, 250));
  }}
  return window.uiRowsHarvest();
}});
await p.reload();   // the SPA-hopped form is never saved: discard it
return h.value;
"""


def helper_src():
    """The helper as the page needs it: the header block and whole-line `//` comments dropped (the run `code`
    travels in every call); every code line kept byte for byte."""
    with open(HELPER, encoding="utf-8") as f:
        src = f.read()
    if src.startswith("/*"):
        src = src[src.index("*/") + 2:]
    return "\n".join(ln for ln in src.splitlines() if ln.strip() and not ln.lstrip().startswith("//"))


def emit(rows, seq, keymap, live, origin):
    r = pick(rows, seq)
    kind, path, args = call_for(r, keymap, live)
    goto = GOTO.format(path=json.dumps(path)) if path else ""
    return ROW.format(label=f"seq {r['seq']} {r['step']} {r['product_key']} {'LIVE' if live else 'dryRun'}",
                      origin=json.dumps(origin), helper=json.dumps(helper_src()), goto=goto, fn=FN[kind],
                      args=json.dumps(args), seq=json.dumps(r["seq"]), step=json.dumps(r["step"]),
                      key=json.dumps(r["product_key"]))


def harvest(origin, pid):
    return HARVEST.format(label="harvest the record-read envelope", origin=json.dumps(origin),
                          helper=json.dumps(helper_src()), pid=json.dumps(str(pid)))


def record(rows, seq, result, progress, keymap_path):
    r = pick(rows, seq)
    if str(result.get("seq", r["seq"])) != r["seq"]:
        raise Refused(f"RESULT_SEQ_MISMATCH: the result is for seq {result.get('seq')}, not {r['seq']}")
    status = result.get("status") or (("DRYRUN" if result.get("dryRun") else "OK") if result.get("ok") else result.get("reason") or "STOP")
    line = {"seq": r["seq"], "step": r["step"], "product_key": r["product_key"], "field": r["field"],
            "channel": r["channel"], "status": status, "at": datetime.now().isoformat(timespec="seconds")}
    for k in ("newProductId", "productId", "strainId", "detail"):
        if k in result:
            line[k] = result[k]
    km = load_keymap(keymap_path)
    if r["step"] == "COPY" and status == "WROTE":
        nid = result.get("newProductId")
        if not str(nid or "").isdigit():
            raise Refused("COPY_ID_MISSING: a COPY that WROTE must carry newProductId")
        if r["product_key"] in km and str(km[r["product_key"]]) != str(nid):
            raise Refused(f"KEYMAP_CONFLICT: {r['product_key']} is already {km[r['product_key']]}, the result says {nid}")
        km[r["product_key"]] = int(nid)
        if keymap_path:
            with open(keymap_path, "w", encoding="utf-8") as f:
                json.dump(km, f, indent=1, sort_keys=True)
    with open(progress, "a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")
    return line, km


def main(argv):
    if "--selftest" in argv:
        return selftest()
    if not argv or argv[0] not in ("emit", "harvest", "record"):
        abort("usage: intake_ui_run.py emit|harvest|record ... (see the header)")
    mode, args = argv[0], argv[1:]
    origin = get_flag(args, "--origin", DEFAULT_ORIGIN)
    try:
        if mode == "harvest":
            print(harvest(origin, get_flag(args, "--product") or abort("--product <a ProductId to load> is required")))
            return EXIT_OK
        plan = get_flag(args, "--plan") or abort("--plan is required")
        seq = get_flag(args, "--seq") or abort("--seq is required")
        rows = load_plan(plan)
        if mode == "emit":
            print(emit(rows, seq, load_keymap(get_flag(args, "--keymap")), "--live" in args, origin))
            return EXIT_OK
        res_path = get_flag(args, "--result") or abort("--result is required")
        with open(res_path, encoding="utf-8") as f:
            result = json.load(f)
        line, _ = record(rows, seq, result, get_flag(args, "--progress") or abort("--progress is required"),
                         get_flag(args, "--keymap"))
        print(json.dumps(line, ensure_ascii=False))
        return EXIT_OK
    except Refused as e:
        print(f"REFUSED {e}")
        return EXIT_ABORT


# ---------------------------------------------------------------------------------------------------------
# selftest: synthetic rows only (Brand A, Strain X ...); no tenant, vendor or brand name.

def _rows():
    base = [("MINT_STRAIN", "strain:Strain Q", "_strain", "", "name=Strain Q;type=Sativa", "strain_mint"),
            ("UNRETIRE", "401", "_state", "retired", "active", "grid_bulk_unretire"),
            ("COPY", "new:2", "_copy", "601", "Brand A | Pre-Roll | Strain Q | 1g", "ui_copy"),
            ("ALIGN", "new:2", "StrainId", "name:Strain X", "name:Strain Q", "grid"),
            ("CONTENT", "new:2", "Online title", "Strain X Pre-Roll 1g", "Strain Q Pre-Roll 1g", "item_form"),
            ("IMAGE_REMOVE", "new:2", "_images", "a.jpg", "", "image_remove"),
            ("UNRETIRE", "402", "_state", "retired", "active", "ui_unretire")]
    out = []
    for i, (step, key, field, before, target, ch) in enumerate(base, 1):
        r = dict(seq=str(i), step=step, line_no="2", product_key=key, field=field, before=before, target=target,
                 channel=ch, depends_on="", provenance="synthetic")
        r["row_sha1"] = row_sha1(r)
        out.append(r)
    return out


def selftest():
    import tempfile
    t = Selftest("intake_ui_run")
    rows = _rows()
    js = emit(rows, "3", {}, False, "https://example.test")
    t.check("COPY emits a full navigation to the SOURCE item and calls uiRowsCopy in dryRun by default",
            "p.goto(ORIGIN + \"/products/catalog/601\")" in js and "window.uiRowsCopy(a)" in js
            and '"dryRun": true' in js and '"sourceId": 601' in js)
    t.check("the emitted script carries the helper source (the sandbox reads no file)", "uiRowsHarvest" in js and "HELPER_SRC" in js)
    t.check("--live flips dryRun to false", '"dryRun": false' in emit(rows, "3", {}, True, "https://example.test"))
    t.check("MINT_STRAIN reads name and type from the target, with no navigation",
            '"name": "Strain Q", "type": "Sativa"' in emit(rows, "1", {}, False, "x") and "p.goto(ORIGIN + " not in
            emit(rows, "1", {}, False, "x"))

    def refused(fn, code):
        try:
            fn()
            return False
        except Refused as e:
            return str(e).startswith(code)
    t.check("FIRES: CONTENT on a new item before its COPY is recorded (NEW_KEY_UNRESOLVED)",
            refused(lambda: emit(rows, "5", {}, False, "x"), "NEW_KEY_UNRESOLVED"))
    t.check("QUIET: CONTENT resolves new:2 through the keyMap to the new item's page",
            "/products/catalog/9500" in emit(rows, "5", {"new:2": 9500}, False, "x"))
    t.check("FIRES: a grid row is gridBatch's (NOT_A_UI_ROW)", refused(lambda: emit(rows, "4", {}, False, "x"), "NOT_A_UI_ROW"))
    t.check("FIRES: the bulk-unretire mutation row is gridBatch's (NOT_A_UI_ROW)",
            refused(lambda: emit(rows, "2", {}, False, "x"), "NOT_A_UI_ROW"))
    t.check("FIRES: a replay row is not run here (NOT_A_UI_ROW)", refused(lambda: emit(rows, "6", {}, False, "x"), "NOT_A_UI_ROW"))
    t.check("QUIET: a ui_unretire row emits the UI fallback", "window.uiRowsUnretire(a)" in emit(rows, "7", {}, False, "x"))
    bad = [dict(r) for r in rows]
    bad[2]["target"] = "Brand A | Pre-Roll | Strain Q | 1g (Copy)"
    t.check("FIRES: an edited row (PLAN_SHA_MISMATCH)", refused(lambda: emit(bad, "3", {}, False, "x"), "PLAN_SHA_MISMATCH"))
    bad[2]["row_sha1"] = row_sha1(bad[2])
    t.check("FIRES: a `(Copy)` name is never emitted (NAME_REFUSED)", refused(lambda: emit(bad, "3", {}, False, "x"), "NAME_REFUSED"))
    d = tempfile.mkdtemp()
    prog, km = os.path.join(d, "p.jsonl"), os.path.join(d, "k.json")
    line, kmap = record(rows, "3", {"seq": "3", "ok": True, "status": "WROTE", "newProductId": 9500}, prog, km)
    t.check("record: a COPY that WROTE puts new:2 -> its ProductId in the keyMap file",
            kmap == {"new:2": 9500} and json.load(open(km, encoding="utf-8")) == {"new:2": 9500})
    t.check("record: one progress line (seq, status, time)", line["status"] == "WROTE" and open(prog, encoding="utf-8").read().count("\n") == 1)
    t.check("FIRES: a second COPY result with another id (KEYMAP_CONFLICT)",
            refused(lambda: record(rows, "3", {"seq": "3", "ok": True, "status": "WROTE", "newProductId": 9501}, prog, km), "KEYMAP_CONFLICT"))
    t.check("FIRES: a COPY that WROTE with no id (COPY_ID_MISSING)",
            refused(lambda: record(rows, "3", {"seq": "3", "ok": True, "status": "WROTE"}, prog, os.path.join(d, "k2.json")), "COPY_ID_MISSING"))
    t.check("FIRES: a result for another seq (RESULT_SEQ_MISMATCH)",
            refused(lambda: record(rows, "3", {"seq": "5", "ok": True}, prog, km), "RESULT_SEQ_MISMATCH"))
    line2, _ = record(rows, "5", {"seq": "5", "ok": False, "reason": "SAVE_GUARD", "detail": "StrainId would move"}, prog, km)
    t.check("record: a STOP is logged with its reason as the status", line2["status"] == "SAVE_GUARD")
    h = harvest("https://example.test", 601)
    t.check("harvest hops read-only and RELOADS so the hopped form is never saved",
            "uiRowsHarvest" in h and "p.reload()" in h and "pushState" in h)
    return t.done()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
