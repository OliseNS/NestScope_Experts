"""
Species Risk Assessment Engine
===============================

Calculates vulnerability scores for Gulf Coast bird species based on:
- Population trends (2010-2021)
- Habitat vulnerability (erosion exposure)
- Range diversity (number of colonies)
- Conservation status
"""

import numpy as np
from typing import Dict, List, Tuple
import sqlite3


# Risk category thresholds
RISK_THRESHOLDS = {
    "CRITICAL": 0.75,
    "ENDANGERED": 0.50,
    "VULNERABLE": 0.25,
    "STABLE": 0.0,
}

# Conservation status scores
CONSERVATION_STATUS = {
    "BRPE": 0.0,   # Brown Pelican - Recovered (delisted 2009)
    "ROSP": 0.3,   # Roseate Spoonbill - Species of Concern
    "BLSK": 0.5,   # Black Skimmer - Declining
    "SNEG": 0.3,   # Snowy Egret - Stable but habitat-dependent
    "LAGU": 0.0,   # Laughing Gull - Stable
    "ROYT": 0.2,   # Royal Tern - Stable but colonial nester
    # Add more species as needed
}

# Erosion risk by colony (based on Louisiana Coastal Master Plan data)
COLONY_EROSION_RISK = {
    "QueenBessIsland": 0.85,      # HIGH - Barataria Bay rapid erosion
    "NewHarborIsland2": 0.60,      # MEDIUM - Chandeleur Islands erosion
    "NewHarborIsland3": 0.60,      # MEDIUM - Chandeleur Islands erosion
    "PepperfishKey": 0.30,         # LOW - Florida Gulf Coast more stable
    "EastTimbalierIsland": 0.90,   # HIGH - Extreme erosion (devDays data)
    "CatIsland": 0.75,             # HIGH - Mississippi barrier island
    "SpoilIsland": 0.55,           # MEDIUM - Alabama coast
}


def calculate_population_trend(db_path: str, species_code: str) -> Tuple[float, List[int]]:
    """
    Calculate population trend from SQLite database (2010-2021).

    Returns:
        (trend_score, yearly_counts)
        trend_score: -1.0 (steep decline) to +1.0 (steep increase)
        yearly_counts: list of annual totals
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Query colony totals table
        query = """
        SELECT Year, SUM(BirdsTotal) as total_birds
        FROM [tblColonyTotals2010-2021_MayJuneCombined]
        WHERE SpeciesCode = ?
        GROUP BY Year
        ORDER BY Year
        """

        cursor.execute(query, (species_code,))
        results = cursor.fetchall()
        conn.close()

        if not results or len(results) < 3:
            return 0.0, []

        years = np.array([r[0] for r in results])
        counts = np.array([r[1] or 0 for r in results])

        # Linear regression to get trend slope
        if len(counts) > 0 and np.max(counts) > 0:
            # Normalize years to 0-1 range
            years_norm = (years - years.min()) / (years.max() - years.min())

            # Fit linear trend
            slope, intercept = np.polyfit(years_norm, counts, 1)

            # Normalize slope to -1 to +1 range
            # A change of 50% over the period is considered significant
            avg_count = np.mean(counts)
            if avg_count > 0:
                normalized_slope = np.clip(slope / (avg_count * 0.5), -1.0, 1.0)
            else:
                normalized_slope = 0.0

            return normalized_slope, counts.tolist()

        return 0.0, counts.tolist()

    except Exception as e:
        print(f"[RISK] Error calculating population trend for {species_code}: {e}")
        return 0.0, []


def calculate_habitat_vulnerability(db_path: str, species_code: str) -> float:
    """
    Calculate habitat vulnerability score based on colony erosion exposure.

    Returns:
        vulnerability_score: 0.0 (low risk) to 1.0 (high risk)
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get colonies where this species nests
        query = """
        SELECT DISTINCT ColonyName
        FROM [tblColonyTotals2010-2021_MayJuneCombined]
        WHERE SpeciesCode = ? AND BirdsTotal > 0
        """

        cursor.execute(query, (species_code,))
        colonies = [row[0] for row in cursor.fetchall()]
        conn.close()

        if not colonies:
            return 0.5  # Default medium risk if no data

        # Calculate average erosion risk across colonies
        erosion_scores = []
        for colony in colonies:
            # Try to match colony name to known erosion risk
            for risk_colony, risk_score in COLONY_EROSION_RISK.items():
                if risk_colony.lower() in colony.lower() or colony.lower() in risk_colony.lower():
                    erosion_scores.append(risk_score)
                    break
            else:
                # Default medium risk for unknown colonies
                erosion_scores.append(0.5)

        return np.mean(erosion_scores)

    except Exception as e:
        print(f"[RISK] Error calculating habitat vulnerability for {species_code}: {e}")
        return 0.5


def calculate_range_diversity(db_path: str, species_code: str) -> float:
    """
    Calculate range diversity score based on number of colonies occupied.

    Returns:
        diversity_score: 0.0 (single colony) to 1.0 (many colonies)
        Inverted so high diversity = low risk
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Count distinct colonies with this species
        query = """
        SELECT COUNT(DISTINCT ColonyName) as colony_count
        FROM [tblColonyTotals2010-2021_MayJuneCombined]
        WHERE SpeciesCode = ? AND BirdsTotal > 0
        """

        cursor.execute(query, (species_code,))
        colony_count = cursor.fetchone()[0] or 1
        conn.close()

        # More colonies = lower risk (inverted score)
        # Assume 20+ colonies = maximum diversity (score 0.0)
        diversity_risk = max(0.0, 1.0 - (colony_count / 20.0))

        return diversity_risk

    except Exception as e:
        print(f"[RISK] Error calculating range diversity for {species_code}: {e}")
        return 0.5


def calculate_species_risk(db_path: str, species_code: str) -> Dict:
    """
    Calculate comprehensive risk assessment for a species.

    Returns:
        {
            "species_code": str,
            "risk_score": float (0-1),
            "risk_category": str (CRITICAL/ENDANGERED/VULNERABLE/STABLE),
            "population_trend": float (-1 to +1),
            "habitat_vulnerability": float (0-1),
            "range_diversity_risk": float (0-1),
            "conservation_status": float (0-1),
            "population_history": List[int],
            "recommendation": str
        }
    """
    # Calculate component scores
    pop_trend, pop_history = calculate_population_trend(db_path, species_code)
    habitat_vuln = calculate_habitat_vulnerability(db_path, species_code)
    range_risk = calculate_range_diversity(db_path, species_code)
    conservation_score = CONSERVATION_STATUS.get(species_code, 0.2)

    # Weighted overall risk score
    # Convert population trend to risk (declining = high risk)
    pop_risk = (1.0 - pop_trend) / 2.0  # Maps [-1,+1] to [1.0, 0.0]

    overall_risk = (
        pop_risk * 0.40 +
        habitat_vuln * 0.30 +
        range_risk * 0.20 +
        conservation_score * 0.10
    )

    # Determine risk category
    if overall_risk >= RISK_THRESHOLDS["CRITICAL"]:
        category = "CRITICAL"
        recommendation = "Immediate intervention required. Consider captive breeding, habitat restoration, and predator management."
    elif overall_risk >= RISK_THRESHOLDS["ENDANGERED"]:
        category = "ENDANGERED"
        recommendation = "High priority for restoration projects. Increase monitoring frequency and protect existing colonies."
    elif overall_risk >= RISK_THRESHOLDS["VULNERABLE"]:
        category = "VULNERABLE"
        recommendation = "Monitor closely. Implement proactive habitat protection measures in high-erosion areas."
    else:
        category = "STABLE"
        recommendation = "Continue routine monitoring. Maintain current conservation efforts."

    return {
        "species_code": species_code,
        "risk_score": round(overall_risk, 3),
        "risk_category": category,
        "population_trend": round(pop_trend, 3),
        "habitat_vulnerability": round(habitat_vuln, 3),
        "range_diversity_risk": round(range_risk, 3),
        "conservation_status": round(conservation_score, 3),
        "population_history": pop_history,
        "recommendation": recommendation,
    }


def get_species_risk_summary(db_path: str, species_list: List[str] = None) -> Dict:
    """
    Get risk assessment summary for all species.

    Returns:
        {
            "species_assessments": List[Dict],
            "summary_stats": {
                "critical_count": int,
                "endangered_count": int,
                "vulnerable_count": int,
                "stable_count": int
            }
        }
    """
    # Default species list (major Gulf Coast colonial nesters)
    if species_list is None:
        species_list = [
            "BRPE", "ROSP", "BLSK", "SNEG", "LAGU", "ROYT", "SATE",
            "AWPE", "DCCO", "GREG", "WHIB", "TRHE", "GBHE", "BCNH"
        ]

    assessments = []
    stats = {"CRITICAL": 0, "ENDANGERED": 0, "VULNERABLE": 0, "STABLE": 0}

    for species_code in species_list:
        try:
            assessment = calculate_species_risk(db_path, species_code)
            assessments.append(assessment)
            stats[assessment["risk_category"]] += 1
        except Exception as e:
            print(f"[RISK] Error assessing {species_code}: {e}")

    # Sort by risk score (highest first)
    assessments.sort(key=lambda x: -x["risk_score"])

    return {
        "species_assessments": assessments,
        "summary_stats": {
            "critical_count": stats["CRITICAL"],
            "endangered_count": stats["ENDANGERED"],
            "vulnerable_count": stats["VULNERABLE"],
            "stable_count": stats["STABLE"],
        }
    }
