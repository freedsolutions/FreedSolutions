from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ops.local_db.lib.config import AppConfig, load_config
from ops.local_db.lib.paths import DEFAULT_SCHEMA_PATH, REPO_ROOT


try:
    EASTERN = ZoneInfo("America/New_York")
    DISPLAY_TZ_LABEL = "ET"
except ZoneInfoNotFoundError:  # pragma: no cover - depends on local tzdata availability
    EASTERN = datetime.now().astimezone().tzinfo or timezone.utc
    fallback_label = EASTERN.tzname(None) or "UTC"
    DISPLAY_TZ_LABEL = "ET" if "Eastern" in fallback_label else fallback_label


def now_eastern() -> datetime:
    return datetime.now(EASTERN)


def iso_now() -> str:
    return now_eastern().replace(microsecond=0).isoformat()


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=EASTERN)
    return parsed.astimezone(EASTERN)


def normalize_title(title: str | None) -> str:
    if not title:
        return ""
    normalized = title.strip()
    prefixes = ("fw:", "fwd:", "re:")
    changed = True
    while changed:
        changed = False
        lower = normalized.lower()
        for prefix in prefixes:
            if lower.startswith(prefix):
                normalized = normalized[len(prefix) :].lstrip()
                changed = True
                break
    return normalized.strip()


def format_email_display_date(value: datetime) -> str:
    local = value.astimezone(EASTERN)
    rendered = local.strftime(f"%b %d, %Y %I:%M %p {DISPLAY_TZ_LABEL}")
    return rendered.replace(" 0", " ")


def format_meeting_display_date(start: datetime, end: datetime | None) -> str:
    local_start = start.astimezone(EASTERN)
    if end is None:
        return format_email_display_date(local_start)
    local_end = end.astimezone(EASTERN)
    day = local_start.strftime("%b %d, %Y").replace(" 0", " ")
    time_range = (
        f"{local_start.strftime('%I:%M').lstrip('0')} {local_start.strftime('%p')}"
        f"-{local_end.strftime('%I:%M').lstrip('0')} {local_end.strftime('%p')} {DISPLAY_TZ_LABEL}"
    )
    return f"{day} {time_range}"


def get_connection(
    db_path: Path | None = None,
    config: AppConfig | None = None,
    *,
    read_only: bool = False,
) -> sqlite3.Connection:
    if db_path is not None:
        resolved_path = Path(db_path)
    else:
        resolved_config = config or load_config()
        resolved_path = Path(resolved_config.database.path)
    if not read_only:
        resolved_path.parent.mkdir(parents=True, exist_ok=True)

    if read_only:
        uri = f"file:{resolved_path.as_posix()}?mode=ro"
        connection = sqlite3.connect(uri, uri=True)
    else:
        connection = sqlite3.connect(resolved_path)

    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    if not read_only:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
    return connection


def init_db(
    connection: sqlite3.Connection | None = None,
    *,
    db_path: Path | None = None,
    schema_path: Path | None = None,
    config: AppConfig | None = None,
) -> sqlite3.Connection:
    owns_connection = connection is None
    conn = connection or get_connection(db_path=db_path, config=config)
    resolved_schema = Path(schema_path or DEFAULT_SCHEMA_PATH)
    if not resolved_schema.is_absolute():
        resolved_schema = (REPO_ROOT / resolved_schema).resolve()
    conn.executescript(resolved_schema.read_text(encoding="utf-8"))
    conn.commit()
    if owns_connection:
        return conn
    return conn


def query(
    connection: sqlite3.Connection,
    sql: str,
    params: Sequence[Any] | None = None,
) -> list[sqlite3.Row]:
    return list(connection.execute(sql, params or ()))


def execute(
    connection: sqlite3.Connection,
    sql: str,
    params: Sequence[Any] | None = None,
) -> sqlite3.Cursor:
    cursor = connection.execute(sql, params or ())
    connection.commit()
    return cursor


def executemany(
    connection: sqlite3.Connection,
    sql: str,
    params: Iterable[Sequence[Any]],
) -> None:
    connection.executemany(sql, params)
    connection.commit()


def ensure_record_id(record: dict[str, Any]) -> dict[str, Any]:
    if record.get("id"):
        return record
    clone = dict(record)
    clone["id"] = str(uuid.uuid4())
    return clone


def upsert(
    connection: sqlite3.Connection,
    table: str,
    record: dict[str, Any],
    *,
    conflict_columns: Sequence[str],
    update_columns: Sequence[str] | None = None,
) -> None:
    payload = ensure_record_id(record)
    columns = list(payload.keys())
    updates = list(update_columns or [column for column in columns if column not in {"id", *conflict_columns}])
    assignments = ", ".join(f"{column}=excluded.{column}" for column in updates)
    placeholders = ", ".join("?" for _ in columns)
    sql = (
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders}) "
        f"ON CONFLICT ({', '.join(conflict_columns)}) DO UPDATE SET {assignments}"
    )
    values = [payload[column] for column in columns]
    connection.execute(sql, values)
    connection.commit()


def fetch_one(
    connection: sqlite3.Connection,
    sql: str,
    params: Sequence[Any] | None = None,
) -> sqlite3.Row | None:
    return connection.execute(sql, params or ()).fetchone()


def get_agent_state(connection: sqlite3.Connection, agent_name: str) -> sqlite3.Row | None:
    return fetch_one(connection, "SELECT * FROM agent_config WHERE agent_name = ?", (agent_name,))


def set_agent_state(
    connection: sqlite3.Connection,
    agent_name: str,
    *,
    last_run: str | None = None,
    last_successful_run: str | None = None,
    state: dict[str, Any] | None = None,
) -> None:
    existing = get_agent_state(connection, agent_name)
    payload = {
        "agent_name": agent_name,
        "last_run": last_run if last_run is not None else (existing["last_run"] if existing else None),
        "last_successful_run": (
            last_successful_run
            if last_successful_run is not None
            else (existing["last_successful_run"] if existing else None)
        ),
        "state_json": (
            json.dumps(state, sort_keys=True)
            if state is not None
            else (existing["state_json"] if existing else "{}")
        ),
        "updated_at": iso_now(),
    }
    upsert(
        connection,
        "agent_config",
        payload,
        conflict_columns=("agent_name",),
        update_columns=("last_run", "last_successful_run", "state_json", "updated_at"),
    )


def compute_lookback(
    connection: sqlite3.Connection,
    agent_name: str,
    *,
    fallback_days: int = 7,
) -> datetime:
    state = get_agent_state(connection, agent_name)
    candidate = None
    if state:
        candidate = parse_datetime(state["last_successful_run"] or state["last_run"])
    if candidate is None:
        return now_eastern() - timedelta(days=fallback_days)
    oldest_allowed = now_eastern() - timedelta(days=fallback_days)
    return candidate if candidate >= oldest_allowed else oldest_allowed


def log_sync_event(
    connection: sqlite3.Connection,
    *,
    operation: str,
    table_name: str,
    status: str,
    local_record_id: str | None = None,
    notion_page_id: str | None = None,
    message: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    connection.execute(
        """
        INSERT INTO sync_log (
            operation,
            table_name,
            local_record_id,
            notion_page_id,
            status,
            message,
            payload,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            operation,
            table_name,
            local_record_id,
            notion_page_id,
            status,
            message,
            json.dumps(payload, sort_keys=True) if payload is not None else None,
            iso_now(),
        ),
    )
    connection.commit()
