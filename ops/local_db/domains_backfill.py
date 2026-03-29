"""Backfill the Notion Domains DB from Companies + Gmail filters.

Usage:
  python ops/local_db/domains_backfill.py                # dry run
  python ops/local_db/domains_backfill.py --confirm      # live create

Prerequisites: same as gmail_filter_manager.py (Google OAuth + Notion token).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from ops.local_db.lib.config import load_config, AppConfig
from ops.local_db.lib.gmail_auth import build_gmail_service
from ops.local_db.gmail_filter_manager import (
    _notion_request,
    _load_notion_token,
    fetch_companies,
    fetch_gmail_filters,
    fetch_gmail_labels,
    extract_filter_domains,
    NOTION_API_VERSION,
    NOTION_BASE,
)

import urllib.request
import urllib.error

# ---------------------------------------------------------------------------
# Domain entry extraction from Companies
# ---------------------------------------------------------------------------

def extract_domain_entries(companies: list[dict]) -> list[dict]:
    """Yield one entry per domain/email from every company's Domains + Additional Domains."""
    entries: list[dict] = []
    for company in companies:
        for domain in company["domains"]:
            entries.append({
                "entry": domain,
                "company_name": company["name"],
                "company_page_id": company["page_id"],
                "source_type": "Primary",
            })
        for entry in company["additional_domains"]:
            if "@" in entry:
                source_type = "Sender-Level"
            else:
                source_type = "Additional"
            entries.append({
                "entry": entry,
                "company_name": company["name"],
                "company_page_id": company["page_id"],
                "source_type": source_type,
            })
    return entries


# ---------------------------------------------------------------------------
# Gmail filter index
# ---------------------------------------------------------------------------

def build_gmail_filter_index(
    gmail_filters: list[dict], label_map: dict[str, str]
) -> dict[str, dict]:
    """Map domain -> {filter_id, label_name, has_archive}."""
    index: dict[str, dict] = {}
    for gf in gmail_filters:
        filter_id = gf.get("id", "")
        action = gf.get("action", {})
        label_ids = action.get("addLabelIds", [])
        remove_ids = action.get("removeLabelIds", [])
        label_names = [label_map.get(lid, "") for lid in label_ids if label_map.get(lid)]
        has_archive = "INBOX" in remove_ids
        label_name = label_names[0] if label_names else ""

        for domain in extract_filter_domains(gf):
            if domain not in index:
                index[domain] = {
                    "filter_id": filter_id,
                    "label_name": label_name,
                    "has_archive": has_archive,
                }
    return index


def determine_routing_tier(filter_info: dict | None) -> str:
    if not filter_info:
        return "Draft Intake"
    if filter_info["label_name"] and filter_info["has_archive"]:
        return "Archive"
    if filter_info["label_name"] and not filter_info["has_archive"]:
        return "Active Auto"
    return "Draft Intake"


# ---------------------------------------------------------------------------
# Subdomain matching
# ---------------------------------------------------------------------------

def find_parent_company(
    domain: str, company_domain_map: dict[str, dict]
) -> dict | None:
    """Walk up the domain hierarchy to find a parent company match."""
    parts = domain.split(".")
    for i in range(1, len(parts)):
        parent = ".".join(parts[i:])
        if parent in company_domain_map:
            return company_domain_map[parent]
    return None


# ---------------------------------------------------------------------------
# Notion: create a Domain record
# ---------------------------------------------------------------------------

def create_domain_record(
    token: str,
    domains_db_id: str,
    entry: str,
    company_page_id: str | None,
    source_type: str,
    is_generic: bool,
    filter_shape: str,
    routing_tier: str,
    gmail_label: str,
    gmail_filter_id: str,
    notes: str,
) -> dict:
    """Create a single page in the Domains DB."""
    properties: dict = {
        "Domain": {"title": [{"text": {"content": entry}}]},
        "Source Type": {"select": {"name": source_type}},
        "Is Generic": {"checkbox": is_generic},
        "Filter Shape": {"select": {"name": filter_shape}},
        "Routing Tier": {"select": {"name": routing_tier}},
        "Record Status": {"select": {"name": "Draft"}},
    }
    if company_page_id:
        properties["Company"] = {"relation": [{"id": company_page_id}]}
    if gmail_label:
        properties["Gmail Label"] = {"rich_text": [{"text": {"content": gmail_label}}]}
    if gmail_filter_id:
        properties["Gmail Filter ID"] = {"rich_text": [{"text": {"content": gmail_filter_id}}]}
    if notes:
        properties["Notes"] = {"rich_text": [{"text": {"content": notes}}]}

    body = {
        "parent": {"database_id": domains_db_id},
        "properties": properties,
    }
    return _notion_request("/pages", token, body)


# ---------------------------------------------------------------------------
# Main backfill logic
# ---------------------------------------------------------------------------

# Gmail-only special cases
GMAIL_ONLY_OVERRIDES: dict[str, dict] = {
    "em1.cloudflare.com": {"parent_domain": "cloudflare.com", "notes": ""},
    "notify.cloudflare.com": {"parent_domain": "cloudflare.com", "notes": ""},
    "mail.notion.so": {"parent_domain": "notion.so", "notes": ""},
    "sweetgrassbotanicalslee.com": {
        "parent_domain": None,
        "notes": "Gmail filter exists, no CRM Company",
    },
    "teams.mail.microsoft": {
        "parent_domain": None,
        "notes": "Teams notification routing filter — not a company domain",
    },
}


def run_backfill(config: AppConfig, confirm: bool, account: str):
    token = _load_notion_token(config)
    domains_db_id = config.notion.databases.get("domains")
    if not domains_db_id:
        print("ERROR: No 'domains' database ID in config.", file=sys.stderr)
        sys.exit(1)

    generic_domains = set(config.adam.generic_domains)

    # 1. Fetch companies (with page IDs)
    print("Fetching companies from Notion...")
    companies = fetch_companies(config)
    print(f"  Found {len(companies)} Active/Draft companies.")

    # 2. Fetch Gmail filters
    print(f"Connecting to Gmail as {account}...")
    service = build_gmail_service(account, config.google)
    print("Fetching Gmail filters and labels...")
    gmail_filters = fetch_gmail_filters(service)
    label_map = fetch_gmail_labels(service)
    print(f"  Found {len(gmail_filters)} filters, {len(label_map)} labels.")

    filter_index = build_gmail_filter_index(gmail_filters, label_map)

    # 3. Build domain entries from companies
    raw_entries = extract_domain_entries(companies)

    # Build company domain map for subdomain matching (domain -> first company info)
    company_domain_map: dict[str, dict] = {}
    for e in raw_entries:
        key = e["entry"].lower().strip()
        if "@" in key:
            # for sender-level, key is the full email
            pass
        if key not in company_domain_map:
            company_domain_map[key] = {
                "company_name": e["company_name"],
                "company_page_id": e["company_page_id"],
            }

    # 4. Dedup: one record per domain/email key
    seen: dict[str, str] = {}  # entry -> first company name
    dedup_entries: list[dict] = []
    dedup_conflicts: list[tuple[str, str, str]] = []  # (entry, first_co, dup_co)

    for e in raw_entries:
        key = e["entry"].lower().strip()
        if key in seen:
            dedup_conflicts.append((key, seen[key], e["company_name"]))
            continue
        seen[key] = e["company_name"]
        dedup_entries.append(e)

    # 5. Build records
    records: list[dict] = []
    for e in dedup_entries:
        entry = e["entry"].lower().strip()
        is_email = "@" in entry
        domain_part = entry.split("@")[1] if is_email else entry
        is_generic = domain_part in generic_domains

        # Filter Shape
        if is_generic and not is_email:
            filter_shape = "None"
        elif is_email:
            filter_shape = "Sender"
        else:
            filter_shape = "Domain"

        # Gmail filter matching — try exact domain, then full entry for sender
        filter_info = filter_index.get(domain_part)
        if not filter_info and is_email:
            filter_info = filter_index.get(entry)

        routing_tier = determine_routing_tier(filter_info)

        records.append({
            "entry": entry,
            "company_name": e["company_name"],
            "company_page_id": e["company_page_id"],
            "source_type": e["source_type"],
            "is_generic": is_generic,
            "filter_shape": filter_shape,
            "routing_tier": routing_tier,
            "gmail_label": filter_info["label_name"] if filter_info else "",
            "gmail_filter_id": filter_info["filter_id"] if filter_info else "",
            "notes": "",
            "category": "company",
        })

    # 6. Handle Gmail-only domains (not matched to any company)
    all_company_domains = set(seen.keys())
    # Also collect bare domains from email entries
    for key in list(all_company_domains):
        if "@" in key:
            all_company_domains.add(key.split("@")[1])

    gmail_only_domains: list[str] = []
    for domain in filter_index:
        if domain not in all_company_domains:
            gmail_only_domains.append(domain)

    for domain in gmail_only_domains:
        override = GMAIL_ONLY_OVERRIDES.get(domain)
        filter_info = filter_index[domain]
        routing_tier = determine_routing_tier(filter_info)

        if override:
            parent_domain = override["parent_domain"]
            notes = override["notes"]
        else:
            # Try subdomain match
            parent_match = find_parent_company(domain, company_domain_map)
            if parent_match:
                parent_domain = "matched"
                notes = ""
            else:
                parent_domain = None
                notes = "Gmail filter exists, no CRM Company"

        if override and parent_domain:
            # Look up the parent company
            parent_info = company_domain_map.get(parent_domain)
            if not parent_info:
                parent_info = find_parent_company(parent_domain, company_domain_map)
                if parent_info:
                    parent_info = parent_info  # already a dict
            company_page_id = parent_info["company_page_id"] if parent_info else None
            company_name = parent_info["company_name"] if parent_info else ""
        elif not override and parent_domain == "matched":
            parent_info = find_parent_company(domain, company_domain_map)
            company_page_id = parent_info["company_page_id"] if parent_info else None
            company_name = parent_info["company_name"] if parent_info else ""
        else:
            company_page_id = None
            company_name = ""

        records.append({
            "entry": domain,
            "company_name": company_name,
            "company_page_id": company_page_id,
            "source_type": "Additional",
            "is_generic": False,
            "filter_shape": "Domain",
            "routing_tier": routing_tier,
            "gmail_label": filter_info["label_name"],
            "gmail_filter_id": filter_info["filter_id"],
            "notes": notes,
            "category": "gmail_only_subdomain" if company_page_id else "gmail_only_no_company",
        })

    # 7. Summary
    print_summary(records, dedup_conflicts, confirm)

    # 8. Print detail table
    print_detail_table(records)

    # 9. Create or dry-run
    if confirm:
        print(f"\nCreating {len(records)} Domain records...")
        for i, rec in enumerate(records, 1):
            result = create_domain_record(
                token=token,
                domains_db_id=domains_db_id,
                entry=rec["entry"],
                company_page_id=rec["company_page_id"],
                source_type=rec["source_type"],
                is_generic=rec["is_generic"],
                filter_shape=rec["filter_shape"],
                routing_tier=rec["routing_tier"],
                gmail_label=rec["gmail_label"],
                gmail_filter_id=rec["gmail_filter_id"],
                notes=rec["notes"],
            )
            page_id = result.get("id", "???")
            print(f"  [{i}/{len(records)}] {rec['entry']} -> {page_id}")
        print(f"\nDone. Created {len(records)} Domain records.")
    else:
        print(f"\nDRY RUN complete. Re-run with --confirm to create {len(records)} records.")

    # Log dedup conflicts
    if dedup_conflicts:
        print(f"\nDEDUP CONFLICTS ({len(dedup_conflicts)}):")
        for entry, first, dup in dedup_conflicts:
            print(f"  {entry}: kept {first}, skipped {dup}")


def print_summary(records: list[dict], dedup_conflicts: list, confirm: bool):
    primary = sum(1 for r in records if r["source_type"] == "Primary")
    additional = sum(1 for r in records if r["source_type"] == "Additional" and r["category"] == "company")
    sender = sum(1 for r in records if r["source_type"] == "Sender-Level")
    gmail_sub = sum(1 for r in records if r["category"] == "gmail_only_subdomain")
    gmail_no = sum(1 for r in records if r["category"] == "gmail_only_no_company")
    generic = sum(1 for r in records if r["is_generic"])
    with_filter = sum(1 for r in records if r["gmail_filter_id"])
    without_filter = sum(1 for r in records if not r["gmail_filter_id"])

    mode = "WILL CREATE" if confirm else "DRY RUN — would create"
    print(f"\n{'=' * 60}")
    print(f"  DOMAINS BACKFILL SUMMARY ({mode})")
    print(f"{'=' * 60}")
    print(f"  Total records:                    {len(records)}")
    print(f"  - Primary domains:                {primary}")
    print(f"  - Additional domains:             {additional}")
    print(f"  - Sender-level entries:           {sender}")
    print(f"  - Gmail-only (subdomain matches): {gmail_sub}")
    print(f"  - Gmail-only (no Company match):  {gmail_no}")
    print(f"  - Generic domains (Is Generic):   {generic}")
    print(f"  - With Gmail filter matched:      {with_filter}")
    print(f"  - Without Gmail filter:           {without_filter}")
    print(f"  - Dedup conflicts (logged):       {len(dedup_conflicts)}")
    print(f"{'=' * 60}")


def print_detail_table(records: list[dict]):
    print(f"\n{'Domain/Entry':<40} {'Company':<25} {'Source':<12} {'Tier':<14} {'Shape':<8} {'Label'}")
    print(f"{'-'*40} {'-'*25} {'-'*12} {'-'*14} {'-'*8} {'-'*20}")
    for r in records:
        company = (r["company_name"][:23] + "..") if len(r["company_name"]) > 25 else r["company_name"]
        entry = (r["entry"][:38] + "..") if len(r["entry"]) > 40 else r["entry"]
        generic_flag = " [G]" if r["is_generic"] else ""
        print(
            f"{entry:<40} {company:<25} {r['source_type']:<12} "
            f"{r['routing_tier']:<14} {r['filter_shape']:<8} "
            f"{r['gmail_label']}{generic_flag}"
        )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Backfill the Notion Domains DB from Companies + Gmail filters."
    )
    parser.add_argument(
        "--confirm", action="store_true",
        help="Actually create records (default is dry run).",
    )
    parser.add_argument(
        "--account", default="adam@freedsolutions.com",
        help="Gmail account to audit filters for (default: adam@freedsolutions.com).",
    )
    args = parser.parse_args()

    config = load_config()
    run_backfill(config, args.confirm, args.account)


if __name__ == "__main__":
    main()
