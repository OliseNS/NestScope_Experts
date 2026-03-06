"""
Build comprehensive coastal risk database combining:
- Bird population data (existing)
- Hurricane history (HURDAT2)
- Sea level rise projections (NOAA)
- Erosion rates (USGS)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import sqlite3
import logging
from server.coastal_tools.hurricane_data import (
    parse_hurdat2,
    filter_gulf_coast_storms,
    get_major_storms_summary,
    calculate_storm_frequency_trend
)
from server.coastal_tools.slr_projections import (
    calculate_inundation_risk,
    estimate_land_loss_percentage,
    get_colony_elevation_estimate,
    years_until_critical
)
from server.coastal_tools.erosion_models import (
    get_erosion_rate,
    calculate_erosion_projection,
    calculate_combined_threat,
    get_region_for_colony,
    years_until_uninhabitable
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_risk_tables(db_path: str):
    """Create tables for coastal risk data"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Gulf Coast hurricanes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gulf_hurricanes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            storm_id TEXT NOT NULL,
            name TEXT,
            year INTEGER NOT NULL,
            category TEXT,
            max_wind_kt INTEGER,
            max_wind_in_region INTEGER,
            impact_description TEXT,
            bird_impact TEXT,
            UNIQUE(storm_id)
        )
    """)

    # Colony risk assessment table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS colony_risk_assessment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            colony_name TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            region TEXT,

            -- Current status
            current_area_m2 REAL,
            average_elevation_m REAL,
            current_bird_count INTEGER,
            species_count INTEGER,

            -- Erosion metrics
            erosion_rate_m_per_year REAL,
            years_until_uninhabitable INTEGER,

            -- Sea level rise (2050 intermediate scenario)
            slr_2050_m REAL,
            percent_inundated_2050 REAL,
            habitability_2050 TEXT,

            -- Combined risk
            combined_risk_score REAL,
            risk_level TEXT,
            risk_color TEXT,
            recommended_action TEXT,
            years_until_critical INTEGER,

            -- Population trend
            population_trend_2010_2021_pct REAL,

            last_updated TIMESTAMP,

            UNIQUE(colony_name)
        )
    """)

    # Future projections table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS colony_projections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            colony_name TEXT NOT NULL,
            projection_year INTEGER NOT NULL,
            scenario TEXT NOT NULL,  -- low, intermediate, high

            -- Projected values
            projected_area_m2 REAL,
            projected_elevation_m REAL,
            inundated BOOLEAN,
            habitable BOOLEAN,

            -- Probability estimates
            storm_probability_pct REAL,

            UNIQUE(colony_name, projection_year, scenario)
        )
    """)

    conn.commit()
    conn.close()
    logger.info("Risk tables created")


def populate_hurricane_data(db_path: str, hurdat_path: str):
    """Parse HURDAT2 and populate hurricane table"""
    logger.info("Parsing HURDAT2 data...")

    storms = parse_hurdat2(hurdat_path)
    logger.info(f"Parsed {len(storms)} total storms from HURDAT2")

    # Filter to Gulf Coast storms (2005-present)
    gulf_storms = filter_gulf_coast_storms(storms, min_year=2005)
    logger.info(f"Filtered to {len(gulf_storms)} Gulf Coast storms")

    # Get major storms with documented impacts
    major_storms = get_major_storms_summary(min_year=2005)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    inserted = 0

    for storm in gulf_storms:
        # Try to find matching major storm entry for impact description
        major_match = None
        for major in major_storms:
            if (major['name'].lower() in storm['name'].lower() or
                storm['name'].lower() in major['name'].lower()) and \
               major['year'] == storm['year']:
                major_match = major
                break

        try:
            cursor.execute("""
                INSERT OR REPLACE INTO gulf_hurricanes
                (storm_id, name, year, category, max_wind_kt, max_wind_in_region,
                 impact_description, bird_impact)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                storm['id'],
                storm['name'],
                storm['year'],
                storm.get('category', 'Unknown'),
                max(t['wind_kt'] for t in storm['tracks']),
                storm.get('max_wind_in_region', 0),
                major_match['impact'] if major_match else None,
                major_match['bird_impact'] if major_match else None
            ))
            inserted += 1
        except sqlite3.Error as e:
            logger.warning(f"Failed to insert storm {storm['name']}: {e}")

    conn.commit()
    conn.close()

    logger.info(f"Inserted {inserted} Gulf Coast hurricanes into database")


def calculate_colony_risks(db_path: str):
    """Calculate comprehensive risk assessment for each colony"""
    logger.info("Calculating colony risk assessments...")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all colonies with coordinates
    cursor.execute("""
        SELECT DISTINCT
            ColonyName,
            CAST(Latitude AS REAL) as Latitude,
            CAST(Longitude AS REAL) as Longitude
        FROM [tblColonyTotals2010-2021_MayJuneCombined]
        WHERE Latitude IS NOT NULL
          AND Longitude IS NOT NULL
          AND CAST(Latitude AS REAL) != 0
          AND CAST(Longitude AS REAL) != 0
    """)

    colonies = cursor.fetchall()
    logger.info(f"Processing {len(colonies)} colonies...")

    processed = 0

    for colony_name, lat, lon in colonies:
        try:
            # Get current bird statistics
            cursor.execute("""
                SELECT
                    SUM(CAST(COALESCE(Birds, 0) AS INTEGER)) as total_birds,
                    COUNT(DISTINCT SpeciesCode) as species_count
                FROM [tblColonyTotals2010-2021_MayJuneCombined]
                WHERE ColonyName = ?
                  AND CAST(COALESCE(Birds, 0) AS INTEGER) > 0
            """, (colony_name,))

            bird_stats = cursor.fetchone()
            total_birds = bird_stats[0] if bird_stats[0] else 0
            species_count = bird_stats[1] if bird_stats[1] else 0

            # Calculate population trend (2010 vs 2021)
            cursor.execute("""
                SELECT
                    SUM(CASE WHEN CAST(Year AS INTEGER) = 2010
                        THEN CAST(COALESCE(Birds, 0) AS INTEGER) ELSE 0 END) as birds_2010,
                    SUM(CASE WHEN CAST(Year AS INTEGER) = 2021
                        THEN CAST(COALESCE(Birds, 0) AS INTEGER) ELSE 0 END) as birds_2021
                FROM [tblColonyTotals2010-2021_MayJuneCombined]
                WHERE ColonyName = ?
            """, (colony_name,))

            trend_data = cursor.fetchone()
            birds_2010 = trend_data[0] if trend_data[0] else 0
            birds_2021 = trend_data[1] if trend_data[1] else 0

            if birds_2010 > 0 and birds_2021 > 0:
                trend_pct = ((birds_2021 - birds_2010) / birds_2010) * 100
            elif birds_2021 > 0 and birds_2010 == 0:
                trend_pct = 100.0  # New colony
            else:
                trend_pct = None  # No data for trend

            # Determine region and get erosion rate
            region = get_region_for_colony(colony_name, lat, lon)
            erosion_rate = get_erosion_rate(region)

            # Estimate colony characteristics
            # In production, these would come from GIS analysis
            estimated_area = 50000  # Default 5 hectares (typical small colony)
            estimated_elevation = get_colony_elevation_estimate("barrier_island")

            # Calculate comprehensive threat
            threat = calculate_combined_threat(
                current_area_m2=estimated_area,
                elevation_m=estimated_elevation,
                erosion_rate_m_per_year=erosion_rate,
                region=region,
                years_ahead=25  # 2050
            )

            # Insert risk assessment
            cursor.execute("""
                INSERT OR REPLACE INTO colony_risk_assessment
                (colony_name, latitude, longitude, region,
                 current_area_m2, average_elevation_m,
                 current_bird_count, species_count,
                 erosion_rate_m_per_year, years_until_uninhabitable,
                 slr_2050_m, percent_inundated_2050, habitability_2050,
                 combined_risk_score, risk_level, risk_color, recommended_action,
                 years_until_critical, population_trend_2010_2021_pct,
                 last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                colony_name, lat, lon, region,
                estimated_area, estimated_elevation,
                total_birds, species_count,
                erosion_rate,
                threat.get('years_until_critical'),
                threat['slr_projection']['slr_by_year'],
                threat['erosion_projection']['percent_area_lost'],
                threat['slr_projection']['habitability_status'],
                threat['combined_risk_score'],
                threat['risk_level'],
                threat['risk_color'],
                threat['recommended_action'],
                threat.get('years_until_critical'),
                trend_pct
            ))

            processed += 1

            if processed % 10 == 0:
                logger.info(f"Processed {processed}/{len(colonies)} colonies...")

        except Exception as e:
            logger.error(f"Error processing {colony_name}: {e}")
            continue

    conn.commit()
    conn.close()

    logger.info(f"Successfully processed {processed} colony risk assessments")


def generate_future_projections(db_path: str):
    """Generate projections for 2030, 2050, 2070, 2100"""
    logger.info("Generating future projections...")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT colony_name, current_area_m2, average_elevation_m,
               erosion_rate_m_per_year
        FROM colony_risk_assessment
    """)

    colonies = cursor.fetchall()

    projection_years = [2030, 2050, 2070, 2100]
    scenarios = ['low', 'intermediate', 'high']

    inserted = 0

    for colony_name, area, elevation, erosion_rate in colonies:
        for year in projection_years:
            for scenario in scenarios:
                years_ahead = year - 2025

                # Erosion projection
                erosion = calculate_erosion_projection(
                    area, erosion_rate, years_ahead
                )

                # SLR projection
                slr = calculate_inundation_risk(
                    elevation, year, scenario
                )

                try:
                    cursor.execute("""
                        INSERT OR REPLACE INTO colony_projections
                        (colony_name, projection_year, scenario,
                         projected_area_m2, projected_elevation_m,
                         inundated, habitable, storm_probability_pct)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        colony_name, year, scenario,
                        erosion['future_area_m2'],
                        slr['remaining_elevation_m'],
                        slr['inundated_typical_storm'],
                        not slr['inundated_typical_storm'],
                        50.0  # Placeholder storm probability
                    ))
                    inserted += 1
                except sqlite3.Error as e:
                    logger.warning(f"Failed to insert projection: {e}")

    conn.commit()
    conn.close()

    logger.info(f"Generated {inserted} future projections")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build coastal risk database")
    parser.add_argument(
        "--db",
        default="data/bird_data_complete.db",
        help="Path to database"
    )
    parser.add_argument(
        "--hurdat",
        default="data/real_sources/hurdat2.txt",
        help="Path to HURDAT2 file"
    )

    args = parser.parse_args()

    logger.info("="*60)
    logger.info("COASTAL RISK DATABASE BUILD")
    logger.info("="*60)

    # Step 1: Create tables
    create_risk_tables(args.db)

    # Step 2: Populate hurricane data
    populate_hurricane_data(args.db, args.hurdat)

    # Step 3: Calculate colony risks
    calculate_colony_risks(args.db)

    # Step 4: Generate future projections
    generate_future_projections(args.db)

    logger.info("="*60)
    logger.info("BUILD COMPLETE!")
    logger.info("="*60)
