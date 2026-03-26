# Record Lifecycle

> Context card — extracted from `ops/notion-workspace/CLAUDE.md`. Verify against the canonical source if stale.

## Record Status Flow

`Draft` -> `Active` -> `Delete`

## Who Controls Each Transition

| Transition | Controller |
|-----------|------------|
| Create (Draft) | Agents and manual workflows |
| Draft -> Active | Adam only |
| Active -> Delete | Adam only (set `Record Status = Delete` + annotate notes, then trash) |
| Archiving (UI) | Adam only — hides from views but preserves wiring and remains searchable for dedup |
| Permanent delete from trash | Adam only |

## Key Rules

- Agents create Draft records and never change `Record Status`.
- A legacy `Inactive` option may still exist in some database schemas. Treat it as retired; do not use it.
- Archiving is an orthogonal visibility layer — records are hidden from views but preserve all wiring.
- Notion automatically clears reciprocal synced-dual relations when a record is trashed.

## Delete Path

1. Set `Record Status = Delete` plus the relevant notes field explaining why.
2. Trash the record (or trash directly if already annotated).
3. Permanent delete from Notion trash is Adam's manual step.
