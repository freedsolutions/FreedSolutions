"""Generate domain-routing-review.csv for NOTION ONLY domains (no Gmail filter).

One-off script — reads Domains DB and Companies DB, applies suggested tier logic,
writes CSV for Adam's review.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from ops.local_db.lib.config import load_config
from ops.local_db.gmail_filter_manager import (
    _notion_request,
    _load_notion_token,
    NOTION_API_VERSION,
)

# Established routing labels (use these instead of Company Name)
ESTABLISHED_LABELS = {
    "Primitiv": "Primitiv/PRI_Outlook",
    "DMC": "DMC/DMC_GMail",
    "LinkedIn": "LinkedIn",
}


def fetch_all_domains(token: str, db_id: str) -> list[dict]:
    """Fetch all Domain records."""
    domains = []
    start_cursor = None
    while True:
        body: dict = {"page_size": 100}
        if start_cursor:
            body["start_cursor"] = start_cursor
        resp = _notion_request(f"/databases/{db_id}/query", token, body)
        for page in resp.get("results", []):
            props = page.get("properties", {})
            title_parts = props.get("Domain", {}).get("title", [])
            domain = "".join(t.get("plain_text", "") for t in title_parts).strip()

            source_select = props.get("Source Type", {}).get("select")
            source_type = source_select["name"] if source_select else ""

            is_generic = props.get("Is Generic", {}).get("checkbox", False)

            filter_id = "".join(
                t.get("plain_text", "")
                for t in props.get("Gmail Filter ID", {}).get("rich_text", [])
            ).strip()

            shape_select = props.get("Filter Shape", {}).get("select")
            filter_shape = shape_select["name"] if shape_select else ""

            # Company relation
            company_relations = props.get("Company", {}).get("relation", [])
            company_page_id = company_relations[0]["id"] if company_relations else None

            domains.append({
                "domain": domain,
                "source_type": source_type,
                "is_generic": is_generic,
                "gmail_filter_id": filter_id,
                "filter_shape": filter_shape,
                "company_page_id": company_page_id,
            })
        if resp.get("has_more") and resp.get("next_cursor"):
            start_cursor = resp["next_cursor"]
        else:
            break
    return domains


def fetch_company_details(token: str, page_id: str) -> dict:
    """Fetch a single Company page for name, type, status, email count."""
    resp = _notion_request(f"/pages/{page_id}", token)
    props = resp.get("properties", {})

    name_parts = props.get("Company Name", {}).get("title", [])
    name = "".join(t.get("plain_text", "") for t in name_parts).strip()

    type_select = props.get("Company Type", {}).get("select")
    company_type = type_select["name"] if type_select else ""

    status_select = props.get("Record Status", {}).get("select")
    status = status_select["name"] if status_select else ""

    # Emails rollup — try to get count
    emails_prop = props.get("Emails", {})
    email_count = 0
    if emails_prop.get("type") == "rollup":
        rollup = emails_prop.get("rollup", {})
        if rollup.get("type") == "number":
            email_count = rollup.get("number") or 0
        elif rollup.get("type") == "array":
            email_count = len(rollup.get("array", []))
    elif emails_prop.get("type") == "relation":
        email_count = len(emails_prop.get("relation", []))

    return {
        "name": name,
        "company_type": company_type,
        "status": status,
        "email_count": email_count,
    }


def suggest_tier(
    company_type: str,
    company_status: str,
    email_count: int,
    source_type: str,
    is_generic: bool,
) -> str:
    if is_generic:
        return "None"
    if source_type == "Sender-Level":
        return "Draft Intake"
    if company_type == "Personal":
        return "None"
    if company_type in ("Operator", "Network"):
        return "Active Auto"
    if company_type == "Tech Stack":
        return "Draft Intake"
    if company_status == "Draft" and email_count == 0:
        return "Archive"
    if company_status == "Active" and email_count > 0:
        return "Active Auto"
    return "Draft Intake"


def suggest_shape(source_type: str, suggested_tier: str) -> str:
    if suggested_tier == "None":
        return "None"
    if source_type == "Sender-Level":
        return "Sender"
    return "Domain"


def suggest_label(company_name: str, suggested_tier: str) -> str:
    if suggested_tier == "None":
        return ""
    return ESTABLISHED_LABELS.get(company_name, company_name)


def main():
    config = load_config()
    token = _load_notion_token(config)
    domains_db_id = config.notion.databases.get("domains")

    print("Fetching all Domain records...")
    all_domains = fetch_all_domains(token, domains_db_id)
    print(f"  Found {len(all_domains)} total domains.")

    # Filter to NOTION ONLY (no Gmail filter, not generic-flagged-as-None)
    notion_only = [d for d in all_domains if not d["gmail_filter_id"]]
    print(f"  {len(notion_only)} without Gmail filter.")

    # Fetch company details (cache by page_id)
    company_cache: dict[str, dict] = {}
    company_ids = {d["company_page_id"] for d in notion_only if d["company_page_id"]}
    print(f"  Fetching details for {len(company_ids)} companies...")

    for i, pid in enumerate(sorted(company_ids), 1):
        company_cache[pid] = fetch_company_details(token, pid)
        if i % 10 == 0:
            print(f"    {i}/{len(company_ids)}...")

    print(f"  Done fetching companies.")

    # Build CSV rows
    rows = []
    for d in notion_only:
        company = company_cache.get(d["company_page_id"], {}) if d["company_page_id"] else {}
        company_name = company.get("name", "")
        company_type = company.get("company_type", "")
        company_status = company.get("status", "")
        email_count = company.get("email_count", 0)

        tier = suggest_tier(company_type, company_status, email_count, d["source_type"], d["is_generic"])
        shape = suggest_shape(d["source_type"], tier)
        label = suggest_label(company_name, tier)

        rows.append({
            "Domain": d["domain"],
            "Company": company_name,
            "Company Type": company_type,
            "Company Status": company_status,
            "Source Type": d["source_type"],
            "Email Volume": email_count,
            "Suggested Tier": tier,
            "Suggested Filter Shape": shape,
            "Gmail Label": label,
            "Notes": "",
        })

    # Sort by company name then domain
    rows.sort(key=lambda r: (r["Company"].lower(), r["Domain"].lower()))

    # Write CSV
    out_path = Path(__file__).resolve().parent / "domain-routing-review.csv"
    fieldnames = [
        "Domain", "Company", "Company Type", "Company Status",
        "Source Type", "Email Volume", "Suggested Tier",
        "Suggested Filter Shape", "Gmail Label", "Notes",
    ]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {len(rows)} rows to {out_path}")


if __name__ == "__main__":
    main()
