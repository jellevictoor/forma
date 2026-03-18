-- Initial schema.

CREATE TABLE IF NOT EXISTS athletes (
    id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    role                    TEXT        NOT NULL DEFAULT 'user',
    is_blocked              BOOLEAN     NOT NULL DEFAULT FALSE,
    ai_enabled              BOOLEAN     NOT NULL DEFAULT TRUE,
    token_limit_30d         INTEGER,
    strava_athlete_id       BIGINT,
    strava_access_token     TEXT,
    strava_refresh_token    TEXT,
    strava_token_expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS workouts (
    id TEXT PRIMARY KEY,
    athlete_id TEXT NOT NULL,
    strava_id BIGINT,
    start_time TIMESTAMPTZ NOT NULL,
    workout_type TEXT,
    distance_meters     DOUBLE PRECISION,
    duration_seconds    DOUBLE PRECISION,
    moving_time_seconds DOUBLE PRECISION,
    average_heartrate   DOUBLE PRECISION,
    data TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_athletes_strava_athlete_id ON athletes(strava_athlete_id)
    WHERE strava_athlete_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_workouts_athlete_id ON workouts(athlete_id);
CREATE INDEX IF NOT EXISTS idx_workouts_strava_id ON workouts(strava_id);
CREATE INDEX IF NOT EXISTS idx_workouts_start_time ON workouts(start_time);
CREATE INDEX IF NOT EXISTS idx_workouts_workout_type ON workouts(workout_type);

CREATE TABLE IF NOT EXISTS weight_entries (
    id TEXT PRIMARY KEY,
    athlete_id TEXT NOT NULL,
    weight_kg REAL NOT NULL,
    recorded_at DATE NOT NULL,
    notes TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_weight_entries_athlete_id ON weight_entries(athlete_id);
CREATE INDEX IF NOT EXISTS idx_weight_entries_recorded_at ON weight_entries(recorded_at);

CREATE TABLE IF NOT EXISTS activity_analysis_cache (
    workout_id TEXT PRIMARY KEY,
    generated_at TIMESTAMPTZ NOT NULL,
    data TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS activity_chat (
    id SERIAL PRIMARY KEY,
    workout_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS insights_cache (
    athlete_id TEXT NOT NULL,
    year INTEGER NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL,
    data TEXT NOT NULL,
    PRIMARY KEY (athlete_id, year)
);

CREATE TABLE IF NOT EXISTS recap_cache (
    athlete_id TEXT PRIMARY KEY,
    generated_at TIMESTAMPTZ NOT NULL,
    latest_activity_at TIMESTAMPTZ,
    summary TEXT NOT NULL,
    highlight TEXT NOT NULL,
    form_note TEXT NOT NULL,
    focus TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS plan_cache (
    athlete_id TEXT PRIMARY KEY,
    generated_at TIMESTAMPTZ NOT NULL,
    latest_activity_at TIMESTAMPTZ,
    data TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS activity_streams (
    workout_id TEXT PRIMARY KEY,
    fetched_at TIMESTAMPTZ NOT NULL,
    data TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS execution_sessions (
    session_id TEXT PRIMARY KEY,
    athlete_id TEXT NOT NULL,
    data TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_execution_sessions_athlete_id ON execution_sessions(athlete_id);
