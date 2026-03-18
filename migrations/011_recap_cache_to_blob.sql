-- Reshape recap_cache to use a single data blob, consistent with all other cache tables.
-- Merges summary, highlight, form_note, focus into a JSON blob in the data column.

ALTER TABLE recap_cache
    ADD COLUMN data TEXT;

UPDATE recap_cache SET data = json_build_object(
    'summary',    summary,
    'highlight',  highlight,
    'form_note',  form_note,
    'focus',      focus::json
)::text;

ALTER TABLE recap_cache
    ALTER COLUMN data SET NOT NULL;

ALTER TABLE recap_cache
    DROP COLUMN summary,
    DROP COLUMN highlight,
    DROP COLUMN form_note,
    DROP COLUMN focus;
