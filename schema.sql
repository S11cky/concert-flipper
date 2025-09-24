CREATE TABLE IF NOT EXISTS ticket_price_snapshots (
  id BIGSERIAL PRIMARY KEY,
  event_id UUID NOT NULL,
  captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  face_min NUMERIC,
  face_max NUMERIC,
  secondary_floor NUMERIC,
  listings_count INT,
  tickets_remaining_pct NUMERIC,
  currency TEXT NOT NULL DEFAULT 'EUR',
  source TEXT NOT NULL
);

DROP MATERIALIZED VIEW IF EXISTS ticket_prices_daily;
CREATE MATERIALIZED VIEW ticket_prices_daily AS
SELECT
  event_id,
  date_trunc('day', captured_at)::date AS day,
  MIN(face_min)  AS face_min_day_min,
  MAX(face_max)  AS face_max_day_max,
  MIN(secondary_floor) AS sec_floor_day_min,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY secondary_floor) AS sec_floor_day_median,
  AVG(secondary_floor) AS sec_floor_day_avg,
  AVG(listings_count)  AS listings_day_avg,
  MIN(tickets_remaining_pct) AS tickets_remaining_day_min
FROM ticket_price_snapshots
GROUP BY event_id, date_trunc('day', captured_at);
