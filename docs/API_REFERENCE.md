# API Reference

Technical reference for programmatic access to the Bird Colony Data system.

---

## SQLChatbot Class

Located in: `sql_chatbot.py` and `chatbot.py`

### Initialization

```python
from sql_chatbot import SQLChatbot

chatbot = SQLChatbot(
    db_path="bird_data.db",
    model="anthropic/claude-3.5-sonnet"
)
```

**Parameters:**
- `db_path` (str): Path to SQLite database file (default: "bird_data.db")
- `model` (str): OpenRouter model identifier (default: "anthropic/claude-3.5-sonnet")

---

## Methods

### `ask(question: str) -> str`

Main method to ask questions and get answers.

```python
answer = chatbot.ask("What colonies had oil in 2010?")
```

**Parameters:**
- `question` (str): Natural language question

**Returns:**
- `str`: Natural language answer from Claude, or `None` if error

**Process:**
1. Generates SQL query using LLM
2. Executes query against database
3. Formats results
4. Generates natural language explanation

---

### `generate_sql_query(user_question: str) -> str`

Generate SQL query from natural language.

```python
sql = chatbot.generate_sql_query("Show LAGU observations")
# Returns: "SELECT * FROM observations WHERE species_code = 'LAGU' LIMIT 50;"
```

**Parameters:**
- `user_question` (str): Question in natural language

**Returns:**
- `str`: SQL query string, or "ERROR: ..." if invalid

---

### `execute_query(sql_query: str) -> Tuple[pd.DataFrame, str]`

Execute SQL query and return results.

```python
df, error = chatbot.execute_query("SELECT * FROM species LIMIT 5")
if error:
    print(f"Error: {error}")
else:
    print(df)
```

**Parameters:**
- `sql_query` (str): Valid SQLite query

**Returns:**
- `Tuple[pd.DataFrame, str]`:
  - DataFrame with results (or None if error)
  - Error message (or None if successful)

---

### `generate_answer(user_question: str, sql_query: str, results_df: pd.DataFrame) -> str`

Generate natural language answer from query results.

```python
answer = chatbot.generate_answer(
    user_question="What species are most common?",
    sql_query="SELECT species_code, COUNT(*) FROM observations GROUP BY species_code",
    results_df=results_dataframe
)
```

**Parameters:**
- `user_question` (str): Original question
- `sql_query` (str): SQL query that was executed
- `results_df` (pd.DataFrame): Query results

**Returns:**
- `str`: Natural language explanation

---

### `get_database_schema() -> dict`

Get database schema information.

```python
schema = chatbot.get_database_schema()
print(schema['tables'].keys())  # ['observations', 'colony_profiles', 'species', 'colony_inventory']
```

**Returns:**
- `dict`: Schema information with table names, columns, and sample data

---

### `close()`

Close database connection.

```python
chatbot.close()
```

**Important**: Always call this when done to release resources.

---

## Complete Example Script

```python
from sql_chatbot import SQLChatbot
import pandas as pd

# Initialize
chatbot = SQLChatbot()

# Ask question
answer = chatbot.ask("What colonies had oil in 2010?")
print(answer)

# Generate SQL directly
sql = chatbot.generate_sql_query("Show top 5 species")
print(f"Generated SQL: {sql}")

# Execute and process results
df, error = chatbot.execute_query(sql)
if df is not None:
    print(df.head())
    df.to_csv('results.csv', index=False)

# Clean up
chatbot.close()
```

---

## Direct Database Access

### Using sqlite3

```python
import sqlite3

conn = sqlite3.connect('bird_data.db')
cursor = conn.cursor()

# Execute query
cursor.execute("SELECT * FROM species WHERE species_code = 'LAGU'")
results = cursor.fetchall()

for row in results:
    print(row)

conn.close()
```

### Using pandas

```python
import pandas as pd
import sqlite3

conn = sqlite3.connect('bird_data.db')

# Read query into DataFrame
df = pd.read_sql_query("SELECT * FROM observations WHERE year = 2010", conn)

# Process data
print(df.describe())
print(df.groupby('species_code')['nests'].sum())

conn.close()
```

---

## Database Creation Scripts

### `create_sql_database.py`

Builds database from cleaned CSV files.

```python
# Run from command line
python create_sql_database.py

# Or import and use
from create_sql_database import create_database
create_database()
```

**Output:**
- Creates `bird_data.db`
- Builds indexes
- Runs verification queries

---

### `clean_and_prepare_data.py`

Processes raw CSV files into cleaned format.

```python
# Run from command line
python clean_and_prepare_data.py

# Or import functions
from clean_and_prepare_data import load_csv_files, create_consolidated_observations

dfs = load_csv_files()
observations = create_consolidated_observations(dfs)
```

**Output:**
- `cleaned_data/observations.csv`
- `cleaned_data/colony_profiles.csv`
- `cleaned_data/species_lookup.json`
- `cleaned_data/metadata.json`

---

## Environment Variables

### Required: `.env` file

```bash
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

### Loading in Python

```python
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("OPENROUTER_API_KEY")
```

---

## OpenRouter API

### Model Options

```python
# Fast and cost-effective
chatbot = SQLChatbot(model="anthropic/claude-3-haiku")

# Balanced (default)
chatbot = SQLChatbot(model="anthropic/claude-3.5-sonnet")

# Most capable
chatbot = SQLChatbot(model="anthropic/claude-opus-4-6")
```

### API Costs

Approximate costs per query:
- Haiku: $0.0003 - $0.001
- Sonnet: $0.001 - $0.003
- Opus: $0.01 - $0.03

---

## Error Handling

### Common Errors

**No API Key:**
```python
# Error: "No API key found"
# Solution: Create .env file with OPENROUTER_API_KEY
```

**Database Not Found:**
```python
# Error: "ERROR: Vector database not found!"
# Solution: Run create_sql_database.py
```

**Invalid SQL:**
```python
# Error: "Query error: near ..."
# Solution: Check SQL syntax, use chatbot.generate_sql_query()
```

### Try-Except Pattern

```python
try:
    chatbot = SQLChatbot()
    answer = chatbot.ask("Your question")
    print(answer)
except FileNotFoundError:
    print("Database not found. Run create_sql_database.py")
except Exception as e:
    print(f"Error: {e}")
finally:
    chatbot.close()
```

---

## Performance Optimization

### Query Limits

All queries automatically limited to 50 results:
```sql
-- Chatbot automatically adds:
LIMIT 50
```

Override for specific needs:
```python
sql = "SELECT * FROM observations LIMIT 1000"
df, error = chatbot.execute_query(sql)
```

### Indexes

Pre-built indexes on:
- `observations.year`
- `observations.colony_name`
- `observations.species_code`
- `observations.state`
- `observations.oil_present`

Use these fields in WHERE clauses for fast queries.

---

## Batch Processing

### Multiple Queries

```python
questions = [
    "What colonies had oil in 2010?",
    "Show top 5 species",
    "List colonies in Louisiana"
]

results = []
for q in questions:
    answer = chatbot.ask(q)
    results.append(answer)

# Save results
with open('batch_results.txt', 'w') as f:
    for i, (q, a) in enumerate(zip(questions, results)):
        f.write(f"Q{i+1}: {q}\nA{i+1}: {a}\n\n")
```

### Data Export Pipeline

```python
import pandas as pd

# Define queries
queries = {
    'oil_colonies': "SELECT DISTINCT colony_name FROM observations WHERE oil_present = 'Y'",
    'species_counts': "SELECT species_code, COUNT(*) as count FROM observations GROUP BY species_code",
    'yearly_obs': "SELECT year, COUNT(*) as total FROM observations GROUP BY year"
}

# Execute and export
for name, query in queries.items():
    df, error = chatbot.execute_query(query)
    if df is not None:
        df.to_csv(f'export_{name}.csv', index=False)
        print(f"Exported {name}: {len(df)} rows")
```

---

## Testing

### Unit Tests

```python
import unittest
from sql_chatbot import SQLChatbot

class TestChatbot(unittest.TestCase):
    def setUp(self):
        self.chatbot = SQLChatbot()

    def tearDown(self):
        self.chatbot.close()

    def test_generate_sql(self):
        sql = self.chatbot.generate_sql_query("Show species")
        self.assertIn("SELECT", sql.upper())
        self.assertIn("species", sql.lower())

    def test_execute_query(self):
        df, error = self.chatbot.execute_query("SELECT COUNT(*) FROM species")
        self.assertIsNone(error)
        self.assertIsNotNone(df)

if __name__ == '__main__':
    unittest.main()
```

---

## Integration Examples

### Jupyter Notebook

```python
# Cell 1: Setup
from sql_chatbot import SQLChatbot
import pandas as pd
import matplotlib.pyplot as plt

chatbot = SQLChatbot()

# Cell 2: Query
sql = "SELECT year, COUNT(*) as total FROM observations GROUP BY year"
df, _ = chatbot.execute_query(sql)

# Cell 3: Visualize
plt.plot(df['year'], df['total'])
plt.xlabel('Year')
plt.ylabel('Observations')
plt.title('Observations Over Time')
plt.show()

# Cell 4: Cleanup
chatbot.close()
```

### Web API (Flask)

```python
from flask import Flask, request, jsonify
from sql_chatbot import SQLChatbot

app = Flask(__name__)
chatbot = SQLChatbot()

@app.route('/ask', methods=['POST'])
def ask_question():
    question = request.json.get('question')
    answer = chatbot.ask(question)
    return jsonify({'answer': answer})

if __name__ == '__main__':
    app.run(port=5000)
```

---

## Documentation

- **[README.md](../README.md)** - Project overview
- **[SETUP.md](SETUP.md)** - Installation guide
- **[USAGE.md](USAGE.md)** - User guide
- **[DATA_SCHEMA.md](DATA_SCHEMA.md)** - Database structure
- **[EXAMPLES.md](EXAMPLES.md)** - Example queries

---

## Support

For technical issues:
1. Check error messages
2. Review this API reference
3. Consult [SETUP.md](SETUP.md) for configuration
4. Open GitHub issue if needed

---

**Technical Reference Complete!** For usage examples, see [USAGE.md](USAGE.md)
