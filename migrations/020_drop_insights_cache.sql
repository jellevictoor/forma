DROP TABLE IF EXISTS insights_cache;
DELETE FROM system_prompts WHERE service = 'insights';
