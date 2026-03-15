# NestChat Diagnosis & Fix (March 14, 2026)

## Problems Diagnosed

### Problem 1: Token Overload (65,000+ tokens)
**Symptom:** Model overwhelmed, confused, generating garbage output

**Root Cause:**
- `prompt.txt`: 607 lines (~15,000 tokens) containing BOTH SQL generation AND answer generation instructions
- `database_metadata_enhanced.json`: 2,000+ lines (~50,000+ tokens) with full verbose schema
- **Total context before question**: ~65,000 tokens

**Impact:** Model couldn't focus on the task, mixed SQL with HTML/explanations

### Problem 2: Conflicting Instructions
**Symptom:** SQL queries mixed with formatted text, HTML tags, explanations

**Root Cause:**
- Same prompt used for both SQL generation and answer generation
- SQL generation phase: "Return ONLY SQL, no explanations"
- Answer generation phase: "Generate HTML artifacts with Chart.js"
- Model confused which phase it was in

**Example Errors:**
```
ERROR: Invalid SQL - must start with SELECT or WITH. Got: Here are all the **Geographic Regions (GeoRegions)** in the Gulf Coast bird survey database: | # | ...
```

### Problem 3: No Structured Output
**Symptom:** String manipulation fails, SQL contaminated with text

**Root Cause:**
- Model returned free-form text: explanations + SQL mixed together
- Regex cleanup (lines 1022-1044) tried to extract SQL but failed often
- No enforcement of output structure

## Solutions Implemented

### ✅ Solution 1: Separate Prompts (Separation of Concerns)

**Created: `server/sql_prompt.txt`** (~100 lines, ~2,500 tokens)
- Minimal, focused ONLY on SQL generation
- No artifact instructions, no answer generation rules
- Clear examples of correct query patterns
- **90% size reduction** from original prompt

**Modified: `server/main.py`**
- Added `_load_sql_prompt()` method
- `generate_sql_query()` now uses `sql_prompt` instead of `system_prompt`
- `prompt.txt` reserved for answer generation only

### ✅ Solution 2: Compress Metadata (90% size reduction)

**Created: `data/metadata_essential.json`** (~300 lines, ~5,000 tokens)
- Only critical information: table purposes, key columns, common patterns
- Removed verbose column details, samples, temporal/spatial flags
- **Kept:** Critical rules, join relationships, query hints
- **Removed:** Full column lists, sample data, metadata for all 70+ tables

**Token Comparison:**
- Before: ~50,000 tokens (full schema)
- After: ~5,000 tokens (essential schema)
- **90% reduction**

**Priority Loading (already implemented in code):**
1. `metadata_essential.json` (use this - we created it)
2. `metadata_extended.json` (fallback - doesn't exist yet)
3. `database_metadata_enhanced.json` (final fallback - old verbose schema)

### ✅ Solution 3: Structured JSON Output

**Modified: `generate_sql_query()`**
- Requests JSON format: `{"sql": "SELECT ..."}`
- Parses JSON to extract clean SQL
- Fallback to regex cleanup if JSON parsing fails
- Prevents contamination with explanations

**Before:**
```
Response: "Here's the query: SELECT * FROM table"
Cleanup: Regex tries to find "SELECT", often fails
```

**After:**
```
Response: {"sql": "SELECT * FROM table"}
Parse: json.loads() → result["sql"]
Result: Clean SQL, no contamination
```

## Results Expected

### Token Usage Comparison

| Phase | Before | After | Reduction |
|-------|--------|-------|-----------|
| System Prompt | 15,000 | 2,500 | -83% |
| Metadata | 50,000 | 5,000 | -90% |
| **Total Context** | **65,000** | **7,500** | **-88%** |

### Behavioral Improvements

1. **Clearer Instructions**: Model sees only SQL rules during SQL generation
2. **Faster Response**: 88% fewer tokens to process before generating SQL
3. **Fewer Errors**: Structured output prevents contamination
4. **Better Accuracy**: Model not confused by artifact/chart instructions

## Files Changed

### Created
- `server/sql_prompt.txt` - SQL generation prompt (100 lines)
- `data/metadata_essential.json` - Compressed schema (300 lines)
- `NESTCHAT_FIX.md` - This document

### Modified
- `server/main.py`:
  - Added `sql_prompt_path` and `_load_sql_prompt()` method
  - Modified `generate_sql_query()` to use SQL prompt + JSON parsing
  - Existing metadata priority loading already uses `metadata_essential.json`

### Unchanged
- `server/prompt.txt` - Still used for answer generation (keep as-is)
- `data/database_metadata_enhanced.json` - Fallback if essential missing

## Testing Checklist

Test these queries to verify the fix:

1. **Geographic Query**
   - "Where is Rabbit Island?"
   - Should: Include Lat/Lon, return clean SQL, show map

2. **List Query**
   - "List all georegions"
   - Should: Return clean SELECT DISTINCT query, no HTML contamination

3. **Comparison Query**
   - "Compare species diversity across different colonies"
   - Should: Return aggregated query with coordinates, generate chart artifact

4. **Error Recovery**
   - Ask a question that causes SQL error
   - Should: Retry with better SQL, not mix errors with HTML

## Rollback Plan

If issues occur:

1. Rename files:
   ```bash
   mv server/sql_prompt.txt server/sql_prompt.txt.backup
   mv data/metadata_essential.json data/metadata_essential.json.backup
   ```

2. Revert `server/main.py` changes:
   ```bash
   git diff server/main.py  # Review changes
   git checkout server/main.py  # Revert if needed
   ```

3. Restart server - will fall back to old behavior

## Next Steps (Optional Improvements)

1. **Further Prompt Refinement**
   - Add more query examples to sql_prompt.txt
   - Fine-tune critical rules based on common errors

2. **Metadata Tiers**
   - Create `metadata_extended.json` (middle tier, ~15k tokens)
   - For complex queries that need more schema context

3. **Error-Guided Refinement**
   - Log queries that fail after 3 retries
   - Add those patterns to sql_prompt.txt as examples

4. **Monitoring**
   - Track token usage per query
   - Measure accuracy improvement (% queries that succeed first try)

## Technical Details

### Prompt Separation Pattern

This fix follows the **3-phase agentic pipeline**:

1. **SQL Generation** (uses `sql_prompt.txt`)
   - Input: Natural language question + schema
   - Output: JSON `{"sql": "SELECT ..."}`
   - Focus: Accuracy, proper table selection, coordinate inclusion

2. **Query Execution** (no prompt needed)
   - Input: SQL string
   - Output: DataFrame with results
   - Focus: Security validation, error handling

3. **Answer Generation** (uses `prompt.txt`)
   - Input: Question + SQL + Results
   - Output: Natural language answer + artifacts
   - Focus: Clarity, insights, visualizations

Each phase has ONE job, ONE prompt, ONE output format.

### Why JSON Output?

**Alternative Approaches Considered:**
- ❌ Free-form text: Causes contamination (current problem)
- ❌ Markdown code blocks: Still needs regex cleanup
- ✅ **JSON structured output**: Forces clean separation

**Benefits:**
- Parser enforces structure (`json.loads()` fails if malformed)
- No ambiguity about where SQL starts/ends
- Easy to extend with metadata: `{"sql": "...", "reasoning": "...", "requires_coords": true}`

### Metadata Compression Strategy

**What to Keep (Essential Tier):**
- Table purposes (observations vs records vs reference)
- Key columns only (ColonyName, Year, Birds, Latitude, etc.)
- Join relationships (foreign keys)
- Common query patterns
- Critical rules (observations vs records distinction)

**What to Remove:**
- Full column lists with types/constraints
- Sample data rows
- Temporal/spatial column classifications (redundant)
- Verbose descriptions for every table

**Estimated Token Savings:**
- 8 bird data tables × 6,000 tokens each = 48,000 tokens removed
- Keep only summary metadata = 5,000 tokens
- **Net savings: 43,000 tokens per query**

---

**Fix implemented by:** Claude (Sonnet 4.5)
**Date:** March 14, 2026
**Issue:** Token overload causing SQL generation failures
**Status:** ✅ Deployed, ready for testing
