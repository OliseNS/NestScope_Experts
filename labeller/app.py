"""
Nestperts V2 - Project-Based Annotation Platform

Enhanced version with:
- Multi-project management (like CVAT)
- Folder upload support
- Dark/light theme
- Team collaboration
- Multiple export formats (YOLO, COCO, GeoJSON)
"""

import os
import sys
import json
import glob
import uuid
import zipfile
import shutil
import numpy as np
import time
from pathlib import Path
from datetime import datetime
from functools import lru_cache
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, jsonify, send_from_directory, send_file, redirect, url_for, session, flash
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

import yaml

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Load server configuration from YAML
def load_server_config():
    """Load configuration from server/config.yaml"""
    config_path = os.path.join(PROJECT_ROOT, 'server', 'config.yaml')
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"⚠️  Warning: Could not load server/config.yaml: {e}")
        # Return sensible defaults
        return {
            'cv': {
                'model': 'models/swift.onnx',
                'classifier': 'models/classifier_swift.onnx',
                'default_confidence': 0.25
            }
        }

server_config = load_server_config()

# Import authentication module
from labeller.auth import (
    init_auth_db,
    setup_oauth,
    login_required,
    admin_required,
    api_login_required,
    annotator_required,
    api_annotator_required,
    api_db_editor_required,
    is_email_approved,
    is_admin,
    is_base_admin,
    create_or_update_user,
    add_approved_email,
    remove_approved_email,
    get_approved_emails,
    get_all_users,
    get_current_user,
    add_admin,
    get_user_permissions,
    delete_user,
)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = None  # No upload limit
app.config['MAX_FORM_MEMORY_SIZE'] = None  # No form memory limit
app.config['UPLOAD_FOLDER'] = 'projects_data'

# Security configuration for sessions
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24).hex())

# Initialize OAuth
oauth, google = setup_oauth(app)

# Initialize authentication database
init_auth_db()

# Configure request limits
@app.before_request
def before_request():
    """Remove any size limits on requests"""
    if request.method == 'POST':
        # Allow unlimited content length
        request.environ['CONTENT_LENGTH'] = request.environ.get('CONTENT_LENGTH', '0')

# Configure caching for static assets
@app.after_request
def add_header(response):
    """Add caching headers for static assets to improve performance"""
    if request.path.startswith('/static/'):
        # Cache static assets for 1 day (86400 seconds)
        # Includes CSS, JS, images, fonts
        response.headers['Cache-Control'] = 'public, max-age=86400, immutable'
    return response

# ============================================================================
# PROJECT MANAGEMENT
# ============================================================================

# Get the directory where app.py is located
APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(APP_DIR, 'projects')

# ============================================================================
# PERFORMANCE: IN-MEMORY CACHING
# ============================================================================
# Cache expensive operations to avoid repeated file I/O and calculations
# Cache is invalidated when projects are modified (upload, delete, annotation)

_cache = {
    'project_stats': {},      # {project_folder: {'data': stats_dict, 'timestamp': time}}
    'all_users_with_roles': {'data': None, 'timestamp': 0},  # Cache user list from DB
    'user_contributions': {}, # {user_email: {'data': contributions_dict, 'timestamp': time}}
    'team_page': {'data': None, 'timestamp': 0},  # Cached /users payload (heavy filesystem scan)
}

CACHE_TTL = 60  # Cache time-to-live in seconds (1 minute)

def get_cached_project_stats(project_folder):
    """Get cached project stats or calculate and cache them"""
    cache_entry = _cache['project_stats'].get(project_folder)
    now = time.time()

    # Return cached data if fresh (less than 60 seconds old)
    if cache_entry and (now - cache_entry['timestamp']) < CACHE_TTL:
        return cache_entry['data']

    # Calculate fresh stats and cache them
    stats = calculate_project_stats(project_folder)
    _cache['project_stats'][project_folder] = {
        'data': stats,
        'timestamp': now
    }
    return stats

def get_cached_all_users_with_roles():
    """Get cached user list from database"""
    from labeller.auth import get_all_users_with_roles

    cache_entry = _cache['all_users_with_roles']
    now = time.time()

    # Return cached data if fresh
    if cache_entry['data'] and (now - cache_entry['timestamp']) < CACHE_TTL:
        return cache_entry['data']

    # Fetch fresh data and cache it
    users = get_all_users_with_roles()
    _cache['all_users_with_roles'] = {
        'data': users,
        'timestamp': now
    }
    return users

def invalidate_project_cache(project_folder=None):
    """Invalidate cache for a specific project or all projects"""
    if project_folder:
        # Clear cache for specific project
        _cache['project_stats'].pop(project_folder, None)
        # Also clear user contributions cache as it depends on projects
        _cache['user_contributions'].clear()
    else:
        # Clear all caches
        _cache['project_stats'].clear()
        _cache['user_contributions'].clear()
    # Team page aggregates all projects; any project change can alter counts
    _cache['team_page'] = {'data': None, 'timestamp': 0}

def invalidate_user_cache():
    """Invalidate user-related caches"""
    _cache['all_users_with_roles'] = {'data': None, 'timestamp': 0}
    _cache['user_contributions'].clear()
    _cache['team_page'] = {'data': None, 'timestamp': 0}


def _build_team_users_list():
    """
    Build data for /users (Team page). Precomputes per-project annotation line counts
    once per unique completed image — avoids O(users * completed) label file reads.
    """
    users_list = []
    auth_users = get_cached_all_users_with_roles()
    projects = get_all_projects()
    project_states = {}

    for proj in projects:
        folder = proj['folder']
        state = load_project_state(folder)
        labels_dir = os.path.join(PROJECTS_DIR, folder, 'labels')
        all_completed_here = set()
        for ud in state.get('users', {}).values():
            all_completed_here.update(ud.get('completed', []))
        ann_by_image = {}
        for img in all_completed_here:
            label_path = os.path.join(labels_dir, os.path.splitext(img)[0] + '.txt')
            if os.path.exists(label_path):
                with open(label_path, 'r') as f:
                    ann_by_image[img] = sum(1 for line in f if line.strip())
            else:
                ann_by_image[img] = 0
        project_states[folder] = {
            'metadata': proj,
            'state': state,
            'ann_by_image': ann_by_image,
        }

    for user in auth_users:
        user_projects = []
        total_completed = 0
        total_annotations = 0

        for proj_folder, proj_data in project_states.items():
            state = proj_data['state']
            user_data = state.get('users', {}).get(user['email'])
            if not user_data:
                user_data = state.get('users', {}).get(user['name'])
            if not user_data:
                continue

            assigned = user_data.get('assigned', [])
            completed = user_data.get('completed', [])
            if not (assigned or completed):
                continue

            user_projects.append({
                'folder': proj_folder,
                'name': proj_data['metadata']['name'],
                'assigned': len(assigned),
                'completed': len(completed),
            })
            total_completed += len(completed)
            if completed:
                ann_map = proj_data['ann_by_image']
                total_annotations += sum(ann_map.get(img, 0) for img in completed)

        users_list.append({
            'name': user['name'],
            'email': user['email'],
            'picture': user.get('picture'),
            'role': user['role'],
            'first_login': user.get('first_login', ''),
            'projects': user_projects,
            'total_projects': len(user_projects),
            'total_completed': total_completed,
            'total_annotations': total_annotations,
        })

    return users_list


def get_cached_team_users_list():
    """Cached Team page user rows (same TTL as other caches)."""
    cache_entry = _cache['team_page']
    now = time.time()
    if cache_entry['data'] is not None and (now - cache_entry['timestamp']) < CACHE_TTL:
        return cache_entry['data']
    users_list = _build_team_users_list()
    _cache['team_page'] = {'data': users_list, 'timestamp': now}
    return users_list


def ensure_directories():
    """Create necessary directories"""
    os.makedirs(PROJECTS_DIR, exist_ok=True)

def sanitize_folder_name(name):
    """Convert project name to safe folder name"""
    import re
    # Convert to lowercase, replace spaces with underscores
    safe = name.lower().strip()
    safe = re.sub(r'[^\w\s-]', '', safe)  # Remove special chars
    safe = re.sub(r'[-\s]+', '_', safe)   # Replace spaces/hyphens with underscore
    return safe

def load_projects():
    """Load all projects by scanning projects/ directory"""
    projects = {}

    if not os.path.exists(PROJECTS_DIR):
        return projects

    for folder_name in os.listdir(PROJECTS_DIR):
        # Skip hidden directories (starting with .)
        if folder_name.startswith('.'):
            continue

        project_path = os.path.join(PROJECTS_DIR, folder_name)
        if not os.path.isdir(project_path):
            continue

        metadata_file = os.path.join(project_path, 'metadata.json')
        if os.path.exists(metadata_file):
            with open(metadata_file, 'r') as f:
                projects[folder_name] = json.load(f)
        else:
            # Legacy support: project exists but no metadata
            projects[folder_name] = {
                'name': folder_name.replace('_', ' ').title(),
                'description': '',
                'created_at': datetime.now().isoformat()
            }

    return projects

def save_project_metadata(project_folder, metadata):
    """Save metadata.json for a project"""
    project_path = os.path.join(PROJECTS_DIR, project_folder)
    metadata_file = os.path.join(project_path, 'metadata.json')
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)

def get_project(project_folder):
    """Get a single project by folder name"""
    project_path = os.path.join(PROJECTS_DIR, project_folder)
    if not os.path.exists(project_path):
        return None

    metadata_file = os.path.join(project_path, 'metadata.json')
    if os.path.exists(metadata_file):
        with open(metadata_file, 'r') as f:
            return json.load(f)
    return None

def get_all_projects():
    """Get list of all projects with folder name and metadata"""
    projects_dict = load_projects()
    projects_list = []

    for folder_name, metadata in projects_dict.items():
        project = {
            'folder': folder_name,
            'name': metadata.get('name', folder_name.replace('_', ' ').title()),
            'description': metadata.get('description', ''),
            'created_at': metadata.get('created_at', '')
        }
        projects_list.append(project)

    return projects_list

def load_project_state(project_folder):
    """Load project_state.json for user assignments"""
    project_path = os.path.join(PROJECTS_DIR, project_folder)
    state_file = os.path.join(project_path, 'project_state.json')

    if os.path.exists(state_file):
        with open(state_file, 'r') as f:
            return json.load(f)
    return {'users': {}}

def save_project_state(project_folder, state):
    """Save project_state.json"""
    project_path = os.path.join(PROJECTS_DIR, project_folder)
    state_file = os.path.join(project_path, 'project_state.json')
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)

def load_data_yaml(project_folder):
    """Load data.yaml for class definitions"""
    import yaml
    project_path = os.path.join(PROJECTS_DIR, project_folder)
    yaml_file = os.path.join(project_path, 'data.yaml')

    if os.path.exists(yaml_file):
        with open(yaml_file, 'r') as f:
            return yaml.safe_load(f)
    return None

def save_data_yaml(project_folder, data):
    """Save data.yaml"""
    import yaml
    project_path = os.path.join(PROJECTS_DIR, project_folder)
    yaml_file = os.path.join(project_path, 'data.yaml')
    with open(yaml_file, 'w') as f:
        yaml.dump(data, f, default_flow_style=False)

def calculate_project_stats(project_folder):
    """
    Calculate statistics for a project based on USER WORK, not pre-imported labels.

    This counts only images that users have marked as "completed" through the
    annotation interface, not all label files (which may include pre-imported data).
    """
    project_path = os.path.join(PROJECTS_DIR, project_folder)
    images_dir = os.path.join(project_path, 'images')
    labels_dir = os.path.join(project_path, 'labels')

    # Get list of actual images that exist
    existing_images = set()
    if os.path.exists(images_dir):
        existing_images = set([f for f in os.listdir(images_dir)
                              if f.lower().endswith(('.jpg', '.jpeg', '.png'))])

    total_images = len(existing_images)

    # Get user-completed images from project_state.json
    state = load_project_state(project_folder)
    completed_by_users = set()
    for user_data in state.get('users', {}).values():
        completed_by_users.update(user_data.get('completed', []))

    # Filter out "ghost completions" - images marked complete but no longer exist
    completed_by_users = completed_by_users & existing_images

    # Count only user-completed images and their annotations
    completed_images = len(completed_by_users)
    total_annotations = 0
    for img_name in completed_by_users:
        label_file = os.path.splitext(img_name)[0] + '.txt'
        label_path = os.path.join(labels_dir, label_file)
        if os.path.exists(label_path):
            with open(label_path, 'r') as f:
                lines = [line.strip() for line in f if line.strip()]
                total_annotations += len(lines)

    # Calculate progress based on user work
    if total_images == 0:
        progress = 0
    elif completed_images == 0:
        progress = 0
    else:
        progress = min((completed_images / total_images * 100), 100.0)  # Cap at 100%

    return {
        'total_images': total_images,
        'completed_images': completed_images,
        'total_annotations': total_annotations,
        'progress': progress
    }

def get_all_project_stats():
    """Get global statistics across all projects"""
    projects = load_projects()
    total_projects = len(projects)
    total_images = 0
    total_annotations = 0
    active_users = set()

    for project_folder in projects.keys():
        stats = calculate_project_stats(project_folder)
        total_images += stats['total_images']
        total_annotations += stats['total_annotations']

        # Load project state for user info
        state = load_project_state(project_folder)
        active_users.update(state.get('users', {}).keys())

    return {
        'total_projects': total_projects,
        'total_images': total_images,
        'total_annotations': total_annotations,
        'active_users': len(active_users)
    }

def sync_project_labels_images(project_folder):
    """
    Synchronize labels and images in a project.

    Rules:
    1. If a label exists without a matching image → DELETE the label
    2. If an image exists without a matching label → CREATE an empty label

    This ensures every image has exactly one label file, and no orphaned labels exist.

    Returns:
        dict with 'deleted_labels', 'created_labels', and 'errors'
    """
    project_path = os.path.join(PROJECTS_DIR, project_folder)
    images_dir = os.path.join(project_path, 'images')
    labels_dir = os.path.join(project_path, 'labels')

    # Ensure directories exist
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(labels_dir, exist_ok=True)

    deleted_labels = []
    created_labels = []
    errors = []

    # Step 1: Find and delete orphaned labels (labels without images)
    try:
        label_files = [f for f in os.listdir(labels_dir) if f.endswith('.txt')]
        for label_file in label_files:
            # Get base name (without .txt extension)
            base_name = os.path.splitext(label_file)[0]
            # Check if matching image exists (.jpg, .jpeg, or .png)
            matching_images = [
                f for f in os.listdir(images_dir)
                if os.path.splitext(f)[0] == base_name and f.lower().endswith(('.jpg', '.jpeg', '.png'))
            ]

            if not matching_images:
                # No matching image - delete the label
                label_path = os.path.join(labels_dir, label_file)
                try:
                    os.remove(label_path)
                    deleted_labels.append(label_file)
                    print(f"Deleted orphaned label: {label_file}")
                except Exception as e:
                    errors.append(f"Failed to delete {label_file}: {str(e)}")

    except Exception as e:
        errors.append(f"Error scanning labels: {str(e)}")

    # Step 2: Find images without labels and create empty labels
    try:
        image_files = [f for f in os.listdir(images_dir)
                      if f.lower().endswith(('.jpg', '.jpeg', '.png'))]

        for image_file in image_files:
            # Get base name (without extension)
            base_name = os.path.splitext(image_file)[0]
            label_file = base_name + '.txt'
            label_path = os.path.join(labels_dir, label_file)

            if not os.path.exists(label_path):
                # Create empty label file
                try:
                    with open(label_path, 'w') as f:
                        pass  # Create empty file
                    created_labels.append(label_file)
                    print(f"Created empty label: {label_file}")
                except Exception as e:
                    errors.append(f"Failed to create {label_file}: {str(e)}")

    except Exception as e:
        errors.append(f"Error scanning images: {str(e)}")

    return {
        'deleted_labels': deleted_labels,
        'created_labels': created_labels,
        'errors': errors,
        'deleted_count': len(deleted_labels),
        'created_count': len(created_labels),
        'error_count': len(errors)
    }

# ============================================================================
# PUBLIC ROUTES (No Authentication Required)
# ============================================================================

@app.route('/health')
def health():
    """Health check endpoint for monitoring (no auth required)"""
    import sqlite3
    from labeller.auth import get_auth_db_path

    try:
        path = get_auth_db_path()
        conn = sqlite3.connect(str(path), timeout=5.0)
        try:
            user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        finally:
            conn.close()

        return jsonify({
            'status': 'healthy',
            'database': 'sqlite',
            'auth_db': str(path),
            'service': 'nestperts',
            'port': 5000,
            'users': user_count,
            'authenticated': 'user' in session
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@app.route('/login')
def login():
    """Show login page"""
    error = request.args.get('error')
    not_approved = request.args.get('not_approved')
    return render_template('login.html', error=error, not_approved=not_approved)

@app.route('/auth/google')
def google_login():
    """Redirect to Google for authentication"""
    redirect_uri = url_for('google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/auth/google/callback')
def google_callback():
    """Handle Google OAuth callback"""
    try:
        # Get user info from Google
        token = google.authorize_access_token()
        user_info = token.get('userinfo')

        if not user_info:
            return redirect(url_for('login', error='Failed to get user information'))

        email = user_info.get('email')
        name = user_info.get('name')
        picture = user_info.get('picture')

        # Check if email is approved
        if not is_email_approved(email):
            return redirect(url_for('login', not_approved=email))

        # Create or update user record
        create_or_update_user(email, name, picture)

        # Role, permissions, and admin flag in one DB query
        from labeller.auth import get_login_session_payload
        payload = get_login_session_payload(email)
        if not payload:
            return redirect(url_for('login', error='Failed to load user profile'))
        perms, is_adm = payload

        # Store user in session (like giving them a wristband)
        session['user'] = {
            'email': email,
            'name': name,
            'picture': picture,
            'is_admin': is_adm,
            'role': perms['role'],
            'permissions': perms
        }

        # Redirect to the page they were trying to access (or home)
        next_page = request.args.get('next', '/')
        return redirect(next_page)

    except Exception as e:
        print(f"Auth error: {e}")
        return redirect(url_for('login', error='Authentication failed'))

@app.route('/logout')
def logout():
    """Log out user"""
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/admin')
@admin_required
def admin_panel():
    """Admin panel for managing approved emails and user roles"""
    approved_emails = get_approved_emails()
    users = get_cached_all_users_with_roles()

    total_logins = sum(u['login_count'] for u in users)

    # Count users by role
    role_counts = {'admin': 0, 'annotator': 0, 'viewer': 0}
    for u in users:
        role_counts[u['role']] = role_counts.get(u['role'], 0) + 1

    return render_template('admin_panel.html',
                         user=session['user'],
                         approved_emails=approved_emails,
                         users=users,
                         total_logins=total_logins,
                         role_counts=role_counts)

@app.route('/admin/add-email', methods=['POST'])
@admin_required
def admin_add_email():
    """Add an approved email"""
    email = request.form.get('email', '').strip().lower()
    notes = request.form.get('notes', '').strip()

    if not email:
        flash('Email is required', 'error')
        return redirect(url_for('admin_panel'))

    added_by = session['user']['email']
    success = add_approved_email(email, added_by, notes)

    if success:
        invalidate_user_cache()
        flash(f'Added {email} to approved list', 'success')
    else:
        flash(f'{email} is already approved', 'error')

    return redirect(url_for('admin_panel'))

@app.route('/admin/remove-email', methods=['POST'])
@admin_required
def admin_remove_email():
    """Remove an approved email"""
    email = request.form.get('email', '').strip()

    if not email:
        flash('Email is required', 'error')
        return redirect(url_for('admin_panel'))

    # Don't allow removing your own email
    if email == session['user']['email']:
        flash('Cannot remove your own email', 'error')
        return redirect(url_for('admin_panel'))

    remove_approved_email(email)
    invalidate_user_cache()
    flash(f'Removed {email} from approved list', 'success')

    return redirect(url_for('admin_panel'))

@app.route('/admin/update-role', methods=['POST'])
@admin_required
def admin_update_role():
    """Update a user's role"""
    from labeller.auth import update_user_role
    email = request.form.get('email', '').strip()
    new_role = request.form.get('role', '').strip()

    if not email or not new_role:
        flash('Email and role are required', 'error')
        return redirect(url_for('admin_panel'))

    # Don't allow changing your own role
    if email == session['user']['email']:
        flash('Cannot change your own role', 'error')
        return redirect(url_for('admin_panel'))

    try:
        success = update_user_role(email, new_role)
        if success:
            invalidate_user_cache()
            flash(f'Updated {email} to {new_role}', 'success')
        else:
            flash(f'Failed to update role', 'error')
    except ValueError as e:
        # Base admin protection triggered
        flash(str(e), 'error')

    return redirect(url_for('admin_panel'))

@app.route('/admin/delete-user', methods=['POST'])
@admin_required
def admin_delete_user():
    """Delete a user completely"""
    email = request.form.get('email', '').strip()

    if not email:
        flash('Email is required', 'error')
        return redirect(url_for('admin_panel'))

    # Don't allow deleting yourself
    if email == session['user']['email']:
        flash('Cannot delete your own account', 'error')
        return redirect(url_for('admin_panel'))

    try:
        success = delete_user(email)
        if success:
            invalidate_user_cache()
            flash(f'Deleted user {email}', 'success')
        else:
            flash(f'Failed to delete user', 'error')
    except ValueError as e:
        # Base admin protection triggered
        flash(str(e), 'error')

    return redirect(url_for('admin_panel'))

# ============================================================================
# ROUTES - MAIN PAGES
# ============================================================================

@app.route('/')
@login_required
def projects_dashboard():
    """Main projects dashboard - OPTIMIZED with caching"""
    projects = load_projects()
    projects_list = []

    # Aggregate stats (calculated inline to avoid double-calculation)
    aggregate_stats = {
        'total_projects': len(projects),
        'total_images': 0,
        'total_annotations': 0,
        'active_users': set()
    }

    # Get all auth users with their profile pictures (CACHED)
    auth_users_dict = {}
    try:
        all_auth_users = get_cached_all_users_with_roles()
        # Index by both email and name for flexible lookup
        for u in all_auth_users:
            auth_users_dict[u['email']] = u
            auth_users_dict[u['name']] = u
    except Exception as e:
        print(f"Warning: Could not load auth users: {e}")

    for project_folder, metadata in projects.items():
        # Use cached stats instead of recalculating every time
        stats = get_cached_project_stats(project_folder)

        # Aggregate stats inline
        aggregate_stats['total_images'] += stats['total_images']
        aggregate_stats['total_annotations'] += stats['total_annotations']

        # Get first image for thumbnail
        thumbnail_url = None
        images_dir = os.path.join(PROJECTS_DIR, project_folder, 'images')
        if os.path.exists(images_dir):
            images = [f for f in os.listdir(images_dir)
                     if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            if images:
                # Get first image (sorted alphabetically)
                first_image = sorted(images)[0]
                thumbnail_url = f'/project/{project_folder}/image/{first_image}'

        # Load project state for user count with profile pictures
        state = load_project_state(project_folder)
        user_keys = list(state.get('users', {}).keys())

        # Build users list with name, email, and picture
        users_with_pics = []
        seen_emails = set()  # Track unique users to avoid duplicates
        for user_key in user_keys:
            # Skip if we've already added this user
            if user_key in seen_emails:
                continue
            seen_emails.add(user_key)

            # Track active users globally
            aggregate_stats['active_users'].add(user_key)

            # Try to find user in auth database
            user_info = auth_users_dict.get(user_key, {})
            users_with_pics.append({
                'name': user_info.get('name', user_key),
                'email': user_info.get('email', user_key),
                'picture': user_info.get('picture')
            })

        projects_list.append({
            'folder': project_folder,
            'name': metadata.get('name', project_folder.replace('_', ' ').title()),
            'description': metadata.get('description', ''),
            'created_at': metadata.get('created_at', datetime.now().isoformat()),
            'users': users_with_pics,
            'total_images': stats['total_images'],
            'progress': stats['progress'],
            'thumbnail_url': thumbnail_url
        })

    # Sort by creation date (newest first)
    projects_list.sort(key=lambda x: x['created_at'], reverse=True)

    # Convert active_users set to count
    aggregate_stats['active_users'] = len(aggregate_stats['active_users'])

    return render_template('projects_dashboard.html',
                         projects=projects_list,
                         stats=aggregate_stats,
                         active_page='projects')

@app.route('/project/<project_folder>')
@login_required
def project_detail(project_folder):
    """Project detail page with task management"""
    metadata = get_project(project_folder)
    if not metadata:
        return "Project not found", 404

    # Use cached stats for performance
    stats = get_cached_project_stats(project_folder)
    project_path = os.path.join(PROJECTS_DIR, project_folder)
    images_dir = os.path.join(project_path, 'images')
    labels_dir = os.path.join(project_path, 'labels')

    # Get images
    images = []
    if os.path.exists(images_dir):
        for img_file in os.listdir(images_dir):
            if img_file.lower().endswith(('.jpg', '.jpeg', '.png')):
                label_file = os.path.splitext(img_file)[0] + '.txt'
                completed = os.path.exists(os.path.join(labels_dir, label_file))
                images.append({
                    'name': img_file,
                    'completed': completed
                })

    # Load project state for user details
    state = load_project_state(project_folder)

    # One pass over label files for all completed images (avoid re-reading the same file per user)
    ann_per_image = {}
    all_completed_imgs = set()
    for user_data in state.get('users', {}).values():
        for img in user_data.get('completed', []):
            all_completed_imgs.add(img)
    for img in all_completed_imgs:
        label_path = os.path.join(labels_dir, os.path.splitext(img)[0] + '.txt')
        if os.path.exists(label_path):
            with open(label_path, 'r') as f:
                ann_per_image[img] = sum(1 for line in f if line.strip())
        else:
            ann_per_image[img] = 0

    # Get user profile pictures from auth database (cached; same list as dashboard)
    auth_users = {}
    try:
        all_auth_users = get_cached_all_users_with_roles()
        for u in all_auth_users:
            auth_users[u['email']] = u
            auth_users[u['name']] = u
    except Exception as e:
        print(f"Warning: Could not load auth users: {e}")

    users_detail = []
    for user_key, user_data in state.get('users', {}).items():
        assigned = user_data.get('assigned', [])
        completed = user_data.get('completed', [])

        user_annotations = sum(ann_per_image.get(img, 0) for img in completed)

        # Get user info from auth database (user_key might be email or name)
        auth_user = auth_users.get(user_key, {})
        display_name = user_data.get('name', auth_user.get('name', user_key))
        user_picture = auth_user.get('picture')
        user_email = user_key if '@' in user_key else auth_user.get('email', user_key)

        users_detail.append({
            'username': display_name,
            'email': user_email,
            'picture': user_picture,
            'assigned': len(assigned),
            'completed': len(completed),
            'annotations': user_annotations
        })

    return render_template('project_detail.html',
                         project={
                             'folder': project_folder,
                             'name': metadata.get('name', project_folder.replace('_', ' ').title()),
                             'description': metadata.get('description', ''),
                             'users': list(state.get('users', {}).keys()),
                             'users_detail': users_detail,
                             'images': images,
                             **stats
                         },
                         active_page='projects')

@app.route('/help')
@login_required
def help_page():
    """Help and documentation page"""
    return render_template('help.html', active_page='help')

@app.route('/nestdb')
@login_required
def nestdb_page():
    """
    NestDB - Supabase-inspired database management interface

    SECURITY: Query execution requires admin or database editor permissions.
    We check permissions here and pass them to the frontend for UI control.

    Educational Note:
    Two-layer security:
    1. Flask checks if user CAN access NestDB interface
    2. FastAPI backend validates each query execution
    This prevents unauthorized database modifications.
    """
    # Get current user's permissions
    user_email = session['user']['email']
    permissions = get_user_permissions(user_email)

    # Check if user has database editing permission
    if not permissions.get('can_edit_db', False):
        return '''
        <html>
        <head><title>Access Denied</title></head>
        <body style="font-family: system-ui; padding: 2rem; max-width: 600px; margin: 0 auto;">
            <h1>🔒 Access Denied</h1>
            <p>You need <strong>database editor</strong> or <strong>admin</strong> permissions to access NestDB.</p>
            <p><a href="/" style="color: #D97757;">← Back to Home</a></p>
        </body>
        </html>
        ''', 403

    # Get API base URL from environment
    api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")

    return render_template(
        'nestdb.html',
        active_page='nestdb',
        can_edit_db=True,
        is_admin=is_admin(user_email),
        api_base_url=api_base_url
    )

@app.route('/flood-intelligence')
@login_required
def flood_intelligence_page():
    """
    Flood Intelligence Center - Real-time coastal risk assessment

    Expert tool for monitoring colony flood risk using multi-modal data fusion:
    - NOAA water levels (real-time)
    - FEMA flood zones
    - USGS erosion rates
    - HURDAT2 hurricane data
    - TWI survey data

    Uses persistent cache for instant loading with background updates.
    """
    # Get current user's permissions
    user_email = session['user']['email']
    permissions = get_user_permissions(user_email)

    # Check if user has database editing permission (expert access)
    if not permissions.get('can_edit_db', False):
        return '''
        <html>
        <head><title>Access Denied</title></head>
        <body style="font-family: system-ui; padding: 2rem; max-width: 600px; margin: 0 auto;">
            <h1>🔒 Access Denied</h1>
            <p>You need <strong>expert</strong> or <strong>admin</strong> permissions to access Flood Intelligence.</p>
            <p>This tool is designed for experts conducting coastal risk assessments.</p>
            <p><a href="/" style="color: #7BABAE;">← Back to Home</a></p>
        </body>
        </html>
        ''', 403

    # Get API base URL from environment
    api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")

    return render_template(
        'flood_intelligence.html',
        active_page='flood_intelligence',
        api_base_url=api_base_url,
        is_admin=is_admin(user_email)
    )

@app.route('/users')
@login_required
def users_page():
    """Global users management page — cached; label files read once per image per project."""
    users_list = []
    try:
        users_list = get_cached_team_users_list()
    except Exception as e:
        print(f"Error loading users: {e}")
        import traceback
        traceback.print_exc()

    team_stats = {
        'user_count': len(users_list),
        'assignment_count': sum(len(u['projects']) for u in users_list),
        'total_completed': sum(u['total_completed'] for u in users_list),
        'total_annotations': sum(u['total_annotations'] for u in users_list),
    }

    return render_template(
        'users_page.html',
        users=users_list,
        team_stats=team_stats,
        active_page='users',
    )

@app.route('/test-image')
def test_image():
    """Test page for debugging image loading"""
    return send_from_directory(APP_DIR, 'test_image_route.html')

@app.route('/project/<project_folder>/editor/<username>')
@app.route('/project/<project_folder>/editor/<username>/<int:image_index>')
@login_required
def editor(project_folder, username, image_index=None):
    """Expert annotation editor for a specific user in a project"""
    metadata = get_project(project_folder)
    if not metadata:
        return "Project not found", 404

    # Load project state
    state = load_project_state(project_folder)

    # Get user's images (both assigned and completed)
    # Try email first (new system), then name (legacy)
    user_data = state.get('users', {}).get(username, {})
    if not user_data:
        # Try to find by name if email not found (legacy support)
        auth_users = get_cached_all_users_with_roles()
        for user in auth_users:
            if user['name'] == username and user['email'] in state.get('users', {}):
                user_data = state['users'][user['email']]
                break

    assigned_images = user_data.get('assigned', [])
    completed_images = user_data.get('completed', [])

    # Combine assigned and completed (user can review completed work)
    all_user_images = list(set(assigned_images + completed_images))

    if not all_user_images:
        display_name = user_data.get('name', username)
        return f"No images for user '{display_name}'. Please assign images first.", 404

    # If no image_index provided, find first incomplete image
    if image_index is None:
        if assigned_images:
            # assigned_images contains images NOT yet completed
            first_incomplete = assigned_images[0]
            try:
                image_index = all_user_images.index(first_incomplete)
            except ValueError:
                image_index = 0
        else:
            # All completed or none assigned, go to first image
            image_index = 0

    # Validate image index
    if image_index < 0 or image_index >= len(all_user_images):
        image_index = 0

    # Get current image
    image_name = all_user_images[image_index]
    project_path = os.path.join(PROJECTS_DIR, project_folder)
    images_dir = os.path.join(project_path, 'images')
    labels_dir = os.path.join(project_path, 'labels')
    image_path = os.path.join(images_dir, image_name)

    if not os.path.exists(image_path):
        return f"Image not found: {image_name}", 404

    # Load all potential species for search from database
    all_real_species = []
    try:
        service = get_species_service()
        all_real_species = service.get_all_species()
    except Exception as e:
        print(f"Error loading species from database: {e}")
        # Fallback to species_list.json
        species_file = os.path.join(APP_DIR, 'data', 'species_list.json')
        if os.path.exists(species_file):
            with open(species_file, 'r') as f:
                data = json.load(f)
                all_real_species = data.get('real_species', [])

    # Load classes from project's data.yaml
    data_yaml_path = os.path.join(project_path, 'data.yaml')
    project_classes = []
    class_names = {}  # Map class_id to class_name

    if os.path.exists(data_yaml_path):
        import yaml
        with open(data_yaml_path, 'r') as f:
            yaml_data = yaml.safe_load(f)
            names = yaml_data.get('names', {})

            # Handle both dict and list formats
            if isinstance(names, dict):
                class_names = names
                for class_id, class_name in names.items():
                    project_classes.append({'code': class_name, 'name': class_name})
            elif isinstance(names, list):
                class_names = {i: name for i, name in enumerate(names)}
                for i, class_name in enumerate(names):
                    project_classes.append({'code': class_name, 'name': class_name})

    # class_list for editor: project classes first, then others for searchability
    class_list = project_classes.copy()
    seen_codes = {c.get('code') for c in project_classes if c.get('code')}
    for s in all_real_species:
        if s.get('code') not in seen_codes:
            class_list.append(s)
            seen_codes.add(s.get('code'))

    # If no data.yaml or it was empty, use all_real_species
    if not class_list:
        class_list = all_real_species

    # Load existing labels (if any)
    label_file = os.path.splitext(image_name)[0] + '.txt'
    label_path = os.path.join(labels_dir, label_file)
    boxes = []

    if os.path.exists(label_path):
        with open(label_path, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 5:
                    class_id = int(parts[0])
                    # Prefer species from 6th column if it exists
                    species = parts[5] if len(parts) >= 6 else class_names.get(class_id, "bird")
                    
                    boxes.append({
                        'class_id': class_id,
                        'x_center': float(parts[1]),
                        'y_center': float(parts[2]),
                        'width': float(parts[3]),
                        'height': float(parts[4]),
                        'species': species
                    })

    # Simple questions structure (can be expanded later)
    questions = [
        {
            "id": 0,
            "text": "Select the class",
            "type": "class_select"
        }
    ]

    # Navigation indices
    prev_index = image_index - 1 if image_index > 0 else None
    next_index = image_index + 1 if image_index < len(all_user_images) - 1 else None

    # URL encode the image name for proper URL handling
    from urllib.parse import quote
    image_url = f'/project/{project_folder}/image/{quote(image_name)}'

    # Debug logging
    import logging
    logging.info(f"Editor loading: {username} - {image_name}")
    logging.info(f"Image URL: {image_url}")
    logging.info(f"Total images: {len(all_user_images)}")
    logging.info(f"Loaded {len(class_list)} classes from data.yaml")

    return render_template('expert_editor.html',
                         username=username,
                         project_id=project_folder,  # Keep as project_id for template compatibility
                         image_name=image_name,
                         image_url=image_url,
                         current_index=image_index,
                         total_images=len(all_user_images),
                         prev_index=prev_index,
                         next_index=next_index,
                         boxes=boxes,
                         species_list=class_list,  # Keep as species_list for template compatibility
                         questions=questions,
                         back_url=f'/project/{project_folder}')

# ============================================================================
# API - PROJECT MANAGEMENT
# ============================================================================

@app.route('/api/projects/upload_chunk', methods=['POST'])
@api_annotator_required
def upload_chunk():
    """Receive and store a single chunk of a large file upload"""
    try:
        upload_id = request.form.get('upload_id')
        chunk_index = int(request.form.get('chunk_index'))
        total_chunks = int(request.form.get('total_chunks'))
        chunk_file = request.files.get('chunk')

        if not all([upload_id, chunk_file]) or chunk_index is None or total_chunks is None:
            return jsonify({'error': 'Missing required fields'}), 400

        # Create temp directory for this upload
        temp_upload_dir = os.path.join(PROJECTS_DIR, '.uploads', upload_id)
        os.makedirs(temp_upload_dir, exist_ok=True)

        # Save chunk
        chunk_path = os.path.join(temp_upload_dir, f'chunk_{chunk_index:06d}')
        chunk_file.save(chunk_path)

        return jsonify({
            'success': True,
            'chunk_index': chunk_index,
            'total_chunks': total_chunks
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/projects/assemble_and_create', methods=['POST'])
@api_annotator_required
def assemble_and_create():
    """Assemble uploaded chunks and create project"""
    import traceback
    import logging
    import yaml

    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)

    try:
        upload_id = request.form.get('upload_id')
        total_chunks = int(request.form.get('total_chunks'))
        original_filename = request.form.get('filename')
        name = request.form.get('name')
        description = request.form.get('description', '')

        logger.info("=" * 60)
        logger.info("ASSEMBLING CHUNKED UPLOAD")
        logger.info("=" * 60)
        logger.info(f"Upload ID: {upload_id}")
        logger.info(f"Total chunks: {total_chunks}")
        logger.info(f"Original file: {original_filename}")
        logger.info(f"Project name: {name}")

        if not all([upload_id, total_chunks, original_filename, name]):
            return jsonify({'error': 'Missing required fields'}), 400

        # Assemble chunks
        temp_upload_dir = os.path.join(PROJECTS_DIR, '.uploads', upload_id)
        if not os.path.exists(temp_upload_dir):
            return jsonify({'error': 'Upload not found'}), 404

        # Create temporary assembled file
        assembled_path = os.path.join(temp_upload_dir, original_filename)
        logger.info(f"Assembling {total_chunks} chunks into {assembled_path}")

        with open(assembled_path, 'wb') as outfile:
            for i in range(total_chunks):
                chunk_path = os.path.join(temp_upload_dir, f'chunk_{i:06d}')
                if not os.path.exists(chunk_path):
                    return jsonify({'error': f'Missing chunk {i}'}), 400

                with open(chunk_path, 'rb') as infile:
                    outfile.write(infile.read())

                # Delete chunk after adding to assembled file
                os.remove(chunk_path)

                if (i + 1) % 10 == 0:
                    logger.info(f"  Assembled {i + 1}/{total_chunks} chunks...")

        logger.info(f"All chunks assembled into {assembled_path}")

        # Now process the assembled file (reuse existing logic)
        project_folder = sanitize_folder_name(name)
        project_path = os.path.join(PROJECTS_DIR, project_folder)

        # Check if project already exists
        if os.path.exists(project_path):
            counter = 1
            while os.path.exists(f"{project_path}_{counter}"):
                counter += 1
            project_folder = f"{project_folder}_{counter}"
            project_path = os.path.join(PROJECTS_DIR, project_folder)

        # Create project directories
        os.makedirs(project_path, exist_ok=True)
        images_dir = os.path.join(project_path, 'images')
        labels_dir = os.path.join(project_path, 'labels')
        os.makedirs(images_dir, exist_ok=True)
        os.makedirs(labels_dir, exist_ok=True)
        logger.info("Project directories created")

        # Move assembled file to project directory
        temp_zip_path = os.path.join(project_path, 'temp.zip')
        shutil.move(assembled_path, temp_zip_path)
        logger.info("Moved assembled file to project directory")

        # Extract and process (reuse existing extraction logic)
        has_data_yaml = False
        has_project_state = False
        data_yaml_content = None
        project_state_content = None
        image_count = 0
        label_count = 0

        import time
        with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
            logger.info(f"Opened zip, contains {len(zip_ref.namelist())} files")

            # Analyze structure
            for file_info in zip_ref.namelist():
                if file_info.lower().endswith('.yaml') or file_info.lower().endswith('.yml'):
                    if not has_data_yaml:
                        has_data_yaml = True
                        data_yaml_content = zip_ref.read(file_info).decode('utf-8')
                        logger.info(f"Found {os.path.basename(file_info)}")
                elif file_info.endswith('project_state.json'):
                    has_project_state = True
                    project_state_content = zip_ref.read(file_info).decode('utf-8')
                    logger.info("Found project_state.json")

            import_type = 'full' if (has_data_yaml and has_project_state) else ('yolo' if has_data_yaml else ('partial' if has_project_state else 'new'))
            logger.info(f"📦 Import type: {import_type}")

            # Extract files
            logger.info("📤 Extracting files...")
            for file_info in zip_ref.namelist():
                if file_info.endswith('/') or '/.' in file_info or file_info.startswith('.'):
                    continue

                filename = os.path.basename(file_info)
                if not filename:
                    continue

                if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                    zip_ref.extract(file_info, project_path)
                    extracted_path = os.path.join(project_path, file_info)
                    dest_path = os.path.join(images_dir, filename)
                    shutil.move(extracted_path, dest_path)
                    image_count += 1
                    if image_count % 100 == 0:
                        logger.info(f"  Extracted {image_count} images...")

                elif filename.endswith('.txt') and 'classes.txt' not in filename:
                    zip_ref.extract(file_info, project_path)
                    extracted_path = os.path.join(project_path, file_info)
                    dest_path = os.path.join(labels_dir, filename)
                    shutil.move(extracted_path, dest_path)
                    label_count += 1

                elif (filename.lower().endswith('.yaml') or filename.lower().endswith('.yml')) and has_data_yaml:
                    with open(os.path.join(project_path, 'data.yaml'), 'w') as f:
                        f.write(data_yaml_content)

                elif filename == 'project_state.json' and has_project_state:
                    with open(os.path.join(project_path, 'project_state.json'), 'w') as f:
                        f.write(project_state_content)

                elif filename == 'classes.txt':
                    zip_ref.extract(file_info, project_path)
                    extracted_path = os.path.join(project_path, file_info)
                    shutil.move(extracted_path, os.path.join(project_path, 'classes.txt'))

            logger.info(f"Extracted {image_count} images, {label_count} labels")

            # Cleanup
            os.remove(temp_zip_path)
            for item in os.listdir(project_path):
                item_path = os.path.join(project_path, item)
                if os.path.isdir(item_path) and item not in ['images', 'labels']:
                    shutil.rmtree(item_path)

        # Create missing files
        if not has_data_yaml:
            data_yaml = {'path': '.', 'train': 'images', 'val': 'images', 'test': 'images', 'names': {0: 'Bird'}}
            save_data_yaml(project_folder, data_yaml)

        if not has_project_state:
            save_project_state(project_folder, {'users': {}})

        metadata = {
            'name': name,
            'description': description,
            'created_at': datetime.now().isoformat(),
            'import_type': import_type
        }
        save_project_metadata(project_folder, metadata)

        # Clean up upload directory
        shutil.rmtree(temp_upload_dir, ignore_errors=True)

        # Invalidate project cache since new project was created
        invalidate_project_cache()

        logger.info("Project created successfully")
        logger.info("=" * 60)

        return jsonify({
            'success': True,
            'project_folder': project_folder,
            'images_uploaded': image_count,
            'labels_uploaded': label_count,
            'users_imported': 0
        })

    except Exception as e:
        logger.error(f"Error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@app.route('/api/projects/create', methods=['POST'])
@api_annotator_required  # Only annotators and admins can create projects
def create_project():
    """Create a new project from a zip file with smart import detection"""
    import traceback
    import logging
    import yaml

    # Setup logging
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)

    try:
        logger.info("=" * 60)
        logger.info("PROJECT CREATION STARTED")
        logger.info("=" * 60)

        # Get content length to show upload size
        content_length = request.content_length
        if content_length:
            size_mb = content_length / (1024 * 1024)
            logger.info(f"📦 Upload size: {size_mb:.2f} MB ({content_length:,} bytes)")

        name = request.form.get('name')
        description = request.form.get('description', '')

        logger.info(f"Project name: {name}")
        logger.info(f"Description: {description}")

        if not name:
            logger.error("No project name provided")
            return jsonify({'error': 'Project name required'}), 400

        # Check for zip file
        logger.info("Receiving zip file from request...")
        zip_file = request.files.get('zip_file')
        if not zip_file:
            logger.error("No zip file provided")
            return jsonify({'error': 'Zip file required'}), 400

        if not zip_file.filename.lower().endswith('.zip'):
            logger.error(f"Invalid file type: {zip_file.filename}")
            return jsonify({'error': 'Only .zip files are accepted'}), 400

        logger.info(f"Received zip file: {zip_file.filename}")

        # Generate project folder name
        project_folder = sanitize_folder_name(name)
        project_path = os.path.join(PROJECTS_DIR, project_folder)

        # Check if project already exists
        if os.path.exists(project_path):
            # Add suffix to make unique
            counter = 1
            while os.path.exists(f"{project_path}_{counter}"):
                counter += 1
            project_folder = f"{project_folder}_{counter}"
            project_path = os.path.join(PROJECTS_DIR, project_folder)

        logger.info(f"Project folder: {project_folder}")
        logger.info(f"Project path: {project_path}")

        # Create project directory
        os.makedirs(project_path, exist_ok=True)
        images_dir = os.path.join(project_path, 'images')
        labels_dir = os.path.join(project_path, 'labels')
        os.makedirs(images_dir, exist_ok=True)
        os.makedirs(labels_dir, exist_ok=True)
        logger.info("Directories created")

        # Save and analyze zip
        temp_zip_path = os.path.join(project_path, 'temp.zip')
        logger.info(f"Saving zip file to disk (this may take a while for large files)...")

        # Save with progress logging
        import time
        start_time = time.time()
        zip_file.save(temp_zip_path)
        elapsed = time.time() - start_time

        # Get actual file size
        zip_size = os.path.getsize(temp_zip_path)
        zip_size_mb = zip_size / (1024 * 1024)
        logger.info(f"Saved zip to: {temp_zip_path}")
        logger.info(f"Zip file size: {zip_size_mb:.2f} MB, took {elapsed:.2f}s to save")

        # Analyze zip structure
        has_data_yaml = False
        has_project_state = False
        data_yaml_content = None
        project_state_content = None
        image_count = 0
        label_count = 0

        try:
            with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                logger.info(f"Opened zip, contains {len(zip_ref.namelist())} files")

                # First pass: detect structure
                for file_info in zip_ref.namelist():
                    # Check for any YAML file (could be data.yaml, dataset.yaml, etc.)
                    if file_info.lower().endswith('.yaml') or file_info.lower().endswith('.yml'):
                        if not has_data_yaml:  # Only take the first YAML found
                            has_data_yaml = True
                            data_yaml_content = zip_ref.read(file_info).decode('utf-8')
                            yaml_filename = os.path.basename(file_info)
                            logger.info(f"Found {yaml_filename} - this is a YOLO dataset import")
                    elif file_info.endswith('project_state.json') or file_info == 'project_state.json':
                        has_project_state = True
                        project_state_content = zip_ref.read(file_info).decode('utf-8')
                        logger.info("Found project_state.json - importing user assignments")

                # Determine import type
                if has_data_yaml and has_project_state:
                    import_type = 'full'
                    logger.info("📦 Import type: FULL (has data.yaml + project_state.json)")
                elif has_data_yaml:
                    import_type = 'yolo'
                    logger.info("📦 Import type: YOLO (has data.yaml)")
                elif has_project_state:
                    import_type = 'partial'
                    logger.info("📦 Import type: PARTIAL (has project_state.json)")
                else:
                    import_type = 'new'
                    logger.info("📦 Import type: NEW (fresh dataset)")

                # Second pass: extract files
                logger.info(f"📦 Starting extraction of {len(zip_ref.namelist())} files...")
                extraction_start = time.time()

                for file_info in zip_ref.namelist():
                    # Skip directories and hidden files
                    if file_info.endswith('/') or '/.' in file_info or file_info.startswith('.'):
                        continue

                    filename = os.path.basename(file_info)
                    if not filename:
                        continue

                    # Extract images
                    if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                        zip_ref.extract(file_info, project_path)
                        extracted_path = os.path.join(project_path, file_info)
                        dest_path = os.path.join(images_dir, filename)
                        shutil.move(extracted_path, dest_path)
                        image_count += 1
                        if image_count % 100 == 0:
                            logger.info(f"  Extracted {image_count} images...")

                    # Extract labels
                    elif filename.endswith('.txt') and 'classes.txt' not in filename:
                        zip_ref.extract(file_info, project_path)
                        extracted_path = os.path.join(project_path, file_info)
                        dest_path = os.path.join(labels_dir, filename)
                        shutil.move(extracted_path, dest_path)
                        label_count += 1
                        if label_count % 100 == 0 and label_count > 0:
                            logger.info(f"  Extracted {label_count} labels...")

                    # Extract YAML file (rename to data.yaml for consistency)
                    elif (filename.lower().endswith('.yaml') or filename.lower().endswith('.yml')) and has_data_yaml:
                        dest_path = os.path.join(project_path, 'data.yaml')
                        with open(dest_path, 'w') as f:
                            f.write(data_yaml_content)
                        logger.info(f"Preserved {filename} as data.yaml")

                    # Extract project_state.json
                    elif filename == 'project_state.json' and has_project_state:
                        dest_path = os.path.join(project_path, 'project_state.json')
                        with open(dest_path, 'w') as f:
                            f.write(project_state_content)
                        logger.info("Preserved project_state.json")

                    # Extract classes.txt if present
                    elif filename == 'classes.txt':
                        dest_path = os.path.join(project_path, 'classes.txt')
                        zip_ref.extract(file_info, project_path)
                        extracted_path = os.path.join(project_path, file_info)
                        shutil.move(extracted_path, dest_path)
                        logger.info("Preserved classes.txt")

                extraction_elapsed = time.time() - extraction_start
                logger.info(f"Extracted {image_count} images, {label_count} labels from zip in {extraction_elapsed:.2f}s")

                # Clean up temp files
                logger.info("🧹 Cleaning up temporary files...")
                os.remove(temp_zip_path)
                # Remove any extracted directories
                for item in os.listdir(project_path):
                    item_path = os.path.join(project_path, item)
                    if os.path.isdir(item_path) and item not in ['images', 'labels']:
                        shutil.rmtree(item_path)

        except Exception as zip_error:
            logger.error(f"Error processing zip: {zip_error}")
            logger.error(traceback.format_exc())
            raise

        # Create or preserve data.yaml
        if not has_data_yaml:
            logger.info("Creating default data.yaml...")
            data_yaml = {
                'path': '.',
                'train': 'images',
                'val': 'images',
                'test': 'images',
                'names': {0: 'Bird'}
            }
            save_data_yaml(project_folder, data_yaml)
            logger.info("Created data.yaml with default class (Bird)")

        # Create or preserve project_state.json
        if not has_project_state:
            logger.info("Creating empty project_state.json...")
            project_state = {'users': {}}
            save_project_state(project_folder, project_state)
            logger.info("Created empty project_state.json")

        # Create metadata.json
        logger.info("Creating metadata.json...")
        metadata = {
            'name': name,
            'description': description,
            'created_at': datetime.now().isoformat(),
            'import_type': import_type
        }
        save_project_metadata(project_folder, metadata)
        logger.info("Created metadata.json")

        # Count imported users
        users_imported = 0
        if has_project_state:
            state = load_project_state(project_folder)
            users_imported = len(state.get('users', {}))

        logger.info("=" * 60)
        logger.info("PROJECT CREATION SUCCESS")
        logger.info(f"  Project folder: {project_folder}")
        logger.info(f"  Images: {image_count}")
        logger.info(f"  Labels: {label_count}")
        logger.info(f"  Import type: {import_type}")
        logger.info(f"  Users: {users_imported}")
        logger.info("=" * 60)

        return jsonify({
            'success': True,
            'project_folder': project_folder,
            'images_uploaded': image_count,
            'labels_uploaded': label_count,
            'users_imported': users_imported,
            'import_type': import_type
        })

    except Exception as e:
        logger.error("=" * 60)
        logger.error("PROJECT CREATION FAILED")
        logger.error(f"Error: {str(e)}")
        logger.error("Traceback:")
        logger.error(traceback.format_exc())
        logger.error("=" * 60)
        return jsonify({'error': f'{type(e).__name__}: {str(e)}'}), 500

@app.route('/api/projects/assign-task', methods=['POST'])
@login_required  # Any authenticated user can assign tasks
def assign_task():
    """
    Smart image assignment with random selection.

    Features:
    - Random selection from unassigned pool
    - Can add more images to existing users
    - Uses centralized user registry
    - Tracks assignment across projects
    """
    try:
        import random

        data = request.json
        project_folder = data.get('project_id')
        # Support both email (new) and username (legacy) parameters
        user_email = data.get('user_email') or data.get('username')
        num_images = data.get('num_images', 10)
        allow_reassign = data.get('allow_reassign', False)  # Allow taking assigned images

        if not user_email:
            return jsonify({'error': 'User email required'}), 400

        # Get user info from auth system (cached user list)
        auth_users = {u['email']: u for u in get_cached_all_users_with_roles()}

        # If username was provided instead of email, try to find the email
        if '@' not in user_email:
            # Legacy: username provided, find matching email
            matching_users = [u for u in auth_users.values() if u['name'] == user_email]
            if not matching_users:
                return jsonify({'error': f'User not found: {user_email}'}), 404
            if len(matching_users) > 1:
                return jsonify({'error': f'Multiple users with name "{user_email}". Please use email instead.'}), 400
            user_email = matching_users[0]['email']

        user_name = auth_users.get(user_email, {}).get('name', user_email)

        metadata = get_project(project_folder)
        if not metadata:
            return jsonify({'error': 'Project not found'}), 404

        # Get all images in project
        images_dir = os.path.join(PROJECTS_DIR, project_folder, 'images')
        all_images = [f for f in os.listdir(images_dir)
                     if f.lower().endswith(('.jpg', '.jpeg', '.png'))]

        if not all_images:
            return jsonify({'error': 'No images in project'}), 400

        # Load project state
        state = load_project_state(project_folder)

        # Get already assigned images
        assigned_images = set()
        for user_data in state.get('users', {}).values():
            assigned_images.update(user_data.get('assigned', []))

        # Get user's current assignments (using EMAIL as key)
        user_current = set()
        if user_email in state.get('users', {}):
            user_current = set(state['users'][user_email].get('assigned', []))

        # Determine selection pool
        if allow_reassign:
            # Can select from all images
            available = [img for img in all_images if img not in user_current]
            selection_type = "all images (including assigned to others)"
        else:
            # Only unassigned images
            unassigned = [img for img in all_images if img not in assigned_images]
            available = unassigned
            selection_type = "unassigned images only"

        # Calculate statistics for better feedback
        total_images = len(all_images)
        total_assigned = len(assigned_images)
        total_unassigned = total_images - total_assigned
        user_already_has = len(user_current)

        if not available:
            if allow_reassign:
                return jsonify({
                    'error': f'All {total_images} images already assigned to {user_name}'
                }), 400
            else:
                return jsonify({
                    'error': f'No unassigned images available. {total_assigned}/{total_images} images are already assigned to other users. Enable "Allow Reassignment" to assign already-assigned images.'
                }), 400

        # Random selection
        num_to_assign = min(num_images, len(available))
        to_assign = random.sample(available, num_to_assign)

        # Initialize user in project state if needed (using EMAIL as key)
        if 'users' not in state:
            state['users'] = {}
        if user_email not in state['users']:
            state['users'][user_email] = {
                'name': user_name,  # Store name for display purposes
                'assigned': [],
                'completed': []
            }

        # Add new assignments (avoid duplicates)
        current_assigned = set(state['users'][user_email]['assigned'])
        new_assignments = [img for img in to_assign if img not in current_assigned]
        state['users'][user_email]['assigned'].extend(new_assignments)

        # Save project state
        save_project_state(project_folder, state)
        invalidate_project_cache(project_folder)

        # Update global user registry (still uses name for legacy reasons)
        user_service = get_user_service()
        if user_service:
            try:
                # Create user if doesn't exist
                if not user_service.get_user(user_name):
                    user_service.create_user(user_name)

                # Add project to user's project list
                user_service.add_user_to_project(user_name, project_folder)
            except Exception as e:
                print(f"Warning: Could not update user service: {e}")

        return jsonify({
            'success': True,
            'assigned': len(new_assignments),
            'total_assigned': len(state['users'][user_email]['assigned']),
            'total_images': total_images,
            'total_unassigned': total_unassigned,
            'available': len(available),
            'selection_type': selection_type,
            'message': f'Assigned {len(new_assignments)} new image(s) to {user_name}. Total: {len(state["users"][user_email]["assigned"])}/{total_images} images. Unassigned remaining: {total_unassigned - len(new_assignments)}'
        })

    except Exception as e:
        import traceback
        print(f"Error in assign_task: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects/<project_folder>/remove-user', methods=['POST'])
@login_required
def remove_user_from_project(project_folder):
    """
    Remove a user from a project (unassign all their images).

    This removes the user from project_state.json but KEEPS any label files
    they created. Use this to fix bad assignments or remove inactive users.
    """
    try:
        data = request.json
        user_email = data.get('user_email')

        if not user_email:
            return jsonify({'error': 'User email required'}), 400

        metadata = get_project(project_folder)
        if not metadata:
            return jsonify({'error': 'Project not found'}), 404

        # Load project state
        state = load_project_state(project_folder)

        # Check if user exists in project
        if user_email not in state.get('users', {}):
            return jsonify({'error': f'User not found in project'}), 404

        # Get user info for logging
        user_data = state['users'][user_email]
        user_name = user_data.get('name', user_email)
        assigned_count = len(user_data.get('assigned', []))
        completed_count = len(user_data.get('completed', []))

        # Remove user from project
        del state['users'][user_email]

        # Save updated state
        save_project_state(project_folder, state)
        invalidate_project_cache(project_folder)

        return jsonify({
            'success': True,
            'message': f'Removed {user_name} from project',
            'removed': {
                'name': user_name,
                'email': user_email,
                'assigned': assigned_count,
                'completed': completed_count
            }
        })

    except Exception as e:
        import traceback
        print(f"Error removing user from project: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects/<project_folder>/sync', methods=['POST'])
@admin_required  # Only admins can sync project data
def api_sync_project_data(project_folder):
    """
    Synchronize images and labels for a project.

    Ensures data hygiene by:
    1. Deleting labels without matching images (orphaned labels)
    2. Creating empty labels for images without labels

    This endpoint is admin-only to prevent accidental data loss.
    """
    try:
        # Verify project exists
        metadata = get_project(project_folder)
        if not metadata:
            return jsonify({'error': 'Project not found'}), 404

        # Run sync
        result = sync_project_labels_images(project_folder)

        return jsonify({
            'success': True,
            'project': project_folder,
            'deleted_labels': result['deleted_labels'],
            'created_labels': result['created_labels'],
            'errors': result['errors'],
            'summary': {
                'deleted_count': result['deleted_count'],
                'created_count': result['created_count'],
                'error_count': result['error_count']
            }
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects/<project_folder>/delete', methods=['DELETE'])
@admin_required  # CRITICAL: Only admins can delete projects!
def delete_project(project_folder):
    """
    Delete an entire project permanently.

    Deletes:
    - All images
    - All labels
    - Project metadata
    - Project state
    - User assignments
    """
    try:
        import logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        logger.info(f"Delete project request: {project_folder}")

        # Verify project exists
        metadata = get_project(project_folder)
        if not metadata:
            return jsonify({'error': 'Project not found'}), 404

        project_path = os.path.join(PROJECTS_DIR, project_folder)

        # Get stats before deletion for logging
        stats = calculate_project_stats(project_folder)
        logger.info(f"Deleting project with {stats['total_images']} images, {stats['total_annotations']} annotations")

        # Remove project from global users registry
        user_service = get_user_service()
        if user_service:
            try:
                state = load_project_state(project_folder)
                project_users = list(state.get('users', {}).keys())

                # Update each user's project list
                with open(user_service.users_file, 'r') as f:
                    users_data = json.load(f)

                for user in users_data.get('users', []):
                    if project_folder in user.get('projects', []):
                        user['projects'].remove(project_folder)
                        logger.info(f"Removed project from user: {user['name']}")

                # Save updated users registry
                with open(user_service.users_file, 'w') as f:
                    json.dump(users_data, f, indent=2)

                logger.info(f"Updated {len(project_users)} user(s) in global registry")

            except Exception as e:
                logger.warning(f"Could not update users registry: {e}")
                # Continue with deletion even if user update fails

        # Delete the entire project directory
        if os.path.exists(project_path):
            shutil.rmtree(project_path)
            logger.info(f"Deleted project directory: {project_path}")
        else:
            logger.warning(f"Project directory not found: {project_path}")

        # Invalidate all project caches since we deleted a project
        invalidate_project_cache()

        return jsonify({
            'success': True,
            'message': f'Project "{metadata["name"]}" deleted successfully',
            'deleted': {
                'images': stats['total_images'],
                'annotations': stats['total_annotations'],
                'users': len(project_users) if user_service else 0
            }
        })

    except Exception as e:
        import traceback
        print(f"Error deleting project: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

def _list_project_image_files(images_dir):
    """Return sorted image filenames (jpg/png/webp/bmp/tiff)."""
    if not os.path.isdir(images_dir):
        return []
    exts = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff')
    return sorted(f for f in os.listdir(images_dir) if f.lower().endswith(exts))

def _get_image_size_wh(image_path):
    """Return (width, height) for COCO / GeoJSON pixel math."""
    from PIL import Image
    with Image.open(image_path) as im:
        return im.size

def _parse_yolo_label_line(line):
    line = line.strip()
    if not line or line.startswith('#'):
        return None
    parts = line.split()
    if len(parts) < 5:
        return None
    try:
        class_id = int(float(parts[0]))
        xc, yc, w, h = map(float, parts[1:5])
        species = ' '.join(parts[5:]) if len(parts) > 5 else None
        return {'class_id': class_id, 'xc': xc, 'yc': yc, 'w': w, 'h': h, 'species': species}
    except (ValueError, TypeError):
        return None

def _coco_categories_from_yaml(data_yaml):
    """Build COCO categories list from data.yaml names (ids must match label files)."""
    if not data_yaml:
        return [{'id': 0, 'name': 'object'}]
    names = data_yaml.get('names')
    cats = []
    if isinstance(names, dict):
        for k, v in sorted(names.items(), key=lambda x: int(x[0])):
            cats.append({'id': int(k), 'name': str(v)})
    elif isinstance(names, list):
        for i, v in enumerate(names):
            cats.append({'id': i, 'name': str(v)})
    return cats if cats else [{'id': 0, 'name': 'object'}]

def _yolo_norm_to_coco_bbox(parsed, img_w, img_h):
    """YOLO normalized xywh -> COCO bbox [x, y, width, height] in pixels."""
    xc, yc, bw, bh = parsed['xc'], parsed['yc'], parsed['w'], parsed['h']
    px_w = bw * img_w
    px_h = bh * img_h
    px_xc = xc * img_w
    px_yc = yc * img_h
    x0 = px_xc - px_w / 2.0
    y0 = px_yc - px_h / 2.0
    x0 = max(0.0, min(x0, float(img_w) - 1.0))
    y0 = max(0.0, min(y0, float(img_h) - 1.0))
    bw_px = max(1.0, min(px_w, float(img_w) - x0))
    bh_px = max(1.0, min(px_h, float(img_h) - y0))
    return [round(x0, 2), round(y0, 2), round(bw_px, 2), round(bh_px, 2)]

def _merge_georeference_dict(merged, data):
    if not data:
        return
    db = data.get('default_bounds')
    if db and len(db) == 4:
        merged['default_bounds'] = [float(db[0]), float(db[1]), float(db[2]), float(db[3])]
    for name, entry in (data.get('images') or {}).items():
        merged['images'][name] = entry

def _load_georeference_map(project_path, metadata):
    """
    Georeference sources (merged): georeference.json in project folder, then metadata['georeference'].
    Each image may have {'bounds': [west, south, east, north]} in WGS84 (EPSG:4326).
    Optional top-level 'default_bounds' applies to any image without an entry.
    """
    merged = {'default_bounds': None, 'images': {}}
    gpath = os.path.join(project_path, 'georeference.json')
    if os.path.isfile(gpath):
        with open(gpath, 'r') as f:
            _merge_georeference_dict(merged, json.load(f))
    if metadata.get('georeference'):
        _merge_georeference_dict(merged, metadata['georeference'])
    return merged

def _bounds_for_image(geo_map, filename):
    """Return [west, south, east, north] or None."""
    entry = geo_map['images'].get(filename)
    if isinstance(entry, dict) and entry.get('bounds') and len(entry['bounds']) == 4:
        b = entry['bounds']
        return [float(b[0]), float(b[1]), float(b[2]), float(b[3])]
    if geo_map['default_bounds'] and len(geo_map['default_bounds']) == 4:
        return list(geo_map['default_bounds'])
    return None

def _pixel_box_corners_to_geo_ring(x0, y0, x1, y1, img_w, img_h, bounds):
    """
    Map axis-aligned pixel box to GeoJSON polygon ring (WGS84).
    Image origin top-left; bounds map top edge to north lat and bottom to south.
    """
    west, south, east, north = bounds

    def px_to_lonlat(px, py):
        lon = west + (px / float(img_w)) * (east - west)
        lat = north - (py / float(img_h)) * (north - south)
        return [lon, lat]

    tl = px_to_lonlat(x0, y0)
    tr = px_to_lonlat(x1, y0)
    br = px_to_lonlat(x1, y1)
    bl = px_to_lonlat(x0, y1)
    return [tl, tr, br, bl, tl]

@app.route('/api/projects/<project_folder>/export/<format>')
def export_project(project_folder, format):
    """Export project annotations in YOLO, COCO, or GeoJSON."""
    try:
        metadata = get_project(project_folder)
        if not metadata:
            return jsonify({'error': 'Project not found'}), 404

        project_path = os.path.join(PROJECTS_DIR, project_folder)
        images_dir = os.path.join(project_path, 'images')
        labels_dir = os.path.join(project_path, 'labels')

        if format == 'yolo':
            image_files = _list_project_image_files(images_dir)
            if not image_files:
                return jsonify({'error': 'No images found in project (expected images/ with jpg/png/…).'}), 400

            zip_path = os.path.join(project_path, f'{project_folder}_yolo.zip')
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for img in image_files:
                    zipf.write(os.path.join(images_dir, img), f'images/{img}')

                if os.path.isdir(labels_dir):
                    for label in os.listdir(labels_dir):
                        if not label.startswith('.'):
                            zipf.write(os.path.join(labels_dir, label), f'labels/{label}')

                data_yaml_path = os.path.join(project_path, 'data.yaml')
                if os.path.exists(data_yaml_path):
                    zipf.write(data_yaml_path, 'data.yaml')

                state_path = os.path.join(project_path, 'project_state.json')
                if os.path.exists(state_path):
                    zipf.write(state_path, 'project_state.json')

                metadata_path = os.path.join(project_path, 'metadata.json')
                if os.path.exists(metadata_path):
                    zipf.write(metadata_path, 'metadata.json')

            return send_file(zip_path, as_attachment=True, download_name=f'{project_folder}_yolo.zip')

        elif format == 'geojson':
            geo_map = _load_georeference_map(project_path, metadata)
            image_files = _list_project_image_files(images_dir)
            if not image_files:
                return jsonify({'error': 'No images found for GeoJSON export.'}), 400

            features = []
            ann_id = 0
            for img_name in image_files:
                bounds = _bounds_for_image(geo_map, img_name)
                if not bounds:
                    continue

                label_file = os.path.splitext(img_name)[0] + '.txt'
                label_path = os.path.join(labels_dir, label_file)
                if not os.path.isfile(label_path):
                    continue

                img_path = os.path.join(images_dir, img_name)
                try:
                    img_w, img_h = _get_image_size_wh(img_path)
                except Exception:
                    continue

                with open(label_path, 'r') as lf:
                    for line in lf:
                        parsed = _parse_yolo_label_line(line)
                        if not parsed:
                            continue
                        xc, yc, bw, bh = parsed['xc'], parsed['yc'], parsed['w'], parsed['h']
                        x0 = (xc - bw / 2.0) * img_w
                        y0 = (yc - bh / 2.0) * img_h
                        x1 = (xc + bw / 2.0) * img_w
                        y1 = (yc + bh / 2.0) * img_h
                        ring = _pixel_box_corners_to_geo_ring(x0, y0, x1, y1, img_w, img_h, bounds)
                        ann_id += 1
                        features.append({
                            'type': 'Feature',
                            'id': ann_id,
                            'geometry': {'type': 'Polygon', 'coordinates': [ring]},
                            'properties': {
                                'image': img_name,
                                'class_id': parsed['class_id'],
                                'species': parsed.get('species'),
                            }
                        })

            if not features:
                return jsonify({
                    'error': 'No geographic bounds for this project, or no labels with matching georeference.',
                    'hint': 'Add georeference.json (or metadata.georeference) with default_bounds or per-image bounds [west, south, east, north] in WGS84.'
                }), 400

            geojson = {
                'type': 'FeatureCollection',
                'name': metadata.get('name', project_folder),
                'features': features
            }

            zip_path = os.path.join(project_path, f'{project_folder}_geojson.zip')
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.writestr('annotations.geojson', json.dumps(geojson, indent=2))
            return send_file(zip_path, as_attachment=True, download_name=f'{project_folder}_geojson.zip')

        elif format == 'coco':
            data_yaml = load_data_yaml(project_folder)
            categories = _coco_categories_from_yaml(data_yaml)
            cat_ids = {c['id'] for c in categories}

            image_files = _list_project_image_files(images_dir)
            if not image_files:
                return jsonify({'error': 'No images found for COCO export.'}), 400

            coco = {
                'info': {
                    'description': metadata.get('name', project_folder),
                    'date_created': metadata.get('created_at', ''),
                    'version': '1.0'
                },
                'licenses': [],
                'images': [],
                'annotations': [],
                'categories': categories
            }

            image_id = 0
            ann_id = 0
            for img_name in image_files:
                img_path = os.path.join(images_dir, img_name)
                try:
                    img_w, img_h = _get_image_size_wh(img_path)
                except Exception as e:
                    return jsonify({'error': f'Could not read image {img_name}: {e}'}), 500

                image_id += 1
                coco['images'].append({
                    'id': image_id,
                    'file_name': img_name,
                    'width': img_w,
                    'height': img_h
                })

                label_file = os.path.splitext(img_name)[0] + '.txt'
                label_path = os.path.join(labels_dir, label_file)
                if not os.path.isfile(label_path):
                    continue

                with open(label_path, 'r') as lf:
                    for line in lf:
                        parsed = _parse_yolo_label_line(line)
                        if not parsed:
                            continue
                        cid = parsed['class_id']
                        if cid not in cat_ids:
                            categories.append({'id': cid, 'name': f'class_{cid}'})
                            cat_ids.add(cid)
                            coco['categories'] = categories

                        bbox = _yolo_norm_to_coco_bbox(parsed, img_w, img_h)
                        area = bbox[2] * bbox[3]
                        ann_id += 1
                        coco['annotations'].append({
                            'id': ann_id,
                            'image_id': image_id,
                            'category_id': cid,
                            'bbox': bbox,
                            'area': round(area, 2),
                            'iscrowd': 0
                        })

            zip_path = os.path.join(project_path, f'{project_folder}_coco.zip')
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.writestr('annotations.json', json.dumps(coco, indent=2))
                for img_name in image_files:
                    zipf.write(os.path.join(images_dir, img_name), f'images/{img_name}')

            return send_file(zip_path, as_attachment=True, download_name=f'{project_folder}_coco.zip')

        else:
            return jsonify({'error': 'Unsupported format'}), 400

    except Exception as e:
        import traceback
        print(f"Export error: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# COMPATIBILITY ROUTES (for existing editor)
# ============================================================================

@app.route('/project/<project_folder>/image/<path:filename>')
def serve_project_image(project_folder, filename):
    """Serve image from a specific project"""
    import logging
    logging.info(f"[IMAGE REQUEST] project={project_folder}, filename={filename}")

    images_dir = os.path.join(PROJECTS_DIR, project_folder, 'images')
    full_path = os.path.join(images_dir, filename)

    logging.info(f"[IMAGE REQUEST] Looking for: {full_path}")
    logging.info(f"[IMAGE REQUEST] Exists: {os.path.exists(full_path)}")

    if os.path.exists(full_path):
        logging.info(f"[IMAGE REQUEST] Serving {filename}")
        return send_from_directory(images_dir, filename)

    logging.error(f"[IMAGE REQUEST] ✗ Not found: {full_path}")
    return jsonify({'error': 'Image not found', 'path': full_path}), 404

@app.route('/images/<path:filename>')
def serve_image(filename):
    """Serve images from any project (legacy route)"""
    # Try to find image in any project
    if os.path.exists(PROJECTS_DIR):
        for project_folder in os.listdir(PROJECTS_DIR):
            images_dir = os.path.join(PROJECTS_DIR, project_folder, 'images')
            if os.path.exists(os.path.join(images_dir, filename)):
                return send_from_directory(images_dir, filename)

    return jsonify({'error': 'Image not found'}), 404

@app.route('/api/save_annotations', methods=['POST'])
@api_annotator_required
def save_annotations():
    """Save annotations for an image"""
    try:
        data = request.json
        project_folder = data.get('project_id')  # Still called project_id in frontend
        username = data.get('username')
        image_name = data.get('image_name')
        boxes = data.get('boxes', [])

        if not all([project_folder, username, image_name]):
            return jsonify({'error': 'Missing required fields'}), 400

        # Save labels
        labels_dir = os.path.join(PROJECTS_DIR, project_folder, 'labels')
        label_file = os.path.splitext(image_name)[0] + '.txt'
        label_path = os.path.join(labels_dir, label_file)

        with open(label_path, 'w') as f:
            for box in boxes:
                # YOLO format: class_id x_center y_center width height [species]
                # Ensure class_id is always 0 (not None)
                class_id = box.get('class_id') or 0
                x_center = box.get('x_center', box.get('x', 0))
                y_center = box.get('y_center', box.get('y', 0))
                width = box.get('width', 0)
                height = box.get('height', 0)
                species = box.get('species')

                # Only include species if it's actually set (not None/empty)
                if species:
                    line = f"{class_id} {x_center} {y_center} {width} {height} {species}"
                else:
                    # No species assigned - just save bbox coordinates
                    line = f"{class_id} {x_center} {y_center} {width} {height}"
                f.write(line + '\n')

        # Update data.yaml with new species (if any)
        species_in_boxes = set()
        for box in boxes:
            species = box.get('species')
            if species:  # Only add non-empty species
                species_in_boxes.add(species)

        if species_in_boxes:
            # Load current data.yaml
            data_yaml = load_data_yaml(project_folder)
            if not data_yaml:
                # Create default data.yaml if it doesn't exist
                data_yaml = {
                    'path': '.',
                    'train': 'images',
                    'val': 'images',
                    'test': 'images',
                    'names': {0: 'Bird'}
                }

            # Get existing class names (convert keys to int if they're strings)
            names = data_yaml.get('names', {})
            # Normalize to {int: str} format
            names_normalized = {}
            if isinstance(names, dict):
                for k, v in names.items():
                    names_normalized[int(k)] = v
            elif isinstance(names, list):
                for i, v in enumerate(names):
                    names_normalized[i] = v

            # Find species codes that exist in names values
            existing_species = set(names_normalized.values())

            # Find new species to add
            new_species = species_in_boxes - existing_species

            if new_species:
                # Get next available class ID
                max_class_id = max(names_normalized.keys()) if names_normalized else -1
                next_class_id = max_class_id + 1

                # Add new species
                for species_code in sorted(new_species):  # Sort for consistency
                    names_normalized[next_class_id] = species_code
                    print(f"Added new species to data.yaml: {next_class_id} -> {species_code}")
                    next_class_id += 1

                # Update data.yaml
                data_yaml['names'] = names_normalized
                data_yaml['nc'] = len(names_normalized)
                save_data_yaml(project_folder, data_yaml)
                print(f"Updated data.yaml with {len(new_species)} new species. New nc: {data_yaml['nc']}")

        # Update user progress
        state = load_project_state(project_folder)

        # Find user by email (new) or username (legacy)
        user_key = None
        if '@' in username:
            # Email provided
            user_key = username if username in state.get('users', {}) else None
        else:
            # Username provided (legacy) - try to find email
            user_key = username if username in state.get('users', {}) else None
            if not user_key:
                # Try to map username to email
                auth_users = get_cached_all_users_with_roles()
                for user in auth_users:
                    if user['name'] == username and user['email'] in state.get('users', {}):
                        user_key = user['email']
                        break

        if user_key:
            user_data = state['users'][user_key]
            completed = user_data.get('completed', [])
            if image_name not in completed:
                completed.append(image_name)
                user_data['completed'] = completed
                save_project_state(project_folder, state)

        # Invalidate cache since project stats changed
        invalidate_project_cache(project_folder)

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/get_project_classes', methods=['POST'])
@api_annotator_required
def get_project_classes():
    """Get updated class list from project's data.yaml"""
    try:
        data = request.json
        project_folder = data.get('project_id')

        if not project_folder:
            return jsonify({'error': 'Missing project_id'}), 400

        # Load data.yaml
        data_yaml = load_data_yaml(project_folder)
        if not data_yaml:
            return jsonify({'classes': []})

        # Get class names
        names = data_yaml.get('names', {})

        # Convert to list format expected by frontend
        class_list = []
        if isinstance(names, dict):
            for class_id, class_name in names.items():
                class_list.append({
                    'id': int(class_id),
                    'code': class_name,
                    'name': class_name
                })
        elif isinstance(names, list):
            for i, class_name in enumerate(names):
                class_list.append({
                    'id': i,
                    'code': class_name,
                    'name': class_name
                })

        return jsonify({'classes': class_list})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users', methods=['GET'])
@api_login_required
def get_all_users():
    """Get all authenticated users who can be assigned to tasks"""
    try:
        # Get all logged-in users from authentication system
        auth_users = get_cached_all_users_with_roles()

        # Filter to only include annotators and admins (can annotate)
        # Count projects for each user
        projects = get_all_projects()  # Function defined in this file

        users = []
        for u in auth_users:
            if not u['can_annotate']:
                continue

            # Count how many projects this user is in
            project_count = 0
            for proj in projects:
                state = load_project_state(proj['folder'])
                # Check by email (new) or name (legacy)
                if u['email'] in state.get('users', {}) or u['name'] in state.get('users', {}):
                    project_count += 1

            users.append({
                'name': u['name'],
                'email': u['email'],
                'picture': u['picture'],
                'role': u['role'],
                'can_annotate': u['can_annotate'],
                'project_count': project_count
            })

        return jsonify({'users': users})

    except Exception as e:
        print(f"Error getting users: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/create', methods=['POST'])
@admin_required  # Only admins can access this endpoint
def create_user():
    """
    DEPRECATED: Manual user creation is disabled.
    Users are automatically created when they sign in with Google OAuth.
    """
    return jsonify({
        'error': 'Manual user creation is disabled',
        'message': 'Users are automatically created when they sign in with Google OAuth. Please direct users to sign in at /login.'
    }), 403

@app.route('/api/projects/<project_folder>/images/unassigned', methods=['GET'])
@api_login_required  # Require authentication to view project info
def get_unassigned_images(project_folder):
    """Get count of unassigned images in a project"""
    try:
        metadata = get_project(project_folder)
        if not metadata:
            return jsonify({'error': 'Project not found'}), 404

        # Get all images
        images_dir = os.path.join(PROJECTS_DIR, project_folder, 'images')
        all_images = [f for f in os.listdir(images_dir)
                     if f.lower().endswith(('.jpg', '.jpeg', '.png'))]

        # Get assigned images
        state = load_project_state(project_folder)
        assigned_images = set()
        for user_data in state.get('users', {}).values():
            assigned_images.update(user_data.get('assigned', []))

        # Calculate unassigned
        unassigned_count = len([img for img in all_images if img not in assigned_images])

        return jsonify({
            'total_images': len(all_images),
            'assigned_images': len(assigned_images),
            'unassigned_images': unassigned_count
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/correction/upload', methods=['POST'])
def upload_correction():
    """
    Upload an image with initial detections for expert correction.
    All corrections are saved to the 'corrections' project.

    This endpoint is called by NestVision's "Train with Experts" button.
    """
    import base64
    import time

    try:
        data = request.get_json()

        if not data or 'image_base64' not in data:
            return jsonify({'error': 'No image data provided'}), 400

        # Decode image
        image_data = base64.b64decode(data['image_base64'])
        detections = data.get('detections', [])

        # Ensure 'corrections' project exists
        corrections_folder = 'corrections'
        corrections_path = os.path.join(PROJECTS_DIR, corrections_folder)

        if not os.path.exists(corrections_path):
            # Create corrections project
            os.makedirs(corrections_path, exist_ok=True)
            os.makedirs(os.path.join(corrections_path, 'images'), exist_ok=True)
            os.makedirs(os.path.join(corrections_path, 'labels'), exist_ok=True)

            # Create metadata
            metadata = {
                'name': 'Corrections',
                'description': 'Expert corrections and refinements from NestVision',
                'created_at': datetime.now().isoformat()
            }
            save_project_metadata(corrections_folder, metadata)

            # Create data.yaml with default bird class
            import yaml
            data_yaml = {
                'path': corrections_path,
                'train': 'images',
                'val': 'images',
                'names': {0: 'bird'}
            }
            with open(os.path.join(corrections_path, 'data.yaml'), 'w') as f:
                yaml.dump(data_yaml, f, default_flow_style=False)

            # Initialize project state
            save_project_state(corrections_folder, {'users': {}})

        # Generate unique filename with timestamp
        timestamp = int(time.time() * 1000)  # milliseconds
        image_filename = f"correction_{timestamp}.jpg"

        # Save image
        image_path = os.path.join(corrections_path, 'images', image_filename)
        with open(image_path, 'wb') as f:
            f.write(image_data)

        # Save detections as YOLO labels
        label_filename = f"correction_{timestamp}.txt"
        label_path = os.path.join(corrections_path, 'labels', label_filename)

        with open(label_path, 'w') as f:
            for det in detections:
                # Convert detections to YOLO format: class x_center y_center width height
                # Assuming detections come in format with bbox [x1, y1, x2, y2]
                bbox = det.get('bbox', [])
                if len(bbox) == 4:
                    x1, y1, x2, y2 = bbox
                    x_center = (x1 + x2) / 2
                    y_center = (y1 + y2) / 2
                    width = x2 - x1
                    height = y2 - y1

                    # Class 0 for bird (default)
                    class_id = det.get('class_id', 0)
                    f.write(f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")

        # Return URL to edit this image in Nestperts
        correction_url = f"/project/{corrections_folder}/editor/unassigned"

        return jsonify({
            'success': True,
            'message': 'Correction uploaded successfully',
            'image_filename': image_filename,
            'correction_url': correction_url,
            'project': 'corrections'
        })

    except Exception as e:
        import traceback
        print(f"Error uploading correction: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete_image', methods=['POST'])
@api_annotator_required  # Only annotators and admins can delete images
def delete_image():
    """
    Delete an image and its label from the project

    Use case: Remove low-quality images from the dataset
    """
    try:
        data = request.json
        project_folder = data.get('project_id')
        username = data.get('username')
        image_name = data.get('image_name')

        if not all([project_folder, username, image_name]):
            return jsonify({'error': 'Missing required fields'}), 400

        project_path = os.path.join(PROJECTS_DIR, project_folder)
        images_dir = os.path.join(project_path, 'images')
        labels_dir = os.path.join(project_path, 'labels')

        # Get image and label paths
        image_path = os.path.join(images_dir, image_name)
        label_file = os.path.splitext(image_name)[0] + '.txt'
        label_path = os.path.join(labels_dir, label_file)

        # Check if image exists
        if not os.path.exists(image_path):
            return jsonify({'error': 'Image not found'}), 404

        # Delete image file
        os.remove(image_path)
        print(f"Deleted image: {image_name}")

        # Delete label file if exists
        if os.path.exists(label_path):
            os.remove(label_path)
            print(f"Deleted label: {label_file}")

        # Update user's task list (remove from both assigned and completed)
        state = load_project_state(project_folder)
        if username in state.get('users', {}):
            user_data = state['users'][username]

            # Remove from assigned list
            assigned = user_data.get('assigned', [])
            if image_name in assigned:
                assigned.remove(image_name)
                user_data['assigned'] = assigned

            # Remove from completed list
            completed = user_data.get('completed', [])
            if image_name in completed:
                completed.remove(image_name)
                user_data['completed'] = completed

            save_project_state(project_folder, state)
            invalidate_project_cache(project_folder)

        return jsonify({
            'success': True,
            'message': f'Deleted {image_name} and its label'
        })

    except Exception as e:
        import traceback
        print(f"Error deleting image: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# API - SAM SEGMENTATION & SPECIES CLASSIFICATION
# ============================================================================

# Lazy load services
_bird_detector = None
_species_service = None
_user_service = None

def get_cv_config():
    """Get CV configuration with latest server/config.yaml values"""
    # Reload config to pick up any manual changes to server/config.yaml
    config = load_server_config()
    return config.get('cv', {})

# Track loaded model paths to detect changes
_loaded_classifier_path = None

def get_bird_detector():
    """Lazy load BirdDetector with classifier"""
    global _bird_detector, _loaded_classifier_path
    
    cv_config = get_cv_config()
    rel_cls_path = cv_config.get('classifier', 'models/classifier_swift.onnx')
    model_path = os.path.join(PROJECT_ROOT, rel_cls_path)
    
    # Reload if not loaded or if the configured path has changed
    if _bird_detector is None or _loaded_classifier_path != model_path:
        try:
            from labeller.onnx_classifier import get_bird_detector as _get_detector
            
            # Optional: custom classes file from config
            classes_path = None
            if 'classifier_classes' in cv_config:
                classes_path = os.path.join(PROJECT_ROOT, cv_config['classifier_classes'])
            
            _bird_detector = _get_detector(model_path=model_path, classes_file=classes_path)
            _loaded_classifier_path = model_path
            print(f"✓ SwiftID classifier loaded from: {model_path}")
        except Exception as e:
            print(f"✗ Could not load SwiftID: {e}")
            import traceback
            traceback.print_exc()
    return _bird_detector

def get_species_service():
    """Lazy load SpeciesService"""
    global _species_service
    if _species_service is None:
        try:
            from labeller.services.species_service import get_species_service as _get_svc
            _species_service = _get_svc()
            print("SpeciesService loaded")
        except Exception as e:
            print(f" Could not load SpeciesService: {e}")
    return _species_service

def get_user_service():
    """Lazy load UserService"""
    global _user_service
    if _user_service is None:
        try:
            from labeller.services.user_service import get_user_service as _get_svc
            _user_service = _get_svc(PROJECTS_DIR)
            print("UserService loaded")
        except Exception as e:
            print(f" Could not load UserService: {e}")
    return _user_service

def get_wikipedia_images_func(species_name, max_images=5, offset=0):
    """Get Wikipedia images using function import (not class)"""
    try:
        from labeller.services.wikipedia_images_v2 import get_wikipedia_images
        return get_wikipedia_images(species_name, max_images=max_images, offset=offset)
    except Exception as e:
        print(f" Could not load Wikipedia images: {e}")
        return []

@app.route('/api/detect_all_birds', methods=['POST'])
@api_annotator_required
def detect_all_birds():
    """
    Detect all birds in an image using swift.onnx detector.

    This is much faster than SAM clicking:
    - Finds ALL birds in one pass (~100-200ms)
    - Returns YOLO format bounding boxes
    - 85-90% accuracy
    - Supports superzoom mode with smaller slices (512x512) for tiny birds
    """
    try:
        data = request.json
        image_name = data.get('image_name')
        project_folder = data.get('project_id', 'nestvision')
        conf_threshold = data.get('confidence', 0.25)  # Configurable confidence
        slice_size = data.get('slice_size', 1024)  # 1024 (normal) or 512 (superzoom)

        if not image_name:
            return jsonify({'error': 'Missing image_name'}), 400

        # Get image path
        images_dir = os.path.join(PROJECTS_DIR, project_folder, 'images')
        image_path = os.path.join(images_dir, image_name)

        if not os.path.exists(image_path):
            return jsonify({'error': f'Image not found: {image_name}'}), 404

        # Load model path from config
        cv_config = get_cv_config()
        rel_model_path = cv_config.get('model', 'models/swift.onnx')
        model_path = os.path.join(PROJECT_ROOT, rel_model_path)

        # Initialize swift detector (cached)
        if not hasattr(detect_all_birds, 'detector') or getattr(detect_all_birds, 'path', None) != model_path:
            import onnxruntime as ort

            print(f"Loading Swift detector from: {model_path}")
            if not os.path.exists(model_path):
                return jsonify({'error': f'Model not found at {model_path}'}), 500

            providers = ['CPUExecutionProvider']
            if 'CUDAExecutionProvider' in ort.get_available_providers():
                providers.insert(0, 'CUDAExecutionProvider')
                print("  Using GPU")
            else:
                print("  Using CPU")

            detect_all_birds.detector = ort.InferenceSession(model_path, providers=providers)
            detect_all_birds.path = model_path
            print("✓ Swift detector loaded")
        detector = detect_all_birds.detector

        # Read and preprocess image
        import cv2
        img = cv2.imread(image_path)
        if img is None:
            return jsonify({'error': 'Failed to read image'}), 500

        orig_height, orig_width = img.shape[:2]

        # USE SAHI for large images (> 1024x1024)
        if orig_height > 1024 or orig_width > 1024:
            try:
                from sahi import AutoDetectionModel
                from sahi.predict import get_sliced_prediction
                from sahi.models.ultralytics import UltralyticsDetectionModel

                mode_name = "SuperZoom" if slice_size == 512 else "SAHI"
                print(f"Detector: Using {mode_name} ({slice_size}x{slice_size} slices) for large image ({orig_width}x{orig_height})")

                # Initialize SAHI model (cached)
                cv_config = get_cv_config()
                rel_model_path = cv_config.get('model', 'models/swift.onnx')
                model_path = os.path.join(PROJECT_ROOT, rel_model_path)

                if not hasattr(detect_all_birds, 'sahi_model') or getattr(detect_all_birds, 'sahi_path', None) != model_path:

                    detect_all_birds.sahi_model = UltralyticsDetectionModel(
                        model_path=model_path,
                        confidence_threshold=conf_threshold,
                        device='cpu' # Use CPU for now as default providers in app are CPU
                    )
                    detect_all_birds.sahi_path = model_path
                    print("✓ Swift SAHI Model loaded")

                sahi_model = detect_all_birds.sahi_model
                sahi_model.model.conf = conf_threshold # Update confidence

                # Run sliced inference with configurable slice size
                result = get_sliced_prediction(
                    image_path,
                    sahi_model,
                    slice_height=slice_size,
                    slice_width=slice_size,
                    overlap_height_ratio=0.2,
                    overlap_width_ratio=0.2
                )

                results = []
                for object_prediction in result.object_prediction_list:
                    bbox = object_prediction.bbox.to_xyxy() # [x1, y1, x2, y2]
                    score = object_prediction.score.value
                    category_id = object_prediction.category.id
                    
                    # Convert to normalized YOLO format
                    x1, y1, x2, y2 = bbox
                    x_center = ((x1 + x2) / 2) / orig_width
                    y_center = ((y1 + y2) / 2) / orig_height
                    width = (x2 - x1) / orig_width
                    height = (y2 - y1) / orig_height

                    results.append({
                        'x_center': float(x_center),
                        'y_center': float(y_center),
                        'width': float(width),
                        'height': float(height),
                        'confidence': float(score),
                        'class_id': int(category_id)
                    })

                mode_label = f"sahi_{slice_size}" if slice_size != 1024 else "sahi"
                print(f"Swift ({mode_name}): Found {len(results)} birds")
                return jsonify({
                    'success': True,
                    'boxes': results,
                    'count': len(results),
                    'mode': mode_label,
                    'slice_size': slice_size
                })
            except ImportError:
                print("⚠️ SAHI not installed, falling back to standard detection")
            except Exception as e:
                print(f"⚠️ SAHI error: {e}, falling back to standard detection")

        # Standard detector (for small images or fallback)
        # Dynamically determine target_size from ONNX model input shape
        input_shape = detector.get_inputs()[0].shape
        if isinstance(input_shape[2], int):
            target_size = input_shape[2]
        else:
            target_size = 1024

        print(f"  Model input size: {target_size}x{target_size}")

        scale = target_size / max(orig_height, orig_width)
        new_w = int(orig_width * scale)
        new_h = int(orig_height * scale)

        resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        # Pad to square
        padded = np.ones((target_size, target_size, 3), dtype=np.uint8) * 114
        padded[:new_h, :new_w] = resized

        # Convert BGR to RGB (YOLO expects RGB)
        rgb = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB)

        # Normalize and transpose
        input_tensor = rgb.astype(np.float32) / 255.0
        input_tensor = np.transpose(input_tensor, (2, 0, 1))
        input_tensor = np.expand_dims(input_tensor, axis=0)

        # Run detection
        print(f"Detector: Running on {image_name} (confidence={conf_threshold})...")
        input_name = detector.get_inputs()[0].name
        outputs = detector.run(None, {input_name: input_tensor})

        # Post-process outputs
        # Support both YOLOv8 (1, nc+4, 8400) and YOLO26n End-to-End (1, 300, 6)
        output = outputs[0][0]
        
        if output.shape[0] == 300 and output.shape[1] == 6:
            # YOLO26n End-to-End format: [x1, y1, x2, y2, conf, class]
            print("  Detected YOLO26n End-to-End format")
            detections = output
            confidences = detections[:, 4]
            mask = confidences > conf_threshold
            filtered = detections[mask]
            
            if len(filtered) == 0:
                return jsonify({'success': True, 'boxes': [], 'count': 0})
                
            # Extract boxes (already in corner format)
            final_boxes = filtered[:, :4]
            final_scores = filtered[:, 4]
        else:
            # Traditional YOLO format: [x, y, w, h, conf, class]
            # Transpose to (8400, 6)
            detections = output.T
            confidences = detections[:, 4]
            mask = confidences > conf_threshold
            filtered = detections[mask]

            if len(filtered) == 0:
                print(f"Detector: No birds found (tried {len(detections)} candidates)")
                return jsonify({
                    'success': True,
                    'boxes': [],
                    'count': 0
                })

            # Extract boxes and scores
            boxes_xywh = filtered[:, :4]
            scores = filtered[:, 4]

            # Convert to corner format for NMS
            boxes_xyxy = boxes_xywh.copy()
            boxes_xyxy[:, 0] -= boxes_xyxy[:, 2] / 2  # x1
            boxes_xyxy[:, 1] -= boxes_xyxy[:, 3] / 2  # y1
            boxes_xyxy[:, 2] += boxes_xyxy[:, 0]      # x2
            boxes_xyxy[:, 3] += boxes_xyxy[:, 1]      # y2

            # NMS
            def nms(boxes, scores, iou_threshold=0.45):
                x1, y1, x2, y2 = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
                areas = (x2 - x1) * (y2 - y1)
                order = scores.argsort()[::-1]
                keep = []
                while order.size > 0:
                    i = order[0]
                    keep.append(i)
                    xx1 = np.maximum(x1[i], x1[order[1:]])
                    yy1 = np.maximum(y1[i], y1[order[1:]])
                    xx2 = np.minimum(x2[i], x2[order[1:]])
                    yy2 = np.minimum(y2[i], y2[order[1:]])
                    w = np.maximum(0.0, xx2 - xx1)
                    h = np.maximum(0.0, yy2 - yy1)
                    inter = w * h
                    iou = inter / (areas[i] + areas[order[1:]] - inter)
                    inds = np.where(iou <= iou_threshold)[0]
                    order = order[inds + 1]
                return keep

            indices = nms(boxes_xyxy, scores)
            final_boxes = boxes_xyxy[indices]
            final_scores = scores[indices]

        # Scale back to original image and convert to YOLO format
        final_boxes /= scale
        
        # Extract class IDs if available
        if output.shape[0] == 300 and output.shape[1] == 6:
            final_class_ids = filtered[:, 5].astype(int)
        else:
            final_class_ids = filtered[indices, 5].astype(int)
            
        results = []

        for i, (box, score) in enumerate(zip(final_boxes, final_scores)):
            x1, y1, x2, y2 = box
            class_id = int(final_class_ids[i])

            # Clamp to image bounds
            x1 = max(0, min(x1, orig_width))
            y1 = max(0, min(y1, orig_height))
            x2 = max(0, min(x2, orig_width))
            y2 = max(0, min(y2, orig_height))

            # Convert to normalized YOLO format
            x_center = ((x1 + x2) / 2) / orig_width
            y_center = ((y1 + y2) / 2) / orig_height
            width = (x2 - x1) / orig_width
            height = (y2 - y1) / orig_height

            results.append({
                'x_center': float(x_center),
                'y_center': float(y_center),
                'width': float(width),
                'height': float(height),
                'confidence': float(score),
                'class_id': class_id
            })

        print(f"Detector: Found {len(results)} birds")

        return jsonify({
            'success': True,
            'boxes': results,
            'count': len(results)
        })

    except Exception as e:
        import traceback
        print(f"Detection error: {traceback.format_exc()}")
        return jsonify({'error': f'Detection failed: {str(e)}'}), 500

@app.route('/api/classify_crop', methods=['POST'])
@api_annotator_required
def classify_crop():
    """Classify a bird crop using the species classifier"""
    try:
        data = request.json
        image_name = data.get('image_name')
        bbox = data.get('bbox')  # {x_center, y_center, width, height} in normalized coords
        project_folder = data.get('project_id', 'nestvision')

        if not image_name or not bbox:
            return jsonify({'error': 'Missing image_name or bbox'}), 400

        # Get image path
        images_dir = os.path.join(PROJECTS_DIR, project_folder, 'images')
        image_path = os.path.join(images_dir, image_name)

        if not os.path.exists(image_path):
            return jsonify({'error': f'Image not found: {image_name}'}), 404

        # Load detector with classifier
        detector = get_bird_detector()
        if detector is None:
            return jsonify({'error': 'Classifier not available'}), 500

        # Read image
        import cv2
        img = cv2.imread(image_path)
        height, width = img.shape[:2]

        # Convert normalized bbox to pixel coordinates
        x_center = bbox['x_center'] * width
        y_center = bbox['y_center'] * height
        box_width = bbox['width'] * width
        box_height = bbox['height'] * height

        x1 = int(x_center - box_width / 2)
        y1 = int(y_center - box_height / 2)
        x2 = int(x_center + box_width / 2)
        y2 = int(y_center + box_height / 2)

        # Clamp to image bounds
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(width, x2), min(height, y2)

        # Extract crop
        crop = img[y1:y2, x1:x2]

        if crop.size == 0:
            return jsonify({'error': 'Invalid crop'}), 400

        # Classify (get top-5)
        result = detector.classify_crop(crop, top_k=5)

        # Convert result format to API format
        predictions = []
        for pred in result.get('top_predictions', []):
            predictions.append({
                'species_code': pred['code'],
                'species_name': pred['full_name'],
                'confidence': pred['confidence']
            })

        # Return predictions
        return jsonify({
            'success': True,
            'predictions': predictions
        })

    except Exception as e:
        import traceback
        print(f"Classification error: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/classify_all_birds', methods=['POST'])
@api_annotator_required
def classify_all_birds():
    """Batch classify all birds in an image"""
    try:
        data = request.json
        image_name = data.get('image_name')
        boxes = data.get('boxes', [])  # List of bbox dicts
        project_folder = data.get('project_id', 'nestvision')

        if not image_name or not boxes:
            return jsonify({'error': 'Missing image_name or boxes'}), 400

        # Get image path
        images_dir = os.path.join(PROJECTS_DIR, project_folder, 'images')
        image_path = os.path.join(images_dir, image_name)

        if not os.path.exists(image_path):
            return jsonify({'error': f'Image not found: {image_name}'}), 404

        # Load detector with classifier
        detector = get_bird_detector()
        if detector is None:
            return jsonify({'error': 'Classifier not available'}), 500

        # Read image once
        import cv2
        img = cv2.imread(image_path)
        if img is None:
            return jsonify({'error': 'Failed to load image'}), 500

        height, width = img.shape[:2]

        # Classify each bird
        classified_boxes = []
        for box in boxes:
            # Convert normalized bbox to pixel coordinates
            x_center = box['x_center'] * width
            y_center = box['y_center'] * height
            box_width = box['width'] * width
            box_height = box['height'] * height

            x1 = int(x_center - box_width / 2)
            y1 = int(y_center - box_height / 2)
            x2 = int(x_center + box_width / 2)
            y2 = int(y_center + box_height / 2)

            # Clamp to image bounds
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(width, x2), min(height, y2)

            # Extract crop
            crop = img[y1:y2, x1:x2]

            if crop.size == 0 or (x2 - x1) < 5 or (y2 - y1) < 5:
                # Skip invalid boxes
                classified_boxes.append({
                    **box,
                    'species': 'UNKNOWN',
                    'species_name': 'Unknown',
                    'confidence': 0.0
                })
                continue

            # Classify (get top prediction)
            result = detector.classify_crop(crop, top_k=1)

            # Extract top prediction (it's a list of dicts now)
            if result.get('top_predictions') and len(result['top_predictions']) > 0:
                pred = result['top_predictions'][0]
                species_code = pred['code']
                species_name = pred['full_name']
                confidence = pred['confidence']
            else:
                species_code = 'UNKNOWN'
                species_name = 'Unknown'
                confidence = 0.0

            # Add classification result to box
            classified_boxes.append({
                **box,
                'species': species_code,
                'species_name': species_name,
                'confidence': confidence
            })

        # Return classified boxes
        return jsonify({
            'success': True,
            'boxes': classified_boxes
        })

    except Exception as e:
        import traceback
        print(f"Batch classification error: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/species', methods=['GET'])
def get_all_species():
    """Get all species from database"""
    try:
        service = get_species_service()
        if service is None:
            # Fallback to species_list.json
            species_file = os.path.join(APP_DIR, 'data', 'species_list.json')
            if os.path.exists(species_file):
                with open(species_file, 'r') as f:
                    data = json.load(f)
                    return jsonify(data.get('real_species', []))
            return jsonify([])

        species = service.get_all_species()
        return jsonify(species)

    except Exception as e:
        print(f"Error getting species: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/species/search', methods=['GET'])
def search_species():
    """Search species by name or code"""
    try:
        query = request.args.get('q', '').lower().strip()

        if not query:
            return jsonify([])

        service = get_species_service()
        if service is None:
            # Fallback to species_list.json
            species_file = os.path.join(APP_DIR, 'data', 'species_list.json')
            if os.path.exists(species_file):
                with open(species_file, 'r') as f:
                    data = json.load(f)
                    all_species = data.get('real_species', [])
            else:
                all_species = []
        else:
            all_species = service.get_all_species()

        # Search by code or name
        results = []
        for species in all_species:
            code = species.get('code', '').lower()
            name = species.get('name', '').lower()
            if query in code or query in name:
                results.append(species)

        return jsonify(results)

    except Exception as e:
        print(f"Error searching species: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/species/images/<species_name>', methods=['GET'])
def get_species_images(species_name):
    """Get Wikipedia images for a species"""
    try:
        max_images = int(request.args.get('max', 5))
        offset = int(request.args.get('offset', 0))

        # Fetch images using function
        all_images = get_wikipedia_images_func(species_name, max_images=max_images + 10, offset=0)

        # Apply offset and limit
        paginated_images = all_images[offset:offset + max_images]
        has_more = (offset + max_images) < len(all_images)

        # Convert string URLs to objects with 'url' key for consistency
        image_objects = [{'url': img} if isinstance(img, str) else img for img in paginated_images]

        return jsonify({
            'images': image_objects,
            'has_more': has_more,
            'total': len(all_images)
        })

    except Exception as e:
        print(f"Error getting species images: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    ensure_directories()

    print("=" * 70)
    print("🦅 Nestperts V2 - Project-Based Annotation Platform")
    print("=" * 70)
    print(f"📁 Projects Directory: {PROJECTS_DIR}")
    print(f"🌐 Server: http://0.0.0.0:5000")
    print(f"📤 Upload: Zip files only (unlimited size)")
    print(f"📦 Smart Import: Detects YOLO datasets, user assignments")
    print("=" * 70)

    # Run with no limits
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
