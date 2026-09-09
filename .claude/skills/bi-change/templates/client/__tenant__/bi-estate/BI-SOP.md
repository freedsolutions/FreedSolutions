<!-- Generated from "freed-solutions/skills/bi-change/templates/client/__tenant__/bi-estate/BI-SOP.md". Edit the repo skill source and rerun ops/notion-workspace/scripts/sync-claude-skill-wrappers.ps1; do not edit this Claude copy directly. -->

# <TENANT> BI — Standard Operating Procedures

**The single operating document for the <TENANT> BI estate** (Dutchie Backoffice → BI tools,
Looker). One section per dashboard, all sections in the same shape, so anyone can open a
board and know what each tile is asking, what a row means, and what to do about it.

**Last synced: <date>** — scaffolded from the `bi-change` client template. · Source of truth:
`clients/<client>/<tenant>/bi-estate/BI-SOP.md` (this file) · Shareable copies:
`renders/BI-SOP.docx` / `renders/BI-SOP.pdf`.

---

## 1 · How this document works

**Audience:** anyone operating the BI boards — Adam first, then the team as boards are
promoted to them.

**The three-layer doc stack** (each layer has one job):

| Layer | Document | Job |
|---|---|---|
| **Why** | `DATA-DICTIONARY.md` | The business rules themselves (the R-register). Rules change HERE first. Their history is `DECISIONS.md`. |
| **How it's built** | `dashboard-<id>-*.md` guides | Maintainer reference per board: tile structure, query ids, change history. |
| **How to operate** | **This SOP** | Process + governance: what each tile asks, full flag detail, the change process. |
| **What to click** | `BI-WI.md` | **Work Instructions** — the quick-and-dirty operator layer, one page per board. **Pairing doctrine (Adam): every operating SOP gets a paired WI.** |

**Section discipline:** every dashboard section follows the template in Appendix A — purpose
& cadence, top-level filters, then tile-by-tile in layout order, each tile in the same
five-part shape (*Answers / Healthy state / How to read / Key fields & flags / Fix*). A board
without a section here is not yet "ready for primetime."

---

## 2 · When a business rule changes — the ripple runbook

**This is the single copy of the runbook (Adam ruled 2026-09-02).** `DATA-DICTIONARY.md` §4
Lane 1 points here; the step list that used to live there is retired, because two copies of a
process drift apart in exactly the clauses nobody re-reads.

**Entry point (2026-09-04, Adam ruled).** The runbook's executable form is the `bi-change` skill:
`/bi-change plan <path> "<ask>"` writes the R row(s) and the kickoff (Steps 1–2b) and asks Adam once;
`/bi-change build <kickoff>` executes Steps 3–6 in a new session and closes the kickoff;
`/bi-change check <kickoff>` is the login-free gate that fails any change whose required surfaces are
untouched (scope diff against the pre-build snapshot, rule text unchanged since seal, impl cells no
longer NOT BUILT, `--stale` and `--verify`, Status + done block). Paths: `rule` · `tile` · `new-tile`
· `dashboard` · `retire` · `config` · `sync`. The steps below stay the canon; the skill sequences and
gates them, it does not restate them. Write channel: Playwright under HOLDER.json; the login is
Adam's and the build lane stops and notifies for it.

A master-data business rule change is not done until it has rippled through four
surfaces. **The order matters** — the dictionary leads, BI follows, documents trail,
and the live catalog verifies.

**Step 1 — Data Dictionary first.**
Amend the rule in `DATA-DICTIONARY.md` (R-register row, or §2b for the bespoke
dimensions). Record what changed, who ruled it, and the date. No BI edit happens before
the dictionary says so. Take the next free R-number by fresh-reading the register tail at
write time — and if you only *reserve* a number for a proposal, write a placeholder row the
same day, or the next mint takes the number.

**Step 2 — Impact scan (mechanized), on the OLD string and on every NEW one.**

```bash
node .claude/skills/bi-change/scripts/bi_impact_scan.js --estate clients/<client>/<tenant>/bi-estate "<old string, field name, or /regex/>"
node .claude/skills/bi-change/scripts/bi_impact_scan.js --estate clients/<client>/<tenant>/bi-estate "<new literal you are about to introduce>"
```

Run it once per retiring needle to build the tile worklist and the doc sync list, and once
per literal you are about to introduce — a flag token, a program name, a tag, a room name —
because the document hits show whether canon already forbids the word. The scan sweeps every
estate snapshot — expressions,
filtered-measure filters, baked filters, `fields`, `sorts`, filter chips, merge fields, listen
mappings, titles — attributed to the owning dashboard + tile, plus the expression inventory,
the dictionary, the maintainer guides, this SOP and both WIs. Its output IS the worklist.
Rules that span many tiles are exactly why this step is a script and not a memory exercise.

**Step 2b — Peer-review gate (Adam ruled 2026-09-02).**
Before any write, an instruction that *generalizes* a finding across explores or boards
("verified on one explore, so delete it on its twin too"), or that introduces new
vocabulary, gets a second session's read, because an unreviewed generalization is the error
class no other step catches. State the scope you verified in and the scope you are
applying to, in one line, and let the reviewer say whether they are the same thing.

**Step 3 — Apply to BI.**
Work the worklist via the internal-API recipes (skill `dutchie-bi-looker`). Disciplines
that are not optional: live re-GET before every write (ids rotate, and sessions run in
parallel); rebuild queries with the full four-dim PL chain when the PL dim rides along;
assert a custom dim's slug is in `fields` before editing its expression (a missing slug 200s
and silently keeps the old expression) and never put a table-calc slug in `fields`; verify
`run/json` 200 **before** repointing any tile, even for a sort-only change; content-verify
after every bind (a 200 is not proof); mirror any change on shared/twin queries to all
sharers; Playwright channel only, under the HOLDER protocol.

**Step 4 — Re-harvest, diff, and verify the residual.**
Re-harvest the touched boards; the estate diff is the verification that the change (and only
the change) landed. Then:

```bash
node .claude/skills/bi-change/scripts/bi_impact_scan.js --estate clients/<client>/<tenant>/bi-estate --verify "<old string>"
```

`--verify` greps only the executable surfaces — `dynamic_fields` (expressions AND
filtered-measure filters), query filters, `fields`, `sorts`, filter chips, merge fields, listen
mappings — and lists any raw-snapshot hit outside them as *unexplained*. **Never grep the
whole snapshot:** `vis_config.query_fields[].lookml_expression` is Looker's stale server-side
cache and keeps retired strings forever. Zero structured hits, or the ripple isn't done.
Regenerate the expression inventory to a NEW dated file and record its delta in the guide change log.

**Step 5 — Sync the documents.**
Same pass, not "later": the maintainer guide(s) get the change + a bumped "Last synced"
stamp; **this SOP** gets its affected section updated (filters table, tile entries, flag
glossaries); **the WI (`BI-WI.md`) gets its operator-facing update** — a Means/Do row
for any new flag, a tiles-at-a-glance edit for any new/changed tile, and a dated
**"why" callout** written for the operator. Bump both stamps; regenerate the DOCX/PDFs
(and refresh circulating Google Doc copies). A stamp older than the latest harvest =
stale document. **The dictionary must not run ahead of the operator docs:** a rule changed
in Step 1 whose SOP/WI/guide still sit on the prior stamp is an unrippled change, and
`--stale` flags it. **Close the kickoff:** append an as-built Status section to the kickoff
document, because a build with no as-built record cannot be audited later.
**The WI why-handshake (Adam 8/29):** the WI is only useful with intent attached. If
the change request already states the business WHY and what the operator should now do
differently, write the callout from it. If not, ask Adam ONE compact question before
closing Step 5: *"WI context: why this change, and what should the operator do
differently?"* Screenshots are optional and Adam-supplied for efficiency (drop in
`wi-assets/`, reference from the WI section); tile screenshots reuse `guide-assets/`.
This handshake runs both directions — when Adam gives the why up front, the WI row
writes itself, and the why sharpens the BI implementation too.

**Sourcing rule (added 8/30, learned the hard way).** Meeting notes and AI-generated
summaries are **context, not the decision record**. Mine them for the WHY — rationale,
constraints, and the operator-facing "why" callouts. Take the WHAT from the config
export plus the person who made the change. A generated summary has already inverted a
ruling and invented an executed decision, so raise anything one implies as a question
against live config rather than acting on it.

**Step 6 — Prove the numbers moved only where they should.**
Two halves. **(a) Count invariance on every touched query, every board:** before/after row
and unit counts, expected delta only. Removing an exclusion chip is a write like any other —
prove it inert first — and prove the KEEP half too, because a
chip that looks redundant on one view can be the only thing holding a denominator steady on its
twin. A zero on a new leg is worthless until the same construct is shown to fire somewhere. **(b) QC against the live Dutchie catalog** (when the rule touches catalog
data): run the affected Catalog QC tiles and check the queue against expectation — rows the
rule change should clear are gone, rows it should catch appear — and nothing else. For big
rule changes, pre-verify by simulating the new logic against a fresh Catalog export before
Step 3, then confirm sim = live after. Record the new baseline count in the guide's
change log.

**The short form:**

> Rule changes → 1. Dictionary → 2. `bi_impact_scan` on old + new strings → 2b. Peer read
> on any generalization → 3. Tiles updated (verify-before-bind) → 4. Re-harvest + `--verify`
> → 5. Guides + SOP + WI stamped, kickoff closed → 6. Counts + catalog QC re-baselined.

**Change classes (the ripple generalizes — surfaces per class):**

| Change class | Dictionary | Impact scan + BI | SOP layer | WI layer |
|---|---|---|---|---|
| Business rule (definitions, QC logic, lanes) | R-register / §2b | full (steps 2–4, 6) | this SOP §4+ | `BI-WI.md` flag/tile rows + why callout |
| **Catalog attribute config** (Fields Configure) | R-register + `fields-config/` drift log | only where a QC flag enforces it | `ITEM-CREATION-SOP.md` | intake WI row + why callout (**key context driven by Adam**) |
| Naming convention (templates, tokens) | R-register | full — spans many tiles | this SOP + intake SOP | both WIs' affected rows + why callout |

Freshness at any time: `node .claude/skills/bi-change/scripts/bi_impact_scan.js --estate clients/<client>/<tenant>/bi-estate --stale` compares
every harvest timestamp against every document stamp, checks the dictionary is not ahead of
the operator docs, and checks that every live tile and dashboard filter on a promoted board
appears in this SOP and the WI. It reports what is behind.

---

## 3 · Shared definitions (used across all boards)

**Every definition here CITES its rule and stops.** The rule text lives in
`DATA-DICTIONARY.md` §2 and its history in `DECISIONS.md`; restating either is how the two
copies drift. One line per term: the term, what it means to an operator, and `(Rnn)`.

---

## 4 · Dashboard roster & promotion status

| Dashboard | id | SOP section | Status |
|---|---|---|---|
| <board> | <id> | — | Pending promotion |

Promoting a board = copying Appendix A into a new §, filling it from the live harvest + the
board's maintainer guide, and flipping this row to ACTIVE.

---

## Appendix A · Section template (copy this for each new dashboard)

```markdown
## N · Dashboard SOP — <Board Name> (<id>)

**Purpose:** <one sentence — the board's job.>
**Cadence:** <when this board gets opened, and by whom.>

### N.1 · Filters
| Filter | Default | When to touch it |
|---|---|---|
| <name> | <default> | <guidance> |

<One line on scope: what the defaults deliberately include/exclude.>

### N.2 · Tiles
#### Tile n — <Exact tile title as shown>
**Answers:** <the one question this tile exists to answer.>
**Healthy state:** <"No Results" / a stable baseline / n-a for reference tiles.>
**How to read:** <grain, key columns, anything counterintuitive.>
**Key fields & flags:** <define every derived field a user will see — flag glossaries
as a table (Flag | Fires when | Fix) whenever the tile prints tokens.>
**Fix:** <where in Backoffice + the action. If a row can be legitimate, say how to
tell.>
```

### A2 · The WI page template (BI-WI.md — one page per board)

The WI is PURE REFERENCE for the end user — tiles and flags only. No process, no
roster, no history, no authoring guidance (all of that lives here in the SOP; Adam
ruled the first draft "too verbose and SOP-like" — this is the corrected shape):

```markdown
## <Board Name>
**Job:** <one sentence.> **Open it:** <when.> **Golden rule:** <the one thing.>
**Filters:** <each: leave alone / how you may change it.>
### Tiles
| Tile | What it reports | You act when… |
**Terms:** <one compact line — only groupings this board shows.>
### Flags — <tile>        (one table per flag-printing tile: Flag | Means | Do)
> **Why … (dated):** the change-context callout — Adam's rationale, phrased for the
> operator. Every meaningful change gets one (the why-handshake, §2 Step 5).
```

WI authoring rules: one line per thing · flags always get a Means/Do table ·
screenshots only when they earn their space (Backoffice shots Adam supplies →
`wi-assets/`; skip empty-state tile shots) · keep it printable — a WI page should
run 1–2 pages per board.

Dashboard-section (SOP) template rules: tiles in layout order · every flag token the tile can print gets a
glossary row · plain language, no query ids in prose (the maintainer guide holds those) ·
"review, not always a defect" tiles must say so explicitly.

---

## Appendix B · Keeping this document true

- This file is the master; DOCX/PDF (and any Google Doc copy) are renders. Never edit a
  render.
- Any BI change that touches filters, tiles, or flag vocabulary updates the affected
  section **in the same pass** and bumps the header stamp (ripple runbook Step 5).
- `bi_impact_scan.js --stale` reports when this document's stamp is older than an
  estate harvest.
- Change log:
  - <date> — scaffolded from the `bi-change` client template.
