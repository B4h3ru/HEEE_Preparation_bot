from contextlib import contextmanager
from typing import Generator

import mysql.connector
from mysql.connector import MySQLConnection

from config.settings import db_settings


def get_connection() -> MySQLConnection:
    return mysql.connector.connect(
        host=db_settings.host,
        port=db_settings.port,
        database=db_settings.name,
        user=db_settings.user,
        password=db_settings.password,
        ssl_disabled=False,
        ssl_verify_cert=False,
    )


@contextmanager
def db_cursor(commit: bool = False) -> Generator:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        yield cursor
        if commit:
            conn.commit()
    finally:
        cursor.close()
        conn.close()
