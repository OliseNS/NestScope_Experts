-- Legacy reference: this schema matched the former Turso (libSQL) Nestperts auth database.
-- The project now uses local SQLite only (default path: data/user_auth.db).
--
-- Current schema (includes app_settings for root admin) lives in labeller/auth.py (init_auth_db).
-- Optional SQL reference: scripts/user_auth_schema.sql
--
-- One-time copy from Turso: install libsql-client, set TURSO_* in .env, then:
--   python scripts/migrate_auth_from_turso.py

-- Table: users (people who've signed in)
CREATE TABLE IF NOT EXISTS users (
    email TEXT PRIMARY KEY,
    name TEXT,
    picture TEXT,
    first_login TEXT DEFAULT (datetime('now')),
    last_login TEXT DEFAULT (datetime('now')),
    login_count INTEGER DEFAULT 1,
    role TEXT DEFAULT 'viewer',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Table: approved_emails (admin-managed whitelist)
CREATE TABLE IF NOT EXISTS approved_emails (
    email TEXT PRIMARY KEY,
    added_by TEXT DEFAULT 'SYSTEM',
    added_at TEXT DEFAULT (datetime('now')),
    notes TEXT
);

-- Table: admin_users (superusers who can manage approved emails)
CREATE TABLE IF NOT EXISTS admin_users (
    email TEXT PRIMARY KEY,
    added_at TEXT DEFAULT (datetime('now'))
);

-- Table: permissions (defines what each role can do)
CREATE TABLE IF NOT EXISTS permissions (
    role TEXT PRIMARY KEY,
    can_annotate INTEGER DEFAULT 0,
    can_edit_db INTEGER DEFAULT 0,
    can_manage_users INTEGER DEFAULT 0,
    description TEXT
);
