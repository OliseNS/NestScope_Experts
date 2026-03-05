"""
Erosion & Species Risk Assessment Tools
========================================

Provides erosion risk analysis, sea level rise projections,
and species vulnerability assessments for Gulf Coast bird colonies.
"""

from .species_risk import calculate_species_risk, get_species_risk_summary
from .erosion_data import get_erosion_risk_zones, get_shoreline_history
from .predictive_models import project_population, assess_colony_viability
from .restoration_roi import calculate_restoration_priorities

__all__ = [
    "calculate_species_risk",
    "get_species_risk_summary",
    "get_erosion_risk_zones",
    "get_shoreline_history",
    "project_population",
    "assess_colony_viability",
    "calculate_restoration_priorities",
]
