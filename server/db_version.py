"""
Database Versioning Service - Git-based SQLite Version Control

This module provides version control for the SQLite database using Git.
Every database change is automatically committed, allowing experts to:
- Track all modifications with timestamps and user info
- View diffs between versions
- Rollback to any previous state
- Maintain audit trails for scientific integrity

Architecture:
- bird_data_complete.db → Working database (fast queries)
- bird_data_complete.sql → SQL dump (git-tracked, human-readable diffs)
- .git/ → Full version history
- snapshots/ → Pre-rollback safety backups
"""

import os
import subprocess
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import sqlite3


class DatabaseVersionControl:
    """
    Manages Git-based versioning for SQLite databases.

    Workflow:
    1. Expert makes change via NestDB (insert/update/delete)
    2. DatabaseVersionControl.commit() is called
    3. System exports .db to .sql dump
    4. Git commits the .sql file with descriptive message
    5. Change is now tracked forever with rollback capability

    Educational Note:
    Why use SQL dumps instead of versioning the .db file directly?
    - SQLite .db files are binary (Git can't show meaningful diffs)
    - SQL dumps are plain text (Git shows exactly what changed)
    - Example diff: "+INSERT INTO observations VALUES (12345, 'Brown Pelican', 5000);"
    """

    def __init__(self, db_path: str, expert_email: str = "system", expert_name: str = None):
        """
        Initialize version control for a database.

        Args:
            db_path: Path to SQLite database file (e.g., data/bird_data_complete.db)
            expert_email: Email/username of the expert making changes (for commit attribution)
            expert_name: Full name of the expert (optional, extracted from email if not provided)
        """
        self.db_path = Path(db_path).resolve()
        self.db_dir = self.db_path.parent
        self.db_name = self.db_path.stem  # "bird_data_complete"
        self.sql_dump_path = self.db_dir / f"{self.db_name}.sql"
        self.snapshot_dir = self.db_dir / "snapshots"
        self.expert_email = expert_email
        self.expert_name = expert_name or self._extract_name_from_email(expert_email)

        # Ensure database exists
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")

        # Create snapshot directory if it doesn't exist
        self.snapshot_dir.mkdir(exist_ok=True)

        # Initialize Git repo if not already initialized
        self._init_git_repo()

    def _init_git_repo(self):
        """
        Initialize Git repository in the database directory if not already present.

        Educational Note:
        This is like running "git init" in the data/ folder.
        We do this automatically so experts don't need to know Git commands.
        """
        git_dir = self.db_dir / ".git"

        if not git_dir.exists():
            print(f"Initializing Git repository in {self.db_dir}")
            subprocess.run(
                ["git", "init"],
                cwd=self.db_dir,
                check=True,
                capture_output=True
            )

            # Configure Git user if not already set
            # This prevents "Please tell me who you are" errors
            subprocess.run(
                ["git", "config", "user.email", "nestscope@system.local"],
                cwd=self.db_dir,
                capture_output=True
            )
            subprocess.run(
                ["git", "config", "user.name", "NestScope System"],
                cwd=self.db_dir,
                capture_output=True
            )

            # Create .gitignore to exclude binary .db files (we only track .sql dumps)
            gitignore_path = self.db_dir / ".gitignore"
            if not gitignore_path.exists():
                gitignore_path.write_text("*.db\nsnapshots/\n__pycache__/\n")

            print("Git repository initialized successfully")

    def _extract_name_from_email(self, email: str) -> str:
        """
        Extract a display name from an email address.

        Examples:
            "olisemeka.nmarkwe@selu.edu" → "Olisemeka Nmarkwe"
            "system" → "NestScope System"
            "anonymous" → "Anonymous User"
        """
        if email == "system":
            return "NestScope System"

        if email == "anonymous" or not email:
            return "Anonymous User"

        # Get part before @
        local_part = email.split('@')[0]

        # Replace dots and underscores with spaces, then title case
        name = local_part.replace('.', ' ').replace('_', ' ').title()

        return name

    def _export_db_to_sql(self) -> bool:
        """
        Export SQLite database to SQL dump file.

        This creates a human-readable text file with all CREATE and INSERT statements.
        Git can diff this file to show exactly what changed.

        Educational Note:
        This is equivalent to running: sqlite3 bird_data_complete.db .dump > bird_data_complete.sql
        The .dump command exports the entire database schema and data as SQL statements.

        Returns:
            True if export succeeded, False otherwise
        """
        try:
            print(f"Exporting database to {self.sql_dump_path}")

            # Use Python's sqlite3 library to dump database
            conn = sqlite3.connect(str(self.db_path))

            with open(self.sql_dump_path, 'w', encoding='utf-8') as f:
                for line in conn.iterdump():
                    f.write(f'{line}\n')

            conn.close()

            print(f"Database exported successfully ({self.sql_dump_path.stat().st_size} bytes)")
            return True

        except Exception as e:
            print(f"Failed to export database: {e}")
            return False

    def commit(self, message: str, details: Optional[Dict[str, Any]] = None, skip_timestamp: bool = False, expert_picture: Optional[str] = None) -> Dict[str, Any]:
        """
        Commit current database state to Git with descriptive message.

        This is the main function called after every database modification.
        It captures a snapshot of the database state and stores it in Git history.

        Args:
            message: Human-readable commit message (e.g., "Updated 5 Brown Pelican counts")
            details: Optional dict with additional context (table, rows_affected, operation, etc.)
            skip_timestamp: If True, don't prepend timestamp to message (for manual checkpoints)

        Returns:
            Dictionary with success status, commit hash, and timestamp

        Example:
            version_control.commit(
                message="Corrected species classification for Queen Bess 2021",
                details={
                    "table": "observations",
                    "rows_affected": 12,
                    "operation": "UPDATE",
                    "expert": "sarah.chen@waterinstitute.org"
                }
            )
        """
        try:
            # Step 1: Export database to SQL dump
            if not self._export_db_to_sql():
                return {
                    "success": False,
                    "error": "Failed to export database to SQL"
                }

            # Step 2: Stage the SQL dump file for commit
            subprocess.run(
                ["git", "add", self.sql_dump_path.name],
                cwd=self.db_dir,
                check=True,
                capture_output=True
            )

            # Step 2.5: Check if there are any staged changes
            diff_check = subprocess.run(
                ["git", "diff", "--cached", "--quiet"],
                cwd=self.db_dir,
                capture_output=True
            )

            # If diff_check returns 0, there are NO staged changes
            if diff_check.returncode == 0:
                return {
                    "success": True,
                    "message": "No changes to commit (database unchanged)",
                    "no_changes": True
                }

            # Step 3: Build commit message with metadata
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # For manual checkpoints, skip timestamp prefix (it's redundant with Git's own timestamp)
            if skip_timestamp:
                commit_msg = message
            else:
                commit_msg = f"[{timestamp}] {message}"

            if details:
                commit_msg += f"\n\nDetails:"
                for key, value in details.items():
                    commit_msg += f"\n  {key}: {value}"

            # Add expert attribution
            commit_msg += f"\n\nExpert: {self.expert_name}"
            if self.expert_email != "system":
                commit_msg += f" <{self.expert_email}>"

            # Store expert picture URL in commit message for display in history
            if expert_picture:
                commit_msg += f"\nPicture: {expert_picture}"

            # Step 4: Set Git author to expert for this commit
            # This overrides the default "NestScope System" for manual checkpoints
            env = os.environ.copy()
            env['GIT_AUTHOR_NAME'] = self.expert_name
            env['GIT_AUTHOR_EMAIL'] = self.expert_email
            env['GIT_COMMITTER_NAME'] = self.expert_name
            env['GIT_COMMITTER_EMAIL'] = self.expert_email

            # Step 5: Commit to Git
            result = subprocess.run(
                ["git", "commit", "-m", commit_msg],
                cwd=self.db_dir,
                env=env,
                check=False,  # Don't raise exception immediately, we'll handle errors manually
                capture_output=True,
                text=True
            )

            # Check for errors manually
            if result.returncode != 0:
                # Check if it's just "nothing to commit"
                combined_output = (result.stdout or "") + (result.stderr or "")
                if "nothing to commit" in combined_output or "working tree clean" in combined_output:
                    return {
                        "success": True,
                        "message": "No changes to commit (database unchanged)",
                        "no_changes": True
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Git commit failed: {result.stderr or result.stdout or 'Unknown error'}"
                    }

            # Step 5: Get commit hash for tracking
            commit_hash = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.db_dir,
                capture_output=True,
                text=True,
                check=True
            ).stdout.strip()

            print(f"Database committed successfully: {commit_hash[:8]}")

            return {
                "success": True,
                "commit_hash": commit_hash,
                "commit_hash_short": commit_hash[:8],
                "timestamp": timestamp,
                "message": message
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Commit failed: {str(e)}"
            }

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get commit history for the database.

        Returns a list of commits with metadata, newest first.
        This powers the "Version History" tab in NestDB.

        Args:
            limit: Maximum number of commits to return (default: 50)

        Returns:
            List of commit dictionaries with hash, message, author, date, picture (if available)

        Educational Note:
        This is equivalent to "git log" but parsed into a Python-friendly format.
        The --pretty=format option customizes the output to include specific fields.
        """
        try:
            # Format: commit_hash|author|date|message
            result = subprocess.run(
                [
                    "git", "log",
                    f"-{limit}",
                    "--pretty=format:%H|%an|%ad|%s",
                    "--date=format:%Y-%m-%d %H:%M:%S",
                    "--", self.sql_dump_path.name
                ],
                cwd=self.db_dir,
                capture_output=True,
                text=True,
                check=True
            )

            commits = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue

                parts = line.split('|', 3)
                if len(parts) == 4:
                    commit_hash = parts[0]
                    commit_data = {
                        "hash": commit_hash,
                        "hash_short": commit_hash[:8],
                        "author": parts[1],
                        "date": parts[2],
                        "message": parts[3]
                    }

                    # Extract full commit message body with details
                    try:
                        # Get full commit message body
                        body_result = subprocess.run(
                            ["git", "show", "-s", "--format=%b", commit_hash],
                            cwd=self.db_dir,
                            capture_output=True,
                            text=True,
                            check=True
                        )

                        # Parse the body for structured details
                        body_text = body_result.stdout.strip()
                        commit_data["details"] = {}
                        commit_data["full_message"] = body_text

                        # Extract structured details (operation, table, rows_affected, query, etc.)
                        current_section = None
                        for body_line in body_text.split('\n'):
                            if body_line.startswith('Details:'):
                                current_section = 'details'
                                continue
                            elif body_line.startswith('Expert:'):
                                current_section = None
                                continue
                            elif body_line.startswith('Picture: '):
                                commit_data["picture"] = body_line.replace('Picture: ', '').strip()
                                continue

                            # Parse detail lines (e.g., "  operation: SQL_QUERY")
                            if current_section == 'details' and ':' in body_line:
                                key_value = body_line.strip().split(':', 1)
                                if len(key_value) == 2:
                                    key = key_value[0].strip()
                                    value = key_value[1].strip()
                                    commit_data["details"][key] = value
                    except:
                        # If parsing fails, at least we have the basic message
                        commit_data["details"] = {}
                        commit_data["full_message"] = ""

                    commits.append(commit_data)

            return commits

        except subprocess.CalledProcessError as e:
            print(f"Failed to get history: {e}")
            return []

    def get_diff(self, commit_hash: Optional[str] = None) -> str:
        """
        Get diff showing what changed in a specific commit.

        Args:
            commit_hash: Hash of commit to diff (default: latest commit vs working tree)

        Returns:
            Diff string showing added/removed SQL statements

        Educational Note:
        This shows the actual SQL statements that changed.
        Example output:
            +INSERT INTO observations VALUES (12345, 'Brown Pelican', 5000);
            -INSERT INTO observations VALUES (12345, 'Brown Pelican', 4800);

        The + means "added" and - means "removed", so this shows a count was updated from 4800 to 5000.
        """
        try:
            if commit_hash:
                # Diff for specific commit
                result = subprocess.run(
                    ["git", "show", commit_hash, "--", self.sql_dump_path.name],
                    cwd=self.db_dir,
                    capture_output=True,
                    text=True,
                    check=True
                )
            else:
                # Diff for latest changes (working tree vs HEAD)
                result = subprocess.run(
                    ["git", "diff", "HEAD", "--", self.sql_dump_path.name],
                    cwd=self.db_dir,
                    capture_output=True,
                    text=True,
                    check=True
                )

            return result.stdout

        except subprocess.CalledProcessError as e:
            return f"Failed to get diff: {e}"

    def create_snapshot(self, label: str = "") -> Dict[str, Any]:
        """
        Create a snapshot backup of the current database.

        This creates a full copy of the .db file before major operations like rollbacks.
        It's a safety net - if something goes wrong, we can always restore from snapshot.

        Args:
            label: Optional label for snapshot (e.g., "pre-rollback", "before-bulk-edit")

        Returns:
            Dictionary with snapshot path and timestamp
        """
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            label_str = f"_{label}" if label else ""
            snapshot_path = self.snapshot_dir / f"{timestamp}{label_str}_{self.db_name}.db"

            # Copy database file
            shutil.copy2(self.db_path, snapshot_path)

            print(f"Snapshot created: {snapshot_path}")

            return {
                "success": True,
                "snapshot_path": str(snapshot_path),
                "timestamp": timestamp
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to create snapshot: {e}"
            }

    def rollback_to_commit(self, commit_hash: str) -> Dict[str, Any]:
        """
        Rollback database to a specific commit.

        **WARNING**: This is a destructive operation. It will:
        1. Create a safety snapshot of current database
        2. Restore the SQL dump from the specified commit
        3. Re-import that SQL dump into the database
        4. Commit the rollback as a new commit (preserving history)

        Args:
            commit_hash: Hash of commit to rollback to

        Returns:
            Dictionary with success status and details

        Educational Note:
        This is like "undo" but for an entire database. We don't delete history
        (that would be bad for scientific integrity). Instead, we create a NEW
        commit that restores the old state. This way, we can see:
        - What the database looked like before
        - What changes were rolled back
        - When and why the rollback happened
        """
        try:
            # Step 1: Create safety snapshot
            print(f"Creating safety snapshot before rollback...")
            snapshot_result = self.create_snapshot(label="pre-rollback")

            if not snapshot_result.get("success"):
                return {
                    "success": False,
                    "error": "Failed to create safety snapshot"
                }

            # Step 2: Checkout the SQL dump from the target commit
            print(f"Checking out SQL dump from commit {commit_hash[:8]}...")
            subprocess.run(
                ["git", "checkout", commit_hash, "--", self.sql_dump_path.name],
                cwd=self.db_dir,
                check=True,
                capture_output=True
            )

            # Step 3: Drop and recreate database from SQL dump
            print(f"Restoring database from SQL dump...")

            # Remove current database
            if self.db_path.exists():
                self.db_path.unlink()

            # Re-import from SQL dump using Python's sqlite3
            conn = sqlite3.connect(str(self.db_path))
            with open(self.sql_dump_path, 'r', encoding='utf-8') as f:
                sql_script = f.read()
                conn.executescript(sql_script)
            conn.close()

            # Step 4: Commit the rollback
            print(f"Committing rollback...")
            commit_result = self.commit(
                message=f"Rollback to commit {commit_hash[:8]}",
                details={
                    "operation": "ROLLBACK",
                    "target_commit": commit_hash,
                    "snapshot": snapshot_result["snapshot_path"]
                }
            )

            if not commit_result.get("success"):
                return {
                    "success": False,
                    "error": "Rollback succeeded but failed to commit: " + commit_result.get("error", "")
                }

            print(f"Rollback completed successfully")

            return {
                "success": True,
                "message": f"Rolled back to commit {commit_hash[:8]}",
                "snapshot_path": snapshot_result["snapshot_path"],
                "new_commit": commit_result["commit_hash_short"]
            }

        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "error": f"Rollback failed: {e.stderr.decode() if e.stderr else str(e)}"
            }

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the version control history.

        Returns:
            Dictionary with total commits, date range, database size, etc.
        """
        try:
            # Count total commits
            result = subprocess.run(
                ["git", "rev-list", "--count", "HEAD", "--", self.sql_dump_path.name],
                cwd=self.db_dir,
                capture_output=True,
                text=True,
                check=True
            )
            total_commits = int(result.stdout.strip())

            # Get first commit date
            result = subprocess.run(
                ["git", "log", "--reverse", "--pretty=format:%ad", "--date=format:%Y-%m-%d %H:%M:%S", "-1", "--", self.sql_dump_path.name],
                cwd=self.db_dir,
                capture_output=True,
                text=True,
                check=True
            )
            first_commit_date = result.stdout.strip() if result.stdout.strip() else "N/A"

            # Get database size
            db_size_mb = self.db_path.stat().st_size / (1024 * 1024)

            # Count snapshots
            snapshots = list(self.snapshot_dir.glob("*.db"))

            return {
                "success": True,
                "total_commits": total_commits,
                "first_commit_date": first_commit_date,
                "database_size_mb": round(db_size_mb, 2),
                "snapshot_count": len(snapshots),
                "current_branch": "main"
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get stats: {e}"
            }


# ============================================================================
# Convenience Functions for Integration
# ============================================================================

def auto_commit_wrapper(func):
    """
    Decorator to automatically commit database changes after a function executes.

    This wraps existing database functions (update_table_row, insert_table_row, etc.)
    to automatically version changes without modifying their code.

    Educational Note:
    This is a Python decorator - a function that wraps another function.
    It's like putting a "version control layer" around every database write.

    Usage:
        @auto_commit_wrapper
        def update_table_row(table, row_id, updates):
            # ... existing code ...
            return result

    Now every time update_table_row() is called, it automatically commits to Git!
    """
    def wrapper(*args, **kwargs):
        # Execute the original function
        result = func(*args, **kwargs)

        # If successful, commit the change
        if isinstance(result, dict) and result.get("success"):
            try:
                # Extract database path from environment or config
                from config import get_config
                config = get_config()
                db_path = config.get("database", {}).get("path", "data/bird_data_complete.db")

                # Get expert email from kwargs or use system default
                expert_email = kwargs.get("expert_email", "system")

                # Initialize version control
                vc = DatabaseVersionControl(db_path, expert_email)

                # Build commit message from function name and result
                operation = func.__name__.replace("_", " ").title()
                message = f"{operation}"

                # Add details if available
                details = {
                    "operation": func.__name__.upper(),
                }
                if "table" in kwargs:
                    details["table"] = kwargs["table"]
                if "rows_affected" in result:
                    details["rows_affected"] = result["rows_affected"]

                # Commit the change
                commit_result = vc.commit(message, details)

                # Add commit info to result
                result["version_control"] = commit_result

            except Exception as e:
                # Don't fail the original operation if versioning fails
                # Just log the error
                print(f"Warning: Auto-commit failed: {e}")
                result["version_control"] = {
                    "success": False,
                    "error": str(e)
                }

        return result

    return wrapper


# ============================================================================
# Testing and Demo
# ============================================================================

if __name__ == "__main__":
    """
    Demo script showing how to use DatabaseVersionControl.

    Run this with: python server/db_version.py
    """
    print("=== Database Version Control Demo ===\n")

    # Initialize version control
    db_path = "data/bird_data_complete.db"
    vc = DatabaseVersionControl(db_path, expert_email="demo@nestscope.org")

    # Show stats
    print("1. Version Control Statistics:")
    stats = vc.get_stats()
    if stats.get("success"):
        print(f"   Total commits: {stats['total_commits']}")
        print(f"   First commit: {stats['first_commit_date']}")
        print(f"   Database size: {stats['database_size_mb']} MB")
        print(f"   Snapshots: {stats['snapshot_count']}")
    print()

    # Show recent history
    print("2. Recent Commit History:")
    history = vc.get_history(limit=5)
    for commit in history:
        print(f"   [{commit['hash_short']}] {commit['date']} - {commit['message']}")
    print()

    # Create a snapshot
    print("3. Creating snapshot...")
    snapshot = vc.create_snapshot(label="demo")
    if snapshot.get("success"):
        print(f"   Snapshot created: {snapshot['snapshot_path']}")
    print()

    print("=== Demo Complete ===")
