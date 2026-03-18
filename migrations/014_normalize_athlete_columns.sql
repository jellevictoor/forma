-- Normalize the athletes table: promote all scalar fields to proper columns,
-- keep complex arrays as individual JSON text columns, drop the data blob.

ALTER TABLE athletes
    ADD COLUMN name                   TEXT,
    ADD COLUMN date_of_birth          DATE,
    ADD COLUMN height_cm              DOUBLE PRECISION,
    ADD COLUMN weight_kg              DOUBLE PRECISION,
    ADD COLUMN max_hours_per_week     DOUBLE PRECISION,
    ADD COLUMN notes                  TEXT NOT NULL DEFAULT '',
    ADD COLUMN max_heartrate          INTEGER,
    ADD COLUMN aerobic_threshold_bpm  INTEGER,
    ADD COLUMN goals                  TEXT NOT NULL DEFAULT '[]',
    ADD COLUMN injuries               TEXT NOT NULL DEFAULT '[]',
    ADD COLUMN goal_history           TEXT NOT NULL DEFAULT '[]',
    ADD COLUMN schedule_template      TEXT NOT NULL DEFAULT '[]',
    ADD COLUMN equipment              TEXT NOT NULL DEFAULT '[]',
    ADD COLUMN preferred_workout_days TEXT NOT NULL DEFAULT '[]';

UPDATE athletes SET
    name                   = data::jsonb->>'name',
    date_of_birth          = (data::jsonb->>'date_of_birth')::date,
    height_cm              = (data::jsonb->>'height_cm')::double precision,
    weight_kg              = (data::jsonb->>'weight_kg')::double precision,
    max_hours_per_week     = (data::jsonb->>'max_hours_per_week')::double precision,
    notes                  = COALESCE(data::jsonb->>'notes', ''),
    max_heartrate          = (data::jsonb->>'max_heartrate')::integer,
    aerobic_threshold_bpm  = (data::jsonb->>'aerobic_threshold_bpm')::integer,
    goals                  = COALESCE(data::jsonb->>'goals', '[]'),
    injuries               = COALESCE(data::jsonb->>'injuries', '[]'),
    goal_history           = COALESCE(data::jsonb->>'goal_history', '[]'),
    schedule_template      = COALESCE(data::jsonb->>'schedule_template', '[]'),
    equipment              = COALESCE(data::jsonb->>'equipment', '[]'),
    preferred_workout_days = COALESCE(data::jsonb->>'preferred_workout_days', '[]');

ALTER TABLE athletes ALTER COLUMN name SET NOT NULL;

ALTER TABLE athletes DROP COLUMN data;
