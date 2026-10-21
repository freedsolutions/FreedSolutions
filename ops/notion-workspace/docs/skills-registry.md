# Skills Registry

> Canonical inventory of all Skills across the Freed Solutions repo.

Last updated: April 5, 2026 (S76)

## Workspace Skills

Skills for Notion CRM/PMO automation. Canonical source: `ops/notion-workspace/skills/`.

| Skill | Purpose | Claude.ai Synced? | Last Updated |
|-------|---------|-------------------|--------------|
| `notion-action-items` | Execute a single Action Item end-to-end | Yes | S76 |
| `notion-agent-config` | Audit/update Notion Custom Agent settings | Yes | S75 |
| `notion-meeting-prep` | Pre-call context brief for meeting attendees | Yes | S75 |

## Repo Skills

Skills sourced from `freed-solutions/skills/` and synced to `.claude/skills/` by the sync workflow below.

| Skill | Purpose | Last Updated |
|-------|---------|--------------|
| `codex-review` | Run a Codex-backed review of the current git worktree | 2026-10-21 (moved under `freed-solutions/skills/`) |

## Sync Workflow

1. Edit the canonical repo skill source
2. Validate: `ops/notion-workspace/scripts/publish-codex-skills.ps1 -ValidateOnly`
3. Publish to Codex: `ops/notion-workspace/scripts/publish-codex-skills.ps1`
4. Sync to Claude.ai: `ops/notion-workspace/scripts/sync-claude-skill-wrappers.ps1`

## Notes

- Repo is always the source of truth
- Claude.ai copies are generated wrappers, not independently maintained
- Name in repo = name in Claude.ai (no aliases)
- `codex-review` became a synced skill on 2026-10-21; its source is `freed-solutions/skills/codex-review/`
