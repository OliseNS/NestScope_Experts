"""
Erosion Data & Sea Level Rise Integration
==========================================

Provides erosion risk zones and historical shoreline data for Gulf Coast.
Uses publicly available datasets from NOAA, USGS, and Louisiana Coastal Master Plan.
"""

import json
from typing import Dict, List, Optional


# Gulf Coast erosion risk zones (GeoJSON polygons)
# Based on Louisiana Coastal Master Plan 2023 + USGS data
EROSION_RISK_ZONES = {
    "type": "FeatureCollection",
    "features": [
        # Barataria Bay - HIGH RISK
        {
            "type": "Feature",
            "properties": {
                "name": "Barataria Bay",
                "risk_level": "HIGH",
                "risk_score": 0.85,
                "erosion_rate_m_per_year": 12.5,
                "description": "Rapid marsh loss, island fragmentation. Queen Bess Island restoration ongoing.",
                "affected_colonies": ["Queen Bess Island"],
                "sea_level_rise_vulnerability": "EXTREME",
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-90.2, 29.1],
                    [-89.7, 29.1],
                    [-89.7, 29.5],
                    [-90.2, 29.5],
                    [-90.2, 29.1],
                ]]
            }
        },
        # Chandeleur Islands - MEDIUM-HIGH RISK
        {
            "type": "Feature",
            "properties": {
                "name": "Chandeleur Islands",
                "risk_level": "MEDIUM-HIGH",
                "risk_score": 0.65,
                "erosion_rate_m_per_year": 8.3,
                "description": "Barrier island system eroding westward. Hurricane impacts severe.",
                "affected_colonies": ["New Harbor Island 2", "New Harbor Island 3"],
                "sea_level_rise_vulnerability": "HIGH",
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-89.0, 29.5],
                    [-88.7, 29.5],
                    [-88.7, 30.1],
                    [-89.0, 30.1],
                    [-89.0, 29.5],
                ]]
            }
        },
        # Timbalier Islands - EXTREME RISK
        {
            "type": "Feature",
            "properties": {
                "name": "Timbalier Islands",
                "risk_level": "EXTREME",
                "risk_score": 0.95,
                "erosion_rate_m_per_year": 18.7,
                "description": "Catastrophic land loss. Islands disappearing rapidly.",
                "affected_colonies": ["East Timbalier Island"],
                "sea_level_rise_vulnerability": "EXTREME",
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-90.5, 29.0],
                    [-90.1, 29.0],
                    [-90.1, 29.2],
                    [-90.5, 29.2],
                    [-90.5, 29.0],
                ]]
            }
        },
        # Apalachee Bay - LOW RISK
        {
            "type": "Feature",
            "properties": {
                "name": "Apalachee Bay - Florida",
                "risk_level": "LOW",
                "risk_score": 0.25,
                "erosion_rate_m_per_year": 2.1,
                "description": "Relatively stable coastline. Mangrove protection.",
                "affected_colonies": ["Pepperfish Key"],
                "sea_level_rise_vulnerability": "MODERATE",
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-83.6, 29.3],
                    [-83.2, 29.3],
                    [-83.2, 29.7],
                    [-83.6, 29.7],
                    [-83.6, 29.3],
                ]]
            }
        },
        # Mississippi Sound - MEDIUM RISK
        {
            "type": "Feature",
            "properties": {
                "name": "Mississippi Sound",
                "risk_level": "MEDIUM",
                "risk_score": 0.55,
                "erosion_rate_m_per_year": 5.8,
                "description": "Barrier islands migrating. Moderate storm exposure.",
                "affected_colonies": ["Cat Island", "Ship Island"],
                "sea_level_rise_vulnerability": "HIGH",
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-89.5, 30.1],
                    [-88.5, 30.1],
                    [-88.5, 30.4],
                    [-89.5, 30.4],
                    [-89.5, 30.1],
                ]]
            }
        },
    ]
}


# Sea level rise projection scenarios (feet above current levels)
SEA_LEVEL_RISE_SCENARIOS = {
    "2030_intermediate": 0.5,   # 6 inches
    "2050_intermediate": 1.5,   # 18 inches
    "2070_intermediate": 3.0,   # 3 feet
    "2100_high": 6.0,           # 6 feet (NOAA high scenario)
}


# Historical shoreline positions (simplified - in production would load from USGS DSAS outputs)
HISTORICAL_SHORELINES = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {
                "year": 1850,
                "source": "USGS T-Sheets",
                "description": "Pre-industrial shoreline position"
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [-90.3, 29.25],
                    [-90.1, 29.28],
                    [-89.9, 29.30],
                    # ... (simplified, full dataset would have thousands of points)
                ]
            }
        },
        {
            "type": "Feature",
            "properties": {
                "year": 1980,
                "source": "NOAA Coastal Imagery",
                "description": "Post-oil-and-gas development"
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [-90.28, 29.22],
                    [-90.08, 29.25],
                    [-89.88, 29.27],
                ]
            }
        },
        {
            "type": "Feature",
            "properties": {
                "year": 2020,
                "source": "NAIP Orthoimagery",
                "description": "Current shoreline"
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [-90.25, 29.18],
                    [-90.05, 29.21],
                    [-89.85, 29.23],
                ]
            }
        },
    ]
}


# Major storm tracks that impacted bird colonies (2005-2024)
MAJOR_STORM_TRACKS = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {
                "name": "Hurricane Katrina",
                "year": 2005,
                "category": 5,
                "impact": "CATASTROPHIC - Chandeleur Islands destroyed, Queen Bess severely eroded",
                "max_wind_mph": 175,
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [-88.6, 29.3],
                    [-89.6, 29.5],
                    [-90.0, 30.0],
                ]
            }
        },
        {
            "type": "Feature",
            "properties": {
                "name": "Hurricane Rita",
                "year": 2005,
                "category": 5,
                "impact": "SEVERE - Southwest Louisiana coast devastated",
                "max_wind_mph": 180,
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [-92.0, 28.5],
                    [-92.5, 29.0],
                    [-93.0, 29.8],
                ]
            }
        },
        {
            "type": "Feature",
            "properties": {
                "name": "Hurricane Isaac",
                "year": 2012,
                "category": 1,
                "impact": "MODERATE - Prolonged flooding, marsh damage",
                "max_wind_mph": 80,
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [-89.5, 28.8],
                    [-90.0, 29.3],
                    [-90.3, 29.8],
                ]
            }
        },
        {
            "type": "Feature",
            "properties": {
                "name": "Hurricane Ida",
                "year": 2021,
                "category": 4,
                "impact": "SEVERE - Direct hit on Barataria Bay, Queen Bess Island damaged",
                "max_wind_mph": 150,
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [-89.8, 28.9],
                    [-90.1, 29.2],
                    [-90.5, 29.7],
                ]
            }
        },
    ]
}


def get_erosion_risk_zones() -> Dict:
    """
    Return GeoJSON FeatureCollection of erosion risk zones.
    """
    return EROSION_RISK_ZONES


def get_shoreline_history() -> Dict:
    """
    Return GeoJSON FeatureCollection of historical shoreline positions.
    """
    return HISTORICAL_SHORELINES


def get_sea_level_rise_projections(scenario: str = "2050_intermediate") -> Dict:
    """
    Return sea level rise projection polygons for a given scenario.

    Args:
        scenario: One of 2030_intermediate, 2050_intermediate, 2070_intermediate, 2100_high

    Returns:
        GeoJSON FeatureCollection of inundation zones
    """
    rise_feet = SEA_LEVEL_RISE_SCENARIOS.get(scenario, 1.5)

    # For demo purposes, return simplified inundation zones
    # In production, would integrate with NOAA Sea Level Rise Viewer API
    return {
        "type": "FeatureCollection",
        "properties": {
            "scenario": scenario,
            "sea_level_rise_feet": rise_feet,
            "description": f"Areas inundated by {rise_feet} ft sea level rise"
        },
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "risk_level": "INUNDATED",
                    "elevation_ft": 0.0 if rise_feet > 3 else 1.0,
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-90.2, 29.1],
                        [-89.7, 29.1],
                        [-89.7, 29.3],
                        [-90.2, 29.3],
                        [-90.2, 29.1],
                    ]]
                }
            }
        ]
    }


def get_storm_tracks(years: Optional[List[int]] = None) -> Dict:
    """
    Return GeoJSON FeatureCollection of major storm tracks.

    Args:
        years: List of years to filter (None = all storms)
    """
    if years is None:
        return MAJOR_STORM_TRACKS

    filtered_features = [
        f for f in MAJOR_STORM_TRACKS["features"]
        if f["properties"]["year"] in years
    ]

    return {
        "type": "FeatureCollection",
        "features": filtered_features
    }


def get_colony_erosion_risk(colony_id: str) -> Dict:
    """
    Get erosion risk details for a specific colony.

    Returns:
        {
            "colony_id": str,
            "risk_score": float (0-1),
            "risk_level": str,
            "erosion_rate_m_per_year": float,
            "recommendation": str
        }
    """
    from .species_risk import COLONY_EROSION_RISK

    risk_score = COLONY_EROSION_RISK.get(colony_id, 0.5)

    if risk_score >= 0.9:
        level = "EXTREME"
        recommendation = "Critical intervention needed. Consider island restoration or population relocation."
    elif risk_score >= 0.7:
        level = "HIGH"
        recommendation = "High priority for restoration. Monitor closely for rapid changes."
    elif risk_score >= 0.5:
        level = "MEDIUM"
        recommendation = "Proactive management recommended. Regular monitoring essential."
    else:
        level = "LOW"
        recommendation = "Continue routine monitoring. Focus resources on higher-risk sites."

    return {
        "colony_id": colony_id,
        "risk_score": risk_score,
        "risk_level": level,
        "erosion_rate_m_per_year": risk_score * 20.0,  # Approximate scaling
        "recommendation": recommendation,
    }
