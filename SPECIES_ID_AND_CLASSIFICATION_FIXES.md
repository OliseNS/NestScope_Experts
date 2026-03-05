# Species ID and Classification Fixes

## Changes Made

### 1. Removed Species ID Tab from Streamlit ✅

**Why:**
- Species ID is specifically designed for the Nestperts labeller
- Not needed in the public-facing Streamlit frontend
- Reduces clutter in navigation

**What was removed:**
- "🐦 Species ID" button from sidebar navigation
- Tab no longer accessible from Streamlit frontend
- Page file still exists but not linked

**Files Modified:**
- `frontend/components/page_layout.py` - Removed Species ID button from sidebar

**Navigation Now:**
```
🏠 Home
💬 NestChat
🦅 NestVision
📈 NestTrends
🗄️ NestDB

🛠️ Tools
🧑‍🔬 Nestperts (external link)
```

**Species ID Still Available In:**
- ✅ Nestperts labeller (http://localhost:5000)
- ✅ Expert annotation workflow
- ❌ Public Streamlit frontend (removed)

---

### 2. Fixed Classification Mismatch (BLSK → TERN) ✅

**Problem:**
- Model detected "BLSK" (Black Skimmer) and labeled it correctly on image
- Stats below showed "TERN: 1" instead of "GULL: 1"
- User confusion: "The model knows what it is but stats show something else"

**Root Cause:**
Black Skimmer was incorrectly mapped to GULL group, but should be in TERN group.

**Why BLSK Should Be With Terns:**
- **Taxonomy**: Family Laridae (gulls & terns), but in separate subfamily
- **Morphology**: Tern-like body shape, long wings, forked tail
- **Behavior**: Catch fish by skimming water surface (like terns)
- **Habitat**: Nest colonially with terns
- **Field Guides**: Usually grouped with terns, not gulls

**The Fix:**
```python
# Before (WRONG):
'LAGU': 'GULL',
'BLSK': 'GULL',  # ❌ Black Skimmer grouped with gulls

# After (CORRECT):
'LAGU': 'GULL',
'BLSK': 'TERN',  # ✅ Black Skimmer grouped with terns
```

**Now When Model Detects BLSK:**
- Image label: "BLSK" ✓
- Stats: "TERN: 1" ✓
- **Consistent and correct!**

**Files Modified:**
- `server/cv_tools/classifier_species.py` - Moved BLSK from GULL to TERN group

---

## Before vs After

### Navigation (Streamlit)

**Before:**
```
Sidebar:
├── Home
├── NestChat
├── NestVision
├── NestTrends
├── NestDB
└── Species ID  ← Shouldn't be here (for labeller only)
```

**After:**
```
Sidebar:
├── Home
├── NestChat
├── NestVision
├── NestTrends
└── NestDB  ← Cleaner!

Tools:
└── Nestperts (external)
```

---

### Classification Display

**Before (INCORRECT):**
```
Image:
┌─────────────────┐
│   [BLSK]        │  ← Shows "BLSK" correctly
│                 │
└─────────────────┘

Stats:
┌─────────────────┐
│ Gull:      1    │  ← WRONG! Should be Tern
└─────────────────┘
```

**After (CORRECT):**
```
Image:
┌─────────────────┐
│   [BLSK]        │  ← Shows "BLSK" correctly
│                 │
└─────────────────┘

Stats:
┌─────────────────┐
│ Tern:      1    │  ← CORRECT! Matches the detection
└─────────────────┘
```

---

## Species Group Mapping (Updated)

### Complete Group Assignments:

**PELICAN:**
- BRPE (Brown Pelican)
- AWPE (American White Pelican)

**CORMORANT:**
- DCCO (Double-crested Cormorant)
- NECO (Neotropic Cormorant)

**LARGE_HERON:**
- GBHE (Great Blue Heron)
- GREG (Great Egret)
- BCNH (Black-crowned Night Heron)

**WHITE_WADER:**
- SNEG (Snowy Egret)
- CAEG (Cattle Egret)
- WHIB (White Ibis)

**COLOR_WADER:**
- REEG (Reddish Egret)
- TRHE (Tricolored Heron)
- ROSP (Roseate Spoonbill)
- WFIB (White-faced Ibis)

**GULL:**
- LAGU (Laughing Gull)

**TERN:** (Updated!)
- BLSK (Black Skimmer) ← **MOVED FROM GULL**
- ROYT (Royal Tern)
- CATE (Caspian Tern)
- SATE (Sandwich Tern)
- FOTE (Forster's Tern)
- GBTE (Gull-billed Tern)
- LETE (Least Tern)
- SOTE (Sooty Tern)

**SHOREBIRD:**
- AMOY (American Oystercatcher)

**RARE:**
- GRFL (Greater Flamingo)

---

## Testing

### Species ID Removal:
```bash
./run_app.sh
# Navigate through Streamlit sidebar
✓ Species ID button should NOT appear
✓ Navigation should be cleaner
✓ All other pages still work
```

### Classification Fix:
```bash
./run_app.sh
# Go to NestVision
# Upload image with Black Skimmers
# Run detection

✓ Image shows: "BLSK" label
✓ Stats show: "Tern: X"
✓ Both match correctly!
```

**Also Test Other Species:**
- LAGU (Laughing Gull) → Shows as "GULL" ✓
- ROYT (Royal Tern) → Shows as "TERN" ✓
- BRPE (Brown Pelican) → Shows as "PELICAN" ✓

---

## Why This Matters

### User Experience:
**Before:**
- User sees "BLSK" on image
- Stats say "GULL"
- **Confusion!** "Is the model wrong?"

**After:**
- User sees "BLSK" on image
- Stats say "TERN"
- **Consistency!** Everything matches

### Ecological Accuracy:
Black Skimmers are NOT gulls:
- Different feeding behavior (skim water surface)
- Different bill structure (unique lower mandible)
- More closely related to terns
- Field guides group them with terns

### Professional Appearance:
- Shows understanding of avian taxonomy
- Matches scientific classification
- Aligns with field guide conventions

---

## Files Modified

1. `frontend/components/page_layout.py`
   - Removed Species ID button from sidebar
   - Lines ~137-144 deleted

2. `server/cv_tools/classifier_species.py`
   - Line 97: Changed `'BLSK': 'GULL'` to `'BLSK': 'TERN'`
   - Updated comments to reflect change

---

## Color Coding (No Change)

TERN group color remains:
```python
'TERN': (42, 180, 220),  # Cyan/teal (BGR format)
```

BLSK detections will now show in cyan/teal color instead of green.

---

## Educational Notes

### Why Species Groups?
- **Simplification**: 25 species → 9 groups for easier visualization
- **Color Coding**: Each group has distinct color for quick identification
- **Field Use**: Groups similar-looking birds together

### Taxonomic Hierarchy:
```
Order: Charadriiformes (shorebirds)
├── Family: Laridae (gulls, terns, skimmers)
│   ├── Subfamily: Larinae (gulls)
│   │   └── LAGU (Laughing Gull)
│   ├── Subfamily: Sterninae (terns)
│   │   ├── ROYT (Royal Tern)
│   │   ├── CATE (Caspian Tern)
│   │   └── [other terns]
│   └── Subfamily: Rynchopinae (skimmers)
│       └── BLSK (Black Skimmer) ← Closer to terns!
```

### Black Skimmer Facts:
- **Scientific Name**: Rynchops niger
- **Unique Feature**: Lower mandible longer than upper (for skimming)
- **Behavior**: Flies low over water, lower bill slicing surface
- **Habitat**: Coastal beaches, salt marshes
- **Often Seen**: Nesting near tern colonies

---

## Rollback Instructions

If issues arise:

```bash
# Restore Species ID tab
git checkout HEAD -- frontend/components/page_layout.py

# Revert BLSK grouping
git checkout HEAD -- server/cv_tools/classifier_species.py
```

Or manually:
- Add back Species ID button to page_layout.py
- Change line 97 in classifier_species.py: `'BLSK': 'GULL'`

---

## Future Enhancements

### Species Grouping:
- [ ] Add SKIMMER as separate group (instead of with TERN)
- [ ] Split CORMORANT and LARGE_HERON into separate groups
- [ ] Add IBIS group (separate from COLOR_WADER)

### Navigation:
- [ ] Add Species ID as admin-only page
- [ ] Add authentication to hide labeller tools

### Classification:
- [ ] Show both species code and common name on image
- [ ] Add confidence % to image labels
- [ ] Group stats by confidence level
