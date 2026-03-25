from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Any

from ops.local_db.lib.db import iso_now
from ops.local_db.lib.notion_client import (
    extract_date_range,
    extract_people_ids,
    extract_plain_text,
    extract_relation_ids,
)


TABLE_ORDER = ("companies", "contacts", "meetings", "emails", "action_items")
TABLE_TO_DATABASE_KEY = {
    "companies": "companies",
    "contacts": "contacts",
    "meetings": "meetings",
    "emails": "emails",
    "action_items": "action_items",
}


def find_existing_local_row(
    connection: sqlite3.Connection,
    table_name: str,
    page: dict[str, Any],
) -> sqlite3.Row | None:
    page_id = page["id"]
    existing = connection.execute(
        f"SELECT * FROM {table_name} WHERE notion_page_id = ?",
        (page_id,),
    ).fetchone()
    if existing:
        return existing

    properties = page["properties"]
    if table_name == "emails":
        thread_id = extract_plain_text(properties.get("Thread ID"))
        if thread_id:
            return connection.execute(
                "SELECT * FROM emails WHERE thread_id = ?",
                (thread_id,),
            ).fetchone()
    if table_name == "meetings":
        calendar_event_id = extract_plain_text(properties.get("Calendar Event ID"))
        if calendar_event_id:
            return connection.execute(
                "SELECT * FROM meetings WHERE calendar_event_id = ?",
                (calendar_event_id,),
            ).fetchone()
    return None


def page_to_local_record(
    table_name: str,
    page: dict[str, Any],
    existing: sqlite3.Row | None = None,
) -> tuple[dict[str, Any], dict[str, list[str] | str | None]]:
    properties = page["properties"]
    now_value = iso_now()
    common = {
        "id": existing["id"] if existing else str(uuid.uuid4()),
        "notion_page_id": page["id"],
        "notion_last_edited_at": page.get("last_edited_time"),
        "notion_synced_at": now_value,
        "created_at": existing["created_at"] if existing else page.get("created_time", now_value),
        "updated_at": page.get("last_edited_time", now_value),
    }

    if table_name == "companies":
        record = {
            **common,
            "company_name": extract_plain_text(properties.get("Company Name")) or "(unnamed company)",
            "company_type": extract_plain_text(properties.get("Company Type")) or None,
            "qc": extract_plain_text(properties.get("QC")) or None,
            "domains": extract_plain_text(properties.get("Domains")) or None,
            "additional_domains": extract_plain_text(properties.get("Additional Domains")) or None,
            "states": extract_plain_text(properties.get("States")) or None,
            "website": extract_plain_text(properties.get("Website")) or None,
            "record_status": extract_plain_text(properties.get("Record Status")) or None,
            "company_notes": extract_plain_text(properties.get("Company Notes")) or None,
        }
        return record, {}

    if table_name == "contacts":
        record = {
            **common,
            "contact_name": extract_plain_text(properties.get("Contact Name")) or "(unnamed contact)",
            "display_name": extract_plain_text(properties.get("Display Name")) or None,
            "qc": extract_plain_text(properties.get("QC")) or None,
            "email": extract_plain_text(properties.get("Email")) or None,
            "secondary_email": extract_plain_text(properties.get("Secondary Email")) or None,
            "tertiary_email": extract_plain_text(properties.get("Tertiary Email")) or None,
            "phone": extract_plain_text(properties.get("Phone")) or None,
            "pronouns": extract_plain_text(properties.get("Pronouns")) or None,
            "nickname": extract_plain_text(properties.get("Nickname")) or None,
            "linkedin": extract_plain_text(properties.get("LinkedIn")) or None,
            "company_id": existing["company_id"] if existing else None,
            "role_title": extract_plain_text(properties.get("Role / Title")) or None,
            "record_status": extract_plain_text(properties.get("Record Status")) or None,
            "contact_notes": extract_plain_text(properties.get("Contact Notes")) or None,
        }
        relations = {"company": _first_relation_id(properties.get("Company"))}
        return record, relations

    if table_name == "meetings":
        start, end = extract_date_range(properties.get("Date"))
        record = {
            **common,
            "meeting_title": extract_plain_text(properties.get("Meeting Title")) or "(untitled meeting)",
            "raw_title": extract_plain_text(properties.get("Meeting Title")) or "(untitled meeting)",
            "calendar_event_id": extract_plain_text(properties.get("Calendar Event ID")) or None,
            "calendar_name": extract_plain_text(properties.get("Calendar Name")) or None,
            "date_start": start,
            "date_end": end,
            "display_date": extract_plain_text(properties.get("Display Date")) or None,
            "location": extract_plain_text(properties.get("Location")) or None,
            "record_status": extract_plain_text(properties.get("Record Status")) or None,
            "qc": extract_plain_text(properties.get("QC")) or None,
            "series_parent_id": existing["series_parent_id"] if existing else None,
            "raw_gcal_data": existing["raw_gcal_data"] if existing else None,
        }
        relations = {
            "contacts": extract_relation_ids(properties.get("Contacts")),
            "series_parent": _first_relation_id(properties.get("Series")),
        }
        return record, relations

    if table_name == "emails":
        start, _ = extract_date_range(properties.get("Date"))
        record = {
            **common,
            "email_subject": extract_plain_text(properties.get("Email Subject")) or "(no subject)",
            "raw_subject": extract_plain_text(properties.get("Email Subject")) or "(no subject)",
            "thread_id": extract_plain_text(properties.get("Thread ID")) or None,
            "mailbox_address": existing["mailbox_address"] if existing else None,
            "source": extract_plain_text(properties.get("Source")) or None,
            "intake_type": existing["intake_type"] if existing else None,
            "from_address": extract_plain_text(properties.get("From")) or None,
            "direction": extract_plain_text(properties.get("Direction")) or None,
            "message_timestamp": start,
            "display_date": extract_plain_text(properties.get("Display Date")) or None,
            "labels": json.dumps(_extract_multi_select_names(properties.get("Labels"))),
            "record_status": extract_plain_text(properties.get("Record Status")) or None,
            "email_notes": extract_plain_text(properties.get("Email Notes")) or None,
            "qc": extract_plain_text(properties.get("QC")) or None,
            "is_terminal": existing["is_terminal"] if existing else 0,
            "raw_gmail_data": existing["raw_gmail_data"] if existing else None,
        }
        relations = {"contacts": extract_relation_ids(properties.get("Contacts"))}
        return record, relations

    if table_name == "action_items":
        start, end = extract_date_range(properties.get("Due Date"))
        record = {
            **common,
            "task_name": extract_plain_text(properties.get("Task Name")) or "(untitled action item)",
            "type": extract_plain_text(properties.get("Type")) or None,
            "status": extract_plain_text(properties.get("Status")) or None,
            "priority": extract_plain_text(properties.get("Priority")) or None,
            "record_status": extract_plain_text(properties.get("Record Status")) or None,
            "task_notes": extract_plain_text(properties.get("Task Notes")) or None,
            "due_date_start": start,
            "due_date_end": end,
            "created_date": extract_plain_text(properties.get("Created Date")) or None,
            "contact_id": existing["contact_id"] if existing else None,
            "company_id": existing["company_id"] if existing else None,
            "assignee_ids": json.dumps(extract_people_ids(properties.get("Assignee"))),
            "source_meeting_id": existing["source_meeting_id"] if existing else None,
            "source_email_id": existing["source_email_id"] if existing else None,
            "attach_files": extract_plain_text(properties.get("Attach File")) or None,
            "qc": extract_plain_text(properties.get("QC")) or None,
        }
        relations = {
            "contact": _first_relation_id(properties.get("Contact")),
            "company": _first_relation_id(properties.get("Company")),
            "source_meeting": _first_relation_id(properties.get("Source Meeting")),
            "source_email": _first_relation_id(properties.get("Source Email")),
        }
        return record, relations

    raise ValueError(f"Unsupported table for mapping: {table_name}")


def apply_relation_resolution(
    connection: sqlite3.Connection,
    table_name: str,
    local_id: str,
    relations: dict[str, list[str] | str | None],
) -> None:
    now_value = iso_now()
    if table_name == "contacts":
        company_notion_id = relations.get("company")
        company_id = resolve_local_id(connection, "companies", company_notion_id if isinstance(company_notion_id, str) else None)
        connection.execute(
            "UPDATE contacts SET company_id = ?, updated_at = ? WHERE id = ?",
            (company_id, now_value, local_id),
        )
    elif table_name == "meetings":
        _replace_junction_rows(
            connection,
            "meeting_contacts",
            "meeting_id",
            local_id,
            "contact_id",
            resolve_local_ids(connection, "contacts", relations.get("contacts") or []),
        )
        series_notion_id = relations.get("series_parent")
        series_id = resolve_local_id(connection, "meetings", series_notion_id if isinstance(series_notion_id, str) else None)
        connection.execute(
            "UPDATE meetings SET series_parent_id = ?, updated_at = ? WHERE id = ?",
            (series_id, now_value, local_id),
        )
    elif table_name == "emails":
        _replace_junction_rows(
            connection,
            "email_contacts",
            "email_id",
            local_id,
            "contact_id",
            resolve_local_ids(connection, "contacts", relations.get("contacts") or []),
        )
    elif table_name == "action_items":
        connection.execute(
            """
            UPDATE action_items
            SET contact_id = ?, company_id = ?, source_meeting_id = ?, source_email_id = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                resolve_local_id(connection, "contacts", relations.get("contact") if isinstance(relations.get("contact"), str) else None),
                resolve_local_id(connection, "companies", relations.get("company") if isinstance(relations.get("company"), str) else None),
                resolve_local_id(connection, "meetings", relations.get("source_meeting") if isinstance(relations.get("source_meeting"), str) else None),
                resolve_local_id(connection, "emails", relations.get("source_email") if isinstance(relations.get("source_email"), str) else None),
                now_value,
                local_id,
            ),
        )
    connection.commit()


def build_notion_properties(
    table_name: str,
    row: sqlite3.Row,
    database_schema: dict[str, Any],
    connection: sqlite3.Connection,
) -> dict[str, Any]:
    properties = database_schema["properties"]
    payload: dict[str, Any] = {}

    if table_name == "companies":
        _assign_property(payload, properties, "Company Name", row["company_name"])
        _assign_property(payload, properties, "Company Type", row["company_type"])
        _assign_property(payload, properties, "Domains", row["domains"])
        _assign_property(payload, properties, "Additional Domains", row["additional_domains"])
        _assign_property(payload, properties, "States", row["states"])
        _assign_property(payload, properties, "Website", row["website"])
        _assign_property(payload, properties, "Record Status", row["record_status"])
        _assign_property(payload, properties, "Company Notes", row["company_notes"])
        return payload

    if table_name == "contacts":
        _assign_property(payload, properties, "Contact Name", row["contact_name"])
        _assign_property(payload, properties, "Email", row["email"])
        _assign_property(payload, properties, "Secondary Email", row["secondary_email"])
        _assign_property(payload, properties, "Tertiary Email", row["tertiary_email"])
        _assign_property(payload, properties, "Phone", row["phone"])
        _assign_property(payload, properties, "Pronouns", row["pronouns"])
        _assign_property(payload, properties, "Nickname", row["nickname"])
        _assign_property(payload, properties, "LinkedIn", row["linkedin"])
        _assign_property(payload, properties, "Role / Title", row["role_title"])
        _assign_property(payload, properties, "Record Status", row["record_status"])
        _assign_property(payload, properties, "Contact Notes", row["contact_notes"])
        _assign_property(
            payload,
            properties,
            "Company",
            _resolve_related_notion_ids(connection, "companies", [row["company_id"]] if row["company_id"] else []),
        )
        return payload

    if table_name == "meetings":
        _assign_property(payload, properties, "Meeting Title", row["meeting_title"])
        _assign_property(payload, properties, "Calendar Event ID", row["calendar_event_id"])
        _assign_property(payload, properties, "Calendar Name", row["calendar_name"])
        _assign_property(payload, properties, "Date", {"start": row["date_start"], "end": row["date_end"]})
        _assign_property(payload, properties, "Display Date", row["display_date"])
        _assign_property(payload, properties, "Location", row["location"])
        _assign_property(payload, properties, "Record Status", row["record_status"])
        _assign_property(
            payload,
            properties,
            "Contacts",
            _resolve_related_notion_ids(connection, "contacts", _fetch_related_ids(connection, "meeting_contacts", "meeting_id", row["id"], "contact_id")),
        )
        _assign_property(
            payload,
            properties,
            "Series",
            _resolve_related_notion_ids(connection, "meetings", [row["series_parent_id"]] if row["series_parent_id"] else []),
        )
        return payload

    if table_name == "emails":
        _assign_property(payload, properties, "Email Subject", row["email_subject"])
        _assign_property(payload, properties, "Thread ID", row["thread_id"])
        _assign_property(payload, properties, "From", row["from_address"])
        _assign_property(payload, properties, "Source", row["source"])
        _assign_property(payload, properties, "Date", {"start": row["message_timestamp"], "end": None})
        _assign_property(payload, properties, "Display Date", row["display_date"])
        _assign_property(payload, properties, "Labels", _decode_json_list(row["labels"]))
        _assign_property(payload, properties, "Record Status", row["record_status"])
        _assign_property(payload, properties, "Email Notes", row["email_notes"])
        _assign_property(
            payload,
            properties,
            "Contacts",
            _resolve_related_notion_ids(connection, "contacts", _fetch_related_ids(connection, "email_contacts", "email_id", row["id"], "contact_id")),
        )
        return payload

    if table_name == "action_items":
        _assign_property(payload, properties, "Task Name", row["task_name"])
        _assign_property(payload, properties, "Status", row["status"])
        _assign_property(payload, properties, "Priority", row["priority"])
        _assign_property(payload, properties, "Record Status", row["record_status"])
        _assign_property(payload, properties, "Task Notes", row["task_notes"])
        _assign_property(payload, properties, "Due Date", {"start": row["due_date_start"], "end": row["due_date_end"]})
        _assign_property(payload, properties, "Assignee", _decode_json_list(row["assignee_ids"]))
        _assign_property(
            payload,
            properties,
            "Contact",
            _resolve_related_notion_ids(connection, "contacts", [row["contact_id"]] if row["contact_id"] else []),
        )
        _assign_property(
            payload,
            properties,
            "Company",
            _resolve_related_notion_ids(connection, "companies", [row["company_id"]] if row["company_id"] else []),
        )
        _assign_property(
            payload,
            properties,
            "Source Meeting",
            _resolve_related_notion_ids(connection, "meetings", [row["source_meeting_id"]] if row["source_meeting_id"] else []),
        )
        _assign_property(
            payload,
            properties,
            "Source Email",
            _resolve_related_notion_ids(connection, "emails", [row["source_email_id"]] if row["source_email_id"] else []),
        )
        return payload

    raise ValueError(f"Unsupported table for Notion serialization: {table_name}")


def _assign_property(payload: dict[str, Any], schema: dict[str, Any], property_name: str, value: Any) -> None:
    property_schema = schema.get(property_name)
    if not property_schema:
        return
    property_type = property_schema["type"]

    if property_type == "title":
        payload[property_name] = {"title": _rich_text_array(value)}
        return
    if property_type == "rich_text":
        payload[property_name] = {"rich_text": _rich_text_array(value)}
        return
    if property_type == "select":
        if not value:
            payload[property_name] = {"select": None}
            return
        option_names = {
            option.get("name")
            for option in property_schema.get("select", {}).get("options", [])
            if option.get("name")
        }
        if option_names and value not in option_names:
            return
        payload[property_name] = {"select": {"name": value}}
        return
    if property_type == "multi_select":
        names = value if isinstance(value, list) else _decode_json_list(value)
        payload[property_name] = {"multi_select": [{"name": item} for item in names]}
        return
    if property_type == "relation":
        ids = value if isinstance(value, list) else []
        payload[property_name] = {"relation": [{"id": item} for item in ids]}
        return
    if property_type == "date":
        payload[property_name] = {"date": value if value and value.get("start") else None}
        return
    if property_type == "email":
        payload[property_name] = {"email": value or None}
        return
    if property_type == "phone_number":
        payload[property_name] = {"phone_number": value or None}
        return
    if property_type == "url":
        payload[property_name] = {"url": value or None}
        return
    if property_type == "people":
        ids = value if isinstance(value, list) else _decode_json_list(value)
        payload[property_name] = {"people": [{"id": item} for item in ids]}
        return
    if property_type == "checkbox":
        payload[property_name] = {"checkbox": bool(value)}
        return
    if property_type == "number":
        payload[property_name] = {"number": value if value not in {"", None} else None}
        return


def resolve_local_id(connection: sqlite3.Connection, table_name: str, notion_page_id: str | None) -> str | None:
    if not notion_page_id:
        return None
    row = connection.execute(
        f"SELECT id FROM {table_name} WHERE notion_page_id = ?",
        (notion_page_id,),
    ).fetchone()
    return row["id"] if row else None


def resolve_local_ids(connection: sqlite3.Connection, table_name: str, notion_page_ids: list[str]) -> list[str]:
    ids: list[str] = []
    for notion_page_id in notion_page_ids:
        local_id = resolve_local_id(connection, table_name, notion_page_id)
        if local_id:
            ids.append(local_id)
    return ids


def _resolve_related_notion_ids(
    connection: sqlite3.Connection,
    table_name: str,
    local_ids: list[str],
) -> list[str]:
    notion_ids: list[str] = []
    for local_id in local_ids:
        row = connection.execute(
            f"SELECT notion_page_id FROM {table_name} WHERE id = ?",
            (local_id,),
        ).fetchone()
        if row and row["notion_page_id"]:
            notion_ids.append(row["notion_page_id"])
    return notion_ids


def _replace_junction_rows(
    connection: sqlite3.Connection,
    table_name: str,
    self_column: str,
    self_id: str,
    related_column: str,
    related_ids: list[str],
) -> None:
    now_value = iso_now()
    connection.execute(f"DELETE FROM {table_name} WHERE {self_column} = ?", (self_id,))
    for related_id in related_ids:
        connection.execute(
            f"""
            INSERT INTO {table_name} ({self_column}, {related_column}, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (self_id, related_id, now_value, now_value),
        )


def _fetch_related_ids(
    connection: sqlite3.Connection,
    table_name: str,
    self_column: str,
    self_id: str,
    related_column: str,
) -> list[str]:
    rows = connection.execute(
        f"SELECT {related_column} FROM {table_name} WHERE {self_column} = ?",
        (self_id,),
    ).fetchall()
    return [row[related_column] for row in rows]


def _rich_text_array(value: Any) -> list[dict[str, Any]]:
    if not value:
        return []
    text = str(value)
    if not text:
        return []
    chunks = [text[index : index + 1800] for index in range(0, len(text), 1800)]
    return [{"type": "text", "text": {"content": chunk}} for chunk in chunks]


def _decode_json_list(value: Any) -> list[str]:
    if value in {None, ""}:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return [item.strip() for item in str(value).split(",") if item.strip()]
    if isinstance(parsed, list):
        return [str(item) for item in parsed if str(item)]
    return []


def _extract_multi_select_names(property_value: dict[str, Any] | None) -> list[str]:
    if not property_value or property_value.get("type") != "multi_select":
        return []
    return [item.get("name", "") for item in property_value.get("multi_select", []) if item.get("name")]


def _first_relation_id(property_value: dict[str, Any] | None) -> str | None:
    relation_ids = extract_relation_ids(property_value)
    return relation_ids[0] if relation_ids else None
