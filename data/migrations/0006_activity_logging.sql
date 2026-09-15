-- Migration 0006: Activity and copy status logging
CREATE TABLE IF NOT EXISTS book_copy_status_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    copy_id     INTEGER NOT NULL REFERENCES book_copies(copy_id),
    old_status  TEXT NOT NULL,
    new_status  TEXT NOT NULL,
    reason      TEXT,
    changed_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS activity_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    logged_at   TEXT NOT NULL,
    actor       TEXT,
    action      TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id   TEXT NOT NULL,
    detail      TEXT
);

CREATE INDEX IF NOT EXISTS idx_activity_log_entity ON activity_log(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_activity_log_time ON activity_log(logged_at);

CREATE TABLE IF NOT EXISTS sync_state (
    key         TEXT PRIMARY KEY,
    value       TEXT,
    updated_at  TEXT
);
