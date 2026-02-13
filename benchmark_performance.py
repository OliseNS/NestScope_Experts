#!/usr/bin/env python3
"""
Benchmark script to compare Fast Mode vs Standard Mode inference times
"""

from server.cv_tools.inference import BirdDetector
import time

def benchmark_inference():
    print("=" * 60)
    print("INFERENCE PERFORMANCE BENCHMARK")
    print("=" * 60)

    # Initialize detector
    detector = BirdDetector()

    # Test image
    test_image = "server/cv_tools/images/10 June 2010 Camera 1 Card 1 130.JPG"

    print(f"\nTest Image: {test_image}")

    from PIL import Image
    img = Image.open(test_image)
    print(f"Dimensions: {img.width}x{img.height} pixels")
    print(f"Model input size: {detector.imgsz}x{detector.imgsz}")

    # Calculate thresholds
    fast_threshold = detector.imgsz * 2  # 2048
    standard_threshold = detector.imgsz * 4  # 4096

    print(f"\nThresholds:")
    print(f"  Fast mode downsample: >{fast_threshold}px")
    print(f"  Standard mode downsample: >{standard_threshold}px")

    will_downsample_fast = img.width > fast_threshold or img.height > fast_threshold
    will_downsample_standard = img.width > standard_threshold or img.height > standard_threshold

    print(f"\nPredicted behavior:")
    print(f"  Fast mode: {'Downsample ⚡' if will_downsample_fast else 'Sliding window'}")
    print(f"  Standard mode: {'Downsample ⚡' if will_downsample_standard else 'Sliding window'}")

    print("\n" + "-" * 60)
    print("Running benchmarks...")
    print("-" * 60)

    # Test Fast Mode
    print("\n1️⃣  FAST MODE")
    print("   " + "─" * 50)
    start = time.perf_counter()
    result_fast = detector.predict(test_image, conf_threshold=0.25, fast_mode=True)
    fast_time = time.perf_counter() - start

    print(f"   ✓ Birds detected: {result_fast['bird_count']}")
    print(f"   ✓ Inference time: {fast_time:.2f}s")
    print(f"   ✓ Speed: {result_fast['bird_count'] / fast_time:.1f} birds/second")

    # Test Standard Mode
    print("\n2️⃣  STANDARD MODE (OPTIMIZED)")
    print("   " + "─" * 50)
    start = time.perf_counter()
    result_standard = detector.predict(test_image, conf_threshold=0.25, fast_mode=False)
    standard_time = time.perf_counter() - start

    print(f"   ✓ Birds detected: {result_standard['bird_count']}")
    print(f"   ✓ Inference time: {standard_time:.2f}s")
    print(f"   ✓ Speed: {result_standard['bird_count'] / standard_time:.1f} birds/second")

    # Comparison
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)

    print(f"\n{'Mode':<20} {'Time':<15} {'Birds':<10} {'Speed'}")
    print("-" * 60)
    print(f"{'Fast Mode':<20} {fast_time:<15.2f}s {result_fast['bird_count']:<10} {result_fast['bird_count']/fast_time:.1f} birds/s")
    print(f"{'Standard Mode':<20} {standard_time:<15.2f}s {result_standard['bird_count']:<10} {result_standard['bird_count']/standard_time:.1f} birds/s")
    print("-" * 60)

    if fast_time < standard_time:
        speedup = standard_time / fast_time
        print(f"\n⚡ Fast mode is {speedup:.1f}x faster")
    elif standard_time < fast_time * 0.9:
        speedup = fast_time / standard_time
        print(f"\n🎉 Standard mode is {speedup:.1f}x faster (unusual for large images)")
    else:
        print(f"\n✓ Both modes have similar performance (~{(fast_time + standard_time)/2:.2f}s)")

    count_diff = abs(result_fast['bird_count'] - result_standard['bird_count'])
    if count_diff == 0:
        print(f"✓ Detection count matches perfectly!")
    else:
        print(f"ℹ️  Detection count difference: {count_diff} birds ({count_diff / max(result_fast['bird_count'], 1) * 100:.1f}%)")

    print("\n" + "=" * 60)
    print("CONCLUSION")
    print("=" * 60)

    if standard_time < 10:
        print("✅ Standard mode is now optimized and performs well!")
        print("   Both modes complete in reasonable time.")
    elif standard_time > 20:
        print("⚠️  Standard mode is still slow. Consider:")
        print("   - Using batch processing")
        print("   - Implementing parallel window processing")
        print("   - Using GPU acceleration (CUDA/TensorRT)")
    else:
        print("✓ Standard mode performance is acceptable.")

    print()

if __name__ == "__main__":
    try:
        benchmark_inference()
    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()
