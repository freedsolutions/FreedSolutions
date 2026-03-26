# Schema Quick Reference

> Context card — extracted from `ops/notion-workspace/CLAUDE.md` and `docs/agent-sops.md`. Verify against the canonical sources if stale.

## Contacts DB

| Property | Type | Notes |
|----------|------|-------|
| Contact Name | title | |
| Display Name | formula | |
| QC | formula | |
| Email | email | Dedup field |
| Secondary Email | email | Dedup field |
| Tertiary Email | email | Dedup field |
| Phone | phone | |
| Pronouns | select | |
| Nickname | rich_text | |
| LinkedIn | url | Canonical form: `https://www.linkedin.com/in/<slug>` |
| Company | relation | |
| Role / Title | rich_text | |
| Record Status | select | `Draft` / `Active` / `Delete` |
| Contact Notes | rich_text | |

## Companies DB

| Property | Type | Notes |
|----------|------|-------|
| Company Name | title | |
| Company Type | select | Tech Stack, Operator, Network, Personal |
| QC | formula | |
| Domains | multi_select | Primary domains — dedup field |
| Additional Domains | multi_select | Merged/subsidiary/sender-level — dedup field. May hold full sender email for platform companies. |
| States | select | Default: "All" |
| Website | url | |
| Contacts | relation | |
| Emails | rollup | |
| Meetings | rollup | |
| Action Items | relation | |
| Engagements | relation | |
| Tech Stack | multi_select | |
| Record Status | select | `Draft` / `Active` / `Delete` |
| Company Notes | rich_text | |

## Action Items DB

| Property | Type | Notes |
|----------|------|-------|
| Task Name | title | |
| Type | formula | |
| Status | select | |
| Priority | select | |
| Record Status | select | `Draft` / `Active` / `Delete` |
| Task Notes | rich_text | |
| Due Date | date | |
| Created Date | created_time | |
| Contact | relation | Counterparty person |
| Company | relation | Owning/execution context (not counterparty's employer) |
| Assignee | people | |
| Source Meeting | relation | Where the work originated |
| Source Email | relation | Where the work originated |
| Target Meeting | relation | Optional future touchpoint for review/close-out |
| Target Email | relation | Optional future touchpoint for review/close-out |
| Attach File | files | |
| QC | formula | |

## Meetings DB

| Property | Type | Notes |
|----------|------|-------|
| Meeting Title | title | |
| Calendar Event ID | rich_text | |
| Calendar Name | select | Live options: `Adam - Business`, `Adam - Personal` only |
| Date | date | |
| Contacts | relation | |
| Companies | rollup | |
| Action Items | relation | |
| Target Action Items | relation | Reciprocal of Action Items.Target Meeting |
| Series | relation | |
| Instances | relation | |
| Is Series Parent | checkbox | |
| Series Status | rollup | |
| Location | rich_text | |
| Record Status | select | `Draft` / `Active` / `Delete` |
| QC | formula | |

## Emails DB

| Property | Type | Notes |
|----------|------|-------|
| Email Subject | title | |
| Thread ID | rich_text | Canonical dedup key (exact match, not subject line) |
| From | email | |
| Direction | formula | |
| Date | date | |
| Contacts | relation | |
| Companies | rollup | |
| Action Items | relation | |
| Target Action Items | relation | Reciprocal of Action Items.Target Email |
| Labels | multi_select | Routing: `Primitiv/PRI_Outlook`, `Primitiv/PRI_Teams`, `LinkedIn`, `DMC/DMC_GMail` |
| Source | select | `Email - Freed Solutions`, `Email - Personal`, `LinkedIn - DMs` |
| Record Status | select | `Draft` / `Active` / `Delete` |
| Email Notes | rich_text | |
| QC | formula | |
| Created Timestamp | created_time | |

## Dedup Rules

| Entity | Match fields |
|--------|-------------|
| Contacts | Email + Secondary Email + Tertiary Email (all three checked) |
| Companies | Domains + Additional Domains (both checked). Additional Domains may hold full sender email for platform companies. |
| Emails | Thread ID (exact match, not subject line) |

## Normalization

- **LinkedIn URLs:** `https://www.linkedin.com/in/<slug>` (canonical form)
- **Emails:** lowercase + trim
- **Domains:** hostname only (no protocol, no path)
- **Company domain matching:** Check domains first, then fall back to full sender email address against Additional Domains
