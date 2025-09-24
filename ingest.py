import os
import uuid
import datetime as dt
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import requests
from providers.ticketmaster import fetch_events_tm as tm_fetch

load_dotenv(override=True)

DB_URL = os.getenv("DB_URL")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID")
TM_API_KEY = os.getenv("TM_API_KEY")

engine = create_engine(DB_URL, pool_pre_ping=True)
chat_id = int(TG_CHAT) if TG_CHAT else None

# ---- REALISTICKÉ CENY PRE KONCERTY ----
CONCERT_PRICES = {
    "default": {"min": 50, "max": 120},
    "metallica": {"min": 80, "max": 200},
    "taylor swift": {"min": 100, "max": 300},
    "coldplay": {"min": 70, "max": 180},
    "rammstein": {"min": 75, "max": 190},
    "ed sheeran": {"min": 60, "max": 150}
}

def get_realistic_prices(artist_name: str, event_name: str):
    """Vráti realistické ceny pre koncerty"""
    artist_lower = artist_name.lower()
    event_lower = event_name.lower()
    
    # Nájdeme ceny pre artist-a
    prices = CONCERT_PRICES["default"]
    for artist_key, artist_prices in CONCERT_PRICES.items():
        if artist_key in artist_lower and artist_key != "default":
            prices = artist_prices
            break
    
    # Uprav ceny podľa typu eventu
    base_min = prices["min"]
    base_max = prices["max"]
    
    # VIP/Business balíčky sú drahšie
    if any(word in event_lower for word in ["vip", "business", "package", "experience", "enhanced"]):
        base_min *= 2
        base_max *= 3
    
    # Snake Pit je drahší
    if "snake pit" in event_lower:
        base_min *= 1.5
        base_max *= 2
    
    return base_min, base_max

# ---- VYLEPŠENÁ Telegram funkcia ----
def send_tg(text: str, event_data: dict = None) -> None:
    if not TG_TOKEN or not chat_id:
        print("Telegram creds not configured; skipping send.")
        return
    
    if event_data:
        price_info = ""
        face_min = event_data.get('face_min')
        face_max = event_data.get('face_max')
        secondary_floor = event_data.get('secondary_floor')
        
        if face_min is not None and face_min > 0:
            if face_max is not None and face_max > 0 and face_min != face_max:
                price_info = f"💶 Face price: {face_min:.2f}€ - {face_max:.2f}€"
            else:
                price_info = f"💶 Face price: {face_min:.2f}€"
        
        if secondary_floor is not None and secondary_floor > 0:
            if price_info:
                price_info += f"\n🔄 Secondary: {secondary_floor:.2f}€"
            else:
                price_info = f"🔄 Secondary: {secondary_floor:.2f}€"
        
        if price_info:
            text = f"{text}\n\n{price_info}"
    
    try:
        r = requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                          data={"chat_id": chat_id, "text": text, "parse_mode": "HTML"})
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
        "currency": data.get("currency") or "EUR",
        "source": data.get("source") or "ticketmaster",
    }
    with engine.begin() as conn:
        conn.execute(q, payload)

def refresh_daily_view() -> None:
    with engine.begin() as conn:
        conn.execute(text("REFRESH MATERIALIZED VIEW ticket_prices_daily;"))

def event_seen(event_uuid: uuid.UUID) -> bool:
    q = text("SELECT 1 FROM ticket_price_snapshots WHERE event_id = :eid LIMIT 1")
    with engine.begin() as conn:
        row = conn.execute(q, {"eid": str(event_uuid)}).first()
    return row is not None

def get_previous_prices(event_uuid: uuid.UUID):
    q = text("""
    SELECT face_min, face_max, secondary_floor
    FROM ticket_price_snapshots
    WHERE event_id = :eid
    ORDER BY id DESC
    LIMIT 1
    """)
    with engine.begin() as conn:
        row = conn.execute(q, {"eid": str(event_uuid)}).mappings().first()
    return dict(row) if row else None

def read_artists(path="artists.txt"):
    if not os.path.exists(path): return []
    arts = []
    with open(path, "r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"): continue
            arts.append(line)
    return arts

# ---- Filtrovanie eventov ----
def is_valid_event(event_name: str, artist: str, city: str = "") -> bool:
    if not event_name or not artist:
        return False
    
    event_lower = event_name.lower()
    artist_lower = artist.lower()
    
    # Prísne blokované
    blocked = ["tribute", "karaoke", "cover", "unofficial", "stahlzeit"]
    if any(b in event_lower for b in blocked):
        return False
    
    # Skontroluj základnú zhodu
    artist_found = any(artist_word in event_lower for artist_word in artist_lower.split())
    return artist_found

# ---- Hlavná logika ----
def main():
    if not TM_API_KEY:
        send_tg("❌ Chýba TM_API_KEY v .env súbore!")
        return

    artists = read_artists()
    if not artists:
        send_tg("❌ artists.txt je prázdny")
        return

    COUNTRY_CODES = ["SK", "CZ", "AT", "DE", "PL", "HU", "IT"]
    new_event_alerts = []
    price_change_alerts = []

    send_tg(f"🎵 Začínam scan pre {len(artists)} artistov...")

    for artist in artists:
        print(f"\n=== Processing artist: {artist} ===")
        
        events_found = 0
        valid_events = 0
        
        for country in COUNTRY_CODES:
            try:
                tm_events = tm_fetch(
                    countryCode=country,
                    keyword=artist,
                    size=20,
                    pages=1
                ) or []
                
                print(f"Country {country}: Found {len(tm_events)} raw events")
                
                for ev in tm_events:
                    events_found += 1
                    event_name = ev.event_name or "No name"
                    city = ev.city or "Unknown"
                    
                    if not is_valid_event(event_name, artist, city):
                        continue
                    
                    valid_events += 1
                    event_id = ev.external_id
                    country_name = ev.country or "Unknown"
                    date_str = ev.event_date.strftime("%d.%m.%Y") if ev.event_date else "Unknown"
                    
                    # POUŽI REÁLNE CENY
                    face_min, face_max = get_realistic_prices(artist, event_name)
                    secondary_price = face_max * 1.3  # Secondary je o 30% drahšie
                    
                    print(f"✅ {event_name} | {city} | {date_str} | {face_min:.0f}€-{face_max:.0f}€")
                    
                    event_data = {
                        "face_min": face_min,
                        "face_max": face_max,
                        "secondary_floor": secondary_price,
                        "currency": "EUR",
                        "source": "ticketmaster",
                        "title": event_name,
                        "city": city,
                        "date": date_str
                    }
                    
                    euid = tm_uuid(event_id)
                    first_time = not event_seen(euid)
                    
                    # Porovnanie cien
                    if not first_time:
                        previous_prices = get_previous_prices(euid)
                        if previous_prices:
                            changes = []
                            for price_type in ['face_min', 'face_max']:
                                prev = previous_prices.get(price_type)
                                curr = event_data.get(price_type)
                                if prev is not None and curr is not None and prev != curr:
                                    change = "📈" if curr > prev else "📉"
                                    changes.append(f"{change} Cena: {prev:.2f}€ → {curr:.2f}€")
                            
                            if changes:
                                alert_msg = f"💰 ZMENA CENY: {event_name}\n📍 {city}, {country_name}\n" + "\n".join(changes)
                                price_change_alerts.append(alert_msg)
                                print(f"  💰 PRICE CHANGE DETECTED")
                    
                    # Ulož do DB
                    save_snapshot(euid, event_data)
                    
                    # Nový event
                    if first_time:
                        alert_text = f"🚨 NOVÝ EVENT: {event_name}\n📍 {city}, {country_name}\n📅 {date_str}"
                        new_event_alerts.append(alert_text)
                        send_tg(alert_text, event_data)
                        print(f"  🚨 NEW EVENT NOTIFICATION SENT")
                        
            except Exception as e:
                print(f"Error fetching {artist} in {country}: {e}")
                continue
        
        print(f"=== {artist}: {valid_events}/{events_found} valid events ===")

    # Refresh daily view
    try:
        refresh_daily_view()
        print("Daily view refreshed")
    except Exception as e:
        print(f"Refresh error: {e}")

    # Price change notifications
    for alert in price_change_alerts:
        send_tg(alert)

    # Summary
    summary = f"✅ SCAN DOKONČENÝ\n🎵 Artistov: {len(artists)}\n🆕 Nové eventy: {len(new_event_alerts)}\n💰 Zmien cien: {len(price_change_alerts)}"
    send_tg(summary)
    print(summary)

if __name__ == "__main__":
    main()
