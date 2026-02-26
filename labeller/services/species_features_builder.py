"""
Species Feature Database Builder

This script builds a numerical feature database for all Gulf Coast bird species.
The features are factual, measurable characteristics that enable Akinator-style
identification through probabilistic matching.

Educational Context:
------------------
This is inspired by Akinator's algorithm, which uses Bayesian probability to
narrow down possibilities. Each feature has a numerical value (0-1) representing
how strongly that feature applies to each species.

Example:
    "Is it white?"
    - Brown Pelican: 0.1 (mostly brown, some white)
    - Great Egret: 0.95 (almost entirely white)
    - Black Skimmer: 0.6 (white belly, black back)

This allows the system to ask smart questions and handle ambiguous answers.
"""

import json
import os
from typing import Dict, List, Tuple


class SpeciesFeatureDatabase:
    """
    Numerical feature database for bird species identification.

    Features are normalized to 0-1 scale:
        0.0 = Feature completely absent
        0.2 = Feature rarely present
        0.4 = Feature sometimes present
        0.6 = Feature usually present
        0.8 = Feature almost always present
        1.0 = Feature always present
    """

    def __init__(self):
        self.features = self._define_feature_schema()
        self.species_profiles = {}

    def _define_feature_schema(self) -> Dict:
        """
        Define all measurable features for bird identification.

        This schema represents factual, observable characteristics that
        experts use in field identification.
        """
        return {
            # PHYSICAL SIZE (relative to common reference points)
            "size_small": {
                "description": "Small bird (< 12 inches, sparrow to robin size)",
                "type": "continuous",
                "range": [0, 1]
            },
            "size_medium": {
                "description": "Medium bird (12-24 inches, crow to duck size)",
                "type": "continuous",
                "range": [0, 1]
            },
            "size_large": {
                "description": "Large bird (> 24 inches, goose to pelican size)",
                "type": "continuous",
                "range": [0, 1]
            },

            # BODY COLOR (dominant plumage colors)
            "color_white": {
                "description": "White or light colored plumage",
                "type": "continuous",
                "range": [0, 1]
            },
            "color_black": {
                "description": "Black or very dark plumage",
                "type": "continuous",
                "range": [0, 1]
            },
            "color_brown": {
                "description": "Brown plumage",
                "type": "continuous",
                "range": [0, 1]
            },
            "color_gray": {
                "description": "Gray plumage",
                "type": "continuous",
                "range": [0, 1]
            },
            "color_blue": {
                "description": "Blue or slate-colored plumage",
                "type": "continuous",
                "range": [0, 1]
            },
            "color_multicolored": {
                "description": "Multiple distinct colors (patterned)",
                "type": "continuous",
                "range": [0, 1]
            },

            # BILL CHARACTERISTICS
            "bill_long": {
                "description": "Long bill (relative to head size)",
                "type": "continuous",
                "range": [0, 1]
            },
            "bill_straight": {
                "description": "Straight bill shape",
                "type": "continuous",
                "range": [0, 1]
            },
            "bill_hooked": {
                "description": "Hooked or decurved bill",
                "type": "continuous",
                "range": [0, 1]
            },
            "bill_spatulate": {
                "description": "Spatula or spoon-shaped bill",
                "type": "continuous",
                "range": [0, 1]
            },
            "bill_pouched": {
                "description": "Bill with throat pouch",
                "type": "continuous",
                "range": [0, 1]
            },
            "bill_color_red": {
                "description": "Red or reddish bill",
                "type": "continuous",
                "range": [0, 1]
            },
            "bill_color_yellow": {
                "description": "Yellow or orange bill",
                "type": "continuous",
                "range": [0, 1]
            },
            "bill_color_black": {
                "description": "Black or dark bill",
                "type": "continuous",
                "range": [0, 1]
            },

            # LEG CHARACTERISTICS
            "legs_long": {
                "description": "Long legs (relative to body)",
                "type": "continuous",
                "range": [0, 1]
            },
            "legs_color_red": {
                "description": "Red or pink legs",
                "type": "continuous",
                "range": [0, 1]
            },
            "legs_color_yellow": {
                "description": "Yellow or orange legs",
                "type": "continuous",
                "range": [0, 1]
            },
            "legs_color_black": {
                "description": "Black or dark legs",
                "type": "continuous",
                "range": [0, 1]
            },

            # NECK CHARACTERISTICS
            "neck_long": {
                "description": "Long neck (egret/heron style)",
                "type": "continuous",
                "range": [0, 1]
            },
            "neck_s_shaped": {
                "description": "S-shaped neck when standing",
                "type": "continuous",
                "range": [0, 1]
            },

            # WING/TAIL PATTERNS
            "wings_dark_tips": {
                "description": "Dark wing tips (black on white bird)",
                "type": "continuous",
                "range": [0, 1]
            },
            "wings_patterned": {
                "description": "Distinct wing pattern or bars",
                "type": "continuous",
                "range": [0, 1]
            },
            "tail_forked": {
                "description": "Forked tail",
                "type": "continuous",
                "range": [0, 1]
            },

            # DISTINCTIVE FEATURES
            "has_crest": {
                "description": "Crest or plumes on head",
                "type": "continuous",
                "range": [0, 1]
            },
            "has_throat_pouch": {
                "description": "Visible throat pouch",
                "type": "continuous",
                "range": [0, 1]
            },

            # BEHAVIOR (observable in photos/field)
            "behavior_diving": {
                "description": "Dives underwater for food",
                "type": "continuous",
                "range": [0, 1]
            },
            "behavior_wading": {
                "description": "Wades in shallow water",
                "type": "continuous",
                "range": [0, 1]
            },
            "behavior_soaring": {
                "description": "Soars or glides frequently",
                "type": "continuous",
                "range": [0, 1]
            },
            "behavior_colonial": {
                "description": "Nests in large colonies",
                "type": "continuous",
                "range": [0, 1]
            },
            "behavior_ground_nesting": {
                "description": "Nests on ground",
                "type": "continuous",
                "range": [0, 1]
            },

            # HABITAT PREFERENCE
            "habitat_coastal": {
                "description": "Primarily coastal/beach habitat",
                "type": "continuous",
                "range": [0, 1]
            },
            "habitat_marsh": {
                "description": "Marsh or wetland habitat",
                "type": "continuous",
                "range": [0, 1]
            },
            "habitat_open_water": {
                "description": "Open water habitat",
                "type": "continuous",
                "range": [0, 1]
            },

            # RELATIVE ABUNDANCE (in Gulf Coast colonies)
            "abundance_common": {
                "description": "Common in Gulf Coast breeding colonies",
                "type": "continuous",
                "range": [0, 1]
            }
        }

    def add_species_profile(self, species_code: str, species_name: str, features: Dict[str, float]):
        """
        Add a species profile to the database.

        Args:
            species_code: 4-letter species code (e.g., "BRPE")
            species_name: Full species name (e.g., "Brown Pelican")
            features: Dict mapping feature names to values (0-1)
        """
        # Validate features
        for feature_name, value in features.items():
            if feature_name not in self.features:
                raise ValueError(f"Unknown feature: {feature_name}")
            if not 0 <= value <= 1:
                raise ValueError(f"Feature value must be 0-1, got {value}")

        self.species_profiles[species_code] = {
            "code": species_code,
            "name": species_name,
            "features": features
        }

    def calculate_match_score(self, species_code: str, observed_features: Dict[str, float]) -> float:
        """
        Calculate how well a species matches observed features.

        This uses a similarity scoring algorithm:
        - For each feature, calculate distance between observed and expected
        - Weight by feature importance
        - Return overall match score (0-1)

        Args:
            species_code: Species to check
            observed_features: Dict of observed features and their values

        Returns:
            Match score (0 = no match, 1 = perfect match)
        """
        if species_code not in self.species_profiles:
            return 0.0

        species = self.species_profiles[species_code]
        total_distance = 0
        num_features = 0

        for feature_name, observed_value in observed_features.items():
            if feature_name in species["features"]:
                expected_value = species["features"][feature_name]
                # Calculate squared distance (penalizes large differences more)
                distance = (observed_value - expected_value) ** 2
                total_distance += distance
                num_features += 1

        if num_features == 0:
            return 0.5  # No information, neutral score

        # Convert distance to similarity score
        avg_distance = total_distance / num_features
        similarity = 1 - avg_distance  # Since distance is squared, range is 0-1

        return max(0, min(1, similarity))  # Clamp to 0-1

    def rank_species(self, observed_features: Dict[str, float], top_n: int = 10) -> List[Tuple[str, float]]:
        """
        Rank all species by how well they match observed features.

        Args:
            observed_features: Dict of observed features
            top_n: Number of top matches to return

        Returns:
            List of (species_code, match_score) tuples, sorted by score
        """
        scores = []
        for species_code in self.species_profiles:
            score = self.calculate_match_score(species_code, observed_features)
            scores.append((species_code, score))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)

        return scores[:top_n]

    def get_most_discriminating_feature(self, candidate_species: List[str]) -> str:
        """
        Find the feature that best separates remaining candidate species.

        This is the key to smart questioning: ask about features that
        will eliminate the most candidates.

        Strategy:
        - For each feature, calculate variance across candidates
        - Higher variance = more discriminating
        - Return feature with highest variance

        Args:
            candidate_species: List of species codes still in consideration

        Returns:
            Feature name that best discriminates
        """
        if len(candidate_species) <= 1:
            return None

        feature_variances = {}

        for feature_name in self.features:
            values = []
            for species_code in candidate_species:
                if species_code in self.species_profiles:
                    features = self.species_profiles[species_code]["features"]
                    if feature_name in features:
                        values.append(features[feature_name])

            if len(values) > 1:
                # Calculate variance
                mean = sum(values) / len(values)
                variance = sum((x - mean) ** 2 for x in values) / len(values)
                feature_variances[feature_name] = variance

        if not feature_variances:
            return None

        # Return feature with highest variance
        return max(feature_variances, key=feature_variances.get)

    def save_to_json(self, filepath: str):
        """Save database to JSON file"""
        data = {
            "schema": self.features,
            "species": self.species_profiles
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"✓ Saved {len(self.species_profiles)} species profiles to {filepath}")

    def load_from_json(self, filepath: str):
        """Load database from JSON file"""
        with open(filepath, 'r') as f:
            data = json.load(f)

        self.features = data["schema"]
        self.species_profiles = data["species"]

        print(f"✓ Loaded {len(self.species_profiles)} species profiles from {filepath}")


if __name__ == "__main__":
    # Example usage
    db = SpeciesFeatureDatabase()

    # Example: Brown Pelican profile
    db.add_species_profile("BRPE", "Brown Pelican", {
        "size_large": 1.0,
        "color_brown": 0.8,
        "color_white": 0.3,
        "bill_long": 0.9,
        "bill_pouched": 1.0,
        "bill_color_yellow": 0.7,
        "neck_long": 0.6,
        "behavior_diving": 0.9,
        "behavior_colonial": 1.0,
        "habitat_coastal": 1.0,
        "abundance_common": 0.9
    })

    print("Feature schema defined with", len(db.features), "features")
    print("Example species added:", list(db.species_profiles.keys()))
