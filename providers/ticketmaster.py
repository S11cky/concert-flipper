import os
from decimal import Decimal
import requests
from datetime import datetime, timedelta, timezone

TM_BASE = "https://app.ticketmaster.com/discovery/v2"

def _tm_key() -> str | None:
    return os.getenv("TICKETMASTER_API_KEY")

BLOCKED_SUBSTRINGS = [
    "tribute", "experience", "sing-along", "karaoke", "cover",
    "suite", "logen", "loge", "package", "business", "vip",
    "tribute show", "unofficial", "sta hlzeit", "stahlzeit"  # tribute na Rammstein
]

def _looks_official(title: str, artist: str) -> bool:
    t = (title or "").casefold()
    a = (artist or "").casefold()
    if a not in t:
        return False
    return not any(b in t for b in BLOCKED_SUBSTRINGS)

def fetch_events(
    performer_query: str | None = None,
    country_codes: list[str] | None = None,   # napr. ["SK","CZ","AT","DE","PL","HU","IT"]
    size: int = 20,
    days_ahead: int = 365,
    exclude_keywords: list[str] | None = None
):
    TM_KEY = _tm_key()
    if not TM_KEY:
        return []

    if exclude_keywords:
        # umožníme pridať vlastné blokované slová z ingestu
        for x in exclude_keywords:
            if x and x.casefold() not in BLOCKED_SUBSTRINGS:
                BLOCKED_SUBSTRINGS.append(x.casefold())

    now = datetime.now(timezone.utc)
    end = now + timedelta(days=days_ahead)
    params_base = {
        "apikey": TM_KEY,
        "size": size,
        "sort": "date,asc",
        "classificationName": "music",
        "startDateTime": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "endDateTime": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if performer_query:
        params_base["keyword"] = performer_query

    cc_list = country_codes or [None]
    results = []
    for cc in cc_list:
        params = dict(params_base)
        if cc:
            params["countryCode"] = cc

        r = requests.get(f"{TM_BASE}/events.json", params=params, timeout=25)
        r.raise_for_status()
        data = r.json()
        events = (data.get("_embedded") or {}).get("events", [])

        for ev in events:
            name = (ev.get("name") or "")
            # hrubý filter (blokované slová)
            low = name.casefold()
            if any(b in low for b in BLOCKED_SUBSTRINGS):
                continue

            eid = ev.get("id")
            dates = ev.get("dates") or {}
            start = dates.get("start") or {}
            local_date = start.get("localDate")
            local_time = start.get("localTime")

            city_name = None
            currency = None
            venues = (ev.get("_embedded") or {}).get("venues") or []
            if venues:
                city_name = (venues[0].get("city") or {}).get("name")

            face_min = face_max = None
            for pr in ev.get("priceRanges") or []:
                try:
                    if pr.get("min") is not None:
                        face_min = Decimal(str(pr["min"]))
                    if pr.get("max") is not None:
                        face_max = Decimal(str(pr["max"]))
                    currency = pr.get("currency") or currency
                    break
                except Exception:
                    pass

            results.append({
                "provider": "ticketmaster",
                "provider_event_id": eid,
                "title": name,
                "date": local_date,
                "time": local_time,
                "city": city_name,
                "face_min": face_min,
                "face_max": face_max,
                "secondary_floor": None,
                "listings_count": None,
                "tickets_remaining_pct": None,
                "currency": currency or "USD",
                "source": "ticketmaster",
            })
    return results
