CREATE TABLE IF NOT EXISTS feedback (
    id SERIAL PRIMARY KEY,
    athlete_id TEXT,
    page TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_feedback_created ON feedback(created_at DESC);
