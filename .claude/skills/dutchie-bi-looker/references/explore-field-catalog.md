<!-- Generated from "freed-solutions/skills/dutchie-bi-looker/references/explore-field-catalog.md". Edit the repo skill source and rerun ops/notion-workspace/scripts/sync-claude-skill-wrappers.ps1; do not edit this Claude copy directly. -->

# Dutchie / leaflogix Looker — Explore & Field Catalog

> **Curated subset — the COMPLETE list is `explore-field-index.md` beside this file** (generated
> 2026-09-04 from a full internal-API harvest: 19 explores, 3,469 fields, 37 views; refreshed under
> the `bi-change` `sync` path, never hand-edited). This file keeps the mandatory filters, the
> recipes and the semantics; the index answers "does the field exist, on which explore, from
> which view, what type". Before proposing a leg on an attribute no live tile reads, grep the
> index — three sessions built on fields that did not exist (Servings 9/1, Flavor 9/3). The
> 8/28 deltas that used to sit here (`inventory_historical`, `weekly_transactions`, `products`,
> the `transaction_items` ↔ `inventory` join) are all in the index.

Model: `sql_server`. Captured by enumerating each explore's field picker via React props
(see "Harvesting the catalog" below). Field names are **LookML names**, which frequently
differ from the display labels — always reference the LookML name in `${...}`.

Embed URL form: `https://leaflogix.looker.com/embed/explore/sql_server/<explore_name>`

---

## Mandatory filters — read this before writing any query

These are not optional hygiene. Omitting them does not raise an error; it silently returns
wrong numbers that look plausible.

### 1. `lsp_location.lsp_name` — the instance is MULTI-TENANT

**More than one organisation's data lives in this same Looker model**, and a single embed
session can read across them. An unfiltered query silently blends them into one result set.
Enumerate `lsp_location.lsp_name` at the start of any engagement to see which tenants are
visible from the current seat.

This is the single easiest way to produce a confidently wrong analysis, because the failure
mode is *plausible-looking data* rather than an error. Worked example:

Grouping `products.master_category` without the tenant filter appears to show a badly
fragmented taxonomy — `Preroll` sitting alongside `Pre-Rolls`, `Vape Carts` alongside
`Vaporizer`, `Concentrates` alongside `Concentrate`, `Accessories` alongside `Accessory`.
It reads exactly like a master-data quality problem worth escalating.

It is not. Each spelling in those pairs belongs to a *different tenant*, and each tenant is
internally consistent with itself. The "fragmentation" was entirely an artifact of the
missing filter. Retail cannabis tenants tend to pick different plural/singular conventions
for the same concepts, so this specific trap will recur on any multi-tenant instance.

The scale distortion is equally severe — in the observed case the unfiltered catalog was
roughly **7.5× larger** than the single-tenant catalog. Any count, mix, velocity, or
days-of-supply figure computed without this filter is meaningless.

**Always filter `lsp_location.lsp_name` to exactly one tenant.** If a number looks
surprising — an unfamiliar category label, an implausible SKU count — check this filter
before forming any conclusion or reporting a finding.

Note `lsp_id` in the embed user attributes may list several ids (e.g. `"1132, 1852"`),
which is what permits the cross-tenant read in the first place. A single `logged_in_lsp_id`
does **not** constrain what a query returns.

### 2. `lsp_location.is_sandbox = No`

Excludes test/sandbox LSPs. Neither current tenant has sandbox rows today, so this filter
changes nothing right now — apply it anyway. It is cheap, and it fails safe if a sandbox
LSP is ever provisioned.

### 3. `transactions.is_void = No` — on every sales-side query

`transaction_items` joins voided transactions by default. Void rows are typically a very
small share of volume — in one observed 90-day single-tenant window, voided items were
under 0.02% of line items and returns under 0.15%. The aggregate size is not the point:

Negligible for a revenue total. **Decisive for any boolean signal.** A catalog-QC or
dead-stock tool asking "did this SKU sell in the last 365 days?" will mark a SKU as active
off a single voided transaction. Same hazard for "first sold" / "last sold" dates, new-item
detection, and assortment-breadth counts.

The void share is client-dependent — verify per tenant rather than assuming it stays small.

### 4. `transaction_items.was_returned` — decide explicitly

Returns are a separate flag from voids. Both `was_returned` and
`was_returned_yes_cash_returned` exist. Netting returns out is right for velocity and
sell-through; leaving them in is right for gross-demand questions. Either is defensible —
choose deliberately and state which, rather than inheriting the default.

### Baseline filter set

```
lsp_location.lsp_name   is  <exactly one tenant>
lsp_location.is_sandbox is  No
transactions.is_void    is  No          # sales-side explores only
```

---

## Explores

| Explore name | Display label | Fields |
|---|---|---|
| `transaction_items` | Transactions, Products & Customers | 295 |
| `reference_data` | Reference Data | 184 |
| `inventory` | Inventory | 346 |
| `inventory_snapshot` | Inventory Snapshot | 107 |
| `inventory_conversions` | Inventory Conversions | 320 |
| `inventory_adjustments` | Inventory Adjustments | 206 |
| `inventory_receive_history` | Inventory Receive History | 135 |
| `inventory_all` | Inventory All | 117 |
| `purchase_order` | Purchase Orders | 185 |
| `register_close_out` | Register Close Out | 44 |
| `plant` | Cultivation | 253 |

**This list is complete** for the Backoffice Data-type menu as of capture.

**The LookML names do not reliably match the Backoffice display labels** — several are
singular where the label is plural, or share no words with it at all. Every confirmed trap:

| Backoffice label | Wrong guess | Actual LookML name |
|---|---|---|
| Inventory Including Out Of Stock | `inventory_including_out_of_stock` | `inventory_all` |
| Purchase Orders | `purchase_orders` | `purchase_order` |
| Register Close-out | `register_closeout` | `register_close_out` |
| Cultivation | `cultivation` | `plant` |

Never guess an explore URL from its label — check this table first.

To resolve an unknown explore, navigate to `/embed/explore/sql_server/<guess>` and read
`document.title` — a valid explore yields `Explore <Label>`, an invalid one stays at the
bare `Explore` shell. Allow ~20s; slow explores return the bare shell simply because they
have not finished rendering, so a bare result is only meaningful after a generous wait.

## Views per explore

| Explore | Views exposed |
|---|---|
| `transaction_items` | batch_lab_results, customers, doctors, employees, lsp_location, **products**, producttags, transaction_item_discounts, transaction_items, transactions |
| `reference_data` | customers, doctors, employees, lsp_location, **products**, room, strain, vendors |
| `inventory` | batch, batch_lab_results, inventory, inventory_adjustments, inventory_moves, inventory_receive_history, inventory_recon_last_audited_date, inventorytags, lsp_location, **products**, strain |
| `inventory_snapshot` | inventory_snapshot, inventorytags, lsp_location, **products**, producttags |
| `inventory_conversions` | batch, batch_lab_results, inventory_adjustments, inventory_conversion_inputs_outputs, inventory_conversions, inventory_moves, inventory_receive_history, inventorytags, lsp_location, **products**, strain |
| `inventory_receive_history` | inventory_receive_history, lsp_location, **products**, purchase_order_items |
| `inventory_adjustments` | batch, batch_lab_results, inventory_adjustments, inventory_receive_history, inventorytags, lsp_location, **products**, strain |
| `inventory_all` | batch_lab_results, inventory_all, lsp_location, **products** |
| `purchase_order` | inventory_receive_history, lsp_location, **products**, purchase_order, purchase_order_items, strain |
| `register_close_out` | lsp_location, register_close_out |
| `plant` | batch, lsp_location, plant, plant_batch, room, waste |

### The single most useful fact in this document

**The `products` view is joined into all nine retail/product-grain explores**:
`transaction_items`, `reference_data`, `inventory`, `inventory_all`, `inventory_snapshot`,
`inventory_conversions`, `inventory_receive_history`, `inventory_adjustments`,
`purchase_order`. The two exceptions are `register_close_out` (cash/register data) and
`plant` (cultivation, which is grain-by-plant and reaches finished goods only via `batch`).
Consequences:

1. Any merge query can join its source queries on `${products.product_id}` — a numeric
   surrogate key present everywhere, immune to the casing/format mismatches that break
   name-, brand-, and size-based joins.
2. The `Inventory.X` vs `Products.X` value-space trap documented in SKILL.md is entirely
   avoidable: always select the `products.*` copy of a shared attribute, never the
   explore-native copy (`inventory.category`, `transaction_items.category`, etc.).
3. `reference_data` is the only explore whose grain is the product itself, so it is the
   correct spine for any catalog/master-data work — it shows products with zero activity.

Note the explore-native duplicates really do exist and really are different fields:
`inventory` has its own `category`, `product_grams`, `size`, `sku`, `product_name`,
`Brand_Name`, `MasterCategory`; `transaction_items` has its own `category`,
`master_category`, `product_grams`, `size`; `inventory_snapshot` has `Category`,
`MasterCategory`, `ProductGrams`, `SKU`. These capture values **as of the transaction or
snapshot**, not current catalog state — occasionally what you want, usually not.

---

## Recipes — which explore answers which question

Start here before opening a field picker.

| Question | Explore(s) | Key fields |
|---|---|---|
| What's in the catalog, including never-stocked items? | `reference_data` | `products.*`, filter `products.is_retired` |
| What do we have on hand right now? | `inventory` | `inventory.total_quantity`, `inventory.total_product_grams` |
| What do we carry, **including zeroed-out SKUs**? | `inventory_all` | `inventory_all.total_quantity`, `inventory_all.InventoryStatus` |
| What sold, and when? | `transaction_items` | `transaction_items.total_quantity`, `transactions.transaction_date` |
| Gram-weighted velocity | `transaction_items` | `transaction_items.total_product_grams` |
| Days in stock / snapshot history | `inventory_snapshot` | `inventory_snapshot.snapshot_date`, `sum_total_quantity` |
| When did we last receive this? | `inventory_receive_history` | `received_date`, `received_quantity`, `vendor_name` |
| Vendor lead time / on-time delivery | `purchase_order` | `expected_arrival_date_date` vs `actual_arrival_date_date` |
| PO approval workflow | `purchase_order` | `approval_status`, `approver`, `approval_action_date` |
| Which days was the store actually open? | `register_close_out` | `closing_date`, `closing_day_of_week` (a row exists only for trading days) |
| Shrink / adjustments | `inventory_adjustments` | `adjusted_quantity`, `reason`, `transaction_date` |
| Cultivation cycle times | `plant` | `days_in_vegetation`, `days_in_flowering`, `days_in_current_phase` |
| Harvest yields | `plant` | `plant_batch.dry_weight`, `total_dry_weight`, `trim_weight` (check `*_UOM`) |

### Master-data / catalog QC field set

Everything needed to construct and validate `Category | Dosage (per-unit x Npk) | Brand`
lives on `products` in `reference_data`:

```
products.product_id        # join key — numeric, use this for all merges
products.sku
products.product_name
products.master_category
products.category
products.brand_name
products.product_grams     # PRODUCTGRAMS — weight items
products.thccontent        # THCCONTENT — mg items, TOTAL package mg not per-unit
products.Product_Size      # SIZE — pack count ("5pk") / volume ("0.5ml")
products.is_cannabis       # gate dosage checks on this: "false" = Accessories/Apparel/Merch
products.is_retired        # lifecycle
products.Is_POS_Available
products.unit_type
```

### Joining source queries in a merge

Use `${products.product_id}` as the merge key in **every** source query. It is present in
all nine retail explores, it is numeric, and it cannot suffer the casing ("Wyld" vs "WYLD")
or format ("5pk" vs "5") mismatches that silently break name-, brand-, and size-based merge
rules. Select the `products.*` copy of every shared attribute, never the explore-native
duplicate.

---

## View field dictionary

Format: `field_name|type`. Prefix with the view name to get the LookML name
(e.g. `brand_name|string` in `products` → `${products.brand_name}`).
Types `count`, `sum`, `average`, `min`, `max`, `count_distinct`, `sum_distinct`,
`average_distinct` are measures; everything else is a dimension.

### products (51) — the master-data view

```
Allergen_List|string
Alternate_Description|string
brand_name|string
category|string
cbdcontent|number
cost|number
expiration_days|number
external_category|string
external_sub_category|string
flower_equivalent|number
Ingredient_List|string
Instructions|string
is_available_online|string
is_cannabis|string
Is_Coupon|yesno
Is_Nutrient|yesno
Is_On_Sale|yesno
Is_POS_Available|yesno
is_retired|yesno
Low_Inventory_Threshold|number
master_category|string
NDC|string
Online_Description|string
Online_Title|string
product_grams|number
product_id|number
Product_Image_File_Name|string
product_name|string
Product_Net_Weight|number
Product_Size|string
Provincial_SKU|string
sku|string
strain_name|string
Strain_Type|string
Tax_Categories|string
Taxable|string
thccontent|number
unit_price|number
unit_type|string
upc|string
UPC_GTIN|string
Vendor_Abbreviation|string
Vendor_Name|string
average_unit_price|average
count|count
total_product_grams|sum
total_unit_price|sum
```

Mapping to the Product Line construction inputs (see `dutchie-taxonomy` skill):

| Taxonomy input | LookML field |
|---|---|
| Master Category | `products.master_category` |
| Category | `products.category` |
| Brand | `products.brand_name` |
| `PRODUCTGRAMS` (weight items) | `products.product_grams` |
| `THCCONTENT` (mg items) | `products.thccontent` |
| `SIZE` (pack count / ml) | `products.Product_Size` — note capitalisation |
| SKU / join key | `products.sku` (string), `products.product_id` (number, preferred) |
| Non-cannabis gate | `products.is_cannabis` (string "true"/"false") |
| Lifecycle gate | `products.is_retired` (yesno), `products.Is_POS_Available` (yesno) |

`products.total_product_grams` is `sum_distinct`-flavoured and **not** quantity-weighted —
see the SKILL.md warning; use `transaction_items.total_product_grams` or
`inventory.total_product_grams` for gram-weighted math.

### transaction_items (42)

```
average_price|average
average_quantity|average
average_unit_price|average
batch_name|string
category|string
cost|number
count|count
cultivation_tax|number
customer_id|number
excise_tax|number
external_package_id|string
flower_equivalent|string
item_net_price|number
item_total_tax|number
loc_id|number
lsp_id|number
master_category|string
net_price|number
package_id|string
price|number
pricing_tier|string
product_grams|number
product_id|number
product|string
quantity|number
return_date|date
size|string
total_cost|sum
total_discount|sum
total_price|sum
total_product_grams|sum
total_quantity|sum
total_tax|sum
total_unit_price|sum
transaction_id|number
transaction_item_id|number
unit_price|number
unit|string
vendor_abbreviation|string
vendor|string
was_returned_yes_cash_returned|yesno
was_returned|yesno
```

No date field of its own — sale dates come from the `transactions` view.

### transactions (76)

```
LoyaltyEarned|number
LoyaltyPaid|number
average_change_due|average_distinct
average_net_transaction|average_distinct
average_total_items|average_distinct
average_total_transaction|average_distinct
average_transaction_subtotal|average_distinct
average_wait_time|average_distinct
cash_paid|sum_distinct
change_due|number
check_paid|sum_distinct
count|count_distinct
credit_paid|sum_distinct
credit|number
customer_id|number
debit_paid|sum_distinct
dynamic_transaction_time_frame|string
electronic_paid|sum_distinct
employee_id|number
gift_paid|sum_distinct
invoice_title|string
is_void|yesno
loc_id|number
loc_name|string
lsp_id|number
lsp_name|string
net_total|number
order_customer_type|string
order_source|string
order_type|string
paid|number
payment_type|string
pos_terminal_name|string
subtotal|number
sum_total_Loyalty_Earned|sum_distinct
sum_total_Loyalty_Paid|sum_distinct
sum_total_discount|sum_distinct
sum_total_items|sum_distinct
sum_total|sum_distinct
tax|number
total_change_due|sum_distinct
total_discount|number
total_items|number
total_tax|sum_distinct
total_wait_time|sum_distinct
total|number
transaction_date|date_date
transaction_day_of_month|date_day_of_month
transaction_day_of_week_index|date_day_of_week_index
transaction_day_of_week|date_day_of_week
transaction_hour12|date_hour12
transaction_hour2|date_hour2
transaction_hour3|date_hour3
transaction_hour4|date_hour4
transaction_hour6|date_hour6
transaction_hour8|date_hour8
transaction_hour_of_day|date_hour_of_day
transaction_hour|date_hour
transaction_id|number
transaction_month_name|date_month_name
transaction_month_num|date_month_num
transaction_month|date_month
transaction_quarter|date_quarter
transaction_time_formatted|string
transaction_time_frame|string
transaction_time|date_time
transaction_week|date_week
transaction_year|date_year
type|string
void_date|date_date
void_month|date_month
void_quarter|date_quarter
void_time|date_time
void_week|date_week
void_year|date_year
wait_time|number
```

**`transactions.transaction_day_of_week` exists.** SKILL.md's Sunday-exclusion section says
Looker "can't filter by day-of-week" — that is true for the *Inventory Snapshot* explore
(no such sub-timeframe on `snapshot_date`), but **not** for sales. Anything grouped or
filtered on the sales side can use a real day-of-week rather than the proportional 6/7
approximation.

### inventory (111)

```
Alternate_Name|string
Brand_Name|string
CBDA_String|string
CBD_String|string
CBN_String|string
Effective_Potency_Mg|number
External_Category|string
Harvest_Completed_On|string
Image_Url|string
Instructions|string
Inventory_Received_date|date_date
Inventory_Received_month|date_month
Inventory_Received_quarter|date_quarter
Inventory_Received_time|date_time
Inventory_Received_week|date_week
Inventory_Received_year|date_year
Is_Finished_In_Integration|string
Last_Modified_Utc|string
Location_Cost|number
Location_Price|number
Location_Rec_Price|number
Low_Inventory_Threshold|number
Manufacturing_Date|string
MasterCategory|string
Online_Description|string
Online_Title|string
Package_NDC|string
Packaged_Date_date|date_date
Packaged_Date_month|date_month
Packaged_Date_quarter|date_quarter
Packaged_Date_time|date_time
Packaged_Date_week|date_week
Packaged_Date_year|date_year
Pricing_Tier_Name|string
Producer_Id|number
Producer_Name|string
Rec_Flower_Equivalent|number
Rec_Unit_Price|number
Source_Batch|string
THCA_String|string
THC_String|string
Total_Rec_Price|number
Transaction_Status|string
UPC_GTIN|string
Unit_Weight|number
average_cost|average
average_price|average
average_quantity|average
average_unit_cost|average
batch_id|number
batch_name|string
category|string
cost_plus_excise_tax|number
cost|number
count|count
cultivation_tax|number
excise_tax|number
expiration_date|date_date
expiration_month|date_month
expiration_quarter|date_quarter
expiration_time|date_time
expiration_week|date_week
expiration_year|date_year
external_package_id|string
flower_equivalent|number
gross_weight|number
harvest_room|string
inventory_id|number
inventory_status_id|number
is_available_online|string
is_cannabis|string
is_sample|string
loc_id|number
location_license|string
lsp_id|number
med_usable_weight|number
medical_only|string
net_weight|number
package_id|string
pesticides_used|string
potency_indicator|string
prescription_number|number
price|number
product_grams|number
product_id|number
product_name|string
provincial_sku|string
quantity|number
remediated|string
remediation_eligible|string
restocked|string
room_id|number
room|string
size|string
sku|string
status|string
strain_name|string
strain_type|string
test_status|string
total_cost|sum
total_price|sum
total_product_grams|sum
total_quantity|sum
total_unit_cost|sum
total_unit_price|sum
unit_cost|number
unit_id|number
unit_name|string
unit_price|number
vendor_id|number
vendor|string
```

### inventory_snapshot (40)

```
Category|string
MasterCategory|string
PackageNDC|string
ProductGrams|number
SKU|string
SourceBatch|string
batch_id|number
batch_name|string
count|count
expiration_date|date_date
expiration_day_of_month|date_day_of_month
expiration_month_num|date_month_num
expiration_month|date_month
expiration_quarter|date_quarter
expiration_time|date_time
expiration_week|date_week
expiration_year|date_year
inventory_status|string
loc_id|number
lsp_id|number
package_id|string
package_status|string
product_name|string
quantity|number
received_date|date_date
received_day_of_month|date_day_of_month
received_month_num|date_month_num
received_month|date_month
received_quarter|date_quarter
received_time|date_time
received_week|date_week
received_year|date_year
room_name|string
snapshot_date|date_date
sum_total_cost|sum
sum_total_product_grams|sum
sum_total_quantity|sum
total_cost|number
unit|string
vendor_name|string
```

Confirms SKILL.md: `snapshot_date` exposes only `date_date` — no day-of-week sub-timeframe,
hence the proportional operating-days workaround for snapshot-derived Days In Stock.

### inventory_receive_history (56)

```
average_cost|average
average_price|average
batch_name|string
brand|string
category|string
cost|number
count|count
delivered_by|string
delivered_date|date_date
delivered_month|date_month
delivered_quarter|date_quarter
delivered_time|date_time
delivered_week|date_week
delivered_year|date_year
expiration_date|date_date
expiration_month|date_month
expiration_quarter|date_quarter
expiration_time|date_time
expiration_week|date_week
expiration_year|date_year
external_id|string
external_package_id|string
loc_id|number
lot|string
lsp_id|number
master_category|string
note|string
order_title|string
package_id|string
package_ndc|string
price|number
product_id|number
product_name|string
received_by|string
received_date|date_date
received_month|date_month
received_quantity|number
received_quarter|date_quarter
received_time|date_time
received_week|date_week
received_year|date_year
shipment_id|number
shipping_charge|number
source_batch|string
status|string
strain_type|string
sum_total_cost|sum
sum_total_quantity|sum
total_cost|number
total_credit|number
total_price|number
transaction_id|string
unit_name|string
vendor_abbreviation|string
vendor_license|string
vendor_name|string
```

### inventory_adjustments (22)

```
adjusted_quantity|number
count|count
from_quantity|number
loc_id|number
lsp_id|number
package_id|string
product_id|number
product_name|string
reason|string
to_quantity|number
total_adjusted_quantity|sum
total_from_quantity|sum
total_to_quantity|sum
transaction_by|string
transaction_date|date_date
transaction_month|date_month
transaction_quarter|date_quarter
transaction_time|date_time
transaction_type|string
transaction_week|date_week
transaction_year|date_year
unit_name|string
```

### inventory_conversions (70)

```
Is_Finished_In_Integration|string
MasterCategory|string
Packaged_Date_date|date_date
Packaged_Date_month|date_month
Packaged_Date_quarter|date_quarter
Packaged_Date_time|date_time
Packaged_Date_week|date_week
Packaged_Date_year|date_year
average_cost|average
average_price|average
average_quantity|average
average_unit_cost|average
batch_id|number
batch_name|string
category|string
cost|number
count|count
cultivation_tax|number
expiration_date|date_date
expiration_month|date_month
expiration_quarter|date_quarter
expiration_time|date_time
expiration_week|date_week
expiration_year|date_year
external_package_id|string
flower_equivalent|number
gross_weight|number
harvest_room|string
inventory_date_date|date_date
inventory_date_month|date_month
inventory_date_quarter|date_quarter
inventory_date_time|date_time
inventory_date_week|date_week
inventory_date_year|date_year
inventory_id|number
inventory_status_id|number
is_available_online|string
is_cannabis|string
loc_id|number
lsp_id|number
medical_only|string
net_weight|number
package_id|string
pesticides_used|string
potency_indicator|string
prescription_number|number
price|number
product_grams|number
product_id|number
product_name|string
quantity|number
room_id|number
room|string
size|string
sku|string
status|string
strain_name|string
test_status|string
total_cost|sum
total_price|sum
total_product_grams|sum
total_quantity|sum
total_unit_cost|sum
total_unit_price|sum
unit_cost|number
unit_id|number
unit_name|string
unit_price|number
vendor_id|number
vendor|string
```

### inventory_conversion_inputs_outputs (24)

```
conversion_date_date|date_date
conversion_date_month|date_month
conversion_date_quarter|date_quarter
conversion_date_time|date_time
conversion_date_week|date_week
conversion_date_year|date_year
conversion_input_package_id|number
conversion_type|string
input_cost|number
input_package_id|string
input_package_quantity|number
input_product|string
input_unit|string
inventory_id|number
location|string
lsp_id|number
lsp|string
output_cost|number
output_package_id|string
output_package_quantity|number
output_product|string
output_unit|string
transaction_by|string
variance|number
```

### inventory_moves (20)

```
count|count
from_location|string
from_room|string
loc_id|number
lsp_id|number
package_id|string
product_id|number
quantity_moved|number
to_location|string
to_room|string
total_quantity_moved|sum
transaction_by|string
transaction_date|date_date
transaction_month|date_month
transaction_quarter|date_quarter
transaction_time|date_time
transaction_type|string
transaction_week|date_week
transaction_year|date_year
unit_name|string
```

### inventory_all (47) — inventory *including* zero/out-of-stock rows

```
InventoryStatus|string
MasterCategory|string
average_cost|average
average_price|average
average_quantity|average
average_unit_cost|average
batch_id|number
batch_name|string
category|string
cost|number
count|count
expiration_date|date_date
expiration_month|date_month
expiration_quarter|date_quarter
expiration_time|date_time
expiration_week|date_week
expiration_year|date_year
flower_equivalent|number
inventory_id|number
inventory_status_id|number
is_available_online|string
is_cannabis|string
loc_id|number
lsp_id|number
medical_only|string
package_id|string
price|number
product_grams|number
product_id|number
product_name|string
quantity|number
room_id|number
room|string
status|string
strain_name|string
total_cost|sum
total_price|sum
total_product_grams|sum
total_quantity|sum
total_unit_cost|sum
total_unit_price|sum
unit_cost|number
unit_id|number
unit_name|string
unit_price|number
vendor_id|number
vendor|string
```

A near-clone of `inventory` minus the extended attribute block (no `Brand_Name`,
`THC_String`, `Packaged_Date`, `Producer_Name`, etc.), plus `InventoryStatus`. Use it when
you need SKUs that have gone to zero — `inventory` drops them, which silently biases any
"what do we carry" or dead-stock question toward things currently in stock.

### purchase_order (44)

```
actual_arrival_date_date|date_date
actual_arrival_date_month|date_month
actual_arrival_date_quarter|date_quarter
actual_arrival_date_time|date_time
actual_arrival_date_week|date_week
actual_arrival_date_year|date_year
approval_action_date|date_date
approval_action_month|date_month
approval_action_quarter|date_quarter
approval_action_time|date_time
approval_action_week|date_week
approval_action_year|date_year
approval_status|string
approver|string
created_by|string
created_from_purchase_order_id|number
creation_date_date|date_date
creation_date_month|date_month
creation_date_quarter|date_quarter
creation_date_time|date_time
creation_date_week|date_week
creation_date_year|date_year
date_submitted_date|date_date
date_submitted_month|date_month
date_submitted_quarter|date_quarter
date_submitted_time|date_time
date_submitted_week|date_week
date_submitted_year|date_year
expected_arrival_date_date|date_date
expected_arrival_date_month|date_month
expected_arrival_date_quarter|date_quarter
expected_arrival_date_time|date_time
expected_arrival_date_week|date_week
expected_arrival_date_year|date_year
is_deleted|yesno
loc_id|number
lsp_id|number
order_number|number
purchase_order_id|number
purchase_order_status|string
shipping_information|string
title|string
vendor_email|string
vendor|string
```

Carries approval workflow (`approval_status`, `approver`, `approval_action_date`) and both
`expected_arrival_date` and `actual_arrival_date` — enough to measure vendor lead time and
on-time delivery, which the procurement tiles currently have no visibility into.

### register_close_out (29)

```
cash_counted|number
cash_difference|number
cash_ending|number
cash_expected|number
cash_opening|number
closing_date|date_date
closing_day_of_month|date_day_of_month
closing_day_of_week_index|date_day_of_week_index
closing_day_of_week|date_day_of_week
closing_hour12|date_hour12
closing_hour2|date_hour2
closing_hour3|date_hour3
closing_hour4|date_hour4
closing_hour6|date_hour6
closing_hour8|date_hour8
closing_hour_of_day|date_hour_of_day
closing_hour|date_hour
closing_month_name|date_month_name
closing_month_num|date_month_num
closing_month|date_month
closing_quarter|date_quarter
closing_time|date_time
closing_week|date_week
closing_year|date_year
deposit|number
employee_name|string
register_id|number
register_name|string
set_register_balance|number
```

**`closing_day_of_week` is a real dimension, and a register close-out row exists only for
days the store actually traded.** That makes this explore an empirical source for operating
days — a direct answer to the "which days is the store open" problem that the proportional
6/7 Sunday-exclusion calc in SKILL.md only approximates.

### batch (49)

```
batch_created_date|date_date
batch_created_day_of_month|date_day_of_month
batch_created_day_of_week|date_day_of_week
batch_created_hour_of_day|date_hour_of_day
batch_created_hour|date_hour
batch_created_month|date_month
batch_created_quarter|date_quarter
batch_created_time|date_time
batch_created_week|date_week
batch_created_year|date_year
batch_id|number
dry_waste_total|sum_distinct
dry_waste|number
dry_weight_total|sum_distinct
dry_weight|number
harvest_completed_on_date|date_date
harvest_completed_on_day_of_month|date_day_of_month
harvest_completed_on_day_of_week|date_day_of_week
harvest_completed_on_hour_of_day|date_hour_of_day
harvest_completed_on_hour|date_hour
harvest_completed_on_month|date_month
harvest_completed_on_quarter|date_quarter
harvest_completed_on_week|date_week
harvest_completed_on_year|date_year
harvest_date|date_date
harvest_day_of_month|date_day_of_month
harvest_day_of_week|date_day_of_week
harvest_hour_of_day|date_hour_of_day
harvest_hour|date_hour
harvest_month|date_month
harvest_quarter|date_quarter
harvest_time|date_time
harvest_unit_id|number
harvest_week|date_week
harvest_year|date_year
loc_id|number
lsp_id|number
name|string
plant_count|count
plant_weight_total|sum_distinct
plant_weight|number
room_id|number
strain_id|number
strain_name|string
type|string
wet_waste_total|sum_distinct
wet_waste|number
wet_weight_total|sum_distinct
wet_weight|number
```

### plant (82)

```
Destroyed_Seedling_Reason|string
Group_Date_Created_date|date_date
Group_Date_Created_month|date_month
Group_Date_Created_quarter|date_quarter
Group_Date_Created_week|date_week
Group_Date_Created_year|date_year
Group_Phase|string
Group_Plant_Count|sum
Group_Room|string
Group_Status|string
Group_Strain|string
Harvest_Average|average
Harvest_Total|sum
Plant_Destroyed_Date_date|date_date
Plant_Destroyed_Date_month|date_month
Plant_Destroyed_Date_quarter|date_quarter
Plant_Destroyed_Date_week|date_week
Plant_Destroyed_Date_year|date_year
Trim_Date_date|date_date
Trim_Date_month|date_month
Trim_Date_quarter|date_quarter
Trim_Date_week|date_week
Trim_Date_year|date_year
Trim_Plants_Serial_Number|string
Trim_Weight_UoM|string
Trim_Weight|number
batch_id|number
bench_id|number
bench_name|string
count|count
current_phase_started_on_date|date_date
current_phase_started_on_month|date_month
current_phase_started_on_quarter|date_quarter
current_phase_started_on_week|date_week
current_phase_started_on_year|date_year
current_phase|string
days_in_current_phase|number
days_in_flowering|number
days_in_vegetation|number
flowering_ended_on_date|date_date
flowering_ended_on_month|date_month
flowering_ended_on_quarter|date_quarter
flowering_ended_on_week|date_week
flowering_ended_on_year|date_year
flowering_started_on_date|date_date
flowering_started_on_month|date_month
flowering_started_on_quarter|date_quarter
flowering_started_on_week|date_week
flowering_started_on_year|date_year
growth_phase|string
harvested_weight|number
is_mother|string
loc_id|number
lsp_id|number
mother_plant_id|number
plant_count|number
plant_group_name|string
plant_id|number
plant_stage|string
plant_total_count|sum
planted_on_date|date_date
planted_on_month|date_month
planted_on_quarter|date_quarter
planted_on_week|date_week
planted_on_year|date_year
room_id|number
room|string
serial_number|string
status|string
strain|string
type|string
vegetation_ended_on_date|date_date
vegetation_ended_on_month|date_month
vegetation_ended_on_quarter|date_quarter
vegetation_ended_on_week|date_week
vegetation_ended_on_year|date_year
vegetation_started_on_date|date_date
vegetation_started_on_month|date_month
vegetation_started_on_quarter|date_quarter
vegetation_started_on_week|date_week
vegetation_started_on_year|date_year
```

`days_in_vegetation`, `days_in_flowering`, and `days_in_current_phase` are precomputed —
no table calc needed for cycle-time analysis.

### plant_batch (83)

```
batch_closed_date|date_date
batch_closed_month|date_month
batch_closed_quarter|date_quarter
batch_closed_time|date_time
batch_closed_week|date_week
batch_closed_year|date_year
batch_created_date|date_date
batch_created_month|date_month
batch_created_quarter|date_quarter
batch_created_time|date_time
batch_created_week|date_week
batch_created_year|date_year
batch_id|number
batch_issued_by|number
batch_plant_status|string
brand|string
count|count
de_leaf_wet_weight|number
dry_waste|number
dry_weight|number
empty_weight|number
full_product_weight_UOM|string
full_product_weight|number
full_weight|number
harvest_completed_on|string
harvest_date_date|date_date
harvest_date_day_of_month|date_day_of_month
harvest_date_day_of_week|date_day_of_week
harvest_date_hour_of_day|date_hour_of_day
harvest_date_hour|date_hour
harvest_date_month|date_month
harvest_date_quarter|date_quarter
harvest_date_week|date_week
harvest_date_year|date_year
harvest_reporting_stage|number
harvest_unit_id|number
harvest_units|string
harvested|number
inventory_status|string
issued_by|string
item_count|number
joint_material_value_UOM|string
joint_material_value|number
kief_value_UOM|string
kief_value|number
loc_id|number
lsp_id|number
net_product_weight_UOM|string
net_product_weight|number
other_plant_lot_no|string
package_date|date_date
package_expiration_date|date_date
package_expiration_month|date_month
package_expiration_quarter|date_quarter
package_expiration_time|date_time
package_expiration_week|date_week
package_expiration_year|date_year
package_id|number
package_month|date_month
package_no|number
package_quantity|number
package_quarter|date_quarter
package_tare_weight_UOM|string
package_tare_weight|number
package_time|date_time
package_type|string
package_week|date_week
package_year|date_year
plant_group|string
product_type|string
product|string
room|string
status|string
strain_id|number
strain_name|string
sugar_leaf_value_UOM|string
sugar_leaf_value|number
total_dry_weight|number
trim_weight|number
type|string
water_leaf_value_UOM|string
water_leaf_value|number
wet_waste|number
```

Carries the full harvest yield breakdown (dry/wet weight, trim, kief, sugar leaf, water
leaf, joint material) with explicit UOM strings alongside each value — **check the UOM
field before summing**, units are not guaranteed consistent across rows.

### waste (18)

```
RecordedBy|string
Room|string
Unit_name|string
WasteComments|number
Waste_Date_date|date_date
Waste_Date_day_of_month|date_day_of_month
Waste_Date_day_of_week|date_day_of_week
Waste_Date_hour_of_day|date_hour_of_day
Waste_Date_hour|date_hour
Waste_Date_month|date_month
Waste_Date_quarter|date_quarter
Waste_Date_week|date_week
Waste_Date_year|date_year
Waste_Reference_No|string
Waste_Type|string
Waste_Weight|number
batchid|number
plantid|number
```

`WasteComments` is typed `number` in LookML but named like a free-text field — treat its
type as suspect until verified against real rows.

### batch_lab_results (8)

```
average_result|average
lab_name|string
lab_result_url|string
max_result|max
min_result|min
result_unit|string
result|sum
test|string
```

### purchase_order_items (17)

```
expiration_date_date|date_date
expiration_date_month|date_month
expiration_date_quarter|date_quarter
expiration_date_time|date_time
expiration_date_week|date_week
expiration_date_year|date_year
purchase_order_id|number
quantity_requested|number
serial_number|string
subtotal|number
tax|number
unit_name|string
vendor_price|number
vendor_product_name|string
vendor_product_sku|string
vendor_quantity_units|string
vendor_quantity|number
```

### inventory_recon_last_audited_date (9)

```
last_audited_date_date|date_date
last_audited_date_month|date_month
last_audited_date_quarter|date_quarter
last_audited_date_time|date_time
last_audited_date_week|date_week
last_audited_date_year|date_year
loc_id|number
lsp_id|number
product_id|number
```

### strain (6)

```
abbreviation|string
description|string
lsp_id|number
name|string
strain_id|number
type|string
```

### vendors (10)

```
abbreviation|string
city|string
license_number|string
lsp_id|number
postal_code|string
state|string
street_address|string
vendor_id|number
vendor_name|string
count|count
```

### room (7)

```
cultivation_stage|string
external_id|string
loc_id|number
lsp_id|number
name|string
room_id|number
count|count
```

### lsp_location (15)

```
is_sandbox|yesno
loc_address_line_1|string
loc_address_line_2|string
loc_city|string
loc_id|number
loc_phone_no|string
loc_postal_code|string
loc_state|string
location_name|string
lsp_address_line1|string
lsp_city|string
lsp_id|number
lsp_name|string
lsp_postal_code|string
count|count
```

### inventorytags (3) / producttags (2) / transaction_item_discounts (6)

```
# inventorytags
inventory_id|number
packageid|number
tag_name_list|string

# producttags
product_id|number
tag_name_list|string

# transaction_item_discounts
amount|sum
loc_id|number
lsp_id|number
name|string
reason|string
transaction_item_id|number
```

`customers` (62), `doctors` (16), `employees` (22) are standard PII/reference views and are
omitted here — enumerate them on demand if a task actually needs them. Notable fields, so
you know they exist: `customers.first_transaction_date`, `customers.last_transaction_date`,
`customers.is_loyalty_member`, `customers.customer_type`, `customers.age_range` (a `tier`
dimension), `customers.referral_source`, `employees.employee_name`, `employees.status`.

---

## Coverage

11 explores, 27 distinct views. Every explore in the Backoffice Data-type menu is resolved
to its LookML name. Field lists are complete for all views except `customers`, `doctors`,
and `employees` as noted above.

Re-run the harvest (below) after any Dutchie/leaflogix LookML release — fields get added
without notice, and a stale catalog is worse than none.

---

## Harvesting the catalog

Two techniques make this repeatable. Both depend on being **top-level** on
`leaflogix.looker.com` rather than inside the Backoffice iframe.

### 1. Escape the iframe entirely

Once Backoffice has loaded any BI-tools page, the signed `/login/embed/...` URL has set the
embed cookie for the whole `leaflogix.looker.com` origin. From then on you can open a plain
browser tab directly at `https://leaflogix.looker.com/embed/explore/sql_server/<explore>`
and it renders, authenticated, as a **same-origin top-level document**. No `contentFrame()`
gymnastics, no cross-origin `SecurityError`, and `javascript_tool` / `evaluate` work
directly on the page.

The Looker REST API stays blocked for embed users (`/api/4.0/...` → 401,
`/api/internal/4.0/...` → 403), so schema still has to come from the rendered UI.

### 2. Drive queries by URL, and enumerate in hidden iframes

Explore URLs accept full query state as parameters, which Looker converts to a `qid`:

```
/embed/explore/sql_server/reference_data
  ?fields=products.master_category,products.count
  &sorts=products.count+desc
  &limit=200
  &vis=%7B%22type%22%3A%22table%22%7D
  &run=true
```

Navigate to that and read the rendered table out of `document.body.innerText` — a fast way
to profile data without touching the field picker.

Because you are same-origin, you can also load *other* explores into a hidden iframe and
read their DOM, enumerating many explores in one pass:

```js
const f = document.createElement('iframe');
f.style.cssText = 'position:absolute;left:-9999px;width:1400px;height:2000px';
document.body.appendChild(f);
f.src = '/embed/explore/sql_server/' + name;   // then poll f.contentDocument
```

Expand every collapsed view group before reading, repeating for nested groups:

```js
for (let pass = 0; pass < 6; pass++) {
  const collapsed = [...doc.querySelectorAll('[role="treeitem"][aria-expanded="false"]')];
  if (!collapsed.length) break;
  collapsed.forEach(c => c.click());     // group expansion DOES respond to .click()
  await sleep(1200);
}
```

Note the asymmetry with SKILL.md: group **expansion** works with a plain `.click()`; field
**selection** does not, and still needs the React `onKeyDown` Enter trick.

Then read each field's LookML metadata off the React props:

```js
function findField(node, depth = 0) {
  if (!node || depth > 30) return null;
  if (node.props?.field?.name) return node.props.field;
  if (Array.isArray(node)) {
    for (const c of node) { const r = findField(c, depth + 1); if (r) return r; }
    return null;
  }
  if (node.props?.children) return findField(node.props.children, depth + 1);
  return null;
}
document.querySelectorAll('[role="treeitem"]').forEach(ti => {
  const k = Object.keys(ti).find(x => x.startsWith('__reactProps'));
  if (!k) return;
  const f = findField(ti[k].children);
  if (f) console.log(f.name, f.type, f.label_short || f.label, f.view);
});
```

### 3. Beat the 30-second tool timeout

Enumerating many explores exceeds the browser tool's per-call limit. Kick the loop off as a
detached async job that parks its results on `window`, return immediately, then poll:

```js
window.__cat = { done: false, at: '', data: {} };
(async () => { /* ... loop, writing into window.__cat ... */ window.__cat.done = true; })();
'started';
```

Subsequent calls just `await sleep(25000)` and report `window.__cat`. This pattern
generalises to any long Looker automation.
