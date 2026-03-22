---
name: notion-agent-test
description: Run structured smoke or regression tests for Notion Custom Agents using the local playbooks, Notion MCP, and browser activity checks. Use when validating triggers, downstream record creation, cleanup flows, or recent workflow changes in the Automation Hub.
---

<!-- Generated from ops/notion-workspace/skills/notion-agent-test/. Edit the repo skill source and rerun ops/notion-workspace/scripts/sync-claude-skill-wrappers.ps1; do not edit this Claude copy directly. -->

# Notion Agent Test

Read `ops/notion-workspace/CLAUDE.md`, `ops/notion-workspace/docs/agent-sops.md`, and `ops/notion-workspace/docs/test-playbooks.md` first when they exist. The local playbooks are the canonical acceptance criteria.

## Workflow

1. Pick the exact test target.
   - Use the user request plus the local playbook to decide whether this is a smoke test, regression, or targeted failure reproduction.
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

## Guardrails

- Never test with unlabeled production records.
- Wait long enough for asynchronous runs before calling a trigger dead.
- Do not skip cleanup on partial failures.
- Treat runtime timestamps and activity history as evidence, not assumptions.

## Read Next

- Read [workflow.md](references/workflow.md) for the generic E2E testing pattern and report template.
