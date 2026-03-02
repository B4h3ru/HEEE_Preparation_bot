"""
Backup executor script - runs heee_preparation (1).sql against the configured database.
Use to restore schema and data from backup.

Usage:
    python run_backup_sql.py
    python run_backup_sql.py --file "path/to/backup.sql"
"""

import argparse
import re
import sys
from pathlib import Path

import mysql.connector

from config.settings import db_settings


DEFAULT_SQL_FILE = Path(__file__).parent / "heee_preparation (1).sql"


TABLES_ORDER = [
    "user_answers", "session_questions", "quiz_sessions",
    "options", "questions", "subjects", "departments", "users",
]


def drop_tables(conn) -> None:
    """Drop tables in reverse dependency order."""
    cursor = conn.cursor()
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    for table in TABLES_ORDER:
        try:
            cursor.execute(f"DROP TABLE IF EXISTS `{table}`")
            print(f"  Dropped: {table}")
        except mysql.connector.Error as err:
            print(f"  Drop {table}: {err}")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    conn.commit()
    cursor.close()


def execute_sql_file(conn, sql_path: Path) -> None:
    """Execute SQL file. Handles phpMyAdmin dump format."""
    content = sql_path.read_text(encoding="utf-8", errors="replace")

    # Remove SQL comments (-- and /* */)
    content = re.sub(r"--[^\n]*", "", content)
    content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)

    # Split by semicolon, keep multi-line statements
    raw_statements = [s.strip() for s in content.split(";") if s.strip()]

    statements = []
    for stmt in raw_statements:
        # Skip empty, SET NAMES, SET modes (we handle those separately)
        upper = stmt.upper()
        if not stmt or upper.startswith("SET NAMES") or upper.startswith("SET TIME_ZONE"):
            continue
        if "START TRANSACTION" in upper or "COMMIT" in upper:
            continue
        statements.append(stmt)

    cursor = conn.cursor()
    try:
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        conn.commit()

        for i, stmt in enumerate(statements):
            try:
                cursor.execute(stmt)
                if "CREATE TABLE" in stmt.upper() or "INSERT INTO" in stmt.upper():
                    preview = stmt[:60].replace("\n", " ")
                    print(f"  [{i+1}/{len(statements)}] OK: {preview}...")
            except mysql.connector.Error as err:
                print(f"  [{i+1}/{len(statements)}] Error: {err}")
                print(f"     Statement: {stmt[:200]}...")

        conn.commit()
    finally:
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        conn.commit()
        cursor.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run backup SQL file against database")
    parser.add_argument(
        "--file", "-f",
        type=Path,
        default=DEFAULT_SQL_FILE,
        help="Path to SQL backup file",
    )
    parser.add_argument(
        "--drop-tables",
        action="store_true",
        help="Drop existing tables before restore (use for full restore)",
    )
    args = parser.parse_args()

    if not args.file.exists():
        print(f"Error: SQL file not found: {args.file}")
        sys.exit(1)

    print(f"Connecting to {db_settings.host}:{db_settings.port}/{db_settings.name}...")
    conn = mysql.connector.connect(
        host=db_settings.host,
        port=db_settings.port,
        database=db_settings.name,
        user=db_settings.user,
        password=db_settings.password,
        ssl_disabled=False,
        ssl_verify_cert=False,
    )

    if args.drop_tables:
        print("Dropping existing tables...")
        drop_tables(conn)

    print(f"Executing: {args.file}")
    execute_sql_file(conn, args.file)
    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()
