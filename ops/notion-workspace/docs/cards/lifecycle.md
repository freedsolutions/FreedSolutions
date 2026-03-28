# Record Lifecycle

> Context card — extracted from `ops/notion-workspace/CLAUDE.md`. Verify against the canonical source if stale.

## Record Status Flow

`Draft` -> `Active`

## Who Controls Each Transition

| Transition | Controller |
|-----------|------------|
| Create (Draft) | Agents and manual workflows |
| Draft -> Active | Adam only |
| Delete (trash) | Adam only — trash the record directly in Notion, no intermediate status |
| Archiving (UI) | Adam only — hides from views but preserves wiring and remains searchable for dedup |
| Permanent delete from trash | Adam only |

## Key Rules

- Agents create Draft records and never change `Record Status`.
- Archiving is an orthogonal visibility layer — records are hidden from views but preserve all wiring.
- Notion automatically clears reciprocal synced-dual relations when a record is trashed.

## Delete Path

1. Trash the record directly in Notion. No intermediate status.
2. Notion automatically clears reciprocal relations on linked records.
3. Permanent delete from Notion trash is Adam's manual step.
