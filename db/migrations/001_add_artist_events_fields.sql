-- 001_add_artist_events_fields.sql

-- 1) Základná tabuľka events (ak ešte neexistuje)
CREATE TABLE IF NOT EXISTS events (
  id SERIAL PRIMARY KEY,
  event_name TEXT,
  event_date DATE,
  venue TEXT,
  city TEXT,
  country TEXT,
  created_at TIMESTAMP DEFAULT now()
);

-- 2) Interpreti + metriky (Spotify)
CREATE TABLE IF NOT EXISTS artists (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  spotify_id TEXT,
  popularity INT,
  followers BIGINT,
  updated_at TIMESTAMP DEFAULT now()
);

-- 3) Rozšírenie events o polia potrebné na flipping
ALTER TABLE events
  ADD COLUMN IF NOT EXISTS artist_id INT REFERENCES artists(id),
  ADD COLUMN IF NOT EXISTS buy_url TEXT,
  ADD COLUMN IF NOT EXISTS resale_url TEXT,
  ADD COLUMN IF NOT EXISTS venue_section TEXT,           -- JSON/text so sekciami
  ADD COLUMN IF NOT EXISTS lowest_price NUMERIC,
  ADD COLUMN IF NOT EXISTS lowest_resale_price NUMERIC,
  ADD COLUMN IF NOT EXISTS seats_total INT,
  ADD COLUMN IF NOT EXISTS seats_available INT,
  ADD COLUMN IF NOT EXISTS source_vendor TEXT;

-- 4) Indexy
CREATE INDEX IF NOT EXISTS idx_events_artist_date
  ON events(artist_id, event_date);
