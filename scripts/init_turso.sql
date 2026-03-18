-- Turso Cloud Database Initialization Script
-- For complete authentication and role-based access control

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

-- Insert default permissions
INSERT OR IGNORE INTO permissions (role, can_annotate, can_edit_db, can_manage_users, description)
VALUES 
    ('admin', 1, 1, 1, 'Full access to all features'),
    ('annotator', 1, 0, 0, 'Can annotate images'),
    ('viewer', 0, 0, 0, 'Read-only access');

-- Ensure base admin is always approved (Replace with your email)
INSERT OR IGNORE INTO approved_emails (email, notes)
VALUES ('olisemekanmarkwe@gmail.com', 'Protected base administrator');

-- Ensure base admin is always an admin (Replace with your email)
INSERT OR IGNORE INTO admin_users (email)
VALUES ('olisemekanmarkwe@gmail.com');
