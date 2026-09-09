<!-- Generated from "freed-solutions/skills/bi-change/templates/client/__tenant__/scripts/README.md". Edit the repo skill source and rerun ops/notion-workspace/scripts/sync-claude-skill-wrappers.ps1; do not edit this Claude copy directly. -->

# <TENANT> — client scripts

Measurement and QC runners for this tenant only. The SHARED tools (`bi_impact_scan.js`,
`render_docs.sh`, `explore_catalog_*.js`, the gate) ship in the `bi-change` skill and take
`--estate <dir>`; nothing here duplicates one. One-offs live in `oneoff/` and are never cited
as evidence.

## The lane contract

Every QC runner in this folder obeys the six-point lane contract stated once in
`../bi-estate/qc-surface-register.md` §5. It is not restated here — read it there before
adding or editing a runner. In short: cite the rules, default to the freshest input under a
row-count guard, carry `--selftest`, write a new timestamped output, exit 1 only on DEFECT,
and abort on a missing column.

Which lane runs when: the cadence table, same section.

## Adding a runner

1. The rule is canon FIRST — a row in `DATA-DICTIONARY.md`, per the runbook (BI-SOP §2 Step 1).
2. Route it: which surface can see the attribute (`qc-surface-register.md` §1–§3).
3. One entry in the runner's rule table citing the R number.
4. `--selftest`: the new flag fires on a synthetic row and stays quiet on its control.
5. A row in the §4 script table, classed CONTROL or GENERATOR.
6. A row in the §5 cadence table saying when it runs.
