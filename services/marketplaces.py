import urllib.parse

# jednoduché mapovanie domén; pre neznáme krajiny použijeme .com
_STUBHUB_DOMAIN_BY_CC = {
    "DE": "stubhub.de",
    # ostatné budú na .com (PL, CZ, SK, AT, HU, ...):
}

def stubhub_search_url(artist_name: str, city: str | None, date_iso: str, country_code: str | None) -> str:
    """
    Vygeneruje StubHub vyhľadávanie: interpret + mesto + dátum (YYYY-MM-DD).
    Pr.: https://www.stubhub.com/find?q=The%20Offspring%20Cologne%202025-11-05
    """
    cc = (country_code or "").upper()
    domain = _STUBHUB_DOMAIN_BY_CC.get(cc, "stubhub.com")
    parts = [artist_name]
    if city:
        parts.append(city)
    parts.append(date_iso)  # yyyy-mm-dd
    q = urllib.parse.quote(" ".join(parts))
    return f"https://{domain}/find?q={q}"
