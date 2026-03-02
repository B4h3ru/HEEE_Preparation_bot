from typing import List, Optional

from db.connection import db_cursor


def get_or_create_user(
    telegram_id: int,
    username: Optional[str],
    first_name: Optional[str],
    last_name: Optional[str],
) -> int:
    with db_cursor(commit=True) as cursor:
        cursor.execute(
            """
            SELECT id FROM users WHERE telegram_id = %s
            """,
            (telegram_id,),
        )
        row = cursor.fetchone()
        if row:
            cursor.execute(
                """
                UPDATE users
                SET username = %s, first_name = %s, last_name = %s
                WHERE id = %s
                """,
                (username, first_name, last_name, row["id"]),
            )
            return row["id"]

        cursor.execute(
            """
            INSERT INTO users (telegram_id, username, first_name, last_name)
            VALUES (%s, %s, %s, %s)
            """,
            (telegram_id, username, first_name, last_name),
        )
        return cursor.lastrowid


def set_premium_by_username(username: str, is_premium: bool) -> int:
    """
    Returns number of affected rows.
    """
    with db_cursor(commit=True) as cursor:
        cursor.execute(
            """
            UPDATE users
            SET is_premium = %s
            WHERE username = %s
            """,
            (int(is_premium), username),
        )
        return cursor.rowcount


def list_all_telegram_ids() -> List[int]:
    """Returns all telegram_ids from users table for broadcasting."""
    with db_cursor() as cursor:
        cursor.execute("SELECT telegram_id FROM users")
        return [row["telegram_id"] for row in cursor.fetchall() if row.get("telegram_id")]


def is_user_premium(user_id: int) -> bool:
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT is_premium
            FROM users
            WHERE id = %s
            """,
            (user_id,),
        )
        row = cursor.fetchone()
        return bool(row and row.get("is_premium"))

