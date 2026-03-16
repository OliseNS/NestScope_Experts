"""
NestScope Web Application - Flask Server
Clean HTML/Tailwind frontend with artifact support
"""

from flask import Flask, render_template, request, Response, jsonify, send_from_directory
import json
import sys
import os
from io import BytesIO

# Import webapp's API client
from api_client import (
    ask_question_agentic_streaming,
    run_cv_inference,
    get_backend_config,
    get_stats_from_backend,
    get_example_images,
    fetch_example_image
)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max upload
app.config['SECRET_KEY'] = 'nestscope-dev-key'  # Change in production

# ============================================================================
# ROUTES - Pages
# ============================================================================

@app.route('/')
def index():
    """Landing page with feature cards and stats"""
    try:
        stats = get_stats_from_backend()
        config = get_backend_config()
    except Exception as e:
        print(f"Error fetching initial data: {e}")
        stats = {
            "min_year": 2010,
            "max_year": 2021,
            "total_colonies": 0,
            "total_species": 0,
            "total_observations": 0
        }
        config = {
            "model": {"name": "Unknown"}
        }

    return render_template('index.html', stats=stats, config=config)


@app.route('/chat')
def chat():
    """NestChat interface with artifact support"""
    try:
        config = get_backend_config()
        model_name = config.get("model", {}).get("name", "Unknown")
    except:
        model_name = "Unknown"

    return render_template('chat.html', model_name=model_name)


@app.route('/vision')
def vision():
    """NestVision interface for bird detection"""
    try:
        examples = get_example_images()
    except:
        examples = []

    return render_template('vision.html', examples=examples)


@app.route('/status')
def status():
    """System status page showing service health"""
    import requests

    services = {
        "backend": {
            "url": "http://localhost:8000",
            "name": "FastAPI Backend",
            "healthy": False,
            "response_time": None,
            "error": None
        },
        "labeller": {
            "url": "http://localhost:5000",
            "name": "Nestperts Platform",
            "healthy": False,
            "response_time": None,
            "error": None
        }
    }

    # Check backend
    try:
        import time
        start = time.time()
        response = requests.get(f"{services['backend']['url']}/health", timeout=5)
        services['backend']['response_time'] = round((time.time() - start) * 1000, 2)
        services['backend']['healthy'] = response.status_code == 200
        if response.status_code == 200:
            services['backend']['details'] = response.json()
    except Exception as e:
        services['backend']['error'] = str(e)

    # Check labeller
    try:
        start = time.time()
        response = requests.get(f"{services['labeller']['url']}/health", timeout=5)
        services['labeller']['response_time'] = round((time.time() - start) * 1000, 2)
        services['labeller']['healthy'] = response.status_code == 200
        if response.status_code == 200:
            services['labeller']['details'] = response.json()
    except Exception as e:
        services['labeller']['error'] = str(e)

    return render_template('status.html', services=services)


# ============================================================================
# HEALTH & STATUS
# ============================================================================

@app.route('/api/health')
def health_check():
    """Check health of webapp"""
    return jsonify({"status": "ok", "service": "webapp"})


@app.route('/api/services/status')
def services_status():
    """Check status of all services"""
    import requests

    services = {
        "backend": {"url": "http://localhost:8000", "name": "FastAPI Backend", "healthy": False},
        "labeller": {"url": "http://localhost:5000", "name": "Nestperts Platform", "healthy": False}
    }

    # Check backend
    try:
        response = requests.get(f"{services['backend']['url']}/health", timeout=2)
        services['backend']['healthy'] = response.status_code == 200
    except:
        pass

    # Check labeller
    try:
        response = requests.get(f"{services['labeller']['url']}/health", timeout=2)
        services['labeller']['healthy'] = response.status_code == 200
    except:
        pass

    return jsonify(services)


# ============================================================================
# API ROUTES - NestChat
# ============================================================================

@app.route('/api/chat/stream', methods=['POST'])
def chat_stream():
    """
    SSE streaming endpoint for NestChat.
    Streams AI responses with support for artifacts and conversation context.
    """
    data = request.get_json()
    question = data.get('question', '')
    conversation_history = data.get('conversation_history', [])

    if not question:
        return jsonify({"error": "No question provided"}), 400

    def generate():
        # Send keep-alive padding for some browsers
        yield ":" + " " * 2048 + "\n\n"

        try:
            # Stream events from backend with conversation history
            for event in ask_question_agentic_streaming(question, conversation_history=conversation_history):
                yield f"data: {json.dumps(event)}\n\n"

            # Always send done event to close the connection
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

    response = Response(generate(), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'  # Disable nginx buffering
    response.headers['Connection'] = 'keep-alive'
    return response


# ============================================================================
# API ROUTES - NestVision
# ============================================================================

@app.route('/api/vision/inference', methods=['POST'])
def vision_inference():
    """CV inference endpoint for bird detection"""
    try:
        # Get uploaded file
        if 'file' not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "Empty filename"}), 400

        # Get confidence threshold
        conf_threshold = float(request.form.get('conf_threshold', 0.25))

        # Run inference
        result = run_cv_inference(file, conf_threshold)

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/vision/examples')
def vision_examples():
    """Get list of example images"""
    try:
        examples = get_example_images()
        return jsonify({"examples": examples})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/vision/example/<path:filename>')
def vision_example_image(filename):
    """Fetch a specific example image"""
    try:
        image_bytes = fetch_example_image(filename)
        if image_bytes:
            return Response(image_bytes, mimetype='image/jpeg')
        else:
            return jsonify({"error": "Image not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# STATIC FILE SERVING
# ============================================================================

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory('static', filename)


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    # Get port from environment (Railway sets this) or default to 8501
    port = int(os.getenv('WEBAPP_PORT', 8501))

    print("\n" + "="*50)
    print("  NestScope Web Application")
    print("="*50)
    print(f"\n  Backend:  http://localhost:8000")
    print(f"  Frontend: http://localhost:{port}")
    print(f"\n  Ctrl+C to stop\n")

    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
