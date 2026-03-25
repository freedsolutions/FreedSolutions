import json
import unittest
from datetime import datetime
from pathlib import Path
import shutil

from ops.local_db.ingest.gcal_ingest import should_skip_event, upsert_event
from ops.local_db.ingest.gmail_ingest import (
    build_gmail_query,
    classify_thread,
    determine_skip_reason,
    sanitize_thread_payload,
    upsert_thread,
)
from ops.local_db.lib.config import AdamConfig, CalendarConfig, GmailAccountConfig, GmailRoutingLabel
from ops.local_db.lib.db import DISPLAY_TZ_LABEL, EASTERN, format_meeting_display_date, init_db, normalize_title, upsert
from ops.local_db.lib.dedup import (
    find_company_by_domain,
    find_company_by_sender_address,
    find_contact_by_email,
)
from ops.local_db.lib.paths import DEFAULT_SCHEMA_PATH
from ops.local_db.sync.pull_from_notion import merge_record, merge_relations


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / ".claude" / "tmp" / "test-local-db-fixture"


class LocalDbTests(unittest.TestCase):
    def setUp(self) -> None:
        if FIXTURE_ROOT.exists():
            shutil.rmtree(FIXTURE_ROOT)
        FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)
        self.db_path = FIXTURE_ROOT / "local.db"
        self.connection = init_db(db_path=self.db_path, schema_path=DEFAULT_SCHEMA_PATH)

    def tearDown(self) -> None:
        self.connection.close()
        if FIXTURE_ROOT.exists():
            shutil.rmtree(FIXTURE_ROOT)

    def test_init_db_creates_core_tables(self) -> None:
        tables = {
            row["name"]
            for row in self.connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        self.assertTrue({"companies", "contacts", "meetings", "emails", "action_items", "agent_config"}.issubset(tables))

    def test_normalize_title_strips_recursive_prefixes(self) -> None:
        self.assertEqual(normalize_title("Re: Fwd: FW: Quarterly update"), "Quarterly update")

    def test_format_meeting_display_date_uses_eastern_range(self) -> None:
        start = datetime(2026, 3, 7, 15, 0, tzinfo=EASTERN)
        end = datetime(2026, 3, 7, 15, 30, tzinfo=EASTERN)
        self.assertEqual(
            format_meeting_display_date(start, end),
            f"Mar 7, 2026 3:00 PM-3:30 PM {DISPLAY_TZ_LABEL}",
        )

    def test_find_contact_by_email_checks_secondary_and_tertiary(self) -> None:
        upsert(
            self.connection,
            "contacts",
            {
                "contact_name": "Alex Example",
                "email": "primary@example.com",
                "secondary_email": "second@example.com",
                "tertiary_email": "third@example.com",
                "record_status": "Draft",
                "created_at": "2026-03-24T10:00:00-04:00",
                "updated_at": "2026-03-24T10:00:00-04:00",
            },
            conflict_columns=("id",),
        )

        match = find_contact_by_email(self.connection, "third@example.com")
        self.assertIsNotNone(match)
        self.assertEqual(match["contact_name"], "Alex Example")

    def test_find_company_helpers_cover_domain_and_sender_level_matching(self) -> None:
        upsert(
            self.connection,
            "companies",
            {
                "company_name": "Google",
                "domains": "google.com",
                "additional_domains": "workspace@google.com",
                "record_status": "Draft",
                "created_at": "2026-03-24T10:00:00-04:00",
                "updated_at": "2026-03-24T10:00:00-04:00",
            },
            conflict_columns=("id",),
        )

        domain_match = find_company_by_domain(self.connection, "hello@google.com")
        sender_match = find_company_by_sender_address(self.connection, "workspace@google.com")
        self.assertEqual(domain_match["company_name"], "Google")
        self.assertEqual(sender_match["company_name"], "Google")

    def test_gmail_classification_prefers_routing_labels_and_manual_queue(self) -> None:
        account = GmailAccountConfig(
            address="adam@freedsolutions.com",
            source_label="Email - Freed Solutions",
            routing_labels=(
                GmailRoutingLabel(label="Primitiv/PRI_Teams", type="teams_notification"),
                GmailRoutingLabel(label="LinkedIn", type="linkedin_notification"),
            ),
            ignore_labels=("Action Items",),
        )
        thread = {
            "messages": [
                {
                    "payload": {
                        "headers": [{"name": "Subject", "value": "Chat notification"}],
                        "body": {},
                    }
                }
            ],
            "snippet": "Microsoft Teams notification",
        }

        self.assertEqual(
            classify_thread(account, thread, ["Primitiv/PRI_Teams"]),
            "teams_notification",
        )
        self.assertEqual(
            determine_skip_reason(thread, "ignored_manual_queue", ["Action Items/Review"]),
            "Configured ignore label kept the thread out of automated intake.",
        )

    def test_gmail_ignore_labels_are_respected(self) -> None:
        account = GmailAccountConfig(
            address="adam@freedsolutions.com",
            source_label="Email - Freed Solutions",
            routing_labels=(),
            ignore_labels=("Skip Me",),
        )
        thread = {
            "messages": [
                {
                    "payload": {
                        "headers": [{"name": "Subject", "value": "Ignore this"}],
                        "body": {},
                    }
                }
            ],
            "snippet": "Ignore this thread",
        }

        self.assertEqual(
            classify_thread(account, thread, ["Skip Me/Child"]),
            "ignored_manual_queue",
        )

    def test_gmail_query_uses_supported_date_format(self) -> None:
        lookback = datetime(2026, 3, 7, 9, 30, tzinfo=EASTERN)
        self.assertEqual(build_gmail_query(lookback), "after:2026/03/07")

    def test_sanitize_thread_payload_strips_attachment_bodies(self) -> None:
        thread = {
            "id": "thread-raw",
            "snippet": "hello",
            "messages": [
                {
                    "id": "message-1",
                    "threadId": "thread-raw",
                    "internalDate": "1711306800000",
                    "labelIds": ["INBOX"],
                    "payload": {
                        "mimeType": "multipart/mixed",
                        "headers": [{"name": "Subject", "value": "Hello"}],
                        "parts": [
                            {
                                "mimeType": "text/plain",
                                "body": {"data": "SGVsbG8"},
                            },
                            {
                                "mimeType": "application/pdf",
                                "filename": "file.pdf",
                                "body": {"attachmentId": "abc123", "data": "BIGBLOB"},
                            },
                        ],
                    },
                }
            ],
        }

        sanitized = sanitize_thread_payload(thread)

        attachment_part = sanitized["messages"][0]["payload"]["parts"][1]
        self.assertEqual(attachment_part["body"], {"attachmentId": "abc123"})
        self.assertNotIn("BIGBLOB", json.dumps(sanitized))

    def test_gmail_upsert_logs_non_null_local_record_id(self) -> None:
        account = GmailAccountConfig(
            address="adam@freedsolutions.com",
            source_label="Email - Freed Solutions",
            routing_labels=(),
            ignore_labels=(),
        )
        adam = AdamConfig(
            exclude_emails=(
                "adam@freedsolutions.com",
                "adam@primitivgroup.com",
                "adamjfreed@gmail.com",
                "freedsolutions@gmail.com",
            ),
            generic_domains=("gmail.com",),
            notion_user_id="123",
        )
        thread = {
            "id": "thread-1",
            "snippet": "Hello there",
            "messages": [
                {
                    "internalDate": "1711306800000",
                    "payload": {
                        "headers": [
                            {"name": "Subject", "value": "Hello"},
                            {"name": "From", "value": "Sam Sender <sam@example.com>"},
                        ],
                        "body": {},
                    },
                }
            ],
        }

        created = upsert_thread(
            self.connection,
            account,
            adam,
            thread,
            ["Inbox"],
            "standard_email",
            None,
        )

        self.assertTrue(created)
        row = self.connection.execute(
            "SELECT local_record_id FROM sync_log WHERE operation = 'gmail_ingest' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        self.assertTrue(row["local_record_id"])

    def test_gcal_upsert_logs_non_null_local_record_id(self) -> None:
        calendar = CalendarConfig(
            account="adam@freedsolutions.com",
            calendar_id="primary",
            calendar_name="Adam - Business",
            default_company="Freed Solutions",
        )
        event = {
            "id": "event-1",
            "summary": "Project sync",
            "start": {"dateTime": "2026-03-24T15:00:00-04:00"},
            "end": {"dateTime": "2026-03-24T15:30:00-04:00"},
            "status": "confirmed",
        }

        created = upsert_event(self.connection, calendar, event, None)

        self.assertTrue(created)
        row = self.connection.execute(
            "SELECT local_record_id FROM sync_log WHERE operation = 'gcal_ingest' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        self.assertTrue(row["local_record_id"])

    def test_merge_record_prefers_remote_notes_and_status(self) -> None:
        upsert(
            self.connection,
            "emails",
            {
                "id": "email-local",
                "notion_page_id": "notion-email-1",
                "email_subject": "Hello",
                "thread_id": "thread-merge",
                "record_status": "Draft",
                "email_notes": "local note",
                "created_at": "2026-03-24T10:00:00-04:00",
                "updated_at": "2026-03-24T10:00:00-04:00",
            },
            conflict_columns=("id",),
        )
        existing = self.connection.execute("SELECT * FROM emails WHERE id = 'email-local'").fetchone()
        remote_record = {
            "id": "ignored",
            "notion_page_id": "notion-email-1",
            "email_subject": "Hello",
            "thread_id": "thread-merge",
            "record_status": "Active",
            "email_notes": "remote note",
            "notion_last_edited_at": "2026-03-24T11:00:00-04:00",
            "notion_synced_at": "2026-03-24T11:00:00-04:00",
            "created_at": "2026-03-24T10:00:00-04:00",
            "updated_at": "2026-03-24T11:00:00-04:00",
        }

        merged = merge_record("emails", existing, remote_record)

        self.assertEqual(merged["record_status"], "Active")
        self.assertEqual(merged["email_notes"], "remote note")
        self.assertEqual(merged["id"], "email-local")

    def test_merge_relations_unions_existing_and_remote_contact_links(self) -> None:
        upsert(
            self.connection,
            "contacts",
            {
                "id": "contact-1",
                "notion_page_id": "notion-contact-1",
                "contact_name": "One",
                "created_at": "2026-03-24T10:00:00-04:00",
                "updated_at": "2026-03-24T10:00:00-04:00",
            },
            conflict_columns=("id",),
        )
        upsert(
            self.connection,
            "contacts",
            {
                "id": "contact-2",
                "notion_page_id": "notion-contact-2",
                "contact_name": "Two",
                "created_at": "2026-03-24T10:00:00-04:00",
                "updated_at": "2026-03-24T10:00:00-04:00",
            },
            conflict_columns=("id",),
        )
        upsert(
            self.connection,
            "emails",
            {
                "id": "email-merge",
                "notion_page_id": "notion-email-merge",
                "email_subject": "Hello",
                "thread_id": "thread-merge-2",
                "created_at": "2026-03-24T10:00:00-04:00",
                "updated_at": "2026-03-24T10:00:00-04:00",
            },
            conflict_columns=("id",),
        )
        self.connection.execute(
            """
            INSERT INTO email_contacts (email_id, contact_id, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            ("email-merge", "contact-1", "2026-03-24T10:00:00-04:00", "2026-03-24T10:00:00-04:00"),
        )
        self.connection.commit()

        merged = merge_relations(
            self.connection,
            "emails",
            "email-merge",
            {"contacts": ["notion-contact-2"]},
        )

        self.assertEqual(sorted(merged["contacts"]), ["notion-contact-1", "notion-contact-2"])

    def test_should_skip_event_only_skips_declined_or_cancelled(self) -> None:
        base_event = {
            "id": "event-1",
            "summary": "Sync",
            "start": {"dateTime": "2026-03-24T15:00:00-04:00"},
            "end": {"dateTime": "2026-03-24T15:30:00-04:00"},
            "attendees": [{"email": "adam@freedsolutions.com", "responseStatus": "needsAction"}],
        }

        self.assertFalse(should_skip_event(base_event, "adam@freedsolutions.com"))
        declined = dict(base_event)
        declined["attendees"] = [{"email": "adam@freedsolutions.com", "responseStatus": "declined"}]
        self.assertTrue(should_skip_event(declined, "adam@freedsolutions.com"))
        cancelled = dict(base_event)
        cancelled["status"] = "cancelled"
        self.assertTrue(should_skip_event(cancelled, "adam@freedsolutions.com"))


if __name__ == "__main__":
    unittest.main()
