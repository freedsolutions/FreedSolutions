from __future__ import annotations

import sqlite3
from urllib.parse import urlparse

from ops.local_db.lib.config import split_csv_text
from ops.local_db.lib.db import fetch_one, query


def normalize_email(email: str | None) -> str:
    return (email or "").strip().lower()


def normalize_linkedin_url(url: str | None) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    path = parsed.path.rstrip("/")
    host = parsed.netloc.lower().replace("www.", "")
    if host != "linkedin.com":
        return raw
    if path.startswith("/in/"):
        return f"https://www.linkedin.com/in/{path.split('/in/', 1)[1].strip('/')}"
    if path.startswith("/company/"):
        return f"https://www.linkedin.com/company/{path.split('/company/', 1)[1].strip('/')}"
    return f"https://www.linkedin.com{path}"


def extract_domain(value: str | None) -> str:
    raw = normalize_email(value)
    if "@" in raw:
        return raw.split("@", 1)[1]

    if not value:
        return ""
    parsed = urlparse(value if "://" in value else f"https://{value}")
    return parsed.netloc.lower().replace("www.", "").split(":", 1)[0]


def is_generic_domain(domain: str | None, generic_domains: tuple[str, ...]) -> bool:
    return extract_domain(domain) in {item.lower() for item in generic_domains}


def find_contact_by_email(connection: sqlite3.Connection, email: str | None) -> sqlite3.Row | None:
    target = normalize_email(email)
    if not target:
        return None
    return fetch_one(
        connection,
        """
        SELECT *
        FROM contacts
        WHERE lower(trim(coalesce(email, ''))) = ?
           OR lower(trim(coalesce(secondary_email, ''))) = ?
           OR lower(trim(coalesce(tertiary_email, ''))) = ?
        LIMIT 1
        """,
        (target, target, target),
    )


def find_company_by_domain(connection: sqlite3.Connection, domain: str | None) -> sqlite3.Row | None:
    target = extract_domain(domain)
    if not target:
        return None

    for row in query(connection, "SELECT * FROM companies"):
        domains = {item.lower() for item in split_csv_text(row["domains"])}
        additional = {item.lower() for item in split_csv_text(row["additional_domains"])}
        if target in domains or target in additional:
            return row
    return None


def find_company_by_sender_address(
    connection: sqlite3.Connection,
    sender_email: str | None,
) -> sqlite3.Row | None:
    target = normalize_email(sender_email)
    if not target:
        return None
    for row in query(connection, "SELECT * FROM companies"):
        additional = {item.lower() for item in split_csv_text(row["additional_domains"])}
        if target in additional:
            return row
    return None
