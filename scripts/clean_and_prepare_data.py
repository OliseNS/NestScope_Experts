"""
Data Cleaning and Preparation Script
Consolidates CSV files and prepares them for LLM/Vector Database
"""

import pandas as pd
import json
from pathlib import Path
from datetime import datetime

def remove_duplicate_file():
    """Remove the duplicate coordinate file"""
    duplicate_file = Path("CSV_Files/tblChandeleurNorthSouth_2010-2021ColonyCentroidCoordinates(1).csv")
    if duplicate_file.exists():
        duplicate_file.unlink()
        print(f"✓ Removed duplicate file: {duplicate_file}")
    else:
        print(f"ℹ Duplicate file already removed or doesn't exist")

def load_csv_files():
    """Load all CSV files into dataframes"""
    csv_folder = Path("CSV_Files")

    files = {
        'colony_notes_2010': 'tblColonySiteNotes2010.csv',
        'colony_notes_2011_2021': 'tblColonySiteNotes2011-2021.csv',
        'colony_totals': 'tblColonyTotals2010-2021_MayJuneCombined.csv',
        'species_data_2010': 'tblSpeciesData2010.csv',
        'species_data_2011_2013': 'tblSpeciesData2011-2013.csv',
        'species_data_2015_2021': 'tblSpeciesData2015_2018_2021.csv',
        'species_codes': 'tblSpeciesCodes.csv',
        'colony_inventory': 'tblRWCWB_ColonyInventory_10Nov22.csv',
        'colony_coordinates': 'tblChandeleurNorthSouth_2010-2021ColonyCentroidCoordinates.csv'
    }

    dataframes = {}
    for key, filename in files.items():
        filepath = csv_folder / filename
        if filepath.exists():
            dataframes[key] = pd.read_csv(filepath)
            print(f"✓ Loaded {filename}: {len(dataframes[key])} rows")
        else:
            print(f"⚠ File not found: {filename}")

    return dataframes

def clean_and_standardize_dates(df, date_columns):
    """Standardize date formats"""
    for col in date_columns:
        if col in df.columns:
            try:
                df[col] = pd.to_datetime(df[col], errors='coerce')
            except:
                pass
    return df

def create_consolidated_observations(dfs):
    """
    Create a consolidated dataset of all observations with text data
    This will be used for vector database and LLM queries
    """

    observations = []

    # Process colony_notes_2010
    if 'colony_notes_2010' in dfs:
        df = dfs['colony_notes_2010'].copy()
        for idx, row in df.iterrows():
            obs = {
                'source_file': 'colony_notes_2010',
                'record_id': f"CN2010_{idx}",
                'year': 2010,
                'date': None,
                'colony_name': row.get('ColonyName', ''),
                'latitude': row.get('Latitude', None),
                'longitude': row.get('Longitude', None),
                'dotter': row.get('Dotter', ''),
                'habitat': row.get('Habitat', ''),
                'oil_present': row.get('Oil', ''),
                'notes': row.get('Notes', ''),
                'additional_notes': row.get('AdditionalNotes', ''),
                'species_code': None,
                'state': None,
                'geo_region': None,
            }

            # Create combined text for embedding
            text_parts = []
            if pd.notna(obs['habitat']):
                text_parts.append(f"Habitat: {obs['habitat']}")
            if pd.notna(obs['notes']):
                text_parts.append(f"Notes: {obs['notes']}")
            if pd.notna(obs['additional_notes']):
                text_parts.append(f"Additional: {obs['additional_notes']}")

            obs['combined_text'] = " | ".join(text_parts) if text_parts else ""

            # Only include if there's meaningful text
            if obs['combined_text'].strip():
                observations.append(obs)

    # Process colony_notes_2011_2021
    if 'colony_notes_2011_2021' in dfs:
        df = dfs['colony_notes_2011_2021'].copy()
        for idx, row in df.iterrows():
            obs = {
                'source_file': 'colony_notes_2011_2021',
                'record_id': f"CN2011_{idx}",
                'year': row.get('Year', None),
                'date': row.get('Date', None),
                'colony_name': row.get('ColonyName', ''),
                'latitude': None,
                'longitude': None,
                'dotter': row.get('Dotter', ''),
                'habitat': row.get('Habitat', ''),
                'oil_present': row.get('Oil', ''),
                'notes': row.get('Notes', ''),
                'additional_notes': row.get('AdditionalNotes', ''),
                'species_code': row.get('SpeciesCode', ''),
                'state': None,
                'geo_region': None,
            }

            # Create combined text for embedding
            text_parts = []
            if pd.notna(obs['habitat']):
                text_parts.append(f"Habitat: {obs['habitat']}")
            if pd.notna(obs['species_code']) and obs['species_code']:
                text_parts.append(f"Species: {obs['species_code']}")
            if pd.notna(obs['notes']):
                text_parts.append(f"Notes: {obs['notes']}")
            if pd.notna(obs['additional_notes']):
                text_parts.append(f"Additional: {obs['additional_notes']}")

            obs['combined_text'] = " | ".join(text_parts) if text_parts else ""

            # Only include if there's meaningful text
            if obs['combined_text'].strip():
                observations.append(obs)

    # Process colony_totals with notes
    if 'colony_totals' in dfs:
        df = dfs['colony_totals'].copy()
        df_with_notes = df[df['Notes'].notna()]

        for idx, row in df_with_notes.iterrows():
            obs = {
                'source_file': 'colony_totals',
                'record_id': f"CT_{idx}",
                'year': row.get('Year', None),
                'date': row.get('Date', None),
                'colony_name': row.get('ColonyName', ''),
                'latitude': row.get('Latitude', None),
                'longitude': row.get('Longitude', None),
                'dotter': None,
                'habitat': None,
                'oil_present': None,
                'notes': row.get('Notes', ''),
                'additional_notes': None,
                'species_code': row.get('SpeciesCode', ''),
                'state': row.get('State', ''),
                'geo_region': row.get('GeoRegion', ''),
                'nests': row.get('Nests', None),
                'birds': row.get('Birds', None),
            }

            # Create combined text for embedding
            text_parts = []
            if pd.notna(obs['species_code']):
                text_parts.append(f"Species: {obs['species_code']}")
            if pd.notna(obs['notes']):
                text_parts.append(f"Notes: {obs['notes']}")
            if pd.notna(obs['nests']):
                text_parts.append(f"Nests: {obs['nests']}")
            if pd.notna(obs['birds']):
                text_parts.append(f"Birds: {obs['birds']}")

            obs['combined_text'] = " | ".join(text_parts) if text_parts else ""

            if obs['combined_text'].strip():
                observations.append(obs)

    # Process species data files with notes
    for species_file in ['species_data_2010', 'species_data_2011_2013', 'species_data_2015_2021']:
        if species_file in dfs:
            df = dfs[species_file].copy()
            df_with_notes = df[df['Notes'].notna()] if 'Notes' in df.columns else pd.DataFrame()

            for idx, row in df_with_notes.iterrows():
                obs = {
                    'source_file': species_file,
                    'record_id': f"{species_file}_{idx}",
                    'year': row.get('Year', None),
                    'date': row.get('Date', None),
                    'colony_name': row.get('ColonyName', ''),
                    'latitude': row.get('Latitude', None),
                    'longitude': row.get('Longitude', None),
                    'dotter': row.get('Dotter', ''),
                    'habitat': None,
                    'oil_present': None,
                    'notes': row.get('Notes', ''),
                    'additional_notes': row.get('AdditionalNotes', '') if 'AdditionalNotes' in row else '',
                    'species_code': row.get('SpeciesCode', ''),
                    'state': None,
                    'geo_region': None,
                }

                # Create combined text for embedding
                text_parts = []
                if pd.notna(obs['species_code']):
                    text_parts.append(f"Species: {obs['species_code']}")
                if pd.notna(obs['notes']):
                    text_parts.append(f"Notes: {obs['notes']}")

                obs['combined_text'] = " | ".join(text_parts) if text_parts else ""

                if obs['combined_text'].strip():
                    observations.append(obs)

    # Create DataFrame
    obs_df = pd.DataFrame(observations)

    # Add metadata columns
    obs_df['text_length'] = obs_df['combined_text'].str.len()
    obs_df['has_coordinates'] = (obs_df['latitude'].notna()) & (obs_df['longitude'].notna())

    print(f"\n✓ Created consolidated observations: {len(obs_df)} records with text data")
    print(f"  - Average text length: {obs_df['text_length'].mean():.0f} characters")
    print(f"  - Records with coordinates: {obs_df['has_coordinates'].sum()}")

    return obs_df

def create_species_lookup(dfs):
    """Create species code to name lookup"""
    if 'species_codes' in dfs:
        df = dfs['species_codes']
        species_dict = dict(zip(df['SpeciesCode'], df['SpeciesName']))
        print(f"\n✓ Created species lookup with {len(species_dict)} species")
        return species_dict
    return {}

def create_colony_profiles(dfs, obs_df):
    """Create colony-level profiles aggregating all observations"""

    colony_profiles = []

    for colony_name in obs_df['colony_name'].unique():
        if not pd.notna(colony_name) or not colony_name:
            continue

        colony_obs = obs_df[obs_df['colony_name'] == colony_name]

        profile = {
            'colony_name': colony_name,
            'total_observations': len(colony_obs),
            'years_observed': sorted(colony_obs['year'].dropna().unique().tolist()),
            'states': colony_obs['state'].dropna().unique().tolist(),
            'geo_regions': colony_obs['geo_region'].dropna().unique().tolist(),
            'habitats': colony_obs['habitat'].dropna().unique().tolist(),
            'species_observed': colony_obs['species_code'].dropna().unique().tolist(),
            'oil_observations': colony_obs['oil_present'].value_counts().to_dict(),
        }

        # Aggregate all notes for this colony
        all_notes = []
        for note in colony_obs['notes'].dropna():
            if note:
                all_notes.append(str(note))

        profile['aggregated_notes'] = " || ".join(all_notes[:100])  # Limit to 100 notes
        profile['note_count'] = len(all_notes)

        # Get representative location if available
        coords = colony_obs[colony_obs['has_coordinates']]
        if len(coords) > 0:
            profile['latitude'] = coords['latitude'].mean()
            profile['longitude'] = coords['longitude'].mean()
        else:
            profile['latitude'] = None
            profile['longitude'] = None

        colony_profiles.append(profile)

    colony_df = pd.DataFrame(colony_profiles)
    print(f"\n✓ Created {len(colony_df)} colony profiles")

    return colony_df

def save_cleaned_data(obs_df, colony_df, species_dict):
    """Save cleaned data to files"""

    output_dir = Path("cleaned_data")
    output_dir.mkdir(exist_ok=True)

    # Save observations
    obs_file = output_dir / "observations.csv"
    obs_df.to_csv(obs_file, index=False)
    print(f"\n✓ Saved observations to: {obs_file}")

    # Save colony profiles
    colony_file = output_dir / "colony_profiles.csv"
    colony_df.to_csv(colony_file, index=False)
    print(f"✓ Saved colony profiles to: {colony_file}")

    # Save species lookup
    species_file = output_dir / "species_lookup.json"
    with open(species_file, 'w') as f:
        json.dump(species_dict, f, indent=2)
    print(f"✓ Saved species lookup to: {species_file}")

    # Save metadata
    metadata = {
        'created_at': datetime.now().isoformat(),
        'total_observations': len(obs_df),
        'total_colonies': len(colony_df),
        'total_species': len(species_dict),
        'year_range': [int(obs_df['year'].min()), int(obs_df['year'].max())] if len(obs_df) > 0 else [],
        'source_files': obs_df['source_file'].unique().tolist()
    }

    metadata_file = output_dir / "metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"✓ Saved metadata to: {metadata_file}")

    return output_dir

def main():
    print("=" * 80)
    print("DATA CLEANING AND PREPARATION")
    print("=" * 80)

    # Step 1: Remove duplicate
    print("\n[1/5] Removing duplicate files...")
    remove_duplicate_file()

    # Step 2: Load data
    print("\n[2/5] Loading CSV files...")
    dfs = load_csv_files()

    # Step 3: Create consolidated observations
    print("\n[3/5] Creating consolidated observations...")
    obs_df = create_consolidated_observations(dfs)

    # Step 4: Create reference data
    print("\n[4/5] Creating reference data...")
    species_dict = create_species_lookup(dfs)
    colony_df = create_colony_profiles(dfs, obs_df)

    # Step 5: Save cleaned data
    print("\n[5/5] Saving cleaned data...")
    output_dir = save_cleaned_data(obs_df, colony_df, species_dict)

    print("\n" + "=" * 80)
    print("DATA CLEANING COMPLETE!")
    print("=" * 80)
    print(f"\nCleaned data saved to: {output_dir}")
    print(f"  - {len(obs_df):,} observations ready for vector database")
    print(f"  - {len(colony_df):,} colony profiles")
    print(f"  - {len(species_dict):,} species codes")
    print("\n✓ Data is ready for embedding and chatbot!")

if __name__ == '__main__':
    main()
