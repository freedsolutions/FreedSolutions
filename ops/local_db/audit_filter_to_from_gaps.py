"""Audit Gmail filters for from/to coverage gaps.

For each labelling filter, group the filter criteria under the label it adds.
Surface labels that have from-side filters without matching to-side filters
(and vice versa), which is the outbound-coverage bug Adam observed.

Usage:
  python ops/local_db/audit_filter_to_from_gaps.py [--account adam@freedsolutions.com]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from ops.local_db.lib.config import load_config
from ops.local_db.lib.gmail_auth import build_gmail_service
from ops.local_db.gmail_filter_manager import fetch_gmail_filters, fetch_gmail_labels


def _normalize_recipient_token(token: str) -> str:
    token = token.strip().lower()
    if token.startswith("*@"):
        return token[2:]
    if token.startswith("@"):
        return token[1:]
    return token


def _split_criteria(value: str) -> list[str]:
    if not value:
        return []
    cleaned = value.strip().strip("{}")
    tokens = []
    for p in cleaned.split():
        norm = _normalize_recipient_token(p)
        if not norm:
            continue
        # Skip Gmail OR-group keyword
        if norm in ("or", "and"):
            continue
        tokens.append(norm)
    return tokens


def _is_sender_level(token: str) -> bool:
    """A token is sender-level (not domain-level) when it's a full email address."""
    return "@" in token


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", default=None)
    args = parser.parse_args()

    config = load_config()
    account = args.account or config.gmail_accounts[0].address
    service = build_gmail_service(account, config.google)

    filters = fetch_gmail_filters(service)
    label_map = fetch_gmail_labels(service)

    # label_id -> {"name": ..., "from": set(tokens), "to": set(tokens), "other": [criteria]}
    by_label: dict[str, dict] = {}
    skipped_complex: list[dict] = []

    for gf in filters:
        criteria = gf.get("criteria", {}) or {}
        action = gf.get("action", {}) or {}
        add_ids = action.get("addLabelIds", []) or []

        from_tokens = _split_criteria(criteria.get("from", ""))
        to_tokens = _split_criteria(criteria.get("to", ""))
        has_query = bool(criteria.get("query"))

        # Only consider filters that add a user label (not system labels)
        user_label_ids = [lid for lid in add_ids if lid in label_map and not lid.startswith("CATEGORY_")]
        if not user_label_ids:
            continue

        for lid in user_label_ids:
            lbucket = by_label.setdefault(lid, {
                "name": label_map[lid],
                "from": set(),
                "to": set(),
                "from_filters": [],
                "to_filters": [],
                "query_filters": [],
            })
            if from_tokens and not to_tokens:
                lbucket["from"].update(from_tokens)
                lbucket["from_filters"].append({"id": gf.get("id"), "tokens": from_tokens})
            elif to_tokens and not from_tokens:
                lbucket["to"].update(to_tokens)
                lbucket["to_filters"].append({"id": gf.get("id"), "tokens": to_tokens})
            elif from_tokens and to_tokens:
                # Mixed from+to in a single filter — count both
                lbucket["from"].update(from_tokens)
                lbucket["to"].update(to_tokens)
                lbucket["from_filters"].append({"id": gf.get("id"), "tokens": from_tokens, "mixed": True})
                lbucket["to_filters"].append({"id": gf.get("id"), "tokens": to_tokens, "mixed": True})
            elif has_query:
                lbucket["query_filters"].append({"id": gf.get("id"), "query": criteria.get("query")})
            else:
                # Filter with neither from nor to nor query — unusual
                skipped_complex.append({"id": gf.get("id"), "label_id": lid, "criteria": criteria})

    gap_rows = []
    for lid, info in sorted(by_label.items(), key=lambda kv: kv[1]["name"].lower()):
        from_set = info["from"]
        to_set = info["to"]
        # Tokens on from-side missing from to-side
        all_missing_to = sorted(from_set - to_set)
        all_missing_from = sorted(to_set - from_set)
        # Split: domain-level is the actionable class; sender-level bots Adam never emails
        missing_to_domains = [t for t in all_missing_to if not _is_sender_level(t)]
        missing_to_senders = [t for t in all_missing_to if _is_sender_level(t)]
        missing_from_domains = [t for t in all_missing_from if not _is_sender_level(t)]
        missing_from_senders = [t for t in all_missing_from if _is_sender_level(t)]
        if all_missing_to or all_missing_from:
            gap_rows.append({
                "label": info["name"],
                "label_id": lid,
                "from_tokens": sorted(from_set),
                "to_tokens": sorted(to_set),
                "missing_to_domains": missing_to_domains,
                "missing_to_senders": missing_to_senders,
                "missing_from_domains": missing_from_domains,
                "missing_from_senders": missing_from_senders,
                "query_filter_count": len(info["query_filters"]),
            })

    report = {
        "account": account,
        "total_filters": len(filters),
        "labels_considered": len(by_label),
        "gap_count": len(gap_rows),
        "gaps": gap_rows,
        "skipped_odd_filters": skipped_complex,
    }

    print(json.dumps(report, indent=2, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
