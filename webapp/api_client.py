"""
API Client for NestScope Webapp
Communicates with FastAPI backend at localhost:8000
"""

import requests
import json
from typing import Generator, Dict, Any, Optional, List


BACKEND_URL = "http://localhost:8000"


def ask_question_agentic_streaming(question: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Generator[Dict[str, Any], None, None]:
    """
    Stream chat responses from backend using SSE.
    Yields events as they arrive from the backend.

    Args:
        question: User's question
        conversation_history: List of previous messages [{"role": "user"/"assistant", "content": "..."}]
    """
    url = f"{BACKEND_URL}/ask/stream"
    payload = {
        "question": question,
        "conversation_history": conversation_history or []
    }

    with requests.post(url, json=payload, stream=True, timeout=300) as response:
        response.raise_for_status()

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


def run_cv_inference(file, conf_threshold: float = 0.25) -> Dict[str, Any]:
    """
    Run computer vision inference on uploaded image.

    Args:
        file: File object from Flask request.files
        conf_threshold: Detection confidence threshold (0.0 to 1.0)

    Returns:
        Dict with detection results including bird_count, annotated_image_base64, etc.
    """
    url = f"{BACKEND_URL}/cv/inference"

    # Prepare multipart form data
    files = {'file': (file.filename, file.stream, file.content_type)}
    data = {'conf_threshold': conf_threshold}

    response = requests.post(url, files=files, data=data, timeout=120)
    response.raise_for_status()

    return response.json()


def get_backend_config() -> Dict[str, Any]:
    """
    Get backend configuration including model name.

    Returns:
        Dict with config data like {"model": {"name": "..."}}
    """
    url = f"{BACKEND_URL}/config"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()


def get_stats_from_backend() -> Dict[str, Any]:
    """
    Get database statistics from backend.

    Returns:
        Dict with stats like min_year, max_year, total_colonies, etc.
    """
    url = f"{BACKEND_URL}/stats"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()


def get_example_images() -> List[str]:
    """
    Get list of example image filenames from backend.

    Returns:
        List of filenames like ["example1.jpg", "example2.jpg"]
    """
    url = f"{BACKEND_URL}/cv/examples"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()
    return data.get('examples', [])


def fetch_example_image(filename: str) -> Optional[bytes]:
    """
    Fetch a specific example image from backend.

    Args:
        filename: Name of the example image file

    Returns:
        Image bytes or None if not found
    """
    url = f"{BACKEND_URL}/cv/example/{filename}"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.content
    except requests.RequestException:
        return None
