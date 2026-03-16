# NestScope Public - Deployment Package

AI-powered Gulf Coast avian monitoring platform with **NestChat** (Text-to-SQL natural language queries) and **NestVision** (bird detection with computer vision).

## 📦 What's Included

This standalone package contains:

- **FastAPI Backend** (`main.py`) - REST API for NestChat & NestVision
- **Flask Webapp** (`webapp/`) - Clean HTML/CSS frontend with artifact rendering
- **Database** (`data/bird_data_complete.db`) - 2010-2021 Gulf Coast bird surveys (8.7MB)
- **Detection Models** (`models/`) - Swift ONNX bird detector + species classifier (~16MB)
- **Example Images** (`cv_tools/images/`) - Sample bird colony images

**Total Size:** ~67MB

## 🚀 Quick Start (Local Development)

### Prerequisites

- Python 3.11+
- OpenRouter API key ([get one here](https://openrouter.ai/keys))

### Setup

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Configure environment:**
```bash
cp .env.example .env
# Edit .env and add your OPENROUTER_API_KEY
```

3. **Run the application:**
```bash
./run.sh
```

This starts:
- FastAPI backend at `http://localhost:8000`
- Flask webapp at `http://localhost:8501`

## ☁️ Railway Deployment

### One-Click Deploy

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new)

### Manual Deployment

1. **Create a new Railway project**
```bash
railway login
railway init
```

2. **Set environment variables:**
```bash
railway variables set OPENROUTER_API_KEY=your-key-here
```

3. **Deploy:**
```bash
railway up
```

Railway will automatically:
- Detect `Procfile` and start the FastAPI backend
- Set `$PORT` environment variable
- Provide a public URL

### Environment Variables (Railway)

Required:
- `OPENROUTER_API_KEY` - Your OpenRouter API key

Optional:
- `MODEL_NAME` - Override model (default: from `config.yaml`)
- `DB_PATH` - Database path (default: `data/bird_data_complete.db`)

## 📁 Structure

```
public/
├── main.py              # FastAPI server (NestChat + NestVision endpoints)
├── requirements.txt     # Python dependencies
├── config.yaml          # Model and server configuration
├── Procfile             # Railway deployment config
├── run.sh               # Local startup script
├── .env.example         # Environment variable template
├── models/              # ONNX detection models
│   ├── swift.onnx       # Bird detector (10MB)
│   └── classifier_swift.onnx  # Species classifier (6MB)
├── data/                # Database
│   ├── bird_data_complete.db  # SQLite database (8.7MB)
│   └── database_metadata_enhanced.json  # Schema metadata
├── cv_tools/            # Computer vision inference
│   ├── inference.py     # BirdDetector class
│   └── images/          # Example images
├── prompts/             # LLM prompts for SQL generation
│   ├── prompt.txt       # Answer generation prompt
│   ├── sql_prompt.txt   # SQL generation prompt
│   ├── sql_prompt_reasoning.txt   # Reasoning phase prompt
│   └── sql_prompt_generation.txt  # Generation phase prompt
└── webapp/              # Flask frontend
    ├── app.py           # Flask server
    ├── api_client.py    # Backend API client
    ├── templates/       # HTML templates
    └── static/          # CSS, JS, assets
```

## 🔌 API Endpoints

### NestChat (Text-to-SQL)

- `POST /ask/agentic/stream` - Ask questions in natural language (streaming SSE)
  - Self-correcting SQL generation (max 3 attempts)
  - Real-time progress updates
  - Automatic artifact generation (charts, maps, tables)

- `GET /schema` - Get database schema
- `GET /stats` - Get database statistics
- `GET /api/species` - Get all species

### NestVision (Bird Detection)

- `POST /cv/inference` - Run bird detection on uploaded image
  - Returns: bird count, detections, annotated image (base64)
  - Species classification (7 groups)

- `GET /cv/examples` - Get list of example images
- `GET /cv/example/{filename}` - Get specific example image

### System

- `GET /health` - Health check
- `GET /config` - Get server configuration
- `GET /` - API documentation

Full interactive docs at `/docs` (Swagger UI)

## 🧠 How NestChat Works

### Agentic SQL Pipeline (5 Phases)

1. **Context & Setup** - Load database metadata
2. **Reasoning** - Analyze question structure (optional)
3. **SQL Generation** - Generate query from natural language
4. **Execution** - Run query with error handling
5. **Answer & Artifacts** - Generate natural language answer + visualizations

**Self-Correction:** If SQL fails, the AI analyzes the error and retries (max 3 attempts)

**Artifact Generation:** AI can generate:
- Line/bar charts (Chart.js)
- Geographic maps (Leaflet)
- HTML tables
- Custom visualizations

## 🎨 Frontend Features

- **Mobile-first design** (320px → 768px → 1024px breakpoints)
- **Artifact rendering** - Charts, maps, tables embedded in chat
- **Theme toggle** - Light/dark coastal theme
- **SSE streaming** - Real-time AI responses
- **Toast notifications** - User feedback
- **Example prompts** - Quick start questions

## 🗃️ Database Schema

### Primary Table: `tblColonyTotals2010-2021_MayJuneCombined`
Pre-aggregated bird and nest counts by colony, species, year.

**Key Columns:**
- `ColonyName`, `GeoRegion`, `State`
- `Year`, `Month` (May/June combined)
- `"# Adults"`, `"# Nests"` (actual bird counts)
- `Latitude`, `Longitude` (for mapping)

### Reference Tables:
- `tblSpeciesCodes` - Species codes and names
- `tblRWCWB_ColonyInventory_10Nov22` - Colony metadata

**Important:** Queries about "observations" mean bird/nest counts from `tblColonyTotals`, NOT photo records.

## 🛠️ Configuration

### Model Settings (`config.yaml`)

```yaml
model:
  name: "anthropic/claude-sonnet-4.5"
  temperature: 0.3
  max_tokens: 2000
  sql_temperature: 0.1
  sql_max_tokens: 1000

agentic:
  max_attempts: 3
  enable_reasoning: true

cv:
  default_confidence: 0.25
```

### Local Overrides (`.env`)

```
MODEL_NAME=anthropic/claude-opus-4  # Override model locally
```

## 📊 Usage Examples

### NestChat Examples

```
"How many brown pelicans were observed in 2020?"
"Show me the top 10 colonies by total bird count"
"What species are found in Texas colonies?"
"Compare nest counts between Louisiana and Mississippi"
```

### NestVision Example

Upload a bird colony image:
- Confidence threshold: 0.25 (default)
- Returns: bird count, bounding boxes, species classification
- Annotated image with color-coded detections

## 🔒 Security Features

- **Read-only database** - NestChat uses SQLite in read-only mode
- **Query validation** - Only SELECT/WITH statements allowed
- **No admin features** - Database editing disabled in public version
- **Comment stripping** - SQL comments removed before validation

## 📝 Logs

Local development logs:
```bash
tail -f logs/backend.log   # FastAPI backend
tail -f logs/webapp.log    # Flask webapp
```

Railway logs:
```bash
railway logs
```

## 🐛 Troubleshooting

### Backend won't start
- Check `OPENROUTER_API_KEY` is set in `.env`
- Verify database exists at `data/bird_data_complete.db`
- Check port 8000 is not in use: `lsof -i :8000`

### NestChat returns errors
- Ensure OpenRouter API key is valid
- Check model name in `config.yaml` is correct
- Review backend logs: `tail -f logs/backend.log`

### NestVision not working
- Verify models exist in `models/` directory
- Check ONNX Runtime is installed: `pip list | grep onnx`
- Ensure image file size < 100MB

### Railway deployment fails
- Check `Procfile` exists
- Verify `requirements.txt` is complete
- Set `OPENROUTER_API_KEY` in Railway dashboard

## 📚 Documentation

- **API Docs:** `http://localhost:8000/docs` (Swagger UI)
- **Model Info:** [OpenRouter Models](https://openrouter.ai/models)
- **YOLO Detection:** [Ultralytics Docs](https://docs.ultralytics.com/)

## 🤝 Support

For issues or questions:
1. Check logs first (`logs/backend.log`, `logs/webapp.log`)
2. Verify environment variables are set correctly
3. Test API endpoints directly: `curl http://localhost:8000/health`

## 📄 License

This is a public deployment package for the NestScope project (DevDays 2026).
Data source: Gulf Coast bird colony surveys (2010-2021).

---

**Built with:** FastAPI, Flask, OpenRouter (Claude), Ultralytics YOLO, Chart.js, Leaflet
