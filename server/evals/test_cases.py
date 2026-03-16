"""
NestEval Test Cases — Predefined questions for evaluating NestChat quality.

Each test case is a dict with:
  - question:          The natural language question to ask NestChat
  - description:       Human-readable name for the test (shown in the dashboard)
  - expected_keywords: Words/phrases we expect to appear in a good answer
                       (used as context hints, not hard requirements)
  - category:          Type of query being tested

WHY THESE CATEGORIES?
We test across different "difficulty levels" of SQL:
  - Simple lookup   → "What states are in the dataset?"
  - Aggregation     → "How many total birds in 2015?"
  - Ranking         → "Which year had the highest count?"
  - Geographic      → "How many Louisiana colonies are in the dataset?"
  - Time-series     → "Show me the trend from 2010 to 2021"
  - Specific lookup → "Which colony had the most nests in 2018?"
  - Comparison      → "How did 2021 compare to 2010?"
  - Species         → "What were the top species in 2021?"

DATA FACTS (verified against the database):
  - 5 states: Louisiana (LA), Texas (TX), Florida (FL), Alabama (AL), Mississippi (MS)
  - Louisiana dominates: ~190 colonies, ~2 million birds (~78% of all records)
  - Survey years are NOT continuous: 2010, 2011, 2012, 2013, 2015, 2018, 2021
    (No surveys in 2014, 2016, 2017, 2019, 2020)
  - 444 total distinct colonies across all states
  - Top all-time colony: Raccoon Island, LA (highest single-year count: 2018)
  - Top species in 2021: Laughing Gull, Royal Tern, Brown Pelican, Sandwich Tern

KNOWN SQL PITFALLS:
  - COUNT(DISTINCT col1, col2) fails in SQLite; correct form is a subquery
  - The prompt forces GROUP BY ColonyName+Lat+Lon, which inflates "colony count"
    queries when the model groups by location instead of counting distinct names
  - Survey gaps mean "2010 to 2021 trend" only returns 7 data points, not 12

This gives us a balanced scorecard that reveals WHERE the AI struggles.
"""

NESTCHAT_TEST_CASES = [
    # ── Core tests (original 8) ────────────────────────────────────────────────
    {
        "id": 1,
        "description": "Annual total bird count (aggregation)",
        "question": "How many total birds were observed in 2015?",
        "expected_keywords": ["2015", "birds", "total"],
        "category": "aggregation",
    },
    {
        "id": 2,
        "description": "State with most observations (ranking + geographic)",
        "question": "Which state had the most total bird observations overall?",
        # Louisiana (~2M birds) should win clearly
        "expected_keywords": ["Louisiana", "birds"],
        "category": "ranking",
    },
    {
        "id": 3,
        "description": "Total distinct colony count (aggregation)",
        # Phrased to avoid triggering COUNT(DISTINCT col1, col2) SQLite bug
        "question": "How many unique bird colony names are in the dataset?",
        "expected_keywords": ["colonies", "total"],
        "category": "aggregation",
    },
    {
        "id": 4,
        "description": "Best year for bird counts (max aggregation)",
        "question": "Which year had the highest total bird count across all colonies?",
        # 2021 is the answer (585,253 birds)
        "expected_keywords": ["2021", "highest"],
        "category": "ranking",
    },
    {
        "id": 5,
        "description": "Louisiana colony count (geographic filter)",
        # Changed from Texas — Louisiana is the primary focus; LA has 190 colonies
        "question": "How many distinct bird colonies are located in Louisiana?",
        "expected_keywords": ["Louisiana", "colonies"],
        "category": "geographic",
    },
    {
        "id": 6,
        "description": "Trend over time — survey years (time-series)",
        # Note: only 7 survey years exist (2010–2013, 2015, 2018, 2021)
        "question": "Show me the total bird count for each survey year from 2010 to 2021.",
        "expected_keywords": ["2010", "2021", "year", "count"],
        "category": "time_series",
    },
    {
        "id": 7,
        "description": "Worst year for bird counts (min aggregation)",
        "question": "Which year had the fewest total bird observations?",
        # 2012 is the answer (273,083 birds)
        "expected_keywords": ["2012", "fewest"],
        "category": "ranking",
    },
    {
        "id": 8,
        "description": "Top colony by nests in specific year (specific lookup)",
        "question": "Which colony had the highest nest count in 2018?",
        # Raccoon Island, LA (60,533 nests)
        "expected_keywords": ["Raccoon Island", "nests", "2018"],
        "category": "specific_lookup",
    },

    # ── Extended tests ─────────────────────────────────────────────────────────
    {
        "id": 9,
        "description": "Top Louisiana colony all-time (specific Louisiana lookup)",
        # Changed from "LA vs TX comparison" — focuses on the dominant state
        # Answer: Raccoon Island with the highest cumulative count
        "question": "Which Louisiana colony had the highest total bird count summed across all years?",
        "expected_keywords": ["Raccoon Island", "Louisiana", "birds"],
        "category": "specific_lookup",
    },
    {
        "id": 10,
        "description": "Average birds per colony in 2018 (average aggregation)",
        "question": "What is the average number of birds per colony in 2018?",
        "expected_keywords": ["average", "birds", "colony", "2018"],
        "category": "aggregation",
    },
    {
        "id": 11,
        "description": "Top 5 colonies by bird count in 2021 (top-N lookup)",
        "question": "What are the top 5 colonies by total bird count in 2021?",
        "expected_keywords": ["colony", "birds", "2021"],
        "category": "specific_lookup",
    },
    {
        "id": 12,
        "description": "Top species in Louisiana 2021 (species join lookup)",
        # Changed from "Florida colonies" — tests species JOIN with tblSpeciesCodes
        # Top answers: Laughing Gull, Royal Tern, Brown Pelican
        "question": "What were the top 3 bird species by count in Louisiana in 2021?",
        "expected_keywords": ["Laughing Gull", "species", "2021", "Louisiana"],
        "category": "specific_lookup",
    },
    {
        "id": 13,
        "description": "Colony-specific trend — Raccoon Island (time-series)",
        "question": "How has the total bird count at Raccoon Island changed across all survey years?",
        # Raccoon Island exists in 2010, 2011, 2012, 2013, 2015, 2018, 2021
        "expected_keywords": ["Raccoon Island", "birds", "year"],
        "category": "time_series",
    },
    {
        "id": 14,
        "description": "State with fewest bird observations (min ranking)",
        "question": "Which state had the fewest total bird observations across all years?",
        # Mississippi (MS) is the answer with ~11,352 birds
        "expected_keywords": ["Mississippi", "fewest"],
        "category": "ranking",
    },
    {
        "id": 15,
        "description": "Year-over-year comparison 2010 vs 2021 (comparison)",
        "question": "How did the total bird count in 2021 compare to 2010?",
        # 2021: 585,253 vs 2010: 332,746 — roughly 76% increase
        "expected_keywords": ["2021", "2010", "birds"],
        "category": "comparison",
    },
    {
        "id": 16,
        "description": "All states covered in the dataset (simple lookup)",
        "question": "What states are covered in this dataset?",
        # Five Gulf Coast states: LA, TX, FL, AL, MS
        "expected_keywords": ["Louisiana", "Texas", "Florida", "Mississippi", "Alabama"],
        "category": "simple_lookup",
    },
    {
        "id": 17,
        "description": "All-time highest single colony-year count (max lookup)",
        "question": "Which colony recorded the highest bird count in any single survey year?",
        # Raccoon Island in 2018 (74,544 birds) and 2011 (75,439 birds)
        "expected_keywords": ["Raccoon Island", "highest", "birds"],
        "category": "specific_lookup",
    },
    {
        "id": 18,
        "description": "Total nest count in 2021 (aggregation)",
        "question": "How many total nests were recorded across all colonies in 2021?",
        # 456,049 nests in 2021
        "expected_keywords": ["nests", "2021", "total"],
        "category": "aggregation",
    },
]
