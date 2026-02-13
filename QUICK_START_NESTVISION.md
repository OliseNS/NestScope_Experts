# Quick Start: NestVision Enhanced Features

## 🚀 Getting Started in 3 Steps

### Step 1: Start All Services
```bash
./run_app.sh
```

This starts:
- FastAPI Server (http://localhost:8000)
- Streamlit App (http://localhost:8501)
- Labeller App (http://localhost:5000)

### Step 2: Use NestVision
1. Go to http://localhost:8501
2. Click the **🦅 NestVision** tab
3. Upload an image or use an example
4. Wait for detection to complete

### Step 3: Improve the Model

#### Option A: Correct AI Errors
1. Click **"🔧 Correct AI"** button
2. Fix any wrong detections
3. Click **"💾 Save Corrections"**

Data saved to: `labeller/nestvision/corrections/`

#### Option B: Identify Species
1. Scroll to **"🐦 Species Identification Training"**
2. Select species for each crop
3. Click **"💾 Save"** for each

Data saved to: `labeller/nestvision/crops/`

---

## 📊 Training a New Model

### Easy Way (Recommended for Beginners)

1. **Run Vision Train UI:**
   ```bash
   ./run_vision_train.sh
   ```
   Or manually:
   ```bash
   streamlit run VisionTrain/train_ui.py --server.port 8502
   ```

2. **Configure in the UI:**
   - Go to http://localhost:8502
   - Set dataset path to your data
   - Choose parameters (use defaults for beginners)
   - Click **"🚀 Start Training"**

3. **Monitor Progress:**
   - Switch to **"📊 Monitor Progress"** tab
   - Watch metrics update in real-time

### Advanced Way (For Experts)

Edit and run `VisionTrain/train.py` directly:
```bash
python VisionTrain/train.py
```

---

## 📁 Directory Structure

```
nexus/
├── labeller/
│   └── nestvision/
│       ├── corrections/      # AI-corrected images & labels
│       │   ├── images/
│       │   └── labels/
│       └── crops/            # Species-identified bird crops
├── VisionTrain/
│   ├── train.py              # Training script
│   └── train_ui.py           # User-friendly training UI
└── runs/
    └── detect/
        └── train/            # Training results
            └── weights/
                └── best.pt   # Your trained model
```

---

## ⚡ Common Tasks

### Check What's Running
```bash
# Check if services are up
curl http://localhost:8000/health     # FastAPI
curl http://localhost:8501            # Streamlit
curl http://localhost:5000            # Labeller
```

### View Logs
```bash
tail -f logs/server.log      # FastAPI logs
tail -f logs/streamlit.log   # Streamlit logs
tail -f logs/labeller.log    # Labeller logs
```

### Stop All Services
Press `Ctrl+C` in the terminal running `./run_app.sh`

### Prepare Dataset for Training
Your dataset should look like this:
```
nestvision/
├── images/
│   ├── img1.jpg
│   └── img2.jpg
└── labels/
    ├── img1.txt
    └── img2.txt
```

Labels should be in YOLO format:
```
0 0.5 0.5 0.1 0.1
```
(class_id, x_center, y_center, width, height - all normalized 0-1)

---

## 🐛 Troubleshooting

### "Labeller app not running"
**Solution:**
```bash
python labeller/app.py --data nestvision
```

### "Out of memory" during training
**Solutions:**
- Reduce batch size to 8 or 4
- Reduce image size to 640
- Close other applications
- Use smaller model (yolov8n.pt instead of yolov8m.pt)

### No species showing up
**Check:**
- File exists: `CSV_Files/tblSpeciesData2015_2018_2021.csv`
- File has `SpeciesCode` column

### Corrections not saving
**Check:**
- Labeller is running on port 5000
- Directory exists: `labeller/nestvision/corrections/`
- Directory has write permissions

---

## 📚 Full Documentation

For detailed documentation, see:
- [NESTVISION_FEATURES.md](NESTVISION_FEATURES.md) - Complete feature guide
- [QUICK_START_NESTVISION.md](QUICK_START_NESTVISION.md) - This file

---

## 💡 Pro Tips

1. **Start small:** Test with 10-20 images before processing hundreds
2. **Correct consistently:** Use the same class labels across all corrections
3. **Identify confidently:** Only identify species you're sure about
4. **Train incrementally:** Start with 10 epochs to test, then increase
5. **Monitor regularly:** Check the Monitor Progress tab during training
6. **Backup models:** Copy `runs/detect/train/weights/best.pt` after each training session

---

## 🎯 Complete Workflow Example

```bash
# 1. Start all services
./run_app.sh

# 2. In browser: http://localhost:8501
# - Go to NestVision tab
# - Upload image
# - Run detection
# - Correct AI (if needed)
# - Identify species (5 crops)

# 3. Repeat for 50-100 images to build dataset

# 4. Start Vision Train UI (in new terminal)
./run_vision_train.sh

# 5. In browser: http://localhost:8502
# - Configure training
# - Start training
# - Monitor progress

# 6. After training completes:
# - Copy runs/detect/train/weights/best.pt to your model directory
# - Update your model path in the app
# - Test new model in NestVision

# 7. Iterate:
# - Test new model
# - Find and correct errors
# - Retrain with more data
# - Improve accuracy
```

---

## 🆘 Need Help?

1. Check logs in `logs/` directory
2. Verify all services are running
3. Check directory permissions
4. Review [NESTVISION_FEATURES.md](NESTVISION_FEATURES.md)
5. Ensure Python packages are installed: `pip install -r requirements.txt`

Happy bird detecting! 🦅
