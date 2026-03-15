# LinkedIn CSV Importer Plan v4

## Status

Implementation-ready. This is a clean rewrite consolidating all decisions from the v3 series (3a–3e) into a single, self-contained specification, with final fixes for strict-mode coverage, exit-code precedence, and Status property type pinning. No delta markers — every rule is stated directly.

- No importer code has been added yet.
- No production behavior changes are being made by this document.
- See [linkedin-ingestion-enrichment.md](./linkedin-ingestion-enrichment.md) for how this importer fits with the CRM service and enrichment workflow.

## Final Recommendation

1. Build a standalone CLI under `ops/linkedin-csv-import/`
2. Reuse pure helpers by importing directly from `ops/linkedin-crm-service/src/`
3. Do not embed CSV-import behavior into the CRM HTTP service or intake workflow
4. v1 targets classic Notion databases only

## Architecture Decision

### Chosen

- Standalone CSV CLI with direct imports from CRM service source
- Database-only target for v1

### Rejected

- Standalone tool that rebuilds Notion/config/util logic from scratch
- Importer embedded directly inside `ops/linkedin-crm-service/`
- Shared helper extraction into `ops/shared/` — deferred until a third consumer exists
- Data source target support in v1
- LinkedIn connections API path
- Browser automation or scraping

## Boundary Rules

The importer should:

- Run locally as a CLI
- Target one classic Notion database per run
- Own only CSV-import behavior
- Validate schema against the live Notion database at startup before any writes
- Produce both console output and a machine-readable report

The importer should not:

- Modify the existing CRM intake/approval HTTP endpoints
- Depend on LinkedIn OAuth configuration
- Depend on a live enrichment provider or LinkedIn API lookup to complete imports
- Require `crm.js` to accept CSV-specific input shapes
- Deduplicate by title alone
- Scrape LinkedIn or use restricted member-connections APIs
- Claim existing records unless they pass the adoption criteria
- Update existing records via fallback key — no-email matches are create-only

## Reuse Strategy

Reuse by direct import, not by extraction.

The importer imports directly from the CRM service source files:

- `ops/linkedin-crm-service/src/notion.js`
  - `NotionClient`
  - `buildPropertyPatch`
  - `buildEqualsFilter`
  - `readPropertyValue`
  - `propertyOptionNames`
- `ops/linkedin-crm-service/src/utils.js`
  - `safeTrim`
  - `normalizeEmail`
  - `nowIso`
  - `mergeText`
  - `splitRichText`
  - `uniqueIds`

The importer wraps `NotionClient` with a retry-aware subclass (`notionRetryClient.js`). It does not import `ServiceError` or other CRM-specific error types — it catches by HTTP status code only, keeping the coupling surface to pure helpers.

No changes to `ops/linkedin-crm-service/` are needed for v1.

## Planned Folder Layout

```text
ops/
|- linkedin-csv-import-plan4.md
|- linkedin-crm-service/
|  |- ...  (unchanged)
|- linkedin-csv-import/
   |- package.json
   |- README.md
   |- .env.example
   |- config.example.json
   |- src/
   |  |- cli.js
   |  |- importer.js
   |  |- linkedinCsv.js
   |  |- mapping.js
   |  |- notionRetryClient.js
   |  |- report.js
   |- test/
      |- fixtures/
      |- importer.test.js
      |- linkedinCsv.test.js
      |- mapping.test.js
      |- report.test.js
```

## Scope

### In Scope

- A local CLI importer in `ops/linkedin-csv-import/`
- One target classic Notion database per run
- CSV parsing for LinkedIn `Connections.csv`
- Startup schema validation against the live Notion database
- Startup duplicate detection in the target database
- Deterministic import-key generation
- Idempotent create-or-update behavior for email-keyed rows; create-only behavior for no-email rows (reported as `collision` on reruns, not `unchanged`)
- Adoption policy for email-matched records (with source-match guard)
- Create-only policy for fallback-key-matched no-email rows
- Dry-run support
- Ambiguous-row skipping
- Rate limiting, retries, and summary reporting
- JSON audit output
- Report-based retry for retriable rows only (enforcing CSV hash, config hash, and API version)
- Indeterminate create recovery
- Defined exit code policy with optional strict mode

### Out Of Scope

- Hosted deployment
- Changes to the CRM service workflow
- LinkedIn scraping
- Browser automation
- Partner-only LinkedIn APIs
- Multi-database CRM orchestration
- Automatic enrichment of missing emails
- `ops/shared/` extraction (deferred)
- Rollback/undo support
- Data source target support (deferred)
- Updating existing records via no-email fallback key (deferred — v1 is create-only for fallback matches)

## Planned CLI Interface

```text
node src/cli.js --csv <path> --config <path> [--target-id <id>] [--dry-run] [--limit <n>] [--include-no-email] [--start-row <n>] [--retry-from <path>] [--report <path>] [--pace-ms <n>] [--force-large-target] [--force-retry-mismatch] [--strict]
```

### Planned Flags

- `--csv <path>`
  - Path to LinkedIn `Connections.csv`
- `--config <path>`
  - Importer config with property mappings and defaults
- `--target-id <id>`
  - Optional override for the configured Notion database ID
- `--dry-run`
  - Parse, validate, compare, and report without writing
- `--limit <n>`
  - Process only the first `n` rows for testing
- `--include-no-email`
  - Opt in to importing rows without an email address (off by default). The operator is accepting the residual cross-run fallback-key collision risk. No-email matches are create-only — existing records are never updated via fallback key. Repeated no-email reruns will report `collision` for previously created records.
- `--start-row <n>`
  - Start processing at CSV row `n` — debugging convenience only, not the primary resume mechanism
- `--retry-from <path>`
  - Read a previous JSON report and retry only retriable rows, matched by import key
  - Fails if the current CSV hash differs from the report's `csvSha256` unless `--force-retry-mismatch` is provided
  - Fails if the current config hash differs from the report's `configHash` unless `--force-retry-mismatch` is provided
  - Fails if the effective Notion API version differs from the report's `notionApiVersion` unless `--force-retry-mismatch` is provided
- `--report <path>`
  - Write a JSON report file; default filename includes `runId` (UUID) to avoid collisions
- `--pace-ms <n>`
  - Override the default pacing interval for all Notion API calls (queries and writes)
- `--force-large-target`
  - Override the 5,000-page bulk-load guardrail. The operator is accepting the memory and time cost of a large bulk load.
- `--force-retry-mismatch`
  - Override CSV hash, config hash, and/or API version mismatch checks in `--retry-from`. The operator is accepting that input data, mapping, or API behavior may have changed since the original run.
- `--strict`
  - Exit non-zero if any rows result in `ambiguous`, `collision`, `conflict`, or `rejected` outcomes. Without this flag, these outcomes are informational and the process exits 0. Useful for automation where blocked imports should be surfaced as failures. Also upgrades preexisting-duplicate warnings to exit 2.

## Planned Config Shape

```json
{
  "notion": {
    "targetId": "00000000-0000-0000-0000-000000000000"
  },
  "properties": {
    "title": "Name",
    "importKey": "LinkedIn Import Key",
    "firstName": "First Name",
    "lastName": "Last Name",
    "email": "Email",
    "company": "Company",
    "position": "Position",
    "connectedOn": "Connected On",
    "source": "Source",
    "status": "Status",
    "lastSyncedAt": "Last Synced At"
  },
  "defaults": {
    "source": "LinkedIn CSV",
    "needsEmailStatus": "Needs Email"
  },
  "import": {
    "paceMs": 400,
    "maxRetryAttempts": 4,
    "baseRetryDelayMs": 500,
    "notionApiVersion": "2022-06-28"
  },
  "mergeStrategy": {
    "title": "always",
    "importKey": "always",
    "firstName": "write-if-blank",
    "lastName": "write-if-blank",
    "email": "write-if-blank",
    "company": "write-if-blank",
    "position": "write-if-blank",
    "connectedOn": "always",
    "source": "always",
    "lastSyncedAt": "always",
    "status": "write-if-blank"
  }
}
```

The `NOTION_VERSION` environment variable can override `import.notionApiVersion`, but the effective version (whichever wins) is what gets sent as the `Notion-Version` header, recorded in the report, and validated during `--retry-from`. There is no silent divergence between the reported version and the version actually used.

Environment variables:

- `NOTION_API_KEY`
- `NOTION_VERSION` optional override for `import.notionApiVersion` — if set, this becomes the effective version for the run

### Blank-Value Rule

If a CSV cell is empty or whitespace-only, the importer treats it as absent data. It never writes a blank to Notion, regardless of merge mode. This means `always` mode only overwrites when the CSV actually provides a value.

## Planned Notion Shape

Default target properties:

- `Name` as title
- `LinkedIn Import Key`
- `First Name`
- `Last Name`
- `Email`
- `Company`
- `Position`
- `Connected On`
- `Source` — must be a `select` property (see Source Property Type below)
- `Status` — must be a `select` or `status` property (see Status Property Type below)
- `Last Synced At`

Recommended operational rule:

- `LinkedIn Import Key` should be treated as required for importer-owned records

### Source Property Type

The `Source` property must be a Notion `select` property. This is a hard requirement because:

1. The adoption policy compares the existing page's `Source` value against the configured `defaults.source` — this comparison must be exact and unambiguous
2. `select` properties have enumerated options that can be validated at startup
3. `rich_text` would require fuzzy matching (trimming, case sensitivity) and cannot be validated against a known option set

If the target database uses a different type for `Source` (e.g., `rich_text`, `multi_select`), startup validation will fail with a message directing the operator to either change the Notion property type or update the config to point to a `select` property.

### Status Property Type

The `Status` property must be a Notion `select` or `status` property. This is a hard requirement because:

1. The importer writes `defaults.needsEmailStatus` as an option value — this only works for option-based property types
2. Startup validation confirms the configured value exists as an option in the property
3. `rich_text` cannot be validated against a known option set and would allow unconstrained values

If the target database uses a different type for `Status` (e.g., `rich_text`), startup validation will fail with a message directing the operator to either change the Notion property type or update the config.

## Field Ownership Policy

The importer uses a configurable merge strategy per field.

Three merge modes:

- `always` — overwrite every run (for identity and sync-tracking fields)
- `write-if-blank` — only set if the Notion property is currently empty (safe default for most fields)
- `skip` — never write this field (for manually curated fields)

Default assignments:

| Field | Merge Mode | Rationale |
|-------|-----------|-----------|
| `Name` (title) | `always` | Identity field, must stay in sync |
| `LinkedIn Import Key` | `always` | Dedup primitive, must always be stamped |
| `First Name` | `write-if-blank` | Operator may correct manually |
| `Last Name` | `write-if-blank` | Operator may correct manually |
| `Email` | `write-if-blank` | May be enriched manually |
| `Company` | `write-if-blank` | Often corrected or updated manually |
| `Position` | `write-if-blank` | Often corrected or updated manually |
| `Connected On` | `always` | Immutable fact from LinkedIn |
| `Source` | `always` | Provenance stamp |
| `Last Synced At` | `always` | Sync tracking |
| `Status` | `write-if-blank` | Only sets the configured `defaults.needsEmailStatus` when blank |

Fields not listed in `mergeStrategy` are never written.

## Deduplication And Idempotency

### Core Rule

Use a stored `LinkedIn Import Key` as the dedup primitive.

`needs-email` is useful for workflow, but it must not be the identity mechanism.

### Idempotency Semantics By Key Type

- **Email-keyed rows** are fully idempotent: re-importing the same CSV row produces `unchanged` if nothing differs, or `updated` if merge strategy allows a write. This is classic create-or-update behavior.
- **No-email (fallback-keyed) rows** are create-only: the first import creates the record; all subsequent imports of a row with the same fallback key produce `collision`, even if the row content is identical. This is intentional — the fallback key is not strong enough to guarantee identity, so the importer refuses to update through it. Operators should expect `collision` counts on no-email reruns; this is safe behavior, not an error.

### Import Key Rules

For rows with email:

- `importKey = li_csv:email:<normalized-email>`

For rows without email:

- `importKey = li_csv:row:v1:<hash(normalized-first-name|normalized-last-name|connected-on-iso)>`

### Normalization Spec

All normalization rules apply both to CSV input values when generating import keys and to existing Notion values when building the dedup index.

- **Email normalization:** apply `normalizeEmail` (lowercase + trim) to both CSV email values and existing Notion email property values before indexing. This ensures that `User@Example.com` in Notion matches `user@example.com` from the CSV.
- **Unicode:** NFC normalization
- **Case:** `.toLowerCase()` after NFC
- **Whitespace:** collapse all internal whitespace to single space, then trim
- **`Connected On` parsing:** expect `DD Mon YYYY` format (e.g., `15 Mar 2024`), parse to ISO `YYYY-MM-DD` using explicit English month map (not locale-dependent `Date.parse`). If the format doesn't match, reject the row with reason `unparseable-date`.
- **Hash:** SHA-256 hex of the pipe-delimited normalized string
- **Import key normalization for index:** when reading existing `LinkedIn Import Key` values from Notion, trim whitespace but do not otherwise transform — the key format is controlled by the importer and should already be canonical.

If the importer cannot build a deterministic fallback key (e.g., first name, last name, or connected-on date is blank/missing), it should reject the row with reason `missing-key-fields`.

Before any writes, the importer should detect duplicate generated import keys within the input file.

- If multiple no-email rows in the same CSV generate the same fallback key, mark them all as ambiguous and skip them
- Do not silently pick one row as the canonical record

### Matching Order

1. Match by exact `LinkedIn Import Key` (lookup in the import-key index)
2. If the row has an email, no import-key match exists, and exactly one existing page matches by normalized email (lookup in the email index): apply the adoption policy
3. If more than one match is found for the same key path (the index entry has multiple pages), skip as `ambiguous`
4. Never match by title or display name alone

### Adoption Policy For Email Matches

When a CSV row has an email, no existing page matches by import key, but exactly one existing page matches by normalized email:

- The page is **adoptable** only if both conditions are met:
  1. Its `LinkedIn Import Key` is blank
  2. Its `Source` value exactly matches the configured `defaults.source` — blank `Source` is **not** sufficient for adoption
- If adoptable: stamp the import key, apply the merge strategy as for any update
- If the `LinkedIn Import Key` is non-blank and differs from the generated one: skip as `conflict`
- If the `Source` is blank or does not match the configured import source: skip as `conflict`
- If the `LinkedIn Import Key` is non-blank but matches: this case should have been caught by step 1 (import-key match); treat as a logic error and skip with a warning

**Adoption scope and limitations:** this rule proves source-label match, not actual importer provenance. A page that was manually created and tagged with `Source` matching `defaults.source` would still be adoptable. The importer cannot distinguish "created by a previous import run" from "manually tagged with the same source label." In practice, this is acceptable because: (a) the operator controls the source label and can choose a distinctive value, (b) adoption only fires when the import key is blank, and (c) every adoption is logged in the report with `matchedBy: "email-adopt"` for auditability. The README should note this behavior.

### Create-Only Policy For Fallback-Key Matches

When a no-email row (with `--include-no-email`) generates a fallback key:

- If no existing page has that import key: **create** the page
- If an existing page already has that import key: **skip** with action `collision` and reason `fallback-key-exists` — do not update it

`collision` is a distinct action (not `unchanged`) so operators can distinguish "same email-keyed record seen again on re-import" from "a row's fallback key matched an existing record and was intentionally not updated."

### Expected Behavior

- Create a page when no exact match exists
- Update the existing page when exactly one safe match exists (applying merge strategy per field), subject to adoption guard — but only for email-keyed matches
- Never update an existing page via fallback key — create-only for no-email rows
- Skip ambiguous rows rather than risking a false merge
- Skip conflict rows where the matched page is not eligible for adoption or update
- Report collision rows where a fallback key matched an existing record (distinct from unchanged)
- Stamp `Source` with the configured `defaults.source` value
- Stamp `Last Synced At` on every successful create or update
- Set the configured `defaults.needsEmailStatus` on the `Status` property only for rows without email when that property is blank

## Dedup Fetch Strategy

For v1, use bulk-load-then-index:

1. At startup, query all pages from the target Notion database
2. Build multi-valued indexes: `normalizedImportKey -> [{ pageId, page }, ...]` and `normalizedEmail -> [{ pageId, page }, ...]`. Each key maps to an array of matching pages, not a single page.
3. Normalize existing Notion values before indexing:
   - **Email:** apply `normalizeEmail` (lowercase + trim) to the existing page's email property value
   - **Import key:** trim whitespace only (the key format is importer-controlled)
4. The index must store the full page object (not just pageId) so the importer can check the existing import key value and source for adoption decisions, and read current field values for `write-if-blank` logic
5. Use the index for O(1) lookups per row during import
6. Guard: if the database contains more than 5,000 pages, fail with a clear message unless `--force-large-target` is provided

### Preexisting Duplicate Detection

After building the index, before processing any CSV rows:

1. Scan the import-key index for any key that maps to more than one page. These are preexisting duplicates in the Notion database — they represent a data quality issue that existed before the import.
2. Scan the email index for any normalized email that maps to more than one page.
3. Log a summary warning listing the duplicate keys/emails and the affected page IDs.
4. During row processing, if a row's lookup returns multiple pages from the index, skip as `ambiguous`.

The importer does not attempt to fix preexisting duplicates. It warns and skips affected rows. The operator should resolve duplicates in Notion manually before re-running.

## No-Email Contact Policy

No-email rows are importable but off by default.

Default behavior:

- No-email rows are skipped unless the operator explicitly opts in with `--include-no-email`

Opted-in behavior (with `--include-no-email`):

- Import the row if a deterministic fallback import key can be built
- Mark the record with the configured `defaults.needsEmailStatus` on the `Status` property (only if the Status field is blank)
- Do not merge into an unrelated existing record based only on title or name similarity
- Create-only: if an existing page already has the same fallback key, skip as `collision` — never update via fallback key
- Skip and report if a no-email row would create an ambiguous collision within the same CSV
- On reruns: opted-in no-email rows that were previously created will always produce `collision` in the report. This is by design — the fallback key is not strong enough to safely update through, so the importer treats every rerun encounter as a collision rather than a quiet no-op. No-email rerun reports will show collision counts proportional to the number of previously imported no-email contacts. This is informational, not an error (exit 0 without `--strict`).

Known limitation:

- Two distinct no-email contacts with the same normalized first name, last name, and connected-on date will collide on the v1 fallback key
- In a single CSV run, those rows should be detected and skipped as ambiguous
- Across separate runs, the first import wins — the second distinct person's row is reported as a `collision`, not merged into the wrong record

## Startup Schema Validation

Before processing any rows, the importer must:

1. Fetch the target database schema from the Notion API (`GET /v1/databases/{id}`)
2. Confirm every property name in the config `properties` map exists in the database
3. Confirm property types are compatible (e.g., `email` config key maps to an `email`-type property, not `rich_text`)
4. Confirm that `LinkedIn Import Key` is a filterable type (`rich_text` or `title`)
5. Confirm that `Source` is a `select` property — fail if it is any other type
6. Confirm that `Status` is a `select` or `status` property — fail if it is any other type
7. Confirm that configured select/status default values (`defaults.source` and `defaults.needsEmailStatus`) exist as options in their respective properties
8. Fail fast with a clear, actionable error message listing every mismatch

This prevents silent data loss from misconfigured property names (Notion ignores unknown properties without error).

## Rate Limiting And Retries

Use both proactive pacing and centralized retry handling.

### Proactive Pacing

- Default to `400ms` between all Notion API calls (queries and writes)
- Allow override via `--pace-ms`
- Pace applies to all API calls, not just writes — the Notion rate limit (~3 req/sec) counts all requests

### Centralized Notion Backoff

Add retry logic in `src/notionRetryClient.js` — a thin wrapper around `NotionClient` that:

- Resolves effective Notion API version at construction (config value, then `NOTION_VERSION` env override) and sends it as `Notion-Version` header on every request
- Catches by HTTP status code (not CRM-specific error types) to minimize coupling
- Retries `429` responses using `Retry-After` header when present, else exponential backoff
- Retries transient `5xx` failures with exponential backoff and jitter
- Caps retry attempts at `maxRetryAttempts` (default 4) with a clear error once exhausted
- Surfaces structured error details to the importer for reporting

### Indeterminate Create Recovery

When a `POST /v1/pages` (create) fails with a network error, timeout, or ambiguous status (e.g., the request was sent but no response was received):

1. The importer must not blindly retry the create
2. Instead, re-query the database by the generated import key
3. If a page now exists with that import key, treat it as a successful create (the original request likely succeeded server-side)
4. If no page exists, retry the create
5. Log the recovery action in the report row as `action: "created"` with `note: "recovered-after-indeterminate-failure"`

## Reporting And Audit Trail

Every run should produce:

- A concise console summary
- A JSON report file

Default report filename: `report-<runId>.json` under a local `reports/` folder, where `runId` is a UUID.

### Console Summary

The console summary should print:

- Run metadata (target ID, dry-run status, effective API version)
- Totals for each outcome
- Preexisting duplicate warnings (if any)
- A clear statement when `--strict` would have caused a non-zero exit (if running without `--strict`)

### JSON Report Schema

- `runId`
- `startedAt`
- `finishedAt`
- `csvPath`
- `csvSha256` — hash of the input CSV
- `configHash` — hash of the config file
- `notionApiVersion` — the effective Notion API version used for this run
- `targetId`
- `dryRun`
- `includeNoEmail` — whether `--include-no-email` was set
- `strict` — whether `--strict` was set
- `preexistingDuplicates` — object with `importKeys` and `emails` arrays listing any duplicate keys/emails found during index building, with affected page IDs
- `totals`
  - `processed`
  - `created`
  - `updated`
  - `unchanged`
  - `skipped`
  - `rejected`
  - `ambiguous`
  - `collisions`
  - `conflicts`
  - `errors`
- `rows`
  - `rowNumber`
  - `importKey`
  - `action` — one of: `created`, `updated`, `unchanged`, `skipped`, `rejected`, `ambiguous`, `collision`, `conflict`, `error`
  - `matchedBy` — one of: `import-key`, `email-adopt`, `email-conflict`, `fallback-key-collision`, `none`
  - `pageId` when available
  - `reason` or `error` when skipped, rejected, collision, conflict, or failed
  - `retriable` — boolean; `true` for transient errors (network, 429, 5xx); `false` for permanent outcomes (rejected, ambiguous, collision, conflict). `--retry-from` only retries rows where `retriable` is `true`.
  - `note` when additional context is useful (e.g., `recovered-after-indeterminate-failure`)

### Resume via `--retry-from`

When `--retry-from <report-path>` is provided:

1. Read the previous report's `rows` array
2. Filter to rows where `retriable` is `true` — this excludes ambiguous matches, collisions, conflicts, and permanent parse failures
3. Match against the current CSV by `importKey`, not by `rowNumber`
4. Process only the matched rows
5. If the current CSV's SHA-256 differs from the report's `csvSha256`, **fail** unless `--force-retry-mismatch` is provided
6. If the current config's hash differs from the report's `configHash`, **fail** unless `--force-retry-mismatch` is provided
7. If the current effective Notion API version differs from the report's `notionApiVersion`, **fail** unless `--force-retry-mismatch` is provided
8. If `--force-retry-mismatch` is provided with mismatches, log a warning specifying which value(s) differ and proceed

`--start-row` remains available as a debugging convenience but is not the recommended resume path.

## Exit Code Policy

The CLI exits with a code that reflects the worst outcome of the run.

### Exit Codes

- `0` — success: all processed rows resulted in `created`, `updated`, `unchanged`, or `skipped` (without `--strict`, also allows `rejected`, `collision`, `ambiguous`, `conflict`)
- `1` — row-level failure: at least one row resulted in `error` (transient failure that exhausted retries), OR `--strict` was set and at least one row resulted in `rejected`, `ambiguous`, `collision`, or `conflict`
- `2` — validation failure: startup schema validation failed, CSV parsing failed on required columns, `--retry-from` mismatch without `--force-retry-mismatch`, or preexisting duplicates detected with `--strict`
- `3` — fatal: unhandled exception, missing config/CSV file, invalid CLI arguments

### Exit Code Precedence

When multiple exit-worthy conditions occur in the same run, the highest code wins:

`3 > 2 > 1 > 0`

A fatal exception (3) takes precedence over a validation failure (2), which takes precedence over row-level errors (1). This means:
- If the process encounters a fatal error after processing some rows with errors, exit 3
- If startup validation fails, exit 2 regardless of any row outcomes
- If both `error` rows and `--strict`-triggered outcomes exist, exit 1 (both contribute to the same code)

### Row Outcome Classification

`skipped` vs `rejected`: rows that the importer intentionally does not process fall into two categories:

- `skipped` — operator-configured, expected non-processing. Examples: no-email rows without `--include-no-email`, rows before `--start-row`, rows beyond `--limit`. These are never interesting to `--strict` because the operator explicitly configured this behavior.
- `rejected` — the row was processed but the importer could not build a valid import from it. Examples: `unparseable-date`, `missing-key-fields` (first name, last name, or connected-on blank/missing). These represent data quality issues in the CSV that prevent the row from being imported. They are permanent (non-retriable) and should be surfaced by `--strict`.

| Outcome | Default Exit Impact | With `--strict` |
|---------|-------------------|----------------|
| `created` | None (exit 0) | None (exit 0) |
| `updated` | None (exit 0) | None (exit 0) |
| `unchanged` | None (exit 0) | None (exit 0) |
| `skipped` | None (exit 0) | None (exit 0) |
| `rejected` | None (exit 0) | Exit 1 |
| `collision` | None (exit 0) | Exit 1 |
| `ambiguous` | None (exit 0) | Exit 1 |
| `conflict` | None (exit 0) | Exit 1 |
| `error` | Exit 1 | Exit 1 |
| Preexisting duplicates | Warning only | Exit 2 |

Without `--strict`: the importer is lenient. Safety decisions (`ambiguous`, `collision`, `conflict`) and data quality rejections (`rejected`) are informational. The operator reads the report to understand what was blocked. Exit 0 can include materially blocked imports — this is by design for a manual CLI tool where the operator reviews the report after every run.

With `--strict`: the importer is conservative. Any blocked import, rejected row, or data quality issue causes a non-zero exit, making it suitable for automation where blocked imports should fail the pipeline.

The report always contains the full breakdown of all outcomes regardless of exit code or strict mode.

## Concurrency Safety

The importer does not support concurrent runs against the same Notion database. Two simultaneous runs can both see "no match" for the same import key and create duplicate records.

For v1, document this limitation in the README: "Do not run multiple instances against the same target simultaneously."

## Planned Modules

### `src/linkedinCsv.js`

- Strip BOM safely
- Parse quoted CSV correctly
- Expect and validate specific LinkedIn column names: `First Name`, `Last Name`, `Email Address`, `Company`, `Position`, `Connected On`
- Fail loudly on missing required columns; warn on unexpected columns
- Convert `Connected On` values into ISO dates using explicit `DD Mon YYYY` parser with English month map (not `Date.parse`)
- Return normalized row objects with source row numbers

### `src/mapping.js`

- Build Notion property payloads from normalized CSV rows
- Generate import keys using pinned normalization rules (NFC, lowercase, whitespace collapse, SHA-256)
- Apply per-field merge strategy (`always`, `write-if-blank`, `skip`)
- Never produce a write for a blank CSV value regardless of merge mode

### `src/notionRetryClient.js`

Thin wrapper around `NotionClient`:

- Resolves effective Notion API version at construction (config value, then env override) and sends it as `Notion-Version` header on every request
- Catches by HTTP status code, not CRM error types
- Adds retry with backoff for 429 and transient 5xx
- Adds indeterminate-create recovery (re-query before retry)
- Pacing between all API calls

### `src/importer.js`

- Validate config and schema against live Notion database at startup
- Validate that `Source` is a `select` property and that `defaults.source` is a valid option
- Validate that `Status` is a `select` or `status` property and that `defaults.needsEmailStatus` is a valid option
- Bulk-load existing records and build multi-valued in-memory index (with 5,000-page guardrail)
- Normalize existing email values with `normalizeEmail` before indexing
- Detect and warn about preexisting duplicates (import keys and emails) after index build
- Apply adoption policy for email matches (blank import key + matching source = adoptable; blank source or non-matching source = conflict)
- Apply create-only policy for fallback-key matches (skip as `collision` if page already exists with that key)
- Decide `create`, `update`, `unchanged`, `skipped`, `rejected`, `ambiguous`, `collision`, `conflict`, or `error`
- Record `matchedBy` and `retriable` for each row
- Coordinate pacing and writes via `notionRetryClient`
- Return structured results for the console summary and JSON report

### `src/report.js`

- Build machine-readable report output (including `csvSha256`, `configHash`, `notionApiVersion`, `preexistingDuplicates`)
- Format a concise human summary (including strict-mode advisory when applicable)
- Distinguish `collision` from `unchanged` and `rejected` from `skipped` in summaries
- Support reading a previous report for `--retry-from`
- Filter retriable rows when loading a previous report
- Validate `csvSha256`, `configHash`, and `notionApiVersion` when loading a previous report for retry

### `src/cli.js`

- Parse CLI args (including `--retry-from`, `--force-large-target`, `--force-retry-mismatch`, `--include-no-email`, `--strict`)
- No `--skip-no-email` flag — skipping is the default
- Resolve effective Notion API version (config then env) and pass to importer
- Enforce CSV hash, config hash, and API version match for `--retry-from` unless `--force-retry-mismatch` is provided
- Invoke the importer
- Write the report file with UUID-based filename
- Exit with code per the exit code policy

## Test Plan

The implementation should cover:

- CSV parsing with BOM
- CSV parsing with quoted commas
- CSV parsing with blank rows
- CSV parsing with missing required columns (should fail, exit 2)
- CSV parsing with unexpected extra columns (should warn)
- Blank email handling
- Date conversion from `DD Mon YYYY` format specifically
- Date conversion failure for unexpected formats (should reject row with `unparseable-date`)
- Import-key generation with NFC normalization and whitespace collapse
- Existing Notion email values normalized before indexing (case/whitespace variants match)
- No-email rows skipped by default; imported only with `--include-no-email`
- No-email rows becoming `defaults.needsEmailStatus` records when opted in
- No-email fallback-key collision reported as `collision` action (not `unchanged`)
- No-email rerun produces `collision` for previously created records (informational, exit 0 without `--strict`)
- No-email rerun with `--strict` produces exit 1
- Duplicate fallback-key detection within the same CSV file
- No title-only merges
- Idempotent re-import of the same CSV (email-keyed rows produce `unchanged`)
- Ambiguous collision skipping
- Email-match adoption: blank import key + matching `defaults.source` = adopt
- Email-match adoption: blank import key + blank source = conflict (not adoptable)
- Email-match adoption: blank import key + non-matching source = conflict
- Email-match adoption: non-blank import key = conflict
- Fallback-key: create-only, never update via fallback key
- Indeterminate create recovery: re-query before retry
- Startup schema validation: `Source` must be `select` type
- Startup schema validation: `Status` must be `select` or `status` type
- Startup schema validation against Notion database (missing properties, wrong types, missing select options)
- Startup validation confirms `defaults.source` exists as an option in the `Source` select
- Startup validation confirms `defaults.needsEmailStatus` exists as an option in the `Status` select/status
- Preexisting duplicate detection: duplicate import keys and emails in Notion are warned at startup
- Preexisting duplicates with `--strict` cause exit 2
- Rows matching preexisting duplicates are skipped as `ambiguous`
- Centralized retry handling for `429`
- JSON report generation (including `csvSha256`, `configHash`, `notionApiVersion`, `matchedBy`, `retriable`, `preexistingDuplicates`)
- Report distinguishes `collision` from `unchanged` and `rejected` from `skipped` in totals and row actions
- Rows with unparseable dates or missing key fields are `rejected` (not `skipped`)
- `rejected` rows with `--strict` produce exit 1
- `--retry-from` behavior (filters by `retriable`, matches by import key)
- `--retry-from` fails on CSV hash mismatch; succeeds with `--force-retry-mismatch`
- `--retry-from` fails on config hash mismatch; succeeds with `--force-retry-mismatch`
- `--retry-from` fails on API version mismatch; succeeds with `--force-retry-mismatch`
- `--start-row` behavior for debugging
- Merge strategy: `always` overwrites, `write-if-blank` preserves existing values, `skip` never writes
- Blank CSV values never clear existing Notion values
- Bulk-load guardrail at 5,000 pages; overridable with `--force-large-target`
- Notion API version pinned in config and recorded in report
- `NOTION_VERSION` env override is recorded as the effective version in the report
- Exit code 0 for runs with only success + collision + conflict + ambiguous + rejected outcomes (without `--strict`)
- Exit code 1 for runs with at least one `error` outcome
- Exit code 1 for runs with collision/conflict/ambiguous/rejected outcomes and `--strict`
- Exit code 2 for validation failures
- Exit code 2 for preexisting duplicates with `--strict`
- Exit code 3 for fatal errors (missing files, bad args)
- Exit code precedence: 3 > 2 > 1 > 0 (highest wins when multiple conditions co-occur)

Fixture set should include at minimum:

- A clean CSV with standard LinkedIn column names
- A UTF-8 BOM CSV
- A CSV with quoted commas
- A CSV with duplicate names and no emails
- A CSV with blank rows
- A CSV with missing required columns
- A CSV with an unusual `Connected On` date format
- A CSV with an email matching an existing page with matching `defaults.source` (adoption test)
- A CSV with an email matching a page with blank import key and blank source (adoption rejection test)
- A CSV with an email matching a page with blank import key but non-matching source (adoption rejection test)
- A CSV with blank cells for fields that have existing Notion values (blank-value preservation test)
- A CSV with an email that differs only by case/whitespace from an existing Notion record (normalization test)

## Verification Plan

1. Create or obtain a small redacted sample `Connections.csv`
2. Run `--dry-run` and verify parsing, schema validation, and per-row actions
3. Intentionally misconfigure a property name and verify startup validation catches it (exit 2)
4. Set `Source` to `rich_text` type in Notion and verify startup validation rejects it (exit 2)
5. Set `Status` to `rich_text` type in Notion and verify startup validation rejects it (exit 2)
6. Run against a test Notion database
7. Verify records appear with the correct mapped properties
8. Re-run the same CSV and confirm idempotent behavior (email-keyed rows produce `unchanged`, exit 0)
9. Manually create a page with an email, blank import key, and `Source` matching `defaults.source`; import a CSV row with that email; confirm the page is adopted
10. Manually create a page with an email, blank import key, and blank source; import a CSV row with that email; confirm it is skipped as a conflict
11. Manually create a page with an email, blank import key, and `Source` = `"Manual"`; import a CSV row with that email; confirm it is skipped as a conflict
12. Manually create a page with an email and a non-matching import key; import a CSV row with that email; confirm it is skipped as a conflict
13. Verify no-email rows are skipped by default; re-run with `--include-no-email` and confirm they create
14. Re-run with `--include-no-email` again and confirm existing no-email records are reported as `collision` (exit 0)
15. Re-run step 14 with `--strict` and confirm exit 1
16. Manually create duplicate import keys in Notion; run the importer and confirm the duplicates are warned about at startup and affected rows are skipped as `ambiguous`
17. Re-run step 16 with `--strict` and confirm exit 2
18. Add a record in Notion with email `User@Example.COM`; import a CSV row with `user@example.com`; confirm the email index matches them
19. Confirm the JSON report matches actual Notion outcomes and includes `matchedBy`, `retriable`, `notionApiVersion`, `collision` totals, and `preexistingDuplicates`
20. Simulate a mid-run failure, then use `--retry-from` to retry only retriable rows
21. Modify the CSV file after a run and confirm `--retry-from` fails without `--force-retry-mismatch` (exit 2)
22. Modify the config file after a run and confirm `--retry-from` fails without `--force-retry-mismatch` (exit 2)
23. Set `NOTION_VERSION` env to a different value and confirm `--retry-from` fails without `--force-retry-mismatch` (exit 2)

## Implementation Sequence

1. Implement the standalone importer CLI with direct imports from `ops/linkedin-crm-service/src/`
2. Add fixture-based tests
3. Validate on a test Notion database before any production import
4. Defer `ops/shared/` extraction — revisit only if a third consumer appears

## Review Checklist

Before implementation starts, confirm:

- The importer belongs under `ops/linkedin-csv-import/`
- Direct imports from `ops/linkedin-crm-service/src/` are acceptable for v1 (no `ops/shared/` extraction)
- v1 should not modify the CRM service code
- The target Notion database ID is identified
- The target is a classic Notion database (confirmed)
- The `Source` property in the target database is a `select` type
- The `Status` property in the target database is a `select` or `status` type
- The default property set above is acceptable, or exact custom mappings will be supplied
- The default `write-if-blank` merge strategy is acceptable for owned fields
- The email-match adoption policy (blank import key + matching `defaults.source` = adoptable; this proves source-label match, not provenance — a manually tagged page with the same source is still adoptable) is acceptable
- No-email rows being off by default is acceptable
- No-email fallback-key matches being create-only is acceptable (reruns produce `collision`, not `unchanged`)
- The importer should use stored import keys and never title-match by itself
- The JSON report format is sufficient for audit and reruns
- Notion API version `2022-06-28` is acceptable as the pinned default
- The exit code policy (0/1/2/3, highest wins) is acceptable — collisions, conflicts, rejections, and ambiguous outcomes only cause non-zero exit with `--strict`
- Existing Notion email values will be normalized before indexing
- The README must document the adoption limitation (source-label match, not provenance proof) prominently

## Inputs Needed Later

Implementation should wait until the reviewer provides:

- Notion API key
- Target Notion database ID
- Confirmation that `Source` is a `select` property in the target database
- Confirmation that `Status` is a `select` or `status` property in the target database
- Exact property names if they differ from the defaults
- Confirmation of merge strategy defaults or custom overrides
- Optional redacted sample `Connections.csv`

## Known Limitations (v1)

- No rollback/undo — if a mapping is wrong, records must be manually fixed or deleted
- No concurrent run safety — single operator only
- No-email fallback key collisions across runs for same-name contacts with identical connection dates (mitigated: no-email is opt-in and create-only, so collisions result in skips not overwrites)
- Bulk-load is memory-bound — guardrail at 5,000 pages (overridable with `--force-large-target`)
- No automatic enrichment of missing emails
- No data source target support (database-only for v1)
- Direct import coupling to CRM service internals — acceptable for two consumers, revisit if a third appears
- No-email records are never updated by the importer — only created. If a no-email contact's details change on LinkedIn, the Notion record must be updated manually until a stronger identity signal is available.
- Adoption proves source-label match, not actual importer provenance: a manually created page tagged with the same `defaults.source` label is still adoptable if its import key is blank. Blank-source pages are not adoptable.
- Preexisting duplicates in Notion are warned about but not fixed — the operator must resolve them manually before affected rows can be imported.
