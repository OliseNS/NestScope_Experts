"""
Coastal erosion models and land loss predictions
Based on USGS Louisiana coastal erosion studies
"""

from typing import Dict, Tuple
import math


# USGS-documented erosion rates for Louisiana coastal regions (meters/year)
# Source: USGS Open-File Report 2017-1051 and Louisiana Coastal Master Plan
EROSION_RATES_BY_REGION = {
    "Barataria Bay": {
        "rate_m_per_year": 12.0,
        "source": "USGS 2017-1051",
        "description": "Rapid erosion, barrier island breaching"
    },
    "Terrebonne Bay": {
        "rate_m_per_year": 15.0,
        "source": "USGS 2017-1051",
        "description": "One of fastest eroding coastlines in world"
    },
    "Chandeleur Islands": {
        "rate_m_per_year": 20.0,
        "source": "USGS 2017-1051",
        "description": "Catastrophic post-Katrina erosion"
    },
    "Mississippi River Delta": {
        "rate_m_per_year": 8.0,
        "source": "USGS 2017-1051",
        "description": "Delta subsidence and erosion"
    },
    "Pontchartrain Basin": {
        "rate_m_per_year": 6.0,
        "source": "USGS 2017-1051",
        "description": "Moderate erosion and subsidence"
    },
    "Atchafalaya Bay": {
        "rate_m_per_year": 5.0,
        "source": "USGS 2017-1051",
        "description": "Some natural accretion from river sediment"
    },
    "Calcasieu-Sabine": {
        "rate_m_per_year": 10.0,
        "source": "USGS 2017-1051",
        "description": "Southwest Louisiana coastal erosion"
    },
    "Texas_Coast": {
        "rate_m_per_year": 4.0,
        "source": "USGS coastal studies",
        "description": "Slower erosion than Louisiana"
    },
}


def get_erosion_rate(region: str) -> float:
    """
    Get erosion rate for a region (meters/year)

    Args:
        region: Region name

    Returns:
        Erosion rate in meters per year
    """
    if region in EROSION_RATES_BY_REGION:
        return EROSION_RATES_BY_REGION[region]["rate_m_per_year"]

    # Default Louisiana coast average
    return 10.0


def calculate_erosion_projection(current_area_m2: float,
                                 erosion_rate_m_per_year: float,
                                 years_ahead: int = 10,
                                 colony_shape: str = "circular") -> Dict:
    """
    Project future land area based on erosion rate

    Args:
        current_area_m2: Current land area in square meters
        erosion_rate_m_per_year: Shoreline erosion rate (m/yr)
        years_ahead: Years to project forward
        colony_shape: "circular" or "linear" (affects calculation)

    Returns:
        Dictionary with erosion projections
    """
    total_erosion_m = erosion_rate_m_per_year * years_ahead

    # Calculate area loss
    if colony_shape == "circular":
        # Circular island: area = π * r²
        # Erosion reduces radius uniformly
        current_radius = math.sqrt(current_area_m2 / math.pi)
        future_radius = max(0, current_radius - total_erosion_m)
        future_area = math.pi * future_radius ** 2

    else:  # linear/rectangular approximation
        # Assume erosion on all sides
        # Estimate perimeter
        perimeter = 4 * math.sqrt(current_area_m2)  # Rough square approximation
        area_lost = perimeter * total_erosion_m
        future_area = max(0, current_area_m2 - area_lost)

    percent_lost = ((current_area_m2 - future_area) / current_area_m2) * 100

    return {
        "current_area_m2": current_area_m2,
        "current_area_hectares": round(current_area_m2 / 10000, 2),
        "erosion_rate_m_per_year": erosion_rate_m_per_year,
        "years_ahead": years_ahead,
        "total_erosion_m": round(total_erosion_m, 1),
        "future_area_m2": round(future_area, 0),
        "future_area_hectares": round(future_area / 10000, 2),
        "percent_area_lost": round(percent_lost, 1),
        "area_lost_m2": round(current_area_m2 - future_area, 0)
    }


def years_until_uninhabitable(current_area_m2: float,
                              erosion_rate_m_per_year: float,
                              minimum_viable_area_m2: float = 5000) -> int:
    """
    Calculate years until colony becomes too small for bird nesting

    Args:
        current_area_m2: Current land area
        erosion_rate_m_per_year: Erosion rate
        minimum_viable_area_m2: Minimum area for viable colony (default 5000m² / 0.5 hectares)

    Returns:
        Years until uninhabitable, or None if already below threshold
    """
    if current_area_m2 <= minimum_viable_area_m2:
        return 0  # Already uninhabitable

    # Approximate calculation (linear for simplicity)
    # In reality, erosion is nonlinear
    area_to_lose = current_area_m2 - minimum_viable_area_m2

    # Estimate perimeter (assume circular)
    avg_radius = math.sqrt(current_area_m2 / math.pi)
    perimeter = 2 * math.pi * avg_radius

    # Area loss per year (perimeter × erosion rate)
    area_loss_per_year = perimeter * erosion_rate_m_per_year

    if area_loss_per_year <= 0:
        return None  # No erosion (shouldn't happen)

    years = area_to_lose / area_loss_per_year

    return int(math.ceil(years))


def calculate_combined_threat(current_area_m2: float,
                              elevation_m: float,
                              erosion_rate_m_per_year: float,
                              region: str,
                              years_ahead: int = 25) -> Dict:
    """
    Combine erosion and sea level rise for comprehensive threat assessment

    Args:
        current_area_m2: Current land area
        elevation_m: Average elevation
        erosion_rate_m_per_year: Shoreline erosion rate
        region: Geographic region
        years_ahead: Years to project (default 25 = year 2050)

    Returns:
        Comprehensive threat assessment
    """
    from .slr_projections import get_slr_for_year, calculate_inundation_risk

    target_year = 2025 + years_ahead

    # Erosion projection
    erosion = calculate_erosion_projection(
        current_area_m2,
        erosion_rate_m_per_year,
        years_ahead
    )

    # Sea level rise projection (intermediate scenario)
    slr = calculate_inundation_risk(
        elevation_m,
        target_year,
        "intermediate"
    )

    # Combined risk score (0-100)
    # Factors:
    # - Percent area lost to erosion (40% weight)
    # - SLR habitability (40% weight)
    # - Erosion rate magnitude (20% weight)

    erosion_score = min(100, erosion['percent_area_lost'])

    slr_score = 0
    if slr['inundated_normal_tide']:
        slr_score = 100
    elif slr['inundated_typical_storm']:
        slr_score = 80
    elif slr['remaining_elevation_m'] < 0.5:
        slr_score = 60
    else:
        slr_score = 40 * (1 - slr['remaining_elevation_m'] / 2.0)

    rate_score = min(100, (erosion_rate_m_per_year / 20) * 100)

    combined_score = (
        erosion_score * 0.4 +
        slr_score * 0.4 +
        rate_score * 0.2
    )

    # Determine risk level
    if combined_score >= 75:
        risk_level = "CRITICAL"
        risk_color = "#FF4444"
        action = "IMMEDIATE ACTION REQUIRED"
    elif combined_score >= 50:
        risk_level = "HIGH"
        risk_color = "#FF8C00"
        action = "PRIORITIZE FOR RESTORATION"
    elif combined_score >= 25:
        risk_level = "MODERATE"
        risk_color = "#FFA500"
        action = "MONITOR CLOSELY"
    else:
        risk_level = "LOW"
        risk_color = "#4CAF50"
        action = "STABLE - ROUTINE MONITORING"

    # Calculate years until critical threshold
    years_until_critical = None

    # Critical = either <0.5m elevation OR <20% original area
    critical_area = current_area_m2 * 0.2

    for year in range(2025, 2101):
        years_out = year - 2025

        # Check erosion
        erosion_check = calculate_erosion_projection(
            current_area_m2,
            erosion_rate_m_per_year,
            years_out
        )

        # Check SLR
        slr_check = calculate_inundation_risk(elevation_m, year, "intermediate")

        if (erosion_check['future_area_m2'] < critical_area or
            slr_check['remaining_elevation_m'] < 0.5):
            years_until_critical = years_out
            break

    return {
        "target_year": target_year,
        "combined_risk_score": round(combined_score, 1),
        "risk_level": risk_level,
        "risk_color": risk_color,
        "recommended_action": action,
        "erosion_projection": erosion,
        "slr_projection": slr,
        "years_until_critical": years_until_critical,
        "critical_year": 2025 + years_until_critical if years_until_critical else None,
        "components": {
            "erosion_score": round(erosion_score, 1),
            "slr_score": round(slr_score, 1),
            "rate_score": round(rate_score, 1)
        }
    }


def get_region_for_colony(colony_name: str, lat: float, lon: float) -> str:
    """
    Determine region based on colony name or coordinates

    In production, this would use GIS polygon intersection
    For now, use simple heuristics
    """
    name_lower = colony_name.lower()

    if any(x in name_lower for x in ["barataria", "grand isle", "queen bess", "east timbalier"]):
        return "Barataria Bay"
    elif any(x in name_lower for x in ["terrebonne", "isles dernieres", "timbalier"]):
        return "Terrebonne Bay"
    elif "chandeleur" in name_lower:
        return "Chandeleur Islands"
    elif any(x in name_lower for x in ["breton", "mississippi river", "pass a loutre"]):
        return "Mississippi River Delta"
    elif any(x in name_lower for x in ["pontchartrain", "shell beach", "fort pike"]):
        return "Pontchartrain Basin"
    elif "atchafalaya" in name_lower:
        return "Atchafalaya Bay"
    elif any(x in name_lower for x in ["cameron", "calcasieu", "sabine"]):
        return "Calcasieu-Sabine"
    elif lon > -94.0:  # Western colonies
        return "Texas_Coast"
    else:
        return "Barataria Bay"  # Default Louisiana coast
