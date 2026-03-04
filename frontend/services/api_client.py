"""
API Client for communicating with the FastAPI backend
"""

import requests
import streamlit as st
import json
from typing import Dict, Any, List, Optional, Generator
from .config import DEFAULT_MODEL


def ask_question_to_backend(question: str, model: str = None, conversation_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Send a question to the FastAPI backend and return the response.

    Args:
        question: Natural language question
        model: LLM model to use (defaults to MODEL_NAME from .env)
        conversation_history: Previous conversation messages for context

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
            json={"question": question, "model": model, "conversation_history": conversation_history},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}


def ask_question_streaming(question: str, model: str = None, conversation_history: List[Dict[str, str]] = None) -> Generator[Dict[str, Any], None, None]:
    """
    Send a question to the FastAPI backend and stream the response.

    Args:
        question: Natural language question
        model: LLM model to use (defaults to MODEL_NAME from .env)
        conversation_history: Previous conversation messages for context

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
            json={"question": question, "model": model, "conversation_history": conversation_history},
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


def ask_question_agentic_streaming(question: str, model: str = None, conversation_history: List[Dict[str, str]] = None) -> Generator[Dict[str, Any], None, None]:
    """
    Send a question to the FastAPI backend with agentic self-correction and stream progress updates.

    This uses multi-step reasoning with real-time progress updates:
    1. Analyze question
    2. Generate SQL
    3. Self-validate SQL
    4. Execute query
    5. Validate results
    6. Retry if needed (max 3 attempts)

    Args:
        question: Natural language question
        model: LLM model to use (defaults to MODEL_NAME from .env)
        conversation_history: Previous conversation messages for context

    Yields:
        Events: {
            'type': 'thinking_step'|'sql_generated'|'validation_result'|'results'|
                    'retry'|'answer_chunk'|'success'|'error'|'done',
            'content': ...,
            ...
        }
    """
    from .config import API_BASE_URL

    # Use DEFAULT_MODEL from config if not specified
    if model is None:
        model = DEFAULT_MODEL

    try:
        response = requests.post(
            f"{API_BASE_URL}/ask/agentic/stream",
            json={"question": question, "model": model, "conversation_history": conversation_history},
            stream=True,
            timeout=120  # Longer timeout for agentic mode
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
def get_backend_config() -> Dict[str, Any]:
    """
    Fetch backend configuration to stay synchronized with server settings.
    Cached for 1 hour to reduce API calls.

    Returns:
        Dictionary containing model and CV configuration
    """
    from .config import API_BASE_URL

    try:
        response = requests.get(f"{API_BASE_URL}/config", timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        # Fallback to default if backend is unreachable
        return {
            "model": {
                "name": "minimax/minimax-m2.5",
                "temperature": 0.7,
                "max_tokens": 1000
            },
            "cv": {
                "default_confidence": 0.25,
                "default_fast_mode": True
            }
        }


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
    from urllib.parse import quote

    try:
        # URL-encode the filename to handle spaces and special characters
        encoded_name = quote(example_name)
        response = requests.get(
            f"{API_BASE_URL}/cv/example/{encoded_name}",
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


def get_tables() -> Dict[str, Any]:
    """
    Get list of all tables in the database.

    Returns:
        Dictionary containing list of table names
    """
    from .config import API_BASE_URL

    try:
        response = requests.get(f"{API_BASE_URL}/db/tables", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"tables": [], "error": str(e)}


def get_table_data(table_name: str, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
    """
    Get paginated data from a specific table.

    Args:
        table_name: Name of the table
        page: Page number (1-indexed)
        page_size: Number of rows per page

    Returns:
        Dictionary containing table data and pagination info
    """
    from .config import API_BASE_URL

    try:
        response = requests.get(
            f"{API_BASE_URL}/db/table/{table_name}",
            params={"page": page, "page_size": page_size},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "data": None,
            "total_rows": 0,
            "page": page,
            "page_size": page_size,
            "total_pages": 0,
            "error": str(e)
        }


def get_table_schema(table_name: str) -> Dict[str, Any]:
    """
    Get schema information for a specific table.

    Args:
        table_name: Name of the table

    Returns:
        Dictionary containing table schema
    """
    from .config import API_BASE_URL

    try:
        response = requests.get(
            f"{API_BASE_URL}/db/table/{table_name}/schema",
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "table_name": table_name,
            "columns": None,
            "error": str(e)
        }


def update_table_row(table_name: str, row_id: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update a row in a table.

    Args:
        table_name: Name of the table
        row_id: Primary key column(s) and value(s)
        updates: Columns to update

    Returns:
        Dictionary containing success status
    """
    from .config import API_BASE_URL

    try:
        response = requests.put(
            f"{API_BASE_URL}/db/table/{table_name}/row",
            json={"table_name": table_name, "row_id": row_id, "updates": updates},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": None, "error": str(e)}


def delete_table_row(table_name: str, row_id: Dict[str, Any]) -> Dict[str, Any]:
    """
    Delete a row from a table.

    Args:
        table_name: Name of the table
        row_id: Primary key column(s) and value(s)

    Returns:
        Dictionary containing success status
    """
    from .config import API_BASE_URL

    try:
        response = requests.delete(
            f"{API_BASE_URL}/db/table/{table_name}/row",
            json={"table_name": table_name, "row_id": row_id},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": None, "error": str(e)}


def insert_table_row(table_name: str, row_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Insert a new row into a table.

    Args:
        table_name: Name of the table
        row_data: Column names and values for the new row

    Returns:
        Dictionary containing success status
    """
    from .config import API_BASE_URL

    try:
        response = requests.post(
            f"{API_BASE_URL}/db/table/{table_name}/row",
            json={"table_name": table_name, "row_data": row_data},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": None, "error": str(e)}


# ============================================================================
# STAC DATA API — Water Institute avian monitoring catalog
# ============================================================================

@st.cache_data(ttl=3600)
def get_stac_summary() -> Dict[str, Any]:
    """
    Fetch complete STAC summary: colony metadata + species totals.
    Cached for 1 hour — data is static (historical survey records).
    """
    from .config import API_BASE_URL
    try:
        r = requests.get(f"{API_BASE_URL}/stac/summary", timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e), "colonies": [], "species_totals": {}}


@st.cache_data(ttl=3600)
def get_stac_species(colony_id: str, year: str) -> Dict[str, Any]:
    """
    Fetch species breakdown for a specific colony-year.
    Returns {colony_id, year, species: [{code, name, color, total_birds, total_nests}]}
    """
    from .config import API_BASE_URL
    try:
        r = requests.get(f"{API_BASE_URL}/stac/species/{colony_id}/{year}", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e), "species": []}


@st.cache_data(ttl=3600)
def get_stac_dots(colony_id: str, year: str, species_code: str, dot_type: str = "Bird") -> Dict[str, Any]:
    """
    Fetch expert-annotated species dot GeoJSON for a colony-year-species.
    Returns a GeoJSON FeatureCollection.
    """
    from .config import API_BASE_URL
    try:
        r = requests.get(
            f"{API_BASE_URL}/stac/dots/{colony_id}/{year}/{species_code}",
            params={"dot_type": dot_type},
            timeout=15
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"type": "FeatureCollection", "features": [], "error": str(e)}


@st.cache_data(ttl=3600)
def get_mosaic_preview(colony_id: str, year: str) -> Optional[str]:
    """
    Fetch a 512x512 JPEG preview of a COG mosaic from S3 via the backend.
    Returns base64-encoded JPEG string, or None if unavailable.
    """
    from .config import API_BASE_URL
    try:
        r = requests.get(f"{API_BASE_URL}/stac/mosaic_preview/{colony_id}/{year}", timeout=30)
        r.raise_for_status()
        return r.json().get("preview_base64")
    except Exception:
        return None


def run_mosaic_inference(colony_id: str, year: str, conf: float = 0.25, fast_mode: bool = True) -> Dict[str, Any]:
    """
    Run NestVision bird detection on a center tile of a colony COG mosaic.
    Returns detection results with species_summary.
    """
    from .config import API_BASE_URL
    try:
        r = requests.post(
            f"{API_BASE_URL}/cv/inference/mosaic",
            params={"colony_id": colony_id, "year": year, "conf": conf, "fast_mode": fast_mode},
            timeout=90
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}
