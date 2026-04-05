<!-- Generated from "ops/notion-workspace/skills/notion-action-items/references/workflow.md". Edit the repo skill source and rerun ops/notion-workspace/scripts/sync-claude-skill-wrappers.ps1; do not edit this Claude copy directly. -->

# Notion Action Item Workflow

## Resolution

- Accept a Notion URL, raw UUID, Action Item title, or a pre-loaded Action Item context bundle.
- If the user provides a pre-loaded Action Item context bundle, it should identify the page by URL or page ID and include the current Task Name plus whatever status, relations, notes, or attachment context is already known.
- Verify that any supplied bundle, URL, and UUID all resolve to the same Action Item page before proceeding.
- If the bundle page does not exist or the identifiers disagree, stop and report the mismatch.
- If the bundle is valid, use it as the starting record and refresh this minimum field set before risky work: `Task Name`, `Task Notes`, `Status`, `Priority`, `Due Date`, `Record Status`, `Assignee`, `Contact`, `Company`, `Source Meeting`, `Source Email`, and `Files`.
- Treat copied notes, relation summaries, and attachment details as stale when they came from an earlier session, have no capture timestamp, include placeholder values, or the user indicates the record may have changed. Re-fetch only the stale pieces you need.
- If title search returns multiple candidate Action Items, use `HARDENED_GATE` to ask the user to disambiguate before fetching related context or doing work.
- Otherwise fetch the page immediately.
- Extract the Task Name, Task Notes, Status, Priority, Due Date, Record Status, Assignee, Contact, Company, Source Meeting, Source Email, Files, and page body.

## Compact Summary Template

```text
## Action Item: [Task Name]
- Status: [Status] | Priority: [Priority] | Due: [Due Date or "none"]
- Review Trigger: [⚡ marker text from Task Notes, or omit if Status ≠ Review]
- Contact: [name(s)] | Company: [name(s)]
- Source Meeting: [Meeting title or "none"]
- Source Email: [Email subject(s) — list all wired emails, or "none"]
- Target: [Meeting title or Email subject or "none"]
- Notes/Sub-tasks: [brief summary]
- Attached files: [list]
```

## Context Sources

### Wiring-first context

- Contact: role, company, email, LinkedIn, notes
- Company: type, domains, website, notes, tech stack
- Meeting: date, attendees, calendar name, location, transcript or notes
- Email: summary, participants, date

Fetch source and target records separately when both exist. Source explains provenance; target explains where the work is meant to be reviewed, presented, or closed out.

Fetch only what the current task needs.

### External context

- Gmail MCP: relevant mail threads
- Calendar MCP: scheduling or timing context
- Web search: market or product research
- Google Docs: normal fetch flow
- Google Sheets: ask for CSV/XLSX export when the contents matter

## Deliverable Types

| Pattern | Deliverable | Default method |
| --- | --- | --- |
| Analysis or data work | `.xlsx` | Create the file in the workspace |
| Written deliverable | `.docx`, `.pdf`, or `.md` | Create the file in the workspace |
| Email draft | Gmail draft | Create via Gmail MCP when recipients are clear |
| Notion content update | Direct page edit on the target Action Item | Treat as routine follow-through after an explicit execution request |
| Target Action Item `Status` update | Direct property update | Keep it bounded to the target record and requested task |
| Presentation | `.pptx` | Create the file in the workspace |
| Research summary | Inline response | Keep it concise and concrete |

## Gate Protocol

- `UNGATED`: present the deliverable, iterate when the user asks for revisions, and perform bounded target Action Item note/content/`Status` updates that fit the explicit execution request.
- `HARDENED_GATE`: use for ambiguous identity, unclear business intent, missing source data that changes execution, unclear outbound recipients/content, or any repo file edit. Re-ask if the reply is empty or unclear.
- `GOVERNANCE_GATE`: use when `Record Status`, schema, destructive or bulk work, or unrelated-record mutations would invoke the existing Rules of Engagement.

## Review Resolution

When Status = Review, the Action Item has been flagged by a nightly agent or the Follow-Up Agent because new context was received. Review is not a terminal state — it means "needs Adam's assessment."

### Marker vocabulary

| Marker | Set by | Meaning |
| --- | --- | --- |
| `⚡ FOLLOW-UP RECEIVED [date]` | Post-Email Agent (§2.3.1) | An email reply was received on a thread related to this AI |
| `⚡ MEETING FOLLOW-UP [date]` | Post-Meeting Agent (§2.4) | A meeting discussed or advanced this AI's topic |
| `⚡ REOPENED [date]` | Post-Meeting or Post-Email (Done→Review) | New activity surfaced after the AI was marked Done |
| `⚡ FOLLOW-UP FLAGGED [date]` | Follow-Up Agent (manual @mention) | Adam tagged @Follow-Up Agent on a page related to this AI |

### Resolution flow

1. Parse the `⚡` marker(s) from Task Notes to understand what triggered the Review.
2. Read all wired Source Emails (multi-relation) and Source Meetings for full context.
3. Present resolution options to Adam:
   - **Done** — the work is resolved by the new context.
   - **In progress** — more work is needed; update Task Notes with next steps.
   - **Escalate** — surface specific questions or blockers for Adam's decision.
4. Apply the chosen status update. This is `UNGATED` after an explicit execution request.

## Rules

- Follow the wiring.
- Use `HARDENED_GATE` before acting on real ambiguity.
- Create real deliverables.
- Keep changes scoped to the wired source relations; do not infer additional wiring from source notes alone.
- Set `Record Status` only when the request or a documented workflow/test path already authorizes that exact lifecycle move; otherwise use `GOVERNANCE_GATE`.
- Keep changes scoped to the target Action Item unless the user expands scope.

## Known Limitations

- Google Sheets content still needs an export.
- Attached file URLs may not be directly fetchable.
- Cannabis operations tasks often need domain-aware interpretation; clarify only where it changes the output materially.

## Regression Checks

- Complete pre-loaded context bundle vs. standard URL or UUID path: confirm the pre-execution summary matches after any minimal refresh.
- Pre-loaded context bundle with stale status or relations: confirm the skill refreshes the minimum required field set before risky work.
- Pre-loaded context bundle with stale notes or attachments: confirm only the stale fields are refreshed before execution.
- Pre-loaded context bundle with missing required fields: pause and fetch the missing data before execution.
- Pre-loaded context bundle with no capture timestamp: confirm copied notes, relations, and attachments are treated as stale and refreshed as needed.
- Pre-loaded context bundle with a missing or mismatched page ID, URL, or UUID: confirm the skill reports the mismatch and stops before execution.
- Standard URL or UUID path plus an explicit execution request: confirm the skill still performs an initial fetch, produces the same pre-execution summary, and can perform bounded target note/content/`Status` updates without an extra approval loop.
- Source relations present vs. absent on the same Action Item: confirm the summary reports source context after the minimum refresh.
- Title search with multiple matching Action Items: confirm the skill asks for disambiguation instead of selecting one arbitrarily.
- Unclear outbound recipient or outbound content: confirm the skill uses `HARDENED_GATE` before proceeding.
- Empty or ambiguous reply to a required gate question: confirm the skill re-asks before proceeding.
- Review-status AI: confirm the skill surfaces the `⚡` trigger context from Task Notes and presents resolution options (Done / In progress / escalate) rather than treating Review as a normal starting status.
- Review-status AI with multiple Source Emails: confirm the skill reads all wired Source Emails for context, not just the first.
