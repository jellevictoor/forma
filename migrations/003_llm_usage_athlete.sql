-- Add athlete_id to llm_usage for per-user tracking and blocking.
ALTER TABLE llm_usage ADD COLUMN IF NOT EXISTS athlete_id TEXT;

CREATE INDEX IF NOT EXISTS idx_llm_usage_athlete ON llm_usage(athlete_id);
