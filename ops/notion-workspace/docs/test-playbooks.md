# Agent Test Playbooks

Step-by-step test procedures for each Notion Custom Agent.

---

## Post-Meeting Agent

### Trigger
Property change: Meetings → Record Status = Draft + page-content-edit CHECKED

### Setup
1. Create a meeting page: `[TEST] Agent Smoke Test — [date]`
2. Set Calendar Event ID: `test-event-[timestamp]`, Date: today
3. Add body content simulating an AI summary with `### Action Items` and `### Attendees`

### Fire
1. Edit the page body (satisfies page-content-edit)
2. Set Record Status = Draft via `notion-update-page`

### Verify
- [ ] Action Items created with Source Meeting → test meeting
- [ ] Contacts matched or created from attendee emails
- [ ] Calendar Name populated on the meeting page
- [ ] Agent Config → Last Successful Run timestamp updated

### Cleanup
Set test meeting + created Action Items + created Contacts → Record Status = Delete

---

## Curated Notes Agent

### Trigger
Property change: Meetings → Record Status = Active (page-content-edit UNCHECKED)

### Setup
Use an existing Draft meeting that has been processed by Post-Meeting Agent (has body content)

### Fire
Set Record Status = Active via `notion-update-page` (do NOT edit page body)

### Verify
- [ ] Meeting page body updated with curated notes
- [ ] Action Items count unchanged (no duplicates)
- [ ] Original content preserved

### Cleanup
Revert Record Status if needed. No new records to clean up.

---

## Delete Unwiring Agent

### Trigger
Property change: Record Status = Delete on any of 5 DBs (page-content-edit UNCHECKED)

### Setup
1. Create test contact: `[TEST] Delete Agent Test Contact`, Email: `deletetest@example.com`
2. Wire to an existing Active company

### Fire
Set test contact's Record Status = Delete via `notion-update-page`

### Verify
- [ ] All relations on test contact cleared (Company, Meetings, Emails)
- [ ] Reciprocal side cleared (company no longer lists test contact)
- [ ] Contact Notes contain deletion explanation
- [ ] Record Status = Delete (unchanged)

### Cleanup
Adam hard-deletes from Notion UI

---

## Contact & Company Agent

### Trigger
@mention ONLY

### Setup
Navigate to a test contact page with minimal data (name + email)

### Fire
In page body, type: `@Contact & Company Agent Please enrich this contact`

### Verify
- [ ] Contact fields enriched (Company, Role/Title, LinkedIn)
- [ ] If new company created → Record Status = Draft, Domains populated
- [ ] No duplicate companies (check by domain)

### Cleanup
Revert test contact or set Record Status = Delete

---

## Post-Email Agent

### Trigger
Scheduled (10:30 PM ET) + @mention

### Setup
For @mention test: navigate to any workspace page

### Fire
Type: `@Post-Email Agent Process any new email threads from today`

### Verify
- [ ] New Email stubs in Emails DB with Thread ID
- [ ] Contacts wired via email matching
- [ ] Agent Config → Post-Email Agent Last Run updated

### Cleanup
Set any test email stubs → Record Status = Delete
