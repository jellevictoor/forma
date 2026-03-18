-- Initial schema: all tables from the original SQLite implementation.

CREATE TABLE IF NOT EXISTS athletes (
    id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS workouts (
    id TEXT PRIMARY KEY,
    athlete_id TEXT NOT NULL,
    strava_id BIGINT,
    start_time TEXT NOT NULL,
    workout_type TEXT,
    data TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_workouts_athlete_id ON workouts(athlete_id);
CREATE INDEX IF NOT EXISTS idx_workouts_strava_id ON workouts(strava_id);
CREATE INDEX IF NOT EXISTS idx_workouts_start_time ON workouts(start_time);
CREATE INDEX IF NOT EXISTS idx_workouts_workout_type ON workouts(workout_type);

CREATE TABLE IF NOT EXISTS weight_entries (
    id TEXT PRIMARY KEY,
    athlete_id TEXT NOT NULL,
    weight_kg REAL NOT NULL,
    recorded_at TEXT NOT NULL,
    notes TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_weight_entries_athlete_id ON weight_entries(athlete_id);
CREATE INDEX IF NOT EXISTS idx_weight_entries_recorded_at ON weight_entries(recorded_at);

CREATE TABLE IF NOT EXISTS activity_analysis_cache (
    workout_id TEXT PRIMARY KEY,
    generated_at TEXT NOT NULL,
    data TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS activity_chat (
    id SERIAL PRIMARY KEY,
    workout_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS insights_cache (
    athlete_id TEXT NOT NULL,
    year INTEGER NOT NULL,
    generated_at TEXT NOT NULL,
    data TEXT NOT NULL,
    PRIMARY KEY (athlete_id, year)
);

CREATE TABLE IF NOT EXISTS recap_cache (
    athlete_id TEXT PRIMARY KEY,
    generated_at TEXT NOT NULL,
    latest_activity_at TEXT,
    summary TEXT NOT NULL,
    highlight TEXT NOT NULL,
    form_note TEXT NOT NULL,
    focus TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS plan_cache (
    athlete_id TEXT PRIMARY KEY,
    generated_at TEXT NOT NULL,
    latest_activity_at TEXT,
    data TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS activity_streams (
    workout_id TEXT PRIMARY KEY,
    fetched_at TEXT NOT NULL,
    data TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS execution_sessions (
    session_id TEXT PRIMARY KEY,
    athlete_id TEXT NOT NULL,
    data TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_execution_sessions_athlete_id ON execution_sessions(athlete_id);
