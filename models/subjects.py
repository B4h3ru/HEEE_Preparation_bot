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

