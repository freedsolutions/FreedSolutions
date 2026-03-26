# Gate Taxonomy & Standing Approval

> Context card — extracted from `ops/notion-workspace/CLAUDE.md`. Verify against the canonical source if stale.

## Shared Gate Taxonomy

| Gate | Meaning |
|------|---------|
| `UNGATED` | Proceed without pausing. |
| `HARDENED_GATE` | Ask one compact decision-shaped question. Re-ask if the reply is empty, unclear, or ambiguous. Never treat silence as approval. |
| `GOVERNANCE_GATE` | Same pause mechanism as `HARDENED_GATE`, but only when the Rules of Engagement require a pause. |

## Autonomous Skill Run Rule

Any repo/code mutation must go through `HARDENED_GATE` before the first edit, even when the broader workflow is standing-approved. This includes edits under `docs/`, `skills/`, `CLAUDE.md`, `session-active.md`, and repo scripts.

## Standing Approval Summary

Routine Notion work is pre-authorized once Adam requests it: reading mapped pages/databases, editing local docs, pushing instruction changes to Notion, updating `session-active.md`, running documented tests with `[TEST]` records, applying safe runtime repairs, and staging/committing/pushing `ops/notion-workspace` changes after validation.

**Pause and ask** when the task is ambiguous, schema-changing, destructive, touches `Record Status` outside documented paths, creates non-test CRM records, or is a bulk operation.
