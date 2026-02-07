# Louisiana Coastal Bird Monitoring Copilot

**AI-Powered Natural Language Interface for NOAA Bird Survey Data**

Transform bird survey analysis from hours to seconds using AI via OpenRouter.

---

## Project Overview

**Goal**: Build an AI-powered natural language interface for Louisiana coastal bird survey data that reduces analysis time from hours to seconds.

**Data Source**: NOAA DIVER Deepwater Horizon Avian Monitoring Database (2010-2021)

**Timeline**: 8 hours (9 AM - 5 PM)

### The Innovation

Instead of manually querying databases or writing complex SQL, users can ask natural language questions:
- "Show brown pelican trends from 2015-2021 in Louisiana"
- "What were the top 5 species in 2020?"
- "Compare Terrebonne vs Plaquemines parishes"
- "How did Hurricane Ida affect bird populations?"

The system uses AI via OpenRouter to understand the question, generate appropriate database queries, visualize results, and provide AI-generated explanations.

---

## Quick Start

### 1. Installation

```bash
# Clone repository
git clone <repository-url>
cd nexus

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Set Up Environment Variables

```bash
# Create .env file
echo "OPENROUTER_API_KEY=your_api_key_here" > .env
```

Get your API key from [openrouter.ai/keys](https://openrouter.ai/keys)

### 3. Load Data

```bash
# Extract CSV files from Access database (manual step)
# Then load into DuckDB
python src/data/load_data.py
```

### 4. Launch Application

```bash
streamlit run src/app/app.py
```

---

## Tech Stack

### Data Layer
- **DuckDB** - Fast analytical database for storing bird survey data
- **Pandas** - Data manipulation and CSV processing
- **Python** - Core programming language

### AI/LLM Layer
- **OpenRouter API** - Natural language understanding and query planning
- **Function Calling** - Structured query generation

### Frontend Layer
- **Streamlit** - Web application framework
- **Plotly** - Interactive data visualizations
- **Streamlit-folium** (optional) - Map visualizations

### Development Tools
- **Git/GitHub** - Version control
- **Python venv** - Virtual environment management
- **dotenv** - Environment variable management

---

## Project Structure

```
coastal-bird-copilot/
├── data/
│   ├── raw/                    # CSV files from Access export
│   └── processed/              # DuckDB database
├── src/
│   ├── data/                   # Data functions
│   │   ├── load_data.py        # Load CSVs into DuckDB
│   │   └── queries.py          # Query functions (species trends, comparisons)
│   ├── llm/                    # AI functions
│   │   ├── functions.py        # Claude function schemas
│   │   ├── planner.py          # Query planner (natural language → function calls)
│   │   └── formatter.py        # AI response generation
│   └── app/                    # Frontend
│       ├── app.py              # Streamlit web interface
│       └── charts.py           # Visualization components
├── tests/                      # Test cases
├── docs/                       # Documentation
├── .env                        # API keys (gitignored)
├── .gitignore
├── requirements.txt
└── README.md
```

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   USER INTERACTION                          │
│  "Show brown pelican trends from 2015-2021 in Louisiana"   │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                  STREAMLIT FRONTEND                         │
│  - Captures user question                                   │
│  - Shows loading indicator                                  │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                  LLM PLANNER (OpenRouter)                   │
│  - Understands natural language question                   │
│  - Extracts parameters: species="Brown Pelican"             │
│                        start_year=2015, end_year=2021       │
│  - Selects function: species_trend()                        │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                  QUERY FUNCTIONS                            │
│  - Execute DuckDB query                                     │
│  - Return structured data (DataFrame)                       │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                  DUCKDB DATABASE                            │
│  - Fast SQL queries on bird survey data                    │
│  - Aggregations, filtering, grouping                       │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│              VISUALIZATION & RESPONSE                       │
│  - Generate Plotly chart from data                          │
│  - LLM generates natural language explanation              │
│  - Display results to user                                  │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Features

- **Natural Language Queries**: Ask questions in plain English
- **Fast Analytics**: DuckDB provides subsecond query performance
- **AI Explanations**: LLM generates insights from the data
- **Interactive Visualizations**: Plotly charts for exploring trends
- **Geographic Analysis**: Compare different parishes and regions
- **Time Series Analysis**: Track species populations over years
- **Species Comparisons**: Analyze multiple species simultaneously

---

## Demo Queries

Here are 5 example queries to showcase the system:

1. **Trend Analysis**
   - "Show brown pelican trends from 2015-2021"
   - Output: Line chart + AI explanation

2. **Species Ranking**
   - "What were the top 5 species in 2020?"
   - Output: Bar chart + AI explanation

3. **Geographic Comparison**
   - "Compare Terrebonne vs Plaquemines parishes"
   - Output: Comparison chart + AI explanation

4. **Impact Assessment**
   - "How did Hurricane Ida affect bird populations?"
   - Output: Before/after comparison + AI explanation

5. **Colony Detail**
   - "Tell me about the Grand Isle colony"
   - Output: Multi-year trend + map + AI explanation

---

## Development Workflow

### Team Roles

**Person 1: Data Engineer**
- Extract data from Access database to CSV
- Load data into DuckDB
- Write query functions (species trends, comparisons, aggregations)
- Data validation and cleaning

**Person 2: LLM/AI Developer**
- Set up OpenRouter API integration
- Build query planner (natural language → function calls)
- Design function schemas for LLM
- Generate AI explanations for results

**Person 3: Frontend Developer**
- Build Streamlit web interface
- Create chart/visualization components
- Implement user interaction flow
- Error handling and loading states

**Person 4: Project Manager/QA**
- Extract data from Access database
- Create test cases and sample queries
- Documentation and README
- Demo preparation and presentation

### Hour-by-Hour Timeline

**Hour 1 (9:00-10:00 AM)**: Setup & Data Extraction
- Create project structure, set up Python environment
- Get OpenRouter API key, test connection
- Design UI wireframe
- Export CSV files from Access database

**Hour 2 (10:00-11:00 AM)**: Core Pipeline
- Load CSVs into DuckDB, clean data
- Design function schemas for LLM
- Build basic Streamlit app skeleton
- Validate data, create test queries

**Hour 3 (11:00 AM-12:00 PM)**: Query Functions
- Implement query functions (trends, comparisons, top species)
- Build LLM query planner
- Create chart rendering functions
- Test query functions manually

**Hour 4 (12:00-1:00 PM)**: Lunch + Integration
- 30-min lunch, then connect components
- Connect LLM planner to query functions
- Integrate queries into UI
- Write README documentation

**Hour 5 (1:00-2:00 PM)**: Visualization & Responses
- Add data export, optimize performance
- Build AI response formatter
- Complete full app integration with charts
- Create demo script with sample queries

**Hour 6 (2:00-3:00 PM)**: Advanced Features
- Advanced queries (aggregations, geographic)
- Multi-step reasoning, context memory
- Interactive features (drill-down, filters, maps)
- QA testing, bug tracking

**Hour 7 (3:00-4:00 PM)**: Polish & Testing
- Error handling, logging, validation
- Handle edge cases, ambiguous queries
- UI/UX polish, accessibility
- Final testing, update documentation

**Hour 8 (4:00-5:00 PM)**: Demo Prep
- Full integration test, demo rehearsal
- Create presentation slides, prepare backup plan

---

## Data Source

**NOAA DIVER Database**: Deepwater Horizon Avian Monitoring
- Years: 2010-2021
- Coverage: Louisiana coastal parishes
- Data types: Species counts, colony locations, survey dates, environmental conditions
- Format: Microsoft Access database (export to CSV)

---

## Contributing

This project was developed during an 8-hour hackathon. Contributions are welcome for:
- Additional query functions
- New visualization types
- Performance optimizations
- UI/UX improvements
- Documentation

---

## License

[Add your license here]

---

## Acknowledgments

- **NOAA** - For providing the Deepwater Horizon Avian Monitoring Database
- **OpenRouter** - For providing unified LLM API access
- **DuckDB Team** - For the fast analytical database

---

## Contact

[Add your contact information or team details]

---

**Built for Louisiana's Coastal Bird Conservation**
