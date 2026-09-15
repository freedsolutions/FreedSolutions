<!-- Generated from "freed-solutions/skills/dutchie-bi-looker/references/dutchie-platform-kb.md". Edit the repo skill source and rerun ops/notion-workspace/scripts/sync-claude-skill-wrappers.ps1; do not edit this Claude copy directly. -->

# Dutchie Platform Knowledge Base

Platform-behavior facts: what Dutchie POS actually does, sourced from official support
docs and from live probes. **Portable layer** — sits with mdm-product-line-rules in the
precedence chain (Dictionary > mdm rules > this KB + SKILL mechanics > memories).
Every entry carries its source class and date:
- `[DOC yyyy-mm-dd]` — official support.dutchie.com article (URL in §Sources), as read that day.
- `[PROBE yyyy-mm-dd]` — verified live against the pilot tenant (API/UI capture).
- `[TENANT]` — pilot-tenant-specific observation; may differ elsewhere.

Support articles are living documents — re-read before relying on a `[DOC]` fact for a
destructive change. support.dutchie.com blocks plain fetchers (403); read via browser.

---

## 1. Catalog → Inventory attribute inheritance [DOC 2026-08-27]

Every package is assigned to exactly one Catalog product. Inheritance is strictly
Catalog → inventory; nothing flows back. Three classes:

**A. Catalog-controlled (live reference — catalog edits propagate to ALL packages
instantly, no package-level value exists):**
Name, SKU, Category, Master category, External category, Cannabis product Y/N, Brand,
Size, Alternate name, Available on POS, Taxable, Is additive, Ingredients, Allergens,
Instructions, Days supply.
→ Renames/repoints (subbrand waves, category moves) auto-flow to all packages, active
and historical views alike. No lag class exists for these.

**B. Catalog-default, package-overridable (snapshot at receive/create; package edits
never touch the catalog):**
Grams/concentration, Vendor, Producer, Net weight, Available for [customer types].
→ The 193884 drift-QC semantics are doc-confirmed: package-vs-catalog divergence on
these is a real, intended-to-be-possible state — drift QC is the right control.

**C. Catalog-only (no inventory equivalent at all):**
Abbreviation, NDC, GTIN, OCS item number, Provincial SKU, UPC, Administration Method,
**Non-cannabis weight, Oil volume, Serving size, Servings per unit, Lineage,
Distillation, Flavor, Dosage**, Allow automatic discounts, Tax categories, Test product,
Is finished, THC content (renders in the inventory grid as "Calculated THC (mg)"),
CBD content, Low inventory threshold, Use SKU as package ID, Default pricing tier,
Max quantity per transaction, External ID, MN medicine ID, Sales account,
Expiration days (drives inventory Expiration date = receive date + N), Regulatory
category, Unit THC/CBD Content Dose.
→ **The entire attribute-hardening slate (Distillation, Oil Volume, Serving size,
Servings per unit) is class C**: values apply instantly and uniformly, no receive-time
snapshots, no backfill-vs-new-inventory divergence possible.

**Unique behaviors:**
- **Price**: product-level vs inventory-level pricing is an LSP-wide config ONLY
  Dutchie Support can change. Product-level = price catalog-controlled (class A, with
  optional location-specific catalog prices); inventory-level = class B. [TENANT: the pilot tenant
  mode unconfirmed; 193884 unit-price drift QC exists either way.]
- **Cost**: receive pre-populates from catalog, per-package override allowed;
  convert/create/recipe offers Catalog / Calculated (from inputs) / Other, default per
  Settings > Location "Which unit cost".
- **Flower equivalent**: class B in spirit — catalog value is the receive-time default,
  inventory-level value is what ENFORCES limits/allotments. See §2 for auto-calc.
- **Type + Default unit**: catalog-only, but NOT retroactive — existing inventory keeps
  its original unit of measure; only new inventory takes a changed Type/unit.
- **Tags**: packages inherit catalog-product tags at RECEIVE ONLY. Adding a tag to a
  catalog product does NOT tag existing inventory; converted/created packages inherit
  from neither source package nor catalog. **Smart tags are the retroactive mechanism**
  (rule refresh re-evaluates existing packages). → Any tag migration (e.g. moving
  Promo/Sample/Limited prefixes to tags) must be smart-tag-driven or manually swept;
  plain catalog tags only cover future receives.
- **Strain**: inventory-level strain inherits from the BATCH, not the catalog [DOC —
  confirms the PROBE 2026-08-26 finding that batch strain lags catalog repoints].
- **Inheritance triggers**: Receive / Convert / Create package → inherit from catalog.
  Sublot / Create lab sample → inherit from SOURCE PACKAGE.

## 2. Automatic flower equivalency calculations [DOC 2026-08-27]

Dutchie can auto-calculate FL EQ from **Purchase limit category × Customer type** rules —
the platform-native home for PLC-keyed EQ standards.

- **Enable**: Settings > Location → "Use Flower Equivalency Definition" (permissions:
  View/Edit Flower Equivalency Definition). Definitions are LSP-wide.
- **Define**: Settings > Taxes & compliance > Flower equivalency tab > Add. Per rule:
  PLC + customer type (All unless the state splits med/rec) + **based-on** ∈
  {Grams/concentration, Package net weight, Potency} + category amount ≡ equivalent
  flower amount → ratio (= flower ÷ category).
- **Recalc behavior**: catalog EQ recalculates when the based-on field is edited;
  inventory EQ likewise (Potency-based reads THC lab results, falls back to catalog THC
  content). Manual overrides allowed but a based-on edit re-fires the calc.
- **Rollout safety**: enabling preserves ALL existing EQ values; on first defining a
  rule, the calc auto-fills only items whose EQ is BLANK. Editing a rule later does not
  touch existing values.
- Only INVENTORY-level EQ enforces limits; catalog EQ is the default feed.
- Requires every product category to be associated to a PLC (pilot tenant: verified complete,
  category-qc).

**⚠ Pilot-tenant hazard — infused composites [TENANT 2026-08-27]:** definitions are per-PLC and
cannot exclude categories. The pilot tenant's four infused categories share the **Concentrates PLC**
with vapes/dabs. A Concentrates ×5.6 rule fits vapes (grams = concentrate grams) but
would recalc infused items as total_grams × 5.6 — the FL_EQ_IMPOSSIBLE bound — whenever
grams is edited. The R2 composite formula `EQ = (g − conc) + conc×5.6` is NOT
expressible in Dutchie's linear model. If auto-calc is ever enabled: infused EQ stays
manual (overrides survive until a grams edit), with the 28006 three-tier QC as the
tripwire. Also note the ratio-vs-canon seam: Dutchie's MA example uses 28.35g (true oz);
house standard is ×5.6 / ×56 (28g basis, R1 LOCKED) — enter amounts that produce the
HOUSE ratio.

## 3. Tenant lists & virgin-field census [PROBE 2026-08-27]

- Item-form lookup endpoints live in per-entity namespaces (guessed paths 404):
  `POST /api/distillation/get-distillations` · `POST /api/lineage/get-lineages` ·
  `POST /api/flower-equivalencies/list` (all bare-ctx envelope). All three return EMPTY
  lists for the pilot tenant = tenant-configurable, unseeded.
- Full candidate-field census (934 items × 153 fields): DistillationId+Name, OilVolume,
  NonCannabisWeight+Unit, ServingSize, ServingSizePerUnit, LineageId+Name, THCContent,
  UnitThc/CbdContentDose — ALL 0-populated (THCContentUnitId=1 default only).
- Item edit form (`/products/catalog/<id>`, SPA soft-nav) fires the lookup set:
  get-product-details-v2, get-strains, get-brands, tax/product-category/get-all,
  distillation, lineage, flower-equivalencies, get-product-extra-info,
  get-product-loc-info, metrc required-fields, mmur/get-devices.
- Fields hidden in Products > Configure > Fields do not render on the item form —
  flip to Show before expecting a field to be settable (fields-config lane:
  the estate's `fields-config/`).

## 3b. Product retirement & duplicate combining [DOC 2026-08-28]

Read by the prefix-cleanup assessment session (task_65a4aa88); facts relayed for the
prefix-collapse program:

- **Retire = hide, not delete.** Retiring a product hides it from active catalog/menu
  surfaces; it is REVERSIBLE, has NO Metrc effect, and historic transactions stay on
  the SKU. Safe default for prefixed-duplicate cleanup (never delete).
- **"Combine duplicate products"** is a documented Change-product flow: packages move
  from a duplicate product to its twin. Candidate mechanism for HOLD-INVENTORY
  prefixed SKUs (move packages to the clean twin, then retire the husk).
- **UNKNOWN (probe proposed, 1 package):** whether Change-product re-attributes a
  package's PRIOR sales display to the new product, or history stays rendered under
  the old SKU. Do NOT bulk-combine until probed.

## 3c. Inventory tags in the reporting model [PROBE 2026-08-28]

From the R14 tag-pivot build (5 dashboards moved to `inventorytags`-based filters):

- The `inventorytags` join is **left-outer**, and negative filters on
  `tag_name_list` are **null-safe** — untagged packages are NOT dropped by a
  `-%Limited%`-style exclusion (they pass through). Safe to filter-negatively
  without losing the untagged population.
- `tag_name_list` is **comma-joined per package** (e.g. "Limited, Minor
  Cannabinoids") — one row per package, **no fan-out** from multiple tags.
  Contains-style matching is the right pattern; exact-equality is wrong.
- Live tag names are **pipe-less** (`Limited`, `Display`, `Promo`) — the name-prefix
  convention (`Limited |`) does NOT carry into tags.
- **Reporting lag exists**: Backoffice tag edits take time to reach the Looker
  reporting DB (Adam's same-day tag changes not yet visible at build time) — never
  treat a fresh tag edit's absence in a tile as a failure; re-check later.

## 3d. Tag-join matrix in the reporting model [PROBE 2026-08-28 ×2]

Which tag views can safely filter which query contexts (probed after the R14 tag
pivot; the broken cell caused live Snowflake 400s until unwired):

| Tag view | Query context | Join behavior | Verdict |
|---|---|---|---|
| inventorytags | inventory explore | numeric join, left-outer, null-safe | ✅ SAFE (the R14 filters live here) |
| inventorytags | inventory_snapshot | **BROKEN — numeric `packageid` cast against the STRING Metrc package id → Snowflake "Numeric value '1A40A…' is not recognized"** | ❌ NEVER filter snapshot queries on inventorytags |
| producttags | inventory_snapshot | **INNER-join behavior — even a no-op filter drops all unmatched rows** | ❌ never |
| producttags | transaction_items | left-outer + null-safe (exact value parity proven vs unfiltered) | ✅ SAFE (the designed Product Tag wave) |

Also: the **inventory explore surfaces CURRENT packages only** (census invariant to
`is_retired`) and **inventory_all has no tags view** — but ~~historic packages are
BI-invisible for tags~~ **SUPERSEDED same day: the newly-discovered
`inventory_historical` explore carries FULL package history (5,835 pkgs incl.
qty-0 sold-out) WITH a working inventorytags join (numeric key)** — the historic tag
lane exists; Adam's 59 historic Limited-tagged packages are queryable there.

**Feature-request ledger (ask Dutchie):**
- `inventorytags` join on `transaction_items` (currently rejected — 'Invalid filter').
- Fix the snapshot↔inventorytags join key (numeric packageid cast vs string Metrc id).

## 4. Related internal-API knowledge (pointers)

- Backoffice internal REST recipes + Global Brand Catalog: SKILL §"Backoffice Internal
  REST API" + memory `reference_dutchie_internal_api.md`.
- Category/Tax/PLC config endpoints: the estate's `category-qc/extract.md`.
- Fields-config (get_validated_forms): the estate's `fields-config/README.md`.
- Smart-tag rule surface: the estate's `smart-tag-13948-roster-2026-08-26.md`.

## 5. Ingestion queue (articles spotted, not yet read)

- Automate inventory tagging with smart tags
- Customize which product and inventory fields are hidden, shown, or required
- Manage location-specific product details (→ loc-override-qc kickoff)
- Customize package ID, batch ID, and SKU formats
- Manage product categories in Dutchie POS
- Bulk update prices and costs in Dutchie Backoffice

## Watch-list (repurposed-field / platform-evolution risks)

**⚠ AMENDED same day — field-test failures [TENANT 2026-08-27]:** writes to the
MO-Metrc Unit fields FAILED in this MA tenant (failure mode TBD — likely state-gated
form rendering or rejected saves), and the Distillation list has no tenant seeding
surface. Working architecture instead: Conc Wgt = permanent FE-back-derivation
`(FE − g)/4.6`; Conc Type = NAME-CARRIED (vocab-governed token, BI/API-derived +
consistency-QC'd); CBD dose = **`CBD Content`** (plain field, mg default — WORKS;
scoped by QC to Category-CBD only). Vocab: never "Live"+Rosin; composites join with
" + ". Lesson for the KB: **MO-only Metrc fields are not writable in MA tenants even
though they appear in the API schema** — virgin-field census alone doesn't prove
writability; field-test before architecting on a dead field.

Original slate (superseded parts struck in Dictionary R31, kept for context):

- `Distillation` = concentrate-type vocabulary (broader than distillation literally).
- `Unit THC Content Dose` = **concentrate GRAMS** (infused/composite lane) — the big
  repurpose: a mg-dose-named field holding gram mass. Spendable because the fields are
  Missouri-Metrc-only and the non-unit siblings (`THC Content`/`CBD Content`) stay
  Hidden as reserved backups if a literal per-piece-THC home is ever needed.
  ⚠ Sibling asymmetry is deliberate: UnitTHC holds grams-mass while UnitCBD holds
  mg-dose (Adam ruling with the backup-fields rationale).
- `Unit CBD Content Dose` = per-piece CBD mg — native meaning, not a repurpose.
- `Serving Size` = per-PIECE THC mg; `Servings Per Unit` = physical pieces with
  EXPLICIT 1 (Unflavored doctrine — blank means not-yet-backfilled, never single; a
  scored bar is 1 piece per the pieces ruling; regulatory 5mg servings stay
  label-side). SPU goes Required (incl. non-cannabis counts) after backfill; the
  other four stay Show (lane-specific — blank is lane-legitimate).
- If Dutchie ever renders Serving-named fields shopper-facing, recompute semantics
  from the grams identity (`grams = ServingSize × SPU`).
- VERIFY (queued probe): MA's `/api/metrc/get-metrc-product-master-required-fields`
  excludes UnitThc/UnitCbdContentDose (belt-and-suspenders on the MO-only claim).
- `/api/flower-equivalencies/list` + the §2 feature = candidate platform home for R1
  flat-ratio classes; infused composites stay house-side (see hazard above).

## Sources

- How Catalog attributes apply to Inventory in Dutchie POS —
  https://support.dutchie.com/hc/en-us/articles/31454734671507 (read 2026-08-27)
- Set up automatic flower equivalency calculations in Dutchie POS —
  https://support.dutchie.com/hc/en-us/articles/40478745844243 (read 2026-08-27)
- Retire products (hide-not-delete semantics) —
  https://support.dutchie.com/hc/en-us/articles/12882339814035 (read 2026-08-28 by task session)
- Combine duplicate products (Change-product flow) —
  https://support.dutchie.com/hc/en-us/articles/12882362921491 (read 2026-08-28 by task session)

## Category exports: label vs slug, and the item-level GC/GSC surface (2026-08-30)

Dutchie exposes Global Category / Global SubCategory in **two incompatible
representations**, and mixing them silently manufactures phantom diffs:

- **Categories UI export** → GSC as a **display label** (`Whole Flower`, `Pre-Roll Packs`,
  `Flavored Tinctures`).
- **`get-product-categories` config API** → GSC as a **slug** (`whole-flower`, `packs`,
  `flavored`).

⚠ **The label→slug mapping is NOT a slugify.** Slugs are GC-scoped short forms:
`Pre-Roll Packs`→`packs`, `Flavored Tinctures`→`flavored`, `Unflavored Tinctures`→
`unflavored`, `Single Infused Pre-Roll`→(was)`infused`. A naive slugify comparison
produced 65 false diffs in one pass, and a second slugify-based reconciliation invented
6 more false "drift" rows. **Never diff a UI export against an API snapshot at GSC
grain.** A UI export is authoritative for Master Category / Tax / PLC / Global Category
ONLY.

**The arbiter (new surface, first seen 2026-08-30):** the **item Catalog export gained
`Global Category` + `Global SubCategory` columns, in SLUG form** — the first time GC/GSC
is readable at item grain. Use it to (a) settle any category-level GSC question where the
category holds ≥1 item, and (b) detect **item-level GC/GSC overrides** by checking whether
a category's items carry more than one distinct GSC value (first run: zero mixed-GSC
categories, so no override drift existed). Empty categories remain unresolvable from item
data — they need the API replay.

**Practical consequence:** category-config QC needs BOTH pulls — the API snapshot for
ids + slugs, the item export for item-grain verification. Neither alone is sufficient.

## [DOC] Catalog content auto-update after a match (2026-08-30)

`support.dutchie.com` article **12883855947027** — *Utilizing the Dutchie Catalog | Adding Product
Images and Descriptions to Your Menu from Dutchie Connect* — states verbatim:

> "After a match is saved, your menu will automatically receive any catalog updates made for that
> product. The ability to push product updates out in real time ensures that your menu stays up to
> date on packaging or other marketing changes, with no manual effort on your part."

Also documented there: matching never overrides an existing potency or Sativa/Hybrid/Indica/CBD
type; it only fills empty type/potency fields. Wrong matches are corrected by selecting the right
match and saving again; the library connection is removed by editing the Product Name away from
the pre-populated catalog name.

⚠️ **[PROBE] contradicts this on the Backoffice path (pilot tenant, 2026-08-30).** Auditing 337 Backoffice
Global-Brand-Catalog links: **26 (~8%) still serve a copy of the catalog image as it existed when
the link was made**, up to 17 months stale (e.g. Rove Skywalker OG local 2024-04-25 vs brand
2025-10-30). Unlink+relink pulls the current image, so the asset is available — it simply does not
propagate. Open question whether the documented auto-update covers only Connect matches made from
the **E-Commerce admin**, not **Backoffice → Catalog → Global Brand Catalog** links. Ticket drafted
in the client's `tickets/2026-08-30-catalog-image-updates-not-propagating.md`.

**[PROBE] Image linkage mechanics (2026-08-30):** the local image row's `CatalogImageId` points at a
specific catalog image *version*; the file served is a local copy on `leaflogixmedia.blob…`, not a
live reference to the brand's `dutchie-images.s3` asset. Detection of staleness = local
`CatalogImageId` not present in the linked record's current `images[]._id`. A local id **newer**
than anything on the brand record = orphaned reference; the UI re-sync will not stick (3 SKUs).

**[DOC] No documented size limit for POS catalog images.** Article 12882291561491 gives upload steps
only. Ecom dimensions (Product 1600x1600, Banner 3019x900) are documented separately and are Ecom-
only. Six pilot-tenant SKUs had brand catalog images rejected as too large against an undocumented limit.

## [DOC-ADAM] Ecom Admin vs Backoffice Global Brand — the omega content pipeline (2026-08-31)

Stated by Adam; supersedes any inference that the Backoffice item image/description is what the
menu publishes.

- **Pre-beta:** Ecom automapped its own canonical product; Backoffice content did not drive the menu.
- **On omega TODAY:** **Ecom Admin is still the source of truth**, with **Global Brand able to
  overwrite it**. A **separate toggle** governs whether Global Brands may overwrite
  titles / descriptions / images.
- **"Broken integration":** a user editing the menu page in **Ecom Admin** breaks the integration for
  that item. This is *independent* of the Global-Brand overwrite path — i.e. a Global Brand can still
  overwrite content you had already overwritten in Ecom Admin.
- **Direction of travel:** Backoffice Global Brand linking/control is meant to replace all of this.
  Adam's plan at the omega flip: **turn the Global-Brand overwrite toggle OFF** (so the tenant's canonical
  OT/description/image win, per R41), and **wipe the Ecom menu** to reset the broken-integration
  items Shaun overwrote in Ecom Admin.

⚠ **Consequence for QC:** menu impact of any Backoffice-side content defect is **conditional** — on
the toggle and on whether that item was hand-edited in Ecom Admin. Never assert menu impact from
Backoffice data alone. The "broken integration" population is a distinct, un-audited cleanup lane
(relates to R16 Ecom-Admin override work).

## Backoffice bulk-edit grid [PROBE 2026-09-13]

The Catalog grid (`/products/catalog`) is a virtualised MUI DataGrid with two bulk
write paths. Both act on the CURRENT tenant catalog; neither is a Looker surface.

### Scope and selection

- Retired items are behind a filter: **More → Retired products → Save**. It defaults
  OFF, so the grid opens on ACTIVE items only.
- Filters (Brand / Vendor / Category / Tags) offer only values present on ACTIVE
  records — a platform defect. Work around it with the search box and column sorting
  (shift-click multi-sorts, though the server governs the final sort order).
- Search is a single case-insensitive substring match over the row. A SKU works. A
  comma-separated list of SKUs matches nothing.
- Ticking any row reveals a **Bulk actions (N)** button; the button is ABSENT when the
  selection is empty. That absence is the ONLY trustworthy emptiness signal.
- The header checkbox opens a menu: Select all (every page) / Select page / Select a
  quantity / **Select none**.
- **Selection survives a search change.** Search a SKU, tick it, search the next, tick
  it — the count accumulates. This is how to build an exact set on a virtualised grid
  without scrolling, and `(N)` is the invariant to assert before saving.
- **Selection also survives a save**, and clearing the query does NOT clear it. Use
  **Select none** between groups, or a later edit silently re-hits the previous set.

### Path A — Bulk edit product details (selection-scoped)

Modal "Catalog bulk edit": a Field dropdown, a value box, `+ Add field` for several
fields in one save, a trash icon per row, Cancel / Save. Roughly 25 settable fields
including price, cost, flower equivalent, grams/concentration, name, strain, flavor,
category, tags and the online/POS availability flags.

- Field LABELS differ from their internal names (e.g. "Flower equivalent" →
  `FlowerEquivalent`, "Grams/concentration" → `Grams`). Assert the internal name
  after selecting, not the label.
- "Grams/concentration" is the field the catalog export calls `Product grams`.
- The Field dropdown is a MUI Select: it opens on **mousedown**, not `click()`.
- The value box is a plain MUI text input. Real keystrokes work, and a synthetic
  native-setter + `input` event also updates React state here and saves correctly —
  unlike the product FORM's Autocomplete-backed fields, which reject synthetic input.
- Click the value box and CONFIRM focus before typing: a click while the field
  dropdown is still closing lands on the dialog container and the keystrokes vanish.
- Write endpoint `POST /api/product-master/update-products-multiple` → `{"Result":true}`,
  followed by a grid refetch. Success also shows a "Products updated." toast.

### Path B — Bulk update cost and prices via CSV (BETA)

In both the top-level Actions menu and the Bulk actions menu. Opens a "Before you
upload" freshness interstitial, then an upload drop zone.

- Contract: the file needs **ProductId** plus at least one of **Price** or **Cost**;
  add Location price / Location cost only for location-level pricing. **All other
  columns are ignored.**
- ProductId is available as a grid column (historically hidden; enable it in the
  column configuration). Export from the same table to get it.
- A row supplying both Price and Cost where only one differs produces a genuine no-op
  on the other. Reconcile an upload as `changed + already-at-target = rows × columns`,
  never `changed = rows × columns`.

### Traps

1. **Save is enabled with an EMPTY value box.** Saving then blanks that field across
   the whole selection. Guard on field + non-empty value + expected count immediately
   before every Save.
2. **`Bulk unretire products` sits in the same menu**, adjacent to the bulk-edit and
   price-upload entries. On a retired selection it is the catastrophic neighbour.
3. **Reloading clears the selection but ALSO drops the Retired filter**, landing on the
   active catalog. Never reload as a "reset" without re-applying the filter and
   re-checking the row count.
4. **Visible checkboxes can all read unchecked while the selection still holds N.**
   Counting checked DOM checkboxes is not an emptiness check.
5. **`innerText` on a row collapses blank cells and mis-aligns columns.** Read cells
   individually and map by header NAME — the column set changes between sessions, and
   an inserted column shifts every positional index.
6. Grid cells render flower equivalent and grams WITH a `g` suffix; the bulk-edit input
   takes the bare number.
7. Cost is stored to four decimals. Diff money on a half-cent tolerance, never string
   equality.
8. The page-side coordinate frame can differ from the screenshot frame. Scale a
   `getBoundingClientRect()` value by `screenshotWidth / window.innerWidth` before
   using it as a click coordinate, or drive elements by reference instead.

### Recipe

Per group of items sharing one target value: **Select none** and assert 0 → search
each SKU, verify the row's SKU and that it carries no do-not-use tag, tick it, assert
the count rose by exactly one → open the modal, set the field, assert the internal
name, set the value → guard field + value + count → Save → read every touched SKU back
by header-name lookup → **Select none**. Keep a done-list on disk so an interrupted run
resumes without re-writing. A group whose read-back disagrees is a conflict: stop that
group, never retry blind. Certify the whole run with one FULL-ROW diff of a fresh
export against a pre-run baseline, attributing every changed cell to a known
population — an unattributed cell is the finding.

---

## Item creation by Copy item [PROBE 2026-09-13]

Creating a catalog item by copying an existing member of the same product line, rather
than filling the Add-product form from scratch. The copy inherits the whole product
line's lane facts, so only the genuinely variable attributes are edited. Verified on a
three-item vendor-invoice intake.

**The variable attributes of a product line are: Name, Strain and/or Flavor, and the
ecom attributes.** Everything else is a lane fact and should arrive correct by
inheritance. If a field you did not intend to change differs from the siblings, that is
a finding about the source item, not something to fix silently on the copy.

### Where the control is

Item page -> **Actions > Copy** (the menu also holds `Retire`). It is **not** on the
catalog grid — the grid's own Actions menu carries only coupon / bulk-CSV / export /
print. Open the item you want to copy first.

### What the copy carries

Everything: category, type, unit, cannabis flags, grams/concentration, flower
equivalent, price, cost, taxed prices, vendor, brand, servings per unit, tags, the
online-available flag, online title, online description, **and images**.

**Only the SKU is new** — it is issued automatically. Never reuse a retired item's SKU;
this path cannot, which is one of its advantages.

**Strain Type is not an item field.** It derives from the Strain record and updates
itself the moment the Strain is set; it is displayed under the item title. Do not look
for a control for it.

### The name is set before the copy exists

`Copy` opens a **`Confirm copy product`** modal — a pre-save form, not an immediate
write. It carries one field, `Product name`, pre-filled with the source name plus a
**` (Copy)`** suffix (capital C). Replace the whole value with the final name **here**,
then `Confirm`. The name the modal holds is the name the new item is created with, so
the ` (Copy)` string never has to be cleaned up afterwards, and the new name is never
derived by editing the old one in place.

### Field-entry mechanics

- **Strain** is a **modal picker with its own search box**, not an inline autocomplete.
  Click the field, type, and click the option. The option row shows the strain's type
  beneath its name, which is a free pre-flight check that you are taking the right record.
- Where two strains share a prefix (`X` and `X + Y`), both appear. Take the exact one.
- **Plain text inputs are React-controlled and fight synthetic clearing.** `ctrl+a` +
  `Delete` then typing can interleave old and new text into a corrupt value, and a
  same-length result makes that easy to miss. Two reliable options: click the field,
  `End`, then `Backspace` with a repeat count past the full length before typing; or set
  the value with the native property setter and dispatch bubbling `input` + `change`
  events. The native-setter route is proven to register with the framework — the value
  survives save and reload.
- **Verify on the element you actually edited.** A loose selector such as
  "first text input on the page" can return a different field and report a confident,
  false green. Resolve the control from its label, and re-read that same node.

### The ecom payload is a template — attempt the link BEFORE wiping it

The copied description is typically **a strain-specific opening paragraph followed by
reusable brand boilerplate**. Do not wipe it:

1. The boilerplate is worth keeping, and retyping it invites drift. Splice at a stable
   marker (the first words of the boilerplate) and keep the tail byte-for-byte.
2. The existing ecom content is match signal for the global-catalog link, and a
   successful link overwrites the description anyway. Wiping first is both destructive
   and wasted work.

Replace only the strain paragraph. **Sourcing chain:**

1. The brand's own site.
2. dutchie.com — other retailers' menus.
3. Leafly, for the strain itself.
4. **Leafly for the BASE strain**, where the item is a named variant (a backcross, a
   phenotype number, a selection) and the variant itself has no entry anywhere. Write it
   in the house register as a description of the line the cultivar belongs to.

Omit medical claims and potency figures at every rung. Where the house strain record and
a public database disagree on variety, the house record is canon — write the copy so it
does not contradict it.

**Do not manufacture sensory or effects copy from nothing, and do not borrow a
near-name's copy.** Other cultivars sharing a word with yours are different products;
their descriptions are not weak evidence about yours, they are evidence about them.
Rung 4 is the sanctioned fallback precisely because it is honest about what it asserts:
the base strain's character, attributed to the line rather than invented for the variant.
If even rung 4 is unavailable, ship the brand boilerplate alone and flag the item.

**Online title follows the current (non-canonical) ecom convention**, not the canonical
item-name grammar — it tracks whatever the live siblings use. Only the strain name
changes.

### Images

- If the carried image is **generic brand art, leave it** — it is as correct on the new
  item as on the old one.
- If it is **strain- or product-specific**, it is wrong on the new item and must not
  ship. A named product's label art on a different product is a defect, not a placeholder.
- Delete it, and if no replacement can be mined cheaply, **leave the item image-less and
  let the missing-image flag stand as the honest state** for a human to fill last.
- Deleting the local image first is required anyway before adopting brand art, since the
  pre-link image otherwise keeps sort order 1 and stays the customer-facing image.

### Chaining copies

Once one item is finished and image-free, **use it as the source for the next one**. The
next copy then carries no image to delete and carries the governance tag forward. The
source stays a product-line sibling, so the method's premise still holds. Order the run
so the most-edited item is built first and the rest descend from it.

### Governance tag on creation

Apply the estate's item-QC tag at creation. It surfaces the new item on a QC tile until
a human reviews it and removes the tag, which is what makes a deliberately thin
description or a missing image a tracked open item rather than a silent gap. A copy made
from an already-tagged item inherits it.

### The global-catalog link picker

- The picker pre-selects the item's **Global Brand** and lists that brand's catalog
  products. A brand being present globally does not mean *your* product is.
- **Clear any pre-selected Strain Type filter.** It is prefilled from the item's own
  strain type and silently narrows the result set. The control reads `Strain Type (1)`
  when one is set and is bare when none is — check the label rather than opening it.
  Use `Select none`; note that pressing Escape closes the whole modal, not just the
  dropdown.
- **Keep the Category filter** — it usefully excludes wrong-category records. QC it for
  tinctures, which may be filed under edibles.
- **Search the first word of the strain name only**, for partial-match tolerance.
- The picker grid is **virtualised**: reading rendered rows under-reports. The backing
  search call returns `data` (global candidates, with `meta.totalCount`) alongside
  `retailerCatalog` (your own matching item, including its strain id and its
  brand-catalog link id). `totalCount: 0` is real evidence of absence; an empty rendered
  grid is not.
- `status` (`Active` / archived) **is present on the global payload**, so the
  is-it-Active check is machine-readable from this surface rather than eyeball-only.
- **A near-name hit is not your record.** One returned row sharing a word with your
  strain is a different cultivar. Linking it writes that product's art and description
  onto yours. No linkable record is a normal outcome; leave it unlinked.

### Invoice intake caveat

**A vendor's first invoice is not that vendor's list price.** Opening orders carry
new-account concessions and can show a price spread that looks like a potency or volume
tier but is not. Do not carry a first-order price onto a new item as standing cost —
confirm against a repeat order or the vendor's list before treating any price as the
lane's.

An invoice line that matches **no existing product line** is a stop for a human, never
an automatic create: the copy method presupposes a sibling to copy.

### Verification

Read every field back **after saving and reloading the page**, not from the form state
you just edited. A staged value that never registered with the framework looks identical
to a saved one until the reload. Confirm the catalog total moved by exactly the number
of items created, and diff a fresh export against a pre-run baseline with a row guard:
expected additions, zero removals, and zero changed cells on pre-existing rows.

## Product export & attribute bulk update by CSV [DOC-ADAM 2026-09-14]

Backoffice Catalog → Export emits the **Product export**: one row per product, **63 columns**, keyed
on `ProductId`. Its headers are Dutchie's own attribute names, and they are the headers a
Dutchie-side **CSV bulk update** accepts. Per Dutchie (relayed by Adam, 2026-09-14) every column
in this export is an attribute their load can update; five are PROVEN by a load that landed the same
day — `Name`, `Strain`, `Flavor`, `Online title`, `Online description`. Treat the rest as asserted
until a load proves each one.

### The 63 headers, in order

`ProductId`, `SKU`, `Name`, `Abbreviation`, `Product grams`, `Strain`, `Price`, `Rec price`, `Cost`,
`Category`, `UPC`, `Default pricing tier`, `Flower equivalent`, `Alternate description`, `Vendor`,
`Is cannabis`, `Is additive`, `Is available online`, `Is POS available`, `Is retired`, `Taxable`,
`Is finished`, `Is test product`, `Allow automatic discounts`, `Brand name`, `Online title`,
`Online description`, `Default unit`, `Unit type`, `Net weight`, `Net weight unit`, `Gross weight`,
`Non cannabis weight`, `Non cannabis weight unit`, `Low inventory threshold`, `Instructions`,
`Allergens`, `Ingredients`, `Days supply`, `Size`, `WeedMapsOrderable`, `Dosage`, `Flavor`,
`Medical customers only`, `Max quantity per transaction`, `Producer`, `Lineage`, `NDC`,
`Expiration days`, `Tags`, `Location_Price`, `Location_Cost`, `Location_PricingTier`,
`Location_OnlineAvailable`, `Location_POSAvailable`, `Location_MaxPurchasable`,
`Location_LowInventoryThreshold`, `Sync To Metrc`, `Use Sku Number As Serial No`, `Regulatory Name`,
`THC Content`, `CBD Content`, `External ID`.

### Reading the export

- Cells are Excel-formula-quoted: `="value"`, blank is `=""`. Strip per CELL, never per column —
  `Online description` is inconsistent (in one 862-row export, 45 wrapped, the rest plain).
- Booleans come in two vocabularies: `Yes`/`No` (`Is cannabis`, `Is available online`,
  `Is POS available`, `Is retired`, `Taxable`, `Sync To Metrc`, `Use Sku Number As Serial No`)
  and `true`/`false` (`Is additive`, `Is finished`, `Is test product`, `Allow automatic discounts`,
  `WeedMapsOrderable`). Do not normalise one vocabulary into the other on an upload.
- `Product grams` is the bare number (`1`); the 27-column Catalog export from the BI tile prints
  `1g`. Same field, two spellings — see the map below.
- The export follows the grid's state: a grid opened on active items exports active items only
  (`Is retired` = No on every row). Turn the Retired products filter ON before exporting retired
  rows, and confirm the export followed it [unproven — the retired-filtered export has not been
  pulled yet].
- There is **no image column**. An image cannot be set or cleared by CSV; the item form and the
  Copy-item recipe above govern images.
- Multi-tag `Tags` cells: separator unverified (every observed cell held one tag).

### Map to the 27-column Catalog export (BI tile)

| Product export | Catalog export | Note |
|---|---|---|
| `Name` | `Product` | the item name; the upload header is `Name` |
| `Brand name` | `Brand` | |
| `Flower equivalent` | `Flower equiv` | |
| `Product grams` `1` | `Product grams` `1g` | number vs unit-suffixed string |
| `Price` / `Cost` | `Price` / `Cost` | Product export adds `Rec price` and the `Location_*` overrides |
| `ProductId` `SKU` `Strain` `Flavor` `Category` `Vendor` `Tags` `Is available online` `Online title` `Online description` | same names | |
| `Rec price`, `Location_*`, `UPC`, `Dosage`, `Default pricing tier`, `Producer`, `Lineage`, `NDC`, `Allergens`, `Ingredients`, `Instructions`, `External ID` | — | Product-export only |
| — | `Master category`, `Global Category`, `Global SubCategory`, `Strain Type`, `Servings per Unit`, `CBD content`, `Brand catalog product`, `Available` | Catalog-export only — the classification and link surface lives there |

### The CSV bulk-update contract (Dutchie-side load, by support ticket)

- One file per attribute: `ProductId` + the ONE column that changes (an ecom clear carries
  `Online title` + `Online description` together). Rows: only the products that change.
- Values are plain — no `="…"` wrapper — UTF-8 without BOM, CRLF, straight apostrophes.
  Accented letters pass through unchanged.
- A `Strain` value must equal an existing Strain record's name; the load matches, it never mints.
  Create the record first. **The match is case-INSENSITIVE and it sees records the Strains export
  does not list.** Measured on a 624-row Strain load (2026-09-14): 8 rows bound to a NAMESAKE
  record — 2 came back with different casing, 6 with a Strain Type unlike the live record's, 1 with
  no Type — while the Strains export (1,216 records) held no case-insensitive duplicate at all.
  Setting `Strain` also DERIVES the item's Strain Type from the record it bound (595 cells moved
  on that load). Expect both after any Strain load: the string exact, and Strain Type equal to the
  live record's Type; a miss is a re-bind through the item form or the bulk-edit grid.
- **A blank cell CLEARS the field.** Omit every column you are not changing; a blank appears only
  in a file whose purpose is a clear, and the ticket says so in words.
- The Backoffice bulk-edit grid (Path A/B above) is the self-serve alternative: ~25 fields,
  selection-scoped, no ticket — but it cannot carry a per-row VALUE list at estate scale (names,
  strains). Price/Cost alone have the self-serve CSV (Path B). Everything else at scale is this path.
- Retired rows load without un-retiring; say so in the ticket anyway.

### Verification, both sides of the load

1. Before sending: every `ProductId` exists in a frozen export pulled the same day; every value
   differs from the current value or is an intended clear; no duplicate `ProductId`; no blank
   outside a clear file; a row count per file stated in the ticket.
2. After the load: pull the export again and diff FULL rows against the pre-load freeze. Changed
   cells = rows × columns per file; every other cell identical. A cell that moved outside your
   columns is a finding about the load, not about your file.
3. A rejected file re-emits to a NEW versioned filename. A sent file is never edited.

Source: a Backoffice Product export and a four-file bulk update applied in the same day's load
(2026-09-14), read against the BI-tile Catalog export of the same catalog.
