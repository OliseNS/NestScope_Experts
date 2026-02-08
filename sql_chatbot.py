"""
Text-to-SQL Bird Colony Chatbot (FINAL VERSION)
- Enhanced map/coordinates handling
- Better prompt rules for geography queries
- Auto-augment coordinates when results have ColonyName but missing lat/lon
- Safer SQL validation
- Prevents LLM from providing external map links
"""

from __future__ import annotations

import os
import re
import json
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Initialize OpenRouter client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)


class SQLChatbot:
    def __init__(self, db_path: Optional[str] = None, model: str = "anthropic/claude-opus-4.5"):
        """
        Initialize the SQL chatbot.
        db_path defaults to env var DB_PATH, fallback to bird_data_complete.db
        """
        if db_path is None:
            db_path = os.getenv("DB_PATH", "bird_data_complete.db")

        self.db_path = db_path
        self.model = model
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conversation_history: List[Dict[str, Any]] = []

        # Load DB schema once (used for prompt + repair)
        self.schema = self.get_database_schema()

    # -------------------------------------------------------------------------
    # Schema
    # -------------------------------------------------------------------------
    def get_database_schema(self) -> Dict[str, Any]:
        """Get database schema for prompt construction."""
        cursor = self.conn.cursor()
        schema_info: Dict[str, Any] = {"tables": {}}

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        for table in tables:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()

            cursor.execute(f"SELECT * FROM {table} LIMIT 3")
            samples = cursor.fetchall()

            schema_info["tables"][table] = {
                "columns": [
                    {
                        "name": col[1],
                        "type": col[2],
                        "notnull": col[3],
                        "pk": col[5],
                    }
                    for col in columns
                ],
                "sample_data": samples,
            }

        return schema_info

    # -------------------------------------------------------------------------
    # SQL safety
    # -------------------------------------------------------------------------
    def validate_sql(self, sql: str) -> Tuple[bool, str, str]:
        """
        Validate SQL query for safety before execution.
        Only allow SELECT or WITH ... SELECT
        Block dangerous keywords.
        Auto-add LIMIT if missing.
        """
        if not sql or not isinstance(sql, str):
            return False, "Empty SQL", sql

        cleaned = sql.strip().rstrip(";")
        upper = cleaned.upper().strip()

        # Allow WITH (CTE) but must contain SELECT
        if upper.startswith("WITH"):
            if "SELECT" not in upper:
                return False, "CTE query without SELECT is not allowed", cleaned
        elif not upper.startswith("SELECT"):
            return False, "Only SELECT queries are allowed for safety", cleaned

        # Hard-block DDL/DML and sqlite PRAGMA/ATTACH
        dangerous = [
            "DROP", "DELETE", "INSERT", "UPDATE", "ALTER",
            "TRUNCATE", "ATTACH", "DETACH", "PRAGMA", "CREATE",
            "REPLACE", "VACUUM"
        ]

        # Block as whole words to avoid false positives
        for kw in dangerous:
            if re.search(rf"\b{kw}\b", upper):
                return False, f"Keyword '{kw}' is not allowed for safety", cleaned

        # Auto add limit if missing
        if "LIMIT" not in upper:
            cleaned = cleaned + " LIMIT 200"
            print("Warning: Auto-added LIMIT 200 to prevent large result set")

        return True, "Valid", cleaned

    # -------------------------------------------------------------------------
    # Prompting
    # -------------------------------------------------------------------------
    def _schema_text(self) -> str:
        schema_desc = []
        for table_name, table_info in self.schema["tables"].items():
            cols = [f"{col['name']} ({col['type']})" for col in table_info["columns"]]
            schema_desc.append(f"\n{table_name}:\n  " + "\n  ".join(cols))
        return "\n".join(schema_desc)

    def _system_prompt(self) -> str:
        schema_text = self._schema_text()

        return f"""You are a SQL query generator for a bird colony observation database tracking Gulf Coast birds from 2010-2021.

DATABASE SCHEMA:
{schema_text}

CORE INTENT:
- Answer questions about bird colonies, species, trends, habitat notes, oil impacts, storms, and erosion.
- Generate VALID SQLite ONLY.

CRITICAL MAP / GEO RULES - READ CAREFULLY:

1. ALWAYS INCLUDE COORDINATES IN SELECT CLAUSE:
   If the user asks about ANY of these topics, you MUST include BOTH Latitude AND Longitude 
   in your SELECT clause (not just use them in WHERE):
   
   Trigger words: "location", "where", "map", "show", "list", "colonies", "geographic", 
   "distribution", "region", "area", "coordinates", "latitude", "longitude", "Gulf", 
   "coast", "coastal", "near", "around", "in Louisiana", "in Texas", "highest", "most", etc.

2. RETURN THE ACTUAL COORDINATE COLUMNS:
   ❌ WRONG: SELECT ColonyName FROM colony_inventory WHERE Latitude IS NOT NULL
   ✅ CORRECT: SELECT ColonyName, Latitude, Longitude FROM colony_inventory WHERE Latitude IS NOT NULL
   
   The user needs the coordinates IN THE RESULTS to see them on a map!

3. PREFERRED COORDINATE SOURCES (in order):
   a) colony_inventory (Latitude, Longitude) - Most complete
   b) colony_totals (Latitude, Longitude) - Has coordinates for most records
   c) colony_coordinates (Latitude, Longitude) - Chandeleur Islands specific

4. USE JOINS TO GET COORDINATES:
   If your main table doesn't have coordinates, LEFT JOIN to get them:
   
   Example:
   SELECT ct.ColonyName, ct.Year, ct.Nests, ci.Latitude, ci.Longitude
   FROM colony_totals ct
   LEFT JOIN colony_inventory ci ON ct.ColonyName = ci.ColonyName
   WHERE ct.State = 'LA'

5. ALWAYS INCLUDE COORDINATES FOR THESE QUERY TYPES:
   - "Show colonies in [location]" → Include Lat/Long
   - "Which colony has [highest/most/...]" → Include Lat/Long
   - "List all colonies" → Include Lat/Long
   - "Geographic distribution" → Include Lat/Long
   - Any question about specific colonies → Include Lat/Long

GENERAL RULES:
1. Generate ONLY valid SQLite queries.
2. Use JOINs when you need species names or to combine tables.
3. Always use LIMIT (default 50; max 200).
4. For "most/top" queries, use ORDER BY and LIMIT.
5. Use LIKE '%keyword%' for text searches in notes (case-insensitive).
6. For erosion analysis: look for colonies present earlier but absent later, or search Notes/AdditionalNotes for:
   "flood", "erosion", "vegetation", "overwash", "washover", "storm", "hurricane".
7. For migration: compare species presence across years and sites (use Year field).
8. Return ONLY the SQL query, no explanations.
9. If the question is unrelated to birds, coasts, habitat monitoring, or environmental data:
   return exactly: ERROR: Not relevant to this dataset

EXAMPLE QUERIES WITH COORDINATES:

Question: "Show colonies in Louisiana"
SQL: SELECT DISTINCT ColonyName, State, Latitude, Longitude
     FROM colony_inventory
     WHERE State = 'LA'
     ORDER BY ColonyName
     LIMIT 200

Question: "What's the geographic distribution of colonies?"
SQL: SELECT ColonyName, State, Latitude, Longitude, GeoRegion
     FROM colony_inventory
     WHERE Latitude IS NOT NULL
     ORDER BY State, GeoRegion
     LIMIT 200

Question: "List all bird colonies"
SQL: SELECT DISTINCT ColonyName, State, Latitude, Longitude
     FROM colony_inventory
     ORDER BY State, ColonyName
     LIMIT 200

Question: "Which colony has the highest number of birds in 2021?"
SQL: SELECT ct.ColonyName, ct.State, ci.Latitude, ci.Longitude, SUM(ct.Birds) as total_birds
     FROM colony_totals ct
     LEFT JOIN colony_inventory ci ON ct.ColonyName = ci.ColonyName
     WHERE ct.Year = 2021
     GROUP BY ct.ColonyName, ct.State, ci.Latitude, ci.Longitude
     ORDER BY total_birds DESC
     LIMIT 10

Question: "Show brown pelican colonies in 2021"
SQL: SELECT ct.ColonyName, ct.State, ci.Latitude, ci.Longitude, SUM(ct.Nests) as total_nests
     FROM colony_totals ct
     LEFT JOIN colony_inventory ci ON ct.ColonyName = ci.ColonyName
     WHERE ct.SpeciesCode = 'BRPE' AND ct.Year = 2021
     GROUP BY ct.ColonyName, ct.State, ci.Latitude, ci.Longitude
     ORDER BY total_nests DESC
     LIMIT 200

Question: "Where is Bay Chaland Island?"
SQL: SELECT ColonyName, State, Latitude, Longitude, GeoRegion
     FROM colony_inventory
     WHERE ColonyName LIKE '%Bay Chaland%'
     LIMIT 10
"""

    def generate_sql_query(self, user_question: str) -> str:
        """Generate SQL query from natural language using LLM."""
        messages = [
            {"role": "system", "content": self._system_prompt()},
            {"role": "user", "content": f"Generate a SQL query for this question: {user_question}"},
        ]

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1,
                max_tokens=500,
            )

            sql_query = response.choices[0].message.content.strip()

            # Strip markdown fences if present
            if sql_query.startswith("```sql"):
                sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
            elif sql_query.startswith("```"):
                sql_query = sql_query.replace("```", "").strip()

            return sql_query

        except Exception as e:
            return f"ERROR: {e}"

    # -------------------------------------------------------------------------
    # Repair
    # -------------------------------------------------------------------------
    def repair_sql(self, sql_query: str, error_message: str) -> Optional[str]:
        """Ask the model to fix broken SQL query."""
        schema_text = self._schema_text()

        repair_prompt = f"""The following SQL query failed with an error. Please fix it.

FAILED SQL:
{sql_query}

ERROR MESSAGE:
{error_message}

DATABASE SCHEMA:
{schema_text}

RULES FOR FIXED QUERY:
1. Use ONLY columns that exist in the schema above.
2. Use proper SQLite syntax.
3. Always include LIMIT (max 200 rows).
4. Use correct table names and JOIN syntax.
5. If the query was about locations, include Latitude and Longitude in SELECT.
6. Return ONLY the corrected SQL query, no explanation.

Generate the fixed SQL query:"""

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": repair_prompt}],
                temperature=0.1,
                max_tokens=500,
            )

            fixed_sql = response.choices[0].message.content.strip()

            if fixed_sql.startswith("```sql"):
                fixed_sql = fixed_sql.replace("```sql", "").replace("```", "").strip()
            elif fixed_sql.startswith("```"):
                fixed_sql = fixed_sql.replace("```", "").strip()

            return fixed_sql

        except Exception as e:
            print(f"Could not repair SQL: {e}")
            return None

    # -------------------------------------------------------------------------
    # Execute
    # -------------------------------------------------------------------------
    def execute_query(self, sql_query: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """Execute SQL query and return (df, error)."""
        try:
            df = pd.read_sql_query(sql_query, self.conn)
            return df, None
        except Exception as e:
            return None, f"Query error: {e}"

    # -------------------------------------------------------------------------
    # Map augmentation (KEY FEATURE)
    # -------------------------------------------------------------------------
    def _find_lat_lon_cols(self, df: pd.DataFrame) -> Tuple[Optional[str], Optional[str]]:
        """Find latitude and longitude column names (case-insensitive)."""
        lat_col = next((c for c in df.columns if "lat" in c.lower()), None)
        lon_col = next((c for c in df.columns if "lon" in c.lower() or "lng" in c.lower()), None)
        return lat_col, lon_col

    def augment_with_coordinates(self, df: pd.DataFrame, max_names: int = 200) -> pd.DataFrame:
        """
        If df has ColonyName but no lat/lon, left-join coords from colony_inventory.
        This makes your Streamlit map tab appear much more often.
        """
        if df is None or df.empty:
            return df

        # If already has coords, do nothing
        lat_col, lon_col = self._find_lat_lon_cols(df)
        if lat_col and lon_col:
            return df

        # Must have ColonyName to join
        if "ColonyName" not in df.columns:
            return df

        colony_names = df["ColonyName"].dropna().astype(str).unique().tolist()
        if not colony_names:
            return df

        colony_names = colony_names[:max_names]

        # Build SQL IN clause with proper escaping
        quoted_names = []
        for name in colony_names:
            # Convert to string and escape single quotes
            name_str = str(name)
            escaped_name = name_str.replace("'", "''")
            quoted_names.append(f"'{escaped_name}'")

        quoted = ",".join(quoted_names)

        sql = f"""
        SELECT ColonyName, Latitude, Longitude
        FROM colony_inventory
        WHERE ColonyName IN ({quoted})
        """

        try:
            coord_df, err = self.execute_query(sql)

            if err or coord_df is None or coord_df.empty:
                return df

            # Merge coordinates into original dataframe
            merged = df.merge(coord_df, on="ColonyName", how="left")
            return merged

        except Exception as e:
            print(f"Warning: Could not augment coordinates: {e}")
            return df

    # -------------------------------------------------------------------------
    # Answer generation
    # -------------------------------------------------------------------------
    def generate_answer(self, user_question: str, sql_query: str, results_df: pd.DataFrame) -> str:
        """Generate natural language answer from query results."""
        if results_df is not None and len(results_df) > 0:
            results_text = results_df.to_string(index=False, max_rows=50)
            row_count = len(results_df)
        else:
            results_text = "No results found."
            row_count = 0

        # Check if results have coordinates
        has_coords = False
        if results_df is not None and not results_df.empty:
            lat_col = next((c for c in results_df.columns if "lat" in c.lower()), None)
            lon_col = next((c for c in results_df.columns if "lon" in c.lower() or "lng" in c.lower()), None)
            has_coords = lat_col is not None and lon_col is not None

        system_prompt = """You are a helpful assistant that explains bird colony data query results.

Your task is to:
1. Answer the user's question based on the SQL query results
2. Provide specific details from the data (names, numbers, etc.)
3. Highlight interesting patterns or insights
4. Use a conversational but informative tone
5. If there are no results, explain why that might be

CRITICAL RULES FOR GEOGRAPHIC DATA:
- If the results include Latitude and Longitude columns, an INTERACTIVE MAP will be 
  automatically displayed in the Streamlit interface
- DO NOT provide Google Maps links, OpenStreetMap links, or any external map URLs
- DO NOT say "You can view this on Google Maps" or similar phrases
- DO NOT create ASCII maps or attempt to visualize the map yourself
- Simply describe the location in text (e.g., "Located at 29.23°N, 90.63°W in coastal Louisiana")
- The map will appear automatically in a "Map View" tab or inline below your answer
- Focus on describing what the data shows, not how to visualize it"""

        user_content = f"""Question: {user_question}

SQL Query Used:
{sql_query}

Query Results ({row_count} rows):
{results_text}

{"Note: These results include geographic coordinates, so an interactive map will be shown automatically." if has_coords else ""}

Please provide a clear, informative answer to the question based on these results."""

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.7,
                max_tokens=1000,
            )

            answer = response.choices[0].message.content

            self.conversation_history.append(
                {"question": user_question, "sql_query": sql_query, "answer": answer}
            )

            return answer
        except Exception as e:
            return f"Error generating answer: {e}"

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------
    def query(self, question: str) -> Dict[str, Any]:
        """
        Frontend-friendly API method for Streamlit integration.
        Returns:
          {success, error, sql, results, answer, row_count}
        """
        if not question or not isinstance(question, str):
            return {
                "success": False,
                "error": "Empty question",
                "sql": None,
                "results": None,
                "answer": None,
                "row_count": 0,
            }

        if question.lower() in ["quit", "exit", "examples", "stats"]:
            return {
                "success": False,
                "error": "Command not supported in API mode",
                "sql": None,
                "results": None,
                "answer": None,
                "row_count": 0,
            }

        try:
            # Step 1: Generate SQL
            sql_query = self.generate_sql_query(question)
            if sql_query.startswith("ERROR"):
                return {
                    "success": False,
                    "error": sql_query,
                    "sql": None,
                    "results": None,
                    "answer": None,
                    "row_count": 0,
                }

            # Step 2: Validate SQL
            is_valid, msg, safe_sql = self.validate_sql(sql_query)
            if not is_valid:
                return {
                    "success": False,
                    "error": f"Validation failed: {msg}",
                    "sql": safe_sql,
                    "results": None,
                    "answer": None,
                    "row_count": 0,
                }

            # Step 3: Execute
            results_df, err = self.execute_query(safe_sql)

            # Repair once if needed
            if err:
                fixed = self.repair_sql(safe_sql, err)
                if fixed:
                    ok2, msg2, fixed2 = self.validate_sql(fixed)
                    if ok2:
                        results_df, err = self.execute_query(fixed2)
                        if not err:
                            safe_sql = fixed2

            if err:
                return {
                    "success": False,
                    "error": f"Query execution failed: {err}",
                    "sql": safe_sql,
                    "results": None,
                    "answer": None,
                    "row_count": 0,
                }

            # Step 3.5: Augment coords if missing (so map works more often)
            if results_df is not None and not results_df.empty:
                results_df = self.augment_with_coordinates(results_df)

            # Step 4: Answer
            answer = self.generate_answer(question, safe_sql, results_df)

            row_count = len(results_df) if results_df is not None else 0
            return {
                "success": True,
                "error": None,
                "sql": safe_sql,
                "results": results_df.to_dict("records") if results_df is not None and row_count > 0 else [],
                "answer": answer,
                "row_count": row_count,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "sql": None,
                "results": None,
                "answer": None,
                "row_count": 0,
            }

    # Optional interactive (kept, simpler)
    def interactive_mode(self) -> None:
        print("\n" + "=" * 80)
        print("BIRD COLONY SQL CHATBOT")
        print("=" * 80)
        print("\nAsk questions about bird colonies (2010-2021). Type 'quit' to exit.\n")
        print("=" * 80 + "\n")

        while True:
            try:
                q = input("Your question: ").strip()
                if not q:
                    continue
                if q.lower() in ["quit", "exit", "q"]:
                    print("\nBye!\n")
                    break

                resp = self.query(q)
                if not resp["success"]:
                    print(f"\nError: {resp['error']}\n")
                    continue

                print("\nSQL:")
                print(resp["sql"])
                print("\nAnswer:")
                print(resp["answer"])
                print("\nRows:", resp["row_count"])
                print("\n" + "-" * 80 + "\n")

            except KeyboardInterrupt:
                print("\n\nBye!\n")
                break
            except Exception as e:
                print(f"\nError: {e}\n")

    def close(self) -> None:
        self.conn.close()


def main():
    bot = SQLChatbot()
    try:
        bot.interactive_mode()
    finally:
        bot.close()


if __name__ == "__main__":
    main()