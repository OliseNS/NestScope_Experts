"""
FastAPI Server for Text-to-SQL Bird Colony Chatbot
Provides REST API endpoints for querying bird colony data
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import sqlite3
import pandas as pd
from openai import OpenAI
import os
from pathlib import Path
from dotenv import load_dotenv
import json
import asyncio
import cv2
import base64
from server.cv_tools.inference import BirdDetector, get_example_images

# Load environment variables
load_dotenv()

# Initialize OpenRouter client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

app = FastAPI(
    title="Bird Colony SQL Chatbot API",
    description="REST API for querying bird colony observation data using natural language",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Models
class QuestionRequest(BaseModel):
    question: str
    model: Optional[str] = None  # Use MODEL_NAME from env if not specified
    conversation_history: Optional[List[Dict[str, str]]] = None  # Previous messages for context

class QueryResponse(BaseModel):
    sql_query: str
    results: Optional[List[Dict[str, Any]]]
    results_count: int
    answer: str
    error: Optional[str] = None
    show_chart: bool = False
    chart_type: Optional[str] = None  # 'line' or 'bar'
    show_map: bool = False

class SchemaResponse(BaseModel):
    tables: Dict[str, Any]

class StatsResponse(BaseModel):
    total_observations: int
    year_range: str
    total_colonies: int
    total_species: int
    states: List[str]
    observations_by_year: Dict[str, int]

class CVInferenceResponse(BaseModel):
    bird_count: int
    detections: List[Dict[str, Any]]
    annotated_image_base64: str
    message: str
    inference_time: float

class ExampleImagesResponse(BaseModel):
    examples: List[str]

class CustomSQLRequest(BaseModel):
    sql_query: str

class CustomSQLResponse(BaseModel):
    success: bool
    results: Optional[List[Dict[str, Any]]]
    results_count: int
    error: Optional[str] = None

class InsightsRequest(BaseModel):
    results: List[Dict[str, Any]]
    sample_size: int = 50

class InsightsResponse(BaseModel):
    success: bool
    insights: Optional[str]
    error: Optional[str] = None

# Database configuration
DB_PATH = os.getenv("DB_PATH", "../data/bird_data_complete.db")

# Model configuration - SINGLE SOURCE OF TRUTH
# Change this in .env file only
MODEL_NAME = os.getenv("MODEL_NAME", "anthropic/claude-sonnet-4.5")

# Get the directory where this file is located
SERVER_DIR = Path(__file__).parent
DEFAULT_PROMPT_PATH = SERVER_DIR / "prompt.txt"

def parse_visualization_directives(answer_text: str, results_df=None) -> Dict[str, Any]:
    """
    Parse visualization directives from LLM response with automatic fallback detection.

    Args:
        answer_text: The LLM's answer text
        results_df: DataFrame with query results for automatic detection

    Returns:
        Dictionary with 'clean_answer', 'show_chart', 'chart_type', 'show_map'
    """
    import re

    directives = {
        'clean_answer': answer_text,
        'show_chart': False,
        'chart_type': None,
        'show_map': False
    }

    # Look for visualization directives from LLM
    chart_match = re.search(r'\[SHOW_CHART:\s*(line|bar)\]', answer_text, re.IGNORECASE)
    map_match = re.search(r'\[SHOW_MAP:\s*true\]', answer_text, re.IGNORECASE)
    no_viz_match = re.search(r'\[NO_VIZ\]', answer_text, re.IGNORECASE)

    if chart_match:
        directives['show_chart'] = True
        directives['chart_type'] = chart_match.group(1).lower()

    if map_match:
        directives['show_map'] = True

    # AUTOMATIC FALLBACK: If LLM didn't provide directives, detect them from data
    if not no_viz_match and results_df is not None and not results_df.empty:
        # Check if we should show a map (has coordinates)
        if not directives['show_map']:
            cols_lower = [str(col).lower() for col in results_df.columns]
            has_lat = 'latitude' in cols_lower
            has_lon = 'longitude' in cols_lower

            if has_lat and has_lon:
                # Check if we have valid non-null coordinates
                lat_col = results_df.columns[cols_lower.index('latitude')]
                lon_col = results_df.columns[cols_lower.index('longitude')]
                has_valid_coords = (
                    results_df[lat_col].notna().any() and
                    results_df[lon_col].notna().any()
                )
                if has_valid_coords:
                    directives['show_map'] = True

        # Check if we should show a chart (has numeric data suitable for visualization)
        if not directives['show_chart'] and len(results_df.columns) >= 2:
            # Look for time-based columns (Year, Date, Month, Season)
            time_keywords = ['year', 'date', 'time', 'month', 'season']
            time_cols = [col for col in results_df.columns
                        if any(keyword in str(col).lower() for keyword in time_keywords)]
            has_time_col = len(time_cols) > 0

            # Look for count/numeric columns
            numeric_cols = results_df.select_dtypes(include=['number']).columns.tolist()
            # Filter out coordinate columns
            numeric_cols = [col for col in numeric_cols
                          if not any(coord in str(col).lower() for coord in ['latitude', 'longitude', 'lat', 'lon'])]

            # Look for categorical columns (species, colony, state, etc.)
            categorical_cols = results_df.select_dtypes(include=['object', 'string']).columns.tolist()
            has_categorical = len(categorical_cols) > 0

            has_counts = len(numeric_cols) > 0

            if has_counts:
                # Decide between line and bar chart
                if has_time_col and len(results_df) >= 3:
                    # Time series data with multiple points -> line chart
                    directives['show_chart'] = True
                    directives['chart_type'] = 'line'
                elif has_categorical and len(results_df) <= 50:
                    # Categorical comparison data (not too many rows) -> bar chart
                    directives['show_chart'] = True
                    directives['chart_type'] = 'bar'
                elif len(results_df) <= 20:
                    # Small dataset, default to bar chart for clarity
                    directives['show_chart'] = True
                    directives['chart_type'] = 'bar'

    # Remove directives from answer text
    clean_answer = re.sub(r'\[SHOW_CHART:\s*(line|bar)\]', '', answer_text, flags=re.IGNORECASE)
    clean_answer = re.sub(r'\[SHOW_MAP:\s*true\]', '', clean_answer, flags=re.IGNORECASE)
    clean_answer = re.sub(r'\[NO_VIZ\]', '', clean_answer, flags=re.IGNORECASE)
    directives['clean_answer'] = clean_answer.strip()

    return directives


class SQLChatbot:
    def __init__(self, db_path=DB_PATH, model=None, prompt_path=None):
        """Initialize the SQL chatbot"""
        self.db_path = db_path
        self.model = model or MODEL_NAME  # Use MODEL_NAME from env if not specified
        self.schema = None
        self.prompt_path = prompt_path or str(DEFAULT_PROMPT_PATH)
        self.system_prompt = self._load_system_prompt()

    def _load_system_prompt(self):
        """Load system prompt from prompt.txt file"""
        try:
            with open(self.prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"System prompt file not found at: {self.prompt_path}")

    def get_connection(self):
        """Get a database connection"""
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def get_database_schema(self):
        """Get the database schema for the LLM"""
        if self.schema:
            return self.schema

        conn = self.get_connection()
        cursor = conn.cursor()

        schema_info = {
            'tables': {}
        }

        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        for table in tables:
            # Get column info
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()

            # Get sample data
            cursor.execute(f"SELECT * FROM {table} LIMIT 3")
            samples = cursor.fetchall()

            schema_info['tables'][table] = {
                'columns': [
                    {
                        'name': col[1],
                        'type': col[2],
                        'notnull': col[3],
                        'pk': col[5]
                    }
                    for col in columns
                ],
                'sample_data': samples
            }

        conn.close()
        self.schema = schema_info
        return schema_info

    def generate_sql_query(self, user_question, conversation_history=None):
        """Generate SQL query from natural language using LLM with conversation context"""
        # Use the system prompt loaded from prompt.txt
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]

        # Add conversation history for context (last 3 exchanges to keep token usage reasonable)
        if conversation_history:
            for msg in conversation_history[-6:]:  # Last 3 Q&A pairs (6 messages)
                messages.append(msg)

        # Add the current question
        messages.append({
            "role": "user",
            "content": f"""Question: {user_question}

CRITICAL REQUIREMENTS:
1. Return ONLY the SQL query - no explanations, no markdown, no comments
2. If the query returns colony data, you MUST include "Latitude, Longitude" in SELECT and GROUP BY clauses
3. Add "WHERE Latitude IS NOT NULL AND Longitude IS NOT NULL" for colony queries
4. Use exact column names: "ColonyName", "Latitude", "Longitude" (case-sensitive)

Generate the SQL query now:"""
        })

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1,
                max_tokens=500
            )

            sql_query = response.choices[0].message.content.strip()

            # Clean up the query (remove markdown formatting if present)
            if sql_query.startswith("```sql"):
                # Extract content between ```sql and ```
                sql_query = sql_query.split("```sql")[1].split("```")[0].strip()
            elif sql_query.startswith("```"):
                sql_query = sql_query.split("```")[1].split("```")[0].strip()

            # Remove any remaining explanatory text before SELECT/WITH/INSERT/UPDATE/DELETE
            # Find the first SQL keyword
            sql_keywords = ['SELECT', 'WITH', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER']
            for keyword in sql_keywords:
                if keyword in sql_query.upper():
                    idx = sql_query.upper().find(keyword)
                    sql_query = sql_query[idx:].strip()
                    break

            return sql_query

        except Exception as e:
            return f"ERROR: {e}"

    def execute_query(self, sql_query):
        """Execute SQL query and return results"""
        try:
            conn = self.get_connection()
            df = pd.read_sql_query(sql_query, conn)
            conn.close()

            # Return empty dataframe, not an error - let AI explain the empty result
            return df, None

        except Exception as e:
            return None, f"Query error: {e}"

    def generate_answer(self, user_question, sql_query, results_df, query_error=None, conversation_history=None):
        """Generate natural language answer from query results or explain query errors"""

        # Format results for LLM
        if query_error:
            results_text = f"QUERY ERROR: {query_error}"
            row_count = 0
        elif results_df is not None and len(results_df) > 0:
            results_text = results_df.to_string(index=False, max_rows=50)
            row_count = len(results_df)
        else:
            results_text = "No results found."
            row_count = 0

        system_prompt = """You are a helpful assistant that explains bird colony data query results.

IMPORTANT: You can see the conversation history, so use it to provide contextual answers. If the user asks follow-up questions like "List them" or "Show me more details", refer to the previous context to understand what they're asking about.

Your task is to:
1. Answer the user's question based on the SQL query results
2. Provide specific details from the data (names, numbers, etc.)
3. Highlight interesting patterns or insights
4. Use a conversational but informative tone
5. If there are no results, explain why that might be
6. If there's a query error, explain what went wrong in simple terms and suggest how to fix it

CRITICAL - VISUALIZATION DIRECTIVES (MANDATORY):
You MUST include visualization directives at the END of your response on separate lines.

IMPORTANT: Check the query results to determine what visualizations to show:

**Use LINE CHARTS for:**
- Time-series data with Year/Date columns showing TRENDS OVER TIME
- Data where the x-axis represents a continuous temporal progression
- Examples: yearly counts, monthly trends, population changes over years
- Requirements: Must have 3+ data points, x-axis must be chronological

**Use BAR CHARTS for:**
- Comparisons between categories (species, colonies, states, regions)
- Rankings or "top N" lists
- Categorical data where order doesn't represent time progression
- Examples: top 10 species, comparison by colony name, counts by state

**Use MAPS for:**
- ANY results with Latitude AND Longitude columns → ALWAYS add [SHOW_MAP: true]

**General Rules:**
- You can include BOTH chart and map directives if appropriate
- Only use [NO_VIZ] for errors, empty results, or purely informational queries
- When in doubt: time-based = line, categorical = bar

DIRECTIVE FORMAT (include these exact tags):
- [SHOW_CHART: line] - for time-series trends (Year/Date on x-axis)
- [SHOW_CHART: bar] - for categorical comparisons and rankings
- [SHOW_MAP: true] - when results have Latitude and Longitude columns
- [NO_VIZ] - only when truly no visualization is possible or useful

EXAMPLES:
- Query: "Brown pelican trends 2015-2021" → [SHOW_CHART: line]
- Query: "Top 10 species in 2021" → [SHOW_CHART: bar]
- Query: "Colonies in Louisiana" with lat/lon → [SHOW_MAP: true]
- Query: "Yearly counts by colony" with lat/lon → BOTH [SHOW_MAP: true] and [SHOW_CHART: line]
- Query: "Compare species diversity across colonies" → [SHOW_CHART: bar]

The visualization directives should be on the last line(s) of your response, after your explanation."""

        user_content = f"""Question: {user_question}

SQL Query Used:
{sql_query}

Query Results ({row_count} rows):
{results_text}

Please provide a clear, informative answer to the question based on these results."""

        messages = [
            {"role": "system", "content": system_prompt}
        ]

        # Add conversation history for context (last 3 exchanges)
        if conversation_history:
            for msg in conversation_history[-6:]:  # Last 3 Q&A pairs
                messages.append(msg)

        # Add current query info
        messages.append({"role": "user", "content": user_content})

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )

            answer = response.choices[0].message.content
            return answer

        except Exception as e:
            return f"Error generating answer: {e}"

    def generate_answer_stream(self, user_question, sql_query, results_df, query_error=None, conversation_history=None):
        """Generate natural language answer from query results with streaming or explain query errors"""

        # Format results for LLM
        if query_error:
            results_text = f"QUERY ERROR: {query_error}"
            row_count = 0
        elif results_df is not None and len(results_df) > 0:
            results_text = results_df.to_string(index=False, max_rows=50)
            row_count = len(results_df)
        else:
            results_text = "No results found."
            row_count = 0

        system_prompt = """You are a helpful assistant that explains bird colony data query results.

IMPORTANT: You can see the conversation history, so use it to provide contextual answers. If the user asks follow-up questions like "List them" or "Show me more details", refer to the previous context to understand what they're asking about.

Your task is to:
1. Answer the user's question based on the SQL query results
2. Provide specific details from the data (names, numbers, etc.)
3. Highlight interesting patterns or insights
4. Use a conversational but informative tone
5. If there are no results, explain why that might be
6. If there's a query error, explain what went wrong in simple terms and suggest how to fix it

CRITICAL - VISUALIZATION DIRECTIVES (MANDATORY):
You MUST include visualization directives at the END of your response on separate lines.

IMPORTANT: Check the query results to determine what visualizations to show:

**Use LINE CHARTS for:**
- Time-series data with Year/Date columns showing TRENDS OVER TIME
- Data where the x-axis represents a continuous temporal progression
- Examples: yearly counts, monthly trends, population changes over years
- Requirements: Must have 3+ data points, x-axis must be chronological

**Use BAR CHARTS for:**
- Comparisons between categories (species, colonies, states, regions)
- Rankings or "top N" lists
- Categorical data where order doesn't represent time progression
- Examples: top 10 species, comparison by colony name, counts by state

**Use MAPS for:**
- ANY results with Latitude AND Longitude columns → ALWAYS add [SHOW_MAP: true]

**General Rules:**
- You can include BOTH chart and map directives if appropriate
- Only use [NO_VIZ] for errors, empty results, or purely informational queries
- When in doubt: time-based = line, categorical = bar

DIRECTIVE FORMAT (include these exact tags):
- [SHOW_CHART: line] - for time-series trends (Year/Date on x-axis)
- [SHOW_CHART: bar] - for categorical comparisons and rankings
- [SHOW_MAP: true] - when results have Latitude and Longitude columns
- [NO_VIZ] - only when truly no visualization is possible or useful

EXAMPLES:
- Query: "Brown pelican trends 2015-2021" → [SHOW_CHART: line]
- Query: "Top 10 species in 2021" → [SHOW_CHART: bar]
- Query: "Colonies in Louisiana" with lat/lon → [SHOW_MAP: true]
- Query: "Yearly counts by colony" with lat/lon → BOTH [SHOW_MAP: true] and [SHOW_CHART: line]
- Query: "Compare species diversity across colonies" → [SHOW_CHART: bar]

The visualization directives should be on the last line(s) of your response, after your explanation."""

        user_content = f"""Question: {user_question}

SQL Query Used:
{sql_query}

Query Results ({row_count} rows):
{results_text}

Please provide a clear, informative answer to the question based on these results."""

        messages = [
            {"role": "system", "content": system_prompt}
        ]

        # Add conversation history for context (last 3 exchanges)
        if conversation_history:
            for msg in conversation_history[-6:]:  # Last 3 Q&A pairs
                messages.append(msg)

        # Add current query info
        messages.append({"role": "user", "content": user_content})

        try:
            stream = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000,
                stream=True
            )

            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            yield f"Error generating answer: {e}"

# Initialize chatbot and bird detector
chatbot = SQLChatbot()
try:
    bird_detector = BirdDetector()
    print("Bird detector initialized successfully!")
except Exception as e:
    print(f"Warning: Bird detector initialization failed: {e}")
    bird_detector = None

# API Endpoints
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Bird Colony SQL Chatbot API",
        "version": "1.0.0",
        "endpoints": {
            "/ask": "POST - Ask a question in natural language",
            "/schema": "GET - Get database schema",
            "/stats": "GET - Get database statistics",
            "/health": "GET - Health check"
        }
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    try:
        conn = chatbot.get_connection()
        conn.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")

@app.get("/schema", response_model=SchemaResponse)
async def get_schema():
    """Get database schema"""
    try:
        schema = chatbot.get_database_schema()
        return schema
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get database statistics"""
    try:
        conn = chatbot.get_connection()
        cursor = conn.cursor()

        # Total observations
        cursor.execute("SELECT COUNT(*) FROM observations")
        total_obs = cursor.fetchone()[0]

        # Year range
        cursor.execute("SELECT MIN(year), MAX(year) FROM observations")
        min_year, max_year = cursor.fetchone()

        # Total colonies
        cursor.execute("SELECT COUNT(DISTINCT colony_name) FROM observations WHERE colony_name != ''")
        total_colonies = cursor.fetchone()[0]

        # Total species
        cursor.execute("SELECT COUNT(*) FROM species")
        total_species = cursor.fetchone()[0]

        # States
        cursor.execute("SELECT DISTINCT state FROM observations WHERE state != '' ORDER BY state")
        states = [row[0] for row in cursor.fetchall()]

        # Observations by year
        cursor.execute("""
            SELECT year, COUNT(*) as count
            FROM observations
            GROUP BY year
            ORDER BY year
        """)
        obs_by_year = {str(int(year)): count for year, count in cursor.fetchall()}

        conn.close()

        return {
            "total_observations": total_obs,
            "year_range": f"{int(min_year)}-{int(max_year)}",
            "total_colonies": total_colonies,
            "total_species": total_species,
            "states": states,
            "observations_by_year": obs_by_year
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ask", response_model=QueryResponse)
async def ask_question(request: QuestionRequest):
    """
    Ask a question in natural language.
    The API will:
    1. Convert the question to SQL
    2. Execute the query
    3. Return results and a natural language answer
    """
    try:
        # Update model if provided, otherwise use default from env
        if request.model:
            chatbot.model = request.model

        # Step 1: Generate SQL query with conversation context
        sql_query = chatbot.generate_sql_query(request.question, conversation_history=request.conversation_history)

        if sql_query.startswith("ERROR"):
            return QueryResponse(
                sql_query=sql_query,
                results=None,
                results_count=0,
                answer="",
                error=sql_query
            )

        # Step 2: Execute query
        results_df, error = chatbot.execute_query(sql_query)

        # Convert dataframe to list of dicts (will be None if error occurred)
        results = results_df.to_dict(orient='records') if results_df is not None else None
        results_count = len(results_df) if results_df is not None else 0

        # Step 3: Generate natural language answer with conversation context (handles both success and error cases)
        answer = chatbot.generate_answer(request.question, sql_query, results_df, query_error=error, conversation_history=request.conversation_history)

        # Parse visualization directives (with automatic fallback detection)
        viz_directives = parse_visualization_directives(answer, results_df)

        return QueryResponse(
            sql_query=sql_query,
            results=results,
            results_count=results_count,
            answer=viz_directives['clean_answer'],
            error=error,  # Still include error for debugging, but answer will explain it
            show_chart=viz_directives['show_chart'],
            chart_type=viz_directives['chart_type'],
            show_map=viz_directives['show_map']
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ask/stream")
async def ask_question_stream(request: QuestionRequest):
    """
    Ask a question in natural language with streaming response.
    Returns a stream of Server-Sent Events (SSE)
    """
    async def event_generator():
        try:
            # Update model if provided, otherwise use default from env
            if request.model:
                chatbot.model = request.model

            # Step 1: Generate SQL query with conversation context
            sql_query = chatbot.generate_sql_query(request.question, conversation_history=request.conversation_history)

            if sql_query.startswith("ERROR"):
                yield f"data: {json.dumps({'type': 'error', 'content': sql_query})}\n\n"
                return

            # Step 2: Execute query
            results_df, error = chatbot.execute_query(sql_query)

            # Convert dataframe to list of dicts (will be None if error occurred)
            results = results_df.to_dict(orient='records') if results_df is not None else None
            results_count = len(results_df) if results_df is not None else 0

            # Send SQL query and results (or error info)
            yield f"data: {json.dumps({'type': 'sql_query', 'content': sql_query})}\n\n"
            yield f"data: {json.dumps({'type': 'results', 'content': results, 'count': results_count})}\n\n"

            if error:
                yield f"data: {json.dumps({'type': 'query_error', 'content': error})}\n\n"

            # Step 3: Stream the answer with conversation context (handles both success and error cases)
            yield f"data: {json.dumps({'type': 'answer_start'})}\n\n"

            full_answer = ""
            for chunk in chatbot.generate_answer_stream(request.question, sql_query, results_df, query_error=error, conversation_history=request.conversation_history):
                full_answer += chunk
                yield f"data: {json.dumps({'type': 'answer_chunk', 'content': chunk})}\n\n"
                await asyncio.sleep(0)  # Allow other tasks to run

            yield f"data: {json.dumps({'type': 'answer_end'})}\n\n"

            # Parse visualization directives (with automatic fallback detection)
            viz_directives = parse_visualization_directives(full_answer, results_df)
            yield f"data: {json.dumps({'type': 'visualization', 'show_chart': viz_directives['show_chart'], 'chart_type': viz_directives['chart_type'], 'show_map': viz_directives['show_map']})}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.get("/cv/examples", response_model=ExampleImagesResponse)
async def get_cv_examples():
    """Get list of example images for computer vision"""
    try:
        examples = get_example_images()
        return {"examples": examples}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/cv/inference", response_model=CVInferenceResponse)
async def run_cv_inference(
    file: UploadFile = File(...),
    conf_threshold: float = 0.25,
    fast_mode: bool = True
):
    """
    Run bird detection inference on an uploaded image

    Args:
        file: Uploaded image file
        conf_threshold: Confidence threshold for detections (default: 0.25)
        fast_mode: Enable fast mode for quicker processing of large images (default: True)
                   Fast mode uses downsampling for very large images or minimal overlap for sliding windows

    Returns:
        CVInferenceResponse: Detection results with annotated image
    """
    if bird_detector is None:
        raise HTTPException(
            status_code=503,
            detail="Computer vision model is not available"
        )

    try:
        # Read image bytes
        image_bytes = await file.read()

        # Run inference
        results = bird_detector.predict_from_bytes(image_bytes, conf_threshold, fast_mode=fast_mode)

        # Convert annotated image to base64
        _, buffer = cv2.imencode('.jpg', results['annotated_image'])
        image_base64 = base64.b64encode(buffer).decode('utf-8')

        # Create response message
        bird_count = results['bird_count']
        inference_time = results.get('inference_time', 0.0)

        if bird_count == 0:
            message = "No birds detected in the image. Try adjusting the confidence threshold or using a different image."
        elif bird_count == 1:
            message = f"Detected 1 bird in the image!"
        else:
            message = f"Detected {bird_count} birds in the image!"

        return {
            "bird_count": bird_count,
            "detections": results['detections'],
            "annotated_image_base64": image_base64,
            "message": message,
            "inference_time": inference_time
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference failed: {str(e)}")

@app.get("/cv/example/{filename}")
async def get_example_image(filename: str):
    """
    Get an example image by filename

    Args:
        filename: Name of the example image file

    Returns:
        Image file
    """
    try:
        from pathlib import Path
        images_dir = Path(__file__).parent / "cv_tools" / "images"
        image_path = images_dir / filename

        if not image_path.exists():
            raise HTTPException(status_code=404, detail="Image not found")

        # Read and return image
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        # Determine content type
        content_type = "image/jpeg"
        if filename.lower().endswith('.png'):
            content_type = "image/png"
        elif filename.lower().endswith('.webp'):
            content_type = "image/webp"

        return Response(content=image_bytes, media_type=content_type)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query/execute", response_model=CustomSQLResponse)
async def execute_custom_query(request: CustomSQLRequest):
    """
    Execute a custom SQL query provided by the user.

    Args:
        request: CustomSQLRequest with sql_query

    Returns:
        CustomSQLResponse with results or error
    """
    try:
        # Execute the query
        results_df, error = chatbot.execute_query(request.sql_query)

        if error:
            return CustomSQLResponse(
                success=False,
                results=None,
                results_count=0,
                error=error
            )

        # Convert results to list of dicts
        results = results_df.to_dict(orient='records') if results_df is not None else []
        results_count = len(results_df) if results_df is not None else 0

        return CustomSQLResponse(
            success=True,
            results=results,
            results_count=results_count,
            error=None
        )

    except Exception as e:
        return CustomSQLResponse(
            success=False,
            results=None,
            results_count=0,
            error=str(e)
        )

@app.post("/query/insights", response_model=InsightsResponse)
async def get_query_insights(request: InsightsRequest):
    """
    Get AI-powered insights on query results.

    Args:
        request: InsightsRequest with results data

    Returns:
        InsightsResponse with AI-generated insights
    """
    try:
        # Limit results to sample size
        results = request.results[:request.sample_size]

        if not results or len(results) == 0:
            return InsightsResponse(
                success=False,
                insights=None,
                error="No results to analyze"
            )

        # Convert to DataFrame for easier analysis
        df = pd.DataFrame(results)

        # Generate insights using LLM
        system_prompt = """You are a data analyst assistant specializing in bird colony survey data.
Your task is to analyze query results and provide valuable insights.

Provide:
1. **Summary**: Brief overview of what the data shows
2. **Key Findings**: 3-5 specific insights or interesting patterns
3. **Data Quality**: Any notable trends, outliers, or data characteristics
4. **Recommendations**: Suggestions for further analysis or questions to explore

Be concise, specific, and focus on actionable insights. Use bullet points for clarity."""

        # Format results for LLM
        results_summary = f"""
Dataset Overview:
- Rows: {len(df)}
- Columns: {', '.join(df.columns.tolist())}

Sample Data (first 10 rows):
{df.head(10).to_string(index=False)}

Column Statistics:
{df.describe(include='all').to_string()}
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Analyze these query results and provide insights:\n\n{results_summary}"}
        ]

        response = client.chat.completions.create(
            model=chatbot.model,
            messages=messages,
            temperature=0.7,
            max_tokens=800
        )

        insights = response.choices[0].message.content

        return InsightsResponse(
            success=True,
            insights=insights,
            error=None
        )

    except Exception as e:
        return InsightsResponse(
            success=False,
            insights=None,
            error=str(e)
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
