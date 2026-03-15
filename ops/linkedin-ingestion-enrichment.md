# LinkedIn Ingestion and Enrichment Architecture

## Purpose

This note aligns the three LinkedIn-related workstreams in this repo:

- `ops/linkedin-csv-import/` for bulk import from LinkedIn `Connections.csv`
- `ops/linkedin-crm-service/` for LinkedIn OAuth, proof-of-life, and Notion CRM intake
- `ops/notion-workspace/docs/contact-company-review.md` for contact and company enrichment workflow

The goal is to keep ingestion, approval, and enrichment on one consistent model so future automation does not assume LinkedIn capabilities that are not actually available.

## Canonical Roles

### 1. CSV Importer

The CSV importer is a standalone local CLI.

It is responsible for:

- Parsing LinkedIn `Connections.csv`
- Generating deterministic import keys
- Writing directly to one Notion database
- Handling dedup, retries, reporting, and resume safety

It is not responsible for:

- LinkedIn OAuth
- Live LinkedIn API enrichment
- CRM intake or approval workflows

### 2. CRM Service

The CRM service is a separate private Node service.

It is responsible for:

- LinkedIn OAuth
- LinkedIn self-serve proof-of-life calls such as `userinfo`
- Intake queue creation for pasted LinkedIn URLs
- Approval into the CRM with safe upsert rules

It is not responsible for:

- Bulk CSV import
- Arbitrary people search or email-to-profile enrichment
- Hidden partner-only enrichment behavior

### 3. Enrichment Provider Layer

Enrichment should live in a separate provider layer, even if the first implementation is simple.

This layer is responsible for:

- Looking up additional contact or company data from approved sources
- Reporting capability, provenance, and confidence
- Falling back cleanly when a provider is unavailable or restricted

This layer should be provider-agnostic. It must not hardcode the assumption that LinkedIn can search arbitrary people by email or name.

### 4. Notion Workflow

The Notion workflow should call an enrichment provider, not "the LinkedIn API" directly.

That keeps the operational workflow stable even if:

- LinkedIn access is limited to OAuth and self-profile endpoints
- A different provider becomes the primary enrichment source
- LinkedIn partner access is approved later

## Capability Matrix

Current expected baseline:

| Capability | Status | Notes |
|---|---|---|
| Import from LinkedIn `Connections.csv` | Available now | Covered by the standalone CSV importer plan |
| LinkedIn OAuth sign-in | Available now | Implemented in `ops/linkedin-crm-service/` |
| LinkedIn `userinfo` / proof-of-life | Available now | Implemented in `ops/linkedin-crm-service/` |
| Paste LinkedIn URLs into intake + approve into CRM | Available now | Implemented in `ops/linkedin-crm-service/` |
| Arbitrary contact lookup by email | Not assumed | Requires confirmed product access; do not plan around it by default |
| Arbitrary people search by name + company | Not assumed | Requires confirmed product access; do not plan around it by default |
| Browser scraping or automation | Rejected | Out of scope for current architecture |
| Manual or web-search enrichment fallback | Available now | Remains the default fallback path |

## Design Rules

1. Do not assume access you have not confirmed.
2. Keep CSV import, CRM intake, and enrichment as separate responsibilities.
3. Treat LinkedIn self-serve developer access as lower-capability by default.
4. Add new LinkedIn enrichment only behind explicit capability detection.
5. If LinkedIn partner access is later approved, add it as a new provider implementation instead of weakening existing guardrails.

## Recommended Provider Contract

An enrichment provider should expose a small stable interface such as:

- `getCapabilities()`
- `lookupContact(input)`
- `lookupCompany(input)`

Each result should include:

- `provider`
- `matched`
- `confidence`
- `provenance`
- `fields`
- `warnings`

This contract lets the Notion workflow say "try enrichment" without caring whether the source is LinkedIn, web search, or something else.

## Immediate Cleanup Tasks

1. Keep `ops/linkedin-csv-import.md` focused on CSV import only.
2. Keep `ops/linkedin-crm-service/README.md` explicit that the service is auth/intake, not bulk enrichment.
3. Update `ops/notion-workspace/docs/contact-company-review.md` so Step A3 is provider-based rather than "LinkedIn API by email".
4. Confirm the actual LinkedIn product access for the current developer app before planning any LinkedIn-backed provider implementation.
