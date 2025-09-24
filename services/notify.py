import os
import requests
from dotenv import load_dotenv

load_dotenv()

API = "https://api.telegram.org"

def _post(token: str, payload: dict):
    url = f"{API}/bot{token}/sendMessage"
    r = requests.post(url, json=payload, timeout=20)
    r.raise_for_status()
    return r.json()

def _split_chunks(text: str, limit: int = 3500):
    # delíme po riadkoch, aby sa nelámali uprostred linkov
    lines = text.splitlines(keepends=True)
    chunks, current = [], ""
    for ln in lines:
        if len(current) + len(ln) > limit and current:
            chunks.append(current)
            current = ln
        else:
            current += ln
    if current:
        chunks.append(current)
    return chunks

def send_telegram(text: str, parse_mode: str | None = "Markdown"):
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    chat_id = (os.getenv("TELEGRAM_CHAT_ID") or "").strip()
    if not token or not chat_id:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID")

    chunks = _split_chunks(text, 3500)
    for part in chunks:
        payload = {"chat_id": chat_id, "text": part}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        try:
            _post(token, payload)
        except requests.HTTPError as e:
            # Ak je problém s Markdownom (400), skúsime znova bez formátovania
            if e.response is not None and e.response.status_code == 400 and parse_mode is not None:
                _post(token, {"chat_id": chat_id, "text": part})
            else:
                raise

# zachováme aj pôvodnú signatúru pre existujúce importy
def send_telegram_markdown(text: str):
    return send_telegram(text, parse_mode="Markdown")
