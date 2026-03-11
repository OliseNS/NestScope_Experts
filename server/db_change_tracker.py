"""
Enhanced Database Change Tracker - Row-Level Change Detection

This module provides granular tracking of database changes at the row and column level.
It works alongside Git-based version control to provide detailed change logs.

Why we need this:
- Git tracks SQL dumps (good for full backups)
- This tracks individual changes (good for auditing and detailed history)
- Together, they provide complete visibility into what changed

Educational Note:
Think of Git as a "save point" system (like in video games) and this tracker
as a "move history" system (like in chess). Both are useful for different purposes.
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path


class ChangeTracker:
    """
    Tracks database changes at the row and column level.

    Creates a separate tracking database that stores:
    - What changed (table, column, old value, new value)
    - Who changed it (user email, name, picture)
    - When it changed (timestamp)
    - Why it changed (operation context)

    This provides a queryable audit trail that's easier to search and display
    than Git commit logs.
    """

    def __init__(self, db_path: str):
        """
        Initialize change tracker.

        Args:
            db_path: Path to the main database (e.g., data/bird_data_complete.db)
        """
        self.db_path = Path(db_path).resolve()
        self.db_dir = self.db_path.parent
        self.db_name = self.db_path.stem

        # Change log database stored alongside main database
        self.changelog_db = self.db_dir / f"{self.db_name}_changelog.db"

        # Initialize changelog database
        self._init_changelog_db()

    def _init_changelog_db(self):
        """
        Create changelog database with tracking tables.

        Tables:
        - changes: Individual column-level changes
        - commits: Groups of changes (like Git commits but with more metadata)
        - users: Cached user info for fast lookups
        """
        conn = sqlite3.connect(str(self.changelog_db))
        cursor = conn.cursor()

        # Table: commits (one per operation)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS commits (
                commit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                commit_hash TEXT,
                timestamp TEXT NOT NULL,
                user_email TEXT NOT NULL,
                user_name TEXT,
                user_picture TEXT,
                operation TEXT NOT NULL,
                table_name TEXT NOT NULL,
                rows_affected INTEGER,
                query TEXT,
                message TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Table: changes (one per column changed)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS changes (
                change_id INTEGER PRIMARY KEY AUTOINCREMENT,
                commit_id INTEGER NOT NULL,
                table_name TEXT NOT NULL,
                row_identifier TEXT NOT NULL,
                column_name TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT,
                value_type TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (commit_id) REFERENCES commits(commit_id) ON DELETE CASCADE
            )
        ''')

        # Table: users (cached user info)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                email TEXT PRIMARY KEY,
                name TEXT,
                picture TEXT,
                first_seen TEXT,
                last_seen TEXT,
                change_count INTEGER DEFAULT 0
            )
        ''')

        # Indexes for fast queries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_commits_timestamp ON commits(timestamp DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_commits_user ON commits(user_email)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_commits_table ON commits(table_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_changes_commit ON changes(commit_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_changes_table_col ON changes(table_name, column_name)')

        conn.commit()
        conn.close()

    def track_update(
        self,
        table_name: str,
        row_id: Dict[str, Any],
        old_values: Dict[str, Any],
        new_values: Dict[str, Any],
        user_email: str,
        user_name: str = None,
        user_picture: str = None,
        commit_hash: str = None
    ) -> Dict[str, Any]:
        """
        Track an UPDATE operation with before/after values.

        Args:
            table_name: Name of table that was updated
            row_id: Primary key(s) identifying the row (e.g., {"id": 123})
            old_values: Values before update (e.g., {"count": 100, "species": "Pelican"})
            new_values: Values after update (e.g., {"count": 150, "species": "Pelican"})
            user_email: Email of user who made the change
            user_name: Full name of user (optional)
            user_picture: Profile picture URL (optional)
            commit_hash: Git commit hash (optional, from version control)

        Returns:
            Dictionary with commit_id and number of changes tracked
        """
        conn = sqlite3.connect(str(self.changelog_db))
        cursor = conn.cursor()

        try:
            timestamp = datetime.now().isoformat()

            # Update user cache
            self._update_user_cache(cursor, user_email, user_name, user_picture, timestamp)

            # Create commit record
            cursor.execute('''
                INSERT INTO commits (
                    commit_hash, timestamp, user_email, user_name, user_picture,
                    operation, table_name, rows_affected, message
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                commit_hash,
                timestamp,
                user_email,
                user_name,
                user_picture,
                'UPDATE',
                table_name,
                1,
                f"Updated row in {table_name}"
            ))

            commit_id = cursor.lastrowid

            # Track each column that changed
            row_identifier = json.dumps(row_id, sort_keys=True)
            changes_tracked = 0

            for col, new_val in new_values.items():
                old_val = old_values.get(col)

                # Only track if value actually changed
                if old_val != new_val:
                    cursor.execute('''
                        INSERT INTO changes (
                            commit_id, table_name, row_identifier,
                            column_name, old_value, new_value, value_type
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        commit_id,
                        table_name,
                        row_identifier,
                        col,
                        str(old_val) if old_val is not None else None,
                        str(new_val) if new_val is not None else None,
                        type(new_val).__name__
                    ))
                    changes_tracked += 1

            conn.commit()

            return {
                "success": True,
                "commit_id": commit_id,
                "changes_tracked": changes_tracked,
                "timestamp": timestamp
            }

        except Exception as e:
            conn.rollback()
            return {
                "success": False,
                "error": f"Failed to track changes: {e}"
            }
        finally:
            conn.close()

    def track_insert(
        self,
        table_name: str,
        row_data: Dict[str, Any],
        user_email: str,
        user_name: str = None,
        user_picture: str = None,
        commit_hash: str = None
    ) -> Dict[str, Any]:
        """
        Track an INSERT operation.

        Args:
            table_name: Name of table
            row_data: Values inserted (e.g., {"id": 123, "species": "Pelican", "count": 100})
            user_email: Email of user
            user_name: Full name (optional)
            user_picture: Profile picture (optional)
            commit_hash: Git commit hash (optional)

        Returns:
            Dictionary with commit_id
        """
        conn = sqlite3.connect(str(self.changelog_db))
        cursor = conn.cursor()

        try:
            timestamp = datetime.now().isoformat()

            # Update user cache
            self._update_user_cache(cursor, user_email, user_name, user_picture, timestamp)

            # Create commit record
            cursor.execute('''
                INSERT INTO commits (
                    commit_hash, timestamp, user_email, user_name, user_picture,
                    operation, table_name, rows_affected, message
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                commit_hash,
                timestamp,
                user_email,
                user_name,
                user_picture,
                'INSERT',
                table_name,
                1,
                f"Inserted row into {table_name}"
            ))

            commit_id = cursor.lastrowid

            # Track each column as a "new value"
            row_identifier = json.dumps({"row": "new"})  # No old ID since it's new

            for col, val in row_data.items():
                cursor.execute('''
                    INSERT INTO changes (
                        commit_id, table_name, row_identifier,
                        column_name, old_value, new_value, value_type
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    commit_id,
                    table_name,
                    row_identifier,
                    col,
                    None,  # No old value for inserts
                    str(val) if val is not None else None,
                    type(val).__name__
                ))

            conn.commit()

            return {
                "success": True,
                "commit_id": commit_id,
                "timestamp": timestamp
            }

        except Exception as e:
            conn.rollback()
            return {
                "success": False,
                "error": f"Failed to track insert: {e}"
            }
        finally:
            conn.close()

    def track_delete(
        self,
        table_name: str,
        row_id: Dict[str, Any],
        deleted_values: Dict[str, Any],
        user_email: str,
        user_name: str = None,
        user_picture: str = None,
        commit_hash: str = None
    ) -> Dict[str, Any]:
        """
        Track a DELETE operation.

        Args:
            table_name: Name of table
            row_id: Primary key(s) of deleted row
            deleted_values: Values that were deleted
            user_email: Email of user
            user_name: Full name (optional)
            user_picture: Profile picture (optional)
            commit_hash: Git commit hash (optional)

        Returns:
            Dictionary with commit_id
        """
        conn = sqlite3.connect(str(self.changelog_db))
        cursor = conn.cursor()

        try:
            timestamp = datetime.now().isoformat()

            # Update user cache
            self._update_user_cache(cursor, user_email, user_name, user_picture, timestamp)

            # Create commit record
            cursor.execute('''
                INSERT INTO commits (
                    commit_hash, timestamp, user_email, user_name, user_picture,
                    operation, table_name, rows_affected, message
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                commit_hash,
                timestamp,
                user_email,
                user_name,
                user_picture,
                'DELETE',
                table_name,
                1,
                f"Deleted row from {table_name}"
            ))

            commit_id = cursor.lastrowid

            # Track each column as a "deleted value"
            row_identifier = json.dumps(row_id, sort_keys=True)

            for col, val in deleted_values.items():
                cursor.execute('''
                    INSERT INTO changes (
                        commit_id, table_name, row_identifier,
                        column_name, old_value, new_value, value_type
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    commit_id,
                    table_name,
                    row_identifier,
                    col,
                    str(val) if val is not None else None,
                    None,  # No new value for deletes
                    type(val).__name__
                ))

            conn.commit()

            return {
                "success": True,
                "commit_id": commit_id,
                "timestamp": timestamp
            }

        except Exception as e:
            conn.rollback()
            return {
                "success": False,
                "error": f"Failed to track delete: {e}"
            }
        finally:
            conn.close()

    def track_query(
        self,
        query: str,
        rows_affected: int,
        user_email: str,
        user_name: str = None,
        user_picture: str = None,
        commit_hash: str = None
    ) -> Dict[str, Any]:
        """
        Track a custom SQL query.

        Args:
            query: SQL query that was executed
            rows_affected: Number of rows affected
            user_email: Email of user
            user_name: Full name (optional)
            user_picture: Profile picture (optional)
            commit_hash: Git commit hash (optional)

        Returns:
            Dictionary with commit_id
        """
        conn = sqlite3.connect(str(self.changelog_db))
        cursor = conn.cursor()

        try:
            timestamp = datetime.now().isoformat()

            # Update user cache
            self._update_user_cache(cursor, user_email, user_name, user_picture, timestamp)

            # Detect operation type from query
            query_upper = query.upper().strip()
            operation = 'QUERY'
            table_name = 'multiple'

            if query_upper.startswith('INSERT'):
                operation = 'INSERT'
            elif query_upper.startswith('UPDATE'):
                operation = 'UPDATE'
            elif query_upper.startswith('DELETE'):
                operation = 'DELETE'
            elif query_upper.startswith('CREATE'):
                operation = 'CREATE'
            elif query_upper.startswith('DROP'):
                operation = 'DROP'
            elif query_upper.startswith('ALTER'):
                operation = 'ALTER'

            # Create commit record
            cursor.execute('''
                INSERT INTO commits (
                    commit_hash, timestamp, user_email, user_name, user_picture,
                    operation, table_name, rows_affected, query, message
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                commit_hash,
                timestamp,
                user_email,
                user_name,
                user_picture,
                operation,
                table_name,
                rows_affected,
                query,
                f"Executed {operation} query"
            ))

            commit_id = cursor.lastrowid
            conn.commit()

            return {
                "success": True,
                "commit_id": commit_id,
                "timestamp": timestamp
            }

        except Exception as e:
            conn.rollback()
            return {
                "success": False,
                "error": f"Failed to track query: {e}"
            }
        finally:
            conn.close()

    def _update_user_cache(
        self,
        cursor: sqlite3.Cursor,
        email: str,
        name: str = None,
        picture: str = None,
        timestamp: str = None
    ):
        """
        Update or create user cache entry.

        This keeps a denormalized copy of user info for fast lookups
        without needing to join with the users.db authentication database.
        """
        cursor.execute('SELECT email FROM users WHERE email = ?', (email,))
        exists = cursor.fetchone()

        if exists:
            # Update existing user
            cursor.execute('''
                UPDATE users
                SET name = COALESCE(?, name),
                    picture = COALESCE(?, picture),
                    last_seen = ?,
                    change_count = change_count + 1
                WHERE email = ?
            ''', (name, picture, timestamp, email))
        else:
            # Create new user
            cursor.execute('''
                INSERT INTO users (email, name, picture, first_seen, last_seen, change_count)
                VALUES (?, ?, ?, ?, ?, 1)
            ''', (email, name, picture, timestamp, timestamp))

    def get_history(
        self,
        limit: int = 50,
        table_name: str = None,
        user_email: str = None,
        operation: str = None
    ) -> List[Dict[str, Any]]:
        """
        Get change history with filters.

        Args:
            limit: Maximum number of commits to return
            table_name: Filter by table (optional)
            user_email: Filter by user (optional)
            operation: Filter by operation type (optional)

        Returns:
            List of commits with change details
        """
        conn = sqlite3.connect(str(self.changelog_db))
        cursor = conn.cursor()

        # Build query with filters
        query = '''
            SELECT
                c.commit_id,
                c.commit_hash,
                c.timestamp,
                c.user_email,
                c.user_name,
                c.user_picture,
                c.operation,
                c.table_name,
                c.rows_affected,
                c.query,
                c.message
            FROM commits c
            WHERE 1=1
        '''
        params = []

        if table_name:
            query += ' AND c.table_name = ?'
            params.append(table_name)

        if user_email:
            query += ' AND c.user_email = ?'
            params.append(user_email)

        if operation:
            query += ' AND c.operation = ?'
            params.append(operation)

        query += ' ORDER BY c.timestamp DESC LIMIT ?'
        params.append(limit)

        cursor.execute(query, params)
        commits = []

        for row in cursor.fetchall():
            commit_id = row[0]
            commit = {
                'commit_id': commit_id,
                'commit_hash': row[1],
                'timestamp': row[2],
                'user_email': row[3],
                'user_name': row[4],
                'user_picture': row[5],
                'operation': row[6],
                'table_name': row[7],
                'rows_affected': row[8],
                'query': row[9],
                'message': row[10],
                'changes': []
            }

            # Get detailed changes for this commit
            cursor.execute('''
                SELECT
                    change_id,
                    table_name,
                    row_identifier,
                    column_name,
                    old_value,
                    new_value,
                    value_type
                FROM changes
                WHERE commit_id = ?
                ORDER BY change_id
            ''', (commit_id,))

            for change_row in cursor.fetchall():
                commit['changes'].append({
                    'change_id': change_row[0],
                    'table_name': change_row[1],
                    'row_identifier': change_row[2],
                    'column_name': change_row[3],
                    'old_value': change_row[4],
                    'new_value': change_row[5],
                    'value_type': change_row[6]
                })

            commits.append(commit)

        conn.close()
        return commits

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about tracked changes.

        Returns:
            Dictionary with total commits, users, tables affected, etc.
        """
        conn = sqlite3.connect(str(self.changelog_db))
        cursor = conn.cursor()

        # Total commits
        cursor.execute('SELECT COUNT(*) FROM commits')
        total_commits = cursor.fetchone()[0]

        # Total changes (individual column changes)
        cursor.execute('SELECT COUNT(*) FROM changes')
        total_changes = cursor.fetchone()[0]

        # Unique users
        cursor.execute('SELECT COUNT(DISTINCT user_email) FROM commits')
        unique_users = cursor.fetchone()[0]

        # Unique tables affected
        cursor.execute('SELECT COUNT(DISTINCT table_name) FROM commits')
        unique_tables = cursor.fetchone()[0]

        # Operation breakdown
        cursor.execute('''
            SELECT operation, COUNT(*) as count
            FROM commits
            GROUP BY operation
            ORDER BY count DESC
        ''')
        operations = {row[0]: row[1] for row in cursor.fetchall()}

        # Most active user
        cursor.execute('''
            SELECT user_email, user_name, COUNT(*) as count
            FROM commits
            GROUP BY user_email
            ORDER BY count DESC
            LIMIT 1
        ''')
        most_active = cursor.fetchone()

        # Most modified table
        cursor.execute('''
            SELECT table_name, COUNT(*) as count
            FROM commits
            GROUP BY table_name
            ORDER BY count DESC
            LIMIT 1
        ''')
        most_modified = cursor.fetchone()

        conn.close()

        return {
            'total_commits': total_commits,
            'total_changes': total_changes,
            'unique_users': unique_users,
            'unique_tables': unique_tables,
            'operations': operations,
            'most_active_user': {
                'email': most_active[0],
                'name': most_active[1],
                'commits': most_active[2]
            } if most_active else None,
            'most_modified_table': {
                'name': most_modified[0],
                'commits': most_modified[1]
            } if most_modified else None
        }


# ============================================================================
# Testing and Demo
# ============================================================================

if __name__ == "__main__":
    """
    Demo script showing how to use ChangeTracker.

    Run this with: python server/db_change_tracker.py
    """
    print("=== Change Tracker Demo ===\n")

    # Initialize tracker
    tracker = ChangeTracker("data/bird_data_complete.db")

    # Track a sample update
    print("1. Tracking an UPDATE operation...")
    result = tracker.track_update(
        table_name="observations",
        row_id={"id": 12345},
        old_values={"species": "Brown Pelican", "count": 100},
        new_values={"species": "Brown Pelican", "count": 150},
        user_email="demo@nestscope.org",
        user_name="Demo User",
        user_picture="https://example.com/avatar.jpg"
    )
    print(f"   Result: {result}\n")

    # Get statistics
    print("2. Change Statistics:")
    stats = tracker.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    print()

    # Get recent history
    print("3. Recent Changes:")
    history = tracker.get_history(limit=5)
    for commit in history:
        print(f"   [{commit['timestamp']}] {commit['user_name']} - {commit['message']}")
        for change in commit['changes']:
            print(f"      {change['column_name']}: {change['old_value']} → {change['new_value']}")
    print()

    print("=== Demo Complete ===")
