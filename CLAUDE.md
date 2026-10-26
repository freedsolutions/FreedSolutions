# FreedSolutions - Multi-Project Repo

## Non-obvious locations
- `freed-solutions/skills/` is the skill SOURCE; `.claude/skills/` is the generated copy made by `ops/notion-workspace/scripts/sync-claude-skill-wrappers.ps1`. Edit the source, then re-sync. `~/.claude/skills/pandoc-deliverable` is its own source (TheoryWellness removed 2026-10-26; the `notion-*` skills retired).
- `scripts/` and `tests/` at the repo root are repo-level utilities (closeout-sanity and local-DB tests), distinct from `ops/notion-workspace/scripts/`. `ops/local_db/` and `ops/typesafe/` are private service scaffolds. `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check.ps1` runs every repo check in order and stops at the first failure.

## Project Routing
Each project has its own CLAUDE.md or README with workflow details.

**Notion Workspace (RETIRED 2026-10-21)** -> `ops/notion-workspace/NOTION-WORKSPACE-DESIGN.md`
- Adam no longer uses Notion. The folder stays as the design reference (CRM/PMO/automation principles, gate taxonomy) for the New Wave Cannabis build. Do not run its session protocol, Notion sync, or closeout gates; its `scripts/` still host the skill-wrapper sync.

## Client Engagements
Client engagement folders live under `clients/<client-slug>/` and are **local-only** (see `.gitignore`): engagement context, discovery, working artifacts and deliverables are never committed. Tracked files may name a client in routing, fixtures or test data, but never carry discovery content, deliverable text, or contact details. The active engagements are moving to a new repo and process set (2026-10); treat this repo's client handling as legacy.

## Repo-Level Rules
- Direct push to `main`
- Git hooks path: `.githooks` (`git config core.hooksPath .githooks`); its pre-commit runs the skill proofs (bi-change gate self-test, skill leak proof, wrapper sync check) when a commit touches `freed-solutions/skills/` or `.claude/skills/`
- No `package.json` or `node_modules` at the repo root - zero-dep repo
- `index.html` at root is the Freed Solutions landing page (GitHub Pages)
- Do not edit `index.html` without confirming the current CTA strategy (may change when Workspace email goes live)
