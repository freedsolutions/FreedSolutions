---
name: notion-agent-config
description: Audit or update Notion Custom Agent settings through the browser UI using the workspace's local config spec. Use when reviewing triggers, page access, mail or calendar connections, models, permission drift, or other Automation Hub runtime settings.
---

# Notion Agent Config

Read `ops/notion-workspace/CLAUDE.md` and `ops/notion-workspace/docs/agent-sops.md` first when they exist. Those files define the current operating model and the prescriptive config baseline.
If routine repo-scoped shell, Notion MCP, or Playwright MCP support actions start surfacing local approval prompts during the audit, treat that as launcher/profile drift and switch to the documented quiet lane instead of normalizing repeated ad hoc approvals.

## Workflow

1. Read the local spec before opening the browser.
   - Use `docs/agent-sops.md` for the expected triggers, access, and model.
   - Use task-specific docs when the change targets one workflow only.
2. Navigate directly to the agent settings page.
   - Use the documented settings URL from the local docs.
   - Do not hunt through the sidebar when a direct URL is known.
3. Capture the current state.
   - Screenshot triggers, property-trigger dialogs, tools and access, model, and advanced settings before editing.
4. Compare runtime to spec.
   - Treat live settings as runtime truth for risk assessment.
   - Treat the local docs as the target state unless the user explicitly approves a new direction.
5. Apply changes one agent at a time.
   - Clear, safe runtime repairs that bring live settings back to the documented baseline are `UNGATED`.
   - Use `HARDENED_GATE` before fixing unclear drift, redefining the local spec, or making agent-architecture, permission, or model changes not plainly dictated by the current docs.
   - Bundle all currently known `HARDENED_GATE` drift items into one compact prompt instead of serial pauses.
   - Once the bounded repair slice is approved, continue autonomously unless a new ambiguity appears or a `GOVERNANCE_GATE` condition is triggered.
   - Save before navigating away.
   - Re-open any property-trigger dialog to verify the final state.
6. Report drift explicitly.
   - Distinguish between what you changed, what still differs, and what needs an Adam UI confirmation step.

## Guardrails

- Never navigate away with unsaved changes.
- Always capture before and after evidence for live config changes.
- Do not silently "fix" runtime drift when the spec is unclear; use `HARDENED_GATE`.
- Treat instruction-page content edits as a separate Notion MCP task, not a browser settings task.
- This skill does not currently delegate to sub-agents. If a future version supports delegation, it must follow `docs/sub-agent-contract.md`.

## Gate Protocol

Use the shared gate taxonomy from `ops/notion-workspace/CLAUDE.md` and `ops/notion-workspace/docs/agent-sops.md`.

| Operation | Gate | Notes |
| --- | --- | --- |
| Read the spec, navigate to settings, capture current state, compare runtime to the documented target state, and apply clear safe runtime repairs that restore that baseline | `UNGATED` | Save and verify each logical change set. Adam confirmation still applies only to marking a UI-only step complete. |
| Unclear drift, agent-architecture changes, permission or model changes not plainly dictated by the current docs, and any repo doc edit | `HARDENED_GATE` | Ask a compact question and re-ask if the reply is empty or unclear. |
| Schema, destructive, bulk, or out-of-contract lifecycle changes triggered by the requested repair | `GOVERNANCE_GATE` | Follow the existing Rules of Engagement. |

## Read Next

- Read [browser-ui.md](references/browser-ui.md) for the settings panel layout, edit patterns, and save discipline.
