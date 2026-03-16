# Testing NestScope Public Locally

Quick guide to test the public deployment package before deploying to Railway.

## 🧪 Pre-Deployment Testing

### 1. Setup Environment

```bash
cd public/

# Create .env file
cp .env.example .env

# Edit .env and add your OpenRouter API key
nano .env  # or your preferred editor
```

Add to `.env`:
```
OPENROUTER_API_KEY=your-actual-key-here
DB_PATH=data/bird_data_complete.db
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

Or with virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Test FastAPI Backend Only

```bash
# Start backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# In another terminal, test endpoints:

# Health check
curl http://localhost:8000/health

# Get stats
curl http://localhost:8000/stats

# Get config
curl http://localhost:8000/config

# Interactive API docs
open http://localhost:8000/docs
```

### 4. Test Full Stack (Backend + Webapp)

```bash
# Use the startup script
./run.sh

# This starts:
# - FastAPI backend at :8000
# - Flask webapp at :8501

# Open in browser:
# http://localhost:8501
```

### 5. Test NestChat

1. Open `http://localhost:8501/chat`
2. Try example questions:
   - "How many brown pelicans were observed in 2020?"
   - "Show me the top 10 colonies by bird count"
   - "What species are found in Texas?"

**Expected behavior:**
- Streaming AI responses
- SQL query generation with self-correction
- Charts/maps embedded in responses
- Mobile-responsive UI

### 6. Test NestVision

1. Open `http://localhost:8501/vision`
2. Upload a bird colony image or use example
3. Adjust confidence threshold (default: 0.25)
4. Click "Detect Birds"

**Expected behavior:**
- Bird count displayed
- Annotated image with bounding boxes
- Species classification (7 groups)
- Inference time shown

### 7. Test API Directly (Optional)

**NestChat Streaming:**
```bash
curl -X POST http://localhost:8000/ask/agentic/stream \
  -H "Content-Type: application/json" \
  -d '{"question": "How many colonies are in Texas?"}' \
  --no-buffer
```

**NestVision Inference:**
```bash
curl -X POST http://localhost:8000/cv/inference \
  -F "file=@test_image.jpg" \
  -F "conf_threshold=0.25"
```

## ✅ Validation Checklist

Before deploying to Railway, verify:

### Backend
- [ ] Health endpoint returns `{"status": "healthy"}`
- [ ] Config endpoint returns model name
- [ ] Stats endpoint returns database statistics
- [ ] Schema endpoint returns table structure
- [ ] Species endpoint returns list of species

### NestChat
- [ ] Questions generate SQL queries
- [ ] SQL executes successfully
- [ ] Errors trigger retry (max 3 attempts)
- [ ] Answers stream in real-time
- [ ] Charts render correctly
- [ ] Maps show colony locations

### NestVision
- [ ] Image upload works
- [ ] Detection runs without errors
- [ ] Annotated image displays
- [ ] Species classification works
- [ ] Confidence threshold adjustable

### Webapp
- [ ] Landing page loads
- [ ] Stats display correctly
- [ ] Chat interface responsive
- [ ] Vision interface responsive
- [ ] Mobile warning shows on small screens
- [ ] Theme toggle works (light/dark)

## 🐛 Common Issues

### "OPENROUTER_API_KEY not set"
**Solution:** Add key to `.env` file, restart server

### "Database not found"
**Solution:** Verify `data/bird_data_complete.db` exists

### "No module named 'cv_tools'"
**Solution:** Ensure you're running from `public/` directory

### "Port already in use"
**Solution:** Kill existing process or change port in `.env`

### Models not loading
**Solution:** Check `models/` folder contains:
- `swift.onnx` (~10MB)
- `classifier_swift.onnx` (~6MB)

### Webapp can't connect to backend
**Solution:** Ensure backend is running at `http://localhost:8000`

## 📊 Performance Benchmarks

**Expected performance on local machine:**

| Operation | Time | Memory |
|-----------|------|--------|
| Backend startup | 2-3s | ~150MB |
| SQL query | 0.5-2s | +50MB |
| Bird detection | 2-5s | +300MB |
| First request (cold) | 3-5s | - |
| Subsequent requests | 0.5-1s | - |

**Railway deployment (estimated):**
- Cold start: 10-15s
- Warm requests: 2-3s
- Detection: 5-10s (no GPU)

## 🚀 Ready for Deployment?

If all tests pass, you're ready to deploy to Railway!

See `DEPLOYMENT_GUIDE.md` for Railway deployment instructions.

---

**Testing complete? Deploy with confidence! 🎉**
