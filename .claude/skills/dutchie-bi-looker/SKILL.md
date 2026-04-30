---
name: dutchie-bi-looker
description: Edit Looker tiles and merge queries embedded in Dutchie Backoffice (leaflogix.looker.com) — table calc syntax, Ace editor automation via Playwright, signed embed token navigation, dashboard column/sort cleanup, save flow. Use when Adam needs to add or modify a metric, calc, or column on any dashboard tile in Dutchie Backoffice → BI tools.
---

<!-- Generated from "freed-solutions/skills/dutchie-bi-looker/SKILL.md". Edit the repo skill source and rerun ops/notion-workspace/scripts/sync-claude-skill-wrappers.ps1; do not edit this Claude copy directly. -->

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

### Tile-bound vs standalone merge editor

- **Tile-bound** (`/embed/merge/edit?did=<merge_id>&dbnx=1`): outer Save commits the new mid to the tile binding on the dashboard. **Use this.**
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
- `match(string, regex)` — **returns Number** (1-based position, 0/null no-match), NOT YesNo despite docs. To use as boolean: `match(...) > 0`. For category-membership checks, prefer `${cat}="x" OR ${cat}="y"`.

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

### Delete a custom calc

Click the calc's column dropdown → "Delete". No confirmation dialog. Calc is gone from the merge query immediately. **Verify** no other calcs reference the deleted one before pulling the trigger.

### Set a sort

Click the column header's sort button (NOT the dropdown). Single click on a numeric column defaults to DESC (right behavior for "show me biggest first"). Click again to flip ASC. Replaces any existing sort (single-sort behavior); use `Shift+Enter` for multi-sort.

When auto-binding adds an unwanted dim that becomes the sort key (e.g., adding Product Size auto-creates a Size DESC sort), explicitly click the intended sort column to replace the sort, then hide the unwanted column.

## Known Gotchas

### Adding a dim auto-creates merge rules across same-view source queries

Adding `products.product_size` to Q1 auto-creates a Q1.size = Q3.size merge rule when Q3 also has the products view. Usually desirable. The flip side: it can also auto-set sort on the new dim, which is rarely what you want.

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
| Buyers_3 merge (Brand granularity) | did=185905 |
| Buyers_2 merge (Product Type granularity) | did=185926 |
| Chelsea legacy "Reorder of Inventory Sold" | did=185826 (preserved, untouched) |
| Buyers_3 merge editor URL | https://leaflogix.looker.com/embed/merge/edit?did=185905&dbnx=1 |
| Buyers_2 merge editor URL | https://leaflogix.looker.com/embed/merge/edit?did=185926&dbnx=1 |

Merge mids rotate every save — don't memorize. Look up current mid via "Edit Merged Query" or read the dashboard YAML if needed.

## House Style Notes

- Calc names use Title Case with spaces ("Daily Avg Sales", "Operating Days In Stock"), not snake_case. They display as-is in column headers.
- Hide internal helper calcs (denominators, intermediate sums) from the tile — surface only buyer-actionable columns.
- Buyer's procurement workflow sorts by **OTB-21 DESC** (highest projected reorder first). Default to that for any new buyer-facing tile.
- Multi-step merge edits: Save calc → Run → Save outer → Hard-reload parent. Don't skip the hard reload; tile cache lag is real.

## References

- Memory files (load when relevant):
  - `feedback_looker_table_calc_syntax.md` — full operator + function cheat sheet
  - `feedback_looker_merge_field_refs.md` — `${view.field}` vs `${q1.field}` syntax
  - `feedback_looker_ace_editor.md` — Ace overlay click blocking, focus + pressSequentially workaround
  - `feedback_looker_tile_cache_lag.md` — `location.reload(true)` to bust dashboard render cache
- Notion handoff for the HSCG procurement work: page id `25fd87c4566243918266315d5935177a` ("[Replaces HB] Reorder & Velocity (Days-In-Stock methodology) — AI Handoff").
- GS source-of-truth Sales sheet (still drives downstream): `1LUCoMf3Cw-2O89gJfo2NEPo4WkrXHi85UPJhWkQDVJI`, `inventory` tab — `salesGroup` and `salesGroupBrand` formulas at R1/S1.
