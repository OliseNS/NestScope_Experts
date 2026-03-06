"""
Extrapolate bird population data from 2021 to 2026
Uses historical trend to project current estimates
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def extrapolate_to_current_year(db_path: str, current_year: int = 2026):
    """
    Add extrapolated current year estimates to colony risk assessment

    Uses 2010-2021 trend to project forward to current year
    """
    logger.info(f"Extrapolating bird populations to {current_year}...")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Add new columns for current year estimates
    try:
        cursor.execute("""
            ALTER TABLE colony_risk_assessment
            ADD COLUMN estimated_2026_birds INTEGER
        """)
        logger.info("Added estimated_2026_birds column")
    except sqlite3.OperationalError:
        logger.info("Column already exists, updating values...")

    try:
        cursor.execute("""
            ALTER TABLE colony_risk_assessment
            ADD COLUMN last_survey_year INTEGER DEFAULT 2021
        """)
        logger.info("Added last_survey_year column")
    except sqlite3.OperationalError:
        pass

    # Get all colonies with population trends
    cursor.execute("""
        SELECT
            colony_name,
            current_bird_count,
            population_trend_2010_2021_pct
        FROM colony_risk_assessment
        WHERE current_bird_count > 0
    """)

    updated = 0
    for row in cursor.fetchall():
        colony_name, birds_2021, trend_pct = row

        if trend_pct is None or trend_pct == 100.0:  # New colony or no trend data
            # Use 2021 value as estimate (assume stable)
            estimated_2026 = birds_2021
        else:
            # Apply trend for 5 more years (2021 → 2026)
            # Annual rate = (trend_pct / 11 years) because 2010-2021 is 11 years
            annual_rate = trend_pct / 11.0
            years_forward = current_year - 2021  # 5 years

            # Compound the trend
            total_change = annual_rate * years_forward
            estimated_2026 = int(birds_2021 * (1 + total_change / 100))
            estimated_2026 = max(0, estimated_2026)  # Can't be negative

        cursor.execute("""
            UPDATE colony_risk_assessment
            SET estimated_2026_birds = ?,
                last_survey_year = 2021
            WHERE colony_name = ?
        """, (estimated_2026, colony_name))

        updated += 1

    conn.commit()

    # Update years_until_critical to count from 2026 not 2025
    cursor.execute("""
        UPDATE colony_risk_assessment
        SET years_until_critical = years_until_critical - 1
        WHERE years_until_critical IS NOT NULL AND years_until_critical > 0
    """)

    logger.info(f"Updated {updated} colonies with 2026 estimates")
    logger.info("Adjusted years_until_critical to count from 2026")

    # Show some examples
    cursor.execute("""
        SELECT
            colony_name,
            current_bird_count as birds_2021,
            estimated_2026_birds,
            population_trend_2010_2021_pct as trend_pct,
            years_until_critical
        FROM colony_risk_assessment
        WHERE risk_level = 'CRITICAL'
        ORDER BY combined_risk_score DESC
        LIMIT 5
    """)

    logger.info("\nExample extrapolations (Top 5 Critical):")
    logger.info("Colony | 2021 Count | 2026 Estimate | Trend | Years Until Critical")
    logger.info("-" * 80)
    for row in cursor.fetchall():
        logger.info(f"{row[0][:30]:30} | {row[1]:10,} | {row[2]:13,} | {row[3]:5.1f}% | {row[4]}")

    conn.close()
    logger.info("\nExtrapolation complete!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Extrapolate to current year")
    parser.add_argument("--db", default="data/bird_data_complete.db", help="Database path")
    parser.add_argument("--year", type=int, default=2026, help="Current year")

    args = parser.parse_args()

    extrapolate_to_current_year(args.db, args.year)
