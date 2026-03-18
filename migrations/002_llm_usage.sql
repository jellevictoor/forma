-- LLM API usage log — one row per Gemini call.
CREATE TABLE IF NOT EXISTS llm_usage (
    id         SERIAL PRIMARY KEY,
    service    TEXT NOT NULL,
    model      TEXT NOT NULL,
    input_tokens  INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_llm_usage_created ON llm_usage(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_llm_usage_service ON llm_usage(service);
