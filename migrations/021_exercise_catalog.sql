CREATE TABLE IF NOT EXISTS exercise_catalog (
    id SERIAL PRIMARY KEY,
    athlete_id TEXT NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    plan_date DATE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_exercise_catalog_athlete ON exercise_catalog(athlete_id);
CREATE INDEX IF NOT EXISTS idx_exercise_catalog_name ON exercise_catalog(name);
CREATE INDEX IF NOT EXISTS idx_exercise_catalog_created ON exercise_catalog(created_at DESC);
