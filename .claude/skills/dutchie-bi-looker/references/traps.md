<!-- Generated from "freed-solutions/skills/dutchie-bi-looker/references/traps.md". Edit the repo skill source and rerun ops/notion-workspace/scripts/sync-claude-skill-wrappers.ps1; do not edit this Claude copy directly. -->

# Looker-in-Dutchie — traps

Every entry is **symptom → cause → do**. They are here because each one cost a session, and most
of them fail *silently*: a 200, plausible rows, a tile that renders. Distilled 2026-09-08 from the
dated session logs (2026-08-18 → 2026-09-04); the client-specific narrative those logs carried is
in the client archive, not here.

The single rule behind half this file: **a 200 is not evidence.** Re-GET and assert the content.

---

## 1. Writes that silently do nothing

### The `fields` gate — an expression edit that never lands
**Symptom.** `POST /queries` returns 200, the slug/label/filter-key renames persist, and the
**expression is unchanged** — even a one-character edit.
**Cause.** A custom dimension whose slug is not in the query's `fields` array cannot have its
expression changed. Referenced only by a query filter or a measure's `based_on`, it is invisible
to the write.
**Do.** Assert the slug appears in `fields` *before* editing its expression. If it does not,
either add it to `fields` for the write, or restructure so the logic is expressed directly.
This is very likely the root cause of the older "silent 200 no-op" folklore — check it before
blaming the binding form.

### …but never put a TABLE CALCULATION in `fields`
**Symptom.** The query runs, the tile renders correctly, yet every open of the Explore or
"Edit Tile" editor throws `'<slug>' no longer exists on <explore>, or you do not have access to
it, and it will be ignored`. Later, a UI save silently rewrites `fields` and drops them —
and reverts `sorts` with them.
**Cause.** Table calcs live only in `dynamic_fields`; Looker renders them as columns
automatically. The editor tries to resolve anything in `fields` as a real explore field.
**Do.** `fields` = real explore fields + custom dimensions/measures. Table calcs, never.
`hidden_fields`, `hidden_points_if_no` and calc sorts all work fine on a calc absent from `fields`.

### API-minted tiles ignore a bare `{query_id}` PATCH
**Symptom.** 200, but neither `element.query_id` nor `result_maker.query_id` moves. UI-created
tiles accept the same call fine.
**Cause.** Tiles created via `POST dashboard_elements` need the binding written at both levels.
**Do.** Use the **v1-both** form: `{query_id: X, result_maker: {id: <result_maker.id>, query_id: X}}`.
The same silent-no-op class has been seen once on `{merge_result_id}`.

### `result_maker.vis_config` PATCH is ignored
**Symptom.** 200, `dynamic_fields` untouched, viz unchanged — even with `result_maker.id` included.
**Do.** Viz changes (hide column, formats) go through the merge editor UI, or ride along in a new
merge/query POST.

### Look-linked tiles reject the repoint
**Symptom.** `PATCH dashboard_elements {query_id}` → **422** *"Query ID must not have a value if a
Look ID is provided"*; `{result_maker:{query_id}}` → 200 and ignored.
**Cause.** The Look owns the query.
**Do.** `PATCH /looks/<look_id> {query_id}` — and know it changes the Look everywhere it renders.
Always check `look_id` before treating a plain tile as element-owned. Harvests before 2026-08-27
do not record it.

### A PATCH that throws `Failed to fetch` MAY STILL HAVE LANDED
**Symptom.** An exception from the fetch, so the write "failed".
**Cause.** The write committed; the exception came from reading the response.
**Do.** **Re-GET before any retry.** A blind retry double-binds the tile.

### Verify content after the bind, not the 200
A silent no-op mid-chain poisons every later rebuild built from "the current binding" — one tile
went two rebuild generations still carrying a pre-fix expression because a repoint had no-op'd and
the next edit re-GET'd the stale lineage. After any bind: re-GET element → container → query and
assert the edited text is present. Close the session with an estate-wide residual grep.

---

## 2. Verification that lies

### Scope the residual grep to `dynamic_fields` + query `filters` — never the whole snapshot
`vis_config.query_fields[].lookml_expression` is Looker's **stale server-side cache** of a field
definition. It does not update when the expression changes, so retired strings live there forever.
Measured after one rename: a whole-file grep found the dead string 3× (reads as a failed ripple)
while `dynamic_fields` had **0** — the truth. Element-level `result_maker.vis_config` caches full
field definitions including expressions for the same reason; they are display-layer, not
executable, not API-writable, and self-heal on the next editor save.

### `run/json` returns yesno table calcs as `"Yes"` / `"No"` strings
`rows.filter(r => r.flag === true)` counts zero on a tile whose flags fire perfectly. Verify a QC
tile on its **label** column, not the yesno bands driving it; if you must test a yesno, compare to
the string.

### Looker silently drops an unknown field and still returns rows
POSTing a field that does not exist on the explore succeeds, runs, and returns the other columns
with the bad one simply absent. A join keyed on it collapses every row onto `undefined` and looks
like a data mismatch rather than a typo. **Check `Object.keys(rows[0])` against the `fields` you
asked for** before trusting any join or count.

### Merge queries have no `run/json` endpoint (404)
Count invariance on a merge tile is measured on the **spine source query's** own row count, run
before and after the bind — never on the merge id.

### `run/json` is not equivalent to how a tile renders
Plain queries whose table calcs use `to_number` 400 chronically on `run/json` while their tiles
render fine. Diagnose a render error through the querymanager batch instead
(`POST /api/internal/querymanager/queries` + the streaming GET); the failing task carries
`"status":"error"` with the real server message.

### Reference a new query by `res.id`, never `res.client_id`
A query POST returns two 32-char slugs. Only `id` resolves in `PATCH dashboard_elements
{query_id}` and in merge `source_queries[].query_id`; `client_id` 422s *"Query not found"*.
Content-addressing makes a re-POST to recover the right id a free no-op.

### Queries and merges are content-addressed
An identical POST body returns the **same id**. Rebuilding a merge two tiles share converges both
onto one new mid, and accidental double-rebuilds are harmless. It also means a filter change that
mints new qids on one dashboard **silently leaves a sharing twin on the old ones** — find sharers
by grepping the estate snapshots for the qid, and mirror the rebuild.

---

## 3. Semantics that produce plausible wrong numbers

### `lsp_location.location_name` is NOT `lsp_location.lsp_name`
Same view, near-identical labels. Filtering the tenant string on `location_name` matches nothing —
or worse, another tenant's identically-named store, because suggestions are not tenant-scoped.
**The multi-tenant pin is ALWAYS `lsp_name`.** See `explore-field-catalog.md` §1.

### Inner-dialog yesno filters default to "Yes" when added
A freshly added `Is Sandbox` or `Is Void` filter silently means sandbox-ONLY / void-ONLY until
flipped to No. Always verify after adding.

### A field's ROLE in a query changes the join's behaviour
On a one-to-many join, using a field as a **filter only** is exact and NULL-safe; **selecting the
same field as a dimension fans the result out** (measured: +2.5% units / +2.9% dollars, and rows
with no match are dropped). Rule: on one-to-many joins, filter-only — never put the field in
`fields`.

### Adding a dimension re-grains every measure on that query
min/max and other measures aggregate at the query grain. There is no way to hold one leg coarse
and another fine inside a single query — that is two queries or a merge. Say so before building.

### Filtered measures' `type` is inert
A custom measure with `based_on: <measure>` + `filters` may carry `type: 'count_distinct'` and
still compute the underlying measure's sum. Verified by minting a `type:'sum'` variant and
comparing `run/json` row-for-row. Do not "fix" it; it is a red herring.

### `count_distinct` over a custom dimension is the string-consistency primitive
min/max only work on numerics. For a string attribute use
`{category:"measure", based_on:"<dim slug>", type:"count_distinct"}` and flag `> 1`. Normalize
**inside the dim** before counting. The dim is referenced only via `based_on`, so it does not go
in `fields` — which puts it straight into the `fields`-gate trap above if you later edit it.

### Snowflake DESC sorts NULLS FIRST
A null else-branch floats empty rows to the top of a DESC-sorted queue. Return `0`, not null, for
"not applicable" rows on any queue calc.

### An explore may not be able to join what you assume
Reachability is per-explore and worth auditing before designing an exclusion: one explore listened
to the inventory-tag filter on 25 of 29 queries while a snapshot explore could not join the tag
table **at all** (0 of 16). A tag-based exclusion therefore does not protect snapshot-derived
measures, and a name-chip standing in for it there is **load-bearing** — not redundant cleanup.

### A live join rewrites history retroactively
A room name read through a live join (rather than stored on the row) means renaming the room
rewrites all snapshot history. There is no dual-name transition window to code around — the
opposite of an attribute stored on transaction rows, where trend lines break at the seam.

### Inline-form logic in a SQL-context custom dimension breaks the tile
Symptom: *"Trouble loading data"*, querymanager error `Invalid function for sql context:
"to_number"`. Custom dimensions evaluate in SQL context; use the chain form.

### A four-dim dependency chain must be copied as a unit
A custom dim built on other custom dims (e.g. a product-line chain) POSTs fine and runs fine as
dims-only with a dangling reference — the 400 *"Referenced expression contains errors"* only
detonates when a `based_on` measure forces it to compile. So a partial copy passes every cheap
check and breaks the tile after bind. Copy the whole chain, and **run-before-patch**: verify
`run/json` 200 on the exact new qid, with the measure included, before repointing anything.

### `vis_config.row_groups` works on DIMENSIONS only
Pointed at a table calculation the config POSTs, persists, and the grid **ignores it** — no error,
and a later reader sees config claiming grouping is on. Detect by DOM
(`.ag-row-group`, a first cell with `col-id="ag-Grid-AutoColumn"`), not by config. Remove dead
config rather than leaving it.

### `hidden_points_if_no` is an ARRAY on UI-configured merges
The UI writes `["calc_name"]`, not a scalar. Writing a bare string to a merge the UI once touched
silently breaks the Hide-No's. Read the existing shape and match it.

---

## 4. Session, channel and transport

### CSRF is required on GETs, not just writes
An internal-API GET without `x-csrf-token` returns a **bare 403 that reads exactly like an auth
failure** — you will waste time re-logging in. Send it on every call.

### Use `/embed/preload` as the read surface
It exposes the full internal API but renders no tiles, so it loads fast and cannot wedge. Loading
a real dashboard just to get an API origin is a trap: a heavy board can wedge the renderer past
the CDP budget and the evaluate times out before you can call anything.

### Embed session expiry reads as profile loss
The browser profile's cookie jar survives process kills and relaunches. When it shows the login
page, that is **server-side session expiry**, not profile loss — the fix is one human login, not
a profile rebuild. If every browser call errors *"Browser is already in use"*, pre-reconnect
processes hold the lock: kill scoped by the profile path in the command line; cookies survive.

### `browser_evaluate` `filename` saves are double-encoded
The result is wrapped as a JSON string literal. Unwrap with one parse pass before treating the
file as the document — an object-walk on a wrapped file parses to a bare string and silently
"finds nothing", which is vacuous verification.

### Chrome-channel JS output is capped and redacted
Results are truncated at roughly a kilobyte and redacted on key names that look like secrets;
never return `location.search` or cookies from that channel. Push a baseline into the page and
diff hashes there instead of shipping rows out.

### Server-side render tasks fail on any dashboard with merge tiles
`POST /render_tasks/dashboards/<id>/png` is permitted, but fails server-side with *"Making a merge
result with filters requires the filters array to be the same length as the number of source
queries"*. Scheduled delivery hits the same wall. For images, take element screenshots of tile
cards instead.

### Dashboard grids virtualise, and below-fold tiles lazy-load
A tile that looks blank is usually below the fold; scroll the dashboard scroller through the page
first, and allow 10–30s for multi-query merges. A missing grid right after a scroll is a race, not
a failure. Read cells via `.ag-cell[col-id]` grouped by `row-index` — **never by flattening
`innerText`**, which mis-aligns columns and makes every table calc look empty.

### Re-GET the current binding before any write
A parallel session's rebuild landing mid-review would be silently reverted by a POST built from an
old query body. Estate snapshots date fast on active days; the API is the only current truth.

---

## 5. UI automation, when the API cannot do it

- **Ace editor**: direct clicks are blocked by the `.ace_content` overlay. Focus the textarea ref
  directly, `Ctrl+A` + `Delete`, then type. Short formulas: `pressSequentially`. Long ones
  (>~1000 chars): `pressSequentially` times out — use `fill()`, then one trailing keystroke to
  force a reparse, then **read back the expression before saving** (fill + Ace can leave a
  missing or extra paren).
- **Chip inputs** commit headless via React fiber: native value setter + `input` event, then
  invoke `__reactProps.onKeyDown` with a fake Enter that includes **`persist: () => {}`** —
  without it you get `e.persist is not a function`.
- **React menu items**: synthetic pointer sequences open the menu, but items need
  `__reactProps.onClick` invoked with a fake event (persist, preventDefault, stopPropagation,
  isDefaultPrevented, isPropagationStopped all stubbed).
- **Angular row menus** (source-query Edit/Rename/Make Primary/Delete) ignore full pointer
  sequences erratically: plain-`.click()` the `a.dropdown-toggle`, then plain-click the item by
  `data-test-id`. A primary query's menu has no Delete — demote first.
- **Gear-menu items do not respond to synthetic events at all** — the menu opens
  programmatically, but selecting an item needs a real click.
- **`prompt()` is blocked in the embed.**
- **Standalone merge saves create orphan mids.** Once a merge is bound to a tile, only ever edit
  it at `/embed/merge/edit?did=<n>&dbnx=1`.
- **The merge editor's Save is bottom-right, not in the header, and is disabled until dirty.** A
  disabled Save and a missing Save look identical if you only scan the header. If it stays grey
  after real edits, append an underscore to the title to force the dirty state, then rename back.
- **Explore→merge conversion carries the explore's table calcs INSIDE Q1**, not at merge level:
  they render as columns but have no Edit/Delete at merge level and evaluate in Q1's field
  context, so removing a Q1 field they reference errors them all (re-Run does not fix it). Delete
  them in Q1's inner dialog and re-add at merge level.
- **Hard-reload (`location.reload(true)`) after any save** before trusting what a tile renders.
  Soft reload and cache-clear are not always sufficient.
