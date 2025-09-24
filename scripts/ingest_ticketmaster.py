from providers.ticketmaster import fetch_events_tm
from services.save_event import upsert_artist, upsert_event

# Jednoduchý ingest: SK + okolie (prípadne uprav country kódy)
COUNTRIES = ["SK", "CZ", "AT", "HU", "PL", "DE"]

def main():
    total = 0
    for cc in COUNTRIES:
        events = fetch_events_tm(countryCode=cc, keyword=None, size=100, pages=2)
        for e in events:
            artist_id = upsert_artist(e.artist_name)
            upsert_event(e, artist_id)
            total += 1
    print(f"✅ Ingest done. Upserted {total} events from Ticketmaster.")

if __name__ == "__main__":
    main()
