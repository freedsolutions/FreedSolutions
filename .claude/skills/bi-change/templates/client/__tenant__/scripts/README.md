<!-- Generated from "freed-solutions/skills/bi-change/templates/client/__tenant__/scripts/README.md". Edit the repo skill source and rerun ops/notion-workspace/scripts/sync-claude-skill-wrappers.ps1; do not edit this Claude copy directly. -->

# <TENANT> — client scripts

Scripts for this tenant only. The SHARED tools (`bi_impact_scan.js`, `render_docs.sh`,
`explore_catalog_*.js`, the gate) ship in the `bi-change` skill and take `--estate <dir>`;
nothing here duplicates one.

**Three families, and the difference is load-bearing:**

- **QC runners (CONTROL)** — a standing check you may re-run to test a rule. Each obeys the lane
  contract below and appears in the cadence table. These are the only scripts whose output is QC
  evidence.
- **Deliverable generators (GENERATOR)** — they build an HTML, PDF or workbook for a person to
  read, and prove nothing. Output goes to `../deliverables/`, never to `../bi-estate/`, and is
  versioned rather than overwritten. **Never cite a generator as QC evidence.** Several are the
  standing source for a delivered document, so they are not one-offs.
- **One-offs** — `oneoff/`. Written for a single job, kept for provenance, never cited.

`../bi-estate/qc-surface-register.md` §4 is where the CONTROL/GENERATOR line is drawn once for
the whole estate. Its roster is every script a register row CITES, so a script no rule cites has
no row there — and is classed by the same test anyway: if it does not check a rule, it is not
evidence.

## The lane contract

Every QC runner in this folder obeys the six-point lane contract stated once in
`../bi-estate/qc-surface-register.md` §5. It is not restated here — read it there before
adding or editing a runner. In short: cite the rules, default to the freshest input under a
row-count guard, carry `--selftest`, write a new timestamped output, exit 1 only on DEFECT,
and abort on a missing column.

Which lane runs when: the cadence table, same section.

## Adding a runner (a CONTROL)

1. The rule is canon FIRST — a row in `DATA-DICTIONARY.md`, per the runbook (BI-SOP §2 Step 1).
2. Route it: which surface can see the attribute (`qc-surface-register.md` §1–§3).
3. One entry in the runner's rule table citing the R number.
4. `--selftest`: the new flag fires on a synthetic row and stays quiet on its control.
5. A row in the §4 script table, classed CONTROL or GENERATOR.
6. A row in the §5 cadence table saying when it runs.

## Adding a generator

1. If any register row cites it, a row in the §4 script table classed GENERATOR, saying what it
   builds. If none does, no row is needed — but it is still a generator, and still not evidence.
2. Output to `../deliverables/` under a NEW versioned or dated name — a delivered file Adam has
   edited is his, and regenerating over it destroys his edits.
3. No cadence row: a generator runs when someone needs the document, not on a schedule.
