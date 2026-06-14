# DMC Sales Velocity Analysis — Briefing for ChatGPT

> Upload this file into your ChatGPT project as a reference document. It captures the business context, data structure, methodology, and edge cases for DMC's sales-by-product-line analysis so ChatGPT can help you execute the workflow end to end.

## Who we are

- **Company:** DMC (Massachusetts cannabis manufacturer and distributor).
- **Primary ERP / source of truth for sales:** Apex.
- **Secondary sales system:** Dutchie (point of sale, e-commerce, BI).
- **Goal of this analysis:** Produce sales by product line over time (weekly or monthly), so DMC can understand velocity, commercialization, and stockout patterns. Today's work is an interim workaround; the permanent infrastructure will come out of the Michael & McCumber (M&M) discovery project.

## The core problem

Apex does not have a native "product line" attribute. Product line is encoded inside the item name via pipe delimiters. The analysis therefore depends on:

1. Parsing the product line out of the item name.
2. Aggregating sales by that derived product line and by week (or month).
3. Correctly handling zeros — distinguishing "we were in stock and didn't sell" (good zero) from "we were stocked out" (bad zero).
4. Detecting commercialization date so the velocity denominator is fair for newer product lines.

## Apex naming convention

Apex item names use pipe characters (`|`) as segment delimiters. Product line is **every segment except the last one** (the last segment is strain/flavor; a units-per-case tag may trail that).

Examples of shapes that appear in the data:

- Two-segment items: `Product Line | Strain/Flavor` → product line is segment 1.
- Three-segment items (sub-brand present): `Brand | Product Line | Strain/Flavor` → product line is segments 1–2.
- Multi-pack variants: extra size notation (e.g. `0.3g`) appended — still strip the final strain/flavor segment.
- Vape hardware and a handful of newer items have inconsistent naming and will need to be flagged as exceptions.

The important rule: **product line = everything up to and including the second-to-last pipe segment.** The final segment (plus any units-per-case tag) is stripped off.

## Recommended workflow (Google Sheets + AI)

1. **Export sales data from Apex as CSV.** The export is roughly 48 columns; you only need product name, quantity/units sold, and date for this analysis.
2. **Paste into a new Google Sheet.** (Paste-values works fine.)
3. **Add a `product_line` column in column A** (to the left of the existing data). Use a single-cell array formula, not a dragged-down formula, so the column stays in sync automatically when data is refreshed.
4. **Ask Claude or ChatGPT for the array formula.** Tell it:
   - You are working in Google Sheets.
   - Your item names live in column B (adjust to match your layout).
   - You want a single array formula that lives in cell A1, outputs a header label (`product_line`) in A1 and the parsed product line for every row in A2 through the end of B.
   - The parse rule is: strip everything from the final pipe onward, trim whitespace, and return the remaining string.
   - Some rows may have odd naming (vape hardware, recent additions); return the item name unchanged when the parse rule cannot find a pipe.
5. **Freeze the top row** (`View → Freeze → 1 row`) and highlight A1 yellow as a reminder that a formula lives there.
6. **Pivot (or hand to AI) for aggregation.** Either:
   - Select the full data range, insert a pivot table, rows = product_line, columns = week (or month), values = sum of units sold.
   - Or paste the data into ChatGPT/Claude and ask for a weekly sales-by-product-line table.

## The shape of data you actually need

For real velocity analysis, the pivoted output needs **two values per time bucket, not one**:

| product_line | Week 1 Sales | Week 1 Inventory | Week 2 Sales | Week 2 Inventory | ... |
| --- | --- | --- | --- | --- | --- |
| Pre-Roll 1g | ... | ... | ... | ... | ... |

- **Sales** comes from Apex (or Dutchie) sales history.
- **Inventory on hand** is the piece that's harder to get — Apex does not snapshot inventory historically.

### Handling "good zero" vs "bad zero"

- **Good zero:** sales = 0 AND inventory on hand > some threshold (e.g. 10 units). We had it on the menu, it just didn't sell. This *should* drag velocity down.
- **Bad zero:** sales = 0 AND inventory on hand = 0 (or below threshold). We were stocked out. This should **not** count against velocity — exclude the week from the denominator.

### Denominator rules for velocity

Velocity = total units sold over period ÷ weeks-in-stock-and-commercialized.

- Denominator starts at the **first week the product line appears in the sales data** (commercialization date).
- Denominator excludes weeks flagged as stockouts (bad zeros).
- Denominator runs through the last week of the period.

Example: 52-week lookback, product line first shows up in week 10, stocked out in weeks 20 and 21, analysis runs through week 52. Denominator = 52 − 10 − 2 = 40 weeks.

## Getting inventory snapshots — options ranked

You do not have historical point-in-time inventory in Apex today. Options:

1. **Dutchie BI inventory snapshots (best).** Dutchie takes a nightly inventory snapshot you can query by day/week. Requires matching Dutchie SKUs back to Apex items. If you want this, work with Adam — he can help build the report and the SKU match, though you'd be pulling snapshots individually per period and joining by room.
2. **Start snapshotting Apex manually going forward.** Export the Apex all-inventory report daily or weekly, stamp it with the date, and stack them. You won't recover history, but you'll build a snapshot series from today forward. Trivial to automate later.
3. **Stockout heuristic (acceptable as an interim).** If a product line has zero sales for **N consecutive weeks** (you pick the threshold — 2 to 4 weeks is a reasonable starting point), treat those weeks as stockouts and drop them from the denominator. This will misclassify slow movers occasionally, but it's usable without any inventory data.

**For now,** option 3 is the fastest path to answers. Validate a handful of known stockout periods against the heuristic before trusting the output.

## Commercialization detection nuance

- The first week a product line appears in the data is treated as the commercialization date.
- Caveat: if a product was stocked out for the first few weeks of the lookback window, the heuristic will misdate commercialization to the first week it actually sold. Don't lookback too far — name conventions also shifted historically, which will confuse the parser.
- Suggested lookback: **26 weeks (6 months)** or **52 weeks (12 months)**. Start with 26 and expand only if the dataset is clean.

## Specific prompts to give ChatGPT

After uploading this document, try prompts like:

1. **Parsing:**
   > "Write a single Google Sheets array formula that lives in cell A1. It outputs the header 'product_line' and parses each row of column B by stripping everything from the final pipe character onward. Trim whitespace. If a row has no pipe, return the original value."

2. **Aggregation:**
   > "Here is my parsed sales data (pasted table). Aggregate units sold by product_line and by ISO week. Return a pivot where rows are product_line and columns are week_year. Include a total column."

3. **Velocity with stockout heuristic:**
   > "Using the pivoted weekly sales above, calculate weekly sales velocity per product line. Treat the first non-zero week as the commercialization week. Treat any run of 3 or more consecutive zero-sales weeks as stockouts and exclude those weeks from the denominator. Output: product_line, total_units, in_stock_weeks, velocity_units_per_week, commercialization_week."

4. **Sanity checks:**
   > "Flag any product lines where (a) the commercialization week is in the last 4 weeks (too new to be reliable), (b) the stockout-adjusted denominator is under 4 weeks, or (c) more than 50% of the weeks were classified as stockouts. These rows need manual review."

## Known limitations and exceptions

- **Vape hardware items** and a handful of newer SKUs have messy naming. Expect the parser to return odd values for them — review the bottom of the unique-values list manually.
- **Sub-brand items** (Todd Dan's Gold Leaf, Dime co-manufactured lines, etc.) may have three-segment names; the parser still works but sub-brand handling is worth spot-checking.
- **Apex vs Dutchie match:** if you want to layer inventory data, matching happens on SKU, not name. Don't try to join on item name.
- **Apex export doesn't include SKU by default** in some report templates — make sure the export you use includes the SKU column if you plan to cross-reference Dutchie later.

## Long-term direction (context for ChatGPT, not for action)

- DMC is moving master data cleanup and reporting toward Wherefore + Dutchie. Apex will not be the source of truth forever.
- Dutchie Brand Connect is rolling out; DMC is a candidate to publish digital assets, e-commerce descriptions, and discounts out to the 70% of MA retailers on Dutchie.
- The M&M discovery project (Michael & McCumber) will deliver dynamic sales dashboards and permanent infrastructure. This Google Sheets + AI workflow is explicitly interim.

---

_Document prepared by Adam Freed (Freed Solutions) from the Apr 17, 2026 DMC Sales Data working session with John Hanmer._
