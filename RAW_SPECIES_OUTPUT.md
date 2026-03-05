# Raw Species Output (No Grouping)

## Changes Made

### Problem
The classification system was showing grouped categories (PELICAN, TERN, GULL, etc.) instead of the exact species codes the model predicted. This added an abstraction layer that obscured what the model actually detected.

**User feedback:**
> "It should just say the exact thing the model gives to it no overlay on top no grouping just model answer"

### Solution
Removed the grouping abstraction and now display raw species codes directly from the classifier model.

---

## What Changed

### 1. Backend: Species Summary Grouping

**File:** `server/cv_tools/inference.py`

**Before (Grouped by functional groups):**
```python
# Build species summary: {group: count}
species_summary: dict = {}
for det in detections:
    g = det.get('species_group', 'UNKNOWN')
    species_summary[g] = species_summary.get(g, 0) + 1

# Result: {'PELICAN': 3, 'TERN': 2, 'GULL': 5}
```

**After (Grouped by species codes):**
```python
# Build species summary: {species_code: count}
species_summary: dict = {}
for det in detections:
    code = det.get('species_code', 'UNKNOWN')
    species_summary[code] = species_summary.get(code, 0) + 1

# Result: {'BRPE': 3, 'BLSK': 2, 'LAGU': 5}
```

**Changes made in two functions:**
- `detect()` - line ~962
- `detect_on_mosaic_tile()` - line ~1095

---

### 2. Frontend: Species Display

**File:** `frontend/pages/02_nest_vision.py`

**Changed section title:**
```python
# Before:
st.markdown("#### 🦜 Species Group Breakdown")

# After:
st.markdown("#### 🦜 Species Breakdown")
```

**Built species name mapping:**
```python
# Build species code to name mapping from detections
detections = result.get("detections", [])
species_names = {}
for det in detections:
    code = det.get("species_code", "")
    name = det.get("species_name", "")
    if code and code not in species_names:
        species_names[code] = name
```

**Updated metric display:**
```python
# Before (showed groups):
label = group.replace("_", " ").title()  # e.g., "Pelican"
st.metric(label=label, value=count)

# After (shows species codes):
species_name = species_names.get(species_code, species_code)
label = f"{species_code}"  # e.g., "BRPE"
st.metric(label=label, value=count, help=species_name)
```

**Updated chart labels:**
```python
# Before (showed groups):
y=[g.replace("_", " ").title() for g in display_summary.keys()]
# Result: ["Pelican", "Tern", "Gull"]

# After (shows species codes + names):
chart_labels = []
for code in display_summary.keys():
    name = species_names.get(code, code)
    if name and name != code:
        chart_labels.append(f"{code} - {name}")
    else:
        chart_labels.append(code)
# Result: ["BRPE - Brown Pelican", "BLSK - Black Skimmer", "LAGU - Laughing Gull"]
```

---

## Before vs After

### Display Changes

**Before (Grouped):**
```
Species Group Breakdown

Pelican      3
Tern         2
Gull         5

[Bar chart showing: Pelican, Tern, Gull]
```

**After (Raw Species):**
```
Species Breakdown

BRPE         3  (hover: Brown Pelican)
BLSK         2  (hover: Black Skimmer)
LAGU         5  (hover: Laughing Gull)

[Bar chart showing: BRPE - Brown Pelican, BLSK - Black Skimmer, LAGU - Laughing Gull]
```

### API Response Changes

**Before:**
```json
{
  "bird_count": 10,
  "species_summary": {
    "PELICAN": 3,
    "TERN": 2,
    "GULL": 5
  },
  "detections": [...]
}
```

**After:**
```json
{
  "bird_count": 10,
  "species_summary": {
    "BRPE": 3,
    "BLSK": 2,
    "LAGU": 5
  },
  "detections": [...]
}
```

---

## Why This is Better

### Transparency
**Before:** User sees "BLSK" label on image but stats say "TERN"
- Confusing abstraction layer
- User doesn't know what the model actually detected
- "Is BLSK a tern? Why doesn't it say BLSK in the stats?"

**After:** User sees "BLSK" on image AND in stats
- Direct, transparent output
- Clear what the model detected
- No abstraction or grouping confusion

### Accuracy
**Before:** Model outputs 25 species but only shows 9 groups
- Loss of information
- Can't distinguish between species in same group
- Example: Can't tell BRPE from AWPE (both show as "PELICAN")

**After:** Model outputs 25 species and shows all 25
- No information loss
- Full classification detail preserved
- Example: BRPE and AWPE shown separately with exact counts

### Educational Value
**Before:** Users learn about arbitrary functional groups
- Groups are project-specific abstractions
- Don't match scientific taxonomy exactly
- Not transferable to other contexts

**After:** Users learn 4-letter AOU species codes
- Standard ornithological codes (American Ornithological Union)
- Recognized by bird researchers worldwide
- Directly applicable to field guides and databases

---

## Species Codes Reference

The model classifies into 25 Gulf Coast waterbird species:

**Pelicans:**
- BRPE - Brown Pelican
- AWPE - American White Pelican

**Cormorants:**
- DCCO - Double-crested Cormorant
- NECO - Neotropic Cormorant

**Large Herons:**
- GBHE - Great Blue Heron
- GREG - Great Egret
- BCNH - Black-crowned Night Heron

**White Waders:**
- SNEG - Snowy Egret
- CAEG - Cattle Egret
- WHIB - White Ibis

**Colorful Waders:**
- REEG - Reddish Egret
- TRHE - Tricolored Heron
- ROSP - Roseate Spoonbill
- WFIB - White-faced Ibis

**Gulls:**
- LAGU - Laughing Gull

**Terns:**
- BLSK - Black Skimmer
- ROYT - Royal Tern
- CATE - Caspian Tern
- SATE - Sandwich Tern
- FOTE - Forster's Tern
- GBTE - Gull-billed Tern
- LETE - Least Tern
- SOTE - Sooty Tern

**Shorebirds:**
- AMOY - American Oystercatcher

**Rare:**
- GRFL - Greater Flamingo

---

## Color Coding Still Works

The bounding boxes are still color-coded by functional group for visual distinction:
- Each species still has its group assigned internally
- Colors help distinguish different birds visually
- Labels and stats show species codes, not groups

**Example:**
- BRPE detection → Box colored orange (PELICAN group color)
- BLSK detection → Box colored cyan (TERN group color)
- LAGU detection → Box colored green (GULL group color)

But labels and stats display:
- "BRPE" not "PELICAN"
- "BLSK" not "TERN"
- "LAGU" not "GULL"

---

## Testing

```bash
./run_app.sh
# Navigate to NestVision
# Upload image or use example
# Run detection

✓ Species codes shown in stats (BRPE, LAGU, etc.)
✓ Full names shown on hover/in chart
✓ No grouped categories (no PELICAN, TERN, GULL labels)
✓ Chart shows individual species
✓ Counts match image labels exactly
```

**Test with varied species:**
1. Image with 3 Brown Pelicans, 2 Laughing Gulls
   - Stats should show: "BRPE: 3, LAGU: 2"
   - NOT: "PELICAN: 3, GULL: 2"

2. Image with 5 Black Skimmers, 3 Royal Terns
   - Stats should show: "BLSK: 5, ROYT: 3"
   - NOT: "TERN: 8"

3. Image with mixed species from same group
   - Should distinguish each species separately
   - No lumping into single group count

---

## Files Modified

1. **`server/cv_tools/inference.py`**
   - Lines ~962-965: Changed species_summary grouping (detect function)
   - Lines ~1095-1098: Changed species_summary grouping (mosaic function)
   - Both now group by `species_code` instead of `species_group`

2. **`frontend/pages/02_nest_vision.py`**
   - Lines ~261-268: Added species_names mapping builder
   - Lines ~334-372: Updated species breakdown display
   - Section title changed from "Species Group Breakdown" to "Species Breakdown"
   - Metrics show species codes with full names in help text
   - Chart labels show "CODE - Name" format

---

## Impact on Other Features

### Detection Details Table (Still Shows All Info)
The detailed detection table (in expander) still shows all fields:
- Species code
- Common name
- Classification confidence
- Group (for reference)

This provides full transparency while keeping the main display clean and focused on raw species codes.

### Nestperts Integration (Unchanged)
When sending detections to Nestperts, all fields are preserved:
- `species_code`
- `species_name`
- `species_group`
- `species_confidence`

Experts can see and modify all classification information.

### Color Coding (Unchanged)
Bounding box colors remain group-based:
- Visual distinction between different bird types
- Color consistency across similar species
- Helps identify birds at a glance

Only the labels and stats changed to show raw codes.

---

## Rollback Instructions

If needed, revert to grouped display:

```bash
git checkout HEAD -- server/cv_tools/inference.py frontend/pages/02_nest_vision.py
```

Or manually change:

**Backend:**
```python
# Change back to:
g = det.get('species_group', 'UNKNOWN')
species_summary[g] = species_summary.get(g, 0) + 1
```

**Frontend:**
```python
# Change back to:
st.markdown("#### 🦜 Species Group Breakdown")
label = group.replace("_", " ").title()
st.metric(label=label, value=count)
```

---

## Future Enhancements

### Potential Improvements:
- [ ] Toggle between species view and group view
- [ ] Show both code and name in metric label (not just hover)
- [ ] Color-code metrics by species group
- [ ] Add species thumbnails/silhouettes next to codes
- [ ] Export species breakdown as CSV with full details
- [ ] Filter detections by specific species in UI

### Advanced Features:
- [ ] Species confidence threshold slider (only show high-confidence species)
- [ ] Top-K species alternatives per detection
- [ ] Species confusion matrix (which species get confused)
- [ ] Confidence distribution chart per species

---

## Summary

Removed the functional group abstraction layer and now display raw species codes directly from the classifier model. This provides:

✅ **Transparency** - What you see on the image matches what you see in stats
✅ **Accuracy** - No information loss from grouping
✅ **Standards** - Uses official AOU 4-letter codes
✅ **Clarity** - Direct model output, no overlay or interpretation

The system still uses groups internally for color-coding bounding boxes, but all labels and statistics now show the exact species codes the model predicted.
