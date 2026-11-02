---
name: create-skill
description: Scaffold a new SKILL for Adam's workspace — confirm it belongs in this repo's single skills root (.claude/skills/), draft a focused frontmatter description with triggers, set up the folder + SKILL.md, and prove it with the skill checks. Use when Adam asks to create or formalize a new skill.
---

<!-- Generated from "freed-solutions/skills/create-skill/SKILL.md". Edit the repo skill source and rerun ops/notion-workspace/scripts/sync-claude-skill-wrappers.ps1; do not edit this Claude copy directly. -->

# Create Skill

Scaffold a new SKILL end-to-end: confirm it belongs in this repo, write the frontmatter, draft the body with house-style sections, and run the skill checks so the skill is clean and invocable via `/<name>`.

## When to Use

- Adam wants to formalize an existing ad-hoc workflow as a reusable SKILL.
- Adam mentions "I should have a SKILL for X" — capture the ask and scaffold immediately.
- Refactoring an existing inline prompt into a SKILL for reuse across sessions or by subagents.

## Inputs

- **Skill name** (required): kebab-case slug, short and scoped. Examples: `google-sheets-patterns`, `dutchie-support-ticket`, `pandoc-deliverable`.
- **Purpose** (required): 1-sentence description of what the skill does.
- **Trigger conditions** (required): when should this skill be invoked automatically? When should it be skipped?
- **Bucket** (required): `.claude/skills/` is the only skills root in this repo (cross-project, client-agnostic technical toolkit). A skill that must work from any folder on the machine (`pandoc-deliverable`, `designed-pdf`, `browseros-neo`) is published to `~/.claude/skills/` as well; say which kind the new skill is.
- **Model hint** (optional): if the skill needs a specific model (e.g., Opus for longer reasoning), note it.

If any required input is ambiguous, use `AskUserQuestion` before scaffolding.

## Bucket Decision

`.claude/skills/` holds cross-project technical patterns and the client-agnostic toolkit. A skill never names a client, a tenant, a concrete client path or a tenant id: `node .claude/skills/bi-change/scripts/skill_leak_proof.js` fails the commit if it does. Client-specific procedure lives in the client tree (local-only, gitignored), never in a skill.

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
- `designed-pdf`: "Render a business-facing one-pager, decision brief, example sheet, or anything a stakeholder signs off on as a designed PDF ... Use for business or external audiences."
- `dutchie-support-ticket`: states the artifact (a filed ticket in the house format), the inputs it reads, and the one trigger phrase.

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
2. **Check for collisions**: does `.claude/skills/<name>/` already exist? If so, ask whether to update or pick a new name.
3. **Create the directory**:
   ```
   .claude/skills/<name>/
   └── SKILL.md
   ```
   Optional `scripts/` for anything the model must not improvise; optional `templates/` or `references/` for bundled files.
4. **Write `SKILL.md`** following the structure above. Start lean — 80-200 lines is a good target for a focused skill. Prose a model can rediscover stays out; a procedure it cannot rediscover goes into a script.
5. **Review**: read it back end-to-end, checking the description accurately reflects the body.
6. **Run the checks** from the repo root, and both must pass:
   - `node .claude/skills/bi-change/scripts/skill_leak_proof.js` — no client name, path or tenant id in any tracked skill file.
   - the skill's own `--selftest`, if it ships scripts.
7. **Verify discovery**: the skill should now appear in `/` slash-command listings and be invocable. Adam can test with a trigger query matching the description.
8. **Commit** on the branch the session is on. While a client tree still runs from the FreedSolutions repo, mirror the skills there: `powershell -ExecutionPolicy Bypass -File scripts/mirror_skills_to_fs.ps1`.

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

When using this skill to create a new skill, the irony is not lost. But the pattern is: read the existing skills before drafting; match their length, tone, and section depth; prefer concision over completeness. A skill that is too long doesn't get read.

## References

- Existing skills for reference:
  - `.claude/skills/dutchie-support-ticket/SKILL.md` — short, single-purpose
  - `.claude/skills/designed-pdf/SKILL.md` — script-backed (the render step is code, the judgement is prose)
- Leak check: `.claude/skills/bi-change/scripts/skill_leak_proof.js`
- FreedSolutions mirror (temporary, until every client tree runs from this repo): `scripts/mirror_skills_to_fs.ps1`
- Claude Code skill discovery docs: see `claude-code-guide` for harness behavior.
