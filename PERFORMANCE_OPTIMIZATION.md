# Performance Optimization Summary

## Problem
- **Fast Mode**: ~2 seconds inference ✓
- **Standard Mode**: 40+ seconds inference ✗

## Root Cause
Standard mode was using sliding windows (with no overlap) for ALL large images, creating 10-20+ windows that each required separate inference passes. This resulted in very slow processing for large images.

## Solution Implemented

### Smart Downsampling Thresholds
Modified `server/cv_tools/inference.py` to use intelligent downsampling based on image size:

| Image Size | Fast Mode | Standard Mode |
|------------|-----------|---------------|
| <2048px | Sliding window (64px overlap) | Sliding window (no overlap) |
| 2048-4096px | Downsample (single pass) | Sliding window (no overlap) |
| >4096px | Downsample (single pass) | Downsample (single pass) |

### Key Changes
1. **Lines 395-402**: Added dynamic threshold calculation
   - Fast mode: Uses downsampling for images >2048px
   - Standard mode: Uses downsampling for images >4096px

2. **Lines 510-517**: Applied same logic to `predict_from_bytes()`

3. **Updated docstrings**: Clarified the behavior of each mode

4. **Enhanced logging**: Better console output showing which mode is being used

## Expected Results

### Standard Mode Performance
- **Small images (<2048px)**: Maximum detail with sliding windows
- **Medium images (2048-4096px)**: Good balance of speed and accuracy
- **Large images (>4096px)**: Fast inference via downsampling (~2-5 seconds)

This should bring standard mode inference down from **40+ seconds to 2-10 seconds** for very large images!

## Testing
```python
from server.cv_tools.inference import BirdDetector

detector = BirdDetector()

# Test with fast mode
result_fast = detector.predict("large_image.jpg", fast_mode=True)
print(f"Fast mode: {result_fast['inference_time']:.2f}s")

# Test with standard mode (should be much faster now!)
result_standard = detector.predict("large_image.jpg", fast_mode=False)
print(f"Standard mode: {result_standard['inference_time']:.2f}s")
```

## Additional Optimization Options

### Option 2: Batch Processing (Future Enhancement)
Process multiple sliding windows in a single batch:
```python
# Process windows in batches of 4
batch_outputs = self.model.run(
    self.output_names,
    {self.input_name: np.stack([window1, window2, window3, window4])}
)
```
**Benefit**: Could reduce overhead and speed up sliding window mode by 2-3x

### Option 3: Parallel Window Processing (Future Enhancement)
Use `ThreadPoolExecutor` to process windows in parallel:
```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(self._process_window, window) for window in windows]
    results = [f.result() for f in futures]
```
**Benefit**: Could achieve 2-4x speedup on multi-core CPUs

### Option 4: Dynamic Overlap (Future Enhancement)
Start with no overlap, then increase if detections near edges:
- First pass: 0px overlap
- If detections within 100px of edge: Re-process with 128px overlap in that region
**Benefit**: Best of both worlds - speed + accuracy

### Option 5: TensorRT/CUDA Optimization
For production deployment with GPU:
- Use TensorRT execution provider
- Enable FP16 precision
**Benefit**: 5-10x speedup on GPU inference

## Recommendation
The current fix (smart downsampling thresholds) should resolve your 40-second issue. Monitor the results and consider implementing batch processing if you still need further optimization.
