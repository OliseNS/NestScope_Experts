"""
Parse NOAA HURDAT2 hurricane database and extract Gulf Coast storms
Future projection models for storm frequency and intensity
"""

import csv
from datetime import datetime
from typing import List, Dict, Tuple
import re


def parse_hurdat2(file_path: str) -> List[Dict]:
    """
    Parse HURDAT2 format hurricane data

    Format:
    Line 1: Storm header (ID, Name, Number of entries)
    Lines 2+: Track points (Date, Time, Record, Status, Lat, Lon, Wind, Pressure, ...)

    Returns:
        List of storm dictionaries with track points
    """
    storms = []
    current_storm = None

    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            # Check if this is a header line (starts with AL or EP)
            if line[0:2] in ['AL', 'EP']:
                # Save previous storm if exists
                if current_storm and current_storm['tracks']:
                    storms.append(current_storm)

                # Parse header: AL012005,              HURRICANE KATRINA,      44,
                parts = [p.strip() for p in line.split(',')]
                storm_id = parts[0]
                name = parts[1] if len(parts) > 1 else "UNNAMED"
                num_entries = int(parts[2]) if len(parts) > 2 else 0

                current_storm = {
                    'id': storm_id,
                    'name': name.replace('HURRICANE', '').replace('TROPICAL STORM', '').strip(),
                    'year': int(storm_id[4:8]),
                    'tracks': []
                }
            else:
                # Parse track point
                # Format: 20050823, 1800,  , HU, 25.4N,  76.9W, 100, 957, ...
                parts = [p.strip() for p in line.split(',')]

                if len(parts) < 7:
                    continue

                try:
                    date_str = parts[0]
                    time_str = parts[1]
                    status = parts[3]  # HU=Hurricane, TS=Tropical Storm, etc.

                    # Parse latitude (e.g., "25.4N")
                    lat_str = parts[4]
                    lat = float(lat_str[:-1])
                    if lat_str[-1] == 'S':
                        lat = -lat

                    # Parse longitude (e.g., "76.9W")
                    lon_str = parts[5]
                    lon = float(lon_str[:-1])
                    if lon_str[-1] == 'W':
                        lon = -lon

                    # Wind speed (knots)
                    wind = int(parts[6]) if parts[6] and parts[6] != '-999' else 0

                    # Pressure (mb)
                    pressure = int(parts[7]) if parts[7] and parts[7] != '-999' else 0

                    track_point = {
                        'date': date_str,
                        'time': time_str,
                        'status': status,
                        'lat': lat,
                        'lon': lon,
                        'wind_kt': wind,
                        'pressure_mb': pressure
                    }

                    if current_storm:
                        current_storm['tracks'].append(track_point)

                except (ValueError, IndexError) as e:
                    continue

    # Add last storm
    if current_storm and current_storm['tracks']:
        storms.append(current_storm)

    return storms


def filter_gulf_coast_storms(storms: List[Dict],
                             min_year: int = 2005,
                             lat_range: Tuple[float, float] = (27.0, 31.0),
                             lon_range: Tuple[float, float] = (-94.0, -87.0),
                             min_wind: int = 34) -> List[Dict]:
    """
    Filter storms that affected the Louisiana/Gulf Coast region

    Args:
        storms: List of storm dictionaries from parse_hurdat2
        min_year: Minimum year to include
        lat_range: Latitude bounds (min, max)
        lon_range: Longitude bounds (min, max) - negative for West
        min_wind: Minimum wind speed (knots) for tropical storm strength

    Returns:
        Filtered list of storms
    """
    gulf_storms = []

    for storm in storms:
        if storm['year'] < min_year:
            continue

        # Check if any track point is in Gulf Coast region
        in_region = False
        max_wind = 0

        for track in storm['tracks']:
            if (lat_range[0] <= track['lat'] <= lat_range[1] and
                lon_range[0] <= track['lon'] <= lon_range[1] and
                track['wind_kt'] >= min_wind):
                in_region = True
                max_wind = max(max_wind, track['wind_kt'])

        if in_region:
            storm['max_wind_in_region'] = max_wind
            storm['category'] = wind_to_category(max_wind)
            gulf_storms.append(storm)

    return gulf_storms


def wind_to_category(wind_kt: int) -> str:
    """Convert wind speed to hurricane category or storm type"""
    if wind_kt < 34:
        return "Tropical Depression"
    elif wind_kt < 64:
        return "Tropical Storm"
    elif wind_kt < 83:
        return "Category 1"
    elif wind_kt < 96:
        return "Category 2"
    elif wind_kt < 113:
        return "Category 3"
    elif wind_kt < 137:
        return "Category 4"
    else:
        return "Category 5"


def get_major_storms_summary(min_year: int = 2005) -> List[Dict]:
    """
    Get summary of major Gulf Coast storms

    Returns:
        List of storm summaries with name, year, category, impact description
    """
    # Well-documented major storms
    major_storms = [
        {
            "name": "Katrina",
            "year": 2005,
            "month": 8,
            "category": "Category 5",
            "max_wind_kt": 150,
            "impact": "Catastrophic flooding, New Orleans levee failures, $125B damage",
            "bird_impact": "Massive habitat destruction, colony abandonment"
        },
        {
            "name": "Rita",
            "year": 2005,
            "month": 9,
            "category": "Category 5",
            "max_wind_kt": 155,
            "impact": "Southwest Louisiana devastation, coastal erosion",
            "bird_impact": "Cameron Parish colony losses"
        },
        {
            "name": "Gustav",
            "year": 2008,
            "month": 9,
            "category": "Category 4",
            "max_wind_kt": 135,
            "impact": "Widespread Louisiana flooding and wind damage",
            "bird_impact": "Barrier island habitat degradation"
        },
        {
            "name": "Ike",
            "year": 2008,
            "month": 9,
            "category": "Category 4",
            "max_wind_kt": 125,
            "impact": "Texas/Louisiana border, massive storm surge",
            "bird_impact": "Coastal wetland inundation"
        },
        {
            "name": "Isaac",
            "year": 2012,
            "month": 8,
            "category": "Category 1",
            "max_wind_kt": 70,
            "impact": "Slow-moving, prolonged flooding in southeast Louisiana",
            "bird_impact": "Extended nest site flooding, population decline"
        },
        {
            "name": "Harvey",
            "year": 2017,
            "month": 8,
            "category": "Category 4",
            "max_wind_kt": 115,
            "impact": "Texas catastrophic rainfall, indirect Louisiana impacts",
            "bird_impact": "Texas colony devastation, displacement"
        },
        {
            "name": "Laura",
            "year": 2020,
            "month": 8,
            "category": "Category 4",
            "max_wind_kt": 130,
            "impact": "Southwest Louisiana direct hit, Lake Charles destroyed",
            "bird_impact": "Cameron Parish nesting sites severely damaged"
        },
        {
            "name": "Delta",
            "year": 2020,
            "month": 10,
            "category": "Category 3",
            "max_wind_kt": 105,
            "impact": "Hit same area as Laura 6 weeks later",
            "bird_impact": "Compounded habitat destruction"
        },
        {
            "name": "Ida",
            "year": 2021,
            "month": 8,
            "category": "Category 4",
            "max_wind_kt": 130,
            "impact": "Grand Isle/Port Fourchon devastation, $75B damage",
            "bird_impact": "Barataria Bay colonies heavily impacted, breeding season disruption"
        },
        {
            "name": "Francine",
            "year": 2024,
            "month": 9,
            "category": "Category 2",
            "max_wind_kt": 85,
            "impact": "Southeast Louisiana landfall, moderate impacts",
            "bird_impact": "Recent event, assessment ongoing"
        }
    ]

    return [s for s in major_storms if s['year'] >= min_year]


def calculate_storm_frequency_trend(storms: List[Dict],
                                    window_years: int = 5) -> Dict:
    """
    Calculate storm frequency trends to project future risk

    Args:
        storms: List of storm dictionaries
        window_years: Rolling window for trend calculation

    Returns:
        Dictionary with frequency statistics and projections
    """
    if not storms:
        return {}

    # Count storms by year
    year_counts = {}
    for storm in storms:
        year = storm['year']
        year_counts[year] = year_counts.get(year, 0) + 1

    # Calculate rolling averages
    years = sorted(year_counts.keys())
    min_year = min(years)
    max_year = max(years)

    total_storms = len(storms)
    total_years = max_year - min_year + 1
    avg_per_year = total_storms / total_years

    # Recent trend (last 10 years)
    recent_years = [y for y in years if y >= max_year - 9]
    recent_storms = sum(year_counts.get(y, 0) for y in recent_years)
    recent_avg = recent_storms / len(recent_years) if recent_years else 0

    # Historical average (before last 10 years)
    historical_years = [y for y in years if y < max_year - 9]
    historical_storms = sum(year_counts.get(y, 0) for y in historical_years)
    historical_avg = historical_storms / len(historical_years) if historical_years else 0

    # Calculate percent change
    if historical_avg > 0:
        percent_increase = ((recent_avg - historical_avg) / historical_avg) * 100
    else:
        percent_increase = 0

    return {
        'total_storms': total_storms,
        'year_range': (min_year, max_year),
        'avg_per_year': round(avg_per_year, 2),
        'recent_avg': round(recent_avg, 2),
        'historical_avg': round(historical_avg, 2),
        'percent_change': round(percent_increase, 1),
        'trend': 'increasing' if percent_increase > 10 else 'stable' if percent_increase > -10 else 'decreasing'
    }


def project_future_storm_risk(base_frequency: float,
                              years_ahead: int = 10,
                              climate_factor: float = 1.15) -> Dict:
    """
    Project future storm risk based on current trends and climate models

    Args:
        base_frequency: Current average storms per year
        years_ahead: How many years to project
        climate_factor: Multiplier for climate change (1.15 = 15% increase)

    Returns:
        Dictionary with future projections
    """
    projected_frequency = base_frequency * climate_factor

    # Probability calculations
    prob_one_per_year = 1 - (1 - projected_frequency) ** 1
    prob_major_in_decade = 1 - (1 - (projected_frequency * 0.3)) ** years_ahead  # Assume 30% are major

    return {
        'years_ahead': years_ahead,
        'current_frequency': round(base_frequency, 2),
        'projected_frequency': round(projected_frequency, 2),
        'percent_increase': round((climate_factor - 1) * 100, 1),
        'probability_per_year': round(prob_one_per_year * 100, 1),
        'probability_major_in_period': round(prob_major_in_decade * 100, 1),
        'expected_storms_total': round(projected_frequency * years_ahead, 1)
    }
