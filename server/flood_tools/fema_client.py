"""
FEMA Flood Zone API Client
============================

Integrates with FEMA National Flood Hazard Layer (NFHL) REST API to get
flood zone classifications for bird colony locations.

FEMA Flood Zones:
- Zone A: High-risk flood area (1% annual chance of flooding)
- Zone AE: High-risk with Base Flood Elevation determined
- Zone V/VE: High-risk coastal areas with wave action
- Zone X (shaded): Moderate risk (0.2% annual chance)
- Zone X (unshaded): Minimal risk

API Documentation: https://hazards.fema.gov/gis/nfhl/rest/services/
"""

import requests
import logging
from typing import Dict, List, Optional, Tuple
from functools import lru_cache

logger = logging.getLogger(__name__)

# FEMA NFHL REST API endpoint
FEMA_API_BASE = "https://hazards.fema.gov/gis/nfhl/rest/services/public/NFHL/MapServer"

# Risk severity mapping
FEMA_ZONE_RISK = {
    'A': 4,    # High risk, no BFE
    'AE': 5,   # High risk with BFE (highest detail)
    'AO': 4,   # High risk, sheet flow
    'AH': 4,   # High risk, ponding
    'A99': 3,  # High risk, levee protection
    'V': 5,    # High risk, coastal wave action
    'VE': 5,   # High risk, coastal wave action with BFE
    'X500': 2, # Moderate risk (0.2% annual chance)
    'X': 1,    # Minimal risk
    'D': 1,    # Undetermined risk (assumed minimal)
}

class FEMAClient:
    """Client for FEMA National Flood Hazard Layer API"""

    def __init__(self):
        self.base_url = FEMA_API_BASE
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'NestScope/1.0 (Gulf Coast Bird Colony Risk Assessment)'
        })

    @lru_cache(maxsize=500)
    def get_flood_zone(self, latitude: float, longitude: float) -> Dict:
        """
        Get FEMA flood zone for a specific location.

        Args:
            latitude: Location latitude
            longitude: Location longitude

        Returns:
            Dict with 'zone', 'risk_level' (1-5), 'description'
        """
        try:
            # FEMA API uses State Plane or Web Mercator coordinates
            # Convert lat/lon to Web Mercator (EPSG:3857)
            x, y = self._latlon_to_web_mercator(latitude, longitude)

            # Query the NFHL MapServer for flood zones at this location
            # Layer 28 is the Special Flood Hazard Area layer
            identify_url = f"{self.base_url}/identify"

            params = {
                'geometry': f'{{"x": {x}, "y": {y}}}',
                'geometryType': 'esriGeometryPoint',
                'sr': '3857',  # Web Mercator spatial reference
                'layers': 'all:28',  # SFHA layer
                'tolerance': 10,
                'mapExtent': f'{x-1000},{y-1000},{x+1000},{y+1000}',
                'imageDisplay': '400,400,96',
                'returnGeometry': 'false',
                'f': 'json'
            }

            response = self.session.get(identify_url, params=params, timeout=1.5)  # Shorter timeout

            if response.status_code == 200:
                data = response.json()

                if 'results' in data and len(data['results']) > 0:
                    # Extract flood zone from first result
                    attributes = data['results'][0].get('attributes', {})
                    zone = attributes.get('FLD_ZONE', 'X')  # Default to minimal risk
                    zone_subtype = attributes.get('ZONE_SUBTY', '')

                    # Normalize zone code
                    zone_code = self._normalize_zone(zone, zone_subtype)
                    risk_level = FEMA_ZONE_RISK.get(zone_code, 1)

                    return {
                        'zone': zone_code,
                        'risk_level': risk_level,
                        'description': self._get_zone_description(zone_code),
                        'source': 'FEMA NFHL',
                        'bfe': attributes.get('STATIC_BFE'),  # Base Flood Elevation if available
                    }

            # If no data or API error, return default minimal risk
            logger.warning(f"No FEMA data for ({latitude}, {longitude}), assuming minimal risk")
            return {
                'zone': 'X',
                'risk_level': 1,
                'description': 'Outside mapped flood hazard area',
                'source': 'FEMA NFHL (default)'
            }

        except Exception as e:
            logger.error(f"FEMA API error for ({latitude}, {longitude}): {e}")
            # Graceful fallback
            return {
                'zone': 'UNKNOWN',
                'risk_level': 2,  # Assume moderate risk if unknown
                'description': 'Flood zone data unavailable',
                'source': 'FEMA NFHL (error)'
            }

    def get_flood_zones_batch(self, locations: List[Tuple[float, float]]) -> List[Dict]:
        """
        Get flood zones for multiple locations.

        Args:
            locations: List of (latitude, longitude) tuples

        Returns:
            List of flood zone dicts matching input order
        """
        results = []
        for lat, lon in locations:
            zone_data = self.get_flood_zone(lat, lon)
            results.append(zone_data)
        return results

    def _latlon_to_web_mercator(self, lat: float, lon: float) -> Tuple[float, float]:
        """Convert lat/lon to Web Mercator (EPSG:3857) coordinates"""
        import math

        # Earth radius in meters
        R = 6378137.0

        # Convert longitude
        x = R * math.radians(lon)

        # Convert latitude
        lat_rad = math.radians(lat)
        y = R * math.log(math.tan(math.pi / 4 + lat_rad / 2))

        return (x, y)

    def _normalize_zone(self, zone: str, subtype: str) -> str:
        """Normalize FEMA flood zone codes"""
        zone_upper = zone.upper().strip()

        # Handle subtypes
        if subtype:
            subtype_upper = subtype.upper().strip()
            if 'SHADED' in subtype_upper or '0.2 PCT ANNUAL CHANCE' in subtype_upper:
                return 'X500'

        # Common zone mappings
        if zone_upper in ['A', 'AE', 'AO', 'AH', 'A99', 'V', 'VE']:
            return zone_upper

        if zone_upper.startswith('X'):
            # X zones can be shaded (moderate) or unshaded (minimal)
            if '500' in zone_upper or 'SHADED' in subtype.upper():
                return 'X500'
            return 'X'

        if zone_upper in ['D', 'AREA NOT INCLUDED']:
            return 'D'

        # Default to minimal risk
        return 'X'

    def _get_zone_description(self, zone: str) -> str:
        """Get human-readable flood zone description"""
        descriptions = {
            'A': 'High flood risk area (1% annual chance)',
            'AE': 'High flood risk with base flood elevation determined',
            'AO': 'High flood risk with sheet flow flooding',
            'AH': 'High flood risk with ponding',
            'A99': 'High risk area with levee protection being constructed',
            'V': 'High risk coastal area with wave action',
            'VE': 'High risk coastal area with wave action and BFE',
            'X500': 'Moderate flood risk (0.2% annual chance)',
            'X': 'Minimal flood risk (outside 500-year floodplain)',
            'D': 'Undetermined flood hazard',
            'UNKNOWN': 'Flood zone data unavailable'
        }
        return descriptions.get(zone, 'Flood zone classification unknown')

    def get_100_year_floodplain(self, latitude: float, longitude: float) -> bool:
        """
        Check if location is in the 100-year floodplain (Zone A/AE/V/VE).

        Args:
            latitude: Location latitude
            longitude: Location longitude

        Returns:
            True if in 100-year floodplain, False otherwise
        """
        zone_data = self.get_flood_zone(latitude, longitude)
        high_risk_zones = ['A', 'AE', 'AO', 'AH', 'A99', 'V', 'VE']
        return zone_data['zone'] in high_risk_zones


# Singleton instance
_fema_client = None

def get_fema_client() -> FEMAClient:
    """Get singleton FEMA client instance"""
    global _fema_client
    if _fema_client is None:
        _fema_client = FEMAClient()
    return _fema_client
