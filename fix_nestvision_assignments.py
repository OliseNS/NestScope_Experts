#!/usr/bin/env python3
"""
Quick fix for NestVision project - Remove duplicate user assignment

The selu.edu user was assigned 505 images (including duplicates from gmail user).
This script removes that user to clean up the project.
"""

import json

PROJECT_STATE = 'labeller/projects/nestvision/project_state.json'

# Load state
with open(PROJECT_STATE, 'r') as f:
    state = json.load(f)

print("Current state:")
for email, data in state['users'].items():
    print(f"  {email}: {len(data['assigned'])} assigned, {len(data['completed'])} completed")

# Save backup BEFORE modifying
with open(PROJECT_STATE + '.before_cleanup', 'w') as f:
    json.dump(state, f, indent=2)
print(f"\nBackup saved to {PROJECT_STATE}.before_cleanup")

# Remove selu.edu user
if 'olisemeka.nmarkwe@selu.edu' in state['users']:
    removed = state['users'].pop('olisemeka.nmarkwe@selu.edu')
    print(f"\nRemoved olisemeka.nmarkwe@selu.edu:")
    print(f"  - Had {len(removed['assigned'])} images assigned")
    print(f"  - Had {len(removed['completed'])} images completed")

    # Save cleaned state
    with open(PROJECT_STATE, 'w') as f:
        json.dump(state, f, indent=2)
    print(f"\nCleaned state saved to {PROJECT_STATE}")
else:
    print("\nolisemeka.nmarkwe@selu.edu not found in project - nothing to remove")

print("\n✅ Done! Restart NestPerts to see changes.")
