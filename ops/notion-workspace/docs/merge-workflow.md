<!-- Notion Page ID: 323adb01-222f-8111-89c7-c92eaac10ebb -->

# Merge Workflow

> Live Notion doc. This repo file is the source of truth for the mapped Notion page. Sync local changes to Notion in the same task.

Last synced: April 3, 2026 (Session 55: Legacy domain field references removed — Domains DB is sole domain source)

# When This Applies

Use this workflow when a placeholder Company or duplicate Contact should be merged into the canonical record without leaving stale wiring behind.

---

# Company Merge Workflow

## Step 1: Decide the Domain's Source Type

Use these rules in the **Domains DB**:

- `Primary` — primary operational domains; employees actively send email from them today
- `Additional` — merged, subsidiary, legacy, or alternate domains kept for matching and dedup
- `Sender-Level` — full sender email addresses for platform companies where the domain is too broad

Promotion rule:

- if the merged domain becomes a current day-to-day operating domain, set Source Type to `Primary`
- otherwise set Source Type to `Additional`

Do not treat every merged domain as Primary by default.

## Step 2: Update the Domains DB

Create or update a Domain record for the merged domain with the correct Source Type and wire the 💼 Companies relation to the canonical Company.

## Step 3: Rewire Contacts

Move all Contacts from the duplicate Company to the canonical Company.

## Step 4: Rewire Action Items

Move any Action Items still wired to the duplicate Company to the canonical Company.

## Step 5: Cleanup

Once the duplicate Company has no remaining contacts or action items:

1. set `Record Status = Delete`
2. add a note explaining the merge target
3. trash the record — Notion automatically clears any remaining reciprocal links

---

# Contact Merge Workflow

## Step 1: Preserve The Duplicate Email

Add the duplicate email to the canonical Contact as `Secondary Email` or `Tertiary Email`.

## Step 2: Rewire Meetings, Emails, And Action Items

Move all relations from the duplicate Contact to the canonical Contact.

## Step 3: Cleanup

Once the duplicate Contact has no remaining relations:

1. set `Record Status = Delete`
2. add a merge note that names the canonical Contact
3. trash the record — Notion automatically clears any remaining reciprocal links

---

# Quick Rules

1. Domain records in the **Domains DB** drive all domain matching and dedup.
2. Source Type `Primary` = active operational; `Additional` = merged/subsidiary/alternate/legacy; `Sender-Level` = full email for platform companies.
3. Always preserve the canonical dedup signal (Domain records + 💼 Companies relation) before deleting the duplicate record.
