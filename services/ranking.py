import math
from typing import List, Dict, Any

def score_artist(popularity: int, followers: int) -> float:
    pop = popularity or 0
    fol = followers or 0
    return 0.7 * pop + 0.3 * (math.log10(fol + 1) * 10.0)

def sell_window(popularity: int, days_to_event: int) -> str:
    if (popularity or 0) >= 80:
        lo, hi = 3, 10
    elif (popularity or 0) >= 60:
        lo, hi = 7, 21
    else:
        lo, hi = 14, 35
    if lo <= days_to_event <= hi:
        return "PREDAŤ TERAZ"
    if days_to_event > hi:
        return f"ČAKAŤ (cieľ T–{hi})"
    return "POSLEDNÁ ŠANCA"

def _rank_desc(values: List[float]) -> Dict[float, float]:
    # 1 = top; normalizácia na 0..1 (1 = top)
    uniq = sorted(set(values), reverse=True)
    rank_map = {v: i + 1 for i, v in enumerate(uniq)}
    n = len(uniq) or 1
    return {v: (1.0 if n == 1 else 1.0 - (rank - 1) / (n - 1)) for v, rank in rank_map.items()}

def fallback_scores(rows: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Skóre bez Spotify:
      0.5 * rank(event_count_by_artist)
    + 0.3 * rank(country_count_by_artist)
    + 0.2 * rank(min_lowest_price)   (vyššia cena = vyššie skóre)
    """
    agg: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        a = r["artist_name"]
        agg.setdefault(a, {"events": 0, "countries": set(), "min_price": None})
        agg[a]["events"] += 1
        if r.get("country"):
            agg[a]["countries"].add(r["country"])
        lp = r.get("lowest_price")
        if lp is not None:
            agg[a]["min_price"] = lp if agg[a]["min_price"] is None else min(agg[a]["min_price"], lp)

    events_vec = [v["events"] for v in agg.values()]
    country_vec = [len(v["countries"]) for v in agg.values()]
    price_vec = [(v["min_price"] if v["min_price"] is not None else 0.0) for v in agg.values()]

    r_events = _rank_desc(events_vec)
    r_country = _rank_desc(country_vec)
    r_price  = _rank_desc(price_vec)

    scores: Dict[str, float] = {}
    for a, v in agg.items():
        s = (
            0.5 * r_events[v["events"]] +
            0.3 * r_country[len(v["countries"])] +
            0.2 * r_price[v["min_price"] if v["min_price"] is not None else 0.0]
        )
        scores[a] = s
    return scores

def top_percent(items: List[Dict[str, Any]], field: str, percent: float) -> List[Dict[str, Any]]:
    if not items:
        return []
    k = max(1, int(len(items) * percent))
    return sorted(items, key=lambda x: x.get(field) or 0, reverse=True)[:k]
