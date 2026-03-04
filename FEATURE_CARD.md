# Feature: Repo Cleanup and Process Hardening

## Problem
Audit found documentation drift, missing defensive patterns, and process gaps accumulated over recent feature work. No behavioral bugs — this is a docs/config/tooling hygiene pass.

## Scope
- Fix CLAUDE.md source count (19 → 20), add layoutTokens.js to manifest table, add Phase 3 pre-flight checklist
- Harden .gitignore with defensive patterns (node_modules, IDE files, .env) and simplify root image globs to extension-based
- Remove cat/head/tail Bash permissions from settings.json (contradicts Tool Selection Rules)
- Archive pre-March CHANGES.md entries to CHANGES_ARCHIVE.md; add 300-line maintenance rule to CLAUDE.md
- Add scripts/validate-order.js (checks src/ ↔ ORDER parity) wired into pre-commit hook

## Files
- `CLAUDE.md` — source count, manifest table, pre-flight checklist, changelog maintenance rule, project files table
- `.gitignore` — defensive patterns, simplified image globs
- `.claude/settings.json` — remove cat/head/tail permissions
- `CHANGES.md` — trimmed to March entries + archive pointer
- `CHANGES_ARCHIVE.md` — new file with pre-March entries
- `scripts/validate-order.js` — new ORDER validation script
- `.githooks/pre-commit` — wire in validate-order before archive step

## Out of scope
- Any src/ code changes or build output changes
- preview.html, build.js logic, settings.local.json
- Git hook archive logic (working correctly)
