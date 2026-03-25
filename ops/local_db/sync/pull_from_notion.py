from __future__ import annotations

import argparse
import json
import sqlite3
from typing import Any

from ops.local_db.lib.db import compute_lookback, init_db, iso_now, log_sync_event, parse_datetime, set_agent_state, upsert
from ops.local_db.lib.config import load_config
from ops.local_db.lib.notion_client import NotionApiClient
from ops.local_db.sync.mappings import (
    TABLE_ORDER,
    TABLE_TO_DATABASE_KEY,
    apply_relation_resolution,
    find_existing_local_row,
    page_to_local_record,
)


REMOTE_WINS_FIELDS = {
    "contacts": {"record_status", "contact_notes"},
    "companies": {"record_status", "company_notes"},
    "emails": {"record_status", "email_notes"},
    "action_items": {"record_status", "task_notes"},
    "meetings": {"record_status"},
}
LOCAL_ONLY_FIELDS = {"raw_gmail_data", "raw_gcal_data", "mailbox_address", "intake_type", "is_terminal"}


def run(config_path: str | None = None) -> dict[str, int]:
    config = load_config(config_path)
    connection = init_db(config=config)
    client = NotionApiClient(config.notion.token_path)
    counts: dict[str, int] = {}

    try:
        for table_name in TABLE_ORDER:
            agent_name = f"pull_from_notion:{table_name}"
            lookback = compute_lookback(connection, agent_name)
            database_id = config.notion.databases[TABLE_TO_DATABASE_KEY[table_name]]
            pages = client.get_database_records(
                database_id,
                filter={
                    "timestamp": "last_edited_time",
                    "last_edited_time": {"on_or_after": lookback.isoformat()},
                },
            )
            counts[table_name] = 0
            for page in pages:
                existing = find_existing_local_row(connection, table_name, page)
                remote_record, remote_relations = page_to_local_record(table_name, page, existing)
                merged_record = merge_record(table_name, existing, remote_record)
                upsert(
                    connection,
                    table_name,
                    merged_record,
                    conflict_columns=("id",) if existing else ("notion_page_id",),
                )
                merged_relations = merge_relations(connection, table_name, merged_record["id"], remote_relations)
                if merged_relations:
                    apply_relation_resolution(connection, table_name, merged_record["id"], merged_relations)
                counts[table_name] += 1
                log_sync_event(
                    connection,
                    operation="pull_from_notion",
                    table_name=table_name,
                    local_record_id=merged_record["id"],
                    notion_page_id=merged_record["notion_page_id"],
                    status="ok",
                    message="Pulled latest Notion changes into SQLite.",
                )

            now_value = iso_now()
            set_agent_state(
                connection,
                agent_name,
                last_run=now_value,
                last_successful_run=now_value,
                state={"count": counts[table_name]},
            )
        return counts
    finally:
        connection.close()


def merge_record(
    table_name: str,
    existing: sqlite3.Row | None,
    remote_record: dict[str, Any],
) -> dict[str, Any]:
    if existing is None:
        return remote_record

    merged = dict(existing)
    remote_edit = parse_datetime(remote_record.get("notion_last_edited_at") or remote_record.get("updated_at"))
    local_update = parse_datetime(existing["updated_at"])
    remote_is_newer = bool(remote_edit and (not local_update or remote_edit >= local_update))

    for key, value in remote_record.items():
        if key in {"id", "created_at"}:
            continue
        if key in LOCAL_ONLY_FIELDS:
            continue
        if key in {"notion_page_id", "notion_last_edited_at"}:
            merged[key] = value
            continue
        if key == "notion_synced_at":
            merged[key] = iso_now()
            continue
        if key in REMOTE_WINS_FIELDS.get(table_name, set()):
            merged[key] = value
            continue
        if merged.get(key) in {None, ""}:
            merged[key] = value
            continue
        if remote_is_newer:
            merged[key] = value

    merged["updated_at"] = (
        remote_record.get("notion_last_edited_at")
        if remote_is_newer and remote_record.get("notion_last_edited_at")
        else existing["updated_at"]
    )
    merged["notion_synced_at"] = iso_now()
    merged["created_at"] = existing["created_at"]
    merged["id"] = existing["id"]
    return merged


def merge_relations(
    connection,
    table_name: str,
    local_id: str,
    remote_relations: dict[str, list[str] | str | None],
) -> dict[str, list[str] | str | None]:
    if table_name == "emails":
        current = set(_current_related_notion_ids(connection, "email_contacts", "email_id", local_id, "contact_id", "contacts"))
        remote = set(remote_relations.get("contacts") or [])
        return {"contacts": sorted(current | remote)}

    if table_name == "meetings":
        current = set(_current_related_notion_ids(connection, "meeting_contacts", "meeting_id", local_id, "contact_id", "contacts"))
        remote = set(remote_relations.get("contacts") or [])
        series_remote = remote_relations.get("series_parent")
        return {
            "contacts": sorted(current | remote),
            "series_parent": series_remote or _current_single_relation_notion_id(connection, "meetings", local_id, "series_parent_id"),
        }

    if table_name == "contacts":
        return {
            "company": remote_relations.get("company")
            or _current_single_relation_notion_id(connection, "companies", local_id, "company_id", table_name="contacts"),
        }

    if table_name == "action_items":
        return {
            "contact": remote_relations.get("contact")
            or _current_single_relation_notion_id(connection, "contacts", local_id, "contact_id", table_name="action_items"),
            "company": remote_relations.get("company")
            or _current_single_relation_notion_id(connection, "companies", local_id, "company_id", table_name="action_items"),
            "source_meeting": remote_relations.get("source_meeting")
            or _current_single_relation_notion_id(connection, "meetings", local_id, "source_meeting_id", table_name="action_items"),
            "source_email": remote_relations.get("source_email")
            or _current_single_relation_notion_id(connection, "emails", local_id, "source_email_id", table_name="action_items"),
        }

    return remote_relations


def _current_related_notion_ids(
    connection,
    junction_table: str,
    self_column: str,
    self_id: str,
    related_column: str,
    target_table: str,
) -> list[str]:
    rows = connection.execute(
        f"""
        SELECT target.notion_page_id
        FROM {junction_table} junction
        JOIN {target_table} target ON target.id = junction.{related_column}
        WHERE junction.{self_column} = ?
          AND target.notion_page_id IS NOT NULL
        """,
        (self_id,),
    ).fetchall()
    return [row["notion_page_id"] for row in rows]


def _current_single_relation_notion_id(
    connection,
    target_table: str,
    self_id: str,
    local_column: str,
    *,
    table_name: str = "meetings",
) -> str | None:
    row = connection.execute(
        f"""
        SELECT target.notion_page_id
        FROM {table_name} source
        LEFT JOIN {target_table} target ON target.id = source.{local_column}
        WHERE source.id = ?
        """,
        (self_id,),
    ).fetchone()
    return row["notion_page_id"] if row and row["notion_page_id"] else None


def main() -> None:
    parser = argparse.ArgumentParser(description="Pull review-side Notion edits into the local SQLite cache.")
    parser.add_argument("--config", default=None, help="Optional path to config.yaml")
    args = parser.parse_args()
    print(json.dumps(run(args.config), indent=2))


if __name__ == "__main__":
    main()
