from typing import List, Dict

from db.connection import db_cursor


def list_departments() -> List[Dict]:
    with db_cursor() as cursor:
        cursor.execute("SELECT id, name FROM departments ORDER BY name")
        return cursor.fetchall()


def create_department(name: str) -> int:
    with db_cursor(commit=True) as cursor:
        cursor.execute(
            "INSERT INTO departments (name) VALUES (%s)",
            (name,),
        )
        return cursor.lastrowid


def update_department_name(department_id: int, new_name: str) -> int:
    """Returns affected rows."""
    with db_cursor(commit=True) as cursor:
        cursor.execute(
            "UPDATE departments SET name = %s WHERE id = %s",
            (new_name, department_id),
        )
        return cursor.rowcount


def delete_department(department_id: int) -> int:
    """Returns affected rows."""
    with db_cursor(commit=True) as cursor:
        cursor.execute("DELETE FROM departments WHERE id = %s", (department_id,))
        return cursor.rowcount
