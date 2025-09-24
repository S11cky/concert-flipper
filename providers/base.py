from dataclasses import dataclass
from typing import Optional, Dict, List, Protocol
from datetime import datetime

@dataclass
class EventData:
    external_id: str              # ID z externého zdroja (napr. Ticketmaster event id)
    source_vendor: str            # "ticketmaster", "seatgeek", ...
    artist_name: str
    event_name: str
    event_date: datetime          # ISO datetime v UTC alebo local (budeme ukladať len dátum)
    venue: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    buy_url: Optional[str] = None
    resale_url: Optional[str] = None
    lowest_price: Optional[float] = None           # primárny predaj
    lowest_resale_price: Optional[float] = None    # sekundárny trh
    sections: Optional[Dict[str, int]] = None      # {"A": 40, "B": 0, ...}
    seats_total: Optional[int] = None
    seats_available: Optional[int] = None

class Provider(Protocol):
    def fetch_events(self) -> List[EventData]:
        """Vráť zoznam EventData pre nové/aktualizované eventy."""
        ...
