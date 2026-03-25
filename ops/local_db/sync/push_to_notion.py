from __future__ import annotations

import argparse
import json

from ops.local_db.lib.config import load_config
from ops.local_db.lib.db import init_db, iso_now, log_sync_event, set_agent_state
from ops.local_db.lib.notion_client import NotionApiClient
from ops.local_db.sync.mappings import TABLE_ORDER, TABLE_TO_DATABASE_KEY, build_notion_properties


def run(config_path: str | None = None) -> dict[str, int]:
    config = load_config(config_path)
    connection = init_db(config=config)
    client = NotionApiClient(config.notion.token_path)
    counts: dict[str, int] = {}

    try:
        for table_name in TABLE_ORDER:
            database_id = config.notion.databases[TABLE_TO_DATABASE_KEY[table_name]]
            schema = client.get_database(database_id)
            rows = connection.execute(
                f"""
                SELECT *
                FROM {table_name}
                WHERE notion_synced_at IS NULL
                   OR updated_at > notion_synced_at
                ORDER BY updated_at ASC
                """
            ).fetchall()
            counts[table_name] = 0
            for row in rows:
                properties = build_notion_properties(table_name, row, schema, connection)
                if not properties:
                    continue

                if row["notion_page_id"]:
                    client.update_page(row["notion_page_id"], properties)
                    notion_page_id = row["notion_page_id"]
                    action = "updated"
                else:
                    created = client.create_page(database_id, properties)
                    notion_page_id = created["id"]
                    action = "created"
                    connection.execute(
                        f"UPDATE {table_name} SET notion_page_id = ? WHERE id = ?",
                        (notion_page_id, row["id"]),
                    )

                synced_at = iso_now()
                connection.execute(
                    f"UPDATE {table_name} SET notion_synced_at = ?, updated_at = updated_at WHERE id = ?",
                    (synced_at, row["id"]),
                )
                connection.commit()
                counts[table_name] += 1
                log_sync_event(
                    connection,
                    operation="push_to_notion",
                    table_name=table_name,
                    local_record_id=row["id"],
                    notion_page_id=notion_page_id,
                    status="ok",
                    message=f"Record {action} in Notion.",
                )

            now_value = iso_now()
            set_agent_state(
                connection,
                f"push_to_notion:{table_name}",
                last_run=now_value,
                last_successful_run=now_value,
                state={"count": counts[table_name]},
            )
        return counts
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Push locally changed CRM records to Notion.")
    parser.add_argument("--config", default=None, help="Optional path to config.yaml")
    args = parser.parse_args()
    print(json.dumps(run(args.config), indent=2))


if __name__ == "__main__":
    main()
