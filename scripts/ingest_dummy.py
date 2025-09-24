from datetime import datetime, timedelta
from providers.base import EventData
from services.save_event import upsert_artist, upsert_event

def main():
    # simulovaný event
    e = EventData(
        external_id="SIM-12345",
        source_vendor="dummy",
        artist_name="The Testers",
        event_name="The Testers Live",
        event_date=datetime.utcnow() + timedelta(days=21),
        venue="Hall A",
        city="Bratislava",
        country="SK",
        buy_url="https://example.com/buy/SIM-12345",
        resale_url="https://example.com/sell/SIM-12345",
        lowest_price=39.9,
        lowest_resale_price=55.0,
        sections={"A": 40, "B": 0, "C": 12},
        seats_total=5000,
        seats_available=1250,
    )

    artist_id = upsert_artist(e.artist_name)
    event_id = upsert_event(e, artist_id)
    print(f"Saved artist_id={artist_id}, event_id={event_id}")

if __name__ == "__main__":
    main()
