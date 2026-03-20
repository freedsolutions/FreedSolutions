---
name: notion-action-item
description: Execute a Notion Action Item end-to-end from its URL, UUID, or title using CRM wiring, related records, and explicit approval gates. Use when the user wants an Action Item worked, its meeting or email context reviewed, a deliverable produced, or the record closed after confirmation.
---

# Notion Action Item

Read `ops/notion-workspace/CLAUDE.md` first when that file exists in the workspace. It holds the current DB IDs, lifecycle rules, and review gate.

## Workflow

1. Resolve the Action Item from the user input.
   - Accept a Notion URL, UUID, or title search.
   - Fetch the record immediately before doing any work from memory.
2. Summarize the record before execution.
   - Include status, priority, due date, wired Contact and Company, source Meeting or Email, notes, and attachments.
3. Follow the wiring.
   - Fetch only the related records that matter to the task: Contact, Company, Source Meeting, Source Email, and attached files.
   - Use the wired records as the context backbone instead of ad hoc searching.
4. Gather extra context only when needed.
   - Use Gmail, Calendar, web, or uploaded files when the task actually depends on them.
   - Ask for exported CSV/XLSX files when the work depends on Google Sheets contents.
5. Confirm the deliverable only when material ambiguity remains.
   - Do not ask for confirmation that can be resolved from the data.
   - Do pause before acting on unclear business intent, missing source data, or risky outbound work.
6. Produce the real deliverable.
   - Prefer actual files, Gmail drafts, or direct Notion edits over describing what you would do.
   - Show reasoning for analytical work before the final artifact.
7. Close the loop carefully.
   - Wait for explicit approval before updating the Action Item's Status, Record Status, or notes.
   - Do not modify unrelated CRM records.

## Guardrails

- Always fetch the Action Item first.
- Treat wiring as authoritative unless the user explicitly overrides it.
- Do not create Contacts, Companies, or Meetings from this skill.
- Do not change `Record Status` without explicit approval.
- Treat deliverable review and Notion updates as separate approval gates.

## Read Next

- Read [workflow.md](references/workflow.md) for the detailed execution pattern, deliverable types, and known limitations.
