from typing import List, Dict

from db.connection import db_cursor


def list_subjects_by_department(department_id: int) -> List[Dict]:
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT id, name
            FROM subjects
            WHERE department_id = %s
            ORDER BY name
            """,
            (department_id,),
        )
        return cursor.fetchall()


def create_subject(department_id: int, name: str) -> int:
    with db_cursor(commit=True) as cursor:
        cursor.execute(
            """
            INSERT INTO subjects (department_id, name)
            VALUES (%s, %s)
            """,
            (department_id, name),
        )
        return cursor.lastrowid


def update_subject_name(subject_id: int, new_name: str) -> int:
    """Returns affected rows."""
    with db_cursor(commit=True) as cursor:
        cursor.execute(
            "UPDATE subjects SET name = %s WHERE id = %s",
            (new_name, subject_id),
        )
        return cursor.rowcount


def delete_subject(subject_id: int) -> int:
    """Returns affected rows."""
    with db_cursor(commit=True) as cursor:
        cursor.execute("DELETE FROM subjects WHERE id = %s", (subject_id,))
        return cursor.rowcount

