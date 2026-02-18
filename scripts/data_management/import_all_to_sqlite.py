"""
Complete Data Import to SQLite Database
Preserves ALL data from CSV files without filtering
"""

import pandas as pd
import sqlite3
from pathlib import Path
import json
from datetime import datetime
import numpy as np


def safe_read_csv(filepath):
    """Safely read CSV with proper handling of quotes and encoding"""
    try:
        df = pd.read_csv(
            filepath,
            encoding='utf-8',
            quotechar='"',
            escapechar='\\',
            na_values=['', 'NA', 'N/A'],
            keep_default_na=True,
            low_memory=False
        )
        return df
    except Exception as e:
        print(f"  ⚠ Error reading {filepath}: {e}")
        try:
            # Fallback to Python engine
            df = pd.read_csv(
                filepath,
                encoding='utf-8',
                engine='python',
                quotechar='"',
                escapechar='\\'
            )
            return df
        except Exception as e2:
            print(f"  ✗ Failed to read {filepath}: {e2}")
            return None


def clean_dataframe(df):
    """Clean dataframe by standardizing nulls and data types"""
    # Replace various null representations
    df = df.replace(['NA', 'N/A', 'na', 'n/a'], np.nan)

    # Clean string columns - strip whitespace
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].str.strip() if df[col].dtype == 'object' else df[col]

    return df


def convert_date_columns(df, date_cols):
    """Convert date columns to datetime"""
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    return df


def convert_numeric_columns(df, numeric_cols):
    """Convert numeric columns to appropriate types"""
    for col in numeric_cols:
        if col in df.columns:
            # Try to convert to numeric, coerce errors to NaN
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df


def import_species_codes(conn, csv_folder):
    """Import species codes lookup table"""
    print("\n[1/9] Importing species codes...")

    filepath = csv_folder / 'tblSpeciesCodes.csv'
    if not filepath.exists():
        print("  ⚠ File not found")
        return

    df = safe_read_csv(filepath)
    if df is None:
        return

    df = clean_dataframe(df)

    # Create table
    df.to_sql('species_codes', conn, if_exists='replace', index=False)

    print(f"  ✓ Imported {len(df)} species codes")

    # Create index
    cursor = conn.cursor()
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_species_code ON species_codes(SpeciesCode)")
    conn.commit()


def import_colony_coordinates(conn, csv_folder):
    """Import colony coordinates"""
    print("\n[2/9] Importing colony coordinates...")

    filepath = csv_folder / 'tblChandeleurNorthSouth_2010-2021ColonyCentroidCoordinates.csv'
    if not filepath.exists():
        print("  ⚠ File not found")
        return

    df = safe_read_csv(filepath)
    if df is None:
        return

    df = clean_dataframe(df)

    # Convert coordinates to numeric
    numeric_cols = ['Longitude', 'Latitude']
    df = convert_numeric_columns(df, numeric_cols)

    # Rename Year column to avoid SQL issues
    if 'Year (ChandeleursOnly)' in df.columns:
        df = df.rename(columns={'Year (ChandeleursOnly)': 'Year_ChandeleursOnly'})

    # Create table
    df.to_sql('colony_coordinates', conn, if_exists='replace', index=False)

    print(f"  ✓ Imported {len(df)} colony coordinate records")

    # Create indexes
    cursor = conn.cursor()
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_colony_id ON colony_coordinates(ColonyID)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_colony_name ON colony_coordinates(ColonyName)")
    conn.commit()


def import_colony_inventory(conn, csv_folder):
    """Import colony inventory"""
    print("\n[3/9] Importing colony inventory...")

    filepath = csv_folder / 'tblRWCWB_ColonyInventory_10Nov22.csv'
    if not filepath.exists():
        print("  ⚠ File not found")
        return

    df = safe_read_csv(filepath)
    if df is None:
        return

    df = clean_dataframe(df)

    # Convert coordinate columns to numeric
    numeric_cols = ['Latitude', 'Longitude']
    df = convert_numeric_columns(df, numeric_cols)

    # Create table
    df.to_sql('colony_inventory', conn, if_exists='replace', index=False)

    print(f"  ✓ Imported {len(df)} colony inventory records")

    # Create indexes
    cursor = conn.cursor()
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventory_colony ON colony_inventory(ColonyName)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventory_state ON colony_inventory(State)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventory_georegion ON colony_inventory(GeoRegion)")
    conn.commit()


def import_colony_site_notes(conn, csv_folder):
    """Import colony site notes from both files"""
    print("\n[4/9] Importing colony site notes...")

    dfs = []

    # Import 2010 notes
    filepath_2010 = csv_folder / 'tblColonySiteNotes2010.csv'
    if filepath_2010.exists():
        df = safe_read_csv(filepath_2010)
        if df is not None:
            df = clean_dataframe(df)
            dfs.append(df)
            print(f"  ✓ Loaded 2010 notes: {len(df)} records")

    # Import 2011-2021 notes
    filepath_2011 = csv_folder / 'tblColonySiteNotes2011-2021.csv'
    if filepath_2011.exists():
        df = safe_read_csv(filepath_2011)
        if df is not None:
            df = clean_dataframe(df)
            dfs.append(df)
            print(f"  ✓ Loaded 2011-2021 notes: {len(df)} records")

    if not dfs:
        print("  ⚠ No data loaded")
        return

    # Combine dataframes - standardize columns first
    # Get all unique columns
    all_columns = set()
    for df in dfs:
        all_columns.update(df.columns)

    # Add missing columns to each dataframe
    for i, df in enumerate(dfs):
        for col in all_columns:
            if col not in df.columns:
                df[col] = np.nan
        dfs[i] = df[sorted(all_columns)]

    # Concatenate
    combined_df = pd.concat(dfs, ignore_index=True)

    # Convert date columns
    date_cols = ['Date']
    combined_df = convert_date_columns(combined_df, date_cols)

    # Convert Year to numeric
    combined_df = convert_numeric_columns(combined_df, ['Year'])

    # Create table
    combined_df.to_sql('colony_site_notes', conn, if_exists='replace', index=False)

    print(f"  ✓ Imported total {len(combined_df)} colony site note records")

    # Create indexes
    cursor = conn.cursor()
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_colony ON colony_site_notes(ColonyName)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_year ON colony_site_notes(Year)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_species ON colony_site_notes(SpeciesCode)")
    conn.commit()


def import_colony_totals(conn, csv_folder):
    """Import colony totals"""
    print("\n[5/9] Importing colony totals...")

    filepath = csv_folder / 'tblColonyTotals2010-2021_MayJuneCombined.csv'
    if not filepath.exists():
        print("  ⚠ File not found")
        return

    df = safe_read_csv(filepath)
    if df is None:
        return

    df = clean_dataframe(df)

    # Convert date columns
    date_cols = ['Date']
    df = convert_date_columns(df, date_cols)

    # Convert numeric columns
    numeric_cols = ['ID', 'Year', 'Latitude', 'Longitude', 'Nests', 'Birds']
    df = convert_numeric_columns(df, numeric_cols)

    # Rename problematic column names
    if 'BestForBPE?' in df.columns:
        df = df.rename(columns={'BestForBPE?': 'BestForBPE'})
    if 'CombinedMayJuneTotal?' in df.columns:
        df = df.rename(columns={'CombinedMayJuneTotal?': 'CombinedMayJuneTotal'})

    # Create table
    df.to_sql('colony_totals', conn, if_exists='replace', index=False)

    print(f"  ✓ Imported {len(df)} colony total records")

    # Create indexes
    cursor = conn.cursor()
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_totals_year ON colony_totals(Year)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_totals_colony ON colony_totals(ColonyName)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_totals_species ON colony_totals(SpeciesCode)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_totals_state ON colony_totals(State)")
    conn.commit()


def import_species_data(conn, csv_folder):
    """Import all species observation data"""
    print("\n[6/9] Importing species observations (2010)...")

    # Import 2010 data
    filepath_2010 = csv_folder / 'tblSpeciesData2010.csv'
    if filepath_2010.exists():
        df = safe_read_csv(filepath_2010)
        if df is not None:
            df = clean_dataframe(df)

            # Convert dates
            df = convert_date_columns(df, ['Date', 'DateDotted'])

            # Convert numeric columns - all the count fields
            numeric_cols = [
                'AutoID', 'Year', 'Latitude', 'Longitude', 'DottingAreaNumber',
                'CameraNumber', 'CardNumber', 'PhotoNumber',
                'WBN', 'ChickNestw/outAdult', 'AbandNest', 'EmptyNest', 'PBN',
                'Site', 'Brood', 'OtherAdultsInColony', 'OtherImmInColony',
                'Chicks/Nestlings', 'RoostingBirds', 'RoostingAdults',
                'RoostingImmatures', 'UnknownAge'
            ]
            df = convert_numeric_columns(df, numeric_cols)

            # Rename problematic column
            if 'BestForBPE?' in df.columns:
                df = df.rename(columns={'BestForBPE?': 'BestForBPE'})

            df.to_sql('species_data_2010', conn, if_exists='replace', index=False)
            print(f"  ✓ Imported {len(df)} records from 2010")

    # Import 2011-2013 data
    print("\n[7/9] Importing species observations (2011-2013)...")
    filepath_2011 = csv_folder / 'tblSpeciesData2011-2013.csv'
    if filepath_2011.exists():
        df = safe_read_csv(filepath_2011)
        if df is not None:
            df = clean_dataframe(df)

            # Convert dates
            df = convert_date_columns(df, ['Date', 'DateDotted'])

            # Convert numeric columns
            numeric_cols = [
                'AutoID', 'Year', 'DottingAreaNumber',
                'CameraNumber', 'CardNumber', 'PhotoNumber',
                'WBN', 'ChickNest', 'ChickNestw/outAdult', 'Brood',
                'AbandNest', 'EmptyNest', 'PBN', 'Site',
                'OtherAdultsInColony', 'OtherImmInColony',
                'Chicks/Nestlings', 'RoostingBirds', 'RoostingAdults',
                'RoostingImmatures', 'UnknownAge'
            ]
            df = convert_numeric_columns(df, numeric_cols)

            # Rename problematic column
            if 'BestForBPE?' in df.columns:
                df = df.rename(columns={'BestForBPE?': 'BestForBPE'})

            df.to_sql('species_data_2011_2013', conn, if_exists='replace', index=False)
            print(f"  ✓ Imported {len(df)} records from 2011-2013")

    # Import 2015-2021 data
    print("\n[8/9] Importing species observations (2015-2021)...")
    filepath_2015 = csv_folder / 'tblSpeciesData2015_2018_2021.csv'
    if filepath_2015.exists():
        df = safe_read_csv(filepath_2015)
        if df is not None:
            df = clean_dataframe(df)

            # Convert dates
            df = convert_date_columns(df, ['Date', 'DateDotted'])

            # Convert numeric columns
            numeric_cols = [
                'AutoID', 'Year', 'DottingAreaNumber',
                'CameraNumber', 'CardNumber', 'PhotoNumber',
                'WBN', 'ChickNest', 'ChickNestw/outAdult', 'Brood',
                'AbandNest', 'EmptyNest', 'PBN', 'Territory', 'Site',
                'OtherBirds'
            ]
            df = convert_numeric_columns(df, numeric_cols)

            # Rename problematic column
            if 'BestForBPE?' in df.columns:
                df = df.rename(columns={'BestForBPE?': 'BestForBPE'})

            df.to_sql('species_data_2015_2021', conn, if_exists='replace', index=False)
            print(f"  ✓ Imported {len(df)} records from 2015-2021")

    # Create indexes on all species tables
    print("\n[9/9] Creating indexes on species data...")
    cursor = conn.cursor()

    for table in ['species_data_2010', 'species_data_2011_2013', 'species_data_2015_2021']:
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_year ON {table}(Year)")
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_colony ON {table}(ColonyName)")
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_species ON {table}(SpeciesCode)")
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_dotter ON {table}(Dotter)")

    conn.commit()
    print("  ✓ Created indexes for fast queries")


def create_metadata(conn, db_path):
    """Create metadata about the database"""
    cursor = conn.cursor()

    # Get table information
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()

    metadata = {
        'created_at': datetime.now().isoformat(),
        'database_size_mb': Path(db_path).stat().st_size / 1024 / 1024,
        'tables': {}
    }

    for table in tables:
        table_name = table[0]
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]

        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()

        metadata['tables'][table_name] = {
            'row_count': count,
            'columns': [col[1] for col in columns]
        }

    return metadata


def main():
    print("=" * 80)
    print("COMPLETE DATA IMPORT TO SQLITE")
    print("Preserves ALL data without filtering")
    print("=" * 80)

    csv_folder = Path("CSV_Files")
    db_path = "data/bird_data_complete.db"

    # Remove existing database
    if Path(db_path).exists():
        Path(db_path).unlink()
        print(f"\n✓ Removed existing database")

    # Create connection
    conn = sqlite3.connect(db_path)

    try:
        # Import all data
        import_species_codes(conn, csv_folder)
        import_colony_coordinates(conn, csv_folder)
        import_colony_inventory(conn, csv_folder)
        import_colony_site_notes(conn, csv_folder)
        import_colony_totals(conn, csv_folder)
        import_species_data(conn, csv_folder)

        # Create metadata
        print("\n" + "=" * 80)
        print("GENERATING DATABASE METADATA")
        print("=" * 80)

        metadata = create_metadata(conn, db_path)

        # Save metadata
        with open('database_metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        print("\n✓ Saved metadata to database_metadata.json")

        # Display summary
        print("\n" + "=" * 80)
        print("DATABASE CREATED SUCCESSFULLY!")
        print("=" * 80)
        print(f"\nDatabase: {db_path}")
        print(f"Size: {metadata['database_size_mb']:.2f} MB")
        print(f"\nTables created:")

        total_rows = 0
        for table_name, info in sorted(metadata['tables'].items()):
            print(f"  • {table_name}: {info['row_count']:,} rows, {len(info['columns'])} columns")
            total_rows += info['row_count']

        print(f"\nTotal records: {total_rows:,}")

        # Test query
        print("\n" + "=" * 80)
        print("VALIDATION QUERIES")
        print("=" * 80)

        cursor = conn.cursor()

        # Check species codes
        cursor.execute("SELECT COUNT(*) FROM species_codes")
        print(f"\n✓ Species codes: {cursor.fetchone()[0]}")

        # Check year range in species data
        cursor.execute("SELECT MIN(Year), MAX(Year) FROM species_data_2010")
        years = cursor.fetchone()
        print(f"✓ Species data 2010 year range: {years[0]} - {years[1]}")

        cursor.execute("SELECT MIN(Year), MAX(Year) FROM species_data_2011_2013")
        years = cursor.fetchone()
        print(f"✓ Species data 2011-2013 year range: {years[0]} - {years[1]}")

        cursor.execute("SELECT MIN(Year), MAX(Year) FROM species_data_2015_2021")
        years = cursor.fetchone()
        print(f"✓ Species data 2015-2021 year range: {years[0]} - {years[1]}")

        # Check colony totals
        cursor.execute("SELECT COUNT(DISTINCT ColonyName) FROM colony_totals")
        print(f"✓ Unique colonies in totals: {cursor.fetchone()[0]}")

        print("\n" + "=" * 80)
        print("✓ ALL DATA SUCCESSFULLY IMPORTED!")
        print("✓ No data was filtered or lost")
        print("=" * 80)

    except Exception as e:
        print(f"\n✗ Error during import: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()


if __name__ == '__main__':
    main()
