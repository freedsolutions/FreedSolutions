"""S80 Task 1: Patch missing to-side mirror filters for approved domain tokens.

Creates Gmail `to:*@<domain>` filters that add the same label as the existing
`from:*@<domain>` filter, so outbound mail picks up the label. Only covers the
"Obvious real-correspondence domains" list Adam approved in S80.

Dry-run (default): prints each filter that would be created.
Live:              pass --confirm to actually create the filters.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from ops.local_db.lib.config import load_config
from ops.local_db.lib.gmail_auth import build_gmail_service
from ops.local_db.gmail_filter_manager import fetch_gmail_filters, fetch_gmail_labels

# Label name -> list of domain tokens missing a to-side mirror.
# Sourced from audit_filter_to_from_gaps.py and filtered to Adam-approved
# "Obvious real-correspondence domains" only (S80).
APPROVED_MIRRORS: dict[str, list[str]] = {
    "Ads-N-Motion (ANM)":       ["adsnmotiontrucks.com", "billboardbroadcast.com"],
    "Advanced Psychotherapy":   ["advancepsychotherapy.org"],
    "AIQ (Alpine IQ)":          ["aiq.com"],
    "CannaPlanners":            ["cannaplanners.com"],
    "DA Advisory Group":        ["dacpas.com"],
    "Dope SEO":                 ["dopeseo.com"],
    "Edge":                     ["ouredge.com"],
    "ePropel":                  ["epropel.ca"],
    "Fat Nugs Magazine":        ["fatnugsmag.com"],
    "Fireflies":                ["fireflies.ai"],
    "Formul8":                  ["druckerdataworks.com", "staqs.io"],
    "GMP Collective":           ["gmpcollective.com"],
    "Gold Standard":            ["goldstandrd.com"],
    "Happier Valley Comedy":    ["happiervalley.com"],
    "Hoodie Analytics":         ["hoodieanalytics.com"],
    "iFLYTEK":                  ["iflytek.com", "iflytekglobal.ai"],
    "Illumify":                 ["illumify.com"],
    "LLYC":                     ["llyc.global"],
    "Lunar Moth Studios":       ["lunarmothstudios.com"],
    "Mercor":                   ["mercor.com"],
    "Orfao Tech Services":      ["orfaotechservices.com"],
    "PandaDoc":                 ["email.pandadoc.net", "pandadoc.com"],
    "Parallel":                 ["netacare.org"],
    "Ryan Spelts Marketing":    ["ryanspelts.com"],
    "Seed":                     ["getseed.io"],
    "SmartSource LLC":          ["smartsourcellc.com"],
    "Surfside":                 ["surfside.io"],
    "The Other Magazine":       ["theothermagazines.com"],
}


def _existing_to_tokens(filters: list[dict]) -> dict[str, set[str]]:
    """label_id -> set of to: tokens already mirrored (normalized domain)."""
    seen: dict[str, set[str]] = {}
    for gf in filters:
        criteria = gf.get("criteria", {}) or {}
        action = gf.get("action", {}) or {}
        to_val = (criteria.get("to") or "").strip()
        if not to_val:
            continue
        cleaned = to_val.strip("{}")
        for token in cleaned.split():
            t = token.strip().lower()
            if t.startswith("*@"):
                t = t[2:]
            elif t.startswith("@"):
                t = t[1:]
            if t in ("or", "and"):
                continue
            for lid in action.get("addLabelIds", []) or []:
                seen.setdefault(lid, set()).add(t)
    return seen


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", default=None)
    parser.add_argument("--confirm", action="store_true",
                        help="actually create filters (default: dry run)")
    args = parser.parse_args()

    config = load_config()
    account = args.account or config.gmail_accounts[0].address
    service = build_gmail_service(account, config.google)

    filters = fetch_gmail_filters(service)
    label_map = fetch_gmail_labels(service)              # id -> name
    name_to_id = {v: k for k, v in label_map.items()}    # name -> id
    existing_to = _existing_to_tokens(filters)

    to_create: list[tuple[str, str, str]] = []  # (label_name, label_id, domain)
    missing_labels: list[str] = []

    for label_name, domains in APPROVED_MIRRORS.items():
        lid = name_to_id.get(label_name)
        if not lid:
            missing_labels.append(label_name)
            continue
        already = existing_to.get(lid, set())
        for d in domains:
            if d.lower() in already:
                continue
            to_create.append((label_name, lid, d.lower()))

    mode = "CREATE" if args.confirm else "DRY RUN — would create"
    print(f"{mode} {len(to_create)} to-side mirror filter(s) on {account}:")
    for label_name, _lid, d in to_create:
        print(f"  to:*@{d}  ->  {label_name}")
    if missing_labels:
        print(f"\nWARNING: {len(missing_labels)} approved label(s) not found in Gmail; "
              f"skipped: {missing_labels}")

    if not args.confirm:
        return 0

    created = 0
    for label_name, lid, d in to_create:
        body = {
            "criteria": {"to": f"*@{d}"},
            "action": {"addLabelIds": [lid], "removeLabelIds": ["SPAM"]},
        }
        try:
            service.users().settings().filters().create(userId="me", body=body).execute()
            print(f"  CREATED: to:*@{d} -> {label_name}")
            created += 1
        except Exception as e:
            print(f"  ERROR creating to:*@{d} -> {label_name}: {e}", file=sys.stderr)

    print(f"\nCreated {created}/{len(to_create)} to-side mirror filters.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
