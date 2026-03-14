#!/usr/bin/env python3
"""Test if labeller app can be imported and started"""

import sys
import os

# Add labeller to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'labeller'))

print("Testing labeller app startup...")
print("=" * 60)

try:
    print("1. Testing imports...")
    from flask import Flask
    print("   ✓ Flask")

    from dotenv import load_dotenv
    print("   ✓ dotenv")

    load_dotenv()
    print("   ✓ Environment loaded")

    # Check required env vars
    required = ['GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET', 'SECRET_KEY',
                'TURSO_DATABASE_URL', 'TURSO_AUTH_TOKEN']
    for var in required:
        val = os.getenv(var)
        if val:
            print(f"   ✓ {var}: {val[:20]}...")
        else:
            print(f"   ✗ {var}: MISSING")

    print("\n2. Testing auth module...")
    from labeller import auth
    print("   ✓ Auth module imported")

    print("\n3. Testing main app import...")
    from labeller import app as labeller_app
    print("   ✓ App module imported")

    print("\n4. Checking app object...")
    app = labeller_app.app
    print(f"   ✓ App exists: {app}")
    print(f"   ✓ App name: {app.name}")

    print("\n5. Testing routes...")
    routes = [rule.rule for rule in app.url_map.iter_rules()]
    print(f"   ✓ {len(routes)} routes registered")
    print(f"   First few: {routes[:5]}")

    print("\n" + "=" * 60)
    print("✅ ALL CHECKS PASSED")
    print("\nApp should be ready to run on port 5000")
    print("Try: cd labeller && python app.py")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
