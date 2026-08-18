<!-- Generated from "freed-solutions/skills/dutchie-bi-looker/references/mdm-product-line-rules.md". Edit the repo skill source and rerun ops/notion-workspace/scripts/sync-claude-skill-wrappers.ps1; do not edit this Claude copy directly. -->

# Cannabis Master Data — Product Type / Product Line / Variety

Canonical naming and attribute rules for Dutchie catalog master data. Developed within the
bounds of Dutchie's Catalog, with Connect and Global PIM considerations.

**These rules are canon and supersede conflicting guidance elsewhere** — including the
`dutchie-taxonomy` skill, which states that mg-dosed categories take their dosage from
`THCCONTENT`. That is wrong for this setup: see "Dosage" below.

---

## Naming conventions

```
Product Type   single      Category | Dosage
               multipack   Category | Dosage (PerUnit x Size)

Product Line   single      Category | Dosage | Brand
               multipack   Category | Dosage (PerUnit x Size) | Brand
```

Product Type is Product Line minus Brand. Spaces around every pipe.

`PerUnit = Dosage / Count`, where `Count` is the numeric part of `Size` with "pk" stripped.
A 10-pack of 5mg gummies totalling 50mg renders `Edibles | 50mg (5mg x 10pk) | Brand`.

The **Category** component is `products.category` — the finer level — **not** Master Category.
`Infused Pre-Rolls` and `Disposable Vaporizers` are Categories in their own right and must
appear as such; rolling them up to `Pre-Rolls` / `Vaporizer` is wrong.

### Unit of measure

Tied to **Master Category**:

| Master Category kind | UoM |
|---|---|
| smokable / vape-able (Flower, Pre-Rolls, Concentrate, Vaporizer) | `g` |
| everything else (drinkable, edible, topical, suppository, sprays, oral/nasal/inhalers) | `mg` |

Define the `g` list **positively** and let everything else fall through to `mg`. Defining the
mg list positively means a newly introduced category (Suppositories, Sprays) silently renders
in grams.

### Rounding

- smokable / vape-able → round to **0.1g**, always rendered with one decimal: `1.0g`, `3.5g`
- everything else → round to the **nearest 1mg**, no decimals: `50mg`, `5mg`

Looker table calcs have no `format()`, so the forced decimal is a conditional concat:

```
if(round(x,1)=round(x,0), concat(round(x,0),".0"), concat("",round(x,1)))
```

### Dosage

Dosage represents **THC content, taken from the `Grams / Concentration` field**
(`products.product_grams`), expressed in `g`. **Multiply by 1000 to convert to mg.**

- `0.005g` → `5mg` · `0.05g` → `50mg` · `0.1g` → `100mg`
- `1g` → `1.0g` · `3.5g` → `3.5g`

Two traps:

- **`THC Content` (`products.thccontent`) is NOT the dosage.** It is hidden in the Dutchie
  field config for this setup and unpopulated on active items; where a value does exist it is
  the *lab-tested* THC figure, not the label dose. Profiling it as the mg source yields a
  false "the entire catalog is missing dosage" finding.
- There is also a separate hidden `Dosage` field in Dutchie. Not used. Use
  `Grams / Concentration`.

### Size

Used **only for multipacks**, formatted `<count>pk` (`2pk`, `10pk`, `20pk`) — a
Dutchie-specific convention. A null `Size` means single unit and is correct, not a defect.

For **non-cannabis items**, `Size` occupies the **middle attribute** where Dosage sits for
cannabis: `Accessory | 2pk | Brand`, `Apparel | L | Brand`. When absent, the segment is
omitted entirely: `Accessory | Brand`.

---

## Attribute relationships

All of these are many-to-one in one direction only, and each is a QC surface.

| Child | Parent | Notes |
|---|---|---|
| Master Category | ← set on Category | **Free text — must be QC'd.** Many Categories per Master Category; never the reverse. |
| Category | → Global Subcategory | Category is canonical. Many Categories may map to one Global Subcategory. |
| Global Subcategory | → Global Category | Both lists defined by Dutchie, aligned across platforms, chosen from dropdowns in Category config. |
| Brand | → Vendor | Many Brands per Vendor; a Brand under more than one Vendor is a violation. |

**Vendor** is a parent attribute. Used correctly, item-level Vendor is the "house of brands"
that manufactures and typically delivers the product. Third-party distribution produces
different vendors at the *package* level, but the item level keeps the house of brands. This
matters most for Accessories, which should carry the MFG/CPG brand, not the distributor.

**Global hierarchy mappings live in `admin.dutchie.com`**, not the reporting database.
`products.external_category` / `products.external_sub_category` are **Metrc Catalog** fields
(required for manufacturers, not retailers) and are *not* the Global hierarchy — do not QC
Category→Global from them.

Worth surfacing: instances where several Backoffice Categories map to one Global Subcategory
(e.g. "Chews" and "Gummies" both mapping to "Gummies" globally for Ecom/Connect).

Note that Category granularity is not equally correct across every tenant — some are aligned
to Ecom and map cleanly to the Global hierarchy, others need Category made more granular
before the mapping works. Check before assuming a tenant's hierarchy is sound.

---

## Strain, Flavor, Variety

**Strain** carries several attributes, including Dutchie `StrainType` — a Global dropdown
tied to "effects" in Ecom — plus free-text fields.

Best practice:

- smokable / vape-able → **Strain**
- everything else → **Flavor + Strain** (together representing the Variety)

Flavor may be used alongside Strain, or Strain may be cannibalised to carry both, but the
split above is preferred.

**Variety** is a set of Strain-level attribute rules. It resolves to three values across all
products, deliberately simplified for velocity and procurement analysis:

- **THC**
- **CBD** — anything more than 50% CBD, including the less common smokable/vape-able forms
- **Ratio** — several distinct ratios at the same THC level are intentionally grouped

For smokable/vape-able this splits Sativa / Hybrid / Indica; for everything else it splits
THC / CBD / specific ratios, plus Sativa / Hybrid / Indica where applicable.

`Product Line | Variety` is a strong aggregation grain.

### CPG vs. Herb

Every Product Line is either **CPG** or **Herb**, and the distinction hinges on
**Strain-related attributes, not Category**:

- A flavour-specific distillate vape is **CPG** even though it is cannabis distillate, because
  the terpenes are botanical rather than cannabis-derived. Same for "live distillate" lines
  that still have flavours added.
- Pre-roll blends not tied to a specific strain are **CPG**. Some infused pre-rolls likewise.
- Strain-specific products are **Herb** — which is why a strain-specific edible, though best
  avoided, would classify as Herb.

Deriving this from Category instead of Strain attributes gives the wrong answer.

---

## Grain architecture

Best practice: dial in one tile, then duplicate it and move the grain coarser or finer.

| Grain | Purpose |
|---|---|
| **Item / SKU** | Remediation surface — errors are corrected at the item level |
| **PT** — `Category \| Dosage` | Relationship integrity, assortment shape |
| **PL** — `+ Brand` | Procurement grain |
| **PL+V** — `+ Variety` | Blocked until Strain cleanup; expect many errors initially |

Relationship checks (Master Category→Category, Brand→Vendor) **cannot be table calcs** — they
need a group-by, and Looker table calcs have no group-by-within-calc. At item grain each row
sees only itself. These violations become visible at the aggregate grains instead: a Category
sitting under two Master Categories shows up as two PT rows that should have been one.

Strain lives in its own table (the `strain` view in `reference_data`: `strain.name`,
`strain.type`, `strain.abbreviation`, `strain.description`, `strain.strain_id`). Variety rules
should read from there rather than the item-level copies — cleaning a few hundred strains once
beats cleaning them across every item. Many strains can likely be archived; item-to-strain
relationships identify which are actually in use.

---

## QC rules derived from the Dutchie field config

Source of truth for what is enforced: **Products → Configure → Fields**
(`/products/configure/fields`). Fields are `Required`, `Required if Cannabis`, `Show`, or
`Hide`. A blank Required field means someone overrode it via Bulk Edit — which is exactly
what QC should catch.

**Always required:** Name · SKU · Category · Type (weight/qty) · Default Unit ·
Cannabis Product (Y/N) · Price · Cost · Vendor · **Brand**

**Required if Cannabis:** Flower Equivalent · **Grams / Concentration**

**Show (optional but load-bearing):** Master Category · Size · Strain · Tax Categories ·
Default Pricing Tier

The gap worth automating: **`Size` is optional in Dutchie but mandatory for the multipack
naming convention.** Nothing in the platform prevents a "20pk" product from having no `Size`,
yet without it the Product Line cannot render its `(PerUnit x Size)` segment. Brand was the
same shape until it was switched to Required.

`IsCannabis = No` defines Merch / Accessories / Apparel. Cannabis-specific rules
(Flower Equivalent, Grams/Concentration) must be gated on it; naming rules still apply, with
`Size` substituting for Dosage.

### Dosage is NOT a QC rule

Do not encode a "standard dosage grid" per category and flag deviations. Dosage plausibility
is judged by comparing generated Product Lines against the known-good PL list — a bad dosage
surfaces as an **unrecognised Product Line**, which is the correct signal.

An inferred grid produces false positives on legitimate values: infused pre-rolls at 1.2g and
1.4g (1g flower plus infusion weight, or a 2-pack at 0.7g each) are real products that a
naive grid rejects.

### Flower Equivalent IS a QC rule (MA class constants)

Unlike dosage, `Flower Equivalent` follows deterministic per-class math (verified against
the full HSCG catalog 2026-08-18; constants confirmed by Adam — MA: 1 oz = 28 g ≡ 5 g
concentrate ≡ 500 mg THC in edibles):

| Class (by Category) | Expected FL EQ |
|---|---|
| Flower, Pre-Rolls | `product_grams × 1` |
| Concentrate, Vaporizer, Disposable Vaporizers, **Tinctures**, Transdermals | `product_grams × 5.6` |
| Edibles, Drink Mix, **Beverages** | `product_grams × 56` (THC grams; beverages are edible-treated — Adam ruling) |
| Infused Pre-Rolls, Infused Flower | blended (flower + concentrate×5.6, per-product split) — bounds-check only: `grams ≤ FL EQ ≤ grams×5.6` |
| Non-cannabis (gate on `is_cannabis`) | n/a |

**Tinctures deliberately take the concentrate constant (×5.6), not the edible one** — a
100 mg shot carries 0.56 g FL EQ as a Tincture vs 5.6 g as an Edible, a 10× difference
against customer purchase limits. This is why concentrated liquids (THC shots, syrups,
beverage enhancers, drink drops) are POS-classified as Tinctures at HSCG; reclassifying
them to Beverages/Edibles is a compliance change, not a merchandising one.

Implemented as the `BAD_FLOWER_EQ` rule on the Product QC tile (±5% two-sided compare —
SQL context has no `abs()`; precompute 5.32/5.88/53.2/58.8). On first run it caught 17
mis-multiplied beverages and 8 grams-vs-name mismatches. Categories with no branch pass
silently — extend the chain when a new category appears.

---

## Working order

Read the business rules **before** profiling master data. Profiling first and inferring
conventions from the data produces confident, wrong findings — an unpopulated field looks like
a systemic defect when it is simply switched off, and a 90% null rate looks alarming when null
is the correct value for the majority case.
