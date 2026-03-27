# Sub-Agent Delegation Contract

> Local-only repo doc. Governs sub-agent delegation within Claude Code and Codex sessions.

## Scope

This contract applies when:

- Claude Code spawns a sub-agent via the `Agent` tool
- Codex spawns a child process via `codex exec` with a skill-scoped prompt

It does **not** apply to:

- Notion Custom Agents (server-side, governed by `docs/agent-sops.md`)
- Sequential user-invoked skill execution (the existing pattern where the user picks the next skill after the prior completes)

## Bootstrap Protocol

The parent provides each sub-agent with three items:

### 1. Delegation Manifest

| Field | Required | Description |
|-------|----------|-------------|
| `run_id` | Yes | ISO timestamp + short hash (e.g., `2026-03-25T14:30:00-a3f2`) for traceability |
| `parent_skill` | Yes | Name of the invoking skill or `"direct"` if launched outside a skill |
| `delegated_scope` | Yes | Bounded natural-language description of the task |
| `gate_ceiling` | Yes | Maximum gate the sub-agent may exercise: `UNGATED` (read-only) or `HARDENED_GATE` (mutations within `write_paths`). Never `GOVERNANCE_GATE`. |
| `read_paths` | Yes | List of repo paths and Notion page IDs the sub-agent may read |
| `write_paths` | Yes | List of repo paths and Notion page IDs the sub-agent may write to. Empty for read-only sub-agents. |
| `scaffold_profile` | Yes | One of the four scaffold profiles below |
| `depth` | Yes | Always `1`. Sub-agents must refuse further delegation when `depth >= 1`. |
| `timeout_seconds` | No | Default: 120. Maximum wall-clock time before the parent treats the sub-agent as timed out. |

### 2. Context Bundle

Pre-fetched records, file contents, or the relevant slice of session state needed for the task. The parent should minimize what it passes — the scaffold profile tells the sub-agent which repo files to read for conventions.

### 3. Result Schema

The JSON envelope the sub-agent must return (see Result Contract below).

**Scope enforcement:** If the sub-agent determines it needs something outside its manifest envelope — a file not in `read_paths`, a write target not in `write_paths`, or a `GOVERNANCE_GATE`-level decision — it must return `needs_escalation` rather than broadening its own scope.

Use `ops/notion-workspace/scripts/test-sub-agent-contract.ps1` to validate repo-stored manifest or result fixtures and to smoke-test parent-side overlap checks before relying on new delegation scaffolding.

## Scaffold Profiles

Four named profiles tell the sub-agent which repo files to read for context. The sub-agent reads files in the listed order, then proceeds with the delegated task.

All card paths are relative to `ops/notion-workspace/docs/`.

| Profile | Files to read (in order) | Use case |
|---------|-------------------------|----------|
| `explorer` | `cards/db-ids.md`, then `CLAUDE.md` through the Database IDs section, then the task-specific doc if the parent names one | Read-only discovery, context gathering, research |
| `crm-worker` | `cards/gates.md`, `cards/db-ids.md`, `cards/lifecycle.md`, `cards/schema.md`, then the task-specific skill `SKILL.md` | CRM execution, Action Item work, record mutations |
| `validator` | `cards/closeout.md`, `cards/gates.md`, `docs/test-playbooks.md`, then the task-specific regression section | Testing, audit, parity checks |
| `scaffolding-editor` | `cards/gates.md`, `cards/closeout.md`, then `CLAUDE.md` Sync Convention + Codex Review Gate sections, then the task-specific doc | Repo doc edits, skill changes, publication |

Profiles are optional acceleration. A sub-agent can always fall back to reading the full canonical docs if the cards are insufficient.

## Gate Inheritance Rules

| Parent Gate State | Sub-Agent Gate Ceiling | Mutation Rule |
|---|---|---|
| Any | `HARDENED_GATE` (default) | May mutate within `write_paths`. The delegation manifest serves as the parent's scope approval — the sub-agent does not re-prompt the user, but must not exceed the `write_paths` boundary. |
| Any | `UNGATED` (read-only) | Reads and computation only. Any mutation attempt is a contract violation; return error. |
| Any | `GOVERNANCE_GATE` | **Never delegated.** If the sub-agent encounters a governance-level decision, it returns `needs_escalation` with the decision question. The parent asks Adam. |

## Result Contract

Every sub-agent must return a result matching this JSON envelope:

```json
{
  "run_id": "<matches delegation_manifest.run_id>",
  "status": "success | failure | needs_escalation | timeout",
  "summary": "<1-2 sentence natural language summary>",
  "findings": [],
  "mutations_performed": [
    {
      "target": "<repo path or Notion page ID>",
      "action": "create | update | delete",
      "detail": "<what changed>"
    }
  ],
  "escalation_question": "<only when status is needs_escalation>",
  "error_detail": "<only when status is failure>"
}
```

- `findings` is a task-specific typed array. Each skill that supports delegation should define its own findings schema.
- `mutations_performed` tracks what the sub-agent actually changed, even on partial failure.
- The parent uses `mutations_performed` to audit state before retrying or proceeding.

## Depth Limit

Maximum delegation depth is **1** (parent -> sub-agent, no further).

- The delegation manifest carries `depth: 1`.
- A sub-agent receiving a manifest with `depth >= 1` must refuse to delegate further.
- If the sub-agent determines it needs to spawn a child, it returns `needs_escalation` explaining what additional work is needed.

## Parallel Execution Rules

The parent may spawn multiple sub-agents in parallel when **both** conditions are met:

1. Their `write_paths` are completely disjoint — no two sub-agents write to the same Notion page, same DB for record creation, or same repo file.
2. Their tasks are logically independent — the output of one does not affect the input of another.

When write targets overlap, the parent must **serialize**: run one sub-agent, collect its result, then run the next with updated context.

**Notion DB record creation specifically:** The parent must either:
- (a) Assign each sub-agent a disjoint set of source records to process, OR
- (b) Run a dedup-before-create check after collecting all sub-agent results and before committing any creates, OR
- (c) Serialize all creation through a single sub-agent.

This convention addresses the race-condition class demonstrated by the March 25 Hoodie Analytics / David Winter duplicate cluster.

**Coordination:** The parent session is the sole aggregator. Sub-agents do not communicate with each other. The `run_id` provides traceability across delegations.

## Failure and Timeout Handling

**Timeout:** If a sub-agent exceeds `timeout_seconds`, the parent treats the result as `{ "status": "timeout" }` and must not assume any mutations completed.

**Failure:** If a sub-agent returns `status: "failure"`, the parent logs `error_detail` and decides whether to retry, escalate, or abort. The parent never retries silently — a failed delegation should be reported to the user with the error context.

**Partial mutations:** The `mutations_performed` array (if populated before failure) helps the parent understand what happened. If empty on failure, the parent should audit the target resources before retrying.

**Escalation:** When `status: "needs_escalation"`, the parent reads `escalation_question` and presents it to the user through the appropriate gate. The sub-agent's work is paused (or already complete up to the decision point).
