<!-- Notion Page ID: 323adb01-222f-8111-89c7-c92eaac10ebb -->
# Merge Workflow

# When This Applies

A placeholder Company exists in the Companies DB for a domain that actually belongs to an existing Company. This happens when an attendee's email domain (e.g., `subsidiary.com`) doesn't match any Company's Domains property, so Agent 1 or Quick Sync creates a placeholder. Later, Adam realizes the domain belongs to an existing Company (e.g., "Parent Corp" with domain `parentcorp.com`).

**Example:** Agent creates placeholder Company "subsidiary.com" (Record Status = Draft). Adam knows subsidiary.com is actually part of Parent Corp. The placeholder needs to be merged into Parent Corp.

---

# Step-by-Step Merge Procedure

## Step 1: Add the Domain to the Real Company

Open the **real Company** (e.g., "Parent Corp") in the Companies DB. Edit the **Domains** property to include the new domain.

**Before:** `parentcorp.com`

**After:** `parentcorp.com, subsidiary.com`

> **Why this is the critical step:** Once the domain is added, all future agent runs will automatically match `subsidiary.com` to "Parent Corp." Steps 2-4 are cleanup of existing records only.

## Step 2: Re-wire Contacts to the Real Company

Find all Contacts currently linked to the placeholder Company. Update each Contact's **Company** relation to point to the real Company instead.

**How to find them:** Open the placeholder Company page -- its backlinks / relation will show all linked Contacts.

## Step 3: Re-wire Action Items to the Real Company

Find all Action Items currently linked to the placeholder Company. Update each Action Item's **Company** relation to point to the real Company.

**How to find them:** Same approach -- check the placeholder Company's backlinks for Action Items.

> **Order matters:** Do Contacts (Step 2) before Action Items (Step 3). Action Items derive their Company from the Contact's Company (per Agent 2 rules), so fixing Contacts first ensures any *new* Action Items created after the merge inherit the correct Company automatically.

## Step 4: Flag or Delete the Placeholder Company

Once all Contacts and Action Items have been re-wired:

- Set the placeholder's **Record Status** to **Delete** (red). This flags it in the Delete view for Adam to hard-delete.
- Alternatively, Adam can hard-delete it immediately from the Companies DB.

**Why delete?** The placeholder's domain is now on the real Company. There is no dedup risk -- future agent runs will match the domain to the real Company. Keeping the placeholder would just be noise.

---

# Edge Case: Enriched Placeholder

If the placeholder Company has been **set to Active and enriched** (Adam added Industry, States, Notes, etc.) before realizing it's a duplicate:

1. Transfer any enrichment data (Industry, States, Notes, Website) to the real Company before deleting.
1. Then proceed with Steps 1-4 as normal.

This is unlikely but possible if Adam approves a placeholder before discovering the relationship.

---

# Frequency

This is expected to be **rare**. The scenario only arises when:

- A new attendee has an email at a subsidiary/alternate domain
- That domain isn't already listed on the parent Company
- The agents create a placeholder before Adam adds the domain

For now, this remains a **manual workflow**. If it starts happening frequently, it could be partially automated (e.g., a merge button or agent helper).

---

# Contact Merge (Email-Based Duplicates)

When a duplicate Contact exists because Agent 1 or Quick Sync created a new contact from an email address that actually belongs to an existing contact (matched via Secondary Email or Tertiary Email that wasn't checked at creation time).

**Example:** Agent creates placeholder Contact "Morgan" from `morgantmendoza@gmail.com`. Adam knows this is Morgan Carlone's personal email. The placeholder needs to be merged into the canonical Morgan Carlone record.

## Step-by-Step

### Step 1: Add the Email to the Canonical Contact

Open the **canonical Contact** (e.g., "Morgan Carlone"). Set the email as **Secondary Email** (or **Tertiary Email** if Secondary is already populated).

> **Why this is the critical step:** Once the email is on the canonical contact, all future agent dedup checks will catch it. Steps 2-3 are cleanup of existing records only.

### Step 2: Re-wire Meetings and Action Items

Find all Meetings and Action Items currently linked to the duplicate Contact. Update each record's **Contact** relation to point to the canonical Contact instead.

**How to find them:** Open the duplicate Contact page — its backlinks / relation will show all linked Meetings and Action Items.

### Step 3: Flag or Delete the Duplicate Contact

Once all Meetings and Action Items have been re-wired:

- Set the duplicate's **Record Status** to **Delete** (red).
- Add a Notes flag: "MERGED → [Canonical Contact Name]. Ready for HARD DELETE per merge workflow."
- Adam periodically sweeps the Delete view and trashes flagged records.

---

# Domain Field Reference

Both merge workflows rely on correct domain data:

- **Companies → Domains** (primary): comma-separated, no spaces. Used for agent matching (email domain → company lookup).
- **Companies → Additional Domains**: merged/subsidiary/alternate domains. Comma-separated, no spaces, domains only — no full email addresses.
- **Contacts → Email / Secondary Email / Tertiary Email**: All three fields are checked during dedup.

When merging a company, add the merged domain to **Additional Domains** on the canonical company (not Domains) to preserve the distinction between primary and acquired domains. When merging a contact, add the duplicate's email to **Secondary Email** or **Tertiary Email** on the canonical contact.

---

# Quick Checklist

## Company Merge
- [ ] Domain added to real Company's Domains or Additional Domains property
- [ ] All Contacts re-wired from placeholder → real Company
- [ ] All Action Items re-wired from placeholder → real Company
- [ ] Placeholder Company set to Record Status = Delete (or hard-deleted)
- [ ] Spot-check: open real Company, verify Contacts and Action Items look correct

## Contact Merge
- [ ] Duplicate's email added to canonical Contact's Secondary/Tertiary Email
- [ ] All Meetings re-wired from duplicate → canonical Contact
- [ ] All Action Items re-wired from duplicate → canonical Contact
- [ ] Duplicate Contact set to Record Status = Delete with Notes flag
- [ ] Spot-check: open canonical Contact, verify Meetings and Action Items look correct
