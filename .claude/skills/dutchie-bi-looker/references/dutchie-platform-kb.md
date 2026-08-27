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

- `Oil Volume` = concentrate grams (house convention; field name says volume).
- `Serving Size` = per-PIECE mg; `Servings Per Unit` = physical pieces, blank = single
  (pieces ruling; NOT regulatory 5mg servings — a scored bar is 1 piece). If Dutchie
  ever renders these shopper-facing, recompute from the grams identity.
- `Distillation` = concentrate-type vocabulary (broader than distillation literally).
- `/api/flower-equivalencies/list` + the §2 feature = candidate platform home for R1
  flat-ratio classes; infused composites stay house-side (see hazard above).

## Sources

- How Catalog attributes apply to Inventory in Dutchie POS —
  https://support.dutchie.com/hc/en-us/articles/31454734671507 (read 2026-08-27)
- Set up automatic flower equivalency calculations in Dutchie POS —
  https://support.dutchie.com/hc/en-us/articles/40478745844243 (read 2026-08-27)
