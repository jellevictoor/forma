CREATE TABLE IF NOT EXISTS system_prompts (
    service    TEXT PRIMARY KEY,
    label      TEXT NOT NULL,
    text       TEXT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
