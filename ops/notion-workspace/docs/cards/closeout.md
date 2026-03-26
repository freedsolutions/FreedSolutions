# Close-Out Protocol

> Context card — extracted from `ops/notion-workspace/CLAUDE.md` Codex Review Gate section. Verify against the canonical source if stale.

## Close-Out Steps

For tasks that change local files in `ops/notion-workspace/`:

1. **Edit local source-of-truth files.**
2. **Push mapped instruction docs to Notion** via MCP when applicable, omitting the repo-only `<!-- Notion Page ID: ... -->` comment.
3. **Re-fetch updated Notion pages** and confirm the live body does not contain the repo-only comment.
4. **Save the fetched live body** to `ops/notion-workspace/tmp/notion-sync-remote-YYYY-MM-DD-<doc>.md` and run parity check.
5. **If parity fails, stop.** Do not downgrade to visual verification. Do not mark the doc synced.
6. **If skill sources changed**, run `sync-claude-skill-wrappers.ps1 -ValidateOnly` to confirm Claude copies mirror repo skills.
7. **Run `test-closeout-sanity.ps1`** and disclose untracked-file warnings. Treat mojibake as blocking.
8. **Run Codex review gate.** If unrelated changes exist, scope with `--pathspec`.
9. **Update `session-active.md`** only after review passes or findings are explicitly accepted.
10. **Commit and push** to `main`.

## Validation Scripts

| Script | Purpose | Key flags |
|--------|---------|-----------|
| `publish-codex-skills.ps1` | Validate and publish Codex skill copies | `-ValidateOnly` (no install) |
| `sync-claude-skill-wrappers.ps1` | Sync repo skills to `.claude/skills/` | `-ValidateOnly` (check only) |
| `compare-notion-sync.ps1` | Deterministic parity check: local doc vs. live Notion page | `-LocalFile <path> -RemoteFile <path>` |
| `test-closeout-sanity.ps1` | Pre-commit encoding check and untracked-file disclosure | `-RequireCleanScope` (optional strict mode) |

## Key Rules

- Do not claim a clean close-out with a dirty worktree. Disclose unrelated modified or untracked files.
- Do not update the handoff before the Codex review gate unless Adam explicitly asks for a draft note.
- Visual inspection is not a substitute for a failed parity check.
