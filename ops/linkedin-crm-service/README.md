# LinkedIn CRM Service

Private Node service for a compliant LinkedIn OAuth to Notion CRM intake flow.

This code lives in the repo for convenience, but it should be deployed as a separate private service. Do not serve it from GitHub Pages and do not commit real secrets.

See [../linkedin-ingestion-enrichment.md](../linkedin-ingestion-enrichment.md) for the repo-level architecture that separates CSV import, CRM intake, and enrichment.

## What It Does

- Starts a 3-legged LinkedIn OAuth flow
- Exchanges the auth code server-side and stores tokens only in server memory
- Calls LinkedIn `userinfo` as the v1 proof-of-life API
- Accepts pasted LinkedIn profile or company URLs and writes them to a Notion intake queue
- Approves intake items into your existing `Companies` and `Contacts` CRM with dedupe and relation linking
- Rejects partner-only enrichment attempts in self-serve mode
- Audits config gaps and Notion schema gaps so the remaining setup questions are explicit

## Role In The Overall System

This service is the LinkedIn auth and CRM intake layer.

It should own:

- LinkedIn OAuth
- Self-serve LinkedIn proof-of-life calls
- Intake queue creation
- Approval into the CRM

It should not own:

- Bulk CSV import
- Arbitrary people enrichment by email or name
- Capability guessing for partner-only APIs
- Browser automation or scraping

If richer LinkedIn enrichment is added later, it should live in a separate provider layer with explicit capability checks rather than being folded into this intake service.

## Endpoints

- `GET /`
- `GET /setup/questions`
- `GET /setup/schema-audit`
- `GET /auth/linkedin/start`
- `GET /auth/linkedin/callback`
- `GET /integrations/linkedin/userinfo`
- `POST /crm/linkedin-intake`
- `POST /crm/linkedin-intake/:id/approve`

## Setup

1. Copy `.env.example` to `.env`.
2. Copy `config/crm.config.example.json` to `config/crm.config.json`.
3. Fill in your LinkedIn app credentials, Notion API key, and exact Notion data source or database IDs.
4. Map each logical CRM field in `crm.config.json` to the exact Notion property name you already use.
5. Run `npm run dev` from this folder.
6. Visit `GET /setup/questions` and `GET /setup/schema-audit` until both come back clean enough to proceed.

## AskUserQuestions

Use these answers to finish `config/crm.config.json`:

- What is the exact Notion data source or database ID for `intake`, `companies`, and `contacts`?
- What are the exact property names for each mapped field in the example config?
- Which private host will own the OAuth callback URL?
- Do you want approval to update existing CRM notes and status fields, or only structural LinkedIn fields and relations?
- Should operator identity be written into Notion for audit, or used only for session validation?

## Request Shapes

### `POST /crm/linkedin-intake`

```json
{
  "entityType": "contact",
  "linkedinUrl": "https://www.linkedin.com/in/example-person/",
  "contactName": "Example Person",
  "companyName": "Example Company",
  "companyLinkedinUrl": "https://www.linkedin.com/company/example-company/",
  "email": "person@example.com",
  "website": "https://example.com",
  "notes": "Met at NECANN. Good wholesale fit.",
  "ownerId": "notion-user-id-if-owner-property-is-people",
  "notionImportedByUserId": "notion-user-id-if-imported-by-is-people",
  "status": "New"
}
```

### `POST /crm/linkedin-intake/:id/approve`

```json
{
  "approvalNotes": "Approved after quick manual review.",
  "allowMetadataUpdates": false
}
```

`allowMetadataUpdates` defaults to `false`, which means approval will safely upsert structural fields like LinkedIn URL, source, import status, timestamps, and relations without overwriting existing CRM notes or status values.

## Verification

- `npm run test`
- `GET /setup/questions`
- `GET /setup/schema-audit`

## Notes

- v1 intentionally does not scrape LinkedIn and does not attempt partner-only enrichment APIs.
- If you later gain LinkedIn partner access, add that as a separate branch instead of weakening these guardrails.
