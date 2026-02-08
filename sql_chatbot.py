"""
Text-to-SQL Bird Colony Chatbot
Converts natural language questions to SQL queries and answers based on results
"""

import sqlite3
import pandas as pd
from openai import OpenAI
import os
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Initialize OpenRouter client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

class SQLChatbot:
    def __init__(self, db_path=None, model="anthropic/claude-opus-4.5"):
        """Initialize the SQL chatbot"""
        # Use environment variable or provided path, fallback to bird_data_complete.db
        if db_path is None:
            db_path = os.getenv("DB_PATH", "bird_data_complete.db")

        self.db_path = db_path
        self.model = model
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conversation_history = []

        # Load database schema
        self.schema = self.get_database_schema()

        pass

    def get_database_schema(self):
        """Get the database schema for the LLM"""
        cursor = self.conn.cursor()

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

        return schema_info

    def validate_sql(self, sql):
        """Validate SQL query for safety before execution"""
        sql_upper = sql.upper().strip()

        # Only allow SELECT queries
        if not sql_upper.startswith('SELECT'):
            return False, "Only SELECT queries are allowed for safety", sql

        # Block dangerous keywords
        dangerous_keywords = [
            'DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER',
            'TRUNCATE', 'ATTACH', 'DETACH', 'PRAGMA', 'CREATE'
        ]

        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                return False, f"Keyword '{keyword}' is not allowed for safety", sql

        # Auto-add LIMIT if missing (prevent huge result sets)
        if 'LIMIT' not in sql_upper:
            sql = sql.rstrip(';') + ' LIMIT 200'
            print("Warning: Auto-added LIMIT 200 to prevent large result set")

        return True, "Valid", sql

    def repair_sql(self, sql_query, error_message):
        """Ask Claude to fix broken SQL query"""

        print("Attempting to repair SQL query...")

        # Create schema description for repair
        schema_desc = []
        for table_name, table_info in self.schema['tables'].items():
            cols = [f"{col['name']} ({col['type']})" for col in table_info['columns']]
            schema_desc.append(f"\n{table_name}:\n  " + "\n  ".join(cols))
        schema_text = "\n".join(schema_desc)

        repair_prompt = f"""The following SQL query failed with an error. Please fix it.

FAILED SQL:
{sql_query}

ERROR MESSAGE:
{error_message}

DATABASE SCHEMA:
{schema_text}

RULES FOR FIXED QUERY:
1. Use ONLY columns that exist in the schema above
2. Use proper SQLite syntax
3. Always include LIMIT (max 200 rows)
4. Use correct table names and JOIN syntax
5. Return ONLY the corrected SQL query, no explanation

Generate the fixed SQL query:"""

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": repair_prompt}],
                temperature=0.1,
                max_tokens=500
            )

            fixed_sql = response.choices[0].message.content.strip()

            # Clean up markdown if present
            if fixed_sql.startswith("```sql"):
                fixed_sql = fixed_sql.replace("```sql", "").replace("```", "").strip()
            elif fixed_sql.startswith("```"):
                fixed_sql = fixed_sql.replace("```", "").strip()

            print(f"Repaired SQL: {fixed_sql}")
            return fixed_sql

        except Exception as e:
            print(f"Could not repair SQL: {e}")
            return None

    def generate_sql_query(self, user_question):
        """Generate SQL query from natural language using LLM"""

        # Create schema description
        schema_desc = []
        for table_name, table_info in self.schema['tables'].items():
            cols = [f"{col['name']} ({col['type']})" for col in table_info['columns']]
            schema_desc.append(f"\n{table_name}:\n  " + "\n  ".join(cols))

        schema_text = "\n".join(schema_desc)

        system_prompt = f"""You are a SQL query generator for a bird colony observation database tracking Gulf Coast birds from 2010-2021.

DATABASE SCHEMA:
{schema_text}

IMPORTANT NOTES:
- observations table: Individual observation records with notes, habitat, species, location data
  - year: Year of observation (2010-2021)
  - colony_name: Name of the bird colony
  - species_code: 4-letter species code (e.g., LAGU, BRPE, TRHE)
  - state: Two-letter state code (TX, LA, MS, AL, FL)
  - oil_present: 'Y' or 'N' indicating oil presence from Deepwater Horizon spill
  - habitat: Text description of habitat
  - notes: Detailed observation notes (may mention erosion, flooding, hurricanes, habitat changes)
  - combined_text: Full text combining habitat, notes, and additional notes

- colony_profiles table: Aggregated data per colony
  - colony_name, years_observed, states, species_observed, total_observations
  - aggregated_notes: Combined notes from all years showing habitat changes over time

- colony_inventory table: Master list of all colonies with geographic/habitat data
  - ColonyName, State, Longitude, Latitude
  - ActiveInventory: 'Yes' or 'No' (indicates if colony still active)
  - PrimaryHabitat, LandForm: Habitat classification
  - GeoRegion, TerrestEcoRegion, MarineEcoRegion: Geographic classifications
  - Use this to identify lost/inactive colonies for erosion analysis

- species table: Species code to name lookup
  - species_code: 4-letter code, species_name: Full species name

IMPORTANT: This database can answer questions about:
1. Bird populations and species (primary purpose)
2. COASTAL EROSION PATTERNS (colonies lost, habitat changes, island degradation)
3. MIGRATION PATTERNS (species presence/absence over time, seasonal timing)
4. Oil spill impacts (2010 Deepwater Horizon)
5. Storm/hurricane impacts (notes mention flooding, overwash, vegetation loss)

RULES:
1. Generate ONLY valid SQLite queries
2. Use JOINs when you need species names or to combine tables
3. Always use LIMIT to prevent huge results (default 50)
4. For "most" or "top" queries, use ORDER BY and LIMIT
5. Use LIKE '%keyword%' for text searches in notes (case-insensitive)
6. For erosion analysis: look for colonies present in early years but absent later, search notes for "flood", "erosion", "vegetation", "overwash"
7. For migration: compare species presence across years/seasons

EXAMPLE QUERIES:
Question: "Top 5 most observed species"
SQL: SELECT species_code, COUNT(*) as observation_count FROM observations GROUP BY species_code ORDER BY observation_count DESC LIMIT 5

Question: "Colonies that disappeared by 2021"
SQL: SELECT ColonyName, State FROM colony_inventory WHERE ActiveInventory = 'No' LIMIT 100

Question: "Brown Pelican observations in Louisiana"
SQL: SELECT year, colony_name, COUNT(*) as count FROM observations WHERE species_code = 'BRPE' AND state = 'LA' GROUP BY year, colony_name ORDER BY year LIMIT 200

Question: "Colonies with oil present in 2010"
SQL: SELECT DISTINCT colony_name, state FROM observations WHERE oil_present = 'Y' AND year = 2010 LIMIT 50

8. Return ONLY the SQL query, no explanations
9. If the question is completely unrelated to birds, coasts, or environmental data, return: ERROR: Not relevant to this dataset"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Generate a SQL query for this question: {user_question}"}
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
                sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
            elif sql_query.startswith("```"):
                sql_query = sql_query.replace("```", "").strip()

            return sql_query

        except Exception as e:
            return f"ERROR: {e}"

    def execute_query(self, sql_query):
        """Execute SQL query and return results"""
        try:
            # Execute query
            df = pd.read_sql_query(sql_query, self.conn)

            # Return empty dataframe, not an error - let AI explain the empty result
            return df, None

        except Exception as e:
            return None, f"Query error: {e}"

    def generate_answer(self, user_question, sql_query, results_df):
        """Generate natural language answer from query results"""

        # Format results for LLM
        if results_df is not None and len(results_df) > 0:
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
5. If there are no results, explain why that might be"""

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

            # Store in conversation history
            self.conversation_history.append({
                "question": user_question,
                "sql_query": sql_query,
                "answer": answer
            })

            return answer

        except Exception as e:
            return f"Error generating answer: {e}"

    def ask(self, question):
        """Main method to ask a question - now with validation and repair"""

        print(f"\n{'=' * 80}")
        print(f"Q: {question}")
        print(f"{'=' * 80}\n")

        # Check if it's a command
        if question.lower() in ['quit', 'exit', 'examples', 'stats']:
            return None

        # Step 1: Generate SQL query
        print("Generating SQL query...")
        sql_query = self.generate_sql_query(question)

        if sql_query.startswith("ERROR"):
            print(f"\nError: {sql_query}\n")
            return None

        print(f"Generated SQL: {sql_query}\n")

        # Step 2: Validate the SQL query
        print("Validating SQL for safety...")
        is_valid, message, sql_query = self.validate_sql(sql_query)

        if not is_valid:
            print(f"Validation failed: {message}\n")
            return f"Sorry, I couldn't generate a safe query: {message}"

        # print(f"SQL is safe to execute\n")
        #
        # # Step 3: Execute query with retry
        # print("Executing query...")
        results_df, error = self.execute_query(sql_query)

        # If query failed, try to repair it
        if error:
            print(f"Query failed: {error}")

            # Attempt one repair
            fixed_sql = self.repair_sql(sql_query, error)

            if fixed_sql:
                # Validate the repaired SQL
                is_valid, message, fixed_sql = self.validate_sql(fixed_sql)

                if is_valid:
                    print("Retrying with repaired SQL...")
                    results_df, error = self.execute_query(fixed_sql)

                    if error:
                        print(f"\nRepaired query also failed: {error}\n")
                        return f"Sorry, I couldn't execute that query even after repair. Error: {error}"
                    else:
                        sql_query = fixed_sql
                else:
                    print(f"Repaired SQL failed validation: {message}\n")
                    return f"Sorry, the repaired query was not safe: {message}"
            else:
                print(f"\nCould not repair query\n")
                return f"Sorry, I couldn't execute that query. Error: {error}"

        result_count = len(results_df) if results_df is not None else 0
        print(f"Found {result_count} results\n")

        # Show results preview
        if result_count > 0:
            print("Results preview:")
            print(results_df.head(10).to_string(index=False))
            if result_count > 10:
                print(f"... and {result_count - 10} more rows")
            print()
        else:
            print("Query returned no results. Generating explanation...\n")

        # Step 4: Generate natural language answer (AI will explain empty results)
        print("Generating answer...\n")
        answer = self.generate_answer(question, sql_query, results_df)

        print(f"A: {answer}\n")
        print(f"{'=' * 80}\n")

        return answer

    def query(self, question):
        """
        Frontend-friendly API method
        Returns structured response for Streamlit integration
        """

        # Check if it's a command
        if question.lower() in ['quit', 'exit', 'examples', 'stats']:
            return {
                'success': False,
                'error': 'Command not supported in API mode',
                'sql': None,
                'results': None,
                'answer': None,
                'row_count': 0
            }

        try:
            # Step 1: Generate SQL
            sql_query = self.generate_sql_query(question)

            if sql_query.startswith("ERROR"):
                return {
                    'success': False,
                    'error': sql_query,
                    'sql': None,
                    'results': None,
                    'answer': None,
                    'row_count': 0
                }

            # Step 2: Validate SQL
            is_valid, message, sql_query = self.validate_sql(sql_query)

            if not is_valid:
                return {
                    'success': False,
                    'error': f"Validation failed: {message}",
                    'sql': sql_query,
                    'results': None,
                    'answer': None,
                    'row_count': 0
                }

            # Step 3: Execute query
            results_df, error = self.execute_query(sql_query)

            # If query failed, try to repair
            if error:
                fixed_sql = self.repair_sql(sql_query, error)

                if fixed_sql:
                    is_valid, message, fixed_sql = self.validate_sql(fixed_sql)

                    if is_valid:
                        results_df, error = self.execute_query(fixed_sql)

                        if not error:
                            sql_query = fixed_sql

            # If still errored after repair
            if error:
                return {
                    'success': False,
                    'error': f"Query execution failed: {error}",
                    'sql': sql_query,
                    'results': None,
                    'answer': None,
                    'row_count': 0
                }

            # Step 4: Generate answer (AI will explain if results are empty)
            answer = self.generate_answer(question, sql_query, results_df)

            # Return structured response (empty results are valid, not errors)
            row_count = len(results_df) if results_df is not None else 0
            return {
                'success': True,
                'error': None,
                'sql': sql_query,
                'results': results_df.to_dict('records') if results_df is not None and row_count > 0 else [],
                'answer': answer,
                'row_count': row_count
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'sql': None,
                'results': None,
                'answer': None,
                'row_count': 0
            }

    def interactive_mode(self):
        """Run the chatbot in interactive mode"""
        print("\n" + "="*80)
        print("BIRD COLONY SQL CHATBOT")
        print("="*80)
        print("\nI can answer questions about bird colony observations from 2010-2021")
        print("I'll convert your questions to SQL queries and explain the results.\n")
        print("Commands:")
        print("  - Type your question and press Enter")
        print("  - Type 'examples' to see example questions")
        print("  - Type 'stats' to see database statistics")
        print("  - Type 'quit' or 'exit' to end the session\n")
        print("="*80 + "\n")

        while True:
            try:
                question = input("Your question: ").strip()

                if not question:
                    continue

                if question.lower() in ['quit', 'exit', 'q']:
                    print("\nThanks for using the Bird Colony Chatbot!")
                    break

                if question.lower() == 'examples':
                    self.show_examples()
                    continue

                if question.lower() == 'stats':
                    self.show_stats()
                    continue

                # Process the question
                self.ask(question)

            except KeyboardInterrupt:
                print("\n\nThanks for using the Bird Colony Chatbot!")
                break
            except Exception as e:
                print(f"\nError: {e}\n")

    def show_examples(self):
        """Show example questions"""
        print("\n" + "="*80)
        print("EXAMPLE QUESTIONS")
        print("="*80)
        examples = [
            "What colonies had oil present in 2010?",
            "Which species were observed most frequently?",
            "Show me observations from Chandeleur Islands",
            "What are the top 5 colonies by number of observations?",
            "How many observations are there per year?",
            "List all colonies in Louisiana",
            "What species were seen at Breton Island?",
            "Show me all BLSK (Black Skimmer) observations",
            "What habitats are mentioned for colonies in Mississippi?",
            "Which colonies have the most species diversity?",
            "Show observations with oil present after 2010",
            "What are the most common habitat types?"
        ]

        for i, example in enumerate(examples, 1):
            print(f"  {i}. {example}")

        print("="*80 + "\n")

    def show_stats(self):
        """Show database statistics"""
        print("\n" + "="*80)
        print("DATABASE STATISTICS")
        print("="*80)

        cursor = self.conn.cursor()

        # Total observations
        cursor.execute("SELECT COUNT(*) FROM observations")
        total_obs = cursor.fetchone()[0]
        print(f"Total Observations: {total_obs:,}")

        # Year range
        cursor.execute("SELECT MIN(year), MAX(year) FROM observations")
        min_year, max_year = cursor.fetchone()
        print(f"Year Range: {int(min_year)}-{int(max_year)}")

        # Total colonies
        cursor.execute("SELECT COUNT(DISTINCT colony_name) FROM observations WHERE colony_name != ''")
        total_colonies = cursor.fetchone()[0]
        print(f"Total Colonies: {total_colonies}")

        # Total species
        cursor.execute("SELECT COUNT(*) FROM species")
        total_species = cursor.fetchone()[0]
        print(f"Total Species: {total_species}")

        # States
        cursor.execute("SELECT DISTINCT state FROM observations WHERE state != '' ORDER BY state")
        states = [row[0] for row in cursor.fetchall()]
        print(f"States: {', '.join(states)}")

        # Observations by year
        print("\nObservations by Year:")
        cursor.execute("""
            SELECT year, COUNT(*) as count
            FROM observations
            GROUP BY year
            ORDER BY year
        """)
        for year, count in cursor.fetchall():
            print(f"  {int(year)}: {count:,}")

        print("="*80 + "\n")

    def close(self):
        """Close database connection"""
        self.conn.close()

def main():
    """Main entry point"""

    # Initialize chatbot
    try:
        chatbot = SQLChatbot()
    except Exception as e:
        print(f"Error initializing chatbot: {e}")
        return

    # Run in interactive mode
    try:
        chatbot.interactive_mode()
    finally:
        chatbot.close()

if __name__ == '__main__':
    main()