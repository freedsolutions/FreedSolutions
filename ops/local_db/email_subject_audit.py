"""Audit and fix Email Subject drift between Notion and Gmail.

Usage:
  python ops/local_db/email_subject_audit.py                   # audit only
  python ops/local_db/email_subject_audit.py --fix             # dry-run fix
  python ops/local_db/email_subject_audit.py --fix --confirm   # live fix
  python ops/local_db/email_subject_audit.py --account adam@freedsolutions.com

Compares the Email Subject (title) on every Active Email record in Notion
against the actual Gmail thread subject from threads.get().  Prints a summary
table of mismatches.  With --fix --confirm, updates Notion titles in place.
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# Force UTF-8 output on Windows to handle emoji and special characters
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from ops.local_db.lib.config import load_config, AppConfig
from ops.local_db.lib.gmail_auth import build_gmail_service

# ---------------------------------------------------------------------------
# Notion API helpers (same pattern as gmail_filter_manager.py)
# ---------------------------------------------------------------------------

NOTION_API_VERSION = "2022-06-28"
NOTION_BASE = "https://api.notion.com/v1"


def _notion_request(path: str, token: str, body: dict | None = None, method: str | None = None) -> dict:
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
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(error_body)
            msg = detail.get("message", error_body)
        except json.JSONDecodeError:
            msg = error_body
        print(f"ERROR: Notion API {e.code} on {url}\n  {msg}", file=sys.stderr)
        raise


def _load_notion_token(config: AppConfig) -> str:
    token_path = config.notion.token_path
    if not token_path.exists():
        print(f"ERROR: Notion token file not found at {token_path}", file=sys.stderr)
        sys.exit(1)
    return token_path.read_text(encoding="utf-8").strip()


# ---------------------------------------------------------------------------
# Notion: fetch Active Email records
# ---------------------------------------------------------------------------

def fetch_active_emails(config: AppConfig) -> list[dict]:
    """Return list of {page_id, thread_id, subject, source} for Active Emails."""
    token = _load_notion_token(config)
    db_id = config.notion.databases.get("emails")
    if not db_id:
        print("ERROR: No 'emails' database ID in config.", file=sys.stderr)
        sys.exit(1)

    records: list[dict] = []
    start_cursor: str | None = None

    while True:
        body: dict = {
            "filter": {
                "property": "Record Status",
                "select": {"equals": "Active"},
            },
            "page_size": 100,
        }
        if start_cursor:
            body["start_cursor"] = start_cursor

        resp = _notion_request(f"/databases/{db_id}/query", token, body)

        for page in resp.get("results", []):
            props = page.get("properties", {})

            # Email Subject — title property
            title_parts = props.get("Email Subject", {}).get("title", [])
            subject = "".join(t.get("plain_text", "") for t in title_parts).strip()

            # Thread ID — rich_text property
            tid_parts = props.get("Thread ID", {}).get("rich_text", [])
            thread_id = "".join(t.get("plain_text", "") for t in tid_parts).strip()

            # Source — select property (to determine which mailbox)
            source_obj = props.get("Source", {}).get("select")
            source = source_obj["name"] if source_obj else ""

            records.append({
                "page_id": page["id"],
                "thread_id": thread_id,
                "subject": subject,
                "source": source,
            })

        if resp.get("has_more") and resp.get("next_cursor"):
            start_cursor = resp["next_cursor"]
        else:
            break

    return records


# ---------------------------------------------------------------------------
# Notion: update Email Subject (title)
# ---------------------------------------------------------------------------

def update_email_subject(config: AppConfig, page_id: str, new_subject: str) -> None:
    token = _load_notion_token(config)
    body = {
        "properties": {
            "Email Subject": {
                "title": [
                    {
                        "type": "text",
                        "text": {"content": new_subject},
                    }
                ]
            }
        }
    }
    _notion_request(f"/pages/{page_id}", token, body, method="PATCH")


# ---------------------------------------------------------------------------
# Gmail: get thread subject
# ---------------------------------------------------------------------------

def get_gmail_thread_subject(service, thread_id: str) -> str | None:
    """Fetch the thread subject from Gmail. Returns None if not found."""
    try:
        thread = service.users().threads().get(
            userId="me", id=thread_id, format="metadata",
            metadataHeaders=["Subject"],
        ).execute()
    except Exception as e:
        err_str = str(e)
        if "404" in err_str or "not found" in err_str.lower():
            return None
        if "429" in err_str or "rate" in err_str.lower():
            print("  Rate limited, waiting 5s...", file=sys.stderr)
            time.sleep(5)
            return get_gmail_thread_subject(service, thread_id)
        raise

    # Subject is on the first message's headers
    messages = thread.get("messages", [])
    if not messages:
        return None

    headers = messages[0].get("payload", {}).get("headers", [])
    for h in headers:
        if h.get("name", "").lower() == "subject":
            return h.get("value", "")
    return ""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Audit Email Subject drift between Notion and Gmail")
    parser.add_argument("--fix", action="store_true", help="Fix mismatches (dry-run unless --confirm)")
    parser.add_argument("--confirm", action="store_true", help="Actually execute fixes (requires --fix)")
    parser.add_argument("--account", type=str, help="Limit to a specific Gmail account")
    args = parser.parse_args()

    if args.confirm and not args.fix:
        print("ERROR: --confirm requires --fix", file=sys.stderr)
        sys.exit(1)

    config = load_config()

    # Build Gmail services for both accounts
    accounts = [acct.address for acct in config.gmail_accounts]
    if args.account:
        if args.account not in accounts:
            print(f"ERROR: Account {args.account} not in config. Available: {accounts}", file=sys.stderr)
            sys.exit(1)
        accounts = [args.account]

    gmail_services: dict[str, object] = {}
    for acct in accounts:
        print(f"Authenticating Gmail: {acct}")
        gmail_services[acct] = build_gmail_service(acct, config.google)

    # Map Source values to accounts
    source_to_account = {
        "Email - Freed Solutions": "adam@freedsolutions.com",
        "Email - Personal": "adamjfreed@gmail.com",
        "LinkedIn - DMs": "adam@freedsolutions.com",
    }

    print("\nFetching Active Email records from Notion...")
    records = fetch_active_emails(config)
    print(f"Found {len(records)} Active Email records.\n")

    matches = 0
    mismatches: list[dict] = []
    missing_thread_id = 0
    gmail_not_found = 0
    skipped_account = 0

    for i, rec in enumerate(records):
        thread_id = rec["thread_id"]
        notion_subject = rec["subject"]
        source = rec["source"]

        if not thread_id:
            print(f"MISSING_THREAD_ID: page {rec['page_id']} — \"{notion_subject}\"")
            missing_thread_id += 1
            continue

        # Determine which Gmail account to use
        account = source_to_account.get(source)
        if not account or account not in gmail_services:
            # Try both accounts
            account = None
            for acct, svc in gmail_services.items():
                gmail_subject = get_gmail_thread_subject(svc, thread_id)
                if gmail_subject is not None:
                    account = acct
                    break
                time.sleep(0.1)
            if account is None:
                print(f"GMAIL_NOT_FOUND: Thread {thread_id} — \"{notion_subject}\" (tried all accounts)")
                gmail_not_found += 1
                continue
        else:
            svc = gmail_services[account]
            gmail_subject = get_gmail_thread_subject(svc, thread_id)
            if gmail_subject is None:
                # Try the other account(s) before giving up
                found = False
                for other_acct, other_svc in gmail_services.items():
                    if other_acct == account:
                        continue
                    gmail_subject = get_gmail_thread_subject(other_svc, thread_id)
                    if gmail_subject is not None:
                        found = True
                        break
                    time.sleep(0.1)
                if not found:
                    print(f"GMAIL_NOT_FOUND: Thread {thread_id} — \"{notion_subject}\"")
                    gmail_not_found += 1
                    continue

        if notion_subject == gmail_subject:
            matches += 1
        else:
            print(f"MISMATCH: Thread {thread_id} — Notion: \"{notion_subject}\" | Gmail: \"{gmail_subject}\"")
            mismatches.append({
                "page_id": rec["page_id"],
                "thread_id": thread_id,
                "notion_subject": notion_subject,
                "gmail_subject": gmail_subject,
            })

        # Throttle to avoid Gmail rate limits
        time.sleep(0.1)

        # Progress indicator every 25 records
        if (i + 1) % 25 == 0:
            print(f"  ... checked {i + 1}/{len(records)}", file=sys.stderr)

    # Summary
    print("\n" + "=" * 80)
    print("AUDIT SUMMARY")
    print("=" * 80)
    print(f"Total Active records checked:  {len(records)}")
    print(f"  Matches:                     {matches}")
    print(f"  Mismatches:                  {len(mismatches)}")
    print(f"  Missing Thread ID:           {missing_thread_id}")
    print(f"  Gmail thread not found:      {gmail_not_found}")
    print(f"  Skipped (wrong account):     {skipped_account}")

    if mismatches:
        print(f"\n{'='*80}")
        print("MISMATCHES")
        print(f"{'='*80}")
        for m in mismatches:
            print(f"\n  Thread ID: {m['thread_id']}")
            print(f"  Notion:    \"{m['notion_subject']}\"")
            print(f"  Gmail:     \"{m['gmail_subject']}\"")
            print(f"  Page ID:   {m['page_id']}")

    # Fix mode
    if args.fix and mismatches:
        print(f"\n{'='*80}")
        if args.confirm:
            print(f"FIXING {len(mismatches)} mismatches...")
        else:
            print(f"DRY RUN — would fix {len(mismatches)} mismatches (add --confirm to execute)")
        print(f"{'='*80}")

        for m in mismatches:
            old = m["notion_subject"]
            new = m["gmail_subject"]
            if args.confirm:
                try:
                    update_email_subject(config, m["page_id"], new)
                    print(f"FIXED: Thread {m['thread_id']} — \"{old}\" -> \"{new}\"")
                    time.sleep(0.2)  # Gentle rate limiting for Notion writes
                except Exception as e:
                    print(f"FAILED: Thread {m['thread_id']} — {e}", file=sys.stderr)
            else:
                print(f"WOULD FIX: Thread {m['thread_id']} — \"{old}\" -> \"{new}\"")

    print("\nDone.")


if __name__ == "__main__":
    main()
