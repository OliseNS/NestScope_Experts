# Usage Guide

How to use the Bird Colony Data Chatbot for research and analysis.

---

## Starting the Chatbot

```bash
python chatbot.py
```

You'll see the welcome screen:
```
================================================================================
🐦 BIRD COLONY SQL CHATBOT
================================================================================

I can answer questions about bird colony observations from 2010-2021
I'll convert your questions to SQL queries and explain the results.

Commands:
  - Type your question and press Enter
  - Type 'examples' to see example questions
  - Type 'stats' to see database statistics
  - Type 'quit' or 'exit' to end the session

================================================================================
```

---

## Basic Usage

### Asking Questions

Just type your question in natural language:

```
Your question: What colonies had oil present in 2010?
```

The chatbot will:
1. **Generate SQL** - Creates an appropriate SQL query
2. **Execute Query** - Runs it against the database
3. **Show Results** - Displays data preview
4. **Explain Answer** - Provides natural language explanation

### Example Session

```
Your question: What colonies had oil present in 2010?

================================================================================
Q: What colonies had oil present in 2010?
================================================================================

🔍 Generating SQL query...
📝 SQL: SELECT DISTINCT colony_name, state, geo_region
FROM observations
WHERE oil_present = 'Y' AND year = 2010
ORDER BY state, colony_name
LIMIT 50;

⚡ Executing query...
✓ Found 5 results

Results preview:
       colony_name state geo_region
Chandeleur South C  None       None
   Gaillard Island  None       None
    Manilla Island  None       None
     Martin Island  None       None
 Queen Bess Island  None       None

🤖 Generating answer...

A: Based on the query results, there were 5 colonies that had oil present in
2010: Chandeleur South C, Gaillard Island, Manilla Island, Martin Island, and
Queen Bess Island. These are known Louisiana colonies affected by the Deepwater
Horizon oil spill...

================================================================================
```

---

## Commands

### `examples` - See Example Questions

```
Your question: examples
```

Shows 12 example questions covering different analysis types.

### `stats` - View Database Statistics

```
Your question: stats
```

Displays:
- Total observations
- Year range
- Number of colonies
- Number of species
- States covered
- Observations per year

### `quit` or `exit` - End Session

```
Your question: quit
```

Closes the chatbot and database connection.

---

## Query Types

### 1. Bird Population Queries

**Species Counts:**
```
Which species were observed most frequently?
How many Brown Pelican observations are there?
Show me all BLSK (Black Skimmer) observations
```

**Colony-Specific:**
```
What species were seen at Breton Island?
Show observations from Chandeleur Islands
List colonies in Louisiana
```

**Temporal:**
```
How many observations per year?
Show observations from 2015 to 2021
What species were present in 2010 vs 2021?
```

### 2. Coastal Erosion Queries

**Colony Loss:**
```
Which colonies were active in 2010 but disappeared by 2021?
What percentage of 2010 colonies are still active?
List inactive colonies
```

**Habitat Change:**
```
Show colonies with notes mentioning erosion
Which colonies experienced flooding?
Show observations with vegetation loss
How did habitats change at Cat Bay South Island?
```

**Geographic Patterns:**
```
Which barrier islands show the most degradation?
What colonies in Mississippi were lost?
Show erosion patterns by state
```

### 3. Environmental Impact Queries

**Oil Spill:**
```
What colonies had oil present in 2010?
Show observations with oil after 2010
Compare oil-affected vs non-affected colonies
```

**Storm Damage:**
```
Which colonies were affected by Hurricane Isaac?
Show observations mentioning storms or hurricanes
List colonies with overwash events
```

**Habitat Types:**
```
What are the most common habitat types?
Show colonies with mangrove habitats
Which habitats have decreased over time?
```

### 4. Migration Pattern Queries

**Species Presence:**
```
Which species appear in different years?
Show seasonal patterns for Royal Terns
What species stopped nesting at certain colonies?
```

**Temporal Patterns:**
```
Compare species diversity 2010 vs 2021
Show species that increased in abundance
Which species disappeared from colonies?
```

---

## Tips for Better Results

### Be Specific

**Good:**
```
Show Brown Pelican observations from Louisiana in 2010
```

**Less Effective:**
```
Tell me about birds
```

### Use Species Codes

If you know the 4-letter species codes:
```
Show LAGU observations
List colonies with BRPE and TRHE
```

**Common codes:**
- LAGU = Laughing Gull
- BRPE = Brown Pelican
- TRHE = Tricolored Heron
- ROYT = Royal Tern
- BLSK = Black Skimmer

See [DATA_SCHEMA.md](DATA_SCHEMA.md) for full species list.

### Limit Results

For large queries, ask for top N:
```
What are the top 10 colonies by observation count?
Show me 5 colonies in Texas
```

### Combine Criteria

```
What colonies in Louisiana had oil present and lost vegetation?
Show BRPE observations from 2010 with flooding notes
```

---

## Understanding Results

### SQL Query Display

The chatbot shows the generated SQL:
```
📝 SQL: SELECT colony_name, COUNT(*) as total
FROM observations
WHERE species_code = 'LAGU'
GROUP BY colony_name
ORDER BY total DESC
LIMIT 10;
```

This helps you:
- Understand how your question was interpreted
- Learn SQL patterns
- Verify the query logic

### Results Preview

Shows first 10 rows by default:
```
Results preview:
  colony_name  total
Long Bay Island    450
Cat Bay Island     320
...
```

If more than 10 results:
```
... and 25 more rows
```

### AI Answer

Natural language explanation:
- Answers your specific question
- Provides context and insights
- Mentions interesting patterns
- Notes limitations or caveats

---

## Advanced Usage

### Follow-up Questions

The chatbot remembers conversation context:

```
Your question: What colonies had oil in 2010?
A: [Lists 5 colonies]

Your question: How many species at those colonies?
A: [Uses context from previous question]
```

### Complex Queries

```
Compare species diversity between colonies active in 2010
that are still active today versus those that disappeared
```

```
Show colonies with the most habitat changes documented
in field notes from 2010 to 2021
```

### Analytical Questions

```
What's the correlation between oil presence and colony survival?
Which ecoregions had the most colony losses?
How did nesting populations change after Hurricane Isaac?
```

---

## Exporting Results

### Copy from Terminal

Select and copy the results preview from your terminal.

### Direct SQL Query

For custom exports:
```bash
sqlite3 bird_data.db "SELECT * FROM observations WHERE year = 2010" > output.csv
```

### Python Script

```python
from sql_chatbot import SQLChatbot
import pandas as pd

chatbot = SQLChatbot()
sql = chatbot.generate_sql_query("What colonies had oil in 2010?")
df, error = chatbot.execute_query(sql)

if df is not None:
    df.to_csv('results.csv', index=False)
    print(f"Exported {len(df)} rows")

chatbot.close()
```

---

## Common Questions

### "Why no results found?"

**Possible reasons:**
1. Query too specific (no data matches)
2. Typo in colony/species name
3. Year out of range (2010-2021 only)
4. State code incorrect (use TX, LA, MS, AL, FL)

**Solutions:**
- Check `stats` for available years
- Try broader search
- Use `examples` for working queries

### "Can I see the raw SQL?"

Yes! It's shown for every query:
```
📝 SQL: [your generated query]
```

You can copy and modify it for direct database access.

### "How accurate are the answers?"

The chatbot:
- ✅ Generates accurate SQL based on schema
- ✅ Returns exact database results
- ✅ Uses Claude 3.5 Sonnet for interpretation
- ⚠️ May occasionally misinterpret complex questions

Always review the SQL and results preview to verify accuracy.

### "Can I ask about future predictions?"

No. The dataset contains **historical observations only** (2010-2021).

For predictive analysis:
- Export data
- Use statistical modeling tools
- Consider time series analysis in Python/R

---

## Best Practices

### Research Workflow

1. **Start broad** - Get overview with `stats`
2. **Explore** - Try `examples` queries
3. **Focus** - Ask specific research questions
4. **Verify** - Check SQL and results
5. **Document** - Save useful queries
6. **Export** - Extract data for further analysis

### Performance Tips

- Use specific filters (year, state, species)
- Limit result counts for large queries
- Avoid wildcards in text searches when possible
- Close chatbot when done (releases database connection)

---

## Next Steps

- **See More Examples**: [EXAMPLES.md](EXAMPLES.md)
- **Learn Data Structure**: [DATA_SCHEMA.md](DATA_SCHEMA.md)
- **Erosion Analysis Guide**: [EROSION_ANALYSIS.md](EROSION_ANALYSIS.md)
- **Migration Analysis Guide**: [MIGRATION_ANALYSIS.md](MIGRATION_ANALYSIS.md)

---

**Happy Exploring!** 🐦📊
