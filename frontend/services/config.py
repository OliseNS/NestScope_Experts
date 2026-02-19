"""
Configuration for the frontend application
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Model configuration - reads from .env file (SINGLE SOURCE OF TRUTH)
# Change MODEL_NAME in .env file to update the default model
DEFAULT_MODEL = os.getenv("MODEL_NAME", "anthropic/claude-sonnet-4.5")

# UI configuration
CHART_COLORS = {
    'primary': '#D97757',
    'hover': '#E5865F'
}
