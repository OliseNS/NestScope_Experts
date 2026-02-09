# NestScope Cloud Migration Guide

This guide provides step-by-step instructions for migrating NestScope from local development to production cloud infrastructure using Supabase (PostgreSQL database) and Railway (application hosting).

---

## Table of Contents

1. [Migration Overview](#migration-overview)
2. [Prerequisites](#prerequisites)
3. [Phase 1: Database Migration to Supabase](#phase-1-database-migration-to-supabase)
4. [Phase 2: Server Deployment to Railway](#phase-2-server-deployment-to-railway)
5. [Phase 3: Model Hosting Strategy](#phase-3-model-hosting-strategy)
6. [Phase 4: Frontend Deployment](#phase-4-frontend-deployment)
7. [Testing & Validation](#testing--validation)
8. [Rollback Plan](#rollback-plan)
9. [Cost Estimates](#cost-estimates)
10. [Troubleshooting](#troubleshooting)

---

## Migration Overview

### Current Architecture (Local)
```
┌─────────────────────────────────────────────┐
│  Streamlit Frontend (localhost:8501)        │
└────────────────┬────────────────────────────┘
                 │ HTTP
┌────────────────▼────────────────────────────┐
│  FastAPI Backend (localhost:8000)           │
│  ├── Text-to-SQL (OpenRouter API)           │
│  └── YOLO Bird Detection (best.pt)          │
└──────┬──────────────────────┬───────────────┘
       │                      │
┌──────▼─────────┐   ┌────────▼────────────┐
│  SQLite DB     │   │  YOLOv6m Model      │
│  (10.5 MB)     │   │  (40.5 MB)          │
└────────────────┘   └─────────────────────┘
```

### Target Architecture (Cloud)
```
┌─────────────────────────────────────────────┐
│  Streamlit Cloud / Railway Frontend         │
│  (https://nestscope.streamlit.app)          │
└────────────────┬────────────────────────────┘
                 │ HTTPS
┌────────────────▼────────────────────────────┐
│  Railway FastAPI Backend                    │
│  (https://nestscope-api.railway.app)        │
│  ├── Text-to-SQL (OpenRouter API)           │
│  └── YOLO Inference (API call)              │
└──────┬──────────────────────┬───────────────┘
       │                      │
┌──────▼─────────┐   ┌────────▼────────────┐
│  Supabase      │   │  Hugging Face       │
│  PostgreSQL    │   │  Inference API      │
│  (Free tier)   │   │  (YOLOv6m)          │
└────────────────┘   └─────────────────────┘
```

---

## Prerequisites

### Required Accounts
1. **Supabase** - https://supabase.com (Free tier available)
2. **Railway** - https://railway.app (Free $5 credit, then usage-based)
3. **Hugging Face** - https://huggingface.co (Free tier for model hosting)
4. **Streamlit Cloud** - https://streamlit.io/cloud (Free tier available)

### Local Tools
```bash
# Install required tools
pip install psycopg2-binary  # PostgreSQL adapter
pip install supabase  # Supabase client library
pip install railway  # Railway CLI
```

### API Keys Needed
- ✓ OpenRouter API key (already have)
- □ Supabase project URL & API key (create in Phase 1)
- □ Hugging Face API token (create in Phase 3)
- □ Railway project token (create in Phase 2)

---

## Phase 1: Database Migration to Supabase

### 1.1 Create Supabase Project

1. Go to https://supabase.com and sign up/login
2. Click "New Project"
3. Configure:
   - **Name**: `nestscope-production`
   - **Database Password**: (generate strong password - save it!)
   - **Region**: Select closest to your users (e.g., `us-east-1`)
   - **Plan**: Free tier (500 MB database, 2 GB bandwidth/month)

4. Wait 2-3 minutes for project provisioning

### 1.2 Get Supabase Credentials

After project is created:

1. Go to **Settings** → **API**
2. Copy these values:
   ```
   Project URL: https://xxxxx.supabase.co
   anon/public key: eyJhbGc...
   service_role key: eyJhbGc... (keep secret!)
   ```

3. Go to **Settings** → **Database**
4. Copy connection string:
   ```
   postgres://postgres:[YOUR-PASSWORD]@db.xxxxx.supabase.co:5432/postgres
   ```

### 1.3 Export SQLite Data

Create a migration script `scripts/migrate_to_supabase.py`:

```python
"""
Migrate SQLite database to Supabase PostgreSQL
"""
import sqlite3
import psycopg2
from psycopg2.extras import execute_batch
import os
from pathlib import Path

# Supabase connection string
SUPABASE_URL = os.getenv("SUPABASE_DB_URL")  # Set this in .env

def get_sqlite_connection():
    """Connect to local SQLite database"""
    db_path = Path(__file__).parent.parent / "data" / "bird_data_complete.db"
    return sqlite3.connect(db_path)

def get_postgres_connection():
    """Connect to Supabase PostgreSQL"""
    return psycopg2.connect(SUPABASE_URL)

def create_postgres_schema(pg_conn):
    """Create PostgreSQL schema matching SQLite structure"""
    cursor = pg_conn.cursor()

    # Drop existing tables if they exist
    tables = [
        'species_data_2015_2021',
        'species_data_2011_2013',
        'species_data_2010',
        'colony_totals',
        'colony_site_notes',
        'colony_inventory',
        'colony_coordinates',
        'species_codes'
    ]

    for table in tables:
        cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")

    # 1. Species codes
    cursor.execute("""
        CREATE TABLE species_codes (
            SpeciesCode VARCHAR(10) PRIMARY KEY,
            SpeciesName VARCHAR(100) NOT NULL
        )
    """)

    # 2. Colony coordinates
    cursor.execute("""
        CREATE TABLE colony_coordinates (
            ColonyID VARCHAR(50) PRIMARY KEY,
            ColonyName VARCHAR(100) NOT NULL,
            State VARCHAR(2),
            Latitude DECIMAL(10, 6),
            Longitude DECIMAL(10, 6),
            GeoRegion VARCHAR(50)
        )
    """)

    # 3. Colony inventory
    cursor.execute("""
        CREATE TABLE colony_inventory (
            ColonyID VARCHAR(50) PRIMARY KEY,
            ColonyName VARCHAR(100),
            Habitat VARCHAR(100),
            Latitude DECIMAL(10, 6),
            Longitude DECIMAL(10, 6),
            State VARCHAR(2)
        )
    """)

    # 4. Colony site notes
    cursor.execute("""
        CREATE TABLE colony_site_notes (
            id SERIAL PRIMARY KEY,
            ColonyName VARCHAR(100),
            Year INTEGER,
            Date DATE,
            Oil VARCHAR(10),
            Notes TEXT,
            Latitude DECIMAL(10, 6),
            Longitude DECIMAL(10, 6)
        )
    """)

    # 5. Colony totals
    cursor.execute("""
        CREATE TABLE colony_totals (
            id SERIAL PRIMARY KEY,
            ColonyName VARCHAR(100),
            Year INTEGER,
            SpeciesCode VARCHAR(10),
            Nests INTEGER DEFAULT 0,
            Latitude DECIMAL(10, 6),
            Longitude DECIMAL(10, 6),
            FOREIGN KEY (SpeciesCode) REFERENCES species_codes(SpeciesCode)
        )
    """)

    # 6-8. Species data tables (2010, 2011-2013, 2015-2021)
    for table_name in ['species_data_2010', 'species_data_2011_2013', 'species_data_2015_2021']:
        cursor.execute(f"""
            CREATE TABLE {table_name} (
                id SERIAL PRIMARY KEY,
                ColonyName VARCHAR(100),
                Year INTEGER,
                SpeciesCode VARCHAR(10),
                Site INTEGER DEFAULT 0,
                WBN INTEGER DEFAULT 0,
                EmptyNest INTEGER DEFAULT 0,
                Latitude DECIMAL(10, 6),
                Longitude DECIMAL(10, 6),
                FOREIGN KEY (SpeciesCode) REFERENCES species_codes(SpeciesCode)
            )
        """)

    # Create indexes for common queries
    cursor.execute("CREATE INDEX idx_colony_totals_year ON colony_totals(Year)")
    cursor.execute("CREATE INDEX idx_colony_totals_species ON colony_totals(SpeciesCode)")
    cursor.execute("CREATE INDEX idx_species_2010_year ON species_data_2010(Year)")
    cursor.execute("CREATE INDEX idx_species_2011_year ON species_data_2011_2013(Year)")
    cursor.execute("CREATE INDEX idx_species_2015_year ON species_data_2015_2021(Year)")

    pg_conn.commit()
    print("✓ PostgreSQL schema created successfully")

def migrate_table(sqlite_conn, pg_conn, table_name):
    """Migrate a single table from SQLite to PostgreSQL"""
    print(f"\nMigrating table: {table_name}")

    sqlite_cursor = sqlite_conn.cursor()
    pg_cursor = pg_conn.cursor()

    # Get column names
    sqlite_cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in sqlite_cursor.fetchall()]

    # Fetch all data
    sqlite_cursor.execute(f"SELECT * FROM {table_name}")
    rows = sqlite_cursor.fetchall()

    if not rows:
        print(f"  ⚠ Table {table_name} is empty")
        return

    # Insert into PostgreSQL
    placeholders = ','.join(['%s'] * len(columns))
    insert_query = f"INSERT INTO {table_name} ({','.join(columns)}) VALUES ({placeholders})"

    # Batch insert for efficiency
    execute_batch(pg_cursor, insert_query, rows, page_size=1000)
    pg_conn.commit()

    print(f"  ✓ Migrated {len(rows):,} rows")

def main():
    """Run migration"""
    print("=" * 80)
    print("NestScope SQLite → Supabase PostgreSQL Migration")
    print("=" * 80)

    # Connect to databases
    print("\n1. Connecting to databases...")
    sqlite_conn = get_sqlite_connection()
    pg_conn = get_postgres_connection()
    print("  ✓ Connected to SQLite and PostgreSQL")

    # Create PostgreSQL schema
    print("\n2. Creating PostgreSQL schema...")
    create_postgres_schema(pg_conn)

    # Migrate tables in order (respecting foreign key constraints)
    print("\n3. Migrating data...")
    tables = [
        'species_codes',
        'colony_coordinates',
        'colony_inventory',
        'colony_site_notes',
        'colony_totals',
        'species_data_2010',
        'species_data_2011_2013',
        'species_data_2015_2021'
    ]

    for table in tables:
        migrate_table(sqlite_conn, pg_conn, table)

    # Verify migration
    print("\n4. Verifying migration...")
    pg_cursor = pg_conn.cursor()
    for table in tables:
        pg_cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = pg_cursor.fetchone()[0]
        print(f"  {table}: {count:,} rows")

    # Close connections
    sqlite_conn.close()
    pg_conn.close()

    print("\n" + "=" * 80)
    print("✓ Migration completed successfully!")
    print("=" * 80)

if __name__ == '__main__':
    main()
```

### 1.4 Run Migration

```bash
# Add Supabase URL to .env
echo "SUPABASE_DB_URL=postgres://postgres:[PASSWORD]@db.xxxxx.supabase.co:5432/postgres" >> .env

# Install PostgreSQL adapter
pip install psycopg2-binary

# Run migration
python scripts/migrate_to_supabase.py
```

Expected output:
```
NestScope SQLite → Supabase PostgreSQL Migration
================================================================================

1. Connecting to databases...
  ✓ Connected to SQLite and PostgreSQL

2. Creating PostgreSQL schema...
  ✓ PostgreSQL schema created successfully

3. Migrating data...

Migrating table: species_codes
  ✓ Migrated 73 rows

Migrating table: colony_coordinates
  ✓ Migrated 87 rows

[... continues for all tables ...]

4. Verifying migration...
  species_codes: 73 rows
  colony_totals: 5,931 rows
  species_data_2010: 9,557 rows
  species_data_2011_2013: 15,920 rows
  species_data_2015_2021: 23,747 rows
  [...]

================================================================================
✓ Migration completed successfully!
================================================================================
```

### 1.5 Update Application to Use PostgreSQL

Edit `server/main.py` to support both SQLite (local) and PostgreSQL (production):

```python
import os
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor

# Database configuration
DB_TYPE = os.getenv("DB_TYPE", "sqlite")  # "sqlite" or "postgres"
DB_PATH = os.getenv("DB_PATH", "../data/bird_data_complete.db")
SUPABASE_URL = os.getenv("SUPABASE_DB_URL", None)

class DatabaseConnection:
    """Database connection manager supporting SQLite and PostgreSQL"""

    def __init__(self):
        self.db_type = DB_TYPE
        self.db_path = DB_PATH
        self.pg_url = SUPABASE_URL

    def get_connection(self):
        """Get database connection based on DB_TYPE"""
        if self.db_type == "postgres":
            return psycopg2.connect(self.pg_url, cursor_factory=RealDictCursor)
        else:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn

    def execute_query(self, query):
        """Execute query and return results"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(query)
            results = cursor.fetchall()

            # Convert to list of dicts for consistency
            if self.db_type == "postgres":
                return [dict(row) for row in results]
            else:
                return [dict(row) for row in results]
        finally:
            conn.close()
```

Update `.env` for production:
```bash
DB_TYPE=postgres
SUPABASE_DB_URL=postgres://postgres:[PASSWORD]@db.xxxxx.supabase.co:5432/postgres
```

---

## Phase 2: Server Deployment to Railway

### 2.1 Prepare Application for Railway

1. **Create `railway.json`** in project root:
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "uvicorn server.main:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 100
  }
}
```

2. **Create `Procfile`**:
```
web: uvicorn server.main:app --host 0.0.0.0 --port $PORT
```

3. **Add health check endpoint** to `server/main.py`:
```python
@app.get("/health")
async def health_check():
    """Health check endpoint for Railway"""
    return {"status": "healthy", "timestamp": time.time()}
```

4. **Update `requirements.txt`** with all dependencies:
```txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
openai==1.10.0
pandas==2.2.0
plotly==5.18.0
folium==0.15.1
Pillow==10.2.0
psycopg2-binary==2.9.9
python-multipart==0.0.6
```

### 2.2 Deploy to Railway

1. **Install Railway CLI**:
```bash
npm install -g @railway/cli
# or
brew install railway
```

2. **Login to Railway**:
```bash
railway login
```

3. **Initialize Railway project**:
```bash
cd /home/olise/Projects/nexus
railway init
# Select: "Create new project"
# Name: nestscope-api
```

4. **Set environment variables**:
```bash
railway variables set OPENROUTER_API_KEY="sk-or-v1-..."
railway variables set DB_TYPE="postgres"
railway variables set SUPABASE_DB_URL="postgres://postgres:[PASSWORD]@db.xxxxx.supabase.co:5432/postgres"
```

5. **Deploy**:
```bash
railway up
```

6. **Get deployment URL**:
```bash
railway domain
# Example output: nestscope-api-production.up.railway.app
```

### 2.3 Configure Custom Domain (Optional)

```bash
railway domain add api.nestscope.org
# Then add CNAME record in your DNS provider:
# CNAME api.nestscope.org -> nestscope-api-production.up.railway.app
```

---

## Phase 3: Model Hosting Strategy

The YOLOv6m model (40.5 MB) needs to be hosted for inference. Three options:

### Option A: Railway Model Server (Recommended for <100 requests/day)

**Pros:**
- Simple deployment (same platform as API)
- Low latency (co-located with API)
- Full control over inference

**Cons:**
- Higher costs for GPU compute (~$50-100/month for GPU)
- Need to manage server scaling

**Implementation:**

1. Create separate Railway service for model:
```bash
railway service create nestscope-model
```

2. Create `model_server/main.py`:
```python
from fastapi import FastAPI, UploadFile, File
from ultralytics import YOLO
import cv2
import numpy as np
from PIL import Image
import io
import base64

app = FastAPI()

# Load model once at startup
model = YOLO("best.pt")

@app.post("/predict")
async def predict(image: UploadFile = File(...), confidence: float = 0.25):
    """Run bird detection on uploaded image"""
    # Read image
    image_bytes = await image.read()
    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    # Run inference
    results = model.predict(img, conf=confidence, imgsz=1024)

    # Parse results
    detections = []
    for box in results[0].boxes:
        detections.append({
            "confidence": float(box.conf[0]),
            "bbox": box.xyxy[0].tolist()
        })

    # Annotate image
    annotated = results[0].plot()
    _, buffer = cv2.imencode('.jpg', annotated)
    img_base64 = base64.b64encode(buffer).decode('utf-8')

    return {
        "bird_count": len(detections),
        "detections": detections,
        "annotated_image": img_base64
    }
```

3. Deploy:
```bash
railway up --service nestscope-model
```

**Cost:** ~$20-50/month (Railway compute without GPU) or $50-100/month with GPU

---

### Option B: Hugging Face Inference API (Recommended for >100 requests/day)

**Pros:**
- Free tier available (30 requests/hour)
- Automatic scaling
- No server management
- GPU inference included

**Cons:**
- Higher latency (external API call)
- Rate limits on free tier
- Need to upload model to Hugging Face

**Implementation:**

1. **Upload model to Hugging Face**:

```bash
# Install Hugging Face CLI
pip install huggingface_hub

# Login
huggingface-cli login

# Create model repository
huggingface-cli repo create nestscope-yolov6m --type model

# Upload model
git lfs install
git clone https://huggingface.co/YOUR_USERNAME/nestscope-yolov6m
cp server/best.pt nestscope-yolov6m/
cd nestscope-yolov6m
git add best.pt
git commit -m "Add YOLOv6m bird detection model"
git push
```

2. **Update inference code in `server/cv_tools/inference.py`**:

```python
import requests
import base64

class BirdDetector:
    def __init__(self, hf_token=None, model_id="YOUR_USERNAME/nestscope-yolov6m"):
        self.hf_token = hf_token or os.getenv("HF_TOKEN")
        self.model_id = model_id
        self.api_url = f"https://api-inference.huggingface.co/models/{model_id}"

    def predict_from_bytes(self, image_bytes, conf_threshold=0.25):
        """Run inference using Hugging Face API"""
        headers = {"Authorization": f"Bearer {self.hf_token}"}

        response = requests.post(
            self.api_url,
            headers=headers,
            data=image_bytes
        )

        if response.status_code == 200:
            results = response.json()
            return self._parse_results(results, conf_threshold)
        else:
            raise Exception(f"HF API error: {response.text}")
```

3. **Set Hugging Face token in Railway**:
```bash
railway variables set HF_TOKEN="hf_..."
```

**Cost:** Free tier (30 requests/hour) or Pro ($9/month for 10,000 requests)

---

### Option C: Roboflow Inference API (Easiest, Commercial)

**Pros:**
- Purpose-built for computer vision
- Excellent docs and support
- Fast inference
- Free tier available

**Cons:**
- Commercial service (paid after free tier)
- Vendor lock-in
- Need to re-train/upload model

**Implementation:**

1. Upload model to Roboflow: https://app.roboflow.com
2. Use Roboflow inference API:

```python
from roboflow import Roboflow

rf = Roboflow(api_key=os.getenv("ROBOFLOW_API_KEY"))
project = rf.workspace().project("nestscope-birds")
model = project.version(1).model

result = model.predict("image.jpg", confidence=25)
```

**Cost:** Free tier (1,000 predictions/month), then $0.0001/prediction

---

### Recommendation

**For NestScope:**
- **Start with Option B (Hugging Face)** - Free tier is sufficient for demo/prototype
- **Upgrade to Option A (Railway)** if you need <100ms latency or >30 req/hour
- **Use Option C (Roboflow)** if you need production reliability and support

---

## Phase 4: Frontend Deployment

### 4.1 Deploy to Streamlit Cloud

1. **Push code to GitHub** (if not already):
```bash
git add .
git commit -m "Prepare for cloud deployment"
git push origin master
```

2. **Go to Streamlit Cloud**: https://streamlit.io/cloud

3. **Deploy app**:
   - Click "New app"
   - Select repository: `OliseNS/nexus_project`
   - Branch: `master`
   - Main file path: `frontend/app/app_ui.py`
   - App URL: `nestscope` (becomes nestscope.streamlit.app)

4. **Set secrets** (in Streamlit Cloud settings):
```toml
# .streamlit/secrets.toml
API_URL = "https://nestscope-api.railway.app"
```

5. **Update `frontend/app/app_ui.py`**:
```python
import streamlit as st

# Get API URL from environment or secrets
API_URL = st.secrets.get("API_URL", "http://localhost:8000")

# Update all API calls to use API_URL
response = requests.post(f"{API_URL}/ask", json=payload)
```

### 4.2 Alternative: Deploy to Railway

If you prefer Railway for frontend too:

```bash
railway service create nestscope-frontend

# Add to railway.json:
{
  "deploy": {
    "startCommand": "streamlit run frontend/app/app_ui.py --server.port $PORT",
    "healthcheckPath": "/_stcore/health"
  }
}

railway up --service nestscope-frontend
```

---

## Testing & Validation

### Checklist

- [ ] **Database Migration**
  - [ ] All tables migrated to Supabase
  - [ ] Row counts match SQLite
  - [ ] Queries return correct results
  - [ ] Indexes created for performance

- [ ] **API Deployment**
  - [ ] Railway deployment successful
  - [ ] Health check endpoint responding
  - [ ] Text-to-SQL queries working
  - [ ] Schema endpoint accessible
  - [ ] CORS configured correctly

- [ ] **Model Hosting**
  - [ ] Model accessible via API
  - [ ] Inference returns correct detections
  - [ ] Response time <5 seconds
  - [ ] Error handling working

- [ ] **Frontend Deployment**
  - [ ] Streamlit app loads successfully
  - [ ] Can connect to Railway API
  - [ ] NestChat tab functional
  - [ ] NestVision tab functional
  - [ ] Maps rendering correctly
  - [ ] Charts displaying properly

### Test Queries

Run these queries to validate migration:

```python
# Test 1: Species count
SELECT COUNT(*) FROM species_codes
# Expected: 73

# Test 2: Colony totals for 2021
SELECT COUNT(*) FROM colony_totals WHERE Year = 2021
# Expected: ~1000

# Test 3: Geographic query
SELECT ColonyName, Latitude, Longitude
FROM colony_coordinates
WHERE State = 'LA'
# Expected: ~50 Louisiana colonies

# Test 4: Species trend
SELECT Year, SUM(Nests) as total_nests
FROM colony_totals
WHERE SpeciesCode = 'BRPE'
GROUP BY Year
ORDER BY Year
# Expected: Declining trend from 2010-2021
```

---

## Rollback Plan

If migration fails, revert to local setup:

```bash
# 1. Stop Railway deployments
railway down

# 2. Revert .env to local config
DB_TYPE=sqlite
DB_PATH=data/bird_data_complete.db

# 3. Restart local servers
./run_app.sh
```

To preserve Supabase data for retry:
- Do NOT drop Supabase tables
- Fix issues and re-run migration script with `--skip-schema-creation` flag

---

## Cost Estimates

### Monthly Costs

| Service | Plan | Cost | Notes |
|---------|------|------|-------|
| **Supabase** | Free | $0 | 500 MB DB, 2 GB bandwidth |
| **Railway API** | Hobby | $5-10 | ~500 MB RAM, always-on |
| **Railway Model** | Pro | $20-50 | CPU inference (or $50-100 for GPU) |
| **Hugging Face** | Free | $0 | 30 requests/hour (recommended) |
| **Streamlit Cloud** | Free | $0 | Public apps |
| **Domain (optional)** | - | $12/year | Custom domain |

**Total (Recommended Setup):** $5-10/month
- Supabase: Free
- Railway API: $5-10
- Hugging Face Model: Free
- Streamlit Cloud: Free

**Total (Full Self-Hosted):** $30-65/month
- Supabase: Free
- Railway API: $5-10
- Railway Model: $20-50
- Streamlit Cloud: Free

---

## Troubleshooting

### Database Issues

**Problem:** "SSL required" error connecting to Supabase

**Solution:**
```python
SUPABASE_URL = "postgres://...?sslmode=require"
```

**Problem:** Query timeout on large datasets

**Solution:** Add connection pooling:
```python
from psycopg2.pool import SimpleConnectionPool

pool = SimpleConnectionPool(1, 10, dsn=SUPABASE_URL)
```

### Railway Deployment Issues

**Problem:** Build fails with "Module not found"

**Solution:** Verify `requirements.txt` includes all dependencies:
```bash
pip freeze > requirements.txt
```

**Problem:** Application crashes on startup

**Solution:** Check logs:
```bash
railway logs
```

### Model Hosting Issues

**Problem:** Hugging Face API rate limit exceeded

**Solution:**
1. Upgrade to HF Pro ($9/month)
2. Or implement caching for duplicate queries
3. Or switch to Railway-hosted model

**Problem:** Model inference too slow (>10 seconds)

**Solution:**
1. Reduce image size before sending
2. Use GPU instance on Railway
3. Implement async inference with queuing

---

## Next Steps

After successful migration, consider:

1. **Performance Optimization**
   - Add Redis caching for frequent queries
   - Implement database read replicas
   - Use CDN for static assets

2. **Monitoring & Logging**
   - Set up Sentry for error tracking
   - Add Grafana/Prometheus for metrics
   - Configure Railway log retention

3. **Security Enhancements**
   - Add API authentication (JWT)
   - Implement rate limiting
   - Enable HTTPS-only mode
   - Regular security audits

4. **Feature Additions**
   - User accounts & saved queries
   - Email alerts for colony monitoring
   - Bulk image processing
   - Export to PDF reports

---

## Support & Resources

- **Supabase Docs**: https://supabase.com/docs
- **Railway Docs**: https://docs.railway.app
- **Hugging Face Docs**: https://huggingface.co/docs
- **Streamlit Docs**: https://docs.streamlit.io

For NestScope-specific issues:
- GitHub Issues: https://github.com/OliseNS/nexus_project/issues
- Email: [your-email]

---

**Last Updated:** February 8, 2026
**Version:** 1.0
