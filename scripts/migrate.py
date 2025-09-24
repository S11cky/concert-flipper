import os
import psycopg2
from glob import glob

MIGRATIONS_DIR = os.path.join("db", "migrations")

def run():
    conn = psycopg2.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=os.getenv("PGPORT", "5432"),
        user=os.getenv("PGUSER", "postgres"),
        password=os.getenv("PGPASSWORD", "postgres"),
        dbname=os.getenv("PGDATABASE", "concert_flipper"),
    )
    files = sorted(glob(os.path.join(MIGRATIONS_DIR, "*.sql")))
    if not files:
        print("⚠️  No migration files found.")
        return

    with conn, conn.cursor() as cur:
        for path in files:
            with open(path, "r", encoding="utf-8-sig") as f:
                sql = f.read()
            print(f"Applying: {os.path.basename(path)}")
            cur.execute(sql)
    print("✅ All migrations applied.")

if __name__ == "__main__":
    run()
