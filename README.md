# NestScope

**AI-Powered Gulf Coast Avian Monitoring Platform**

NestScope combines natural language database queries with computer vision bird detection to analyze Gulf Coast colonial waterbird data from 2010-2021.

## Features

### 💬 NestChat
- Natural language queries of bird colony data
- AI-generated SQL with automatic visualization
- Interactive maps and charts
- Export results as CSV

### 🦅 NestVision
- AI bird detection and counting
- YOLO-based object detection (ONNX)
- SAHI (Slicing Aided Hyper Inference) support
- Species identification workflow
- Annotation correction tool

## Quick Start

### Prerequisites
- Python 3.8+
- OpenRouter API key (for LLM access)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd nexus
```

2. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env and add your OPENROUTER_API_KEY
```

5. Set up the database:
```bash
python scripts/data_management/import_all_to_sqlite.py
```

### Running the Application

Start all services (FastAPI, Streamlit, Labeller):
```bash
./run_app.sh
```

Or run services individually:

**Backend API:**
```bash
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend:**
```bash
streamlit run frontend/app.py --server.port 8501
```

**Labeller:**
```bash
python labeller/app.py --data labeller/nestvision
```

### Access Points

- **Streamlit App**: http://localhost:8501
- **API Server**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Labeller**: http://localhost:5000

## Project Structure

```
nexus/
├── frontend/               # Streamlit web application
│   ├── pages/              # Multi-page app structure
│   ├── services/           # API communication
│   ├── components/         # Reusable UI components
│   ├── utils/              # Helper functions
│   └── styles/             # UI theming
├── server/                 # FastAPI backend
│   ├── cv_tools/           # Computer vision inference
│   └── main.py             # API endpoints
├── labeller/               # Annotation tool
├── VisionTrain/            # Model training pipeline
├── models/                 # Model files (.pt, .onnx)
├── data/                   # SQLite database
├── CSV_Files/              # Source CSV data
├── scripts/                # Utility scripts
│   ├── data_management/    # Database scripts
│   ├── analysis/           # Analysis tools
│   └── deployment/         # Deployment scripts
└── docs/                   # Documentation

```

## Technology Stack

- **Backend**: FastAPI, SQLite, OpenRouter API (Claude)
- **Frontend**: Streamlit
- **Computer Vision**: ONNX Runtime, SAHI, Ultralytics YOLO
- **Segmentation**: MobileSAM
- **Labelling**: Flask, HTML/JS

## Model Information

### Detection Model
- **File**: `models/seconditer.onnx`
- **Type**: YOLOv8-based ONNX
- **Input**: 1024x1024
- **Purpose**: Bird detection and counting

### Segmentation Model
- **File**: `models/mobile_sam.pt`
- **Type**: MobileSAM (PyTorch)
- **Purpose**: Interactive segmentation in labeller

### Detection Model (Legacy)
- **File**: `models/best.pt`
- **Type**: PyTorch YOLO
- **Purpose**: Legacy detection model

## Agentic Visualization

NestScope uses an agentic approach where the backend LLM controls visualizations:

- The LLM analyzes query results and user intent
- It decides whether to show charts (line/bar) or maps
- Frontend respects these directives instead of auto-detecting
- Provides context-aware, intelligent visualizations

## Data Coverage

- **Years**: 2010-2021
- **States**: Texas, Louisiana, Mississippi, Alabama, Florida
- **Species**: 20+ coastal waterbird species
- **Observations**: 100,000+ data points

## Development

See [docs/guides/SETUP.md](docs/guides/SETUP.md) for detailed setup instructions.

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]

## Support

For issues and questions, please create an issue on the repository.
