# Access to SQLite Migration Tool

This tool migrates Microsoft Access databases (.accdb or .mdb files) to SQLite and generates comprehensive metadata.

## Quick Start

Run the migration with default settings (uses files in current directory):

```bash
cd /home/olise/Projects/nexus/data
python migrate_access_to_sqlite.py
```

This will:
- Read from: `Colibri2010-2021CWBColonies_2Jan2023.accdb`
- Write to: `bird_data_complete.db`
- Generate: `database_metadata.json`

## Custom Usage

Specify custom paths:

```bash
python migrate_access_to_sqlite.py \
  --input your_database.accdb \
  --output output.db \
  --metadata metadata.json
```

### Options

- `--input`, `-i`: Path to Access database (default: Colibri2010-2021CWBColonies_2Jan2023.accdb)
- `--output`, `-o`: Path for SQLite output (default: bird_data_complete.db)
- `--metadata`, `-m`: Path for metadata JSON (default: database_metadata.json)

## What It Does

### 1. Schema Extraction
- Reads all tables from the Access database
- Extracts column names and data types
- Converts Access data types to SQLite equivalents

### 2. Data Migration
- Exports all rows from each table
- Handles special characters in column names (spaces, slashes)
- Converts empty strings to NULL for better SQLite compatibility
- Preserves data types and relationships

### 3. Metadata Generation
Creates a JSON file with:
- Database creation timestamp
- Total database size in MB
- Source database name
- For each table:
  - Row count
  - Column names (in order)

### Example Metadata Format

```json
{
  "created_at": "2026-02-21T15:30:00.123456",
  "database_size_mb": 10.45,
  "source_database": "Colibri2010-2021CWBColonies_2Jan2023.accdb",
  "tables": {
    "colony_totals": {
      "row_count": 5931,
      "columns": ["ID", "Year", "Date", "State", "ColonyName", "Latitude", "Longitude"]
    }
  }
}
```

## Technical Details

### How It Works (Under the Hood)

The migration uses **mdbtools**, a Linux command-line toolset for reading Access databases:

1. **`mdb-tables`**: Lists all tables in the database
2. **`mdb-schema`**: Extracts CREATE TABLE statements with schema info
3. **`mdb-export`**: Exports table data as CSV format

The Python script orchestrates these tools and:
- Parses the schema SQL to extract column types
- Creates equivalent SQLite tables
- Imports CSV data with proper type handling
- Generates comprehensive metadata

### Why mdbtools?

- **Cross-platform**: Works on Linux without Windows ODBC drivers
- **Reliable**: Mature open-source project
- **No dependencies**: Uses standard command-line tools
- **Fast**: Efficient for large databases

### Data Type Mapping

Access types are converted to SQLite equivalents:
- `Text` → `TEXT`
- `Long` → `INTEGER`
- `Double` → `REAL`
- `DateTime` → `TEXT` (ISO 8601 format)
- `Memo` → `TEXT`

## Requirements

### System Dependencies
- **mdbtools**: Install with `sudo apt-get install mdbtools` (Ubuntu/Debian)
- **Python 3.7+**: Built-in `sqlite3` module

### Python Dependencies
- Standard library only (no pip packages required!)
  - `subprocess` - Run mdbtools commands
  - `sqlite3` - Create and populate SQLite database
  - `json` - Write metadata file
  - `pathlib` - File path handling

## Troubleshooting

### "mdbtools not found"
Install mdbtools:
```bash
sudo apt-get update
sudo apt-get install mdbtools
```

### Migration fails on specific table
The script continues with other tables. Check error message for details. Common causes:
- Invalid characters in table/column names (script handles most cases)
- Corrupted data in source table
- Data type conversion issues

### Database already exists
The script automatically removes existing SQLite database before migration to ensure clean state.

## Integration with NestScope

After migration, the SQLite database is ready for use with:
- **NestChat**: Text-to-SQL queries via FastAPI backend
- **NestVision**: Computer vision bird detection
- **Nestperts**: Expert species training platform

The metadata JSON file helps the application understand database structure without repeated schema queries.

## Advanced Usage

### Programmatic Usage

You can also import and use the migrator in your own Python scripts:

```python
from migrate_access_to_sqlite import AccessToSQLiteMigrator

migrator = AccessToSQLiteMigrator(
    accdb_path='input.accdb',
    sqlite_path='output.db',
    metadata_path='metadata.json'
)

metadata = migrator.migrate()
print(f"Migrated {len(metadata['tables'])} tables")
```

### Selective Table Migration

To migrate specific tables, modify the `migrate()` method to filter the tables list:

```python
# In migrate() method, after tables = self.get_tables():
tables = [t for t in tables if t in ['colony_totals', 'species_codes']]
```

## Performance

Migration speed depends on:
- Database size
- Number of tables
- Row counts
- Disk I/O speed

Typical performance:
- **60 MB Access DB** with 8 tables, ~50K rows: **~30-60 seconds**
- Bottleneck: CSV export and parsing (mdb-export)

## License

Part of the NestScope project. See main project LICENSE.
