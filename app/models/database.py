import psycopg2
import os
from psycopg2 import extras
from contextlib import contextmanager
from app.models.common import printer

def get_db_config():
    return {
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT"),
        "database": os.getenv("DB_NAME")
    }


@contextmanager
def get_db_connection():
    conn = psycopg2.connect(**get_db_config(), cursor_factory=extras.RealDictCursor)
    try:
        yield conn
    except Exception as e:
        printer(f"Errore DB: {e}")
    finally:
        conn.close()


def get_cursor(conn):
    return conn.cursor()
