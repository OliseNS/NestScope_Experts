# NestChat Agentic System Redesign Plan

## Problems Identified

### 1. Retry Loop Confusion
- **Issue**: Shows "Attempt 5/10 (Attempt 5/3)" - conflicting retry counts
- **Root Cause**: Config says `max_attempts: 3` but somewhere else shows higher number
- **Fix**: Single source of truth for max_attempts, clear logging

### 2. Malformed Visualization Directives
- **Issue**: `[SHOW_CHART: line]` appearing in answer text instead of being parsed out
- **Root Cause**: `parse_visualization_directives()` not being used on final answer before display
- **Fix**: Always use `clean_answer` from directives parsing

### 3. Shallow Reasoning Logs
- **Issue**: Says "✓ Query validated" but doesn't explain WHY or WHAT was checked
- **Root Cause**: Validation functions return boolean + generic message, no details
- **Fix**: Return structured validation with checklist of what was verified

### 4. Map Coordinate Error
- **Issue**: Concatenated string of coordinates: "30.506329.25582..."
- **Root Cause**: SQL returns proper columns, but somewhere they get concatenated
- **Fix**: Better dataframe validation and rendering

### 5. Not Leveraging Enhanced Metadata
- **Issue**: Metadata loaded but used as raw dump, not strategically
- **Root Cause**: No intelligence layer that interprets relationships/semantic types
- **Fix**: Create metadata-aware tools that use relationships intelligently

### 6. Missing Flood Intelligence
- **Issue**: Can't answer questions about flood risk or coastal threats
- **Root Cause**: RiskIntelligenceService exists but not integrated into chatbot
- **Fix**: Add flood intelligence tool to agentic system

## Solution Architecture

### Phase 1: Enhanced Validation with Detailed Reasoning

**Before (Shallow)**:
```python
{
    'is_valid': True,
    'feedback': 'Query validated and meets requirements'
}
```

**After (Deep)**:
```python
{
    'is_valid': True,
    'feedback': 'All validation checks passed',
    'reasoning': {
        'checklist': [
            {'check': 'Uses correct table (tblColonyTotals...)', 'passed': True},
            {'check': 'Includes Latitude and Longitude columns', 'passed': True},
            {'check': 'GROUP BY includes coordinates', 'passed': True},
            {'check': 'WHERE filters NULL coordinates', 'passed': True},
            {'check': 'Uses COALESCE for count aggregation', 'passed': True}
        ],
        'sql_issues_found': [],
        'suggestions': []
    }
}
```

### Phase 2: Tool-Based Agent Architecture

Instead of a monolithic chatbot, create specialized tools:

**Tool 1: Database Query Tool**
- Purpose: Execute SQL and return results
- Uses: Enhanced metadata for table selection

**Tool 2: Flood Intelligence Tool**
- Purpose: Answer coastal risk/flood questions
- Integrates: RiskIntelligenceService
- Triggers: Questions about "flood", "risk", "erosion", "sea level rise", "vulnerable"

**Tool 3: Metadata Analyzer Tool**
- Purpose: Understand relationships between tables
- Uses: DatabaseExplorer to find joinable columns

**Tool 4: Validation Tool**
- Purpose: Self-check SQL for correctness
- Returns: Detailed checklist

### Phase 3: Improved Streaming Protocol

**Event Types**:
1. `thinking_step` - High-level progress ("Analyzing question...")
2. `question_analysis` - Deep semantic understanding with reasoning chain
3. `tool_selection` - Which tool(s) will be used and why
4. `sql_generated` - Generated SQL query
5. `validation_result` - Detailed validation checklist
6. `results` - Query results with metadata
7. `results_validation` - Results sanity check with reasoning
8. `answer_start` - Begin streaming answer
9. `answer_chunk` - Answer text chunk
10. `answer_end` - Answer complete (with CLEANED text)
11. `visualization` - Visualization directives extracted separately
12. `retry` - Retry with detailed reason and fix strategy

### Phase 4: Metadata-Aware Question Analysis

**Enhanced Analysis**:
```json
{
  "understanding": "User wants temporal trend of Brown Pelicans in Louisiana 2015-2021",
  "query_type": "time_series_trend",
  "entities": {
    "species": ["Brown Pelican (BRPE)"],
    "locations": ["Louisiana"],
    "time_range": "2015-2021",
    "metrics": ["Birds"]
  },
  "metadata_used": {
    "tables": ["tblColonyTotals2010-2021_MayJuneCombined"],
    "relationships": ["SpeciesCode -> tblSpeciesCodes"],
    "coordinate_requirement": "YES - trend by location needs map"
  },
  "reasoning_chain": [
    "1. Intent: Track population changes over time",
    "2. Table Selection: tblColonyTotals has pre-aggregated bird counts",
    "3. Filters: State='LA', Year BETWEEN 2015 AND 2021, SpeciesCode='BRPE'",
    "4. Aggregation: SUM(Birds) GROUP BY Year",
    "5. Coordinates: MUST include Lat/Lon for mapping colonies",
    "6. Visualization: Line chart (time series) + Map (locations)"
  ]
}
```

### Phase 5: Flood Intelligence Integration

**Trigger Detection**:
- Keywords: "flood", "risk", "vulnerable", "erosion", "sea level", "storm", "hurricane", "threat"
- Intent: Coastal resilience, restoration priorities, climate adaptation

**Flood Tool Response**:
```json
{
  "tool": "flood_intelligence",
  "results": {
    "critical_colonies": 5,
    "high_risk": 12,
    "analysis": "Fusion of NOAA water levels, USGS erosion, HURDAT2 storms",
    "top_threats": [
      {"colony": "Queen Bess Island", "risk_score": 87.3, "level": "CRITICAL"}
    ]
  }
}
```

## Implementation Checklist

### Backend (`server/main.py`)
- [ ] Create `AgenticToolbox` class with specialized tools
- [ ] Enhance `_analyze_question` to use metadata relationships
- [ ] Enhance `_validate_sql` to return detailed checklist
- [ ] Enhance `_validate_results` to return reasoning
- [ ] Add flood intelligence tool detection and routing
- [ ] Fix `parse_visualization_directives` to always clean answer
- [ ] Fix retry counting (single source: config.yaml)

### Frontend (`frontend/pages/01_nest_chat.py`)
- [ ] Display detailed validation checklist in reasoning view
- [ ] Use `clean_answer` from visualization event
- [ ] Show tool selection decisions
- [ ] Better coordinate error handling

### Testing
- [ ] Test: "Show Brown Pelican trends 2015-2021" → Should have map + line chart
- [ ] Test: "Which colonies are at flood risk?" → Should trigger flood tool
- [ ] Test: Malformed SQL → Should show detailed validation failure
- [ ] Test: Retry logic → Should clearly show attempt numbers

## Expected User Experience After Fix

**User**: "Show me Brown Pelican trends from 2015 to 2021"

**System Response**:
```
🔍 Detailed Reasoning & Validation (took 1 try)

📋 Step 1: Question Analysis
Understanding: Analyze temporal population trajectory of Brown Pelicans from 2015-2021
Query Type: time_series_trend
Tables Required: tblColonyTotals2010-2021_MayJuneCombined
Needs Coordinates: YES (for mapping colony locations)

Reasoning Steps:
1. Intent Analysis: User wants to see population changes over time
2. Table Selection: tblColonyTotals has pre-aggregated bird counts (correct table for "observations")
3. Filters: SpeciesCode='BRPE', Year BETWEEN 2015 AND 2021
4. Aggregation: SUM(Birds) GROUP BY Year for time series
5. Coordinates: MUST include Latitude/Longitude for map visualization

📝 Step 2: SQL Query Construction
SELECT
    "Year",
    SUM(COALESCE("Birds", 0)) as total_birds
FROM "tblColonyTotals2010-2021_MayJuneCombined"
WHERE "SpeciesCode" = 'BRPE'
  AND CAST("Year" AS INTEGER) BETWEEN 2015 AND 2021
GROUP BY "Year"
ORDER BY "Year";

✅ Step 3: SQL Validation
✓ All validation checks passed

Validation Checklist:
✓ Uses correct table (tblColonyTotals2010-2021_MayJuneCombined)
✓ Targets pre-aggregated bird counts (not photo records)
✓ Uses COALESCE for NULL-safe aggregation
✓ Filters by SpeciesCode correctly
✓ Year range properly constrained
✓ No dangerous operations (only SELECT)

⚡ Step 4: Query Execution
Retrieved 3 rows

🔬 Step 5: Results Validation
✓ Results validated and match the question

Results Check:
✓ Row count reasonable (3 years of data)
✓ All years in expected range (2015-2021)
✓ Bird counts are positive integers
✓ No NULL values in critical columns
✓ Time series is continuous

---

Brown Pelican populations showed strong recovery from 2015 to 2021:

- 2015: 8,234 birds
- 2018: 9,812 birds (+19% from 2015)
- 2021: 11,043 birds (+34% from 2015)

This represents a steady upward trend with 34% total growth over the period,
indicating successful post-Deepwater Horizon restoration efforts.

[Shows line chart with 3 data points]
```

**Key Improvements**:
1. ✓ Clear reasoning at each step
2. ✓ Detailed validation checklist
3. ✓ No visualization directives in answer text
4. ✓ Single, clear attempt counter
5. ✓ Explains WHY validations passed/failed
6. ✓ Uses metadata intelligently

## Success Metrics

- [ ] Reasoning logs are detailed enough that a junior engineer can understand the logic
- [ ] Visualization directives NEVER appear in displayed answer
- [ ] Retry attempts are clear and consistent (e.g., "Attempt 2/3")
- [ ] Map errors show helpful troubleshooting
- [ ] Flood intelligence questions are answered with risk data
- [ ] Validation failures explain WHAT was wrong and HOW to fix it
