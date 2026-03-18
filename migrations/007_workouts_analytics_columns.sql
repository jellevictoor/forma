-- Extract commonly-aggregated workout metric fields from the JSON blob into proper columns.
-- These are the fields most frequently queried by the analytics layer.
-- The full workout payload remains in the data blob for entity reconstruction.

ALTER TABLE workouts
    ADD COLUMN IF NOT EXISTS distance_meters     DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS duration_seconds    INTEGER,
    ADD COLUMN IF NOT EXISTS moving_time_seconds INTEGER,
    ADD COLUMN IF NOT EXISTS average_heartrate   DOUBLE PRECISION;

-- Backfill from the existing JSON blob.
UPDATE workouts SET
    distance_meters     = (data::jsonb->>'distance_meters')::float,
    duration_seconds    = (data::jsonb->>'duration_seconds')::integer,
    moving_time_seconds = (data::jsonb->>'moving_time_seconds')::float,
    average_heartrate   = (data::jsonb->>'average_heartrate')::float;

CREATE INDEX IF NOT EXISTS idx_workouts_duration ON workouts(duration_seconds)
    WHERE duration_seconds IS NOT NULL;
