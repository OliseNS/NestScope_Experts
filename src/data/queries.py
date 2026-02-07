"""
Query functions for bird survey data analysis.

This module contains all the query functions that can be called by the LLM:
- species_trend(): Get population trends for a species over time
- top_species(): Get top N species by count for a given year/region
- compare_regions(): Compare species counts across different parishes
- colony_details(): Get detailed information about a specific colony
- temporal_comparison(): Compare populations before/after an event

Person 1 (Data Engineer) implementation
"""

import duckdb
import pandas as pd
from typing import Optional, List


def species_trend(
    species: str,
    start_year: int,
    end_year: int,
    db_path: str = "data/processed/bird_survey.duckdb"
) -> pd.DataFrame:
    """
    Get population trend for a species over a time range.

    Args:
        species: Species name (e.g., "Brown Pelican")
        start_year: Start year for analysis
        end_year: End year for analysis
        db_path: Path to DuckDB database

    Returns:
        DataFrame with columns: year, count, location
    """
    # TODO: Implement species trend query
    pass


def top_species(
    n: int = 5,
    year: Optional[int] = None,
    region: Optional[str] = None,
    db_path: str = "data/processed/bird_survey.duckdb"
) -> pd.DataFrame:
    """
    Get top N species by observation count.

    Args:
        n: Number of top species to return
        year: Optional year filter
        region: Optional region/parish filter
        db_path: Path to DuckDB database

    Returns:
        DataFrame with columns: species, count, rank
    """
    # TODO: Implement top species query
    pass


def compare_regions(
    regions: List[str],
    species: Optional[str] = None,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
    db_path: str = "data/processed/bird_survey.duckdb"
) -> pd.DataFrame:
    """
    Compare bird populations across different regions/parishes.

    Args:
        regions: List of region/parish names to compare
        species: Optional species filter
        start_year: Optional start year
        end_year: Optional end year
        db_path: Path to DuckDB database

    Returns:
        DataFrame with columns: region, species, year, count
    """
    # TODO: Implement region comparison query
    pass


def colony_details(
    colony_name: str,
    db_path: str = "data/processed/bird_survey.duckdb"
) -> pd.DataFrame:
    """
    Get detailed information about a specific bird colony.

    Args:
        colony_name: Name of the colony
        db_path: Path to DuckDB database

    Returns:
        DataFrame with colony details over time
    """
    # TODO: Implement colony details query
    pass


def temporal_comparison(
    event_date: str,
    species: Optional[str] = None,
    region: Optional[str] = None,
    before_window: int = 365,
    after_window: int = 365,
    db_path: str = "data/processed/bird_survey.duckdb"
) -> pd.DataFrame:
    """
    Compare populations before and after an event (e.g., hurricane).

    Args:
        event_date: Date of the event (YYYY-MM-DD)
        species: Optional species filter
        region: Optional region filter
        before_window: Days before event to include
        after_window: Days after event to include
        db_path: Path to DuckDB database

    Returns:
        DataFrame with before/after comparison
    """
    # TODO: Implement temporal comparison query
    pass
