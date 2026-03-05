"""
Restoration Priority & ROI Calculator
======================================

Calculates restoration priorities based on:
- Species diversity
- Population size
- Species risk levels
- Site viability (erosion resistance)
- Connectivity to other colonies
"""

import numpy as np
from typing import Dict, List
import sqlite3


def calculate_restoration_priorities(
    db_path: str,
    species_risk_data: Dict,
    erosion_data: Dict,
) -> Dict:
    """
    Calculate restoration priority scores for all colonies.

    Returns:
        {
            "priority_map": GeoJSON FeatureCollection with priority scores,
            "top_recommendations": List[Dict],
            "methodology": Dict
        }
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get all colonies with coordinates
        query = """
        SELECT DISTINCT
            ColonyName,
            Latitude,
            Longitude
        FROM [tblColonyTotals2010-2021_MayJuneCombined]
        WHERE Latitude IS NOT NULL
          AND Longitude IS NOT NULL
          AND BirdsTotal > 0
        """

        cursor.execute(query)
        colonies = cursor.fetchall()

        priority_features = []
        recommendations = []

        for colony_name, lat, lon in colonies:
            # Calculate priority components
            diversity_score = _calculate_diversity_score(cursor, colony_name)
            population_score = _calculate_population_score(cursor, colony_name)
            risk_score = _calculate_colony_risk_score(cursor, colony_name, species_risk_data)
            viability_score = _calculate_viability_score(colony_name, erosion_data)
            connectivity_score = _calculate_connectivity_score(lat, lon, colonies)

            # Weighted overall priority
            priority = (
                diversity_score * 0.30 +
                population_score * 0.25 +
                risk_score * 0.25 +
                viability_score * 0.15 +
                connectivity_score * 0.05
            )

            # Priority level
            if priority >= 0.75:
                level = "CRITICAL"
                color = "#D97757"
            elif priority >= 0.60:
                level = "HIGH"
                color = "#F0A030"
            elif priority >= 0.40:
                level = "MEDIUM"
                color = "#F0F090"
            else:
                level = "LOW"
                color = "#90C090"

            # GeoJSON feature
            feature = {
                "type": "Feature",
                "properties": {
                    "colony_name": colony_name,
                    "priority_score": round(priority, 3),
                    "priority_level": level,
                    "diversity_score": round(diversity_score, 3),
                    "population_score": round(population_score, 3),
                    "risk_score": round(risk_score, 3),
                    "viability_score": round(viability_score, 3),
                    "connectivity_score": round(connectivity_score, 3),
                    "color": color,
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [lon, lat]
                }
            }
            priority_features.append(feature)

            # Top recommendations (priority >= 0.60)
            if priority >= 0.60:
                recommendations.append({
                    "rank": len([f for f in priority_features if f["properties"]["priority_score"] > priority]) + 1,
                    "colony_name": colony_name,
                    "priority_score": round(priority, 3),
                    "justification": _generate_justification(
                        colony_name, diversity_score, population_score,
                        risk_score, viability_score
                    ),
                    "estimated_cost_usd": _estimate_restoration_cost(viability_score),
                    "estimated_birds_benefited": _estimate_birds_benefited(
                        cursor, colony_name, viability_score
                    ),
                })

        conn.close()

        # Sort recommendations by priority
        recommendations.sort(key=lambda x: -x["priority_score"])

        return {
            "priority_map": {
                "type": "FeatureCollection",
                "features": priority_features
            },
            "top_recommendations": recommendations[:10],
            "methodology": {
                "weights": {
                    "species_diversity": 0.30,
                    "population_size": 0.25,
                    "species_risk": 0.25,
                    "site_viability": 0.15,
                    "connectivity": 0.05
                },
                "description": "Priority scores range 0-1. Higher scores indicate sites where restoration will have maximum conservation impact."
            }
        }

    except Exception as e:
        print(f"[ROI] Error calculating restoration priorities: {e}")
        return {
            "priority_map": {"type": "FeatureCollection", "features": []},
            "top_recommendations": [],
            "methodology": {}
        }


def _calculate_diversity_score(cursor, colony_name: str) -> float:
    """
    Score based on number of species using the colony.
    More species = higher conservation value.
    """
    query = """
    SELECT COUNT(DISTINCT SpeciesCode) as species_count
    FROM [tblColonyTotals2010-2021_MayJuneCombined]
    WHERE ColonyName = ? AND BirdsTotal > 0
    """
    cursor.execute(query, (colony_name,))
    species_count = cursor.fetchone()[0] or 1

    # Normalize to 0-1 (assume 15 species = maximum diversity)
    return min(1.0, species_count / 15.0)


def _calculate_population_score(cursor, colony_name: str) -> float:
    """
    Score based on total bird population.
    Larger colonies = higher value (but with diminishing returns).
    """
    query = """
    SELECT MAX(BirdsTotal) as max_birds
    FROM [tblColonyTotals2010-2021_MayJuneCombined]
    WHERE ColonyName = ?
    """
    cursor.execute(query, (colony_name,))
    max_birds = cursor.fetchone()[0] or 0

    # Log scale to avoid overweighting huge colonies
    if max_birds > 0:
        score = np.log10(max_birds + 1) / 5.0  # Log10(100000) = 5
        return min(1.0, score)
    return 0.0


def _calculate_colony_risk_score(cursor, colony_name: str, species_risk_data: Dict) -> float:
    """
    Score based on presence of at-risk species.
    More at-risk species = higher restoration priority.
    """
    # Get species present at colony
    query = """
    SELECT DISTINCT SpeciesCode
    FROM [tblColonyTotals2010-2021_MayJuneCombined]
    WHERE ColonyName = ? AND BirdsTotal > 0
    """
    cursor.execute(query, (colony_name,))
    species_codes = [row[0] for row in cursor.fetchall()]

    if not species_codes:
        return 0.0

    # Get risk scores for these species
    risk_scores = []
    for sp_code in species_codes:
        for assessment in species_risk_data.get("species_assessments", []):
            if assessment["species_code"] == sp_code:
                risk_scores.append(assessment["risk_score"])
                break

    if risk_scores:
        # Average risk of species present
        return np.mean(risk_scores)
    return 0.5


def _calculate_viability_score(colony_name: str, erosion_data: Dict) -> float:
    """
    Score based on erosion resistance.
    Low erosion = higher viability = better restoration investment.
    """
    from .species_risk import COLONY_EROSION_RISK

    # Get erosion risk (0-1, higher = more erosion)
    erosion_risk = COLONY_EROSION_RISK.get(colony_name, 0.5)

    # Invert so low erosion = high viability
    viability = 1.0 - erosion_risk

    return viability


def _calculate_connectivity_score(lat: float, lon: float, all_colonies: List) -> float:
    """
    Score based on proximity to other colonies.
    Near other colonies = higher connectivity = spillover potential.
    """
    # Count colonies within 50km
    nearby_count = 0
    for other_colony, other_lat, other_lon in all_colonies:
        if other_lat == lat and other_lon == lon:
            continue  # Skip self

        # Rough distance in degrees (~111km per degree latitude)
        dist_deg = np.sqrt((lat - other_lat)**2 + (lon - other_lon)**2)
        dist_km = dist_deg * 111.0

        if dist_km < 50:
            nearby_count += 1

    # Normalize (5+ nearby = maximum connectivity)
    return min(1.0, nearby_count / 5.0)


def _generate_justification(
    colony_name: str,
    diversity: float,
    population: float,
    risk: float,
    viability: float
) -> str:
    """
    Generate human-readable justification for restoration priority.
    """
    reasons = []

    if diversity > 0.6:
        reasons.append(f"High species diversity ({int(diversity * 15)} species)")
    if population > 0.7:
        reasons.append("Large bird population (>10,000 birds)")
    if risk > 0.6:
        reasons.append("Hosts at-risk species requiring protection")
    if viability > 0.7:
        reasons.append("Site has high long-term viability (low erosion)")
    if viability < 0.3:
        reasons.append("Urgent intervention needed due to erosion")

    if not reasons:
        return "Moderate conservation value. Continue monitoring."

    return ". ".join(reasons) + "."


def _estimate_restoration_cost(viability_score: float) -> int:
    """
    Estimate restoration cost based on site conditions.

    Low viability (high erosion) = more expensive restoration.
    """
    # Base cost: $500K
    # High erosion sites: up to $5M for major interventions
    base_cost = 500_000

    if viability_score < 0.3:
        # Extreme erosion: major island rebuilding
        return int(base_cost * 10)
    elif viability_score < 0.5:
        # High erosion: significant nourishment
        return int(base_cost * 5)
    elif viability_score < 0.7:
        # Moderate erosion: targeted restoration
        return int(base_cost * 2)
    else:
        # Low erosion: maintenance and enhancement
        return base_cost


def _estimate_birds_benefited(cursor, colony_name: str, viability_score: float) -> int:
    """
    Estimate number of birds that would benefit from restoration.

    Assumptions:
    - Restoration restores habitat to 80% of historical capacity
    - Effective for 20 years
    """
    query = """
    SELECT MAX(BirdsTotal) as max_birds
    FROM [tblColonyTotals2010-2021_MayJuneCombined]
    WHERE ColonyName = ?
    """
    cursor.execute(query, (colony_name,))
    current_max = cursor.fetchone()[0] or 0

    # Assume restoration could increase capacity by 50% in viable sites
    # or prevent 80% loss in eroding sites
    if viability_score < 0.4:
        # Eroding site: restoration prevents loss
        birds_saved = int(current_max * 0.8)
    else:
        # Stable site: restoration increases capacity
        birds_saved = int(current_max * 0.5)

    # Cumulative over 20 years
    return birds_saved * 20
