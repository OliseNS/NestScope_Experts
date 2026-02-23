#!/usr/bin/env python3
"""
Access Database to SQLite Migration Tool

This script migrates an Access database (.accdb or .mdb) to SQLite and generates
metadata JSON file with schema information.

Uses mdbtools (Linux command-line tools) to read Access databases without
requiring Windows ODBC drivers.

Usage:
    python migrate_access_to_sqlite.py [options]

Example:
    python migrate_access_to_sqlite.py --input data.accdb --output data.db
"""

import subprocess
import sqlite3
import json
import os
import sys
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any
import argparse


class AccessToSQLiteMigrator:
    """Migrates Access databases to SQLite and generates metadata."""

    def __init__(self, accdb_path: str, sqlite_path: str, metadata_path: str = None):
        """
        Initialize the migrator.

        Args:
            accdb_path: Path to the Access database (.accdb or .mdb)
            sqlite_path: Path for the output SQLite database
            metadata_path: Path for the output metadata JSON (optional)
        """
        self.accdb_path = Path(accdb_path)
        self.sqlite_path = Path(sqlite_path)

        if metadata_path:
            self.metadata_path = Path(metadata_path)
        else:
            # Default: same directory as SQLite DB with _metadata.json suffix
            self.metadata_path = self.sqlite_path.with_suffix('').with_suffix('.metadata.json')

        # Check if Access database exists
        if not self.accdb_path.exists():
            raise FileNotFoundError(f"Access database not found: {self.accdb_path}")

        # Check if mdbtools is installed
        if not self._check_mdbtools():
            raise RuntimeError(
                "mdbtools not found. Install with: sudo apt-get install mdbtools"
            )

    def _check_mdbtools(self) -> bool:
        """Check if mdbtools is installed."""
        try:
            subprocess.run(
                ['mdb-tables', '--help'],
                capture_output=True,
                check=False
            )
            return True
        except FileNotFoundError:
            return False

    def _run_mdb_command(self, command: List[str]) -> str:
        """
        Run an mdbtools command and return output.

        Args:
            command: Command to run (e.g., ['mdb-tables', 'database.accdb'])

        Returns:
            Command output as string
        """
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Error running command {' '.join(command)}: {e.stderr}")
            raise

    def get_tables(self) -> List[str]:
        """
        Get list of all tables in the Access database.

        Returns:
            List of table names
        """
        print(f"📋 Reading tables from {self.accdb_path.name}...")

        output = self._run_mdb_command([
            'mdb-tables',
            '-1',  # One table per line
            str(self.accdb_path)
        ])

        # Split by newlines and filter out empty strings
        tables = [t.strip() for t in output.split('\n') if t.strip()]

        print(f"✓ Found {len(tables)} tables")
        return tables

    def get_table_schema(self, table_name: str) -> Tuple[List[str], Dict[str, str]]:
        """
        Get schema information for a table.

        Uses mdb-export to get actual column names (more reliable than mdb-schema
        for handling special characters).

        Args:
            table_name: Name of the table

        Returns:
            Tuple of (column_names, column_types_dict)
        """
        # Get column names from the first line of mdb-export (CSV header)
        # This is more reliable than mdb-schema for special characters
        # Note: mdb-export outputs headers by default; -H would suppress them
        csv_output = self._run_mdb_command([
            'mdb-export',
            str(self.accdb_path),
            table_name
        ])

        # Parse the header line to get column names
        lines = csv_output.split('\n')
        if not lines:
            return [], {}

        header_line = lines[0]
        columns = []
        current_field = []
        in_quotes = False

        # Parse CSV header (handles quoted column names)
        for char in header_line:
            if char == '"':
                in_quotes = not in_quotes
            elif char == ',' and not in_quotes:
                col_name = ''.join(current_field).strip('"').strip()
                # Handle empty or duplicate column names
                if not col_name:
                    col_name = f"Column{len(columns) + 1}"
                # If column name already exists, make it unique
                original_col_name = col_name
                counter = 1
                while col_name in columns:
                    col_name = f"{original_col_name}_{counter}"
                    counter += 1
                columns.append(col_name)
                current_field = []
            else:
                current_field.append(char)

        # Add last column
        if current_field or header_line.endswith(','):
            col_name = ''.join(current_field).strip('"').strip()
            if not col_name:
                col_name = f"Column{len(columns) + 1}"
            # If column name already exists, make it unique
            original_col_name = col_name
            counter = 1
            while col_name in columns:
                col_name = f"{original_col_name}_{counter}"
                counter += 1
            columns.append(col_name)

        # Try to get type information from mdb-schema (but don't fail if it has issues)
        column_types = {}
        try:
            schema_sql = self._run_mdb_command([
                'mdb-schema',
                str(self.accdb_path),
                'sqlite',
                '-T', table_name
            ])

            # Extract type information if possible
            create_match = re.search(
                r'CREATE TABLE.*?\((.*?)\);',
                schema_sql,
                re.DOTALL | re.IGNORECASE
            )

            if create_match:
                column_defs = create_match.group(1)
                # Simple extraction of types (best effort)
                for col in columns:
                    # Look for this column in the schema
                    # Match patterns like: "ColName" TYPE, or [ColName] TYPE, or ColName TYPE
                    pattern = re.compile(
                        rf'["\[]?{re.escape(col)}["\]]?\s+(\w+)',
                        re.IGNORECASE
                    )
                    match = pattern.search(column_defs)
                    if match:
                        column_types[col] = match.group(1).upper()
        except Exception:
            # If schema parsing fails, just use TEXT for everything
            pass

        # Default to TEXT for any columns without type information
        for col in columns:
            if col not in column_types:
                column_types[col] = 'TEXT'

        return columns, column_types

    def export_table_data(self, table_name: str) -> List[List[Any]]:
        """
        Export all data from a table.

        Args:
            table_name: Name of the table to export

        Returns:
            List of rows (each row is a list of values)
        """
        # Export as CSV-like format
        csv_output = self._run_mdb_command([
            'mdb-export',
            str(self.accdb_path),
            table_name
        ])

        # Parse CSV output
        rows = []
        for line in csv_output.split('\n'):
            if not line.strip():
                continue

            # Simple CSV parsing (handles quoted fields)
            row = []
            current_field = []
            in_quotes = False

            for i, char in enumerate(line):
                if char == '"':
                    in_quotes = not in_quotes
                elif char == ',' and not in_quotes:
                    row.append(''.join(current_field))
                    current_field = []
                else:
                    current_field.append(char)

            # Add last field
            if current_field:
                row.append(''.join(current_field))

            rows.append(row)

        return rows

    def create_sqlite_table(self, conn: sqlite3.Connection, table_name: str,
                           columns: List[str], column_types: Dict[str, str]):
        """
        Create a table in the SQLite database.

        Args:
            conn: SQLite connection
            table_name: Name of the table to create
            columns: List of column names
            column_types: Dict mapping column names to SQL types
        """
        cursor = conn.cursor()

        # Build CREATE TABLE statement
        # Always escape column names to handle special characters (spaces, apostrophes, etc.)
        col_defs = []
        for col in columns:
            col_type = column_types.get(col, 'TEXT')
            # Always use double quotes for column names to handle any special characters
            # Replace any double quotes in column name with two double quotes (SQL escaping)
            col_escaped = col.replace('"', '""')
            col_defs.append(f'"{col_escaped}" {col_type}')

        create_sql = f'CREATE TABLE IF NOT EXISTS "{table_name}" (\n  '
        create_sql += ',\n  '.join(col_defs)
        create_sql += '\n);'

        cursor.execute(create_sql)
        conn.commit()

    def insert_table_data(self, conn: sqlite3.Connection, table_name: str,
                         columns: List[str], rows: List[List[Any]]):
        """
        Insert data into a SQLite table.

        Args:
            conn: SQLite connection
            table_name: Name of the table
            columns: List of column names
            rows: List of data rows (first row should be header)
        """
        if not rows or len(rows) < 2:
            print(f"  ⚠ No data to insert for table {table_name}")
            return

        cursor = conn.cursor()

        # Skip header row (first row from mdb-export)
        data_rows = rows[1:]

        # Build INSERT statement with proper escaping
        # Always escape column names to handle special characters
        col_names_escaped = [f'"{col.replace(chr(34), chr(34)+chr(34))}"' for col in columns]
        placeholders = ','.join(['?' for _ in columns])
        insert_sql = f'INSERT INTO "{table_name}" ({",".join(col_names_escaped)}) VALUES ({placeholders})'

        # Convert empty strings to None for better SQLite compatibility
        cleaned_rows = []
        for row in data_rows:
            cleaned_row = [val if val and val.strip() else None for val in row]
            # Ensure row has correct number of columns
            if len(cleaned_row) < len(columns):
                cleaned_row.extend([None] * (len(columns) - len(cleaned_row)))
            elif len(cleaned_row) > len(columns):
                cleaned_row = cleaned_row[:len(columns)]
            cleaned_rows.append(cleaned_row)

        try:
            cursor.executemany(insert_sql, cleaned_rows)
            conn.commit()
            print(f"  ✓ Inserted {len(cleaned_rows)} rows")
        except sqlite3.Error as e:
            print(f"  ✗ Error inserting data: {e}")
            conn.rollback()
            raise

    def migrate_table(self, conn: sqlite3.Connection, table_name: str) -> Dict[str, Any]:
        """
        Migrate a single table from Access to SQLite.

        Args:
            conn: SQLite connection
            table_name: Name of the table to migrate

        Returns:
            Dictionary with table metadata (row_count, columns)
        """
        print(f"\n📦 Migrating table: {table_name}")

        # Get schema
        columns, column_types = self.get_table_schema(table_name)
        print(f"  Schema: {len(columns)} columns")

        # Show any special character warnings
        special_chars_found = []
        for col in columns:
            if any(c in col for c in ["'", "?", "/", " "]):
                special_chars_found.append(col)

        if special_chars_found:
            print(f"  ℹ Special characters in {len(special_chars_found)} column names (will be escaped)")

        # Create table
        self.create_sqlite_table(conn, table_name, columns, column_types)
        print(f"  ✓ Created table structure")

        # Export and insert data
        rows = self.export_table_data(table_name)
        self.insert_table_data(conn, table_name, columns, rows)

        # Count rows to verify
        cursor = conn.cursor()
        cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
        row_count = cursor.fetchone()[0]

        return {
            'row_count': row_count,
            'columns': columns
        }

    def generate_metadata(self, conn: sqlite3.Connection,
                         tables_info: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate metadata JSON for the database.

        Args:
            conn: SQLite connection
            tables_info: Dictionary mapping table names to their metadata

        Returns:
            Complete metadata dictionary
        """
        # Get database file size
        db_size_bytes = self.sqlite_path.stat().st_size
        db_size_mb = db_size_bytes / (1024 * 1024)

        metadata = {
            'created_at': datetime.now().isoformat(),
            'database_size_mb': round(db_size_mb, 2),
            'source_database': str(self.accdb_path.name),
            'tables': tables_info
        }

        return metadata

    def migrate(self) -> Dict[str, Any]:
        """
        Perform the complete migration from Access to SQLite.

        Returns:
            Generated metadata dictionary
        """
        print("=" * 70)
        print("Access to SQLite Migration Tool")
        print("=" * 70)
        print(f"Source: {self.accdb_path}")
        print(f"Target: {self.sqlite_path}")
        print(f"Metadata: {self.metadata_path}")
        print("=" * 70)

        # Get all tables
        tables = self.get_tables()

        # Remove existing SQLite database if it exists
        if self.sqlite_path.exists():
            print(f"\n⚠ Removing existing database: {self.sqlite_path}")
            self.sqlite_path.unlink()

        # Create new SQLite database
        conn = sqlite3.connect(str(self.sqlite_path))

        try:
            # Migrate each table
            tables_info = {}
            for table in tables:
                try:
                    table_info = self.migrate_table(conn, table)
                    tables_info[table] = table_info
                except Exception as e:
                    print(f"  ✗ Failed to migrate table {table}: {e}")
                    # Continue with other tables
                    continue

            # Generate metadata
            print("\n" + "=" * 70)
            print("📊 Generating Metadata")
            print("=" * 70)
            metadata = self.generate_metadata(conn, tables_info)

            # Write metadata to file
            with open(self.metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)

            print(f"✓ Metadata written to {self.metadata_path}")

            # Print summary
            print("\n" + "=" * 70)
            print("✅ Migration Complete!")
            print("=" * 70)
            print(f"Tables migrated: {len(tables_info)}/{len(tables)}")
            print(f"Total rows: {sum(t['row_count'] for t in tables_info.values())}")
            print(f"Database size: {metadata['database_size_mb']} MB")
            print("=" * 70)

            return metadata

        finally:
            conn.close()


def main():
    """Main entry point for the migration tool."""
    parser = argparse.ArgumentParser(
        description='Migrate Access database (.accdb/.mdb) to SQLite',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Migrate with default output names
  python migrate_access_to_sqlite.py --input data.accdb

  # Specify all paths
  python migrate_access_to_sqlite.py --input data.accdb --output data.db --metadata meta.json

  # Use current directory files
  python migrate_access_to_sqlite.py
        """
    )

    parser.add_argument(
        '--input', '-i',
        default='Colibri2010-2021CWBColonies_2Jan2023.accdb',
        help='Path to Access database (.accdb or .mdb)'
    )

    parser.add_argument(
        '--output', '-o',
        default='bird_data_complete.db',
        help='Path for output SQLite database'
    )

    parser.add_argument(
        '--metadata', '-m',
        default='database_metadata.json',
        help='Path for output metadata JSON file'
    )

    args = parser.parse_args()

    try:
        migrator = AccessToSQLiteMigrator(
            accdb_path=args.input,
            sqlite_path=args.output,
            metadata_path=args.metadata
        )

        migrator.migrate()

        return 0

    except Exception as e:
        print(f"\n❌ Migration failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
