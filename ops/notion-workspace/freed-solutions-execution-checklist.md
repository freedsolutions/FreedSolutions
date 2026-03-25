# Execution Checklist: FreedSolutions Local-First CRM Architecture

**For:** Fresh VSCode context window (Claude Code / Codex)
**Repo:** FreedSolutions (access `ops/` directory)
**Date:** March 22, 2026
**Scope:** Phase 0–2 (local DB + ingestion + sync + agent porting) plus Phase 3 / v2 planning notes for Gmail filter automation

---

## READ FIRST

Before writing any code, read these files in order:

1. `ops/notion-workspace/CLAUDE.md` — repo contract, DB IDs, lifecycle rules
2. `ops/notion-workspace/session-active.md` — current state and priorities
3. `ops/notion-workspace/docs/agent-sops.md` — agent registry, schema, triggers
4. `ops/notion-workspace/docs/post-email.md` — email ingestion logic to port
5. `ops/notion-workspace/docs/post-meeting.md` — meeting pipeline to port
6. `ops/notion-workspace/docs/contact-company.md` — enrichment logic to port
7. This checklist — the execution contract for this session

---

## CONTEXT (From Planning Session)

### What we're building

A **local orchestration layer** (`ops/local_db/`) that sits between raw APIs (Gmail, GCal) and Notion:

```
Gmail API ──→ Local SQLite ──→ Claude Code Agents ──→ Notion (push sync)
GCal API  ──→     (fast reads)     (repo instructions)     (dashboard/review UI)
```

### Why

- Notion MCP round-trips are slow for every CLI read
- Nightly Notion Agent scheduling limits processing cadence (target: 3x/day)
- Agent instruction MDs currently must sync repo → Notion; local agents read repo directly
- Direct Gmail/GCal API gives control over parsing, timing, and enrichment pipeline

### Architecture decisions (already made)

- **Language:** Python for the entire local-db layer
- **Database:** SQLite (WAL mode for concurrency)
- **Sync direction:** Local DB is the write-first target; push to Notion as dashboard layer
- **Notion stays** as the UI/review surface — Adam reviews Drafts daily there
- **Agent instructions** stay in `ops/notion-workspace/docs/` — local agents read from repo, not Notion
- **Lifecycle model:** Draft → Active → Delete (Adam controls Active promotion). Archive is Adam's UI-managed visibility layer — hides records from views while preserving all wiring.

### Credentials available

- **Notion:** Internal integration token exists (created for Claude Code). Verify it has access to all 6 CRM databases.
- **Google Cloud:** Project `eternal-wavelet-460306-n2` under `adam@freedsolutions.com` (Google Workspace domain). May need IAM permissions fix — see Prerequisites below.
- **Gmail accounts in scope:** `adam@freedsolutions.com`, `adamjfreed@gmail.com`
- **GCal calendars in scope:** `Adam - Business` (freedsolutions), `Adam - Personal` (personal, shared to freedsolutions)

### Notion Database IDs (from CLAUDE.md)

| Database | Data Source ID |
|----------|---------------|
| Contacts | `fd06740b-ea9f-401f-9083-ebebfb85653c` |
| Companies | `796deadb-b5f0-4adc-ac06-28e94c90db0e` |
| Action Items | `319adb01-222f-8059-bd33-000b029a2fdd` |
| Meetings | `31fadb01-222f-80c0-acf7-000b401a5756` |
| Agent Config | `322adb01-222f-8114-b1b0-cc8971f1b61a` |
| Emails | `f685a378-5a37-4517-9b0c-d2928be4af4d` |

---

## PREREQUISITES

### P-1: Google Cloud project ✅ COMPLETE

- **Project:** `FreedSolutions CRM` under `freedsolutions.com` org (account: `adam@freedsolutions.com`)
- **APIs enabled:** Gmail API, Google Calendar API
- **OAuth consent screen:** Internal (Workspace-only), app name `FreedSolutions CRM`
- **OAuth scopes:** `gmail.readonly`, `gmail.modify`, `calendar.readonly`
- **Credentials:** Desktop app OAuth client ID created, `credentials.json` downloaded
- **Action for execution session:** Place `credentials.json` at `ops/local_db/credentials/google_oauth_credentials.json` (gitignored). First run of gmail_ingest.py will open a browser for OAuth consent → saves `token.json` for subsequent runs.

### P-2: Notion integration token ✅ VERIFIED

- The existing Claude Code internal integration has read/write access to all 6 CRM databases:
  - ✅ Contacts (`fd06740b-ea9f-401f-9083-ebebfb85653c`)
  - ✅ Companies (`796deadb-b5f0-4adc-ac06-28e94c90db0e`)
  - ✅ Action Items (`319adb01-222f-8059-bd33-000b029a2fdd`)
  - ✅ Meetings (`31fadb01-222f-80c0-acf7-000b401a5756`)
  - ✅ Emails (`f685a378-5a37-4517-9b0c-d2928be4af4d`)
  - ✅ Agent Config (`322adb01-222f-8114-b1b0-cc8971f1b61a` — this is a page, not a database)
- **Action for execution session:** Copy the integration token to `ops/local_db/credentials/notion_token.txt` (gitignored). The token is the same one Claude Code uses — find it at `notion.so/profile/integrations`.
- **Note:** Agent Config is a Notion page (not a database). The local-db layer replaces this with the `agent_config` SQLite table. The Notion page can be kept as a read-only audit log or retired after cutover.

### P-3: Python dependencies ✅ COMPLETE

Installed and verified on Python 3.12.3:

- ✅ `google-api-python-client` — Gmail + GCal API client
- ✅ `google-auth-httplib2` — Auth transport
- ✅ `google-auth-oauthlib` — OAuth2 flow
- ✅ `notion-client` — Notion API SDK
- ✅ `anthropic` (v0.86.0) — Claude API for agent runner
- ✅ `pyyaml` — Config file parsing

**Note for execution session:** These are installed in the system Python. If you prefer a venv, create one and reinstall:
```bash
python3 -m venv ops/local_db/.venv
source ops/local_db/.venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib notion-client anthropic pyyaml
```

---

## PHASE 0: Local DB + Direct API Ingestion

### 0.1: Create directory structure

```
ops/
├── local_db/
│   ├── .gitignore              # credentials/, *.db, token.json
│   ├── config.yaml             # paths, schedule, account mappings
│   ├── schema.sql              # SQLite schema
│   ├── credentials/            # gitignored — OAuth + Notion token
│   ├── ingest/
│   │   ├── __init__.py
│   │   ├── gmail_ingest.py     # Gmail API → SQLite
│   │   └── gcal_ingest.py      # GCal API → SQLite
│   ├── agents/
│   │   ├── __init__.py
│   │   └── runner.py           # Agent execution framework
│   ├── sync/
│   │   ├── __init__.py
│   │   ├── notion_backfill.py  # One-time Notion → SQLite pull
│   │   ├── push_to_notion.py   # SQLite → Notion push
│   │   └── pull_from_notion.py # Notion → SQLite pull (Adam's edits)
│   ├── lib/
│   │   ├── __init__.py
│   │   ├── db.py               # SQLite connection + helpers
│   │   ├── gmail_auth.py       # Google OAuth2 helper
│   │   ├── notion_client.py    # Notion API wrapper
│   │   └── dedup.py            # Shared dedup logic (email, domain)
│   └── tests/
│       ├── test_gmail_ingest.py
│       ├── test_gcal_ingest.py
│       ├── test_sync.py
│       └── test_dedup.py
```

### 0.2: Schema (create `ops/local_db/schema.sql`)

Mirror the 6 Notion DBs. Key design rules:

- Every table gets `id` (local UUID), `notion_page_id`, `created_at`, `updated_at`, `notion_synced_at`
- `emails.thread_id` is UNIQUE (canonical key — same as Notion)
- `meetings.calendar_event_id` is the canonical meeting key
- Junction tables for many-to-many: `email_contacts`, `meeting_contacts`
- `agent_config` table replaces Notion Agent Config for runtime state
- `sync_log` table for audit trail
- Indexes on all email fields, domain fields, thread_id, calendar_event_id

**Additional schema/UX rules (from planning session):**

- **Title normalization:** Both `emails.email_subject` and `meetings.meeting_title` should be stored in normalized form — strip `FW:`, `Fwd:`, `Fw:`, `RE:`, `Re:`, `re:` prefixes (case-insensitive, recursive for chains like `Re: Fwd: ...`) plus leading whitespace. The raw original title is preserved in `raw_gmail_data` / `raw_gcal_data`. This normalization happens at ingestion time in `gmail_ingest.py` and `gcal_ingest.py`.
  ```python
  import re
  def normalize_title(title: str) -> str:
      return re.sub(r'^(?:(?:FW|Fwd|Fw|RE|Re|re)\s*:\s*)+', '', title).strip()
  ```

- **Display timestamps:** Add `display_date` TEXT column to both `emails` and `meetings` tables. Computed at ingestion time in human-readable Eastern Time format:
  - Meetings: `"Mar 15, 2026 3:00–3:30 PM ET"` (start–end range, critical for Series events where titles are identical)
  - Emails: `"Mar 15, 2026 2:47 PM ET"` (single timestamp from first message)
  - This field is pushed to Notion alongside the ISO date, making manual wiring unambiguous.

- **Bot-like → annotated Draft:** The Post-Email agent logic for bot-only / alias-only threads carries forward from `docs/post-email.md`. Bot-like addresses that pass the skip filter but have no human participants get: `record_status = 'Draft'` + `email_notes` explaining the classification. Adam archives terminal stubs from the UI when ready. Actual spam/noise is handled upstream by Gmail filters and the ingestion skip filter (never creates a record at all). The distinction: bot-like = real automated thread worth tracking for audit, spam = noise that should never enter the CRM.

Refer to the full schema in `freed-solutions-architecture-plan.md` — it's ready to use (add the `display_date` column and title normalization to the schema there).

### 0.3: Config (create `ops/local_db/config.yaml`)

```yaml
database:
  path: ops/local_db/freed.db

google:
  credentials_path: ops/local_db/credentials/google_oauth_credentials.json
  token_path: ops/local_db/credentials/token.json
  scopes:
    - https://www.googleapis.com/auth/gmail.readonly
    - https://www.googleapis.com/auth/gmail.modify
    - https://www.googleapis.com/auth/calendar.readonly

notion:
  token_path: ops/local_db/credentials/notion_token.txt
  databases:
    contacts: fd06740b-ea9f-401f-9083-ebebfb85653c
    companies: 796deadb-b5f0-4adc-ac06-28e94c90db0e
    action_items: 319adb01-222f-8059-bd33-000b029a2fdd
    meetings: 31fadb01-222f-80c0-acf7-000b401a5756
    agent_config: 322adb01-222f-8114-b1b0-cc8971f1b61a
    emails: f685a378-5a37-4517-9b0c-d2928be4af4d

gmail:
  accounts:
    - address: adam@freedsolutions.com
      source_label: "Email - Freed Solutions"
      routing_labels:
        - label: "Primitiv/PRI_Outlook"
          type: forwarded_outlook
        - label: "Primitiv/PRI_Teams"
          type: teams_notification
        - label: "LinkedIn"
          type: linkedin_notification
        - label: "DMC/DMC_GMail"
          type: standard_email
      ignore_labels:
        - "Action Items"
    - address: adamjfreed@gmail.com
      source_label: "Email - Personal"
      routing_labels: []  # labels out of scope for routing
      ignore_labels: []

calendars:
  - account: adam@freedsolutions.com
    calendar_id: primary
    calendar_name: "Adam - Business"
    default_company: "Freed Solutions"
  - account: adamjfreed@gmail.com
    calendar_id: primary
    calendar_name: "Adam - Personal"
    default_company: "Personal"

adam:
  exclude_emails:
    - adam@freedsolutions.com
    - adam@primitivgroup.com
    - adamjfreed@gmail.com
    - freedsolutions@gmail.com
  generic_domains:
    - gmail.com
    - yahoo.com
    - outlook.com
    - hotmail.com
    - icloud.com
    - aol.com
    - protonmail.com
  notion_user_id: "30cd872b-594c-81b7-99dc-0002af0f255a"
```

### 0.4: Build `lib/db.py`

- SQLite connection with WAL mode enabled
- Helper: `get_connection()`, `init_db()` (runs schema.sql), `upsert()`, `query()`
- All timestamps in Eastern time (match Notion convention from post-meeting.md)

### 0.5: Build `lib/gmail_auth.py`

- OAuth2 flow using `google-auth-oauthlib`
- First run opens browser for consent → saves `token.json`
- Subsequent runs use refresh token
- Handle both accounts (`adam@freedsolutions.com`, `adamjfreed@gmail.com`)

### 0.6: Build `ingest/gmail_ingest.py`

Port the logic from `docs/post-email.md` Step 0 + Step 1:

1. Read `agent_config.last_run` for `post_email` agent (or 7-day fallback)
2. For each Gmail account in config:
   - List threads since last run via `threads.list()`
   - For each thread: `threads.get()` for full messages
   - Apply skip filter (calendar invites, DMARC, receipts, etc. — same list as post-email.md Step 1.3)
   - Apply intake classification (standard email, Teams notification, LinkedIn notification, ignored manual queue)
   - Check `thread_id` against local DB for dedup / partial-run detection
   - Insert or resume the email record in SQLite
   - Store `raw_gmail_data` as JSON for downstream agent processing
3. Update `agent_config.last_run` for the ingest step

**Key port decisions:**
- Label routing logic: copy exactly from post-email.md Step 1.1
- Bot filtering: copy from Step 2.2
- Alias exclusion list: from config (`adam.exclude_emails`)
- DO NOT do CRM wiring here — that's the agent's job (Phase 2). Ingest only captures raw thread data.

### 0.7: Build `ingest/gcal_ingest.py`

Port the logic from `docs/post-meeting.md` Step 1.1–1.4:

1. Read `agent_config.last_run` for `post_meeting` agent (or 7-day fallback)
2. For each calendar in config:
   - `events.list()` since last run
   - Filter: accepted only, dateTime only (skip all-day), not cancelled
   - Check `calendar_event_id` against local DB
   - Insert or update meeting record in SQLite
   - Store `raw_gcal_data` as JSON
3. Also create records for events with no existing Meetings DB page (no-notes meetings — Step 1.4 logic)

### 0.8: Build `lib/dedup.py`

Shared dedup utilities used by both ingest and agents:

- `find_contact_by_email(email)` — checks `email`, `secondary_email`, `tertiary_email`
- `find_company_by_domain(domain)` — checks `domains` and `additional_domains`
- `is_generic_domain(domain)` — checks against config list
- `normalize_email(email)` — lowercase + trim
- `normalize_linkedin_url(url)` — canonical `https://www.linkedin.com/in/<slug>` form

### 0.9: Test Phase 0

```bash
# Initialize DB
python -c "from ops.local_db.lib.db import init_db; init_db()"

# Run Gmail ingest (will trigger OAuth consent on first run)
python -m ops.local_db.ingest.gmail_ingest

# Run GCal ingest
python -m ops.local_db.ingest.gcal_ingest

# Verify records
sqlite3 ops/local_db/freed.db "SELECT COUNT(*) FROM emails; SELECT COUNT(*) FROM meetings;"
```

**Validation criteria:**
- [ ] SQLite DB created with correct schema
- [ ] Gmail threads ingested for both accounts
- [ ] Label routing preserved on email records
- [ ] Bot/noise threads filtered correctly
- [ ] GCal events ingested for both calendars
- [ ] Calendar Name mapped correctly
- [ ] All-day and declined events filtered
- [ ] No duplicate records on re-run
- [ ] `agent_config.last_run` updated

---

## PHASE 1: Bidirectional Sync (Notion ↔ SQLite)

### 1.1: Build `lib/notion_client.py`

Thin wrapper around `notion-client` Python SDK:

- `get_database_records(db_id, filter=None)` — paginated query
- `create_page(db_id, properties)` — create a Notion page
- `update_page(page_id, properties)` — update properties
- `get_page(page_id)` — fetch full page with properties
- Property type mapping: Notion types ↔ SQLite types (title, rich_text, select, multi_select, date, relation, rollup, formula, people, url, email, phone_number, checkbox, number, created_time)

### 1.2: Build `sync/notion_backfill.py`

One-time migration:

1. For each of the 6 Notion DBs:
   - Paginate through all records
   - Map Notion properties to SQLite columns
   - Handle relations by storing Notion page IDs (resolve to local IDs after all tables are loaded)
2. After all tables loaded: resolve relation page IDs to local UUIDs
3. Set `notion_synced_at` = now for all records
4. Log record counts per table

**Run once. Verify counts match Notion.**

### 1.3: Build `sync/push_to_notion.py`

Local → Notion push (runs after agents process):

1. Query each table for records where `updated_at > notion_synced_at` (or `notion_synced_at IS NULL` for new records)
2. For new records (`notion_page_id IS NULL`): create Notion page, store the returned page ID
3. For existing records: update Notion page properties
4. Handle relations: resolve local IDs → Notion page IDs before pushing
5. Update `notion_synced_at` after successful push
6. Log to `sync_log`

**Push rules:**
- Push all property changes
- DO NOT push `raw_gmail_data` or `raw_gcal_data` (local-only fields)
- Respect Notion's rate limits (3 requests/second for internal integrations)
- Batch by table, not interleaved

### 1.4: Build `sync/pull_from_notion.py`

Notion → Local pull (catches Adam's manual edits):

1. For each Notion DB: query for records modified since last pull timestamp
2. Map Notion properties back to SQLite columns
3. **Conflict resolution rules:**
   - `record_status` changes: **Notion wins** (Adam's review authority)
   - `contact_notes`, `company_notes`, `task_notes`, `email_notes`: **Notion wins** (Adam may edit)
   - Agent-written fields (`qc_status`, enrichment data): **local wins** unless Notion timestamp is newer
   - Relations: **merge** — union of local and Notion relations
4. Update `notion_modified_at` on affected records
5. Log conflicts to `sync_log`

### 1.5: Test Phase 1

```bash
# Backfill (one-time)
python -m ops.local_db.sync.notion_backfill

# Verify counts
sqlite3 ops/local_db/freed.db "SELECT 'contacts', COUNT(*) FROM contacts UNION ALL SELECT 'companies', COUNT(*) FROM companies UNION ALL SELECT 'emails', COUNT(*) FROM emails UNION ALL SELECT 'meetings', COUNT(*) FROM meetings UNION ALL SELECT 'action_items', COUNT(*) FROM action_items;"

# Push test (after modifying a local record)
python -m ops.local_db.sync.push_to_notion

# Pull test (after Adam edits something in Notion)
python -m ops.local_db.sync.pull_from_notion
```

**Validation criteria:**
- [ ] Backfill record counts match Notion DB counts
- [ ] Relations resolved correctly (local IDs ↔ Notion page IDs)
- [ ] Push creates new Notion pages for new local records
- [ ] Push updates existing Notion pages for changed local records
- [ ] Pull detects Adam's manual edits in Notion
- [ ] Conflict resolution follows the rules above
- [ ] `sync_log` captures all operations
- [ ] No data loss on round-trip (push then pull same record)

---

## PHASE 2: Local Agent Runner

### 2.1: Build `agents/runner.py`

Generic framework for running agents locally via Claude API:

```python
class AgentRunner:
    def __init__(self, agent_name, instruction_path, db_path):
        """
        agent_name: e.g., 'post_email'
        instruction_path: e.g., 'ops/notion-workspace/docs/post-email.md'
        db_path: path to SQLite DB
        """

    def get_records_in_scope(self) -> list:
        """Override per agent — returns records to process."""

    def build_context(self, records) -> str:
        """Builds the prompt context from local DB records."""

    def execute(self, context) -> dict:
        """Calls Claude API with instruction + context. Returns structured results."""

    def apply_results(self, results):
        """Writes agent output back to local SQLite."""

    def run(self):
        """Full pipeline: scope → context → execute → apply → log."""
```

**Claude API integration:**
- Use `anthropic` Python SDK
- Model: `claude-sonnet-4-20250514` (cost-effective for batch processing)
- System prompt: the instruction MD content
- User prompt: the structured record context from local DB
- Response: structured JSON with actions to apply
- Store API key in `ops/local_db/credentials/anthropic_key.txt` (gitignored)

**Alternative approach (simpler for v1):** Instead of calling Claude API, the runner can execute the agent logic directly in Python — deterministic code for the well-defined steps (dedup, contact matching, company wiring, skip filtering), calling Claude API only for the judgment-heavy steps (enrichment, action item parsing from email bodies, curated notes generation). This hybrid approach is faster and cheaper.

### 2.2: Port Post-Email Agent (`agents/post_email.py`)

Port from `docs/post-email.md`. The ingestion (Step 0–1) is already handled by Phase 0. This agent handles Steps 2–4:

**Step 2 — CRM Wiring (deterministic Python):**
- Extract participant emails from `raw_gmail_data`
- Run alias exclusion (from config)
- Run bot filtering
- Teams/LinkedIn notification body parsing (call Claude API for this — needs NLP)
- Contact matching: use `lib/dedup.py` against local SQLite
- Company matching: domain extraction → local SQLite lookup
- Create Draft contacts/companies for unknowns
- Write relations to junction tables

**Step 3 — Action Items (Claude API call):**
- For emails with human contacts and business context:
- Build prompt with email body + contact/company context
- Claude parses actionable work → returns structured JSON
- Apply required-property fallback rules (Company ownership, Due Date, etc.)
- Write Draft Action Items to local SQLite

**Step 4 — Summary and cleanup (deterministic Python):**
- Write `email_notes` summary
- Update `agent_config` timestamp
- Mark terminal Gmail threads as read via Gmail API `modify()`

### 2.3: Port Post-Meeting Agent (`agents/post_meeting.py`)

Port from `docs/post-meeting.md`. GCal ingestion is Phase 0. This agent handles the pipeline:

**Step 1 — CRM Wiring (deterministic Python):**
- Attendee list from `raw_gcal_data`
- Contact matching against local SQLite
- Company wiring via domain lookup
- Series matching against local series registry
- Calendar Name already set by ingestion

**Step 2.0 — Floppy Parsing (hybrid):**
- **Transcript access:** Still fetched from Notion via API (Notion Calendar owns this content)
- Parse `(Floppy)` items from AI summary (deterministic regex)
- Transcript fallback parsing (deterministic regex)
- Notes block parsing (deterministic)
- Classification and entity extraction (Claude API call for ambiguous cases)
- Contact resolution: two-tier local lookup

**Step 2.1–2.3 — Notes-driven Action Items (hybrid):**
- Parse typed notes from Notion page content
- Grouping and dedup (deterministic)
- Property mapping and DB write (deterministic)

**Step 3 — Curated Notes (Claude API call):**
- Only on Active trigger path
- Build context from local DB records + transcript content
- Claude generates structured summary
- Write curated blocks to Notion page via API (this stays in Notion — it's page content, not DB properties)

**Note on transcript dependency:** The Post-Meeting agent still needs to fetch transcript/notes content from Notion. This is acceptable — Notion Calendar is the transcript source. The local DB stores meeting metadata; Notion stores page content. This dependency shrinks if/when you move to local Whisper recording on Mac Mini.

### 2.4: Port Contact & Company Agent (`agents/contact_company.py`)

Port from `docs/contact-company.md`. Simplest agent — mostly enrichment:

**Queue building (deterministic Python):**
- Companies: `record_status = 'Draft'` OR (`record_status = 'Active'` AND QC gap)
- Contacts: same filter
- Fairness ordering: oldest Active gaps → oldest Draft → newest
- Cap: 20 per queue

**Phase 1 — Company pass (hybrid):**
- Dedup: deterministic domain comparison against local SQLite
- Enrichment: Claude API call with web search tool for company name, type, website, states, additional domains

**Phase 2 — Contact pass (hybrid):**
- Dedup: deterministic email comparison
- Evidence gathering: Gmail API for signatures (read from `raw_gmail_data`), GCal for context
- Enrichment: Claude API call for role, LinkedIn, phone normalization

### 2.5: Scheduler (`ops/local_db/scheduler.py`)

Simple Python scheduler (or cron wrapper) for 3x/day processing:

```python
SCHEDULE = [
    # (time, function, description)
    ("07:00", gmail_ingest,    "Morning Gmail sweep"),
    ("07:05", gcal_ingest,     "Morning GCal sweep"),
    ("07:15", post_email,      "Post-Email CRM wiring"),
    ("07:20", post_meeting,    "Post-Meeting CRM wiring"),
    ("07:30", contact_company, "Contact & Company enrichment"),
    ("07:45", push_to_notion,  "Push results to Notion"),

    ("13:00", gmail_ingest,    "Midday Gmail sweep"),
    ("13:05", gcal_ingest,     "Midday GCal sweep"),
    ("13:15", post_email,      "Post-Email CRM wiring"),
    ("13:20", post_meeting,    "Post-Meeting CRM wiring"),
    ("13:30", contact_company, "Contact & Company enrichment"),
    ("13:45", push_to_notion,  "Push results to Notion"),

    ("21:00", gmail_ingest,    "Evening Gmail sweep"),
    ("21:05", gcal_ingest,     "Evening GCal sweep"),
    ("21:15", post_email,      "Post-Email CRM wiring"),
    ("21:20", post_meeting,    "Post-Meeting CRM wiring"),
    ("21:30", contact_company, "Contact & Company enrichment"),
    ("21:45", push_to_notion,  "Push results to Notion"),

    # Pull from Notion hourly (catch Adam's manual edits)
    ("*/60",  pull_from_notion, "Pull Adam's Notion edits"),
]
```

### 2.6: Test Phase 2

**Parallel run validation:**

1. Run local agents AND keep Notion agents running for 2–3 days
2. Compare local DB records against Notion records after each cycle
3. Fix discrepancies in agent logic
4. Once parity is confirmed:
   - Disable Notion Custom Agents one at a time
   - Start with Contact & Company (simplest, lowest risk)
   - Post-Email next
   - Post-Meeting last (most complex, transcript dependency)

**Validation criteria per agent:**
- [ ] Post-Email: same email records created, same contacts matched, same action items generated
- [ ] Post-Meeting: same CRM wiring, same action items, Floppy parsing matches
- [ ] Contact & Company: same enrichment results, same dedup flags
- [ ] No duplicate records across local + Notion
- [ ] `record_status` changes in Notion flow back correctly via pull sync

---

## PHASE 2.5: Update Repo Infrastructure

### Update `ops/notion-workspace/CLAUDE.md`

Add a section documenting the local-db layer:

- `ops/local_db/` directory purpose and relationship to `ops/notion-workspace/`
- How local agents read instructions from `ops/notion-workspace/docs/` (no change to instruction MDs)
- Sync model: local DB → Notion push, Notion → local pull
- New credential paths (gitignored)

### Update `ops/notion-workspace/session-active.md`

Add the local-db work as a new priority block, documenting:

- Current phase status
- Parallel run results
- Which Notion agents have been disabled vs. still running

### Update `.gitignore`

```
ops/local_db/credentials/
ops/local_db/*.db
ops/local_db/credentials/token.json
```

---

## EXECUTION ORDER SUMMARY

```
Phase 0 (do first — independently valuable):
  0.1  Directory structure
  0.2  SQLite schema
  0.3  Config file
  0.4  lib/db.py
  0.5  lib/gmail_auth.py
  0.6  ingest/gmail_ingest.py      ← FIRST LIVE TEST (triggers OAuth consent)
  0.7  ingest/gcal_ingest.py
  0.8  lib/dedup.py
  0.9  Test: verify ingestion works

Phase 1 (enables Notion as dashboard):
  1.1  lib/notion_client.py
  1.2  sync/notion_backfill.py      ← ONE-TIME RUN
  1.3  sync/push_to_notion.py
  1.4  sync/pull_from_notion.py
  1.5  Test: verify round-trip sync

Phase 2 (replaces Notion agents):
  2.1  agents/runner.py
  2.2  agents/post_email.py
  2.3  agents/post_meeting.py
  2.4  agents/contact_company.py
  2.5  scheduler.py
  2.6  Test: parallel run validation
```

---

## DECISIONS FOR EXECUTION SESSION

If ambiguity arises during execution, use these defaults:

1. **Schema disagreement between this checklist and Notion docs:** Notion docs (`ops/notion-workspace/docs/`) are the source of truth for business logic. This checklist is the source of truth for architecture.
2. **Agent logic ambiguity:** Follow the existing agent MD files exactly. The local agents should produce identical output to the Notion agents.
3. **Rate limiting:** Notion API limit is 3 req/sec for internal integrations. Gmail API default is 250 quota units/sec. Build in retry with exponential backoff.
4. **Error handling:** Log and continue. Never crash the pipeline on a single record failure. Write errors to `sync_log` and move to the next record.
5. **Testing approach:** Test each phase independently before building the next. Don't skip Phase 0 testing to rush Phase 2.
6. **Routing source of truth:** Live Gmail labels and filters are the upstream routing contract. Notion/DB business rules should define the desired state, and Gmail should enforce it through labels and filters rather than through hard-coded one-off inbox rules.

---

## PHASE 3 / V2: Gmail Filter Automation (Next Phase)

Goal: make Gmail filters a managed automation layer driven by approved Company and Contact records, while keeping `thread_id` as the downstream canonical dedup key in the Emails DB.

### 3.1: Desired-state model

- Treat Notion + local DB business rules as the policy source of truth.
- Treat live Gmail labels/filters as the enforcement layer and audit surface.
- Reconcile desired filter state into Gmail rather than managing filters manually forever.
- Preserve support for overlapping company context. Multiple filters are acceptable, including cases like `Deeproots` + `Primitiv` on the same incoming message.

### 3.2: Trigger rules

- Company approved/activated:
  - Read `Domains` and `Additional Domains`
  - Ensure the canonical Gmail label exists
  - Create or refresh company-domain filters for the relevant mailbox
- Contact approved/activated:
  - Create narrower sender-based filters only when contact-level routing is needed beyond the company-domain rules
  - Use these as exceptions or tie-breakers, not as the default routing path for every contact
- Manual review remains valid for edge cases, but the desired end state is that approved CRM records drive Gmail routing automatically

### 3.3: Gmail implementation rules

- Use Gmail API filter management (`users.settings.filters`) plus label management
- Add future OAuth scopes when this phase starts:
  - `https://www.googleapis.com/auth/gmail.settings.basic`
  - `https://www.googleapis.com/auth/gmail.labels`
- Filters operate at the individual-message level; this is acceptable because downstream ingestion and CRM dedup remain thread-based via `thread_id`
- Gmail filters do not have a true update call; edits should be handled as list/get -> diff -> delete/recreate
- Multiple filters per message are allowed and expected in cross-company or exception scenarios

### 3.4: Routing defaults

- Use company/domain filters as the primary routing path
- Use contact/email filters for exceptions, named senders, or special handling that domain rules cannot express cleanly
- Preserve routed Gmail labels into `Emails.Labels`
- Continue ignoring personal-mailbox labels for routing unless a mailbox-specific contract is added later
- Keep calendar handling narrow:
  - accepted/declined/tentative response emails should be filtered out where possible
  - invite/update emails can remain available when they help reconcile the correct Meeting / calendar assignment

### 3.5: Reconciliation job

- Build a small reconciliation pass that:
  - reads the current Gmail labels and filters
  - computes the desired labels and filters from approved Companies/Contacts
  - creates missing labels
  - creates missing filters
  - recreates changed filters
  - reports stale filters for safe cleanup or controlled removal
- Prefer idempotent sync over one-off create-only behavior
- Log every create/delete/recreate action so routing drift is auditable

### 3.6: Validation for Phase 3 / v2

- [ ] New approved Company creates or refreshes the expected Gmail label + domain filter
- [ ] New approved Contact can add a narrower sender exception without breaking company-domain routing
- [ ] Overlapping company messages can receive multiple labels without breaking downstream thread-based dedup
- [ ] `thread_id` remains the canonical Emails key even though Gmail filters operate per message
- [ ] Routed labels continue to land in `Emails.Labels`
- [ ] Accepted calendar responses are filtered out
- [ ] Invite/update emails still remain available when needed for Meeting reconciliation
- [ ] Filter reconciliation is idempotent across repeat runs
- [ ] Filter changes are logged with enough detail to audit drift and rollback manually if needed

---

## NOT IN SCOPE (Future Phases)

- Mac Mini daemon setup (later infrastructure phase — hardware not yet procured)
- Local meeting recording / Whisper transcription
- Custom dashboard frontend (Notion stays as UI)
- LinkedIn API direct access (stay with Gmail notification intake)
- Claude Cowork Agents for outbound LinkedIn actions
