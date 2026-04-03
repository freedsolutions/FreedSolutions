# Domain Intake Workflow

Operator checklist for when the Post-Email script creates a "Review new domain: [domain]" Action Item.

## Gmail Filter Decision Model

The script classifies threads by **inbox state** — whether Gmail's filters labeled and/or archived the thread. There are no routing tiers. The decision is binary:

| Decision | What it means | Gmail filter action |
|----------|--------------|---------------------|
| **Track** | Business contact worth CRM visibility. Create a Gmail filter with a company label. | `from:*@domain` → apply label. Optionally skip inbox for low-priority sources. |
| **Don't track** | No CRM value. Let Gmail's default behavior handle it, or block. | No filter needed. Archive/delete manually, or add a filter to auto-delete. |

## Decision Checklist

For each "Review new domain" Action Item:

1. Open the Draft Company record linked to the Action Item.
2. Review the domain, sender, and email thread context in Task Notes.
3. **Create Gmail filter?**
   - If yes: create a filter matching the domain (`from:*@[domain]`) or specific sender.
   - Apply the Gmail label matching the company name (create the label first if needed).
   - Choose filter behavior: label only (stays in inbox), or label + skip inbox (auto-filed).
4. In Notion:
   - If the Company is worth keeping: promote to Active, verify Domains, set Company Type.
   - If not worth keeping: trash the record directly.
   - Verify the Gmail label exists as an `Emails.Labels` option in the Emails DB schema.
5. Promote the Domain record to Active (Record Status = Active).
6. Mark the Action Item as Done.

## Edge Cases

- **Generic domains** (gmail.com, outlook.com, etc.): no company filter needed. The Contact-level record is sufficient. Mark the AI as Done with a note.
- **Subdomain of an existing Company**: create a Domain record in the Domains DB with Source Type = `Additional` and wire the 💼 Companies relation to the existing Company instead of keeping the new Draft. Mark the AI as Done with a note.
- **Multiple senders at the same new domain**: one filter covers the domain. Don't create per-sender filters unless routing differs by sender.
