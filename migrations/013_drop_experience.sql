-- Remove experience_years and sports_background from the athlete profile blob.
-- These fields were unused and have no meaning for the coaching features.
-- Since all athlete fields except the promoted columns live in the JSON blob,
-- no column drop is needed — the fields simply disappear from new saves.
-- Backfill removes them from existing blobs.

UPDATE athletes
SET data = (data::jsonb - 'experience_years' - 'sports_background')::text;
