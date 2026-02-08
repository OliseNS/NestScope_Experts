"""
FastAPI Server for Text-to-SQL Bird Colony Chatbot
Provides REST API endpoints for querying bird colony data
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import sqlite3
import pandas as pd
from openai import OpenAI
import os
from dotenv import load_dotenv
import json
import asyncio

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
    model: Optional[str] = "anthropic/claude-opus-4.5"

class QueryResponse(BaseModel):
    sql_query: str
    results: Optional[List[Dict[str, Any]]]
    results_count: int
    answer: str
    error: Optional[str] = None

class SchemaResponse(BaseModel):
    tables: Dict[str, Any]

class StatsResponse(BaseModel):
    total_observations: int
    year_range: str
    total_colonies: int
    total_species: int
    states: List[str]
    observations_by_year: Dict[str, int]

# Database configuration
DB_PATH = os.getenv("DB_PATH", "../bird_data_complete.db")

class SQLChatbot:
    def __init__(self, db_path=DB_PATH, model="anthropic/claude-opus-4.5", prompt_path="server/prompt.txt"):
        """Initialize the SQL chatbot"""
        self.db_path = db_path
        self.model = model
        self.schema = None
        self.prompt_path = prompt_path
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

    def generate_sql_query(self, user_question):
        """Generate SQL query from natural language using LLM"""
        # Use the system prompt loaded from prompt.txt
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"""Question: {user_question}

IMPORTANT: Return ONLY the SQL query, nothing else. No explanations, no markdown formatting, no comments - just the raw SQL query that can be executed directly."""}
        ]

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

    def generate_answer(self, user_question, sql_query, results_df, query_error=None):
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

Your task is to:
1. Answer the user's question based on the SQL query results
2. Provide specific details from the data (names, numbers, etc.)
3. Highlight interesting patterns or insights
4. Use a conversational but informative tone
5. If there are no results, explain why that might be
6. If there's a query error, explain what went wrong in simple terms and suggest how to fix it"""

        user_content = f"""Question: {user_question}

SQL Query Used:
{sql_query}

Query Results ({row_count} rows):
{results_text}

Please provide a clear, informative answer to the question based on these results."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

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

    def generate_answer_stream(self, user_question, sql_query, results_df, query_error=None):
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

Your task is to:
1. Answer the user's question based on the SQL query results
2. Provide specific details from the data (names, numbers, etc.)
3. Highlight interesting patterns or insights
4. Use a conversational but informative tone
5. If there are no results, explain why that might be
6. If there's a query error, explain what went wrong in simple terms and suggest how to fix it"""

        user_content = f"""Question: {user_question}

SQL Query Used:
{sql_query}

Query Results ({row_count} rows):
{results_text}

Please provide a clear, informative answer to the question based on these results."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

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

# Initialize chatbot
chatbot = SQLChatbot()

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
        # Update model if provided
        chatbot.model = request.model

        # Step 1: Generate SQL query
        sql_query = chatbot.generate_sql_query(request.question)

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

        # Step 3: Generate natural language answer (handles both success and error cases)
        answer = chatbot.generate_answer(request.question, sql_query, results_df, query_error=error)

        return QueryResponse(
            sql_query=sql_query,
            results=results,
            results_count=results_count,
            answer=answer,
            error=error  # Still include error for debugging, but answer will explain it
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
            # Update model if provided
            chatbot.model = request.model

            # Step 1: Generate SQL query
            sql_query = chatbot.generate_sql_query(request.question)

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

            # Step 3: Stream the answer (handles both success and error cases)
            yield f"data: {json.dumps({'type': 'answer_start'})}\n\n"

            for chunk in chatbot.generate_answer_stream(request.question, sql_query, results_df, query_error=error):
                yield f"data: {json.dumps({'type': 'answer_chunk', 'content': chunk})}\n\n"
                await asyncio.sleep(0)  # Allow other tasks to run

            yield f"data: {json.dumps({'type': 'answer_end'})}\n\n"
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
