---
name: dutchie-bi-looker
description: Edit Looker tiles and merge queries embedded in Dutchie Backoffice (leaflogix.looker.com) — table calc syntax, Ace editor automation via Playwright, signed embed token navigation, dashboard column/sort cleanup, save flow. Use when Adam needs to add or modify a metric, calc, or column on any dashboard tile in Dutchie Backoffice → BI tools.
---

# Dutchie BI Looker

Work on Looker dashboards embedded inside Dutchie Backoffice (`omega.backoffice.dutchie.com` → BI tools → iframe to `leaflogix.looker.com`). Cover the merge-query editor, table calculations, dashboard tile bindings, and the Playwright automation patterns that survive cross-origin iframes and Ace editor quirks. Source of truth for the procurement tiles (Buyers_2, Buyers_3) on dashboard 26549.

## When to Use

- Adam asks to add, edit, or fix a metric on any Looker tile in Dutchie Backoffice.
- A merge query needs a new dimension, custom measure, or table calculation.
- A buyer-facing dashboard needs column-visibility or sort cleanup (hide internal helpers, surface the right priority sort).
- A formula error ("Expression incomplete", "Unknown function 'X'", "Field does not exist") shows up in a Looker calc.

## When NOT to Use

- Native Dutchie reports (Sales, Inventory, Closing — non-Looker tabs in Backoffice). Different system entirely.
- Building new LookML at the Dutchie/Looker schema level — out of scope (model is read-only from Adam's seat).
- Google Sheets formula work — see `google-sheets-patterns`.

## Inputs

- **Target tile / merge query** (required): dashboard ID + tile name OR merge query did. Dashboard 26549 hosts Buyers_2 (did=185926) and Buyers_3 (did=185905); Chelsea's legacy "Reorder of Inventory Sold" tile is did=185826 (preserved untouched).
- **Change description** (required): concrete enough to map to a calc, dim, or column ("rebase Daily Avg Sales on operating days", "hide Product Size column", "swap sort to OTB-21 DESC").
- **Dutchie login** (required at session start): Adam logs in to Backoffice manually; the embed cookie is then good for ~24h.

## Embedded Architecture

```
omega.backoffice.dutchie.com/reports/bi-tools/<page>
        │
        ▼
   <iframe src="https://leaflogix.looker.com/login/embed/<signed-path>?nonce=...&time=...">
        │  (302 redirect to /embed/<actual-path>, cookie set)
        ▼
   <iframe src="https://leaflogix.looker.com/embed/<path>">
```

- The `/login/embed/` URL carries a signed nonce + timestamp scoped to the path it was issued for; you can't swap `dashboards/1151` → `dashboards/26549` in the signed URL.
- Once the cookie is set, `iframe.src = "https://leaflogix.looker.com/embed/dashboards/26549"` (or `/embed/merge/edit?did=...`) navigates within the session without re-signing. This is how you reach custom dashboards that aren't in Backoffice's BI-tools sidebar.

### Login + iframe navigation (Playwright)

1. Navigate to `https://omega.backoffice.dutchie.com/reports/bi-tools/explore` (or any BI-tools page that signs an embed). Wait for sign-in.
2. Once Adam confirms login, the iframe contains a `leaflogix.looker.com/login/embed/...` URL — embed cookie is now set.
3. Mutate iframe src to the real target:
   ```js
   document.querySelector('iframe[src*="leaflogix.looker.com"]').src =
     'https://leaflogix.looker.com/embed/merge/edit?did=185905&dbnx=1';
   ```
4. Wait 12–15s for the Looker app to render in the iframe.

### Creating a new merge query

Merge queries are **created from an Explore**, not from a dashboard. The entry point is the
gear icon labelled **"Explore actions"**, above the fold in the page header immediately to
the right of Run / Auto Run → **"Merge results"**.

That opens the **Merged Results** backend view — a standalone builder at
`https://leaflogix.looker.com/embed/merge` showing `Source Queries` / `Add Query` /
`MERGE RULES` / `Visualization` / `Data`. **This backend view is the preferred surface to
work in**: it is the same view you return to for later edits, so building here matches how
the query will be maintained.

The bare URL renders the builder directly, which is the fastest way in:

```
https://leaflogix.looker.com/embed/merge
```

Caveats worth knowing before relying on it:

- Appending `?qid=<explore_qid>` does **not** seed the first source query — the builder
  still opens empty ("Add a query to get started"). Use the gear → Merge results path when
  you want the current explore query carried in as Q1, or add queries manually via
  `Add Query`.
- The gear menu items **do not respond to synthetic events** — not `.click()`, and not a
  full `pointerdown`/`mousedown`/`mouseup`/`click` sequence. The menu opens fine
  programmatically, but selecting "Merge results" requires a real click (Playwright, or the
  browser pane displayed so `computer` can composite). Same class of problem as the field
  picker's `onKeyDown` requirement.
- Locate the gear by matching `aria-label` / `title` / text against `Explore actions` —
  it carries no stable `data-testid`.

Once the merge is saved and bound to a dashboard tile, **stop using the standalone URL** and
switch to the tile-bound editor below; further standalone saves create orphan mids.

### Committing merge edits to a tile — the binding rule

**A `did` in the URL is not a binding.** Opening `/embed/merge/edit?did=<n>&dbnx=1` directly
gives a fully working editor — you can add calcs, run, sort, and see correct results — but
there is **no Save control anywhere on the page**. The header holds only Run and a gear, and
that gear offers just `Save to Dashboard...` / `Clear Cache & Refresh` / `Clear Merge`.
`Save to Dashboard...` opens the *Add to a Dashboard* dialog with Title `New Tile`, i.e. it
would create a **second tile**, not update the one you are editing. Everything done in that
session is lost on navigation.

Merge edits only commit when the editor is opened **from a dashboard already in edit mode**:

1. Open the dashboard → `Dashboard actions` → **Edit dashboard**.
2. On the tile → `Tile actions` → **Edit Merged Query**.
3. Make the changes, Run to verify.
4. Return and **Save the dashboard**.

### Making Save appear (dirty-state workaround)

Looker only enables the dashboard Save control once it considers the dashboard *dirty*, and
merge-query edits alone may not mark it dirty — leaving finished work with no way to commit.

**Fix: make a trivial edit to the dashboard title** (e.g. append an underscore) while in edit
mode. That marks the dashboard dirty and the Save option appears. Save, then rename the title
back if you want it clean.

This is the difference between losing an hour of calc-building and keeping it. Apply it any
time you have unsaved merge work and no visible Save.

### Tile-bound vs standalone merge editor

- **Tile-bound** (`/embed/merge/edit?did=<merge_id>&dbnx=1`): read/verify only unless reached
  via dashboard edit mode — see the binding rule above.
- **Standalone "Explore from here"** (`/embed/merge?mid=<some_mid>`): saves create orphan mids not bound to any tile. **Avoid.** This is a recurring footgun.
- "Edit Merged Query" from a tile's hover-menu in Edit-mode dashboard view also lands on the tile-bound URL.

## Core Workflow: Edit a Table Calculation

1. Open the merge editor at `did=<X>` (see iframe-navigation above).
2. Find the column header for the target calc. Click its dropdown (`Toggle Dropdown` button in the column header) → "Edit calculation".
3. The Edit dialog opens. The Expression textarea is an Ace editor — **direct clicks on it are blocked by the `.ace_content` overlay**. Workaround:
   ```js
   // Focus via Playwright frame-aware evaluate
   element.focus()  // on the textarea ref directly
   ```
   Then `Ctrl+A` + `Delete` to clear, then type.
4. **For short formulas (<200 chars)**: `pressSequentially` (slowly:true) — works reliably with Ace's key handlers.
5. **For long formulas (>~1000 chars)**: `pressSequentially` times out (default 5s). Use `fill()` (slowly:false) for bulk paste — Ace's textarea binding accepts the value, then a single trailing keystroke (e.g., extra `)`) triggers reparse. **Verify resulting formula** in the snapshot before saving — fill mode + Ace can leave a missing/extra paren if the original wasn't fully cleared.
6. Click the dialog's Save button. Dialog closes.
7. Click outer Run. Verify rows render correctly (look for null cells, ERROR cells, or wrong-type warnings).
8. Click outer Save. This commits the new mid and rebinds the dashboard tile.

### Save flow recap

| Action | Effect |
|---|---|
| Calc dialog Save | Updates calc in current draft of merge query (in-memory) |
| Outer merge Run | Re-executes query, refreshes Data table |
| Outer merge Save | Creates new mid, rebinds dashboard tile, returns to dashboard view |
| Dashboard outer Save | Often unnecessary — the merge Save commits the binding |

### Cache-bust after save

Dashboard tile sometimes renders stale data even after merge Save. **Hard reload** the parent page:
```js
location.reload(true)
```
Soft reload + Clear cache + refresh aren't always sufficient. See `feedback_looker_tile_cache_lag.md`.

## Looker Lexp Cheat Sheet (Table Calculations)

Verified by direct probing — Looker docs are occasionally wrong. See `feedback_looker_table_calc_syntax.md` for the full annotated list.

**Operators**
- Equality: `=`. Inequality: `!=`. **Not** `<>` (parses but rejects with "Expression incomplete").
- Boolean: `AND`, `OR`, `NOT` as **uppercase infix**: `${a}="x" OR ${a}="y"`. Not `or(...)` function form. Not `||` / `&&`.
- Comparison: `<`, `>`, `<=`, `>=` work normally.

**Functions confirmed available**
- `if(yesno, true_val, false_val)` — both branches MUST return same type. String/Number mix → "Argument types for the Yes and No cases must match". Push concat outside the if to flatten.
- `concat(...)` — auto-casts numbers to strings.
- `round(num, decimals)` — both args required; standard rounding (23 × 6 / 7 = 19.71 → round to 0 decimals = 20).
- `coalesce(value, fallback)` — null fallback.
- `replace(string, find, replacement)` — literal find/replace (no regex).
- `to_number(string)` — parse string to number; returns null on parse failure.
- `match(string, pattern)` — **treat as unusable.** Probed directly against a product name
  containing the literal text `(SAMPLE)`: `match(name,"(?i)sample|test")` returned null, and
  so did SQL-style `match(name,"%SAMPLE%")`. Neither regex nor LIKE syntax matches anything.
  Do not build flags on it — the calc saves and runs, it just silently never fires.

  **Substring test that works**, using only verified functions:

  ```
  if(replace(${field}, "needle", "") != ${field}, 1, 0)
  ```

  If removing the needle changes the string, the string contained it. **Case-sensitive**, so
  enumerate the casings that actually occur — real catalog data had both `(Sample)` and
  `(SAMPLE)`, and testing one variant alone missed five rows. Chain with `OR`:

  ```
  if(replace(${n},"(SAMPLE)","")!=${n} OR replace(${n},"(Sample)","")!=${n}, "SAMPLE; ", "")
  ```

  For category-membership checks, still prefer `${cat}="x" OR ${cat}="y"`.

**Functions NOT available**
- `format(value, fmt)` — Excel-style formatting NOT in table calc. Use a workaround (see "Trailing-zero pad" pattern below).
- `regex_replace(string, regex, replacement)` — use `replace()` with literal find/replace.
- `day_of_week(date)`, `extract_day_of_week(date)` — neither exposed in Lexp; the LookML `dimension_group` for snapshot_date doesn't expose `snapshot_day_of_week` either. See "Sunday-exclusion methodology" below for the workaround.

**Field naming**
- LookML field names may differ from display labels. "Products Product Size" displays as such but the actual reference is `${products.Product_Size}` (capitalized) in the Dutchie/leaflogix model.
- Discover the correct name via Angular controller on a column header in the merge editor:
  ```js
  angular.element(thElement).scope().col.field.name
  ```
- Merge-level field references: `${view.field_name}` (e.g. `${products.brand_name}`), NOT source-query alias `${q1.field}`. Calcs reference each other by bare name: `${daily_avg_sales}`. See `feedback_looker_merge_field_refs.md`.

## Dosage Encoding — check the business rules before profiling

`products.product_grams` is the **universal dosage field**, and for mg-dosed categories the
milligram value is stored **as grams**:

| Label | Stored `product_grams` |
|---|---|
| 5mg / 10mg / 25mg / 50mg / 100mg | 0.005 / 0.01 / 0.025 / 0.05 / 0.1 |
| 1.0g / 2.0g / 3.5g / 7.0g | 1 / 2 / 3.5 / 7 |

So `mg = product_grams × 1000`. A 100mg 20-pack edible stores `0.1`.

```
if(<mg category>, concat(round(${products.product_grams}*1000, 0), "mg"),
                  concat(round(${products.product_grams}, 2), "g"))
```

Two traps this avoids:

- **`products.thccontent` is not the dose.** In some tenants it is unpopulated entirely; where
  it does hold a value it is the *lab-tested* THC figure, not the label dosage. Profiling it
  as the mg source produces a false "100% of the catalog is missing dosage" finding.
- **`products.Product_Size` is only populated for multipacks.** Null means single unit, which
  matches the taxonomy rule that singles never take the `(x Npk)` parenthetical. A null-rate
  around 90% is *expected*, not a defect. The real check is "populated but unparseable", plus
  a dosage that implies a multipack with no pack count to explain it.

**Read the client's Product Line business rules before profiling their master data.** Getting
this backwards produces confident, wrong findings about data quality. The pack/dosage
conventions live with the product-line maintenance workflow, not in the BI tooling.

## Common Patterns

### Trailing-zero pad ("0.0#" format substitute)

`format()` doesn't exist. To render integers as "X.0g" while keeping decimals as-is ("X.5g"):

```
if(round(${grams}, 2) = round(${grams}, 0),
   concat(round(${grams}, 0), ".0"),
   concat("", round(${grams}, 2)))
```

The `concat("", ...)` wrap forces String type to match the if-true branch. Both branches now return String — type-check passes.

### Per-pack-grams annotation (multi-pack products)

Buyers_3 Product Line shows `Pre-Rolls | 2.5g (0.5g x 5pk) | Happy Valley` for multi-pack products. Pattern:

```
if(coalesce(${products.Product_Size}, "") != "" 
   AND to_number(replace(${products.Product_Size}, "pk", "")) > 0,
   concat(${products.category}, " | ",
          <total_grams_padded>,
          "g (", <per_pack_grams_padded>, "g x ", ${products.Product_Size}, ") | ",
          ${products.brand_name}),
   <fallback to plain "(Npk)" annotation>)
```

`pack_count = to_number(replace(${products.Product_Size}, "pk", ""))` parses "5pk" → 5. The `>0` guard prevents division-by-zero on malformed Product_Size (returns null from to_number → falls back to plain `(Npk)` format).

### Sunday-exclusion methodology

HSCG (and similar single-store retailers) may be closed Sundays while the Inventory Snapshot writes a row every calendar day. Days In Stock then over-counts by the # of Sundays in the window — inflating the Daily Avg Sales denominator and understating procurement signals (OTB-21) by ~1/7.

Looker can't filter by day-of-week (no `day_of_week()`, no LookML sub-timeframe exposed). Workaround: a proportional Operating Days calc.

```
Operating Days In Stock = round(${days_in_stock} * 6 / 7, 0)
Daily Avg Sales = if(${operating_days_in_stock} > 0, 
                     ${transaction_items.total_quantity} / ${operating_days_in_stock}, 
                     null)
Days Stocked Without Sale = if(${operating_days_in_stock} - ${count_of_transaction_date} > 0,
                              ${operating_days_in_stock} - ${count_of_transaction_date},
                              0)
```

Why proportional (6/7) not subtract-4: the `-4` shortcut is correct for full-28-day windows but breaks for partial windows (new launches, recent restocks). A product in stock 4 days returns operating=0 → null Daily Avg Sales → row hidden. Proportional degrades gracefully: 28 days → 24, 21 days → 18, 14 days → 12, 7 days → 6, 1 day → 1.

When the store re-opens Sundays, revert by editing Operating Days In Stock to just `${days_in_stock}` (or delete the calc and inline `/ ${days_in_stock}` in Daily Avg Sales).

## Dashboard Tile Cleanup

### Hide a column from visualization

Click the column header dropdown → "Hide this field from visualization". Persists through outer Save. The column stays in the row schema but isn't rendered on the tile.

**Hidden state inherits across tile duplication** — when you Duplicate tile in dashboard editor, the new (Copy) tile preserves all column hide settings AND sort state from the source. So if Buyers_1 has Inventory Snapshot Sum Total Quantity + Operating Days In Stock hidden + OTB-21 DESC sorted, a Buyers_X clone of Buyers_1 inherits all three. Phase 5 work (column hiding + sort) on a clone is usually just hiding the new dim column (the one you swapped to) — everything else carries over.

**Scripted detection of hidden state**: open the column dropdown and read menu items:
- `'Hide this field from visualization'` → currently visible
- `'Show this field in visualization'` → currently hidden

This is more reliable than trying to detect the column header's hidden state from DOM attributes.

### Delete a custom calc

Click the calc's column dropdown → "Delete". No confirmation dialog. Calc is gone from the merge query immediately. **Verify** no other calcs reference the deleted one before pulling the trigger.

### Set a sort

Click the column header's sort button (NOT the dropdown). Single click on a numeric column defaults to DESC (right behavior for "show me biggest first"). Click again to flip ASC. Replaces any existing sort (single-sort behavior); use `Shift+Enter` for multi-sort.

When auto-binding adds an unwanted dim that becomes the sort key (e.g., adding Product Size auto-creates a Size DESC sort), explicitly click the intended sort column to replace the sort, then hide the unwanted column.

## What Is and Isn't Scriptable

Looker's embed UI mixes Angular and React, and the automation approach differs per control.
Verified by direct probing; check here before assuming a click "doesn't work".

| Control | Technique |
|---|---|
| Explore picker in merge builder (`a[lk-track-action="Explore"]`) | plain `.click()` (Angular `ng-click`) |
| View-group expand/collapse in field tree | plain `.click()` |
| Field **selection** in field tree | synthetic React `onKeyDown` Enter (see below) |
| Filter **field** picker (`button[role="treeitem"]`) | plain `.click()` |
| Filter value — string | native value setter + `input` event, then Enter to commit the chip |
| Filter value — yesno | click input, then `.click()` the `li[role="option"]` |
| Filter value — date | click the expression input → `li` "is in the last" → set number → unit dropdown |
| Column sort | `.click()` on `div.sorting[role="button"]` inside the `th` — **not** the `Toggle Dropdown` button |
| Delete a calc | column `Toggle Dropdown` → `[role="menuitem"]` "Delete" |
| Calc expression textarea | native `HTMLTextAreaElement` value setter + `input` event |
| **Explore-actions gear menu items** | ❌ needs a real user click |
| **`New Dashboard` button** | ❌ needs a real user click |
| **`Edit Merged Query` tile menu item** | ❌ needs a real user click |
| **Row Limit / dashboard Title inputs** | ❌ `execCommand` only, and only with genuine user focus |

### The user-activation rule

`document.execCommand('insertText', …)` **works only when the element already has genuine
user focus.** A programmatic `.focus()` does not grant user activation, so the value is set
and then reverted by the next Angular `$digest` — which looks like "the input rejects
scripting" but is really a missing activation. Once a human has clicked into the field, the
exact same code sticks.

Practical division of labour: ask the user to click into the field, then script the typing.
For Row Limit specifically, `ngModel.$setViewValue()` also updates the model but is still
reverted on re-render — don't trust it.

### Long calc expressions

SKILL's older advice to switch to `fill()` past ~1,000 chars is unnecessary with the
value-setter approach: a **1,127-character** expression saved cleanly, no truncation and no
paren damage. Set the textarea value directly and dispatch `input`.

### Reusable calc helper

```js
window.__addCalc = async function(name, expr) {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  Array.from(document.querySelectorAll('button,[role="button"],a'))
    .find(x => /Add calculation/i.test(x.textContent||'')).click();
  await sleep(3500);
  const dlg = document.querySelector('[role="dialog"],.modal');
  const ta = dlg.querySelector('textarea');
  const nameInp = Array.from(dlg.querySelectorAll('input'))
    .find(i => i.placeholder === 'Create a custom field name');
  const taSet = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set;
  const inSet = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;
  ta.focus();      taSet.call(ta, expr);   ta.dispatchEvent(new Event('input',{bubbles:true}));
  await sleep(2000);
  nameInp.focus(); inSet.call(nameInp, name); nameInp.dispatchEvent(new Event('input',{bubbles:true}));
  await sleep(1800);
  Array.from(dlg.querySelectorAll('button')).find(b => b.textContent.trim()==='Save').click();
  await sleep(4500);
  return !document.querySelector('[role="dialog"],.modal');
};
```

### `prompt()` is blocked in the embed

Looker's **New Dashboard** button calls `window.prompt()` for the name. The embed context
blocks it, so the button silently does nothing — for scripted *and* human clicks alike. The
console shows:

```
Error: prompt() is not supported.  at x.createNewDashboard
```

Polyfill before clicking:

```js
window.prompt = () => 'Your Dashboard Name';
```

Saving to an **existing** dashboard never hits this. Note the button is also disabled until
the tile Title field is non-default, so set Title first — a disabled button and a
`prompt()`-blocked one both look like "nothing happened".

## Known Gotchas

### Gram-weighted measures for cross-grain comparability

At Category or Master Category grain, **unit counts mix products of different gram weights** (1g pre-rolls + 0.5g pre-rolls counted as 2 units, but only 1.5g actual product). This makes velocity / DoH / OTB-21 misleading at coarser grains. Switch to gram-weighted measures.

The Dutchie / leaflogix model exposes built-in `sum(quantity × per-unit grams)` measures — no custom measure needed:

| Source query | Field | Type | Use |
|---|---|---|---|
| Q1 (Transactions) | `transaction_items.total_product_grams` | sum | Sales numerator |
| Q2 (Inventory) | `inventory.total_product_grams` | sum | Current inventory |
| Q3 (Inventory Snapshot) | `inventory_snapshot.sum_total_product_grams` | sum | NOT NEEDED (Q3 only contributes `days_in_stock` to the calcs; the snapshot grams field has weird semantics — values way off vs Q1/Q2 ratios — so don't use it) |

**Avoid `products.total_product_grams`** — it's `sum_distinct(products.product_grams)`, which sums grams across distinct catalog products in the result set (NOT weighted by quantity sold/inventoried). For Pre-Rolls in HSCG it returned 80g vs the correct 2,023g from `transaction_items.total_product_grams` — a 25× discrepancy.

**Calc rewrites for grain ≤ Category** (when switching from unit-based to gram-based):

| Calc | Unit-based (wrong at Category grain) | Gram-based (correct) |
|---|---|---|
| Daily Avg Sales | `${transaction_items.total_quantity} / ${operating_days_in_stock}` | `${transaction_items.total_product_grams} / ${operating_days_in_stock}` |
| Days On Hand | `coalesce(${inventory.total_quantity}, 0) / ${daily_avg_sales}` | `coalesce(${inventory.total_product_grams}, 0) / ${daily_avg_sales}` |
| OTB-21 | `... 21 * ${daily_avg_sales} - coalesce(${inventory.total_quantity}, 0) ...` | `... 21 * ${daily_avg_sales} - coalesce(${inventory.total_product_grams}, 0) ...` |

Keep the unit measures visible too (Total Quantity, Inventory Total Quantity) as reference columns — buyers want to see units alongside the gram-based math.

**When NOT to use gram-weighted**: any tile where Product Grams is already a dim (Buyers_2 Cat+Grams, Buyers_3 Brand+Cat+Grams+Size, Buyers_4 SKU). Each row already has consistent per-unit grams, so unit-based math is meaningful.

### Adding a Custom Measure / dim selection via Playwright (cross-origin React)

The field-picker treeitems in the source-query inner editor (loaded as same-origin iframe `editQueryDialogId1`) **do NOT respond to `.click()` or synthetic mouse events** — Looker uses React `onKeyDown` for selection toggle.

Working pattern:
```js
const treeitems = doc.querySelectorAll('[role="treeitem"]');
for (const ti of treeitems) {
  if (ti.textContent.replace(/\s+/g, ' ').trim() === '<Field Label>') {
    const propsKey = Object.keys(ti).find(k => k.startsWith('__reactProps'));
    const props = ti[propsKey];
    const fakeEvent = {
      key: 'Enter', code: 'Enter', keyCode: 13, charCode: 13,
      target: ti, currentTarget: ti,
      preventDefault: () => {}, stopPropagation: () => {},
      nativeEvent: {key: 'Enter', code: 'Enter', keyCode: 13}
    };
    props.onKeyDown(fakeEvent);
    break;
  }
}
// aria-pressed flips false ↔ true to confirm selection state
```

To **inspect** a field's underlying LookML metadata (name, type, view, sql, description) — useful to disambiguate same-labeled fields (e.g., two "Total Product Grams" entries):
```js
function findField(node, depth=0) {
  if (!node || depth > 30) return null;
  if (node.props?.field?.name) return node.props.field;
  if (Array.isArray(node)) {
    for (const c of node) { const r = findField(c, depth+1); if (r) return r; }
    return null;
  }
  if (node.props?.children) return findField(node.props.children, depth+1);
  return null;
}
const propsKey = Object.keys(treeitem).find(k => k.startsWith('__reactProps'));
const field = findField(treeitem[propsKey].children, 0);
// field.name, field.type ('sum' / 'sum_distinct' / 'count'), field.view, field.label
```

Use this to verify before adding — `sum_distinct` ≠ `sum`, and the same-labeled field can have different semantics across views (see `Inventory.X vs Products.X` gotcha below).

**Renaming a dashboard tile title** — React rejects synthetic `onChange` events on the title input (state immediately reverts). Workaround: real keyboard via `Ctrl+A` + `Delete` to clear, then `document.execCommand('insertText', false, 'New Title')`. Both the keyboard select+clear AND the execCommand insert produce events React's controlled input accepts:
```js
// 1. Focus the existing title input (.value contains old title)
const i = Array.from(document.querySelectorAll('input[type="text"]')).find(x => x.value.includes('(Copy)'));
i.focus(); i.select();
// 2. Press Ctrl+A then Delete via Playwright keyboard (NOT synthetic events)
// 3. Then in evaluate:
document.execCommand('insertText', false, 'New Title');
// 4. Tab/Enter to commit; click dashboard Save
```
Why execCommand and not direct value setter: React's controlled inputs reject value mutations from outside React's onChange flow. execCommand is a real DOM operation that fires a real `beforeinput` + `input` event sequence.

**Discovering a duplicated tile's merge did** — when you "Duplicate tile" in dashboard edit mode, the new tile's element_id IS the new merge did. Find it via `data-testid="dashboard-tile-title"` H2's `id` attribute (`element-title-NNNNNN` → did = NNNNNN). Then navigate `/embed/merge/edit?did=NNNNNN&dbnx=1` directly — the duplicate creates a NEW merge query, not a shared reference. Saving inner queries / outer merge updates only the new mid bound to the (Copy) tile, not the original.

**Editing a calc's expression** — set value on the React-bound `<textarea>` (not the Ace `.ace_content` div) and dispatch `input`. Ace re-renders from the textarea automatically:
```js
const ta = doc.querySelector('[role="dialog"] textarea');
ta.focus();
const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
setter.call(ta, '<new formula>');
ta.dispatchEvent(new Event('input', {bubbles: true}));
// Then click dialog Save button
```

### Same-named field on different views can have different semantics (CRITICAL)

The Inventory and Products views both expose a field called `Product Grams`, but they mean **different things**:
- `Products.Product Grams` = per-unit grams of a product (1.0g pre-roll, 3.5g flower) — the value space sales data uses
- `Inventory.Product Grams` = some other LookML-derived metric (observed values 119, 50, 120, 117, 100, 86 — likely package weight or similar)

If Q1 (Sales) uses `Products.Product_Grams` and Q2 (Inventory) uses `Inventory.Product_Grams`, the merge rule `Q1.products.product_grams = Q2.inventory.product_grams` joins on **incompatible value spaces** — almost nothing matches. Symptom: most merge rows show `Empty Value` for inventory measures, OR a single dramatically-low number (whatever inventory row happened to have a matching value).

**Always prefer `Products.X` fields in Q2 (Inventory) when the products view is joined into the Inventory explore in LookML** (it usually is). The dim swap is: open Q2 inner editor → Field Picker → search the field name → click `Products > X` to add → click `Inventory > X` to deselect. Looker auto-rewrites the merge rule.

Real example: Buyers_2 Q2 originally used `Inventory.Product_Grams`. Pre-Rolls 1g showed Inventory Total Quantity=1 (one accidental match across the whole HSCG inventory). After swapping to `Products.Product_Grams`: 2,068 units (the actual sum across all brands).

Same warning applies for Brand Name, Size, Category — verify they reference `Products.X` not `Inventory.X` if the merge fails to populate. Category is often safe (values match across views) but Brand Name can have casing mismatches ("Wyld" vs "WYLD") and Size can have format mismatches ("5pk" vs "5").

### Adding a dim auto-creates merge rules across same-view source queries

Adding `products.product_size` to Q1 auto-creates a Q1.size = Q3.size merge rule when Q3 also has the products view. Usually desirable. The flip side: it can also auto-set sort on the new dim, which is rarely what you want.

### Swapping dims breaks merge rules — sometimes silently

When you replace a shared dim across source queries (e.g., deselect `products.category` and select `products.product_name` in Q1, Q2, and Q3), Looker handles it inconsistently:
- **Q1↔Q3 (sometimes)**: auto-rewrites the merge rule from Category=Category → Product Name=Product Name. ✓
- **Q1↔Q2 (often)**: drops the merge rule entirely. The merge then becomes a Cartesian product (each Q1 row × each Q2 row), and the table shows duplicate dim columns side-by-side ("Products Product Name" twice in headers). Symptom in the data: same SKU appears in N rows pairing with every other SKU's Q2 measure.

**Fix**: scroll to the merge rules section — the broken Q1↔Q2 line shows a `+ Add merge rule for Inventory` link. Clicking it auto-creates the missing Product Name = Product Name rule. Re-Run; the table should now show one Product Name column with correctly joined values.

**Detection in scripted workflows**: after dim swaps, scan `body.innerText` for the `MERGE RULES` section. If it contains `+ Add merge rule for` text, a rule is missing. Also check the table headers — duplicate column names (same field appearing 2× or 3×) indicates Cartesian merge.

### Cloning Buyers_X for a new grain

Workflow that worked end-to-end (Buyers_0 from Buyers_1, Buyers_4 from Buyers_1):
1. Adam manually duplicates the source tile via dashboard editor → Tile actions → Duplicate tile, then saves the dashboard. (Scripted Duplicate tile clicks were unreliable.)
2. Find the new tile's merge did via `h2[data-testid="dashboard-tile-title"]` element id (`element-title-NNNNNN` → did = NNNNNN).
3. Navigate `/embed/merge/edit?did=NNNNNN&dbnx=1` directly.
4. Q1: deselect old grain dim, select new grain dim (use the React `onKeyDown` Enter trick), Save inner.
5. Q2: same, paying attention to Inventory.X vs Products.X (prefer Products.X). Save inner.
6. Q3: same. Save inner.
7. Verify merge rules in the rendered text — if any `+ Add merge rule for X` appears, click it to add the missing rule.
8. Edit Product Line calc to `concat("", ${products.<new_dim>})`. Save calc.
9. Run, verify, Save outer.
10. In dashboard editor, click tile title → `Ctrl+A` + `Delete` + `document.execCommand('insertText', false, 'New Title')` to rename. Tab to commit. Save dashboard.

**Cloning gram-weighted Buyers_1 vs unit-based Buyers_3**: Buyers_1 is the cleaner template (1 dim only → 1 merge rule per join). Buyers_3 has 4 dims (Brand+Cat+Grams+Size) → 4 merge rules per join, all of which need cleanup when narrowing to a single SKU dim. Even with rules deleted, the inherited gram-weighted calcs from Buyers_1 still produce correct procurement signals at finer grains (each SKU has consistent grams, so units and grams sort identically).

### Outer Run sometimes returns transient empty calcs

After Q1/Q2/Q3 source-query changes, the first outer Run may show calc columns as Empty Value. Run again — usually recovers on second attempt.

### Field schema lag after structural changes

After adding a dim or measure to a source query, calcs in the outer merge may say "Field X does not exist in current query" until you click Run once. Don't panic; Run, then re-edit the calc.

### Beforeunload "Leave site?" dialog after merge save

When merge Save commits but the dashboard tile is still in edit mode, navigating away triggers a "Leave site?" dialog. Cancel out, hard-reload the page, then verify the tile reflects the saved state.

### Standalone editor saves create orphan mids

"Explore from here" on a tile opens `/embed/merge?mid=...` (no `did`). Saves there create a NEW mid not bound to any tile — orphan. Always use the tile-bound editor (`/embed/merge/edit?did=...`).

### Cross-origin iframe blocks direct JS access

`iframe.contentDocument` access from the parent throws SecurityError. Use Playwright's `contentFrame()` API for all iframe-internal operations. Direct JS only works for setting `iframe.src` (the property setter is allowed cross-origin).

## Workflow: Common Tasks

### Add a new merge-level table calc

1. Open tile-bound merge editor (`did=<X>`).
2. In the Data tab, click "Add calculation".
3. Fill in name, expression. Use the autocomplete (type `${`) to verify field references — Ace's autocomplete shows the actual `${view.field_name}` form.
4. Save calc dialog. Run. Save outer.
5. Hard-reload parent page (`location.reload(true)`).

### Modify an existing calc's formula

1. Open tile-bound merge editor.
2. Column dropdown on the target calc → "Edit calculation".
3. Focus the expression textarea (cross-origin requires Playwright `evaluate` with `el.focus()`).
4. `Ctrl+A`, `Delete`, type new formula (`pressSequentially` for short, `fill` for long).
5. Verify expression in snapshot before saving — Looker says "Expression incomplete" if syntax is malformed. Add missing parens at end if needed.
6. Save calc dialog. Run. Save outer.

### Add an LSP / store filter to a source query

1. Open the source query inner editor (Q1/Q2/Q3 in the merge).
2. Add filter row: Lsp Name is "<store name>" (or whatever filter dim).
3. Save inner query → returns to outer merge.
4. Run outer twice (first Run sometimes blanks calcs).
5. Save outer.

### Verify a formula change post-save

1. Re-open the calc's Edit dialog and confirm the expression matches what you expected.
2. Sample a few rows in the Run output — for the proportional Sunday formula, verify days=28 gives ops=24 AND a partial-window row (e.g., days=23) gives ops=20 (round(23×6/7) = 20).
3. Hard-reload the parent dashboard page and re-verify on the tile-rendered values.

## Reference IDs (HSCG / Dashboard 26549)

These are stable; treat as canonical.

| Resource | ID |
|---|---|
| Dashboard | 26549 |
| Buyers_3 merge (Brand granularity, units) | did=185905 |
| Buyers_2 merge (Product Type / Cat+Grams, units) | did=185926 |
| Buyers_1 merge (Category, **gram-weighted** as of 2026-05-09) | did=186802 |
| Buyers_0 merge (Master Category, **gram-weighted** as of 2026-05-09) | did=186807 |
| Buyers_4 merge (SKU / Product Name, **gram-weighted** as of 2026-05-09) | did=186810 |
| Chelsea legacy "Reorder of Inventory Sold" | did=185826 (preserved, untouched) |
| Buyers_3 merge editor URL | https://leaflogix.looker.com/embed/merge/edit?did=185905&dbnx=1 |
| Buyers_2 merge editor URL | https://leaflogix.looker.com/embed/merge/edit?did=185926&dbnx=1 |
| Buyers_1 merge editor URL | https://leaflogix.looker.com/embed/merge/edit?did=186802&dbnx=1 |
| Buyers_0 merge editor URL | https://leaflogix.looker.com/embed/merge/edit?did=186807&dbnx=1 |
| Buyers_4 merge editor URL | https://leaflogix.looker.com/embed/merge/edit?did=186810&dbnx=1 |

Merge mids rotate every save — don't memorize. Look up current mid via "Edit Merged Query" or read the dashboard YAML if needed.

## House Style Notes

- Calc names use Title Case with spaces ("Daily Avg Sales", "Operating Days In Stock"), not snake_case. They display as-is in column headers.
- Hide internal helper calcs (denominators, intermediate sums) from the tile — surface only buyer-actionable columns.
- Buyer's procurement workflow sorts by **OTB-21 DESC** (highest projected reorder first). Default to that for any new buyer-facing tile.
- Multi-step merge edits: Save calc → Run → Save outer → Hard-reload parent. Don't skip the hard reload; tile cache lag is real.

## References

- `references/explore-field-catalog.md` — **read before writing any Looker query.** Opens
  with the mandatory filter set: the instance is **multi-tenant**, so every query needs
  `lsp_location.lsp_name` pinned to one tenant (omitting it blends clients and produces
  plausible-looking wrong numbers), plus `is_sandbox = No` and `transactions.is_void = No`
  on sales-side queries. Then: every explore, view, and LookML field name in the
  `sql_server` model; the LookML-name-vs-display-label traps (Cultivation is `plant`,
  Purchase Orders is `purchase_order`); a recipes table mapping questions to explores; the
  top-level embed escape (skip the iframe entirely by opening `leaflogix.looker.com/embed/...`
  in a plain tab once the Backoffice cookie is set); driving queries by URL params; and the
  hidden-iframe + `window`-parked-async pattern for automation that outlives the 30s tool
  timeout.
- Memory files (load when relevant):
  - `feedback_looker_table_calc_syntax.md` — full operator + function cheat sheet
  - `feedback_looker_merge_field_refs.md` — `${view.field}` vs `${q1.field}` syntax
  - `feedback_looker_ace_editor.md` — Ace overlay click blocking, focus + pressSequentially workaround
  - `feedback_looker_tile_cache_lag.md` — `location.reload(true)` to bust dashboard render cache
- Notion handoff for the HSCG procurement work: page id `25fd87c4566243918266315d5935177a` ("[Replaces HB] Reorder & Velocity (Days-In-Stock methodology) — AI Handoff").
- GS source-of-truth Sales sheet (still drives downstream): `1LUCoMf3Cw-2O89gJfo2NEPo4WkrXHi85UPJhWkQDVJI`, `inventory` tab — `salesGroup` and `salesGroupBrand` formulas at R1/S1.
