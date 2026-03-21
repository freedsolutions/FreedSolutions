---
name: notion-action-item
description: Execute a Notion Action Item end-to-end from its URL, UUID, title, or a pre-loaded context bundle using CRM wiring, related records, and explicit approval gates. Use when the user wants an Action Item worked, its meeting or email context reviewed, a deliverable produced, or the record closed after confirmation.
---

# Notion Action Item

Read `ops/notion-workspace/CLAUDE.md` first when that file exists in the workspace. It holds the current DB IDs, lifecycle rules, and review gate.

## Workflow

1. Resolve the Action Item from the user input.
   - Accept a Notion URL, UUID, title search, or a pre-loaded Action Item context bundle.
   - If title search returns multiple plausible matches, stop and ask the user to disambiguate. Do not choose arbitrarily.
   - If the user already provided the target record and wiring context, use that as the starting point and refresh the minimum required field set defined in `references/workflow.md` before risky work.
   - Otherwise fetch the record immediately before doing any work from memory.
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

- Always resolve the Action Item against the Notion page before risky work.
- Treat an explicit pre-loaded context bundle as valid input, but verify the page exists and refresh the minimum required field set from `references/workflow.md` before proceeding.
- A valid pre-loaded context bundle should identify the target page by URL or page ID and include the current Task Name plus whatever status, relations, notes, or attachment context the user already has.
- Treat copied notes, relation summaries, and attachment details as stale when they came from an earlier session, have no capture timestamp, include placeholder text, or the user indicates the record may have changed. Re-fetch only the stale pieces you need.
- If the bundle page ID does not exist, or if a supplied URL or UUID points at a different Action Item than the bundle, stop and surface the mismatch before doing any work.
- Treat wiring as authoritative unless the user explicitly overrides it.
- Do not create Contacts, Companies, or Meetings from this skill.
- Do not change `Record Status` without explicit approval.
- Treat deliverable review and Notion updates as separate approval gates.

## Read Next

- Read [workflow.md](references/workflow.md) for the detailed execution pattern, deliverable types, known limitations, and regression checks for the pre-loaded context path.
