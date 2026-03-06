"""
Generate realistic synthetic flood data for Louisiana coastal stations
Based on known Gulf Coast flooding patterns and major storm events
"""

import sys
from pathlib import Path
import logging
from datetime import datetime, timedelta
import random

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from server.flood_tools.flood_database import FloodDatabase
from server.flood_tools.noaa_client import LOUISIANA_STATIONS

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Major Gulf Coast flood/storm events (2010-2021)
MAJOR_EVENTS = [
    {
        "year": 2011,
        "month": 4,
        "name": "Spring Floods",
        "severity_multiplier": 1.5
    },
    {
        "year": 2012,
        "month": 8,
        "name": "Hurricane Isaac",
        "severity_multiplier": 3.0
    },
    {
        "year": 2016,
        "month": 8,
        "name": "Louisiana Floods",
        "severity_multiplier": 2.5
    },
    {
        "year": 2017,
        "month": 8,
        "name": "Hurricane Harvey",
        "severity_multiplier": 2.0
    },
    {
        "year": 2020,
        "month": 8,
        "name": "Hurricane Laura",
        "severity_multiplier": 2.8
    },
    {
        "year": 2021,
        "month": 8,
        "name": "Hurricane Ida",
        "severity_multiplier": 3.5
    }
]

# King tide months (highest normal tides)
KING_TIDE_MONTHS = [10, 11, 12]  # October-December

def generate_baseline_events(year: int, month: int, station_id: str) -> list:
    """Generate baseline minor flooding events (normal seasonal variation)"""
    events = []

    # More events during king tide season
    if month in KING_TIDE_MONTHS:
        num_events = random.randint(3, 8)
    else:
        num_events = random.randint(1, 4)

    for i in range(num_events):
        # Random day in month
        day = random.randint(1, 28)
        hour = random.randint(0, 23)

        timestamp = f"{year}-{month:02d}-{day:02d}T{hour:02d}:00:00Z"

        # Minor flooding: 0.5-0.8m exceedance
        exceedance = random.uniform(0.50, 0.80)
        water_level = 0.5 + exceedance  # MHHW + exceedance

        events.append({
            'timestamp': timestamp,
            'water_level': water_level,
            'exceedance': exceedance,
            'severity': 'minor'
        })

    return events


def generate_major_event_flooding(year: int, month: int, station_id: str, multiplier: float) -> list:
    """Generate major flooding events during storms"""
    events = []

    # Multiple days of flooding during major events
    num_days = random.randint(3, 7)

    for day_offset in range(num_days):
        # Peak flooding in middle of event
        if day_offset == num_days // 2:
            severity = 'major'
            exceedance = random.uniform(1.5, 2.5) * multiplier
        elif day_offset in [num_days // 2 - 1, num_days // 2 + 1]:
            severity = 'moderate'
            exceedance = random.uniform(1.0, 1.4) * multiplier
        else:
            severity = 'minor'
            exceedance = random.uniform(0.5, 0.9) * multiplier

        # Ensure exceedance doesn't exceed severity thresholds incorrectly
        if exceedance >= 1.5:
            severity = 'major'
        elif exceedance >= 1.0:
            severity = 'moderate'
        else:
            severity = 'minor'

        # Random day in the month
        day = random.randint(1, 28)
        hour = random.randint(0, 23)

        timestamp = f"{year}-{month:02d}-{day:02d}T{hour:02d}:00:00Z"
        water_level = 0.5 + exceedance

        events.append({
            'timestamp': timestamp,
            'water_level': water_level,
            'exceedance': exceedance,
            'severity': severity
        })

    return events


def generate_moderate_events(year: int, month: int, station_id: str) -> list:
    """Generate occasional moderate flooding (spring tides, weather systems)"""
    events = []

    # 20% chance of moderate flooding any given month
    if random.random() < 0.2:
        num_events = random.randint(1, 3)

        for i in range(num_events):
            day = random.randint(1, 28)
            hour = random.randint(0, 23)

            timestamp = f"{year}-{month:02d}-{day:02d}T{hour:02d}:00:00Z"

            # Moderate flooding: 1.0-1.4m exceedance
            exceedance = random.uniform(1.0, 1.4)
            water_level = 0.5 + exceedance

            events.append({
                'timestamp': timestamp,
                'water_level': water_level,
                'exceedance': exceedance,
                'severity': 'moderate'
            })

    return events


def generate_flood_data_for_station_year(station_id: str, year: int) -> dict:
    """Generate realistic flood data for one station-year"""
    all_events = []

    for month in range(1, 13):
        # Check if this is a major event month
        major_event = None
        for event in MAJOR_EVENTS:
            if event['year'] == year and event['month'] == month:
                major_event = event
                break

        if major_event:
            # Generate major event flooding
            logger.info(f"  {year}-{month:02d}: {major_event['name']}")
            events = generate_major_event_flooding(
                year, month, station_id, major_event['severity_multiplier']
            )
            all_events.extend(events)
        else:
            # Generate baseline + occasional moderate events
            baseline = generate_baseline_events(year, month, station_id)
            moderate = generate_moderate_events(year, month, station_id)
            all_events.extend(baseline)
            all_events.extend(moderate)

    return {
        'station_id': station_id,
        'year': year,
        'events': all_events
    }


def populate_synthetic_flood_data(
    db_path: str = "data/bird_data_complete.db",
    start_year: int = 2010,
    end_year: int = 2021
):
    """
    Generate and populate synthetic flood data

    Args:
        db_path: Path to SQLite database
        start_year: First year (inclusive)
        end_year: Last year (inclusive)
    """
    logger.info("="*60)
    logger.info("SYNTHETIC FLOOD DATA GENERATION")
    logger.info(f"Date range: {start_year}-{end_year}")
    logger.info(f"Database: {db_path}")
    logger.info("="*60)

    db = FloodDatabase(db_path)

    # Insert station metadata
    logger.info(f"\nInserting {len(LOUISIANA_STATIONS)} stations...")
    for station_id, info in LOUISIANA_STATIONS.items():
        db.insert_station(
            station_id=station_id,
            station_name=info['name'],
            latitude=info['latitude'],
            longitude=info['longitude'],
            region=info['region'],
            mhhw_value=0.5  # Standard MHHW estimate for Gulf Coast
        )

    total_events = 0

    # Generate data for each station-year
    for station_id, info in LOUISIANA_STATIONS.items():
        logger.info(f"\n{'='*60}")
        logger.info(f"Station: {info['name']} ({station_id})")
        logger.info(f"{'='*60}")

        station_events = 0

        for year in range(start_year, end_year + 1):
            result = generate_flood_data_for_station_year(station_id, year)
            events = result['events']

            if events:
                inserted = db.insert_flood_events(station_id, events)
                station_events += inserted
                logger.info(f"  {year}: Generated {len(events)} events, inserted {inserted}")

        logger.info(f"Total for {info['name']}: {station_events} events")
        total_events += station_events

    # Final statistics
    logger.info("\n" + "="*60)
    logger.info("GENERATION COMPLETE")
    logger.info("="*60)

    stats = db.get_database_stats()
    logger.info(f"Total stations: {stats['station_count']}")
    logger.info(f"Total flood events: {stats['event_count']}")
    logger.info(f"Year range: {stats['year_range'][0]} - {stats['year_range'][1]}")
    logger.info("="*60)

    # Show major events summary
    logger.info("\nMajor Events Included:")
    for event in MAJOR_EVENTS:
        logger.info(f"  {event['year']}-{event['month']:02d}: {event['name']}")

    return total_events


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate synthetic flood data")
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
        help="Clear existing flood data before generating"
    )

    args = parser.parse_args()

    # Clear if requested
    if args.clear:
        logger.warning("Clearing existing flood data...")
        db = FloodDatabase(args.db)
        db.clear_flood_events()

    # Generate data
    try:
        populate_synthetic_flood_data(
            db_path=args.db,
            start_year=args.start_year,
            end_year=args.end_year
        )
        logger.info("\nSUCCESS: Synthetic flood data generated!")

    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
        sys.exit(1)

    except Exception as e:
        logger.error(f"FAILED: {e}", exc_info=True)
        sys.exit(1)
