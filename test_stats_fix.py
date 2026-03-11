#!/usr/bin/env python3
"""
Test that project stats only count user-completed images, not all labels
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from labeller.app import calculate_project_stats, load_project_state, PROJECTS_DIR

# Test nestvision project
project_folder = 'nestvision'
state = load_project_state(project_folder)
stats = calculate_project_stats(project_folder)

print("=" * 60)
print("NestVision Project Stats Test")
print("=" * 60)
print()

# Show what's in project_state.json
print("📄 Project State (what users completed):")
for user_email, user_data in state.get('users', {}).items():
    print(f"  {user_data.get('name', user_email)}")
    print(f"    - Assigned: {len(user_data.get('assigned', []))}")
    print(f"    - Completed: {len(user_data.get('completed', []))}")
print()

# Show calculated stats
print("📊 Calculated Stats (should match user work):")
print(f"  Total Images: {stats['total_images']}")
print(f"  Completed: {stats['completed_images']}")
print(f"  Annotations: {stats['total_annotations']}")
print(f"  Progress: {stats['progress']:.1f}%")
print()

# Verify correctness
images_dir = os.path.join(PROJECTS_DIR, project_folder, 'images')
labels_dir = os.path.join(PROJECTS_DIR, project_folder, 'labels')
total_labels = len([f for f in os.listdir(labels_dir) if f.endswith('.txt')])

print("✓ Verification:")
print(f"  Total label files on disk: {total_labels}")
print(f"  User-completed images: {stats['completed_images']}")
print()

if stats['completed_images'] == 10:
    print("✅ PASS: Stats correctly show only user-completed images (10)")
    print("   (Not counting all 505 pre-imported labels)")
else:
    print(f"❌ FAIL: Expected 10 completed, got {stats['completed_images']}")
    sys.exit(1)

if stats['total_images'] == 505:
    print("✅ PASS: Total images correct (505)")
else:
    print(f"❌ FAIL: Expected 505 total, got {stats['total_images']}")
    sys.exit(1)

if stats['progress'] < 3:  # Should be ~2%
    print(f"✅ PASS: Progress correct ({stats['progress']:.1f}%, not 100%)")
else:
    print(f"❌ FAIL: Progress too high ({stats['progress']:.1f}%)")
    sys.exit(1)

print()
print("🎉 All tests passed! Stats are now accurate.")
