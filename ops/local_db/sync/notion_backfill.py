from __future__ import annotations

import argparse
import json
from ops.local_db.lib.config import load_config
from ops.local_db.lib.db import init_db, iso_now, log_sync_event, set_agent_state, upsert
from ops.local_db.lib.notion_client import NotionApiClient
from ops.local_db.sync.mappings import (
    TABLE_ORDER,
    TABLE_TO_DATABASE_KEY,
    apply_relation_resolution,
    find_existing_local_row,
    page_to_local_record,
)


def run(config_path: str | None = None) -> dict[str, int]:
    config = load_config(config_path)
    connection = init_db(config=config)
    client = NotionApiClient(config.notion.token_path)
    counts: dict[str, int] = {}
    pending_relations: list[tuple[str, str, dict[str, list[str] | str | None]]] = []

    try:
        for table_name in TABLE_ORDER:
            database_id = config.notion.databases[TABLE_TO_DATABASE_KEY[table_name]]
            pages = client.get_database_records(database_id)
            counts[table_name] = len(pages)

            for page in pages:
                existing = find_existing_local_row(connection, table_name, page)
                record, relations = page_to_local_record(table_name, page, existing)
                upsert(
                    connection,
                    table_name,
                    record,
                    conflict_columns=("id",) if existing else ("notion_page_id",),
                )
                pending_relations.append((table_name, record["id"], relations))

            log_sync_event(
                connection,
                operation="notion_backfill",
                table_name=table_name,
                status="ok",
                message=f"Backfilled {counts[table_name]} records from Notion.",
                payload={"database_id": database_id},
            )

        for table_name, local_id, relations in pending_relations:
            if relations:
                apply_relation_resolution(connection, table_name, local_id, relations)

        now_value = iso_now()
        set_agent_state(
            connection,
            "notion_backfill",
            last_run=now_value,
            last_successful_run=now_value,
            state=counts,
        )
        return counts
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill existing Notion CRM records into the local SQLite cache.")
    parser.add_argument("--config", default=None, help="Optional path to config.yaml")
    args = parser.parse_args()
    print(json.dumps(run(args.config), indent=2))


if __name__ == "__main__":
    main()
