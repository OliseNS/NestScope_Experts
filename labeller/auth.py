"""
Authentication module for Nestperts
Handles Google OAuth, user management, and access control
"""

import os
import sqlite3
from datetime import datetime
from functools import wraps
from pathlib import Path
from flask import session, redirect, url_for, request, jsonify
from authlib.integrations.flask_client import OAuth
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# DATABASE SETUP (local SQLite)
# ============================================================================

def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _default_auth_db_path() -> Path:
    return _repo_root() / "data" / "user_auth.db"


def get_auth_db_path() -> Path:
    """Resolved path to the Nestperts auth SQLite database."""
    raw = os.getenv("AUTH_DB_PATH")
    if raw:
        return Path(raw).expanduser().resolve()
    return _default_auth_db_path().resolve()


def _connect():
    path = get_auth_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def get_root_email():
    """Email stored as protected root admin (cannot delete / demote). None if unset."""
    try:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT value FROM app_settings WHERE key = 'root_email'"
            ).fetchone()
            return row[0] if row else None
        finally:
            conn.close()
    except Exception as e:
        logger.error("Failed to read root_email: %s", e)
        return None


def init_auth_db():
    """Initialize authentication database: schema, default permissions, optional root from env."""
    conn = _connect()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

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
        """)
        n = conn.execute("SELECT COUNT(*) FROM permissions").fetchone()[0]
        if n == 0:
            conn.executemany(
                """INSERT INTO permissions
                   (role, can_annotate, can_edit_db, can_manage_users, description)
                   VALUES (?, ?, ?, ?, ?)""",
                [
                    ("admin", 1, 1, 1, "Full access to all features"),
                    ("annotator", 1, 0, 0, "Can annotate images"),
                    ("viewer", 0, 0, 0, "Read-only access"),
                ],
            )

        env_root = (os.getenv("ROOT_ADMIN_EMAIL") or "").strip().lower()
        if env_root:
            has_root = conn.execute(
                "SELECT 1 FROM app_settings WHERE key = 'root_email'"
            ).fetchone()
            if not has_root:
                conn.execute(
                    "INSERT INTO app_settings (key, value) VALUES ('root_email', ?)",
                    (env_root,),
                )
                now = datetime.now().isoformat()
                conn.execute(
                    "INSERT OR IGNORE INTO approved_emails (email, added_by, added_at, notes) VALUES (?, ?, ?, ?)",
                    (env_root, "ENV", now, "ROOT_ADMIN_EMAIL in .env"),
                )
                conn.execute(
                    "INSERT OR IGNORE INTO admin_users (email, added_at) VALUES (?, ?)",
                    (env_root, now),
                )

        conn.commit()
        logger.info("Authentication database ready at %s", get_auth_db_path())
    except Exception as e:
        logger.error("Failed to initialize auth database: %s", e)
        raise
    finally:
        conn.close()


def seed_root_admin(email: str, *, force: bool = False) -> None:
    """
    Create auth DB if needed and set the protected root admin (approved + admin + app_settings).
    Idempotent if the same email is already root.
    """
    email = (email or "").strip().lower()
    if not email or "@" not in email:
        raise ValueError("A valid email address is required")

    init_auth_db()
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT value FROM app_settings WHERE key = 'root_email'"
        ).fetchone()
        existing = row[0] if row else None
        if existing and existing.lower() != email:
            if not force:
                raise ValueError(
                    f"Root is already set to {existing!r}; pass force=True to replace"
                )
        conn.execute(
            "INSERT OR REPLACE INTO app_settings (key, value) VALUES ('root_email', ?)",
            (email,),
        )
        now = datetime.now().isoformat()
        conn.execute(
            """INSERT OR IGNORE INTO approved_emails (email, added_by, added_at, notes)
               VALUES (?, ?, ?, ?)""",
            (email, "seed_root_admin", now, "Initial root administrator"),
        )
        conn.execute(
            "INSERT OR IGNORE INTO admin_users (email, added_at) VALUES (?, ?)",
            (email, now),
        )
        conn.commit()
        logger.info("Root admin seeded: %s", email)
    finally:
        conn.close()


# ============================================================================
# OAUTH CONFIGURATION
# ============================================================================

def setup_oauth(app):
    """
    Configure Google OAuth 2.0

    How OAuth works:
    1. User clicks "Sign in with Google"
    2. We redirect them to Google's login page
    3. User logs in and approves our app
    4. Google redirects back to us with an authorization code
    5. We exchange the code for user info (email, name, picture)
    6. We check if email is approved and create session
    """
    oauth = OAuth(app)

    google = oauth.register(
        name='google',
        client_id=os.getenv('GOOGLE_CLIENT_ID'),
        client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )

    return oauth, google

# ============================================================================
# USER MANAGEMENT
# ============================================================================

def is_email_approved(email):
    """Check if email is in the approved list."""
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT email FROM approved_emails WHERE email = ?", (email,)
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def is_admin(email):
    """Check if user is an admin."""
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT email FROM admin_users WHERE email = ?", (email,)
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def add_approved_email(email, added_by, notes=''):
    """Add email to approved list."""
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT OR IGNORE INTO approved_emails (email, added_by, added_at, notes)
            VALUES (?, ?, ?, ?)
            """,
            (email, added_by, datetime.now().isoformat(), notes),
        )
        conn.commit()
        logger.info("Email %s added to approved list", email)
        return True
    except Exception as e:
        logger.error("Failed to add approved email: %s", e)
        return False
    finally:
        conn.close()


def remove_approved_email(email):
    """Remove email from approved list."""
    if is_base_admin(email):
        raise ValueError(f"Cannot remove root admin from approved list: {email}")

    conn = _connect()
    try:
        conn.execute("DELETE FROM approved_emails WHERE email = ?", (email,))
        conn.commit()
        logger.info("Email %s removed from approved list", email)
    except Exception as e:
        logger.error("Failed to remove approved email: %s", e)
        raise
    finally:
        conn.close()


def get_approved_emails():
    """Get all approved emails."""
    conn = _connect()
    try:
        cur = conn.execute(
            "SELECT email, added_by, added_at, notes FROM approved_emails ORDER BY added_at DESC"
        )
        return [
            {"email": r[0], "added_by": r[1], "added_at": r[2], "notes": r[3]}
            for r in cur.fetchall()
        ]
    except Exception as e:
        logger.error("Failed to get approved emails: %s", e)
        raise
    finally:
        conn.close()


def create_or_update_user(email, name, picture):
    """Create new user or update existing user's login info."""
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT email, login_count, role FROM users WHERE email = ?", (email,)
        ).fetchone()

        if row:
            conn.execute(
                """
                UPDATE users
                SET name = ?, picture = ?, last_login = ?, login_count = login_count + 1
                WHERE email = ?
                """,
                (name, picture, datetime.now().isoformat(), email),
            )
        else:
            is_admin_row = conn.execute(
                "SELECT email FROM admin_users WHERE email = ?", (email,)
            ).fetchone()
            default_role = "admin" if is_admin_row else "viewer"
            conn.execute(
                """
                INSERT INTO users (email, name, picture, first_login, last_login, login_count, role)
                VALUES (?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    email,
                    name,
                    picture,
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                    default_role,
                ),
            )
        conn.commit()
        logger.info("User %s created/updated", email)
    except Exception as e:
        logger.error("User update failed: %s", e)
        raise
    finally:
        conn.close()


def get_all_users():
    """Get all registered users."""
    conn = _connect()
    try:
        cur = conn.execute(
            """
            SELECT email, name, picture, first_login, last_login, login_count
            FROM users
            ORDER BY last_login DESC
            """
        )
        return [
            {
                "email": r[0],
                "name": r[1],
                "picture": r[2],
                "first_login": r[3],
                "last_login": r[4],
                "login_count": r[5],
            }
            for r in cur.fetchall()
        ]
    except Exception as e:
        logger.error("Failed to get users: %s", e)
        raise
    finally:
        conn.close()


def add_admin(email):
    """Add user to admin list."""
    conn = _connect()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO admin_users (email, added_at) VALUES (?, ?)",
            (email, datetime.now().isoformat()),
        )
        conn.commit()
        logger.info("User %s added as admin", email)
        return True
    except Exception as e:
        logger.error("Failed to add admin: %s", e)
        return False
    finally:
        conn.close()

# ============================================================================
# DECORATORS (Route Protection)
# ============================================================================

def login_required(f):
    """
    Decorator to protect routes - requires user to be logged in

    Usage:
        @app.route('/secure-page')
        @login_required
        def secure_page():
            return "Only logged in users see this"

    How it works:
    - Checks if 'user' exists in session (session is like a secure cookie)
    - If not logged in, redirects to login page
    - If logged in, allows the function to run
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """
    Decorator to protect admin-only routes

    Usage:
        @app.route('/admin-panel')
        @admin_required
        def admin_panel():
            return "Only admins see this"
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login', next=request.url))

        user_email = session['user']['email']
        if session['user'].get('is_admin'):
            return f(*args, **kwargs)
        if is_admin(user_email):
            session['user']['is_admin'] = True
            session.modified = True
            return f(*args, **kwargs)

        return jsonify({'error': 'Admin access required'}), 403
    return decorated_function

def api_login_required(f):
    """
    Decorator for API endpoints - returns JSON error instead of redirect

    Usage:
        @app.route('/api/data')
        @api_login_required
        def get_data():
            return jsonify({'data': 'sensitive'})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

# ============================================================================
# ROLE-BASED ACCESS CONTROL (RBAC)
# ============================================================================

def get_user_role(email):
    """Get user's role from database."""
    conn = _connect()
    try:
        row = conn.execute("SELECT role FROM users WHERE email = ?", (email,)).fetchone()
        return row[0] if row else "viewer"
    except Exception as e:
        logger.error("Failed to get user role: %s", e)
        return "viewer"
    finally:
        conn.close()


def get_user_permissions(email):
    """Get user's permissions based on their role."""
    role = get_user_role(email)
    conn = _connect()
    try:
        row = conn.execute(
            """
            SELECT can_annotate, can_edit_db, can_manage_users
            FROM permissions
            WHERE role = ?
            """,
            (role,),
        ).fetchone()
        if row:
            return {
                "role": role,
                "can_annotate": bool(row[0]),
                "can_edit_db": bool(row[1]),
                "can_manage_users": bool(row[2]),
            }
        return {
            "role": "viewer",
            "can_annotate": False,
            "can_edit_db": False,
            "can_manage_users": False,
        }
    except Exception as e:
        logger.error("Failed to get user permissions: %s", e)
        return {
            "role": "viewer",
            "can_annotate": False,
            "can_edit_db": False,
            "can_manage_users": False,
        }
    finally:
        conn.close()


def is_base_admin(email):
    """True if email is the protected root admin (set via seed script or ROOT_ADMIN_EMAIL)."""
    root = get_root_email()
    if not root or not email:
        return False
    return email.strip().lower() == root.strip().lower()


def update_user_role(email, new_role):
    """Update a user's role."""
    valid_roles = ['admin', 'annotator', 'viewer']
    if new_role not in valid_roles:
        return False

    if is_base_admin(email) and new_role != 'admin':
        raise ValueError(f"Cannot change role of root admin: {email}")

    conn = _connect()
    try:
        conn.execute("UPDATE users SET role = ? WHERE email = ?", (new_role, email))
        if new_role == 'admin':
            conn.execute(
                "INSERT OR IGNORE INTO admin_users (email, added_at) VALUES (?, ?)",
                (email, datetime.now().isoformat()),
            )
        else:
            conn.execute("DELETE FROM admin_users WHERE email = ?", (email,))
        conn.commit()
        logger.info("User %s role updated to %s", email, new_role)
        return True
    except Exception as e:
        logger.error("Failed to update user role: %s", e)
        return False
    finally:
        conn.close()


def delete_user(email):
    """Delete a user completely from the system."""
    if is_base_admin(email):
        raise ValueError(f"Cannot delete root admin: {email}")

    conn = _connect()
    try:
        conn.execute("DELETE FROM users WHERE email = ?", (email,))
        conn.execute("DELETE FROM admin_users WHERE email = ?", (email,))
        conn.execute("DELETE FROM approved_emails WHERE email = ?", (email,))
        conn.commit()
        logger.info("User %s deleted", email)
        return True
    except Exception as e:
        logger.error("Failed to delete user: %s", e)
        return False
    finally:
        conn.close()


def get_all_users_with_roles():
    """Get all registered users with their roles and permissions (batched queries)."""
    conn = _connect()
    try:
        perm_by_role = {}
        for prow in conn.execute(
            "SELECT role, can_annotate, can_edit_db, can_manage_users FROM permissions"
        ).fetchall():
            perm_by_role[prow[0]] = {
                "can_annotate": bool(prow[1]),
                "can_edit_db": bool(prow[2]),
                "can_manage_users": bool(prow[3]),
            }
        default_perm = {
            "can_annotate": False,
            "can_edit_db": False,
            "can_manage_users": False,
        }

        root_row = conn.execute(
            "SELECT value FROM app_settings WHERE key = 'root_email'"
        ).fetchone()
        root = root_row[0] if root_row else None
        root_l = root.strip().lower() if root else None

        users = []
        for row in conn.execute(
            """
            SELECT u.email, u.name, u.picture, u.first_login, u.last_login,
                   u.login_count, u.role
            FROM users u
            ORDER BY u.last_login DESC
            """
        ).fetchall():
            email = row[0]
            role = row[6] or "viewer"
            p = perm_by_role.get(role, default_perm)
            is_root = bool(
                root_l and email and email.strip().lower() == root_l
            )
            users.append({
                "email": email,
                "name": row[1],
                "picture": row[2],
                "first_login": row[3],
                "last_login": row[4],
                "login_count": row[5],
                "role": role,
                "is_base_admin": is_root,
                "can_annotate": p["can_annotate"],
                "can_edit_db": p["can_edit_db"],
                "can_manage_users": p["can_manage_users"],
            })
        return users
    except Exception as e:
        logger.error("Failed to get users with roles: %s", e)
        raise
    finally:
        conn.close()


def get_login_session_payload(email):
    """
    Load role, permission flags, and admin status in one query.
    Call after create_or_update_user so the users row exists.
    """
    conn = _connect()
    try:
        row = conn.execute(
            """
            SELECT u.role, p.can_annotate, p.can_edit_db, p.can_manage_users,
                   EXISTS(SELECT 1 FROM admin_users a WHERE a.email = u.email)
            FROM users u
            LEFT JOIN permissions p ON p.role = COALESCE(u.role, 'viewer')
            WHERE u.email = ?
            """,
            (email,),
        ).fetchone()
        if not row:
            return None
        role = row[0] or "viewer"
        perms = {
            "role": role,
            "can_annotate": bool(row[1]) if row[1] is not None else False,
            "can_edit_db": bool(row[2]) if row[2] is not None else False,
            "can_manage_users": bool(row[3]) if row[3] is not None else False,
        }
        is_adm = bool(row[4])
        return perms, is_adm
    except Exception as e:
        logger.error("Failed to load login session payload: %s", e)
        raise
    finally:
        conn.close()

# ============================================================================
# PERMISSION DECORATORS
# ============================================================================

def annotator_required(f):
    """
    Decorator for routes that require annotator permission or higher

    Usage:
        @app.route('/annotate')
        @annotator_required
        def annotate_page():
            return "Annotators and admins can access"
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login', next=request.url))

        user_email = session['user']['email']
        perms = get_user_permissions(user_email)

        if not perms['can_annotate']:
            return jsonify({'error': 'Annotator permission required'}), 403

        return f(*args, **kwargs)
    return decorated_function

def db_editor_required(f):
    """
    Decorator for routes that require database edit permission

    Usage:
        @app.route('/db/edit')
        @db_editor_required
        def edit_db():
            return "Only users with DB edit permission"
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login', next=request.url))

        user_email = session['user']['email']
        perms = get_user_permissions(user_email)

        if not perms['can_edit_db']:
            return jsonify({'error': 'Database edit permission required'}), 403

        return f(*args, **kwargs)
    return decorated_function

def api_annotator_required(f):
    """API version of annotator_required (returns JSON error)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return jsonify({'error': 'Authentication required'}), 401

        user_email = session['user']['email']
        perms = get_user_permissions(user_email)

        if not perms['can_annotate']:
            return jsonify({'error': 'Annotator permission required'}), 403

        return f(*args, **kwargs)
    return decorated_function

def api_db_editor_required(f):
    """API version of db_editor_required (returns JSON error)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return jsonify({'error': 'Authentication required'}), 401

        user_email = session['user']['email']
        perms = get_user_permissions(user_email)

        if not perms['can_edit_db']:
            return jsonify({'error': 'Database edit permission required'}), 403

        return f(*args, **kwargs)
    return decorated_function

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_current_user():
    """Get the currently logged-in user from session"""
    return session.get('user')

def is_logged_in():
    """Check if user is logged in"""
    return 'user' in session
