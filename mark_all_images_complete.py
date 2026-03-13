#!/usr/bin/env python3
"""
Mark all images in a project as completed in project_state.json

This is useful when importing a pre-labeled dataset where all images
are already annotated and don't need expert review.
"""

import json
import os
from pathlib import Path
import argparse


def mark_all_complete(project_folder, user_email="system@nestperts"):
    """
    Mark all images in a project as completed.

    Args:
        project_folder: Name of the project folder in labeller/projects/
        user_email: Email to assign completed images to (default: system@nestperts)
    """
    project_path = Path('labeller/projects') / project_folder
    state_file = project_path / 'project_state.json'
    images_dir = project_path / 'images'

    # Check if project exists
    if not project_path.exists():
        print(f"❌ Error: Project '{project_folder}' does not exist")
        return False

    if not images_dir.exists():
        print(f"❌ Error: Images directory not found in project '{project_folder}'")
        return False

    # Get all image filenames
    image_files = [f.name for f in images_dir.glob('*.jpg')] + \
                  [f.name for f in images_dir.glob('*.png')]

    if not image_files:
        print(f"⚠️  Warning: No images found in {images_dir}")
        return False

    print(f"Found {len(image_files):,} images in {project_folder}")

    # Load or create project state
    if state_file.exists():
        with open(state_file, 'r') as f:
            state = json.load(f)
        print(f"Loaded existing project_state.json")
    else:
        state = {"users": {}}
        print(f"Creating new project_state.json")

    # Ensure users dict exists
    if "users" not in state:
        state["users"] = {}

    # Get or create user entry
    if user_email not in state["users"]:
        state["users"][user_email] = {
            "name": "Pre-labeled Dataset",
            "assigned": [],
            "completed": []
        }

    user_data = state["users"][user_email]

    # Ensure user has required fields
    if "assigned" not in user_data:
        user_data["assigned"] = []
    if "completed" not in user_data:
        user_data["completed"] = []

    # Count existing completed
    existing_completed = set(user_data["completed"])
    new_images = [img for img in image_files if img not in existing_completed]

    if new_images:
        print(f"\nMarking {len(new_images):,} new images as completed...")

        # Add all images to completed
        user_data["completed"].extend(new_images)

        # Remove duplicates and sort
        user_data["completed"] = sorted(list(set(user_data["completed"])))

        # Clear assigned list (they're all completed now)
        user_data["assigned"] = []

        # Save updated state
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)

        print(f"✓ Successfully marked {len(new_images):,} images as completed")
        print(f"✓ Total completed images: {len(user_data['completed']):,}")
        print(f"✓ Updated {state_file}")
    else:
        print(f"\n✓ All images already marked as completed")
        print(f"  Total completed: {len(existing_completed):,}")

    return True


def main():
    parser = argparse.ArgumentParser(
        description='Mark all images in a project as completed',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Mark all images in stage_2 as completed
  python mark_all_images_complete.py --project stage_2

  # Assign to specific user
  python mark_all_images_complete.py --project stage_2 --user expert@example.com
        """
    )

    parser.add_argument('--project', type=str, required=True,
                        help='Project folder name (e.g., stage_2, nestvision)')
    parser.add_argument('--user', type=str, default='system@nestperts',
                        help='User email to assign completed images to (default: system@nestperts)')

    args = parser.parse_args()

    print("╔═══════════════════════════════════════════════════════╗")
    print("║     Mark All Images as Completed - Nestperts         ║")
    print("╚═══════════════════════════════════════════════════════╝\n")

    success = mark_all_complete(args.project, args.user)

    if not success:
        exit(1)


if __name__ == '__main__':
    main()
