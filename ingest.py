import os, datetime as dt
from decimal import Decimal
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from telegram import Bot

load_dotenv()
DB_URL = os.getenv("DB_URL")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID")

if DB_URL is None:
raise RuntimeError("DB_URL is not set. Configure .env or environment variable.")

engine = create_engine(DB_URL, pool_pre_ping=True)
bot = Bot(TG_TOKEN) if TG_TOKEN else None
chat_id = int(TG_CHAT) if TG_CHAT else None

DEMO: sledujeme 1 event (nahodné UUID). Potom pridáš reálne eventy.

WATCHED_EVENTS = ["00000000-0000-0000-0000-000000000001"]

def fetch_market_data(event_id: str) -> dict:
"""
TODO: Napoj reálne zdroje (SeatGeek/StubHub/...).
Teraz vraciame demo dáta, aby systém bežal.
"""
return {
"face_min": Decimal("59.0"),
"face_max": Decimal("129.0"),
"secondary_floor": Decimal("98.0"),
"listings_count": 143,
"tickets_remaining_pct": Decimal("62.5"),
"currency": "EUR",
"source": "demo"
}

def save_snapshot(event_id: str, data: dict) -> None:
q = text("""
INSERT INTO ticket_price_snapshots
(event_id, face_min, face_max, secondary_floor, listings_count, tickets_remaining_pct, currency, source)
VALUES
(:event_id, :face_min, :face_max, :secondary_floor, :listings_count, :tickets_remaining_pct, :currency, :source)
""")
with engine.begin() as conn:
conn.execute(q, {"event_id": event_id, **data})

def refresh_daily_view() -> None:
with engine.begin() as conn:
conn.execute(text("REFRESH MATERIALIZED VIEW ticket_prices_daily;"))

def get_daily_row(event_id: str, day=None):
if day is None:
day = dt.date.today()
q = text("""
SELECT * FROM ticket_prices_daily
WHERE event_id = :event_id AND day = :day
""")
with engine.begin() as conn:
row = conn.execute(q, {"event_id": event_id, "day": day}).mappings().first()
return dict(row) if row else None

def send_daily_report(event_id: str, daily: dict) -> None:
if not bot or not chat_id:
print("Telegram creds not configured; skipping send.")
return
msg = (
f"📊 Denný prehľad cien\n"
f"Event: {event_id}\n"
f"Deň: {daily['day']}\n"
f"Face min (min): {daily['face_min_day_min']} EUR\n"
f"Face max (max): {daily['face_max_day_max']} EUR\n"
f"Secondary floor (min/median/avg): "
f"{daily['sec_floor_day_min']}/{daily['sec_floor_day_median']}/{round(daily['sec_floor_day_avg'],2)} EUR\n"
f"Listings avg: {round(daily['listings_day_avg'],1)}\n"
f"Tickets remaining (min): {daily['tickets_remaining_day_min']} %"
)
bot.send_message(chat_id=chat_id, text=msg)

def maybe_alert_hot(event_id: str, snap: dict) -> None:
if not bot or not chat_id:
return
face = snap.get("face_min")
floor = snap.get("secondary_floor")
rem = snap.get("tickets_remaining_pct")
try:
if face and floor and rem is not None:
if floor >= face * Decimal("1.5") and rem < Decimal("30"):
bot.send_message(
chat_id=chat_id,
text=f"🔥 HOT signal\nEvent: {event_id}\nSecondary/Face: {floor}/{face}\nRemaining: {rem}%"
)
except Exception as e:
print("HOT check error:", e)

if name == "main":
# 1) Ulož snapshot pre každý sledovaný event
for ev in WATCHED_EVENTS:
snap = fetch_market_data(ev)
save_snapshot(ev, snap)
maybe_alert_hot(ev, snap)
@'
import os, datetime as dt
from decimal import Decimal
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from telegram import Bot

load_dotenv()
DB_URL = os.getenv("DB_URL")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TG_CHAT  = os.getenv("TELEGRAM_CHAT_ID")

if DB_URL is None:
    raise RuntimeError("DB_URL is not set. Configure .env or environment variable.")

engine = create_engine(DB_URL, pool_pre_ping=True)
bot = Bot(TG_TOKEN) if TG_TOKEN else None
chat_id = int(TG_CHAT) if TG_CHAT else None

# DEMO: sledujeme 1 event (nahodné UUID). Potom pridáš reálne eventy.
WATCHED_EVENTS = ["00000000-0000-0000-0000-000000000001"]

def fetch_market_data(event_id: str) -> dict:
    """
    TODO: Napoj reálne zdroje (SeatGeek/StubHub/...).
    Teraz vraciame demo dáta, aby systém bežal.
    """
    return {
        "face_min": Decimal("59.0"),
        "face_max": Decimal("129.0"),
        "secondary_floor": Decimal("98.0"),
        "listings_count": 143,
        "tickets_remaining_pct": Decimal("62.5"),
        "currency": "EUR",
        "source": "demo"
    }

def save_snapshot(event_id: str, data: dict) -> None:
    q = text("""
    INSERT INTO ticket_price_snapshots
      (event_id, face_min, face_max, secondary_floor, listings_count, tickets_remaining_pct, currency, source)
    VALUES
      (:event_id, :face_min, :face_max, :secondary_floor, :listings_count, :tickets_remaining_pct, :currency, :source)
    """)
    with engine.begin() as conn:
        conn.execute(q, {"event_id": event_id, **data})

def refresh_daily_view() -> None:
    with engine.begin() as conn:
        conn.execute(text("REFRESH MATERIALIZED VIEW ticket_prices_daily;"))

def get_daily_row(event_id: str, day=None):
    if day is None:
        day = dt.date.today()
    q = text("""
    SELECT * FROM ticket_prices_daily
    WHERE event_id = :event_id AND day = :day
    """)
    with engine.begin() as conn:
        row = conn.execute(q, {"event_id": event_id, "day": day}).mappings().first()
    return dict(row) if row else None

def send_daily_report(event_id: str, daily: dict) -> None:
    if not bot or not chat_id:
        print("Telegram creds not configured; skipping send.")
        return
    msg = (
        f"📊 Denný prehľad cien\n"
        f"Event: {event_id}\n"
        f"Deň: {daily['day']}\n"
        f"Face min (min): {daily['face_min_day_min']} EUR\n"
        f"Face max (max): {daily['face_max_day_max']} EUR\n"
        f"Secondary floor (min/median/avg): "
        f"{daily['sec_floor_day_min']}/{daily['sec_floor_day_median']}/{round(daily['sec_floor_day_avg'],2)} EUR\n"
        f"Listings avg: {round(daily['listings_day_avg'],1)}\n"
        f"Tickets remaining (min): {daily['tickets_remaining_day_min']} %"
    )
    bot.send_message(chat_id=chat_id, text=msg)

def maybe_alert_hot(event_id: str, snap: dict) -> None:
    if not bot or not chat_id:
        return
    face = snap.get("face_min")
    floor = snap.get("secondary_floor")
    rem = snap.get("tickets_remaining_pct")
    try:
        if face and floor and rem is not None:
            if floor >= face * Decimal("1.5") and rem < Decimal("30"):
                bot.send_message(
                    chat_id=chat_id,
                    text=f"🔥 HOT signal\nEvent: {event_id}\nSecondary/Face: {floor}/{face}\nRemaining: {rem}%"
                )
    except Exception as e:
        print("HOT check error:", e)

if __name__ == "__main__":
    # 1) Ulož snapshot pre každý sledovaný event
    for ev in WATCHED_EVENTS:
        snap = fetch_market_data(ev)
        save_snapshot(ev, snap)
        maybe_alert_hot(ev, snap)

    # 2) Refresh dennej tabuľky (spúšťaj ideálne večer alebo v dennom jobe)
    try:
        refresh_daily_view()
    except Exception as e:
        print("Refresh MV error:", e)

    # 3) Pošli dnešný report (ak existuje)
    for ev in WATCHED_EVENTS:
        daily = get_daily_row(ev)
        if daily:
            send_daily_report(ev, daily)
