"""
Authentication module for Nestperts
Handles Google OAuth, user management, and access control
"""

import os
import json
import libsql_client
from datetime import datetime
from functools import wraps
from flask import session, redirect, url_for, request, jsonify
from authlib.integrations.flask_client import OAuth
import logging

# Initialize logger
logger = logging.getLogger(__name__)

# ============================================================================
# DATABASE SETUP
# ============================================================================

# Turso Cloud Configuration (CLOUD-ONLY MODE)
TURSO_URL = os.getenv("TURSO_DATABASE_URL")
TURSO_TOKEN = os.getenv("TURSO_AUTH_TOKEN")

def get_cloud_client():
    """Get a connection to the Turso cloud database."""
    if not TURSO_URL or not TURSO_TOKEN:
        raise ValueError("❌ TURSO_DATABASE_URL and TURSO_AUTH_TOKEN must be set in .env")
    try:
        client = libsql_client.create_client_sync(url=TURSO_URL, auth_token=TURSO_TOKEN)
        logger.info("✅ Successfully connected to Turso cloud database")
        return client
    except Exception as e:
        logger.error(f"❌ Failed to connect to Turso: {e}")
        raise ConnectionError(f"Cannot connect to Turso database: {e}")

# Base admin that cannot be removed or demoted
BASE_ADMIN_EMAIL = 'olisemekanmarkwe@gmail.com'

def init_auth_db():
    """Initialize authentication database with users and approved emails (Turso Cloud ONLY)"""
    client = get_cloud_client()

    if client:  # Will always be True now (or raises exception)
        try:
            # Initialize all tables in Turso
            client.execute('''
                CREATE TABLE IF NOT EXISTS approved_emails (
                    email TEXT PRIMARY KEY,
                    added_by TEXT,
                    added_at TEXT,
                    notes TEXT
                )
            ''')

            client.execute('''
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

            client.execute('''
                CREATE TABLE IF NOT EXISTS admin_users (
                    email TEXT PRIMARY KEY,
                    added_at TEXT
                )
            ''')

            client.execute('''
                CREATE TABLE IF NOT EXISTS permissions (
                    role TEXT PRIMARY KEY,
                    can_annotate INTEGER DEFAULT 0,
                    can_edit_db INTEGER DEFAULT 0,
                    can_manage_users INTEGER DEFAULT 0,
                    description TEXT
                )
            ''')

            # Insert default permissions if table is empty
            perms_count = client.execute('SELECT COUNT(*) FROM permissions')
            if perms_count.rows[0][0] == 0:
                client.batch([
                    ("INSERT INTO permissions (role, can_annotate, can_edit_db, can_manage_users, description) VALUES (?, ?, ?, ?, ?)", 
                     ['admin', 1, 1, 1, 'Full access to all features']),
                    ("INSERT INTO permissions (role, can_annotate, can_edit_db, can_manage_users, description) VALUES (?, ?, ?, ?, ?)", 
                     ['annotator', 1, 0, 0, 'Can annotate images']),
                    ("INSERT INTO permissions (role, can_annotate, can_edit_db, can_manage_users, description) VALUES (?, ?, ?, ?, ?)", 
                     ['viewer', 0, 0, 0, 'Read-only access'])
                ])

            # Ensure base admin is approved and set as admin
            client.execute('INSERT OR IGNORE INTO approved_emails (email, added_by, added_at, notes) VALUES (?, ?, ?, ?)', 
                          [BASE_ADMIN_EMAIL, 'SYSTEM', datetime.now().isoformat(), 'Protected base administrator'])
            client.execute('INSERT OR IGNORE INTO admin_users (email, added_at) VALUES (?, ?)', 
                          [BASE_ADMIN_EMAIL, datetime.now().isoformat()])
            
            logger.info("✅ Cloud authentication database initialized (Turso)")
            client.close()
            return
        except Exception as e:
            logger.error(f"❌ Failed to initialize Turso database: {e}")
            if client: client.close()
            raise  # Fail loudly instead of falling back

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
    """Check if email is in the approved list (Turso Cloud ONLY)"""
    client = get_cloud_client()
    try:
        result = client.execute('SELECT email FROM approved_emails WHERE email = ?', [email])
        client.close()
        return len(result.rows) > 0
    except Exception as e:
        if client: client.close()
        logger.error(f"❌ Failed to check approved email: {e}")
        raise

def is_admin(email):
    """Check if user is an admin (Turso Cloud ONLY)"""
    client = get_cloud_client()
    try:
        result = client.execute('SELECT email FROM admin_users WHERE email = ?', [email])
        client.close()
        return len(result.rows) > 0
    except Exception as e:
        if client: client.close()
        logger.error(f"❌ Failed to check admin status: {e}")
        raise

def add_approved_email(email, added_by, notes=''):
    """Add email to approved list (Turso Cloud ONLY)"""
    client = get_cloud_client()
    try:
        client.execute('''
            INSERT INTO approved_emails (email, added_by, added_at, notes)
            VALUES (?, ?, ?, ?)
        ''', [email, added_by, datetime.now().isoformat(), notes])
        client.close()
        logger.info(f"✅ Email {email} added to approved list")
        return True
    except Exception as e:
        if client: client.close()
        logger.error(f"❌ Failed to add approved email: {e}")
        return False

def remove_approved_email(email):
    """Remove email from approved list (Turso Cloud ONLY)"""
    if is_base_admin(email):
        raise ValueError(f"Cannot remove base admin from approved list: {email}")

    client = get_cloud_client()
    try:
        client.execute('DELETE FROM approved_emails WHERE email = ?', [email])
        client.close()
        logger.info(f"✅ Email {email} removed from approved list")
    except Exception as e:
        if client: client.close()
        logger.error(f"❌ Failed to remove approved email: {e}")
        raise

def get_approved_emails():
    """Get all approved emails (Turso Cloud ONLY)"""
    client = get_cloud_client()
    try:
        result = client.execute('SELECT email, added_by, added_at, notes FROM approved_emails ORDER BY added_at DESC')
        emails = [{'email': row[0], 'added_by': row[1], 'added_at': row[2], 'notes': row[3]}
                  for row in result.rows]
        client.close()
        return emails
    except Exception as e:
        if client: client.close()
        logger.error(f"❌ Failed to get approved emails: {e}")
        raise

def create_or_update_user(email, name, picture):
    """Create new user or update existing user's login info (Turso Cloud ONLY)"""
    client = get_cloud_client()
    try:
        # Check if user exists
        result = client.execute('SELECT email, login_count, role FROM users WHERE email = ?', [email])

        if result.rows:
            # Update existing user
            client.execute('''
                UPDATE users
                SET name = ?, picture = ?, last_login = ?, login_count = login_count + 1
                WHERE email = ?
            ''', [name, picture, datetime.now().isoformat(), email])
        else:
            # Create new user
            is_admin_res = client.execute('SELECT email FROM admin_users WHERE email = ?', [email])
            default_role = 'admin' if len(is_admin_res.rows) > 0 else 'viewer'

            client.execute('''
                INSERT INTO users (email, name, picture, first_login, last_login, login_count, role)
                VALUES (?, ?, ?, ?, ?, 1, ?)
            ''', [email, name, picture, datetime.now().isoformat(), datetime.now().isoformat(), default_role])

        client.close()
        logger.info(f"✅ User {email} created/updated in Turso")
    except Exception as e:
        logger.error(f"❌ Cloud user update failed: {e}")
        if client: client.close()
        raise

def get_all_users():
    """Get all registered users (Turso Cloud ONLY)"""
    client = get_cloud_client()
    try:
        result = client.execute('''
            SELECT email, name, picture, first_login, last_login, login_count
            FROM users
            ORDER BY last_login DESC
        ''')
        users = [{'email': row[0], 'name': row[1], 'picture': row[2],
                  'first_login': row[3], 'last_login': row[4], 'login_count': row[5]}
                 for row in result.rows]
        client.close()
        return users
    except Exception as e:
        if client: client.close()
        logger.error(f"❌ Failed to get users: {e}")
        raise

def add_admin(email):
    """Add user to admin list (Turso Cloud ONLY)"""
    client = get_cloud_client()
    try:
        client.execute('''
            INSERT INTO admin_users (email, added_at)
            VALUES (?, ?)
        ''', [email, datetime.now().isoformat()])
        client.close()
        logger.info(f"✅ User {email} added as admin")
        return True
    except Exception as e:
        if client: client.close()
        logger.error(f"❌ Failed to add admin: {e}")
        return False

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
    """Get user's role from database (Turso Cloud ONLY)"""
    client = get_cloud_client()
    try:
        result = client.execute('SELECT role FROM users WHERE email = ?', [email])
        client.close()
        return result.rows[0][0] if result.rows else 'viewer'
    except Exception as e:
        if client: client.close()
        logger.error(f"❌ Failed to get user role: {e}")
        return 'viewer'  # Safe default

def get_user_permissions(email):
    """Get user's permissions based on their role (Turso Cloud ONLY)"""
    role = get_user_role(email)
    client = get_cloud_client()
    try:
        result = client.execute('''
            SELECT can_annotate, can_edit_db, can_manage_users
            FROM permissions
            WHERE role = ?
        ''', [role])
        client.close()
        if result.rows:
            return {
                'role': role,
                'can_annotate': bool(result.rows[0][0]),
                'can_edit_db': bool(result.rows[0][1]),
                'can_manage_users': bool(result.rows[0][2])
            }
        # Safe default if role not found
        return {
            'role': 'viewer',
            'can_annotate': False,
            'can_edit_db': False,
            'can_manage_users': False
        }
    except Exception as e:
        if client: client.close()
        logger.error(f"❌ Failed to get user permissions: {e}")
        # Safe default on error
        return {
            'role': 'viewer',
            'can_annotate': False,
            'can_edit_db': False,
            'can_manage_users': False
        }

def is_base_admin(email):
    """Check if email is the protected base admin"""
    return email == BASE_ADMIN_EMAIL

def update_user_role(email, new_role):
    """Update a user's role (Turso Cloud ONLY)"""
    valid_roles = ['admin', 'annotator', 'viewer']
    if new_role not in valid_roles:
        return False

    if is_base_admin(email) and new_role != 'admin':
        raise ValueError(f"Cannot change role of base admin: {email}")

    client = get_cloud_client()
    try:
        # Update users table
        client.execute('UPDATE users SET role = ? WHERE email = ?', [new_role, email])

        # Update admin_users table accordingly
        if new_role == 'admin':
            client.execute('INSERT OR IGNORE INTO admin_users (email, added_at) VALUES (?, ?)',
                          [email, datetime.now().isoformat()])
        else:
            client.execute('DELETE FROM admin_users WHERE email = ?', [email])

        client.close()
        logger.info(f"✅ User {email} role updated to {new_role}")
        return True
    except Exception as e:
        if client: client.close()
        logger.error(f"❌ Failed to update user role: {e}")
        return False

def delete_user(email):
    """Delete a user completely from the system (Turso Cloud ONLY)"""
    if is_base_admin(email):
        raise ValueError(f"Cannot delete base admin: {email}")

    client = get_cloud_client()
    try:
        client.batch([
            ('DELETE FROM users WHERE email = ?', [email]),
            ('DELETE FROM admin_users WHERE email = ?', [email]),
            ('DELETE FROM approved_emails WHERE email = ?', [email])
        ])
        client.close()
        logger.info(f"✅ User {email} deleted")
        return True
    except Exception as e:
        if client: client.close()
        logger.error(f"❌ Failed to delete user: {e}")
        return False

def get_all_users_with_roles():
    """Get all registered users with their roles and permissions (Turso Cloud ONLY)"""
    client = get_cloud_client()
    try:
        result = client.execute('''
            SELECT u.email, u.name, u.picture, u.first_login, u.last_login,
                   u.login_count, u.role
            FROM users u
            ORDER BY u.last_login DESC
        ''')
        users = []
        for row in result.rows:
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
            perms = get_user_permissions(user['email'])
            user.update(perms)
            users.append(user)
        client.close()
        return users
    except Exception as e:
        if client: client.close()
        logger.error(f"❌ Failed to get users with roles: {e}")
        raise

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
