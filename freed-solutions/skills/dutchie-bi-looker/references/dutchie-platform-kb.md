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
- The documented POS public API (`api.pos.dutchie.com`, Basic auth, no session): its own
  section at the end of this file, "POS public API".

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

⚠️ **[PROBE 2026-09-15] "It only fills empty fields" is wrong for the Backoffice link path: it fills
NOTHING.** The earlier reading of the line above — that a link inherits a description or an image
into a blank local field — does not survive a full-population check. The **Manage brand updates**
dialog that the picker raises ships with **every checkbox unchecked**, and the adjacent **Link
without updates** button takes the link and nothing else. Linking a large retired population through
that path moved the link column and no other field: descriptions stayed blank where they were blank,
images stayed absent where they were absent. Treat the documented auto-fill as describing the
**Connect / E-Commerce admin** match, not `Backoffice → Catalog → Global Brand Catalog`. If you want
a field filled, check its box deliberately or write it yourself.

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
- Search is a single case-insensitive substring match over the row ON THE ACTIVE GRID. A SKU
  works there; a comma-separated list of SKUs matches nothing. **With the Retired filter ON the
  search box is INERT** [PROBE 2026-09-22]: real keystrokes set it to a SKU and then to a brand
  substring and the grid stayed at 23 of 23 pages with unchanged head rows, and the captured
  `get-product-master-retired-v2` body never gained a search key — no client filter, no refetch.
  Reach a retired row by sorting a column (SKU ascending works) and paging to the bracketing page.
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
fields in one save, a trash icon per row, Cancel / Save. Exactly 25 settable fields
(internal names, read from the dropdown 2026-09-15): `CustomerTypes`, `BrandId`,
`CBDContent`, `IsCannabisProduct`, `ProductCategoryId`, `Cost`, `DefaultUnitId`,
`ExternalSubCategory`, `Flavor`, `FlowerEquivalent`, `EcomCategory`, `Grams`,
`LowInventory`, `MetrcBrand`, `Name`, `IsOnlineProduct`, `IsPosProduct`, `Price`,
`PricingTier`, `ServingSizePerUnit`, `StrainId`, `SyncToMetrcItem`, `Tags`,
`UnitTypeId`, `VendorId`.

- Strain is `StrainId`, not a string: the value is a strain RECORD picked by name, so the
  bind is exact and a generic entry such as `THC` works here where the product form's
  Autocomplete resists it. Read the bound name back after the save.
- **`Online title`, `Online description` and images are NOT grid fields.** They are written
  on the product form's Online details tab only (see "Online description on the product
  form" below).

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
- The modal is WIDER than the default pane. Emulate a wider viewport before opening it,
  or Save sits off-screen — and inside the modal drive by element REF only (see Traps).

### Path A′ — the same endpoint, called directly [PROBE 2026-09-18]

The picker's own Save posts a flat body, captured from a real UI save:

    {"ProductList":[<productId>, …], "FieldList":[{"StrainId": <id>}],
     "CustomerTypes":[], "TaxCategories":[], "Tags":[],
     "SessionId":"…", "LspId":…, "LocId":…, "OrgId":…, "UserId":…}

- One call per VALUE: `FieldList` carries the same value for every id in `ProductList`, so group the
  work by target value (one call per strain, per flavor; a per-item field such as `Name` is one call each).
- `{"Result":true}` plus HTTP 200 is the success pair; read the row back regardless.
- Field names are the INTERNAL ones (`StrainId`, `Flavor`, `Name`), which the modal also exposes as the
  value control's accessible name once a field is chosen — assert it there before trusting a label.
- Record ids come from `POST /api/strain/get-strains` (`StrainName` → `StrainId`); resolve every name to
  EXACTLY ONE live record first and abort on an ambiguity. This binds by RECORD, which is what makes it
  safe where a CSV load is not: the CSV binds by NAME, case-insensitively, archived records included.
- Cost: the picker path is ~8 browser calls per item (search, tick, two menu clicks, field, record search,
  pick, Save) against one HTTP call per group here. Use the UI to PROVE the payload on a live save, then
  replay its exact shape; a body invented from the form's own state is not the same request.
- Verify with `get-product-master-v2` (active) + `get-product-master-retired-v2` (retired), which return
  `{Data:{products:[…]}}`; compare name, the numeric id and the derived `StrainType` per item.
- **[PROBE 2026-09-19] This call writes RETIRED items WITHOUT unretiring them.** Proven in real runs
  for `StrainId`, `Flavor` (the explicit clear included) and `Name`, each read back afterwards on the
  retired read. The item stays retired throughout; the adjacent `Bulk unretire products` menu entry is
  never part of this path and nothing here needs it.

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
9. **Inside this modal, drive by element REF only.** In a real run a guessed coordinate
   aimed at the value box landed on Save and CLEARED a live field (trap 1, executed).
   Refs also go stale on every re-render, so re-read them after each save rather than
   reusing a ref or a remembered position.
10. **Several guarded writes looped inside ONE in-page call can wedge the tab.**
    [PROBE 2026-09-19] Each write does full catalog read-backs, so a loop that is fine
    one call at a time exhausts the call and times out. After a timeout the helper's
    done-list UNDER-counts — writes that landed are missing from it, so it reads as
    fewer done than there are. Establish state from a fresh read of the LIVE rows, never
    from that list, and continue ONE write per call.
11. **A timed-out write is done-UNKNOWN in both directions, even at one write per call.**
    [PROBE 2026-09-19, two write lanes, 123 writes] A single guarded write can still time
    out. Across seven timeouts six had LANDED and one had NOT, so neither "it failed, retry"
    nor "it landed, move on" is safe: a blind retry double-writes nothing here (the write is
    idempotent) but a blind skip leaves a hole the done-list will not show. Read the live
    row first, then decide. Retired rows are read back on the retired endpoint.
12. **A timed-out in-page JS call poisons that tab's JS channel.** [PROBE 2026-09-19] Every
    later call on the tab hangs or errors until the page is RELOADED. The reload drops the
    pasted helper and its read captures, so: reload → re-paste the helper → re-prove one
    refusal → re-trigger the reads. The retired read does not re-fire on a no-change Save;
    toggle the retired filter OFF then ON to make the app request it again. Until the
    capture is back the helper refuses with `MISSING_READ_CAPTURE` and writes nothing —
    that refusal is the guard working, not a fault.
13. **A page can serve its list from cache and fire no request to capture.** [PROBE
    2026-09-19] Opening Configure → Categories by in-app navigation fired the Tax and
    Purchase-limit lookups but NOT `get-product-categories`. Every call on that screen
    carries the same bare session envelope, so the body captured from a sibling lookup
    replays the missing read. Never hand-build the envelope; borrow a live one.
14. **The virtual scroller keeps its scrollTop across page changes.** [PROBE 2026-09-22] After
    paging deep and jumping back, a page's apparent head row is whatever sits under the retained
    offset, not the page's first row (page 9 read as starting at SKU 38122597; its real first row
    was 35350937), so a bracketing search reads wrong. Set `.MuiDataGrid-virtualScroller`'s
    `scrollTop` to 0 after every page change before reading the head or tail row.
15. **The More-filters dialog gives all THREE of its toggles one DOM id** (`toggle-toggle_`).
    [PROBE 2026-09-22] `getElementById` / `querySelector('#toggle-toggle_')` silently returns the
    first one. Resolve the retired toggle through its own label text ("Show products that have
    been retired"), take the checkbox scoped to that label's row, and read the other two back
    as still off before Save.
16. **A hidden browser tab throttles the write channel.** [PROBE 2026-09-20/21, two write sessions]
    In the Claude Browser pane, a tab the app reports as hidden runs a guarded write at ~37 s
    instead of ~6 s; the fetch outlasts the tool ceiling, the channel wedges (trap 12) and every
    recovery costs a reload plus re-install. 190 names cost three wedges in the first ten items.
    The same 46 + 42 writes in BrowserOS neo — a real, visible window signed in as the operator —
    ran with ONE timeout and no wedge. **Channel rule:** pane-sized write batches (up to ~50
    cells) go through neo, one tab, one writer, the helper injected and hash-verified in-page,
    the envelope captured from the page's own read, progress persisted to disk after every
    call (page storage dies with the tab). Name batches above that go by the bulk CSV that
    support applies (one attribute per file). Never run two writers on one catalog; parallel
    tabs are for read-only work. [PROBE 2026-09-23, 47 writes] neo tabs still hang under the
    full product-master reads (four tabs lost in one lane); keeping the neo window FRONTED helped, and
    every hang was resumed from a live read, never a blind retry. A write in flight on a hung tab can
    still land: the next guard found the unlink already done and refused a second call, so the landing
    time is unknown and recorded as such.
17. **neo's in-page download is gated PER TAB.** [PROBE 2026-09-22, Looker harvest ×3] The first
    anchor-click download on a tab lands; later ones on the same tab are silently dropped while the
    page reports success. One fresh tab per file, and verify each file's size and SHA-256 on disk
    against the in-page digest — that check is what caught it. Also seen on the same run: the
    write-approval prompt is per CALL, not per session, so a denied call mid-loop leaves a partial
    bind; record the bind ORDER so a resume is unambiguous.

18. **The Brands CSV export can serve one cached copy for over an hour.** [PROBE 2026-09-22] After
    Dutchie's own auto-association bound 47 local brand records, two Brands exports pulled 55 minutes
    apart were byte-identical and still showed them unassociated; a third pull minutes later matched
    the live read. Two identical re-pulls prove a CACHE, not a decoupled column — re-pull LATER before
    calling an export wrong, and keep the live read as the arbiter meanwhile. The association read is
    the page's own `POST /api/graphql` `getBrands` (paged, `brandCatalogBrandId` per record) plus
    `batch-catalog-brands` to resolve the id to an active `isGlobal: true` record; the grid shows the
    same state as a verified badge with the global name, versus a `Link to global brand` button.
19. **`search-catalog-brands` is NOT the global brand catalog.** [PROBE 2026-09-22] `SearchTerm: ""`
    returned 438 brands, 128 already linked, and none of the fourteen Global Brands that
    `batch-catalog-brands` resolved by id. A zero here is not evidence that a Global Brand is absent,
    so it cannot serve as an "exactly one resolves" gate; gate on the live association (trap 18).
20. **`Manage brand updates` → `Link without updates` issues NO link call — on RETIRED items [PROBE
    2026-09-22, neo] and on ACTIVE items too [PROBE 2026-09-23, neo, 47 writes].** The 155-field diff
    showed 0 changes; what fired looked like a product-form preflight. The 9/15 probe that recorded the
    button committing server-side is no longer reproducible; treat the button as inert on both states and
    use the direct `link-catalog-product` call (the retired write path below), proving the shape on the
    first guarded call. `unlink-from-catalog-product` works the same way. The same button ignored a
    synthetic `.click()` that drove every other control on the app; it needed a full pointer sequence.
21. **The link picker applies a HIDDEN subcategory filter that can hide an Active approved record.**
    [PROBE 2026-09-22] Three approved records of one brand sat in subcategory `candy` while the items
    were `Gummies`; the picker reported "No matching products found in the global catalog" for all
    three. The records existed and linked by id. "No matching products" is a filter result, not
    evidence of absence — resolve the record by id through the search call before reading it as missing.
    [PROBE 2026-09-23] The picker search returned ZERO records for an entire brand whose records linked
    by id, so the gap is not only a subcategory filter; a whole-brand zero proves nothing either.

Traps 1, 8 and 9 all come from driving the modal. The guarded helper named under *Recipe* does not
drive it: it calls the endpoint directly and REFUSES the bad write rather than warning about it.
Reach for the modal only for what the helper does not cover.

### Recipe

**Default path: `<this skill>/scripts/backoffice_grid_write.js`.** A guarded page-side helper for a
tab you are already signed in to. It is the DEFAULT for a grid write; the picker recipe below is the
fallback for anything it refuses or does not cover. It turns the traps above into hard stops rather
than things to remember — a session read this section on 2026-09-18 and still executed trap 1.

    gridWrite({ productIds, field, value, clear, expectCount, scope, refuseTags, dryRun })

- `dryRun` defaults to TRUE and returns the plan. Refusals are NAMED and stop the run: an unproven
  field, an empty value without an explicit `clear`, a count that disagrees with the id list, a
  duplicate id, a strain id that is non-numeric / unresolved / archived, a product id that does not
  resolve on the read for its `scope`, and an item carrying a caller-supplied refuse-tag. It names
  no tag itself — the caller passes the tenant's.
- It invents nothing. The envelope values are harvested from a request the PAGE made, and each read
  is a replay of the page's own request, so an unobserved endpoint is a stop (`MISSING_READ_CAPTURE`)
  rather than a guessed path. Let the grid issue its own read first; `gridWriteCapture()` reports
  what it has.
- It reads EVERY item back on the matching endpoint and marks any disagreement a CONFLICT, including
  a write that returns the success pair while nothing moves. It never retries blind. Full per-item
  before/after and a resume done-list sit on `window.__gridWrite`, because the in-page JS channel
  truncates near 1 KB.
- v1 allowlist is `StrainId`, `Flavor`, `Name` — what the direct-call entry above proves, each
  carrying its provenance into the plan. `Tags` is deliberately excluded: replace-or-append is
  unproven, and a guess there rewrites governance silently.
- **[PROBE 2026-09-19] `get-strains` is the LIVE list, and that is how an archived strain is
  caught.** The records carry no archive/active field — observed as exactly `StrainId`,
  `StrainName`, `StrainDescription`, `Abbreviation`, `StrainAbbreviation`, `StrainType`,
  `ExternalId` — and the Strains page offers one Type filter, four columns and no archived toggle.
  That absence is the answer, not a gap: a strain id still REFERENCED by catalog item rows (which
  render its name and type) was absent from this read entirely, and strain records that a
  name-bound CSV load had demonstrably bound items to were likewise absent while their live
  namesakes were present — the response carried no case-insensitive duplicate names at all. So an
  archived id simply fails to resolve, and **resolution against this read IS the archive check.**
  The helper refuses it as `STRAIN_ID_UNRESOLVED`; it keeps a flag branch for the day the platform
  grows one. Corollary for the *Product export & attribute bulk update by CSV* entry: whatever
  surface shows archived strain records, it is not this endpoint.
- A record can therefore exist, be referenced by items, and be invisible in both the Strains page
  and its export — unreachable for editing from the UI. Census strain ids from the item rows, not
  from the Strains list, when you need the true referenced set.
- Selftest `scripts/backoffice_grid_write_selftest.js` (node, mocked fetch, no login) proves every
  refusal green on a clean fixture and red on a fixture broken in one place.

Fallback — driving the modal by hand. Per group of items sharing one target value: **Select none** and assert 0 → search
each SKU, verify the row's SKU and that it carries no do-not-use tag, tick it, assert
the count rose by exactly one → open the modal, set the field, assert the internal
name, set the value → guard field + value + count → Save → read every touched SKU back
by header-name lookup → **Select none**. Keep a done-list on disk so an interrupted run
resumes without re-writing. A group whose read-back disagrees is a conflict: stop that
group, never retry blind. Certify the whole run with one FULL-ROW diff of a fresh
export against a pre-run baseline, attributing every changed cell to a known
population — an unattributed cell is the finding.

### Minting a Strain record on the Strains page [PROBE 2026-09-18]

`/products/strains` → **Add strain**. Five controls: Name, Description, Abbreviation (all required),
Type (a MUI Select) and External ID, then Save. House convention fills Name = Abbreviation = Description.

- The Type list is `None / Hybrid / Indica / Indica-Hybrid / Sativa / Sativa-Hybrid / CBD / THC / 1 to 1 /
  2 to 1 / 5 to 1 / 10 to 1 / 20 to 1 / 50 to 1`. Open it, press the first letter, then **`Enter`** —
  the key name `Return` moves the highlight but does NOT commit, so the list stays open.
- **A Save clicked while that list is still closing is swallowed and writes nothing** — no toast, the form
  simply stays filled. Wait ~2s after the commit, click Save, then confirm you are back on the list.
- Every ref goes stale on each save; re-read the page for the next record rather than reusing one.
- Read back by searching the name: the row must appear exactly once with the Type you chose. A search that
  returns two rows means a duplicate mint, not a stale grid.
- The same form edits an existing record (click its name), which is how a record's Type is corrected.
- **RENAME vs RE-BIND reach different things.** [PROBE 2026-09-19, Inventory export] Editing a record
  (its name or its Type) flows to every item bound to it AND to those items' on-hand packages — the
  Inventory export's package `Strain` followed a renamed record with no package edit. Re-binding an item
  to a DIFFERENT record moves the item only: its existing packages keep the old record until each is
  edited by hand. So when one item (or one brand's items) is the record's whole membership, RENAME it;
  mint + re-bind only when other items must keep the old value. A Type change on a shared record
  re-derives Strain Type on every item bound to it — list the membership before changing it. After any
  re-bind of an item with stock, compare package Strain with item Strain on the Inventory export.

### Clearing an attribute through the grid

An empty value box is the supported CLEAR for the selection's field: the same Save that trap 1 warns about
is the intended path when a blank IS the target (proven on `Flavor`, read back as empty on both endpoints).
State the clear in words before running it, and never leave an empty box in a modal you opened for a set.

### Online description on the product form [PROBE 2026-09-15]

`/products/catalog/<ProductId>` → Online details tab. Proven on two records (one append,
one full replacement), each re-read byte-exact after a full page reload.

- Resolve the field by id: textarea `input-input_Online description:`. A bare "first
  textarea" selector also matches `Large online description:` and writes the wrong field.
- Real keystrokes APPEND only. `Backspace` and `ctrl+a` + `Delete` delete nothing even with
  focus confirmed by a real click — the value length does not move. `ctrl+End` does not move
  the caret; `setSelectionRange(len, len)` does, and keystrokes then register at the end.
- A REPLACEMENT goes through the native `HTMLTextAreaElement` value setter plus bubbling
  `input` and `change` events; that enables Save and survives reload. Guard on
  `value === target` immediately before Save.
- Read the LIVE field before composing a replacement: the Catalog export collapses the
  newlines inside a description (a 129-char live value exported as 126), so an export cell
  is not the byte-exact baseline. Copy a sibling's text from the sibling's own field, never
  from a markdown file — a curly apostrophe straightened in transit breaks byte-identity.
- The tool key name is `Backspace`; a wrong name (`BackSpace`) reports success and does nothing.
- **A form Save writes more than the field you edited [PROBE 2026-09-16].** On a record never
  saved through the form, `IngredientList` goes `null` → `""` and `NonCannabisWeightUnit`
  `null` → `0` on the same Save. Both are empty → empty; nothing an operator sees changes. A
  full-row certifier WILL report them, so declare both as a form-Save signature rather than
  calling them drift. A catalog that has been form-edited before already carries the pattern
  on the rows that were saved, so a mixed `null` / `""` census is expected, not a defect.
- **A form Save also DROPS the item's location-override row [PROBE 2026-09-25].** The Save
  posts the full record. When the item carries a location row (`LocationID` set, usually with
  `LocationRecPrice`), every `Location*` field reads `null` after the Save (`LocationID`,
  `LocationRecPrice`, `LocationExternalCategory`, `LocationSalesAccount`). Proven on a one-field
  Name edit (one Save, no location tab opened, no dialog), then at catalog scale: every row with
  the form-Save signature above carried no location row, while a large share of the rows never
  saved through the form carried one. Rows renamed through the bulk-edit grid kept theirs, so
  the grid does neither the normalisation nor the drop.
  **Unknown:** what the row's price fields mean. `LocationRecPrice` is not the same grain as
  `RecPrice` (one probe read the grid Price equal to `LocationRecPrice` while `RecPrice`
  differed, and the Location details tab showed the row as blank / 0), so make no sell-price
  claim from these fields. **Rule until that is settled:** read the product-master row's
  `Location*` fields before any form Save, and do not Save through the form on an item whose
  `LocationID` is set (use the grid, or get a ruling first). In a full-row certify, declare the
  drop with its before values.
- **A page-side `fetch` wrapper must call a BOUND fetch [PROBE 2026-09-25].** A wrapper that
  keeps `const f = window.fetch` and later calls `f(...)` throws Illegal invocation inside the
  app's own request. The item form's Save then stops silently after `validate-sku` and writes
  nothing. Use `window.fetch.bind(window)`, or hook `XMLHttpRequest` only.
- Certify by an API full-row diff of the product-master row, before vs after. A "Product
  updated." toast is not a read-back.

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
  tinctures, which may be filed under edibles. A SUBCATEGORY filter also applies and is not
  shown (trap 21): an approved record in `candy` is invisible to a `Gummies` item.
- **Search the first word of the strain name only**, for partial-match tolerance.
- The picker grid is **virtualised**: reading rendered rows under-reports. The backing
  search call returns `data` (global candidates, with `meta.totalCount`) alongside
  `retailerCatalog` (your own matching item, including its strain id and its
  brand-catalog link id). `totalCount: 0` is real evidence of absence; an empty rendered
  grid is not.
- **`search-catalog-products` IS brand-scopable — the key is PLURAL** [PROBE 2026-09-15].
  `BrandCatalogBrandIds` takes an **array**. The singular spellings are accepted by the
  endpoint and **silently ignored**, returning the unscoped result set, which is what an
  earlier probe measured and wrongly recorded as "cannot be scoped by brand". `SearchTerm: ""`
  is legal and, with the brand ids set, enumerates that brand's whole catalog.
- **The 20 rows are a default PAGE SIZE, not a ceiling** [PROBE 2026-09-15]. Page with
  `Limit` **and** `Offset` together: `Limit` on its own **422s**, and `Offset >= 10000`
  **500s** while `meta.totalCount` saturates at 10,000. Within those bounds absence is
  provable — but a 20-row answer alone never is, so never read "20 returned" as "20 exist".
- **The picker commits the link server-side; the product form's Save is NOT part of it**
  [PROBE 2026-09-15]. Choosing a candidate and pressing **Link without updates** fires
  `POST /api/v2/brands-catalog/link-catalog-product` with
  `{…ctx, BrandCatalogBrandId, BrandCatalogBrandName, BrandCatalogProductId,
  BrandCatalogProductVersion: 0, ProductId}` and the link is live on that response. Driving
  the UI additionally fires a full-form `update-product`; the API path does not need it and
  does not send it. This is why the picker works on a product whose form will not Save —
  see the retired read/write path below.
- **Unlinking is its own call too, and also needs no Save** [PROBE 2026-09-16]. The item
  page's **Unlink from global product** → confirm fires
  `POST /api/v2/brands-catalog/unlink-from-catalog-product` with `{…ctx, ProductId}`. It
  commits on a RETIRED product, and an API replay of the same body commits identically
  (6 of 6, full-row certified: `BrandCatalogProductId` is the only field that moves, and the
  description the item already carries is untouched). Record the old link id before the call —
  the response does not return it, and it is the only way to restore the link.
- **After an unlink the page offers a "potential match" — treat it as a name hit.** It
  proposed a different flavour of the same product line, because the names share every
  word but the flavour. Accepting it is a link like any other: gate it, never click through.
- `status` (`Active` / archived) **is present on the global payload**, so the
  is-it-Active check is machine-readable from this surface rather than eyeball-only.
- **The catalog search returns ALL state libraries, and no server-side filter narrows it** [PROBE
  2026-09-22]. A global record carries `stateLibrary`; a brand that reads 160 records in your state
  reads 1,641 unscoped. `StateLibrary`, `State`, `StateCode`, `StateLibraries`, `Categories`,
  `Category`, `SubCategories`, `SortBy` and `SortDirection` are all accepted and silently ignored
  (`totalCount` never moves), exactly like the singular brand-id key. Apply the state scope
  CLIENT-SIDE on `stateLibrary`, and say so in the harvest file's record — an earlier harvest was
  state-scoped without saying so, and an unscoped re-run would have read five times the records as
  additions. `Limit: 500` is honoured. The rate limit is bursty: ~140 calls/min ran 90 s then 429;
  ~50/min with a 1.2 s pacer and exponential back-off ran the rest clean.
- **`search-catalog-products`, `batch-catalog-products` and `/api/graphql` answer on the browser's
  own cookie with NO session envelope** [PROBE 2026-09-22]. Only the two product-master reads need the
  page's location context. A harvest therefore needs no envelope capture at all; a session that cannot
  capture one is not blocked from the catalog side. In neo, a call that would outrun the 30 s cap is
  started as an in-page background job and polled cheaply, and an oversized `evaluate` result spills
  to a local file, which is a working path to disk when the anchor-click download is dead.
- **`batch-catalog-products` resolves records BY ID, up to 1,000 per call** (key
  `BrandCatalogProductIds`, cookie only) [PROBE 2026-09-22]. It is the arbiter for an apparent
  removal: of 809 ids an older harvest held and a new one did not, 765 still existed (probe gaps),
  11 had left the state library and 33 were gone. A raw set difference would have claimed 809.
  Column mapping for a harvest, proven against an older file: `wg` = `suggestedWeightGrams` (not
  `weightGrams`, null on the rows that matter), `pk` = `suggestedPackSize`, `dose` = `dosageMg`.
- **A bare body on the product-master reads returns 200 with an EMPTY product list** [PROBE
  2026-09-22]. A harvest that tests only the status code reads "no products" as a fact about the
  tenant. Assert the row count against a known population (the export's) before trusting a read.
- **A near-name hit is not your record.** One returned row sharing a word with your
  strain is a different cultivar. Linking it writes that product's art and description
  onto yours. No linkable record is a normal outcome; leave it unlinked.

### Retired products: a separate endpoint, a form that will not Save, a blank export column [PROBE 2026-09-15]

- **Retired products live on their own read.** `get-product-master-retired-v2` returns them;
  `get-product-master-v2` returns **active only**. The grid's *Retired products* toggle is a **saved
  user preference**, not a request-body flag — flipping it changes which endpoint the page calls, so
  a replayed request body will not follow the toggle and a harvest that only ever calls the active
  endpoint reports a retired population of zero without erroring.
- **`IsCannabisProduct` is the STRING `"Yes"` / `"No"` on both endpoints**, not a boolean. A
  truthiness test (`if (p.IsCannabisProduct)`) is true for `"No"` as well, so it counts **every** row
  as cannabis and silently inflates any survivor set built on it. Compare to `"Yes"`.
- **A retired item's product form will not Save — but the link picker does not need it.** Selecting
  a candidate commits through `link-catalog-product` on its own (see the picker section above), so a
  retired product can be linked **without unretiring it**. Verified on retired items linked through
  the picker and read back on `get-product-master-retired-v2`. Any edit that DOES go through the form
  still needs unretire → edit → retire.
- ⚠️ **The Catalog export cannot be used to read a retired item's link state.** `Brand catalog
  product` exports **blank on retired rows even when the link exists and the product card shows it** —
  measured across a full retired export at zero populated rows against hundreds of links written and
  read back on the retired endpoint the same day, while the ACTIVE export matched the API exactly.
  Read retired link state from the API harvest, never from that column. Filed as a Dutchie bug.

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
- Newlines inside `Online description` do not survive the 27-column Catalog export (BI tile):
  a 129-char live value exported as 126 [proven 2026-09-15]. Whether the 63-column Product
  export keeps them is unproven. Neither export is the byte-exact baseline for a description
  rewrite — read the live field.

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
- Retired rows load without un-retiring; say so in the ticket anyway. Re-proven 2026-09-25 on a
  261-row retired `Name` load: 261 cells at target, 0 other cells moved on the full retired export.

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

## POS public API (`api.pos.dutchie.com`) [DOC 2026-09-25 · PROBE 2026-09-25]

The documented integrator API. It is NOT the Backoffice internal REST layer (section "Backoffice
Internal REST API" in the SKILL/patterns): no login, no session context, one key per location.
Spec: `https://api.pos.dutchie.com/swagger/v001/swagger.json` (OpenAPI 3.0.4, "Dutchie Point of
Sale API v1.0.0"; browsable at `/swagger/index.html`). Save a dated copy beside the work that
reads it; the endpoint descriptions carry contract facts that the schemas do not.

### Auth [DOC]

- HTTP Basic. Username = the Location Key; password = the Integrator Key, optional today, so the
  password is empty: `Authorization: Basic base64(locationKey + ":")`.
- **Encode the header client-side.** `GET /util/AuthorizationHeader/{apiKey}` returns a ready
  header value, but the spec calls it a testing convenience, and it puts the key in a URL path,
  which lands in every proxy and server log. A tool never calls it.
- `GET /whoami` is the first call. It proves the header and names the location. Log the location
  name only. Never log a request header or save one with a response.
- The key belongs to the operator. It reaches a session only from an environment variable or a
  secrets file outside the repo, and never appears in a URL, a log, a saved response, a diff or a
  message. A missing key is a stop that asks for it to be set, never a prompt for its value.

### Rate limits [DOC]

- Per endpoint, per Location Key, per minute. Baseline 120 (`GET /products`,
  `POST /products/product`). Bulk operations 10. The tier table lists `GET /inventory` and
  `GET /whoami` at 200, but those endpoints' own descriptions say 120: pace to the lower number.
- A 429 returns `{"Message": ..., "TraceId": ...}`. Back off exponentially. Re-GET before any
  re-POST: a write that threw may have landed.

### Write contract: `POST /products/product` [DOC]

- `ProductId` present = update. `ProductId` absent = create (needs SKU and `productName`).
- **Omitted fields are overwritten with null or zero.** The endpoint's own description says so:
  `Optional<T>` fields keep their value when omitted, regular fields do not. Every update is a
  full echo of a fresh GET, mapped to the upload schema. Never send a partial body, not even as a
  probe. The only proof of a clean write is a GET-vs-GET diff on every field; a 2xx is not proof.
- `isActive` defaults to `true` on the upload schema. A retired item's body must carry
  `isActive: false`, or the write brings the item back to life.
- `bypassExternalUpdate` defaults to `true` (no traceability push). `syncExternally` sends the
  change to the state traceability system; leave it unset for attribute work.
- `description` is deprecated on the upload schema; `alternateName` replaces it.
- Read and write schemas differ. `ProductDetail` (GET, 101 fields) references by id;
  `ProductDetailUpload` (69 fields) takes most references by name (`strainId` -> `strain`,
  `brandId` -> `brandName`, category and tax categories by name) and tags by id. After that
  id-to-name mapping, 26 GET fields still have no upload field (among them `internalName`,
  `flavor`, `dosage`, `effects`, `allergens`, the image fields, `lineageName`,
  `distillationName`, `libraryProductId`). If a write clears one of those,
  this API cannot put it back; restore it through the Backoffice (grid Path A, or the image
  control).
- `POST /products/products` (bulk) is not atomic: it returns HTTP 200 with a mixed array of
  saved records and per-item errors. Check every item. A bad row in a bulk call is hard to
  attribute; prove a shape on single calls first.

### Field identity [PROBE 2026-09-25, read-only, 2,496 rows]

- GET `internalName` = the Backoffice item **Name** (equal to the export's `Product` / `Name`
  cell on every row read).
- GET `productName` = the **Online title** when one is set, otherwise `internalName`.
- The upload schema has **no `internalName` field.** Whether the upload `productName` ("display
  name") writes the Name or the Online title is UNPROVEN: no write has been made. Until a probe
  settles it, rename items through the bulk-edit grid (Path A) or the CSV bulk update by support,
  not through this API.
- The probe that settles it: one retired item whose Online title differs from its Name, full-echo
  body, `isActive: false`. Success = `internalName` moves to the target and the Online title stays.
  If the Online title moves instead, restore it by the same echo call (it is an upload field) and
  treat the route as closed for Names.
- A pre-write guard that compares GET `productName` to the current Name skips every item that has
  an Online title. Guard on `internalName`.

### Reach [DOC + PROBE 2026-09-25]

- `GET /products` returns only products enabled for API access and online availability (spec). On
  the pilot tenant it returned about three quarters of the retired catalog [TENANT]. Reconcile the
  write set against what the API can reach before any pass.
- `GET /inventory` returns only API-enabled products with non-zero stock (spec). One read returned
  0 rows while the Backoffice grid showed stocked items; the cause is not known. Do not use it as an
  on-hand read until that is explained.
- `GET /tags` returns 404. There is no single-product GET: read a product by listing and filtering.
- Responses are bare JSON (no envelope); dates are ISO-8601 UTC with `Z`; ids are integers.
