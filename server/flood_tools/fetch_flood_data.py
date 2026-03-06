"""
Script to fetch and populate historical flood data from NOAA
Run this to populate the database with 2010-2021 flood events
"""

import sys
from pathlib import Path
import logging
from datetime import datetime
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from server.flood_tools.noaa_client import NOAAClient, year_to_date_range, LOUISIANA_STATIONS
from server.flood_tools.flood_database import FloodDatabase

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def fetch_station_datums(client: NOAAClient, station_id: str) -> float:
    """
    Fetch MHHW (Mean Higher High Water) datum for a station
    This is the baseline for flood detection

    Returns:
        MHHW value in meters, or default estimate if unavailable
    """
    logger.info(f"Fetching datums for station {station_id}...")
    datums_data = client.get_datums(station_id)

    if not datums_data or 'datums' not in datums_data:
        logger.warning(f"Could not fetch datums for {station_id}, using default estimate")
        return 0.5  # Default MHHW estimate for Gulf Coast

    # Find MHHW datum
    for datum in datums_data['datums']:
        if datum['n'] == 'MHHW':
            try:
                mhhw = float(datum['v'])
                logger.info(f"Station {station_id} MHHW: {mhhw:.3f}m")
                return mhhw
            except (ValueError, KeyError):
                pass

    logger.warning(f"MHHW not found for {station_id}, using default estimate")
    return 0.5


def fetch_year_data(
    client: NOAAClient,
    db: FloodDatabase,
    station_id: str,
    year: int,
    mhhw_value: float
) -> int:
    """
    Fetch and process flood data for one station-year

    Returns:
        Number of flood events detected
    """
    logger.info(f"Fetching {year} data for station {station_id}...")

    begin_date, end_date = year_to_date_range(year)

    # Fetch water level data
    water_data = client.get_water_levels(
        station_id=station_id,
        begin_date=begin_date,
        end_date=end_date,
        datum="MLLW"  # Mean Lower Low Water (standard datum)
    )

    if not water_data:
        logger.warning(f"No data returned for {station_id} in {year}")
        return 0

    # Detect flood events
    flood_events = client.detect_flood_events(water_data, mhhw_value)

    if flood_events:
        # Store in database
        inserted = db.insert_flood_events(station_id, flood_events)
        logger.info(f"Found {len(flood_events)} flood events in {year}, inserted {inserted}")
        return inserted
    else:
        logger.info(f"No flood events detected in {year}")
        return 0


def populate_flood_database(
    db_path: str = "data/bird_data_complete.db",
    start_year: int = 2010,
    end_year: int = 2021
):
    """
    Main function to populate flood database with historical data

    Args:
        db_path: Path to SQLite database
        start_year: First year to fetch (inclusive)
        end_year: Last year to fetch (inclusive)
    """
    logger.info("="*60)
    logger.info("NOAA Flood Data Fetch - Starting")
    logger.info(f"Date range: {start_year}-{end_year}")
    logger.info(f"Database: {db_path}")
    logger.info("="*60)

    # Initialize
    client = NOAAClient()
    db = FloodDatabase(db_path)

    # Get station info
    all_stations = client.get_all_stations()
    logger.info(f"Processing {len(all_stations)} Louisiana coastal stations")

    total_events = 0

    # Process each station
    for station_id, station_info in all_stations.items():
        logger.info(f"\n{'='*60}")
        logger.info(f"Station: {station_info['name']} ({station_id})")
        logger.info(f"Location: {station_info['latitude']:.4f}, {station_info['longitude']:.4f}")
        logger.info(f"Region: {station_info['region']}")
        logger.info(f"{'='*60}")

        # Get MHHW datum for flood detection
        mhhw_value = fetch_station_datums(client, station_id)

        # Insert station metadata
        db.insert_station(
            station_id=station_id,
            station_name=station_info['name'],
            latitude=station_info['latitude'],
            longitude=station_info['longitude'],
            region=station_info['region'],
            mhhw_value=mhhw_value
        )

        station_events = 0

        # Fetch data for each year
        for year in range(start_year, end_year + 1):
            try:
                events = fetch_year_data(client, db, station_id, year, mhhw_value)
                station_events += events

                # Be nice to NOAA servers - rate limit
                time.sleep(1)

            except Exception as e:
                logger.error(f"Error fetching {year} data for {station_id}: {e}")
                continue

        logger.info(f"Total events for {station_info['name']}: {station_events}")
        total_events += station_events

        # Longer pause between stations
        logger.info("Pausing between stations...")
        time.sleep(2)

    # Final statistics
    logger.info("\n" + "="*60)
    logger.info("FETCH COMPLETE")
    logger.info("="*60)

    stats = db.get_database_stats()
    logger.info(f"Total stations: {stats['station_count']}")
    logger.info(f"Total flood events: {stats['event_count']}")
    logger.info(f"Year range: {stats['year_range'][0]} - {stats['year_range'][1]}")
    logger.info("="*60)

    return total_events


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fetch NOAA flood data")
    parser.add_argument(
        "--db",
        default="data/bird_data_complete.db",
        help="Path to database file"
    )
    parser.add_argument(
        "--start-year",
        type=int,
        default=2010,
        help="Start year (default: 2010)"
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=2021,
        help="End year (default: 2021)"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing flood data before fetching"
    )

    args = parser.parse_args()

    # Clear if requested
    if args.clear:
        logger.warning("Clearing existing flood data...")
        db = FloodDatabase(args.db)
        db.clear_flood_events()

    # Run fetch
    try:
        populate_flood_database(
            db_path=args.db,
            start_year=args.start_year,
            end_year=args.end_year
        )
        logger.info("SUCCESS: Flood data populated!")

    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
        sys.exit(1)

    except Exception as e:
        logger.error(f"FAILED: {e}", exc_info=True)
        sys.exit(1)
