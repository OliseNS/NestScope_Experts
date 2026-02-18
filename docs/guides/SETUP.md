# Setup Guide

Complete installation and configuration guide for the Bird Colony Data Chatbot.

---

## Prerequisites

### System Requirements
- **Python**: 3.8 or higher
- **Operating System**: Windows, macOS, or Linux
- **Memory**: 2 GB RAM minimum
- **Disk Space**: 50 MB for application + dependencies

### Required Accounts
- **OpenRouter API Key** - Sign up at [openrouter.ai](https://openrouter.ai)

---

## Installation

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd nexus
```

### Step 2: Create Virtual Environment (Recommended)

**On Linux/macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**On Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

**Dependencies installed:**
- `openai` - OpenRouter API client
- `pandas` - Data manipulation
- `python-dotenv` - Environment variable management

---

## Configuration

### API Key Setup

1. **Get OpenRouter API Key**
   - Visit [openrouter.ai/keys](https://openrouter.ai/keys)
   - Sign up or log in
   - Create a new API key
   - Copy your API key

2. **Create `.env` File**

Create a file named `.env` in the project root:

```bash
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

**Important:**
- Never commit `.env` to version control
- The `.gitignore` file already excludes it
- Keep your API key private

3. **Verify Configuration**

```bash
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('✓ API key loaded' if os.getenv('OPENROUTER_API_KEY') else '✗ API key missing')"
```

---

## Database Setup

### Pre-built Database

The database `bird_data.db` is **already included** and ready to use. No setup required!

### Rebuild Database (Optional)

If you need to rebuild the database from source data:

```bash
python create_sql_database.py
```

This will:
1. Load data from `cleaned_data/` directory
2. Create SQLite database `bird_data.db`
3. Create indexes for fast queries
4. Run test queries to verify

**Time**: ~10-30 seconds

### Prepare New Data (Optional)

If you have new raw CSV files in `CSV_Files/`:

```bash
python clean_and_prepare_data.py
```

This will:
1. Process all CSV files from `CSV_Files/`
2. Clean and standardize data
3. Create `cleaned_data/` output files
4. Generate metadata and species lookup

**Time**: ~1-2 minutes

---

## Verification

### Test the Chatbot

```bash
python chatbot.py
```

You should see:
```
✓ Connected to database: bird_data.db
✓ Using model: anthropic/claude-3.5-sonnet

================================================================================
🐦 BIRD COLONY SQL CHATBOT
================================================================================
```

### Test Queries

Type these test queries:
```
stats
What colonies had oil present in 2010?
quit
```

If you see results, everything is working!

---

## Troubleshooting

### "No module named 'openai'"

**Problem**: Dependencies not installed

**Solution**:
```bash
pip install -r requirements.txt
```

### "No API key found" or "401 Unauthorized"

**Problem**: Missing or invalid API key

**Solution**:
1. Check `.env` file exists in project root
2. Verify API key format: `OPENROUTER_API_KEY=sk-or-v1-...`
3. Get a new key from [openrouter.ai/keys](https://openrouter.ai/keys)

### "Database not found"

**Problem**: `bird_data.db` missing

**Solution**:
```bash
python create_sql_database.py
```

### "No such table: colony_inventory"

**Problem**: Database outdated

**Solution**:
```bash
# Rebuild database
python create_sql_database.py

# Then add colony inventory
python -c "
import pandas as pd
import sqlite3

df = pd.read_csv('CSV_Files/tblRWCWB_ColonyInventory_10Nov22.csv')
conn = sqlite3.connect('bird_data.db')
df.to_sql('colony_inventory', conn, if_exists='replace', index=False)
conn.close()
print('✓ Added colony_inventory table')
"
```

### "Memory Error" or Slow Performance

**Problem**: Large query results

**Solution**:
- Queries automatically limit to 50 results
- Ask for specific subsets: "Show 10 colonies in Louisiana"
- Use filters: "Show observations from 2010 only"

### Python Version Issues

**Problem**: Python version too old

**Solution**:
```bash
python3 --version  # Check version
# Should be 3.8 or higher

# Install specific version if needed
pyenv install 3.11.0
pyenv local 3.11.0
```

---

## Optional Setup

### Development Mode

For development with auto-reload:

```bash
pip install watchdog
watchmedo auto-restart --patterns="*.py" --recursive python chatbot.py
```

### IDE Integration

**VS Code:**
1. Install Python extension
2. Select Python interpreter from `.venv`
3. Install recommended extensions (in `.vscode/extensions.json`)

**PyCharm:**
1. File → Settings → Project → Python Interpreter
2. Add `.venv/bin/python` as interpreter
3. Mark `CSV_Files/` and `cleaned_data/` as excluded

---

## Performance Optimization

### For Faster Queries

The database includes pre-built indexes on:
- `observations.year`
- `observations.colony_name`
- `observations.species_code`
- `observations.state`
- `observations.oil_present`

No additional optimization needed!

### API Cost Management

Claude 3.5 Sonnet costs vary:
- Simple queries: $0.001-0.003 per query
- Complex queries: $0.01-0.03 per query

**Tips to reduce costs:**
1. Use specific questions (avoids retries)
2. Limit result counts
3. Cache common queries locally

---

## Next Steps

Once setup is complete:

1. **Read Usage Guide**: [USAGE.md](USAGE.md)
2. **Try Example Queries**: [EXAMPLES.md](EXAMPLES.md)
3. **Learn Data Schema**: [DATA_SCHEMA.md](DATA_SCHEMA.md)
4. **Explore Erosion Analysis**: [EROSION_ANALYSIS.md](EROSION_ANALYSIS.md)

---

## Support

If you encounter issues not covered here:
1. Check [USAGE.md](USAGE.md) for common questions
2. Review [API_REFERENCE.md](API_REFERENCE.md) for technical details
3. Open an issue on GitHub
4. Contact the maintainers

---

**Setup Complete!** 🎉 Start the chatbot with `python chatbot.py`
