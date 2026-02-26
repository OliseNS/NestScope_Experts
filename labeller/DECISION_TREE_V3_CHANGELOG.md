# Decision Tree v3.0 - Neck Length Update

## Date: 2026-02-26

## Summary
Redesigned the bird classification decision tree from **bill shape** (v2) to **neck length** (v3) for Step 2. This is a fundamental improvement in the system's design based on the realities of aerial photography.

## The Problem with Bill Shape (v2)

**Bill details are too small to see from aerial photographs!**

From high-altitude aerial images:
- ❌ Bill shape: Too small, often completely invisible
- ❌ Bill color: Requires close-up view
- ❌ Bill curvature: Impossible to discern at distance

The old system was asking experts to identify features they literally **could not see** in the images.

## Why Neck Length Works (v3)

**Neck length is highly visible from aerial views!**

From the same aerial images:
- ✅ **Very long neck** (Egrets, Herons) - Obvious even at high altitude
- ✅ **Short neck** (Terns, Gulls) - Compact body profile clearly visible
- ✅ **Stocky neck** (Night-Herons) - Body proportions stand out
- ✅ **Snake-like neck** (Anhinga) - Distinctive elongated silhouette

**This matches actual ornithological field practices** for distant bird identification.

## Changes Made

### 1. New Decision Tree JSON
- Created: `bird_classification_tree_v3_neck.json`
- Backed up old version: `bird_classification_tree_v2_bill_BACKUP.json`
- Replaced: `bird_classification_tree.json` → Now uses v3

### 2. Updated Step 2 Structure

**Old (Bill Shape):**
```
WHITE → Bill Shape:
  - MASSIVE POUCHED
  - LONG STRAIGHT
  - MEDIUM POINTED
  - UPTURNED
```

**New (Neck Length):**
```
WHITE → Neck Length:
  - VERY LONG NECK (Egrets, Herons, Stork)
  - SHORT NECK (Terns, Avocet)
  - HUGE BODY (Pelican)
```

### 3. Updated HTML Template
File: `labeller/templates/species_classification_tree.html`

**Changes:**
- Breadcrumb: "Bill Shape" → "Neck Length"
- Variable: `selectedBill` → `selectedNeck`
- Function: `selectBill()` → `selectNeck()`
- JSON key: `step_2_bill` → `step_2_neck`
- All comments updated to reflect neck-based morphology
- Decision path saved as `neck` instead of `bill`

### 4. Species Groupings by Neck Length

**WHITE birds:**
- Very Long Neck: GREG, SNEG, CAEG, WOST, WHEG
- Short Neck: All terns, AMAV
- Huge Body: AWPE

**DARK birds:**
- Very Long Neck: DCCO, NECO, ANHI, UNCO
- Short Neck: BLTE, SOTE, BRNO, LAGU, SONO, BLSK
- Huge Body: BRPE
- Very Long Wings: MAFR (Frigatebird - special case)

**BLUE-GRAY birds:**
- Very Long Neck: GBHE
- Long Neck: LTBH, TRHE, SDHE, UNHG
- Short Neck: BCNH, YCNH

**BROWN birds:**
- Long Neck: REEG, REEG DM
- Medium Neck: WHIB, WFIB, DAIB, UNIB, AMOY, BNST
- Short Neck: HERG, RUTU, ULGU, UNGU, UNGT, UNSB

**PINK birds:**
- Yes Bright Pink: ROSP (confirmation only)

## Benefits

1. **Accuracy**: Experts can now identify features they can actually see
2. **Speed**: Neck length is immediately obvious, no squinting required
3. **Confidence**: Decisions based on clear visible features increase expert confidence
4. **Scientific validity**: Matches real ornithological aerial ID practices
5. **Reduced errors**: Fewer misidentifications from trying to see invisible bill details

## Testing

After these changes, test the classification flow:
1. Select a color (Step 1)
2. Verify Step 2 shows "Neck Length" options
3. Select a neck length
4. Verify Step 3 shows appropriate species for that color/neck combination
5. Verify breadcrumbs show "Color → Neck Length → Species"

## Future Improvements

Consider adding:
- Visual guides showing neck length examples
- Comparison images (long neck vs short neck)
- Body proportion diagrams for each color group

## Files Modified

- ✅ `labeller/bird_classification_tree.json` (replaced with v3)
- ✅ `labeller/bird_classification_tree_v3_neck.json` (created)
- ✅ `labeller/bird_classification_tree_v2_bill_BACKUP.json` (backup)
- ✅ `labeller/templates/species_classification_tree.html` (updated)

## Backward Compatibility

Decision paths saved with the old system used `bill` field:
```json
{
  "color": "WHITE/PALE",
  "bill": "LONG STRAIGHT",
  "species": "GREG"
}
```

New system uses `neck` field:
```json
{
  "color": "WHITE/PALE",
  "neck": "VERY LONG NECK",
  "species": "GREG"
}
```

**Impact**: Existing labels with `bill` in decision_path will remain valid but represent the old system. New labels will use `neck`.

---

**Conclusion**: This is a **major UX improvement** based on the fundamental constraints of aerial photography. The decision tree now asks experts to identify features they can actually see, resulting in more accurate and confident species classifications.
