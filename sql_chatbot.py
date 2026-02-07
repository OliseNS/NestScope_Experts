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
    def __init__(self, db_path="bird_data.db", model="anthropic/claude-3.5-sonnet"):
        """Initialize the SQL chatbot"""
        self.db_path = db_path
        self.model = model
        self.conn = sqlite3.connect(db_path)
        self.conversation_history = []

        # Load database schema
        self.schema = self.get_database_schema()

        print(f"✓ Connected to database: {db_path}")
        print(f"✓ Using model: {model}")

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

            if len(df) == 0:
                return None, "No results found."

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
        """Main method to ask a question"""

        print(f"\n{'='*80}")
        print(f"Q: {question}")
        print(f"{'='*80}\n")

        # Check if it's a valid question
        if question.lower() in ['quit', 'exit', 'examples', 'stats']:
            return None

        # Step 1: Generate SQL query
        print("🔍 Generating SQL query...")
        sql_query = self.generate_sql_query(question)

        if sql_query.startswith("ERROR"):
            print(f"\n⚠ {sql_query}\n")
            return None

        print(f"📝 SQL: {sql_query}\n")

        # Step 2: Execute query
        print("⚡ Executing query...")
        results_df, error = self.execute_query(sql_query)

        if error:
            print(f"\n❌ {error}\n")
            return None

        print(f"✓ Found {len(results_df)} results\n")

        # Show results preview
        if len(results_df) > 0:
            print("Results preview:")
            print(results_df.head(10).to_string(index=False))
            if len(results_df) > 10:
                print(f"... and {len(results_df) - 10} more rows")
            print()

        # Step 3: Generate natural language answer
        print("🤖 Generating answer...\n")
        answer = self.generate_answer(question, sql_query, results_df)

        print(f"A: {answer}\n")
        print(f"{'='*80}\n")

        return answer

    def interactive_mode(self):
        """Run the chatbot in interactive mode"""
        print("\n" + "="*80)
        print("🐦 BIRD COLONY SQL CHATBOT")
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
                    print("\n👋 Thanks for using the Bird Colony Chatbot!")
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
                print("\n\n👋 Thanks for using the Bird Colony Chatbot!")
                break
            except Exception as e:
                print(f"\nError: {e}\n")

    def show_examples(self):
        """Show example questions"""
        print("\n" + "="*80)
        print("📝 EXAMPLE QUESTIONS")
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
        print("📊 DATABASE STATISTICS")
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
