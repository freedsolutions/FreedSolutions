---
name: notion-active-session
description: Kick off `ops/notion-workspace` work by reading the canonical handoff, repo contract, and agent SOPs, then using local or parallel repo discovery, the shared gate taxonomy, and repo-first updates to route the next scaffolding, documentation, or skill changes.
---

# Notion Active Session

Read `ops/notion-workspace/session-active.md`, `ops/notion-workspace/CLAUDE.md`, and `ops/notion-workspace/docs/agent-sops.md` first when they exist in the workspace.

## Workflow

1. Rebuild the active context.
   - Extract current state, priorities, follow-up items, and any `Planning Output` from `session-active.md`.
   - Extract standing approvals, sync rules, skill-publish rules, and the review gate from `CLAUDE.md`.
   - Read only the workflow docs, skills, and scripts that match the requested scaffolding change.
2. Fan out targeted repo discovery.
   - Use local or parallel discovery by default when kickoff benefits from fan-out.
   - Delegate only when the client supports it and the user explicitly asked for or approved delegation.
   - Split discovery by concern: repo conventions, likely touched files, validation path, and workflow-specific context.
3. Synthesize the next execution slice.
   - Summarize the active priorities that matter to the request, the likely touched files, the validation path, and any "Adam - UI step".
   - Prefer the smallest useful change set instead of a repo-wide rewrite.
   - Treat a handoff `Planning Output` as the current plan unless the user overrides it.
4. Use `HARDENED_GATE` only for the minimum kickoff questions.
   - Ask only when the answer changes scope, naming, risky behavior, or whether live Notion/UI state should be touched.
   - Use the shared gate contract instead of open-ended chat when a question is required.
   - Prefer one or two concrete questions at a time.
5. Execute repo-first updates.
   - Use `HARDENED_GATE` before the first repo/code mutation in a skill run. Name the intended files and change types in one compact prompt.
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
- Use `GOVERNANCE_GATE` for schema changes, destructive actions, bulk CRM edits, or ambiguous lifecycle changes.
- Do not mark UI-only work complete until Adam confirms it in chat.
- Ignore unrelated repo areas unless the current task truly depends on them.

## Gate Protocol

Use the shared gate taxonomy from `ops/notion-workspace/CLAUDE.md` and `ops/notion-workspace/docs/agent-sops.md`.

| Operation | Gate | Notes |
| --- | --- | --- |
| Read the handoff, use local or parallel repo discovery, synthesize the kickoff summary, sync docs to Notion, publish skills, and run validation scripts | `UNGATED` | Delegate only when the client supports it and the user explicitly asked for or approved delegation. |
| Kickoff scope, naming, or risk questions and the first repo/code mutation in a skill run | `HARDENED_GATE` | Name intended files and change types before the first edit, and re-ask if the reply is empty or unclear. |
| Schema changes, destructive actions, bulk CRM edits, or ambiguous lifecycle changes | `GOVERNANCE_GATE` | Follow the existing Rules of Engagement. |

## Read Next

- Read [workflow.md](references/workflow.md) for suggested discovery lanes, kickoff question patterns, and close-out checks.
