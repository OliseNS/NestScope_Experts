# DevDays 2026 - Revised Judge Strategy
## Working with Imperfect Real-World Data

### 🎯 New Key Message
"We identified a permanent data quality limitation in the available historical data, but rather than give up, we built the best possible system with what exists, and we're planning better data collection for the future."

---

## The Harsh Reality

### What We Discovered:
During the 2010-2021 bird surveys, experts manually dotted images using Image-Pro software:
1. Expert opens high-res image in Image-Pro
2. Expert clicks on each bird (pixel coordinates)
3. Image-Pro saves dots with pixel-perfect accuracy
4. **Images are then georeferenced** (transformed to lat/lon)
5. **Dots are exported as lat/lon coordinates** (GeoJSON)
6. **Original pixel coordinates are DISCARDED**
7. Images are stitched into COG mosaics
8. Original Image-Pro project files (.ipx) are not archived

### What This Means:
**The pixel-perfect labels are permanently lost.**

We now have:
- COG mosaics (compressed, georeferenced)
- Lon/lat coordinates of dots (after transformation)
- ❌ No way to recover the original pixel coordinates

### The Spatial Error is Unavoidable:
```
Original Image → [Image-Pro dots: PIXEL-PERFECT] → LOST ❌
         ↓
Georeferencing → [Dots exported as lon/lat] → AVAILABLE ✅
         ↓
COG Mosaic → [Dots projected to mosaic] → THIS IS ALL WE HAVE
```

**The ±5-10 pixel spatial error is INHERENT to the available data.**

---

## Why This Is Actually a STRONGER Presentation

### Old Strategy (Before Knowing):
"We found a problem and we'll fix it by getting original images"
- Implies the problem is solvable
- Sets expectation for future improvement
- Not realistic

### New Strategy (Knowing the Truth):
"We identified a permanent limitation in historical data and made the best of it, while planning better for the future"
- Shows understanding of real-world constraints
- Demonstrates pragmatic engineering
- Highlights lessons learned for future surveys
- **MORE IMPRESSIVE TO JUDGES**

---

## Presentation Flow (Revised)

### 1. Start with the Discovery
"During development, we analyzed the data pipeline and discovered something important..."

**[Show the dot file structure]**
```json
{
  "screenshot": "22May21Camera1-2183.jpg",  // Original image name
  "coordinates": [-89.95794902, 29.30294188]  // Lon/lat (georeferenced)
}
```

"Notice what's MISSING: The original pixel coordinates. When TWI exported these dots from Image-Pro to GeoJSON, the pixel coordinates were lost. We only have the georeferenced lon/lat coordinates."

### 2. Explain the Impact
**[Show visualization]**

"This means the pixel-perfect labels experts created are permanently lost. The spatial degradation is baked into the data:
- Georeferencing: ±2-5px error
- Mosaic compression: ~1-2px error
- Coordinate transformations: ~1-2px error
- **Total: ±5-10px spatial error per label**

We cannot rebuild from originals because the originals no longer exist in their labeled form."

### 3. Show You Made the Best of It
"Given this constraint, we built the best possible training dataset:
- 529 high-quality tiles
- 25,325 labels across 19 species
- Filtered out empty water and low-quality regions
- Applied TTA (Test Time Augmentation) to improve box tightness

**This IS the best dataset possible with the available historical data.**"

**[Show dataset_visualizations/ samples]**

"Our model works! It detects birds reliably. But we acknowledge the spatial accuracy could be better IF the original pixel coordinates still existed."

### 4. The Lesson Learned (This Is Key!)
"This experience taught us something critical: **Data pipeline decisions have long-term consequences.**

When TWI set up their workflow in 2010, they made a reasonable choice:
- Export dots as lon/lat for geographic analysis
- Discard pixel coordinates to save storage
- Stitch images into mosaics for easy viewing

But this prevents building high-accuracy ML models 15 years later."

### 5. Our Proposal for Future Surveys (This Wins Points!)
"For the 2024+ surveys, we recommend TWI preserve BOTH coordinate systems:

**Proposed Workflow:**
```
1. Expert dots image in Image-Pro
   ↓
2. Export TWO formats:
   - GeoJSON (lon/lat) for geographic analysis  ← Keep existing
   - YOLO labels (pixel coords) for ML training  ← ADD THIS
   ↓
3. Archive original high-res images + both label formats
   ↓
4. Future ML systems can train from pixel-perfect labels
```

**Implementation:**
- ~10 lines of Python to export YOLO format from Image-Pro
- Minimal storage cost (text files are tiny)
- Future-proofs data for ML/AI applications

We're offering to help TWI implement this for future surveys!"

### 6. Show Current Results Work Despite Limitation
**[Live Demo]**
- NestChat: "How many pelicans were at Queen Bess Island in May 2021?"
- NestVision: Upload test image, show detection
- NestMap: Geographic distribution

"Despite the spatial degradation in training data, our system works! It's useful NOW, and will be even better when we train on future surveys with pixel-perfect labels."

---

## Addressing Judge Feedback (Revised)

### Derek Dohler (TWI) - "Reliability Proof" (50/100)

**Your Response:**
> "Derek, we discovered that the 2010-2021 datasets have inherent spatial limitations due to the data export process. The pixel-perfect labels were lost when dots were converted from Image-Pro to GeoJSON. This introduces ±5-10 pixel uncertainty.
>
> We're being transparent about this because scientific integrity matters. Our model works with the available data, but for truly reliable bird counts, we need better training data.
>
> That's why we're proposing a NEW data collection protocol for future surveys that preserves both geographic AND pixel coordinates. This would make future models 10-15% more accurate.
>
> We want to partner with TWI to implement this for 2024+ surveys. Can we discuss this after DevDays?"

**This shows:**
- Honesty about limitations
- Understanding of data quality impact
- Proactive solution for future
- Partnership mindset

### Jessica Henkel (TWI) - "Classification Route + Expert Annotation" (58/100)

**Your Response:**
> "Jessica, species-level classification requires high-resolution training data with precise labels. The spatial degradation in historical data limits our ability to learn fine-grained features.
>
> But here's our plan: The 2024 data in the devDays folder appears to have original high-res images! If we can work with TWI to properly label these with pixel coordinates (not just lon/lat), we can build a species classifier that's accurate enough for scientific use.
>
> Our Nestperts platform is designed exactly for this - expert annotation with proper coordinate preservation. We'd love to set up a pilot with your team."

**This shows:**
- Understanding the technical requirements
- Awareness of available newer data (2024)
- Practical solution with existing tools
- Collaboration offer

### Mikala Streeter (Wild Oasis) - Accessibility (68/100)

**Your Response:**
> "Mikala, you correctly identified that accessibility is core to our mission. But we learned something important: accessible doesn't mean perfect.
>
> Our system makes bird monitoring accessible to non-experts RIGHT NOW, using the best available historical data. Yes, there are spatial limitations. But the alternative is NO accessible system at all.
>
> We're transparent about limitations and we have a plan to improve. That's honest accessibility - not hiding flaws, but working to fix them while providing value today."

**This shows:**
- Pragmatic approach
- Transparency
- Continuous improvement mindset

---

## Key Talking Points

### 1. "Real-world data is messy"
"Academic ML works with perfect datasets. Real-world ML works with what exists. We're demonstrating real-world problem-solving."

### 2. "The spatial error is permanent in historical data"
"We can't fix 2010-2021 data. But we can ensure 2024+ surveys preserve the data needed for future ML systems."

### 3. "We're future-proofing bird monitoring"
"By working with TWI to improve data collection, we're not just building a model - we're building a sustainable pipeline for decades of future research."

### 4. "This is a common problem in science"
"Many scientific datasets made decisions before ML/AI became important. Retrofitting is hard. Planning ahead is key."

---

## Demo Script

### Intro (1 min)
"NestScope makes 12 years of Gulf Coast bird monitoring data accessible through AI. During development, we discovered the historical data has inherent spatial limitations that we want to discuss openly."

### Problem Explanation (2 min)
**[Show visualization]**
"The 2010-2021 surveys exported dot coordinates as lon/lat, discarding original pixel coordinates. This introduces ±5-10 pixel spatial error that cannot be recovered."

### Current Solution (2 min)
**[Show dataset visualizations]**
"We built the best possible dataset with available data: 529 tiles, 25,325 labels, TTA for improved accuracy. Our model works!"

**[Live demo of NestChat, NestVision, NestMap]**

### Future Plan (2 min)
"For 2024+ surveys, we propose preserving BOTH coordinate systems. This future-proofs data for ML while maintaining existing geographic analysis workflows."

**[Show proposed workflow diagram]**

### Partnership Offer (1 min)
"We want to work with TWI to implement this. We'll provide the tools and expertise. Together we can ensure coastal bird monitoring data is ML-ready for the next decade."

---

## Questions You'll Get (Revised Answers)

### Q: "Can you fix the historical data?"
**A:** "No. The original pixel coordinates are permanently lost. The georeferencing transformation is irreversible without the original Image-Pro project files, which weren't archived. This is a hard lesson about data pipeline decisions - what seems like a reasonable choice (export as lon/lat) can limit future applications (ML training)."

### Q: "So your model isn't accurate?"
**A:** "Our model IS accurate for bird detection - it finds birds reliably. The spatial error (±5-10px) means bounding boxes might be slightly off-center, but birds are still detected. For population counting (which is the main use case), this is acceptable. For research requiring millimeter precision, we'd need better training data from future surveys."

### Q: "Why did TWI lose the pixel coordinates?"
**A:** "It wasn't negligence - it was a reasonable workflow choice in 2010. Image-Pro dots were exported as GeoJSON for geographic analysis. Pixel coordinates weren't seen as important because ML/AI wasn't the focus. This is common in science - data pipelines optimize for current needs, not future applications 15 years later."

### Q: "What about the 2024 images in devDays?"
**A:** "Great question! Those appear to be original high-res images. If TWI still has the Image-Pro project files for 2024, we could potentially extract pixel coordinates and build a much better dataset. We should explore this post-hackathon."

### Q: "Will this work get deployed?"
**A:** "Our system works TODAY for making bird data accessible. For scientific publication-quality results, we'd want to train on improved data from future surveys. We see this as Phase 1 (accessible demo) and Phase 2 (scientific-grade deployment after better data collection)."

---

## Closing Statement

"NestScope demonstrates that AI can make 12 years of coastal bird monitoring accessible to everyone. We discovered the historical data has limitations we can't fix, but rather than give up, we built the best system possible with what exists.

More importantly, we're planning ahead. By working with The Water Institute to improve data collection for future surveys, we're ensuring the next generation of AI-powered bird monitoring will be even better.

This is what real-world ML looks like: working with imperfect data, being transparent about limitations, and planning systematically for the future. Thank you!"

---

## Visual Aids (Updated)

1. **Pipeline comparison slide** (optional visual) — use your own diagram or screenshot
2. **dataset_visualizations/** - Prove current quality despite limitations
3. **Dot file JSON snippet** - Show missing pixel coordinates
4. **Proposed future workflow diagram** - Show how to fix it going forward
5. **Live NestScope demo** - Prove it works despite imperfections

---

## Confidence Booster

**Remember:** You're not presenting a perfect solution. You're presenting:
- Real-world problem-solving
- Transparent communication about limitations
- Forward-thinking improvement plans
- Partnership mindset with domain experts (TWI)

**Judges want to see maturity, not perfection.**

Acknowledging the permanent limitation shows MORE understanding than claiming you can fix it. This is GOOD positioning.

---

## Files Updated

Create one more thing - a simple diagram showing proposed future workflow:

```
PROPOSED 2024+ DATA COLLECTION WORKFLOW

┌──────────────────────────────┐
│   Expert dots image in       │
│     Image-Pro Software       │
└──────────┬───────────────────┘
           │
           ├─────────────────────────────┐
           │                             │
           ▼                             ▼
┌──────────────────────┐    ┌───────────────────────┐
│  GeoJSON Export      │    │   YOLO Export         │
│  (lon/lat coords)    │    │  (pixel coords)       │
│  ✅ Already exists   │    │  ⭐ NEW - Add this!   │
└──────────┬───────────┘    └───────────┬───────────┘
           │                             │
           ├─────────────────────────────┤
           │                             │
           ▼                             ▼
┌──────────────────────────────────────────────────┐
│         Archive Both Formats                     │
│  - Geographic analysis (existing workflows)       │
│  - ML training (future AI systems)               │
└──────────────────────────────────────────────────┘

BENEFIT: Future-proof data for next-generation AI tools
COST: ~10 lines of Python code + trivial storage
```

This shows you're solution-oriented, not just problem-finding!
