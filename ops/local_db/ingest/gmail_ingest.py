from __future__ import annotations

import argparse
import base64
import json
import uuid
from datetime import datetime
from email.utils import parseaddr
from typing import Any

from ops.local_db.lib.config import AdamConfig, GmailAccountConfig, load_config
from ops.local_db.lib.db import (
    EASTERN,
    compute_lookback,
    format_email_display_date,
    init_db,
    iso_now,
    log_sync_event,
    parse_datetime,
    set_agent_state,
    upsert,
)
from ops.local_db.lib.gmail_auth import build_gmail_service


SKIP_SUBJECT_PATTERNS = (
    "dmarc",
    "dkim",
    "calendar invitation",
    "invitation:",
    "declined:",
    "accepted:",
    "shipment",
    "tracking number",
    "password reset",
    "security alert",
    "receipt",
    "invoice",
    "statement available",
    "newsletter",
    "release notes",
    "changelog",
)
SKIP_FROM_PATTERNS = (
    "mailer-daemon",
    "postmaster@",
    "no-reply@",
    "noreply@",
    "donotreply@",
)


def run(config_path: str | None = None) -> dict[str, dict[str, int]]:
    config = load_config(config_path)
    connection = init_db(config=config)
    try:
        summary: dict[str, dict[str, int]] = {}
        for account in config.gmail_accounts:
            summary[account.address] = ingest_account(connection, account, config)
        return summary
    finally:
        connection.close()


def ingest_account(connection, account: GmailAccountConfig, config) -> dict[str, int]:
    service = build_gmail_service(account.address, config.google)
    label_map = list_label_names(service)
    agent_name = f"gmail_ingest:{account.address}"
    lookback = compute_lookback(connection, agent_name)
    query_text = build_gmail_query(lookback)

    counters = {"seen": 0, "inserted": 0, "updated": 0, "skipped": 0}
    page_token = None

    while True:
        response = service.users().threads().list(
            userId="me",
            q=query_text,
            pageToken=page_token,
        ).execute()
        threads = response.get("threads", [])
        for thread_ref in threads:
            counters["seen"] += 1
            thread = service.users().threads().get(userId="me", id=thread_ref["id"], format="full").execute()
            user_labels = extract_user_labels(thread, label_map)
            classification = classify_thread(account, thread, user_labels)
            skip_reason = determine_skip_reason(thread, classification, user_labels)
            if skip_reason:
                counters["skipped"] += 1
                log_sync_event(
                    connection,
                    operation="gmail_ingest",
                    table_name="emails",
                    notion_page_id=None,
                    status="skipped",
                    message=skip_reason,
                    payload={"thread_id": thread.get("id"), "labels": user_labels},
                )
                continue

            existing = connection.execute(
                "SELECT * FROM emails WHERE thread_id = ?",
                (thread.get("id"),),
            ).fetchone()
            created = upsert_thread(
                connection,
                account,
                config.adam,
                thread,
                user_labels,
                classification,
                existing,
            )
            counters["inserted" if created else "updated"] += 1

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    now_value = iso_now()
    set_agent_state(
        connection,
        agent_name,
        last_run=now_value,
        last_successful_run=now_value,
        state=counters,
    )
    return counters


def list_label_names(service) -> dict[str, str]:
    response = service.users().labels().list(userId="me").execute()
    labels = response.get("labels", [])
    return {item["id"]: item["name"] for item in labels}


def build_gmail_query(lookback: datetime) -> str:
    return f"after:{lookback.strftime('%Y/%m/%d')}"


def extract_user_labels(thread: dict[str, Any], label_map: dict[str, str]) -> list[str]:
    labels: set[str] = set()
    for message in thread.get("messages", []):
        for label_id in message.get("labelIds", []):
            label_name = label_map.get(label_id)
            if label_name and not label_name.startswith("CATEGORY_") and label_name not in {
                "INBOX",
                "UNREAD",
                "IMPORTANT",
                "STARRED",
                "SENT",
            }:
                labels.add(label_name)
    return sorted(labels)


def classify_thread(
    account: GmailAccountConfig,
    thread: dict[str, Any],
    labels: list[str],
) -> str:
    if has_ignored_label(labels, account.ignore_labels):
        return "ignored_manual_queue"

    label_lookup = {item.label: item.type for item in account.routing_labels}
    for label in labels:
        if label in label_lookup:
            return label_lookup[label]

    if any(label == "LinkedIn" for label in labels):
        return "linkedin_notification"
    if any(label.startswith("Action Items") for label in labels):
        return "ignored_manual_queue"

    body = get_thread_text(thread).lower()
    subject = extract_subject(thread).lower()
    if "microsoft teams" in body or "via teams" in body or "[teams]" in subject:
        return "teams_notification"
    if "linkedin" in body or "linkedin" in subject:
        return "linkedin_notification"
    return "standard_email"


def determine_skip_reason(thread: dict[str, Any], classification: str, labels: list[str]) -> str | None:
    if classification == "ignored_manual_queue":
        return "Configured ignore label kept the thread out of automated intake."

    subject = extract_subject(thread).lower()
    sender = extract_sender_email(thread).lower()
    snippet = (thread.get("snippet") or "").lower()
    haystack = f"{subject}\n{sender}\n{snippet}"

    if any(pattern in sender for pattern in SKIP_FROM_PATTERNS):
        return f"Skipped noisy sender: {sender}"
    if any(pattern in haystack for pattern in SKIP_SUBJECT_PATTERNS):
        return f"Skipped by conservative filter: {subject}"
    if any(label.startswith("Calendar") for label in labels):
        return "Skipped calendar-labeled thread."
    return None


def has_ignored_label(labels: list[str], ignore_labels: tuple[str, ...]) -> bool:
    for label in labels:
        for ignored in ignore_labels:
            if label == ignored or label.startswith(f"{ignored}/"):
                return True
    return False


def upsert_thread(
    connection,
    account: GmailAccountConfig,
    adam_config: AdamConfig,
    thread: dict[str, Any],
    labels: list[str],
    classification: str,
    existing,
) -> bool:
    first_message = thread.get("messages", [{}])[0]
    subject = extract_subject(thread)
    timestamp = parse_gmail_datetime(first_message.get("internalDate"))
    existing_created_at = existing["created_at"] if existing else iso_now()

    local_id = existing["id"] if existing else str(uuid.uuid4())
    record = {
        "id": local_id,
        "notion_page_id": existing["notion_page_id"] if existing else None,
        "email_subject": subject,
        "raw_subject": subject,
        "thread_id": thread.get("id"),
        "mailbox_address": account.address,
        "source": account.source_label,
        "intake_type": classification,
        "from_address": extract_sender_email(thread),
        "direction": determine_direction(
            extract_sender_email(thread),
            account.address,
            adam_config.exclude_emails,
        ),
        "message_timestamp": timestamp.isoformat() if timestamp else None,
        "display_date": format_email_display_date(timestamp) if timestamp else None,
        "labels": json.dumps(labels),
        "record_status": existing["record_status"] if existing else "Draft",
        "email_notes": existing["email_notes"] if existing else None,
        "qc": existing["qc"] if existing else None,
        "is_terminal": existing["is_terminal"] if existing else 0,
        "raw_gmail_data": json.dumps(sanitize_thread_payload(thread), sort_keys=True),
        "notion_last_edited_at": existing["notion_last_edited_at"] if existing else None,
        "notion_synced_at": existing["notion_synced_at"] if existing else None,
        "created_at": existing_created_at,
        "updated_at": iso_now(),
    }
    upsert(
        connection,
        "emails",
        record,
        conflict_columns=("thread_id",),
        update_columns=(
            "notion_page_id",
            "email_subject",
            "raw_subject",
            "mailbox_address",
            "source",
            "intake_type",
            "from_address",
            "direction",
            "message_timestamp",
            "display_date",
            "labels",
            "record_status",
            "email_notes",
            "qc",
            "is_terminal",
            "raw_gmail_data",
            "notion_last_edited_at",
            "notion_synced_at",
            "updated_at",
        ),
    )
    log_sync_event(
        connection,
        operation="gmail_ingest",
        table_name="emails",
        local_record_id=local_id,
        notion_page_id=record["notion_page_id"],
        status="upserted",
        message=f"{classification} thread ingested",
        payload={"thread_id": record["thread_id"], "mailbox": account.address},
    )
    return existing is None


def extract_subject(thread: dict[str, Any]) -> str:
    first_message = thread.get("messages", [{}])[0]
    return extract_header(first_message, "Subject") or "(no subject)"


def extract_sender_email(thread: dict[str, Any]) -> str:
    first_message = thread.get("messages", [{}])[0]
    raw = extract_header(first_message, "From")
    return parseaddr(raw)[1].strip().lower()


def determine_direction(
    sender: str,
    account_address: str,
    known_outbound_emails: tuple[str, ...],
) -> str:
    sender_lower = sender.lower()
    if sender_lower == account_address.lower():
        return "Outbound"
    if sender_lower in {item.lower() for item in known_outbound_emails}:
        return "Outbound"
    return "Inbound"


def extract_header(message: dict[str, Any], header_name: str) -> str:
    payload = message.get("payload") or {}
    for header in payload.get("headers", []):
        if header.get("name", "").lower() == header_name.lower():
            return header.get("value", "")
    return ""


def get_thread_text(thread: dict[str, Any]) -> str:
    chunks: list[str] = []
    for message in thread.get("messages", []):
        payload = message.get("payload") or {}
        chunks.extend(_collect_payload_text(payload))
    return "\n".join(chunk for chunk in chunks if chunk)


def _collect_payload_text(payload: dict[str, Any]) -> list[str]:
    collected: list[str] = []
    body_data = payload.get("body", {}).get("data")
    if body_data:
        collected.append(_decode_body_data(body_data))

    for part in payload.get("parts", []) or []:
        mime_type = (part.get("mimeType") or "").lower()
        if mime_type.startswith("text/"):
            part_data = part.get("body", {}).get("data")
            if part_data:
                collected.append(_decode_body_data(part_data))
        collected.extend(_collect_payload_text(part))
    return collected


def _decode_body_data(data: str) -> str:
    padded = data + "=" * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8", errors="replace")


def sanitize_thread_payload(thread: dict[str, Any]) -> dict[str, Any]:
    sanitized_messages = []
    for message in thread.get("messages", []):
        sanitized_messages.append(
            {
                "id": message.get("id"),
                "threadId": message.get("threadId"),
                "internalDate": message.get("internalDate"),
                "labelIds": message.get("labelIds", []),
                "payload": sanitize_payload_part(message.get("payload") or {}),
            }
        )
    return {
        "id": thread.get("id"),
        "historyId": thread.get("historyId"),
        "snippet": thread.get("snippet"),
        "messages": sanitized_messages,
    }


def sanitize_payload_part(payload: dict[str, Any]) -> dict[str, Any]:
    mime_type = (payload.get("mimeType") or "").lower()
    sanitized = {
        "mimeType": payload.get("mimeType"),
        "filename": payload.get("filename"),
        "headers": [
            header
            for header in payload.get("headers", [])
            if header.get("name") in {"Subject", "From", "To", "Cc", "Bcc", "Date"}
        ],
    }

    body = payload.get("body") or {}
    data = body.get("data")
    attachment_id = body.get("attachmentId")
    if data and mime_type.startswith("text/"):
        sanitized["body"] = {"data": data}
    elif attachment_id:
        sanitized["body"] = {"attachmentId": attachment_id}

    parts = payload.get("parts") or []
    if parts:
        sanitized["parts"] = [sanitize_payload_part(part) for part in parts]
    return sanitized


def parse_gmail_datetime(raw_internal_date: str | None) -> datetime | None:
    if not raw_internal_date:
        return None
    try:
        milliseconds = int(raw_internal_date)
    except ValueError:
        return parse_datetime(raw_internal_date)
    return datetime.fromtimestamp(milliseconds / 1000, tz=EASTERN)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest Gmail threads into the local SQLite cache.")
    parser.add_argument("--config", default=None, help="Optional path to config.yaml")
    args = parser.parse_args()
    summary = run(args.config)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
