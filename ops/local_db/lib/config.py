from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ops.local_db.lib.paths import DEFAULT_CONFIG_PATH, REPO_ROOT

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover - exercised only when PyYAML is missing
    yaml = None


@dataclass(frozen=True)
class DatabaseConfig:
    path: Path


@dataclass(frozen=True)
class GoogleConfig:
    credentials_path: Path
    token_path: Path
    scopes: tuple[str, ...]


@dataclass(frozen=True)
class NotionConfig:
    token_path: Path
    databases: dict[str, str]


@dataclass(frozen=True)
class GmailRoutingLabel:
    label: str
    type: str


@dataclass(frozen=True)
class GmailAccountConfig:
    address: str
    source_label: str
    routing_labels: tuple[GmailRoutingLabel, ...]
    ignore_labels: tuple[str, ...]


@dataclass(frozen=True)
class CalendarConfig:
    account: str
    calendar_id: str
    calendar_name: str
    default_company: str


@dataclass(frozen=True)
class AdamConfig:
    exclude_emails: tuple[str, ...]
    generic_domains: tuple[str, ...]
    notion_user_id: str


@dataclass(frozen=True)
class AppConfig:
    database: DatabaseConfig
    google: GoogleConfig
    notion: NotionConfig
    gmail_accounts: tuple[GmailAccountConfig, ...]
    calendars: tuple[CalendarConfig, ...]
    adam: AdamConfig
    source_path: Path


def load_config(path: Path | None = None) -> AppConfig:
    config_path = Path(path or DEFAULT_CONFIG_PATH)
    if not config_path.is_absolute():
        config_path = (REPO_ROOT / config_path).resolve()

    if yaml is None:
        raise RuntimeError(
            "PyYAML is required to load ops/local_db/config.yaml. Install `pyyaml` first."
        )

    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise RuntimeError(f"Config file did not parse into a mapping: {config_path}")

    database = raw["database"]
    google = raw["google"]
    notion = raw["notion"]
    adam = raw["adam"]

    return AppConfig(
        database=DatabaseConfig(path=_resolve_path(database["path"])),
        google=GoogleConfig(
            credentials_path=_resolve_path(google["credentials_path"]),
            token_path=_resolve_path(google["token_path"]),
            scopes=tuple(google["scopes"]),
        ),
        notion=NotionConfig(
            token_path=_resolve_path(notion["token_path"]),
            databases=dict(notion["databases"]),
        ),
        gmail_accounts=tuple(_parse_gmail_account(item) for item in raw["gmail"]["accounts"]),
        calendars=tuple(
            CalendarConfig(
                account=item["account"],
                calendar_id=item["calendar_id"],
                calendar_name=item["calendar_name"],
                default_company=item["default_company"],
            )
            for item in raw["calendars"]
        ),
        adam=AdamConfig(
            exclude_emails=tuple(value.strip().lower() for value in adam["exclude_emails"]),
            generic_domains=tuple(value.strip().lower() for value in adam["generic_domains"]),
            notion_user_id=adam["notion_user_id"],
        ),
        source_path=config_path,
    )


def sanitize_filename(value: str) -> str:
    cleaned = []
    for char in value:
        if char.isalnum():
            cleaned.append(char)
        else:
            cleaned.append("_")
    return "".join(cleaned).strip("_").lower()


def split_csv_text(value: str | None) -> list[str]:
    if not value:
        return []
    normalized = value.replace("\n", ",")
    return [item.strip() for item in normalized.split(",") if item.strip()]


def _parse_gmail_account(item: dict[str, Any]) -> GmailAccountConfig:
    return GmailAccountConfig(
        address=item["address"].strip().lower(),
        source_label=item["source_label"],
        routing_labels=tuple(
            GmailRoutingLabel(label=entry["label"], type=entry["type"])
            for entry in item.get("routing_labels", [])
        ),
        ignore_labels=tuple(item.get("ignore_labels", [])),
    )


def _resolve_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()
