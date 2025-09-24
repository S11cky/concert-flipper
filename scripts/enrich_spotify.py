from db import get_conn, dict_cursor
from providers.spotify import fetch_artist_metrics
from services.save_event import upsert_artist

def main():
    q = """
      SELECT DISTINCT a.name
      FROM artists a
      JOIN events e ON e.artist_id = a.id
      WHERE (a.popularity IS NULL OR a.followers IS NULL)
    """
    updated = 0
    with get_conn() as conn, dict_cursor(conn) as cur:
        cur.execute(q)
        rows = cur.fetchall()
        for r in rows:
            name = r["name"]
            m = fetch_artist_metrics(name)
            if not m:
                continue
            upsert_artist(name, m["spotify_id"], m["popularity"], m["followers"])
            updated += 1
    print(f"✅ Spotify enrich done. Updated: {updated}")

if __name__ == "__main__":
    main()
