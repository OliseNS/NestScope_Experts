"""
Expand Species Database to Include All 73 Codes

This script creates feature profiles for ALL species codes in the database:
- 39 real, identifiable species (full feature profiles)
- 8 combo codes (mapped to parent species features)
- 26 unknown/uncertain codes (category-level features)

Educational Context:
This demonstrates handling real-world data challenges: sometimes you can't
make a definitive identification, and that's okay! The system should support
uncertainty while still collecting useful data.
"""

import json
from pathlib import Path


def load_existing_profiles():
    """Load the 39 real species profiles we already researched"""
    profiles_path = Path(__file__).parent.parent / "data" / "species_feature_profiles.json"

    with open(profiles_path, 'r') as f:
        return json.load(f)


def create_combo_code_profile(combo_code, combo_name, parent_codes, real_species_db):
    """
    Create a profile for combo codes by averaging parent species features.

    Example: CARO (Caspian/Royal Tern) = average of CATE + ROYT features
    """
    # Get parent species
    parents = [real_species_db.get(code) for code in parent_codes if code in real_species_db]

    if not parents:
        return None

    # Average all features
    all_features = {}
    for parent in parents:
        for feature, value in parent.get('features', {}).items():
            if feature not in all_features:
                all_features[feature] = []
            all_features[feature].append(value)

    # Calculate averages
    averaged_features = {
        feature: sum(values) / len(values)
        for feature, values in all_features.items()
    }

    # Get average measurements
    avg_length = sum(p.get('length_inches', 0) for p in parents) / len(parents)
    avg_wingspan = sum(p.get('wingspan_inches', 0) for p in parents) / len(parents)

    # Combine field marks
    field_marks = []
    for parent in parents:
        field_marks.extend(parent.get('field_marks', [])[:2])  # Take top 2 from each

    # Add uncertainty note
    field_marks.insert(0, f"Could be either of: {' or '.join([p['name'] for p in parents])}")

    return {
        "code": combo_code,
        "name": combo_name,
        "type": "combo",
        "parent_species": parent_codes,
        "size_category": parents[0].get('size_category', 'medium'),
        "length_inches": round(avg_length, 1),
        "wingspan_inches": round(avg_wingspan, 1),
        "features": averaged_features,
        "field_marks": field_marks[:5],  # Limit to 5
        "reference_photos": []  # Combo codes don't have unique photos
    }


def create_unknown_category_profile(unknown_code, unknown_name, category_type):
    """
    Create a profile for unknown categories based on category type.

    Categories:
    - large_gull: Unknown large gull
    - small_tern: Unknown small tern
    - heron_egret: Unknown heron or egret
    - waterbird: Unknown waterbird (very generic)
    """
    category_features = {
        "large_gull": {
            "size_medium": 0.5,
            "size_large": 0.5,
            "color_white": 0.6,
            "color_gray": 0.4,
            "bill_hooked": 0.6,
            "habitat_coastal": 0.9,
            "behavior_colonial": 0.7
        },
        "small_tern": {
            "size_small": 0.7,
            "size_medium": 0.3,
            "color_white": 0.7,
            "wings_patterned": 0.5,
            "tail_forked": 0.6,
            "habitat_coastal": 0.9,
            "behavior_diving": 0.7
        },
        "large_tern": {
            "size_medium": 0.7,
            "size_large": 0.3,
            "color_white": 0.8,
            "bill_long": 0.7,
            "tail_forked": 0.7,
            "habitat_coastal": 0.9
        },
        "heron_egret": {
            "size_medium": 0.6,
            "size_large": 0.4,
            "color_white": 0.5,
            "neck_long": 0.9,
            "legs_long": 0.9,
            "bill_long": 0.8,
            "behavior_wading": 0.9,
            "habitat_marsh": 0.8
        },
        "night_heron": {
            "size_medium": 1.0,
            "color_gray": 0.5,
            "neck_long": 0.5,
            "legs_long": 0.6,
            "behavior_wading": 0.8,
            "habitat_marsh": 0.7
        },
        "ibis": {
            "size_medium": 0.7,
            "size_large": 0.3,
            "bill_long": 0.9,
            "bill_hooked": 0.8,
            "legs_long": 0.8,
            "behavior_wading": 0.9
        },
        "cormorant": {
            "size_medium": 0.5,
            "size_large": 0.5,
            "color_black": 0.8,
            "neck_long": 0.7,
            "behavior_diving": 1.0,
            "habitat_open_water": 0.9
        },
        "duck": {
            "size_small": 0.3,
            "size_medium": 0.7,
            "color_brown": 0.5,
            "behavior_diving": 0.6,
            "habitat_marsh": 0.7,
            "habitat_open_water": 0.7
        },
        "shorebird": {
            "size_small": 0.6,
            "size_medium": 0.4,
            "bill_long": 0.5,
            "legs_long": 0.7,
            "behavior_wading": 0.8,
            "habitat_coastal": 0.8
        },
        "waterbird_generic": {
            "size_medium": 0.5,
            "habitat_coastal": 0.6,
            "habitat_marsh": 0.5,
            "habitat_open_water": 0.5,
            "behavior_colonial": 0.5
        }
    }

    features = category_features.get(category_type, category_features["waterbird_generic"])

    return {
        "code": unknown_code,
        "name": unknown_name,
        "type": "unknown",
        "category": category_type,
        "size_category": "unknown",
        "length_inches": 0,
        "wingspan_inches": 0,
        "features": features,
        "field_marks": [
            "Unable to identify to species level",
            f"Classified as: {category_type.replace('_', ' ').title()}",
            "Consider: Image quality, viewing angle, molt stage"
        ],
        "reference_photos": []
    }


def build_complete_database():
    """Build database with all 73 species codes"""

    # Load existing real species (39 codes)
    real_species = load_existing_profiles()
    complete_db = real_species.copy()

    print(f"✓ Loaded {len(real_species)} real species profiles")

    # Add combo codes (8 codes)
    combo_definitions = [
        ("CARO", "Caspian/Royal Tern", ["CATE", "ROYT"]),
        ("FOCO", "Forster's/Common Tern", ["FOTE", "COTE"]),
        ("ROSA", "Royal or Sandwich Tern", ["ROYT", "SATE"]),
        ("SONO", "Sooty Tern or Brown Noddy", ["SOTE", "BRNO"]),
        ("TRSN", "Tricolored Heron or Snowy Egret", ["TRHE", "SNEG"]),
        ("UNCO", "Neotropic or Double-crested Cormorant", ["NECO", "DCCO"]),
        ("USTE", "Forster's and/or Gull-billed Tern", ["FOTE", "GBTE"]),
        ("WHEG", "Great/Snowy Egret", ["GREG", "SNEG"])
    ]

    for code, name, parents in combo_definitions:
        profile = create_combo_code_profile(code, name, parents, real_species)
        if profile:
            complete_db[code] = profile
            print(f"✓ Added combo code: {code} ({name})")

    # Add morph variants (treat like combos)
    complete_db["REEG DM"] = {
        **real_species["REEG"],
        "code": "REEG DM",
        "name": "Reddish Egret Dark Morph",
        "type": "morph",
        "parent_species": ["REEG"],
        "features": {
            **real_species["REEG"]["features"],
            "color_brown": 0.5,
            "color_gray": 0.4,
            "color_white": 0.1  # Dark morph has much less white
        }
    }

    complete_db["REEG WM"] = {
        **real_species["REEG"],
        "code": "REEG WM",
        "name": "Reddish Egret White Morph",
        "type": "morph",
        "parent_species": ["REEG"],
        "features": {
            **real_species["REEG"]["features"],
            "color_white": 0.95,  # White morph is almost entirely white
            "color_brown": 0.0,
            "color_gray": 0.05
        }
    }

    print(f"✓ Added 2 color morph variants")

    # Add unknown/uncertain categories (26 codes)
    unknown_definitions = [
        ("ULGU", "Unknown Large Gull", "large_gull"),
        ("ULTE", "Unknown Large Tern", "large_tern"),
        ("UNGU", "Unknown Gull", "large_gull"),
        ("UNTE", "Unknown Tern sp.", "small_tern"),
        ("UNGT", "Unknown Gull or Tern", "waterbird_generic"),
        ("UNEG", "Unknown Egret", "heron_egret"),
        ("UNHG", "Unknown Heron or Egret", "heron_egret"),
        ("SDHE", "Small Dark Heron/Egret", "heron_egret"),
        ("UNNH", "Unidentified Night Heron", "night_heron"),
        ("UNIB", "Unidentified Ibis", "ibis"),
        ("DAIB", "Glossy/White-faced Ibis", "ibis"),
        ("UNCO", "Unknown Cormorant", "cormorant"),
        ("UNDU", "Unknown Duck", "duck"),
        ("UNRA", "Unknown Rail", "shorebird"),
        ("UNSB", "Unknown Shorebird", "shorebird"),
        ("UNWA", "Unknown Waterbird", "waterbird_generic"),
        ("UNWW", "Unknown White Wader", "heron_egret"),
        ("WADE", "Wader sp.", "heron_egret"),
        ("UNCR", "Crow sp.", "waterbird_generic"),
        # Add these special codes
        ("ALL", "All breeding species occurring at this colony", "waterbird_generic"),
        ("AMCO", "American Coot", "duck"),
        ("CANG", "Canada Goose", "waterbird_generic"),
        ("COGA", "Common Gallinule", "duck"),
        ("FUWD", "Fulvous Whistling-Duck", "duck"),
        ("MODU", "Mottled Duck", "duck"),
    ]

    for code, name, category in unknown_definitions:
        profile = create_unknown_category_profile(code, name, category)
        complete_db[code] = profile
        print(f"✓ Added unknown category: {code} ({name})")

    print(f"\n✅ Complete database: {len(complete_db)} species codes")
    print(f"   - Real species: {len(real_species)}")
    print(f"   - Combo codes: {len([s for s in complete_db.values() if s.get('type') == 'combo'])}")
    print(f"   - Morph variants: {len([s for s in complete_db.values() if s.get('type') == 'morph'])}")
    print(f"   - Unknown categories: {len([s for s in complete_db.values() if s.get('type') == 'unknown'])}")

    return complete_db


def save_complete_database(db, output_path):
    """Save complete database to JSON"""
    with open(output_path, 'w') as f:
        json.dump(db, f, indent=2)

    print(f"\n✓ Saved complete database to: {output_path}")


if __name__ == "__main__":
    # Build complete database
    complete_db = build_complete_database()

    # Save to file
    output_path = Path(__file__).parent.parent / "data" / "species_feature_profiles_complete.json"
    save_complete_database(complete_db, output_path)

    # Also update the original file to keep them in sync
    profiles_path = Path(__file__).parent.parent / "data" / "species_feature_profiles.json"
    save_complete_database(complete_db, profiles_path)

    print("\n🎉 Database expansion complete!")
    print("The Akinator engine now supports all 73 species codes.")
