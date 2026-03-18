#!/usr/bin/env python3
"""
Migration Script: Convert project_state.json from name-based to email-based keys

Problem:
--------
Multiple users can have the same name but different emails, causing collisions
in the project system. This script migrates project_state.json to use emails
as the primary key.

Before: state['users']['Olisemeka Nmarkwe'] = {...}
After:  state['users']['olisemeka@example.com'] = {...}

Educational Note:
-----------------
This is a common database design issue - choosing the wrong primary key!
- Names are NOT unique (people can share names)
- Emails ARE unique (Google OAuth enforces this)
- Always use a truly unique identifier as your key

Usage:
------
python3 labeller/migrate_to_email_keys.py
"""

import os
import sys
import json
import sqlite3
from pathlib import Path

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Database path
AUTH_DB = os.path.join(PROJECT_ROOT, 'data', 'users.db')
PROJECTS_DIR = os.path.join(PROJECT_ROOT, 'labeller', 'projects')

def get_user_email(name):
    """
    Look up email for a given name in the auth database.

    If multiple users have the same name, we can't determine which one,
    so we'll prompt the user to resolve it.
    """
    conn = sqlite3.connect(AUTH_DB)
    cursor = conn.cursor()
    cursor.execute('SELECT email, name FROM users WHERE name = ?', (name,))
    results = cursor.fetchall()
    conn.close()

    if not results:
        print(f"⚠️  WARNING: User '{name}' not found in auth database")
        return None

    if len(results) > 1:
        print(f"\n⚠️  CONFLICT: Multiple emails found for name '{name}':")
        for i, (email, _) in enumerate(results, 1):
            print(f"   {i}. {email}")

        while True:
            choice = input(f"Which email should be used for '{name}'? (1-{len(results)}): ").strip()
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(results):
                    return results[idx][0]
            except ValueError:
                pass
            print("Invalid choice. Please try again.")

    return results[0][0]

def migrate_project(project_folder):
    """Migrate a single project's state file"""
    state_file = os.path.join(PROJECTS_DIR, project_folder, 'project_state.json')

    if not os.path.exists(state_file):
        print(f"   ⏭️  No project_state.json found, skipping")
        return False

    # Load current state
    with open(state_file, 'r') as f:
        state = json.load(f)

    if 'users' not in state or not state['users']:
        print(f"   ✓ No users in project, nothing to migrate")
        return False

    # Check if already migrated (emails as keys)
    first_key = list(state['users'].keys())[0]
    if '@' in first_key:
        print(f"   ✓ Already migrated (uses email keys)")
        return False

    # Migrate: name keys → email keys
    new_users = {}
    needs_migration = False

    for name, user_data in state['users'].items():
        email = get_user_email(name)

        if email:
            # Add name to user data so we can still display it
            user_data['name'] = name
            new_users[email] = user_data
            needs_migration = True
            print(f"   ✓ Migrated: '{name}' → '{email}'")
        else:
            print(f"   ⚠️  Skipping user '{name}' (not found in auth database)")

    if not needs_migration:
        print(f"   ✓ No migration needed")
        return False

    # Update state
    state['users'] = new_users

    # Backup original
    backup_file = state_file + '.backup'
    with open(backup_file, 'w') as f:
        json.dump(state, f, indent=2)
    print(f"   💾 Backup saved: {backup_file}")

    # Save migrated state
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)
    print(f"   ✅ Migration complete!")

    return True

def main():
    """Run migration on all projects"""
    print("=" * 70)
    print("NestPerts Migration: Name Keys → Email Keys")
    print("=" * 70)
    print()

    if not os.path.exists(AUTH_DB):
        print(f"❌ Error: Auth database not found at {AUTH_DB}")
        print("   Make sure you've run the app at least once to create the database.")
        return 1

    if not os.path.exists(PROJECTS_DIR):
        print(f"❌ Error: Projects directory not found at {PROJECTS_DIR}")
        return 1

    # Find all projects
    projects = [d for d in os.listdir(PROJECTS_DIR)
                if os.path.isdir(os.path.join(PROJECTS_DIR, d)) and d != '__pycache__']

    if not projects:
        print("No projects found. Nothing to migrate.")
        return 0

    print(f"Found {len(projects)} project(s):\n")

    migrated_count = 0
    for project_folder in projects:
        print(f"📁 Project: {project_folder}")
        if migrate_project(project_folder):
            migrated_count += 1
        print()

    print("=" * 70)
    print(f"Migration Summary: {migrated_count}/{len(projects)} projects migrated")
    print("=" * 70)

    if migrated_count > 0:
        print("\n⚠️  IMPORTANT: Restart the NestPerts application for changes to take effect.")

    return 0

if __name__ == '__main__':
    sys.exit(main())
