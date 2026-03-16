# NestScope Public - Railway Deployment Guide

## 🚂 Railway Deployment Steps

### 1. Prepare Your Repository

```bash
cd public/
git init
git add .
git commit -m "Initial commit - NestScope Public"
```

### 2. Create Railway Project

1. Go to [railway.app](https://railway.app)
2. Click "New Project"
3. Select "Deploy from GitHub repo" or "Empty Project"

### 3. Connect Repository

**Option A: GitHub**
- Push your `public/` folder to a GitHub repository
- Connect Railway to that repository
- Railway will auto-detect the Python project

**Option B: Railway CLI**
```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Initialize project
railway init

# Deploy
railway up
```

### 4. Set Environment Variables

In Railway Dashboard → Variables:

```
OPENROUTER_API_KEY=your-openrouter-api-key-here
```

Optional variables:
```
MODEL_NAME=anthropic/claude-sonnet-4.5
DB_PATH=data/bird_data_complete.db
```

### 5. Verify Deployment

Railway will automatically:
1. Install dependencies from `requirements.txt`
2. Run the Procfile command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
3. Assign a public URL like: `https://your-app-name.up.railway.app`

Check deployment logs:
```bash
railway logs
```

### 6. Test Endpoints

Once deployed, test:

```bash
# Health check
curl https://your-app-name.up.railway.app/health

# API documentation
https://your-app-name.up.railway.app/docs

# Stats
curl https://your-app-name.up.railway.app/stats
```

## 📊 Railway Resource Requirements

**Estimated usage:**
- **Memory:** ~1.5GB (models + ONNX Runtime)
- **Storage:** ~70MB (code + models + database)
- **CPU:** Light (spikes during inference)

**Recommended plan:**
- Hobby plan or higher (for consistent uptime)
- Add-ons: None required

## 🔧 Troubleshooting

### Build Fails

**Issue:** Dependencies not installing
```bash
# Check requirements.txt is present
# Verify Python version compatibility (3.11+)
```

**Solution:** Railway uses Nixpacks to auto-detect Python projects. Ensure `requirements.txt` is in root.

### Runtime Errors

**Issue:** "OPENROUTER_API_KEY not set"
```bash
# Check environment variables in Railway dashboard
railway variables
```

**Issue:** "Database not found"
```bash
# Verify data/bird_data_complete.db exists in deployment
# Check DB_PATH environment variable
```

**Issue:** "Module not found: cv_tools"
```bash
# Ensure cv_tools/ folder is committed to git
# Check .gitignore doesn't exclude it
```

### Performance Issues

**Issue:** Slow inference
- ONNX Runtime may not have CPU optimizations on Railway
- Consider using smaller confidence threshold (0.3 instead of 0.25)
- Limit image size to < 2048px

**Issue:** Cold starts
- Railway free tier has cold starts after inactivity
- Upgrade to Hobby plan for persistent uptime

## 🌐 Custom Domain

1. Go to Railway Dashboard → Settings
2. Click "Generate Domain" or "Add Custom Domain"
3. Follow DNS configuration instructions

## 📈 Monitoring

### Health Checks

Railway will automatically restart if:
- `/health` endpoint returns non-200 status
- Application crashes

### Logs

View real-time logs:
```bash
railway logs --follow
```

Download logs:
```bash
railway logs > deployment.log
```

### Metrics

Railway Dashboard shows:
- Memory usage
- CPU usage
- Network traffic
- Request latency

## 💰 Cost Estimation

**Railway Hobby Plan:**
- $5/month for 500 hours
- Additional usage: $0.20/hour

**Estimated monthly cost:**
- 24/7 uptime: ~$150/month (720 hours)
- 8 hours/day: ~$50/month (240 hours)

**Free Tier:**
- $5 free credit/month
- ~25 hours of runtime
- Good for testing/demos

## 🔒 Security Best Practices

1. **Never commit `.env` file**
   - Use Railway's environment variables
   - Rotate API keys regularly

2. **Database is read-only**
   - SQLite opened in `mode=ro`
   - No write operations possible

3. **Rate limiting** (optional)
   - Add rate limiting middleware for production
   - Protect against API abuse

4. **HTTPS only**
   - Railway provides automatic HTTPS
   - All traffic is encrypted

## 🚀 Next Steps

After deployment:

1. **Test all endpoints** through `/docs`
2. **Monitor logs** for errors
3. **Set up alerts** (Railway notifications)
4. **Add custom domain** (optional)
5. **Share your API** with users

## 📞 Support

- **Railway Docs:** https://docs.railway.app
- **Railway Discord:** https://discord.gg/railway
- **OpenRouter Support:** https://openrouter.ai/docs

---

**Happy deploying! 🎉**
