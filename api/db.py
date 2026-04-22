from contextlib import contextmanager

from psycopg import connect
from psycopg.rows import dict_row

from api.config import DATABASE_URL, require_env


@contextmanager
def get_db():
    require_env("DATABASE_URL")
    conn = connect(DATABASE_URL, row_factory=dict_row)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
