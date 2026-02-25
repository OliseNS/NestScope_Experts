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
import httpx
import yaml
from server.cv_tools.inference import BirdDetector, get_example_images
# Removed: No longer using dynamic prompt generators

# Load environment variables (for secrets like API keys)
load_dotenv()

# Load server configuration from YAML (for shared settings)
SERVER_DIR = Path(__file__).parent
CONFIG_PATH = SERVER_DIR / "config.yaml"

def load_config():
    """Load configuration from YAML file with .env overrides"""
    with open(CONFIG_PATH, 'r') as f:
        config = yaml.safe_load(f)

    # Allow .env to override model name for local development/testing
    if os.getenv("MODEL_NAME"):
        config['model']['name'] = os.getenv("MODEL_NAME")
        print(f"⚠️  MODEL_NAME override from .env: {config['model']['name']}")

    return config

# Load configuration
config = load_config()
print(f"✓ Loaded configuration from {CONFIG_PATH}")
print(f"✓ Using model: {config['model']['name']}")

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

class TableListResponse(BaseModel):
    tables: List[str]

class TableDataRequest(BaseModel):
    table_name: str
    page: int = 1
    page_size: int = 50

class TableDataResponse(BaseModel):
    success: bool
    data: Optional[List[Dict[str, Any]]]
    total_rows: int
    page: int
    page_size: int
    total_pages: int
    error: Optional[str] = None

class TableSchemaResponse(BaseModel):
    success: bool
    table_name: str
    columns: Optional[List[Dict[str, Any]]]
    error: Optional[str] = None

class RowUpdateRequest(BaseModel):
    table_name: str
    row_id: Dict[str, Any]  # Primary key column(s) and value(s)
    updates: Dict[str, Any]  # Columns to update

class RowUpdateResponse(BaseModel):
    success: bool
    message: Optional[str]
    error: Optional[str] = None

class RowDeleteRequest(BaseModel):
    table_name: str
    row_id: Dict[str, Any]  # Primary key column(s) and value(s)

class RowDeleteResponse(BaseModel):
    success: bool
    message: Optional[str]
    error: Optional[str] = None

class RowInsertRequest(BaseModel):
    table_name: str
    row_data: Dict[str, Any]  # Column names and values

class RowInsertResponse(BaseModel):
    success: bool
    message: Optional[str]
    error: Optional[str] = None

# Database configuration
# .env override takes priority, otherwise use config.yaml default
DB_PATH = os.getenv("DB_PATH", config['database']['default_path'])

# Model configuration - SINGLE SOURCE OF TRUTH
# Primary source: config.yaml (version controlled)
# Override: .env MODEL_NAME (for local testing only)
MODEL_NAME = config['model']['name']

# Get the directory where this file is located
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
        self.model = model or MODEL_NAME
        self.schema = None
        self.prompt_path = prompt_path or str(DEFAULT_PROMPT_PATH)
        self.system_prompt = self._load_system_prompt()
        self.metadata = self._load_metadata()

    def _load_system_prompt(self):
        """Load the focused system prompt from prompt.txt"""
        try:
            with open(self.prompt_path, 'r', encoding='utf-8') as f:
                prompt = f.read()
            print(f"✓ System prompt loaded from {self.prompt_path}")
            return prompt
        except FileNotFoundError:
            raise FileNotFoundError(f"System prompt file not found: {self.prompt_path}")

    def _load_metadata(self):
        """Load enhanced database metadata JSON"""
        metadata_path = SERVER_DIR.parent / "data" / "database_metadata_enhanced.json"
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            print(f"✓ Enhanced metadata loaded from {metadata_path}")
            return metadata
        except FileNotFoundError:
            print(f"⚠ Warning: Enhanced metadata not found at {metadata_path}")
            return None

    def get_connection(self, read_only=True):
        """
        Get a database connection.

        Args:
            read_only: If True, opens database in read-only mode (default: True for safety)

        Returns:
            sqlite3.Connection: Database connection
        """
        if read_only:
            # Open in read-only mode - prevents any write operations
            # URI format: file:path?mode=ro
            uri = f"file:{self.db_path}?mode=ro"
            return sqlite3.connect(uri, uri=True, check_same_thread=False)
        else:
            # Regular read-write connection (only for admin operations)
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

    def _format_metadata_context(self):
        """Format metadata as a compact context message"""
        if not self.metadata:
            return "No metadata available."

        context = "# DATABASE SCHEMA\n\n"

        # Add tables with columns
        tables = self.metadata.get('tables', {})
        for table_name, table_info in tables.items():
            rows = table_info.get('row_count', 0)
            columns = table_info.get('columns', [])

            context += f"## {table_name}\n"
            context += f"Rows: {rows:,}\n"

            # Show first 10 columns to keep it compact
            if columns:
                context += "Columns: "
                col_list = columns[:10] if len(columns) > 10 else columns
                context += ", ".join(f'"{c}"' for c in col_list)
                if len(columns) > 10:
                    context += f" ... ({len(columns)} total)"
                context += "\n"
            context += "\n"

        # Add relationships
        relationships = self.metadata.get('relationships', [])
        if relationships:
            context += "# RELATIONSHIPS\n"
            for rel in relationships:
                context += f"- {rel['from_table']}.{rel['from_column']} → {rel['to_table']}.{rel['to_column']} ({rel['type']})\n"
            context += "\n"

        return context

    def generate_sql_query(self, user_question, conversation_history=None):
        """Generate SQL query from natural language using LLM with conversation context"""
        # Build messages starting with system prompt
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]

        # Inject metadata as context (only once at the start)
        if self.metadata and not conversation_history:
            # Only add metadata for the first message to save tokens
            metadata_context = self._format_metadata_context()
            messages.append({"role": "system", "content": metadata_context})

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
                temperature=config['model']['sql_temperature'],
                max_tokens=config['model']['sql_max_tokens']
            )

            sql_query = response.choices[0].message.content.strip()

            # Clean up the query (remove markdown formatting if present)
            if sql_query.startswith("```sql"):
                # Extract content between ```sql and ```
                sql_query = sql_query.split("```sql")[1].split("```")[0].strip()
            elif sql_query.startswith("```"):
                sql_query = sql_query.split("```")[1].split("```")[0].strip()

            # Remove any remaining explanatory text before SELECT/WITH
            # SECURITY: Only look for read-only SQL keywords
            sql_keywords = ['SELECT', 'WITH']
            for keyword in sql_keywords:
                if keyword in sql_query.upper():
                    idx = sql_query.upper().find(keyword)
                    sql_query = sql_query[idx:].strip()
                    break

            return sql_query

        except Exception as e:
            return f"ERROR: {e}"

    def execute_query(self, sql_query):
        """
        Execute SQL query and return results.

        SECURITY: Only allows SELECT and WITH (CTE) statements.
        All other operations (INSERT, UPDATE, DELETE, DROP, etc.) are blocked.
        """
        try:
            # SECURITY: Validate that query is read-only
            query_upper = sql_query.strip().upper()

            # Remove comments and whitespace for validation
            import re
            query_clean = re.sub(r'--.*$', '', query_upper, flags=re.MULTILINE)  # Remove SQL comments
            query_clean = re.sub(r'/\*.*?\*/', '', query_clean, flags=re.DOTALL)  # Remove block comments
            query_clean = query_clean.strip()

            # Allow only SELECT and WITH (Common Table Expressions)
            allowed_keywords = ['SELECT', 'WITH']
            dangerous_keywords = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 'TRUNCATE', 'REPLACE', 'PRAGMA']

            # Check if query starts with an allowed keyword
            starts_with_allowed = any(query_clean.startswith(kw) for kw in allowed_keywords)

            # Check if query contains dangerous keywords
            contains_dangerous = any(kw in query_clean for kw in dangerous_keywords)

            if not starts_with_allowed or contains_dangerous:
                return None, (
                    "Security Error: Only SELECT queries are allowed. "
                    f"Detected prohibited operation. "
                    "NestChat is read-only to protect your data."
                )

            # Execute the validated query with read-only connection
            conn = self.get_connection(read_only=True)
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
                temperature=config['model']['temperature'],
                max_tokens=config['model']['max_tokens']
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
                temperature=config['model']['temperature'],
                max_tokens=config['model']['max_tokens'],
                stream=True
            )

            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            yield f"Error generating answer: {e}"

    def ask(self, question: str, conversation_history: list = None) -> dict:
        """
        Simplified synchronous method to ask a question and get complete results.
        This method is designed for the presentation generator and other modules
        that need a simple, one-shot query interface.

        Args:
            question: Natural language question
            conversation_history: Optional conversation history for context

        Returns:
            dict with keys: 'success', 'sql_query', 'results', 'answer', 'error'
        """
        try:
            # Step 1: Generate SQL query
            sql_query = self.generate_sql_query(question, conversation_history=conversation_history)

            if sql_query.startswith("ERROR"):
                return {
                    'success': False,
                    'sql_query': sql_query,
                    'results': None,
                    'answer': '',
                    'error': sql_query
                }

            # Step 2: Execute query
            results_df, error = self.execute_query(sql_query)

            # Step 3: Generate answer
            answer = self.generate_answer(
                question,
                sql_query,
                results_df,
                query_error=error,
                conversation_history=conversation_history
            )

            # Convert results to list of dicts if successful
            results = results_df.to_dict(orient='records') if results_df is not None else None

            return {
                'success': error is None,
                'sql_query': sql_query,
                'results': results,
                'answer': answer,
                'error': error
            }

        except Exception as e:
            return {
                'success': False,
                'sql_query': '',
                'results': None,
                'answer': '',
                'error': str(e)
            }

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
            "/health": "GET - Health check",
            "/config": "GET - Get server configuration"
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

@app.get("/config")
async def get_config():
    """
    Get server configuration (non-sensitive settings only).
    Frontend can use this to stay synchronized with backend settings.
    """
    return {
        "model": {
            "name": config['model']['name'],
            "temperature": config['model']['temperature'],
            "max_tokens": config['model']['max_tokens']
        },
        "cv": {
            "default_confidence": config['cv']['default_confidence'],
            "default_fast_mode": config['cv']['default_fast_mode']
        }
    }

@app.get("/services/status")
async def get_services_status():
    """
    Check the status of all NestScope services
    Returns the health status of:
    - FastAPI backend (port 8000)
    - Streamlit frontend (port 8501)
    - Flask Labeller (port 5000)
    """
    import httpx

    services = {
        "backend": {
            "name": "FastAPI Backend",
            "url": "http://localhost:8000/health",
            "status": "unknown",
            "port": 8000
        },
        "frontend": {
            "name": "Streamlit Frontend",
            "url": "http://localhost:8501",
            "status": "unknown",
            "port": 8501
        },
        "labeller": {
            "name": "Flask Labeller",
            "url": "http://localhost:5000",
            "status": "unknown",
            "port": 5000
        }
    }

    # Check each service with a short timeout
    async with httpx.AsyncClient(timeout=2.0) as client:
        for service_key, service_info in services.items():
            try:
                response = await client.get(service_info["url"])
                if response.status_code == 200:
                    services[service_key]["status"] = "running"
                else:
                    services[service_key]["status"] = "error"
            except (httpx.ConnectError, httpx.TimeoutException):
                services[service_key]["status"] = "offline"
            except Exception as e:
                services[service_key]["status"] = "error"
                services[service_key]["error"] = str(e)

    # Overall status
    all_running = all(s["status"] == "running" for s in services.values())

    return {
        "overall_status": "healthy" if all_running else "degraded",
        "services": services,
        "timestamp": pd.Timestamp.now().isoformat()
    }

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
            temperature=config['model']['temperature'],
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

# ============================================================================
# DATABASE BROWSER ENDPOINTS
# ============================================================================

@app.get("/db/tables", response_model=TableListResponse)
async def get_tables():
    """
    Get list of all tables in the database.

    Returns:
        TableListResponse with list of table names
    """
    try:
        conn = chatbot.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]

        conn.close()

        return TableListResponse(tables=tables)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/db/table/{table_name}", response_model=TableDataResponse)
async def get_table_data(table_name: str, page: int = 1, page_size: int = 50):
    """
    Get paginated data from a specific table.

    Args:
        table_name: Name of the table
        page: Page number (1-indexed)
        page_size: Number of rows per page

    Returns:
        TableDataResponse with paginated data
    """
    try:
        conn = chatbot.get_connection()
        cursor = conn.cursor()

        # Validate table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        if not cursor.fetchone():
            conn.close()
            return TableDataResponse(
                success=False,
                data=None,
                total_rows=0,
                page=page,
                page_size=page_size,
                total_pages=0,
                error=f"Table '{table_name}' not found"
            )

        # Get total row count
        # Escape table name with double quotes to handle special characters (hyphens, spaces)
        cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
        total_rows = cursor.fetchone()[0]

        # Calculate pagination
        total_pages = (total_rows + page_size - 1) // page_size
        offset = (page - 1) * page_size

        # Get paginated data
        query = f'SELECT * FROM "{table_name}" LIMIT ? OFFSET ?'
        df = pd.read_sql_query(query, conn, params=(page_size, offset))

        conn.close()

        # Convert DataFrame to list of dicts
        data = df.to_dict('records')

        return TableDataResponse(
            success=True,
            data=data,
            total_rows=total_rows,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            error=None
        )
    except Exception as e:
        return TableDataResponse(
            success=False,
            data=None,
            total_rows=0,
            page=page,
            page_size=page_size,
            total_pages=0,
            error=str(e)
        )

@app.get("/db/table/{table_name}/schema", response_model=TableSchemaResponse)
async def get_table_schema(table_name: str):
    """
    Get schema information for a specific table.

    Args:
        table_name: Name of the table

    Returns:
        TableSchemaResponse with column information
    """
    try:
        conn = chatbot.get_connection()
        cursor = conn.cursor()

        # Validate table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        if not cursor.fetchone():
            conn.close()
            return TableSchemaResponse(
                success=False,
                table_name=table_name,
                columns=None,
                error=f"Table '{table_name}' not found"
            )

        # Get column info
        # Escape table name with double quotes to handle special characters
        cursor.execute(f'PRAGMA table_info("{table_name}")')
        columns_raw = cursor.fetchall()

        columns = []
        for col in columns_raw:
            columns.append({
                'cid': col[0],
                'name': col[1],
                'type': col[2],
                'notnull': bool(col[3]),
                'default_value': col[4],
                'pk': bool(col[5])
            })

        conn.close()

        return TableSchemaResponse(
            success=True,
            table_name=table_name,
            columns=columns,
            error=None
        )
    except Exception as e:
        return TableSchemaResponse(
            success=False,
            table_name=table_name,
            columns=None,
            error=str(e)
        )

@app.put("/db/table/{table_name}/row", response_model=RowUpdateResponse)
async def update_table_row(table_name: str, request: RowUpdateRequest):
    """
    Update a row in a table.

    Args:
        table_name: Name of the table
        request: RowUpdateRequest with row_id and updates

    Returns:
        RowUpdateResponse with success status
    """
    try:
        # Use read_only=False for write operations (NestDB admin interface)
        conn = chatbot.get_connection(read_only=False)
        cursor = conn.cursor()

        # Build WHERE clause from row_id
        # Escape column names with double quotes to handle special characters
        where_parts = []
        where_values = []
        for col, val in request.row_id.items():
            where_parts.append(f'"{col}" = ?')
            where_values.append(val)
        where_clause = " AND ".join(where_parts)

        # Build UPDATE SET clause
        set_parts = []
        set_values = []
        for col, val in request.updates.items():
            set_parts.append(f'"{col}" = ?')
            set_values.append(val)
        set_clause = ", ".join(set_parts)

        # Execute update
        # Escape table name with double quotes to handle special characters
        query = f'UPDATE "{table_name}" SET {set_clause} WHERE {where_clause}'
        cursor.execute(query, set_values + where_values)
        conn.commit()

        rows_affected = cursor.rowcount
        conn.close()

        if rows_affected == 0:
            return RowUpdateResponse(
                success=False,
                message=None,
                error="No rows were updated. Row may not exist."
            )

        return RowUpdateResponse(
            success=True,
            message=f"Successfully updated {rows_affected} row(s)",
            error=None
        )
    except Exception as e:
        return RowUpdateResponse(
            success=False,
            message=None,
            error=str(e)
        )

@app.delete("/db/table/{table_name}/row", response_model=RowDeleteResponse)
async def delete_table_row(table_name: str, request: RowDeleteRequest):
    """
    Delete a row from a table.

    Args:
        table_name: Name of the table
        request: RowDeleteRequest with row_id

    Returns:
        RowDeleteResponse with success status
    """
    try:
        # Use read_only=False for write operations (NestDB admin interface)
        conn = chatbot.get_connection(read_only=False)
        cursor = conn.cursor()

        # Build WHERE clause from row_id
        # Escape column names with double quotes to handle special characters
        where_parts = []
        where_values = []
        for col, val in request.row_id.items():
            where_parts.append(f'"{col}" = ?')
            where_values.append(val)
        where_clause = " AND ".join(where_parts)

        # Execute delete
        # Escape table name with double quotes to handle special characters
        query = f'DELETE FROM "{table_name}" WHERE {where_clause}'
        cursor.execute(query, where_values)
        conn.commit()

        rows_affected = cursor.rowcount
        conn.close()

        if rows_affected == 0:
            return RowDeleteResponse(
                success=False,
                message=None,
                error="No rows were deleted. Row may not exist."
            )

        return RowDeleteResponse(
            success=True,
            message=f"Successfully deleted {rows_affected} row(s)",
            error=None
        )
    except Exception as e:
        return RowDeleteResponse(
            success=False,
            message=None,
            error=str(e)
        )

@app.post("/db/table/{table_name}/row", response_model=RowInsertResponse)
async def insert_table_row(table_name: str, request: RowInsertRequest):
    """
    Insert a new row into a table.

    Args:
        table_name: Name of the table
        request: RowInsertRequest with row_data

    Returns:
        RowInsertResponse with success status
    """
    try:
        # Use read_only=False for write operations (NestDB admin interface)
        conn = chatbot.get_connection(read_only=False)
        cursor = conn.cursor()

        # Build INSERT query
        # Escape column names and table name with double quotes to handle special characters
        columns = list(request.row_data.keys())
        values = list(request.row_data.values())
        placeholders = ", ".join(["?" for _ in values])
        columns_str = ", ".join([f'"{col}"' for col in columns])

        query = f'INSERT INTO "{table_name}" ({columns_str}) VALUES ({placeholders})'
        cursor.execute(query, values)
        conn.commit()

        rows_affected = cursor.rowcount
        conn.close()

        if rows_affected == 0:
            return RowInsertResponse(
                success=False,
                message=None,
                error="No rows were inserted."
            )

        return RowInsertResponse(
            success=True,
            message=f"Successfully inserted {rows_affected} row(s)",
            error=None
        )
    except Exception as e:
        return RowInsertResponse(
            success=False,
            message=None,
            error=str(e)
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
