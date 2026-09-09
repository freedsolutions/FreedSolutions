---
name: dutchie-bi-looker
description: Edit Looker tiles and merge queries embedded in Dutchie Backoffice (leaflogix.looker.com) — table calc syntax, Ace editor automation via Playwright, signed embed token navigation, dashboard column/sort cleanup, save flow. Use when Adam needs to add or modify a metric, calc, or column on any dashboard tile in Dutchie Backoffice → BI tools.
---

# Dutchie BI Looker

Work on Looker dashboards embedded inside Dutchie Backoffice (`<server>.backoffice.dutchie.com` →
BI tools → iframe to `leaflogix.looker.com`). Covers the merge-query editor, table calculations,
dashboard tile bindings, the internal REST API that replaced most UI automation, and the
cross-origin/Ace patterns that survive it.

**This skill is client-agnostic.** Tile ids, dashboard ids, rules and tenant names live in the
client's own estate — its `CLAUDE.md` pointer block, `DATA-DICTIONARY.md`, and
`dashboard-<id>-*.md` guides. Nothing here should ever name a client.

## When to Use

- Add, edit, or fix a metric on a Looker tile in Dutchie Backoffice.
- A merge query needs a new dimension, custom measure, or table calculation.
- A buyer-facing dashboard needs column-visibility or sort cleanup.
- A formula error ("Expression incomplete", "Unknown function 'X'", "Field does not exist").

## When NOT to Use

- Native Dutchie reports (Sales, Inventory, Closing — non-Looker tabs). Different system.
- Building LookML at the Dutchie/Looker schema level — the model is read-only from this seat.
- Google Sheets formula work — see `google-sheets-patterns`.
- A Dutchie **platform** defect or gap (not our tile content) — file it rather than working around
  it silently: see `dutchie-support-ticket`.

## Inputs

- **Target tile / merge query** (required): dashboard id + tile name, or the merge did. Get them
  from the client's guides or an estate snapshot, never from this file.
- **Change description** (required): concrete enough to map to a calc, dim, or column.
- **Dutchie login** (required at session start): Adam logs in manually; the embed cookie is then
  good for roughly 24h. Never handle his credentials.

---

## ⚠ The tenant pin — first step of every query, every time

**The Looker instance is MULTI-TENANT.** More than one organisation's data lives in the same
`sql_server` model, and a single embed session can read across all of them. An unfiltered query
does not error — it silently blends tenants and returns numbers that look entirely plausible.

Every query you write, mint, or copy carries:

- `lsp_location.lsp_name` **pinned to exactly one tenant**, and
- `lsp_location.is_sandbox = No`, and
- `transactions.is_void = No` on any sales-side query.

Details and the full mandatory-filter set: **`references/explore-field-catalog.md` §1.**
The client's `CLAUDE.md` pointer block names which tenant. This file never does.

Two ways this bites even when you remember it:

- **`lsp_location.location_name` is NOT `lsp_location.lsp_name`.** Same view, near-identical
  labels. Filtering the tenant string on `location_name` matches nothing — or matches another
  tenant's identically-named store, because the value suggestions are not tenant-scoped.
- **Inner-dialog yesno filters default to "Yes" when added.** A freshly added `Is Sandbox` filter
  means sandbox-ONLY until you flip it to No. Verify after adding, never assume.

---

## Embedded architecture

```
<server>.backoffice.dutchie.com/reports/bi-tools/<page>
        │
        ▼
   <iframe src="https://leaflogix.looker.com/login/embed/<signed-path>?nonce=...&time=...">
        │  (302 redirect to /embed/<actual-path>, cookie set)
        ▼
   <iframe src="https://leaflogix.looker.com/embed/<path>">
```

The `/login/embed/` URL carries a signed nonce + timestamp scoped to the path it was issued for —
you cannot swap the dashboard id inside a signed URL. But once the cookie is set, any
`leaflogix.looker.com/embed/...` URL is reachable in the same session without re-signing. That is
the **embed escape**, and it is how you reach dashboards absent from Backoffice's sidebar.

### Login + navigation

1. Navigate to a Backoffice BI-tools page and wait for Adam's sign-in. The iframe now holds a
   `leaflogix.looker.com/login/embed/...` URL — the embed cookie is set.
2. Point the iframe (or, better, a plain top-level tab) at the real target:
   `https://leaflogix.looker.com/embed/merge/edit?did=<n>&dbnx=1`
3. Allow 12–15s for the Looker app to render.

**Use `https://leaflogix.looker.com/embed/preload` as the read surface.** It exposes the full
internal API but renders no tiles, so it loads fast and cannot wedge. Loading a heavy dashboard
just to get an API origin can wedge the renderer past the tool's timeout budget.

---

## Internal API — the write recipe

The embed session cookie grants the **Looker internal REST API** from an in-page `fetch`. This
replaces most fragile UI automation. All calls are same-origin from a `leaflogix.looker.com`
top-level tab. Headers are mandatory on **reads as well as writes** — without the CSRF token
everything 403s with an empty body that reads exactly like an auth failure:

```js
const h = {
  'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]').content,
  'X-Requested-With': 'XMLHttpRequest',
  'Accept': 'application/json', 'Content-Type': 'application/json',
};  // plus credentials: 'include'
```

### Read surfaces

- `GET /api/internal/dashboards/<id>` — full dashboard: `dashboard_filters` (with configured
  defaults, the ground truth the UI lies about) and `dashboard_elements`, each with `title`,
  `type`, `merge_result_id`, `query`, `result_maker` → `dynamic_fields` (calc expressions
  verbatim), `vis_config` (`hidden_fields`, `column_order`, formats), and **`filterables[].listen`**
  — the per-source-query filter mappings.
- `GET /api/internal/core/4.0/merge_queries/<mid>` — `source_queries`, merge-level
  `dynamic_fields`, `vis_config`, `sorts`.
- `GET /api/internal/core/4.0/queries/<qid>` — a source query's fields/filters/dynamic_fields.
- `GET /api/internal/core/4.0/queries/<qid>/run/json` — run any query, rows as JSON. Merges have
  **no** `run/json` (404) — measure a merge tile on its spine source query.

### Write surfaces

- `PATCH /dashboard_elements/<id>` — `{title}` rename ✅ · `{merge_result_id}` repoint ✅ (listens
  survive) · `{result_maker:{filterables:[{model,view,listen:[{dashboard_filter_name,field}]}]}}`
  ✅ the filter-mapping fix, one call replacing the whole Tiles-to-update panel flow ·
  `{result_maker:{vis_config}}` ❌ **silently ignored**.
- `DELETE /dashboard_elements/<id>` ✅ (204).
- `POST /queries` ✅ mint a query: `{model, view:'<explore>', fields, filters,
  dynamic_fields:'<JSON string>', limit}`.
- `POST /merge_queries` ✅ mint a merge: GET current → modify → POST → new mid → PATCH the
  element's `merge_result_id`. Strip `id`/`client_id`/`result_maker_id`/`can` from a GET payload.
- `POST /dashboard_elements` ✅ create a tile: `{dashboard_id, query_id | merge_result_id,
  type:'vis', title}`. The query **must** carry a `vis_config` or the tile shows "Trouble loading
  data" despite `run/json` working.
- `POST /dashboard_filters` ✅ create a filter · `PATCH {default_value}` ✅ · `PATCH {row}` ✅
  (ordering) · `DELETE` ✅. Never send the fat `field` blob from a GET — it is server-derived.
- `PATCH /looks/<look_id> {query_id}` ✅ — the repoint for a **Look-linked** tile. Check `look_id`
  before treating a plain tile as element-owned; the element-level PATCH 422s or no-ops.

### `dynamic_fields` entry shapes — copy exactly

```
custom dimension  {category:'dimension', expression, label, value_format:null,
                   value_format_name:null, dimension:'<slug>',
                   _kind_hint:'dimension', _type_hint:'string'|'number'}
custom measure    {category:'measure', expression:null, label, based_on:'<dim slug>',
                   type:'count_distinct'|'min'|'max'|'sum', measure:'<slug>',
                   _kind_hint:'measure', _type_hint:'number',
                   value_format:null, value_format_name:null}
table calc        {category:'table_calculation', expression, label,
                   table_calculation:'<slug>', _kind_hint:'measure',
                   _type_hint:'string'|'number'|'yesno',
                   value_format:null, value_format_name:null}
```

### The order that survives contact

1. **Re-GET the current binding.** Never build a POST from a stale snapshot — a parallel session's
   rebuild would be silently reverted. The API is the only current truth.
2. **Pin the tenant** (above) on every query in the change, including ones you only copied.
3. **Check the `fields` array** before editing a custom dimension's expression — a dim whose slug
   is not in `fields` cannot have its expression changed, and the write returns 200 anyway. Table
   calcs, by contrast, must **never** appear in `fields`.
4. **Mint, then run, then bind.** `POST /queries` → verify `run/json` 200 on the exact new id →
   only then PATCH the element. Reference the new query by **`res.id`, never `res.client_id`**.
5. **Bind with the v1-both form** on API-created tiles:
   `{query_id: X, result_maker: {id: <result_maker.id>, query_id: X}}`.
6. **Content-verify after the bind, not the 200.** Re-GET element → container → query and assert
   the edited text is present. A `Failed to fetch` exception may still have LANDED — re-GET before
   any retry, or you double-bind.
7. **Prove count invariance** on the spine query before and after, and close with a residual grep
   scoped to `dynamic_fields` + query `filters` — **never the whole snapshot**, whose
   `vis_config` caches retired strings forever.

### Creating a new query or dashboard

Same recipe, plus: the tenant pin and `is_sandbox = No` go in from the first POST (retrofitting
them later re-mints every downstream id), and a new dashboard's filters are created by API and
wired with the `filterables` PATCH afterwards. Full automation detail:
`references/patterns.md` → *Dashboard-creation + explore-save automation*.

---

## Merge editor — when the UI is still needed

- **Create** merges from an Explore: gear ("Explore actions") → **Merge results**, or open
  `https://leaflogix.looker.com/embed/merge` directly. Gear items need a **real** click.
- **Edit a bound merge** only at `/embed/merge/edit?did=<n>&dbnx=1`. Standalone saves create
  **orphan mids** — a recurring footgun.
- **Save is bottom-right, not in the header, and is disabled until dirty.** A disabled Save and a
  missing Save look identical if you only scan the header. If it stays grey after real edits,
  append an underscore to the title to force the dirty state, then rename back.
- **Ace editor**: clicks are blocked by the `.ace_content` overlay — focus the textarea ref
  directly, `Ctrl+A` + `Delete`, then type. Long formulas need `fill()` plus a trailing keystroke
  to reparse; read the expression back before saving.
- **Hard-reload (`location.reload(true)`)** after any save before trusting what a tile renders.

Save flow: calc-dialog Save updates the in-memory draft → outer **Run** re-executes → outer
**Save** mints a new mid and rebinds the tile.

---

## Traps

`references/traps.md` is the full symptom → cause → do list. The ones that have cost the most:

- A **200 is not evidence** — verify content after every bind.
- The **`fields` gate** silently blocks expression edits; table calcs must never be in `fields`.
- **`run/json` returns yesno calcs as `"Yes"`/`"No"` strings**, so a boolean test counts zero on a
  working tile.
- **Looker silently drops an unknown field** and still returns rows — check `Object.keys(rows[0])`.
- **Queries are content-addressed**, so a rebuild can silently strand a tile that shared the qid.
- **CSRF is required on GETs.** A bare 403 is not an auth failure.
- **Grids virtualise and below-fold tiles lazy-load** — a blank tile is usually a race; never read
  a grid by flattening `innerText`.

## Browser coordination (multi-session)

One shared persistent Playwright profile carries the logins, and concurrent sessions contend for
its lock. The holder file is `%LOCALAPPDATA%\ms-playwright-mcp\HOLDER.json` (machine-scoped):

```json
{"profile": "mcp-chrome-<hash>", "session": "<your name from ListAgents>",
 "claude_pid": 12345, "purpose": "<board> writes", "acquired_at": "<ISO>"}
```

1. **Acquire** before the first browser call of a *phase*: read the file. Absent or its
   `claude_pid` dead → take it. Held by a live session → `SendMessage` that **named** session and
   wait for confirmation. **Never broadcast release requests** — a stale broadcast once nearly
   closed a live browser mid-write. Countermand explicitly if your plans change.
2. **Release** when the browser phase ends, not at session end: `browser_close`, verify no
   `mcp-chrome` processes remain, *then* clear the file. Declare the handoff only after the close.
3. **Staleness**: `Get-CimInstance Win32_Process -Filter "ProcessId=<claude_pid>"` returns nothing
   ⇒ the entry is stale. Find your own pid by walking parents from `$PID` to `claude.exe`.
4. **Seed the file from OBSERVED ownership** (chrome tree → owning `claude.exe`), never intent.
5. Most reads need no profile at all — a separate browser channel or plain internal-API fetches
   are contention-free. The write channel is the client's call; the client pointer block names it.

## References

- **`references/explore-field-catalog.md`** — read before writing any query. Opens with the
  mandatory filter set (the tenant pin, §1), then the explores, views, LookML-name-vs-label traps,
  a recipes table, the embed escape, driving queries by URL params, and the hidden-iframe pattern
  for automation that outlives a tool timeout.
- **`references/explore-field-index.md`** — the generated complete field list. Grep it before
  proposing a leg on an attribute no live tile reads; sessions have built on fields that did not
  exist. Regenerated by the `bi-change` skill's `explore_catalog_index.js`, never hand-edited.
- **`references/traps.md`** — symptom → cause → do, the full list.
- **`references/patterns.md`** — long-form craft: Lexp cheat sheet, common patterns, tile cleanup,
  what is and isn't scriptable, the Backoffice REST API + Global Brand Catalog QC, house style.
- **`references/dutchie-platform-kb.md`** — Dutchie platform behaviour: catalog→inventory
  attribute inheritance classes, the PLC-keyed flower-equivalency system, lookup-list endpoints,
  the repurposed-field watch-list. Entries dated [DOC]/[PROBE]/[TENANT].
- **`references/mdm-product-line-rules.md`** — portable product-line/QC rule patterns. The
  client's `DATA-DICTIONARY.md` outranks it.
- **Ripple scanning** is the `bi-change` skill's job:
  `<bi-change skill>/scripts/bi_impact_scan.js --estate <estate dir> "<needle>" | --verify | --stale`
  attributes every hit to dashboard + tile and reports doc freshness.
- Memory files (load when relevant): `feedback_looker_table_calc_syntax.md`,
  `feedback_looker_merge_field_refs.md`, `feedback_looker_ace_editor.md`,
  `feedback_looker_tile_cache_lag.md`.

**Canon order:** the client's `DATA-DICTIONARY.md` > `mdm-product-line-rules.md` > this skill >
memory. A rule changes in the Dictionary first.
