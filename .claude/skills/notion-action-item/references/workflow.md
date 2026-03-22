# Notion Action Item Workflow

## Resolution

- Accept a Notion URL, raw UUID, Action Item title, or a pre-loaded Action Item context bundle.
- If the user provides a pre-loaded Action Item context bundle, it should identify the page by URL or page ID and include the current Task Name plus whatever status, relations, notes, or attachment context is already known.
- Verify that any supplied bundle, URL, and UUID all resolve to the same Action Item page before proceeding.
- If the bundle page does not exist or the identifiers disagree, stop and report the mismatch.
- If the bundle is valid, use it as the starting record and refresh this minimum field set before risky work: `Task Name`, `Task Notes`, `Status`, `Priority`, `Due Date`, `Record Status`, `Assignee`, `Contact`, `Company`, `Source Meeting`, `Source Email`, and `Attach File`.
- Treat copied notes, relation summaries, and attachment details as stale when they came from an earlier session, have no capture timestamp, include placeholder values, or the user indicates the record may have changed. Re-fetch only the stale pieces you need.
- If title search returns multiple candidate Action Items, pause and ask the user to disambiguate before fetching related context or doing work.
- Otherwise fetch the page immediately.
- Extract the Task Name, Task Notes, Status, Priority, Due Date, Record Status, Assignee, Contact, Company, Source Meeting, Source Email, Attach File, and page body.

## Compact Summary Template

```text
## Action Item: [Task Name]
- Status: [Status] | Priority: [Priority] | Due: [Due Date or "none"]
- Contact: [name(s)] | Company: [name(s)]
- Source: [Meeting title or Email subject]
- Notes/Sub-tasks: [brief summary]
- Attached files: [list]
```

## Context Sources

### Wiring-first context

- Contact: role, company, email, LinkedIn, notes
- Company: type, domains, website, notes, tech stack
- Meeting: date, attendees, calendar name, location, transcript or notes
- Email: summary, participants, date

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
| Notion content update | Direct page edit | Update after approval |
| Presentation | `.pptx` | Create the file in the workspace |
| Research summary | Inline response | Keep it concise and concrete |

## Approval Gates

1. Present the deliverable first.
2. Iterate until approved.
3. Draft the follow-up email when needed.
4. Ask before any Notion status or lifecycle update.

## Rules

- Follow the wiring.
- Ask before acting on real ambiguity.
- Create real deliverables.
- Set `Record Status` only after approval.
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
- Standard URL or UUID path: confirm the skill still performs an initial fetch and produces the same pre-execution summary.
- Title search with multiple matching Action Items: confirm the skill asks for disambiguation instead of selecting one arbitrarily.
