---
name: notion-active-sesson
description: Kick off `ops/notion-workspace` work by reading the canonical handoff, repo contract, and agent SOPs, then fanning out targeted repo discovery, asking the user the minimum high-impact questions, and proposing or starting the next scaffolding, documentation, or skill updates. Use when the user wants to start a Notion-workspace session, review current priorities or Planning Output, or prepare repo-first scaffolding changes without reviving the old Notion session ritual.
---

# Notion Active Sesson

Read `ops/notion-workspace/session-active.md`, `ops/notion-workspace/CLAUDE.md`, and `ops/notion-workspace/docs/agent-sops.md` first when they exist in the workspace.

## Workflow

1. Rebuild the active context.
   - Extract current state, priorities, follow-up items, and any `Planning Output` from `session-active.md`.
   - Extract standing approvals, sync rules, skill-publish rules, and the review gate from `CLAUDE.md`.
   - Read only the workflow docs, skills, and scripts that match the requested scaffolding change.
2. Fan out targeted repo discovery.
   - Default to a small swarm of 2-4 explorer agents for kickoff unless the task is trivial.
   - Split the swarm by concern: repo conventions, likely touched files, validation path, and workflow-specific context.
   - Keep prompts artifact-based. Do not tell subagents the intended answer.
3. Synthesize the next execution slice.
   - Summarize the active priorities that matter to the request, the likely touched files, the validation path, and any "Adam - UI step".
   - Prefer the smallest useful change set instead of a repo-wide rewrite.
   - Treat a handoff `Planning Output` as the current plan unless the user overrides it.
4. Ask the minimum kickoff questions.
   - Ask only when the answer changes scope, naming, risky behavior, or whether live Notion/UI state should be touched.
   - Ask in plain chat. Do not depend on a special AskUserQuestion tool.
   - Prefer one or two concrete questions at a time.
5. Execute repo-first updates.
   - Edit local source-of-truth files first.
   - When you change mapped docs, sync them to Notion in the same task and run the parity helper described in `CLAUDE.md`.
   - When you change a repo skill, validate with `ops/notion-workspace/scripts/publish-codex-skills.ps1 -ValidateOnly` and publish the installed copy before calling the task done.
6. Close out cleanly.
   - Run the Codex review gate before updating `session-active.md`.
   - Update the handoff only after the work is verified or the user explicitly accepts remaining findings.

## Guardrails

- Treat `session-active.md` as the canonical handoff surface.
- Keep the kickoff lightweight. Do not recreate the retired Notion session-handoff workflow or introduce a second handoff system.
- Use repo skills under `ops/notion-workspace/skills/` as the canonical manual operator layer.
- Pause for confirmation on schema changes, destructive actions, bulk CRM edits, or ambiguous lifecycle changes.
- Do not mark UI-only work complete until Adam confirms it in chat.
- Ignore unrelated repo areas unless the current task truly depends on them.

## Read Next

- Read [workflow.md](references/workflow.md) for suggested swarm lanes, kickoff question patterns, and close-out checks.
