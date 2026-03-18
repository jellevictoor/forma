-- Session tokens for cookie-based auth.
-- token is a 256-bit random value — no signing needed.

CREATE TABLE IF NOT EXISTS sessions (
    token       TEXT PRIMARY KEY,
    athlete_id  TEXT NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at  TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_athlete_id ON sessions(athlete_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at  ON sessions(expires_at);
