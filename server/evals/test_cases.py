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
  - Simple lookup  → "What states are in the dataset?"
  - Aggregation    → "How many total birds in 2015?"
  - Ranking        → "Which year had the highest count?"
  - Geographic     → "How many colonies in Texas?"
  - Time-series    → "Show me the trend from 2010 to 2021"
  - Specific lookup → "Which colony had the most nests in 2018?"

This gives us a balanced scorecard that reveals WHERE the AI struggles.
"""

NESTCHAT_TEST_CASES = [
    {
        "id": 1,
        "description": "Annual total bird count (aggregation)",
        "question": "How many total birds were observed in 2015?",
        "expected_keywords": ["2015", "birds", "total", "count"],
        "category": "aggregation",
    },
    {
        "id": 2,
        "description": "State with most observations (ranking + geographic)",
        "question": "Which state had the most total bird observations overall?",
        "expected_keywords": ["state", "most", "birds"],
        "category": "ranking",
    },
    {
        "id": 3,
        "description": "Total colony count (simple aggregation)",
        "question": "What is the total number of distinct bird colonies in the dataset?",
        "expected_keywords": ["colonies", "total", "number"],
        "category": "aggregation",
    },
    {
        "id": 4,
        "description": "Best year for bird counts (max aggregation)",
        "question": "Which year had the highest total bird count across all colonies?",
        "expected_keywords": ["year", "highest", "count"],
        "category": "ranking",
    },
    {
        "id": 5,
        "description": "Geographic filter — Texas colonies (filtering)",
        "question": "How many bird colonies are located in Texas?",
        "expected_keywords": ["Texas", "colonies"],
        "category": "geographic",
    },
    {
        "id": 6,
        "description": "Trend over time — 2010 to 2021 (time-series)",
        "question": "Show me the total bird count for each year from 2010 to 2021.",
        "expected_keywords": ["2010", "2021", "year", "count"],
        "category": "time_series",
    },
    {
        "id": 7,
        "description": "Worst year for bird counts (min aggregation)",
        "question": "Which year had the fewest total bird observations?",
        "expected_keywords": ["year", "fewest", "lowest", "minimum"],
        "category": "ranking",
    },
    {
        "id": 8,
        "description": "Top colony by nests in specific year (specific lookup)",
        "question": "Which colony had the highest nest count in 2018?",
        "expected_keywords": ["colony", "nests", "2018", "highest"],
        "category": "specific_lookup",
    },
]
