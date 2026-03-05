# Classifier Integration Guide

## ✅ What's Been Done

### 1. Model Conversion (COMPLETE)
- ✅ Converted `cls_swift.pt` → `classifier_swift.onnx` (6MB)
- ✅ Converted `cls_apex.pt` → `classifier_apex.onnx` (21MB)
- ✅ Both models output **25 Gulf Coast waterbird species**

### 2. Species Mapping (COMPLETE)
- ✅ Created `server/cv_tools/classifier_species.py`:
  - 25 species codes (AMOY, AWPE, BCNH, etc.)
  - Full species names (Brown Pelican, Laughing Gull, etc.)
  - Functional groups for color-coding (PELICAN, GULL, TERN, etc.)
  - Color mapping for visualization

### 3. Backend Inference (COMPLETE)
- ✅ Updated `server/cv_tools/inference.py`:
  - New `classify_crop()` method returns species info + top-k predictions
  - Updated `_classify_detections()` to add species data to each detection
  - Updated annotation drawing to show 4-letter species codes on boxes
  - Color-coded boxes by functional group

- ✅ Updated `server/config.yaml`:
  - Points to new ONNX classifiers

### 4. NestVision Frontend (COMPLETE)
- ✅ Updated `frontend/pages/02_nest_vision.py`:
  - Updated documentation to mention 25 species
  - Detection table shows: Species Code, Common Name, Classification Confidence, Group
  - Species breakdown chart still works (groups birds by species)

### 5. Nestperts Backend (COMPLETE)
- ✅ Added `/api/classify_crop` endpoint in `labeller/app.py`:
  - Takes image_name + bbox (YOLO format)
  - Returns top-5 species predictions with confidences
  - Uses same BirdDetector as NestVision

## 🔨 What Needs to be Added to Nestperts Frontend

### The Feature
When a user clicks on a bird detection in Nestperts, show:
1. AI-generated top-5 species predictions
2. Wikipedia bird images for each prediction
3. Confidence scores
4. Allow expert to accept/reject predictions

### Implementation Plan

#### Step 1: Add AI Classification Button
In `labeller/templates/expert_editor.html`, in the `showIdentificationChoice()` function, add a third button:

```javascript
// Add after the existing two buttons
<button class="btn-primary" style="width: 100%; margin-bottom: 0.75rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);" onclick="runAIClassification()">
    🤖 AI Classification
</button>
```

#### Step 2: Create `runAIClassification()` Function

```javascript
async function runAIClassification() {
    if (!selectedBoxId) return;

    const selectedBox = boxes.find(b => b.id === selectedBoxId);
    if (!selectedBox) return;

    const content = document.getElementById('classification-content');

    // Show loading state
    content.innerHTML = `
        <div class="classification-inner" style="text-align: center; padding: 2rem;">
            <div style="font-size: 2rem; margin-bottom: 1rem;">🤖</div>
            <h3>AI Classification Running...</h3>
            <p style="color: var(--text-secondary); margin-top: 0.5rem;">
                Analyzing bird features...
            </p>
        </div>
    `;

    try {
        // Call the classification API
        const response = await fetch('/api/classify_crop', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                image_name: "{{ image_name }}",  // Flask template variable
                bbox: {
                    x_center: selectedBox.x_center,
                    y_center: selectedBox.y_center,
                    width: selectedBox.width,
                    height: selectedBox.height
                },
                fast_mode: true  // Use Swift classifier for speed
            })
        });

        const result = await response.json();

        if (result.error) {
            throw new Error(result.error);
        }

        // Show top-5 predictions
        showAIPredictions(result.predictions);

    } catch (error) {
        console.error('Classification error:', error);
        content.innerHTML = `
            <div class="classification-inner" style="text-align: center; padding: 2rem;">
                <div style="font-size: 2rem; margin-bottom: 1rem;">❌</div>
                <h3>Classification Failed</h3>
                <p style="color: var(--text-secondary); margin-top: 0.5rem;">
                    ${error.message}
                </p>
                <button class="btn-secondary" style="margin-top: 1rem;" onclick="showIdentificationChoice()">
                    ← Try Another Method
                </button>
            </div>
        `;
    }
}
```

#### Step 3: Create `showAIPredictions()` Function

```javascript
async function showAIPredictions(predictions) {
    const content = document.getElementById('classification-content');
    const boxNumber = boxes.indexOf(boxes.find(b => b.id === selectedBoxId)) + 1;

    // Start building the HTML
    let html = `
        <div class="classification-inner">
            <h3 style="font-size: 1.25rem; margin-bottom: 0.5rem; color: var(--text-primary);">
                🤖 AI Predictions for Bird #${boxNumber}
            </h3>
            <p style="color: var(--text-secondary); margin-bottom: 1.5rem; font-size: 0.875rem;">
                Top 5 most likely species (click to select)
            </p>

            <div style="display: flex; flex-direction: column; gap: 1rem;">
    `;

    // Add each prediction as a card
    for (let i = 0; i < predictions.length; i++) {
        const pred = predictions[i];
        const rank = i + 1;
        const confidencePercent = (pred.confidence * 100).toFixed(1);

        html += `
            <div class="species-prediction-card" onclick="selectSpeciesFromAI('${pred.species_code}', '${pred.species_name}')"
                 style="background: var(--surface-light); border: 2px solid rgba(217, 119, 87, 0.2); border-radius: 8px; padding: 1rem; cursor: pointer; transition: all 0.3s;">

                <div style="display: flex; gap: 1rem; align-items: center;">
                    <!-- Rank badge -->
                    <div style="background: ${rank === 1 ? 'var(--orange-primary)' : 'var(--surface)'}; color: white; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; flex-shrink: 0;">
                        ${rank}
                    </div>

                    <!-- Species info -->
                    <div style="flex-grow: 1;">
                        <div style="font-weight: 700; color: var(--text-primary); font-size: 1rem; margin-bottom: 0.25rem;">
                            ${pred.species_name}
                        </div>
                        <div style="font-size: 0.875rem; color: var(--text-secondary);">
                            ${pred.species_code} • ${pred.group.replace('_', ' ').toLowerCase()}
                        </div>
                    </div>

                    <!-- Confidence -->
                    <div style="text-align: right; flex-shrink: 0;">
                        <div style="font-size: 1.5rem; font-weight: 700; color: ${confidencePercent > 70 ? '#7cb342' : confidencePercent > 40 ? 'var(--orange-primary)' : 'var(--text-muted)'};">
                            ${confidencePercent}%
                        </div>
                        <div style="font-size: 0.75rem; color: var(--text-muted);">
                            confidence
                        </div>
                    </div>
                </div>

                <!-- Bird image placeholder (will be loaded via Wikipedia API) -->
                <div id="bird-img-${pred.species_code}" style="margin-top: 1rem; display: flex; justify-content: center; min-height: 120px; background: var(--bg-dark); border-radius: 6px; overflow: hidden;">
                    <div style="display: flex; align-items: center; justify-content: center; color: var(--text-muted); font-size: 0.875rem;">
                        Loading image...
                    </div>
                </div>
            </div>
        `;
    }

    html += `
            </div>

            <button class="btn-secondary" style="margin-top: 1.5rem; width: 100%;" onclick="showIdentificationChoice()">
                ← Back to Options
            </button>
        </div>
    `;

    content.innerHTML = html;

    // Load Wikipedia images for each prediction
    predictions.forEach(pred => {
        loadBirdImage(pred.species_name, pred.species_code);
    });

    // Add hover effects via style
    const style = document.createElement('style');
    style.textContent = `
        .species-prediction-card:hover {
            transform: translateY(-2px);
            border-color: var(--orange-primary) !important;
            box-shadow: 0 4px 12px rgba(217, 119, 87, 0.3);
        }
    `;
    document.head.appendChild(style);
}
```

#### Step 4: Load Wikipedia Bird Images

```javascript
async function loadBirdImage(speciesName, speciesCode) {
    const container = document.getElementById(`bird-img-${speciesCode}`);
    if (!container) return;

    try {
        // Call the existing Wikipedia images API
        const response = await fetch(`/api/species/images/${encodeURIComponent(speciesName)}?max=1`);
        const data = await response.json();

        if (data.images && data.images.length > 0) {
            const imageUrl = data.images[0].url;
            container.innerHTML = `
                <img src="${imageUrl}"
                     style="width: 100%; height: 200px; object-fit: cover;"
                     onerror="this.parentElement.innerHTML='<div style=\\'padding: 1rem; color: var(--text-muted);\\'>Image not available</div>'" />
            `;
        } else {
            container.innerHTML = `
                <div style="padding: 1rem; color: var(--text-muted); font-size: 0.875rem;">
                    No image available
                </div>
            `;
        }
    } catch (error) {
        console.error(`Error loading image for ${speciesName}:`, error);
        container.innerHTML = `
            <div style="padding: 1rem; color: var(--text-muted); font-size: 0.875rem;">
                Image loading failed
            </div>
        `;
    }
}
```

#### Step 5: Select Species from AI Prediction

```javascript
function selectSpeciesFromAI(speciesCode, speciesName) {
    if (!selectedBoxId) return;

    const selectedBox = boxes.find(b => b.id === selectedBoxId);
    if (!selectedBox) return;

    // Assign species to the box
    selectedBox.species = speciesCode;

    // Save to backend
    saveLabels();

    // Show success message
    const content = document.getElementById('classification-content');
    content.innerHTML = `
        <div class="classification-inner" style="text-align: center; padding: 2rem;">
            <div style="font-size: 3rem; margin-bottom: 1rem;">✅</div>
            <h3 style="color: var(--success);">Species Assigned!</h3>
            <p style="color: var(--text-secondary); margin-top: 0.5rem; font-size: 1rem;">
                ${speciesName} (${speciesCode})
            </p>
            <button class="btn-primary" style="margin-top: 1.5rem;" onclick="closeClassificationPanel()">
                Continue Annotating
            </button>
        </div>
    `;

    // Update the canvas
    redrawCanvas();
}

function closeClassificationPanel() {
    selectedBoxId = null;
    updateBoxCount();
    redrawCanvas();
}
```

## 🎓 Educational Explanation

### What is Species Classification?

Think of it like a "reverse image search" for birds:

1. **Detection**: First, we find all birds in the image (bounding boxes)
2. **Cropping**: We cut out each bird from the image
3. **Classification**: We run the crop through a neural network trained on 25 species
4. **Top-K Predictions**: Instead of just one answer, we get the top 5 most likely species

### Why Top-5 Instead of Top-1?

Birds can look similar from aerial views! By showing the top 5 predictions:
- Experts can see alternative options if #1 seems wrong
- Builds trust (AI shows its uncertainty)
- Helps catch edge cases (juvenile birds, unusual angles, etc.)

### The Flow

```
User clicks bird → Extract bbox → Call /api/classify_crop → Get top-5 predictions
     ↓
Load Wikipedia images → Show predictions with confidence → Expert selects or rejects
```

### Model Architecture

The classifier is a **YOLOv8-cls** model:
- **Input**: 224×224 RGB image (the cropped bird)
- **Architecture**: CNN with residual connections
- **Output**: 25-class probability distribution (softmax)
- **Training**: Trained on expert-annotated Gulf Coast waterbird data

### Confidence Scores

Confidence = how sure the model is. For example:
- **85%** = Very confident (likely correct)
- **45%** = Uncertain (could be multiple species)
- **15%** = Low confidence (unusual bird or poor image quality)

## 🧪 Testing

### Test the Backend API:
```bash
# Start the backend
./run_app.sh

# In another terminal, test classification
curl -X POST http://localhost:5000/api/classify_crop \
  -H "Content-Type: application/json" \
  -d '{
    "image_name": "test_image.jpg",
    "bbox": {
      "x_center": 0.5,
      "y_center": 0.5,
      "width": 0.1,
      "height": 0.1
    },
    "fast_mode": true
  }'
```

Expected response:
```json
{
  "predictions": [
    {
      "species_code": "BRPE",
      "species_name": "Brown Pelican",
      "confidence": 0.856,
      "group": "PELICAN"
    },
    ...  // 4 more predictions
  ],
  "crop_size": [120, 95]
}
```

### Test NestVision:
1. Go to http://localhost:8501 (NestVision)
2. Upload a bird image or use example
3. Run detection
4. Check that:
   - Bounding boxes show 4-letter species codes (e.g., "BRPE")
   - Boxes are color-coded by functional group
   - Detection details table shows species info

## 📝 Summary

**Backend**: ✅ 100% Complete
- Models converted
- Classification integrated
- API endpoints ready

**Frontend (NestVision)**: ✅ 100% Complete
- Species display updated
- Detection table enhanced

**Frontend (Nestperts)**: ⏳ Needs Implementation
- Add the JavaScript code from this guide to `expert_editor.html`
- Test with real images
- Refine the UI based on user feedback

The hard work (model conversion, backend integration) is done! The Nestperts frontend just needs the UI code added to call the existing API and display results.
