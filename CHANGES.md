# CHANGES
Operational change log for behavior and workflow updates in this repo.
Add newest entries at the top.

## 2026-02-27 - Added feature session scaffold
- What changed: Added `FEATURE_CARD.md` template and a `FEATURE` -> `IMPLEMENT` session protocol in `CLAUDE.md`.
- Why: Standardize kickoff prompts without repeatedly pasting long instructions.
- Files: `CLAUDE.md` (updated), `FEATURE_CARD.md` (added), `CHANGES.md` (updated).
- Validation: Confirmed docs exist and protocol steps are explicit in `CLAUDE.md`.
- Notes/Risks: Protocol depends on contributors using the `FEATURE:` and `IMPLEMENT` triggers consistently.

## 2026-02-27 - Workflow docs consolidated
- What changed: Replaced overlapping workflow docs with `CLAUDE.md` as the single workflow contract, added `CHANGES.md`, and removed legacy checklist/handoff docs.
- Why: Streamline the plan -> edit -> build -> validate -> document -> commit -> push flow for Claude Code and human contributors.
- Files: `CLAUDE.md` (rewritten), `CHANGES.md` (added), `Checklist.md` (deleted), `CLAUDE-CODE-HANDOFF.md` (deleted).
- Validation: Confirmed markdown footprint is two files and stale references to removed docs are gone.
- Notes/Risks: Historical checklist detail was intentionally removed as part of consolidation.

## Entry Template
## YYYY-MM-DD - <short title>
- What changed:
- Why:
- Files:
- Validation:
- Notes/Risks:
