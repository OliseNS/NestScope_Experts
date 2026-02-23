# Server - FastAPI Backend

The server is the **backend** of NestScope - it handles all the heavy lifting: database queries, AI inference, and API endpoints. It's built with **FastAPI**, a modern Python web framework designed for building APIs quickly and efficiently.

## What is FastAPI?

FastAPI is a Python framework for creating REST APIs (Application Programming Interfaces). Think of it as a waiter in a restaurant:
- **Frontend**: Customer orders food
- **Backend**: Kitchen prepares food
- **API**: Waiter takes orders and delivers food

FastAPI automatically:
- Validates incoming data
- Generates API documentation
- Handles async operations
- Serializes responses to JSON

## Features

### NestChat (Text-to-SQL)
- **Natural Language to SQL**: Converts user questions to SQL using Claude LLM
- **Query Execution**: Runs SQL queries against SQLite database
- **Natural Language Answers**: Generates human-readable answers from query results
- **Agentic Visualization**: LLM decides which charts/maps to show
- **Streaming Responses**: Words appear one-by-one (better UX)

### NestVision (Computer Vision)
- **Bird Detection**: YOLOv8 ONNX model for bird counting
- **Two Inference Modes**: Fast (downsampling) and SAHI (sliced inference)
- **Annotation**: Bounding boxes with Claude orange color
- **Example Images**: Built-in test images for demos

### General
- **RESTful API**: Clean REST endpoints
- **Auto-Generated Docs**: Swagger UI at `/docs`
- **CORS Enabled**: Works from web browsers
- **Health Monitoring**: Health check endpoint

## How to Run

Start the backend server:
```bash
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
```

**Flag explanations:**
- `server.main:app`: Python module path (server/main.py, variable `app`)
- `--host 0.0.0.0`: Listen on all network interfaces (allows external access)
- `--port 8000`: Use port 8000
- `--reload`: Auto-restart when code changes (dev only!)

Then open your browser to: **http://localhost:8000/docs** for interactive API documentation.

## Prerequisites

- Python 3.8+
- SQLite database (`data/bird_data_complete.db`)
- OpenRouter API key (for Claude LLM)
- ONNX Runtime (for computer vision)

## Environment Variables

Create a `.env` file in the project root:
```env
OPENROUTER_API_KEY=your_api_key_here
DB_PATH=data/bird_data_complete.db
DB_TYPE=sqlite
MODEL_NAME=anthropic/claude-sonnet-4.5
API_BASE_URL=http://localhost:8000
```

## Project Structure

```
server/
├── main.py                     # FastAPI app and all endpoints
├── prompt.txt                  # System prompt for SQL generation
├── cv_tools/                   # Computer vision module
│   ├── inference.py           # BirdDetector class (ONNX inference)
│   └── images/                # Example images for testing
├── README.md                   # This file
└── __pycache__/               # Python bytecode cache
```

## Key Concepts

### 1. REST API
REST (Representational State Transfer) is a way to design APIs using HTTP methods:
- **GET**: Retrieve data (e.g., get database schema)
- **POST**: Send data (e.g., ask a question)
- **PUT**: Update data
- **DELETE**: Remove data

**Example:**
```
GET /schema → Returns database schema
POST /ask → Send question, get answer
```

### 2. JSON (JavaScript Object Notation)
APIs communicate using JSON - a text format for structured data:
```json
{
  "question": "How many colonies are in Texas?",
  "model": "anthropic/claude-sonnet-4.5"
}
```

FastAPI automatically converts Python dictionaries to JSON and vice versa.

### 3. Pydantic Models
Pydantic validates incoming data. If someone sends bad data, FastAPI rejects it automatically:
```python
class AskRequest(BaseModel):
    question: str  # Required string
    model: str = "anthropic/claude-sonnet-4.5"  # Optional with default
```

### 4. Async/Await
FastAPI uses async functions for concurrent operations:
```python
async def ask_question(request: AskRequest):
    # Can handle multiple requests simultaneously
```

**Why async?** While waiting for database/LLM responses, server can handle other requests.

## Main API Endpoints

### NestChat Endpoints

#### POST `/ask`
Ask a question in natural language and get a complete response (non-streaming).

**Request:**
```json
{
  "question": "What colonies had the most Brown Pelicans in 2015?",
  "model": "anthropic/claude-sonnet-4.5"
}
```

**Response:**
```json
{
  "sql_query": "SELECT ColonyName, SUM(Birds) as Total...",
  "results": [...],
  "answer": "The top colony was Smith Island with 1,234 Brown Pelicans...",
  "viz_directive": "bar",
  "error": null
}
```

**How it works:**
1. LLM reads question + database schema
2. Generates SQL query
3. Execute query against SQLite
4. LLM reads results and writes answer
5. LLM decides visualization type

#### POST `/ask/stream`
Same as `/ask` but streams the answer word-by-word (better UX for long responses).

**Response:** Server-Sent Events (SSE) stream
```
data: {"type": "sql", "content": "SELECT..."}
data: {"type": "answer", "content": "The"}
data: {"type": "answer", "content": " top"}
data: {"type": "answer", "content": " colony"}
data: {"type": "done"}
```

**Why streaming?**
- User sees progress immediately
- Feels faster (perception)
- Can cancel long-running queries

### Computer Vision Endpoints

#### POST `/cv/inference`
Detect and count birds in an uploaded image.

**Request:** `multipart/form-data`
- `file`: Image file (JPG, PNG)
- `conf_threshold`: Confidence threshold (0.0-1.0, default: 0.25)
- `fast_mode`: Use fast inference (boolean, default: true)

**Response:**
```json
{
  "bird_count": 12,
  "detections": [
    {"bbox": [100, 150, 250, 400], "confidence": 0.89},
    ...
  ],
  "annotated_image": "base64_encoded_image_string",
  "inference_time": 0.234
}
```

**How it works:**
1. Receive image upload
2. Preprocess image (resize if needed)
3. Run YOLO ONNX inference
4. Apply NMS (Non-Maximum Suppression) to remove duplicates
5. Draw bounding boxes
6. Return annotated image and results

**Two modes:**
- **Fast**: Downsample large images, quick inference
- **SAHI**: Slice large images into patches, slower but more accurate

#### GET `/cv/examples`
List example images available for testing.

**Response:**
```json
{
  "examples": [
    {"name": "pelicans_colony.jpg", "path": "server/cv_tools/images/pelicans_colony.jpg"},
    ...
  ]
}
```

### Utility Endpoints

#### GET `/`
API information and documentation.

#### GET `/health`
Health check for monitoring.

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "cv_model": "loaded"
}
```

### GET `/health`
Health check endpoint to verify server and database connectivity.

**Response:**
```json
{
  "status": "healthy",
  "database": "connected"
}
```

### GET `/schema`
Returns the complete database schema including table structures and sample data.

**Response:**
```json
{
  "tables": {
    "observations": {
      "columns": [
        {
          "name": "year",
          "type": "INTEGER",
          "notnull": 0,
          "pk": 0
        },
        ...
      ],
      "sample_data": [...]
    },
    ...
  }
}
```

### GET `/stats`
Returns database statistics including observation counts, year ranges, and more.

**Response:**
```json
{
  "total_observations": 15234,
  "year_range": "2010-2021",
  "total_colonies": 156,
  "total_species": 42,
  "states": ["AL", "FL", "LA", "MS", "TX"],
  "observations_by_year": {
    "2010": 1234,
    "2011": 1456,
    ...
  }
}
```

### POST `/ask`
Ask a question in natural language. The API will convert it to SQL, execute the query, and return results with a natural language answer.

**Request Body:**
```json
{
  "question": "What colonies had oil present in 2010?",
  "model": "anthropic/claude-3.5-sonnet"  // Optional, defaults to claude-3.5-sonnet
}
```

**Response:**
```json
{
  "sql_query": "SELECT colony_name, COUNT(*) as observations FROM observations WHERE year = 2010 AND oil_present = 'Y' GROUP BY colony_name ORDER BY observations DESC LIMIT 50",
  "results": [
    {
      "colony_name": "Breton Island",
      "observations": 45
    },
    ...
  ],
  "results_count": 12,
  "answer": "In 2010, there were 12 colonies that had oil present from the Deepwater Horizon spill. The most affected colony was Breton Island with 45 observations...",
  "error": null
}
```

**Error Response:**
```json
{
  "sql_query": "ERROR: Not relevant to this dataset",
  "results": null,
  "results_count": 0,
  "answer": "",
  "error": "ERROR: Not relevant to this dataset"
}
```

## Example Usage

### Using cURL

```bash
# Health check
curl http://localhost:8000/health

# Get database stats
curl http://localhost:8000/stats

# Ask a question
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the top 5 most observed species?"}'
```

### Using Python `requests`

```python
import requests

# Ask a question
response = requests.post(
    "http://localhost:8000/ask",
    json={
        "question": "What colonies had oil present in 2010?",
        "model": "anthropic/claude-3.5-sonnet"
    }
)

data = response.json()
print(f"SQL Query: {data['sql_query']}")
print(f"Results: {data['results_count']} rows")
print(f"Answer: {data['answer']}")
```

### Using JavaScript/Fetch

```javascript
const response = await fetch('http://localhost:8000/ask', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    question: 'What colonies had oil present in 2010?',
    model: 'anthropic/claude-3.5-sonnet'
  })
});

const data = await response.json();
console.log('SQL Query:', data.sql_query);
console.log('Results:', data.results);
console.log('Answer:', data.answer);
```

## Interactive API Documentation

FastAPI automatically generates interactive API documentation:

- **Swagger UI**: Visit `http://localhost:8000/docs`
- **ReDoc**: Visit `http://localhost:8000/redoc`

These interfaces allow you to test all endpoints directly from your browser.

## Architecture Deep Dive

### Text-to-SQL Pipeline (NestChat)

The pipeline has 4 stages:

**1. SQL Generation**
```
User question + Database schema → Claude LLM → SQL query
```
- Loads system prompt from `server/prompt.txt`
- Includes full database schema in prompt
- LLM generates SQL query
- Validates query format and relevance

**2. Query Execution**
```
SQL query → SQLite database → Results (pandas DataFrame)
```
- Executes query with error handling
- Limits results to prevent memory issues
- Converts to JSON-serializable format

**3. Answer Generation**
```
Question + SQL + Results → Claude LLM → Natural language answer
```
- LLM analyzes results
- Writes human-friendly explanation
- Embeds visualization directives (e.g., `[SHOW_CHART: bar]`)

**4. Visualization Directive Parsing**
```
Answer text → Parse directives → Clean answer + viz type
```
- Extracts `[SHOW_CHART: ...]` or `[SHOW_MAP: ...]`
- Removes directives from displayed answer
- Frontend renders appropriate visualizations

### Agentic Visualization Control

The **key innovation** in NestScope is agentic visualization. Traditional systems use rule-based logic:
```python
# Traditional approach (brittle)
if "over time" in question:
    show_line_chart()
elif "top" in question or "most" in question:
    show_bar_chart()
```

NestScope uses the LLM to decide:
```python
# Agentic approach (intelligent)
answer = llm_generate_answer(question, results)
# LLM embeds: "[SHOW_CHART: bar]" in answer
viz_type = parse_visualization_directives(answer)
```

**Why better?**
- LLM understands context and intent
- Handles ambiguous cases intelligently
- No hardcoded rules to maintain

### Computer Vision Pipeline (NestVision)

**1. Image Loading**
```python
image = cv2.imread(image_path)
height, width = image.shape[:2]
```

**2. Mode Selection**
```python
if fast_mode:
    if height > 1024 or width > 1024:
        # Downsample image for speed
        detections = _downsample_and_predict(image)
    else:
        # Standard inference
        detections = _predict_standard(image)
else:
    # SAHI: Slice into patches
    detections = _predict_with_sahi(image)
```

**3. ONNX Inference**
```python
# Preprocess
input_tensor = preprocess(image)  # Resize, normalize

# Run inference
outputs = onnx_session.run(None, {"images": input_tensor})

# Postprocess
detections = postprocess(outputs)  # Extract boxes, scores, classes
```

**4. Non-Maximum Suppression (NMS)**
Removes duplicate/overlapping boxes:
```
Before NMS: [box1, box2, box3, box4]  # Many overlapping boxes on same bird
After NMS:  [box1, box3]                # One box per bird
```

**5. Annotation**
Draw bounding boxes using Claude orange color:
```python
for detection in detections:
    cv2.rectangle(image, bbox, color=(87, 119, 217), thickness=3)
```

## Database Schema

The API works with four main tables:

- **observations**: Individual bird observation records (year, colony, species, habitat, notes)
- **colony_profiles**: Aggregated data per colony
- **colony_inventory**: Master list of colonies with geographic data
- **species**: Species code to name lookup

## Configuration

### Environment Variables

- `OPENROUTER_API_KEY`: Your OpenRouter API key (required)
- `DB_PATH`: Path to SQLite database (default: `../bird_data.db`)

### Modifying the Model

You can specify different models per request or change the default in the code:

```python
# In main.py, modify the default:
chatbot = SQLChatbot(model="anthropic/claude-3.5-sonnet")

# Or specify per request:
POST /ask
{
  "question": "...",
  "model": "openai/gpt-4"
}
```

## Error Handling

The API returns appropriate HTTP status codes:

- `200`: Success
- `500`: Internal server error (database, LLM, or processing error)
- `503`: Service unavailable (database connection failed)

Error responses include detailed error messages in the response body.

## Performance Considerations

- Database connections are created per request (no connection pooling)
- Query results are limited to 50 rows by default (configurable in SQL generation prompt)
- Schema is cached after first load
- CORS is enabled for all origins (configure for production)

## Security Notes

For production deployment:

1. **Restrict CORS**: Update `allow_origins` to specific domains
2. **Add Authentication**: Implement API key or OAuth
3. **Rate Limiting**: Add rate limiting middleware
4. **Input Validation**: Additional validation for malicious inputs
5. **Database Access**: Use read-only database connection
6. **Environment Variables**: Secure storage for API keys

## Debugging and Common Issues

### Check Server Health
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "healthy", "database": "connected"}
```

### View API Documentation
FastAPI auto-generates interactive docs:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

You can test endpoints directly in the browser!

### Tail Logs in Real-Time
```bash
tail -f logs/server.log
```

Logs show all requests, errors, and SQL queries.

### Common Issues

#### "Database Connection Error"
**Problem**: Can't connect to SQLite database
**Solutions:**
- Check `DB_PATH` in `.env` points to correct file
- Verify file exists: `ls -la data/bird_data_complete.db`
- Check file permissions: `chmod 644 data/bird_data_complete.db`

#### "OpenRouter API Error"
**Problem**: LLM requests failing
**Solutions:**
- Verify API key: `echo $OPENROUTER_API_KEY`
- Check key is in `.env` file
- Test key with curl:
  ```bash
  curl https://openrouter.ai/api/v1/models \
    -H "Authorization: Bearer $OPENROUTER_API_KEY"
  ```

#### "ONNX Model Not Found"
**Problem**: Can't load bird detection model
**Solutions:**
- Check model exists: `ls -la models/seconditer.onnx`
- Verify path in `server/cv_tools/inference.py`:
  ```python
  MODEL_PATH = "models/seconditer.onnx"
  ```

#### "Port Already in Use"
**Problem**: Another process using port 8000
**Solutions:**
- Find process: `lsof -i :8000`
- Kill it: `kill -9 <PID>`
- Or use different port: `--port 8001`

#### "Inference Too Slow"
**Problem**: CV inference takes >10 seconds
**Solutions:**
- Use `fast_mode=true` (enabled by default)
- Reduce image size before uploading
- Check CPU usage (should use all cores)
- Consider GPU acceleration (requires CUDA setup)

## System Prompt Engineering

The SQL generation quality depends heavily on `server/prompt.txt`. This file contains:

### 1. Database Schema
Complete table structures with column names, types, and descriptions.

### 2. Example Q&A Pairs
```
Question: "What colonies are in Texas?"
SQL: SELECT DISTINCT ColonyName FROM observations WHERE State = 'TX'
```

### 3. Critical Rules
- **Always include Latitude/Longitude** when grouping by colony (enables maps)
- **Limit results** to 50 rows to prevent memory issues
- **Validate relevance** - reject unrelated questions

### 4. Visualization Directives
Instructions for when to use `[SHOW_CHART: line]`, `[SHOW_MAP: true]`, etc.

**To modify SQL behavior:**
1. Edit `server/prompt.txt`
2. Add examples of desired behavior
3. Test with various questions
4. No server restart needed (auto-reloads)

## Development Workflow

### 1. Add New Endpoint
```python
@app.post("/new_endpoint")
async def new_endpoint(data: RequestModel):
    # Your logic here
    return {"result": "success"}
```

### 2. Test in Swagger UI
Open http://localhost:8000/docs and test interactively.

### 3. Update Frontend
Modify `frontend/services/api_client.py` to call new endpoint.

### 4. Document in README
Add endpoint description above.

## Learning Resources

### FastAPI
- **Official Docs**: https://fastapi.tiangolo.com/
- **Tutorial**: https://fastapi.tiangolo.com/tutorial/
- **Async/Await Guide**: https://realpython.com/async-io-python/

### Computer Vision
- **ONNX Runtime**: https://onnxruntime.ai/docs/
- **YOLO**: https://docs.ultralytics.com/
- **SAHI**: https://github.com/obss/sahi

### LLM Integration
- **OpenRouter**: https://openrouter.ai/docs
- **Prompt Engineering**: https://www.promptingguide.ai/

## Next Steps

To understand the backend better:
1. Read `main.py` top-to-bottom (start with imports and class definitions)
2. Test endpoints in Swagger UI (/docs)
3. Check `server/prompt.txt` to understand SQL generation
4. Read `cv_tools/inference.py` to understand bird detection
5. Watch server logs while testing: `tail -f logs/server.log`

## Connection to Other Components

```
Frontend (Streamlit) → API requests → Server (FastAPI)
                                      ↓
                                    Database (SQLite)
                                      ↓
                                    LLM (Claude via OpenRouter)
                                      ↓
                                    CV Model (YOLO ONNX)
```

The server is the central hub - everything connects through it!
