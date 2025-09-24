# concert-flipper (MVP)

Sledovanie cien lístkov (časové rady) + denný prehľad v tabuľke + Telegram notifikácie.

## Rýchly štart
```bash
python -m venv .venv
. .venv/Scripts/Activate.ps1   # Windows
pip install -r requirements.txt

# DB v Dockeri (voliteľné)
docker compose up -d

# Inicializácia schémy
# nainštaluj psql alebo použi iný klient a vykonaj:
#   psql postgresql://app:app@localhost:5432/tickets -f schema.sql

# Konfigurácia
copy .env.example -> .env a doplň token/chat_id

# Test ingestu
python ingest.py
