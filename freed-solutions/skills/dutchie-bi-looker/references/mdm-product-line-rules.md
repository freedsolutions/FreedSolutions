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

### Rounding (REVISED 2026-08-19 — "logical rounding")

Both UoM classes round to **0.1** and render decimals **only when they exist** (Adam's
ruling after sorting moved to the numeric Product Grams field, making a fixed-width
"1.0g" unnecessary, and a 0.5mg-per-unit Wyld 20pk exposed the old whole-mg floor):

- smokable / vape-able → `1g`, `3.5g`, `0.5g` (no forced trailing `.0`)
- everything else → `50mg`, `0.5mg` (no forced whole-number rounding)

Conditional concat (no `format()` in Looker):

```
if(round(x,1)=round(x,0), concat(round(x,0),"g"), concat(round(x,1),"g"))
```

(mg branch identical over `x*1000`.) SUPERSEDES the original "always one decimal for g /
nearest whole mg" rule. Sort on `products.product_grams`, never on the label.

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

### Master Category `CBD` — dosage exception (Adam ruling 2026-08-19)

CBD items are flagged `is_cannabis = false` in Dutchie (treated Non-Cannabis for
compliance) but still take **cannabis-style dosage naming**:

- Dosage comes from `Grams / Concentration` (`products.product_grams`), same field as
  everything else — **NOT from the `CBD Content` field** (`products.cbdcontent`), which
  the convention no longer relies on.
- Semantic exception: for MC `CBD`, `product_grams` represents **total mg of
  cannabinoids** (÷1000), not THC content. Everywhere else it is THC.
- Renders in **mg** (CBD is not in the smokable g-list, so it falls through to the mg
  branch by design).
- PT/PL take the cannabis form: `Category | Dosage | Brand`, multipack notation included.
- **FL EQ remains NULL** for CBD items — no expected-value branch, no NO_FLOWER_EQ /
  NO_DOSAGE exposure (those rules gate on `is_cannabis`, which stays false).

### Dosage-attribute presence rule (REFINED 2026-08-20 — grams-driven)

Adam's generalisation of the CBD exception: **the dosage segment renders iff
`product_grams` is populated (> 0)** — the cannabis flag is not the gate.

- Grams present → `Category | Dosage [| Brand]` (g/mg per the MC g-list), regardless of
  `is_cannabis`. CBD gets its mg this way.
- Grams absent → the segment is omitted entirely: PT = `Category`,
  PL = `Category | Brand` (Battery, Lighter, Merch, Apparel).

Canonical form (SQL-context-safe and table-calc-safe):

```
if(coalesce(${products.product_grams},0)>0, <g/mg logic>, <no-dosage form>)
```

Implementations: **Buyers 26549 PT/PL** (all four tiles, rebuilt 2026-08-20) use the
grams-driven gate verbatim. **28006's dims** (193267/193297/193298/193334) use the earlier
`${products.is_cannabis}="true" OR ${products.master_category}="CBD"` gate — equivalent on
current data (QC forces grams on cannabis items; no non-CBD NCI item carries grams), but
align them to grams-driven whenever next touched. QC rules keep the bare `is_cannabis` gate
either way.

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

### Edible-side Strain + Flavor conventions (LOCKED 2026-08-20, flavor workstream)

Applies to non-smokable MCs (Edibles, Beverages, Tinctures, Topical, CBD). Smokable MCs
are untouched: flavor/line names ride Strain there and **Flavor stays empty**.

**Flavor is FREE TEXT** — no dropdown rules to maintain. Format: Title Case, the
brand-printed flavor descriptor minus form/dose/ratio/line tokens ("Sour Blue
Raspberry", "Half & Half"). Variety/mixed packs = `Assorted`. Genuinely unflavored
items = the explicit value `Unflavored` (never blank — blank means "not yet
backfilled").

**Strain on edibles**: named strains where the brand names a cultivar;
**composition-named ratio entries** for stated ratio blends; generic entries otherwise.
Generic entries: `Sativa` / `Hybrid` / `Indica` (brand-printed leans), `THC` (Type
Hybrid — lean-less default; typed Hybrid as an Ecom-effects workaround, Description
disclaims the lean), `CBD` (Type CBD — **pure-CBD / THC-free products only**).

**Ratio entries are composition-named, NOT generic** (Adam correction 2026-08-20 —
supersedes the brief generic-`1to1` convention):

```
StrainName:  <ratio> (<cannabinoid list>)     e.g.  1:1 (THC:CBD) · 2:1 (CBN:THC)
                                                     2:1:1 (THC:CBD:CBN) · 20:1 (CBD:THC)
Type:        the effect bucket (rules below)
```

- **Order**: dominant cannabinoid first; THC first on ties; minors in fixed
  precedence CBD → CBN → CBG → CBC → THCV. Ratios in lowest terms
  (100:100:50 → `2:2:1`). Normalized order, NOT brand-printed order (brands are
  inconsistent: Wyld "CBC:THC" vs InHouse "THC:CBC" — one entry per composition).
- **Only STATED compositions get ratio names** — a ratio format in the name/desc, or
  printed mg amounts (derive the ratio: 50mg THC/300mg CBD → `6:1 (CBD:THC)`).
  Unstated cannabinoid blends ("infused with THC and CBN") ride the generic effect
  lean instead. Name composition-TRUE when the brand print is misleading
  (Incredibles "5:1 CBN" is 5mg THC : 1mg CBN → `5:1 (THC:CBN)`).

**Type (effect bucket) rules for ratio entries**:

- CBD-dominant → **CBD**.
- CBN present → **Indica** (sleep family; CBN-dominant or THC-dominant alike:
  `2:1 (CBN:THC)`, `2:1:1 (THC:CBD:CBN)` all Indica).
- CBG / THCV / CBC leaner **with sativa/energy marketing → Sativa** (marketing
  decides, not mere presence).
- Balanced without an effect signal → **CBD** (Adam ruling 2026-08-20: the "1 to 1"
  Type is RETIRED — CBD absorbs the whole ratio bucket, no 1to1-specific rule; the
  Dutchie dropdown value goes unused). When one composition serves items with
  conflicting marketing (HV Focus vs Trifecta on `1:1:1 (THC:CBD:CBG)`), the shared
  entry defaults to **CBD** — no suffix variants.
- THC-dominant with no marketed lean (`2:1 (THC:CBG)`, `5:1 (THC:THCV)`) →
  **Hybrid** (same workaround as the THC generic).

**Item ladder** (decision order):

1. Brand names a cultivar (LE "Flavor x Cultivar" crosses, terpene-infused
   strain beverages, hash-rosin cultivar lines) → the **named strain**
   (brand-label-wins). Dialed In LE and Happy Valley Live Hash Rosin naming is
   **flavor x cultivar**, NOT a strain cross — the flavor half goes to Flavor.
2. Stated ratio blend → the **composition-named ratio entry** (Type per the bucket
   rules above).
3. Pure-CBD / THC-free → generic **CBD**.
4. Unstated cannabinoid blend → the generic **effect lean** (CBN/sleep → Indica;
   sativa-marketed → Sativa).
5. Printed S/H/I lean, no ratio → the generic lean.
6. No signal at all → **THC**.

Notes: names can lie about composition — verify stated mg before naming. Where a
brand prints both a ratio and a lean (Wyld), the ratio entry wins and the lean
informs only the Type. The ratio name-suffix pattern for smokable/vape lines is
**colon format**: "Strawnana (1:1)", "Mango Passionfruit (2:1)" — Adam renamed the
live entries from the older "(1to1)"/"(2to1)" style 2026-08-20, aligning with the
edible-side colon notation. Type-disambiguation suffixes follow the same parens
pattern ("Pina Colada (H)", "Honeydew (S)") — and **the suffix marks the VARIANT;
the canonical entry keeps the bare name**. Canonical = typically first-created; but
when the bare-name holder is retired-only and an active different-leaner arrives,
rewrite history: the old holder takes the suffix and the active variant becomes the
canonical bare (Watermelon [Indica] + Watermelon (H) [Hybrid, retired refs] — Adam
ruling 2026-08-20).

Two further naming conventions (Adam, 2026-08-20 late):

- **" + " joins two UNIQUE strains co-packaged in one product** (dual disposables,
  two-strain jars, dual rosin) — a joint entry named `Strain A + Strain B`, typed by
  the blend (mixed leans → Hybrid): `Double Krush + Lilac Diesel`,
  `Platinum Candy Pineapple + Guava Now n Later`. Distinct from **" x " = a genetic
  cross** (one cultivar): `GSC x Thin Mint`. Known exception: `Mac + Cheese` is
  Bountiful's brand spelling of a cross — brand-faithful, kept.
- **Brand tier/line names get NAMED entries with type suffixes**, not generics:
  Farnsworth `Bold (I)` / `Classic (H)` / `Light (S)` — SUPERSEDES the earlier
  "subbrand tiers ride generic Blend" ruling. With this, NO smokable item rides a
  bare generic; generics serve only the non-smokable side (plus THC/CBD). True abbreviations of existing entries
collapse even when active (Trop Cherry → Tropicana Cherry; Candy Pineapple →
Platinum Candy Pineapple, both Adam rulings) — contrast brand-distinct spellings,
which stay.

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

Since the 2026-08-19 category granularization, the rule is keyed on **Master Category**
(new categories inherit their class automatically):

| Class (by Master Category) | Expected FL EQ |
|---|---|
| Flower (incl. all non-infused pre-roll categories) | `product_grams × 1` |
| Concentrate, Vaporizer, **Tinctures** | `product_grams × 5.6` |
| Edibles, **Beverages** | `product_grams × 56` (THC grams; beverages are edible-treated — Adam ruling) |
| Infused Flower (Infused Blunt/Bud/Pre-Roll/Pre-Roll Pack) | blended (flower + concentrate×5.6, per-product split) — **NO branch as of 2026-08-19** (Adam removed the bounds check; grams-vs-name inconsistencies are worked on the Dutchie side, not the QC queue) |
| **Topical** | **NO branch — MA Adult Use has NO purchase limit on topicals** (Adam ruling 2026-08-19). Convention CONFIRMED: FL EQ = **0.001g** on every topical item (never eats customer limits, and clears the NO_FLOWER_EQ null-or-zero rule). Any expected-value check would false-positive by design. |
| **CBD** | **NO branch — FL EQ remains NULL** (considered Non-Cannabis; `is_cannabis = false`, so the cannabis-gated rules never fire). Dosage naming still applies — see the CBD dosage exception above. |
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
