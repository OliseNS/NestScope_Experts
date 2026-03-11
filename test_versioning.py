#!/usr/bin/env python3
"""
Test script for the enhanced versioning system.

Run this to verify that the change tracker is working correctly.
"""

import sqlite3
from pathlib import Path
from server.db_change_tracker import ChangeTracker

def main():
    print("=" * 70)
    print("🧪 TESTING ENHANCED VERSIONING SYSTEM")
    print("=" * 70)
    print()

    # Initialize change tracker
    db_path = "data/bird_data_complete.db"

    print(f"📁 Initializing change tracker for: {db_path}")
    tracker = ChangeTracker(db_path)
    print(f"✓ Change tracker initialized")
    print(f"✓ Changelog database: {tracker.changelog_db}")
    print()

    # Test 1: Get statistics
    print("📊 Test 1: Getting Statistics")
    print("-" * 70)
    stats = tracker.get_stats()

    print(f"Total commits: {stats['total_commits']}")
    print(f"Total changes: {stats['total_changes']}")
    print(f"Unique users: {stats['unique_users']}")
    print(f"Unique tables: {stats['unique_tables']}")
    print()

    if stats['operations']:
        print("Operation breakdown:")
        for op, count in stats['operations'].items():
            print(f"  {op}: {count}")
    print()

    if stats.get('most_active_user'):
        user = stats['most_active_user']
        print(f"Most active user: {user['name']} ({user['commits']} commits)")

    if stats.get('most_modified_table'):
        table = stats['most_modified_table']
        print(f"Most modified table: {table['name']} ({table['commits']} commits)")
    print()

    # Test 2: Track a sample update
    print("✏️  Test 2: Tracking a Sample Update")
    print("-" * 70)
    result = tracker.track_update(
        table_name="test_table",
        row_id={"id": 999},
        old_values={"name": "Test Bird", "count": 10},
        new_values={"name": "Test Bird", "count": 15},
        user_email="test@nestscope.org",
        user_name="Test User",
        user_picture="https://example.com/avatar.jpg"
    )

    if result['success']:
        print(f"✓ Update tracked successfully!")
        print(f"  Commit ID: {result['commit_id']}")
        print(f"  Changes tracked: {result['changes_tracked']}")
        print(f"  Timestamp: {result['timestamp']}")
    else:
        print(f"✗ Failed to track update: {result.get('error')}")
    print()

    # Test 3: Get recent history
    print("📜 Test 3: Recent Change History (Last 5 Commits)")
    print("-" * 70)
    history = tracker.get_history(limit=5)

    if not history:
        print("No history yet. Make some changes in NestDB to see them here!")
    else:
        for i, commit in enumerate(history, 1):
            print(f"{i}. [{commit['timestamp']}] {commit['user_name']} - {commit['operation']}")
            print(f"   Table: {commit['table_name']} | Rows: {commit['rows_affected']}")

            if commit['changes']:
                print(f"   Changes:")
                for change in commit['changes'][:3]:  # Show first 3 changes
                    col = change['column_name']
                    old = change['old_value']
                    new = change['new_value']
                    print(f"     • {col}: {old} → {new}")

                if len(commit['changes']) > 3:
                    print(f"     ... and {len(commit['changes']) - 3} more")
            print()

    # Test 4: Verify changelog database structure
    print("🗄️  Test 4: Verifying Changelog Database Structure")
    print("-" * 70)

    conn = sqlite3.connect(str(tracker.changelog_db))
    cursor = conn.cursor()

    # Check tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]

    required_tables = ['commits', 'changes', 'users']
    for table in required_tables:
        if table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"✓ Table '{table}' exists ({count} rows)")
        else:
            print(f"✗ Table '{table}' MISSING!")

    conn.close()
    print()

    # Summary
    print("=" * 70)
    print("✅ TESTING COMPLETE")
    print("=" * 70)
    print()
    print("Next steps:")
    print("1. Start the backend: python -m uvicorn server.main:app --reload")
    print("2. Start the frontend: streamlit run frontend/app.py")
    print("3. Go to NestDB and make some changes")
    print("4. Check the 'Version History' tab to see detailed tracking")
    print()
    print("API endpoints to try:")
    print("- http://localhost:8000/db/changes/history")
    print("- http://localhost:8000/db/changes/stats")
    print()

if __name__ == "__main__":
    main()
