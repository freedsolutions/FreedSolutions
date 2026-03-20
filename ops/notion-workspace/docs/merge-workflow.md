<!-- Notion Page ID: 323adb01-222f-8111-89c7-c92eaac10ebb -->

# Merge Workflow

Last synced: Session 62 (March 20, 2026)

# When This Applies

Use this workflow when a placeholder Company or duplicate Contact should be merged into the canonical record without leaving stale wiring behind.

---

# Universal Rule: Unwire Before Delete

Before setting any record to `Record Status = Delete`, clear the relevant relations first and verify the reciprocal links are gone.

Use the relation map from the current Delete Unwiring workflow and spot-check the result.

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

## Step 5: Delete-Safe Cleanup

Once the duplicate Company is fully unwired:

1. verify backlinks are empty
2. set `Record Status = Delete`
3. add a note explaining the merge target

---

# Contact Merge Workflow

## Step 1: Preserve The Duplicate Email

Add the duplicate email to the canonical Contact as `Secondary Email` or `Tertiary Email`.

## Step 2: Rewire Meetings, Emails, And Action Items

Move all relations from the duplicate Contact to the canonical Contact.

## Step 3: Delete-Safe Cleanup

Once the duplicate Contact is fully unwired:

1. verify backlinks are empty
2. set `Record Status = Delete`
3. add a merge note that names the canonical Contact

---

# Quick Rules

1. `Domains` is for active operational domains.
2. `Additional Domains` is for merged, subsidiary, alternate, and legacy domains.
3. Both domain fields are used for matching and dedup.
4. Always preserve the canonical dedup signal before deleting the duplicate record.
