---
name: notion-agent-test
description: Run structured smoke or regression tests for Notion Custom Agents using the local playbooks, Notion MCP, and browser activity checks. Use when validating triggers, downstream record creation, cleanup flows, or recent workflow changes in the Automation Hub.
---

# Notion Agent Test

Read `ops/notion-workspace/CLAUDE.md` and `ops/notion-workspace/docs/agent-sops.md` first when they exist.
If routine repo-scoped shell, Notion MCP, or Playwright MCP support actions start surfacing local approval prompts during setup or verification, treat that as launcher/profile drift and switch to the documented quiet lane instead of normalizing repeated ad hoc approvals.

## Workflow

1. Pick the exact test target.
   - Use the user request plus the local playbook to decide whether this is a smoke test, regression, or targeted failure reproduction.
   - Bundle all currently known off-playbook or risky test questions into one compact `HARDENED_GATE` prompt instead of serial pauses.
2. Prepare test data safely.
   - Prefix new records with `[TEST]`.
   - Keep the blast radius small and plan cleanup before firing the trigger.
3. Trigger the agent intentionally.
   - Use the documented trigger path: scheduled proxy, property change, or `@mention`.
   - Reproduce the exact preconditions from the playbook instead of improvising.
4. Monitor execution.
   - Watch Recent Activity in the browser.
   - Cross-check the downstream records with Notion MCP.
5. Verify outputs against the playbook.
   - Check both positive behavior and non-regression constraints such as duplicate prevention or no-op safety.
6. Clean up.
   - Revert or delete test artifacts according to the documented cleanup path.
7. Report the outcome.
   - Include trigger method, execution time, pass or fail status, concrete checkpoints, issues found, and cleanup status.
   - Once a bounded off-playbook test slice is approved, continue autonomously unless a new ambiguity appears or a `GOVERNANCE_GATE` condition is triggered.

## Guardrails

- Never test with unlabeled production records.
- Wait long enough for asynchronous runs before calling a trigger dead.
- Do not skip cleanup on partial failures.
- Treat runtime timestamps and activity history as evidence, not assumptions.
- This skill does not delegate to sub-agents.

## Gate Protocol

Use the shared gate taxonomy from `ops/notion-workspace/CLAUDE.md` and `ops/notion-workspace/docs/agent-sops.md`.

| Operation | Gate | Notes |
| --- | --- | --- |
| Bounded `[TEST]` setup, trigger, monitoring, verification, cleanup, and reporting that stay inside the documented playbook | `UNGATED` | Follow the playbook exactly and keep the blast radius small. |
| Any repo file edit and any test move that falls outside the documented playbook | `HARDENED_GATE` | Ask a compact question and re-ask if the reply is empty or unclear. |
| Non-test record creation, destructive cleanup beyond the playbook, schema changes, or lifecycle mutations outside documented test paths | `GOVERNANCE_GATE` | Follow the existing Rules of Engagement. |

## Read Next

- Read [workflow.md](references/workflow.md) for the generic E2E testing pattern and report template.
