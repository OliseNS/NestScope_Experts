# Server Directory Organization

Clean, organized structure for the NestScope backend API.

## Directory Structure

```
server/
├── main.py                 # FastAPI application (main entry point)
├── config.yaml             # Configuration (model settings, API config)
├── requirements.txt        # Python dependencies
│
├── prompts/               # AI prompt templates (organized!)
│   ├── prompt.txt                    # Main answer generation prompt
│   ├── sql_prompt.txt                # SQL generation prompt
│   ├── sql_prompt_reasoning.txt      # Phase 2: reasoning/planning
│   ├── sql_prompt_generation.txt     # Phase 3: SQL generation
│   └── sql_prompt_evaluation.txt     # Phase 4: result validation
│
├── cv_tools/              # Computer vision (bird detection)
│   ├── inference.py                  # YOLO detection engine
│   ├── classifier_species.py         # Species classification
│   └── images/                       # Example images
│
├── flood_tools/           # NOAA/FEMA flood data integration
│   ├── flood_database.py             # Flood risk database
│   ├── noaa_client.py                # NOAA API client
│   └── fema_client.py                # FEMA NFHL API client
│
├── coastal_tools/         # Hurricane and coastal data
│   └── hurricane_data.py             # HURDAT2 storm tracks
│
├── stac_tools/            # STAC catalog integration
│   └── stac_client.py                # Water Institute STAC client
│
├── services/              # Shared business logic
│   ├── db_explorer.py                # Database introspection
│   ├── risk_intelligence.py          # Multi-modal risk fusion
│   ├── flood_cache.py                # Flood data caching
│   └── metadata_compressor.py        # Schema compression
│
├── db_version.py          # Database version control
├── db_change_tracker.py   # Change tracking for bird data
│
└── logs/                  # Runtime logs (created by run_app.sh)
```

## What Changed (March 15, 2026 Cleanup)

### Deleted
- `server/admin/` - Unused duplicate directory with old copies of tools (saved ~2MB)

### Organized
- Created `server/prompts/` folder
- Moved all 5 prompt files from root into `prompts/`
- Updated `main.py` to load prompts from new location

### Unchanged
All active tool directories remain the same:
- `cv_tools/` - Used by NestVision
- `flood_tools/` - Used by Risk Intelligence
- `coastal_tools/` - Used by Risk Intelligence
- `stac_tools/` - Used by STAC endpoints
- `services/` - Shared across multiple features

## Active Tools

All directories in `server/` are actively used:

| Directory | Used By | Purpose |
|-----------|---------|---------|
| `cv_tools/` | NestVision | Bird detection and species classification |
| `flood_tools/` | Risk Intelligence | NOAA water levels, FEMA flood zones |
| `coastal_tools/` | Risk Intelligence | Hurricane tracks and storm data |
| `stac_tools/` | STAC Endpoints | Water Institute catalog integration |
| `services/` | Multiple | Shared business logic and utilities |
| `prompts/` | NestChat | AI prompt templates for SQL and answers |

## Imports

All imports follow the pattern:
```python
from server.cv_tools.inference import BirdDetector
from server.flood_tools.noaa_client import NOAAClient
from server.services.risk_intelligence import RiskIntelligenceService
from server.stac_tools.stac_client import STACClient
```

No more confusion!
