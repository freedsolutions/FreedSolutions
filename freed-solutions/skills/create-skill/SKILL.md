---
name: create-skill
description: Scaffold a new SKILL for Adam's workspace — choose the correct bucket (freed-solutions vs ops/notion-workspace), draft a focused frontmatter description with triggers, set up the folder + SKILL.md, and run the sync pipeline so the wrapper lands under .claude/skills/. Use when Adam asks to create or formalize a new skill.
---

# Create Skill

Scaffold a new SKILL end-to-end: pick the right bucket, write the frontmatter, draft the body with house-style sections, and wire it into the sync pipeline so the wrapper is generated and the skill becomes invocable via `/<name>`.

## When to Use

- Adam wants to formalize an existing ad-hoc workflow as a reusable SKILL.
- Adam mentions "I should have a SKILL for X" — capture the ask and scaffold immediately.
- Refactoring an existing inline prompt into a SKILL for reuse across sessions or by subagents.

## Inputs

- **Skill name** (required): kebab-case slug, short and scoped. Examples: `google-sheets-patterns`, `notion-action-items`, `pandoc-deliverable`.
- **Purpose** (required): 1-sentence description of what the skill does.
- **Trigger conditions** (required): when should this skill be invoked automatically? When should it be skipped?
- **Bucket** (required): `freed-solutions/skills/` (default for cross-project, brand-neutral technical toolkit) or `ops/notion-workspace/skills/` (Notion-specific).
- **Model hint** (optional): if the skill needs a specific model (e.g., Opus for longer reasoning), note it.

If any required input is ambiguous, use `AskUserQuestion` before scaffolding.

## Bucket Decision

Pick based on the skill's scope and audience:

| Bucket | Use when |
|---|---|
| `freed-solutions/skills/` | Cross-project technical patterns, client-agnostic toolkit, Adam's personal workflows (resume, sheets, codex reviews). |
| `ops/notion-workspace/skills/` | Notion-specific automation — reads/writes the CRM, relies on Notion schema, uses `notion-` MCP. |

If the skill straddles both, ask Adam which primary audience to optimize for.

## Frontmatter Rules

The YAML frontmatter is what makes the skill discoverable. It drives auto-activation and shows up in `/` slash-command listings.

```yaml
---
name: <kebab-case-slug>
description: <one sentence saying what it does and when to use it, imperative voice, trigger-aware>
---
```

**Description structure** (copy from a working skill and adapt):

> "[Verb the goal]. [Brief elaboration of key inputs/outputs]. Use when [specific trigger condition]."

Good examples:
- `resume-builder`: "Tailor Adam's resume + cover letter + application answers for a specific job opening, using a base resume as the reference-doc for DOCX styling. Use when Adam wants to apply to a role and needs the materials written, tuned to the JD, and rendered to DOCX/PDF."
- `notion-meeting-prep`: "Surface open Action Items and recent email threads for a Meeting's attendees before a call. Use when the user wants a pre-call context brief showing open work and recent correspondence for every Contact attending the meeting."
- `cannabis-tech-sitemap`: "Generate a Phase 1 tech-stack decision canvas (Mermaid source + Figma rendering) for a vertically integrated cannabis MSO from stakeholder interview notes. Use when Adam has run a discovery engagement and needs the sitemap artifact for the deliverable."

Bad examples (what to avoid):
- "Helps with sheets." — vague, no trigger
- "This skill does X, Y, Z. It's useful for A, B, C." — meta-language, avoid
- "A comprehensive guide to..." — marketing tone, skip

Keep the description to ~40 words. It's scanned by the harness to decide when to auto-activate.

## Body Structure

Model the body on existing skills. Sections that almost always appear:

1. **`# Title`** — same slug, title-cased with spaces.
2. **Opening paragraph** — one short paragraph explaining what the skill produces and the house style it enforces.
3. **`## When to Use`** — bullet list of concrete trigger scenarios. Each starts with a present-tense verb or "Adam ...".
4. **`## Inputs`** — bullet list: `**Name** (required/optional)`: description with any defaults.
5. **`## Workflow`** — numbered steps the model follows. Reference concrete file paths, tool names, MCP calls.
6. **Optional domain sections** — canonical facts, style rules, known gotchas, templates, references.

Skip sections that don't apply. Don't pad.

## Scaffolding Steps

1. **Confirm inputs** with the user (name, purpose, triggers, bucket). Use `AskUserQuestion` if anything unclear.
2. **Check for collisions**: does `<bucket>/<name>/` already exist? If so, ask whether to update or pick a new name.
3. **Create the directory**:
   ```
   <bucket>/<name>/
   └── SKILL.md
   ```
   Optional `config.json` for model hints; optional subdirs like `templates/` or `assets/` if the skill needs bundled files.
4. **Write `SKILL.md`** following the structure above. Start lean — 80-200 lines is a good target for a focused skill.
5. **Review**: read it back end-to-end, checking the description accurately reflects the body.
6. **Run sync**:
   ```powershell
   cd ops/notion-workspace/scripts
   .\sync-claude-skill-wrappers.ps1
   ```
   This generates a wrapper at `.claude/skills/<name>/SKILL.md` that points at the source.
7. **Verify discovery**: the skill should now appear in `/` slash-command listings and be invocable. Adam can test with a trigger query matching the description.
8. **Commit** (if not in a protected path). The `.claude/skills/` wrapper is safe to commit; the source in `freed-solutions/skills/` or `ops/notion-workspace/skills/` is the real content.

## Sync Pipeline Details

`sync-claude-skill-wrappers.ps1` lives at `ops/notion-workspace/scripts/` and:
- Scans the two source roots (`ops/notion-workspace/skills/` and `freed-solutions/skills/`) for any folder containing a `SKILL.md`.
- Generates a wrapper at `.claude/skills/<name>/SKILL.md` that re-exports the source.
- Validates frontmatter presence and well-formedness.
- `-ValidateOnly` flag: dry-run without writing.

If you add a new source root later, update both `sync-claude-skill-wrappers.ps1` and `publish-codex-skills.ps1` (the sibling script that publishes to Codex).

## Template: New SKILL.md

```markdown
---
name: <kebab-name>
description: <one sentence with trigger. Use when <specific scenario>.>
---

# <Title Case Name>

<One-paragraph opening: what this skill produces and in what house style.>

## When to Use

- <Concrete trigger scenario 1>
- <Concrete trigger scenario 2>
- <Skip / don't-use condition, if applicable>

## Inputs

- **Input A** (required): description + default if applicable.
- **Input B** (optional): description.

If any required input is missing or ambiguous, use `AskUserQuestion` before proceeding.

## Workflow

### 1. Intake

<What to confirm or load before starting work.>

### 2. <Core work step>

<Concrete actions with file paths, tool names, commands.>

### 3. <Next step>

<...>

### N. Deliver

<What the final artifact looks like, where it lands, how to hand off.>

## House Style Notes

<Any voice / tone / convention constraints specific to this skill's output.>

## References

- <Relevant source files, memory notes, prior art.>
```

## House Style Notes

- Write skills in the same voice Adam writes in: operator-direct, no marketing, no AI-tell phrases ("I'll help you...", "Let me know if...").
- Prefer imperative or second-person instructions to first-person narration.
- Ground every abstract rule in a concrete example (file path, formula, or real interaction).
- Link to memory files when a rule maps to a documented gotcha — don't re-explain things Adam has already captured in memory.
- Skills bundle knowledge plus workflow. Pure reference material belongs in memory; pure workflow belongs in a skill.

## Meta-Skill Self-Reference

When using this skill to create a new skill, the irony is not lost. But the pattern is: read the existing skills in both buckets before drafting; match their length, tone, and section depth; prefer concision over completeness. A skill that is too long doesn't get read.

## References

- Existing skills for reference:
  - `freed-solutions/skills/resume-builder/SKILL.md` — longest, most workflow-heavy example
  - `freed-solutions/skills/cannabis-tech-sitemap/SKILL.md` — mid-length, domain-specific
  - `ops/notion-workspace/skills/notion-meeting-prep/SKILL.md` — Notion-integrated example
  - `ops/notion-workspace/skills/pandoc-deliverable/SKILL.md` — tool-wrapper example
- Sync script: `ops/notion-workspace/scripts/sync-claude-skill-wrappers.ps1`
- Claude Code skill discovery docs: see `claude-code-guide` for harness behavior.
