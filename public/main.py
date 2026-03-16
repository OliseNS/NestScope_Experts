"""
NestScope Public API - FastAPI Server
Provides NestChat (Text-to-SQL) and NestVision (Bird Detection) endpoints
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import sqlite3
import pandas as pd
import time
from datetime import datetime
from openai import OpenAI
import os
from pathlib import Path
from dotenv import load_dotenv
import json
import asyncio
import cv2
import base64
import yaml
import logging
import re
from glob import glob

# Initialize logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Load environment variables
load_dotenv()

# Load configuration
CONFIG_PATH = Path(__file__).parent / "config.yaml"

def load_config():
    """Load configuration from YAML file with .env overrides"""
    with open(CONFIG_PATH, 'r') as f:
        config = yaml.safe_load(f)

    # Allow .env to override model name
    if os.getenv("MODEL_NAME"):
        config['model']['name'] = os.getenv("MODEL_NAME")
        logger.info(f"⚠️  MODEL_NAME override from .env: {config['model']['name']}")

    return config

config = load_config()
logger.info(f"✓ Loaded configuration from {CONFIG_PATH}")
logger.info(f"✓ Using model: {config['model']['name']}")

# Initialize OpenRouter client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

# Initialize FastAPI app
app = FastAPI(
    title="NestScope Public API",
    description="AI-powered Gulf Coast avian monitoring - NestChat & NestVision",
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

# Mount static files and templates for webapp
app.mount("/static", StaticFiles(directory="webapp/static"), name="static")
templates = Jinja2Templates(directory="webapp/templates")

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class QuestionRequest(BaseModel):
    question: str
    model: Optional[str] = None
    conversation_history: Optional[List[Dict[str, str]]] = None

class QueryResponse(BaseModel):
    sql_query: str
    results: Optional[List[Dict[str, Any]]]
    results_count: int
    answer: str
    error: Optional[str] = None
    show_chart: bool = False
    chart_type: Optional[str] = None
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
    species_summary: Dict[str, int] = {}
    annotated_image_base64: str
    message: str
    inference_time: float

class ExampleImagesResponse(BaseModel):
    examples: List[str]

# ============================================================================
# DATABASE CONNECTION
# ============================================================================

DB_PATH = os.getenv("DB_PATH", "data/bird_data_complete.db")
MODEL_NAME = config['model']['name']
PROMPT_PATH = Path(__file__).parent / "prompts" / "prompt.txt"
SQL_PROMPT_PATH = Path(__file__).parent / "prompts" / "sql_prompt.txt"
SQL_REASONING_PROMPT_PATH = Path(__file__).parent / "prompts" / "sql_prompt_reasoning.txt"
SQL_GENERATION_PROMPT_PATH = Path(__file__).parent / "prompts" / "sql_prompt_generation.txt"

def get_db_connection(read_only=True):
    """Get a read-only database connection"""
    if read_only:
        uri = f"file:{DB_PATH}?mode=ro"
        return sqlite3.connect(uri, uri=True, check_same_thread=False)
    else:
        return sqlite3.connect(DB_PATH, check_same_thread=False)

# ============================================================================
# SQL CHATBOT CLASS
# ============================================================================

class SQLChatbot:
    def __init__(self, db_path=DB_PATH, model=None, prompt_path=None):
        """Initialize the SQL chatbot"""
        self.db_path = db_path
        self.model = model or MODEL_NAME
        self.schema = None
        self.prompt_path = prompt_path or str(PROMPT_PATH)
        self.sql_prompt_path = SQL_PROMPT_PATH
        self.system_prompt = self._load_system_prompt()
        self.sql_prompt = self._load_sql_prompt()
        self.metadata = self._load_metadata()

    def _load_system_prompt(self):
        """Load the answer generation prompt"""
        try:
            with open(self.prompt_path, 'r', encoding='utf-8') as f:
                prompt = f.read()
            logger.info(f"✓ Answer prompt loaded from {self.prompt_path}")
            return prompt
        except FileNotFoundError:
            raise FileNotFoundError(f"System prompt file not found: {self.prompt_path}")

    def _load_sql_prompt(self):
        """Load the SQL generation prompt"""
        try:
            with open(self.sql_prompt_path, 'r', encoding='utf-8') as f:
                prompt = f.read()
            logger.info(f"✓ SQL prompt loaded from {self.sql_prompt_path}")
            return prompt
        except FileNotFoundError:
            raise FileNotFoundError(f"SQL prompt file not found: {self.sql_prompt_path}")

    def _load_metadata(self):
        """Load database metadata"""
        metadata_path = Path(self.db_path).parent / "database_metadata_enhanced.json"
        try:
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                json_size = len(json.dumps(metadata))
                token_estimate = json_size // 4
                logger.info(f"✓ Metadata loaded from {metadata_path.name} (~{token_estimate:,} tokens)")
                return metadata
        except Exception as e:
            logger.warning(f"⚠️ Failed to load metadata: {e}")
        return None

    def get_connection(self, read_only=True):
        """Get a database connection"""
        if read_only:
            uri = f"file:{self.db_path}?mode=ro"
            return sqlite3.connect(uri, uri=True, check_same_thread=False)
        else:
            return sqlite3.connect(self.db_path, check_same_thread=False)

    def get_database_schema(self):
        """Get the database schema"""
        if self.schema:
            return self.schema

        conn = self.get_connection()
        cursor = conn.cursor()

        schema_info = {'tables': {}}

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        for table in tables:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()

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
        """Format metadata as context"""
        if not self.metadata:
            return "No metadata available."

        context = "# DATABASE SCHEMA\n\n"

        # Critical rules
        rules = self.metadata.get('critical_rules', [])
        if rules:
            context += "## CRITICAL RULES\n"
            for rule in rules:
                context += f"- {rule}\n"
            context += "\n"

        # Tables
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

        return context

    def generate_sql_query(self, question: str, conversation_history: list = None):
        """Generate SQL query from natural language question"""
        messages = [
            {"role": "system", "content": self.sql_prompt}
        ]

        # Add metadata context
        if self.metadata:
            messages.append({"role": "system", "content": self._format_metadata_context()})

        # Add conversation history
        if conversation_history:
            for msg in conversation_history[-6:]:
                messages.append(msg)

        messages.append({
            "role": "user",
            "content": f"Question: {question}\n\nGenerate SQL query as JSON:"
        })

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=config['model']['sql_temperature'],
                max_tokens=config['model']['sql_max_tokens']
            )

            response_text = response.choices[0].message.content.strip()

            # Parse JSON
            if response_text.startswith("```json"):
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif response_text.startswith("```"):
                response_text = response_text.split("```")[1].split("```")[0].strip()

            result = json.loads(response_text)
            sql_query = result.get("sql", "")

            if not sql_query:
                return "ERROR: No SQL in JSON response"

            # Validate read-only
            sql_upper = sql_query.strip().upper()
            if not (sql_upper.startswith('SELECT') or sql_upper.startswith('WITH')):
                return "ERROR: Invalid SQL - must start with SELECT or WITH"

            return sql_query

        except json.JSONDecodeError:
            logger.warning("JSON parsing failed, trying raw SQL extraction")
            if response_text.upper().startswith('SELECT') or response_text.upper().startswith('WITH'):
                return response_text
            return "ERROR: Could not parse SQL from response"
        except Exception as e:
            return f"ERROR: {e}"

    def execute_sql_query(self, sql_query: str):
        """Execute SQL query and return results"""
        conn = self.get_connection(read_only=True)

        try:
            df = pd.read_sql_query(sql_query, conn)
            conn.close()
            return df, None
        except Exception as e:
            conn.close()
            return None, str(e)

    async def generate_answer_stream(self, question: str, sql_query: str, results_df, conversation_history: list = None):
        """Generate natural language answer with streaming"""
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]

        # Add conversation history
        if conversation_history:
            for msg in conversation_history[-6:]:
                messages.append(msg)

        # Build user message with results
        results_text = "No results found."
        if results_df is not None and not results_df.empty:
            results_text = f"Query returned {len(results_df)} rows:\n\n"
            results_text += results_df.to_string(index=False, max_rows=50)

        user_message = f"""Question: {question}

SQL Query:
{sql_query}

Results:
{results_text}

Generate a natural language answer with appropriate visualizations."""

        messages.append({"role": "user", "content": user_message})

        try:
            stream = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=config['model']['temperature'],
                max_tokens=config['model']['max_tokens'],
                stream=True
            )

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            yield f"Error generating answer: {e}"

# ============================================================================
# AGENTIC SQL CHATBOT CLASS
# ============================================================================

class AgenticSQLChatbot(SQLChatbot):
    """Agentic Text-to-SQL Pipeline with self-correction"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_attempts = config.get('agentic', {}).get('max_attempts', 3)
        self.enable_reasoning = config.get('agentic', {}).get('enable_reasoning', True)

        # Load agentic prompts
        self.reasoning_prompt = self._load_phase_prompt("sql_prompt_reasoning.txt")
        self.generation_prompt = self._load_phase_prompt("sql_prompt_generation.txt")

    def _load_phase_prompt(self, filename):
        """Load a phase-specific prompt file"""
        try:
            path = Path(__file__).parent / "prompts" / filename
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(f"⚠️ {filename} not found, using fallback")
            return ""

    def _generate_error_guidance(self, error_message: str, sql_query: str, attempt: int) -> str:
        """Generate helpful error guidance for SQL correction"""
        guidance = f"Your previous SQL query failed with an error:\n\n"
        guidance += f"SQL:\n{sql_query}\n\n"
        guidance += f"Error: {error_message}\n\n"
        guidance += f"This is attempt {attempt} of {self.max_attempts}.\n\n"

        # Pattern-matched debugging hints
        error_lower = error_message.lower()

        if "syntax error" in error_lower or "near" in error_lower:
            guidance += "HINT: Check for:\n"
            guidance += "- Missing or extra parentheses\n"
            guidance += "- Missing commas in SELECT or GROUP BY clauses\n"
            guidance += "- Proper CTE structure (WITH keyword, named CTE, AS)\n"
        elif "no such table" in error_lower or "no such column" in error_lower:
            guidance += "HINT: Check for:\n"
            guidance += "- Correct table/column names (case-sensitive)\n"
            guidance += "- Use exact names from schema\n"
        elif "ambiguous column" in error_lower:
            guidance += "HINT: Use table aliases to disambiguate columns\n"
            guidance += "Example: SELECT t1.ColonyName, t2.SpeciesCode\n"
        elif "group by" in error_lower:
            guidance += "HINT: Ensure all non-aggregated columns are in GROUP BY\n"

        guidance += "\nGenerate a corrected SQL query as JSON."
        return guidance

    async def agentic_ask_stream(self, question: str, conversation_history: list = None):
        """Agentic pipeline with streaming and self-correction"""

        reasoning_plan = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                # Phase: SQL Generation
                if attempt == 1:
                    yield {
                        'type': 'thinking_step',
                        'step': 'generate_sql',
                        'attempt': attempt,
                        'content': "Generating query...",
                        'icon': '⚡'
                    }
                else:
                    yield {
                        'type': 'thinking_step',
                        'step': 'retry',
                        'attempt': attempt,
                        'content': f"Retrying with corrections (attempt {attempt}/{self.max_attempts})...",
                        'icon': '🔄'
                    }

                # Generate SQL
                sql_query = self.generate_sql_query(question, conversation_history)

                # Handle generation errors
                if sql_query.startswith("ERROR"):
                    if attempt < self.max_attempts:
                        if conversation_history is None:
                            conversation_history = []
                        conversation_history.append({
                            'role': 'system',
                            'content': f"Previous attempt failed: {sql_query}\n\nGenerate corrected SQL."
                        })
                        continue
                    else:
                        yield {'type': 'error', 'content': sql_query}
                        return

                yield {
                    'type': 'sql_generated',
                    'content': sql_query,
                    'attempt': attempt
                }

                # Execute query
                yield {
                    'type': 'thinking_step',
                    'step': 'execute',
                    'content': "Executing query...",
                    'icon': '🔍'
                }

                results_df, error = self.execute_sql_query(sql_query)

                # Handle execution errors
                if error:
                    if attempt < self.max_attempts:
                        yield {
                            'type': 'execution_error',
                            'attempt': attempt,
                            'error': error,
                            'sql': sql_query
                        }

                        # Add error guidance to conversation
                        if conversation_history is None:
                            conversation_history = []

                        error_guidance = self._generate_error_guidance(error, sql_query, attempt + 1)
                        conversation_history.append({'role': 'assistant', 'content': sql_query})
                        conversation_history.append({'role': 'user', 'content': error_guidance})
                        continue
                    else:
                        yield {
                            'type': 'error',
                            'content': f"Query execution failed after {self.max_attempts} attempts: {error}"
                        }
                        return

                # Success! Return results
                yield {
                    'type': 'results',
                    'data': results_df.to_dict('records') if results_df is not None else [],
                    'count': len(results_df) if results_df is not None else 0
                }

                # Generate answer
                yield {'type': 'answer_start'}

                answer_chunks = []
                async for chunk in self.generate_answer_stream(question, sql_query, results_df, conversation_history):
                    answer_chunks.append(chunk)
                    yield {
                        'type': 'answer_chunk',
                        'content': chunk
                    }

                full_answer = ''.join(answer_chunks)
                yield {
                    'type': 'answer_end',
                    'clean_answer': full_answer
                }

                yield {'type': 'done'}
                return

            except Exception as e:
                if attempt < self.max_attempts:
                    logger.error(f"Attempt {attempt} failed: {e}")
                    continue
                else:
                    yield {'type': 'error', 'content': f"Pipeline failed: {e}"}
                    return

# ============================================================================
# INITIALIZE CHATBOT & CV DETECTOR
# ============================================================================

# Initialize chatbot instances
try:
    chatbot = SQLChatbot(db_path=DB_PATH, model=MODEL_NAME)
    agentic_chatbot = AgenticSQLChatbot(db_path=DB_PATH, model=MODEL_NAME)
    logger.info("✓ Chatbot instances initialized")
except Exception as e:
    logger.error(f"❌ Failed to initialize chatbot: {e}")
    raise

# Bird detector removed - now runs client-side with ONNX.js
# Models are served via /models/* endpoints for browser-based inference
logger.info("✓ CV models will run client-side (ONNX.js)")

def get_example_images():
    """Get list of example images from cv_tools/images directory"""
    images_dir = Path(__file__).parent / "cv_tools" / "images"
    if not images_dir.exists():
        return []

    # Get all image files
    image_files = []
    for ext in ['*.jpg', '*.jpeg', '*.png', '*.webp']:
        image_files.extend([f.name for f in images_dir.glob(ext)])

    return sorted(image_files)

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Landing page with stats"""
    try:
        conn = chatbot.get_connection()
        cursor = conn.cursor()

        # Get stats
        cursor.execute("SELECT COUNT(*) FROM observations")
        total_obs = cursor.fetchone()[0]

        cursor.execute("SELECT MIN(year), MAX(year) FROM observations")
        min_year, max_year = cursor.fetchone()

        cursor.execute("SELECT COUNT(DISTINCT colony_name) FROM observations WHERE colony_name != ''")
        total_colonies = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT species_code) FROM observations WHERE species_code != ''")
        total_species = cursor.fetchone()[0]

        conn.close()

        stats = {
            "total_observations": total_obs,
            "min_year": min_year,
            "max_year": max_year,
            "total_colonies": total_colonies,
            "total_species": total_species
        }
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        stats = {
            "total_observations": 0,
            "min_year": 2010,
            "max_year": 2021,
            "total_colonies": 0,
            "total_species": 0
        }

    return templates.TemplateResponse("index.html", {
        "request": request,
        "stats": stats,
        "config": {"model": {"name": config['model']['name']}}
    })

@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    """NestChat interface"""
    return templates.TemplateResponse("chat.html", {
        "request": request,
        "model_name": config['model']['name']
    })

@app.get("/vision", response_class=HTMLResponse)
async def vision_page(request: Request):
    """NestVision interface"""
    return templates.TemplateResponse("vision.html", {
        "request": request
    })

@app.get("/api", response_class=HTMLResponse)
async def api_docs_redirect():
    """Redirect to API documentation"""
    return HTMLResponse(content="""
    <html>
        <head>
            <meta http-equiv="refresh" content="0; url=/docs" />
        </head>
        <body>
            <p>Redirecting to <a href="/docs">API Documentation</a>...</p>
        </body>
    </html>
    """)

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
    """Get server configuration"""
    return {
        "model": {
            "name": config['model']['name'],
            "temperature": config['model']['temperature'],
            "max_tokens": config['model']['max_tokens']
        },
        "cv": {
            "default_confidence": config['cv']['default_confidence']
        }
    }

@app.get("/api/species")
async def get_all_species():
    """Get list of all species from the database"""
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

        # Total observations (bird counts from totals table)
        cursor.execute('SELECT SUM("# Adults") FROM "tblColonyTotals2010-2021_MayJuneCombined"')
        total_obs = cursor.fetchone()[0] or 0

        # Year range
        cursor.execute('SELECT MIN(Year), MAX(Year) FROM "tblColonyTotals2010-2021_MayJuneCombined"')
        min_year, max_year = cursor.fetchone()

        # Total colonies
        cursor.execute('SELECT COUNT(DISTINCT ColonyName) FROM "tblColonyTotals2010-2021_MayJuneCombined" WHERE ColonyName != ""')
        total_colonies = cursor.fetchone()[0]

        # Total species
        cursor.execute('SELECT COUNT(DISTINCT SpeciesCode) FROM "tblColonyTotals2010-2021_MayJuneCombined" WHERE SpeciesCode != ""')
        total_species = cursor.fetchone()[0]

        # States
        cursor.execute('SELECT DISTINCT State FROM "tblColonyTotals2010-2021_MayJuneCombined" WHERE State != "" ORDER BY State')
        states = [row[0] for row in cursor.fetchall()]

        # Observations by year
        cursor.execute('SELECT Year, SUM("# Adults") FROM "tblColonyTotals2010-2021_MayJuneCombined" GROUP BY Year ORDER BY Year')
        obs_by_year = {str(row[0]): int(row[1] or 0) for row in cursor.fetchall()}

        conn.close()

        return {
            "total_observations": total_obs,
            "year_range": f"{min_year}-{max_year}",
            "total_colonies": total_colonies,
            "total_species": total_species,
            "states": states,
            "observations_by_year": obs_by_year
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ask/agentic/stream")
async def ask_question_agentic_stream(request: QuestionRequest):
    """
    Ask a question with agentic self-correction and streaming.
    Returns Server-Sent Events (SSE) with real-time progress.
    """
    async def event_generator():
        try:
            if request.model:
                agentic_chatbot.model = request.model

            async for event in agentic_chatbot.agentic_ask_stream(
                request.question,
                conversation_history=request.conversation_history
            ):
                yield f"data: {json.dumps(event)}\n\n"
                await asyncio.sleep(0)

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

@app.get("/models/swift.onnx")
async def get_detection_model():
    """Serve detection model for client-side inference"""
    model_path = Path(__file__).parent / "models" / "swift.onnx"
    if not model_path.exists():
        raise HTTPException(status_code=404, detail="Detection model not found")
    return FileResponse(model_path, media_type="application/octet-stream")

@app.get("/models/classifier_swift.onnx")
async def get_classifier_model():
    """Serve classifier model for client-side inference"""
    model_path = Path(__file__).parent / "models" / "classifier_swift.onnx"
    if not model_path.exists():
        raise HTTPException(status_code=404, detail="Classifier model not found")
    return FileResponse(model_path, media_type="application/octet-stream")

@app.get("/cv/examples", response_model=ExampleImagesResponse)
async def get_cv_examples():
    """Get list of example images for computer vision"""
    try:
        examples = get_example_images()
        return {"examples": examples}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cv/example/{filename}")
async def get_example_image(filename: str):
    """Get an example image by filename"""
    try:
        images_dir = Path(__file__).parent / "cv_tools" / "images"
        image_path = images_dir / filename

        if not image_path.exists():
            raise HTTPException(status_code=404, detail="Image not found")

        with open(image_path, "rb") as f:
            image_bytes = f.read()

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

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    logger.info(f"🚀 Starting NestScope Public on port {port}")
    logger.info(f"📊 Webapp: http://localhost:{port}")
    logger.info(f"🔌 API Docs: http://localhost:{port}/docs")
    uvicorn.run(app, host="0.0.0.0", port=port)
