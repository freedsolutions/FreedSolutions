<!-- Generated from "ops/notion-workspace/skills/notion-active-session/references/workflow.md". Edit the repo skill source and rerun ops/notion-workspace/scripts/sync-claude-skill-wrappers.ps1; do not edit this Claude copy directly. -->

# Notion Active Session Workflow

## Kickoff Inputs

Read these first:

- `ops/notion-workspace/session-active.md`
- `ops/notion-workspace/CLAUDE.md`
- `ops/notion-workspace/docs/agent-sops.md`

Then read only the workflow docs, skill sources, and scripts that are directly relevant to the requested scaffolding change.

If the request touches `ops/local_db`, direct Gmail or GCal ingestion, SQLite sync, or broader CRM architecture migration, also read `ops/notion-workspace/freed-solutions-execution-checklist.md` before planning. Treat it as an architecture-lane brief, not as a silent replacement for the current handoff.

## Suggested Discovery Lanes

Use local or parallel discovery by default when kickoff benefits from fan-out. Delegate only when the client supports it and the user explicitly asked for or approved delegation.

### Lane 1: Handoff and approvals

Inspect the active handoff plus `CLAUDE.md`. Report:

- current priorities tied to the request
- standing approval scope
- review-gate or sync requirements
- anything that must wait for Adam

If the request touches the local-first architecture lane, also report whether `freed-solutions-execution-checklist.md` changes the relevant priority order or execution contract.

### Lane 2: Existing patterns

Inspect the most relevant docs, skills, and scripts. Report:

- touched files
- reusable patterns to preserve
- constraints or anti-patterns already documented

### Lane 3: Validation and publish path

Inspect validation docs and publish helpers. Report:

- minimum validation commands
- whether skill publish is required
- whether Notion sync or parity checks are required

### Optional Lane 4: Workflow-specific deep dive

Use only when the request targets a specific workflow such as Post-Email, Post-Meeting, delete handling, or a particular repo skill.

## Kickoff Summary Template

Use a compact summary before editing:

```text
## Active session kickoff
- Requested change:
- Current priorities that matter:
- Likely touched files:
- Validation / publish path:
- Decisions needed from Adam:
- Adam - UI step:
```

## Question Patterns

Use `HARDENED_GATE` only when the answer changes execution materially. Keep the prompt concrete and re-ask if the reply is empty or unclear.

- Naming question: when the requested skill or workflow name could be interpreted more than one way.
- Scope question: when it is unclear whether the user wants only local repo edits or also live Notion sync, publish, or UI follow-through.
- Risk question: when the work may change schema, `Record Status`, live automations, or bulk CRM data.
- Repo edit question: before the first repo mutation, name the intended files and change types in one compact prompt.

Do not ask broad brainstorming questions when the repo already answers them.

## Close-Out Checklist

Before calling the kickoff work complete:

1. Validate each changed repo skill with `ops/notion-workspace/scripts/publish-codex-skills.ps1 -ValidateOnly`.
2. Publish the installed copy when the task changed a repo skill.
3. If mapped docs changed, sync them to Notion and run the parity helper from `CLAUDE.md`.
4. Treat a failed parity check as blocking unless Adam explicitly accepts the remaining mismatch.
5. Run `ops/notion-workspace/scripts/test-closeout-sanity.ps1` and disclose any untracked-file warnings before claiming the worktree is clean.
6. If unrelated local changes remain in the worktree, run the review gate with repeated `--pathspec <repo path or glob>` arguments so the review only covers the intended files.
7. Review the final diff for scope creep or stale handoff content.
8. Update `session-active.md` only after the work is verified or the user explicitly accepts remaining findings.
