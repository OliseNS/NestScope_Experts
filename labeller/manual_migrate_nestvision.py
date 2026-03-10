#!/usr/bin/env python3
"""
Quick manual migration for the nestvision project.

Run this after the user specifies which email to use.
"""

import json
import sys

PROJECT_STATE_FILE = 'labeller/projects/nestvision/project_state.json'

def migrate(target_email, target_name):
    """Migrate nestvision project_state.json to use email as key"""

    # Load current state
    with open(PROJECT_STATE_FILE, 'r') as f:
        state = json.load(f)

    if 'users' not in state:
        print("No users to migrate")
        return

    # Get the current user data (keyed by name)
    old_name = 'Olisemeka Nmarkwe'
    if old_name not in state['users']:
        print(f"User '{old_name}' not found in project state")
        return

    user_data = state['users'][old_name]

    # Create new state with email as key
    new_state = {
        'users': {
            target_email: {
                'name': target_name,  # Store name for display
                'assigned': user_data.get('assigned', []),
                'completed': user_data.get('completed', [])
            }
        }
    }

    # Backup original
    backup_file = PROJECT_STATE_FILE + '.backup'
    with open(backup_file, 'w') as f:
        json.dump(state, f, indent=2)
    print(f"✓ Backup saved: {backup_file}")

    # Save migrated state
    with open(PROJECT_STATE_FILE, 'w') as f:
        json.dump(new_state, f, indent=2)

    print(f"✓ Migrated '{old_name}' → '{target_email}'")
    print(f"  - Assigned: {len(user_data.get('assigned', []))} images")
    print(f"  - Completed: {len(user_data.get('completed', []))} images")
    print()
    print("Migration complete! Restart NestPerts to see changes.")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 labeller/manual_migrate_nestvision.py <email>")
        print()
        print("Available emails:")
        print("  1. olisemekanmarkwe@gmail.com")
        print("  2. olisemeka.nmarkwe@selu.edu")
        sys.exit(1)

    email = sys.argv[1]
    name = 'Olisemeka Nmarkwe'

    migrate(email, name)
