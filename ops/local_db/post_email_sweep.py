"""Post-Email Sweep: mechanical CRM wiring for Gmail threads.

Scans Gmail for threads since the last run, classifies each against the
Notion Emails DB, and routes to create/update/skip/dismiss. Handles CRM
wiring (Contacts, Companies, Domains) via exact-match Notion API queries.

Runs BEFORE the Notion Custom Agent's nightly schedule. The Agent handles
semantic reasoning (Email Notes summaries, cross-contextual matching,
Action Item creation) on records this script has wired.

Usage:
  python ops/local_db/post_email_sweep.py --dry-run           # classify only
  python ops/local_db/post_email_sweep.py --dry-run --verbose  # detailed logging
  python ops/local_db/post_email_sweep.py                      # live run
  python ops/local_db/post_email_sweep.py --since 2026-04-01   # override lookback
  python ops/local_db/post_email_sweep.py --account adam@freedsolutions.com
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

# Force UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from ops.local_db.lib.config import load_config, AppConfig
from ops.local_db.lib.gmail_auth import build_gmail_service
from ops.local_db.lib.notion_api import (
    load_notion_token,
    notion_request,
    query_database,
    query_database_single,
    extract_plain_text,
    extract_relation_ids,
    extract_multi_select_names,
    extract_date_start,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GMAIL_SYSTEM_LABELS = frozenset({
    "INBOX", "UNREAD", "IMPORTANT", "STARRED", "SENT", "DRAFT",
    "SPAM", "TRASH",
    "CATEGORY_SOCIAL", "CATEGORY_UPDATES", "CATEGORY_FORUMS",
    "CATEGORY_PROMOTIONS", "CATEGORY_PERSONAL",
    # Star variants (Gmail uses these internally for colored stars)
    "YELLOW_STAR", "ORANGE_STAR", "RED_STAR", "PURPLE_STAR",
    "BLUE_STAR", "GREEN_STAR",
    "RED_BANG", "ORANGE_GUILLEMET", "YELLOW_BANG",
    "GREEN_CHECK", "BLUE_INFO", "PURPLE_QUESTION",
})

# Deterministic skip-filter patterns (Step 1.3)
SKIP_SUBJECT_PREFIXES = (
    "Accepted:", "Declined:", "Tentative:",
    "Delivery Status Notification",
    "Undeliverable:",
    "Mail delivery failed",
)

SKIP_SENDER_PATTERNS = (
    "noreply@", "no-reply@", "donotreply@",
    "mailer-daemon@", "postmaster@",
)

# Senders that indicate delivery/security noise (not CRM-relevant)
SKIP_NOISE_SENDERS = (
    "dmarc-", "dmarc_", "dmarcreport@",
)

MAX_THREADS_PER_RUN = 500
DEFAULT_LOOKBACK_DAYS = 7


# ---------------------------------------------------------------------------
# Step 0: Read Last Run from Agent Config
# ---------------------------------------------------------------------------

def read_last_run(config: AppConfig, notion_token: str, *, verbose: bool = False) -> datetime:
    """Read Post-Email Agent Last Run from Agent Config page.

    The Agent Config page contains table blocks with key-value rows.
    We read the page's child blocks to find the Post-Email Agent section.
    """
    agent_config_id = config.notion.databases.get("agent_config")
    if not agent_config_id:
        print("WARNING: No agent_config page ID in config. Using default lookback.", file=sys.stderr)
        return _default_lookback()

    try:
        # Read child blocks of the Agent Config page
        resp = notion_request(f"/blocks/{agent_config_id}/children?page_size=100", notion_token)
        blocks = resp.get("results", [])
    except Exception as e:
        print(f"WARNING: Failed to read Agent Config page: {e}", file=sys.stderr)
        return _default_lookback()

    # Walk blocks looking for "Post-Email Agent" heading, then the table below it
    in_post_email_section = False
    for block in blocks:
        btype = block.get("type", "")

        # Check for heading that marks our section
        if btype in ("heading_1", "heading_2", "heading_3"):
            heading_text = _block_plain_text(block, btype)
            if "post-email" in heading_text.lower():
                in_post_email_section = True
                if verbose:
                    print(f"  Found Post-Email Agent section: \"{heading_text}\"")
                continue
            elif in_post_email_section:
                # Hit a new section heading — stop looking
                break

        if in_post_email_section and btype == "table":
            # Read table rows
            table_id = block["id"]
            try:
                rows_resp = notion_request(f"/blocks/{table_id}/children?page_size=50", notion_token)
                rows = rows_resp.get("results", [])
            except Exception as e:
                print(f"WARNING: Failed to read Agent Config table: {e}", file=sys.stderr)
                return _default_lookback()

            # Skip header row, find the data row with "Post-Email Agent Last Run"
            for row in rows:
                if row.get("type") != "table_row":
                    continue
                cells = row.get("table_row", {}).get("cells", [])
                if len(cells) < 2:
                    continue
                key = "".join(t.get("plain_text", "") for t in cells[0]).strip()
                value = "".join(t.get("plain_text", "") for t in cells[1]).strip()

                if "last run" in key.lower():
                    if verbose:
                        print(f"  Agent Config Last Run: \"{value}\"")
                    return _parse_last_run(value, verbose=verbose)

    print("WARNING: Post-Email Agent Last Run not found in Agent Config. Using default lookback.", file=sys.stderr)
    return _default_lookback()


def _block_plain_text(block: dict, btype: str) -> str:
    """Extract plain text from a block's rich_text array."""
    rich_text = block.get(btype, {}).get("rich_text", [])
    return "".join(t.get("plain_text", "") for t in rich_text)


def _parse_last_run(value: str, *, verbose: bool = False) -> datetime:
    """Parse an ISO 8601 timestamp string into a datetime."""
    if not value:
        return _default_lookback()
    try:
        dt = datetime.fromisoformat(value)
        # If no timezone, assume ET (UTC-4)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone(timedelta(hours=-4)))

        # Safety: if older than 7 days, cap at 7-day lookback
        now = datetime.now(timezone.utc)
        if (now - dt).days > DEFAULT_LOOKBACK_DAYS:
            print(f"WARNING: Last Run ({value}) is older than {DEFAULT_LOOKBACK_DAYS} days. Capping lookback.", file=sys.stderr)
            return _default_lookback()

        return dt
    except (ValueError, TypeError) as e:
        print(f"WARNING: Could not parse Last Run \"{value}\": {e}. Using default lookback.", file=sys.stderr)
        return _default_lookback()


def _default_lookback() -> datetime:
    """Return a datetime 7 days ago (default lookback)."""
    return datetime.now(timezone.utc) - timedelta(days=DEFAULT_LOOKBACK_DAYS)


# ---------------------------------------------------------------------------
# Gmail: thread fetching + metadata
# ---------------------------------------------------------------------------

def fetch_threads_since(service, since: datetime, *, verbose: bool = False) -> list[dict]:
    """Fetch Gmail thread IDs modified since the given timestamp.

    Uses threads.list with q="after:{epoch} -in:spam -in:trash".
    Returns raw thread list entries (id, snippet, historyId).
    """
    epoch = int(since.timestamp())
    query = f"after:{epoch} -in:spam -in:trash"
    if verbose:
        print(f"  Gmail query: {query}")

    threads: list[dict] = []
    page_token: str | None = None

    while True:
        kwargs: dict = {"userId": "me", "q": query, "maxResults": 100}
        if page_token:
            kwargs["pageToken"] = page_token

        resp = service.users().threads().list(**kwargs).execute()
        batch = resp.get("threads", [])
        threads.extend(batch)

        if verbose and batch:
            print(f"  Fetched {len(batch)} threads (total: {len(threads)})")

        if len(threads) >= MAX_THREADS_PER_RUN:
            print(f"  Hit {MAX_THREADS_PER_RUN}-thread cap. Remaining threads deferred to next run.", file=sys.stderr)
            threads = threads[:MAX_THREADS_PER_RUN]
            break

        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    return threads


def fetch_thread_metadata(service, thread_id: str) -> dict | None:
    """Fetch thread metadata: labelIds + first message headers.

    Returns dict with keys: thread_id, label_ids, subject, from_email,
    to_emails, cc_emails, date, message_count, messages_meta.
    """
    try:
        thread = service.users().threads().get(
            userId="me", id=thread_id, format="metadata",
            metadataHeaders=["Subject", "From", "To", "Cc", "Bcc", "Date"],
        ).execute()
    except Exception as e:
        err_str = str(e)
        if "429" in err_str or "rate" in err_str.lower():
            print("  Gmail rate limited, waiting 5s...", file=sys.stderr)
            time.sleep(5)
            return fetch_thread_metadata(service, thread_id)
        print(f"  ERROR fetching thread {thread_id}: {e}", file=sys.stderr)
        return None

    messages = thread.get("messages", [])
    if not messages:
        return None

    # Thread-level labelIds (union of all messages)
    all_label_ids: set[str] = set()
    for msg in messages:
        all_label_ids.update(msg.get("labelIds", []))

    # Extract headers from first message
    first_msg = messages[0]
    headers = _headers_dict(first_msg)

    # Extract headers from all messages for participant collection
    all_participants: dict[str, set[str]] = {"from": set(), "to": set(), "cc": set(), "bcc": set()}
    messages_meta: list[dict] = []
    for msg in messages:
        msg_headers = _headers_dict(msg)
        msg_from = _extract_email_address(msg_headers.get("from", ""))
        if msg_from:
            all_participants["from"].add(msg_from.lower())
        for field in ("to", "cc", "bcc"):
            for addr in _extract_email_addresses(msg_headers.get(field, "")):
                all_participants[field].add(addr.lower())

        messages_meta.append({
            "id": msg.get("id", ""),
            "from": msg_from,
            "date": msg_headers.get("date", ""),
            "internal_date": msg.get("internalDate", ""),
            "label_ids": msg.get("labelIds", []),
        })

    return {
        "thread_id": thread_id,
        "label_ids": list(all_label_ids),
        "subject": headers.get("subject", ""),
        "from_email": _extract_email_address(headers.get("from", "")),
        "date": headers.get("date", ""),
        "message_count": len(messages),
        "all_from": all_participants["from"],
        "all_to": all_participants["to"],
        "all_cc": all_participants["cc"],
        "all_bcc": all_participants["bcc"],
        "messages_meta": messages_meta,
    }


def _headers_dict(message: dict) -> dict[str, str]:
    """Extract headers from a Gmail message payload into a lowercase-keyed dict."""
    headers = message.get("payload", {}).get("headers", [])
    return {h["name"].lower(): h.get("value", "") for h in headers}


_EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.\w+")


def _extract_email_address(header_value: str) -> str | None:
    """Extract a single email address from a header like 'Name <email@example.com>'."""
    match = _EMAIL_RE.search(header_value)
    return match.group(0).lower() if match else None


def _extract_email_addresses(header_value: str) -> list[str]:
    """Extract all email addresses from a header (To, Cc, Bcc may have multiple)."""
    return [m.lower() for m in _EMAIL_RE.findall(header_value)]


def _extract_display_name(header_value: str) -> str:
    """Extract display name from 'Display Name <email@example.com>' header."""
    # Try to extract the part before <email>
    angle = header_value.find("<")
    if angle > 0:
        name = header_value[:angle].strip().strip('"').strip("'").strip()
        if name:
            return name
    # Fallback: derive from email local part
    email = _extract_email_address(header_value)
    if email:
        local = email.split("@")[0]
        # Convert dots/underscores to spaces and title-case
        return local.replace(".", " ").replace("_", " ").replace("-", " ").title()
    return ""


def _parse_internal_date(internal_date_ms: str) -> datetime | None:
    """Convert Gmail internalDate (milliseconds since epoch) to datetime."""
    try:
        return datetime.fromtimestamp(int(internal_date_ms) / 1000, tz=timezone.utc)
    except (ValueError, TypeError):
        return None


def _format_iso_date(dt: datetime) -> str:
    """Format a datetime as ISO 8601 for Notion date property."""
    return dt.isoformat()


def build_label_map(service) -> dict[str, str]:
    """Build label_id -> label_name map from Gmail."""
    resp = service.users().labels().list(userId="me").execute()
    return {lbl["id"]: lbl["name"] for lbl in resp.get("labels", [])}


# ---------------------------------------------------------------------------
# Classification matrix (Step 1.4)
# ---------------------------------------------------------------------------

class Classification:
    NEW_LABELED = "NEW_LABELED"
    NEW_AUTO_ARCHIVED = "NEW_AUTO_ARCHIVED"
    NEW_UNKNOWN_DOMAIN = "NEW_UNKNOWN_DOMAIN"
    UPDATED = "UPDATED"
    RESUME = "RESUME"
    DISMISS = "DISMISS"
    OUTBOUND_NEW = "OUTBOUND_NEW"
    OUTBOUND_UPDATE = "OUTBOUND_UPDATE"
    SKIP = "SKIP"


def classify_thread(
    thread_meta: dict,
    existing_record: dict | None,
    adam_aliases: set[str],
) -> str:
    """Classify a thread per the 11-row matrix.

    Parameters
    ----------
    thread_meta : dict
        Output of fetch_thread_metadata().
    existing_record : dict | None
        Existing Notion Email page, or None.
    adam_aliases : set[str]
        Adam's email aliases (lowercase).

    Returns
    -------
    str
        Classification constant.
    """
    label_ids = set(thread_meta["label_ids"])
    in_inbox = "INBOX" in label_ids
    user_labels = [lid for lid in label_ids if lid not in GMAIL_SYSTEM_LABELS]
    has_user_label = len(user_labels) > 0

    # Check if sent-only from Adam (all From addresses are Adam aliases)
    all_from = thread_meta.get("all_from", set())
    is_adam_only = bool(all_from) and all_from.issubset(adam_aliases)

    # Outbound detection
    if is_adam_only:
        if existing_record:
            return Classification.OUTBOUND_UPDATE
        return Classification.OUTBOUND_NEW

    # Has existing record?
    if existing_record:
        completeness = _assess_completeness(existing_record)
        if completeness == "partial":
            return Classification.RESUME
        return Classification.UPDATED

    # No existing record
    if has_user_label and in_inbox:
        return Classification.NEW_LABELED
    if has_user_label and not in_inbox:
        return Classification.NEW_AUTO_ARCHIVED
    if not has_user_label and in_inbox:
        return Classification.NEW_UNKNOWN_DOMAIN
    # No label, archived, no record
    return Classification.DISMISS


def _assess_completeness(record: dict) -> str:
    """Check if an existing Email record is complete or partial.

    Complete = Contacts wired AND Email Notes populated.
    Complete (bot-only) = Email Notes says bot-only/alias-only, no Contacts.
    Partial = anything else.
    """
    props = record.get("properties", {})
    contacts = extract_relation_ids(props.get("Contacts"))
    notes = extract_plain_text(props.get("Email Notes"))

    if contacts and notes:
        return "complete"
    if not contacts and notes:
        lower = notes.lower()
        if "bot-only" in lower or "alias-only" in lower:
            return "complete_bot"
    return "partial"


# ---------------------------------------------------------------------------
# Skip filter (Step 1.3) — deterministic only
# ---------------------------------------------------------------------------

def should_skip(thread_meta: dict) -> tuple[bool, str]:
    """Apply deterministic skip filter. Returns (should_skip, reason).

    Teams and LinkedIn notification senders are EXCLUDED from the automated-sender
    skip — they are chat wrappers around real human conversations, not bot noise.
    """
    subject = thread_meta.get("subject", "")
    from_email = (thread_meta.get("from_email") or "").lower()

    # Calendar status replies
    for prefix in SKIP_SUBJECT_PREFIXES:
        if subject.startswith(prefix):
            return True, f"Calendar/delivery skip: subject starts with '{prefix}'"

    # Teams and LinkedIn notifications are NOT skippable — they wrap human content
    is_notification_wrapper = (
        "teams.mail.microsoft" in from_email
        or "linkedin.com" in from_email
    )

    # Automated senders that are never CRM-relevant (except notification wrappers)
    if not is_notification_wrapper:
        for pattern in SKIP_SENDER_PATTERNS:
            if from_email.startswith(pattern):
                return True, f"Automated sender: {from_email}"

    # DMARC / security noise
    for noise in SKIP_NOISE_SENDERS:
        if noise in from_email:
            return True, f"Security/DMARC noise: {from_email}"

    # Password reset / security alert subjects
    subject_lower = subject.lower()
    if any(kw in subject_lower for kw in ("password reset", "security alert", "verify your email")):
        return True, f"Security alert: {subject}"

    return False, ""


# ---------------------------------------------------------------------------
# Notion: lookup existing Email record by Thread ID
# ---------------------------------------------------------------------------

def lookup_email_by_thread_id(
    thread_id: str,
    emails_db_id: str,
    notion_token: str,
) -> dict | None:
    """Query Emails DB for an exact Thread ID match."""
    return query_database_single(
        emails_db_id,
        notion_token,
        filter_body={
            "property": "Thread ID",
            "rich_text": {"equals": thread_id},
        },
    )


# ---------------------------------------------------------------------------
# Notion: fetch Labels multi_select options (for parity check)
# ---------------------------------------------------------------------------

def fetch_labels_options(emails_db_id: str, notion_token: str) -> set[str]:
    """Get the set of valid Labels multi_select option names from Emails DB schema."""
    try:
        resp = notion_request(f"/databases/{emails_db_id}", notion_token)
        labels_prop = resp.get("properties", {}).get("Labels", {})
        options = labels_prop.get("multi_select", {}).get("options", [])
        return {opt["name"] for opt in options}
    except Exception as e:
        print(f"WARNING: Failed to fetch Labels schema: {e}", file=sys.stderr)
        return set()


# ---------------------------------------------------------------------------
# Notion: Contact lookup + create (Steps 2.1-2.3)
# ---------------------------------------------------------------------------

def lookup_contact_by_email(
    email_addr: str,
    contacts_db_id: str,
    notion_token: str,
) -> dict | None:
    """Query Contacts DB by Email, Secondary Email, Tertiary Email (exact match)."""
    return query_database_single(
        contacts_db_id,
        notion_token,
        filter_body={
            "or": [
                {"property": "Email", "email": {"equals": email_addr}},
                {"property": "Secondary Email", "email": {"equals": email_addr}},
                {"property": "Tertiary Email", "email": {"equals": email_addr}},
            ]
        },
    )


def create_draft_contact(
    name: str,
    email_addr: str,
    contacts_db_id: str,
    notion_token: str,
    *,
    verbose: bool = False,
) -> dict:
    """Create a Draft Contact in Notion."""
    properties: dict = {
        "Contact Name": {"title": [{"text": {"content": name}}]},
        "Email": {"email": email_addr},
        "Record Status": {"select": {"name": "Draft"}},
    }
    body = {
        "parent": {"database_id": contacts_db_id},
        "icon": {"type": "emoji", "emoji": "\U0001f464"},  # 👤
        "properties": properties,
    }
    result = notion_request("/pages", notion_token, body)
    if verbose:
        print(f"    CREATED Contact: \"{name}\" <{email_addr}> -> {result['id'][:8]}")
    return result


# ---------------------------------------------------------------------------
# Notion: Domain + Company lookup + create (Steps 2.4, 2.4.1)
# ---------------------------------------------------------------------------

def lookup_domain(
    domain: str,
    domains_db_id: str,
    notion_token: str,
) -> dict | None:
    """Query Domains DB by exact Domain title match."""
    return query_database_single(
        domains_db_id,
        notion_token,
        filter_body={
            "property": "Domain",
            "title": {"equals": domain},
        },
    )


def get_company_from_domain_record(domain_record: dict) -> str | None:
    """Extract the first Company page ID from a Domain record's Companies relation."""
    props = domain_record.get("properties", {})
    # The relation property name has an emoji prefix
    for key in props:
        if "companies" in key.lower():
            ids = extract_relation_ids(props[key])
            return ids[0] if ids else None
    return None



def create_draft_company(
    company_name: str,
    companies_db_id: str,
    notion_token: str,
    *,
    verbose: bool = False,
) -> dict:
    """Create a Draft Company in Notion."""
    properties: dict = {
        "Company Name": {"title": [{"text": {"content": company_name}}]},
        "Record Status": {"select": {"name": "Draft"}},
    }
    body = {
        "parent": {"database_id": companies_db_id},
        "properties": properties,
    }
    result = notion_request("/pages", notion_token, body)
    if verbose:
        print(f"    CREATED Company: \"{company_name}\" -> {result['id'][:8]}")
    return result


def create_draft_domain(
    domain: str,
    company_page_id: str,
    domains_db_id: str,
    notion_token: str,
    *,
    is_generic: bool = False,
    verbose: bool = False,
) -> dict:
    """Create a Draft Domain record in the Domains DB."""
    properties: dict = {
        "Domain": {"title": [{"text": {"content": domain}}]},
        "\U0001f4bc Companies": {"relation": [{"id": company_page_id}]},  # 💼
        "Filter Shape": {"select": {"name": "Domain"}},
        "Source Type": {"select": {"name": "Primary"}},
        "Is Generic": {"checkbox": is_generic},
        "Record Status": {"select": {"name": "Draft"}},
    }
    body = {
        "parent": {"database_id": domains_db_id},
        "icon": {"type": "emoji", "emoji": "\U0001f310"},  # 🌐
        "properties": properties,
    }
    result = notion_request("/pages", notion_token, body)
    if verbose:
        print(f"    CREATED Domain: \"{domain}\" -> {result['id'][:8]}")
    return result


# ---------------------------------------------------------------------------
# Notion: Email record create + update
# ---------------------------------------------------------------------------

def create_email_record(
    thread_meta: dict,
    user_label_names: list[str],
    valid_labels: set[str],
    source_label: str,
    emails_db_id: str,
    notion_token: str,
    *,
    contact_ids: list[str] | None = None,
    email_notes: str = "",
    verbose: bool = False,
) -> dict:
    """Create a new Draft Email record in Notion (Step 1.5)."""
    subject = thread_meta.get("subject", "(no subject)")
    thread_id = thread_meta["thread_id"]

    # Parse first message date
    first_date = _resolve_first_message_date(thread_meta)

    # Filter labels to only valid options
    safe_labels = [ln for ln in user_label_names if ln in valid_labels]

    properties: dict = {
        "Email Subject": {"title": [{"text": {"content": subject}}]},
        "Thread ID": {"rich_text": [{"text": {"content": thread_id}}]},
        "Record Status": {"select": {"name": "Draft"}},
        "Source": {"select": {"name": source_label}},
    }

    if first_date:
        properties["Date"] = {"date": {"start": _format_iso_date(first_date)}}

    if safe_labels:
        properties["Labels"] = {"multi_select": [{"name": ln} for ln in safe_labels]}

    if contact_ids:
        properties["Contacts"] = {"relation": [{"id": cid} for cid in contact_ids]}

    if email_notes:
        properties["Email Notes"] = {"rich_text": [{"text": {"content": email_notes}}]}

    body = {
        "parent": {"database_id": emails_db_id},
        "icon": {"type": "emoji", "emoji": "\U0001f4e7"},  # 📧
        "properties": properties,
    }
    result = notion_request("/pages", notion_token, body)
    if verbose:
        print(f"    CREATED Email: \"{subject}\" -> {result['id'][:8]}")
    return result


def update_email_record(
    page_id: str,
    notion_token: str,
    *,
    contact_ids: list[str] | None = None,
    new_date: datetime | None = None,
    new_subject: str | None = None,
    append_notes: str | None = None,
    existing_notes: str = "",
    label_names: list[str] | None = None,
    valid_labels: set[str] | None = None,
    verbose: bool = False,
) -> dict:
    """Update an existing Email record in Notion."""
    properties: dict = {}

    if contact_ids is not None:
        properties["Contacts"] = {"relation": [{"id": cid} for cid in contact_ids]}

    if new_date is not None:
        properties["Date"] = {"date": {"start": _format_iso_date(new_date)}}

    if new_subject is not None:
        properties["Email Subject"] = {"title": [{"text": {"content": new_subject}}]}

    if append_notes is not None:
        combined = f"{existing_notes}\n{append_notes}" if existing_notes else append_notes
        # Notion rich_text has a 2000 char limit per block
        if len(combined) > 1900:
            combined = combined[:1900] + "\n[truncated]"
        properties["Email Notes"] = {"rich_text": [{"text": {"content": combined}}]}

    if label_names is not None and valid_labels is not None:
        safe = [ln for ln in label_names if ln in valid_labels]
        if safe:
            properties["Labels"] = {"multi_select": [{"name": ln} for ln in safe]}

    if not properties:
        return {}

    result = notion_request(f"/pages/{page_id}", notion_token, {"properties": properties}, method="PATCH")
    if verbose:
        print(f"    UPDATED Email: {page_id[:8]}")
    return result


def _resolve_first_message_date(thread_meta: dict) -> datetime | None:
    """Get the datetime from the first message's internalDate."""
    messages = thread_meta.get("messages_meta", [])
    if messages and messages[0].get("internal_date"):
        return _parse_internal_date(messages[0]["internal_date"])
    return None


def _resolve_latest_message_date(thread_meta: dict) -> datetime | None:
    """Get the datetime from the last message's internalDate."""
    messages = thread_meta.get("messages_meta", [])
    if messages and messages[-1].get("internal_date"):
        return _parse_internal_date(messages[-1]["internal_date"])
    return None


# ---------------------------------------------------------------------------
# Notion: update Agent Config Last Run (Step 4)
# ---------------------------------------------------------------------------

def update_last_run(
    config: AppConfig,
    notion_token: str,
    run_summary: str,
    *,
    verbose: bool = False,
) -> None:
    """Update the Post-Email Agent Last Run timestamp in Agent Config.

    Finds the table row in the Post-Email Agent section and overwrites it.
    """
    agent_config_id = config.notion.databases.get("agent_config")
    if not agent_config_id:
        print("WARNING: No agent_config page ID. Skipping Last Run update.", file=sys.stderr)
        return

    try:
        resp = notion_request(f"/blocks/{agent_config_id}/children?page_size=100", notion_token)
        blocks = resp.get("results", [])
    except Exception as e:
        print(f"WARNING: Failed to read Agent Config for update: {e}", file=sys.stderr)
        return

    in_post_email_section = False
    for block in blocks:
        btype = block.get("type", "")

        if btype in ("heading_1", "heading_2", "heading_3"):
            heading_text = _block_plain_text(block, btype)
            if "post-email" in heading_text.lower():
                in_post_email_section = True
                continue
            elif in_post_email_section:
                break

        if in_post_email_section and btype == "table":
            table_id = block["id"]
            try:
                rows_resp = notion_request(f"/blocks/{table_id}/children?page_size=50", notion_token)
                rows = rows_resp.get("results", [])
            except Exception as e:
                print(f"WARNING: Failed to read Agent Config table rows: {e}", file=sys.stderr)
                return

            for row in rows:
                if row.get("type") != "table_row":
                    continue
                cells = row.get("table_row", {}).get("cells", [])
                if len(cells) < 2:
                    continue
                key = "".join(t.get("plain_text", "") for t in cells[0]).strip()
                if "last run" not in key.lower():
                    continue

                # Found the data row — update it
                now = datetime.now(timezone(timedelta(hours=-4)))
                timestamp_str = now.isoformat()
                updated_str = f"Post-Email Sweep (Script {now.strftime('%I:%M %p ET — %b %d')}). {run_summary}"

                new_cells = [
                    [{"type": "text", "text": {"content": key}}],
                    [{"type": "text", "text": {"content": timestamp_str}}],
                ]
                # If there's a 3rd column (Updated), include it
                if len(cells) >= 3:
                    new_cells.append([{"type": "text", "text": {"content": updated_str}}])

                update_body = {"table_row": {"cells": new_cells}}
                try:
                    notion_request(f"/blocks/{row['id']}", notion_token, update_body, method="PATCH")
                    if verbose:
                        print(f"  Updated Agent Config Last Run: {timestamp_str}")
                except Exception as e:
                    print(f"WARNING: Failed to update Agent Config Last Run: {e}", file=sys.stderr)
                return

    print("WARNING: Could not find Post-Email Agent Last Run row to update.", file=sys.stderr)


# ---------------------------------------------------------------------------
# CRM wiring orchestration
# ---------------------------------------------------------------------------

def wire_crm_for_thread(
    thread_meta: dict,
    email_page_id: str,
    source_label: str,
    config: AppConfig,
    notion_token: str,
    entity_cache: dict,
    counts: dict,
    *,
    is_outbound: bool = False,
    verbose: bool = False,
) -> list[str]:
    """Extract participants, match/create Contacts, lookup Companies via Domains.

    Returns list of Contact page IDs wired to the Email record.
    """
    adam_aliases = set(config.adam.exclude_emails)
    generic_domains = set(config.adam.generic_domains)
    contacts_db_id = config.notion.databases["contacts"]
    domains_db_id = config.notion.databases["domains"]
    companies_db_id = config.notion.databases["companies"]

    # Collect all participant emails (excluding Adam)
    all_emails: set[str] = set()
    # For outbound, wire to recipients; for inbound, wire to senders
    if is_outbound:
        all_emails.update(thread_meta.get("all_to", set()))
        all_emails.update(thread_meta.get("all_cc", set()))
    else:
        all_emails.update(thread_meta.get("all_from", set()))
        all_emails.update(thread_meta.get("all_to", set()))
        all_emails.update(thread_meta.get("all_cc", set()))

    # Remove Adam aliases
    participant_emails = {e for e in all_emails if e.lower() not in adam_aliases}

    # Remove obvious automated senders entirely from Contact creation
    # (Teams/LinkedIn are kept in the thread for classification but not as Contacts)
    participant_emails = {
        e for e in participant_emails
        if not any(e.startswith(p) for p in SKIP_SENDER_PATTERNS)
        and not any(e.startswith(p) for p in ("notification@", "notifications@", "newsletter@", "updates@"))
        and "noreply" not in e.replace("-", "").replace("_", "")
    }

    if not participant_emails:
        if verbose:
            print(f"    No human participants after alias/bot removal")
        return []

    # Build display name map from message headers
    name_map = _build_name_map(thread_meta)

    contact_ids: list[str] = []

    for email_addr in sorted(participant_emails):
        email_lower = email_addr.lower()

        # Check entity cache first
        if email_lower in entity_cache.get("contacts", {}):
            contact_ids.append(entity_cache["contacts"][email_lower])
            continue

        # Exact-match query
        contact = lookup_contact_by_email(email_lower, contacts_db_id, notion_token)
        time.sleep(0.05)

        if contact:
            cid = contact["id"]
            entity_cache.setdefault("contacts", {})[email_lower] = cid
            contact_ids.append(cid)
            if verbose:
                cname = extract_plain_text(contact.get("properties", {}).get("Contact Name"))
                print(f"    MATCHED Contact: \"{cname}\" <{email_lower}>")
        else:
            # Create Draft Contact
            display_name = name_map.get(email_lower, email_lower.split("@")[0].replace(".", " ").title())
            new_contact = create_draft_contact(display_name, email_lower, contacts_db_id, notion_token, verbose=verbose)
            cid = new_contact["id"]
            entity_cache.setdefault("contacts", {})[email_lower] = cid
            contact_ids.append(cid)
            counts["contacts_created"] = counts.get("contacts_created", 0) + 1

            # Domain/Company wiring for new contact
            domain = email_lower.split("@")[1] if "@" in email_lower else None
            if domain and domain not in generic_domains:
                company_id = _resolve_company_for_domain(
                    domain, email_lower, email_page_id,
                    thread_meta.get("subject", ""),
                    cid,
                    config, notion_token, entity_cache, counts,
                    verbose=verbose,
                )
                if company_id:
                    # Wire Contact -> Company
                    try:
                        notion_request(f"/pages/{cid}", notion_token, {
                            "properties": {"Company": {"relation": [{"id": company_id}]}}
                        }, method="PATCH")
                    except Exception as e:
                        print(f"    WARNING: Failed to wire Contact to Company: {e}", file=sys.stderr)

    return contact_ids


def _build_name_map(thread_meta: dict) -> dict[str, str]:
    """Build email -> display name map from all message From/To headers."""
    name_map: dict[str, str] = {}
    for msg in thread_meta.get("messages_meta", []):
        # We only have limited header info in messages_meta
        # The from field already has the email extracted
        pass
    # For more complete name mapping, we'd need the raw headers
    # For now, the display name extraction happens in create_draft_contact
    return name_map


def _resolve_company_for_domain(
    domain: str,
    sender_email: str,
    email_page_id: str,
    email_subject: str,
    contact_page_id: str,
    config: AppConfig,
    notion_token: str,
    entity_cache: dict,
    counts: dict,
    *,
    verbose: bool = False,
) -> str | None:
    """Lookup or create Company for a domain. Returns Company page ID or None."""
    domains_db_id = config.notion.databases["domains"]
    companies_db_id = config.notion.databases["companies"]

    # Check domain cache
    if domain in entity_cache.get("domains", {}):
        cached = entity_cache["domains"][domain]
        return cached.get("company_id")

    # Query Domains DB
    domain_record = lookup_domain(domain, domains_db_id, notion_token)
    time.sleep(0.05)

    if domain_record:
        company_id = get_company_from_domain_record(domain_record)
        entity_cache.setdefault("domains", {})[domain] = {
            "domain_id": domain_record["id"],
            "company_id": company_id,
        }
        if verbose and company_id:
            print(f"    MATCHED Domain: {domain} -> Company {company_id[:8]}")
        return company_id

    # No Domain record — create Draft Company + Draft Domain
    # Derive company name from domain
    company_name = domain.split(".")[0].title()

    # Check company cache
    if domain in entity_cache.get("companies_by_domain", {}):
        company_id = entity_cache["companies_by_domain"][domain]
    else:
        new_company = create_draft_company(company_name, companies_db_id, notion_token, verbose=verbose)
        company_id = new_company["id"]
        entity_cache.setdefault("companies_by_domain", {})[domain] = company_id
        counts["companies_created"] = counts.get("companies_created", 0) + 1

    # Create Draft Domain
    is_generic = domain in set(config.adam.generic_domains)
    new_domain = create_draft_domain(
        domain, company_id, domains_db_id, notion_token,
        is_generic=is_generic, verbose=verbose,
    )
    entity_cache.setdefault("domains", {})[domain] = {
        "domain_id": new_domain["id"],
        "company_id": company_id,
    }
    counts["domains_created"] = counts.get("domains_created", 0) + 1

    return company_id


# ---------------------------------------------------------------------------
# Thread handlers
# ---------------------------------------------------------------------------

def handle_new_thread(
    thread_meta: dict,
    user_label_names: list[str],
    valid_labels: set[str],
    acct,
    config: AppConfig,
    notion_token: str,
    entity_cache: dict,
    counts: dict,
    *,
    is_outbound: bool = False,
    verbose: bool = False,
) -> None:
    """Handle a new thread: create Email record + CRM wiring (Steps 1.5, 2.1-2.5)."""
    emails_db_id = config.notion.databases["emails"]
    thread_id = thread_meta["thread_id"]
    subject = thread_meta.get("subject", "(no subject)")

    # Thread ID dedup: re-check immediately before creation
    existing = lookup_email_by_thread_id(thread_id, emails_db_id, notion_token)
    time.sleep(0.05)
    if existing:
        if verbose:
            print(f"    DEDUP GATE: Record already exists for {thread_id} — routing to update")
        handle_updated_thread(thread_meta, existing, user_label_names, valid_labels, config, notion_token, entity_cache, counts, verbose=verbose)
        return

    # Determine source label
    source_label = acct.source_label
    # LinkedIn notification override
    if any("linkedin" in ln.lower() for ln in user_label_names):
        if "teams.mail.microsoft" not in (thread_meta.get("from_email") or ""):
            source_label = "LinkedIn - DMs"

    # Outbound notes stub
    email_notes = ""
    if is_outbound:
        today = datetime.now(timezone(timedelta(hours=-4))).strftime("%Y-%m-%d")
        email_notes = f"[{today}] Outbound: Adam sent — pending AI summary."

    # Create Email record (initially without contacts)
    email_record = create_email_record(
        thread_meta, user_label_names, valid_labels,
        source_label, emails_db_id, notion_token,
        email_notes=email_notes,
        verbose=verbose,
    )
    email_page_id = email_record["id"]
    counts["emails_created"] = counts.get("emails_created", 0) + 1

    # CRM wiring
    contact_ids = wire_crm_for_thread(
        thread_meta, email_page_id, source_label,
        config, notion_token, entity_cache, counts,
        is_outbound=is_outbound, verbose=verbose,
    )

    # Wire contacts to Email record
    if contact_ids:
        try:
            update_email_record(email_page_id, notion_token, contact_ids=contact_ids, verbose=verbose)
        except Exception as e:
            print(f"    WARNING: Failed to wire contacts to Email: {e}", file=sys.stderr)


def handle_updated_thread(
    thread_meta: dict,
    existing_record: dict,
    user_label_names: list[str],
    valid_labels: set[str],
    config: AppConfig,
    notion_token: str,
    entity_cache: dict,
    counts: dict,
    *,
    verbose: bool = False,
) -> None:
    """Handle updated thread: update Date, Subject sync, append notes stub (Step 1.6)."""
    page_id = existing_record["id"]
    props = existing_record.get("properties", {})
    existing_notes = extract_plain_text(props.get("Email Notes"))
    existing_subject = extract_plain_text(props.get("Email Subject"))
    gmail_subject = thread_meta.get("subject", "")
    existing_date_str = extract_date_start(props.get("Date"))

    updates: dict = {}

    # Rule 1a: Email Subject sync
    new_subject = None
    if gmail_subject and gmail_subject != existing_subject:
        new_subject = gmail_subject
        if verbose:
            print(f"    SUBJECT SYNC: \"{existing_subject}\" -> \"{gmail_subject}\"")
        counts["subjects_synced"] = counts.get("subjects_synced", 0) + 1

    # Rule 3: Update Date to latest message
    latest_date = _resolve_latest_message_date(thread_meta)

    # Determine new message count
    existing_date = None
    if existing_date_str:
        try:
            existing_date = datetime.fromisoformat(existing_date_str)
        except ValueError:
            pass

    new_msg_count = 0
    if existing_date:
        for msg in thread_meta.get("messages_meta", []):
            msg_date = _parse_internal_date(msg.get("internal_date", ""))
            if msg_date and msg_date > existing_date:
                new_msg_count += 1

    # Append notes stub for new messages
    append_notes = None
    if new_msg_count > 0:
        today = datetime.now(timezone(timedelta(hours=-4))).strftime("%Y-%m-%d")
        msg_word = "message" if new_msg_count == 1 else "messages"
        append_notes = f"[{today}] Thread update: {new_msg_count} new {msg_word} — pending AI summary."

    # Check for new labels on updated thread
    existing_labels = extract_multi_select_names(props.get("Labels"))
    new_label_names = [ln for ln in user_label_names if ln not in existing_labels]
    update_labels = None
    if new_label_names:
        update_labels = list(set(existing_labels + user_label_names))

    # Wire any new participants
    existing_contact_ids = extract_relation_ids(props.get("Contacts"))
    emails_db_id = config.notion.databases["emails"]
    new_contact_ids = wire_crm_for_thread(
        thread_meta, page_id,
        extract_plain_text(props.get("Source")),
        config, notion_token, entity_cache, counts,
        verbose=verbose,
    )
    # Merge existing + new contacts
    all_contact_ids = list(dict.fromkeys(existing_contact_ids + new_contact_ids))
    contacts_changed = set(all_contact_ids) != set(existing_contact_ids)

    try:
        update_email_record(
            page_id, notion_token,
            contact_ids=all_contact_ids if contacts_changed else None,
            new_date=latest_date,
            new_subject=new_subject,
            append_notes=append_notes,
            existing_notes=existing_notes,
            label_names=update_labels,
            valid_labels=valid_labels if update_labels else None,
            verbose=verbose,
        )
    except Exception as e:
        print(f"    WARNING: Failed to update Email record: {e}", file=sys.stderr)


def handle_resume_thread(
    thread_meta: dict,
    existing_record: dict,
    user_label_names: list[str],
    valid_labels: set[str],
    config: AppConfig,
    notion_token: str,
    entity_cache: dict,
    counts: dict,
    *,
    verbose: bool = False,
) -> None:
    """Handle partial record: fill in missing CRM wiring."""
    page_id = existing_record["id"]
    props = existing_record.get("properties", {})

    # Check what's missing
    existing_contacts = extract_relation_ids(props.get("Contacts"))
    existing_notes = extract_plain_text(props.get("Email Notes"))

    if not existing_contacts:
        # Wire contacts
        contact_ids = wire_crm_for_thread(
            thread_meta, page_id,
            extract_plain_text(props.get("Source")),
            config, notion_token, entity_cache, counts,
            verbose=verbose,
        )
        if contact_ids:
            try:
                update_email_record(page_id, notion_token, contact_ids=contact_ids, verbose=verbose)
            except Exception as e:
                print(f"    WARNING: Failed to wire contacts on resume: {e}", file=sys.stderr)

    # Subject sync
    existing_subject = extract_plain_text(props.get("Email Subject"))
    gmail_subject = thread_meta.get("subject", "")
    if gmail_subject and gmail_subject != existing_subject:
        try:
            update_email_record(page_id, notion_token, new_subject=gmail_subject, verbose=verbose)
            counts["subjects_synced"] = counts.get("subjects_synced", 0) + 1
        except Exception as e:
            print(f"    WARNING: Failed to sync subject on resume: {e}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Main sweep
# ---------------------------------------------------------------------------

def run_sweep(args: argparse.Namespace) -> None:
    config = load_config()
    notion_token = load_notion_token(config.notion.token_path)

    # Adam's aliases (lowercase)
    adam_aliases = set(config.adam.exclude_emails)

    # Determine which accounts to process
    accounts = [acct for acct in config.gmail_accounts]
    if args.account:
        accounts = [acct for acct in accounts if acct.address == args.account]
        if not accounts:
            available = [a.address for a in config.gmail_accounts]
            print(f"ERROR: Account {args.account} not in config. Available: {available}", file=sys.stderr)
            sys.exit(1)

    # Resolve Last Run timestamp
    if args.since:
        try:
            since = datetime.fromisoformat(args.since)
            if since.tzinfo is None:
                since = since.replace(tzinfo=timezone(timedelta(hours=-4)))
        except ValueError:
            print(f"ERROR: Invalid --since value: {args.since}", file=sys.stderr)
            sys.exit(1)
        if args.verbose:
            print(f"Using --since override: {since.isoformat()}")
    else:
        since = read_last_run(config, notion_token, verbose=args.verbose)

    print(f"Sweeping threads since: {since.isoformat()}")
    if args.dry_run:
        print("DRY RUN MODE — no Notion writes will be made.\n")

    # DB IDs
    emails_db_id = config.notion.databases.get("emails")
    if not emails_db_id:
        print("ERROR: No 'emails' database ID in config.", file=sys.stderr)
        sys.exit(1)

    # Fetch Labels options for parity check
    valid_labels = fetch_labels_options(emails_db_id, notion_token)
    if args.verbose:
        print(f"Valid Labels options: {sorted(valid_labels)}\n")

    # Counters
    counts = {
        "threads_scanned": 0,
        "new_labeled": 0,
        "new_auto_archived": 0,
        "new_unknown_domain": 0,
        "updated": 0,
        "resumed": 0,
        "dismissed": 0,
        "skipped": 0,
        "outbound_new": 0,
        "outbound_update": 0,
        "errors": 0,
        "labels_missing": [],
        "deduped_cross_account": 0,
        "emails_created": 0,
        "contacts_created": 0,
        "companies_created": 0,
        "domains_created": 0,
        "subjects_synced": 0,
    }

    # Batch-local entity cache (prevents duplicate creation within a run)
    entity_cache: dict = {"contacts": {}, "domains": {}, "companies_by_domain": {}}

    # Track thread IDs seen across accounts to avoid double-processing
    seen_thread_ids: set[str] = set()

    for acct in accounts:
        print(f"\n{'='*60}")
        print(f"Account: {acct.address}")
        print(f"{'='*60}")

        # Build Gmail service
        try:
            gmail_svc = build_gmail_service(acct.address, config.google)
        except Exception as e:
            print(f"ERROR: Gmail auth failed for {acct.address}: {e}", file=sys.stderr)
            counts["errors"] += 1
            continue

        # Build label map for this account
        label_map = build_label_map(gmail_svc)
        if args.verbose:
            user_labels = {k: v for k, v in label_map.items() if k not in GMAIL_SYSTEM_LABELS}
            print(f"  User labels: {len(user_labels)}")

        # Fetch threads
        thread_list = fetch_threads_since(gmail_svc, since, verbose=args.verbose)
        print(f"  Threads found: {len(thread_list)}")

        for i, thread_entry in enumerate(thread_list):
            thread_id = thread_entry["id"]

            # Cross-account dedup: skip threads already processed by another account
            if thread_id in seen_thread_ids:
                counts["deduped_cross_account"] += 1
                if args.verbose:
                    print(f"  DEDUP: {thread_id} already processed by another account")
                continue
            seen_thread_ids.add(thread_id)

            counts["threads_scanned"] += 1

            # Fetch full metadata
            thread_meta = fetch_thread_metadata(gmail_svc, thread_id)
            if not thread_meta:
                print(f"  ERROR: Could not fetch metadata for thread {thread_id}")
                counts["errors"] += 1
                continue

            subject = thread_meta.get("subject", "(no subject)")

            # Resolve user label names
            thread_label_ids = set(thread_meta["label_ids"])
            user_label_ids = [lid for lid in thread_label_ids if lid not in GMAIL_SYSTEM_LABELS]
            user_label_names = [label_map.get(lid, f"UNKNOWN({lid})") for lid in user_label_ids]

            # Labels parity check
            for label_name in user_label_names:
                if label_name not in valid_labels and not label_name.startswith("UNKNOWN("):
                    if label_name not in counts["labels_missing"]:
                        counts["labels_missing"].append(label_name)
                        print(f"  LABELS PARITY: Missing option \"{label_name}\" in Emails.Labels schema")

            # Apply skip filter (Step 1.3)
            skip, skip_reason = should_skip(thread_meta)
            if skip:
                counts["skipped"] += 1
                if args.verbose:
                    print(f"  SKIP: {thread_id} \"{subject}\" — {skip_reason}")
                continue

            # Lookup existing Email record by Thread ID (exact match)
            existing = lookup_email_by_thread_id(thread_id, emails_db_id, notion_token)
            time.sleep(0.05)  # gentle Notion rate limiting

            # Classify
            classification = classify_thread(thread_meta, existing, adam_aliases)

            # Count
            count_key = {
                Classification.NEW_LABELED: "new_labeled",
                Classification.NEW_AUTO_ARCHIVED: "new_auto_archived",
                Classification.NEW_UNKNOWN_DOMAIN: "new_unknown_domain",
                Classification.UPDATED: "updated",
                Classification.RESUME: "resumed",
                Classification.DISMISS: "dismissed",
                Classification.OUTBOUND_NEW: "outbound_new",
                Classification.OUTBOUND_UPDATE: "outbound_update",
            }.get(classification, "errors")
            counts[count_key] += 1

            # Log
            in_inbox = "INBOX" in thread_label_ids
            labels_str = ", ".join(user_label_names) if user_label_names else "(none)"
            existing_status = ""
            if existing:
                props = existing.get("properties", {})
                rec_status = extract_plain_text(props.get("Record Status"))
                existing_status = f" [record: {rec_status}]"

            if args.verbose or classification in (Classification.NEW_LABELED, Classification.NEW_UNKNOWN_DOMAIN, Classification.OUTBOUND_NEW):
                inbox_str = "inbox" if in_inbox else "archived"
                print(f"  {classification}: {thread_id} \"{subject}\" [{inbox_str}] labels=[{labels_str}]{existing_status}")
            elif classification == Classification.DISMISS:
                if args.verbose:
                    print(f"  DISMISS: {thread_id} \"{subject}\"")

            # Route to handlers
            if not args.dry_run:
                try:
                    if classification in (Classification.NEW_LABELED, Classification.NEW_AUTO_ARCHIVED, Classification.NEW_UNKNOWN_DOMAIN):
                        handle_new_thread(
                            thread_meta, user_label_names, valid_labels,
                            acct, config, notion_token, entity_cache, counts,
                            verbose=args.verbose,
                        )
                    elif classification == Classification.OUTBOUND_NEW:
                        handle_new_thread(
                            thread_meta, user_label_names, valid_labels,
                            acct, config, notion_token, entity_cache, counts,
                            is_outbound=True, verbose=args.verbose,
                        )
                    elif classification in (Classification.UPDATED, Classification.OUTBOUND_UPDATE):
                        handle_updated_thread(
                            thread_meta, existing, user_label_names, valid_labels,
                            config, notion_token, entity_cache, counts,
                            verbose=args.verbose,
                        )
                    elif classification == Classification.RESUME:
                        handle_resume_thread(
                            thread_meta, existing, user_label_names, valid_labels,
                            config, notion_token, entity_cache, counts,
                            verbose=args.verbose,
                        )
                except Exception as e:
                    print(f"  ERROR handling {thread_id}: {e}", file=sys.stderr)
                    counts["errors"] += 1

            # Throttle Gmail API
            time.sleep(0.05)

            # Progress indicator
            if (i + 1) % 50 == 0:
                print(f"  ... processed {i + 1}/{len(thread_list)} threads", file=sys.stderr)

    # Update Agent Config Last Run (live runs only)
    if not args.dry_run:
        run_summary = (
            f"{counts['emails_created']} created, "
            f"{counts['updated'] + counts['resumed']} updated/resumed, "
            f"{counts['contacts_created']} contacts, "
            f"{counts['companies_created']} companies, "
            f"{counts['domains_created']} domains, "
            f"{counts['errors']} errors."
        )
        update_last_run(config, notion_token, run_summary, verbose=args.verbose)

    # Summary
    _print_summary(counts, since, args.dry_run)


def _print_summary(counts: dict, since: datetime, dry_run: bool) -> None:
    """Print the sweep summary."""
    print(f"\n{'='*60}")
    if dry_run:
        print("POST-EMAIL SWEEP — DRY RUN SUMMARY")
    else:
        print("POST-EMAIL SWEEP COMPLETE")
    print(f"{'='*60}")
    print(f"Lookback since:          {since.isoformat()}")
    print(f"Threads scanned:         {counts['threads_scanned']}")
    print(f"  New (labeled):         {counts['new_labeled']}")
    print(f"  New (auto-archived):   {counts['new_auto_archived']}")
    print(f"  New (unknown domain):  {counts['new_unknown_domain']}")
    print(f"  Updated:               {counts['updated']}")
    print(f"  Resumed partial:       {counts['resumed']}")
    print(f"  Outbound (new):        {counts['outbound_new']}")
    print(f"  Outbound (update):     {counts['outbound_update']}")
    print(f"  Dismissed:             {counts['dismissed']}")
    print(f"  Skipped (filter):      {counts['skipped']}")
    print(f"  Errors:                {counts['errors']}")
    if counts.get("deduped_cross_account"):
        print(f"  Cross-account dedup:   {counts['deduped_cross_account']}")
    if not dry_run:
        print(f"\nCRM wiring:")
        print(f"  Emails created:        {counts.get('emails_created', 0)}")
        print(f"  Contacts created:      {counts.get('contacts_created', 0)}")
        print(f"  Companies created:     {counts.get('companies_created', 0)}")
        print(f"  Domains created:       {counts.get('domains_created', 0)}")
        print(f"  Subjects synced:       {counts.get('subjects_synced', 0)}")
    if counts.get("labels_missing"):
        print(f"\nLabels parity gaps:      {', '.join(counts['labels_missing'])}")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Post-Email sweep: classify Gmail threads and wire CRM records",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Classify threads but do not create/update Notion records",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Print detailed per-thread classification info",
    )
    parser.add_argument(
        "--since", type=str, default=None,
        help="Override Last Run with ISO 8601 timestamp (e.g. 2026-04-01)",
    )
    parser.add_argument(
        "--account", type=str, default=None,
        help="Process only this Gmail account",
    )
    args = parser.parse_args()
    run_sweep(args)


if __name__ == "__main__":
    main()
