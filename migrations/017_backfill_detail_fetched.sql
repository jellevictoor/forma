-- Mark existing workouts that have strava_raw as detail_fetched=true in the JSON blob.
-- These were synced with the old flow that called the detail endpoint.
UPDATE workouts
SET data = jsonb_set(data::jsonb, '{detail_fetched}', 'true')::text
WHERE data::jsonb -> 'strava_raw' IS NOT NULL
  AND (data::jsonb ->> 'detail_fetched' IS NULL OR data::jsonb ->> 'detail_fetched' = 'false');
