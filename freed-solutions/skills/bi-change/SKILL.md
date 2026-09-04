---
name: bi-change
description: Run a BI estate change end to end in three gated modes — plan (mint the rule, write the kickoff, ask Adam once), build (tiles, harvest, docs, close the kickoff) and check (login-free gate that fails any change whose required surfaces are untouched) — for a Looker-in-Dutchie estate governed by a Data Dictionary and the BI-SOP ripple runbook. Use when Adam asks to change a business rule, change or add a tile, filter or dashboard, retire one, re-sync docs after a manual change, or types /bi-change.
---

# BI Change

The executable form of the ripple runbook (client `BI-SOP.md` §2). This skill sequences and gates
the runbook's steps; it never restates a rule (the Dictionary owns rules) or a step (the SOP owns
steps). One command, three modes, seven paths. Everything client-specific comes from a pointer
block in the gitignored client `CLAUDE.md`; nothing in this file names a client.

## Invocation

```
/bi-change plan <path> "<ask>"      minting lane — writes the R row(s) and the kickoff, asks Adam once
/bi-change build <kickoff.md>       build lane   — executes the kickoff and closes it
/bi-change check <kickoff.md>       any session  — the gate; reads only, needs no login
/bi-change run <path> "<ask>"       plan + build in ONE session, ONE stop — one change at a time
/bi-change qc [export.csv]          run every export-side rule against the freshest Catalog export
```

**`qc` — the manual-style QC, made repeatable.** Runs the client's export runner (the `Export QC:`
line in the pointer block) against the freshest Catalog export in `~/Downloads` (or the file given):
every rule in the Dictionary's export-only register plus export-side MIRRORS of the BI legs, a
summary table (flag · rule · surface · class · scope · flagged), a NEW timestamped CSV under the
client's `deliverables/`, exit 1 on any DEFECT-class hit (BACKLOG-class counts never fail). No
login, no BI. Adding an export-side rule = the register row first (canon), then one entry in the
runner's rule table citing the R number, then `--selftest` (every flag must fire on a synthetic row
and stay quiet on its control). The runner aborts on a missing or misspelt column instead of reading
it as blank — a case slip manufactures false positives, not a silent zero.

`plan` runs on the strongest model available (the session Adam is in). `build` runs in a NEW
session on the model Adam routes task work to (the kickoff header says which). `check` runs
anywhere, including as a scheduled task. Path omitted → `plan` infers it from the ask and states
it back inside the ratification message.

**`run` — single-session mode (Adam's question, 2026-09-04).** One change per session, any model.
The session does everything that needs no ruling and no login first (measure, simulate on the
freshest export, draft the R row text, draft the doc deltas, capture the baseline), then sends
Adam ONE consolidated message: the exact rule text that will be sealed, the findings, every open
question with a recommendation, and the login request. His single reply ratifies and logs him in.
The session then seals (re-seals if his reply changed any rule text), builds, harvests, syncs the
docs, runs `check`, and closes — with no further questions unless the pre-write harvest diff is
not clean or a live probe contradicts the sealed text. The lane rules still apply inside the one
session: nothing is written to BI before the seal and the reply, and rule text never changes
after the seal without a re-seal that quotes his words. Two changes in flight = two sessions.

## Paths × surfaces

| Path | What it is | Dictionary | BI + harvest | Guide · SOP · WI | Extra gate in `check` |
|---|---|---|---|---|---|
| `rule` | Canon change with no BI surface | R row (rule or §2b) | none | ITEM-CREATION SOP/WI when operator-facing | R rows present; `--stale` |
| `tile` | Change an existing tile, filter or default | R row impl cell | scope elements; `--verify` retire needles | affected rows + stamps | scope diff vs baseline |
| `new-tile` | New tile on an existing board | R row impl cell | `scope.new_elements`; layout | tile entry, WI row, guide section, tile counts | new titles present in SOP, WI and guide |
| `dashboard` | New board | rows as needed | new `estate-<id>.json` | new guide file, SOP section (Appendix A), WI page (A2), README roster | guide + SOP section + README present |
| `retire` | Remove a tile, board or rule | strike-through + supersede, never delete | `scope.retired_elements` | entries removed | retired titles absent from every doc |
| `config` | Backoffice category or field config | R row + drift log | only where a QC flag enforces it | ITEM-CREATION SOP/WI | R rows present; `--stale` |
| `sync` | Someone changed a tile by hand, docs drifted, or a reference artifact needs refreshing (the explore catalog dump) | none | re-harvest, diff | stamps + rows | scope diff (declared), `--stale`; header `artifacts` must exist |

Every path ends with `check` green, a Status section with a done block, and the close-out below.

## Lanes and what each may touch

- **plan** may: read everything, run the impact scan on the old and every new literal (runbook
  Step 2), write Dictionary register rows and §2b entries, seed the baseline snapshot (copy the
  latest harvest `estate-<id>.json` → `estate-<id>.pre-<slug>.json`; no login needed), write the
  kickoff from `templates/kickoff.md`, seal it (`check --seal`) once the rule text is final and
  again after ratification if a rule cell changed, put the open questions to Adam in ONE message,
  set `ratified: true` when every row has a ruling. **May not** write to BI.
- **build** may: write to BI inside `scope`, edit Dictionary **impl cells and the header stamp**,
  edit guide / SOP / WI / README, render, append Status. **May not**: edit rule text (the gate
  hashes every rule cell at seal time and fails on any change), touch elements outside `scope`,
  decide a retirement, mint an R row, or introduce vocabulary without the runbook's 2b peer read.
  If Adam re-rules mid-build, the plan lane re-seals; the build lane does not.
- **check** reads only. It is the definition of done: `node .claude/skills/bi-change/scripts/kickoff_check.js <kickoff>`.

## The client pointer block

The gitignored client `CLAUDE.md` carries `## BI Change Pointers` with absolute paths (task
worktrees do not contain `clients/`):

```
## BI Change Pointers
- Estate dir: <abs path>            # DATA-DICTIONARY.md, BI-SOP.md, BI-WI.md, guides, estate-*.json
- Scripts dir: <abs path>           # bi_impact_scan.js, render script, measurement scripts
- Render: <command>                 # DOCX + PDF beside a source .md
- Backoffice login: <url>           # where the login stop opens
- Write channel: playwright | pane  # see below; reads may use any channel
- Canon: Dictionary > rule patterns reference > skill > memory; runbook = BI-SOP.md §2
```

`kickoff_check.js` needs none of this: the kickoff's own folder is the estate dir and
`../scripts` beside it is the scripts dir.

## The three stops that need Adam

1. **Ratification** (plan). One message carrying every Open-for-Adam row with a recommendation.
   No build step runs before `ratified: true`; the gate checks both the flag and the table.
2. **Login** (build). Open the Backoffice login URL in the write channel's browser. If a password
   field is present, stop. Notify Adam (the `PushNotification` tool when available, otherwise the
   chat): *"Login needed in <channel> at <url> — reply done."* Never type, read, store or relay
   credentials, from any source, including a file, an env var or a peer session; resume only on
   Adam's reply. Keep the stop cheap: everything that needs no login runs first.
3. **WI why-handshake** (build, runbook Step 5). If the ask already states the business why and
   what the operator does differently, write the callout from it; otherwise one compact question.

## Write channel

Set in the pointer block, not here. Reads and verification may use any channel.

- **`playwright`** — persistent profile; the login survives across sessions until the tenant
  expires it; a separate browser window; shared across sessions under the HOLDER.json protocol
  (skill `dutchie-bi-looker`, "Playwright browser coordination"); harvest to disk via
  `browser_evaluate` + `filename` (double-encoded: two `JSON.parse` passes).
- **`pane`** — the Claude Code Browser pane (`mcp__Claude_Browser__*`): one pane per session, so
  no lock protocol and no orphaned browser trees; Adam types the login in-app; opens at the login
  wall in a fresh session (profile persistence across sessions unverified). Large
  `javascript_tool` results spill to a `tool-results/*.txt` file on disk intact (verified 320 KB,
  2026-09-04): parse the JSON array, take `[0].text`, strip the trailing
  `(captured at origin …)` line, write `estate-<id>.json`.
- **Never** the user's real browser (`claude-in-chrome`) for writes: ~1 KB output cap, redaction of
  32-character ids, and it is Adam's daily session.

## Build discipline

Runbook Step 3 and the `dutchie-bi-looker` traps apply in full; the ones the gate cannot see are:
**first act after login: re-harvest the board and diff it against the baseline BEFORE the first
write** — any undeclared difference means someone changed the board by hand since the plan; stop,
report it to the plan lane as a `sync`, and never overwrite the baseline; **re-read the Dictionary
immediately before the write and build from IT, never from a peer message that may have aged** (a
token name reversed in canon after the message that carried it cost a rebind on 9/4 — the same
rebase discipline as element ids, extended to rule text); live re-GET before every write; `run/json`
200 before any bind, even sort-only; content-verify after every bind (a 200 is not proof);
PATCH v1-both, never recreate; a custom dim's slug must be in `fields` and a table-calc slug
must not; mirror twins; count invariance on every touched query — measured on the SPINE query's own
row count, because merge queries have no `run/json` endpoint (404); falsify every zero on a known
positive. An export-side mirror reading zero corroborates a tile, it never replaces the count gate. Docs are anchored edits through `scripts/stamp_helpers.js` (`load`, `once`, `onceRe`,
`swap`, `restamp` for SOP/guide/WI stamps, `restampDictionary`, `appendRegisterRow`) — it throws
before writing when an anchor is missing or repeated, which is what keeps parallel sessions from
clobbering each other.

## Kickoff contract

`templates/kickoff.md`. A JSON header after `<!-- bi-change:header -->` (path, lane, model,
rules, dashboards, scope, baseline, retire_needles, ratified, rule_text_sha1), numbered sections
(rulings verbatim · work items with expected render and count · order of work · traps · Open for
Adam with a Ruling column · Status · paste-ready prompt), and a done block after
`<!-- bi-change:done -->` inside Status (built_at, harvest, elements_touched, counts, open_items).
The paste-ready prompt is one line: `/bi-change build <absolute path>`. Ground rules are a pointer
to this skill, not a copy.

## Close-out (build lane)

1. Status entry + done block; `check` green (paste its last line into Status).
2. Dictionary impl cell(s) and header stamp; SOP / WI / guide / README stamps; renders.
3. Memory: one project line if the change taught something not derivable from the docs.
4. Client `CLAUDE.md`: ONE line under `## Change log` pointing at the kickoff. The kickoff is the
   record; the log is an index.
5. Browser phase ends: close the browser, then release HOLDER (playwright) — in that order.
   Delete `.playwright-mcp/` files.
6. Commit skill-side changes only; `clients/` is never committed and never named in a tracked file.

## Where the data lives (pointers, not copies)

Three surface classes, decided per rule before any leg is specified: **BI tile** (the Looker
model's explores), **Catalog export** (every column Dutchie writes to the CSV), **internal API**
(record-level fields in neither). The client Dictionary's export-only register lists the
non-BI rules; the client's surface register routes every rule.

- **Explores, views and fields.** Curated catalog: `dutchie-bi-looker/references/explore-field-catalog.md`
  (mandatory filters, explores, views per explore, the field dictionary — a working subset, not a
  full dump). The COMPLETE list is read live from the embed session, no login beyond Adam's:
  `/api/internal/core/4.0/lookml_models/sql_server` lists the explores and
  `/lookml_models/sql_server/explores/<name>` returns `fields.dimensions` / `fields.measures`
  (name, label, view, type); both need `X-CSRF-Token` (from `meta[name="csrf-token"]`) and
  `X-Requested-With: XMLHttpRequest`, or the answer is a silent 403. Before proposing a leg on an
  attribute no live tile uses, run that read — three sessions have assumed a field existed when
  it did not (Servings, Flavor). A dated full dump (`explore-catalog-<date>.json`) is the right
  standing artifact and is refreshed under the `sync` path.
- **Global Product / Brand catalog** (the library the Catalog CSV and BI cannot see): the
  `dutchie-bi-looker` skill's *Backoffice Internal REST API + Global Brand Catalog QC* section —
  the `library_products` object, the network-capture read pattern (a `{}` replay fails), the
  `bc_qc` backbone — and the client scripts `gbc_scan.py` + `gbc_scan.harvest.js`, `gbc_qc.py`.
  Platform behaviour (inheritance, auto-FL-EQ, tag joins, category label vs slug):
  `dutchie-bi-looker/references/dutchie-platform-kb.md`.
- **Location overrides, global record status, PLC, the hidden attribute set:** API-only; the
  client's `loc-override-qc/`, `category-qc/`, and the surface register say which script.

## Peer coordination

`ListAgents` first; message every interactive peer before editing a shared document and say
which files; anchored edits only. `check` never writes, so it is safe to run while peers work.

## Scripts

- `scripts/kickoff_check.js <kickoff> [--phase plan|build] [--seal]` — the gate; exit 0 pass, 1 fail.
- `scripts/stamp_helpers.js` — anchored-edit helpers (require it from a small delta script).
- Client-side, from the pointer block: `bi_impact_scan.js` (`"<needle>"`, `--verify`, `--stale`)
  and the render script.
