from __future__ import annotations

import argparse
import sqlite3
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, func, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.database import Base, SQLALCHEMY_DATABASE_URL


TABLE_ORDER = (
    "crawl_runs",
    "toeic_sw_writing_tests",
    "toeic_sw_writing_parts",
    "toeic_sw_writing_questions",
    "toeic_sw_writing_sample_answers",
)


def sqlite_rows(sqlite_path: Path, table_name: str) -> list[dict[str, Any]]:
    with sqlite3.connect(sqlite_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(f'SELECT * FROM "{table_name}"').fetchall()
        return [dict(row) for row in rows]


def upsert_rows(engine: Engine, table_name: str, rows: Iterable[dict[str, Any]]) -> int:
    table = Base.metadata.tables[table_name]
    primary_keys = [column.name for column in table.primary_key.columns]
    if not primary_keys:
        raise ValueError(f"{table_name} does not have a primary key")

    count = 0
    with engine.begin() as conn:
        for row in rows:
            values = {key: row[key] for key in row.keys() if key in table.c}
            statement = insert(table).values(**values)
            update_values = {
                key: statement.excluded[key]
                for key in values.keys()
                if key not in primary_keys
            }
            if update_values:
                statement = statement.on_conflict_do_update(
                    index_elements=primary_keys,
                    set_=update_values,
                )
            else:
                statement = statement.on_conflict_do_nothing(
                    index_elements=primary_keys,
                )
            conn.execute(statement)
            count += 1
    return count


def migrate_users(engine: Engine, rows: list[dict[str, Any]]) -> tuple[int, dict[int, int]]:
    table = Base.metadata.tables["users"]
    user_id_map: dict[int, int] = {}

    with engine.begin() as conn:
        for row in rows:
            existing_by_username = conn.execute(
                select(table.c.id).where(table.c.username == row["username"])
            ).scalar_one_or_none()
            if existing_by_username is not None:
                conn.execute(
                    update(table)
                    .where(table.c.id == existing_by_username)
                    .values(
                        password_hash=row["password_hash"],
                        created_at=row["created_at"],
                    )
                )
                user_id_map[row["id"]] = existing_by_username
                continue

            existing_by_id = conn.execute(
                select(table.c.id).where(table.c.id == row["id"])
            ).scalar_one_or_none()
            if existing_by_id is None:
                result = conn.execute(insert(table).values(**row).returning(table.c.id))
            else:
                values = {
                    "username": row["username"],
                    "password_hash": row["password_hash"],
                    "created_at": row["created_at"],
                }
                result = conn.execute(insert(table).values(**values).returning(table.c.id))
            user_id_map[row["id"]] = result.scalar_one()

    return len(rows), user_id_map


def remap_user_ids(rows: list[dict[str, Any]], user_id_map: dict[int, int]) -> list[dict[str, Any]]:
    remapped = []
    for row in rows:
        next_row = dict(row)
        next_row["user_id"] = user_id_map[next_row["user_id"]]
        remapped.append(next_row)
    return remapped


def reset_sequence(engine: Engine, table_name: str) -> None:
    table = Base.metadata.tables[table_name]
    primary_keys = [column for column in table.primary_key.columns]
    if len(primary_keys) != 1 or not primary_keys[0].autoincrement:
        return

    pk = primary_keys[0]
    quoted_table = table.name.replace("'", "''")
    quoted_pk = pk.name.replace("'", "''")
    with engine.begin() as conn:
        max_id = conn.scalar(select(func.max(pk))) or 1
        conn.execute(
            text(
                "SELECT setval("
                "pg_get_serial_sequence(:table_name, :column_name), "
                ":next_value, "
                "true"
                ")"
            ),
            {
                "table_name": quoted_table,
                "column_name": quoted_pk,
                "next_value": max_id,
            },
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate the local SQLite database into the configured Postgres database."
    )
    parser.add_argument("--sqlite", type=Path, default=Path("data/database.db"))
    args = parser.parse_args()

    if not args.sqlite.exists():
        raise SystemExit(f"SQLite database not found: {args.sqlite}")
    if not SQLALCHEMY_DATABASE_URL.startswith("postgresql"):
        raise SystemExit("DATABASE_URL must point to Postgres for this migration.")

    target_engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)
    Base.metadata.create_all(bind=target_engine)

    copied: dict[str, int] = {}
    for table_name in TABLE_ORDER:
        rows = sqlite_rows(args.sqlite, table_name)
        copied[table_name] = upsert_rows(target_engine, table_name, rows)

    copied["users"], user_id_map = migrate_users(
        target_engine,
        sqlite_rows(args.sqlite, "users"),
    )
    copied["drafts"] = upsert_rows(
        target_engine,
        "drafts",
        remap_user_ids(sqlite_rows(args.sqlite, "drafts"), user_id_map),
    )
    copied["attempts"] = upsert_rows(
        target_engine,
        "attempts",
        remap_user_ids(sqlite_rows(args.sqlite, "attempts"), user_id_map),
    )

    for table_name in (*TABLE_ORDER, "users", "drafts", "attempts"):
        reset_sequence(target_engine, table_name)

    for table_name, count in copied.items():
        print(f"{table_name}: {count}")


if __name__ == "__main__":
    main()
