from typing import Optional
from datetime import datetime, date
from db import get_conn, dict_cursor
from providers.base import EventData

def upsert_artist(name: str, spotify_id: Optional[str] = None,
                  popularity: Optional[int] = None, followers: Optional[int] = None) -> int:
    sql = """
    INSERT INTO artists (name, spotify_id, popularity, followers, updated_at)
    VALUES (%s, %s, %s, %s, now())
    ON CONFLICT (name)
    DO UPDATE SET
      spotify_id = COALESCE(EXCLUDED.spotify_id, artists.spotify_id),
      popularity = COALESCE(EXCLUDED.popularity, artists.popularity),
      followers  = COALESCE(EXCLUDED.followers, artists.followers),
      updated_at = now()
    RETURNING id;
    """
    with get_conn() as conn, dict_cursor(conn) as cur:
        cur.execute(sql, (name, spotify_id, popularity, followers))
        return cur.fetchone()["id"]

def _to_date(dt: datetime) -> date:
    # events.event_date je DATE; pre istotu si vezmeme iba dátum
    return dt.date() if isinstance(dt, datetime) else dt

def upsert_event(e: EventData, artist_id: int) -> int:
    # venue_section držíme ako text (napr. JSON string), sections dict si zmeníme na "A: 40, B: 0"
    venue_section = None
    if e.sections:
        venue_section = ", ".join(f"{k}: {v}" for k, v in e.sections.items())

    sql = """
    INSERT INTO events (
      external_id, source_vendor, artist_id, event_name, event_date, venue, city, country,
      buy_url, resale_url, lowest_price, lowest_resale_price, venue_section, seats_total, seats_available
    ) VALUES (
      %(external_id)s, %(source_vendor)s, %(artist_id)s, %(event_name)s, %(event_date)s, %(venue)s, %(city)s, %(country)s,
      %(buy_url)s, %(resale_url)s, %(lowest_price)s, %(lowest_resale_price)s, %(venue_section)s, %(seats_total)s, %(seats_available)s
    )
    ON CONFLICT (source_vendor, external_id) DO UPDATE SET
      artist_id = EXCLUDED.artist_id,
      event_name = EXCLUDED.event_name,
      event_date = EXCLUDED.event_date,
      venue = EXCLUDED.venue,
      city = EXCLUDED.city,
      country = EXCLUDED.country,
      buy_url = EXCLUDED.buy_url,
      resale_url = EXCLUDED.resale_url,
      lowest_price = EXCLUDED.lowest_price,
      lowest_resale_price = EXCLUDED.lowest_resale_price,
      venue_section = EXCLUDED.venue_section,
      seats_total = EXCLUDED.seats_total,
      seats_available = EXCLUDED.seats_available
    RETURNING id;
    """
    params = {
        "external_id": e.external_id,
        "source_vendor": e.source_vendor,
        "artist_id": artist_id,
        "event_name": e.event_name,
        "event_date": _to_date(e.event_date),
        "venue": e.venue,
        "city": e.city,
        "country": e.country,
        "buy_url": e.buy_url,
        "resale_url": e.resale_url,
        "lowest_price": e.lowest_price,
        "lowest_resale_price": e.lowest_resale_price,
        "venue_section": venue_section,
        "seats_total": e.seats_total,
        "seats_available": e.seats_available,
    }
    with get_conn() as conn, dict_cursor(conn) as cur:
        cur.execute(sql, params)
        return cur.fetchone()["id"]
