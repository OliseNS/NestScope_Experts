#!/usr/bin/env python3
"""
Diagnostic script for Nestperts installation.

Checks if all required dependencies and models are available.

Usage:
    python labeller/diagnose.py
"""

import os
import sys

def print_header(text):
    """Print a section header"""
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60)

def check_dependency(name, import_name=None):
    """Check if a Python package is installed"""
    if import_name is None:
        import_name = name.lower()

    try:
        module = __import__(import_name)

        # Try to get version (handle deprecation warnings)
        version = 'installed'
        try:
            # Try importlib.metadata first (modern way)
            import importlib.metadata
            version = importlib.metadata.version(name if name != 'OpenCV' else 'opencv-python')
        except:
            # Fallback to __version__ attribute
            try:
                if hasattr(module, '__version__'):
                    version = module.__version__
            except:
                pass

        print(f"  ✓ {name:20} {version}")
        return True
    except ImportError:
        print(f"  ✗ {name:20} NOT INSTALLED")
        return False

def check_file(path, name):
    """Check if a file exists"""
    if os.path.exists(path):
        size_mb = os.path.getsize(path) / (1024 * 1024)
        print(f"  ✓ {name:30} ({size_mb:.1f} MB)")
        return True
    else:
        print(f"  ✗ {name:30} MISSING")
        return False

def main():
    """Run diagnostics"""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    all_ok = True

    # Header
    print_header("Nestperts Installation Diagnostic")
    print(f"Project root: {project_root}")

    # Check Python version
    print_header("1. Python Version")
    print(f"  Python {sys.version.split()[0]}")
    if sys.version_info < (3, 8):
        print("  ⚠️  Warning: Python 3.8+ recommended")
        all_ok = False

    # Check dependencies
    print_header("2. Python Dependencies")
    deps_ok = True
    deps_ok &= check_dependency("Flask")
    deps_ok &= check_dependency("OpenCV", "cv2")
    deps_ok &= check_dependency("NumPy", "numpy")
    deps_ok &= check_dependency("ONNX Runtime", "onnxruntime")
    deps_ok &= check_dependency("Ultralytics", "ultralytics")
    deps_ok &= check_dependency("PyYAML", "yaml")

    if not deps_ok:
        print("\n  ⚠️  Missing dependencies. Install with:")
        print("     pip install flask opencv-python numpy onnxruntime ultralytics pyyaml")
        all_ok = False

    # Check models
    print_header("3. Model Files")
    models_dir = os.path.join(project_root, 'models')
    models_ok = True
    models_ok &= check_file(
        os.path.join(models_dir, 'classifier_swift.onnx'),
        'Species Classifier'
    )
    models_ok &= check_file(
        os.path.join(models_dir, 'mobile_sam.pt'),
        'Swift AI Segmentation'
    )
    models_ok &= check_file(
        os.path.join(models_dir, 'swift.onnx'),
        'Bird Detector (Swift)'
    )

    if not models_ok:
        print("\n  ⚠️  Some models are missing. Ensure all models are in the models/ directory.")
        all_ok = False

    # Check data files
    print_header("4. Data Files")
    data_ok = True
    data_ok &= check_file(
        os.path.join(project_root, 'labeller', 'data', 'species_list.json'),
        'Species List'
    )
    data_ok &= check_file(
        os.path.join(project_root, 'labeller', 'projects', 'users.json'),
        'User Registry'
    )

    if not data_ok:
        print("\n  ⚠️  Some data files are missing.")
        all_ok = False

    # Test classifier
    print_header("5. Classifier Test")
    try:
        sys.path.insert(0, project_root)
        from labeller.onnx_classifier import ONNXClassifier

        print("  Loading classifier...")
        classifier = ONNXClassifier()
        print("  ✓ Classifier loaded successfully")
        print(f"  ✓ Model has {classifier.num_classes} classes")
        print(f"  ✓ Using {classifier.session.get_providers()[0]}")
    except Exception as e:
        print(f"  ✗ Classifier test failed: {e}")
        all_ok = False

    # Test SAM
    print_header("6. Swift AI Test")
    try:
        from ultralytics import SAM
        sam_path = os.path.join(project_root, 'models', 'mobile_sam.pt')

        print("  Loading Swift AI...")
        sam = SAM(sam_path)
        print("  ✓ Swift AI loaded successfully")
        print(f"  ✓ Model ready for segmentation")
    except Exception as e:
        print(f"  ✗ Swift AI test failed: {e}")
        all_ok = False

    # Final summary
    print_header("Summary")
    if all_ok:
        print("  ✅ All checks passed!")
        print("  🚀 Nestperts is ready to use")
        print("\n  To start the server:")
        print("     cd labeller && python app.py")
        print("  Then open: http://localhost:5000")
    else:
        print("  ⚠️  Some issues detected")
        print("  Please fix the issues above before running Nestperts")

    print("=" * 60 + "\n")

    return 0 if all_ok else 1

if __name__ == '__main__':
    sys.exit(main())
