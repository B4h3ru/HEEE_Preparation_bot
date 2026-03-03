"""
Backup executor script - runs heee_preparation (1).sql against the configured database.
Use to restore schema and data from backup.

Usage:
    python run_backup_sql.py --drop-tables
    python run_backup_sql.py --file "path/to/backup.sql" --drop-tables
"""

import argparse
import sys
from pathlib import Path

import mysql.connector

from config.settings import db_settings


DEFAULT_SQL_FILE = Path(__file__).parent / "heee_preparation (1).sql"


def _safe_print(text: str) -> None:
    """Print text, handling Unicode on Windows."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("utf-8", errors="replace").decode("utf-8"))


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
    """Execute SQL file using multi-statement execution."""
    content = sql_path.read_text(encoding="utf-8", errors="replace")

    cursor = conn.cursor()
    try:
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        cursor.execute("SET sql_require_primary_key = 0")
        conn.commit()

        try:
            cursor.execute(content)
            while cursor.with_rows:
                cursor.fetchall()
            while cursor.nextset():
                if cursor.with_rows:
                    cursor.fetchall()
            conn.commit()
            _safe_print("  Executed successfully.")
        except mysql.connector.Error as err:
            _safe_print(f"  Error: {err}")
            conn.rollback()
    finally:
        try:
            cursor.execute("SET sql_require_primary_key = 1")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
            conn.commit()
        except Exception:
            pass
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

    host = db_settings.host
    port = db_settings.port
    db_name = db_settings.name
    user = db_settings.user
    password = db_settings.password

    print(f"Connecting to {host}:{port}/{db_name}...")
    conn = mysql.connector.connect(
        host=host,
        port=port,
        database=db_name,
        user=user,
        password=password,
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
