<!-- Generated from "freed-solutions/skills/bi-change/templates/client/__tenant__/bi-estate/README.md". Edit the repo skill source and rerun ops/notion-workspace/scripts/sync-claude-skill-wrappers.ps1; do not edit this Claude copy directly. -->

# <TENANT> BI Estate — Structure Snapshots

**Last synced: <date>** — scaffolded from the `bi-change` client template.

Machine-readable snapshots of every Looker dashboard in the <TENANT> Shared folder
(<folder_id>), harvested via the internal API. **These files are the canonical record of tile
structure**; business rules live in `DATA-DICTIONARY.md`. Local-only — never committed.

## Files

| File | Dashboard | Notes |
|---|---|---|
| `estate-<id>.json` | <board name> | <harvest date, review state> |

Each doc: `filters` (id, field, **default_value** — the ground truth the UI lies about),
`elements` (id, title, merge_result_id / query_id, `listen` = per-source-query filter
mappings), `merges` (source_queries + merge_fields + merge-level dynamic_fields), `queries`
(fields, filters, sorts, **dynamic_fields with verbatim expressions**). Elements also carry
`look_id` / `look_query_id` when a tile is Look-linked — a Look-linked tile's `query_id`
cannot be trusted without it, because the Look owns the query.

## Documents

| Document | Job |
|---|---|
| `DATA-DICTIONARY.md` | the rules (canon) |
| `DECISIONS.md` | the ruling history behind them |
| `BI-SOP.md` | how to operate; §2 is the ripple runbook, the single copy |
| `BI-WI.md` | what to click, one page per board |
| `qc-surface-register.md` | which rule is checkable where, the lane contract and the cadence table |
| `dashboard-<id>-*.md` | maintainer guide per board |

## Change workflow

One line, on purpose: run `/bi-change` — the skill sequences and gates the runbook (BI-SOP §2),
and its own `SKILL.md` is the only description of the modes, the paths and the gate.

## Drift detection

Re-harvest any time and diff against these files. Expression drift, filter-default drift and
tile re-bindings all surface as diffs. Freshness at any time:
`bi_impact_scan.js --estate <this dir> --stale`.
