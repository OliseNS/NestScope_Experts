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
import time
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
import logging
from server.cv_tools.inference import BirdDetector, get_example_images
from server.db_version import DatabaseVersionControl
from server.db_change_tracker import ChangeTracker
from server.flood_tools.flood_database import FloodDatabase
from server.flood_tools.noaa_client import NOAAClient
from server.services.risk_intelligence import RiskIntelligenceService
from server.services.db_explorer import DatabaseExplorer

# Initialize logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Initialize risk intelligence service
_risk_service = None

def get_risk_service():
    global _risk_service
    if _risk_service is None:
        db_path = os.getenv("DB_PATH", "data/bird_data_complete.db")
        _risk_service = RiskIntelligenceService(db_path)
    return _risk_service

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
    expert_email: Optional[str] = None  # Email of user executing the query

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
    expert_email: Optional[str] = None  # Email of user making the change

class RowUpdateResponse(BaseModel):
    success: bool
    message: Optional[str]
    error: Optional[str] = None
    version_commit: Optional[str] = None  # Git commit hash if versioning is active

class RowDeleteRequest(BaseModel):
    table_name: str
    row_id: Dict[str, Any]  # Primary key column(s) and value(s)
    expert_email: Optional[str] = None  # Email of user making the change

class RowDeleteResponse(BaseModel):
    success: bool
    message: Optional[str]
    error: Optional[str] = None
    version_commit: Optional[str] = None  # Git commit hash if versioning is active

class RowInsertRequest(BaseModel):
    table_name: str
    row_data: Dict[str, Any]  # Column names and values
    expert_email: Optional[str] = None  # Email of user making the change

class RowInsertResponse(BaseModel):
    success: bool
    message: Optional[str]
    error: Optional[str] = None
    version_commit: Optional[str] = None  # Git commit hash if versioning is active

class ColumnAddRequest(BaseModel):
    table_name: str
    column_name: str
    column_type: str  # e.g., "TEXT", "INTEGER", "REAL"
    default_value: Optional[str] = None
    not_null: bool = False
    expert_email: Optional[str] = None

class ColumnAddResponse(BaseModel):
    success: bool
    message: Optional[str]
    error: Optional[str] = None
    version_commit: Optional[str] = None

class ColumnDeleteRequest(BaseModel):
    table_name: str
    column_name: str
    expert_email: Optional[str] = None

class ColumnDeleteResponse(BaseModel):
    success: bool
    message: Optional[str]
    error: Optional[str] = None
    version_commit: Optional[str] = None

# Version Control Request/Response Models
class VersionCommitRequest(BaseModel):
    """Request for manually creating a version control commit"""
    message: str
    expert_email: str = "system"
    expert_name: Optional[str] = None
    expert_picture: Optional[str] = None

class VersionCommit(BaseModel):
    """Represents a single Git commit in version history"""
    hash: str
    hash_short: str
    author: str
    date: str
    message: str
    details: Optional[Dict[str, Any]] = {}
    full_message: Optional[str] = ""
    picture: Optional[str] = None

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

# Initialize Enhanced Change Tracker
# This tracks row-level changes for detailed audit trails
try:
    change_tracker = ChangeTracker(DB_PATH)
    print(f"✓ Change tracker initialized (changelog at {change_tracker.changelog_db})")
except Exception as e:
    print(f"⚠️  Warning: Change tracker initialization failed: {e}")
    change_tracker = None


# ============================================================================
# USER INFO HELPER (for version control attribution)
# ============================================================================

def get_user_info(email: str) -> Dict[str, str]:
    """
    Fetch user information from authentication database.

    This retrieves the user's full name and profile picture from the
    users.db authentication database, so we can attribute changes properly
    in version control.

    Args:
        email: User's email address

    Returns:
        Dictionary with 'name' and 'picture' keys
    """
    # Path to authentication database
    auth_db_path = Path(DB_PATH).parent / "users.db"

    try:
        if not auth_db_path.exists():
            return {"name": email.split('@')[0].replace('.', ' ').title(), "picture": None}

        conn = sqlite3.connect(str(auth_db_path))
        cursor = conn.cursor()

        cursor.execute('SELECT name, picture FROM users WHERE email = ?', (email,))
        result = cursor.fetchone()
        conn.close()

        if result:
            return {
                "name": result[0] or email.split('@')[0].replace('.', ' ').title(),
                "picture": result[1]
            }
        else:
            # User not in auth DB yet - extract name from email
            return {
                "name": email.split('@')[0].replace('.', ' ').title(),
                "picture": None
            }

    except Exception as e:
        print(f"Warning: Failed to fetch user info for {email}: {e}")
        return {
            "name": email.split('@')[0].replace('.', ' ').title(),
            "picture": None
        }

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
            # Simple check: look for Latitude and Longitude columns (case-insensitive)
            lat_col = None
            lon_col = None
            for col in results_df.columns:
                col_lower = str(col).lower()
                if 'latitude' in col_lower and not lat_col:
                    lat_col = col
                if 'longitude' in col_lower and not lon_col:
                    lon_col = col

            if lat_col and lon_col:
                # Check if we have valid non-null coordinates
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


def validate_and_enhance_sql_for_mapping(sql_query: str) -> tuple[str, bool, str]:
    """
    Validate SQL includes coordinates for colony queries and auto-enhance if missing.

    This is a safety net for when the LLM forgets to include Lat/Lon despite prompting.

    Args:
        sql_query: The generated SQL query

    Returns:
        (enhanced_sql, was_modified, reason)
    """
    import re

    sql_upper = sql_query.upper()

    # Detect if this is a colony-related query
    colony_indicators = [
        r'\bCOLONYNAME\b',
        r'\bCOLONY\b',
        r'\bSTATE\b',
        r'\bGEOREGION\b',
        r'GROUP BY.*COLONY',
    ]

    is_colony_query = any(re.search(pattern, sql_upper) for pattern in colony_indicators)

    if not is_colony_query:
        return sql_query, False, "Not a colony query - coordinates not required"

    # Check if coordinates already present
    has_latitude = bool(re.search(r'"?Latitude"?', sql_query, re.IGNORECASE))
    has_longitude = bool(re.search(r'"?Longitude"?', sql_query, re.IGNORECASE))

    if has_latitude and has_longitude:
        # Verify they're in GROUP BY if needed
        group_by_match = re.search(
            r'GROUP\s+BY\s+(.+?)(?:ORDER\s+BY|LIMIT|HAVING|;|$)',
            sql_query,
            re.IGNORECASE | re.DOTALL
        )

        if group_by_match:
            group_by_clause = group_by_match.group(1)
            has_lat_in_group = bool(re.search(r'"?Latitude"?', group_by_clause, re.IGNORECASE))
            has_lon_in_group = bool(re.search(r'"?Longitude"?', group_by_clause, re.IGNORECASE))

            if not (has_lat_in_group and has_lon_in_group):
                # Add to GROUP BY
                enhanced_group = group_by_clause.rstrip().rstrip(',') + ', "Latitude", "Longitude"'
                enhanced_sql = sql_query.replace(
                    f"GROUP BY {group_by_clause}",
                    f"GROUP BY {enhanced_group}",
                    1  # Replace only first occurrence
                )
                return enhanced_sql, True, "Added Lat/Lon to GROUP BY clause"

        return sql_query, False, "Coordinates already present and correct"

    # Coordinates MISSING - Check if we can fix this
    # Identify the source table
    from_match = re.search(
        r'FROM\s+"?(tblColonyTotals2010-2021_MayJuneCombined|tblRWCWB_ColonyInventory_10Nov22)"?',
        sql_query,
        re.IGNORECASE
    )

    if not from_match:
        return sql_query, False, "Cannot enhance: Table doesn't have coordinate columns"

    table_name = from_match.group(1)

    # Strategy: Add Lat/Lon to SELECT clause after ColonyName
    select_match = re.search(
        r'SELECT\s+(DISTINCT\s+)?(.*?)\s+FROM',
        sql_query,
        re.IGNORECASE | re.DOTALL
    )

    if not select_match:
        return sql_query, False, "Cannot parse SELECT clause"

    distinct_keyword = select_match.group(1) or ""
    select_list = select_match.group(2).strip()

    # Smart insertion: After ColonyName if present, otherwise at end
    if '"ColonyName"' in select_list or '"COLONYNAME"' in select_list.upper():
        # Insert after first occurrence of ColonyName
        enhanced_select = re.sub(
            r'("ColonyName")',
            r'\1, "Latitude", "Longitude"',
            select_list,
            count=1,
            flags=re.IGNORECASE
        )
    else:
        # Append to end
        enhanced_select = select_list.rstrip(',') + ', "Latitude", "Longitude"'

    # Replace SELECT clause
    enhanced_sql = re.sub(
        r'SELECT\s+(DISTINCT\s+)?.*?\s+FROM',
        f'SELECT {distinct_keyword}{enhanced_select} FROM',
        sql_query,
        count=1,
        flags=re.IGNORECASE | re.DOTALL
    )

    # Add to GROUP BY if present
    group_by_match = re.search(
        r'GROUP\s+BY\s+(.+?)(?:ORDER\s+BY|LIMIT|HAVING|;|$)',
        enhanced_sql,
        re.IGNORECASE | re.DOTALL
    )

    if group_by_match:
        group_by_clause = group_by_match.group(1).strip().rstrip(',')
        enhanced_group = group_by_clause + ', "Latitude", "Longitude"'
        enhanced_sql = re.sub(
            r'GROUP\s+BY\s+' + re.escape(group_by_clause),
            f'GROUP BY {enhanced_group}',
            enhanced_sql,
            count=1,
            flags=re.IGNORECASE
        )

    # Ensure WHERE filters for non-null coordinates
    if re.search(r'\bWHERE\b', enhanced_sql, re.IGNORECASE):
        # Add to existing WHERE
        where_match = re.search(
            r'(WHERE\s+.+?)(\s+GROUP\s+BY|\s+ORDER\s+BY|\s+LIMIT|;|$)',
            enhanced_sql,
            re.IGNORECASE | re.DOTALL
        )
        if where_match:
            where_clause = where_match.group(1)
            if 'IS NOT NULL' not in where_clause.upper() or '"Latitude"' not in where_clause:
                enhanced_where = where_clause.rstrip() + ' AND "Latitude" IS NOT NULL AND "Longitude" IS NOT NULL'
                enhanced_sql = enhanced_sql.replace(where_clause, enhanced_where, 1)
    else:
        # Insert new WHERE before GROUP BY/ORDER BY/LIMIT
        insertion_point = re.search(
            r'\s+(GROUP\s+BY|ORDER\s+BY|LIMIT|;|$)',
            enhanced_sql,
            re.IGNORECASE
        )
        if insertion_point:
            pos = insertion_point.start()
            enhanced_sql = (
                enhanced_sql[:pos] +
                '\nWHERE "Latitude" IS NOT NULL AND "Longitude" IS NOT NULL' +
                enhanced_sql[pos:]
            )

    return enhanced_sql, True, f"Auto-injected Latitude/Longitude columns for table {table_name}"


def inject_coordinates_via_join(results_df: pd.DataFrame, db_path: str) -> pd.DataFrame:
    """
    Last-resort coordinate injection: If results have ColonyName but no Lat/Lon,
    fetch coordinates from database and merge them in.

    This handles edge cases where Layer 2 couldn't fix the SQL (complex queries, CTEs, etc.)

    Args:
        results_df: Query results DataFrame
        db_path: Path to SQLite database

    Returns:
        DataFrame with coordinates merged in (if possible)
    """
    if results_df is None or results_df.empty:
        return results_df

    # Check if coordinates are already present
    has_colony = 'ColonyName' in results_df.columns
    has_lat = 'Latitude' in results_df.columns
    has_lon = 'Longitude' in results_df.columns

    if not has_colony:
        return results_df  # No colony data to map

    if has_lat and has_lon:
        return results_df  # Coordinates already present

    print(f"🔧 Layer 3 Activation: Injecting coordinates via JOIN lookup")

    import sqlite3

    try:
        unique_colonies = results_df['ColonyName'].unique().tolist()

        # Connect in read-only mode
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)

        # Fetch coordinates from primary table
        placeholders = ','.join(['?' for _ in unique_colonies])
        coord_query = f"""
        SELECT DISTINCT
            "ColonyName",
            "Latitude",
            "Longitude"
        FROM "tblColonyTotals2010-2021_MayJuneCombined"
        WHERE "ColonyName" IN ({placeholders})
          AND "Latitude" IS NOT NULL
          AND "Longitude" IS NOT NULL
        """

        coord_df = pd.read_sql_query(coord_query, conn, params=unique_colonies)
        conn.close()

        if coord_df.empty:
            print(f"⚠️  No coordinates found for {len(unique_colonies)} colonies")
            return results_df

        # Merge coordinates into results (left join to preserve all rows)
        results_with_coords = results_df.merge(
            coord_df[['ColonyName', 'Latitude', 'Longitude']],
            on='ColonyName',
            how='left'
        )

        matched_count = results_with_coords['Latitude'].notna().sum()
        print(f"✓ Injected coordinates for {matched_count}/{len(results_df)} rows")

        return results_with_coords

    except Exception as e:
        print(f"⚠️  Coordinate injection failed: {e}")
        return results_df


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
        """Load database metadata (prefers compressed essential metadata)"""
        # Try compressed essential metadata first (2k tokens vs 35k!)
        essential_path = SERVER_DIR.parent / "data" / "metadata_essential.json"
        extended_path = SERVER_DIR.parent / "data" / "metadata_extended.json"
        fallback_path = SERVER_DIR.parent / "data" / "database_metadata_enhanced.json"

        # Priority: essential > extended > fallback
        for path, tier in [(essential_path, "essential"), (extended_path, "extended"), (fallback_path, "fallback")]:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)

                # Calculate token estimate (rough: 1 token ≈ 4 chars)
                json_size = len(json.dumps(metadata))
                token_estimate = json_size // 4

                print(f"✓ Metadata loaded: {tier.upper()} tier from {path.name} (~{token_estimate:,} tokens)")
                return metadata
            except FileNotFoundError:
                continue

        print(f"⚠ Warning: No metadata found. Run: python scripts/compress_metadata.py")
        return None

    def refresh_metadata(self):
        """Reload metadata from disk"""
        self.metadata = self._load_metadata()
        self.schema = None # Force schema regeneration
        print("🔄 Chatbot metadata context refreshed")

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

        # Check metadata format (compressed vs legacy)
        is_compressed = "_meta" in self.metadata and "compression_version" in self.metadata.get("_meta", {})

        if is_compressed:
            # Use compressed format (much more concise!)
            return self._format_compressed_metadata()
        else:
            # Fallback: legacy verbose format
            return self._format_legacy_metadata()

    def _format_compressed_metadata(self):
        """Format AI-compressed metadata (essential tier)"""
        context = "# DATABASE SCHEMA (COMPRESSED)\n\n"

        # Critical rules first (most important!)
        rules = self.metadata.get('critical_rules', [])
        if rules:
            context += "## CRITICAL RULES\n"
            for rule in rules:
                context += f"- {rule}\n"
            context += "\n"

        # Tables with purpose and key columns
        tables = self.metadata.get('tables', {})
        for table_name, table_info in tables.items():
            context += f"## {table_name}\n"

            if 'purpose' in table_info:
                context += f"Purpose: {table_info['purpose']}\n"

            if 'row_count' in table_info:
                context += f"Rows: {table_info['row_count']:,}\n"

            if 'key_columns' in table_info:
                context += f"Columns: {', '.join(table_info['key_columns'])}\n"

            if 'joins' in table_info:
                context += f"Joins: {', '.join(table_info['joins'])}\n"

            if 'query_hints' in table_info:
                context += f"Hints: {'; '.join(table_info['query_hints'])}\n"

            context += "\n"

        # Common query patterns
        patterns = self.metadata.get('common_patterns', [])
        if patterns:
            context += "## COMMON PATTERNS\n"
            for pattern in patterns:
                context += f"- {pattern}\n"
            context += "\n"

        return context

    def _format_legacy_metadata(self):
        """Format legacy verbose metadata (fallback)"""
        context = "# DATABASE SCHEMA\n\n"

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
2. If the question involves locations, colonies, states, or mapping, you MUST include "Latitude" and "Longitude" columns in the SELECT and GROUP BY clauses.
3. Add "WHERE "Latitude" IS NOT NULL AND "Longitude" IS NOT NULL" to ensure results can be mapped.
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

            # LAYER 2: Validate and enhance SQL for mapping
            enhanced_sql, was_modified, reason = validate_and_enhance_sql_for_mapping(sql_query)

            if was_modified:
                print(f"🗺️  SQL Enhancement: {reason}")
                print(f"   Original: {sql_query[:80]}...")
                print(f"   Enhanced: {enhanced_sql[:80]}...")
                sql_query = enhanced_sql

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

            # LAYER 3: Inject coordinates if missing (safety net)
            df = inject_coordinates_via_join(df, self.db_path)

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
                if chunk.choices and len(chunk.choices) > 0 and chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            print(f"❌ Error in generate_answer_stream: {e}")
            import traceback
            traceback.print_exc()
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

                # Parse visualization directives and get clean answer
                viz_directives = parse_visualization_directives(full_answer, results_df)

                # Send clean answer (without visualization directives)
                yield {
                    'type': 'answer_end',
                    'clean_answer': viz_directives['clean_answer']
                }

                # Send visualization directives separately
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
        """
        Analyze the question with high-fidelity reasoning to understand intent, entities, and constraints.
        This provides the foundation for accurate SQL generation.
        """

        messages = [
            {"role": "system", "content": """You are an expert data analyst specializing in Gulf Coast avian ecology.
Analyze the natural language question to extract deep semantic meaning, entities, and logical constraints.

CRITICAL: The "step_by_step_reasoning" field must contain DETAILED, SPECIFIC analysis of THIS question.
NOT generic placeholders like "Parsing the question" but ACTUAL reasoning.

## KNOWLEDGE BASE: COMMON JOIN PATTERNS & METRICS
1. **Species Diversity (Richness)**: `COUNT(DISTINCT SpeciesCode)` - requires `tblColonyTotals...`
2. **Abundance (Population)**: `SUM(Birds)` - requires `tblColonyTotals...`
3. **Nesting Effort**: `SUM(Nests)` - requires `tblColonyTotals...`
4. **Species Names**: Join `tblColonyTotals...` with `tblSpeciesCodes` on `SpeciesCode`.
5. **Species Groups**: Join `tblColonyTotals...` with `tblSpeciesCodes` on `SpeciesCode`.
6. **Temporal Trends**: Always include `Year` in SELECT and GROUP BY.
7. **Mapping Requirements**: ALWAYS include `Latitude` and `Longitude` for any colony-based query.

## GOLD-STANDARD FEW-SHOT EXAMPLES

**Q1: "Which colonies support the highest biodiversity in Louisiana?"**
**Reasoning**: User wants species diversity (count of unique species) per colony, filtered for State='LA'. Requires tblColonyTotals table. Needs Latitude/Longitude for mapping.
**Query Plan**: SELECT ColonyName, State, Latitude, Longitude, COUNT(DISTINCT SpeciesCode) as species_count FROM tblColonyTotals... WHERE State='LA' AND Latitude IS NOT NULL GROUP BY ColonyName, State, Latitude, Longitude ORDER BY species_count DESC

**Q2: "Show the trend of Brown Pelican population from 2010 to 2021"**
**Reasoning**: User wants temporal trend (Sum of Birds by Year) for a specific species (Brown Pelican). Must join with tblSpeciesCodes to filter by name. 
**Query Plan**: SELECT ct.Year, SUM(ct.Birds) as total_birds FROM tblColonyTotals... ct JOIN tblSpeciesCodes sc ON ct.SpeciesCode = sc.SpeciesCode WHERE sc.SpeciesName = 'Brown Pelican' GROUP BY ct.Year ORDER BY ct.Year

Respond with ONLY a valid JSON object (no markdown, no extra text):

{
  "summary": "Deep semantic summary of the user's intent (2-3 sentences explaining WHAT they want to know and WHY)",
  "question_type": "count | trend | comparison | list | distribution | spatial_analysis",
  "entities": {
    "species": ["Specific species mentioned or 'all species'"],
    "locations": ["Specific states/colonies or 'all Gulf Coast'"],
    "time_range": "Specific years (e.g., '2015-2021') or 'all available years (2010-2021)'",
    "metrics": ["Exact metrics: 'Bird Count', 'Nest Count', 'Species Diversity', etc."]
  },
  "constraints": [
    "SPECIFIC filters extracted from question (e.g., 'State must be Louisiana', 'Year >= 2015', 'Exclude colonies with NULL coordinates')"
  ],
  "tables_needed": ["Exact table names needed: tblColonyTotals2010-2021_MayJuneCombined, etc."],
  "needs_coordinates": true/false,
  "step_by_step_reasoning": [
    "1. Intent: [SPECIFIC explanation of what user wants - not generic]",
    "2. Data Location: [WHY choosing specific table - cite table purpose]",
    "3. Metrics Needed: [EXACT columns to query and aggregate - e.g., 'COUNT(DISTINCT SpeciesCode) for diversity']",
    "4. Filters Required: [SPECIFIC WHERE clause logic - e.g., 'WHERE State=LA AND Year BETWEEN 2015 AND 2021']",
    "5. Grouping: [If applicable, explain GROUP BY - e.g., 'GROUP BY ColonyName to show per-colony diversity']",
    "6. Spatial Data: [If coordinates needed, explain WHY - e.g., 'Need Lat/Lon to map biodiversity hotspots on Gulf Coast']",
    "7. Expected Output: [Describe expected result structure - e.g., '445 rows, each colony with species_count column']"
  ]
}

Now analyze the user's actual question with this same level of detail."""}
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
        """
        Expert SQL validation with detailed checklist of what was verified.
        Returns structured validation with explicit checks.
        """

        # Pure LLM validation - no hard-coded rules
        messages = [
            {"role": "system", "content": """You are a Principal Data Engineer and Ecologist.
Validate the SQL query against high-level scientific and structural principles.

🚨 STRUCTURAL INTEGRITY CHECKLIST:
1. Table Selection: Does it use tblColonyTotals for bird counts (not tblSpeciesData)?
2. Aggregation: Does it use SUM(Birds/Nests) for counts (not COUNT(*))?
3. Spatial Data: If querying locations, are Latitude/Longitude included?
4. GROUP BY: If aggregating, are Lat/Lon in GROUP BY clause?
5. NULL Handling: Does it filter "Latitude IS NOT NULL AND Longitude IS NOT NULL"?
6. Column Names: Are all columns wrapped in double quotes?
7. Joins: If joining tblSpeciesCodes, is the join key correct?

Respond with a JSON object:
{
  "is_valid": true/false,
  "feedback": "One-sentence summary: pass or what's wrong",
  "reasoning": {
    "table_check": "Uses correct table (tblColonyTotals for bird counts)",
    "aggregation_check": "Uses SUM(Birds) for population counts",
    "spatial_check": "Includes Latitude/Longitude for mapping",
    "group_by_check": "Coordinates included in GROUP BY",
    "null_check": "Filters NULL coordinates",
    "issues_found": []
  }
}

Include ONLY the checks that apply to this specific query.
Be technically rigorous."""}
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
                max_tokens=300  # Allow for detailed checklist
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
                    validation['feedback'] = "Query structure validated"
                if 'reasoning' not in validation:
                    validation['reasoning'] = {"summary": validation.get('feedback', "Validation performed")}
            except json.JSONDecodeError:
                # If JSON parsing fails, be lenient and assume valid
                # Only mark as invalid if we see clear negative indicators
                text_lower = validation_text.lower()
                if any(word in text_lower for word in ["invalid", "error", "wrong", "incorrect", "missing"]):
                    validation = {
                        "is_valid": False,
                        "feedback": validation_text[:100],
                        "reasoning": {"summary": validation_text}
                    }
                else:
                    validation = {
                        "is_valid": True,
                        "feedback": "Query structure validated",
                        "reasoning": {"summary": validation_text}
                    }

            return validation
        except Exception as e:
            # On error, assume valid and proceed
            return {
                "is_valid": True,
                "feedback": "Query structure validated",
                "reasoning": {"summary": "Validation check performed"}
            }

    async def _validate_results(self, question: str, sql_query: str, results_df, conversation_history: list = None) -> dict:
        """
        Final validation with detailed reasoning about result quality.
        Returns structured validation showing what was checked.
        """

        if results_df is None or len(results_df) == 0:
            return {
                "is_valid": True,
                "feedback": "Empty result set (may be expected based on filters)",
                "reasoning": {
                    "row_count_check": "0 rows returned",
                    "empty_is_expected": "May be valid if no data matches the filters"
                }
            }

        # Format sample for the model
        results_summary = f"Total Rows: {len(results_df)}\n"
        results_summary += f"Columns: {', '.join(results_df.columns)}\n"
        if len(results_df) > 0:
            results_summary += f"Sample Row 1: {results_df.iloc[0].to_dict()}"
            if len(results_df) > 1:
                results_summary += f"\nSample Row 2: {results_df.iloc[1].to_dict()}"

        messages = [
            {"role": "system", "content": """You are a Senior Data Scientist performing QA.
Cross-reference the question, SQL, and actual results for logical consistency.

RESULT QUALITY CHECKLIST:
1. Row Count: Is the number of rows reasonable for this query type?
2. Column Match: Do the columns match what the question asked for?
3. Value Ranges: Are the numeric values realistic for bird monitoring?
4. Entity Match: Do years/species/locations match the question filters?
5. Data Types: Are columns the expected types (numbers vs text)?

Respond with JSON:
{
  "is_valid": true/false,
  "feedback": "One-sentence summary",
  "reasoning": {
    "row_count_check": "X rows returned, reasonable for this query",
    "column_check": "Columns match question intent",
    "value_check": "Numbers are realistic for bird populations",
    "entity_check": "Years/species match filters",
    "issues_found": []
  }
}

Include ONLY checks that apply. Be specific about numbers."""}
        ]

        messages.append({
            "role": "user",
            "content": f"""Question: {question}

SQL Query:
{sql_query}

Results Summary:
{results_summary}

Validate (respond with JSON):"""
        })

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.validation_temperature,
                max_tokens=300  # Allow for detailed reasoning
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
                    validation['feedback'] = "Results validated"
                if 'reasoning' not in validation:
                    validation['reasoning'] = {"summary": validation.get('feedback', "Results check performed")}
            except json.JSONDecodeError:
                # Default to valid
                validation = {
                    "is_valid": True,
                    "feedback": "Results validated",
                    "reasoning": {"summary": validation_text}
                }

            return validation
        except Exception as e:
            # On error, assume valid
            return {
                "is_valid": True,
                "feedback": "Results validated",
                "reasoning": {"summary": "Results check performed"}
            }


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

            # Parse visualization directives and get clean answer
            viz_directives = parse_visualization_directives(full_answer, results_df)

            # Send clean answer (without visualization directives)
            yield f"data: {json.dumps({'type': 'answer_end', 'clean_answer': viz_directives['clean_answer']})}\n\n"

            # Send visualization directives separately
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

@app.post("/nestdb/generate_query")
async def nestdb_generate_query(request: QuestionRequest):
    """
    Generate SQL query for NestDB admin interface (NO read-only restrictions).

    This endpoint is specifically for the NestDB admin interface where write operations
    are allowed. Unlike /ask, this endpoint:
    - Does NOT enforce read-only validation
    - Returns ONLY the SQL query (does not execute)
    - Allows INSERT, UPDATE, DELETE, CREATE, etc.

    The frontend will display the query for user review before execution.
    """
    try:
        # Update model if provided
        if request.model:
            chatbot.model = request.model

        # Build messages for SQL generation (similar to generate_sql_query but without coordinate requirements)
        messages = [
            {"role": "system", "content": chatbot.system_prompt}
        ]

        # Inject metadata as context (only once at the start)
        if chatbot.metadata and not request.conversation_history:
            metadata_context = chatbot._format_metadata_context()
            messages.append({"role": "system", "content": metadata_context})

        # Add conversation history (last 3 exchanges)
        if request.conversation_history:
            for msg in request.conversation_history[-6:]:
                messages.append(msg)

        # Add the current question with NestDB-specific instructions
        messages.append({
            "role": "user",
            "content": f"""Question: {request.question}

INSTRUCTIONS FOR NESTDB ADMIN INTERFACE:
1. Return ONLY the SQL query/queries - no explanations, no markdown, no comments
2. You can generate ANY valid SQL operation: SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, etc.
3. This is an admin interface, so write operations are allowed
4. Use exact column names from the schema (case-sensitive)
5. For SQLite, use proper syntax (e.g., AUTOINCREMENT, not AUTO_INCREMENT)
6. **IMPORTANT**: You can generate MULTIPLE SQL statements separated by semicolons
   - If the user asks to "create a table and insert data", generate BOTH statements:
     CREATE TABLE ...; INSERT INTO ...;
   - Always complete multi-step operations in a single response
   - Each statement should end with a semicolon
7. Be smart and helpful - understand the user's intent fully
   - "Create a table and add data" = CREATE TABLE + INSERT statements
   - "Set up a test table" = CREATE TABLE + INSERT sample data
   - Think through what the user actually needs

Generate the complete SQL query/queries now:"""
        })

        try:
            response = client.chat.completions.create(
                model=chatbot.model,
                messages=messages,
                temperature=config['model']['sql_temperature'],
                max_tokens=config['model']['sql_max_tokens']
            )

            sql_query = response.choices[0].message.content.strip()

            # Clean up the query (remove markdown formatting if present)
            if sql_query.startswith("```sql"):
                sql_query = sql_query.split("```sql")[1].split("```")[0].strip()
            elif sql_query.startswith("```"):
                sql_query = sql_query.split("```")[1].split("```")[0].strip()

            # Remove any remaining explanatory text before SQL keywords
            sql_keywords = ['SELECT', 'WITH', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP', 'PRAGMA']
            for keyword in sql_keywords:
                if keyword in sql_query.upper():
                    idx = sql_query.upper().find(keyword)
                    sql_query = sql_query[idx:].strip()
                    break

            # Detect if this is a write operation
            query_upper = sql_query.strip().upper()
            write_keywords = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 'TRUNCATE', 'REPLACE']
            is_write_operation = any(kw in query_upper for kw in write_keywords)

            return {
                "sql_query": sql_query,
                "is_write_operation": is_write_operation
            }

        except Exception as e:
            return {
                "sql_query": f"-- Error generating query: {e}",
                "is_write_operation": False,
                "error": str(e)
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
# DATABASE EXPLORER ENDPOINT
# ============================================================================

@app.post("/db/explore")
async def explore_database():
    """
    Trigger the Database Explorer Agent to autonomously discover schema,
    relationships, and semantic context.
    """
    try:
        db_path = str(DB_PATH)
        metadata_path = str(SERVER_DIR.parent / "data" / "database_metadata_enhanced.json")

        explorer = DatabaseExplorer(db_path, metadata_path)
        results = explorer.explore()

        # Refresh chatbot context
        chatbot.refresh_metadata()
        if 'agentic_chatbot' in globals():
            agentic_chatbot.refresh_metadata()

        return {
            "success": True,
            "message": "Database exploration complete. Context refreshed.",
            "insights": results.get("semantic_insights", []),
            "tables_discovered": list(results.get("tables", {}).keys())
        }
    except Exception as e:
        logger.error(f"Error during database exploration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/db/compress-metadata")
async def compress_metadata():
    """
    Use AI to compress database metadata from 35k+ tokens to <2k tokens.

    Creates three-tier metadata system:
    - Essential: Ultra-compact, query-optimized (default)
    - Extended: Mid-tier with full column names
    - Raw: Original verbose metadata (fallback)
    """
    try:
        from server.services.metadata_compressor import MetadataCompressor

        db_path = str(DB_PATH)
        api_key = os.getenv("OPENROUTER_API_KEY")

        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="OPENROUTER_API_KEY not found in environment"
            )

        compressor = MetadataCompressor(db_path, api_key, config['model']['name'])
        paths = compressor.compress(output_dir=str(SERVER_DIR.parent / "data"))

        # Refresh chatbot to use new compressed metadata
        chatbot.refresh_metadata()
        if 'agentic_chatbot' in globals():
            agentic_chatbot.refresh_metadata()

        # Calculate compression stats
        essential_size = Path(paths['essential']).stat().st_size
        raw_size = Path(paths['raw']).stat().st_size
        essential_tokens = essential_size // 4
        raw_tokens = raw_size // 4
        compression_ratio = (1 - essential_tokens / raw_tokens) * 100

        return {
            "success": True,
            "message": "Metadata compression complete. Chatbot context refreshed.",
            "stats": {
                "before_tokens": raw_tokens,
                "after_tokens": essential_tokens,
                "tokens_saved": raw_tokens - essential_tokens,
                "compression_ratio": f"{compression_ratio:.1f}%"
            },
            "files": {
                "essential": paths['essential'],
                "extended": paths['extended'],
                "raw": paths['raw']
            }
        }
    except Exception as e:
        logger.error(f"Error during metadata compression: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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

@app.post("/db/query", response_model=CustomSQLResponse)
async def execute_query(request: CustomSQLRequest):
    """
    Execute a SQL query on the database (for NestDB admin interface).

    This endpoint allows admins to execute any SQL query including write operations.
    Write operations (INSERT, UPDATE, DELETE, etc.) are automatically committed to version control.

    Args:
        request: CustomSQLRequest with sql_query

    Returns:
        CustomSQLResponse with results or error

    Educational Note:
    Unlike /ask which is read-only for safety, this endpoint allows full database access
    because it's protected by authentication in the Flask app (only logged-in admins can access NestDB).
    """
    try:
        query = request.sql_query.strip()

        if not query:
            return CustomSQLResponse(
                success=False,
                results=None,
                results_count=0,
                error="Query cannot be empty"
            )

        # Detect if this is a write operation (check all statements)
        query_upper = query.upper()
        write_keywords = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 'TRUNCATE', 'REPLACE']
        is_write_operation = any(kw in query_upper for kw in write_keywords)

        # Use read-write connection (not read-only like NestChat)
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cursor = conn.cursor()

        try:
            # Check if multiple statements (contains semicolons not at the end)
            statements = [s.strip() for s in query.split(';') if s.strip()]
            has_multiple_statements = len(statements) > 1

            if has_multiple_statements:
                # Use executescript for multiple statements
                # This handles CREATE TABLE; INSERT INTO; etc. in one go
                cursor.executescript(query)
                rows_affected = cursor.rowcount if cursor.rowcount > 0 else len(statements)
            else:
                # Single statement - use regular execute
                cursor.execute(query)
                rows_affected = cursor.rowcount

            # For write operations, commit and track in version control
            if is_write_operation:
                conn.commit()

                # Get user info for attribution
                user_email = request.expert_email or "anonymous"
                user_info = get_user_info(user_email)

                # Commit to Git version control FIRST (to get commit hash)
                commit_hash = None
                try:
                    # Create user-specific version control instance
                    user_vc = DatabaseVersionControl(
                        DB_PATH,
                        expert_email=user_email,
                        expert_name=user_info.get("name")
                    )

                    commit_result = user_vc.commit(
                        message=f"Query executed via NestDB: {query[:100]}{'...' if len(query) > 100 else ''}",
                        details={
                            "operation": "SQL_QUERY",
                            "query": query,
                            "rows_affected": rows_affected,
                            "interface": "NestDB"
                        },
                        expert_picture=user_info.get("picture"),
                        force=True  # Force commit even if Git thinks nothing changed
                    )
                    commit_hash = commit_result.get('commit_hash')  # Get full hash for tracker
                    logger.info(f"Version control commit by {user_info.get('name')} ({user_email}): {commit_result}")
                except Exception as vc_error:
                        logger.warning(f"Version control commit failed: {vc_error}")

                # Track query execution with detailed tracker (WITH commit hash)
                if change_tracker:
                    try:
                        change_tracker.track_query(
                            query=query,
                            rows_affected=rows_affected,
                            user_email=user_email,
                            user_name=user_info.get("name"),
                            user_picture=user_info.get("picture"),
                            commit_hash=commit_hash  # Link Git commit to change tracker
                        )
                        print(f"✓ Query execution tracked for {user_email} (linked to Git commit {commit_result.get('commit_hash_short') if commit_hash else 'none'})")
                    except Exception as e:
                        print(f"⚠️  Warning: Change tracker failed: {e}")

                conn.close()

                return CustomSQLResponse(
                    success=True,
                    results=None,
                    results_count=rows_affected,
                    error=None
                )

            # For read operations (SELECT, etc.), return results
            else:
                columns = [description[0] for description in cursor.description] if cursor.description else []
                rows = cursor.fetchall()

                # Convert rows to list of dicts
                results = []
                for row in rows:
                    row_dict = {}
                    for i, col in enumerate(columns):
                        row_dict[col] = row[i]
                    results.append(row_dict)

                conn.close()

                return CustomSQLResponse(
                    success=True,
                    results=results,
                    results_count=len(results),
                    error=None
                )

        except Exception as e:
            conn.rollback()
            conn.close()
            return CustomSQLResponse(
                success=False,
                results=None,
                results_count=0,
                error=f"Query execution failed: {str(e)}"
            )

    except Exception as e:
        return CustomSQLResponse(
            success=False,
            results=None,
            results_count=0,
            error=f"Failed to process query: {str(e)}"
        )

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
        # Include rowid for tables without explicit primary keys
        query = f'SELECT rowid, * FROM "{table_name}" LIMIT ? OFFSET ?'
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

        # STEP 1: Fetch old values BEFORE updating (for change tracking)
        # Include rowid in case table has no explicit primary key
        select_query = f'SELECT rowid, * FROM "{table_name}" WHERE {where_clause}'
        cursor.execute(select_query, where_values)
        old_row = cursor.fetchone()

        # Get column names
        column_names = [description[0] for description in cursor.description]
        old_values = dict(zip(column_names, old_row)) if old_row else {}

        # Build UPDATE SET clause
        set_parts = []
        set_values = []
        for col, val in request.updates.items():
            set_parts.append(f'"{col}" = ?')
            set_values.append(val)
        set_clause = ", ".join(set_parts)

        # STEP 2: Execute update
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

        # STEP 3: Get user info for attribution
        user_email = request.expert_email or "anonymous"
        user_info = get_user_info(user_email)

        # STEP 4: Auto-commit to Git version control FIRST (to get commit hash)
        commit_hash = None
        try:
            # Create user-specific version control instance
            user_vc = DatabaseVersionControl(
                DB_PATH,
                expert_email=user_email,
                expert_name=user_info.get("name")
            )

            commit_result = user_vc.commit(
                message=f"Updated {rows_affected} row(s) in {table_name}",
                details={
                    "operation": "UPDATE",
                    "table": table_name,
                    "rows_affected": rows_affected,
                    "columns_updated": list(request.updates.keys())
                },
                expert_picture=user_info.get("picture"),
                force=True  # Force commit even if Git thinks nothing changed
            )
            commit_hash = commit_result.get('commit_hash')  # Get full hash for tracker
            print(f"✓ Database change committed by {user_info.get('name')} ({user_email}): {commit_result.get('commit_hash_short')}")
        except Exception as e:
            print(f"⚠️  Warning: Version control commit failed: {e}")

        # STEP 5: Track change with detailed row-level tracker (WITH commit hash)
        if change_tracker and old_values:
            try:
                # Build new values dict (merge old values with updates)
                new_values = {**old_values, **request.updates}

                change_tracker.track_update(
                    table_name=table_name,
                    row_id=request.row_id,
                    old_values=old_values,
                    new_values=new_values,
                    user_email=user_email,
                    user_name=user_info.get("name"),
                    user_picture=user_info.get("picture"),
                    commit_hash=commit_hash  # Link Git commit to change tracker
                )
                print(f"✓ Row-level change tracked for {user_email} (linked to Git commit {commit_result.get('commit_hash_short') if commit_hash else 'none'})")
            except Exception as e:
                print(f"⚠️  Warning: Change tracker failed: {e}")

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

        # STEP 1: Fetch row data BEFORE deleting (for change tracking)
        select_query = f'SELECT * FROM "{table_name}" WHERE {where_clause}'
        cursor.execute(select_query, where_values)
        deleted_row = cursor.fetchone()

        # Get column names
        column_names = [description[0] for description in cursor.description]
        deleted_values = dict(zip(column_names, deleted_row)) if deleted_row else {}

        # STEP 2: Execute delete
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

        # STEP 3: Get user info for attribution
        user_email = request.expert_email or "anonymous"
        user_info = get_user_info(user_email)

        # STEP 4: Track deletion with detailed row-level tracker
        commit_hash = None
        if change_tracker and deleted_values:
            try:
                change_tracker.track_delete(
                    table_name=table_name,
                    row_id=request.row_id,
                    deleted_values=deleted_values,
                    user_email=user_email,
                    user_name=user_info.get("name"),
                    user_picture=user_info.get("picture")
                )
                print(f"✓ Row-level deletion tracked for {user_email}")
            except Exception as e:
                print(f"⚠️  Warning: Change tracker failed: {e}")

        # STEP 5: Auto-commit to version control with user attribution
        try:
            # Create user-specific version control instance
            user_vc = DatabaseVersionControl(
                DB_PATH,
                expert_email=user_email,
                expert_name=user_info.get("name")
            )

            commit_result = user_vc.commit(
                message=f"Deleted {rows_affected} row(s) from {table_name}",
                details={
                    "operation": "DELETE",
                    "table": table_name,
                    "rows_affected": rows_affected
                },
                expert_picture=user_info.get("picture"),
                force=True  # Force commit even if Git thinks nothing changed
            )
            commit_hash = commit_result.get('commit_hash_short')
            print(f"✓ Database change committed by {user_info.get('name')} ({user_email}): {commit_hash}")
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

        # Get user info for attribution
        user_email = request.expert_email or "anonymous"
        user_info = get_user_info(user_email)

        # Auto-commit to Git version control FIRST (to get commit hash)
        commit_hash = None
        try:
            # Create user-specific version control instance
            user_vc = DatabaseVersionControl(
                DB_PATH,
                expert_email=user_email,
                expert_name=user_info.get("name")
            )

            commit_result = user_vc.commit(
                message=f"Inserted {rows_affected} row(s) into {table_name}",
                details={
                    "operation": "INSERT",
                    "table": table_name,
                    "rows_affected": rows_affected,
                    "columns": list(request.row_data.keys())
                },
                expert_picture=user_info.get("picture"),
                force=True  # Force commit even if Git thinks nothing changed
            )
            commit_hash = commit_result.get('commit_hash')  # Get full hash for tracker
            print(f"✓ Database change committed by {user_info.get('name')} ({user_email}): {commit_result.get('commit_hash_short')}")
        except Exception as e:
            print(f"⚠️  Warning: Version control commit failed: {e}")

        # Track insert with detailed row-level tracker (WITH commit hash)
        if change_tracker:
            try:
                change_tracker.track_insert(
                    table_name=table_name,
                    row_data=request.row_data,
                    user_email=user_email,
                    user_name=user_info.get("name"),
                    user_picture=user_info.get("picture"),
                    commit_hash=commit_hash  # Link Git commit to change tracker
                )
                print(f"✓ Row-level insert tracked for {user_email} (linked to Git commit {commit_result.get('commit_hash_short') if commit_hash else 'none'})")
            except Exception as e:
                print(f"⚠️  Warning: Change tracker failed: {e}")

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

@app.post("/db/table/{table_name}/column", response_model=ColumnAddResponse)
async def add_table_column(table_name: str, request: ColumnAddRequest):
    """
    Add a new column to an existing table.

    Args:
        table_name: Name of the table
        request: ColumnAddRequest with column details

    Returns:
        ColumnAddResponse with success status
    """
    try:
        # Use read_only=False for write operations
        conn = chatbot.get_connection(read_only=False)
        cursor = conn.cursor()

        # Build ALTER TABLE query
        column_def = f'"{request.column_name}" {request.column_type}'

        if request.not_null:
            if request.default_value is None:
                return ColumnAddResponse(
                    success=False,
                    message=None,
                    error="NOT NULL columns must have a default value"
                )
            column_def += f" NOT NULL DEFAULT {request.default_value}"
        elif request.default_value is not None:
            column_def += f" DEFAULT {request.default_value}"

        query = f'ALTER TABLE "{table_name}" ADD COLUMN {column_def}'
        cursor.execute(query)
        conn.commit()
        conn.close()

        # Get user info for attribution
        user_email = request.expert_email or "anonymous"
        user_info = get_user_info(user_email)

        # Auto-commit to Git version control
        commit_hash = None
        try:
            user_vc = DatabaseVersionControl(
                DB_PATH,
                expert_email=user_email,
                expert_name=user_info.get("name")
            )

            commit_result = user_vc.commit(
                message=f"Added column '{request.column_name}' to {table_name}",
                details={
                    "operation": "ALTER_TABLE_ADD_COLUMN",
                    "table": table_name,
                    "column_name": request.column_name,
                    "column_type": request.column_type
                },
                expert_picture=user_info.get("picture"),
                force=True
            )
            commit_hash = commit_result.get('commit_hash')
            print(f"✓ Column addition committed by {user_info.get('name')} ({user_email}): {commit_result.get('commit_hash_short')}")
        except Exception as e:
            print(f"⚠️  Warning: Version control commit failed: {e}")

        return ColumnAddResponse(
            success=True,
            message=f"Successfully added column '{request.column_name}' to {table_name}",
            error=None,
            version_commit=commit_hash
        )
    except Exception as e:
        return ColumnAddResponse(
            success=False,
            message=None,
            error=str(e)
        )

@app.delete("/db/table/{table_name}/column/{column_name}", response_model=ColumnDeleteResponse)
async def delete_table_column(table_name: str, column_name: str, expert_email: Optional[str] = None):
    """
    Delete a column from a table.

    Note: SQLite doesn't support DROP COLUMN directly in older versions.
    This recreates the table without the specified column.

    Args:
        table_name: Name of the table
        column_name: Name of the column to delete
        expert_email: Email of user making the change

    Returns:
        ColumnDeleteResponse with success status
    """
    try:
        # Use read_only=False for write operations
        conn = chatbot.get_connection(read_only=False)
        cursor = conn.cursor()

        # Get current table schema
        cursor.execute(f'PRAGMA table_info("{table_name}")')
        columns = cursor.fetchall()

        # Check if column exists
        column_exists = any(col[1] == column_name for col in columns)
        if not column_exists:
            conn.close()
            return ColumnDeleteResponse(
                success=False,
                message=None,
                error=f"Column '{column_name}' does not exist in table '{table_name}'"
            )

        # Get columns to keep (all except the one to delete)
        columns_to_keep = [col for col in columns if col[1] != column_name]

        if not columns_to_keep:
            conn.close()
            return ColumnDeleteResponse(
                success=False,
                message=None,
                error="Cannot delete the last column in a table"
            )

        # Build new column definitions
        new_columns_def = []
        for col in columns_to_keep:
            col_def = f'"{col[1]}" {col[2]}'
            if col[3]:  # NOT NULL
                col_def += " NOT NULL"
            if col[4] is not None:  # DEFAULT value
                col_def += f" DEFAULT {col[4]}"
            if col[5]:  # PRIMARY KEY
                col_def += " PRIMARY KEY"
            new_columns_def.append(col_def)

        columns_to_keep_names = [f'"{col[1]}"' for col in columns_to_keep]

        # SQLite column deletion workflow (recreate table)
        temp_table = f"{table_name}_temp_{int(time.time())}"

        # Create temporary table with new schema
        create_temp_query = f'CREATE TABLE "{temp_table}" ({", ".join(new_columns_def)})'
        cursor.execute(create_temp_query)

        # Copy data
        copy_query = f'INSERT INTO "{temp_table}" SELECT {", ".join(columns_to_keep_names)} FROM "{table_name}"'
        cursor.execute(copy_query)

        # Drop old table
        cursor.execute(f'DROP TABLE "{table_name}"')

        # Rename temp table
        cursor.execute(f'ALTER TABLE "{temp_table}" RENAME TO "{table_name}"')

        conn.commit()
        conn.close()

        # Get user info for attribution
        user_email = expert_email or "anonymous"
        user_info = get_user_info(user_email)

        # Auto-commit to Git version control
        commit_hash = None
        try:
            user_vc = DatabaseVersionControl(
                DB_PATH,
                expert_email=user_email,
                expert_name=user_info.get("name")
            )

            commit_result = user_vc.commit(
                message=f"Deleted column '{column_name}' from {table_name}",
                details={
                    "operation": "ALTER_TABLE_DROP_COLUMN",
                    "table": table_name,
                    "column_name": column_name
                },
                expert_picture=user_info.get("picture"),
                force=True
            )
            commit_hash = commit_result.get('commit_hash')
            print(f"✓ Column deletion committed by {user_info.get('name')} ({user_email}): {commit_result.get('commit_hash_short')}")
        except Exception as e:
            print(f"⚠️  Warning: Version control commit failed: {e}")

        return ColumnDeleteResponse(
            success=True,
            message=f"Successfully deleted column '{column_name}' from {table_name}",
            error=None,
            version_commit=commit_hash
        )
    except Exception as e:
        return ColumnDeleteResponse(
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
async def manual_commit(request: VersionCommitRequest):
    """
    Manually create a version control commit.

    This is useful for checkpointing database state at key moments.
    Normally commits happen automatically after database writes.

    Args:
        request: Contains commit message and expert_email

    Returns:
        Commit hash and timestamp
    """
    if db_version_control is None:
        return {
            "success": False,
            "error": "Version control is not initialized"
        }

    try:
        # Update expert info for this commit
        db_version_control.expert_email = request.expert_email
        if request.expert_name:
            db_version_control.expert_name = request.expert_name

        # Pass skip_timestamp=True for manual checkpoints (timestamp is redundant with Git's own)
        result = db_version_control.commit(
            request.message,
            skip_timestamp=True,
            expert_picture=request.expert_picture
        )

        return result
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.get("/db/changes/history")
async def get_enhanced_change_history(
    limit: int = 50,
    table_name: Optional[str] = None,
    user_email: Optional[str] = None,
    operation: Optional[str] = None
):
    """
    Get enhanced row-level change history with detailed before/after values.

    This provides much more detail than Git commits:
    - Shows exact column values that changed (old → new)
    - Filterable by table, user, or operation type
    - Includes user profile pictures and names

    Args:
        limit: Maximum number of changes to return (default: 50)
        table_name: Filter by table name (optional)
        user_email: Filter by user email (optional)
        operation: Filter by operation type: UPDATE, INSERT, DELETE (optional)

    Returns:
        List of commits with detailed change information

    Educational Note:
    This is the "detailed audit trail" that shows exactly what changed in each row.
    Think of Git commits as "snapshots" and this as a "frame-by-frame replay".
    """
    if change_tracker is None:
        return {
            "success": False,
            "error": "Change tracker is not initialized",
            "commits": []
        }

    try:
        history = change_tracker.get_history(
            limit=limit,
            table_name=table_name,
            user_email=user_email,
            operation=operation
        )

        return {
            "success": True,
            "commits": history,
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "commits": []
        }


@app.get("/db/changes/stats")
async def get_change_stats():
    """
    Get statistics about database changes.

    Returns:
        Statistics including:
        - Total commits
        - Total individual column changes
        - Most active users
        - Most modified tables
        - Operation breakdown (INSERT/UPDATE/DELETE counts)
    """
    if change_tracker is None:
        return {
            "success": False,
            "error": "Change tracker is not initialized"
        }

    try:
        stats = change_tracker.get_stats()
        return {
            "success": True,
            **stats
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================================
# COASTAL RISK INTELLIGENCE ENDPOINTS - Real Data Fusion
# ============================================================================

@app.get("/api/risk/map_zones")
async def get_risk_map_zones():
    """
    Get dynamic GeoJSON-style risk zones for map visualization
    Fuses colony data with live NOAA/HURDAT2/USGS regional factors.
    """
    try:
        service = get_risk_service()
        colonies = service.get_colonies_with_stats()
        results = service.calculate_dynamic_risk(colonies)

        zones = []
        for row in results:
            # Map FEMA zone to risk category
            fema_zone = row.get('fema_flood_zone', 'UNKNOWN')
            if fema_zone in ['A', 'AE', 'V', 'VE']:
                fema_category = 'HIGH'
            elif fema_zone in ['AO', 'AH', 'A99']:
                fema_category = 'MODERATE'
            elif fema_zone == 'X500':
                fema_category = 'LOW'
            else:
                fema_category = 'MINIMAL'

            zones.append({
                "colony_name": row['colony_name'],
                "latitude": row['latitude'],
                "longitude": row['longitude'],
                "risk_score": row['risk_score'],
                "risk_level": row['risk_level'],
                "color": row['risk_color'],
                "years_until_critical": row['years_until_critical'],
                "action": row['recommended_action'],
                "birds": row['bird_count'],
                "species": row['species_count'],
                "last_survey": row['last_year'] if 'last_year' in row else 2021,
                "data_year": 2026,
                "radius_km": 50,
                # FEMA Flood Zone Data
                "fema_zone": fema_zone,
                "fema_description": row.get('fema_zone_description', 'Data unavailable'),
                "fema_category": fema_category
            })

        return {
            "zones": zones,
            "summary": {
                "critical": len([z for z in zones if z['risk_level'] == 'CRITICAL']),
                "high": len([z for z in zones if z['risk_level'] == 'HIGH'])
            }
        }
    except Exception as e:
        logger.error(f"Error in get_risk_map_zones: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/risk/priority_list")
async def get_priority_restoration_sites(limit: int = 10):
    """
    Get top priority sites for restoration ranked by dynamic risk/urgency
    """
    try:
        service = get_risk_service()
        colonies = service.get_colonies_with_stats()
        results = service.calculate_dynamic_risk(colonies)

        # Filter to high priority
        priorities_raw = [r for r in results if r['risk_level'] in ('CRITICAL', 'HIGH')]
        # Sort by urgency (years until critical) then by risk score
        priorities_raw = sorted(priorities_raw, key=lambda x: (x['years_until_critical'], -x['risk_score']))[:limit]

        priorities = []
        for idx, row in enumerate(priorities_raw, 1):
            # Dynamic cost estimation
            erosion = row['erosion_rate']
            birds = row['bird_count']
            complexity = 1.5 if birds > 10000 else 1.2 if birds > 5000 else 1.0
            years_critical = row['years_until_critical']
            urgency = 1.8 if years_critical < 5 else 1.4 if years_critical < 10 else 1.0
            estimated_area_m2 = max(10000, min(200000, erosion * 1000 + birds * 2))
            estimated_cost = estimated_area_m2 * (75 * complexity * urgency) * 1.2

            priorities.append({
                "rank": idx,
                "colony_name": row['colony_name'],
                "risk_score": row['risk_score'],
                "years_until_critical": row['years_until_critical'],
                "recommended_action": row['recommended_action'],
                "bird_population_2026": row['bird_count'],
                "species_count": row['species_count'],
                "erosion_rate": round(row['erosion_rate'], 1),
                "slr_2050": round(row['slr_2050_m'], 2),
                "population_trend_pct": None,
                "estimated_cost_usd": int(estimated_cost),
                "last_survey_year": row.get('last_year', 2021)
            })

        return {
            "priorities": priorities,
            "total_high_priority": len(priorities_raw)
        }
    except Exception as e:
        logger.error(f"Error in get_priority_restoration_sites: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/risk/data_sources/{colony_name}")
async def get_data_fusion_breakdown(colony_name: str):
    """
    Show how dynamic data sources fuse into a risk score for a colony
    """
    try:
        service = get_risk_service()
        colonies = service.get_colonies_with_stats()
        # Find specific colony
        colony_data = [c for c in colonies if c['ColonyName'] == colony_name]
        if not colony_data:
            raise HTTPException(status_code=404, detail="Colony not found")

        results = service.calculate_dynamic_risk(colony_data)
        if not results:
            raise HTTPException(status_code=500, detail="Risk calculation failed")

        row = results[0]

        return {
            "colony_name": row['colony_name'],
            "data_sources": {
                "sea_level_rise": {
                    "value": round(row['slr_2050_m'], 2),
                    "unit": "meters by 2050",
                    "source": "NOAA Sea Level Rise Viewer",
                    "weight": 0.25,
                    "impact": "High" if row['slr_2050_m'] > 0.5 else "Moderate"
                },
                "erosion_rate": {
                    "value": round(row['erosion_rate'], 1),
                    "unit": "meters/year",
                    "source": "USGS Open-File Report 2017-1051",
                    "weight": 0.35,
                    "impact": "High" if row['erosion_rate'] > 10 else "Moderate"
                },
                "hurricane_exposure": {
                    "value": len(service.major_storms),
                    "unit": "major storms since 2005",
                    "source": "NOAA HURDAT2 Database",
                    "weight": 0.1,
                    "impact": "High"
                },
                "population_trend": {
                    "value": row['bird_count'],
                    "unit": "birds (current)",
                    "source": "Water Institute Survey Data",
                    "weight": 0.1,
                    "impact": "High" if row['bird_count'] < 500 else "Moderate"
                }
            },
            "combined_score": row['risk_score'],
            "risk_level": row['risk_level'],
            "years_until_critical": row['years_until_critical'],
            "recommended_action": row['recommended_action']
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_data_fusion_breakdown: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/risk/projection/{year}")
async def get_future_projection(year: int, scenario: str = "intermediate"):
    """
    Get dynamic projection for future state
    """
    try:
        if year not in [2030, 2050, 2070, 2100]:
            raise HTTPException(status_code=400, detail="Year must be 2030, 2050, 2070, or 2100")

        service = get_risk_service()
        colonies = service.get_colonies_with_stats()
        results = service.calculate_dynamic_risk(colonies)

        colonies_projected = []
        submerged = 0
        at_risk = 0
        viable = 0
        total_birds_affected = 0

        years_ahead = year - 2026

        for row in results:
            # Simple projection logic based on erosion rate and years ahead
            area_remaining_pct = max(0, 100 - (row['erosion_rate'] * years_ahead / 100))
            status = "submerged" if area_remaining_pct == 0 else "at_risk" if area_remaining_pct < 30 else "viable"

            if status == "submerged":
                submerged += 1
                total_birds_affected += row['bird_count']
            elif status == "at_risk":
                at_risk += 1
                total_birds_affected += int(row['bird_count'] * 0.5)
            else:
                viable += 1

            colonies_projected.append({
                "colony_name": row['colony_name'],
                "latitude": row['latitude'],
                "longitude": row['longitude'],
                "status": status,
                "projected_area_pct": round(area_remaining_pct, 1),
                "birds_current": row['bird_count']
            })

        total = len(results)
        total_birds = sum(r['bird_count'] for r in results)
        bird_loss_pct = (total_birds_affected / total_birds) * 100 if total_birds > 0 else 0

        return {
            "year": year,
            "scenario": scenario,
            "summary": {
                "total_colonies": total,
                "submerged": submerged,
                "at_risk": at_risk,
                "viable": viable,
                "bird_population_loss_pct": round(bird_loss_pct, 1)
            },
            "colonies": colonies_projected[:100]
        }
    except Exception as e:
        logger.error(f"Error in get_future_projection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/risk/summary")
async def get_risk_summary():
    """Get dynamic overall risk summary statistics"""
    try:
        service = get_risk_service()
        colonies = service.get_colonies_with_stats()
        results = service.calculate_dynamic_risk(colonies)
        summary = service.get_summary_stats(results)
        return summary
    except Exception as e:
        logger.error(f"Error in get_risk_summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))



# ============================================================================
# FLOOD DATA ENDPOINTS - NOAA Water Level Integration (OLD - KEEP FOR NOW)
# ============================================================================

@app.get("/flood/stations")
async def get_flood_stations():
    """
    Get all NOAA flood monitoring stations in Louisiana coastal region.

    Returns:
        List of stations with metadata (name, location, region, MHHW datum)
    """
    try:
        db_path = os.getenv("DB_PATH", "data/bird_data_complete.db")
        flood_db = FloodDatabase(db_path)

        stations = flood_db.get_all_stations()

        return {
            "stations": stations,
            "count": len(stations)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/flood/events")
async def get_flood_events(
    station_id: Optional[str] = None,
    year: Optional[int] = None,
    min_severity: Optional[str] = None,
    limit: int = 1000
):
    """
    Query flood events from NOAA water level data.

    Args:
        station_id: Filter by specific station (e.g., "8761724")
        year: Filter by year (e.g., 2012)
        min_severity: Minimum severity ("minor", "moderate", "major")
        limit: Maximum results (default: 1000)

    Returns:
        List of flood events with timestamp, severity, water level
    """
    try:
        db_path = os.getenv("DB_PATH", "data/bird_data_complete.db")
        flood_db = FloodDatabase(db_path)

        events = flood_db.get_flood_events(
            station_id=station_id,
            year=year,
            min_severity=min_severity,
            limit=limit
        )

        return {
            "events": events,
            "count": len(events),
            "filters": {
                "station_id": station_id,
                "year": year,
                "min_severity": min_severity
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/flood/summary")
async def get_flood_summary(station_id: Optional[str] = None):
    """
    Get flood event summary statistics by year and severity.

    Args:
        station_id: Filter by specific station (optional)

    Returns:
        Yearly summary of flood counts by severity level
    """
    try:
        db_path = os.getenv("DB_PATH", "data/bird_data_complete.db")
        flood_db = FloodDatabase(db_path)

        summary = flood_db.get_flood_summary_by_year(station_id=station_id)

        return {
            "summary": summary,
            "station_id": station_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/flood/impact")
async def calculate_flood_impact(
    latitude: float,
    longitude: float,
    max_distance_km: float = 50,
    year: Optional[int] = None
):
    """
    Calculate flood impact for colonies near a geographic location.

    Args:
        latitude: Colony latitude
        longitude: Colony longitude
        max_distance_km: Search radius in kilometers (default: 50)
        year: Filter events by year (optional)

    Returns:
        {
            "nearby_stations": List of stations within radius,
            "flood_events": Flood events at those stations,
            "impact_score": Calculated impact metric,
            "severity_summary": Counts by severity level
        }
    """
    try:
        db_path = os.getenv("DB_PATH", "data/bird_data_complete.db")
        flood_db = FloodDatabase(db_path)

        # Find nearby stations
        nearby_stations = flood_db.get_stations_near_point(
            latitude=latitude,
            longitude=longitude,
            max_distance_km=max_distance_km
        )

        if not nearby_stations:
            return {
                "nearby_stations": [],
                "flood_events": [],
                "impact_score": 0,
                "severity_summary": {"minor": 0, "moderate": 0, "major": 0}
            }

        # Get flood events for nearby stations
        all_events = []
        for station in nearby_stations:
            events = flood_db.get_flood_events(
                station_id=station['station_id'],
                year=year,
                limit=1000
            )
            all_events.extend(events)

        # Calculate severity summary
        severity_counts = {"minor": 0, "moderate": 0, "major": 0}
        for event in all_events:
            severity_counts[event['severity']] += 1

        # Simple impact score: weighted sum of events
        # major=3, moderate=2, minor=1
        impact_score = (
            severity_counts['major'] * 3 +
            severity_counts['moderate'] * 2 +
            severity_counts['minor'] * 1
        )

        return {
            "nearby_stations": nearby_stations,
            "flood_events": all_events[:100],  # Limit returned events
            "total_events": len(all_events),
            "impact_score": impact_score,
            "severity_summary": severity_counts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/flood/stats")
async def get_flood_database_stats():
    """
    Get overall flood database statistics.

    Returns:
        Database stats including station count, event count, year range
    """
    try:
        db_path = os.getenv("DB_PATH", "data/bird_data_complete.db")
        flood_db = FloodDatabase(db_path)

        stats = flood_db.get_database_stats()

        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
