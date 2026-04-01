# Schema Quick Reference

> Context card — extracted from `ops/notion-workspace/CLAUDE.md` and `docs/agent-sops.md`. Verify against the canonical sources if stale.

## Contacts DB

| Property | Type | Notes |
|----------|------|-------|
| Contact Name | title | |
| Display Name | formula | |
| QC | formula | |
| Email | email | Dedup field |
| Secondary Email | email | Dedup field |
| Tertiary Email | email | Dedup field |
| Phone | phone | |
| Pronouns | select | |
| Nickname | rich_text | |
| LinkedIn | url | Canonical form: `https://www.linkedin.com/in/<slug>` |
| Company | relation | |
| Role / Title | rich_text | |
| Record Status | select | `Draft` / `Active` |
| Contact Notes | rich_text | |

## Companies DB

| Property | Type | Notes |
|----------|------|-------|
| Company Name | title | |
| Company Type | select | Tech Stack, Operator, Network, Personal |
| QC | formula | |
| Domains | rich_text | Primary domains — dedup field (legacy — see Domains DB) |
| Additional Domains | rich_text | Merged/subsidiary/sender-level — dedup field. May hold full sender email for platform companies. (legacy — see Domains DB) |
| States | select | Default: "All" |
| Website | url | |
| Contacts | relation | |
| Emails | rollup | |
| Meetings | rollup | |
| Action Items | relation | |
| Engagements | relation | |
| Tech Stack | multi_select | |
| Record Status | select | `Draft` / `Active` |
| Company Notes | rich_text | |

## Action Items DB

| Property | Type | Notes |
|----------|------|-------|
| Task Name | title | |
| Type | formula | |
| Status | select | Options: `Not started`, `In Progress`, `Done`, `Review`. `Review` is set by agents when a Follow Up receives a response. Adam reviews and decides: Done, back to In Progress, or other action. |
| Priority | select | |
| Record Status | select | `Draft` / `Active` |
| Task Notes | rich_text | |
| Due Date | date | |
| Created Date | created_time | |
| Contact | relation | Counterparty person |
| Company | relation | Owning/execution context (not counterparty's employer) |
| Assignee | people | |
| Source Meeting | relation | Where the work originated |
| Source Email | relation | Where the work originated |
| Target Meeting | relation | Optional future touchpoint for review/close-out |
| Target Email | relation | Optional future touchpoint for review/close-out |
| Attach File | files | |
| QC | formula | |

## Meetings DB

| Property | Type | Notes |
|----------|------|-------|
| Meeting Title | title | |
| Calendar Event ID | rich_text | |
| Calendar Name | select | Live options: `Adam - Business`, `Adam - Personal` only |
| Date | date | |
| Contacts | relation | |
| Companies | rollup | |
| Action Items | relation | |
| Target Action Items | relation | Reciprocal of Action Items.Target Meeting |
| Series | relation | |
| Series Key | rich_text | Google `recurringEventId` on recurring instances and series parents |
| Instances | relation | |
| Is Series Parent | checkbox | |
| Series Status | rollup | |
| Location | rich_text | |
| Record Status | select | `Draft` / `Active` |
| QC | formula | |

## Emails DB

| Property | Type | Notes |
|----------|------|-------|
| Email Subject | title | |
| Thread ID | rich_text | Canonical dedup key (exact match, not subject line) |
| Direction | formula | |
| Date | date | |
| Contacts | relation | |
| Companies | rollup | |
| Action Items | relation | |
| Target Action Items | relation | Reciprocal of Action Items.Target Email |
| Labels | multi_select | Routing: `Primitiv`, `LinkedIn`, `DMC`. Pulled from Gmail API thread labels, filtering out system labels. |
| Source | select | `Email - Freed Solutions`, `Email - Personal`, `LinkedIn - DMs` |
| Record Status | select | `Draft` / `Active` |
| Email Notes | rich_text | |
| QC | formula | |
| Created Timestamp | created_time | |

## Domains DB

| Property | Type | Notes |
|----------|------|-------|
| Domain | title | Canonical domain or subdomain. Page icon: 🌐 |
| 💼 Companies | relation | Parent Company |
| Routing Tier | select | Label, Silent Label, Archive, Block, Draft Intake, None. Archive, Silent Label, and Block tier domains do not create Email records. |
| Filter Shape | select | Domain, Sender, None |
| Gmail Label | rich_text | |
| Gmail Filter ID | rich_text | |
| Is Generic | checkbox | |
| Source Type | select | Primary, Additional, Sender-Level |
| Notes | rich_text | |
| Record Status | select | `Draft` / `Active` |

## QC Formula Logic

Each CRM database has a `QC` formula that validates required fields. Returns `"TRUE"` when all required fields are populated, or `"missing:<field>"` for the first gap found.

### Contacts QC

Checks: Contact Name, Record Status, Email, Role/Title, Company.

```
if(empty(Contact Name), "missing:name",
if(empty(Record Status), "missing:status",
if(empty(Email), "missing:email",
if(empty(Role / Title), "missing:role",
if(empty(Company), "missing:company", "TRUE")))))
```

### Companies QC

Checks: Company Name, Record Status, Company Type, 🌐 Domains, States, Website, Contacts.

```
if(empty(Company Name), "missing:name",
if(empty(Record Status), "missing:status",
if(empty(Company Type), "missing:type",
if(empty(🌐 Domains), "missing:domains",
if(empty(format(States)), "missing:states",
if(empty(Website), "missing:website",
if(empty(Contacts), "missing:contacts", "TRUE")))))))
```

### Action Items QC

Checks: Task Name, Record Status, Status, Priority, Due Date, Contact, Company, Source (Meeting or Email). Also flags past-due items.

```
if(empty(Task Name), "missing:task_name",
if(empty(Record Status), "missing:record_status",
if(empty(format(Status)), "missing:task_status",
if(empty(Priority), "missing:priority",
if(empty(Due Date), "missing:due_date",
if(empty(Contact), "missing:contact",
if(empty(Company), "missing:company",
if(empty(Source Meeting) and empty(Source Email),
"missing:source",
if(Due Date < today() and format(Status) != "Done",
"past_due", "TRUE")))))))))
```

> **Note:** Action Items QC uses `today()` for the past_due check, not `now()`.
>
> **Note:** Items with `Status = Review` may also flag as `past_due` if their Due Date has passed. This is expected — the item needs attention AND is overdue.

### Meetings QC

Checks: Meeting Title, Record Status, Calendar Name, Calendar Event ID, Date, Contacts. Series Parents always pass.

```
if(Is Series Parent, "TRUE",
if(empty(Meeting Title), "missing:Meeting Title",
if(empty(Record Status), "missing:Record Status",
if(empty(Calendar Name), "missing:Calendar Name",
if(empty(Calendar Event ID), "missing:Calendar Event ID",
if(empty(Date), "missing:Date",
if(empty(Contacts), "missing:Contacts", "TRUE")))))))
```

### Emails QC

Checks: Email Subject, Record Status, Thread ID, Date, Contacts, Source.

```
if(empty(Email Subject), "missing:email_subject",
if(empty(Record Status), "missing:record_status",
if(empty(Thread ID), "missing:thread_id",
if(empty(Date), "missing:date",
if(empty(Contacts), "missing:contacts",
if(empty(Source), "missing:source", "TRUE"))))))
```

> **Note:** The `From` field has been removed from the Emails DB (redundant with Contact relation). The live QC formula in Notion must also be updated to remove the `From` check — Adam UI step.

### Domains QC

Checks: Domain, Record Status, Company, Routing Tier, Source Type. Conditionally checks Gmail Label and Gmail Filter ID only when Routing Tier requires a filter (not Draft Intake or None).

```
if(empty(Domain), "missing:domain",
if(empty(Record Status), "missing:record_status",
if(empty(Companies), "missing:company",
if(empty(Routing Tier), "missing:routing_tier",
if(empty(Source Type), "missing:source_type",
if(and(Routing Tier != "Draft Intake",
       Routing Tier != "None",
       empty(Gmail Label)), "missing:gmail_label",
if(and(Routing Tier != "Draft Intake",
       Routing Tier != "None",
       empty(Gmail Filter ID)), "missing:filter_id",
"TRUE")))))))
```

## Dedup Rules

| Entity | Match fields |
|--------|-------------|
| Contacts | Email + Secondary Email + Tertiary Email (all three checked) |
| Companies | Domains + Additional Domains (both checked). Additional Domains may hold full sender email for platform companies. |
| Emails | Thread ID (exact match, not subject line) |

## Normalization

- **LinkedIn URLs:** `https://www.linkedin.com/in/<slug>` (canonical form)
- **Emails:** lowercase + trim
- **Domains:** hostname only (no protocol, no path)
- **Company domain matching:** Check domains first, then fall back to full sender email address against Additional Domains
