<!-- Generated from "freed-solutions/skills/dutchie-bi-looker/references/dutchie-platform-kb.md". Edit the repo skill source and rerun ops/notion-workspace/scripts/sync-claude-skill-wrappers.ps1; do not edit this Claude copy directly. -->

# Dutchie Platform Knowledge Base

Platform-behavior facts: what Dutchie POS actually does, sourced from official support
docs and from live probes. **Portable layer** — sits with mdm-product-line-rules in the
precedence chain (Dictionary > mdm rules > this KB + SKILL mechanics > memories).
Every entry carries its source class and date:
- `[DOC yyyy-mm-dd]` — official support.dutchie.com article (URL in §Sources), as read that day.
- `[PROBE yyyy-mm-dd]` — verified live against the HSCG tenant (API/UI capture).
- `[TENANT]` — HSCG-specific observation; may differ elsewhere.

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
  optional location-specific catalog prices); inventory-level = class B. [TENANT: HSCG
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
- Requires every product category to be associated to a PLC (HSCG: verified complete,
  category-qc).

**⚠ HSCG hazard — infused composites [TENANT 2026-08-27]:** definitions are per-PLC and
cannot exclude categories. HSCG's four infused categories share the **Concentrates PLC**
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
  lists for HSCG = tenant-configurable, unseeded.
- Full candidate-field census (934 items × 153 fields): DistillationId+Name, OilVolume,
  NonCannabisWeight+Unit, ServingSize, ServingSizePerUnit, LineageId+Name, THCContent,
  UnitThc/CbdContentDose — ALL 0-populated (THCContentUnitId=1 default only).
- Item edit form (`/products/catalog/<id>`, SPA soft-nav) fires the lookup set:
  get-product-details-v2, get-strains, get-brands, tax/product-category/get-all,
  distillation, lineage, flower-equivalencies, get-product-extra-info,
  get-product-loc-info, metrc required-fields, mmur/get-devices.
- Fields hidden in Products > Configure > Fields do not render on the item form —
  flip to Show before expecting a field to be settable (fields-config lane:
  `clients/primitiv/bi-estate/fields-config/`).

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
- Category/Tax/PLC config endpoints: `clients/primitiv/bi-estate/category-qc/extract.md`.
- Fields-config (get_validated_forms): `clients/primitiv/bi-estate/fields-config/README.md`.
- Smart-tag rule surface: `clients/primitiv/bi-estate/smart-tag-13948-roster-2026-08-26.md`.

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

⚠️ **[PROBE] contradicts this on the Backoffice path (HSCG, 2026-08-30).** Auditing 337 Backoffice
Global-Brand-Catalog links: **26 (~8%) still serve a copy of the catalog image as it existed when
the link was made**, up to 17 months stale (e.g. Rove Skywalker OG local 2024-04-25 vs brand
2025-10-30). Unlink+relink pulls the current image, so the asset is available — it simply does not
propagate. Open question whether the documented auto-update covers only Connect matches made from
the **E-Commerce admin**, not **Backoffice → Catalog → Global Brand Catalog** links. Ticket drafted
at `clients/primitiv/tickets/2026-08-30-catalog-image-updates-not-propagating.md`.

**[PROBE] Image linkage mechanics (2026-08-30):** the local image row's `CatalogImageId` points at a
specific catalog image *version*; the file served is a local copy on `leaflogixmedia.blob…`, not a
live reference to the brand's `dutchie-images.s3` asset. Detection of staleness = local
`CatalogImageId` not present in the linked record's current `images[]._id`. A local id **newer**
than anything on the brand record = orphaned reference; the UI re-sync will not stick (3 SKUs).

**[DOC] No documented size limit for POS catalog images.** Article 12882291561491 gives upload steps
only. Ecom dimensions (Product 1600x1600, Banner 3019x900) are documented separately and are Ecom-
only. Six HSCG SKUs had brand catalog images rejected as too large against an undocumented limit.

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
  Adam's plan at the omega flip: **turn the Global-Brand overwrite toggle OFF** (so HSCG canonical
  OT/description/image win, per R41), and **wipe the Ecom menu** to reset the broken-integration
  items Shaun overwrote in Ecom Admin.

⚠ **Consequence for QC:** menu impact of any Backoffice-side content defect is **conditional** — on
the toggle and on whether that item was hand-edited in Ecom Admin. Never assert menu impact from
Backoffice data alone. The "broken integration" population is a distinct, un-audited cleanup lane
(relates to R16 Ecom-Admin override work).
