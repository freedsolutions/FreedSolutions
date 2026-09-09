# <client> — Client Engagement

**Engagement:** <what this engagement is>
**POC:** <name> · **Status:** <active / paused / closed — one clause>

> **A ROSTER, not a workspace.** One line per tenant, pointing at that tenant's own `CLAUDE.md`,
> which is where ticket routing, BI pointers, current state and the change log live. Nothing but
> this file and the folders below belongs at this level.

## Tenants

- **`<tenant>/`** — <lsp_name>, <city> (<n> location(s)). Dutchie/Looker BI estate, MDM and
  catalog work. Pointer: `clients/<client>/<tenant>/CLAUDE.md`.

## Engagement folders (not tenant-scoped)

- <none yet — add a bullet per folder that spans the engagement rather than one tenant.>

## Layout contract

Each tenant folder holds its own `CLAUDE.md`, `bi-estate/`, `scripts/`, `deliverables/`,
`exports/`, `reviews/`, `notes/`, `tickets/` and whatever lanes it needs. Loose files at a
tenant root are capped at ten. The whole scaffold is checked by
`node .claude/skills/bi-change/scripts/kickoff_check.js --pointer clients/<client>/<tenant>`,
which also reports (C8) any file this template names that the tenant is missing.
