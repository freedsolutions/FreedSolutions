# Notion Action Item Workflow

## Resolution

- Accept a Notion URL, raw UUID, or Action Item title.
- Fetch the page immediately.
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
