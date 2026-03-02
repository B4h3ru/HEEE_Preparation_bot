from typing import List, Dict

from db.connection import db_cursor


def create_quiz_session(
    user_id: int,
    department_id: int,
    subject_id: int,
    total_questions: int,
) -> int:
    with db_cursor(commit=True) as cursor:
        cursor.execute(
            """
            INSERT INTO quiz_sessions (user_id, department_id, subject_id, total_questions)
            VALUES (%s, %s, %s, %s)
            """,
            (user_id, department_id, subject_id, total_questions),
        )
        return cursor.lastrowid


def add_session_questions(session_id: int, question_ids: List[int]) -> None:
    with db_cursor(commit=True) as cursor:
        cursor.executemany(
            """
            INSERT INTO session_questions (session_id, question_id)
            VALUES (%s, %s)
            """,
            [(session_id, qid) for qid in question_ids],
        )


def save_answer(
    session_id: int,
    question_id: int,
    selected_option_id: int,
    is_correct: bool,
) -> None:
    with db_cursor(commit=True) as cursor:
        cursor.execute(
            """
            INSERT INTO user_answers
                (session_id, question_id, selected_option_id, is_correct)
            VALUES (%s, %s, %s, %s)
            """,
            (session_id, question_id, selected_option_id, int(is_correct)),
        )


def update_score(session_id: int) -> None:
    with db_cursor(commit=True) as cursor:
        cursor.execute(
            """
            SELECT COUNT(*) AS correct_count
            FROM user_answers
            WHERE session_id = %s AND is_correct = 1
            """,
            (session_id,),
        )
        row = cursor.fetchone()
        correct_count = row["correct_count"] if row else 0

        cursor.execute(
            """
            UPDATE quiz_sessions
            SET score = %s, finished_at = NOW()
            WHERE id = %s
            """,
            (correct_count, session_id),
        )


def get_session_summary(session_id: int) -> Dict:
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT total_questions, score
            FROM quiz_sessions
            WHERE id = %s
            """,
            (session_id,),
        )
        return cursor.fetchone() or {}


def has_free_10_attempt(user_id: int) -> bool:
    """
    Returns True if the user has already used their free
    "Random 10 Questions" attempt.

    We treat any small session (up to 10 questions) as consuming
    the free attempt, so even if a subject has fewer than 10
    questions it still counts.
    """
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT 1
            FROM quiz_sessions
            WHERE user_id = %s AND total_questions <= 10
            LIMIT 1
            """,
            (user_id,),
        )
        return cursor.fetchone() is not None
