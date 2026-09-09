<!-- Generated from "freed-solutions/skills/bi-change/templates/client/__tenant__/CLAUDE.md". Edit the repo skill source and rerun ops/notion-workspace/scripts/sync-claude-skill-wrappers.ps1; do not edit this Claude copy directly. -->

# <TENANT> — <lsp_name> (tenant of <client>)

Client roster and engagement folders: `clients/<client>/CLAUDE.md`. <locations, one clause>.

> **A POINTER, not a log.** Gate caps: ≤ 120 lines, no line over 300 chars. "Current state" is ≤ 8
> bullets, **REPLACED** at every close-out, never appended. The change log is `date — what — record`
> only; the narrative belongs to the record.

## Dutchie Ticket Routing

Fills the header block for the `dutchie-support-ticket` skill.

- Server `<server>` · LSP Name `<lsp_name>` · Location `<location name>`
- Login / Ticket CC: `<email>` · Surfaces: <Backoffice | Ecom | Pro | Kiosk>
- Subject prefix `<prefix>` — <how this tenant's subjects are formed, if it diverges from the skill template>
- Open tickets: <none yet>

## BI Change Pointers

Used by the `bi-change` skill (`/bi-change plan | build | check`). Absolute paths — this folder
is gitignored and absent from task worktrees.

- **Estate dir:** `<abs path>\bi-estate` — DATA-DICTIONARY.md, DECISIONS.md, BI-SOP.md, BI-WI.md, `dashboard-<id>-*.md` guides, `estate-*.json`, kickoffs, `renders/`, `archive/`
- **Scripts dir:** `<abs path>\scripts` — CLIENT measurement scripts; one-offs under `scripts/oneoff/`; the lane contract is `scripts/README.md`
- **Shared BI tools:** `<repo root>\.claude\skills\bi-change\scripts` — `bi_impact_scan.js --estate <dir>` (needle / `--verify` / `--stale`), `render_docs.sh`, `explore_catalog_harvest.js`, `explore_catalog_index.js`.
  Edit the source under `freed-solutions/skills/bi-change/scripts/`, then re-sync the wrapper.
- **Render:** `bash .claude/skills/bi-change/scripts/render_docs.sh <source.md ...>` from the repo root → DOCX + PDF into `<source dir>/renders/`
- **Export QC:** `python clients/<client>/<tenant>/scripts/export_qc.py [export.csv] [--retired] [--json out]` (`/bi-change qc`). Package grain: `inventory_qc.py`. Every runner obeys the lane contract in `scripts/README.md`.
- **Explore catalog sync:** `.claude/skills/bi-change/scripts/explore_catalog_harvest.js` → `bi-estate/explore-catalog-<date>.json` → `explore_catalog_index.js <dump>`
- **Backoffice login:** `<backoffice_url>` — Looker read surface `https://leaflogix.looker.com/embed/preload` (internal API needs `X-CSRF-Token` + `X-Requested-With: XMLHttpRequest`)
- **Write channel:** `playwright` under HOLDER.json; the login is Adam's — the build lane opens the login page and notifies, never handles credentials. Reads: any channel.
- **Canon:** DATA-DICTIONARY.md > skill `dutchie-bi-looker` > memory. Runbook: BI-SOP.md §2. Tickets: skill `dutchie-support-ticket` + the routing block above.
- **Model routing:** plan on the session Adam is in; build in a NEW session; check anywhere.
- **Standing runs:** every lane, its runner and its cadence live in ONE place — `bi-estate/qc-surface-register.md` §5, the cadence table. Read it there; never restate a cadence here.

## Current state (<date>) — replace at close-out, never append

Caps, checked by `node .claude/skills/bi-change/scripts/kickoff_check.js --pointer clients/<client>/<tenant>`: ≤ 8 bullets, each ≤ 2 lines; file ≤ 120 lines; no line over 300 chars; ≤ 10 loose files at the tenant root.
Three conventions this section keeps losing: a bullet is REPLACED at close-out and never appended to; a line never runs past 300 chars; and a bullet NEVER tracks an in-flight version number.
Point at the unversioned record and let the version live inside it, or write the bullet once when the work is approved. Three superseding amendments to one bullet in a day, each legal alone, is the append-log failure in new clothes.

- **Estate:** <boards in Shared folder <folder_id> — id and name each; snapshot date>.
- **Dictionary:** <R-range on the 8-column contract; the record is `bi-estate/DECISIONS.md`; stamp date>.

## Change log

One line per session: `date (lane) — what — record`. The record holds the narrative.

- <date> (scaffold) — TENANT SCAFFOLDED from the `bi-change` client template — `bi-estate/`
