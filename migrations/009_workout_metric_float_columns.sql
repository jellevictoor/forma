-- Change duration_seconds and moving_time_seconds from INTEGER to DOUBLE PRECISION.
-- These columns are used exclusively in float arithmetic (pace, effort, time-in-zone
-- calculations). Storing them as INTEGER caused integer/numeric promotion in PostgreSQL
-- division expressions, returning Decimal values that are not JSON-serializable.

ALTER TABLE workouts
    ALTER COLUMN duration_seconds    TYPE DOUBLE PRECISION USING duration_seconds::float,
    ALTER COLUMN moving_time_seconds TYPE DOUBLE PRECISION USING moving_time_seconds::float;
