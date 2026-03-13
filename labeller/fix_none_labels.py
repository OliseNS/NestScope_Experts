#!/usr/bin/env python3
"""
Fix YOLO label files that have "None" instead of numeric class IDs.

This script scans all label files in the projects directory and replaces
any "None" values in the first column with "0" to match YOLO format.

Usage:
    python fix_none_labels.py
"""

import os
import glob

PROJECTS_DIR = os.path.join(os.path.dirname(__file__), 'projects')

def fix_label_file(filepath):
    """Fix a single label file by replacing 'None' with '0'."""
    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
        
        fixed_lines = []
        changes_made = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            parts = line.split()
            if len(parts) >= 5:  # YOLO format: class_id x y w h [species]
                # Fix the class_id (first column)
                if parts[0].lower() in ['none', 'null']:
                    parts[0] = '0'
                    changes_made = True
                
                fixed_lines.append(' '.join(parts))
        
        if changes_made:
            with open(filepath, 'w') as f:
                f.write('\n'.join(fixed_lines) + '\n')
            return True
        
        return False
    
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False


def main():
    """Scan all projects and fix label files."""
    total_files = 0
    fixed_files = 0
    
    # Find all label files in all projects
    label_pattern = os.path.join(PROJECTS_DIR, '*', 'labels', '*.txt')
    label_files = glob.glob(label_pattern)
    
    print(f"Found {len(label_files)} label files to check...")
    
    for label_file in label_files:
        total_files += 1
        if fix_label_file(label_file):
            fixed_files += 1
            print(f"✓ Fixed: {label_file}")
    
    print(f"\n{'='*50}")
    print(f"Checked {total_files} files")
    print(f"Fixed {fixed_files} files")
    print(f"{'='*50}")


if __name__ == '__main__':
    main()
