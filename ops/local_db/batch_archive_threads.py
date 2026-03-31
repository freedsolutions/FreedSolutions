"""Batch-archive Gmail threads by removing the INBOX label.

Usage:
  python ops/local_db/batch_archive_threads.py THREAD_ID [THREAD_ID ...]
  python ops/local_db/batch_archive_threads.py --file thread_ids.txt
  python ops/local_db/batch_archive_threads.py --account adam@freedsolutions.com THREAD_ID ...

Reads thread IDs from arguments or a file (one per line).
Uses the Gmail API batchModify endpoint to remove INBOX in one call,
then verifies each thread's label state.
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


def batch_archive(service, thread_ids: list[str]) -> dict:
    """Remove INBOX label from all given threads via threads.list + messages.batchModify."""
    # Collect all message IDs across threads
    all_message_ids = []
    print(f"[1/3] Resolving message IDs for {len(thread_ids)} threads...")
    for i, tid in enumerate(thread_ids):
        try:
            thread = service.users().threads().get(
                userId="me", id=tid, format="minimal"
            ).execute()
            msg_ids = [m["id"] for m in thread.get("messages", [])]
            all_message_ids.extend(msg_ids)
            if (i + 1) % 10 == 0:
                print(f"  ...resolved {i + 1}/{len(thread_ids)} threads ({len(all_message_ids)} messages)")
        except Exception as e:
            print(f"  WARNING: Could not resolve thread {tid}: {e}")

    print(f"[2/3] Batch-archiving {len(all_message_ids)} messages across {len(thread_ids)} threads...")
    if not all_message_ids:
        print("  No messages to archive.")
        return {"archived": 0, "errors": []}

    # Gmail batchModify handles up to 1000 message IDs per call
    batch_size = 1000
    for start in range(0, len(all_message_ids), batch_size):
        chunk = all_message_ids[start:start + batch_size]
        service.users().messages().batchModify(
            userId="me",
            body={
                "ids": chunk,
                "removeLabelIds": ["INBOX"],
            },
        ).execute()

    # Verify
    print(f"[3/3] Verifying...")
    still_in_inbox = []
    for tid in thread_ids:
        try:
            thread = service.users().threads().get(
                userId="me", id=tid, format="minimal"
            ).execute()
            for msg in thread.get("messages", []):
                if "INBOX" in msg.get("labelIds", []):
                    still_in_inbox.append(tid)
                    break
        except Exception:
            pass

    if still_in_inbox:
        print(f"  WARNING: {len(still_in_inbox)} threads still in INBOX: {still_in_inbox}")
    else:
        print(f"  All {len(thread_ids)} threads confirmed archived.")

    return {"archived": len(thread_ids) - len(still_in_inbox), "still_in_inbox": still_in_inbox}


def main():
    parser = argparse.ArgumentParser(description="Batch-archive Gmail threads")
    parser.add_argument("thread_ids", nargs="*", help="Thread IDs to archive")
    parser.add_argument("--file", "-f", help="File with thread IDs (one per line)")
    parser.add_argument("--account", default="adam@freedsolutions.com", help="Gmail account")
    args = parser.parse_args()

    ids = list(args.thread_ids)
    if args.file:
        with open(args.file, encoding="utf-8") as fh:
            ids.extend(line.strip() for line in fh if line.strip())

    if not ids:
        parser.error("No thread IDs provided. Pass them as arguments or via --file.")

    config = load_config()
    service = build_gmail_service(args.account, config.google)
    result = batch_archive(service, ids)
    print(f"\nDone. Archived: {result['archived']}, Still in inbox: {len(result['still_in_inbox'])}")


if __name__ == "__main__":
    main()
