-- Add foreign key constraints to enforce referential integrity across all tables.
-- Purge orphaned rows first so the constraints can be applied cleanly.

DELETE FROM recap_cache          WHERE athlete_id NOT IN (SELECT id FROM athletes);
DELETE FROM insights_cache       WHERE athlete_id NOT IN (SELECT id FROM athletes);
DELETE FROM plan_cache           WHERE athlete_id NOT IN (SELECT id FROM athletes);
DELETE FROM execution_sessions   WHERE athlete_id NOT IN (SELECT id FROM athletes);
DELETE FROM weight_entries       WHERE athlete_id NOT IN (SELECT id FROM athletes);
DELETE FROM workouts             WHERE athlete_id NOT IN (SELECT id FROM athletes);
DELETE FROM activity_analysis_cache WHERE workout_id NOT IN (SELECT id FROM workouts);
DELETE FROM activity_chat           WHERE workout_id NOT IN (SELECT id FROM workouts);
DELETE FROM activity_streams        WHERE workout_id NOT IN (SELECT id FROM workouts);


ALTER TABLE workouts
    ADD CONSTRAINT fk_workouts_athlete
    FOREIGN KEY (athlete_id) REFERENCES athletes(id) ON DELETE CASCADE;

ALTER TABLE weight_entries
    ADD CONSTRAINT fk_weight_entries_athlete
    FOREIGN KEY (athlete_id) REFERENCES athletes(id) ON DELETE CASCADE;

ALTER TABLE execution_sessions
    ADD CONSTRAINT fk_execution_sessions_athlete
    FOREIGN KEY (athlete_id) REFERENCES athletes(id) ON DELETE CASCADE;

ALTER TABLE insights_cache
    ADD CONSTRAINT fk_insights_cache_athlete
    FOREIGN KEY (athlete_id) REFERENCES athletes(id) ON DELETE CASCADE;

ALTER TABLE recap_cache
    ADD CONSTRAINT fk_recap_cache_athlete
    FOREIGN KEY (athlete_id) REFERENCES athletes(id) ON DELETE CASCADE;

ALTER TABLE plan_cache
    ADD CONSTRAINT fk_plan_cache_athlete
    FOREIGN KEY (athlete_id) REFERENCES athletes(id) ON DELETE CASCADE;

ALTER TABLE activity_analysis_cache
    ADD CONSTRAINT fk_activity_analysis_cache_workout
    FOREIGN KEY (workout_id) REFERENCES workouts(id) ON DELETE CASCADE;

ALTER TABLE activity_chat
    ADD CONSTRAINT fk_activity_chat_workout
    FOREIGN KEY (workout_id) REFERENCES workouts(id) ON DELETE CASCADE;

ALTER TABLE activity_streams
    ADD CONSTRAINT fk_activity_streams_workout
    FOREIGN KEY (workout_id) REFERENCES workouts(id) ON DELETE CASCADE;

ALTER TABLE llm_usage
    ADD CONSTRAINT fk_llm_usage_athlete
    FOREIGN KEY (athlete_id) REFERENCES athletes(id) ON DELETE SET NULL;
