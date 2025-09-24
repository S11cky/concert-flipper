import os
import uuid
import datetime as dt
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import requests
from providers.ticketmaster import fetch_events as tm_fetch

load_dotenv()
DB_URL   = os.getenv("DB_URL")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TG_CHAT  = os.getenv("TELEGRAM_CHAT_ID")

engine = create_engine(DB_URL, pool_pre_ping=True)
chat_id = int(TG_CHAT) if TG_CHAT else None

# ---- Telegram ----
def send_tg(text: str) -> None:
    if not TG_TOKEN or not chat_id:
        print("Telegram creds not configured; skipping send."); return
    try:
        r = requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                          data={"chat_id": chat_id, "text": text})
        if r.status_code >= 400:
            print("Telegram error:", r.status_code, r.text[:200])
    except Exception as e:
        print("Telegram request failed:", e)

# ---- UUID pre Ticketmaster ----
TM_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "ticketmaster")
def tm_uuid(event_id_str: str) -> uuid.UUID:
    return uuid.uuid5(TM_NAMESPACE, event_id_str)

# ---- DB ops ----
def save_snapshot(event_uuid: uuid.UUID, data: dict) -> None:
    q = text("""
    INSERT INTO ticket_price_snapshots
      (event_id, face_min, face_max, secondary_floor, listings_count, tickets_remaining_pct, currency, source)
    VALUES
      (:event_id, :face_min, :face_max, :secondary_floor, :listings_count, :tickets_remaining_pct, :currency, :source)
    """)
    payload = {
        "event_id": str(event_uuid),
        "face_min": data.get("face_min"),
        "face_max": data.get("face_max"),
        "secondary_floor": data.get("secondary_floor"),
        "listings_count": data.get("listings_count"),
        "tickets_remaining_pct": data.get("tickets_remaining_pct"),
        "currency": data.get("currency") or "USD",
        "source": data.get("source") or "ticketmaster",
    }
    with engine.begin() as conn:
        conn.execute(q, payload)

def refresh_daily_view() -> None:
    with engine.begin() as conn:
        conn.execute(text("REFRESH MATERIALIZED VIEW ticket_prices_daily;"))

def get_daily_row(event_uuid: uuid.UUID, day=None):
    if day is None:
        day = dt.date.today()
    q = text("SELECT * FROM ticket_prices_daily WHERE event_id = :event_id AND day = :day")
    with engine.begin() as conn:
        row = conn.execute(q, {"event_id": str(event_uuid), "day": day}).mappings().first()
    return dict(row) if row else None

def event_seen(event_uuid: uuid.UUID) -> bool:
    q = text("SELECT 1 FROM ticket_price_snapshots WHERE event_id = :eid LIMIT 1")
    with engine.begin() as conn:
        row = conn.execute(q, {"eid": str(event_uuid)}).first()
    return row is not None

def read_artists(path="artists.txt"):
    if not os.path.exists(path): return []
    arts = []
    with open(path, "r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"): continue
            arts.append(line)
    return arts

# ---- heuristiky filtrov ----
BLOCKED = ["tribute","experience","sing-along","karaoke","cover","suite","logen","loge","package","business","vip","unofficial","stahlzeit"]
CITY_WHITELIST = {"Vienna","Wien","Praha","Prague","Bratislava","Budapest","Krakow","Kraków","Berlin","Munich","München","Hamburg","Frankfurt","Milan","Milano","Rome","Roma","Warsaw","Wiener Neustadt"}

def is_official(title: str, artist: str) -> bool:
    t = (title or "").casefold()
    a = (artist or "").casefold()
    if a not in t: return False
    return not any(b in t for b in BLOCKED)

if __name__ == "__main__":
    artists = read_artists()
    if not artists:
        print("artists.txt je prázdny – doplň aspoň jedného interpreta."); raise SystemExit

    COUNTRY_CODES = ["SK","CZ","AT","DE","PL","HU","IT"]
    all_lines = []
    new_event_alerts = []

    for artist in artists:
        tm_events = tm_fetch(
            performer_query=artist,
            country_codes=COUNTRY_CODES,
            size=40,
            days_ahead=540,
            exclude_keywords=BLOCKED
        ) or []

        # lokálne filtrovanie podľa názvu a whitelistu miest
        filtered = []
        for ev in tm_events:
            if not is_official(ev.get("title",""), artist):
                continue
            city = (ev.get("city") or "")
            if CITY_WHITELIST and city and city not in CITY_WHITELIST:
                continue
            filtered.append(ev)

        uuids = []
        for ev in filtered:
            euid = tm_uuid(ev["provider_event_id"])
            first_time = not event_seen(euid)
            save_snapshot(euid, ev)
            uuids.append((euid, ev))
            if first_time:
                t = ev.get("title") or artist
                d = ev.get("date") or ""
                c = ev.get("city") or ""
                new_event_alerts.append(f"🚨 NEW EVENT: {t} {('('+c+')') if c else ''} {d}")

        try:
            refresh_daily_view()
        except Exception as e:
            print("Refresh MV error:", e)

        lines = [f"🎵 {artist}"]
        shown = 0
        for euid, ev in uuids:
            if shown >= 3: break
            daily = get_daily_row(euid)
            if daily:
                t = ev.get("title") or "event"
                c = ev.get("city") or ""
                d = ev.get("date") or ""
                fmin = daily.get('face_min_day_min'); fmax = daily.get('face_max_day_max')
                lines.append(f"• {t} {('('+c+')') if c else ''} {d}  face[{fmin}/{fmax}]")
                shown += 1
        if shown == 0:
            lines.append("• (žiadne denné dáta)")
        all_lines.append("\n".join(lines))

    # Najprv NEW EVENT alerty (ak sú)
    if new_event_alerts:
        send_tg("\n".join(new_event_alerts))

    # Potom denný prehľad
    msg = "📊 Denný prehľad – vybraní interpreti (Ticketmaster, EU)\n\n" + "\n\n".join(all_lines[:5])
    send_tg(msg)
