"""
Convert cleaned CSV data to SQLite database for fast querying
"""

import pandas as pd
import sqlite3
from pathlib import Path
import json

def create_database():
    """Create SQLite database from cleaned CSV data"""

    print("="*80)
    print("CREATING SQL DATABASE")
    print("="*80)

    # Load cleaned data
    print("\n[1/3] Loading cleaned data...")
    obs_df = pd.read_csv("cleaned_data/observations.csv")
    colony_df = pd.read_csv("cleaned_data/colony_profiles.csv")

    with open("cleaned_data/species_lookup.json") as f:
        species_dict = json.load(f)

    print(f"✓ Loaded {len(obs_df)} observations")
    print(f"✓ Loaded {len(colony_df)} colony profiles")
    print(f"✓ Loaded {len(species_dict)} species codes")

    # Create database
    print("\n[2/3] Creating SQLite database...")
    db_path = "bird_data.db"
    conn = sqlite3.connect(db_path)

    # Create observations table
    obs_df.to_sql('observations', conn, if_exists='replace', index=False)
    print(f"✓ Created 'observations' table with {len(obs_df)} rows")

    # Create colony profiles table
    colony_df.to_sql('colony_profiles', conn, if_exists='replace', index=False)
    print(f"✓ Created 'colony_profiles' table with {len(colony_df)} rows")

    # Create species lookup table
    species_df = pd.DataFrame([
        {'species_code': code, 'species_name': name}
        for code, name in species_dict.items()
    ])
    species_df.to_sql('species', conn, if_exists='replace', index=False)
    print(f"✓ Created 'species' table with {len(species_df)} rows")

    # Create indexes for faster queries
    print("\n[3/3] Creating indexes...")
    cursor = conn.cursor()

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_year ON observations(year)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_colony ON observations(colony_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_species ON observations(species_code)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_state ON observations(state)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_oil ON observations(oil_present)")

    conn.commit()
    print("✓ Created indexes for fast queries")

    # Show database info
    print("\n" + "="*80)
    print("DATABASE CREATED SUCCESSFULLY!")
    print("="*80)
    print(f"\nDatabase: {db_path}")
    print(f"Size: {Path(db_path).stat().st_size / 1024 / 1024:.2f} MB")

    print("\nTables:")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    for table in cursor.fetchall():
        cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
        count = cursor.fetchone()[0]
        print(f"  - {table[0]}: {count:,} rows")

    # Show sample queries
    print("\n" + "="*80)
    print("TEST QUERIES")
    print("="*80)

    # Test query 1: Oil in 2010
    print("\n1. Colonies with oil in 2010:")
    query = """
    SELECT DISTINCT colony_name, state, COUNT(*) as observations
    FROM observations
    WHERE year = 2010 AND oil_present = 'Y'
    GROUP BY colony_name, state
    ORDER BY observations DESC
    LIMIT 5
    """
    result = pd.read_sql_query(query, conn)
    print(result.to_string(index=False))

    # Test query 2: Species counts
    print("\n2. Top 5 most observed species:")
    query = """
    SELECT species_code, COUNT(*) as observation_count
    FROM observations
    WHERE species_code != ''
    GROUP BY species_code
    ORDER BY observation_count DESC
    LIMIT 5
    """
    result = pd.read_sql_query(query, conn)
    print(result.to_string(index=False))

    # Test query 3: Observations by year
    print("\n3. Observations by year:")
    query = """
    SELECT year, COUNT(*) as total_observations
    FROM observations
    GROUP BY year
    ORDER BY year
    """
    result = pd.read_sql_query(query, conn)
    print(result.to_string(index=False))

    conn.close()

    print("\n" + "="*80)
    print("✓ Database ready for chatbot!")
    print("="*80)

if __name__ == '__main__':
    create_database()
