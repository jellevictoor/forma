-- Extract frequently-queried athlete fields from the JSON blob into proper columns.
-- Access-control fields (role, is_blocked, ai_enabled, token_limit_30d) and
-- Strava credentials are now first-class columns; they are removed from the blob.

ALTER TABLE athletes
    ADD COLUMN IF NOT EXISTS role                    TEXT      NOT NULL DEFAULT 'user',
    ADD COLUMN IF NOT EXISTS is_blocked              BOOLEAN   NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS ai_enabled              BOOLEAN   NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS token_limit_30d         INTEGER,
    ADD COLUMN IF NOT EXISTS strava_athlete_id       BIGINT,
    ADD COLUMN IF NOT EXISTS strava_access_token     TEXT,
    ADD COLUMN IF NOT EXISTS strava_refresh_token    TEXT,
    ADD COLUMN IF NOT EXISTS strava_token_expires_at TIMESTAMP;

-- Backfill from the existing JSON blob.
UPDATE athletes SET
    role                    = COALESCE(data::jsonb->>'role', 'user'),
    is_blocked              = COALESCE((data::jsonb->>'is_blocked')::boolean, FALSE),
    ai_enabled              = COALESCE((data::jsonb->>'ai_enabled')::boolean, TRUE),
    token_limit_30d         = (data::jsonb->>'token_limit_30d')::integer,
    strava_athlete_id       = (data::jsonb->>'strava_athlete_id')::bigint,
    strava_access_token     = data::jsonb->>'strava_access_token',
    strava_refresh_token    = data::jsonb->>'strava_refresh_token',
    strava_token_expires_at = (data::jsonb->>'strava_token_expires_at')::timestamp;

CREATE INDEX IF NOT EXISTS idx_athletes_strava_athlete_id ON athletes(strava_athlete_id)
    WHERE strava_athlete_id IS NOT NULL;
