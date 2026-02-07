"""
Claude function schemas for natural language query planning.

This module defines the function schemas that Claude uses to understand
what query functions are available and how to call them.

Person 2 (LLM/AI Developer) implementation
"""

from typing import List, Dict, Any


# Function schemas for Claude API
FUNCTION_SCHEMAS: List[Dict[str, Any]] = [
    {
        "name": "species_trend",
        "description": "Get population trend for a bird species over a time range. Use this when users ask about trends, changes over time, or population history.",
        "input_schema": {
            "type": "object",
            "properties": {
                "species": {
                    "type": "string",
                    "description": "The bird species name (e.g., 'Brown Pelican', 'Laughing Gull')"
                },
                "start_year": {
                    "type": "integer",
                    "description": "Start year for the trend analysis (2010-2021)"
                },
                "end_year": {
                    "type": "integer",
                    "description": "End year for the trend analysis (2010-2021)"
                }
            },
            "required": ["species", "start_year", "end_year"]
        }
    },
    {
        "name": "top_species",
        "description": "Get the top N bird species by observation count. Use this when users ask about most common species, rankings, or 'what are the top X species'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "n": {
                    "type": "integer",
                    "description": "Number of top species to return (default: 5)"
                },
                "year": {
                    "type": "integer",
                    "description": "Optional: Filter to specific year (2010-2021)"
                },
                "region": {
                    "type": "string",
                    "description": "Optional: Filter to specific region/parish name"
                }
            },
            "required": ["n"]
        }
    },
    {
        "name": "compare_regions",
        "description": "Compare bird populations across different Louisiana parishes/regions. Use this when users ask to compare locations or geographic areas.",
        "input_schema": {
            "type": "object",
            "properties": {
                "regions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of region/parish names to compare (e.g., ['Terrebonne', 'Plaquemines'])"
                },
                "species": {
                    "type": "string",
                    "description": "Optional: Specific species to compare across regions"
                },
                "start_year": {
                    "type": "integer",
                    "description": "Optional: Start year for comparison"
                },
                "end_year": {
                    "type": "integer",
                    "description": "Optional: End year for comparison"
                }
            },
            "required": ["regions"]
        }
    },
    {
        "name": "colony_details",
        "description": "Get detailed information about a specific bird colony over time. Use this when users ask about a specific colony location.",
        "input_schema": {
            "type": "object",
            "properties": {
                "colony_name": {
                    "type": "string",
                    "description": "Name of the bird colony"
                }
            },
            "required": ["colony_name"]
        }
    },
    {
        "name": "temporal_comparison",
        "description": "Compare bird populations before and after a specific event (e.g., hurricane, oil spill). Use this for impact assessment questions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "event_date": {
                    "type": "string",
                    "description": "Date of the event in YYYY-MM-DD format"
                },
                "species": {
                    "type": "string",
                    "description": "Optional: Specific species to analyze"
                },
                "region": {
                    "type": "string",
                    "description": "Optional: Specific region affected by the event"
                },
                "before_window": {
                    "type": "integer",
                    "description": "Days before event to include in analysis (default: 365)"
                },
                "after_window": {
                    "type": "integer",
                    "description": "Days after event to include in analysis (default: 365)"
                }
            },
            "required": ["event_date"]
        }
    }
]


def get_function_schemas() -> List[Dict[str, Any]]:
    """Return all available function schemas for Claude."""
    return FUNCTION_SCHEMAS
