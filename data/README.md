# Data Directory

This directory contains the bird survey data for the Louisiana Coastal Bird Monitoring Copilot.

## Directory Structure

- `raw/` - CSV files exported from NOAA Access database (gitignored)
- `processed/` - DuckDB database files (gitignored)

## Getting Started

### Step 1: Export Data from Access Database

1. Open the NOAA DIVER Deepwater Horizon Avian Monitoring Database
2. Export all relevant tables to CSV format
3. Save CSV files in the `raw/` directory

Common tables to export:
- Survey observations
- Species information
- Colony locations
- Environmental conditions

### Step 2: Load Data into DuckDB

Run the data loading script:

```bash
python src/data/load_data.py
```

This will:
- Read all CSV files from `raw/` directory
- Clean and validate the data
- Create DuckDB database in `processed/` directory
- Set up appropriate indexes for fast queries

### Step 3: Verify Data Loading

Check that the database was created successfully:

```bash
python -c "import duckdb; conn = duckdb.connect('data/processed/bird_survey.duckdb'); print(conn.execute('SHOW TABLES').fetchall()); conn.close()"
```

## Data Schema

Details about the database schema will be documented once the data is loaded.

Expected tables:
- `observations` - Individual bird observations
- `species` - Species metadata
- `colonies` - Colony location information
- `surveys` - Survey metadata

## Notes

- CSV files and database files are gitignored to keep repository size small
- Coordinate with your team to ensure everyone has access to the source data
- For data quality issues, contact the Data Engineer (Person 1)
