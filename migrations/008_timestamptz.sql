-- Convert all TIMESTAMP (naive) columns to TIMESTAMPTZ.
-- All timestamps were stored as UTC, so the USING clause interprets them correctly.
-- After this migration asyncpg returns timezone-aware datetimes and accepts them on write.

ALTER TABLE athletes
    ALTER COLUMN strava_token_expires_at TYPE TIMESTAMPTZ
        USING strava_token_expires_at AT TIME ZONE 'UTC',
    ALTER COLUMN created_at TYPE TIMESTAMPTZ
        USING created_at AT TIME ZONE 'UTC',
    ALTER COLUMN updated_at TYPE TIMESTAMPTZ
        USING updated_at AT TIME ZONE 'UTC';

ALTER TABLE workouts
    ALTER COLUMN start_time  TYPE TIMESTAMPTZ USING start_time  AT TIME ZONE 'UTC',
    ALTER COLUMN created_at  TYPE TIMESTAMPTZ USING created_at  AT TIME ZONE 'UTC';

ALTER TABLE weight_entries
    ALTER COLUMN created_at  TYPE TIMESTAMPTZ USING created_at  AT TIME ZONE 'UTC';

ALTER TABLE activity_analysis_cache
    ALTER COLUMN generated_at TYPE TIMESTAMPTZ USING generated_at AT TIME ZONE 'UTC';

ALTER TABLE activity_chat
    ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC';

ALTER TABLE insights_cache
    ALTER COLUMN generated_at TYPE TIMESTAMPTZ USING generated_at AT TIME ZONE 'UTC';

ALTER TABLE recap_cache
    ALTER COLUMN generated_at       TYPE TIMESTAMPTZ USING generated_at       AT TIME ZONE 'UTC',
    ALTER COLUMN latest_activity_at TYPE TIMESTAMPTZ USING latest_activity_at AT TIME ZONE 'UTC';

ALTER TABLE plan_cache
    ALTER COLUMN generated_at       TYPE TIMESTAMPTZ USING generated_at       AT TIME ZONE 'UTC',
    ALTER COLUMN latest_activity_at TYPE TIMESTAMPTZ USING latest_activity_at AT TIME ZONE 'UTC';

ALTER TABLE activity_streams
    ALTER COLUMN fetched_at TYPE TIMESTAMPTZ USING fetched_at AT TIME ZONE 'UTC';

ALTER TABLE sessions
    ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
    ALTER COLUMN expires_at TYPE TIMESTAMPTZ USING expires_at AT TIME ZONE 'UTC';

ALTER TABLE llm_usage
    ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC';
