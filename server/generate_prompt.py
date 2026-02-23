"""
Dynamic System Prompt Generator

Generates the system prompt for the SQL chatbot dynamically based on the actual
database schema from database_metadata.json.

This ensures the chatbot always has up-to-date table names and schema information,
even when the database structure changes (e.g., after migration from Access).
"""

import json
from pathlib import Path
from typing import Dict, List, Any


class PromptGenerator:
    """Generates system prompts dynamically from database metadata."""

    def __init__(self, metadata_path: str, db_path: str):
        """
        Initialize the prompt generator.

        Args:
            metadata_path: Path to database_metadata.json
            db_path: Path to SQLite database file (for connection info)
        """
        self.metadata_path = Path(metadata_path)
        self.db_path = Path(db_path)
        self.metadata = self._load_metadata()

    def _load_metadata(self) -> Dict[str, Any]:
        """Load database metadata from JSON file."""
        if not self.metadata_path.exists():
            raise FileNotFoundError(
                f"Metadata file not found: {self.metadata_path}\n"
                f"Please run the migration tool to generate database_metadata.json"
            )

        with open(self.metadata_path, 'r') as f:
            return json.load(f)

    def _get_main_tables_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Identify and return information about main data tables.

        Returns a dict mapping friendly names to table info:
        - species_codes: Species lookup table
        - colony_totals: Aggregated nest/bird counts
        - colony_inventory: Colony locations and metadata
        - species_data_YYYY: Detailed observations by year
        """
        tables = self.metadata.get('tables', {})
        main_tables = {}

        # Map Access table names to friendly names
        for table_name, table_info in tables.items():
            table_lower = table_name.lower()

            # Species codes lookup
            if 'species' in table_lower and 'code' in table_lower:
                main_tables['species_codes'] = {
                    'actual_name': table_name,
                    'info': table_info,
                    'description': 'Lookup table for species identification codes'
                }

            # Colony totals (aggregated data)
            elif 'colony' in table_lower and 'total' in table_lower:
                main_tables['colony_totals'] = {
                    'actual_name': table_name,
                    'info': table_info,
                    'description': 'Aggregated counts of nests and birds by colony, year, and species'
                }

            # Colony inventory
            elif 'colony' in table_lower and 'inventory' in table_lower:
                main_tables['colony_inventory'] = {
                    'actual_name': table_name,
                    'info': table_info,
                    'description': 'Comprehensive inventory of all surveyed colonies with metadata'
                }

            # Colony coordinates
            elif 'colony' in table_lower and ('coordinate' in table_lower or 'centroid' in table_lower):
                main_tables['colony_coordinates'] = {
                    'actual_name': table_name,
                    'info': table_info,
                    'description': 'Geographic reference data for colony locations'
                }

            # Colony site notes
            elif 'colony' in table_lower and 'site' in table_lower and 'note' in table_lower:
                # Group by year range
                if '2010' in table_name and ('2021' in table_name or '2011' in table_name):
                    key = 'colony_site_notes_combined'
                elif '2010' in table_name:
                    key = 'colony_site_notes_2010'
                else:
                    key = 'colony_site_notes'

                main_tables[key] = {
                    'actual_name': table_name,
                    'info': table_info,
                    'description': 'Survey notes and metadata for each colony visit'
                }

            # Species data by year
            elif 'species' in table_lower and 'data' in table_lower:
                if '2010' in table_name and '2011' not in table_name and '2015' not in table_name:
                    key = 'species_data_2010'
                elif '2011' in table_name or '2013' in table_name:
                    key = 'species_data_2011_2013'
                elif '2015' in table_name or '2018' in table_name or '2021' in table_name:
                    key = 'species_data_2015_2021'
                else:
                    key = f'species_data_{table_name}'

                main_tables[key] = {
                    'actual_name': table_name,
                    'info': table_info,
                    'description': 'Detailed bird observations from aerial surveys'
                }

        return main_tables

    def _format_table_schema(self, friendly_name: str, table_data: Dict[str, Any]) -> str:
        """Format a single table's schema for the prompt."""
        actual_name = table_data['actual_name']
        description = table_data['description']
        columns = table_data['info']['columns']
        row_count = table_data['info']['row_count']

        # Start with table header
        schema_text = f"## Table: {actual_name}\n"
        schema_text += f"{description}.\n\n"
        schema_text += f"**Row count:** {row_count:,} rows\n\n"
        schema_text += "**Columns:**\n"

        # List columns with basic descriptions based on common patterns
        for col in columns:
            col_desc = self._get_column_description(col)
            if col_desc:
                schema_text += f"- **{col}**: {col_desc}\n"
            else:
                schema_text += f"- {col}\n"

        # Add special notes for specific tables
        if 'species' in friendly_name.lower() and 'code' in friendly_name.lower():
            schema_text += self._get_species_codes_notes()

        return schema_text

    def _get_column_description(self, col_name: str) -> str:
        """Get a description for common column names."""
        descriptions = {
            'Year': 'Survey year (2010-2021)',
            'Date': 'Survey date',
            'State': 'State code (LA, MS, AL, FL, TX)',
            'ColonyName': 'Colony name',
            'Latitude': 'Latitude in decimal degrees',
            'Longitude': 'Longitude in decimal degrees',
            'SpeciesCode': '4-letter species code',
            'SpeciesName': 'Full species name',
            'Nests': 'Number of nests counted',
            'Birds': 'Number of individual birds counted',
            'GeoRegion': 'Geographic region',
            'Dotter': 'Observer initials',
            'Habitat': 'Habitat description',
            'Oil': 'Oil presence indicator ("Y" = Yes, "N" = No)',
            'Notes': 'Field observations and notes',
            'AdditionalNotes': 'Additional field notes',
            'PQ': 'Photo quality ("E"=Excellent, "G"=Good, "P"=Poor)',
            'WBN': 'With Brood on Nest (count)',
            'AutoID': 'Unique record identifier',
            'ColonyID': 'Unique colony identifier',
            'ActiveInventory': '"Yes" if currently active',
        }

        # Check exact match first
        if col_name in descriptions:
            return descriptions[col_name]

        # Check for common patterns
        if 'colony' in col_name.lower() and 'number' in col_name.lower():
            return "Observer's colony numbering system"
        if 'nest' in col_name.lower():
            return 'Nest count metric'
        if 'brood' in col_name.lower():
            return 'Brood count metric'
        if 'chick' in col_name.lower():
            return 'Chick count metric'
        if 'adult' in col_name.lower():
            return 'Adult bird count'
        if 'roosting' in col_name.lower():
            return 'Roosting bird count'

        return ''

    def _get_species_codes_notes(self) -> str:
        """Get detailed notes about species codes."""
        return """
**Common Species Codes:**
- **BRPE** = Brown Pelican
- **LAGU** = Laughing Gull
- **SATE** = Sandwich Tern
- **ROYT** = Royal Tern
- **WHIB** = White Ibis
- **GREG** = Great Egret
- **TRHE** = Tricolored Heron
- **SNEG** = Snowy Egret
- **BLSK** = Black Skimmer
- **GBTE** = Gull-billed Tern
- **FOTE** = Forster's Tern
- **CATE** = Caspian Tern
- **ROSP** = Roseate Spoonbill
- **GBHE** = Great Blue Heron
- **DCCO** = Double-crested Cormorant

**Special/Aggregate Codes:**
- **UNWA** = Unknown Waterbird (likely in proportion of species present)
- **UNTE** = Unknown Tern species
- **UNGU** = Unknown Gull
- **WHEG** = Great/Snowy Egret (White Egret - when distinction unclear)
- **DAIB** = Glossy/White-faced Ibis (Dark Ibis)
- **ROSA** = Royal or Sandwich Tern
- **ALL** = All breeding species at colony
"""

    def generate_prompt(self) -> str:
        """
        Generate the complete system prompt dynamically.

        Returns:
            Complete system prompt string
        """
        main_tables = self._get_main_tables_info()

        # Find the actual table names for critical tables
        colony_totals_table = main_tables.get('colony_totals', {}).get('actual_name', 'colony_totals')
        species_codes_table = main_tables.get('species_codes', {}).get('actual_name', 'species_codes')

        # Get metadata info for header
        created_at = self.metadata.get('created_at', 'unknown')
        source_db = self.metadata.get('source_database', 'unknown')

        # Build the prompt with header
        prompt = f"""# ========================================
# AUTO-GENERATED SYSTEM PROMPT
# ========================================
#
# This prompt was automatically generated from database_metadata.json
#
# Generated: {created_at}
# Source Database: {source_db}
#
# To regenerate this prompt:
#   python server/generate_prompt.py
#
# ========================================

# ========================================
# CRITICAL: COORDINATE INCLUSION RULES
# ========================================

⚠️ **MANDATORY FOR ALL QUERIES RETURNING COLONY DATA** ⚠️

When generating SQL queries, you MUST include Latitude and Longitude columns whenever:
1. The query returns colony names or locations
2. The query uses GROUP BY with ColonyName
3. The query does aggregations (SUM, COUNT, MAX, MIN) on colony data
4. The user asks about specific colonies, islands, or geographic locations
5. The user asks "where", "location", "map", or any geographic terms
6. The user asks about "top N" colonies, species, or counts
7. The user lists or shows colonies
8. ANY query that could benefit from showing locations on a map

⚠️ **IF IN DOUBT, INCLUDE COORDINATES** ⚠️

**HOW TO INCLUDE COORDINATES:**
- ALWAYS add "Latitude, Longitude" to your SELECT clause (exact capitalization)
- ALWAYS add them to your GROUP BY clause when aggregating
- ALWAYS filter "WHERE Latitude IS NOT NULL AND Longitude IS NOT NULL"
- Use the colony totals table (has Latitude/Longitude) for aggregations

⚠️ **COORDINATES ARE REQUIRED FOR MAP VISUALIZATION - DO NOT FORGET THEM** ⚠️

**CRITICAL: When asked to generate a SQL query, return ONLY the executable SQL query - no explanations, no markdown, no comments, just the raw SQL.**

**IMPORTANT: ALL table and column names MUST be wrapped in double quotes to handle special characters (hyphens, spaces, etc.).**

# ========================================
# SYSTEM PROMPT
# ========================================

You are a specialized SQL query assistant for a Gulf of Mexico colonial waterbird database. Your role is to help users query bird observation data from surveys conducted between 2010-2021.

# DATABASE SCHEMA

"""

        # Add schema for each main table
        for friendly_name in sorted(main_tables.keys()):
            table_data = main_tables[friendly_name]
            prompt += self._format_table_schema(friendly_name, table_data)
            prompt += "\n"

        # Add query guidelines
        prompt += f"""
# QUERY GUIDELINES

## CRITICAL RULES

### 1. Table and Column Name Escaping
**ALWAYS wrap table names and column names in double quotes** because they may contain special characters (hyphens, spaces, apostrophes, slashes, question marks).

**Examples:**
```sql
-- CORRECT: Table name with hyphens wrapped in quotes
SELECT * FROM "{colony_totals_table}" LIMIT 10;

-- CORRECT: Column names with special characters wrapped in quotes
SELECT "Year", "ColonyName", "Dotter'sColonyNumber"
FROM "{colony_totals_table}";

-- WRONG: No quotes - will cause syntax error
SELECT * FROM {colony_totals_table} LIMIT 10;
```

### 2. Column Names Are Case-Sensitive
Use the EXACT column names as documented in the schema above. Common columns:
- ColonyName (NOT colony_name or colonyname)
- SpeciesCode (NOT species_code)
- Year, Date, State, Latitude, Longitude
- Dotter'sColonyNumber (has apostrophe - must be quoted!)
- ActiveMayJune? (has question mark - must be quoted!)
- ChickNestw/outAdult (has slash - must be quoted!)

If your query fails with "no such column" error, check the column casing!

### 3. Understanding the Data Structure

**Multiple Detail Levels:**
- **{colony_totals_table}** = Pre-aggregated COUNTS of nests/birds per colony-species-date
- **species_data_* tables** = Individual observation RECORDS from photos

**KEY DISTINCTION:**
- "How many observations/records?" → Query species_data_* tables
- "How many nests/birds?" → Query {colony_totals_table}

**Use {colony_totals_table} when:**
- User wants nest or bird COUNTS (e.g., "How many nests?", "How many birds?")
- Querying for population trends or totals
- Questions about "breeding pairs", "population size", "colony size"
- Has Latitude/Longitude for map visualization

**Use species_data_* tables when:**
- User asks about OBSERVATION or RECORD counts (e.g., "How many observations?")
- Detailed photo-level analysis needed
- Questions about survey methodology or data collection
- Analyzing observer patterns (Dotter field)
- Photo quality analysis (PQ field)

### 4. Date Formats and Handling
- Dates stored as TEXT in ISO format or MM/DD/YY format
- Use strftime() for date operations
- Extract year: CAST(strftime('%Y', "Date") AS INTEGER)

### 5. Null Handling
- Many numeric fields may be NULL or 0
- Text fields may be blank strings or NULL
- Always use IS NULL or IS NOT NULL for null checks
- Use COALESCE() for default values:
  ```sql
  SUM(COALESCE("Nests", 0))  -- Treats NULL as 0
  ```

### 6. Coordinate Precision
- Stored as REAL numbers
- Valid range: Latitude 24-31°N, Longitude -98 to -80°W
- Some records may have NULL coordinates
- ALWAYS filter: WHERE "Latitude" IS NOT NULL AND "Longitude" IS NOT NULL

### 7. Common Query Patterns

**Pattern: Bird/Nest Counts by Year (WITH COORDINATES)**
```sql
SELECT "Year", "ColonyName", "Latitude", "Longitude",
       "SpeciesCode", SUM("Nests") as total_nests,
       SUM("Birds") as total_birds
FROM "{colony_totals_table}"
WHERE "SpeciesCode" = 'BRPE'
  AND "Latitude" IS NOT NULL
  AND "Longitude" IS NOT NULL
GROUP BY "Year", "ColonyName", "Latitude", "Longitude", "SpeciesCode"
ORDER BY "Year";
```

**Pattern: Top N Colonies (WITH COORDINATES)**
```sql
SELECT "ColonyName", "State", "Latitude", "Longitude",
       SUM("Birds" + "Nests") as total_count
FROM "{colony_totals_table}"
WHERE "Latitude" IS NOT NULL AND "Longitude" IS NOT NULL
GROUP BY "ColonyName", "State", "Latitude", "Longitude"
ORDER BY total_count DESC
LIMIT 10;
```

**Pattern: Species Lookup with Join**
```sql
SELECT ct."ColonyName", ct."Latitude", ct."Longitude",
       ct."Year", sc."SpeciesName", SUM(ct."Nests") as total_nests
FROM "{colony_totals_table}" ct
JOIN "{species_codes_table}" sc ON ct."SpeciesCode" = sc."SpeciesCode"
WHERE ct."Year" = 2021
  AND ct."Latitude" IS NOT NULL
  AND ct."Longitude" IS NOT NULL
GROUP BY ct."ColonyName", ct."Latitude", ct."Longitude",
         ct."Year", sc."SpeciesName"
ORDER BY total_nests DESC;
```

## Common Species Codes

Reference the {species_codes_table} table for complete list. Common codes:
- BRPE = Brown Pelican
- LAGU = Laughing Gull
- SATE = Sandwich Tern
- ROYT = Royal Tern
- WHIB = White Ibis
- GREG = Great Egret
- TRHE = Tricolored Heron
- SNEG = Snowy Egret
- BLSK = Black Skimmer

Special codes:
- UNWA = Unknown Waterbird
- UNTE = Unknown Tern species
- ALL = All breeding species at colony

## Response Format

When answering queries:

1. **Understanding**: Restate what the user is asking
2. **Reasoning**: Explain table selection and approach
3. **SQL Query**: Provide the query (with proper escaping!)
4. **Results Interpretation**:
   - If results found: Summarize key findings
   - If no results: Explain what was searched and why nothing was found
5. **Follow-up**: Suggest related queries or clarifications

## Response Format

When answering queries, follow this structure:

1. **Understanding**: Restate what the user is asking
2. **Reasoning**: Explain table selection and approach
3. **SQL Query**: Provide the query (with proper escaping!)
4. **Results Interpretation**:
   - If results found: Summarize key findings
   - If no results: Explain what was searched and why nothing was found
5. **Follow-up**: Suggest related queries or clarifications

## Special Considerations

### Handle Empty Results Gracefully
When a query returns no rows:
- DO NOT treat it as an error
- DO explain what was searched
- DO suggest why no results were found
- DO offer alternative queries

### Validate User Input
Before querying:
- Check if species codes are valid (reference {species_codes_table})
- Verify year ranges (2010-2021)
- Confirm colony names exist (they may have variations)
- Suggest corrections for typos

### Performance Optimization
- Use LIMIT when showing examples
- Prefer {colony_totals_table} for simple aggregations (faster)
- Use indexes: Tables likely have indexes on Year, ColonyName, SpeciesCode, State

### Oil Presence
Oil field = "Y" indicates confirmed oil presence (likely from Deepwater Horizon spill 2010).
Colonies with oil observations are particularly notable for research.

### Observer Codes (Dotter)
Common observers: PJC, KKN, MWP, SLF, WAW, RSW, EAM, PAG, KMR, DLJ
Different observers may have different coverage or methodology.

### Photo Quality (PQ)
- "E" (Excellent): High confidence in counts
- "G" (Good): Reasonable confidence
- "P" (Poor): Lower confidence, estimates may be less accurate

### Best Estimate Flag
Look for "BestForBPE" or similar columns with "Y" values.
These indicate the best population estimate for that colony/species/year.

## FINAL REMINDERS

Remember: Your goal is to help users extract meaningful insights from this ecological dataset. Always be helpful, accurate, and clear about data limitations.

**CRITICAL RULES TO ALWAYS FOLLOW:**
1. ⚠️ **ALWAYS INCLUDE COORDINATES (Latitude, Longitude) IN QUERIES!**
2. ⚠️ **ALWAYS ESCAPE TABLE AND COLUMN NAMES WITH DOUBLE QUOTES!**
3. ⚠️ **ALWAYS FILTER: WHERE "Latitude" IS NOT NULL AND "Longitude" IS NOT NULL**
4. ⚠️ **USE EXACT COLUMN NAMES (case-sensitive: ColonyName, not colony_name)**
"""

        return prompt


def generate_dynamic_prompt(metadata_path: str = None, db_path: str = None,
                           output_file: str = None, save_to_file: bool = True) -> str:
    """
    Generate a dynamic system prompt based on the current database schema.

    Args:
        metadata_path: Path to database_metadata.json (default: data/database_metadata.json)
        db_path: Path to SQLite database (default: data/bird_data_complete.db)
        output_file: Path to save generated prompt (default: server/prompt.txt)
        save_to_file: Whether to save the prompt to a file (default: True)

    Returns:
        Generated system prompt string
    """
    # Default paths relative to project root
    if metadata_path is None:
        project_root = Path(__file__).parent.parent
        # Prefer data/ folder (where migration tool creates it) over root
        metadata_path = project_root / "data" / "database_metadata.json"
        if not metadata_path.exists():
            metadata_path = project_root / "database_metadata.json"

    if db_path is None:
        project_root = Path(__file__).parent.parent
        db_path = project_root / "data" / "bird_data_complete.db"
        if not db_path.exists():
            # Try root directory as fallback
            db_path = project_root / "bird_data_complete.db"

    if output_file is None:
        project_root = Path(__file__).parent
        output_file = project_root / "prompt.txt"

    generator = PromptGenerator(str(metadata_path), str(db_path))
    prompt = generator.generate_prompt()

    # Save to file if requested
    if save_to_file:
        output_path = Path(output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(prompt)
        print(f"✓ Prompt saved to: {output_path}")

    return prompt


if __name__ == "__main__":
    """Generate and save the system prompt."""
    import sys

    # Parse command line arguments
    save_file = True
    output_file = None

    if len(sys.argv) > 1:
        if sys.argv[1] == "--no-save":
            save_file = False
        else:
            output_file = sys.argv[1]

    try:
        print("=" * 70)
        print("Dynamic System Prompt Generator")
        print("=" * 70)
        print()

        prompt = generate_dynamic_prompt(save_to_file=save_file, output_file=output_file)

        print(f"\n✓ Prompt generated successfully")
        print(f"  Length: {len(prompt):,} characters")
        print(f"  Lines: {len(prompt.splitlines()):,}")

        if save_file:
            print(f"\nYou can now inspect the generated prompt at:")
            print(f"  server/prompt.txt")
            print(f"\nTo regenerate at any time, run:")
            print(f"  python server/generate_prompt.py")
        else:
            print("\n" + "=" * 70)
            print("GENERATED PROMPT (Preview - first 500 chars)")
            print("=" * 70)
            print(prompt[:500])
            print("...")

        print("\n" + "=" * 70)

    except Exception as e:
        print(f"❌ Error generating prompt: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
