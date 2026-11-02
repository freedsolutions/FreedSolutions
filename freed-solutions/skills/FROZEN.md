# FROZEN - do not edit

This copy of the skills is frozen as of 2026-11-02.

- The source of truth is the NewWaveCannabis repo, `.claude/skills/` (one root, no generated copies).
- A skill edit is made there, then mirrored here with `scripts/mirror_skills_to_fs.ps1` (in NWC), which
  copies the skill into this folder and re-runs `ops/notion-workspace/scripts/sync-claude-skill-wrappers.ps1`
  so `.claude/skills/` in this repo stays a valid generated copy. Commit the result here.
- Nobody edits this folder or `.claude/skills/` in this repo by hand. The pre-commit proofs still run.
- `cannabis-tech-sitemap`, `freed-solutions-website` and `resume-builder` were not carried to NWC; they
  stay here as history only.

Last change to the source in this repo before the freeze: commit `34f5d72` (2026-11-02).
