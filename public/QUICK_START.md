# Quick Start Guide

Get NestScope Public running in 5 minutes.

## 🚀 Local Development

### 1. Setup (30 seconds)
```bash
cd public/
cp .env.example .env
```

Edit `.env` and add your OpenRouter API key:
```
OPENROUTER_API_KEY=your-actual-key-here
```

### 2. Install (2 minutes)
```bash
pip install -r requirements.txt
```

### 3. Run (instant)
```bash
./run.sh
```

**That's it!** Open http://localhost:8000

Single unified server serves both API and webapp! 🎉

---

## ☁️ Railway Deployment

### 1. Prerequisites
- Railway account ([railway.app](https://railway.app))
- OpenRouter API key ([openrouter.ai/keys](https://openrouter.ai/keys))

### 2. Deploy (3 clicks)
```bash
# Initialize
cd public/
railway login
railway init

# Set environment
railway variables set OPENROUTER_API_KEY=your-key

# Deploy
railway up
```

**Done!** Railway provides your public URL.

---

## 🧪 Quick Test

### Test Backend
```bash
curl http://localhost:8000/health
```

### Test NestChat
1. Open http://localhost:8501/chat
2. Ask: "How many brown pelicans were observed in 2020?"
3. Watch AI generate SQL and answer

### Test NestVision
1. Open http://localhost:8501/vision
2. Upload a bird image
3. See detection results

---

## 📚 Full Documentation

- **Complete setup:** `README.md`
- **Railway deployment:** `DEPLOYMENT_GUIDE.md`
- **Local testing:** `TEST_LOCAL.md`
- **Pre-deployment checklist:** `CHECKLIST.md`

---

## 🆘 Troubleshooting

**"API key not set"**
→ Add `OPENROUTER_API_KEY` to `.env` file

**"Database not found"**
→ Verify `data/bird_data_complete.db` exists

**"Port in use"**
→ Change port: `PORT=8001 ./run.sh`

---

**Questions?** Check the full docs in `README.md`
