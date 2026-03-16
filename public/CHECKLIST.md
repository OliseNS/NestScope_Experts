# Pre-Deployment Checklist

Quick checklist before deploying to Railway.

## 📋 Files Verification

### Core Files
- [ ] `main.py` - FastAPI server (29KB)
- [ ] `requirements.txt` - Dependencies list
- [ ] `config.yaml` - Model configuration
- [ ] `Procfile` - Railway start command
- [ ] `railway.json` - Railway build config
- [ ] `.env.example` - Environment template
- [ ] `.gitignore` - Git ignore rules

### Models (16MB total)
- [ ] `models/swift.onnx` - Bird detector (9.6MB)
- [ ] `models/classifier_swift.onnx` - Species classifier (6MB)

### Database (8.4MB)
- [ ] `data/bird_data_complete.db` - SQLite database
- [ ] `data/database_metadata_enhanced.json` - Schema metadata

### Code
- [ ] `cv_tools/inference.py` - Detection logic
- [ ] `cv_tools/classifier_species.py` - Classification logic
- [ ] `prompts/*.txt` - LLM prompts (5 files)
- [ ] `webapp/app.py` - Flask frontend
- [ ] `webapp/api_client.py` - API client
- [ ] `webapp/templates/*.html` - HTML templates
- [ ] `webapp/static/css/*.css` - Stylesheets
- [ ] `webapp/static/js/*.js` - JavaScript

### Documentation
- [ ] `README.md` - Main docs
- [ ] `DEPLOYMENT_GUIDE.md` - Railway guide
- [ ] `TEST_LOCAL.md` - Local testing
- [ ] `PUBLIC_SUMMARY.md` - Package summary

## 🔑 Environment Setup

- [ ] OpenRouter API key obtained
- [ ] `.env` file created (local testing)
- [ ] Environment variables ready for Railway:
  - `OPENROUTER_API_KEY=your-key`

## 🧪 Local Testing

### Backend
- [ ] `uvicorn main:app --port 8000` starts successfully
- [ ] Health check: `curl http://localhost:8000/health`
- [ ] API docs accessible: `http://localhost:8000/docs`
- [ ] Stats endpoint works: `/stats`
- [ ] Config endpoint works: `/config`

### Frontend
- [ ] Webapp starts: `cd webapp && python app.py`
- [ ] Landing page loads: `http://localhost:8501`
- [ ] Chat interface responsive
- [ ] Vision interface responsive

### NestChat
- [ ] Ask a question → SQL generates
- [ ] SQL executes successfully
- [ ] Answer streams in real-time
- [ ] Artifacts render (charts/maps/tables)
- [ ] Error retry works (if SQL fails)

### NestVision
- [ ] Upload image → detection runs
- [ ] Annotated image displays
- [ ] Bird count shown
- [ ] Species classification works

## 🚂 Railway Deployment

### Pre-Deploy
- [ ] Code committed to git
- [ ] `.env` file NOT committed (in .gitignore)
- [ ] All dependencies in `requirements.txt`
- [ ] No local paths in code (use relative paths)

### Deploy Steps
- [ ] Railway project created
- [ ] Repository connected
- [ ] Environment variables set
- [ ] Build succeeds
- [ ] Service starts

### Post-Deploy
- [ ] Health endpoint returns 200
- [ ] API docs load at `/docs`
- [ ] Test NestChat with sample question
- [ ] Test NestVision with example image
- [ ] Check logs for errors: `railway logs`

## 🎯 Final Checks

### Security
- [ ] Database is read-only (no write operations)
- [ ] API key not in code (environment variable only)
- [ ] `.gitignore` excludes `.env` and logs
- [ ] No admin endpoints exposed

### Performance
- [ ] Backend starts in < 15s (Railway)
- [ ] Health check responds in < 1s
- [ ] SQL queries complete in < 5s
- [ ] Detection completes in < 10s

### Documentation
- [ ] README explains setup
- [ ] DEPLOYMENT_GUIDE covers Railway
- [ ] TEST_LOCAL covers testing
- [ ] API docs auto-generated

## ✅ Ready to Deploy?

If all checkboxes are checked, you're ready for Railway deployment!

```bash
cd public/
railway login
railway init
railway variables set OPENROUTER_API_KEY=your-key
railway up
```

---

**Deployment checklist complete! 🚀**
