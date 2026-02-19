"""
API Client for communicating with the FastAPI backend
"""

import requests
import streamlit as st
import json
from typing import Dict, Any, List, Optional, Generator
from .config import DEFAULT_MODEL


def ask_question_to_backend(question: str, model: str = None) -> Dict[str, Any]:
    """
    Send a question to the FastAPI backend and return the response.

    Args:
        question: Natural language question
        model: LLM model to use (defaults to MODEL_NAME from .env)

    Returns:
        Dictionary containing SQL query, results, and answer
    """
    from .config import API_BASE_URL

    # Use DEFAULT_MODEL from config if not specified
    if model is None:
        model = DEFAULT_MODEL

    try:
        response = requests.post(
            f"{API_BASE_URL}/ask",
            json={"question": question, "model": model},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}


def ask_question_streaming(question: str, model: str = None) -> Generator[Dict[str, Any], None, None]:
    """
    Send a question to the FastAPI backend and stream the response.

    Args:
        question: Natural language question
        model: LLM model to use (defaults to MODEL_NAME from .env)

    Yields:
        Events: {'type': 'sql_query'|'results'|'answer_chunk'|'error'|'done', 'content': ...}
    """
    from .config import API_BASE_URL

    # Use DEFAULT_MODEL from config if not specified
    if model is None:
        model = DEFAULT_MODEL

    try:
        response = requests.post(
            f"{API_BASE_URL}/ask/stream",
            json={"question": question, "model": model},
            stream=True,
            timeout=60
        )
        response.raise_for_status()

        # Process the SSE stream
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data = line[6:]  # Remove 'data: ' prefix
                    try:
                        event = json.loads(data)
                        yield event
                    except json.JSONDecodeError:
                        continue
    except requests.exceptions.RequestException as e:
        yield {"type": "error", "content": str(e)}


def get_stats_from_backend() -> Dict[str, Any]:
    """
    Fetch database statistics from the FastAPI backend.

    Returns:
        Dictionary containing database statistics
    """
    from .config import API_BASE_URL

    try:
        response = requests.get(f"{API_BASE_URL}/stats", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}


def run_cv_inference(image_file, conf_threshold: float = 0.25, fast_mode: bool = True) -> Dict[str, Any]:
    """
    Send an image to the backend for bird detection inference.

    Args:
        image_file: File-like object containing image data
        conf_threshold: Confidence threshold for detections
        fast_mode: Enable fast mode for processing

    Returns:
        Dictionary containing detection results
    """
    from .config import API_BASE_URL

    try:
        files = {"file": image_file}
        response = requests.post(
            f"{API_BASE_URL}/cv/inference",
            files=files,
            params={"conf_threshold": conf_threshold, "fast_mode": fast_mode},
            timeout=120
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


@st.cache_data(ttl=3600)
def get_example_images() -> List[str]:
    """
    Fetch list of example images from the backend.

    Returns:
        List of example image filenames
    """
    from .config import API_BASE_URL

    try:
        response = requests.get(f"{API_BASE_URL}/cv/examples", timeout=10)
        response.raise_for_status()
        return response.json().get("examples", [])
    except requests.exceptions.RequestException:
        return []


@st.cache_data(ttl=3600)
def fetch_example_image(example_name: str) -> Optional[bytes]:
    """
    Fetch a single example image from the backend and cache it.

    Args:
        example_name: Name of the example image

    Returns:
        Image bytes or None if fetch fails
    """
    from .config import API_BASE_URL

    try:
        response = requests.get(
            f"{API_BASE_URL}/cv/example/{example_name}",
            timeout=10
        )
        if response.status_code == 200:
            return response.content
        return None
    except Exception:
        return None


def execute_custom_sql(sql_query: str) -> Dict[str, Any]:
    """
    Execute a custom SQL query on the database.

    Args:
        sql_query: SQL query to execute

    Returns:
        Dictionary containing results and error (if any)
    """
    from .config import API_BASE_URL

    try:
        response = requests.post(
            f"{API_BASE_URL}/query/execute",
            json={"sql_query": sql_query},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e), "results": None}


def get_ai_insights(results_data: List[Dict[str, Any]], sample_size: int = 50) -> Dict[str, Any]:
    """
    Get AI-powered insights on query results.

    Args:
        results_data: List of result rows from SQL query
        sample_size: Maximum number of rows to send for analysis

    Returns:
        Dictionary containing AI insights
    """
    from .config import API_BASE_URL

    try:
        response = requests.post(
            f"{API_BASE_URL}/query/insights",
            json={"results": results_data, "sample_size": sample_size},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e), "insights": None}
