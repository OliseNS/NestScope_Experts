"""
Flood data database schema and operations
Stores NOAA flood events and station metadata
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class FloodDatabase:
    """Database manager for flood event data"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()

    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)

    def init_database(self):
        """Initialize flood database schema"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Stations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS flood_stations (
                station_id TEXT PRIMARY KEY,
                station_name TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                region TEXT,
                mhhw_value REAL,
                last_updated TIMESTAMP
            )
        """)

        # Flood events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS flood_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                station_id TEXT NOT NULL,
                event_timestamp TIMESTAMP NOT NULL,
                water_level REAL NOT NULL,
                exceedance REAL NOT NULL,
                severity TEXT NOT NULL,
                year INTEGER NOT NULL,
                month INTEGER NOT NULL,
                FOREIGN KEY (station_id) REFERENCES flood_stations(station_id),
                UNIQUE(station_id, event_timestamp)
            )
        """)

        # Index for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_flood_events_year
            ON flood_events(year)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_flood_events_station
            ON flood_events(station_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_flood_events_severity
            ON flood_events(severity)
        """)

        conn.commit()
        conn.close()

        logger.info("Flood database initialized")

    def insert_station(
        self,
        station_id: str,
        station_name: str,
        latitude: float,
        longitude: float,
        region: str = None,
        mhhw_value: float = None
    ) -> bool:
        """Insert or update a flood monitoring station"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT OR REPLACE INTO flood_stations
                (station_id, station_name, latitude, longitude, region, mhhw_value, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (station_id, station_name, latitude, longitude, region, mhhw_value, datetime.now()))

            conn.commit()
            logger.info(f"Inserted/updated station {station_id}")
            return True

        except sqlite3.Error as e:
            logger.error(f"Failed to insert station {station_id}: {e}")
            return False

        finally:
            conn.close()

    def insert_flood_events(
        self,
        station_id: str,
        events: List[Dict]
    ) -> int:
        """
        Insert multiple flood events for a station

        Args:
            station_id: NOAA station ID
            events: List of flood event dicts with keys:
                    timestamp, water_level, exceedance, severity

        Returns:
            Number of events inserted
        """
        if not events:
            return 0

        conn = self.get_connection()
        cursor = conn.cursor()

        inserted = 0

        for event in events:
            try:
                # Parse timestamp
                timestamp = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
                year = timestamp.year
                month = timestamp.month

                cursor.execute("""
                    INSERT OR IGNORE INTO flood_events
                    (station_id, event_timestamp, water_level, exceedance, severity, year, month)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    station_id,
                    timestamp,
                    event['water_level'],
                    event['exceedance'],
                    event['severity'],
                    year,
                    month
                ))

                if cursor.rowcount > 0:
                    inserted += 1

            except (ValueError, KeyError, sqlite3.Error) as e:
                logger.warning(f"Failed to insert flood event: {e}")
                continue

        conn.commit()
        conn.close()

        logger.info(f"Inserted {inserted} flood events for station {station_id}")
        return inserted

    def get_all_stations(self) -> List[Dict]:
        """Get all flood monitoring stations"""
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT station_id, station_name, latitude, longitude, region, mhhw_value, last_updated
            FROM flood_stations
            ORDER BY station_name
        """)

        stations = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return stations

    def get_station(self, station_id: str) -> Optional[Dict]:
        """Get a specific station by ID"""
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT station_id, station_name, latitude, longitude, region, mhhw_value, last_updated
            FROM flood_stations
            WHERE station_id = ?
        """, (station_id,))

        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None

    def get_flood_events(
        self,
        station_id: Optional[str] = None,
        year: Optional[int] = None,
        min_severity: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict]:
        """
        Query flood events with filters

        Args:
            station_id: Filter by station (optional)
            year: Filter by year (optional)
            min_severity: Minimum severity level (minor, moderate, major)
            limit: Maximum number of results

        Returns:
            List of flood event dicts
        """
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Build query dynamically
        query = """
            SELECT
                fe.id,
                fe.station_id,
                fs.station_name,
                fs.latitude,
                fs.longitude,
                fs.region,
                fe.event_timestamp,
                fe.water_level,
                fe.exceedance,
                fe.severity,
                fe.year,
                fe.month
            FROM flood_events fe
            JOIN flood_stations fs ON fe.station_id = fs.station_id
            WHERE 1=1
        """
        params = []

        if station_id:
            query += " AND fe.station_id = ?"
            params.append(station_id)

        if year:
            query += " AND fe.year = ?"
            params.append(year)

        if min_severity:
            severity_order = {'minor': 1, 'moderate': 2, 'major': 3}
            if min_severity == 'moderate':
                query += " AND fe.severity IN ('moderate', 'major')"
            elif min_severity == 'major':
                query += " AND fe.severity = 'major'"

        query += " ORDER BY fe.event_timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        events = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return events

    def get_flood_summary_by_year(self, station_id: Optional[str] = None) -> List[Dict]:
        """
        Get flood event counts by year and severity

        Args:
            station_id: Filter by station (optional)

        Returns:
            List of yearly summaries
        """
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = """
            SELECT
                year,
                severity,
                COUNT(*) as event_count,
                AVG(exceedance) as avg_exceedance
            FROM flood_events
        """

        if station_id:
            query += " WHERE station_id = ?"
            params = (station_id,)
        else:
            params = ()

        query += " GROUP BY year, severity ORDER BY year, severity"

        cursor.execute(query, params)
        summary = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return summary

    def get_stations_near_point(
        self,
        latitude: float,
        longitude: float,
        max_distance_km: float = 50
    ) -> List[Dict]:
        """
        Find flood stations near a geographic point

        Args:
            latitude: Point latitude
            longitude: Point longitude
            max_distance_km: Maximum distance in kilometers

        Returns:
            List of nearby stations with calculated distance
        """
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Haversine formula for distance calculation (simplified for small distances)
        # Note: This is approximate but sufficient for our use case
        cursor.execute("""
            SELECT
                station_id,
                station_name,
                latitude,
                longitude,
                region,
                (
                    6371 * acos(
                        cos(radians(?)) * cos(radians(latitude)) *
                        cos(radians(longitude) - radians(?)) +
                        sin(radians(?)) * sin(radians(latitude))
                    )
                ) as distance_km
            FROM flood_stations
            HAVING distance_km <= ?
            ORDER BY distance_km
        """, (latitude, longitude, latitude, max_distance_km))

        stations = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return stations

    def clear_flood_events(self, station_id: Optional[str] = None):
        """Clear flood events (for re-importing)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        if station_id:
            cursor.execute("DELETE FROM flood_events WHERE station_id = ?", (station_id,))
            logger.info(f"Cleared flood events for station {station_id}")
        else:
            cursor.execute("DELETE FROM flood_events")
            logger.info("Cleared all flood events")

        conn.commit()
        conn.close()

    def get_database_stats(self) -> Dict:
        """Get database statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM flood_stations")
        station_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM flood_events")
        event_count = cursor.fetchone()[0]

        cursor.execute("SELECT MIN(year), MAX(year) FROM flood_events")
        year_range = cursor.fetchone()

        conn.close()

        return {
            'station_count': station_count,
            'event_count': event_count,
            'year_range': year_range if year_range[0] else (None, None)
        }
