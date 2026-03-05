"""
Predictive Models for Population & Colony Viability
====================================================

Provides population projections and colony persistence forecasting.
"""

import numpy as np
from typing import Dict, List, Tuple


def project_population(
    historical_counts: List[int],
    years_forward: int = 10,
    model: str = "linear"
) -> Dict:
    """
    Project future population based on historical trend.

    Args:
        historical_counts: List of annual bird counts
        years_forward: Number of years to project
        model: "linear" or "exponential"

    Returns:
        {
            "projected_counts": List[float],
            "confidence_interval": List[Tuple[float, float]],
            "trend": str (increasing/stable/declining),
            "extinction_risk_2050": float (0-1)
        }
    """
    if not historical_counts or len(historical_counts) < 3:
        return {
            "projected_counts": [],
            "confidence_interval": [],
            "trend": "UNKNOWN",
            "extinction_risk_2050": 0.5,
        }

    counts = np.array(historical_counts, dtype=float)
    years_hist = np.arange(len(counts))
    years_future = np.arange(len(counts), len(counts) + years_forward)

    if model == "exponential" and np.all(counts > 0):
        # Exponential model: N(t) = N0 * exp(r*t)
        log_counts = np.log(counts)
        slope, intercept = np.polyfit(years_hist, log_counts, 1)

        # Project
        log_projected = slope * years_future + intercept
        projected = np.exp(log_projected)

        # Estimate confidence interval (±1 std dev)
        residuals = log_counts - (slope * years_hist + intercept)
        std_dev = np.std(residuals)
        ci_lower = np.exp(log_projected - std_dev)
        ci_upper = np.exp(log_projected + std_dev)
    else:
        # Linear model: N(t) = a*t + b
        slope, intercept = np.polyfit(years_hist, counts, 1)
        projected = slope * years_future + intercept

        # Ensure non-negative projections
        projected = np.maximum(projected, 0)

        # Confidence interval
        residuals = counts - (slope * years_hist + intercept)
        std_dev = np.std(residuals)
        ci_lower = np.maximum(projected - 1.5 * std_dev, 0)
        ci_upper = projected + 1.5 * std_dev

    # Determine trend
    if slope > 0.05 * np.mean(counts):
        trend = "INCREASING"
    elif slope < -0.05 * np.mean(counts):
        trend = "DECLINING"
    else:
        trend = "STABLE"

    # Estimate extinction risk by 2050 (30 years out)
    # Based on projected population and trend stability
    if years_forward >= 30:
        final_projection = projected[-1] if len(projected) > 20 else projected[-1]
    else:
        # Extrapolate
        final_projection = projected[-1] + slope * (30 - years_forward)

    avg_historical = np.mean(counts)
    if avg_historical > 0:
        decline_ratio = max(0, (avg_historical - final_projection) / avg_historical)
    else:
        decline_ratio = 0.5

    extinction_risk = np.clip(decline_ratio, 0.0, 0.95)

    return {
        "projected_counts": projected.tolist(),
        "confidence_interval": list(zip(ci_lower.tolist(), ci_upper.tolist())),
        "trend": trend,
        "extinction_risk_2050": round(extinction_risk, 3),
    }


def assess_colony_viability(
    colony_id: str,
    erosion_rate_m_per_year: float,
    current_area_m2: float = 50000,
    minimum_viable_area_m2: float = 5000,
) -> Dict:
    """
    Assess how long a colony will remain viable given erosion rate.

    Args:
        colony_id: Colony identifier
        erosion_rate_m_per_year: Shoreline retreat rate
        current_area_m2: Current colony land area
        minimum_viable_area_m2: Minimum area for nesting success

    Returns:
        {
            "colony_id": str,
            "years_until_critical": int,
            "viability_2050": str (viable/marginal/lost),
            "recommendation": str
        }
    """
    # Simplified model: assume uniform erosion
    # In reality, islands fragment in complex ways

    # Estimate perimeter (assume circular island)
    perimeter = 2 * np.sqrt(np.pi * current_area_m2)

    # Annual area loss
    area_loss_per_year = erosion_rate_m_per_year * perimeter

    # Years until minimum viable area
    area_loss_total = current_area_m2 - minimum_viable_area_m2
    if area_loss_per_year > 0:
        years_until_critical = int(area_loss_total / area_loss_per_year)
    else:
        years_until_critical = 999  # Effectively stable

    # 2050 status (27 years from 2023)
    area_2050 = current_area_m2 - (area_loss_per_year * 27)

    if area_2050 > minimum_viable_area_m2 * 2:
        viability_2050 = "VIABLE"
        recommendation = "Monitor regularly. Continue routine restoration maintenance."
    elif area_2050 > minimum_viable_area_m2:
        viability_2050 = "MARGINAL"
        recommendation = "Proactive restoration needed. Consider sediment nourishment or breakwater installation."
    else:
        viability_2050 = "LOST"
        recommendation = "Critical intervention required. Evaluate feasibility of major restoration vs. population relocation."

    return {
        "colony_id": colony_id,
        "years_until_critical": years_until_critical,
        "viability_2050": viability_2050,
        "area_remaining_2050_m2": int(max(0, area_2050)),
        "recommendation": recommendation,
    }


def correlate_with_environmental_events(
    population_data: List[Tuple[int, int]],  # [(year, count), ...]
    storm_years: List[int],
) -> Dict:
    """
    Analyze correlation between population changes and major storm events.

    Returns:
        {
            "storm_impact_detected": bool,
            "avg_decline_post_storm_pct": float,
            "recovery_time_years": int,
            "resilience_score": float (0-1)
        }
    """
    if not population_data or len(population_data) < 5:
        return {
            "storm_impact_detected": False,
            "avg_decline_post_storm_pct": 0.0,
            "recovery_time_years": 0,
            "resilience_score": 0.5,
        }

    # Sort by year
    population_data = sorted(population_data, key=lambda x: x[0])
    years = [y for y, _ in population_data]
    counts = np.array([c for _, c in population_data], dtype=float)

    # Identify post-storm declines
    declines = []
    recovery_times = []

    for storm_year in storm_years:
        if storm_year not in years:
            continue

        idx = years.index(storm_year)

        # Look at next year if available
        if idx + 1 < len(counts):
            pre_storm = counts[idx]
            post_storm = counts[idx + 1]

            if pre_storm > 0:
                decline_pct = ((pre_storm - post_storm) / pre_storm) * 100
                if decline_pct > 0:
                    declines.append(decline_pct)

                    # Estimate recovery time
                    for i in range(idx + 2, len(counts)):
                        if counts[i] >= pre_storm * 0.9:  # 90% recovery
                            recovery_times.append(years[i] - storm_year)
                            break

    if declines:
        avg_decline = np.mean(declines)
        storm_impact = avg_decline > 10.0  # >10% decline = significant

        if recovery_times:
            avg_recovery = np.mean(recovery_times)
        else:
            avg_recovery = 99  # Not yet recovered

        # Resilience = inverse of decline + speed of recovery
        resilience = 1.0 - np.clip(avg_decline / 100.0 + (avg_recovery / 20.0), 0.0, 1.0)
    else:
        avg_decline = 0.0
        storm_impact = False
        avg_recovery = 0
        resilience = 0.8  # Assume resilient if no major impacts detected

    return {
        "storm_impact_detected": storm_impact,
        "avg_decline_post_storm_pct": round(avg_decline, 1),
        "recovery_time_years": int(avg_recovery) if avg_recovery < 99 else None,
        "resilience_score": round(resilience, 3),
    }
