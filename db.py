import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

# načítaj .env, ak existuje
load_dotenv()

def get_conn():
    return psycopg2.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=os.getenv("PGPORT", "5432"),
        user=os.getenv("PGUSER", "app"),            # default prispôsobený tvojmu dockeru
        password=os.getenv("PGPASSWORD", "app"),
        dbname=os.getenv("PGDATABASE", "tickets"),
    )

def dict_cursor(conn):
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
