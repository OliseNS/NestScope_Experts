# NestScope Future Development & Deployment Plan

**Document Version:** 1.0
**Last Updated:** February 2026
**Status:** Draft

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Deployment Strategy](#deployment-strategy)
3. [UI/UX Enhancements](#uiux-enhancements)
4. [Backend & Infrastructure](#backend--infrastructure)
5. [Feature Roadmap](#feature-roadmap)
6. [Model Improvements](#model-improvements)
7. [Security & Compliance](#security--compliance)
8. [Testing & Quality Assurance](#testing--quality-assurance)
9. [Documentation & Support](#documentation--support)
10. [Timeline & Priorities](#timeline--priorities)

---

## Executive Summary

NestScope is currently a proof-of-concept application that combines natural language database queries with computer vision for avian monitoring. To transition from development to production deployment, this document outlines the technical improvements, infrastructure changes, and feature enhancements required for a robust, scalable, and user-friendly platform.

**Key Goals:**
- Deploy to production cloud infrastructure
- Enhance UI/UX for broader user adoption
- Improve model accuracy and capabilities
- Implement enterprise security features
- Enable team collaboration and data management
- Ensure scalability for growing datasets and users

---

## Deployment Strategy

### 1. Infrastructure Architecture

#### Recommended Cloud Platform Options

**Option A: AWS (Recommended for Scale)**
```
Architecture:
├── Frontend: Amplify or S3 + CloudFront
├── Backend API: ECS Fargate or Lambda
├── Database: RDS PostgreSQL + ElastiCache Redis
├── Model Inference: SageMaker or EC2 GPU instances
├── File Storage: S3
├── Monitoring: CloudWatch + X-Ray
└── Load Balancer: ALB
```

**Option B: DigitalOcean (Recommended for Simplicity & Cost)**
```
Architecture:
├── Frontend + Backend: App Platform
├── Database: Managed PostgreSQL
├── Model Inference: Droplet with GPU
├── File Storage: Spaces (S3-compatible)
├── Load Balancer: Managed Load Balancer
└── Monitoring: Integrated metrics
```

**Option C: Azure (Good for Enterprise)**
```
Architecture:
├── Frontend: Static Web Apps
├── Backend API: App Service or Container Apps
├── Database: Azure Database for PostgreSQL
├── Model Inference: Azure ML or GPU VMs
├── File Storage: Blob Storage
└── Monitoring: Application Insights
```

#### Estimated Costs (Monthly)

| Service | DigitalOcean | AWS | Azure |
|---------|-------------|-----|-------|
| Compute (API) | $48 (4GB Droplet) | $50-100 (Fargate) | $55 (B2s App Service) |
| GPU Instance | $180 (GPU Droplet) | $300 (g4dn.xlarge) | $250 (NC6s v3) |
| Database | $15 (Basic) | $45 (db.t3.small) | $50 (Basic tier) |
| Storage (100GB) | $5 (Spaces) | $3 (S3) | $5 (Blob) |
| CDN/Bandwidth | Included | $20-50 | $20-40 |
| **Total** | **~$250/mo** | **~$420/mo** | **~$380/mo** |

### 2. Containerization

**Docker Compose Structure:**
```yaml
services:
  frontend:
    build: ./frontend
    ports: ["8501:8501"]
    environment:
      - API_BASE_URL=http://backend:8000

  backend:
    build: ./server
    ports: ["8000:8000"]
    environment:
      - DB_TYPE=postgresql
      - REDIS_URL=redis://redis:6379
    depends_on: [db, redis]

  labeller:
    build: ./labeller
    ports: ["5000:5000"]
    volumes:
      - ./labeller/nestvision:/app/nestvision

  db:
    image: postgres:15
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

  nginx:
    image: nginx:alpine
    ports: ["80:80", "443:443"]
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
```

**Benefits:**
- Consistent development/production environments
- Easy scaling and orchestration
- Simplified deployment with Kubernetes or Docker Swarm
- Version control for infrastructure

### 3. Database Migration

**Current:** SQLite (single file, limited concurrency)
**Target:** PostgreSQL (production-grade, concurrent access)

**Migration Steps:**
1. Export SQLite data to CSV
2. Create PostgreSQL schema with proper indexes
3. Import CSV data with `COPY` command
4. Add foreign keys and constraints
5. Create indexes on frequently queried columns

**Recommended Schema Improvements:**
```sql
-- Add indexes for performance
CREATE INDEX idx_observations_year ON observations(Year);
CREATE INDEX idx_observations_colony ON observations(ColonyName);
CREATE INDEX idx_observations_species ON observations(SpeciesName);
CREATE INDEX idx_colony_totals_coords ON colony_totals(Latitude, Longitude);

-- Add full-text search
CREATE INDEX idx_observations_fts ON observations
  USING GIN(to_tsvector('english', SpeciesName || ' ' || ColonyName));

-- Add partitioning by year for large datasets
CREATE TABLE observations_2020 PARTITION OF observations
  FOR VALUES FROM ('2020-01-01') TO ('2021-01-01');
```

### 4. CI/CD Pipeline

**GitHub Actions Workflow:**
```yaml
name: Deploy NestScope

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: |
          python -m pytest tests/
          npm run test

  build-and-deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Build Docker images
        run: docker-compose build

      - name: Push to registry
        run: |
          docker tag nestscope/backend:latest registry/backend:${{ github.sha }}
          docker push registry/backend:${{ github.sha }}

      - name: Deploy to production
        run: |
          kubectl set image deployment/backend backend=registry/backend:${{ github.sha }}
```

### 5. Domain & SSL

**Recommended Setup:**
- Domain: `nestscope.io` or `nestscope.app`
- SSL: Let's Encrypt with automatic renewal
- CDN: CloudFlare for DDoS protection and caching

**DNS Configuration:**
```
A     @              -> 104.28.1.1 (CloudFlare)
A     www            -> 104.28.1.1
CNAME api            -> api-lb.region.cloud.com
CNAME labeller       -> labeller.region.cloud.com
CNAME static         -> cdn.nestscope.io
```

---

## UI/UX Enhancements

### 1. Responsive Design

**Current Issue:** Streamlit has limited mobile support
**Solution:** Consider migrating frontend to React/Next.js or Vue/Nuxt

**Short-term (Streamlit):**
- Add mobile-specific CSS media queries
- Optimize sidebar for mobile with collapsible sections
- Reduce font sizes and padding on small screens
- Test on iOS Safari and Android Chrome

**Long-term (React Migration):**
```
Frontend Stack:
├── Framework: Next.js 14 (App Router)
├── UI Library: shadcn/ui + Tailwind CSS
├── State: Zustand or React Context
├── Charts: Recharts or Chart.js
├── Maps: Mapbox GL JS or Leaflet
└── API Client: TanStack Query (React Query)
```

### 2. Accessibility Improvements

**WCAG 2.1 AA Compliance:**
- Add ARIA labels to all interactive elements
- Ensure 4.5:1 contrast ratio for text
- Keyboard navigation support (tab order, focus indicators)
- Screen reader compatibility
- Alt text for all images and visualizations
- Skip-to-content links

**Implementation:**
```jsx
// Example: Accessible button
<button
  aria-label="Run bird detection on uploaded image"
  aria-describedby="btn-help-text"
  role="button"
  tabIndex={0}
  onKeyPress={(e) => e.key === 'Enter' && handleClick()}
>
  Detect Birds
</button>
<span id="btn-help-text" className="sr-only">
  Uses AI to identify birds in your image
</span>
```

### 3. Performance Optimization

**Frontend:**
- Lazy load images and charts
- Implement virtual scrolling for large datasets
- Code splitting and dynamic imports
- Optimize bundle size (current Next.js builds can be 10-20% of Streamlit)
- Service worker for offline capability

**Backend:**
- API response caching with Redis (5-60 min TTL)
- Database query result caching
- Compress API responses (gzip/brotli)
- Implement pagination for large result sets
- Use WebSockets for real-time updates instead of polling

### 4. Enhanced User Experience

**Loading States:**
```jsx
// Skeleton loaders instead of spinners
<div className="animate-pulse">
  <div className="h-4 bg-gray-300 rounded w-3/4 mb-2"></div>
  <div className="h-4 bg-gray-300 rounded w-1/2"></div>
</div>
```

**Error Handling:**
- User-friendly error messages (avoid stack traces)
- Retry mechanism for failed API calls
- Offline detection and graceful degradation
- Toast notifications for background operations

**Onboarding:**
- Interactive tutorial on first visit
- Feature highlights with tooltips
- Sample queries and examples
- Quick start video (30-60 seconds)

### 5. Advanced UI Features

**Dashboard (New Page):**
- Summary statistics cards
- Recent activity feed
- Quick actions menu
- Favorite queries/images
- Team activity (if multi-user)

**Data Visualization Improvements:**
- Interactive charts with drill-down
- Export charts as PNG/SVG
- Customizable color schemes
- Multiple chart types per query (toggle view)
- Comparison mode (side-by-side years/colonies)

**Labeller Improvements:**
- Undo/redo functionality
- Keyboard shortcuts overlay (press '?')
- Batch operations (delete multiple boxes)
- Copy/paste annotations between images
- Auto-save with visual indicator
- Image preprocessing tools (brightness, contrast)
- Zoom to fit / actual size toggle
- Grid overlay for alignment
- Class color customization

---

## Backend & Infrastructure

### 1. API Architecture

**Current:** Monolithic FastAPI app
**Recommended:** Keep monolithic for now, plan for microservices at scale

**API Improvements:**
- OpenAPI 3.1 documentation (auto-generated with FastAPI)
- API versioning (`/api/v1/`, `/api/v2/`)
- Request validation with Pydantic v2
- Rate limiting per user/IP (Redis-based)
- API key authentication for programmatic access

**Rate Limiting Example:**
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/cv/inference")
@limiter.limit("10/minute")  # 10 inference requests per minute
async def inference_endpoint():
    pass
```

### 2. Caching Strategy

**Multi-Layer Caching:**

```python
# Layer 1: In-memory cache (fast, limited)
from cachetools import TTLCache
memory_cache = TTLCache(maxsize=100, ttl=300)

# Layer 2: Redis (shared, persistent)
import redis
redis_client = redis.Redis(host='localhost', port=6379)

# Layer 3: CDN (for static assets)
# CloudFlare or AWS CloudFront

# Cache key strategy
def get_cache_key(query: str) -> str:
    return f"query:{hashlib.sha256(query.encode()).hexdigest()[:16]}"

# Cache invalidation on data update
def invalidate_cache(pattern: str = "*"):
    for key in redis_client.scan_iter(match=pattern):
        redis_client.delete(key)
```

**What to Cache:**
- SQL query results (5-15 min TTL)
- Model inference results (60 min TTL)
- Database schema metadata (24 hour TTL)
- Example images list (cache until restart)
- User session data (Redis with 30 day TTL)

### 3. Async Task Processing

**Use Case:** Long-running tasks shouldn't block API responses

**Celery + Redis Implementation:**
```python
# tasks.py
from celery import Celery

celery_app = Celery('nestscope', broker='redis://localhost:6379/0')

@celery_app.task
def process_batch_images(image_urls: list[str]):
    results = []
    for url in image_urls:
        result = run_inference(url)
        results.append(result)
    return results

# API endpoint
@app.post("/cv/batch")
async def batch_inference(files: list[UploadFile]):
    task = process_batch_images.delay([f.filename for f in files])
    return {"task_id": task.id, "status": "processing"}

@app.get("/cv/batch/{task_id}")
async def get_batch_result(task_id: str):
    task = celery_app.AsyncResult(task_id)
    return {"status": task.state, "result": task.result}
```

**Task Queue Benefits:**
- Non-blocking API responses
- Retry failed tasks automatically
- Monitor task progress
- Distribute work across multiple workers

### 4. Database Optimization

**Query Optimization:**
```python
# Bad: N+1 query problem
for colony in colonies:
    observations = get_observations(colony.id)  # N queries

# Good: Join or eager loading
observations = db.query(Observation).join(Colony).all()  # 1 query

# Use EXPLAIN ANALYZE in PostgreSQL
EXPLAIN ANALYZE
SELECT * FROM observations WHERE Year = 2021;
```

**Connection Pooling:**
```python
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,  # 20 persistent connections
    max_overflow=10,  # 10 additional on demand
    pool_pre_ping=True,  # Verify connection before use
    pool_recycle=3600  # Recycle after 1 hour
)
```

### 5. Monitoring & Logging

**Observability Stack:**
- **Metrics:** Prometheus + Grafana
- **Logs:** Loki or ELK Stack (Elasticsearch, Logstash, Kibana)
- **Traces:** Jaeger or Zipkin
- **Errors:** Sentry
- **Uptime:** UptimeRobot or Pingdom

**Key Metrics to Track:**
```python
from prometheus_client import Counter, Histogram, Gauge

# Request metrics
request_count = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint'])
request_duration = Histogram('api_request_duration_seconds', 'Request duration')
active_users = Gauge('active_users', 'Number of active users')

# Model metrics
inference_count = Counter('model_inference_total', 'Total inferences')
inference_duration = Histogram('model_inference_duration_seconds', 'Inference duration')
inference_errors = Counter('model_inference_errors_total', 'Inference errors')

# Database metrics
db_query_duration = Histogram('db_query_duration_seconds', 'Database query duration')
db_connection_pool = Gauge('db_connection_pool_size', 'Connection pool size')
```

**Structured Logging:**
```python
import structlog

logger = structlog.get_logger()

logger.info("user_query",
    user_id=user.id,
    query=query_text,
    response_time_ms=elapsed,
    result_count=len(results)
)
```

---

## Feature Roadmap

### Phase 1: MVP Enhancements (Months 1-2)

**User Management:**
- [ ] User registration and login (email/password)
- [ ] OAuth integration (Google, GitHub)
- [ ] User profiles with avatar upload
- [ ] Password reset flow
- [ ] Email verification

**Session Management:**
- [ ] Save conversation history
- [ ] Name and organize chat sessions
- [ ] Search through past conversations
- [ ] Share conversations via link

**Data Export:**
- [ ] Export query results as CSV/Excel
- [ ] Export charts as PNG/PDF
- [ ] Generate PDF reports with multiple queries
- [ ] Scheduled email reports

### Phase 2: Collaboration Features (Months 3-4)

**Team Workspaces:**
- [ ] Create organizations/teams
- [ ] Invite team members
- [ ] Role-based access control (Admin, Editor, Viewer)
- [ ] Shared query library
- [ ] Team activity feed

**Annotation Collaboration:**
- [ ] Multi-user labelling with assignment tracking
- [ ] Review and approval workflow
- [ ] Quality scoring for annotators
- [ ] Consensus labelling (multiple annotators per image)
- [ ] Inter-annotator agreement metrics

**Comments & Discussions:**
- [ ] Comment on images and annotations
- [ ] Threaded discussions
- [ ] @mentions and notifications
- [ ] Resolve/unresolve comments

### Phase 3: Advanced Analytics (Months 5-6)

**Custom Dashboards:**
- [ ] Drag-and-drop dashboard builder
- [ ] Widget library (charts, maps, tables, metrics)
- [ ] Save and share dashboards
- [ ] Real-time data refresh
- [ ] Dashboard templates (colony health, species trends, etc.)

**Alerts & Notifications:**
- [ ] Set up data alerts (e.g., "Notify me if pelican count drops below X")
- [ ] Email/SMS notifications
- [ ] Webhook integrations
- [ ] Alert history and management

**Advanced Queries:**
- [ ] Saved query templates
- [ ] Query parameters and variables
- [ ] Multi-step queries (query results as input to next query)
- [ ] SQL query builder UI
- [ ] Query scheduling (run daily/weekly)

### Phase 4: Model Enhancements (Months 7-9)

**Species Classification:**
- [ ] Train species classifier (ImageNet-based CNN or Vision Transformer)
- [ ] Integrate with detection pipeline
- [ ] Confidence scores per species
- [ ] Unknown/Other class for uncertain predictions
- [ ] User feedback loop for corrections

**Active Learning:**
- [ ] Identify low-confidence predictions for human review
- [ ] Prioritize images for annotation
- [ ] Track model performance over time
- [ ] A/B test model versions
- [ ] Automated retraining pipeline

**Model Explainability:**
- [ ] Grad-CAM visualizations (show what model is looking at)
- [ ] Confidence heatmaps
- [ ] Feature importance for classification
- [ ] Model performance reports (precision, recall, F1)

### Phase 5: Enterprise Features (Months 10-12)

**API Access:**
- [ ] REST API for programmatic access
- [ ] API key management
- [ ] Usage analytics per API key
- [ ] Rate limiting tiers
- [ ] Webhook callbacks for async operations

**Data Management:**
- [ ] Import custom datasets
- [ ] Data validation and cleaning tools
- [ ] Version control for datasets
- [ ] Data lineage tracking
- [ ] GDPR compliance tools (export, delete user data)

**Integrations:**
- [ ] Zapier integration
- [ ] Slack/Discord notifications
- [ ] Google Drive/Dropbox for image import
- [ ] ArcGIS/QGIS export formats
- [ ] Excel plugin for data access

---

## Model Improvements

### 1. Detection Model Enhancement

**Current Model:** YOLOv8-based (seconditer.onnx)

**Improvement Strategy:**

**A. Data Collection & Annotation:**
- Continue manual annotation in Labeller
- Target: 10,000+ annotated images (currently ~125?)
- Diverse conditions: lighting, weather, angles, species, colony sizes
- Stratified sampling across years and locations

**B. Model Architecture Exploration:**

| Model | Speed | Accuracy | Best For |
|-------|-------|----------|----------|
| YOLOv8n | ⚡⚡⚡ | ⭐⭐⭐ | Real-time preview |
| YOLOv8m | ⚡⚡ | ⭐⭐⭐⭐ | Current use case |
| YOLOv8x | ⚡ | ⭐⭐⭐⭐⭐ | Maximum accuracy |
| DINO (Transformer) | ⚡ | ⭐⭐⭐⭐⭐ | Small objects |
| Faster R-CNN | ⚡ | ⭐⭐⭐⭐ | Research/baseline |

**C. Training Pipeline:**
```python
# Recommended training configuration
from ultralytics import YOLO

model = YOLO('yolov8m.pt')  # Start with pretrained weights

results = model.train(
    data='data.yaml',
    epochs=100,
    imgsz=1024,  # Keep high resolution for small birds
    batch=16,
    device='0',  # GPU
    optimizer='AdamW',
    lr0=0.001,
    weight_decay=0.0005,
    augment=True,  # Important for generalization
    mosaic=1.0,
    mixup=0.1,
    copy_paste=0.3,  # Copy-paste augmentation for birds
    degrees=10,  # Small rotation
    flipud=0.5,  # Vertical flip for aerial images
    fliplr=0.5,  # Horizontal flip
)

# Export to ONNX for production
model.export(format='onnx', dynamic=True, simplify=True)
```

**D. Data Augmentation:**
```python
# Albumentations pipeline for bird images
import albumentations as A

transform = A.Compose([
    A.RandomRotate90(p=0.5),
    A.HorizontalFlip(p=0.5),
    A.VerticalFlip(p=0.5),
    A.RandomBrightnessContrast(brightness_limit=0.2, contrast_limit=0.2, p=0.5),
    A.GaussianBlur(blur_limit=(3, 7), p=0.3),
    A.GaussNoise(var_limit=(10.0, 50.0), p=0.3),
    A.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.1, p=0.5),
    A.RandomScale(scale_limit=0.2, p=0.5),
    A.CropAndPad(percent=0.1, p=0.3),
], bbox_params=A.BboxParams(format='yolo', label_fields=['class_labels']))
```

**E. Evaluation Metrics:**
```python
# Track these metrics across training runs
metrics = {
    "mAP@0.5": 0.0,      # Mean Average Precision at IoU 0.5
    "mAP@0.5:0.95": 0.0, # mAP across IoU thresholds
    "precision": 0.0,     # True positives / (TP + FP)
    "recall": 0.0,        # True positives / (TP + FN)
    "F1": 0.0,           # Harmonic mean of precision and recall
    "inference_time_ms": 0.0,
    "model_size_mb": 0.0
}

# Target goals
goals = {
    "mAP@0.5": 0.85,  # 85% mAP is excellent for object detection
    "precision": 0.90,  # High precision (few false positives)
    "recall": 0.80,     # Good recall (find most birds)
    "inference_time_ms": 100,  # <100ms for good UX
}
```

### 2. Species Classification Model

**Approach:** Two-stage pipeline (detect → classify)

**Architecture Options:**

**Option A: Vision Transformer (ViT)**
```python
from transformers import ViTForImageClassification, ViTImageProcessor

model = ViTForImageClassification.from_pretrained(
    'google/vit-base-patch16-224',
    num_labels=num_species,
    ignore_mismatched_sizes=True
)

# Fine-tune on bird crops from detection
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=val_dataset,
)
trainer.train()
```

**Option B: EfficientNet**
```python
import timm

model = timm.create_model(
    'efficientnet_b3',
    pretrained=True,
    num_classes=num_species
)
```

**Option C: Custom CNN with Attention**
```python
import torch.nn as nn

class BirdClassifier(nn.Module):
    def __init__(self, num_species):
        super().__init__()
        self.backbone = models.resnet50(pretrained=True)
        self.attention = nn.MultiheadAttention(embed_dim=2048, num_heads=8)
        self.fc = nn.Linear(2048, num_species)

    def forward(self, x):
        features = self.backbone(x)
        attended, _ = self.attention(features, features, features)
        return self.fc(attended)
```

**Dataset Requirements:**
- Need species-labeled crops from detections
- Minimum 100 examples per species (ideally 500+)
- Balanced across species (or use weighted loss)
- Include "Unknown" class for rare/unlabeled species

**Species List (Gulf Coast Common):**
Based on CLAUDE.md context, likely species:
- Brown Pelican
- Laughing Gull
- Royal Tern
- Sandwich Tern
- Black Skimmer
- Reddish Egret
- Great Blue Heron
- Roseate Spoonbill
- White Ibis
- Snowy Egret
- _(expand based on actual data)_

### 3. Model Versioning & Deployment

**MLflow for Model Registry:**
```python
import mlflow

# Log model during training
with mlflow.start_run():
    mlflow.log_params({"epochs": 100, "batch_size": 16})
    mlflow.log_metrics({"mAP": 0.85, "precision": 0.90})
    mlflow.pytorch.log_model(model, "model")

# Load model in production
model_uri = "models:/bird-detector/production"
model = mlflow.pytorch.load_model(model_uri)
```

**A/B Testing Framework:**
```python
import random

def get_model_for_request(user_id: str):
    # Route 10% of traffic to model B
    if hash(user_id) % 10 == 0:
        return load_model("model_b")
    else:
        return load_model("model_a")

# Track performance per model
log_inference(
    model_version="model_a",
    user_feedback=feedback,
    inference_time=elapsed
)
```

---

## Security & Compliance

### 1. Authentication & Authorization

**Auth System Architecture:**

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT tokens
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def create_access_token(data: dict, expires_delta: timedelta = timedelta(hours=24)):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        return get_user(user_id)
    except JWTError:
        raise credentials_exception

# Protect endpoints
@app.get("/protected")
async def protected_route(current_user: User = Depends(get_current_user)):
    return {"message": f"Hello {current_user.username}"}
```

**Role-Based Access Control (RBAC):**

```python
from enum import Enum

class Role(str, Enum):
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"

class Permission(str, Enum):
    READ_DATA = "read:data"
    WRITE_DATA = "write:data"
    MANAGE_USERS = "manage:users"
    RUN_INFERENCE = "run:inference"
    EXPORT_DATA = "export:data"

ROLE_PERMISSIONS = {
    Role.ADMIN: [Permission.READ_DATA, Permission.WRITE_DATA,
                 Permission.MANAGE_USERS, Permission.RUN_INFERENCE,
                 Permission.EXPORT_DATA],
    Role.EDITOR: [Permission.READ_DATA, Permission.WRITE_DATA,
                  Permission.RUN_INFERENCE],
    Role.VIEWER: [Permission.READ_DATA],
}

def require_permission(permission: Permission):
    def decorator(func):
        async def wrapper(current_user: User = Depends(get_current_user)):
            if permission not in ROLE_PERMISSIONS[current_user.role]:
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            return await func(current_user)
        return wrapper
    return decorator

@app.delete("/data/{id}")
@require_permission(Permission.WRITE_DATA)
async def delete_data(id: int, current_user: User):
    pass
```

### 2. API Security

**Rate Limiting:**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Public endpoints: strict limits
@app.post("/cv/inference")
@limiter.limit("10/minute")
async def inference(request: Request):
    pass

# Authenticated endpoints: generous limits
@app.post("/cv/inference")
@limiter.limit("100/minute")
async def inference(request: Request, user: User = Depends(get_current_user)):
    pass
```

**Input Validation:**
```python
from pydantic import BaseModel, Field, validator

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)

    @validator('question')
    def sanitize_question(cls, v):
        # Prevent SQL injection attempts
        dangerous_keywords = ['DROP', 'DELETE', 'TRUNCATE', 'INSERT', 'UPDATE']
        if any(keyword in v.upper() for keyword in dangerous_keywords):
            raise ValueError('Query contains potentially dangerous keywords')
        return v

class ImageUpload(BaseModel):
    image_base64: str = Field(..., max_length=10_000_000)  # ~7MB limit

    @validator('image_base64')
    def validate_base64(cls, v):
        try:
            decoded = base64.b64decode(v)
            # Verify it's actually an image
            Image.open(BytesIO(decoded))
        except:
            raise ValueError('Invalid image data')
        return v
```

**CORS Configuration:**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://nestscope.io", "https://www.nestscope.io"],  # Production domains
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    max_age=3600,
)
```

### 3. Data Security

**Encryption at Rest:**
- Database: Enable PostgreSQL transparent data encryption (TDE)
- File Storage: Use S3 server-side encryption (SSE-S3 or SSE-KMS)
- Secrets: Store in AWS Secrets Manager, Azure Key Vault, or HashiCorp Vault

**Encryption in Transit:**
- Enforce HTTPS/TLS 1.3 only
- Certificate pinning for mobile apps
- Secure WebSocket connections (wss://)

**Data Sanitization:**
```python
def sanitize_user_input(text: str) -> str:
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove special characters for SQL safety
    text = re.sub(r'[^\w\s\-.,?!]', '', text)
    return text.strip()

def anonymize_data(df: pd.DataFrame) -> pd.DataFrame:
    # Remove PII before exporting
    pii_columns = ['user_email', 'user_name', 'ip_address']
    return df.drop(columns=[c for c in pii_columns if c in df.columns])
```

### 4. Compliance

**GDPR Compliance (if serving EU users):**
- [ ] Privacy policy explaining data usage
- [ ] Cookie consent banner
- [ ] Data portability (export user data)
- [ ] Right to erasure (delete account and all data)
- [ ] Data breach notification procedures
- [ ] DPA (Data Processing Agreement) for any third-party services

**HIPAA Compliance (if handling protected health info):**
- [ ] Business Associate Agreement (BAA) with cloud provider
- [ ] Access logs and audit trails
- [ ] Encrypted backups
- [ ] Regular security risk assessments

**Research Data Management:**
- [ ] Data retention policy (e.g., keep observations for 10 years)
- [ ] Data sharing agreements with research institutions
- [ ] Attribution and citation requirements
- [ ] Embargo periods for unpublished data

---

## Testing & Quality Assurance

### 1. Testing Strategy

**Unit Tests (pytest):**
```python
# tests/test_sql_generator.py
def test_sql_generation():
    query = "Show pelican counts in 2021"
    sql = generate_sql(query)
    assert "WHERE Year = 2021" in sql
    assert "SpeciesName LIKE '%Pelican%'" in sql

def test_detection_confidence_threshold():
    detections = filter_detections(raw_detections, threshold=0.5)
    assert all(d['confidence'] >= 0.5 for d in detections)

# tests/test_api.py
def test_inference_endpoint(client):
    response = client.post("/cv/inference", files={"file": test_image})
    assert response.status_code == 200
    assert "count" in response.json()
```

**Integration Tests:**
```python
# tests/integration/test_chat_flow.py
def test_full_chat_flow(client):
    # 1. Ask question
    response = client.post("/ask", json={"question": "Top species in 2021?"})
    assert response.status_code == 200

    # 2. Verify SQL was generated
    assert "generated_sql" in response.json()

    # 3. Verify results are correct
    results = response.json()["results"]
    assert len(results) > 0
    assert "SpeciesName" in results[0]

# tests/integration/test_labeller.py
def test_annotation_workflow(client):
    # Upload image
    client.post("/api/correction/upload", json={"image_base64": image_data})

    # Load next image
    response = client.get("/api/next_image/TestUser")
    image_name = response.json()["image"]

    # Save annotations
    client.post("/api/save", json={
        "username": "TestUser",
        "filename": image_name,
        "labels": [{"class_id": 0, "x": 0.5, "y": 0.5, "w": 0.1, "h": 0.1}]
    })

    # Verify saved
    response = client.get(f"/api/image_data/{image_name}")
    assert len(response.json()) == 1
```

**End-to-End Tests (Playwright):**
```typescript
// tests/e2e/chat.spec.ts
test('user can ask question and see results', async ({ page }) => {
  await page.goto('http://localhost:8501/nest_chat');

  // Type question
  await page.fill('[data-testid="stChatInput"] textarea', 'Show all colonies in Texas');
  await page.press('[data-testid="stChatInput"] textarea', 'Enter');

  // Wait for response
  await page.waitForSelector('.stDataFrame');

  // Verify results
  const results = await page.locator('.stDataFrame tbody tr').count();
  expect(results).toBeGreaterThan(0);
});
```

**Load Testing (Locust):**
```python
# tests/load/locustfile.py
from locust import HttpUser, task, between

class NestScopeUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def ask_question(self):
        self.client.post("/ask", json={
            "question": "Show pelican trends in Louisiana"
        })

    @task(1)
    def run_inference(self):
        with open("test_image.jpg", "rb") as f:
            self.client.post("/cv/inference", files={"file": f})

# Run: locust -f locustfile.py --host=https://api.nestscope.io
```

### 2. Continuous Testing

**GitHub Actions Workflow:**
```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run unit tests
        run: |
          pip install -r requirements-dev.txt
          pytest tests/unit -v --cov=server --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  integration-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
    steps:
      - uses: actions/checkout@v3
      - name: Run integration tests
        run: |
          docker-compose -f docker-compose.test.yml up -d
          pytest tests/integration -v

  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install Playwright
        run: |
          npm install -D @playwright/test
          npx playwright install
      - name: Run E2E tests
        run: npx playwright test
```

### 3. Quality Metrics

**Code Coverage Target:** >80%
**Performance Benchmarks:**
- API response time: <500ms (p95)
- Model inference: <100ms (fast mode), <3s (SAHI mode)
- Database query time: <100ms (p95)
- Page load time: <2s (First Contentful Paint)

---

## Documentation & Support

### 1. User Documentation

**User Guide Structure:**
```
docs/
├── user-guide/
│   ├── getting-started.md
│   ├── nest-chat/
│   │   ├── asking-questions.md
│   │   ├── query-examples.md
│   │   ├── understanding-results.md
│   │   └── exporting-data.md
│   ├── nest-vision/
│   │   ├── uploading-images.md
│   │   ├── detection-settings.md
│   │   ├── correcting-annotations.md
│   │   └── batch-processing.md
│   ├── labeller/
│   │   ├── annotation-guidelines.md
│   │   ├── keyboard-shortcuts.md
│   │   ├── quality-tips.md
│   │   └── team-workflow.md
│   └── troubleshooting.md
```

**Interactive Tutorials:**
- In-app tooltips and walkthroughs (using Intro.js or Shepherd.js)
- Video tutorials (30-60 seconds each)
- Interactive playground with sample data

### 2. API Documentation

**OpenAPI/Swagger:**
```python
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

app = FastAPI(
    title="NestScope API",
    description="AI-powered avian monitoring analytics API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="NestScope API",
        version="1.0.0",
        description="Complete API reference for NestScope",
        routes=app.routes,
    )
    # Add authentication security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
```

**API Examples:**
```python
# docs/api-examples.py

# Python example
import requests

response = requests.post(
    "https://api.nestscope.io/v1/ask",
    headers={"Authorization": f"Bearer {API_KEY}"},
    json={"question": "Show pelican trends in Louisiana"}
)
results = response.json()

# JavaScript example
const response = await fetch('https://api.nestscope.io/v1/cv/inference', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${API_KEY}`,
  },
  body: formData
});
const result = await response.json();

# cURL example
curl -X POST https://api.nestscope.io/v1/ask \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"question": "Top species in 2021?"}'
```

### 3. Developer Documentation

**Setup Guide:**
```markdown
# Developer Setup

## Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose

## Quick Start
```bash
# Clone repo
git clone https://github.com/yourorg/nestscope.git
cd nestscope

# Install dependencies
pip install -r requirements-dev.txt
npm install

# Setup database
python scripts/setup_db.py

# Run development servers
./run_app.sh

# Run tests
pytest tests/
```

## Architecture
[Diagrams and explanations]

## Contributing
See CONTRIBUTING.md
```

**Code Documentation:**
```python
# Use docstrings for all public functions
def generate_sql(question: str, schema: dict) -> str:
    """
    Generate SQL query from natural language question.

    Args:
        question: User's natural language question
        schema: Database schema information

    Returns:
        Generated SQL query string

    Raises:
        ValueError: If question is empty or invalid

    Example:
        >>> generate_sql("Show all pelicans", schema)
        "SELECT * FROM observations WHERE SpeciesName LIKE '%Pelican%'"
    """
    pass
```

### 4. Support Channels

**Community Support:**
- [ ] GitHub Discussions for Q&A
- [ ] Discord/Slack community
- [ ] Stack Overflow tag (`nestscope`)
- [ ] Monthly office hours (Zoom call)

**Enterprise Support:**
- [ ] Dedicated support email (support@nestscope.io)
- [ ] SLA-based response times
- [ ] Priority bug fixes
- [ ] Custom training and onboarding

---

## Timeline & Priorities

### Short-term (0-3 months) - Production Readiness

**Priority 1: Infrastructure**
- [ ] Week 1-2: Containerization with Docker
- [ ] Week 3-4: PostgreSQL migration
- [ ] Week 5-6: Deploy to cloud (DigitalOcean recommended)
- [ ] Week 7-8: SSL, domain, monitoring setup

**Priority 2: Core Features**
- [ ] Week 2-4: User authentication system
- [ ] Week 4-6: Session management and history
- [ ] Week 6-8: Data export functionality
- [ ] Week 8-10: Improved error handling
- [ ] Week 10-12: Mobile-responsive UI tweaks

**Priority 3: Model**
- [ ] Ongoing: Continue annotation (target 500 more images)
- [ ] Week 8-10: Retrain detection model
- [ ] Week 10-12: A/B test new model

**Success Metrics:**
- App accessible at https://nestscope.io
- <2s page load time
- 99.5% uptime
- 50+ active users
- <5 critical bugs

### Medium-term (3-6 months) - Feature Expansion

**Priority 1: Collaboration**
- [ ] Team workspaces
- [ ] Multi-user labelling
- [ ] Shared query library

**Priority 2: Analytics**
- [ ] Custom dashboards
- [ ] Scheduled reports
- [ ] Alert system

**Priority 3: Model**
- [ ] Species classification model (v1)
- [ ] Active learning pipeline
- [ ] Model explainability

**Success Metrics:**
- 200+ active users
- 10+ organizations using teams
- 5,000+ images annotated
- Species classifier with >80% accuracy

### Long-term (6-12 months) - Enterprise Scale

**Priority 1: Enterprise Features**
- [ ] API access with keys
- [ ] Advanced RBAC
- [ ] Data import/export tools
- [ ] Audit logs

**Priority 2: Integrations**
- [ ] Zapier/API integrations
- [ ] Mobile apps (iOS/Android)
- [ ] ArcGIS compatibility
- [ ] Slack/Discord bots

**Priority 3: Advanced AI**
- [ ] Multi-model ensemble
- [ ] Video processing support
- [ ] Behavior analysis (future research)

**Success Metrics:**
- 1,000+ active users
- 50+ paying organizations
- 99.9% uptime SLA
- 50,000+ images in dataset
- Species classifier with >90% accuracy

---

## Budget Estimates

### Year 1 Costs

**Infrastructure (Monthly):**
- Cloud hosting: $250-400
- Database: $50-100
- CDN/Bandwidth: $50-100
- Monitoring: $50
- Domain/SSL: $10
- **Total: ~$410-660/month = $5K-8K/year**

**Development:**
- Full-time developer (6 months): $60K-120K
- Part-time ML engineer (3 months): $30K-60K
- UI/UX designer (contract): $10K-20K
- **Total: $100K-200K**

**Services:**
- OpenRouter API (LLM): $500-1000/month = $6K-12K/year
- Error tracking (Sentry): $30/month = $360/year
- Monitoring (Grafana Cloud): $50/month = $600/year
- **Total: $7K-13K/year**

**Total Year 1: $112K-221K**

### Revenue Potential (Year 2+)

**Pricing Tiers:**

| Tier | Price/mo | Target | Annual Revenue |
|------|----------|--------|----------------|
| Free | $0 | 1000 users | $0 |
| Pro | $29 | 100 users | $34,800 |
| Team | $99 | 20 teams | $23,760 |
| Enterprise | $499 | 5 orgs | $29,940 |
| **Total** | | | **$88,500** |

**Additional Revenue:**
- API access: $0.01/request
- Custom model training: $5K-20K per client
- Consulting: $150-300/hour
- Grants: Research institutions often have funding

---

## Risk Mitigation

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Model accuracy insufficient | Medium | High | Continuous data collection, multiple model architectures, human-in-loop |
| Cloud costs exceed budget | Medium | Medium | Set billing alerts, optimize queries, use spot instances |
| Database performance issues | Low | High | Connection pooling, caching, read replicas, query optimization |
| Security breach | Low | Critical | Regular audits, penetration testing, bug bounty, encrypted data |
| API rate limit exhaustion | Medium | Medium | Caching, rate limiting, alternative LLM providers |

### Business Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Low user adoption | Medium | High | User research, marketing, partnerships with research institutions |
| Competition | Low | Medium | Focus on avian-specific features, academic partnerships |
| Regulatory changes | Low | Medium | Legal counsel, compliance monitoring |
| Key personnel leaving | Medium | Medium | Documentation, knowledge sharing, backup maintainers |

---

## Success Metrics & KPIs

### Technical KPIs

**Performance:**
- Page load time: <2s (95th percentile)
- API response time: <500ms (95th percentile)
- Model inference time: <100ms (fast), <3s (SAHI)
- Database query time: <100ms (95th percentile)
- Uptime: >99.5% (target 99.9%)

**Quality:**
- Code coverage: >80%
- Bug escape rate: <5% (bugs reaching production)
- Mean time to resolution (MTTR): <24 hours for critical, <1 week for minor
- Model accuracy: mAP@0.5 >0.85

### Product KPIs

**Engagement:**
- Daily active users (DAU)
- Monthly active users (MAU)
- Sessions per user per week
- Average session duration
- Retention rate (D7, D30)

**Usage:**
- Queries per day
- Images processed per day
- Annotations per day
- Data exports per week
- API calls per day

### Business KPIs

**Growth:**
- New user signups per week
- Conversion rate (free → paid)
- Churn rate: <5% monthly
- Customer acquisition cost (CAC)
- Lifetime value (LTV)
- LTV:CAC ratio: >3:1

**Revenue:**
- Monthly recurring revenue (MRR)
- Annual recurring revenue (ARR)
- Average revenue per user (ARPU)
- Revenue growth rate: >10% month-over-month

---

## Conclusion

This roadmap provides a comprehensive plan to transform NestScope from a prototype into a production-ready, scalable platform for avian monitoring. The phased approach balances immediate deployment needs with long-term feature development and business viability.

**Key Takeaways:**

1. **Start Simple:** Deploy on DigitalOcean with Docker for cost-effective scaling
2. **Focus on Core:** Prioritize user authentication, data export, and model accuracy before advanced features
3. **Iterate Fast:** Use A/B testing and user feedback to guide development
4. **Plan for Scale:** Architecture choices support 1000x growth without major rewrites
5. **Measure Everything:** Track technical and business metrics to guide decisions

**Next Steps:**

1. Review and prioritize features with stakeholders
2. Set up infrastructure (Docker, PostgreSQL, cloud hosting)
3. Implement authentication and basic user management
4. Continue model training and annotation
5. Launch MVP to pilot users (beta testing)
6. Iterate based on feedback
7. Scale infrastructure as user base grows

**Questions or Feedback:** Reach out to the development team to discuss this plan and adjust priorities based on organizational goals and resources.

---

*Document maintained by NestScope development team. Last updated: February 2026.*
