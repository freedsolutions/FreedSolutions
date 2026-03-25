PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS companies (
    id TEXT PRIMARY KEY,
    notion_page_id TEXT UNIQUE,
    company_name TEXT NOT NULL,
    company_type TEXT,
    qc TEXT,
    domains TEXT,
    additional_domains TEXT,
    states TEXT,
    website TEXT,
    record_status TEXT,
    company_notes TEXT,
    notion_last_edited_at TEXT,
    notion_synced_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS contacts (
    id TEXT PRIMARY KEY,
    notion_page_id TEXT UNIQUE,
    contact_name TEXT NOT NULL,
    display_name TEXT,
    qc TEXT,
    email TEXT,
    secondary_email TEXT,
    tertiary_email TEXT,
    phone TEXT,
    pronouns TEXT,
    nickname TEXT,
    linkedin TEXT,
    company_id TEXT,
    role_title TEXT,
    record_status TEXT,
    contact_notes TEXT,
    notion_last_edited_at TEXT,
    notion_synced_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (company_id) REFERENCES companies (id)
);

CREATE TABLE IF NOT EXISTS meetings (
    id TEXT PRIMARY KEY,
    notion_page_id TEXT UNIQUE,
    meeting_title TEXT NOT NULL,
    raw_title TEXT,
    calendar_event_id TEXT UNIQUE,
    calendar_name TEXT,
    date_start TEXT,
    date_end TEXT,
    display_date TEXT,
    location TEXT,
    record_status TEXT,
    qc TEXT,
    series_parent_id TEXT,
    raw_gcal_data TEXT,
    notion_last_edited_at TEXT,
    notion_synced_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (series_parent_id) REFERENCES meetings (id)
);

CREATE TABLE IF NOT EXISTS emails (
    id TEXT PRIMARY KEY,
    notion_page_id TEXT UNIQUE,
    email_subject TEXT NOT NULL,
    raw_subject TEXT,
    thread_id TEXT UNIQUE,
    mailbox_address TEXT,
    source TEXT,
    intake_type TEXT,
    from_address TEXT,
    direction TEXT,
    message_timestamp TEXT,
    display_date TEXT,
    labels TEXT,
    record_status TEXT,
    email_notes TEXT,
    qc TEXT,
    is_terminal INTEGER NOT NULL DEFAULT 0,
    raw_gmail_data TEXT,
    notion_last_edited_at TEXT,
    notion_synced_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS action_items (
    id TEXT PRIMARY KEY,
    notion_page_id TEXT UNIQUE,
    task_name TEXT NOT NULL,
    type TEXT,
    status TEXT,
    priority TEXT,
    record_status TEXT,
    task_notes TEXT,
    due_date_start TEXT,
    due_date_end TEXT,
    created_date TEXT,
    contact_id TEXT,
    company_id TEXT,
    assignee_ids TEXT,
    source_meeting_id TEXT,
    source_email_id TEXT,
    attach_files TEXT,
    qc TEXT,
    notion_last_edited_at TEXT,
    notion_synced_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (contact_id) REFERENCES contacts (id),
    FOREIGN KEY (company_id) REFERENCES companies (id),
    FOREIGN KEY (source_meeting_id) REFERENCES meetings (id),
    FOREIGN KEY (source_email_id) REFERENCES emails (id)
);

CREATE TABLE IF NOT EXISTS email_contacts (
    email_id TEXT NOT NULL,
    contact_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (email_id, contact_id),
    FOREIGN KEY (email_id) REFERENCES emails (id) ON DELETE CASCADE,
    FOREIGN KEY (contact_id) REFERENCES contacts (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS meeting_contacts (
    meeting_id TEXT NOT NULL,
    contact_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (meeting_id, contact_id),
    FOREIGN KEY (meeting_id) REFERENCES meetings (id) ON DELETE CASCADE,
    FOREIGN KEY (contact_id) REFERENCES contacts (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS agent_config (
    agent_name TEXT PRIMARY KEY,
    last_run TEXT,
    last_successful_run TEXT,
    state_json TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation TEXT NOT NULL,
    table_name TEXT NOT NULL,
    local_record_id TEXT,
    notion_page_id TEXT,
    status TEXT NOT NULL,
    message TEXT,
    payload TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_contacts_email ON contacts (email);
CREATE INDEX IF NOT EXISTS idx_contacts_secondary_email ON contacts (secondary_email);
CREATE INDEX IF NOT EXISTS idx_contacts_tertiary_email ON contacts (tertiary_email);
CREATE INDEX IF NOT EXISTS idx_contacts_company_id ON contacts (company_id);
CREATE INDEX IF NOT EXISTS idx_companies_domains ON companies (domains);
CREATE INDEX IF NOT EXISTS idx_companies_additional_domains ON companies (additional_domains);
CREATE INDEX IF NOT EXISTS idx_meetings_calendar_event_id ON meetings (calendar_event_id);
CREATE INDEX IF NOT EXISTS idx_emails_thread_id ON emails (thread_id);
CREATE INDEX IF NOT EXISTS idx_emails_mailbox_address ON emails (mailbox_address);
CREATE INDEX IF NOT EXISTS idx_action_items_company_id ON action_items (company_id);
CREATE INDEX IF NOT EXISTS idx_action_items_contact_id ON action_items (contact_id);
CREATE INDEX IF NOT EXISTS idx_action_items_source_meeting_id ON action_items (source_meeting_id);
CREATE INDEX IF NOT EXISTS idx_action_items_source_email_id ON action_items (source_email_id);
