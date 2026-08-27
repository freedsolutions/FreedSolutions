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

**2026-08-26 rulings (signed, see `clients/primitiv/bi-estate/DATA-DICTIONARY.md` §2b for
the definitions of record):** the pack-annotated PL (`Category | total (per-unit x Npk) |
Brand`) is THE canonical PL everywhere including merge-level tiles (deployed estate-wide; the
inline merge-context expression is output-identical to the custom-dim chain). PT stays
pack-free (`Category | total dosage`). The collapsed strain-lane dimension is renamed
**`Sub Variety`** (+ `Sub Variety Sort`) — never "Strain Type", which collides with Dutchie's
OOTB attribute; it pairs hierarchically under `Variety` (THC/Ratio).

The **Category** component is `products.category` — the finer level — **not** Master Category.
`Infused Pre-Rolls` and `Disposable Vaporizers` are Categories in their own right and must
appear as such; rolling them up to `Pre-Rolls` / `Vaporizer` is wrong.

### Unit of measure

Tied to **Master Category**:

| Master Category kind | UoM |
|---|---|
| smokable / vape-able (Flower, **Pre-Roll**, **Infused Flower & Pre-Roll**, Concentrate, Vaporizer) | `g` |
| everything else (drinkable, edible, topical, suppository, sprays, oral/nasal/inhalers) | `mg` |

Define the `g` list **positively** and let everything else fall through to `mg`. Defining the
mg list positively means a newly introduced category (Suppositories, Sprays) silently renders
in grams.

**Canonical g-list expression (2026-08-26, deployed estate-wide via the MC re-point):**
`${products.master_category}="Flower" OR ${products.master_category}="Pre-Roll" OR
${products.master_category}="Infused Flower & Pre-Roll" OR ${products.master_category}="Concentrate"
OR ${products.master_category}="Vaporizer"`. Two historical defects this fixed: (a) `Pre-Roll`
was missing after the Pre-Roll MC breakout from Flower (pre-rolls rendered in mg), and
(b) the old `Infused Flower` / `Infused Pre-Roll` MC values died when Adam consolidated to the
single free-text MC **`Infused Flower & Pre-Roll`** (2026-08-25; Gift Card also left Merch for
its own MC the same day — both are label seams in transaction/snapshot history). ⚠ MC is free
text: every MC rename silently kills string-matched expressions — this list broke twice in one
week (plural→singular pass, then the infused consolidation). A LEGACY generation of these calcs
keying on pre-granularization CATEGORY names (`category="Beverages"/"Edibles"/"Tinctures"`)
survives ONLY on Inventory Health 26741 (tiles 187558/187559) — rebuild or retire, Adam's call.

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

Implementations: **the entire estate is on the grams-driven gate as of 2026-08-20** —
Buyers 26549 PT/PL (all four tiles) and all 13 naming dims on 28006
(193267 ×4, 193297 ×2, 193298 ×3, 193334 ×4). QC rules keep the bare `is_cannabis` gate.

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
disclaims the lean), `CBD` (**pure-CBD / THC-free products only; Type=Hybrid** since
the 2026-08-26 single-lane doctrine — see Type rules below).

**Ratio entries are composition-named, NOT generic** (Adam correction 2026-08-20 —
supersedes the brief generic-`1to1` convention). **NOTATION REVISED 2026-08-26: the
legend parens are GONE** — `1:1 (THC:CBD)` → `1:1 THC:CBD` (23 in-use entries migrate;
list: clients/primitiv/hscg-ratio-entry-migration-2026-08-26.csv; Adam executes on the
strains screen, items follow automatically):

```
Bare composition:     <ratio> <cannabinoids>       e.g.  1:1 THC:CBD · 2:1 CBN:THC
                                                          2:1:1 THC:CBD:CBN · 20:1 CBD:THC
Branded composition:  <line word> (<composition>)  e.g.  Calm (2:2:1 THC:CBD:CBN)
Type:                 the effect bucket (rules below)
```

- **Order**: dominant cannabinoid first; THC first on ties; minors in fixed
  precedence CBD → CBN → CBG → CBC → THCV. Ratios in lowest terms
  (100:100:50 → `2:2:1`). Normalized order, NOT brand-printed order (brands are
  inconsistent: Wyld "CBC:THC" vs InHouse "THC:CBC" — one entry per composition).
- **Only STATED compositions get ratio names** — a ratio format in the name/desc, or
  printed mg amounts (derive the ratio: 50mg THC/300mg CBD → `6:1 CBD:THC`).
  Unstated cannabinoid blends ("infused with THC and CBN") ride the generic effect
  lean instead. Name composition-TRUE when the brand print is misleading
  (Incredibles "5:1 CBN" is 5mg THC : 1mg CBN → `5:1 THC:CBN`).
- **Branded compositions** (NEW class 2026-08-26): brand effect-line word +
  parenthesized composition — `Calm (2:2:1 THC:CBD:CBN)`. Unifies the suffix grammar
  (always `Name (payload)`, same slot as `Celebrate (H)` / `Bold (Higher THC)`) and
  keeps the type-disambiguation suffix slot free (no `1:1 (THC:CBD) (S)` double-parens).
  Minted only on Adam's approval; a line word over a composition WITHOUT a mint lives
  name-side as a registry device only. **Seasonal editions DO mint** (Adam refinement
  2026-08-26 night): seasonal flavors/strains recur annually, so they get real entries
  (`Bundle Up (6:1 CBD:THC)` — Betty's winter chew). Pride specifically remains
  UNRESOLVED (merch/charity-side question; the last Pride-item QC is parked on it).
- **Print rule (item names / titles)**: entries print **VERBATIM except bare-lean
  suffixes** — the `(Sativa)/(Hybrid)/(Indica)/(Higher THC)/(CBD)` lean-suffix class
  strips from prints; branded compositions print WITH their parens (Adam transparency
  ruling: staff + ecom must see cannabinoids; the Type facet stays an effect bucket by
  design). Renames normalize marketing-simplified prints (HV "Calm 1:1" →
  "Calm (2:2:1 THC:CBD:CBN)").

**Type rules for ratio/composition entries — SINGLE-LANE DOCTRINE (Adam ruled +
executed 2026-08-26 night; verified against the post-migration Strains export.
SUPERSEDES the 8/20 effect-bucket rules — CBD-absorbs-ratio-bucket and
marketing-decides are DEAD for non-smokables):**

- **Type=CBD is SMOKABLE-ONLY.** Dutchie Type is one lane; non-smokable items stay in
  the S/H/I ecom-facet lane. Only rare CBD flower/vape/pre-roll entries carry Type=CBD
  (incl. smokable ratio entries: `Strawnana (1:1 THC:CBD)`, `Mango Passionfruit
  (2:1 CBD:THC)`, and the `Light (CBD)` branded lean). A non-smokable item on a
  CBD-typed entry is a QC VIOLATION (baseline zero, verified 2026-08-26).
- **Deterministic ladder for non-smokable composition entries (ORDER MATTERS —
  first match wins on cannabinoid tokens in the entry NAME; AMENDED 2026-08-26 night
  per Adam — CBC-swing + CBDV, source record bi-estate/qc-backlog-type-ladder.md
  §AMENDMENTS):**
  1. contains **CBN** → **Indica**
  2. contains **THCV** → **Sativa**
  3. contains **CBC** → **Sativa**, UNLESS **CBD is the dominant cannabinoid** →
     **Hybrid** (CBD-dominance mutes CBC's sativa pull; dominant = first-listed
     per dominant-first naming, so the SQL-safe test is "name starts with a
     CBD-led ratio")
  4. contains **CBD / CBG / CBDV** → **Hybrid**
  5. THC/THCA only → **Hybrid**
  Worked examples: Sunrise `5:4:1 THC:CBG:THCV` = Sativa (step 2 before step 4 —
  the order-matters proof); the CBC-swing pair: `Bliss (1:1 THC:CBC)` /
  `Focus (1:1:1 THC:CBC:THCV)` / `Revive (1:1:1 THC:CBG:CBC)` = Sativa vs
  `Ache Away (4:1:1 CBD:THC:CBC)` = Hybrid; Relief `20:1 CBD:THC` = Hybrid despite
  CBD dominance — single-lane proof; `Take It Easy (2:2:1 THC:CBG:CBDV)` = Hybrid
  (first live CBDV entry). `Focus (1:1:1 THC:CBD:CBG)` re-typed Sativa → Hybrid by
  Adam 2026-08-26 — **ladder conformance 100%, zero exemptions** (verified vs the
  final Strains (7)/Catalog (14) QC pass; QC-B enforces the amended ladder).
- **Caffeine carve-out — enumerated whitelist OVER the ladder (Adam, 2026-08-26
  night)**: caffeinated/guarana products marketed as energizing may carry
  **Type=Sativa** over the ladder result, as an enumerated whitelist in QC-B (same
  pattern as the FL_EQ_TIER brand whitelists). First entry: `Focus Energy (1:1
  THC:CBD)` = Sativa (Vibations Half & Half — ladder says Hybrid; caffeine adjunct +
  dispensary-standard Sativa placement). Branded-LEAN entries need no carve-out —
  lean is merch-chosen by definition (`Focus Energy (Sativa)` caffeine trio,
  `Achieve (Sativa)`).
- **The generic `CBD` entry is Type=Hybrid** (re-typed under the doctrine; it still
  serves pure-CBD / THC-free non-smokables — the NAME says CBD, the Type rides the
  ecom-facet lane).

**Item ladder** (decision order — strain-slot precedence FINAL 2026-08-26:
cultivar > branded-composition > bare composition > branded-lean line > lean generic > THC):

1. Brand names a cultivar (LE "Flavor x Cultivar" crosses, terpene-infused
   strain beverages, hash-rosin cultivar lines) → the **named strain**
   (brand-label-wins). Dialed In LE and Happy Valley Live Hash Rosin naming is
   **flavor x cultivar**, NOT a strain cross — the flavor half goes to Flavor.
2. Brand effect-line word over a stated composition, mint approved → the
   **branded-composition entry** (`Calm (2:2:1 THC:CBD:CBN)`).
3. Stated ratio blend → the **bare composition entry** (Type per the bucket
   rules above).
4. Branded-lean line entry (`X (Sativa)/(Hybrid)/(Indica)/(CBD)` class) where minted.
5. Pure-CBD / THC-free → generic **CBD**.
6. Unstated cannabinoid blend → the generic **effect lean** (CBN/sleep → Indica;
   sativa-marketed → Sativa).
7. Printed S/H/I lean, no ratio → the generic lean.
8. No signal at all → **THC**.

Notes: names can lie about composition — verify stated mg before naming. Where a
brand prints both a ratio and a lean (Wyld), the ratio entry wins and the lean
informs only the Type. **SUFFIX GRAMMAR FLUSHED TO FULL WORDS 2026-08-26** (zero
short suffixes remain, verified): lean suffixes are `(Sativa)/(Hybrid)/(Indica)/
(Higher THC)/(CBD)` — never `(S)/(H)/(I)`; smokable ratio suffixes carry the FULL
composition — `Strawnana (1:1 THC:CBD)`, `Mango Passionfruit (2:1 CBD:THC)` — never
the bare `(1:1)` form. Type-disambiguation suffixes follow the same full-word parens
pattern ("Pina Colada (Hybrid)", "Honeydew (Sativa)") — and **the suffix marks the
VARIANT; the canonical entry keeps the bare name**. Canonical = typically first-created; but
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
  bare generic; generics serve only the non-smokable side (plus THC/CBD).

### Branding wins all (Adam ruling 2026-08-21 — SUPERSEDES abbreviation-collapse)

**Each brand's published spelling of a strain gets its OWN entry** — one entry per
brand-spelling, never one canonical absorbing variants. The 2026-08-20
abbreviation-collapse rule (Trop Cherry → Tropicana Cherry; Waui → Maui Waui;
Candy Pineapple → Platinum Candy Pineapple) is RETIRED; Trop Cherry and Waui were
re-minted as their own entries. Live per-brand splits: `Maui Waui` (Rove) / `Waui`
(Rove Classics cart line — Rove brands BOTH) / `Maui Wowie` (Jeeter, InHouse) /
`Mowie Wowie` (Dime) · `Granddaddy Purp` (Rove, Baby Jeeter) / `Granddaddy Purple`
(The Tank, Fernway) · `Watermelon Zkittlez` (Rove) / `Watermelon ZKZ` (Jeeter) ·
`Truffle Popz` (Advanced Cultivators) / `Truffle Pops` (QIC House) · `Superglue`
(InHouse) · `Glitterbomb` (Impressed) · `BrrBerry` (Pride Packz).

Operating rules:

- **Verify the brand's spelling externally before minting** — internal product-name
  prints are NOT trusted; the brand's own site / official brand menus are the
  authority. (Fernway printed two spellings in-catalog, but fernway.com says
  "Granddaddy Purple" — both items ride that entry and the product names were fixed.)
- **Same-brand inconsistencies are product-name typos, not new entries** (Rove
  "Granddady" Reload; NH "Dosi-Woah"/"Dosi Woah" → normalized to "Dosi Woah").
  Where a short print is the brand's own abbreviation of its full strain name, the
  product name is expanded to match the entry instead (Beast Coast Berry Cannon;
  Platinum Candy Pineapple dispo; Pride Edition (Blue Dream Sour Jack); GMO
  Zkittlez Hitmaker).
- **Renaming an entry requires an inactive-ref check**: an entry still referenced by
  retired items must NOT be renamed to a different strain — create the new entry and
  leave the old one to its retired refs (Grape Stomper [retired refs] kept alongside
  new Grape Stomper OG; Grape Gaspby kept for a retired Mello Farms item). Pure
  spelling/case renames with zero conflicting refs are fine (BrrrBerry → BrrBerry,
  Aj's → AJ's Sour Diesel).
- Type-suffix disambiguation still applies when two brands' identical spellings
  collide on different leans (Honeydew [Hybrid, Muze] vs Honeydew (S) [Sativa,
  Jeeter/Baby Jeeter]).
- After the 2026-08-21 sweep, the only deliberate name≠strain exceptions are the
  Farnsworth tiers (package prints the bare tier name; the (I)/(H)/(S) suffix is
  table-side) and Honeydew (S).

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

**RE-KEYED 2026-08-26 (Adam ruling): the FL EQ rule is GOVERNED by PLC × GC** — Purchase
Limit Category crossed with Global Category, both hardened config attributes — because free-text
MC just demonstrated (twice in one week) that renames silently kill string-matched rules. PLC is
not exposed in the BI explores, so the BI implementation uses **category enumerations as
documented SHIMS** for the PLC × GC rule (the infused gate below enumerates the four infused
categories); swap for the real key if Dutchie ever exposes PLC. The MC names in this table are
the current canonical singulars, kept for readability:

**Multiplier ruling LOCKED 2026-08-25**: the estate constant is **×5.6 (28 g oz ÷ 5 g)** —
never 5.67 (28.35/5), never a vendor's own multiplier. The multiplier is OUR standard; the
**concentrate grams are a product FACT** (label/COA stated-actual when known, house 20% of
product grams as fallback). Composite formula: `FL EQ = (grams − conc) + conc × 5.6`.
Known-good tiers: house 20%, Rove 35%, InHouse ~42.6% stated, Nimbus 0.2 g kief on 3.5 g.

| Class (current MC labels) | Expected FL EQ |
|---|---|
| Flower **and Pre-Roll** (non-infused; PLC=Flower) | `product_grams × 1` |
| Concentrate, Vaporizer, **Tincture** (PLC=Concentrates, GC≠Pre-Rolls/Flower) | `product_grams × 5.6` |
| **Edible, Beverage** (PLC=Edibles) | `product_grams × 56` (THC grams; beverages are edible-treated — Adam ruling) |
| **Infused Flower & Pre-Roll** (PLC=Concentrates, GC=Pre-Rolls/Flower; gate = the 4 infused categories) | composite `(g − conc) + conc×5.6`. **Three-tier QC (deployed 2026-08-26, replaces the old 10–50% FL_EQ_RANGE which false-flagged Nimbus)**: `FL_EQ_NO_INFUSION` = FE ≤ g (hard); `FL_EQ_IMPOSSIBLE` = FE ≥ g×5.6 (hard); `FL_EQ_TIER` = FE strictly between but outside 20%±2 (ratio 1.828–2.012) / 35%±2 (2.518–2.702) / brand whitelists InHouse 2.822–3.098, Nimbus 1.124–1.4. All three count in qc_fails and label qc_flags on Product QC 193267. |
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

**2026-08-26 repairs to BAD_FLOWER_EQ**: the singular MC normalization had silently killed
the `Tinctures`/`Edibles`/`Beverages` branches (dead string matches — the edible ×56 band
checked NOTHING for a week), and the Pre-Roll MC breakout had dropped pre-rolls from the 1:1
band. Both restored: bands now match `Tincture`/`Edible`/`Beverage` and the 1:1 gate is
`(MC="Flower" OR MC="Pre-Roll")`. This failure class is the standing argument for the
PLC × GC re-key above.

---

## Working order

Read the business rules **before** profiling master data. Profiling first and inferring
conventions from the data produces confident, wrong findings — an unpopulated field looks like
a systemic defect when it is simply switched off, and a 90% null rate looks alarming when null
is the correct value for the majority case.
