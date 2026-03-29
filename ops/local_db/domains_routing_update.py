"""Apply routing-review CSV decisions to the Notion Domains DB.

Usage:
  python ops/local_db/domains_routing_update.py                # dry run
  python ops/local_db/domains_routing_update.py --confirm      # live update

Reads domain-routing-review.csv and updates each matching Domain record's
Routing Tier, Filter Shape, and Gmail Label.

Tier mapping (CSV -> Notion):
  Active Auto -> Label
  Draft Intake -> Draft Intake
  None         -> Draft Intake  (Filter Shape set to None)
"""
from __future__ import annotations

import csv
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from ops.local_db.lib.config import load_config, AppConfig
from ops.local_db.gmail_filter_manager import (
    _notion_request,
    _load_notion_token,
    fetch_domains_db,
    NOTION_API_VERSION,
    NOTION_BASE,
)

CSV_PATH = Path(__file__).resolve().parent / "domain-routing-review.csv"

# CSV "Suggested Tier" -> Notion "Routing Tier"
TIER_MAP = {
    "Active Auto": "Label",
    "Draft Intake": "Draft Intake",
    "None": "Draft Intake",
}


def load_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def update_domain_record(
    token: str,
    page_id: str,
    routing_tier: str,
    filter_shape: str,
    gmail_label: str,
) -> dict:
    """PATCH a Domain page with updated routing fields."""
    properties: dict = {
        "Routing Tier": {"select": {"name": routing_tier}},
    }

    if filter_shape == "None":
        # Clear the select by setting to None
        properties["Filter Shape"] = {"select": None}
    elif filter_shape:
        properties["Filter Shape"] = {"select": {"name": filter_shape}}

    if gmail_label:
        properties["Gmail Label"] = {"rich_text": [{"text": {"content": gmail_label}}]}
    else:
        # Clear the field
        properties["Gmail Label"] = {"rich_text": []}

    body = {"properties": properties}
    data = json.dumps(body).encode("utf-8")
    url = f"{NOTION_BASE}/pages/{page_id}"
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
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run(config: AppConfig, confirm: bool):
    # 1. Load CSV
    csv_rows = load_csv(CSV_PATH)
    print(f"Loaded {len(csv_rows)} rows from {CSV_PATH.name}")

    # 2. Fetch existing Domain records from Notion
    print("Fetching Domains DB from Notion...")
    domains = fetch_domains_db(config)
    print(f"  Found {len(domains)} domain records")

    # Build lookup: domain string -> Notion record
    domain_lookup: dict[str, dict] = {}
    for d in domains:
        key = d["domain"].lower().strip()
        domain_lookup[key] = d

    # 3. Build change plan
    changes: list[dict] = []
    not_found: list[str] = []

    for row in csv_rows:
        csv_domain = row["Domain"].strip().lower()
        csv_tier = row["Suggested Tier"].strip()
        csv_shape = row["Suggested Filter Shape"].strip()
        csv_label = row["Gmail Label"].strip()

        notion_record = domain_lookup.get(csv_domain)
        if not notion_record:
            not_found.append(csv_domain)
            continue

        # Apply tier mapping
        notion_tier = TIER_MAP.get(csv_tier)
        if notion_tier is None:
            print(f"  WARNING: Unknown tier '{csv_tier}' for {csv_domain}, skipping")
            continue

        # For CSV "None" tier: override filter shape to None
        if csv_tier == "None":
            csv_shape = "None"

        # Check what actually changed
        old_tier = notion_record["routing_tier"]
        old_shape = notion_record["filter_shape"]
        old_label = notion_record["gmail_label"]

        tier_changed = old_tier != notion_tier
        shape_changed = old_shape != csv_shape
        label_changed = old_label != csv_label

        if not (tier_changed or shape_changed or label_changed):
            continue  # no changes needed

        changes.append({
            "domain": csv_domain,
            "page_id": notion_record["page_id"],
            "company": row["Company"],
            "csv_tier": csv_tier,
            "old_tier": old_tier,
            "new_tier": notion_tier,
            "old_shape": old_shape,
            "new_shape": csv_shape,
            "old_label": old_label,
            "new_label": csv_label,
            "tier_changed": tier_changed,
            "shape_changed": shape_changed,
            "label_changed": label_changed,
        })

    # 4. Dry-run summary
    print(f"\n{'=' * 60}")
    print(f"  ROUTING UPDATE {'LIVE' if confirm else 'DRY RUN'}")
    print(f"{'=' * 60}")
    print(f"  CSV rows:         {len(csv_rows)}")
    print(f"  Matched:          {len(csv_rows) - len(not_found)}")
    print(f"  Not found:        {len(not_found)}")
    print(f"  Changes needed:   {len(changes)}")

    if not_found:
        print(f"\n  NOT FOUND in Domains DB ({len(not_found)}):")
        for d in not_found:
            print(f"    - {d}")

    # Count by new tier
    tier_counts: dict[str, int] = {}
    for c in changes:
        t = c["new_tier"]
        tier_counts[t] = tier_counts.get(t, 0) + 1

    print(f"\n  Changes by new Routing Tier:")
    for tier, count in sorted(tier_counts.items()):
        print(f"    {tier:<20} {count}")

    # Count by CSV tier (original)
    csv_tier_counts: dict[str, int] = {}
    for c in changes:
        t = c["csv_tier"]
        csv_tier_counts[t] = csv_tier_counts.get(t, 0) + 1

    print(f"\n  Changes by CSV Suggested Tier:")
    for tier, count in sorted(csv_tier_counts.items()):
        print(f"    {tier:<20} {count}")

    # Detail table
    if changes:
        print(f"\n  {'Domain':<35} {'Company':<22} {'Tier':<25} {'Shape':<18} {'Label'}")
        print(f"  {'-'*35} {'-'*22} {'-'*25} {'-'*18} {'-'*20}")
        for c in changes:
            company = (c["company"][:20] + "..") if len(c["company"]) > 22 else c["company"]
            domain = (c["domain"][:33] + "..") if len(c["domain"]) > 35 else c["domain"]

            tier_str = c["old_tier"] or "(empty)"
            if c["tier_changed"]:
                tier_str = f"{tier_str} -> {c['new_tier']}"

            shape_str = c["old_shape"] or "(empty)"
            if c["shape_changed"]:
                shape_str = f"{shape_str} -> {c['new_shape']}"

            label_str = ""
            if c["label_changed"]:
                old = c["old_label"] or "(empty)"
                label_str = f"{old} -> {c['new_label']}"

            print(f"  {domain:<35} {company:<22} {tier_str:<25} {shape_str:<18} {label_str}")

    print(f"{'=' * 60}")

    # 5. Apply if confirmed
    if not confirm:
        if changes:
            print(f"\nDRY RUN complete. Re-run with --confirm to apply {len(changes)} updates.")
        else:
            print(f"\nNo changes needed.")
        return

    if not changes:
        print("\nNo changes to apply.")
        return

    token = _load_notion_token(config)
    print(f"\nApplying {len(changes)} updates...")

    success = 0
    errors = 0
    for i, c in enumerate(changes, 1):
        try:
            update_domain_record(
                token=token,
                page_id=c["page_id"],
                routing_tier=c["new_tier"],
                filter_shape=c["new_shape"],
                gmail_label=c["new_label"],
            )
            print(f"  [{i}/{len(changes)}] {c['domain']} -> {c['new_tier']}")
            success += 1
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            print(f"  [{i}/{len(changes)}] ERROR {c['domain']}: {e.code} {err_body[:200]}")
            errors += 1

    print(f"\nDone. Updated: {success}  Errors: {errors}")


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Apply routing-review CSV decisions to the Notion Domains DB."
    )
    parser.add_argument(
        "--confirm", action="store_true",
        help="Actually apply updates (default is dry run).",
    )
    args = parser.parse_args()

    config = load_config()
    run(config, args.confirm)


if __name__ == "__main__":
    main()
