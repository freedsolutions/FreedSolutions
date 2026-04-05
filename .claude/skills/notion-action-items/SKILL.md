---
name: notion-action-items
description: Execute a Notion Action Item end-to-end from its URL, UUID, title, or a pre-loaded context bundle using CRM wiring, related records, and the shared gate taxonomy. Use when the user wants an Action Item worked, its meeting or email context reviewed, or a deliverable produced and the target record updated.
---

<!-- Generated from "ops/notion-workspace/skills/notion-action-items/SKILL.md". Edit the repo skill source and rerun ops/notion-workspace/scripts/sync-claude-skill-wrappers.ps1; do not edit this Claude copy directly. -->

# Notion Action Item

Read `ops/notion-workspace/CLAUDE.md` first when that file exists in the workspace. It holds the current DB IDs, lifecycle rules, and review gate.

## Workflow

1. Resolve the Action Item from the user input.
   - Accept a Notion URL, UUID, title search, or a pre-loaded Action Item context bundle.
   - If title search returns multiple plausible matches, use `HARDENED_GATE` to ask the user to disambiguate. Do not choose arbitrarily.
   - If the user already provided the target record and wiring context, use that as the starting point and refresh the minimum required field set defined in `references/workflow.md` before risky work.
   - Otherwise fetch the record immediately before doing any work from memory.
2. Summarize the record before execution.
   - Include status, priority, due date, wired Contact and Company, source Meeting or Email, notes, and attachments.
   - When Status = Review, highlight the review trigger first. Look for `⚡` markers in Task Notes (`⚡ FOLLOW-UP RECEIVED`, `⚡ MEETING FOLLOW-UP`, `⚡ REOPENED`, `⚡ FOLLOW-UP FLAGGED`) and present what triggered the Review before asking for direction. Review is not a terminal state — it means "needs Adam's assessment."
2.5. Resolve the Review when Status = Review.
   - When Adam says "work this AI" and Status = Review, treat this as "resolve the Review."
   - Summarize the trigger by parsing `⚡` markers from Task Notes. If the AI was previously Done and is now Review, the `⚡ REOPENED` marker means new context surfaced after completion.
   - Read all wired Source Emails (multi-relation) and Source Meetings for full context on what triggered the Review.
   - Present resolution options: mark Done (work is resolved), move back to In progress (needs more work), or escalate to Adam with specific questions.
   - This step is `UNGATED` — it is bounded target AI status work after an explicit execution request.
3. Follow the wiring.
   - Fetch only the related records that matter to the task: Contact, Company, Source Meeting, Source Email, and attached files.
   - Source Email is a multi-relation — read all wired Source Emails, not just the first. Multiple threads may contribute provenance for the same work item.
   - Trust pre-wired relations from nightly agents (Post-Meeting, Post-Email, Follow-Up) as the context backbone. Do not re-query for context that is already present in Source Meeting/Source Email relations.
   - Use the wired records as the context backbone instead of ad hoc searching.
4. Gather extra context only when needed.
   - Use Gmail, Calendar, web, or uploaded files when the task actually depends on them.
   - Ask for exported CSV/XLSX files when the work depends on Google Sheets contents.
5. Use `HARDENED_GATE` only when material ambiguity remains.
   - Do not ask for confirmation that can be resolved from the data.
   - Use `HARDENED_GATE` before acting on unclear business intent, missing source data that changes execution, or risky outbound work.
6. Produce the real deliverable.
   - Prefer actual files, Gmail drafts, or direct Notion edits over describing what you would do.
   - Show reasoning for analytical work before the final artifact.
7. Close the loop carefully.
   - Update target Action Item notes/content and bounded `Status` changes as routine follow-through after an explicit execution request.
   - Keep changes scoped to the target Action Item unless the user expands scope.
   - Use `GOVERNANCE_GATE` for `Record Status` changes unless the request or a documented workflow/test path already authorizes that exact lifecycle move.
   - Do not modify unrelated CRM records.
   - After completing the Action Item, suggest tagging `@Follow-Up Agent` on the source Meeting or Email page when: the AI is a Follow Up type (completion may affect the counterparty's related AIs), or the AI's Contact has other open AIs that might be affected by this completion. This is informational — do not invoke the agent automatically.

## Guardrails

- Tags are required on Contacts (QC-enforced), not on Action Items. When summarizing an AI, pull Tag context from the wired Contact relation. Reference `QC Requirements` in `agent-sops.md` for the full required-fields spec per DB.
- Always resolve the Action Item against the Notion page before risky work.
- Treat an explicit pre-loaded context bundle as valid input, but verify the page exists and refresh the minimum required field set from `references/workflow.md` before proceeding.
- A valid pre-loaded context bundle should identify the target page by URL or page ID and include the current Task Name plus whatever status, relations, notes, or attachment context the user already has.
- Treat copied notes, relation summaries, and attachment details as stale when they came from an earlier session, have no capture timestamp, include placeholder text, or the user indicates the record may have changed. Re-fetch only the stale pieces you need.
- If the bundle page ID does not exist, or if a supplied URL or UUID points at a different Action Item than the bundle, stop and surface the mismatch before doing any work.
- Treat wiring as authoritative unless the user explicitly overrides it.
- Read source and target relations whenever they exist, but do not infer new target wiring from the notes alone.
- Do not create Contacts, Companies, or Meetings from this skill.
- Use `HARDENED_GATE` for ambiguous title resolution, mismatched page identity, unclear outbound recipients/content, and repo file edits.
- Keep bounded target Action Item updates inside the requested task `UNGATED`; do not treat deliverable review and target-page updates as separate approval loops.
- Do not change `Record Status` outside `GOVERNANCE_GATE`.
- This skill does not delegate to sub-agents.

## Gate Protocol

Use the shared gate taxonomy from `ops/notion-workspace/CLAUDE.md` and `ops/notion-workspace/docs/agent-sops.md`.

| Operation | Gate | Notes |
| --- | --- | --- |
| Resolve by URL or UUID, minimal refresh, wiring-first context, external context gathering, deliverable creation, target Action Item notes/content updates, and bounded `Status` updates after an explicit execution request | `UNGATED` | Keep changes scoped to the target Action Item. |
| Ambiguous title disambiguation, unclear business intent, missing source data that changes execution, mismatched pre-loaded context, unclear outbound recipients/content, and any repo file edit | `HARDENED_GATE` | Ask one compact decision-shaped question and re-ask if the reply is empty or unclear. |
| `Record Status` changes unless already authorized by the request or a documented workflow/test path; schema, destructive, bulk, or unrelated-record mutations | `GOVERNANCE_GATE` | Follow the existing Rules of Engagement. |

## Read Next

- Read [workflow.md](references/workflow.md) for the detailed execution pattern, deliverable types, known limitations, and regression checks for the pre-loaded context path.
