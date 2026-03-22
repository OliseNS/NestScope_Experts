#!/usr/bin/env python3
"""
One-time migration: copy Nestperts auth data from Turso (libSQL) into the local SQLite auth DB.

After this project switched to local SQLite, existing teams can move approved users,
admins, and roles off Turso without manual SQL exports.

Prerequisites:
    pip install libsql-client

Environment (.env):
    TURSO_DATABASE_URL
    TURSO_AUTH_TOKEN
    AUTH_DB_PATH   (optional; default matches labeller: data/user_auth.db)

Usage (repository root):
    python scripts/migrate_auth_from_turso.py

The local database is initialized first (schema + default permissions). Rows from
Turso are merged with INSERT OR REPLACE / OR IGNORE as appropriate.

Note: The protected root email (app_settings.root_email) is not on old Turso schemas.
Run `python seed_root_admin.py your@email.com` after migration if you need a locked root.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    try:
        import libsql_client
    except ImportError:
        print("Install libsql-client for this one-time migration: pip install libsql-client", file=sys.stderr)
        sys.exit(1)

    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")

    url = os.getenv("TURSO_DATABASE_URL")
    token = os.getenv("TURSO_AUTH_TOKEN")
    if not url or not token:
        print("Set TURSO_DATABASE_URL and TURSO_AUTH_TOKEN in .env", file=sys.stderr)
        sys.exit(1)

    import sqlite3

    from labeller.auth import get_auth_db_path, init_auth_db

    init_auth_db()
    local_path = str(get_auth_db_path())

    client = libsql_client.create_client_sync(url=url, auth_token=token)
    try:
        approved = client.execute(
            "SELECT email, added_by, added_at, notes FROM approved_emails"
        ).rows
        users = client.execute(
            """
            SELECT email, name, picture, first_login, last_login, login_count, role
            FROM users
            """
        ).rows
        admins = client.execute("SELECT email, added_at FROM admin_users").rows
        perms = client.execute(
            """
            SELECT role, can_annotate, can_edit_db, can_manage_users, description
            FROM permissions
            """
        ).rows
        try:
            settings = client.execute(
                "SELECT key, value FROM app_settings"
            ).rows
        except Exception:
            settings = []
    finally:
        client.close()

    conn = sqlite3.connect(local_path, timeout=60.0)
    try:
        conn.executemany(
            """
            INSERT OR REPLACE INTO approved_emails (email, added_by, added_at, notes)
            VALUES (?, ?, ?, ?)
            """,
            approved,
        )
        conn.executemany(
            """
            INSERT OR REPLACE INTO users
            (email, name, picture, first_login, last_login, login_count, role)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            users,
        )
        conn.executemany(
            "INSERT OR REPLACE INTO admin_users (email, added_at) VALUES (?, ?)",
            admins,
        )
        conn.executemany(
            """
            INSERT OR REPLACE INTO permissions
            (role, can_annotate, can_edit_db, can_manage_users, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            perms,
        )
        if settings:
            conn.executemany(
                "INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)",
                settings,
            )
        conn.commit()
    finally:
        conn.close()

    print(f"Migrated auth data into {local_path}")
    print("If you have no app_settings.root_email yet, run: python seed_root_admin.py you@example.com")


if __name__ == "__main__":
    main()
