# Kickoff — <one-line title: what changes, on which board(s), under which R rows>

<!-- bi-change:header -->
```json
{
  "path": "tile",
  "lane": "build",
  "model": "opus",
  "rules": ["R00"],
  "dashboards": ["00000"],
  "scope": { "elements": [], "new_elements": [], "retired_elements": [], "retired_titles": [], "filters": false },
  "baseline": "estate-00000.pre-<slug>.json",
  "retire_needles": [],
  "ratified": false,
  "rule_text_sha1": {}
}
```

Ground rules: the `bi-change` skill (`.claude/skills/bi-change/SKILL.md`) and the client pointer block
`## BI Change Pointers` in the client `CLAUDE.md`. Canon: the Dictionary, then the runbook (BI-SOP §2).
This file is the brief; it does not restate either.

## 1. Rulings, verbatim

- <date> — Adam: *"…"*

## 2. Work items

### A — <tile / rule / board>
- **Now:** what the surface does today, measured (snapshot, export, live probe).
- **Target:** what it must do after, in the Dictionary's words.
- **Expected render / count:** what the tile prints and how many rows, so the build can prove it.

## 3. Order of work

1. No-login work first: measure, simulate on the freshest export, draft doc deltas.
2. Put §5 to Adam in ONE message; set `ratified: true` in the header when every row has a ruling.
3. Login stop → HOLDER acquire → build (run before bind, verify after bind, count invariance).
4. Re-harvest to `estate-<id>.json`; `--verify` each retire needle; docs + renders; Dictionary impl cells.
5. `node .claude/skills/bi-change/scripts/kickoff_check.js <this file>` green; Status + done block; close-out.

## 4. Traps carried forward

- <the specific traps this change is exposed to — cite the skill section, do not restate it>

## 5. Open for Adam

| # | Question | Recommendation | Ruling |
|---|---|---|---|
| 1 | … | … | |

## 6. Status

- <date> — written; nothing built.

<!-- appended by the build lane — on a re-run REWRITE this block in place, never append a second one — verbatim shape:
<!-- bi-change:done -->
```json
{ "built_at": "<ISO>", "harvest": { "00000": "estate-00000.json" }, "elements_touched": [], "counts": { "before": {}, "after": {} }, "open_items": [] }
```
-->

## 7. Paste-ready prompt

```
/bi-change build <absolute path to this file>
```
