"""
Authentication module for Nestperts
Handles Google OAuth, user management, and access control
"""

import os
import json
import sqlite3
from datetime import datetime
from functools import wraps
from flask import session, redirect, url_for, request, jsonify
from authlib.integrations.flask_client import OAuth

# ============================================================================
# DATABASE SETUP
# ============================================================================

# Store users.db in the data/ folder alongside bird_data_complete.db
AUTH_DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'users.db')

# Base admin that cannot be removed or demoted
BASE_ADMIN_EMAIL = 'olisemekanmarkwe@gmail.com'

def init_auth_db():
    """Initialize authentication database with users and approved emails"""
    conn = sqlite3.connect(AUTH_DB)
    cursor = conn.cursor()

    # Table: approved_emails (admin-managed whitelist)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS approved_emails (
            email TEXT PRIMARY KEY,
            added_by TEXT,
            added_at TEXT,
            notes TEXT
        )
    ''')

    # Table: users (people who've signed in)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            name TEXT,
            picture TEXT,
            first_login TEXT,
            last_login TEXT,
            login_count INTEGER DEFAULT 1,
            role TEXT DEFAULT 'viewer'
        )
    ''')

    # Table: admin_users (superusers who can manage approved emails)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_users (
            email TEXT PRIMARY KEY,
            added_at TEXT
        )
    ''')

    # Table: permissions (defines what each role can do)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS permissions (
            role TEXT PRIMARY KEY,
            can_annotate INTEGER DEFAULT 0,
            can_edit_db INTEGER DEFAULT 0,
            can_manage_users INTEGER DEFAULT 0,
            description TEXT
        )
    ''')

    # Insert default permissions if table is empty
    cursor.execute('SELECT COUNT(*) FROM permissions')
    if cursor.fetchone()[0] == 0:
        cursor.executemany('''
            INSERT INTO permissions (role, can_annotate, can_edit_db, can_manage_users, description)
            VALUES (?, ?, ?, ?, ?)
        ''', [
            ('admin', 1, 1, 1, 'Full access to all features'),
            ('annotator', 1, 0, 0, 'Can annotate images'),
            ('viewer', 0, 0, 0, 'Read-only access')
        ])

    # Ensure base admin is always in approved_emails
    cursor.execute('SELECT email FROM approved_emails WHERE email = ?', (BASE_ADMIN_EMAIL,))
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO approved_emails (email, added_by, added_at, notes)
            VALUES (?, ?, ?, ?)
        ''', (BASE_ADMIN_EMAIL, 'SYSTEM', datetime.now().isoformat(), 'Protected base administrator'))
        print(f"✓ Added base admin to approved emails: {BASE_ADMIN_EMAIL}")

    # Ensure base admin is always in admin_users
    cursor.execute('SELECT email FROM admin_users WHERE email = ?', (BASE_ADMIN_EMAIL,))
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO admin_users (email, added_at)
            VALUES (?, ?)
        ''', (BASE_ADMIN_EMAIL, datetime.now().isoformat()))
        print(f"✓ Added base admin to admin users: {BASE_ADMIN_EMAIL}")

    conn.commit()
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
    """Check if email is in the approved list"""
    conn = sqlite3.connect(AUTH_DB)
    cursor = conn.cursor()
    cursor.execute('SELECT email FROM approved_emails WHERE email = ?', (email,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def is_admin(email):
    """Check if user is an admin"""
    conn = sqlite3.connect(AUTH_DB)
    cursor = conn.cursor()
    cursor.execute('SELECT email FROM admin_users WHERE email = ?', (email,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def add_approved_email(email, added_by, notes=''):
    """Add email to approved list"""
    conn = sqlite3.connect(AUTH_DB)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO approved_emails (email, added_by, added_at, notes)
            VALUES (?, ?, ?, ?)
        ''', (email, added_by, datetime.now().isoformat(), notes))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # Email already exists
    finally:
        conn.close()

def remove_approved_email(email):
    """
    Remove email from approved list

    Protection: Cannot remove base admin from approved list
    """
    if is_base_admin(email):
        raise ValueError(f"Cannot remove base admin from approved list: {email}")

    conn = sqlite3.connect(AUTH_DB)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM approved_emails WHERE email = ?', (email,))
    conn.commit()
    conn.close()

def get_approved_emails():
    """Get all approved emails"""
    conn = sqlite3.connect(AUTH_DB)
    cursor = conn.cursor()
    cursor.execute('SELECT email, added_by, added_at, notes FROM approved_emails ORDER BY added_at DESC')
    emails = [{'email': row[0], 'added_by': row[1], 'added_at': row[2], 'notes': row[3]}
              for row in cursor.fetchall()]
    conn.close()
    return emails

def create_or_update_user(email, name, picture):
    """Create new user or update existing user's login info"""
    conn = sqlite3.connect(AUTH_DB)
    cursor = conn.cursor()

    # Check if user exists
    cursor.execute('SELECT email, login_count, role FROM users WHERE email = ?', (email,))
    existing = cursor.fetchone()

    if existing:
        # Update existing user
        cursor.execute('''
            UPDATE users
            SET name = ?, picture = ?, last_login = ?, login_count = login_count + 1
            WHERE email = ?
        ''', (name, picture, datetime.now().isoformat(), email))
    else:
        # Create new user with default role
        # Check if they're in admin_users table (from setup script)
        cursor.execute('SELECT email FROM admin_users WHERE email = ?', (email,))
        is_admin_user = cursor.fetchone() is not None
        default_role = 'admin' if is_admin_user else 'viewer'

        cursor.execute('''
            INSERT INTO users (email, name, picture, first_login, last_login, login_count, role)
            VALUES (?, ?, ?, ?, ?, 1, ?)
        ''', (email, name, picture, datetime.now().isoformat(), datetime.now().isoformat(), default_role))

    conn.commit()
    conn.close()

def get_all_users():
    """Get all registered users"""
    conn = sqlite3.connect(AUTH_DB)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT email, name, picture, first_login, last_login, login_count
        FROM users
        ORDER BY last_login DESC
    ''')
    users = [{'email': row[0], 'name': row[1], 'picture': row[2],
              'first_login': row[3], 'last_login': row[4], 'login_count': row[5]}
             for row in cursor.fetchall()]
    conn.close()
    return users

def add_admin(email):
    """Add user to admin list"""
    conn = sqlite3.connect(AUTH_DB)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO admin_users (email, added_at)
            VALUES (?, ?)
        ''', (email, datetime.now().isoformat()))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
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
        if not is_admin(user_email):
            return jsonify({'error': 'Admin access required'}), 403

        return f(*args, **kwargs)
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
    """Get user's role from database"""
    conn = sqlite3.connect(AUTH_DB)
    cursor = conn.cursor()
    cursor.execute('SELECT role FROM users WHERE email = ?', (email,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 'viewer'

def get_user_permissions(email):
    """Get user's permissions based on their role"""
    role = get_user_role(email)
    conn = sqlite3.connect(AUTH_DB)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT can_annotate, can_edit_db, can_manage_users
        FROM permissions
        WHERE role = ?
    ''', (role,))
    result = cursor.fetchone()
    conn.close()

    if result:
        return {
            'role': role,
            'can_annotate': bool(result[0]),
            'can_edit_db': bool(result[1]),
            'can_manage_users': bool(result[2])
        }
    return {
        'role': 'viewer',
        'can_annotate': False,
        'can_edit_db': False,
        'can_manage_users': False
    }

def update_user_role(email, new_role):
    """
    Update a user's role

    Protection: The base admin cannot be demoted from admin role
    """
    valid_roles = ['admin', 'annotator', 'viewer']
    if new_role not in valid_roles:
        return False

    # Protect base admin from being demoted
    if is_base_admin(email) and new_role != 'admin':
        raise ValueError(f"Cannot change role of base admin: {email}")

    conn = sqlite3.connect(AUTH_DB)
    cursor = conn.cursor()

    # Update users table
    cursor.execute('UPDATE users SET role = ? WHERE email = ?', (new_role, email))

    # Update admin_users table accordingly
    if new_role == 'admin':
        # Add to admin_users if not already there
        try:
            cursor.execute('''
                INSERT INTO admin_users (email, added_at)
                VALUES (?, ?)
            ''', (email, datetime.now().isoformat()))
        except sqlite3.IntegrityError:
            pass  # Already an admin
    else:
        # Remove from admin_users if they're not admin anymore
        cursor.execute('DELETE FROM admin_users WHERE email = ?', (email,))

    conn.commit()
    conn.close()
    return True

def is_base_admin(email):
    """Check if email is the protected base admin"""
    return email == BASE_ADMIN_EMAIL

def delete_user(email):
    """
    Delete a user completely from the system

    Protection: The base admin cannot be deleted
    """
    # Protect base admin from deletion
    if is_base_admin(email):
        raise ValueError(f"Cannot delete base admin: {email}")

    conn = sqlite3.connect(AUTH_DB)
    cursor = conn.cursor()

    # Delete from users table
    cursor.execute('DELETE FROM users WHERE email = ?', (email,))

    # Delete from admin_users table if exists
    cursor.execute('DELETE FROM admin_users WHERE email = ?', (email,))

    # Optionally remove from approved_emails (so they can't log back in)
    cursor.execute('DELETE FROM approved_emails WHERE email = ?', (email,))

    conn.commit()
    conn.close()
    return True

def get_all_users_with_roles():
    """Get all registered users with their roles and permissions"""
    conn = sqlite3.connect(AUTH_DB)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.email, u.name, u.picture, u.first_login, u.last_login,
               u.login_count, u.role
        FROM users u
        ORDER BY u.last_login DESC
    ''')
    users = []
    for row in cursor.fetchall():
        user = {
            'email': row[0],
            'name': row[1],
            'picture': row[2],
            'first_login': row[3],
            'last_login': row[4],
            'login_count': row[5],
            'role': row[6] or 'viewer',
            'is_base_admin': is_base_admin(row[0])
        }
        # Add permissions
        perms = get_user_permissions(user['email'])
        user.update(perms)
        users.append(user)

    conn.close()
    return users

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
