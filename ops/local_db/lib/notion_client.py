from __future__ import annotations

import time
from pathlib import Path
from typing import Any

try:
    from notion_client import Client  # type: ignore
except ImportError:  # pragma: no cover - dependency availability depends on local environment
    Client = None


class NotionApiClient:
    def __init__(self, token_path: Path, *, min_interval_seconds: float = 0.35) -> None:
        if Client is None:
            raise RuntimeError("notion-client is required for local-db sync operations.")

        token = token_path.read_text(encoding="utf-8").strip()
        if not token:
            raise RuntimeError(f"Notion token file is empty: {token_path}")
        self._client = Client(auth=token)
        self._min_interval_seconds = min_interval_seconds
        self._last_request_at = 0.0

    def get_database(self, database_id: str) -> dict[str, Any]:
        return self._call(self._client.databases.retrieve, database_id=database_id)

    def query_database(self, database_id: str, **kwargs: Any) -> dict[str, Any]:
        return self._call(self._client.databases.query, database_id=database_id, **kwargs)

    def get_database_records(self, database_id: str, **kwargs: Any) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        cursor = None
        while True:
            payload = dict(kwargs)
            if cursor:
                payload["start_cursor"] = cursor
            page = self.query_database(database_id, **payload)
            results.extend(page.get("results", []))
            if not page.get("has_more"):
                return results
            cursor = page.get("next_cursor")

    def create_page(self, database_id: str, properties: dict[str, Any]) -> dict[str, Any]:
        return self._call(
            self._client.pages.create,
            parent={"database_id": database_id},
            properties=properties,
        )

    def update_page(self, page_id: str, properties: dict[str, Any]) -> dict[str, Any]:
        return self._call(self._client.pages.update, page_id=page_id, properties=properties)

    def get_page(self, page_id: str) -> dict[str, Any]:
        return self._call(self._client.pages.retrieve, page_id=page_id)

    def _call(self, func, **kwargs: Any) -> Any:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self._min_interval_seconds:
            time.sleep(self._min_interval_seconds - elapsed)
        response = func(**kwargs)
        self._last_request_at = time.monotonic()
        return response


def extract_plain_text(property_value: dict[str, Any] | None) -> str:
    if not property_value:
        return ""
    property_type = property_value.get("type")
    if property_type == "title":
        return "".join(item.get("plain_text", "") for item in property_value.get("title", []))
    if property_type == "rich_text":
        return "".join(item.get("plain_text", "") for item in property_value.get("rich_text", []))
    if property_type == "select":
        selected = property_value.get("select")
        return selected.get("name", "") if selected else ""
    if property_type == "multi_select":
        return ", ".join(item.get("name", "") for item in property_value.get("multi_select", []))
    if property_type == "email":
        return property_value.get("email") or ""
    if property_type == "phone_number":
        return property_value.get("phone_number") or ""
    if property_type == "url":
        return property_value.get("url") or ""
    if property_type == "number":
        number = property_value.get("number")
        return "" if number is None else str(number)
    if property_type == "formula":
        formula = property_value.get("formula") or {}
        inner_type = formula.get("type")
        return str(formula.get(inner_type, "")) if inner_type else ""
    return ""


def extract_relation_ids(property_value: dict[str, Any] | None) -> list[str]:
    if not property_value or property_value.get("type") != "relation":
        return []
    return [item["id"] for item in property_value.get("relation", []) if item.get("id")]


def extract_date_range(property_value: dict[str, Any] | None) -> tuple[str | None, str | None]:
    if not property_value or property_value.get("type") != "date":
        return (None, None)
    date_value = property_value.get("date") or {}
    return (date_value.get("start"), date_value.get("end"))


def extract_people_ids(property_value: dict[str, Any] | None) -> list[str]:
    if not property_value or property_value.get("type") != "people":
        return []
    return [item["id"] for item in property_value.get("people", []) if item.get("id")]
