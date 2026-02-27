# Phase 3 REVISED: Separated Download & Detection Pipeline

**Date:** 2026-02-26
**Status:** ✅ CODE COMPLETE - READY FOR TESTING
**Change:** Split into 2 separate scripts for better control and resumability

---

## Why the Change?

**Original Approach:** Download + Detect in one script
**Revised Approach:** Separate download and detection

**Benefits:**
1. **Download once, detect multiple times** - If detection parameters need tweaking, no re-download
2. **Species linkage validation** - Check species correctness before spending 8 hours on detection
3. **Resume support** - Detection can resume from where it left off
4. **Balanced detection** - Can sample images by species for even coverage
5. **Inspect downloads** - Manually verify images before detection

---

## The 3-Script Workflow

### Script 1: Download Images with Species Metadata
**File:** `scripts/batch_download.py`

**What it does:**
- Downloads all 6,795 images from S3
- Creates `image_metadata.json` linking each image to species candidates
- Analyzes species distribution

**Runtime:** ~1-2 hours (mainly network I/O)

**Output:**
```
data/weak_supervision/
├── downloaded_images/          # 6,795 images (~35 GB)
│   ├── 2015_1_1_00001.JPG
│   ├── 2015_1_1_00002.JPG
│   └── ...
└── image_metadata.json         # Species linkage for each image
```

**Metadata Structure:**
```json
{
  "2015_1_1_00001": {
    "photo_id": "2015_1_1_00001",
    "image_path": "data/weak_supervision/downloaded_images/2015_1_1_00001.JPG",
    "s3_path": "s3://twi-aviandata/HighResolutionImages/2015/...",
    "s3_key": "HighResolutionImages/2015/...",
    "species_codes": ["BRPE", "LAGU"],
    "species_count": 2,
    "is_single_species": false,
    "metadata": {
      "year": "2015",
      "camera": "1",
      "card": "1",
      "colony": "East Bay",
      "date": "05/16/15",
      "photo_num": "00001"
    }
  }
}
```

---

### Script 2: Validate Species Linkage
**File:** `scripts/validate_species_linkage.py`

**What it does:**
- Validates species codes against database
- Checks metadata structure integrity
- Analyzes species distribution for anomalies
- Identifies rare species (<5 images)
- Detects extreme imbalances

**Runtime:** ~10 seconds

**Checks performed:**
1. ✅ All species codes exist in database
2. ✅ Metadata structure is complete (no missing fields)
3. ✅ `species_count` matches `species_codes` length
4. ✅ `is_single_species` flag is correct
5. ✅ Species distribution is reasonable
6. ⚠️ Flags rare species and anomalies

**Output:** Console report with pass/fail status

---

### Script 3: Run Detection and Extract Crops
**File:** `scripts/batch_detect.py`

**What it does:**
- Reads `image_metadata.json`
- Runs YOLO detection on each image
- Extracts bird crops with species linkage
- **Saves progress every 100 images** (crash recovery)
- **Can resume** from where it left off

**Runtime:** ~8-10 hours (SAHI mode detection)

**Output:**
```
data/weak_supervision/
└── bird_crops/
    ├── images/                 # 30K-50K bird crops
    │   ├── bird_000000.jpg
    │   ├── bird_000001.jpg
    │   └── ...
    └── metadata.json           # Crop metadata with species linkage
```

**Crop Metadata Structure:**
```json
{
  "crop_id": "bird_000000",
  "photo_id": "2015_1_1_00001",
  "image_path": "data/weak_supervision/downloaded_images/2015_1_1_00001.JPG",
  "s3_path": "s3://twi-aviandata/...",
  "bbox": [100, 200, 300, 400],
  "confidence": 0.85,
  "species_candidates": ["BRPE", "LAGU"],
  "species_count": 2,
  "is_single_species": false,
  "metadata": {
    "year": "2015",
    "camera": "1",
    "card": "1",
    "colony": "East Bay",
    "date": "05/16/15",
    "photo_num": "00001"
  }
}
```

**Key Feature: Resume Support**
- If detection is interrupted (crash, power loss, etc.), just re-run the script
- It checks existing crops and skips already-processed images
- Continues from where it left off

---

## Complete Workflow

### Step 1: Download Images (1-2 hours)
```bash
source .venv/bin/activate
python scripts/batch_download.py
```

**What to check:**
- ✅ All images downloaded successfully
- ✅ `image_metadata.json` created
- ✅ Species distribution looks reasonable

---

### Step 2: Validate Species Linkage (10 seconds)
```bash
python scripts/validate_species_linkage.py
```

**What to check:**
- ✅ All species codes are valid
- ✅ No metadata structure issues
- ✅ No extreme anomalies
- ✅ "ALL CHECKS PASSED" message

**If validation fails:**
- Review warnings
- Check for data issues in Phase 2 (filename_mapper.py)
- Fix issues before proceeding

---

### Step 3: Run Detection (8-10 hours)
```bash
python scripts/batch_detect.py
```

**What to check:**
- ✅ Detection starts successfully
- ✅ Progress saved every 100 images
- ✅ Crops being created in `bird_crops/images/`
- ✅ Can resume if interrupted

**Monitoring:**
```bash
# Check number of crops created
ls data/weak_supervision/bird_crops/images/ | wc -l

# Check disk usage
du -sh data/weak_supervision/

# View last few crops
ls -t data/weak_supervision/bird_crops/images/ | head -10
```

---

## File Organization

```
data/weak_supervision/
├── photo_mappings_2015_2021.json      ✅ Phase 2 output
├── photo_mapping_stats.json           ✅ Phase 2 stats
├── progress.md                        ✅ Overall tracking
├── code_review_phase3.md              ✅ Original review
├── PHASE3_SUMMARY.md                  ✅ Original approach
├── PHASE3_REVISED.md                  ✅ This file
│
├── downloaded_images/                 📥 Phase 3a output (~35 GB)
│   ├── 2015_1_1_00001.JPG
│   └── ...
│
├── image_metadata.json                📄 Phase 3a metadata
│
└── bird_crops/                        🔍 Phase 3b output (~3 GB)
    ├── images/
    │   ├── bird_000000.jpg
    │   └── ...
    └── metadata.json                  📄 Crop metadata with species linkage
```

---

## Key Advantages

### 1. Species Linkage Preserved
Every crop knows:
- Which photo it came from
- What species are in that photo (candidates)
- Whether it's single-species (ground truth) or multi-species (needs weak supervision)

### 2. Resume Capability
Detection script tracks processed photos:
- Checks existing crops
- Skips already-processed images
- Continues from interruption point
- No wasted computation

### 3. Balanced Detection
Future enhancement: Can sample images by species:
```python
# Example: Process 100 images per species
for species in all_species:
    images_with_species = [img for img in metadata.values() if species in img['species_codes']]
    sample = random.sample(images_with_species, 100)
    process_images(sample)
```

### 4. Validation Before Heavy Lifting
Validation script catches issues in 10 seconds:
- Invalid species codes
- Malformed metadata
- Distribution anomalies

**Better than:** Discovering issues after 8 hours of detection!

---

## Expected Statistics

### After Download (Step 1):
- **Images downloaded:** ~6,795 (100% of Phase 2 mappings)
- **Disk usage:** ~35 GB
- **Single-species images:** ~1,774 (26%)
- **Multi-species images:** ~5,020 (74%)

### After Validation (Step 2):
- **Valid species codes:** 100% (all from database)
- **Complete metadata:** 100% (all fields present)
- **Unique species:** ~73 (from tblSpeciesCodes)

### After Detection (Step 3):
- **Total crops:** ~30,000 - 50,000
- **Ground truth crops:** ~10,000 - 15,000 (from single-species images)
- **Need weak supervision:** ~20,000 - 35,000 (from multi-species images)
- **Disk usage:** ~3 GB (crops only)

---

## Known Limitations

### 1. Disk Space for Downloads
- Downloads occupy ~35 GB
- Must keep until detection completes
- **Option:** Delete downloads after detection (or keep for re-runs)

### 2. Detection Still Sequential
- Processes one image at a time
- Could be parallelized (complex)
- **Workaround:** Let run overnight

### 3. No Error Retry
- If S3 download fails, no automatic retry
- **Impact:** Minor (73% success rate expected from Phase 2)

### 4. Manual Cleanup Required
- Downloaded images stay on disk
- **Cleanup command:**
  ```bash
  rm -rf data/weak_supervision/downloaded_images/
  # (Only after detection completes!)
  ```

---

## Success Criteria

### Download (Step 1) Success:
- ✅ >90% of photos downloaded (~6,100+ images)
- ✅ `image_metadata.json` created
- ✅ Species distribution matches Phase 2 stats

### Validation (Step 2) Success:
- ✅ All species codes valid
- ✅ No metadata errors
- ✅ "ALL CHECKS PASSED"

### Detection (Step 3) Success:
- ✅ >90% of images processed (~6,100+ images)
- ✅ ~30K-50K crops extracted
- ✅ ~10K-15K ground truth crops (single-species)
- ✅ Average 5-7 birds per photo
- ✅ Crops visually look good (not cut off)

---

## Next Steps After Phase 3

Once all 3 scripts complete:

### Phase 4: Embedding Extraction & Clustering
- Use existing `BirdCropManager.generate_embeddings()`
- Extract SigLIP embeddings (768-dim vectors)
- Run DBSCAN clustering
- Output: `embeddings_siglip.npy`, `cluster_labels.npy`

### Phase 5: Weak Supervision
- Create `scripts/assign_species_labels.py`
- Algorithm: Single-species → cluster voting → multi-species
- Output: `weak_labels.json` (bird-level species assignments)

### Phase 6: Export Training Dataset
- Create `scripts/export_species_dataset.py`
- YOLO-format dataset with species labels
- Quality filtering by confidence

### Phase 7: Evaluation
- Calculate cluster purity
- Label consistency metrics
- Manual validation

---

## Troubleshooting

### Download Script Issues:

**Error: "Failed to download ... NoSuchKey"**
- Normal (27% expected failure rate)
- Script continues with other images

**Error: "Disk full"**
- Need >40 GB free space
- Clear space or use external drive

### Validation Script Issues:

**Warning: "Invalid species codes detected"**
- Check Phase 2 mappings
- Verify database has correct species codes
- May need to re-run filename_mapper.py

**Warning: "Extreme imbalance"**
- Normal for this dataset (LAGU dominates)
- Not necessarily an error

### Detection Script Issues:

**Error: "CUDA out of memory"**
- Switch to CPU: Set providers to ['CPUExecutionProvider']
- Or switch to `FAST_MODE = True`

**Script hangs:**
- SAHI can take 30 seconds for large images
- Be patient

**Crops look cut off:**
- Increase padding: `padding=0.10` (10%)

---

## Commands Reference

### Full Workflow:
```bash
# Step 1: Download (1-2 hours)
source .venv/bin/activate
python scripts/batch_download.py

# Step 2: Validate (10 seconds)
python scripts/validate_species_linkage.py

# Step 3: Detect (8-10 hours)
python scripts/batch_detect.py
```

### Monitoring:
```bash
# Check downloads
ls data/weak_supervision/downloaded_images/ | wc -l

# Check crops
ls data/weak_supervision/bird_crops/images/ | wc -l

# Disk usage
du -sh data/weak_supervision/
```

### Cleanup (after detection completes):
```bash
# Optional: Delete downloaded images to save space
rm -rf data/weak_supervision/downloaded_images/
```

---

## Educational Notes

### Why Separate Download and Detection?

**Analogy:** Like separating grocery shopping from cooking:
- **Download (shopping):** Get all ingredients once
- **Validate (check receipt):** Verify you got correct items
- **Detect (cooking):** Prepare the meal

If the meal doesn't turn out well, you don't need to go shopping again!

### What is Resume Support?

**Problem:** Detection takes 8-10 hours. What if it crashes at hour 7?

**Without resume:** Start over from scratch (lose 7 hours)
**With resume:** Check what's done, continue from hour 7 (lose nothing)

**How it works:**
```python
# Load existing crops
existing_crops = load_from_disk()
processed_photos = {crop['photo_id'] for crop in existing_crops}

# Skip processed, do remaining
for photo in all_photos:
    if photo.id not in processed_photos:
        process(photo)  # Only process new ones
```

### Why Validation Script?

**Murphy's Law:** "If something can go wrong, it will."

**Better to find out:**
- ✅ In 10 seconds (validation)
- ❌ After 8 hours (detection failure)

**What validation catches:**
- Typos in species codes
- Missing metadata fields
- Data corruption
- Extreme anomalies

---

**Last Updated:** 2026-02-26
**Status:** ✅ Ready for execution
**Start with:** `python scripts/batch_download.py`
