"""Gmail filter audit and management against the Notion Companies CRM.

Usage:
  python ops/local_db/gmail_filter_manager.py                           # audit (notion-domains)
  python ops/local_db/gmail_filter_manager.py --source notion-companies # audit (legacy)
  python ops/local_db/gmail_filter_manager.py --create                  # dry-run create
  python ops/local_db/gmail_filter_manager.py --create --confirm        # live create
  python ops/local_db/gmail_filter_manager.py --cleanup                 # dry-run cleanup
  python ops/local_db/gmail_filter_manager.py --cleanup --confirm       # live cleanup
  python ops/local_db/gmail_filter_manager.py --account user@example.com

Prerequisites:
  - Place your Google OAuth client-secrets JSON at the path specified by
    google.credentials_path in ops/local_db/config.yaml (default:
    ops/local_db/credentials/google_oauth_credentials.json).
  - Place your Notion integration token at the path specified by
    notion.token_path in ops/local_db/config.yaml (default:
    ops/local_db/credentials/notion_token.txt).
  - On first run, the script opens a browser for Google OAuth consent.
    The resulting token is saved per-account (e.g. token-adam_freedsolutions_com.json).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path

# Ensure repo root is importable
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from ops.local_db.lib.config import load_config, AppConfig, split_csv_text
from ops.local_db.lib.gmail_auth import build_gmail_service

# ---------------------------------------------------------------------------
# Notion API helpers (stdlib only — no requests dependency)
# ---------------------------------------------------------------------------

NOTION_API_VERSION = "2022-06-28"
NOTION_BASE = "https://api.notion.com/v1"


def _notion_request(path: str, token: str, body: dict | None = None) -> dict:
    url = f"{NOTION_BASE}{path}"
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": NOTION_API_VERSION,
            "Content-Type": "application/json",
        },
        method="POST" if data else "GET",
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
        print("Place your Notion integration token in that file and retry.", file=sys.stderr)
        sys.exit(1)
    return token_path.read_text(encoding="utf-8").strip()


# ---------------------------------------------------------------------------
# Notion: fetch Active + Draft companies with domains
# ---------------------------------------------------------------------------

def fetch_companies(config: AppConfig) -> list[dict]:
    """Return list of {name, domains, additional_domains, status} dicts."""
    token = _load_notion_token(config)
    db_id = config.notion.databases.get("companies")
    if not db_id:
        print("ERROR: No 'companies' database ID in config.", file=sys.stderr)
        sys.exit(1)

    companies: list[dict] = []
    start_cursor: str | None = None

    while True:
        body: dict = {
            "filter": {
                "property": "Record Status",
                "select": {"is_not_empty": True},
            },
            "page_size": 100,
        }
        if start_cursor:
            body["start_cursor"] = start_cursor

        resp = _notion_request(f"/databases/{db_id}/query", token, body)

        for page in resp.get("results", []):
            props = page.get("properties", {})

            # Company Name — title property
            name_parts = props.get("Company Name", {}).get("title", [])
            name = "".join(t.get("plain_text", "") for t in name_parts).strip()

            # Record Status — select
            status_obj = props.get("Record Status", {}).get("select")
            status = status_obj["name"] if status_obj else ""

            # Only Active and Draft
            if status not in ("Active", "Draft"):
                continue

            # Domains — rich_text (comma or newline separated)
            domains_text = "".join(
                t.get("plain_text", "")
                for t in props.get("Domains", {}).get("rich_text", [])
            ).strip()
            domains = [
                d.strip().lower()
                for d in split_csv_text(domains_text)
            ]

            # Additional Domains — rich_text (comma or newline separated)
            additional_text = "".join(
                t.get("plain_text", "")
                for t in props.get("Additional Domains", {}).get("rich_text", [])
            ).strip()
            additional = [
                d.strip().lower()
                for d in split_csv_text(additional_text)
            ]

            companies.append({
                "page_id": page["id"],
                "name": name,
                "domains": domains,
                "additional_domains": additional,
                "status": status,
            })

        if resp.get("has_more") and resp.get("next_cursor"):
            start_cursor = resp["next_cursor"]
        else:
            break

    return companies


# ---------------------------------------------------------------------------
# Domain extraction helpers
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"^[^@]+@(.+)$")


def extract_domain(entry: str) -> str | None:
    """Return the domain portion. If entry is a bare domain, return it.
    If it's a full email, return the domain after @."""
    entry = entry.strip().lower()
    m = _EMAIL_RE.match(entry)
    if m:
        return m.group(1)
    # Bare domain (contains a dot, no @)
    if "." in entry:
        return entry
    return None


def is_full_email(entry: str) -> bool:
    return "@" in entry


def build_domain_map(
    companies: list[dict], generic_domains: set[str]
) -> tuple[dict[str, str], list[tuple[str, str]]]:
    """Returns (domain -> company_name map, generic_flagged list).

    Entries that are full emails at generic domains are skipped for filter
    purposes but included in generic_flagged for reporting.
    """
    domain_to_company: dict[str, str] = {}
    generic_flagged: list[tuple[str, str]] = []  # (entry, company_name)

    for company in companies:
        name = company["name"]
        all_entries = company["domains"] + company["additional_domains"]

        for entry in all_entries:
            domain = extract_domain(entry)
            if not domain:
                continue

            if domain in generic_domains:
                generic_flagged.append((entry, name))
                continue

            # Full email at a non-generic domain — still extract the domain
            # for matching, but record the entry for reporting
            if domain not in domain_to_company:
                domain_to_company[domain] = name

    return domain_to_company, generic_flagged


# ---------------------------------------------------------------------------
# Gmail helpers
# ---------------------------------------------------------------------------

def fetch_gmail_filters(service) -> list[dict]:
    resp = service.users().settings().filters().list(userId="me").execute()
    return resp.get("filter", [])


def fetch_gmail_labels(service) -> dict[str, str]:
    """Return {label_id: label_name} map."""
    resp = service.users().labels().list(userId="me").execute()
    return {lbl["id"]: lbl["name"] for lbl in resp.get("labels", [])}


def extract_filter_domains(gmail_filter: dict) -> list[str]:
    """Extract domains from a filter's from criteria."""
    criteria = gmail_filter.get("criteria", {})
    from_val = criteria.get("from", "")
    if not from_val:
        return []

    domains = []
    # Patterns: *@domain, @domain, {*@d1 *@d2}
    # Strip curly braces for OR-groups
    cleaned = from_val.strip().strip("{}")
    for part in cleaned.split():
        part = part.strip().lower()
        # Remove leading *@ or @
        if part.startswith("*@"):
            domains.append(part[2:])
        elif part.startswith("@"):
            domains.append(part[1:])
        elif "." in part and "@" not in part:
            # bare domain
            domains.append(part)
    return domains


def create_gmail_label(service, label_name: str) -> str:
    """Create a Gmail label and return its ID."""
    body = {
        "name": label_name,
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show",
    }
    result = service.users().labels().create(userId="me", body=body).execute()
    return result["id"]


def create_gmail_filter(service, domain: str, label_id: str) -> dict:
    """Create a Gmail filter: from:*@domain -> apply label (no archive)."""
    body = {
        "criteria": {"from": f"*@{domain}"},
        "action": {"addLabelIds": [label_id]},
    }
    return service.users().settings().filters().create(userId="me", body=body).execute()


# ---------------------------------------------------------------------------
# Reconciliation
# ---------------------------------------------------------------------------

def reconcile(
    domain_to_company: dict[str, str],
    gmail_filters: list[dict],
    label_map: dict[str, str],
) -> dict[str, list]:
    """Cross-reference Notion domains against Gmail filters.

    Returns dict with keys: matched, notion_only, gmail_only, label_missing.
    Each value is a list of info dicts.
    """
    # Build filter-domain -> filter info map
    label_name_to_id = {v: k for k, v in label_map.items()}
    filter_domain_map: dict[str, dict] = {}  # domain -> filter info

    for gf in gmail_filters:
        filter_id = gf.get("id", "")
        action = gf.get("action", {})
        label_ids = action.get("addLabelIds", [])
        label_names = [label_map.get(lid, f"UNKNOWN({lid})") for lid in label_ids]
        missing_labels = [lid for lid in label_ids if lid not in label_map]

        for domain in extract_filter_domains(gf):
            filter_domain_map[domain] = {
                "filter_id": filter_id,
                "label_names": label_names,
                "label_ids": label_ids,
                "missing_label_ids": missing_labels,
                "criteria_from": gf.get("criteria", {}).get("from", ""),
            }

    all_notion_domains = set(domain_to_company.keys())
    all_filter_domains = set(filter_domain_map.keys())

    matched = []
    notion_only = []
    label_missing = []

    for domain in sorted(all_notion_domains):
        company = domain_to_company[domain]
        if domain in filter_domain_map:
            info = filter_domain_map[domain]
            entry = {"domain": domain, "company": company, **info}
            if info["missing_label_ids"]:
                label_missing.append(entry)
            else:
                matched.append(entry)
        else:
            notion_only.append({"domain": domain, "company": company})

    gmail_only = []
    for domain in sorted(all_filter_domains - all_notion_domains):
        info = filter_domain_map[domain]
        gmail_only.append({"domain": domain, **info})

    return {
        "matched": matched,
        "notion_only": notion_only,
        "gmail_only": gmail_only,
        "label_missing": label_missing,
    }


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def print_table(title: str, rows: list[dict], columns: list[tuple[str, str, int]]):
    """Print a simple formatted table.

    columns: list of (header, dict_key, width).
    """
    if not rows:
        print(f"\n{title}: (none)")
        return

    print(f"\n{title} ({len(rows)}):")
    header = "  ".join(h.ljust(w) for h, _, w in columns)
    print(f"  {header}")
    print(f"  {'-' * len(header)}")
    for row in rows:
        line = "  ".join(str(row.get(k, "")).ljust(w) for _, k, w in columns)
        print(f"  {line}")


def print_report(results: dict, generic_flagged: list[tuple[str, str]]):
    print("=" * 72)
    print("  GMAIL FILTER RECONCILIATION REPORT")
    print("=" * 72)

    print_table("MATCHED (domain has filter + label)", results["matched"], [
        ("Domain", "domain", 30),
        ("Company", "company", 30),
        ("Labels", "label_names", 40),
    ])

    print_table("NOTION ONLY (domain in CRM, no Gmail filter)", results["notion_only"], [
        ("Domain", "domain", 30),
        ("Company", "company", 40),
    ])

    print_table("GMAIL ONLY (filter exists, no matching Company)", results["gmail_only"], [
        ("Domain", "domain", 30),
        ("Filter From", "criteria_from", 30),
        ("Labels", "label_names", 40),
    ])

    print_table("LABEL MISSING (filter references nonexistent label)", results["label_missing"], [
        ("Domain", "domain", 30),
        ("Company", "company", 30),
        ("Missing IDs", "missing_label_ids", 40),
    ])

    if generic_flagged:
        print(f"\nGENERIC DOMAIN ENTRIES ({len(generic_flagged)}):")
        print("  These are at generic domains and should NOT have filters:")
        for entry, company in generic_flagged:
            print(f"  - {entry:30s}  ({company})")
    else:
        print("\nGENERIC DOMAIN ENTRIES: (none)")

    # Summary
    print("\n" + "-" * 72)
    print(f"  Matched: {len(results['matched'])}  |  "
          f"Notion Only: {len(results['notion_only'])}  |  "
          f"Gmail Only: {len(results['gmail_only'])}  |  "
          f"Label Missing: {len(results['label_missing'])}  |  "
          f"Generic: {len(generic_flagged)}")
    print("-" * 72)


# ---------------------------------------------------------------------------
# Create mode
# ---------------------------------------------------------------------------

def run_create(
    notion_only: list[dict],
    service,
    label_map: dict[str, str],
    generic_domains: set[str],
    confirm: bool,
):
    """Create Gmail labels and filters for NOTION ONLY domains."""
    label_name_to_id = {v: k for k, v in label_map.items()}

    if not notion_only:
        print("\nNo NOTION ONLY domains to create filters for.")
        return

    print(f"\n{'CREATING' if confirm else 'DRY RUN — would create'} "
          f"filters for {len(notion_only)} domains:\n")

    created = 0
    skipped = 0

    for entry in notion_only:
        domain = entry["domain"]
        company = entry["company"]

        if domain in generic_domains:
            print(f"  SKIP (generic): {domain} ({company})")
            skipped += 1
            continue

        # Resolve or create label
        label_id = label_name_to_id.get(company)

        if confirm:
            if not label_id:
                print(f"  CREATE LABEL: {company}")
                label_id = create_gmail_label(service, company)
                label_name_to_id[company] = label_id

            print(f"  CREATE FILTER: from:*@{domain} -> label:{company}")
            create_gmail_filter(service, domain, label_id)
            created += 1
        else:
            label_action = "exists" if label_id else "WOULD CREATE"
            print(f"  WOULD CREATE: label:{company} ({label_action}), "
                  f"filter from:*@{domain}")
            created += 1

    print(f"\n  {'Created' if confirm else 'Would create'}: {created}  |  Skipped: {skipped}")
    if not confirm and created > 0:
        print("\n  Re-run with --create --confirm to execute.")


# ---------------------------------------------------------------------------
# Domains DB source (--source notion-domains)
# ---------------------------------------------------------------------------

def fetch_domains_db(config: AppConfig) -> list[dict]:
    """Fetch all Domain records from the Domains DB."""
    token = _load_notion_token(config)
    db_id = config.notion.databases.get("domains")
    if not db_id:
        print("ERROR: No 'domains' database ID in config.", file=sys.stderr)
        sys.exit(1)

    domains: list[dict] = []
    start_cursor: str | None = None

    while True:
        body: dict = {"page_size": 100}
        if start_cursor:
            body["start_cursor"] = start_cursor

        resp = _notion_request(f"/databases/{db_id}/query", token, body)

        for page in resp.get("results", []):
            props = page.get("properties", {})

            title_parts = props.get("Domain", {}).get("title", [])
            domain = "".join(t.get("plain_text", "") for t in title_parts).strip()

            routing_select = props.get("Routing Tier", {}).get("select")
            routing_tier = routing_select["name"] if routing_select else ""

            shape_select = props.get("Filter Shape", {}).get("select")
            filter_shape = shape_select["name"] if shape_select else ""

            status_select = props.get("Record Status", {}).get("select")
            record_status = status_select["name"] if status_select else ""

            is_generic = props.get("Is Generic", {}).get("checkbox", False)

            gmail_filter_text = "".join(
                t.get("plain_text", "")
                for t in props.get("Gmail Filter ID", {}).get("rich_text", [])
            ).strip()

            gmail_label_text = "".join(
                t.get("plain_text", "")
                for t in props.get("Gmail Label", {}).get("rich_text", [])
            ).strip()

            domains.append({
                "page_id": page["id"],
                "domain": domain,
                "routing_tier": routing_tier,
                "filter_shape": filter_shape,
                "record_status": record_status,
                "is_generic": is_generic,
                "gmail_filter_id": gmail_filter_text,
                "gmail_label": gmail_label_text,
            })

        if resp.get("has_more") and resp.get("next_cursor"):
            start_cursor = resp["next_cursor"]
        else:
            break

    return domains


def _update_domain_filter_id(config: AppConfig, page_id: str, filter_id: str):
    """Write Gmail Filter ID back to a Domain record."""
    token = _load_notion_token(config)
    url = f"{NOTION_BASE}/pages/{page_id}"
    body = {
        "properties": {
            "Gmail Filter ID": {
                "rich_text": [{"text": {"content": filter_id}}],
            },
        },
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": NOTION_API_VERSION,
            "Content-Type": "application/json",
        },
        method="PATCH",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        print(f"ERROR: Notion PATCH {e.code} on {url}\n  {error_body}", file=sys.stderr)
        raise


def _tier_filter_action_desc(tier: str) -> str:
    """Human-readable description of what a filter does for this tier."""
    descs = {
        "Label": "label only (inbox, unread)",
        "Silent Label": "label + skip inbox",
        "Archive": "label + skip inbox",
        "Block": "trash",
    }
    return descs.get(tier, tier)


def _build_filter_action(tier: str, label_id: str | None) -> dict | None:
    """Build the Gmail filter action dict for a given tier.

    Returns None for Draft Intake (no filter should be created).

    Note: Silent Label and Archive produce identical Gmail filter mechanics
    (label + removeLabelIds: INBOX). The distinction drives Post-Email agent
    behavior — Silent Label means the agent processes the thread automatically,
    while Archive means the thread is stored but not agent-processed.
    """
    if tier == "Draft Intake":
        return None
    if tier == "Label":
        return {"addLabelIds": [label_id]}
    if tier in ("Silent Label", "Archive"):
        return {"addLabelIds": [label_id], "removeLabelIds": ["INBOX"]}
    if tier == "Block":
        action: dict = {"removeLabelIds": ["INBOX"], "addLabelIds": ["TRASH"]}
        return action
    return None


def run_create_from_domains(
    domain_records: list[dict],
    service,
    label_map: dict[str, str],
    config: AppConfig,
    confirm: bool,
):
    """Create Gmail filters using the Domains DB as source."""
    label_name_to_id = {v: k for k, v in label_map.items()}

    # Only create for records that need filters.
    # Generic domains are allowed when Filter Shape = Sender (from:user@domain
    # is safe — it targets a specific sender, not the whole domain).
    _filterable = [
        d for d in domain_records
        if not d["gmail_filter_id"]
        and (not d["is_generic"] or d["filter_shape"] == "Sender")
        and d["filter_shape"] != "None"
        and d["routing_tier"] not in ("Draft Intake", "None")
    ]

    # Gate: only Active records get filters created.
    candidates = [d for d in _filterable if d["record_status"] == "Active"]
    draft_skipped = [d for d in _filterable if d["record_status"] != "Active"]

    # Log skipped Draft records
    if draft_skipped:
        print(f"\nSKIPPED (Draft): {len(draft_skipped)} domain(s) — "
              "promote to Active to create filter:")
        for d in draft_skipped:
            print(f"  SKIPPED (Draft): {d['domain']} — promote to Active to create filter")

    if not candidates:
        if not draft_skipped:
            print("\nNo Domain records need new Gmail filters.")
        return

    print(f"\n{'CREATING' if confirm else 'DRY RUN — would create'} "
          f"filters for {len(candidates)} domains:\n")

    created = 0
    for entry in candidates:
        domain = entry["domain"]
        label_name = entry["gmail_label"] or domain
        shape = entry["filter_shape"]
        tier = entry["routing_tier"]

        # Build from: criteria based on Filter Shape
        if shape == "Sender":
            from_criteria = domain  # full email address
        else:
            from_criteria = f"*@{domain}"

        label_id = label_name_to_id.get(label_name)

        action_desc = _tier_filter_action_desc(tier)

        if confirm:
            if tier != "Block" and not label_id:
                print(f"  CREATE LABEL: {label_name}")
                label_id = create_gmail_label(service, label_name)
                label_name_to_id[label_name] = label_id

            action = _build_filter_action(tier, label_id)
            if not action:
                continue

            filter_body: dict = {
                "criteria": {"from": from_criteria},
                "action": action,
            }

            print(f"  CREATE FILTER: from:{from_criteria} -> {action_desc}")
            result = service.users().settings().filters().create(
                userId="me", body=filter_body
            ).execute()

            new_filter_id = result.get("id", "")
            if new_filter_id:
                _update_domain_filter_id(config, entry["page_id"], new_filter_id)
                print(f"    -> Filter ID {new_filter_id} written to Domain record")

            created += 1
        else:
            label_action = "exists" if label_id else "WOULD CREATE"
            print(f"  WOULD CREATE: label:{label_name} ({label_action}), "
                  f"filter from:{from_criteria} -> {action_desc}")
            created += 1

    print(f"\n  {'Created' if confirm else 'Would create'}: {created}")
    if not confirm and created > 0:
        print("\n  Re-run with --create --confirm to execute.")


# ---------------------------------------------------------------------------
# Cleanup mode — apply tier actions retroactively to existing threads
# ---------------------------------------------------------------------------

import time


def _expand_threads_to_messages(service, thread_ids: list[str]) -> list[str]:
    """Expand thread IDs to message IDs via threads.get(format=minimal)."""
    message_ids: list[str] = []
    for tid in thread_ids:
        thread = service.users().threads().get(
            userId="me", id=tid, format="minimal"
        ).execute()
        for msg in thread.get("messages", []):
            message_ids.append(msg["id"])
    return message_ids


def _search_threads(service, query: str) -> list[str]:
    """Return all thread IDs matching the Gmail search query."""
    thread_ids: list[str] = []
    page_token: str | None = None
    while True:
        resp = service.users().threads().list(
            userId="me", q=query, pageToken=page_token
        ).execute()
        for t in resp.get("threads", []):
            thread_ids.append(t["id"])
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return thread_ids


def _batch_modify_messages(
    service, message_ids: list[str], add_label_ids: list[str],
    remove_label_ids: list[str], confirm: bool,
) -> int:
    """Batch-modify messages in chunks of 1000. Returns count modified."""
    if not message_ids:
        return 0
    modified = 0
    for i in range(0, len(message_ids), 1000):
        chunk = message_ids[i:i + 1000]
        body: dict = {"ids": chunk}
        if add_label_ids:
            body["addLabelIds"] = add_label_ids
        if remove_label_ids:
            body["removeLabelIds"] = remove_label_ids
        if confirm:
            service.users().messages().batchModify(userId="me", body=body).execute()
        modified += len(chunk)
    return modified


def run_cleanup(
    domain_records: list[dict],
    service,
    label_map: dict[str, str],
    config: AppConfig,
    confirm: bool,
):
    """Apply tier actions retroactively to existing Gmail threads."""
    label_name_to_id = {v: k for k, v in label_map.items()}

    # Domains that require content-conditional routing (multiple Gmail filters
    # with different labels based on subject/query/to patterns). The script's
    # per-domain single-label model can't express these, so cleanup skips them.
    CLEANUP_SKIP_DOMAINS = {"primitivgroup.com"}

    # Candidates: non-Draft-Intake, non-None tier, non-None shape, non-generic
    candidates = [
        d for d in domain_records
        if d["routing_tier"] not in ("Draft Intake", "", "None")
        and d["filter_shape"] != "None"
        and not d["is_generic"]
        and d["domain"].lower() not in CLEANUP_SKIP_DOMAINS
    ]

    if not candidates:
        print("\nNo Domain records need cleanup.")
        return

    print(f"\n{'CLEANUP' if confirm else 'DRY RUN — cleanup'} "
          f"for {len(candidates)} domains:\n")

    total_threads = 0
    total_messages = 0

    for entry in candidates:
        domain = entry["domain"]
        shape = entry["filter_shape"]
        tier = entry["routing_tier"]
        label_name = entry["gmail_label"] or domain

        # Build search query
        if shape == "Sender":
            query = f"from:{domain}"
        else:
            query = f"from:*@{domain}"

        # Search for matching threads
        thread_ids = _search_threads(service, query)
        if not thread_ids:
            continue

        # Expand to message IDs
        message_ids = _expand_threads_to_messages(service, thread_ids)
        if not message_ids:
            continue

        total_threads += len(thread_ids)
        total_messages += len(message_ids)

        # Determine actions based on tier
        add_labels: list[str] = []
        remove_labels: list[str] = []
        action_desc = _tier_filter_action_desc(tier)

        if tier == "Block":
            add_labels = ["TRASH"]
            remove_labels = ["INBOX"]
        else:
            # Label, Silent Label, Archive all get the label applied
            label_id = label_name_to_id.get(label_name)
            if not label_id and confirm:
                print(f"  CREATE LABEL: {label_name}")
                label_id = create_gmail_label(service, label_name)
                label_name_to_id[label_name] = label_id
            if label_id:
                add_labels.append(label_id)

            # Silent Label and Archive: also remove from inbox
            if tier in ("Silent Label", "Archive"):
                remove_labels.append("INBOX")
                remove_labels.append("UNREAD")

        print(f"  {domain:<40} {len(thread_ids):>4} threads  "
              f"{len(message_ids):>5} msgs  -> {action_desc}")

        if confirm:
            _batch_modify_messages(
                service, message_ids, add_labels, remove_labels, confirm=True
            )
            # Rate limit: pause between domains
            time.sleep(1)

    print(f"\n  Total: {total_threads} threads, {total_messages} messages")
    if not confirm and total_threads > 0:
        print("  Re-run with --cleanup --confirm to execute.")


# ---------------------------------------------------------------------------
# Dedup mode — remove old filters where a Domains-DB-managed filter exists
# ---------------------------------------------------------------------------


def _is_complex_filter(gf: dict) -> bool:
    """Return True if the filter uses patterns the script can't express."""
    criteria = gf.get("criteria", {})
    if criteria.get("subject") or criteria.get("query") or criteria.get("hasAttachment"):
        return True
    if criteria.get("negatedQuery"):
        return True
    from_q = criteria.get("from", "")
    to_q = criteria.get("to", "")
    # Dual from+to criteria or multi-domain OR in from:
    if from_q and to_q:
        return True
    if " OR " in from_q:
        return True
    return False


def _extract_from_domains(gf: dict) -> list[str]:
    """Extract domains from a filter's from: criteria, handling *@ and @ and full emails."""
    criteria = gf.get("criteria", {})
    from_val = criteria.get("from", "")
    if not from_val:
        return []
    domains = []
    cleaned = from_val.strip().strip("{}")
    for part in cleaned.split():
        part = part.strip().lower()
        if part.startswith("*@"):
            domains.append(part[2:])
        elif part.startswith("@"):
            domains.append(part[1:])
        elif "@" in part:
            # Full email like systems@thccrafts.com → extract domain AND keep full email
            at_pos = part.index("@")
            domains.append(part[at_pos + 1:])
            domains.append(part)  # also match the full email
        elif "." in part:
            domains.append(part)
    return domains


def run_dedup(
    domain_records: list[dict],
    gmail_filters: list[dict],
    label_map: dict[str, str],
    service,
    confirm: bool,
):
    """Identify and remove old duplicate filters where a Domains-DB-managed filter exists."""
    id_to_name = label_map
    name_to_id = {v: k for k, v in label_map.items()}

    # Build managed filter set from Domains DB
    managed_ids: set[str] = set()
    managed_domains: dict[str, dict] = {}  # domain_or_email -> record
    for d in domain_records:
        fid = d["gmail_filter_id"]
        if fid:
            managed_ids.add(fid)
        domain = d["domain"].lower()
        if d["filter_shape"] != "None" and d["routing_tier"] != "Draft Intake":
            managed_domains[domain] = d

    print(f"  Domains DB: {len(domain_records)} records, "
          f"{len(managed_ids)} with Gmail Filter ID, "
          f"{len(managed_domains)} filterable domains.")
    print(f"  Gmail: {len(gmail_filters)} filters.\n")

    # Classify filters
    managed = []          # script-created, tracked in Domains DB
    duplicates = []       # old filter with a managed equivalent for same domain
    complex_kept = []     # complex filters the script can't express
    to_mirrors = []       # to: counterpart filters
    unmanaged_unique = [] # old filter with NO managed equivalent

    for gf in gmail_filters:
        fid = gf["id"]
        criteria = gf.get("criteria", {})
        action = gf.get("action", {})
        from_q = criteria.get("from", "")
        to_q = criteria.get("to", "")
        label_ids = action.get("addLabelIds", [])
        label_names = [id_to_name.get(lid, lid) for lid in label_ids]

        # 1. Script-managed filter?
        if fid in managed_ids:
            managed.append(gf)
            continue

        # 2. Pure to: filter (no from:)?
        if to_q and not from_q:
            to_mirrors.append(gf)
            continue

        # 3. Complex filter?
        if _is_complex_filter(gf):
            complex_kept.append(gf)
            continue

        # 4. Simple from: filter — check if a managed filter covers same domain
        filter_domains = _extract_from_domains(gf)
        is_dup = False
        for fd in filter_domains:
            if fd in managed_domains:
                is_dup = True
                break
        if is_dup:
            duplicates.append(gf)
        else:
            unmanaged_unique.append(gf)

    # Report
    print(f"CLASSIFICATION:")
    print(f"  Managed (Domains DB):     {len(managed)}")
    print(f"  Duplicate (old, remove):  {len(duplicates)}")
    print(f"  Complex (keep):           {len(complex_kept)}")
    print(f"  to: mirrors:              {len(to_mirrors)}")
    print(f"  Unmanaged unique:         {len(unmanaged_unique)}")

    if duplicates:
        print(f"\n{'DELETING' if confirm else 'DRY RUN — would delete'} "
              f"{len(duplicates)} duplicate old filters:\n")
        for gf in duplicates:
            fid = gf["id"]
            from_q = gf.get("criteria", {}).get("from", "")
            labels = [id_to_name.get(lid, lid) for lid in gf.get("action", {}).get("addLabelIds", [])]
            remove = [id_to_name.get(lid, lid) for lid in gf.get("action", {}).get("removeLabelIds", [])]
            desc = f"from:{from_q} -> {labels}"
            if remove:
                desc += f" remove:{remove}"
            if confirm:
                service.users().settings().filters().delete(userId="me", id=fid).execute()
                print(f"  DELETED: {desc} (id={fid})")
            else:
                print(f"  WOULD DELETE: {desc} (id={fid})")

    if to_mirrors:
        print(f"\nto: MIRROR FILTERS ({len(to_mirrors)}):")
        for gf in to_mirrors:
            to_q = gf.get("criteria", {}).get("to", "")
            labels = [id_to_name.get(lid, lid) for lid in gf.get("action", {}).get("addLabelIds", [])]
            print(f"  to:{to_q} -> {labels} (id={gf['id']})")

    if complex_kept:
        print(f"\nCOMPLEX FILTERS KEPT ({len(complex_kept)}):")
        for gf in complex_kept:
            criteria = gf.get("criteria", {})
            parts = []
            if criteria.get("from"): parts.append(f"from:{criteria['from']}")
            if criteria.get("to"): parts.append(f"to:{criteria['to']}")
            if criteria.get("subject"): parts.append(f"subject:{criteria['subject']}")
            if criteria.get("query"): parts.append(f"query:{criteria['query']}")
            if criteria.get("hasAttachment"): parts.append("hasAttachment")
            if criteria.get("negatedQuery"): parts.append(f"neg:{criteria['negatedQuery']}")
            labels = [id_to_name.get(lid, lid) for lid in gf.get("action", {}).get("addLabelIds", [])]
            print(f"  {' | '.join(parts)} -> {labels}")

    if unmanaged_unique:
        print(f"\nUNMANAGED UNIQUE ({len(unmanaged_unique)}) — no Domains DB equivalent:")
        for gf in unmanaged_unique:
            from_q = gf.get("criteria", {}).get("from", "")
            labels = [id_to_name.get(lid, lid) for lid in gf.get("action", {}).get("addLabelIds", [])]
            print(f"  from:{from_q} -> {labels} (id={gf['id']})")

    if not confirm and duplicates:
        print(f"\n  Re-run with --dedup --confirm to delete {len(duplicates)} duplicates.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Audit and manage Gmail filters against Notion Companies CRM."
    )
    action_group = parser.add_mutually_exclusive_group()
    action_group.add_argument(
        "--create", action="store_true",
        help="Create missing filters (dry-run unless --confirm is also passed)."
    )
    action_group.add_argument(
        "--cleanup", action="store_true",
        help="Apply tier actions retroactively to existing threads (dry-run unless --confirm)."
    )
    action_group.add_argument(
        "--create-labels", nargs="+", metavar="LABEL",
        help="Create one or more Gmail labels (no filters). E.g. --create-labels Personal 'My Network'"
    )
    action_group.add_argument(
        "--dedup", action="store_true",
        help="Find and remove old duplicate filters where a Domains-DB-managed filter exists for the same domain."
    )
    parser.add_argument(
        "--confirm", action="store_true",
        help="Actually execute creates/cleanup (requires --create or --cleanup)."
    )
    parser.add_argument(
        "--account", default="adam@freedsolutions.com",
        help="Gmail account to manage (default: adam@freedsolutions.com)."
    )
    parser.add_argument(
        "--source", choices=["notion-domains", "notion-companies"],
        default="notion-domains",
        help="Data source: notion-domains (default) or notion-companies (legacy)."
    )
    args = parser.parse_args()

    if args.confirm and not args.create and not args.cleanup and not args.dedup:
        parser.error("--confirm requires --create, --cleanup, or --dedup")

    config = load_config()
    generic_domains = set(config.adam.generic_domains)

    # Build Gmail service
    print(f"Connecting to Gmail as {args.account}...")
    service = build_gmail_service(args.account, config.google)

    # --create-labels: standalone label creation, then exit
    if args.create_labels:
        label_map = fetch_gmail_labels(service)
        name_to_id = {v: k for k, v in label_map.items()}
        for label_name in args.create_labels:
            if label_name in name_to_id:
                print(f"  Label already exists: {label_name!r} (id={name_to_id[label_name]})")
            else:
                label_id = create_gmail_label(service, label_name)
                print(f"  Created label: {label_name!r} (id={label_id})")
        return

    # --dedup: standalone duplicate removal, then exit
    if args.dedup:
        print("Fetching Domains DB and Gmail filters for dedup analysis...")
        domain_records = fetch_domains_db(config)
        gmail_filters = fetch_gmail_filters(service)
        label_map = fetch_gmail_labels(service)
        run_dedup(domain_records, gmail_filters, label_map, service, args.confirm)
        return

    print("Fetching Gmail filters and labels...")
    gmail_filters = fetch_gmail_filters(service)
    label_map = fetch_gmail_labels(service)
    print(f"  Found {len(gmail_filters)} filters, {len(label_map)} labels.")

    if args.source == "notion-domains":
        # Domains DB source
        print("Fetching domains from Notion Domains DB...")
        domain_records = fetch_domains_db(config)
        print(f"  Found {len(domain_records)} domain records.")

        # Audit: reconcile Domains DB against Gmail filters
        domain_to_company: dict[str, str] = {}
        for d in domain_records:
            if not d["is_generic"] and d["filter_shape"] != "None":
                domain_to_company[d["domain"]] = d["domain"]

        results = reconcile(domain_to_company, gmail_filters, label_map)
        generic_flagged = [(d["domain"], "") for d in domain_records if d["is_generic"]]
        print_report(results, generic_flagged)

        if args.create:
            run_create_from_domains(domain_records, service, label_map, config, args.confirm)
        elif args.cleanup:
            run_cleanup(domain_records, service, label_map, config, args.confirm)
    else:
        # Legacy: Companies source
        if args.cleanup:
            parser.error("--cleanup requires --source notion-domains")

        print("Fetching companies from Notion...")
        companies = fetch_companies(config)
        print(f"  Found {len(companies)} Active/Draft companies.")

        domain_to_company, generic_flagged = build_domain_map(companies, generic_domains)
        print(f"  Extracted {len(domain_to_company)} non-generic domains.")

        results = reconcile(domain_to_company, gmail_filters, label_map)
        print_report(results, generic_flagged)

        if args.create:
            run_create(
                results["notion_only"],
                service,
                label_map,
                generic_domains,
                args.confirm,
            )


if __name__ == "__main__":
    main()
