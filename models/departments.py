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
