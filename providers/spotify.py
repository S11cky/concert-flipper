import os
from typing import Optional, Dict

def fetch_artist_metrics(name: str) -> Optional[Dict]:
    # No-Spotify mód: bez kľúčov nevraciame nič, kód ďalej to zvládne.
    cid = os.getenv("SPOTIFY_CLIENT_ID")
    secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    if not cid or not secret:
        return None
    # Ak niekedy doplníš kľúče, môžeš sem vrátiť pôvodnú implementáciu s requests.
    return None
