from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime
from typing import Any

from ops.local_db.lib.config import CalendarConfig, load_config
from ops.local_db.lib.db import (
    compute_lookback,
    format_meeting_display_date,
    init_db,
    iso_now,
    log_sync_event,
    normalize_title,
    parse_datetime,
    set_agent_state,
    upsert,
)
from ops.local_db.lib.gmail_auth import build_calendar_service


def run(config_path: str | None = None) -> dict[str, dict[str, int]]:
    config = load_config(config_path)
    connection = init_db(config=config)
    try:
        summary: dict[str, dict[str, int]] = {}
        for calendar in config.calendars:
            summary[f"{calendar.account}:{calendar.calendar_id}"] = ingest_calendar(
                connection,
                calendar,
                config,
            )
        return summary
    finally:
        connection.close()


def ingest_calendar(connection, calendar: CalendarConfig, config) -> dict[str, int]:
    service = build_calendar_service(calendar.account, config.google)
    agent_name = f"gcal_ingest:{calendar.account}:{calendar.calendar_id}"
    lookback = compute_lookback(connection, agent_name)

    counters = {"seen": 0, "inserted": 0, "updated": 0, "skipped": 0}
    page_token = None
    while True:
        response = (
            service.events()
            .list(
                calendarId=calendar.calendar_id,
                timeMin=lookback.isoformat(),
                singleEvents=True,
                showDeleted=False,
                orderBy="updated",
                pageToken=page_token,
            )
            .execute()
        )
        events = response.get("items", [])
        for event in events:
            counters["seen"] += 1
            if should_skip_event(event, calendar.account):
                counters["skipped"] += 1
                log_sync_event(
                    connection,
                    operation="gcal_ingest",
                    table_name="meetings",
                    status="skipped",
                    message="Filtered event out of ingest scope.",
                    payload={"event_id": event.get("id"), "calendar": calendar.calendar_name},
                )
                continue

            existing = connection.execute(
                "SELECT * FROM meetings WHERE calendar_event_id = ?",
                (event.get("id"),),
            ).fetchone()
            created = upsert_event(connection, calendar, event, existing)
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


def should_skip_event(event: dict[str, Any], account_email: str) -> bool:
    if event.get("status") == "cancelled":
        return True
    if "dateTime" not in (event.get("start") or {}):
        return True

    attendees = event.get("attendees", [])
    if not attendees:
        return False
    for attendee in attendees:
        email = (attendee.get("email") or "").lower()
        if email == account_email.lower() and attendee.get("responseStatus") == "declined":
            return True
    return False


def upsert_event(connection, calendar: CalendarConfig, event: dict[str, Any], existing) -> bool:
    start = parse_datetime((event.get("start") or {}).get("dateTime"))
    end = parse_datetime((event.get("end") or {}).get("dateTime"))
    existing_created_at = existing["created_at"] if existing else iso_now()
    raw_title = event.get("summary") or "(untitled meeting)"
    local_id = existing["id"] if existing else str(uuid.uuid4())

    record = {
        "id": local_id,
        "notion_page_id": existing["notion_page_id"] if existing else None,
        "meeting_title": normalize_title(raw_title),
        "raw_title": raw_title,
        "calendar_event_id": event.get("id"),
        "calendar_name": calendar.calendar_name,
        "date_start": start.isoformat() if start else None,
        "date_end": end.isoformat() if end else None,
        "display_date": format_meeting_display_date(start, end) if start else None,
        "location": event.get("location"),
        "record_status": existing["record_status"] if existing else "Draft",
        "qc": existing["qc"] if existing else None,
        "series_parent_id": existing["series_parent_id"] if existing else None,
        "raw_gcal_data": json.dumps(event, sort_keys=True),
        "notion_last_edited_at": existing["notion_last_edited_at"] if existing else None,
        "notion_synced_at": existing["notion_synced_at"] if existing else None,
        "created_at": existing_created_at,
        "updated_at": iso_now(),
    }
    upsert(
        connection,
        "meetings",
        record,
        conflict_columns=("calendar_event_id",),
        update_columns=(
            "notion_page_id",
            "meeting_title",
            "raw_title",
            "calendar_name",
            "date_start",
            "date_end",
            "display_date",
            "location",
            "record_status",
            "qc",
            "series_parent_id",
            "raw_gcal_data",
            "notion_last_edited_at",
            "notion_synced_at",
            "updated_at",
        ),
    )
    log_sync_event(
        connection,
        operation="gcal_ingest",
        table_name="meetings",
        local_record_id=local_id,
        notion_page_id=record["notion_page_id"],
        status="upserted",
        message="Calendar event ingested.",
        payload={"event_id": record["calendar_event_id"], "calendar": calendar.calendar_name},
    )
    return existing is None


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest Google Calendar events into the local SQLite cache.")
    parser.add_argument("--config", default=None, help="Optional path to config.yaml")
    args = parser.parse_args()
    summary = run(args.config)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
