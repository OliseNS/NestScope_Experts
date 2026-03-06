#!/usr/bin/env python3
"""
Quick diagnostic script to test the mapping system layers
"""

import pandas as pd
import sys
sys.path.insert(0, '/home/olisemeka.dev/Projects/nexus')

from server.main import validate_and_enhance_sql_for_mapping, inject_coordinates_via_join

# Test SQL without coordinates
print("=== Testing Layer 2: SQL Enhancement ===\n")

test_sql = '''SELECT "ColonyName", SUM("Birds") as total_birds
FROM "tblColonyTotals2010-2021_MayJuneCombined"
GROUP BY "ColonyName"
LIMIT 10'''

print("Original SQL:")
print(test_sql)
print()

enhanced, modified, reason = validate_and_enhance_sql_for_mapping(test_sql)

print(f"Modified: {modified}")
print(f"Reason: {reason}")
print()
print("Enhanced SQL:")
print(enhanced)
print()

# Test coordinate injection
print("\n=== Testing Layer 3: Coordinate Injection ===\n")

test_df = pd.DataFrame({
    'ColonyName': ['Queen Bess Island', 'Rabbit Island', 'Sister Lake'],
    'Birds': [1000, 2000, 1500]
})

print("Original DataFrame:")
print(test_df)
print()

enriched_df = inject_coordinates_via_join(test_df, "data/bird_data_complete.db")

print("After coordinate injection:")
print(enriched_df)
print()

if 'Latitude' in enriched_df.columns and 'Longitude' in enriched_df.columns:
    print("✅ SUCCESS: Coordinates were injected!")
else:
    print("❌ FAILED: Coordinates not injected")
