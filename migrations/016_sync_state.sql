-- Add sync state tracking to athletes for progressive Strava sync
ALTER TABLE athletes
    ADD COLUMN IF NOT EXISTS sync_state TEXT NOT NULL DEFAULT 'never_synced',
    ADD COLUMN IF NOT EXISTS backfill_cursor TIMESTAMPTZ;

-- Existing athletes with workouts are already fully synced (detail was fetched)
UPDATE athletes SET sync_state = 'complete'
WHERE id IN (SELECT DISTINCT athlete_id FROM workouts);
