"""
Sea Level Rise (SLR) projections and coastal inundation models
Based on NOAA SLR scenarios and IPCC projections
"""

from typing import Dict, List, Tuple
import math


# NOAA Sea Level Rise Scenarios (meters above current sea level)
# Source: https://oceanservice.noaa.gov/hazards/sealevelrise/sealevelrise-tech-report.html
SLR_SCENARIOS = {
    "2030_low": 0.1,      # 10cm by 2030 (low emissions, ~4 inches)
    "2030_intermediate": 0.15,  # 15cm by 2030 (moderate, ~6 inches)
    "2030_high": 0.2,     # 20cm by 2030 (high emissions, ~8 inches)

    "2050_low": 0.3,      # 30cm by 2050 (low emissions, ~12 inches / 1ft)
    "2050_intermediate": 0.5,  # 50cm by 2050 (moderate, ~20 inches)
    "2050_high": 0.8,     # 80cm by 2050 (high emissions, ~31 inches)

    "2070_low": 0.6,      # 60cm by 2070 (low emissions, ~24 inches / 2ft)
    "2070_intermediate": 1.0,  # 1.0m by 2070 (moderate, ~39 inches)
    "2070_high": 1.5,     # 1.5m by 2070 (high emissions, ~59 inches)

    "2100_low": 1.0,      # 1.0m by 2100 (low emissions, ~39 inches)
    "2100_intermediate": 2.0,  # 2.0m by 2100 (moderate, ~79 inches / 6.5ft)
    "2100_high": 3.0,     # 3.0m by 2100 (high emissions, ~118 inches / 10ft)
}


def get_slr_for_year(year: int, scenario: str = "intermediate") -> float:
    """
    Interpolate sea level rise for any year between 2025 and 2100

    Args:
        year: Target year for projection
        scenario: "low", "intermediate", or "high"

    Returns:
        Sea level rise in meters above current level
    """
    if year <= 2025:
        return 0.0

    # Get scenario key
    if year <= 2030:
        key1, key2 = (2025, 0.0), (2030, SLR_SCENARIOS[f"2030_{scenario}"])
    elif year <= 2050:
        key1 = (2030, SLR_SCENARIOS[f"2030_{scenario}"])
        key2 = (2050, SLR_SCENARIOS[f"2050_{scenario}"])
    elif year <= 2070:
        key1 = (2050, SLR_SCENARIOS[f"2050_{scenario}"])
        key2 = (2070, SLR_SCENARIOS[f"2070_{scenario}"])
    elif year <= 2100:
        key1 = (2070, SLR_SCENARIOS[f"2070_{scenario}"])
        key2 = (2100, SLR_SCENARIOS[f"2100_{scenario}"])
    else:
        return SLR_SCENARIOS[f"2100_{scenario}"]

    # Linear interpolation
    year1, slr1 = key1
    year2, slr2 = key2

    fraction = (year - year1) / (year2 - year1)
    return slr1 + (slr2 - slr1) * fraction


def calculate_inundation_risk(elevation_m: float,
                              year: int = 2050,
                              scenario: str = "intermediate") -> Dict:
    """
    Calculate inundation risk for a location given its elevation

    Args:
        elevation_m: Current elevation above sea level (meters)
        year: Target year for assessment
        scenario: SLR scenario ("low", "intermediate", "high")

    Returns:
        Dictionary with inundation metrics
    """
    slr = get_slr_for_year(year, scenario)

    # Account for storm surge (typical Louisiana coast: 1-3m)
    # During major hurricanes, surge can be 3-6m
    typical_surge = 2.0  # meters
    major_surge = 4.0    # meters

    # Calculate different inundation scenarios
    inundated_normal = elevation_m < slr
    inundated_typical_storm = elevation_m < (slr + typical_surge)
    inundated_major_storm = elevation_m < (slr + major_surge)

    # Remaining elevation after SLR
    remaining_elevation = max(0, elevation_m - slr)

    # Calculate years until submersion (if applicable)
    years_until_submerged = None
    if elevation_m > slr and (year - 2025) > 0:
        # Assume linear SLR rate
        rate = slr / (year - 2025)
        if rate > 0:
            years_until_submerged = int(elevation_m / rate) + 2025

    return {
        "current_elevation_m": round(elevation_m, 2),
        "slr_by_year": round(slr, 2),
        "target_year": year,
        "scenario": scenario,
        "remaining_elevation_m": round(remaining_elevation, 2),
        "inundated_normal_tide": inundated_normal,
        "inundated_typical_storm": inundated_typical_storm,
        "inundated_major_storm": inundated_major_storm,
        "years_until_submerged": years_until_submerged,
        "habitability_status": get_habitability_status(
            remaining_elevation,
            inundated_typical_storm
        )
    }


def get_habitability_status(remaining_elevation: float,
                            inundated_in_storms: bool) -> str:
    """Determine if a site is habitable for bird nesting"""
    if remaining_elevation <= 0:
        return "UNINHABITABLE - Permanently submerged"
    elif inundated_in_storms:
        return "CRITICAL - Floods during storms"
    elif remaining_elevation < 0.5:
        return "VULNERABLE - Less than 0.5m above SLR"
    else:
        return "VIABLE - Sufficient elevation"


def estimate_land_loss_percentage(current_area_m2: float,
                                  average_elevation_m: float,
                                  year: int = 2050,
                                  scenario: str = "intermediate") -> Dict:
    """
    Estimate percentage of land lost to sea level rise

    Simplified model assuming uniform elevation distribution
    Real calculation would use DEM data

    Args:
        current_area_m2: Current land area in square meters
        average_elevation_m: Average elevation of the colony
        year: Target year
        scenario: SLR scenario

    Returns:
        Dictionary with land loss metrics
    """
    slr = get_slr_for_year(year, scenario)

    # Simplified model: assume land has some elevation variance
    # Use normal distribution with std dev = 0.3m
    # This is a rough approximation
    elevation_std = 0.3

    # Calculate approximate percentage submerged
    # Areas below (avg_elev - slr) are submerged
    if average_elevation_m <= slr:
        percent_lost = 100.0
    elif average_elevation_m > slr + 2 * elevation_std:
        percent_lost = 0.0
    else:
        # Linear approximation in the transition zone
        percent_lost = 100 * (1 - (average_elevation_m - slr) / (2 * elevation_std))
        percent_lost = max(0, min(100, percent_lost))

    remaining_area = current_area_m2 * (1 - percent_lost / 100)

    return {
        "current_area_m2": current_area_m2,
        "average_elevation_m": average_elevation_m,
        "slr_meters": round(slr, 2),
        "percent_lost": round(percent_lost, 1),
        "remaining_area_m2": round(remaining_area, 0),
        "year": year,
        "scenario": scenario
    }


def get_all_scenarios_summary(elevation_m: float) -> List[Dict]:
    """
    Get inundation summary for all time periods and scenarios

    Args:
        elevation_m: Current elevation above sea level

    Returns:
        List of scenario dictionaries
    """
    scenarios = []

    for year in [2030, 2050, 2070, 2100]:
        for scenario_name in ["low", "intermediate", "high"]:
            result = calculate_inundation_risk(elevation_m, year, scenario_name)
            result['label'] = f"{year} ({scenario_name.title()})"
            scenarios.append(result)

    return scenarios


# Louisiana coastal colony typical elevations (meters above sea level)
# Source: USGS elevation data for barrier islands
TYPICAL_COLONY_ELEVATIONS = {
    "barrier_island": 1.5,   # Typical Louisiana barrier island elevation
    "cheniere": 2.0,          # Cheniere ridge (slightly higher)
    "marsh_island": 0.5,      # Low marsh island
    "spoil_island": 2.5,      # Dredge spoil island (artificially elevated)
    "beach_ridge": 1.8,       # Natural beach ridge
}


def get_colony_elevation_estimate(colony_type: str = "barrier_island") -> float:
    """
    Get estimated elevation for a colony type

    In production, this would query actual DEM data
    """
    return TYPICAL_COLONY_ELEVATIONS.get(colony_type, 1.5)


def years_until_critical(elevation_m: float,
                        scenario: str = "intermediate") -> int:
    """
    Calculate years until site becomes critically vulnerable

    Critical = flooded during typical storms (2m surge + SLR)

    Returns:
        Years from now (2025) until critical, or None if already critical
    """
    critical_threshold = elevation_m - 2.0  # Needs 2m above for storm survival

    if critical_threshold <= 0:
        return 0  # Already critical

    # Find year when SLR reaches critical threshold
    for year in range(2025, 2101):
        slr = get_slr_for_year(year, scenario)
        if slr >= critical_threshold:
            return year - 2025

    return None  # Won't become critical by 2100
