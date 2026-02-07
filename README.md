# Bird Colony Data Chatbot

**AI-Powered Natural Language Interface for Gulf Coast Bird Survey Data**

An intelligent chatbot that analyzes bird colony observations, coastal erosion patterns, and environmental changes using natural language queries powered by Claude 3.5 Sonnet.

---

## Overview

This project provides a conversational interface to explore NOAA's Deepwater Horizon Avian Monitoring Database (2010-2021), enabling researchers, conservationists, and policymakers to analyze:

- **Bird Population Dynamics**: 13,075+ observations across 73 species
- **Coastal Erosion Patterns**: Track 67% colony loss (288 → 94 active colonies) from 2010-2021
- **Environmental Impacts**: Oil spill effects, storm damage, habitat degradation
- **Species Migration Trends**: Seasonal presence/absence patterns

**Key Features:**
- Natural language queries (no SQL knowledge required)
- AI-generated SQL queries using Claude 3.5 Sonnet
- Comprehensive erosion and habitat change analysis
- Real-time answers with data visualizations
- 11+ years of longitudinal data

---

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd nexus

# Install dependencies
pip install openai pandas python-dotenv
```

### 2. Setup API Key

Create a `.env` file in the project root:
```bash
OPENROUTER_API_KEY=your_api_key_here
```

Get your API key from [openrouter.ai/keys](https://openrouter.ai/keys)

### 3. Run the Chatbot

```bash
python chatbot.py
```

That's it! The database is pre-built and ready to use.

---

## Example Queries

### Bird Population Analysis
```
- "What colonies had oil present in 2010?"
- "Which species were observed most frequently?"
- "Show me Brown Pelican observations from 2010-2021"
```

### Coastal Erosion Analysis
```
- "Which colonies were active in 2010 but disappeared by 2021?"
- "Show colonies with notes mentioning flooding or erosion"
- "What percentage of colonies were lost over time?"
- "List colonies affected by Hurricane Isaac"
```

### Environmental Change
```
- "How did habitats change at Cat Bay South Island?"
- "Show observations with vegetation loss"
- "Which barrier islands show the most degradation?"
```

---

## Project Structure

```
nexus/
├── chatbot.py                  # Main application (run this!)
├── sql_chatbot.py              # SQL chatbot implementation
├── create_sql_database.py      # Database builder
├── clean_and_prepare_data.py   # Data preparation script
├── bird_data.db                # SQLite database (5.3 MB)
├── CSV_Files/                  # Original raw data (59,957 rows)
├── cleaned_data/               # Processed data files
│   ├── observations.csv        # 13,075 observations
│   ├── colony_profiles.csv     # 492 colony profiles
│   ├── species_lookup.json     # 73 species codes
│   └── metadata.json           # Dataset metadata
├── docs/                       # Documentation
│   ├── SETUP.md                # Installation guide
│   ├── USAGE.md                # User guide
│   ├── DATA_SCHEMA.md          # Database schema
│   ├── EROSION_ANALYSIS.md     # Erosion analysis guide
│   ├── MIGRATION_ANALYSIS.md   # Migration patterns guide
│   ├── EXAMPLES.md             # Example queries
│   └── API_REFERENCE.md        # Technical reference
├── .env                        # API keys (create this)
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

---

## Dataset Overview

**Source**: NOAA DIVER Deepwater Horizon Avian Monitoring Database

**Coverage**:
- **Time Period**: 2010-2021 (post-Deepwater Horizon oil spill)
- **Geographic Area**: Gulf Coast (TX, LA, MS, AL, FL)
- **Observations**: 13,075 field observations
- **Colonies**: 492 tracked colonies
- **Species**: 73 bird species

**Most Observed Species**:
1. Laughing Gull (LAGU): 2,700 observations
2. Brown Pelican (BRPE): 2,017 observations
3. Tricolored Heron (TRHE): 1,047 observations
4. Royal Tern (ROYT): 608 observations
5. Black Skimmer (BLSK): 595 observations

**Observations by Year**:
- 2010: 2,570 (Deepwater Horizon year)
- 2011: 1,795
- 2012: 1,067
- 2013: 1,342
- 2015: 3,396
- 2018: 1,172
- 2021: 1,733

---

## Key Findings

### Coastal Erosion Impact
- **67% Colony Loss**: 194 of 288 colonies lost between 2010-2021
- **Active Colonies 2010**: 288 colonies
- **Active Colonies 2021**: 94 colonies
- **Major Causes**: Storms, flooding, habitat overwash, vegetation loss

### Oil Spill Impact
- **5 colonies** documented with oil presence in 2010
- Includes: Chandeleur South C, Gaillard Island, Manilla Island, Martin Island, Queen Bess Island

### Storm Damage
- Hurricane Isaac (2012) impacts documented
- Notes mention "land and vegetation likely reduced compared to prior years"
- Multiple colonies show "overwash" and flooding events

---

## Documentation

Comprehensive documentation is available in the `docs/` folder:

- **[SETUP.md](docs/SETUP.md)** - Detailed installation and configuration
- **[USAGE.md](docs/USAGE.md)** - How to use the chatbot
- **[DATA_SCHEMA.md](docs/DATA_SCHEMA.md)** - Database structure and fields
- **[EROSION_ANALYSIS.md](docs/EROSION_ANALYSIS.md)** - Guide for coastal erosion research
- **[MIGRATION_ANALYSIS.md](docs/MIGRATION_ANALYSIS.md)** - Species migration patterns
- **[EXAMPLES.md](docs/EXAMPLES.md)** - 50+ example queries
- **[API_REFERENCE.md](docs/API_REFERENCE.md)** - Technical reference

---

## Technology Stack

- **Database**: SQLite (5.3 MB, indexed for fast queries)
- **AI Model**: Claude 3.5 Sonnet via OpenRouter
- **Language**: Python 3
- **Libraries**:
  - `openai` - OpenRouter API client
  - `pandas` - Data processing
  - `sqlite3` - Database operations
  - `python-dotenv` - Environment variables

---

## Use Cases

### For Researchers
- Analyze population trends across species and time
- Study oil spill impacts on bird colonies
- Track species diversity changes
- Generate datasets for publications

### For Conservationists
- Identify colonies at risk from erosion
- Monitor habitat degradation patterns
- Assess storm impact on nesting sites
- Prioritize restoration efforts

### For Policymakers
- Quantify coastal land loss
- Evaluate environmental policy effectiveness
- Support restoration funding decisions
- Track recovery from Deepwater Horizon spill

### For Educators
- Teach ecological data analysis
- Demonstrate LLM applications in science
- Explore environmental change over time
- Hands-on coastal conservation education

---

## Limitations

**What This Dataset Can Do:**
- ✅ Track bird populations at breeding colonies
- ✅ Analyze coastal erosion and habitat loss
- ✅ Document oil spill and storm impacts
- ✅ Compare species presence/absence over time

**What This Dataset Cannot Do:**
- ❌ Track individual bird migration routes (no GPS tracking)
- ❌ Provide winter/non-breeding season data
- ❌ Show real-time current conditions (data ends 2021)
- ❌ Cover non-Gulf Coast regions

---

## Advanced Usage

### Rebuild Database

If you modify the cleaned CSV files:
```bash
python create_sql_database.py
```

### Prepare New Data

To process new raw data:
```bash
python clean_and_prepare_data.py
```

### Custom Queries

You can also query the database directly:
```bash
sqlite3 bird_data.db "SELECT * FROM observations LIMIT 10;"
```

---

## Data Source & Acknowledgments

**NOAA DIVER Database**: Deepwater Horizon Avian Monitoring

This dataset documents bird colony observations following the 2010 Deepwater Horizon oil spill in the Gulf of Mexico. The data includes detailed observations of 73 bird species across 492 colonies from 2010-2021, providing critical information for understanding the spill's long-term impact on coastal bird populations and habitats.

**Acknowledgments:**
- **NOAA** - For providing the Deepwater Horizon Avian Monitoring Database
- **OpenRouter** - For providing unified LLM API access
- **Anthropic** - For Claude 3.5 Sonnet

---

## Contributing

Contributions are welcome! Areas for improvement:
- Additional analysis tools
- Data visualization features
- Export functionality
- Performance optimizations
- Additional documentation

---

## License

[Specify your license here]

---

## Contact

[Add your contact information or team details]

---

**Built for Gulf Coast Bird Conservation and Environmental Research**

*Combining AI technology with environmental science to understand and protect coastal ecosystems.*
