from typing import List, Dict, Optional

from db.connection import db_cursor, get_connection


def create_question(
    department_id: Optional[int],
    subject_id: Optional[int],
    question_text: str,
    explanation: Optional[str] = None,
) -> int:
    with db_cursor(commit=True) as cursor:
        cursor.execute(
            """
            INSERT INTO questions (department_id, subject_id, question_text, explanation)
            VALUES (%s, %s, %s, %s)
            """,
            (department_id, subject_id, question_text, explanation),
        )
        return cursor.lastrowid


def list_questions_by_department(department_id: int) -> List[Dict]:
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT q.id, q.question_text, q.explanation
            FROM questions q
            WHERE q.department_id = %s
            ORDER BY q.id
            """,
            (department_id,),
        )
        return cursor.fetchall()


def list_questions_by_subject(subject_id: int) -> List[Dict]:
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT q.id, q.question_text, q.explanation
            FROM questions q
            WHERE q.subject_id = %s
            ORDER BY q.id
            """,
            (subject_id,),
        )
        return cursor.fetchall()


def get_random_questions(
    department_id: int,
    subject_id: int,
    limit: int,
) -> List[Dict]:
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT id, question_text, explanation
            FROM questions
            WHERE department_id = %s AND subject_id = %s
            ORDER BY RAND()
            LIMIT %s
            """,
            (department_id, subject_id, limit),
        )
        return cursor.fetchall()


def create_question_with_options_atomic(
    department_id: int,
    subject_id: int,
    question_text: str,
    explanation: Optional[str],
    options: List[str],
    correct_index: int,
) -> int:
    """
    Creates question + all options in one transaction.
    Rolls back everything if any insert fails.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            INSERT INTO questions (department_id, subject_id, question_text, explanation)
            VALUES (%s, %s, %s, %s)
            """,
            (department_id, subject_id, question_text, explanation),
        )
        question_id = cursor.lastrowid

        cursor.executemany(
            """
            INSERT INTO options (question_id, option_text, is_correct)
            VALUES (%s, %s, %s)
            """,
            [
                (question_id, opt_text, int(idx == correct_index))
                for idx, opt_text in enumerate(options)
            ],
        )
        conn.commit()
        return question_id
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

