-- 002_add_external_id.sql

ALTER TABLE events
  ADD COLUMN IF NOT EXISTS external_id TEXT;

-- Unikátne pravidlo: jeden vendor + jedno external_id = 1 event
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_indexes
    WHERE schemaname = 'public'
      AND indexname = 'uniq_vendor_external'
  ) THEN
    EXECUTE 'CREATE UNIQUE INDEX uniq_vendor_external ON events(source_vendor, external_id)';
  END IF;
END$$;
