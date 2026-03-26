from typing import Optional

from db.connection import db_cursor


def get_allow_all() -> bool:
    """
    Returns True if admin allows ALL users to use premium features.
    If the table is missing or empty, defaults to False (Only Premium User).
    """
    try:
        with db_cursor() as cursor:
            cursor.execute(
                """
                SELECT allow_all
                FROM premium_policy
                ORDER BY id DESC
                LIMIT 1
                """
            )
            row = cursor.fetchone()
            if not row:
                return False
            return bool(row.get("allow_all"))
    except Exception:
        return False


def set_allow_all(allow_all: bool, policy_name: Optional[str] = None) -> None:
    """
    Updates premium policy in DB. Does not change any user rows.
    Assumes `premium_policy` table has at least columns:
      - id, policy_name, allow_all, created_at
    """
    if policy_name is None:
        policy_name = "Allow ALL User" if allow_all else "Only Premium User"

    allow_all_int = int(bool(allow_all))
    with db_cursor(commit=True) as cursor:
        # If a row exists, update the most recent one. Otherwise insert.
        cursor.execute(
            """
            SELECT id
            FROM premium_policy
            ORDER BY id DESC
            LIMIT 1
            """
        )
        row = cursor.fetchone()
        if row and row.get("id") is not None:
            cursor.execute(
                """
                UPDATE premium_policy
                SET policy_name = %s, allow_all = %s
                WHERE id = %s
                """,
                (policy_name, allow_all_int, row["id"]),
            )
        else:
            cursor.execute(
                """
                INSERT INTO premium_policy (policy_name, allow_all)
                VALUES (%s, %s)
                """,
                (policy_name, allow_all_int),
            )

