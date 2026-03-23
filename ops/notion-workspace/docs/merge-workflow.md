<!-- Notion Page ID: 323adb01-222f-8111-89c7-c92eaac10ebb -->

# Merge Workflow

> Live Notion doc. This repo file is the source of truth for the mapped Notion page. Sync local changes to Notion in the same task.

Last synced: March 22, 2026

# When This Applies

Use this workflow when a placeholder Company or duplicate Contact should be merged into the canonical record without leaving stale wiring behind.

---

# Company Merge Workflow

## Step 1: Decide Where The Domain Belongs

Use these rules:

- `Domains`
  - primary operational domains
  - employees actively send email from them today
- `Additional Domains`
  - merged domains
  - subsidiary domains
  - legacy domains
  - alternate domains kept for matching and dedup

Promotion rule:

- if the merged domain becomes a current day-to-day operating domain, add it to `Domains`
- otherwise add it to `Additional Domains`

Do not treat every merged domain as primary by default.

## Step 2: Update The Canonical Company

Add the domain to the correct field on the canonical Company.

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

1. `Domains` is for active operational domains.
2. `Additional Domains` is for merged, subsidiary, alternate, and legacy domains.
3. Both domain fields are used for matching and dedup.
4. Always preserve the canonical dedup signal before deleting the duplicate record.
