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
from server.db_version import DatabaseVersionControl
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
    species_summary: Dict[str, int] = {}  # {group_name: count}
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
    version_commit: Optional[str] = None  # Git commit hash if versioning is active

class RowDeleteRequest(BaseModel):
    table_name: str
    row_id: Dict[str, Any]  # Primary key column(s) and value(s)

class RowDeleteResponse(BaseModel):
    success: bool
    message: Optional[str]
    error: Optional[str] = None
    version_commit: Optional[str] = None  # Git commit hash if versioning is active

class RowInsertRequest(BaseModel):
    table_name: str
    row_data: Dict[str, Any]  # Column names and values

class RowInsertResponse(BaseModel):
    success: bool
    message: Optional[str]
    error: Optional[str] = None
    version_commit: Optional[str] = None  # Git commit hash if versioning is active

# Version Control Response Models
class VersionCommit(BaseModel):
    """Represents a single Git commit in version history"""
    hash: str
    hash_short: str
    author: str
    date: str
    message: str

class VersionHistoryResponse(BaseModel):
    """Response for /db/version/history endpoint"""
    success: bool
    commits: Optional[List[VersionCommit]] = None
    error: Optional[str] = None

class VersionStatsResponse(BaseModel):
    """Response for /db/version/stats endpoint"""
    success: bool
    total_commits: Optional[int] = None
    first_commit_date: Optional[str] = None
    database_size_mb: Optional[float] = None
    snapshot_count: Optional[int] = None
    current_branch: Optional[str] = None
    error: Optional[str] = None

class VersionDiffResponse(BaseModel):
    """Response for /db/version/diff endpoint"""
    success: bool
    diff: Optional[str] = None
    error: Optional[str] = None

class VersionRollbackRequest(BaseModel):
    """Request for rollback operation"""
    commit_hash: str
    expert_email: Optional[str] = "system"

class VersionRollbackResponse(BaseModel):
    """Response for /db/version/rollback endpoint"""
    success: bool
    message: Optional[str] = None
    snapshot_path: Optional[str] = None
    new_commit: Optional[str] = None
    error: Optional[str] = None

# Database configuration
# .env override takes priority, otherwise use config.yaml default
DB_PATH = os.getenv("DB_PATH", config['database']['default_path'])

# Initialize Database Version Control
# This Git repo is SEPARATE from the project repo - it only versions the database
# Location: data/.git (for database versioning only)
# Project repo: /home/olisemeka.dev/Projects/nexus/.git (for code versioning)
try:
    db_version_control = DatabaseVersionControl(DB_PATH, expert_email="system")
    print(f"✓ Database version control initialized at {Path(DB_PATH).parent}")
except Exception as e:
    print(f"⚠️  Warning: Database version control initialization failed: {e}")
    db_version_control = None

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

class AgenticSQLChatbot(SQLChatbot):
    """
    Agentic chatbot with multi-step reasoning and self-correction.

    The agent follows these steps:
    1. Analyze the question - understand what's being asked
    2. Generate SQL - create a candidate query
    3. Self-validate SQL - check for common mistakes
    4. Execute query - run the SQL
    5. Validate results - check if results make sense
    6. Retry if needed - regenerate with feedback (configurable max attempts)

    Progress is streamed to the frontend in real-time.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Load agentic configuration from config.yaml
        self.max_attempts = config.get('agentic', {}).get('max_attempts', 3)
        self.validation_temperature = config.get('agentic', {}).get('validation_temperature', 0.1)
        self.analysis_temperature = config.get('agentic', {}).get('analysis_temperature', 0.3)

    async def agentic_ask_stream(self, question: str, conversation_history: list = None):
        """
        Process question with agentic reasoning and stream progress updates.

        Yields events:
        - thinking_start: Agent begins reasoning
        - thinking_step: Progress update with current step details
        - sql_generated: SQL query created
        - validation_start: Beginning validation
        - validation_result: Validation passed/failed with feedback
        - execution_start: Running query
        - results_check: Checking if results make sense
        - retry: Retrying with feedback
        - success: Final results ready
        - error: Critical error occurred
        """

        for attempt in range(1, self.max_attempts + 1):
            try:
                # Step 1: Analyze question
                if attempt == 1:
                    yield {
                        'type': 'thinking_step',
                        'step': 'analyze',
                        'attempt': attempt,
                        'content': "Reading your question and understanding what you need...",
                        'icon': '💭'
                    }
                else:
                    yield {
                        'type': 'thinking_step',
                        'step': 'analyze',
                        'attempt': attempt,
                        'content': f"I found an issue. Let me try a different approach... (Attempt {attempt}/{self.max_attempts})",
                        'icon': '🔄'
                    }

                analysis = await self._analyze_question(question, conversation_history)

                # Emit detailed analysis for transparency
                yield {
                    'type': 'question_analysis',
                    'attempt': attempt,
                    'content': analysis,
                    'icon': '🔍'
                }

                await asyncio.sleep(0.1)  # Small delay for UX

                # Step 2: Generate SQL
                yield {
                    'type': 'thinking_step',
                    'step': 'generate_sql',
                    'attempt': attempt,
                    'content': "Writing a database query to get this information...",
                    'icon': '✏️'
                }

                sql_query = self.generate_sql_query(question, conversation_history=conversation_history)

                if sql_query.startswith("ERROR"):
                    yield {'type': 'error', 'content': sql_query}
                    return

                yield {
                    'type': 'sql_generated',
                    'content': sql_query,
                    'attempt': attempt
                }

                await asyncio.sleep(0.1)

                # Step 3: Self-validate SQL
                yield {
                    'type': 'thinking_step',
                    'step': 'validate_sql',
                    'attempt': attempt,
                    'content': "Double-checking my query to make sure it's correct...",
                    'icon': '🔍'
                }

                validation = await self._validate_sql(sql_query, question, conversation_history)

                # Emit detailed validation reasoning
                yield {
                    'type': 'validation_result',
                    'is_valid': validation['is_valid'],
                    'feedback': validation['feedback'],
                    'reasoning': validation.get('reasoning', validation['feedback']),
                    'attempt': attempt
                }

                if not validation['is_valid']:
                    # SQL failed validation - retry with feedback
                    yield {
                        'type': 'retry',
                        'attempt': attempt,
                        'reason': validation['feedback'],
                        'content': f"Hmm, I spotted an issue: {validation['feedback']}. Let me rewrite this..."
                    }
                    # Add validation feedback to conversation for next attempt
                    if conversation_history is None:
                        conversation_history = []
                    conversation_history.append({
                        'role': 'system',
                        'content': f"Previous SQL had an issue: {validation['feedback']}. Please fix this in the next attempt."
                    })
                    continue  # Try again

                await asyncio.sleep(0.1)

                # Step 4: Execute query
                yield {
                    'type': 'thinking_step',
                    'step': 'execute',
                    'attempt': attempt,
                    'content': "Running the query on the database...",
                    'icon': '⚡'
                }

                results_df, error = self.execute_query(sql_query)

                if error:
                    # Query execution failed - retry with error feedback
                    yield {
                        'type': 'retry',
                        'attempt': attempt,
                        'reason': error,
                        'content': f"The query didn't work: {error}. Let me fix it..."
                    }
                    if conversation_history is None:
                        conversation_history = []
                    conversation_history.append({
                        'role': 'system',
                        'content': f"Previous query failed with error: {error}. Please fix this."
                    })
                    continue  # Try again

                results = results_df.to_dict(orient='records') if results_df is not None else None
                results_count = len(results_df) if results_df is not None else 0

                yield {
                    'type': 'results',
                    'content': results,
                    'count': results_count,
                    'attempt': attempt
                }

                await asyncio.sleep(0.1)

                # Step 5: Validate results
                yield {
                    'type': 'thinking_step',
                    'step': 'validate_results',
                    'attempt': attempt,
                    'content': "Verifying that these results make sense for your question...",
                    'icon': '🔬'
                }

                result_validation = await self._validate_results(question, sql_query, results_df, conversation_history)

                yield {
                    'type': 'results_validation',
                    'is_valid': result_validation['is_valid'],
                    'feedback': result_validation['feedback'],
                    'reasoning': result_validation.get('reasoning', result_validation['feedback']),
                    'attempt': attempt
                }

                if not result_validation['is_valid'] and attempt < self.max_attempts:
                    # Results look suspicious - retry with feedback
                    yield {
                        'type': 'retry',
                        'attempt': attempt,
                        'reason': result_validation['feedback'],
                        'content': f"Wait, something doesn't look right: {result_validation['feedback']}. Let me reconsider..."
                    }
                    if conversation_history is None:
                        conversation_history = []
                    conversation_history.append({
                        'role': 'system',
                        'content': f"Previous query returned suspicious results: {result_validation['feedback']}. Please revise the SQL."
                    })
                    continue  # Try again

                # Success! Generate final answer
                yield {
                    'type': 'thinking_step',
                    'step': 'generate_answer',
                    'attempt': attempt,
                    'content': "Perfect! Now let me explain what I found...",
                    'icon': '✨'
                }

                yield {'type': 'answer_start'}

                full_answer = ""
                for chunk in self.generate_answer_stream(question, sql_query, results_df, conversation_history=conversation_history):
                    full_answer += chunk
                    yield {'type': 'answer_chunk', 'content': chunk}
                    await asyncio.sleep(0)

                yield {'type': 'answer_end'}

                # Parse visualization directives
                viz_directives = parse_visualization_directives(full_answer, results_df)
                yield {
                    'type': 'visualization',
                    'show_chart': viz_directives['show_chart'],
                    'chart_type': viz_directives['chart_type'],
                    'show_map': viz_directives['show_map']
                }

                yield {
                    'type': 'success',
                    'attempts_used': attempt,
                    'content': 'Query completed successfully!'
                }

                yield {'type': 'done'}
                return

            except Exception as e:
                if attempt < self.max_attempts:
                    yield {
                        'type': 'retry',
                        'attempt': attempt,
                        'reason': str(e),
                        'content': f"Unexpected error: {str(e)}. Retrying..."
                    }
                    continue
                else:
                    yield {'type': 'error', 'content': f"Failed after {self.max_attempts} attempts: {str(e)}"}
                    return

        # If we get here, all attempts failed
        yield {'type': 'error', 'content': f"Failed to generate accurate results after {self.max_attempts} attempts. Please try rephrasing your question."}

    async def _analyze_question(self, question: str, conversation_history: list = None) -> dict:
        """Analyze the question to understand what's being asked."""

        messages = [
            {"role": "system", "content": """You are analyzing a natural language question about bird colony data.

Respond with ONLY a valid JSON object (no markdown, no extra text):

{
  "summary": "One sentence describing what the user wants",
  "question_type": "count, trend, comparison, or list",
  "tables_needed": ["tblColonyTotals2010-2021_MayJuneCombined"],
  "step_by_step_reasoning": [
    "Step 1: What is being asked",
    "Step 2: What table to use and why",
    "Step 3: What aggregation/filters needed",
    "Step 4: Any special considerations"
  ]
}

Keep it simple and focused. Example:

Question: "How many brown pelicans in Louisiana in 2021?"
{
  "summary": "Total brown pelican count in Louisiana for 2021",
  "question_type": "count",
  "tables_needed": ["tblColonyTotals2010-2021_MayJuneCombined"],
  "step_by_step_reasoning": [
    "User wants BIRD COUNTS, not photo records",
    "Use tblColonyTotals with pre-aggregated counts",
    "Filter by species code BRPE, State=LA, Year=2021",
    "Sum Birds column across all matching colonies"
  ]
}"""}
        ]

        if conversation_history:
            for msg in conversation_history[-4:]:
                messages.append(msg)

        messages.append({"role": "user", "content": f"Question: {question}"})

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.analysis_temperature,
                max_tokens=500  # Ensure JSON doesn't get truncated
            )

            analysis_text = response.choices[0].message.content.strip()

            # Remove markdown code blocks if present
            if analysis_text.startswith("```"):
                parts = analysis_text.split("```")
                if len(parts) >= 2:
                    analysis_text = parts[1]
                    if analysis_text.startswith("json"):
                        analysis_text = analysis_text[4:].strip()
                analysis_text = analysis_text.strip()

            # Try to parse as JSON
            try:
                analysis = json.loads(analysis_text)
                # Ensure step_by_step_reasoning exists and is properly formatted
                if 'step_by_step_reasoning' not in analysis:
                    analysis['step_by_step_reasoning'] = [analysis.get('summary', 'Analyzing question...')]
                elif not isinstance(analysis['step_by_step_reasoning'], list):
                    # If it's not a list, convert to list
                    analysis['step_by_step_reasoning'] = [str(analysis['step_by_step_reasoning'])]

                # Ensure all required fields exist
                analysis.setdefault('summary', 'Analyzing question...')
                analysis.setdefault('entities', {})
                analysis.setdefault('question_type', 'query')
                analysis.setdefault('tables_needed', [])
                analysis.setdefault('needs_coordinates', False)

            except json.JSONDecodeError as e:
                # JSON parsing failed - provide a simple fallback
                # Extract just the summary if possible
                import re
                summary_match = re.search(r'"summary":\s*"([^"]+)"', analysis_text)
                summary = summary_match.group(1) if summary_match else "Query bird count data by year"

                analysis = {
                    "summary": summary,
                    "entities": {},
                    "question_type": "query",
                    "tables_needed": ["tblColonyTotals2010-2021_MayJuneCombined"],
                    "needs_coordinates": False,
                    "step_by_step_reasoning": [
                        "Parsing the question to understand what data is needed",
                        "Identifying the correct table for bird count aggregation",
                        "Planning the SQL query structure"
                    ]
                }

            return analysis
        except Exception as e:
            return {
                "summary": "Could not analyze question",
                "entities": {},
                "question_type": "unknown",
                "tables_needed": [],
                "needs_coordinates": False,
                "step_by_step_reasoning": ["Error analyzing question"]
            }

    async def _validate_sql(self, sql_query: str, question: str, conversation_history: list = None) -> dict:
        """Self-validate the generated SQL query using LLM reasoning."""

        # Pure LLM validation - no hard-coded rules
        messages = [
            {"role": "system", "content": """You are a SQL validator for bird colony database queries.

🚨 ERROR #1 (MOST COMMON - CHECK FIRST):
**Using tblSpeciesData for bird/observation counts = WRONG!**

This is the MOST COMMON MISTAKE. Check IMMEDIATELY:

❌ WRONG (counts photo records, not birds):
- SELECT Year, COUNT(*) FROM tblSpeciesData GROUP BY Year
- Anything using tblSpeciesData for "how many birds/observations"

✅ CORRECT (counts actual birds):
- SELECT Year, SUM(Birds) FROM tblColonyTotals2010-2021_MayJuneCombined GROUP BY Year

RULE: If question asks about "how many birds/observations/nests/counts", MUST use:
- Table: tblColonyTotals2010-2021_MayJuneCombined
- Aggregation: SUM(Birds) or SUM(Nests), NOT COUNT(*)

Only use tblSpeciesData for questions about PHOTO METHODOLOGY, not bird counts!

OTHER ERRORS TO CHECK:
2. Using COUNT(*) when should use SUM(Birds) for bird totals
3. Missing Year filter when question specifies a year
4. Missing Latitude/Longitude for location questions

IMPORTANT: Respond with a JSON object:
{
  "is_valid": true/false,
  "feedback": "Brief issue description or 'Looks good'",
  "reasoning": "Concise validation (2-3 sentences max):
    - Table check: Correct table used?
    - Aggregation check: Correct method (SUM vs COUNT)?
    - Logic check: Query answers the question?"
}

Be STRICT but FAIR. Only mark invalid if there's a clear error."""}
        ]

        messages.append({
            "role": "user",
            "content": f"""Question: {question}

SQL Query:
{sql_query}

Validate (respond with JSON only):"""
        })

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.validation_temperature,
                max_tokens=200  # Concise validation reasoning
            )

            validation_text = response.choices[0].message.content.strip()

            # Remove markdown code blocks if present
            if validation_text.startswith("```"):
                validation_text = validation_text.split("```")[1]
                if validation_text.startswith("json"):
                    validation_text = validation_text[4:].strip()
                validation_text = validation_text.strip()

            try:
                validation = json.loads(validation_text)
                # Ensure required fields exist
                if 'is_valid' not in validation:
                    validation['is_valid'] = True
                if 'feedback' not in validation:
                    validation['feedback'] = "Looks good"
                if 'reasoning' not in validation:
                    validation['reasoning'] = validation.get('feedback', "Validation performed")
            except json.JSONDecodeError:
                # If JSON parsing fails, be lenient and assume valid
                # Only mark as invalid if we see clear negative indicators
                text_lower = validation_text.lower()
                if any(word in text_lower for word in ["invalid", "error", "wrong", "incorrect", "missing"]):
                    validation = {"is_valid": False, "feedback": validation_text[:100], "reasoning": validation_text}
                else:
                    validation = {"is_valid": True, "feedback": "Looks good", "reasoning": validation_text}

            return validation
        except Exception as e:
            # On error, assume valid and proceed
            return {"is_valid": True, "feedback": "Looks good", "reasoning": "Validation check performed"}

    async def _validate_results(self, question: str, sql_query: str, results_df, conversation_history: list = None) -> dict:
        """Validate if the results make sense for the question."""

        if results_df is None or len(results_df) == 0:
            return {"is_valid": True, "feedback": "No results to validate"}

        # Pure LLM validation - no hard-coded rules
        # Convert results to text summary for LLM validation
        results_summary = f"{len(results_df)} rows returned. "
        if len(results_df) > 0:
            # Show column names and sample values
            results_summary += f"Columns: {', '.join(results_df.columns[:5])}. "
            if len(results_df.columns) > 5:
                results_summary += f"({len(results_df.columns)} total columns). "

            # Show first row as sample
            first_row = results_df.iloc[0].to_dict()
            results_summary += f"Sample row: {first_row}"

        messages = [
            {"role": "system", "content": """You are validating query results for bird colony data.

🚨 CRITICAL CHECK:
**Are these BIRD COUNTS or PHOTO RECORD COUNTS?**

The ONLY red flags that indicate wrong results:
- If SQL uses tblSpeciesData for a bird count question → WRONG! (that's photo records)
- If SQL uses COUNT(*) instead of SUM(Birds) for bird counts → WRONG!

✅ CORRECT approaches:
- Using tblColonyTotals with SUM(Birds) → Correct for bird counts
- Using tblSpeciesData only for photo methodology questions → Correct

IMPORTANT: Respond with a JSON object:
{
  "is_valid": true/false,
  "feedback": "Brief issue description or 'Results look correct'",
  "reasoning": "Concise 1-2 sentence assessment:
    - Table/aggregation correct?
    - Columns match question?
    - Overall assessment"
}

ONLY mark as invalid if SQL used wrong table or wrong aggregation method. Different questions produce different result sizes - this is normal."""}
        ]

        messages.append({
            "role": "user",
            "content": f"""Question: {question}

SQL Query:
{sql_query}

Results Summary:
{results_summary}

Validate (respond with JSON, include reasoning):"""
        })

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.validation_temperature,
                max_tokens=200  # Concise validation reasoning
            )

            validation_text = response.choices[0].message.content.strip()

            # Remove markdown code blocks if present
            if validation_text.startswith("```"):
                validation_text = validation_text.split("```")[1]
                if validation_text.startswith("json"):
                    validation_text = validation_text[4:].strip()
                validation_text = validation_text.strip()

            try:
                validation = json.loads(validation_text)
                # Ensure required fields
                if 'is_valid' not in validation:
                    validation['is_valid'] = True
                if 'feedback' not in validation:
                    validation['feedback'] = "Results look correct"
                if 'reasoning' not in validation:
                    validation['reasoning'] = validation.get('feedback', "Results validation performed")
            except json.JSONDecodeError:
                # Default to valid
                validation = {"is_valid": True, "feedback": "Results appear reasonable", "reasoning": validation_text}

            return validation
        except Exception as e:
            # On error, assume valid
            return {"is_valid": True, "feedback": "Results look correct", "reasoning": "Results validation check performed"}


# Initialize chatbot and bird detector
chatbot = SQLChatbot()
agentic_chatbot = AgenticSQLChatbot()
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
            "/ask/stream": "POST - Ask with streaming response",
            "/ask/agentic/stream": "POST - Ask with agentic self-correction (recommended for accuracy)",
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

@app.get("/api/species")
async def get_all_species():
    """
    Get list of all species from the database
    Returns: List of species with code and name
    """
    try:
        conn = chatbot.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT SpeciesCode, SpeciesName
            FROM tblSpeciesCodes
            ORDER BY SpeciesName
        """)
        species = [{"code": row[0], "name": row[1]} for row in cursor.fetchall() if row[0] and row[1]]
        conn.close()
        return species
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load species: {str(e)}")

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

@app.post("/ask/agentic/stream")
async def ask_question_agentic_stream(request: QuestionRequest):
    """
    Ask a question with agentic self-correction and real-time progress updates.

    This endpoint uses multi-step reasoning:
    1. Analyze question
    2. Generate SQL
    3. Self-validate SQL
    4. Execute query
    5. Validate results
    6. Retry if needed (max 3 attempts)

    Returns a stream of Server-Sent Events (SSE) with progress updates.
    """
    async def event_generator():
        try:
            # Update model if provided
            if request.model:
                agentic_chatbot.model = request.model

            # Stream agentic reasoning process
            async for event in agentic_chatbot.agentic_ask_stream(
                request.question,
                conversation_history=request.conversation_history
            ):
                yield f"data: {json.dumps(event)}\n\n"
                await asyncio.sleep(0)  # Allow other tasks to run

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
    Run bird detection inference on an uploaded image with SAHI and model selection

    Args:
        file: Uploaded image file
        conf_threshold: Confidence threshold for detections (default: 0.25)
        fast_mode: Model selection mode (default: True)
                   - True (Fast): Swift model - optimized for speed, good for quick previews
                   - False (Max): Apex model - optimized for accuracy, better for final results
                   Both modes use SAHI (Slicing Aided Hyper Inference) for large images

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
            "species_summary": results.get('species_summary', {}),
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

# ============================================================================
# STAC DATA ENDPOINTS
# Proxy endpoints for The Water Institute's avian STAC catalog.
# All S3 data is cached 1 hour in stac_client to keep responses fast.
# ============================================================================

from server.stac_tools.stac_client import (
    get_colony_list, get_species_totals, get_colony_species_breakdown,
    get_colony_dots, build_mosaic_url, COLONIES, SPECIES_INFO
)

@app.get("/stac/summary")
async def stac_summary():
    """
    Returns complete STAC summary: colony metadata + species totals.
    Used by the NestMap page to populate the colony map and species charts.
    """
    try:
        return {
            "colonies": get_colony_list(),
            "species_totals": get_species_totals(),
            "species_info": SPECIES_INFO,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stac/colonies")
async def stac_colonies():
    """Returns list of all colonies with coordinates and species counts."""
    try:
        return {"colonies": get_colony_list()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stac/species/{colony_id}/{year}")
async def stac_species_breakdown(colony_id: str, year: str):
    """
    Returns species breakdown for a specific colony-year.
    Each item: {code, name, color, total_birds, total_nests}
    """
    try:
        breakdown = get_colony_species_breakdown(colony_id, year)
        return {"colony_id": colony_id, "year": year, "species": breakdown}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stac/dots/{colony_id}/{year}/{species_code}")
async def stac_dots(colony_id: str, year: str, species_code: str, dot_type: str = "Bird"):
    """
    Proxy for species dot GeoJSON from S3. Cached 1 hour.
    Returns a GeoJSON FeatureCollection with expert-annotated bird locations.
    """
    try:
        geojson = get_colony_dots(colony_id, year, species_code, dot_type)
        return geojson
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stac/mosaic_preview/{colony_id}/{year}")
async def stac_mosaic_preview(colony_id: str, year: str):
    """
    Returns a 512x512 JPEG preview of a COG mosaic via windowed read.
    Requires rasterio. Returns base64-encoded JPEG.
    """
    try:
        import io
        import numpy as np
        import base64 as b64
        from PIL import Image as PILImage

        cog_url = build_mosaic_url(colony_id, year)
        if not cog_url:
            raise HTTPException(status_code=404, detail=f"No mosaic for {colony_id}/{year}")

        try:
            import rasterio
            import rasterio.windows
        except ImportError:
            raise HTTPException(status_code=501, detail="rasterio not installed. Run: pip install rasterio")

        with rasterio.Env(GDAL_HTTP_UNSAFESSL="YES", GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
                          GDAL_HTTP_MERGE_CONSECUTIVE_RANGES="YES"):
            with rasterio.open(cog_url) as src:
                w, h = src.width, src.height
                cx, cy = w // 2, h // 2
                half = min(256, cx, cy)
                window = rasterio.windows.Window(cx - half, cy - half, half * 2, half * 2)
                # Read RGB bands (bands 1,2,3)
                num_bands = src.count
                bands_to_read = list(range(1, min(4, num_bands + 1)))
                data = src.read(bands_to_read, window=window, boundless=True, fill_value=0)

        # data shape: (bands, H, W) — take first 3 bands
        if data.shape[0] >= 3:
            rgb = np.transpose(data[:3], (1, 2, 0))
        elif data.shape[0] == 1:
            rgb = np.repeat(np.transpose(data, (1, 2, 0)), 3, axis=2)
        else:
            rgb = np.transpose(data, (1, 2, 0))

        img_pil = PILImage.fromarray(rgb.astype(np.uint8))
        # Resize to 512x512 for consistent display
        img_pil = img_pil.resize((512, 512), PILImage.LANCZOS)
        buf = io.BytesIO()
        img_pil.save(buf, format="JPEG", quality=80)
        preview_b64 = b64.b64encode(buf.getvalue()).decode()

        return {
            "colony_id": colony_id,
            "year": year,
            "mosaic_url": cog_url,
            "preview_base64": preview_b64,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Mosaic preview failed: {str(e)}")


@app.post("/cv/inference/mosaic")
async def cv_inference_on_mosaic(
    colony_id: str,
    year: str,
    conf: float = 0.25,
    fast_mode: bool = True,
):
    """
    Run NestVision bird detection on a 1024x1024 center tile of a COG mosaic.
    Useful for running inference directly on Water Institute survey mosaics.
    """
    if bird_detector is None:
        raise HTTPException(status_code=503, detail="CV model not loaded")

    try:
        import io
        import tempfile
        import numpy as np

        cog_url = build_mosaic_url(colony_id, year)
        if not cog_url:
            raise HTTPException(status_code=404, detail=f"No mosaic for {colony_id}/{year}")

        try:
            import rasterio
            import rasterio.windows
        except ImportError:
            raise HTTPException(status_code=501, detail="rasterio not installed")

        with rasterio.Env(GDAL_HTTP_UNSAFESSL="YES", GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"):
            with rasterio.open(cog_url) as src:
                w, h = src.width, src.height
                cx, cy = w // 2, h // 2
                half = 512  # 1024x1024 tile
                window = rasterio.windows.Window(
                    max(0, cx - half), max(0, cy - half),
                    min(half * 2, w), min(half * 2, h)
                )
                num_bands = src.count
                bands = list(range(1, min(4, num_bands + 1)))
                data = src.read(bands, window=window, boundless=True, fill_value=0)

        if data.shape[0] >= 3:
            rgb = np.transpose(data[:3], (1, 2, 0)).astype(np.uint8)
        elif data.shape[0] == 1:
            rgb = np.repeat(np.transpose(data, (1, 2, 0)), 3, axis=2).astype(np.uint8)
        else:
            rgb = np.transpose(data, (1, 2, 0)).astype(np.uint8)

        # Convert RGB → BGR for OpenCV/BirdDetector
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        img_bytes = cv2.imencode('.jpg', bgr)[1].tobytes()

        results = bird_detector.predict_from_bytes(img_bytes, conf_threshold=conf, fast_mode=fast_mode)

        annotated_bgr = results['annotated_image']
        _, buffer = cv2.imencode('.jpg', annotated_bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])
        image_base64 = base64.b64encode(buffer).decode('utf-8')

        bird_count = results['bird_count']
        return {
            "colony_id": colony_id,
            "year": year,
            "bird_count": bird_count,
            "detections": results['detections'],
            "species_summary": results.get('species_summary', {}),
            "annotated_image_base64": image_base64,
            "message": f"Detected {bird_count} bird{'s' if bird_count != 1 else ''} in {colony_id} {year} mosaic tile",
            "inference_time": results.get('inference_time', 0.0),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Mosaic inference failed: {str(e)}")


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

        # Auto-commit to version control
        commit_hash = None
        if db_version_control is not None:
            try:
                commit_result = db_version_control.commit(
                    message=f"Updated {rows_affected} row(s) in {table_name}",
                    details={
                        "operation": "UPDATE",
                        "table": table_name,
                        "rows_affected": rows_affected,
                        "columns_updated": list(request.updates.keys())
                    }
                )
                commit_hash = commit_result.get('commit_hash_short')
                print(f"✓ Database change committed to version control: {commit_hash}")
            except Exception as e:
                print(f"⚠️  Warning: Version control commit failed: {e}")

        return RowUpdateResponse(
            success=True,
            message=f"Successfully updated {rows_affected} row(s)",
            error=None,
            version_commit=commit_hash
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

        # Auto-commit to version control
        commit_hash = None
        if db_version_control is not None:
            try:
                commit_result = db_version_control.commit(
                    message=f"Deleted {rows_affected} row(s) from {table_name}",
                    details={
                        "operation": "DELETE",
                        "table": table_name,
                        "rows_affected": rows_affected
                    }
                )
                commit_hash = commit_result.get('commit_hash_short')
                print(f"✓ Database change committed to version control: {commit_hash}")
            except Exception as e:
                print(f"⚠️  Warning: Version control commit failed: {e}")

        return RowDeleteResponse(
            success=True,
            message=f"Successfully deleted {rows_affected} row(s)",
            error=None,
            version_commit=commit_hash
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

        # Auto-commit to version control
        commit_hash = None
        if db_version_control is not None:
            try:
                commit_result = db_version_control.commit(
                    message=f"Inserted {rows_affected} row(s) into {table_name}",
                    details={
                        "operation": "INSERT",
                        "table": table_name,
                        "rows_affected": rows_affected,
                        "columns": list(request.row_data.keys())
                    }
                )
                commit_hash = commit_result.get('commit_hash_short')
                print(f"✓ Database change committed to version control: {commit_hash}")
            except Exception as e:
                print(f"⚠️  Warning: Version control commit failed: {e}")

        return RowInsertResponse(
            success=True,
            message=f"Successfully inserted {rows_affected} row(s)",
            error=None,
            version_commit=commit_hash
        )
    except Exception as e:
        return RowInsertResponse(
            success=False,
            message=None,
            error=str(e)
        )

# ============================================================================
# DATABASE VERSION CONTROL ENDPOINTS
# ============================================================================

@app.get("/db/version/history", response_model=VersionHistoryResponse)
async def get_version_history(limit: int = 50):
    """
    Get commit history for the database.

    Shows all changes made to the database with timestamps and messages.
    This allows experts to see who changed what and when.

    Args:
        limit: Maximum number of commits to return (default: 50)

    Returns:
        List of commits with hash, author, date, message
    """
    if db_version_control is None:
        return VersionHistoryResponse(
            success=False,
            commits=None,
            error="Version control is not initialized"
        )

    try:
        commits = db_version_control.get_history(limit=limit)
        return VersionHistoryResponse(
            success=True,
            commits=[VersionCommit(**commit) for commit in commits],
            error=None
        )
    except Exception as e:
        return VersionHistoryResponse(
            success=False,
            commits=None,
            error=str(e)
        )

@app.get("/db/version/stats", response_model=VersionStatsResponse)
async def get_version_stats():
    """
    Get statistics about database version history.

    Returns:
        Total commits, date range, database size, etc.
    """
    if db_version_control is None:
        return VersionStatsResponse(
            success=False,
            total_commits=None,
            error="Version control is not initialized"
        )

    try:
        stats = db_version_control.get_stats()
        if stats.get("success"):
            return VersionStatsResponse(
                success=True,
                total_commits=stats.get("total_commits"),
                first_commit_date=stats.get("first_commit_date"),
                database_size_mb=stats.get("database_size_mb"),
                snapshot_count=stats.get("snapshot_count"),
                current_branch=stats.get("current_branch"),
                error=None
            )
        else:
            return VersionStatsResponse(
                success=False,
                error=stats.get("error", "Unknown error")
            )
    except Exception as e:
        return VersionStatsResponse(
            success=False,
            error=str(e)
        )

@app.get("/db/version/diff", response_model=VersionDiffResponse)
async def get_version_diff(commit_hash: Optional[str] = None):
    """
    Get diff showing what changed in a specific commit.

    Shows the actual SQL statements that were added/removed.

    Args:
        commit_hash: Hash of commit to diff (default: latest changes)

    Returns:
        Diff string with SQL changes
    """
    if db_version_control is None:
        return VersionDiffResponse(
            success=False,
            diff=None,
            error="Version control is not initialized"
        )

    try:
        diff = db_version_control.get_diff(commit_hash=commit_hash)
        return VersionDiffResponse(
            success=True,
            diff=diff,
            error=None
        )
    except Exception as e:
        return VersionDiffResponse(
            success=False,
            diff=None,
            error=str(e)
        )

@app.post("/db/version/rollback", response_model=VersionRollbackResponse)
async def rollback_database(request: VersionRollbackRequest):
    """
    Rollback database to a specific commit.

    **WARNING**: This is a destructive operation. It will:
    1. Create a safety snapshot
    2. Restore database to the specified commit
    3. Commit the rollback (preserving history)

    Args:
        request: VersionRollbackRequest with commit_hash and expert_email

    Returns:
        Success status, snapshot path, new commit hash
    """
    if db_version_control is None:
        return VersionRollbackResponse(
            success=False,
            error="Version control is not initialized"
        )

    try:
        # Update expert email if provided
        if request.expert_email:
            db_version_control.expert_email = request.expert_email

        result = db_version_control.rollback_to_commit(request.commit_hash)

        if result.get("success"):
            return VersionRollbackResponse(
                success=True,
                message=result.get("message"),
                snapshot_path=result.get("snapshot_path"),
                new_commit=result.get("new_commit"),
                error=None
            )
        else:
            return VersionRollbackResponse(
                success=False,
                error=result.get("error", "Unknown error")
            )
    except Exception as e:
        return VersionRollbackResponse(
            success=False,
            error=str(e)
        )

@app.post("/db/version/commit")
async def manual_commit(message: str, expert_email: str = "system"):
    """
    Manually create a version control commit.

    This is useful for checkpointing database state at key moments.
    Normally commits happen automatically after database writes.

    Args:
        message: Commit message
        expert_email: Email/username of expert making the commit

    Returns:
        Commit hash and timestamp
    """
    if db_version_control is None:
        return {
            "success": False,
            "error": "Version control is not initialized"
        }

    try:
        # Update expert email
        db_version_control.expert_email = expert_email

        result = db_version_control.commit(message)
        return result
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# ============================================================================
# EROSION & SPECIES RISK ENDPOINTS
# ============================================================================

from server.erosion_tools import (
    get_species_risk_summary,
    calculate_species_risk,
    get_erosion_risk_zones,
    get_shoreline_history,
    project_population,
    assess_colony_viability,
    calculate_restoration_priorities,
)
from server.erosion_tools.erosion_data import (
    get_sea_level_rise_projections,
    get_storm_tracks,
    get_colony_erosion_risk,
)
from server.erosion_tools.predictive_models import correlate_with_environmental_events

@app.get("/species/risk_assessment")
async def species_risk_assessment():
    """
    Get comprehensive species risk assessment for all Gulf Coast colonial nesters.

    Returns:
        {
            "species_assessments": List of species with risk scores and categories,
            "summary_stats": Count by risk category
        }
    """
    try:
        db_path = os.getenv("DB_PATH", "data/bird_data_complete.db")
        result = get_species_risk_summary(db_path)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/species/risk/{species_code}")
async def species_risk_detail(species_code: str):
    """
    Get detailed risk assessment for a specific species.

    Args:
        species_code: 4-letter species code (e.g., BRPE, ROSP)
    """
    try:
        db_path = os.getenv("DB_PATH", "data/bird_data_complete.db")
        result = calculate_species_risk(db_path, species_code.upper())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/species/population_projection/{species_code}")
async def population_projection(species_code: str, years_forward: int = 10, model: str = "linear"):
    """
    Project future population for a species based on historical trends.

    Args:
        species_code: 4-letter species code
        years_forward: Number of years to project (default: 10)
        model: "linear" or "exponential"
    """
    try:
        db_path = os.getenv("DB_PATH", "data/bird_data_complete.db")
        risk_data = calculate_species_risk(db_path, species_code.upper())
        population_history = risk_data.get("population_history", [])

        projection = project_population(population_history, years_forward, model)
        projection["species_code"] = species_code.upper()

        return projection
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/erosion/risk_zones")
async def erosion_risk_zones():
    """
    Get GeoJSON FeatureCollection of erosion risk zones across the Gulf Coast.

    Returns:
        GeoJSON with risk levels (EXTREME/HIGH/MEDIUM/LOW) and erosion rates
    """
    try:
        return get_erosion_risk_zones()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/erosion/shoreline_history")
async def shoreline_history():
    """
    Get historical shoreline positions (1850-2020) showing coastal erosion over time.

    Returns:
        GeoJSON FeatureCollection of shoreline LineStrings
    """
    try:
        return get_shoreline_history()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/erosion/slr_projections")
async def slr_projections(scenario: str = "2050_intermediate"):
    """
    Get sea level rise inundation projections for a given scenario.

    Args:
        scenario: One of 2030_intermediate, 2050_intermediate, 2070_intermediate, 2100_high

    Returns:
        GeoJSON FeatureCollection of inundation zones
    """
    try:
        return get_sea_level_rise_projections(scenario)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/erosion/storm_tracks")
async def storm_tracks(years: Optional[List[int]] = None):
    """
    Get major storm tracks that impacted Gulf Coast bird colonies (2005-2024).

    Args:
        years: Optional list of years to filter (e.g., [2005, 2021])

    Returns:
        GeoJSON FeatureCollection of storm tracks with impact descriptions
    """
    try:
        return get_storm_tracks(years)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/colonies/erosion_risk/{colony_id}")
async def colony_erosion_risk(colony_id: str):
    """
    Get erosion risk details for a specific colony.

    Args:
        colony_id: Colony identifier

    Returns:
        {
            "colony_id": str,
            "risk_score": float,
            "risk_level": str,
            "erosion_rate_m_per_year": float,
            "recommendation": str
        }
    """
    try:
        return get_colony_erosion_risk(colony_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/colonies/viability/{colony_id}")
async def colony_viability(
    colony_id: str,
    current_area_m2: float = 50000,
    minimum_viable_area_m2: float = 5000
):
    """
    Assess colony viability and predict years until critical threshold.

    Args:
        colony_id: Colony identifier
        current_area_m2: Current colony land area (default: 50000)
        minimum_viable_area_m2: Minimum area for viability (default: 5000)

    Returns:
        {
            "years_until_critical": int,
            "viability_2050": str,
            "recommendation": str
        }
    """
    try:
        erosion_info = get_colony_erosion_risk(colony_id)
        erosion_rate = erosion_info["erosion_rate_m_per_year"]

        result = assess_colony_viability(
            colony_id,
            erosion_rate,
            current_area_m2,
            minimum_viable_area_m2
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/restoration/priorities")
async def restoration_priorities():
    """
    Calculate restoration priority scores for all colonies.

    Returns:
        {
            "priority_map": GeoJSON with priority scores,
            "top_recommendations": Top 10 sites ranked by priority,
            "methodology": Description of scoring algorithm
        }
    """
    try:
        db_path = os.getenv("DB_PATH", "data/bird_data_complete.db")

        # Get species risk data
        species_risk_data = get_species_risk_summary(db_path)

        # Get erosion data
        erosion_data = get_erosion_risk_zones()

        # Calculate priorities
        result = calculate_restoration_priorities(db_path, species_risk_data, erosion_data)

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analysis/storm_impact/{species_code}")
async def storm_impact_analysis(species_code: str):
    """
    Analyze correlation between population changes and major storm events.

    Args:
        species_code: 4-letter species code

    Returns:
        {
            "storm_impact_detected": bool,
            "avg_decline_post_storm_pct": float,
            "recovery_time_years": int,
            "resilience_score": float
        }
    """
    try:
        db_path = os.getenv("DB_PATH", "data/bird_data_complete.db")

        # Get population history
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        query = """
        SELECT Year, SUM(BirdsTotal) as total_birds
        FROM [tblColonyTotals2010-2021_MayJuneCombined]
        WHERE SpeciesCode = ?
        GROUP BY Year
        ORDER BY Year
        """

        cursor.execute(query, (species_code.upper(),))
        population_data = [(row[0], row[1] or 0) for row in cursor.fetchall()]
        conn.close()

        # Major Gulf Coast storms
        storm_years = [2005, 2008, 2012, 2020, 2021]  # Katrina, Gustav, Isaac, Laura, Ida

        result = correlate_with_environmental_events(population_data, storm_years)
        result["species_code"] = species_code.upper()
        result["analyzed_storms"] = ["Katrina (2005)", "Isaac (2012)", "Ida (2021)"]

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
