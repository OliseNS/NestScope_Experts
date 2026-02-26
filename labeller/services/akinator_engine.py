"""
Akinator-Style Bird Identification Engine

This module implements a probabilistic question-asking system that narrows down
bird species through smart questioning, similar to the Akinator game.

Educational Context:
-------------------
This uses Bayesian-inspired reasoning:
1. Start with all species as candidates
2. Ask about the feature that best discriminates between candidates
3. Update probabilities based on answer
4. Repeat until high confidence in identification

The key insight: Don't just filter yes/no, use NUMERICAL matching!
User says "mostly white" (0.8) → Brown Pelican (0.3 white) scores lower than Great Egret (0.95 white)
"""

import json
from typing import Dict, List, Tuple, Optional
from pathlib import Path


class AkinatorEngine:
    """
    Probabilistic bird identification engine using numerical feature matching.
    """

    def __init__(self, species_db_path: str):
        """
        Args:
            species_db_path: Path to species feature profiles JSON
        """
        self.species_db_path = Path(species_db_path)
        self.species_db = self._load_species_db()
        self.session_state = None

    def _load_species_db(self) -> Dict:
        """Load species feature database"""
        if not self.species_db_path.exists():
            raise FileNotFoundError(
                f"Species database not found at {self.species_db_path}\n"
                "Run species research first to generate this file."
            )

        with open(self.species_db_path, 'r') as f:
            data = json.load(f)

        # Handle nested structure with "species" key
        if "species" in data and isinstance(data["species"], dict):
            return data["species"]

        # Handle flat structure (backwards compatibility)
        return data

    def start_session(self, available_species: Optional[List[str]] = None):
        """
        Start a new identification session.

        Args:
            available_species: Optional list of species codes to consider.
                             If None, considers all species in database.
        """
        if available_species is None:
            available_species = list(self.species_db.keys())

        self.session_state = {
            "candidates": available_species,  # Species still possible
            "observed_features": {},  # User's answers so far
            "questions_asked": [],  # Track what we've asked
            "confidence_scores": {},  # Current match scores for each species
            "question_history": []  # Full history for review
        }

        # Calculate initial scores (all equal)
        self._update_confidence_scores()

    def _update_confidence_scores(self):
        """
        Calculate match scores for all candidates based on observed features.

        This is the CORE algorithm: How well does each species match what we've seen?
        """
        scores = {}

        for species_code in self.session_state["candidates"]:
            if species_code not in self.species_db:
                continue

            species = self.species_db[species_code]
            species_features = species.get("features", {})

            # Calculate match score
            if not self.session_state["observed_features"]:
                # No observations yet, all species equally likely
                scores[species_code] = 1.0
            else:
                # Calculate similarity for each observed feature
                total_distance = 0
                num_features = 0

                for feature_name, observed_value in self.session_state["observed_features"].items():
                    if feature_name in species_features:
                        expected_value = species_features[feature_name]
                        # Squared distance (penalizes large mismatches)
                        distance = (observed_value - expected_value) ** 2
                        total_distance += distance
                        num_features += 1

                # Convert distance to similarity score
                if num_features > 0:
                    avg_distance = total_distance / num_features
                    # Similarity = 1 - distance, scaled to 0-1
                    similarity = max(0, 1 - avg_distance)
                    scores[species_code] = similarity
                else:
                    scores[species_code] = 0.5  # No matching features, neutral

        self.session_state["confidence_scores"] = scores

    def get_next_question(self) -> Optional[Dict]:
        """
        Get the next best question to ask.

        Strategy: Ask about the feature that best DISCRIMINATES between
        remaining candidates (highest variance).

        Returns:
            Question dict with:
            - feature: Feature name to ask about
            - question_text: Human-readable question
            - answer_options: List of answer choices with values
            - candidates_remaining: Number of species still possible
        """
        if not self.session_state["candidates"]:
            return None

        # If only one candidate left, we're done!
        if len(self.session_state["candidates"]) == 1:
            return None

        # Find most discriminating feature
        best_feature = self._find_most_discriminating_feature()

        if best_feature is None:
            # No more discriminating features, show results
            return None

        # Build question
        question = self._build_question_for_feature(best_feature)
        question["candidates_remaining"] = len(self.session_state["candidates"])

        return question

    def _find_most_discriminating_feature(self) -> Optional[str]:
        """
        Find the feature that best separates remaining candidates.

        Uses variance as the discrimination metric: higher variance means
        the feature varies a lot across candidates, making it useful for filtering.
        """
        candidates = self.session_state["candidates"]
        asked_features = self.session_state["questions_asked"]

        feature_variances = {}

        # Features to skip (unreliable in photos)
        SKIP_FEATURES = {
            "size_small", "size_medium", "size_large",  # Size is ambiguous without reference
        }

        # Get all possible features from species database
        all_features = set()
        for species_code in candidates:
            if species_code in self.species_db:
                all_features.update(self.species_db[species_code].get("features", {}).keys())

        # Calculate variance for each feature across candidates
        for feature_name in all_features:
            # Skip if already asked
            if feature_name in asked_features:
                continue

            # Skip unreliable features
            if feature_name in SKIP_FEATURES:
                continue

            values = []
            for species_code in candidates:
                if species_code in self.species_db:
                    features = self.species_db[species_code].get("features", {})
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

    def _build_question_for_feature(self, feature_name: str) -> Dict:
        """
        Build a human-readable question for a feature.

        Maps technical feature names to natural language questions with
        multiple choice answers.
        """
        # Question templates
        # NOTE: Size questions removed - photos don't convey size reliably
        # without reference objects or known distance
        question_templates = {
            # Color questions
            "color_white": {
                "text": "How much WHITE is on the bird?",
                "options": [
                    {"label": "Entirely or mostly white", "value": 0.9},
                    {"label": "Quite a bit of white", "value": 0.7},
                    {"label": "Some white patches", "value": 0.4},
                    {"label": "Little to no white", "value": 0.1},
                    {"label": "Not sure", "value": 0.5}
                ]
            },
            "color_black": {
                "text": "How much BLACK is on the bird?",
                "options": [
                    {"label": "Entirely or mostly black", "value": 0.9},
                    {"label": "Quite a bit of black", "value": 0.7},
                    {"label": "Some black areas", "value": 0.4},
                    {"label": "Little to no black", "value": 0.1},
                    {"label": "Not sure", "value": 0.5}
                ]
            },
            "color_brown": {
                "text": "How much BROWN is on the bird?",
                "options": [
                    {"label": "Entirely or mostly brown", "value": 0.9},
                    {"label": "Quite a bit of brown", "value": 0.7},
                    {"label": "Some brown areas", "value": 0.4},
                    {"label": "Little to no brown", "value": 0.1},
                    {"label": "Not sure", "value": 0.5}
                ]
            },

            # Bill questions
            "bill_long": {
                "text": "How long is the bill (relative to head size)?",
                "options": [
                    {"label": "Very long (longer than head)", "value": 0.9},
                    {"label": "Long (about same as head)", "value": 0.7},
                    {"label": "Medium length", "value": 0.5},
                    {"label": "Short", "value": 0.2},
                    {"label": "Not sure", "value": 0.5}
                ]
            },
            "bill_hooked": {
                "text": "What shape is the bill?",
                "options": [
                    {"label": "Strongly hooked/curved down", "value": 0.9},
                    {"label": "Slightly hooked", "value": 0.5},
                    {"label": "Straight", "value": 0.1},
                    {"label": "Not sure", "value": 0.5}
                ]
            },
            "bill_spatulate": {
                "text": "Is the bill spoon or spatula-shaped?",
                "options": [
                    {"label": "Yes, definitely spoon-shaped", "value": 1.0},
                    {"label": "Slightly flattened/wide", "value": 0.5},
                    {"label": "No, normal bill", "value": 0.0},
                    {"label": "Not sure", "value": 0.5}
                ]
            },

            # Leg questions
            "legs_long": {
                "text": "How long are the legs (relative to body)?",
                "options": [
                    {"label": "Very long (wading bird style)", "value": 0.9},
                    {"label": "Long", "value": 0.7},
                    {"label": "Medium", "value": 0.5},
                    {"label": "Short", "value": 0.2},
                    {"label": "Not sure", "value": 0.5}
                ]
            },
            "legs_color_red": {
                "text": "What color are the legs?",
                "options": [
                    {"label": "Red or pink", "value": 1.0, "feature_values": {"legs_color_red": 1.0, "legs_color_yellow": 0.0, "legs_color_black": 0.0}},
                    {"label": "Yellow or orange", "value": 0.0, "feature_values": {"legs_color_red": 0.0, "legs_color_yellow": 1.0, "legs_color_black": 0.0}},
                    {"label": "Black or dark gray", "value": 0.0, "feature_values": {"legs_color_red": 0.0, "legs_color_yellow": 0.0, "legs_color_black": 1.0}},
                    {"label": "Not sure / Can't see", "value": 0.5, "feature_values": {}}
                ]
            },

            # Neck questions
            "neck_long": {
                "text": "How long is the neck?",
                "options": [
                    {"label": "Very long (egret/heron style)", "value": 0.9},
                    {"label": "Long", "value": 0.7},
                    {"label": "Medium", "value": 0.5},
                    {"label": "Short", "value": 0.2},
                    {"label": "Not sure", "value": 0.5}
                ]
            },

            # Behavior questions
            "behavior_diving": {
                "text": "Does the bird dive underwater?",
                "options": [
                    {"label": "Yes, frequently dives", "value": 0.9},
                    {"label": "Sometimes dives", "value": 0.5},
                    {"label": "No, doesn't dive", "value": 0.1},
                    {"label": "Can't tell from photo", "value": 0.5}
                ]
            },
            "behavior_wading": {
                "text": "Does the bird wade in shallow water?",
                "options": [
                    {"label": "Yes, typical wading bird", "value": 0.9},
                    {"label": "Sometimes wades", "value": 0.5},
                    {"label": "No, doesn't wade", "value": 0.1},
                    {"label": "Can't tell from photo", "value": 0.5}
                ]
            }
        }

        # Get template or create generic question
        if feature_name in question_templates:
            template = question_templates[feature_name]
        else:
            # Generic question for unmapped features
            template = {
                "text": f"About feature '{feature_name}':",
                "options": [
                    {"label": "Yes / High", "value": 0.9},
                    {"label": "Somewhat / Medium", "value": 0.5},
                    {"label": "No / Low", "value": 0.1},
                    {"label": "Not sure", "value": 0.5}
                ]
            }

        return {
            "feature": feature_name,
            "question_text": template["text"],
            "answer_options": template["options"]
        }

    def answer_question(self, feature_name: str, answer_value: float,
                       additional_features: Optional[Dict[str, float]] = None):
        """
        Record an answer and update probabilities.

        Args:
            feature_name: The feature being answered
            answer_value: The numerical value (0-1)
            additional_features: Optional additional features to set (e.g., when answering
                               "leg color" we set all three color features at once)
        """
        # Record the answer
        self.session_state["observed_features"][feature_name] = answer_value

        # Add any additional features (for multi-feature answers)
        if additional_features:
            self.session_state["observed_features"].update(additional_features)

        # Mark feature as asked
        if feature_name not in self.session_state["questions_asked"]:
            self.session_state["questions_asked"].append(feature_name)

        # Record in history
        self.session_state["question_history"].append({
            "feature": feature_name,
            "value": answer_value,
            "additional": additional_features or {}
        })

        # Update confidence scores
        self._update_confidence_scores()

        # Filter candidates below threshold
        self._filter_low_probability_candidates()

    def _filter_low_probability_candidates(self, threshold: float = 0.2):
        """
        Remove species with very low probability matches.

        This gradually narrows the candidate list as we gather more information.
        """
        scores = self.session_state["confidence_scores"]

        # Keep only species above threshold
        self.session_state["candidates"] = [
            species for species in self.session_state["candidates"]
            if scores.get(species, 0) >= threshold
        ]

    def get_top_candidates(self, n: int = 5) -> List[Dict]:
        """
        Get top N most likely species.

        Returns:
            List of dicts with species info and confidence score
        """
        # Use Wikimedia Commons API for images (more reliable and open)
        from labeller.services.wikimedia_images import get_species_images, get_similar_species_images
        from labeller.services.reference_images_complete import get_reference_images

        scores = self.session_state["confidence_scores"]

        # Sort by score
        ranked = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # Build result list
        results = []
        for species_code, score in ranked[:n]:
            if species_code in self.species_db:
                species_data = self.species_db[species_code]

                # Fetch images from Wikimedia Commons (10 photos per species)
                reference_photos = get_species_images(species_code, limit=10)

                # Get similar species for visual comparison (Pinterest-style)
                similar_species = get_similar_species_images(species_code, images_per_species=3)

                # Get eBird/guide links
                references = get_reference_images(species_code)

                results.append({
                    "code": species_code,
                    "name": species_data.get("name", species_code),
                    "confidence": round(score * 100, 1),  # Convert to percentage
                    "field_marks": species_data.get("field_marks", []),
                    "reference_photos": reference_photos,  # Wikimedia Commons images
                    "similar_species": similar_species,  # For visual comparison
                    "ebird_link": references.get("ebird", ""),
                    "guide_link": references.get("guide", "")
                })

        return results

    def should_show_results(self) -> bool:
        """
        Determine if we should show final results.

        Criteria:
        - Only 1 candidate left (100% certain)
        - Top candidate has > 80% confidence
        - Asked 5+ questions and top candidate is clearly ahead
        """
        if len(self.session_state["candidates"]) == 0:
            return True  # No candidates (shouldn't happen, but handle it)

        if len(self.session_state["candidates"]) == 1:
            return True  # Only one option left

        scores = list(self.session_state["confidence_scores"].values())
        if not scores:
            return False

        top_score = max(scores)

        # High confidence in one species
        if top_score > 0.8:
            return True

        # Asked enough questions and have clear leader
        if len(self.session_state["questions_asked"]) >= 5:
            if len(scores) > 1:
                second_score = sorted(scores, reverse=True)[1]
                gap = top_score - second_score
                if gap > 0.3:  # Clear leader
                    return True

        return False


if __name__ == "__main__":
    # Example usage
    print("Akinator Engine - Example Usage")
    print("=" * 50)

    # This will fail until species database is built
    try:
        engine = AkinatorEngine("labeller/data/species_feature_profiles.json")
        engine.start_session()

        # Simulate answering questions
        question = engine.get_next_question()
        if question:
            print(f"\nQ: {question['question_text']}")
            print(f"Candidates remaining: {question['candidates_remaining']}")

    except FileNotFoundError as e:
        print(f"\n⚠️  {e}")
        print("Run the species research agent first to build the database.")
