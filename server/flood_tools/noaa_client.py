"""
NOAA Tides and Currents API Client
Fetches water level and flood data from NOAA CO-OPS stations
"""

import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Louisiana coastal stations near bird colonies
LOUISIANA_STATIONS = {
    "8761724": {
        "name": "Grand Isle, LA",
        "latitude": 29.2633,
        "longitude": -89.9567,
        "region": "Barataria Bay"
    },
    "8761305": {
        "name": "Shell Beach, LA",
        "latitude": 29.8683,
        "longitude": -89.6733,
        "region": "Lake Borgne"
    },
    "8761927": {
        "name": "New Canal Station, LA",
        "latitude": 30.0267,
        "longitude": -90.1133,
        "region": "Lake Pontchartrain"
    },
    "8762075": {
        "name": "Port Fourchon, LA",
        "latitude": 29.1150,
        "longitude": -90.1983,
        "region": "Terrebonne Bay"
    },
    "8764227": {
        "name": "LAWMA, Amerada Pass, LA",
        "latitude": 29.4500,
        "longitude": -91.3383,
        "region": "Atchafalaya Bay"
    },
    "8760922": {
        "name": "Pilots Station East, SW Pass, LA",
        "latitude": 28.9317,
        "longitude": -89.4067,
        "region": "Mississippi River Delta"
    }
}

# Flood severity thresholds (meters above MHHW - Mean Higher High Water)
FLOOD_THRESHOLDS = {
    "minor": 0.5,      # Minor coastal flooding
    "moderate": 1.0,   # Moderate flooding - roads impassable
    "major": 1.5       # Major flooding - significant habitat impact
}

class NOAAClient:
    """Client for fetching NOAA water level and flood data"""

    BASE_URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'NestScope/1.0 (Educational Project)'
        })

    def get_water_levels(
        self,
        station_id: str,
        begin_date: str,
        end_date: str,
        datum: str = "MLLW"
    ) -> Optional[Dict]:
        """
        Fetch water level data for a station

        Args:
            station_id: NOAA station ID (e.g., "8761724")
            begin_date: Start date in YYYYMMDD format
            end_date: End date in YYYYMMDD format
            datum: Tidal datum (MLLW, MHHW, MSL, etc.)

        Returns:
            Dict with water level data or None if request fails
        """
        params = {
            'station': station_id,
            'begin_date': begin_date,
            'end_date': end_date,
            'product': 'water_level',
            'datum': datum,
            'units': 'metric',
            'time_zone': 'gmt',
            'format': 'json',
            'application': 'NestScope'
        }

        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if 'error' in data:
                logger.error(f"NOAA API error for station {station_id}: {data['error']}")
                return None

            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch water levels for station {station_id}: {e}")
            return None

    def get_high_low_tides(
        self,
        station_id: str,
        begin_date: str,
        end_date: str
    ) -> Optional[Dict]:
        """
        Fetch high/low tide predictions for a station

        Args:
            station_id: NOAA station ID
            begin_date: Start date in YYYYMMDD format
            end_date: End date in YYYYMMDD format

        Returns:
            Dict with tide data or None if request fails
        """
        params = {
            'station': station_id,
            'begin_date': begin_date,
            'end_date': end_date,
            'product': 'high_low',
            'datum': 'MLLW',
            'units': 'metric',
            'time_zone': 'gmt',
            'format': 'json',
            'application': 'NestScope'
        }

        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if 'error' in data:
                logger.error(f"NOAA API error for station {station_id}: {data['error']}")
                return None

            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch tides for station {station_id}: {e}")
            return None

    def get_datums(self, station_id: str) -> Optional[Dict]:
        """
        Get tidal datums (reference levels) for a station
        This is needed to determine flood thresholds

        Args:
            station_id: NOAA station ID

        Returns:
            Dict with datum values or None if request fails
        """
        params = {
            'station': station_id,
            'product': 'datums',
            'units': 'metric',
            'format': 'json',
            'application': 'NestScope'
        }

        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if 'error' in data:
                logger.error(f"NOAA API error for station {station_id}: {data['error']}")
                return None

            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch datums for station {station_id}: {e}")
            return None

    def detect_flood_events(
        self,
        water_level_data: Dict,
        mhhw_value: float
    ) -> List[Dict]:
        """
        Detect flood events from water level data

        Args:
            water_level_data: NOAA water level response
            mhhw_value: Mean Higher High Water level in meters

        Returns:
            List of flood events with severity classification
        """
        if not water_level_data or 'data' not in water_level_data:
            return []

        flood_events = []

        for reading in water_level_data.get('data', []):
            try:
                water_level = float(reading['v'])
                timestamp = reading['t']

                # Calculate exceedance above MHHW
                exceedance = water_level - mhhw_value

                # Classify severity
                severity = None
                if exceedance >= FLOOD_THRESHOLDS['major']:
                    severity = 'major'
                elif exceedance >= FLOOD_THRESHOLDS['moderate']:
                    severity = 'moderate'
                elif exceedance >= FLOOD_THRESHOLDS['minor']:
                    severity = 'minor'

                if severity:
                    flood_events.append({
                        'timestamp': timestamp,
                        'water_level': water_level,
                        'exceedance': exceedance,
                        'severity': severity
                    })

            except (ValueError, KeyError) as e:
                logger.warning(f"Invalid water level reading: {e}")
                continue

        return flood_events

    def get_all_stations(self) -> Dict[str, Dict]:
        """Get information about all Louisiana coastal stations"""
        return LOUISIANA_STATIONS.copy()

    def get_station_info(self, station_id: str) -> Optional[Dict]:
        """Get information about a specific station"""
        return LOUISIANA_STATIONS.get(station_id)


# Utility functions for date formatting
def year_to_date_range(year: int) -> tuple[str, str]:
    """Convert year to NOAA API date format (YYYYMMDD)"""
    begin = f"{year}0101"
    end = f"{year}1231"
    return begin, end


def date_to_noaa_format(date: datetime) -> str:
    """Convert datetime to NOAA API format (YYYYMMDD)"""
    return date.strftime("%Y%m%d")
