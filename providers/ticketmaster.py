import os
import requests
from datetime import datetime
from typing import List, Optional
from providers.base import EventData

TM_API_URL = "https://app.ticketmaster.com/discovery/v2/events.json"

def _get_api_key() -> str:
    # Prefer env, fallback .env
    api = os.getenv("TM_API_KEY")
    if api:
        return api
    # optional .env load
    try:
        from dotenv import load_dotenv
        load_dotenv()
        api = os.getenv("TM_API_KEY")
    except Exception:
        api = None
    if not api:
        raise RuntimeError("Missing TM_API_KEY. Set environment variable first.")
    return api

def _safe_date(ev: dict) -> Optional[datetime]:
    # Ticketmaster: dates.start.localDate (YYYY-MM-DD) a localTime (HH:MM:SS)
    d = ev.get("dates", {}).get("start", {})
    local_date = d.get("localDate")
    local_time = d.get("localTime")
    if not local_date:
        return None
    iso = local_date + ("T" + local_time if local_time else "T00:00:00")
    try:
        # ponecháme naive datetime; do DB ukladáme len date
        return datetime.fromisoformat(iso)
    except Exception:
        return None

def _venue_parts(ev: dict):
    v = (ev.get("_embedded") or {}).get("venues") or []
    if not v:
        return None, None, None
    vv = v[0]
    venue = vv.get("name")
    city = (vv.get("city") or {}).get("name")
    country = (vv.get("country") or {}).get("countryCode") or (vv.get("country") or {}).get("name")
    return venue, city, country

def _lowest_price(ev: dict) -> Optional[float]:
    # Ticketmaster priceRanges: [{"type":"standard","currency":"EUR","min":30.0,"max":80.0}, ...]
    pr = ev.get("priceRanges") or []
    try:
        mins = [p.get("min") for p in pr if p.get("min") is not None]
        return float(min(mins)) if mins else None
    except Exception:
        return None

def fetch_events_tm(countryCode: Optional[str] = None, keyword: Optional[str] = None, size: int = 100, pages: int = 3) -> List[EventData]:
    """
    Stiahne events z Ticketmaster Discovery API.
    - countryCode (napr. "SK", "AT", "DE") filtruje podľa krajiny
    - keyword môže byť napr. meno interpreta alebo "concert"
    """
    api_key = _get_api_key()
    out: List[EventData] = []
    page = 0
    while page < pages:
        params = {
            "apikey": api_key,
            "classificationName": "music",
            "size": size,
            "page": page
        }
        if countryCode:
            params["countryCode"] = countryCode
        if keyword:
            params["keyword"] = keyword

        r = requests.get(TM_API_URL, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()

        events = (data.get("_embedded") or {}).get("events") or []
        for ev in events:
            # artist name: berieme prvý performer
            attractions = (ev.get("_embedded") or {}).get("attractions") or []
            artist_name = None
            if attractions:
                # prefer headliner ak je označený, inak prvý
                headliners = [a for a in attractions if a.get("test") is False] or attractions
                artist_name = (headliners[0] or {}).get("name") or attractions[0].get("name")
            if not artist_name:
                # fallback: z názvu eventu vyparsovať neskôr; teraz preskoč
                continue

            event_id = ev.get("id")
            event_name = ev.get("name")
            event_date = _safe_date(ev)
            venue, city, country = _venue_parts(ev)

            # buy link je priamo url na event (Ticketmaster vždy dodá)
            buy_url = ev.get("url")

            out.append(EventData(
                external_id=event_id,
                source_vendor="ticketmaster",
                artist_name=artist_name,
                event_name=event_name,
                event_date=event_date or datetime.now(),
                venue=venue,
                city=city,
                country=country,
                buy_url=buy_url,
                resale_url=None,          # z Ticketmastera nie vždy vieme resale
                lowest_price=_lowest_price(ev),
                lowest_resale_price=None,
                sections=None,
                seats_total=None,
                seats_available=None
            ))

        # stránkovanie
        pg = data.get("page") or {}
        total_pages = pg.get("totalPages") or 1
        page += 1
        if page >= total_pages:
            break

    return out
