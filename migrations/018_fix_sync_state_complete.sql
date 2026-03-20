-- Migration 016 set sync_state='complete' for all athletes with any workouts,
-- but 'complete' means ALL history was imported. Reset to 'up_to_date' so the
-- backfill pass can discover older activities on next sync.
UPDATE athletes SET sync_state = 'up_to_date'
WHERE sync_state = 'complete';
