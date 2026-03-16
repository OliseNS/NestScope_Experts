/**
 * Client-Side ONNX Bird Detection
 * Runs inference entirely in the browser using ONNX Runtime Web
 */

class BirdDetector {
    constructor() {
        this.detectionSession = null;
        this.classifierSession = null;
        this.detectionInputName = null;
        this.classifierInputName = null;
        this.detectionOutputName = null;
        this.classifierOutputName = null;
        this.isLoading = false;
        this.isReady = false;

        // Species groups mapping
        this.speciesGroups = [
            'COLOR_WADER',
            'DARK',
            'GULL',
            'PELICAN',
            'SHOREBIRD',
            'TERN',
            'WHITE_WADER'
        ];

        // Colors for bounding boxes (matching backend)
        this.groupColors = {
            'PELICAN': [217, 119, 87],    // Claude orange
            'TERN': [59, 130, 246],       // Blue
            'GULL': [156, 163, 175],      // Gray
            'SHOREBIRD': [234, 179, 8],   // Yellow
            'DARK': [75, 85, 99],         // Dark gray
            'COLOR_WADER': [236, 72, 153], // Pink
            'WHITE_WADER': [229, 231, 235] // Light gray
        };
    }

    /**
     * Load ONNX models from server
     */
    async loadModels() {
        if (this.isLoading || this.isReady) return;

        this.isLoading = true;
        console.log('Loading ONNX models...');

        try {
            // Load ONNX Runtime Web
            if (typeof ort === 'undefined') {
                throw new Error('ONNX Runtime Web not loaded. Include: <script src="https://cdn.jsdelivr.net/npm/onnxruntime-web/dist/ort.min.js"></script>');
            }

            // Load detection model
            console.log('Loading detection model...');
            this.detectionSession = await ort.InferenceSession.create('/models/swift.onnx');
            this.detectionInputName = this.detectionSession.inputNames[0];
            this.detectionOutputName = this.detectionSession.outputNames[0];
            console.log(`✓ Detection model loaded (input: ${this.detectionInputName}, output: ${this.detectionOutputName})`);

            // Load classifier model
            console.log('Loading classifier model...');
            this.classifierSession = await ort.InferenceSession.create('/models/classifier_swift.onnx');
            this.classifierInputName = this.classifierSession.inputNames[0];
            this.classifierOutputName = this.classifierSession.outputNames[0];
            console.log(`✓ Classifier model loaded (input: ${this.classifierInputName}, output: ${this.classifierOutputName})`);

            this.isReady = true;
            this.isLoading = false;
            console.log('✓ All models ready');

            return true;
        } catch (error) {
            console.error('Failed to load models:', error);
            this.isLoading = false;
            throw error;
        }
    }

    /**
     * Preprocess image for detection (1024x1024)
     */
    preprocessDetection(imageData, targetSize = 1024) {
        const { width, height, data } = imageData;

        // Calculate scaling
        const scale = Math.min(targetSize / width, targetSize / height);
        const newWidth = Math.round(width * scale);
        const newHeight = Math.round(height * scale);

        // Create canvas for resizing
        const canvas = document.createElement('canvas');
        canvas.width = targetSize;
        canvas.height = targetSize;
        const ctx = canvas.getContext('2d');

        // Fill with gray background (114, 114, 114)
        ctx.fillStyle = 'rgb(114, 114, 114)';
        ctx.fillRect(0, 0, targetSize, targetSize);

        // Draw resized image (centered)
        const offsetX = (targetSize - newWidth) / 2;
        const offsetY = (targetSize - newHeight) / 2;

        // Get original image from ImageData
        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = width;
        tempCanvas.height = height;
        const tempCtx = tempCanvas.getContext('2d');
        tempCtx.putImageData(imageData, 0, 0);

        ctx.drawImage(tempCanvas, offsetX, offsetY, newWidth, newHeight);

        // Get processed image data
        const processedData = ctx.getImageData(0, 0, targetSize, targetSize);

        // Convert to CHW format and normalize to [0, 1]
        const float32Data = new Float32Array(3 * targetSize * targetSize);
        for (let i = 0; i < targetSize * targetSize; i++) {
            float32Data[i] = processedData.data[i * 4] / 255.0;                          // R
            float32Data[targetSize * targetSize + i] = processedData.data[i * 4 + 1] / 255.0;     // G
            float32Data[2 * targetSize * targetSize + i] = processedData.data[i * 4 + 2] / 255.0; // B
        }

        return {
            tensor: new ort.Tensor('float32', float32Data, [1, 3, targetSize, targetSize]),
            scale: scale,
            offsetX: offsetX,
            offsetY: offsetY
        };
    }

    /**
     * Apply Non-Maximum Suppression to remove duplicate detections
     */
    nms(boxes, scores, iouThreshold = 0.45) {
        const indices = [];
        const areas = boxes.map(box => (box[2] - box[0]) * (box[3] - box[1]));

        // Sort by score descending
        const order = scores
            .map((score, idx) => ({ score, idx }))
            .sort((a, b) => b.score - a.score)
            .map(item => item.idx);

        while (order.length > 0) {
            const i = order.shift();
            indices.push(i);

            const box1 = boxes[i];
            const remaining = [];

            for (const j of order) {
                const box2 = boxes[j];

                // Calculate IoU
                const x1 = Math.max(box1[0], box2[0]);
                const y1 = Math.max(box1[1], box2[1]);
                const x2 = Math.min(box1[2], box2[2]);
                const y2 = Math.min(box1[3], box2[3]);

                const w = Math.max(0, x2 - x1);
                const h = Math.max(0, y2 - y1);
                const inter = w * h;

                const iou = inter / (areas[i] + areas[j] - inter);

                if (iou <= iouThreshold) {
                    remaining.push(j);
                }
            }

            order.length = 0;
            order.push(...remaining);
        }

        return indices;
    }

    /**
     * Run detection inference
     */
    async detect(imageData, confThreshold = 0.25) {
        if (!this.isReady) {
            await this.loadModels();
        }

        console.log('Running detection inference...');
        const startTime = performance.now();

        // Preprocess
        const { tensor, scale, offsetX, offsetY } = this.preprocessDetection(imageData);

        // Run detection with dynamic input name
        const results = await this.detectionSession.run({ [this.detectionInputName]: tensor });

        // Get output - Format: [1, num_detections, 6]
        // 6 values: [x, y, x/w, y/h, confidence, class_id]
        const outputTensor = results[this.detectionOutputName];
        const output = outputTensor.data;
        const dims = outputTensor.dims;
        const numDetections = dims[1];
        const valuesPerDetection = dims[2]; // Should be 6

        console.log(`Model output shape: [${dims.join(', ')}]`);

        // Parse detections
        const rawBoxes = [];
        const rawScores = [];
        const rawClasses = [];

        for (let i = 0; i < numDetections; i++) {
            const offset = i * valuesPerDetection;
            const confidence = output[offset + 4];

            if (confidence < confThreshold) continue;

            const x1 = output[offset];
            const y1 = output[offset + 1];
            const x2 = output[offset + 2];
            const y2 = output[offset + 3];
            const classId = output[offset + 5];

            // Check if coordinates are in xywh format (need conversion)
            let box_x1, box_y1, box_x2, box_y2;
            if (x2 < x1 || y2 < y1) {
                // xywh format (center, width, height)
                const cx = x1, cy = y1, w = x2, h = y2;
                box_x1 = cx - w / 2;
                box_y1 = cy - h / 2;
                box_x2 = cx + w / 2;
                box_y2 = cy + h / 2;
            } else {
                // xyxy format (already corners)
                box_x1 = x1;
                box_y1 = y1;
                box_x2 = x2;
                box_y2 = y2;
            }

            // Scale back to original image coordinates
            const orig_x1 = (box_x1 - offsetX) / scale;
            const orig_y1 = (box_y1 - offsetY) / scale;
            const orig_x2 = (box_x2 - offsetX) / scale;
            const orig_y2 = (box_y2 - offsetY) / scale;

            rawBoxes.push([
                Math.max(0, orig_x1),
                Math.max(0, orig_y1),
                Math.min(imageData.width, orig_x2),
                Math.min(imageData.height, orig_y2)
            ]);
            rawScores.push(confidence);
            rawClasses.push(classId);
        }

        console.log(`Raw detections before NMS: ${rawBoxes.length}`);

        // Apply NMS to remove duplicate detections
        const keepIndices = this.nms(rawBoxes, rawScores, 0.45);

        console.log(`Detections after NMS: ${keepIndices.length}`);

        // Build final detections
        const detections = keepIndices.map(idx => ({
            bbox: rawBoxes[idx],
            confidence: rawScores[idx],
            class_id: rawClasses[idx]
        }));

        const inferenceTime = performance.now() - startTime;
        console.log(`✓ Detection complete: ${detections.length} birds in ${inferenceTime.toFixed(0)}ms`);

        return { detections, inferenceTime };
    }

    /**
     * Classify detected birds
     */
    async classify(imageData, detections) {
        console.log('Classifying detections...');

        for (const detection of detections) {
            // Extract bird region
            const [x1, y1, x2, y2] = detection.bbox;
            const birdWidth = x2 - x1;
            const birdHeight = y2 - y1;

            // Create canvas for bird region
            const canvas = document.createElement('canvas');
            canvas.width = 224;
            canvas.height = 224;
            const ctx = canvas.getContext('2d');

            // Draw bird region
            const tempCanvas = document.createElement('canvas');
            tempCanvas.width = imageData.width;
            tempCanvas.height = imageData.height;
            const tempCtx = tempCanvas.getContext('2d');
            tempCtx.putImageData(imageData, 0, 0);

            ctx.drawImage(tempCanvas, x1, y1, birdWidth, birdHeight, 0, 0, 224, 224);

            // Get image data and convert to tensor
            const cropData = ctx.getImageData(0, 0, 224, 224);
            const float32Data = new Float32Array(3 * 224 * 224);

            for (let i = 0; i < 224 * 224; i++) {
                float32Data[i] = cropData.data[i * 4] / 255.0;                    // R
                float32Data[224 * 224 + i] = cropData.data[i * 4 + 1] / 255.0;   // G
                float32Data[2 * 224 * 224 + i] = cropData.data[i * 4 + 2] / 255.0; // B
            }

            const tensor = new ort.Tensor('float32', float32Data, [1, 3, 224, 224]);

            // Run classification with dynamic input name
            const results = await this.classifierSession.run({ [this.classifierInputName]: tensor });
            const outputTensor = results[this.classifierOutputName];
            const scores = outputTensor.data;

            // Get best class
            let maxScore = -Infinity;
            let maxIdx = 0;
            for (let i = 0; i < scores.length; i++) {
                if (scores[i] > maxScore) {
                    maxScore = scores[i];
                    maxIdx = i;
                }
            }

            detection.species = this.speciesGroups[maxIdx];
            detection.species_confidence = maxScore;
        }

        console.log('✓ Classification complete');
        return detections;
    }

    /**
     * Draw detections on canvas
     */
    drawDetections(canvas, detections) {
        const ctx = canvas.getContext('2d');
        ctx.lineWidth = 3;
        ctx.font = '14px sans-serif';

        for (const detection of detections) {
            const [x1, y1, x2, y2] = detection.bbox;
            const species = detection.species || 'UNKNOWN';
            const color = this.groupColors[species] || [217, 119, 87];

            // Draw bounding box
            ctx.strokeStyle = `rgb(${color[0]}, ${color[1]}, ${color[2]})`;
            ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

            // Draw label background
            const label = species.replace('_', ' ');
            const textWidth = ctx.measureText(label).width;
            ctx.fillStyle = `rgba(${color[0]}, ${color[1]}, ${color[2]}, 0.8)`;
            ctx.fillRect(x1, y1 - 20, textWidth + 8, 20);

            // Draw label text
            ctx.fillStyle = 'white';
            ctx.fillText(label, x1 + 4, y1 - 6);
        }
    }

    /**
     * Run full inference pipeline
     */
    async infer(imageElement, confThreshold = 0.25) {
        const totalStart = performance.now();

        // Get image data
        const canvas = document.createElement('canvas');
        canvas.width = imageElement.naturalWidth || imageElement.width;
        canvas.height = imageElement.naturalHeight || imageElement.height;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(imageElement, 0, 0);
        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);

        // Run detection
        const { detections, inferenceTime: detectTime } = await this.detect(imageData, confThreshold);

        // Run classification
        await this.classify(imageData, detections);

        // Draw results
        this.drawDetections(canvas, detections);

        // Get annotated image
        const annotatedImage = canvas.toDataURL('image/jpeg', 0.95);

        // Calculate species summary
        const speciesSummary = {};
        for (const detection of detections) {
            const species = detection.species || 'UNKNOWN';
            speciesSummary[species] = (speciesSummary[species] || 0) + 1;
        }

        const totalTime = performance.now() - totalStart;

        return {
            bird_count: detections.length,
            detections: detections,
            species_summary: speciesSummary,
            annotated_image_base64: annotatedImage.split(',')[1], // Remove data:image/jpeg;base64,
            inference_time: totalTime / 1000, // Convert to seconds
            message: detections.length === 0 ? 'No birds detected' :
                     detections.length === 1 ? 'Detected 1 bird!' :
                     `Detected ${detections.length} birds!`
        };
    }
}

// Export for use in other scripts
window.BirdDetector = BirdDetector;
