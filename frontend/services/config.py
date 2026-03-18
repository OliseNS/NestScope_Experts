"""
Configuration for the frontend application
"""

import os
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

# API configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Model configuration - fetched from backend /config endpoint
# This ensures frontend and backend always use the same model
def get_default_model():
    """
    Fetch the default model from backend configuration.
    Falls back to hardcoded value if backend is unavailable.
    """
    try:
        response = requests.get(f"{API_BASE_URL}/config", timeout=2)
        if response.status_code == 200:
            return response.json()['model']['name']
    except:
        pass

    # Fallback: must match server/config.yaml default
    return "minimax/minimax-m2.5"

# Cache the model name at module load time
DEFAULT_MODEL = get_default_model()

# UI configuration
CHART_COLORS = {
    'primary': '#D97757',
    'hover': '#E5865F'
}
