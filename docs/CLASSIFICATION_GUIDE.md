# Bird Species Classification Guide

This guide explains how to train a classification model to identify bird species from aerial images after clustering.

## 📚 Table of Contents

1. [Overview](#overview)
2. [Recommended Models](#recommended-models)
3. [Training Workflow](#training-workflow)
4. [Model Comparison](#model-comparison)
5. [Implementation Examples](#implementation-examples)

---

## Overview

After clustering birds by visual similarity, you can train a supervised classification model to automatically identify species. This is a **two-stage approach**:

**Stage 1: Clustering** (Unsupervised)
- Groups similar-looking birds together
- Expert labels ~30-50 clusters (2-3 hours)
- All birds in a cluster get the same label

**Stage 2: Classification** (Supervised)
- Train model on cluster-labeled data
- Model learns species-specific features
- Can classify new unlabeled birds

---

## Recommended Models

### 🥇 **Option 1: EfficientNet (RECOMMENDED)**

**Best for:** Accuracy + Efficiency

**Why?**
- State-of-the-art performance with fewer parameters
- Pre-trained on ImageNet (transfer learning)
- Works well with small datasets (5,000-10,000 birds)
- Fast inference (30-50 FPS on CPU)

**Model Variants:**
- **EfficientNet-B0**: Smallest (5M params), fastest, 77% accuracy
- **EfficientNet-B1**: Medium (7M params), balanced
- **EfficientNet-B2**: Larger (9M params), more accurate

**Input size:** 224x224 or 260x260 pixels

**Training time:** 2-4 hours on GPU (50 epochs)

**Recommended for:**
- Production deployment
- Limited computational resources
- Best accuracy-to-efficiency ratio

---

### 🥈 **Option 2: ResNet-50**

**Best for:** Proven reliability

**Why?**
- Industry standard for image classification
- Well-documented, easy to use
- Pre-trained models readily available
- Good performance on fine-grained classification

**Specs:**
- 25M parameters
- Input: 224x224 pixels
- Training time: 3-5 hours on GPU

**Recommended for:**
- Academic research (widely cited)
- When you need reproducible results
- Transfer learning from bird datasets

---

### 🥉 **Option 3: Vision Transformer (ViT)**

**Best for:** Cutting-edge performance (if you have enough data)

**Why?**
- Latest architecture (attention-based)
- Potentially best accuracy
- Good for capturing global patterns

**Specs:**
- ViT-Base: 86M parameters
- Input: 224x224 pixels
- Training time: 5-8 hours on GPU

**Caveats:**
- Requires more data (10,000+ samples)
- Slower training and inference
- Higher memory usage

**Recommended for:**
- Research experiments
- Large datasets (50,000+ birds)
- GPU-rich environments

---

### 💡 **Option 4: MobileNetV3**

**Best for:** Edge deployment (mobile/embedded)

**Why?**
- Ultra-lightweight (5M params)
- Designed for mobile devices
- Fast inference on CPU

**Specs:**
- Input: 224x224 pixels
- Inference: 100+ FPS on CPU
- Training time: 1-2 hours on GPU

**Recommended for:**
- Mobile app deployment
- Real-time inference
- Resource-constrained devices

---

## Training Workflow

### Step 1: Prepare Data

**Extract bird crops:**
```bash
python scripts/extract_bird_crops.py --data labeller/nestvision --resize 224
```

This creates:
- `labeller/nestvision/bird_crops/` - Individual bird images (224x224)
- `labeller/nestvision/bird_crops/metadata.json` - Crop metadata

**Run clustering:**
```bash
python scripts/cluster_birds.py --data labeller/nestvision --clusters 30
```

This creates:
- `labeller/nestvision/clusters/` - Cluster data
- Cluster preview images for expert review

---

### Step 2: Label Clusters

**Open cluster explorer:**
```bash
python labeller/app.py --data labeller/nestvision
# Open http://localhost:5000/clusters
```

**Review each cluster:**
1. Look at preview images showing 20 representative birds
2. Identify dominant species (or group like "white egret sp.")
3. Assign species label with confidence level
4. Save progress

**Example labels:**
```
Cluster 0  → BRPE (Brown Pelican) - High confidence
Cluster 1  → AWPE (White Pelican) - High confidence
Cluster 2  → WHEG (White Egret sp.) - Medium confidence (can't distinguish Great vs Snowy)
Cluster 3  → ROTE (Royal Tern) - Medium confidence
...
```

---

### Step 3: Split Data

Split into training and validation sets:

**Option A: Random split (70/30)**
```python
from sklearn.model_selection import train_test_split

# Load metadata with cluster labels
crops = load_crops_with_labels('labeller/nestvision/bird_crops')

train_crops, val_crops = train_test_split(
    crops, test_size=0.3, stratify=crops['species'], random_state=42
)
```

**Option B: Image-level split (better for aerial data)**
```python
# Split by source image to avoid data leakage
images = get_unique_images(crops)
train_images, val_images = train_test_split(images, test_size=0.3)

train_crops = crops[crops['source_image'].isin(train_images)]
val_crops = crops[crops['source_image'].isin(val_images)]
```

---

### Step 4: Train Model

**Using PyTorch + timm library:**

```python
import torch
import timm
from torch.utils.data import DataLoader
from torchvision import transforms

# 1. Define transforms
train_transforms = transforms.Compose([
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(15),
    transforms.ColorJitter(brightness=0.2, contrast=0.2),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                        std=[0.229, 0.224, 0.225])
])

val_transforms = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                        std=[0.229, 0.224, 0.225])
])

# 2. Create datasets
train_dataset = BirdDataset(train_crops, transform=train_transforms)
val_dataset = BirdDataset(val_crops, transform=val_transforms)

train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
val_loader = DataLoader(val_dataset, batch_size=32)

# 3. Load pre-trained model
num_classes = len(unique_species)
model = timm.create_model('efficientnet_b0', pretrained=True, num_classes=num_classes)

# 4. Define training components
criterion = torch.nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=50)

# 5. Training loop
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model.to(device)

for epoch in range(50):
    # Training phase
    model.train()
    train_loss = 0.0
    correct = 0
    total = 0

    for images, labels in train_loader:
        images, labels = images.to(device), labels.to(device)

        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        train_loss += loss.item()
        _, predicted = outputs.max(1)
        correct += predicted.eq(labels).sum().item()
        total += labels.size(0)

    train_acc = 100.0 * correct / total

    # Validation phase
    model.eval()
    val_loss = 0.0
    correct = 0
    total = 0

    with torch.no_grad():
        for images, labels in val_loader:
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            loss = criterion(outputs, labels)

            val_loss += loss.item()
            _, predicted = outputs.max(1)
            correct += predicted.eq(labels).sum().item()
            total += labels.size(0)

    val_acc = 100.0 * correct / total

    print(f'Epoch {epoch+1}/50: Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.2f}%, '
          f'Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.2f}%')

    scheduler.step()

# 6. Save model
torch.save(model.state_dict(), 'models/bird_classifier_efficientnet.pth')
```

---

### Step 5: Evaluate Model

**Confusion Matrix:**
```python
from sklearn.metrics import confusion_matrix, classification_report
import seaborn as sns
import matplotlib.pyplot as plt

# Get predictions on validation set
model.eval()
all_preds = []
all_labels = []

with torch.no_grad():
    for images, labels in val_loader:
        images = images.to(device)
        outputs = model(images)
        _, predicted = outputs.max(1)
        all_preds.extend(predicted.cpu().numpy())
        all_labels.extend(labels.cpu().numpy())

# Confusion matrix
cm = confusion_matrix(all_labels, all_preds)
plt.figure(figsize=(12, 10))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
            xticklabels=species_names, yticklabels=species_names)
plt.title('Bird Species Classification Confusion Matrix')
plt.ylabel('True Species')
plt.xlabel('Predicted Species')
plt.savefig('confusion_matrix.png', dpi=150, bbox_inches='tight')

# Classification report
print(classification_report(all_labels, all_preds, target_names=species_names))
```

**Expected Results:**
- Overall accuracy: 70-85% (depends on cluster quality and species separability)
- Per-species accuracy varies:
  - **High** (>90%): Distinctive species (Brown Pelican, Roseate Spoonbill)
  - **Medium** (70-85%): Common species (White Pelican, gulls)
  - **Low** (<70%): Similar species (tern species, egret species)

---

## Model Comparison

| Model | Parameters | Accuracy | Speed (FPS) | Training Time | Memory | Best For |
|-------|-----------|----------|-------------|---------------|--------|----------|
| **EfficientNet-B0** | 5M | 77-82% | 40 | 2-3h | Low | ✅ Production |
| **EfficientNet-B1** | 7M | 79-84% | 35 | 3-4h | Low | ✅ Balanced |
| **ResNet-50** | 25M | 75-80% | 30 | 3-5h | Medium | Research |
| **MobileNetV3** | 5M | 72-78% | 100+ | 1-2h | Very Low | Mobile |
| **ViT-Base** | 86M | 82-88% | 15 | 5-8h | High | Research (big data) |

**Recommendation:** Start with **EfficientNet-B0** for best balance of accuracy and efficiency.

---

## Implementation Examples

### Full Training Script

See `scripts/train_classifier.py` for a complete training script with:
- Data loading and augmentation
- Model training with progress bars
- Validation and checkpointing
- Confusion matrix generation
- Model export to ONNX

**Run it:**
```bash
python scripts/train_classifier.py \
    --data labeller/nestvision/bird_crops \
    --model efficientnet_b0 \
    --epochs 50 \
    --batch-size 32 \
    --lr 0.001
```

---

### Integration with NestVision

After training, integrate the classifier with your bird detection pipeline:

**Updated workflow:**
1. YOLO detects birds → bounding boxes
2. Crop each bird
3. **Classification model identifies species** ← NEW!
4. Display results with species labels

**Code:**
```python
# In server/cv_tools/inference.py

class BirdDetector:
    def __init__(self):
        self.detector = load_yolo_model()  # Existing
        self.classifier = load_classifier()  # NEW

    def detect_and_classify(self, image):
        # Stage 1: Detection
        detections = self.detector(image)

        # Stage 2: Classification
        for det in detections:
            crop = image[det.y1:det.y2, det.x1:det.x2]
            species = self.classifier.predict(crop)
            det.species = species
            det.confidence = species.confidence

        return detections
```

---

## Tips for Better Accuracy

### 1. **Data Quality**
- Clean cluster labels (review uncertain ones)
- Balance species distribution (oversample rare species)
- Remove mislabeled outliers

### 2. **Data Augmentation**
```python
transforms.Compose([
    transforms.RandomHorizontalFlip(p=0.5),
    transforms.RandomVertation(15),
    transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2),
    transforms.RandomResizedCrop(224, scale=(0.8, 1.0)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])
```

### 3. **Class Weighting**
Handle imbalanced data:
```python
from sklearn.utils.class_weight import compute_class_weight

class_weights = compute_class_weight('balanced', classes=np.unique(labels), y=labels)
criterion = torch.nn.CrossEntropyLoss(weight=torch.tensor(class_weights).float())
```

### 4. **Ensemble Models**
Combine multiple models:
```python
predictions = (
    0.4 * efficientnet_pred +
    0.3 * resnet_pred +
    0.3 * vit_pred
)
```

### 5. **Test-Time Augmentation**
Average predictions over multiple augmented versions:
```python
def predict_tta(model, image, n_aug=5):
    preds = []
    for _ in range(n_aug):
        aug_image = apply_random_augmentation(image)
        pred = model(aug_image)
        preds.append(pred)
    return torch.stack(preds).mean(dim=0)
```

---

## Next Steps

1. **Extract bird crops:** `python scripts/extract_bird_crops.py --data labeller/nestvision`
2. **Run clustering:** `python scripts/cluster_birds.py --data labeller/nestvision --clusters 30`
3. **Label clusters:** Open http://localhost:5000/clusters and assign species
4. **Train classifier:** `python scripts/train_classifier.py --data labeller/nestvision/bird_crops`
5. **Evaluate:** Check confusion matrix and per-species accuracy
6. **Deploy:** Integrate with NestVision inference pipeline

---

## Questions?

- **"Which model should I use?"** → EfficientNet-B0 (best balance)
- **"How much data do I need?"** → 5,000-10,000 birds minimum (100+ per species)
- **"What accuracy can I expect?"** → 75-85% overall (varies by species)
- **"How long does training take?"** → 2-4 hours on GPU
- **"Can I use CPU?"** → Yes, but 10-20x slower

For more details, see the [PyTorch Image Classification Tutorial](https://pytorch.org/tutorials/beginner/transfer_learning_tutorial.html).
