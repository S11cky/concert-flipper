from db import get_conn, dict_cursor
from services.marketplaces import stubhub_search_url

def main():
    # vezmeme všetky budúce eventy bez resale_url
    sql_sel = """
      SELECT e.id, e.event_name, e.event_date, e.city, e.country, a.name AS artist_name
      FROM events e
      JOIN artists a ON a.id = e.artist_id
      WHERE e.event_date >= CURRENT_DATE
        AND (e.resale_url IS NULL OR e.resale_url = '')
    """
    sql_upd = "UPDATE events SET resale_url = %s WHERE id = %s"

    updated = 0
    with get_conn() as conn, dict_cursor(conn) as cur:
        cur.execute(sql_sel)
        rows = cur.fetchall()
        for r in rows:
            url = stubhub_search_url(
                artist_name=r["artist_name"],
                city=r["city"],
                date_iso=r["event_date"].isoformat(),
                country_code=r["country"],
            )
            cur.execute(sql_upd, (url, r["id"]))
            updated += 1
    print(f"✅ StubHub resale URLs doplnené: {updated}")

if __name__ == "__main__":
    main()
