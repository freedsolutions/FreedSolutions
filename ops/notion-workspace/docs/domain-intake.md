# Domain Intake Workflow

Operator checklist for when the Post-Email agent creates a "Review new domain: [domain]" Action Item (Step 2.4.1 of Post-Email Instructions).

## Routing Tiers

| Tier | What it means | Gmail filter behavior |
|------|--------------|----------------------|
| **Label** | Active business contact, ongoing relationship. Adam reviews in inbox. | Apply company label. Mail stays in inbox, unread. |
| **Silent Label** | Tracked source, agent processes automatically. No inbox review needed. | Apply label, mark read. Stays in All Mail. |
| **Archive** | Worth keeping searchable but not surfacing. | Apply label, skip inbox, mark read. |
| **Block** | Spam-adjacent, no CRM value. | Delete or skip inbox entirely. |
| **Draft Intake** | New/unreviewed domain. No filter yet. | No Gmail filter. Mail arrives normally until tier is set. |

## Decision Checklist

For each "Review new domain" Action Item:

1. Open the Draft Company record linked to the Action Item.
2. Review the domain, sender, and email thread context in Task Notes.
3. Decide the routing tier (Label / Silent Label / Archive / Block).
4. In Gmail Settings > Filters (or via `gmail_filter_manager.py --create`):
   - Create or update a filter matching the domain (`from:*@[domain]`) or specific sender.
   - Apply the Gmail label matching the company name (create the label first if needed).
   - Filter actions are determined by the tier (see table above).
5. In Notion:
   - If the Company is worth keeping: promote to Active, verify Domains/Additional Domains, set Company Type.
   - If not worth keeping: trash the record directly.
   - Verify the Gmail label exists as an `Emails.Labels` option in the Emails DB schema.
6. Promote the Domain record to Active (Record Status = Active). This triggers filter eligibility — the next run of `gmail_filter_manager.py --create` will create the Gmail filter automatically.
7. Mark the Action Item as Done.

## Edge Cases

- **Generic domains** (gmail.com, outlook.com, etc.): no company filter needed. The Contact-level record is sufficient. Mark the AI as Done with a note.
- **Subdomain of an existing Company**: add to Additional Domains on the existing Company instead of keeping the new Draft. Mark the AI as Done with a note.
- **Multiple senders at the same new domain**: one filter covers the domain. Don't create per-sender filters unless routing differs by sender.
