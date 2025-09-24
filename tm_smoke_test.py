from dotenv import load_dotenv
load_dotenv()

from providers.ticketmaster import fetch_events

events = fetch_events(performer_query="taylor swift", size=3)
print("Pocet eventov:", len(events))
for i, ev in enumerate(events, 1):
    print(i, ev["provider_event_id"], ev["face_min"], ev["face_max"], ev["currency"])
