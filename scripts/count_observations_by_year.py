#!/usr/bin/env python3
"""
Script to count observations per year from species data CSV files
"""

import pandas as pd
from pathlib import Path
from collections import defaultdict

def count_observations_by_year():
    """Count observations per year from all species data CSV files"""

    # Define the CSV files to process
    csv_dir = Path("/home/olise/Projects/nexus/CSV_Files")
    csv_files = [
        "tblSpeciesData2010.csv",
        "tblSpeciesData2011-2013.csv",
        "tblSpeciesData2015_2018_2021.csv"
    ]

    # Dictionary to store counts per year
    year_counts = defaultdict(int)

    print("Processing CSV files...")
    print("-" * 50)

    # Process each CSV file
    for csv_file in csv_files:
        file_path = csv_dir / csv_file

        if not file_path.exists():
            print(f"Warning: {csv_file} not found, skipping...")
            continue

        print(f"\nProcessing: {csv_file}")

        # Read the CSV file
        df = pd.read_csv(file_path)

        # Count observations per year
        year_counts_in_file = df['Year'].value_counts().sort_index()

        # Add to total counts
        for year, count in year_counts_in_file.items():
            year_counts[year] += count
            print(f"  {year}: {count:,} observations")

    # Display summary
    print("\n" + "=" * 50)
    print("SUMMARY: Total Observations per Year")
    print("=" * 50)

    total_observations = 0
    for year in sorted(year_counts.keys()):
        count = year_counts[year]
        total_observations += count
        print(f"{year}: {count:,} observations")

    print("-" * 50)
    print(f"TOTAL: {total_observations:,} observations across all years")
    print("=" * 50)

    return year_counts

if __name__ == "__main__":
    count_observations_by_year()
