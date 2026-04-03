"""Notion API helpers using stdlib only (no notion-client dependency).

Shared by post_email_sweep.py, gmail_filter_manager.py, email_subject_audit.py.
Uses urllib.request to avoid external dependencies beyond PyYAML + Google libs.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

NOTION_API_VERSION = "2022-06-28"
NOTION_BASE = "https://api.notion.com/v1"


def load_notion_token(token_path: Path) -> str:
    """Read Notion integration token from file."""
    if not token_path.exists():
        print(f"ERROR: Notion token file not found at {token_path}", file=sys.stderr)
        sys.exit(1)
    token = token_path.read_text(encoding="utf-8").strip()
    if not token:
        print(f"ERROR: Notion token file is empty: {token_path}", file=sys.stderr)
        sys.exit(1)
    return token


def notion_request(
    path: str,
    token: str,
    body: dict | None = None,
    method: str | None = None,
    *,
    retries: int = 2,
    retry_delay: float = 1.0,
) -> dict:
    """Make a Notion API request with optional retry on rate-limit (429).

    Parameters
    ----------
    path : str
        API path (e.g. "/databases/{id}/query").
    token : str
        Notion integration token.
    body : dict | None
        JSON body for POST/PATCH requests.
    method : str | None
        HTTP method override. Defaults to POST when body is present, GET otherwise.
    retries : int
        Number of retries on 429 rate-limit responses.
    retry_delay : float
        Initial delay between retries (doubles on each retry).
    """
    url = f"{NOTION_BASE}{path}"
    data = json.dumps(body).encode("utf-8") if body else None
    if method is None:
        method = "POST" if data else "GET"

    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": NOTION_API_VERSION,
            "Content-Type": "application/json",
        },
        method=method,
    )

    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries:
                wait = retry_delay * (2 ** attempt)
                print(f"  Rate limited (429), retrying in {wait:.1f}s...", file=sys.stderr)
                time.sleep(wait)
                continue
            error_body = e.read().decode("utf-8", errors="replace")
            try:
                detail = json.loads(error_body)
                msg = detail.get("message", error_body)
            except json.JSONDecodeError:
                msg = error_body
            print(f"ERROR: Notion API {e.code} on {url}\n  {msg}", file=sys.stderr)
            raise


def query_database(
    db_id: str,
    token: str,
    filter_body: dict,
    *,
    page_size: int = 100,
    max_pages: int | None = None,
) -> list[dict]:
    """Query a Notion database with automatic pagination.

    Returns a flat list of page objects from all pages of results.
    """
    results: list[dict] = []
    start_cursor: str | None = None
    pages_fetched = 0

    while True:
        body: dict = {"filter": filter_body, "page_size": page_size}
        if start_cursor:
            body["start_cursor"] = start_cursor

        resp = notion_request(f"/databases/{db_id}/query", token, body)
        results.extend(resp.get("results", []))
        pages_fetched += 1

        if max_pages and pages_fetched >= max_pages:
            break
        if resp.get("has_more") and resp.get("next_cursor"):
            start_cursor = resp["next_cursor"]
        else:
            break

    return results


def query_database_single(
    db_id: str,
    token: str,
    filter_body: dict,
) -> dict | None:
    """Query a Notion database and return the first matching page, or None."""
    results = query_database(db_id, token, filter_body, page_size=1, max_pages=1)
    return results[0] if results else None


# ---------------------------------------------------------------------------
# Property extraction helpers
# ---------------------------------------------------------------------------

def extract_plain_text(prop: dict | None) -> str:
    """Extract plain text from a Notion property value (title, rich_text, select, email, url)."""
    if not prop:
        return ""
    ptype = prop.get("type")
    if ptype == "title":
        return "".join(t.get("plain_text", "") for t in prop.get("title", [])).strip()
    if ptype == "rich_text":
        return "".join(t.get("plain_text", "") for t in prop.get("rich_text", [])).strip()
    if ptype == "select":
        sel = prop.get("select")
        return sel["name"] if sel else ""
    if ptype == "multi_select":
        return ", ".join(item.get("name", "") for item in prop.get("multi_select", []))
    if ptype == "email":
        return prop.get("email") or ""
    if ptype == "url":
        return prop.get("url") or ""
    if ptype == "checkbox":
        return str(prop.get("checkbox", False))
    return ""


def extract_relation_ids(prop: dict | None) -> list[str]:
    """Extract page IDs from a relation property."""
    if not prop or prop.get("type") != "relation":
        return []
    return [item["id"] for item in prop.get("relation", []) if item.get("id")]


def extract_multi_select_names(prop: dict | None) -> list[str]:
    """Extract option names from a multi_select property."""
    if not prop or prop.get("type") != "multi_select":
        return []
    return [item["name"] for item in prop.get("multi_select", [])]


def extract_date_start(prop: dict | None) -> str | None:
    """Extract the start date string from a date property."""
    if not prop or prop.get("type") != "date":
        return None
    date_val = prop.get("date")
    return date_val.get("start") if date_val else None
