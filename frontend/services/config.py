"""
Configuration for the frontend application
"""

import os

# API configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Model configuration
DEFAULT_MODEL = "anthropic/claude-opus-4.5"

# UI configuration
CHART_COLORS = {
    'primary': '#D97757',
    'hover': '#E5865F'
}
