#!/usr/bin/env python3
"""One-off script: copy all data from the SQLite database into PostgreSQL.

Usage:
    uv run python scripts/migrate_sqlite_to_postgres.py --sqlite data/fitness_coach.db

The DATABASE_URL is read from .env (or the environment).
"""

import argparse
import asyncio
import sqlite3
import sys
from pathlib import Path

# Allow imports from src/
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import asyncpg
from dotenv import load_dotenv
import os

load_dotenv()

TABLES = [
    "athletes",
    "workouts",
    "weight_entries",
    "activity_analysis_cache",
    "activity_chat",
    "insights_cache",
    "recap_cache",
    "plan_cache",
    "activity_streams",
    "execution_sessions",
]


async def migrate(sqlite_path: str, database_url: str) -> None:
    print(f"Source : {sqlite_path}")
    print(f"Target : {database_url}\n")

    src = sqlite3.connect(sqlite_path)
    src.row_factory = sqlite3.Row

    pg = await asyncpg.connect(database_url)

    for table in TABLES:
        # Check table exists in SQLite
        exists = src.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if not exists:
            print(f"  skip  {table} (not in SQLite)")
            continue

        rows = src.execute(f"SELECT * FROM {table}").fetchall()  # noqa: S608
        if not rows:
            print(f"  skip  {table} (empty)")
            continue

        columns = rows[0].keys()
        placeholders = ", ".join(f"${i+1}" for i in range(len(columns)))
        col_list = ", ".join(columns)

        # Build conflict clause per table
        conflict = _conflict_clause(table, list(columns))

        query = (
            f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) {conflict}"
        )

        values = [tuple(row[c] for c in columns) for row in rows]
        await pg.executemany(query, values)
        print(f"  copied {len(values):>5} rows → {table}")

    src.close()
    await pg.close()
    print("\nDone.")


def _conflict_clause(table: str, columns: list[str]) -> str:
    pk_map = {
        "athletes": "id",
        "workouts": "id",
        "weight_entries": "id",
        "activity_analysis_cache": "workout_id",
        "activity_chat": None,  # SERIAL PK, skip on conflict
        "insights_cache": "(athlete_id, year)",
        "recap_cache": "athlete_id",
        "plan_cache": "athlete_id",
        "activity_streams": "workout_id",
        "execution_sessions": "session_id",
    }
    pk = pk_map.get(table)
    if pk is None:
        return ""  # let it insert freely (autoincrement)

    update_cols = [c for c in columns if c not in ("id", "athlete_id", "workout_id", "session_id", "year")]
    if not update_cols:
        return f"ON CONFLICT {pk} DO NOTHING"

    set_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_cols)
    return f"ON CONFLICT ({pk}) DO UPDATE SET {set_clause}"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sqlite", default="data/fitness_coach.db", help="Path to SQLite db")
    parser.add_argument("--url", default=os.getenv("DATABASE_URL"), help="PostgreSQL URL")
    args = parser.parse_args()

    if not args.url:
        print("Error: DATABASE_URL not set (env var or --url)")
        sys.exit(1)

    asyncio.run(migrate(args.sqlite, args.url))
