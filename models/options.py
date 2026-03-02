from typing import List, Dict

from db.connection import db_cursor


def add_option(question_id: int, option_text: str, is_correct: bool = False) -> int:
    with db_cursor(commit=True) as cursor:
        cursor.execute(
            """
            INSERT INTO options (question_id, option_text, is_correct)
            VALUES (%s, %s, %s)
            """,
            (question_id, option_text, int(is_correct)),
        )
        return cursor.lastrowid


def get_options_for_question(question_id: int) -> List[Dict]:
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT id, option_text, is_correct
            FROM options
            WHERE question_id = %s
            ORDER BY id
            """,
            (question_id,),
        )
        return cursor.fetchall()
