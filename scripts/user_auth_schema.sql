-- Reference schema for Nestperts local auth SQLite (data/user_auth.db by default).
-- Created programmatically in labeller/auth.py (init_auth_db). This file is for
-- documentation and manual inspection only.

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Protected root: key = 'root_email', value = lower-case email (set by seed_root_admin.py)

CREATE TABLE IF NOT EXISTS approved_emails (
    email TEXT PRIMARY KEY,
    added_by TEXT,
    added_at TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS users (
    email TEXT PRIMARY KEY,
    name TEXT,
    picture TEXT,
    first_login TEXT,
    last_login TEXT,
    login_count INTEGER DEFAULT 1,
    role TEXT DEFAULT 'viewer'
);

CREATE TABLE IF NOT EXISTS admin_users (
    email TEXT PRIMARY KEY,
    added_at TEXT
);

CREATE TABLE IF NOT EXISTS permissions (
    role TEXT PRIMARY KEY,
    can_annotate INTEGER DEFAULT 0,
    can_edit_db INTEGER DEFAULT 0,
    can_manage_users INTEGER DEFAULT 0,
    description TEXT
);
