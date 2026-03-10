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
from pathlib import Path
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, jsonify, send_from_directory, send_file, redirect, url_for, session, flash
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

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
    BASE_ADMIN_EMAIL
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

# ============================================================================
# PROJECT MANAGEMENT
# ============================================================================

# Get the directory where app.py is located
APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(APP_DIR, 'projects')

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

    # Count total images
    total_images = 0
    if os.path.exists(images_dir):
        total_images = len([f for f in os.listdir(images_dir)
                           if f.lower().endswith(('.jpg', '.jpeg', '.png'))])

    # Get user-completed images from project_state.json
    state = load_project_state(project_folder)
    completed_by_users = set()
    for user_data in state.get('users', {}).values():
        completed_by_users.update(user_data.get('completed', []))

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
        progress = (completed_images / total_images * 100)

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

# ============================================================================
# PUBLIC ROUTES (No Authentication Required)
# ============================================================================

@app.route('/health')
def health():
    """Health check endpoint for monitoring (no auth required)"""
    from labeller.auth import AUTH_DB
    import sqlite3

    try:
        # Check database connection
        conn = sqlite3.connect(AUTH_DB)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users')
        user_count = cursor.fetchone()[0]
        conn.close()

        return jsonify({
            'status': 'healthy',
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

        # Get user permissions
        from labeller.auth import get_user_permissions
        perms = get_user_permissions(email)

        # Store user in session (like giving them a wristband)
        session['user'] = {
            'email': email,
            'name': name,
            'picture': picture,
            'is_admin': is_admin(email),
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
    from labeller.auth import get_all_users_with_roles
    approved_emails = get_approved_emails()
    users = get_all_users_with_roles()

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
    """Main projects dashboard"""
    projects = load_projects()
    projects_list = []

    # Get all auth users with their profile pictures
    from labeller.auth import get_all_users_with_roles
    auth_users_dict = {}
    try:
        all_auth_users = get_all_users_with_roles()
        # Index by both email and name for flexible lookup
        for u in all_auth_users:
            auth_users_dict[u['email']] = u
            auth_users_dict[u['name']] = u
    except Exception as e:
        print(f"Warning: Could not load auth users: {e}")

    for project_folder, metadata in projects.items():
        stats = calculate_project_stats(project_folder)

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

    return render_template('projects_dashboard.html',
                         projects=projects_list,
                         stats=get_all_project_stats(),
                         active_page='projects')

@app.route('/project/<project_folder>')
@login_required
def project_detail(project_folder):
    """Project detail page with task management"""
    metadata = get_project(project_folder)
    if not metadata:
        return "Project not found", 404

    stats = calculate_project_stats(project_folder)
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

    # Get user profile pictures from auth database
    from labeller.auth import get_all_users_with_roles
    auth_users = {}
    try:
        all_auth_users = get_all_users_with_roles()
        # Index by both email and name for backwards compatibility
        for u in all_auth_users:
            auth_users[u['email']] = u
            auth_users[u['name']] = u
    except Exception as e:
        print(f"Warning: Could not load auth users: {e}")

    users_detail = []
    for user_key, user_data in state.get('users', {}).items():
        assigned = user_data.get('assigned', [])
        completed = user_data.get('completed', [])

        # Count annotations by this user
        user_annotations = 0
        for img in completed:
            label_file = os.path.splitext(img)[0] + '.txt'
            label_path = os.path.join(labels_dir, label_file)
            if os.path.exists(label_path):
                with open(label_path, 'r') as f:
                    lines = [line.strip() for line in f if line.strip()]
                    user_annotations += len(lines)

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
    """NestDB - Supabase-inspired database management interface"""
    return render_template('nestdb.html', active_page='nestdb')

@app.route('/users')
@login_required
def users_page():
    """Global users management page - shows authenticated users via Google OAuth"""
    from labeller.auth import get_all_users_with_roles

    users_list = []

    try:
        # Get authenticated users from auth database
        auth_users = get_all_users_with_roles()

        # Enhance with project details
        for user in auth_users:
            user_projects = []
            total_completed = 0
            total_annotations = 0

            # Scan all projects to find this user's contributions
            projects = get_all_projects()
            for proj in projects:
                state = load_project_state(proj['folder'])
                # Look up user by EMAIL (unique identifier)
                # Note: Old projects may use name as key, new projects use email
                user_data = state.get('users', {}).get(user['email'])
                if not user_data:
                    # Fallback: try name (for backwards compatibility with old projects)
                    user_data = state.get('users', {}).get(user['name'])

                if not user_data:
                    continue  # User not in this project

                if user_data.get('assigned') or user_data.get('completed'):  # User has actual assignments in this project
                    assigned = user_data.get('assigned', [])
                    completed = user_data.get('completed', [])

                    project_info = {
                        'folder': proj['folder'],
                        'name': proj['name'],
                        'assigned': len(assigned),
                        'completed': len(completed)
                    }
                    user_projects.append(project_info)
                    total_completed += len(completed)

                    # Count annotations from completed images
                    for img_name in completed:
                        label_file = os.path.join(PROJECTS_DIR, proj['folder'], 'labels', f"{os.path.splitext(img_name)[0]}.txt")
                        if os.path.exists(label_file):
                            with open(label_file, 'r') as f:
                                total_annotations += len(f.readlines())

            users_list.append({
                'name': user['name'],
                'email': user['email'],
                'picture': user.get('picture'),
                'role': user['role'],
                'first_login': user.get('first_login', ''),
                'projects': user_projects,
                'total_projects': len(user_projects),
                'total_completed': total_completed,
                'total_annotations': total_annotations
            })

    except Exception as e:
        print(f"Error loading users: {e}")
        import traceback
        traceback.print_exc()

    return render_template('users_page.html',
                         users=users_list,
                         active_page='users')

@app.route('/test-image')
def test_image():
    """Test page for debugging image loading"""
    return send_from_directory(APP_DIR, 'test_image_route.html')

@app.route('/project/<project_folder>/editor/<username>')
@app.route('/project/<project_folder>/editor/<username>/<int:image_index>')
@login_required
def editor(project_folder, username, image_index=0):
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
        from labeller.auth import get_all_users_with_roles
        auth_users = get_all_users_with_roles()
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

    # Load existing labels (if any)
    label_file = os.path.splitext(image_name)[0] + '.txt'
    label_path = os.path.join(labels_dir, label_file)
    boxes = []

    if os.path.exists(label_path):
        with open(label_path, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 5:
                    boxes.append({
                        'class_id': int(parts[0]),
                        'x_center': float(parts[1]),
                        'y_center': float(parts[2]),
                        'width': float(parts[3]),
                        'height': float(parts[4]),
                        'species': parts[5] if len(parts) > 5 else 'UNWA'
                    })

    # Load species list
    species_file = os.path.join(APP_DIR, 'data', 'species_list.json')
    species_list = []
    if os.path.exists(species_file):
        with open(species_file, 'r') as f:
            data = json.load(f)
            species_list = data.get('real_species', [])

    # Simple questions structure (can be expanded later)
    questions = [
        {
            "id": 0,
            "text": "Select the bird species",
            "type": "species_select"
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
                         species_list=species_list,
                         questions=questions,
                         back_url=f'/project/{project_folder}')

# ============================================================================
# API - PROJECT MANAGEMENT
# ============================================================================

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

        name = request.form.get('name')
        description = request.form.get('description', '')

        logger.info(f"Project name: {name}")
        logger.info(f"Description: {description}")

        if not name:
            logger.error("No project name provided")
            return jsonify({'error': 'Project name required'}), 400

        # Check for zip file
        zip_file = request.files.get('zip_file')
        if not zip_file:
            logger.error("No zip file provided")
            return jsonify({'error': 'Zip file required'}), 400

        if not zip_file.filename.lower().endswith('.zip'):
            logger.error(f"Invalid file type: {zip_file.filename}")
            return jsonify({'error': 'Only .zip files are accepted'}), 400

        logger.info(f"✓ Received zip file: {zip_file.filename}")

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
        logger.info("✓ Directories created")

        # Save and analyze zip
        temp_zip_path = os.path.join(project_path, 'temp.zip')
        zip_file.save(temp_zip_path)
        logger.info(f"✓ Saved zip to: {temp_zip_path}")

        # Analyze zip structure
        has_data_yaml = False
        has_project_state = False
        data_yaml_content = None
        project_state_content = None
        image_count = 0
        label_count = 0

        try:
            with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                logger.info(f"✓ Opened zip, contains {len(zip_ref.namelist())} files")

                # First pass: detect structure
                for file_info in zip_ref.namelist():
                    # Check for any YAML file (could be data.yaml, dataset.yaml, etc.)
                    if file_info.lower().endswith('.yaml') or file_info.lower().endswith('.yml'):
                        if not has_data_yaml:  # Only take the first YAML found
                            has_data_yaml = True
                            data_yaml_content = zip_ref.read(file_info).decode('utf-8')
                            yaml_filename = os.path.basename(file_info)
                            logger.info(f"✓ Found {yaml_filename} - this is a YOLO dataset import")
                    elif file_info.endswith('project_state.json') or file_info == 'project_state.json':
                        has_project_state = True
                        project_state_content = zip_ref.read(file_info).decode('utf-8')
                        logger.info("✓ Found project_state.json - importing user assignments")

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
                        if image_count % 10 == 0:
                            logger.info(f"  Extracted {image_count} images...")

                    # Extract labels
                    elif filename.endswith('.txt') and 'classes.txt' not in filename:
                        zip_ref.extract(file_info, project_path)
                        extracted_path = os.path.join(project_path, file_info)
                        dest_path = os.path.join(labels_dir, filename)
                        shutil.move(extracted_path, dest_path)
                        label_count += 1

                    # Extract YAML file (rename to data.yaml for consistency)
                    elif (filename.lower().endswith('.yaml') or filename.lower().endswith('.yml')) and has_data_yaml:
                        dest_path = os.path.join(project_path, 'data.yaml')
                        with open(dest_path, 'w') as f:
                            f.write(data_yaml_content)
                        logger.info(f"✓ Preserved {filename} as data.yaml")

                    # Extract project_state.json
                    elif filename == 'project_state.json' and has_project_state:
                        dest_path = os.path.join(project_path, 'project_state.json')
                        with open(dest_path, 'w') as f:
                            f.write(project_state_content)
                        logger.info("✓ Preserved project_state.json")

                    # Extract classes.txt if present
                    elif filename == 'classes.txt':
                        dest_path = os.path.join(project_path, 'classes.txt')
                        zip_ref.extract(file_info, project_path)
                        extracted_path = os.path.join(project_path, file_info)
                        shutil.move(extracted_path, dest_path)
                        logger.info("✓ Preserved classes.txt")

                logger.info(f"✓ Extracted {image_count} images, {label_count} labels from zip")

                # Clean up temp files
                os.remove(temp_zip_path)
                # Remove any extracted directories
                for item in os.listdir(project_path):
                    item_path = os.path.join(project_path, item)
                    if os.path.isdir(item_path) and item not in ['images', 'labels']:
                        shutil.rmtree(item_path)

        except Exception as zip_error:
            logger.error(f"❌ Error processing zip: {zip_error}")
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
            logger.info("✓ Created data.yaml with default class (Bird)")

        # Create or preserve project_state.json
        if not has_project_state:
            logger.info("Creating empty project_state.json...")
            project_state = {'users': {}}
            save_project_state(project_folder, project_state)
            logger.info("✓ Created empty project_state.json")

        # Create metadata.json
        logger.info("Creating metadata.json...")
        metadata = {
            'name': name,
            'description': description,
            'created_at': datetime.now().isoformat(),
            'import_type': import_type
        }
        save_project_metadata(project_folder, metadata)
        logger.info("✓ Created metadata.json")

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

        # Get user info from auth system
        from labeller.auth import get_all_users_with_roles
        auth_users = {u['email']: u for u in get_all_users_with_roles()}

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

        if not available:
            if allow_reassign:
                return jsonify({'error': f'All images already assigned to {user_name}'}), 400
            else:
                return jsonify({'error': 'No unassigned images available. Enable "Allow Reassignment" to assign already-assigned images.'}), 400

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
            'selection_type': selection_type,
            'message': f'Assigned {len(new_assignments)} new image(s) to {user_name} ({selection_type})'
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
            logger.info(f"✓ Deleted project directory: {project_path}")
        else:
            logger.warning(f"Project directory not found: {project_path}")

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

@app.route('/api/projects/<project_folder>/export/<format>')
def export_project(project_folder, format):
    """Export project annotations in specified format"""
    try:
        metadata = get_project(project_folder)
        if not metadata:
            return jsonify({'error': 'Project not found'}), 404

        project_path = os.path.join(PROJECTS_DIR, project_folder)
        export_dir = os.path.join(project_path, f'export_{format}')
        os.makedirs(export_dir, exist_ok=True)

        if format == 'yolo':
            # YOLO format: zip entire project (images, labels, data.yaml, project_state.json)
            zip_path = os.path.join(project_path, f'{project_folder}_yolo.zip')
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                # Add images
                images_dir = os.path.join(project_path, 'images')
                for img in os.listdir(images_dir):
                    zipf.write(os.path.join(images_dir, img), f'images/{img}')

                # Add labels
                labels_dir = os.path.join(project_path, 'labels')
                if os.path.exists(labels_dir):
                    for label in os.listdir(labels_dir):
                        zipf.write(os.path.join(labels_dir, label), f'labels/{label}')

                # Add data.yaml
                data_yaml_path = os.path.join(project_path, 'data.yaml')
                if os.path.exists(data_yaml_path):
                    zipf.write(data_yaml_path, 'data.yaml')

                # Add project_state.json
                state_path = os.path.join(project_path, 'project_state.json')
                if os.path.exists(state_path):
                    zipf.write(state_path, 'project_state.json')

                # Add metadata.json
                metadata_path = os.path.join(project_path, 'metadata.json')
                if os.path.exists(metadata_path):
                    zipf.write(metadata_path, 'metadata.json')

            return send_file(zip_path, as_attachment=True)

        elif format == 'geojson':
            # GeoJSON format: convert bounding boxes to geographic features
            # This is a placeholder - actual implementation would need GPS coordinates
            geojson = {
                "type": "FeatureCollection",
                "features": []
            }

            geojson_path = os.path.join(export_dir, 'annotations.geojson')
            with open(geojson_path, 'w') as f:
                json.dump(geojson, f, indent=2)

            zip_path = os.path.join(project_path, f'{project_folder}_geojson.zip')
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                zipf.write(geojson_path, 'annotations.geojson')

            return send_file(zip_path, as_attachment=True)

        elif format == 'coco':
            # COCO format: standard object detection format
            coco = {
                "info": {
                    "description": metadata['name'],
                    "date_created": metadata.get('created_at', '')
                },
                "images": [],
                "annotations": [],
                "categories": [{"id": 0, "name": "bird"}]
            }

            # Convert YOLO to COCO format
            # (Implementation details would go here)

            coco_path = os.path.join(export_dir, 'annotations.json')
            with open(coco_path, 'w') as f:
                json.dump(coco, f, indent=2)

            zip_path = os.path.join(project_path, f'{project_folder}_coco.zip')
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                zipf.write(coco_path, 'annotations.json')

                # Add images
                images_dir = os.path.join(project_path, 'images')
                for img in os.listdir(images_dir):
                    zipf.write(os.path.join(images_dir, img), f'images/{img}')

            return send_file(zip_path, as_attachment=True)

        else:
            return jsonify({'error': 'Unsupported format'}), 400

    except Exception as e:
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
        logging.info(f"[IMAGE REQUEST] ✓ Serving {filename}")
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
                # YOLO format: class_id x_center y_center width height species
                class_id = box.get('class_id', 0)
                x_center = box.get('x_center', box.get('x', 0))
                y_center = box.get('y_center', box.get('y', 0))
                width = box.get('width', 0)
                height = box.get('height', 0)
                species = box.get('species', 'UNWA')

                line = f"{class_id} {x_center} {y_center} {width} {height} {species}"
                f.write(line + '\n')

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
                from labeller.auth import get_all_users_with_roles
                auth_users = get_all_users_with_roles()
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

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users', methods=['GET'])
@api_login_required
def get_all_users():
    """Get all authenticated users who can be assigned to tasks"""
    try:
        from labeller.auth import get_all_users_with_roles

        # Get all logged-in users from authentication system
        auth_users = get_all_users_with_roles()

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
        print(f"✓ Deleted image: {image_name}")

        # Delete label file if exists
        if os.path.exists(label_path):
            os.remove(label_path)
            print(f"✓ Deleted label: {label_file}")

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

def get_bird_detector():
    """Lazy load BirdDetector with classifier"""
    global _bird_detector
    if _bird_detector is None:
        try:
            import sys
            sys.path.insert(0, PROJECT_ROOT)
            from server.cv_tools.inference import BirdDetector
            _bird_detector = BirdDetector()
            print("✓ BirdDetector with classifier loaded")
        except Exception as e:
            print(f"⚠️  Could not load BirdDetector: {e}")
    return _bird_detector

def get_species_service():
    """Lazy load SpeciesService"""
    global _species_service
    if _species_service is None:
        try:
            from labeller.services.species_service import get_species_service as _get_svc
            _species_service = _get_svc()
            print("✓ SpeciesService loaded")
        except Exception as e:
            print(f"⚠️  Could not load SpeciesService: {e}")
    return _species_service

def get_user_service():
    """Lazy load UserService"""
    global _user_service
    if _user_service is None:
        try:
            from labeller.services.user_service import get_user_service as _get_svc
            _user_service = _get_svc(PROJECTS_DIR)
            print("✓ UserService loaded")
        except Exception as e:
            print(f"⚠️  Could not load UserService: {e}")
    return _user_service

def get_wikipedia_images_func(species_name, max_images=5, offset=0):
    """Get Wikipedia images using function import (not class)"""
    try:
        from labeller.services.wikipedia_images_v2 import get_wikipedia_images
        return get_wikipedia_images(species_name, max_images=max_images, offset=offset)
    except Exception as e:
        print(f"⚠️  Could not load Wikipedia images: {e}")
        return []

@app.route('/api/sam_segment', methods=['POST'])
@api_annotator_required
def sam_segment():
    """
    Smart bird detection using YOLO detector (much faster than SAM)

    Instead of using MobileSAM, we use the existing ONNX YOLO detector
    to find birds near the clicked location. This is:
    - 10x faster (ONNX vs PyTorch)
    - More accurate for birds
    - Already uses GPU if available
    """
    try:
        data = request.json
        image_name = data.get('image_name')
        points = data.get('points', [])  # [[x, y]] in normalized coords
        project_folder = data.get('project_id', 'nestvision')

        if not image_name or not points:
            return jsonify({'error': 'Missing image_name or points'}), 400

        # Get image path
        images_dir = os.path.join(PROJECTS_DIR, project_folder, 'images')
        image_path = os.path.join(images_dir, image_name)

        if not os.path.exists(image_path):
            return jsonify({'error': f'Image not found: {image_name}'}), 404

        # Load bird detector with ONNX
        detector = get_bird_detector()
        if detector is None:
            return jsonify({'error': 'Bird detector not available'}), 500

        # Read image
        import cv2
        img = cv2.imread(image_path)
        height, width = img.shape[:2]

        # Convert normalized click to pixel coordinates
        click_x = int(points[0][0] * width)
        click_y = int(points[0][1] * height)

        # Create a crop around the click point (400x400 pixels)
        crop_size = 400
        x1 = max(0, click_x - crop_size // 2)
        y1 = max(0, click_y - crop_size // 2)
        x2 = min(width, x1 + crop_size)
        y2 = min(height, y1 + crop_size)

        # Adjust if crop goes out of bounds
        if x2 - x1 < crop_size:
            x1 = max(0, x2 - crop_size)
        if y2 - y1 < crop_size:
            y1 = max(0, y2 - crop_size)

        # Extract crop
        crop = img[y1:y2, x1:x2]

        # Save crop temporarily for YOLO detection
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            tmp_path = tmp_file.name
            cv2.imwrite(tmp_path, crop)

        try:
            # Run YOLO detection on crop with low confidence threshold
            result = detector.predict(
                tmp_path,
                conf_threshold=0.15,  # Lower threshold to catch more birds
                fast_mode=True,
                use_sliding_window=False,  # Crop is already small
                verbose=False
            )

            # Convert crop-relative detections to full image coordinates
            boxes = []
            for det in result['detections']:
                bbox = det['bbox']  # [x1, y1, x2, y2] in crop coordinates

                # Convert to full image coordinates
                full_x1 = (bbox[0] + x1) / width
                full_y1 = (bbox[1] + y1) / height
                full_x2 = (bbox[2] + x1) / width
                full_y2 = (bbox[3] + y1) / height

                # Convert to YOLO format (center + size)
                x_center = (full_x1 + full_x2) / 2
                y_center = (full_y1 + full_y2) / 2
                box_width = full_x2 - full_x1
                box_height = full_y2 - full_y1

                # Only include boxes near the click point (within 150 pixels)
                box_center_x = x_center * width
                box_center_y = y_center * height
                distance = ((box_center_x - click_x)**2 + (box_center_y - click_y)**2)**0.5

                if distance < 150:  # 150 pixel radius
                    boxes.append({
                        'x_center': x_center,
                        'y_center': y_center,
                        'width': box_width,
                        'height': box_height,
                        'confidence': det.get('confidence', 0.0)
                    })

            # Sort by distance to click (closest first)
            if boxes:
                boxes.sort(key=lambda b: ((b['x_center']*width - click_x)**2 +
                                         (b['y_center']*height - click_y)**2))

            return jsonify({
                'success': True,
                'boxes': boxes[:3],  # Return max 3 closest birds
                'count': len(boxes[:3])
            })

        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    except Exception as e:
        import traceback
        print(f"Bird detection error: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/classify_crop', methods=['POST'])
@api_annotator_required
def classify_crop():
    """Classify a bird crop using the species classifier"""
    try:
        data = request.json
        image_name = data.get('image_name')
        bbox = data.get('bbox')  # {x_center, y_center, width, height} in normalized coords
        fast_mode = data.get('fast_mode', True)
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
        result = detector.classify_crop(crop, fast_mode=fast_mode, top_k=5)

        # Return predictions
        return jsonify({
            'success': True,
            'predictions': result.get('top_predictions', [])
        })

    except Exception as e:
        import traceback
        print(f"Classification error: {traceback.format_exc()}")
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
