-- Convert all TEXT date/datetime columns to proper PostgreSQL types.
-- Existing ISO-format strings are cast in-place via the USING clause.

ALTER TABLE workouts
    ALTER COLUMN start_time TYPE TIMESTAMP USING start_time::timestamp;

ALTER TABLE weight_entries
    ALTER COLUMN recorded_at TYPE DATE USING recorded_at::date;

ALTER TABLE activity_analysis_cache
    ALTER COLUMN generated_at TYPE TIMESTAMP USING generated_at::timestamp;

ALTER TABLE activity_chat
    ALTER COLUMN created_at TYPE TIMESTAMP USING created_at::timestamp;

ALTER TABLE insights_cache
    ALTER COLUMN generated_at TYPE TIMESTAMP USING generated_at::timestamp;

ALTER TABLE recap_cache
    ALTER COLUMN generated_at   TYPE TIMESTAMP USING generated_at::timestamp,
    ALTER COLUMN latest_activity_at TYPE TIMESTAMP USING latest_activity_at::timestamp;

ALTER TABLE plan_cache
    ALTER COLUMN generated_at       TYPE TIMESTAMP USING generated_at::timestamp,
    ALTER COLUMN latest_activity_at TYPE TIMESTAMP USING latest_activity_at::timestamp;

ALTER TABLE activity_streams
    ALTER COLUMN fetched_at TYPE TIMESTAMP USING fetched_at::timestamp;
