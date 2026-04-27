---
name: google-sheets-patterns
description: Build maintainable, column-reorder-safe Google Sheets using Adam's house patterns — dynamic QUERY with helper rows, dynamic VLOOKUP via array construction, header-row spilling formulas, and Apps Script conventions for seed/deploy functions. Use when designing or refactoring formulas in any Sheet Adam owns, especially multi-tab planners like Camp Cleetus.
---

# Google Sheets Patterns

Adam's house style for Sheets that survive column moves, stay readable at the top of each tab, and keep their Apps Script deploys idempotent. Use this skill when writing or reworking formulas in any Sheet Adam maintains.

## When to Use

- Designing a new tab where downstream formulas reference specific columns by name.
- Refactoring hardcoded `QUERY("SELECT A, B, C...")` or `VLOOKUP(..., 3, 0)` calls that break when columns are reordered.
- Writing Apps Script deploy functions to seed or update a sheet's formulas.
- Diagnosing a sheet that silently returns wrong data after a column move.

## Core Patterns

### 1. Dynamic QUERY with helper row

**Problem.** `QUERY('Source'!A:Z, "SELECT A, C, E WHERE D IS NOT NULL")` hardcodes letters. Moving column C to column M silently points the SELECT at the new C, which is now something else.

**Pattern.** Add one hidden row on the source tab holding each column's current letter. QUERY concatenates those cells instead of hardcoding.

**Setup on the source tab:**

1. Insert one row above the header row (grouped + hidden so users don't see it).
2. Put a single spilling ARRAYFORMULA at `A<helperRow>`:
   ```
   =ARRAYFORMULA(SUBSTITUTE(ADDRESS(1, COLUMN(<helperRow>:<helperRow>), 4), "1", ""))
   ```
   `COLUMN(<row>:<row>)` returns `{1,2,3,...}` across every column in the tab — no hardcoded bumper. ADDRESS + SUBSTITUTE turns each column number into its letter. Each cell in the helper row now shows its own column letter ("A", "B", "C", ...).
3. If true headers were at row 1, they're now at row 2 after the insert. Add a second "notes" row above the helper if you want editorial space — bumps headers to row 3.

**Rewrite QUERY formulas to concatenate:**

Before:
```
=IFERROR(QUERY('Source'!A:E, "SELECT A, B, C WHERE E IS NOT NULL", 1), "")
```

After (helper row = row 1, headers = row 2):
```
=IFERROR(QUERY('Source'!A2:E,
  "SELECT " & 'Source'!A1 & ", " & 'Source'!B1 & ", " & 'Source'!C1 &
  " WHERE " & 'Source'!E1 & " IS NOT NULL",
  1), "")
```

Key changes:
- Source range shifts from `A:E` to `A<headerRow>:E` so the helper row isn't treated as data.
- Each column letter in SELECT/WHERE/ORDER BY is replaced with `& 'Source'!<cell> &`.

**Move behavior.** When a user moves a column in Sheets via cut + paste or drag, Sheets moves the helper cell with it *and* updates cross-sheet references that point to that cell. The concatenated SELECT resolves to the new letter automatically.

**What doesn't need special handling.** `IS NOT NULL`, `<> ''`, `<> TRUE`, `ORDER BY <col>` — all string-comparable, plain substitution works. Only numeric literals, date literals in WHERE clauses (e.g., `WHERE E > date '2026-06-02'`), or aggregate calls (`SUM(C)`) might need extra care — QUERY's literal-typing rules apply the same way after substitution.

### 2. Dynamic VLOOKUP via array construction

**Problem.** `VLOOKUP(key, Source!A:Z, 3, 0)` hardcodes the return column index. If columns move, the wrong value returns.

**Pattern.** Build a 2-column array `{key_col, value_col}` on the fly, always VLOOKUP into column 2.

```
=VLOOKUP(
  key,
  {'Source'!A:A, 'Source'!<value_col>:<value_col>},
  2, 0
)
```

Where `<value_col>` is a cell reference whose value is a column letter (e.g., the dynamic helper above) — or an `INDEX('Source'!A:ZZ, 0, MATCH("Header", 'Source'!$2:$2, 0))` expression that resolves the right column by header name.

For returning *multiple* columns in one lookup, wrap with `HSTACK` or construct a 3+ column array. For header-aware lookup without a helper row, `INDEX/MATCH` is usually cleaner than VLOOKUP.

### 3. Header-row spilling formulas

**Pattern.** Put the formula once at the top of its column, spill data down. Avoid per-cell formulas in every row — they're expensive to maintain and easy to break when rows are added.

```
={"Column Name"; ARRAYFORMULA(IF(A2:A="","", <expression over A2:A>))}
```

Or, when ARRAYFORMULA can't iterate (LAMBDA closures, COUNTIFS with array criteria, etc.):

```
={"Column Name"; MAP(A2:A, LAMBDA(x, IF(x="","", <expr on x>)))}
```

Live examples from Camp Cleetus (`🛏 Rooms`):
- `F1` (Claimed): `={"Claimed"; ARRAYFORMULA(IF(E2:E="","", COUNTIF('👫 Campers'!G:G, E2:E)))}`
- `G1` (Beds Free): `={"Beds Free"; ARRAYFORMULA(IF(E2:E="","", C2:C - COUNTIF('👫 Campers'!G:G, E2:E)))}`

Place the formula in the header cell using the `={"header"; ...}` array literal — row 1 becomes the static label, row 2 onwards becomes the spill.

### 4. Per-cell vs. spill trade-offs

Spilling formulas are cleaner but break in specific situations. When they do, fall back to per-cell formulas written by Apps Script.

| Situation | Use |
|---|---|
| Pure arithmetic / lookup per row | Spill with ARRAYFORMULA |
| LAMBDA iteration over rows | Spill with MAP |
| LAMBDA iteration over *dates* captured in closure | **Per-cell** — LAMBDA-date closure bug silently returns wrong values |
| COUNTIFS with array criteria inside a LAMBDA | **Per-cell** — ARRAYFORMULA-COUNTIFS broadcast fails inside LAMBDA |
| Distinct-household count inside a LAMBDA | Use `COUNTUNIQUEIFS`, not `SUMPRODUCT(1/COUNTIFS(...))` |
| TEXT() on an array inside a nested LAMBDA | Wrap with ARRAYFORMULA or BYCOL per iteration |

See `## Known Gotchas` below for details.

### 5. Apps Script seed/deploy conventions

Deploy functions in this project follow a common shape:

- **Single purpose per function**: one function per feature (e.g., `applyRoomCapacityLogic_v1`, `patchAA2Formula_v1`, `applyDynamicQueries_v1`).
- **Versioned**: bump the trailing `_v1` → `_v2` when the implementation changes meaningfully.
- **Idempotent guards**: check a sentinel cell at the top (e.g., "is the 'Shared' header already present?"). Return no-op on re-run.
- **Sentinel header checks**: `if (String(sh.getRange('B2').getValue()).trim() !== 'Name') throw new Error(...)` before touching data.
- **Targeted writes only**: no `clearContents()` on ranges you don't own. No mass overwrites.
- **SpreadsheetApp.flush()** at the end to force materialization.
- **Logger.log** each step: "Step 1: ...", "Step 2: ..." — visible in Apps Script execution log.
- **Run via function picker** — picker at the top of the editor can be finicky; fall back to injecting a one-line call inside `fixFormulas_v2` (or similar default function), save, click Run, then revert. Pattern:
  ```
  function fixFormulas_v2() {
    applyNewThing_v1();  // <-- temporary hack
    return;              // <-- short-circuit
    /* original body unchanged */
  }
  ```

### 6. Row grouping and hiding via Apps Script

```js
// Insert + group a helper row at top (programmatic alternative to the UI).
sh.insertRowBefore(1);
sh.getRange("1:1").shiftRowGroupDepth(1);
sh.collapseAllRowGroups();
```

Or create the group with explicit indices:
```js
var group = sh.getRowGroup(1, 1);
if (!group) sh.getRange("1:1").shiftRowGroupDepth(1);
sh.getRowGroup(1, 1).collapse();
```

Users can still toggle visibility via the `+/−` gutter icons on the left.

## Known Gotchas

Each is a real bug that bit this project. Check memory folder for the longer write-ups.

### LAMBDA + FILTER + captured date scalars silently don't iterate

Inside `MAP(dates, LAMBDA(d, FILTER(..., criterion_using_d)))`, the captured `d` doesn't vary per iteration in some nested patterns. First-date values leak across all cells.

**Workaround**: unroll to literal array of static per-date FILTER calls. For per-row formulas, write 8 hardcoded COUNTIFS (one per trip date) instead of iterating.

### `TEXT(array, fmt)` silently reduces to scalar

`TEXT(dateArray, "M/D")` without `ARRAYFORMULA` wrap returns only the first element. No error — just wrong.

**Workaround**: `ARRAYFORMULA(TEXT(dates, "M/D"))`, or push the TEXT inside the iteration lambda.

### `SUMPRODUCT(1/COUNTIFS(range, range, ...))` errors inside LAMBDA

Classic distinct-count trick fails silently with `#ERROR!` when LAMBDA captures scalars used as COUNTIFS criteria.

**Workaround**: use `COUNTUNIQUEIFS(range, crit_range, crit, ...)` — native, scalar-safe, composes cleanly with LAMBDA.

### QUERY source that starts at the helper row

If the helper row contains letters ("A", "B", ...) and QUERY source is `A:E` with `headers=1`, QUERY treats the letters as headers in output. Users see "A", "B", "C" instead of "Household", "Name", etc.

**Workaround**: shift source range to skip the helper row: `'Source'!A<headerRow>:E`.

### Inserting rows breaks formula references unless Sheets auto-shifts

When inserting a row above existing data, Sheets usually updates cross-sheet references (`Source!A1` → `Source!A2`). But be wary of:
- Named ranges anchored to cells (may or may not shift).
- Apps Script that writes literal cell refs (won't re-shift until the script runs again).
- Conditional format rules (verify the range is still correct post-insert).

**Workaround**: after any row insert, re-run any deploy functions that set formulas/validations, and verify critical conditional format rules by hand.

### Banding on non-header rows when inserting above

Banding often starts at row 2 (data). Inserting a helper row above row 1 shifts data to row 3 but banding still starts at row 2 — the new row 2 (previously headers) gets alternating background color instead of the styled header look.

**Workaround**: after row insert, either re-apply banding or manually re-format row 2. Grouping the helper row hides the visual issue most of the time.

### Apps Script hardcoded row offsets break after user row-inserts

Deploy functions often hardcode ranges like `sh.getRange('A2:A200')` or `getRange(2, 7, 198, 1)` assuming data starts at row 2. When a user inserts a helper/notes row above, data moves to row 3 or 4 — but the hardcoded offsets don't shift. Functions then read helper-row text or header-row labels as "data" and write garbage.

**Detect:** any function that does `getRange(N, ...)` with literal row numbers. Audit after any structural row change.

**Workaround:** pass the data-start row as a parameter or compute dynamically from a sentinel cell (`if (B2 !== 'Name') throw`). Re-run the deploy function after row inserts.

### Cross-sheet cell refs shift when rows inserted, but formula values stored in Apps Script don't

If Campers row 1 had helper letters and Finance!A11 referenced `Campers!A1`, inserting a row above Campers row 1 correctly updates the Finance formula to `Campers!A2`. But if the Apps Script's stored source string still says `Campers!A1`, the next deploy overwrites the live formula back to the broken ref.

**Workaround:** after any row insert, either re-run the deploy function (so Apps Script re-reads the new source string with the right literal) or update the source string to match. Prefer the former.

### Column reorder breaks formulas that reference absolute letters

Moving a column in Sheets (cut-paste or drag) updates cross-sheet references that point at the *moved cell*, but formulas that still reference the *old position* (e.g., `E3:E` when Label moved from E to H) now point at whatever column E is now — often Notes or something unrelated. Symptoms: `#REF!` errors, or silent wrong-column selection in QUERY.

**Diagnosis:** scan all formulas on other tabs for references to the moved source tab (`rg "SourceTabName"`). Check which formulas still point at positions no longer holding the intended content.

**Workaround:** commit to a canonical layout and enforce via a restore function that rewrites headers + formulas to their intended columns. See `applyRoomsLayout_v5` in the Camp Cleetus Code.gs for an example — clears the wrecked range, rewrites all spilling formulas at known positions.

## Workflow: Add Dynamic QUERY to an Existing Sheet

1. **Inventory.** Run an Apps Script that scans all tabs for `QUERY(`:
   ```js
   ss.getSheets().forEach(sh => {
     var f = sh.getRange(1,1,sh.getLastRow(),sh.getLastColumn()).getFormulas();
     f.forEach((row, r) => row.forEach((cell, c) => {
       if (cell && /\bQUERY\s*\(/i.test(cell)) Logger.log(sh.getName()+'!'+sh.getRange(r+1,c+1).getA1Notation()+': '+cell);
     }));
   });
   ```
   Enumerate every source-tab → consumer-cell mapping.

2. **Insert helper row(s)** at row 1 of each source tab. If you want editorial notes above helpers, insert two rows; otherwise just one. Group + hide.

3. **Populate helpers** with the bumper-less ARRAYFORMULA:
   ```
   =ARRAYFORMULA(SUBSTITUTE(ADDRESS(1, COLUMN(<helperRow>:<helperRow>), 4), "1", ""))
   ```

4. **Rewrite QUERIES**. Shift source ranges to skip helper rows. Replace hardcoded letters with `& <source>!<helper_cell> &`. Apply via Apps Script for reproducibility.

5. **Verify**. Check each consumer cell's output. Watch for:
   - `#REF!` (spill blocked — usually a column collision)
   - `#VALUE!` (string concatenation produced malformed SQL)
   - Wrong rows ordered differently (`ORDER BY` might resolve to a different column than intended)

6. **Test column move**. Pick one column on a source tab, cut-paste to a different position. Confirm the consumer cells update automatically. Undo.

## Forms Integration

Pattern: dynamic Google Forms driven by sheet headers, with name-based append to the main tab.

### Architecture

```
 Google Form (Submit)
        │
        ▼
 Hidden response tab  (archive, auto-populated by Forms)
        │
        ▼ onFormSubmit trigger
        ▼
 Main tab  (manual entries + form-appended entries)
```

- **Hidden `_<Tab> Form` tab** holds the raw form-response archive (1 row per submission, Timestamp + each question as a column). Sheet is auto-created by `FormApp.setDestination()`.
- **Main tab** (`💰 Expenses`, `🧺 Groceries`, etc.) is the source of truth for data entry. Users add rows manually; form submissions also append here via trigger.
- **Question titles match main-tab header names exactly.** This is the contract that makes name-based mapping work.

### Dynamic form build (Sheet → Form)

```js
function syncFormQuestions_(form, cfg) {
  var headers = main.getRange(cfg.headerRow, 1, 1, main.getLastColumn())
    .getValues()[0].filter(Boolean).map(String);

  // Index existing items by title
  var byTitle = {};
  form.getItems().forEach(it => byTitle[it.getTitle()] = it);

  // Incremental sync — preserve question IDs where possible
  headers.forEach(h => {
    var expected = expectedTypeForHeader_(h);
    var it = byTitle[h];
    if (it && String(it.getType()) === expected) return;  // keep
    if (it) form.deleteItem(it);                           // retype → delete + recreate
    addQuestionForHeader_(form, h);
  });

  // Delete items whose title is no longer a header
  var headerSet = new Set(headers);
  form.getItems().forEach(it => {
    if (!headerSet.has(it.getTitle())) form.deleteItem(it);
  });

  // Reorder to match header order
  headers.forEach((h, idx) => {
    var items = form.getItems();
    var cur = items.findIndex(x => x.getTitle() === h);
    if (cur !== -1 && cur !== idx) form.moveItem(cur, idx);
  });
}
```

Key discipline: **match by title, preserve IDs where possible**. Don't destroy + rebuild every sync — that thrashes the API, invalidates question IDs, and creates orphan columns in the response tab (see gotcha below).

### Header → question type inference

Use string contains (not regex — escaping in Apps Script template literals is fragile). Map:

| Header pattern | Type |
|---|---|
| matches `DROPDOWN_SOURCES` entry (e.g., "Paid By" → "adults") | `LIST` item, options from `_lists!<colname>` |
| `header === 'date'` or contains `' date'` / `'date '` or starts with `'date'` | `DATE` item |
| contains `notes` or `description` | `PARAGRAPH_TEXT` |
| contains `amount`, `cost`, `qty`, `quantity` | `TEXT` with number validation |
| else | `TEXT` |

Keep `DROPDOWN_SOURCES` in code:

```js
var DROPDOWN_SOURCES = {
  'paid by': 'adults',
  'buyer': 'adults',
  'type': 'expense_types',
  'applies to': 'expense_applies_to',
  'vendor': 'grocery_vendors',
  'purchased': 'grocery_purchased',
  'committee': 'committees'
};
```

### Dropdown options from `_lists`

```js
function getListOptions_(listHeaderName) {
  var lists = ss.getSheetByName('_lists');
  // _lists has headers at row 1, data from row 2+
  var headers = lists.getRange(1, 1, 1, lists.getLastColumn()).getValues()[0];
  var col = headers.indexOf(listHeaderName);
  if (col < 0) return [];
  return lists.getRange(2, col + 1, lists.getLastRow() - 1, 1)
    .getValues().map(r => r[0]).filter(v => v !== '' && v !== null).map(String);
}
```

### onFormSubmit: append to main tab by name

**Always include the hidden-tab fallback.** Form-bound triggers (`.forForm(form).onFormSubmit()`) do NOT populate `e.namedValues` — only spreadsheet-bound triggers (`.forSpreadsheet(ss).onFormSubmit()`) do. So a handler that does `if (!e.namedValues) return` will silently fail on every form-bound submission. The pattern below tries `e.namedValues` first (cheap + robust to retyped-item orphan columns when available) then falls back to reading the latest row from the hidden response tab.

```js
function onFormSubmit_Expense(e) { appendFormSubmission_(EXPENSE_FORM_CFG, e); }

function appendFormSubmission_(cfg, e) {
  var main = ss.getSheetByName(cfg.mainTab);
  var mainHeaders = main.getRange(cfg.headerRow, 1, 1, main.getLastColumn()).getValues()[0];
  var row;
  if (e && e.namedValues) {
    row = mainHeaders.map(h => {
      var v = e.namedValues[h];
      return (v && v[0] !== undefined) ? v[0] : '';
    });
  } else {
    // Fallback: read last row of hidden tab, match by header name (use lastIndexOf to pick newest column)
    var formTab = ss.getSheetByName(cfg.formTab);
    var submission = formTab.getRange(formTab.getLastRow(), 1, 1, formTab.getLastColumn()).getValues()[0];
    var formHeaders = formTab.getRange(1, 1, 1, formTab.getLastColumn()).getValues()[0];
    row = mainHeaders.map(h => {
      var idx = formHeaders.lastIndexOf(h);
      return idx >= 0 ? submission[idx] : '';
    });
  }
  main.appendRow(row);
}
```

### Installable triggers

```js
// Install onFormSubmit for a form
ScriptApp.newTrigger(handlerName).forForm(form).onFormSubmit().create();

// Install onEdit for header-row changes
ScriptApp.newTrigger('onEdit_HeaderSync').forSpreadsheet(ss).onEdit().create();

// Check before re-installing
var existing = ScriptApp.getProjectTriggers()
  .filter(t => t.getHandlerFunction() === handlerName);
if (!existing.length) { ... }
```

Installable triggers do NOT carry over when a sheet is copied (File → Make a copy). On a fresh copy, re-run the setup function to reinstall triggers.

### Persisting form IDs across runs

```js
var props = PropertiesService.getDocumentProperties();
props.setProperty('formId_' + cfg.mainTab, form.getId());
// On next run:
var id = props.getProperty('formId_' + cfg.mainTab);
var form = FormApp.openById(id);  // reuse existing form rather than creating new
```

Keyed by main-tab name so each form has its own remembered ID. Document properties survive across executions and copies of the sheet (one-off — re-running setup on a copy creates NEW forms bound to the copy).

### Multi-row-per-submission forms (1 form → N rows)

The Expense/Grocery pattern is **1 submission = 1 row**. For cases where one logical submission produces multiple rows (e.g., a household registering multiple campers), the architecture diverges:

- **Form structure is hand-built**, not header-driven. The form has fields like `Name 1`, `Name 2`, ..., `Name N` rather than mirroring the sheet's `Name` column.
- **Page breaks** separate per-entity sections so the form doesn't feel like a wall of fields.
- **First entity required, rest optional** — submitter fills only the slots they need.
- **`onFormSubmit` handler iterates 1..N**, builds one row per entity that has a value in its required field, batches all rows, writes once.

Camp Cleetus example: `setupCamperForm_v1()` builds:
- 1 shared section: Household, Arrival, Departure, Leaving From, Ride Seats
- 6 page-break sections: Camper N (Name + Kid?/Yes-No + Age + Drinks Alcohol?/Yes-No + Other Food Restriction)
- Camper 1 required; 2–6 optional

Skeleton:

```js
function buildMultiRowFormItems_(form) {
  form.getItems().forEach(it => form.deleteItem(it));

  // Shared section (header)
  form.addSectionHeaderItem().setTitle('Your Household');
  form.addTextItem().setTitle('Household').setRequired(true);
  form.addDateItem().setTitle('Arrival').setRequired(true);
  // ...

  // Per-entity sections
  for (var n = 1; n <= MAX_PER_SUBMISSION; n++) {
    form.addPageBreakItem()
      .setTitle('Camper ' + n + (n === 1 ? ' (required)' : ' (optional)'));
    form.addTextItem().setTitle('Name ' + n).setRequired(n === 1);
    form.addListItem().setTitle('Kid? ' + n).setChoiceValues(['Yes', 'No']);
    // ...
  }
}

function onFormSubmit_MultiRow(e) {
  // Build named-values map. forForm-bound triggers don't populate e.namedValues,
  // so fall back to reading the latest row from the hidden response tab.
  var nv = (e && e.namedValues) ? e.namedValues : null;
  if (!nv) {
    var formTab = ss.getSheetByName('_<Title> Form');
    if (!formTab || formTab.getLastRow() < 2) return;
    var lc = formTab.getLastColumn();
    var fHdrs = formTab.getRange(1, 1, 1, lc).getValues()[0];
    var fVals = formTab.getRange(formTab.getLastRow(), 1, 1, lc).getValues()[0];
    nv = {};
    for (var k = 0; k < fHdrs.length; k++) {
      if (fHdrs[k]) nv[String(fHdrs[k]).trim()] = [fVals[k]];
    }
  }
  function get(k) { var v = nv[k]; return (v && v[0] !== undefined) ? v[0] : ''; }
  function yn(v) { if (v === 'Yes') return true; if (v === 'No') return false; return v; }
  function parseDate(s) {
    if (!s) return ''; if (s instanceof Date) return s;
    var d = new Date(s); return isNaN(d.getTime()) ? s : d;
  }
  function parseNum(s) {
    if (s === '' || s == null) return '';
    var n = Number(s); return isNaN(n) ? s : n;
  }

  var shared = {
    'Household': get('Household'),
    'Arrival': parseDate(get('Arrival')),
    'Departure': parseDate(get('Departure'))
  };

  // Build all rows first; batch-write at the end
  var rows = [];
  for (var n = 1; n <= 6; n++) {
    var name = get('Name ' + n);
    if (!name) continue;
    var fields = Object.assign({}, shared, {
      'Name': name,
      'Kid': yn(get('Kid? ' + n)),
      'Age': parseNum(get('Age ' + n))
    });
    rows.push(headers.map(h => fields[h] !== undefined ? fields[h] : ''));
  }
  if (!rows.length) return;
  var startRow = findFirstEmptyDataRow_(mainSheet, dataStartRow);
  mainSheet.getRange(startRow, 1, rows.length, rows[0].length).setValues(rows);
}

function findFirstEmptyDataRow_(sh, dataStartRow) {
  // Scan column A from dataStartRow down for the first empty cell.
  // Avoids appending past validation-extended ranges (which inflate getLastRow()).
  var col = sh.getRange(dataStartRow, 1, Math.max(sh.getLastRow(), 200), 1).getValues();
  for (var i = 0; i < col.length; i++) {
    if (col[i][0] === '' || col[i][0] == null) return i + dataStartRow;
  }
  return col.length + dataStartRow;
}
```

Critical bits:
- **Type coercion is non-optional** when the main tab has data validation. `e.namedValues` always returns strings; cells with date/number/checkbox validation will reject string values like `"Tue Jun 02 2026..."`. Coerce with `parseDate`/`parseNum`/`yn` helpers.
- **Batch `setValues` over a sequential `appendRow` loop** — `getLastRow()` and column-scan reads can return stale values between writes within the same execution, causing duplicate-row clobbering. Build the 2D array, write once.
- **`findFirstEmptyDataRow_`, not `appendRow`** — `appendRow` appends past `getLastRow()`, which is inflated by validation/formatting on otherwise-empty rows. Scan column A explicitly.

### Form integration gotchas

- **FormApp ItemType enum stringifies cleanly.** `String(FormApp.ItemType.LIST) === 'LIST'` works — use this in type comparisons.
- **Retyped items leave orphan columns.** When you delete + recreate a form item (e.g., TEXT → LIST), Google Forms creates a NEW column in the response tab tied to the new item's ID. The old column stays, permanently empty. Append flows that read the hidden tab by header name will find the old empty column first. Use `e.namedValues` from the trigger event to avoid this entirely.
- **Regex escaping in Apps Script inserted via template literals is fragile.** I hit `\$` becoming `$` (end-of-string, matching everything) because the template literal ate the escape. Prefer `.toLowerCase().indexOf()` over regex for type-inference logic that lives inside a template-literal insertion.
- **First-run OAuth.** FormApp + DocumentProperties + installable triggers all require auth prompts on first execution. Click "Review permissions" and grant; subsequent runs work silently.
- **`renameResponseTab_`** — `form.setDestination()` creates a new tab named `<form title> (Responses)`. Immediately rename it (e.g., `_Expense Form`) for consistency. Then `sheet.hideSheet()` to tuck it away.
- **Programmatic `FormResponse.submit()` doesn't reliably fire installable `onFormSubmit` triggers.** Real form-UI submissions DO fire it; Apps-Script-driven submissions sometimes don't, especially right after a fresh trigger install. For automated end-to-end tests, manually invoke the handler with a synthetic `e.namedValues` (built from the latest hidden-tab row) instead of relying on the trigger to fire.
- **`e.namedValues` is empty for `.forForm(form)` triggers — only spreadsheet-bound triggers populate it.** A handler installed via `ScriptApp.newTrigger(name).forForm(form).onFormSubmit().create()` receives `e.values` (positional array) and `e.range`, but NOT `e.namedValues`. A guard like `if (!e || !e.namedValues) return;` will silently exit on every real submission. Either install via `forSpreadsheet(ss)` (fires for ALL forms attached, so handler must filter), or always include the hidden-tab fallback shown in the `appendFormSubmission_` pattern. **Symptom:** trigger fires (visible in Executions log as Completed), function exits in <1s, no rows appear in target tab, no Cloud log because Logger output is unavailable for triggers. **Diagnostic:** add a write to a spare cell at the very top of the handler (before the guard) — e.g., `ss.getSheetByName('_config').getRange('E2').setValue('FIRED ' + (e.namedValues ? 'WITH NV' : 'NO NV'));` — then submit and read the cell.
- **Form-trigger source ID = the form ID, not the spreadsheet ID.** When listing triggers via `ScriptApp.getProjectTriggers()`, `t.getTriggerSourceId()` returns the form's underlying ID for `.forForm()` triggers. Cross-reference with the form ID stored in `PropertiesService.getDocumentProperties()` (e.g., `formId_<mainTab>`). Note: the form ID and the published-form URL ID (`/forms/d/e/...`) are different; published IDs appear in `viewform`/`formResponse` URLs but the trigger source uses the underlying ID.
- **`appendRow` lands past `getLastRow()` which is inflated by data validation.** A Campers tab with checkbox validation extending to row 200 has `getLastRow() === 200` even when actual data ends at row 70 — `appendRow` then writes at row 201. Use the column-scan pattern above instead.
- **Shared cache between sequential `getValues`/`setValues` calls.** Within one execution, scanning column A → writing row N → scanning again can return the OLD value (showing N as still empty). Always batch writes in one `setValues` call when appending multiple rows.

## House Style Notes

- Tab names use a leading emoji: `🛏 Rooms`, `👫 Campers`, `🧺 Groceries`, `🛒 Procurement`, `🤑 Finance`. In Apps Script, reference with Unicode escapes: `'\u{1F6CF} Rooms'`.
- Informal column headers ("Household", "Name", not `household_id`, `camper_name`). Drop redundant FKs — "Name" in one tab maps to "Name" in another by human-readable match.
- `_config` tab (lowercase, underscore) for trip-level settings. Typical keys: `camp_year`, `trip_start`, `trip_end`, `n_nights`.
- `_lists` tab for dropdown source ranges and filtered views.
- Label columns like `Rooms!E = A & " - " & B` (concatenation for unambiguous key in dropdowns).
- Checkbox validation on boolean columns (Kid, Drinks Alcohol, Shared Space).

## Template: Deploy Function

```js
function applyFeature_v1() {
  var ss = SpreadsheetApp.getActive();
  var target = ss.getSheetByName('\u{1F4CB} Target');
  if (!target) throw new Error('Target tab missing');

  // Sentinel — avoid clobbering a renamed or rearranged tab
  if (String(target.getRange('A1').getValue()).trim() !== 'ExpectedHeader') {
    throw new Error('Sentinel failed: Target!A1 expected "ExpectedHeader"');
  }

  // Idempotent guard — bail if already applied
  if (String(target.getRange('Z1').getValue()).trim() === 'FeatureFlag') {
    Logger.log('applyFeature_v1: already applied. No-op.');
    return;
  }

  // 1. Do the thing
  target.getRange('B2').setFormula('=...');
  Logger.log('Step 1: B2 set');

  // 2. Mark deployment
  target.getRange('Z1').setValue('FeatureFlag').setFontWeight('bold');
  Logger.log('Step 2: flag set');

  SpreadsheetApp.flush();
  Logger.log('applyFeature_v1 complete.');
}
```

## References

- Live sheet: Camp Cleetus Master Planner (`1ZnUK6q5izSeSCp2eelhiAhkZpajN_qEqcSHHIOGP_QY`) — the test bed for every pattern in this skill.
- Memory files for bug details:
  - `feedback_sheets_text_array_scalar.md` — TEXT() scalar reduction
  - `feedback_sheets_lambda_iteration.md` — LAMBDA date closure
  - `feedback_sheets_sumproduct_countifs_lambda.md` — SUMPRODUCT + COUNTIFS distinct-count failure
  - `feedback_dynamic_query_pattern.md` — dynamic spilling QUERY preference
