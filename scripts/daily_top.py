from datetime import date
from db import get_conn, dict_cursor
from services.ranking import score_artist, top_percent, sell_window, fallback_scores

def fetch_upcoming_with_metrics():
    sql = """
      SELECT e.id as event_id, e.event_name, e.event_date, e.city, e.country,
             e.buy_url, e.resale_url, e.lowest_price, e.lowest_resale_price,
             a.name as artist_name, a.popularity, a.followers
      FROM events e
      JOIN artists a ON a.id = e.artist_id
      WHERE e.event_date >= CURRENT_DATE
    """
    with get_conn() as conn, dict_cursor(conn) as cur:
        cur.execute(sql)
        return cur.fetchall()

def build_top_list(rows):
    today = date.today()
    have_spotify = any((r["popularity"] is not None and r["followers"] is not None) for r in rows)

    enriched = []
    if have_spotify:
        for r in rows:
            sc = score_artist(r["popularity"], r["followers"]) if (r["popularity"] is not None and r["followers"] is not None) else 0.0
            days = (r["event_date"] - today).days
            enriched.append({**r, "score": sc, "days_to_event": days, "sell_advice": sell_window(r["popularity"] or 0, days)})
    else:
        fb = fallback_scores(rows)  # dict {artist_name: score}
        for r in rows:
            days = (r["event_date"] - today).days
            sc = fb.get(r["artist_name"], 0.0)
            enriched.append({**r, "score": sc, "days_to_event": days, "sell_advice": sell_window(60, days)})

    return top_percent(enriched, "score", 0.15)

def format_text(top_events):
    lines = ["🔥 Denné top koncerty (Top 15 %):"]
    for e in top_events:
        price = []
        if e["lowest_price"] is not None:
            price.append(f"buy od {e['lowest_price']:.2f}")
        if e["lowest_resale_price"] is not None:
            price.append(f"resale od {e['lowest_resale_price']:.2f}")
        price_txt = (" | " + " • ".join(price)) if price else ""
        links = []
        if e["buy_url"]:
            links.append(f"[kúpiť]({e['buy_url']})")
        if e["resale_url"]:
            links.append(f"[predať]({e['resale_url']})")
        links_txt = (" | " + " ".join(links)) if links else ""
        lines.append(
          f"• {e['artist_name']} — {e['event_name']} ({e['event_date']}) "
          f"{e['city'] or ''} {e['country'] or ''} — T-{e['days_to_event']} — "
          f"{e['sell_advice']}{price_txt}{links_txt}"
        )
    return "\n".join(lines)

def main():
    rows = fetch_upcoming_with_metrics()
    top_events = build_top_list(rows)
    print(format_text(top_events))

if __name__ == "__main__":
    main()
