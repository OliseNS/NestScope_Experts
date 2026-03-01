"""
Master Orchestrator: Ground-Truth-Anchored Species Classification Pipeline

Pipeline stages:
  1. Generate Embeddings    — EfficientNet features for all 100K crops
  2. Ground Truth Prototypes — Build clean species prototypes from single-species images
  3+4. Classify & Refine     — Hungarian matching + iterative cross-reference refinement
  5. Export                  — Final labels, quality report, frontend visualization

Key improvements over v1:
  - Hungarian algorithm for optimal cluster-to-species matching (was random)
  - Ground truth anchoring from single-species images
  - Iterative refinement with cascading species coverage
  - Per-crop outlier rejection at every stage
  - Accuracy over completeness (excludes ambiguous crops)
"""

import sys
from pathlib import Path
import json
import argparse
from datetime import datetime
import time

# Add project root to path (handles both direct execution and imports)
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from data.weak_supervision.pipeline.stage1_generate_embeddings import EmbeddingGenerator
from data.weak_supervision.pipeline.stage2_ground_truth_prototypes import GroundTruthBuilder
from data.weak_supervision.pipeline.stage4_cross_reference import CrossReferenceValidator
from data.weak_supervision.pipeline.stage5_export import QualityExporter


class PipelineOrchestrator:
    """
    Manages the complete ground-truth-anchored species classification pipeline.

    Provides:
    - Stage execution with dependency checking
    - Resume support (skip completed stages)
    - Progress tracking and logging
    """

    STAGE_NAMES = {
        1: "Generate Embeddings",
        2: "Ground Truth Prototypes",
        3: "Classify & Refine (iterative)",
        4: "Export & Quality Report",
    }

    def __init__(self, crops_dir: str, model: str = 'efficientnet',
                 image_metadata_path: str = None):
        """
        Args:
            crops_dir: Path to bird_crops directory
            model: Embedding model to use
            image_metadata_path: Path to image_metadata.json
        """
        self.crops_dir = Path(crops_dir)
        self.model = model

        # Resolve image_metadata path
        if image_metadata_path:
            self.image_metadata_path = str(image_metadata_path)
        else:
            self.image_metadata_path = str(
                self.crops_dir.parent / "image_metadata.json"
            )

        # Define output paths
        self.embeddings_dir = self.crops_dir / "embeddings"
        self.ground_truth_dir = self.crops_dir / "ground_truth"
        self.assignments_dir = self.crops_dir / "assignments"
        self.export_dir = self.crops_dir / "export"

        # State tracking
        self.state_file = self.crops_dir / "pipeline_state.json"
        self.state = self._load_state()

    def _load_state(self) -> dict:
        """Load pipeline state from file."""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                return json.load(f)
        return {
            "completed_stages": [],
            "last_run": None,
            "model": None,
            "pipeline_version": "v2_ground_truth_anchored"
        }

    def _save_state(self):
        """Save pipeline state to file."""
        self.state["last_run"] = datetime.now().isoformat()
        self.state["model"] = self.model
        self.state["pipeline_version"] = "v2_ground_truth_anchored"
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)

    def check_stage_dependencies(self, stage: int) -> tuple:
        """
        Verify that required files exist for a stage.

        Returns:
            (ready: bool, missing: list of missing file descriptions)
        """
        if stage == 1:
            required = [
                (self.crops_dir / "metadata.json", "crop metadata"),
                (self.crops_dir / "images", "crop images directory"),
            ]
        elif stage == 2:
            required = [
                (self.embeddings_dir / "embeddings_all.npy", "embeddings from Stage 1"),
                (self.embeddings_dir / "embeddings_index.json", "embedding index from Stage 1"),
                (Path(self.image_metadata_path), "image metadata"),
            ]
        elif stage == 3:
            required = [
                (self.ground_truth_dir / "prototypes.json", "prototypes from Stage 2"),
                (self.embeddings_dir / "embeddings_all.npy", "embeddings from Stage 1"),
            ]
        elif stage == 4:
            required = [
                (self.assignments_dir / "final_assignments.json", "assignments from Stage 3"),
                (self.assignments_dir / "final_prototypes.json", "prototypes from Stage 3"),
            ]
        else:
            return False, [f"Unknown stage: {stage}"]

        missing = []
        for path, desc in required:
            if not path.exists():
                missing.append(f"{desc} ({path})")

        return len(missing) == 0, missing

    def run_stage(self, stage: int, force: bool = False):
        """Run a specific pipeline stage."""
        stage_name = self.STAGE_NAMES.get(stage, f"Stage {stage}")

        # Check if already completed
        if not force and stage in self.state["completed_stages"]:
            print(f"\n  Stage {stage} ({stage_name}) already completed "
                  f"(use --force-restart to rerun)")
            return

        # Check dependencies
        ready, missing = self.check_stage_dependencies(stage)
        if not ready:
            print(f"\n  Stage {stage} ({stage_name}) — dependencies not met:")
            for m in missing:
                print(f"    Missing: {m}")
            print(f"    Run previous stages first.")
            return

        # Run
        start_time = time.time()

        try:
            if stage == 1:
                self._run_stage1()
            elif stage == 2:
                self._run_stage2()
            elif stage == 3:
                self._run_stage3()
            elif stage == 4:
                self._run_stage4()

            # Mark completed
            if stage not in self.state["completed_stages"]:
                self.state["completed_stages"].append(stage)
            self._save_state()

            elapsed = time.time() - start_time
            print(f"\n  Stage {stage} completed in {elapsed:.1f}s")

        except Exception as e:
            print(f"\n  Stage {stage} ({stage_name}) FAILED: {e}")
            raise

    def _run_stage1(self):
        """Stage 1: Generate EfficientNet embeddings for all 100K crops."""
        generator = EmbeddingGenerator(
            crops_dir=str(self.crops_dir),
            output_dir=str(self.crops_dir),
            model_name=self.model
        )
        generator.generate_all_embeddings()

    def _run_stage2(self):
        """Stage 2: Build ground truth prototypes from single-species images."""
        builder = GroundTruthBuilder(
            crops_dir=str(self.crops_dir),
            embeddings_dir=str(self.embeddings_dir),
            image_metadata_path=self.image_metadata_path
        )
        builder.build_prototypes()

    def _run_stage3(self):
        """Stage 3+4: Classify multi-species images with iterative refinement."""
        validator = CrossReferenceValidator(
            crops_dir=str(self.crops_dir),
            embeddings_dir=str(self.embeddings_dir),
            prototypes_path=str(self.ground_truth_dir / "prototypes.json"),
            image_metadata_path=self.image_metadata_path
        )
        validator.run_iterative_refinement()

    def _run_stage4(self):
        """Stage 5: Quality control and export."""
        exporter = QualityExporter(
            crops_dir=str(self.crops_dir),
            embeddings_dir=str(self.embeddings_dir),
            assignments_path=str(self.assignments_dir / "final_assignments.json"),
            prototypes_path=str(self.assignments_dir / "final_prototypes.json")
        )
        exporter.export_all()

    def run_all(self, force_restart: bool = False, start_from: int = 1):
        """Execute all pipeline stages in order."""
        print("\n" + "=" * 60)
        print("GROUND-TRUTH-ANCHORED SPECIES CLASSIFICATION PIPELINE (v2)")
        print("=" * 60)
        print(f"Crops: {self.crops_dir}")
        print(f"Model: {self.model}")
        print(f"Image metadata: {self.image_metadata_path}")
        print(f"\nStages:")
        for num, name in self.STAGE_NAMES.items():
            status = "completed" if num in self.state["completed_stages"] else "pending"
            marker = "[done]" if status == "completed" else "[    ]"
            print(f"  {marker} {num}. {name}")
        print("=" * 60)

        if force_restart:
            print("\nForce restart: clearing previous state")
            self.state["completed_stages"] = []
            self._save_state()

        total_start = time.time()

        for stage in range(start_from, 5):
            self.run_stage(stage, force=force_restart)

        total_elapsed = time.time() - total_start

        print("\n" + "=" * 60)
        print("PIPELINE COMPLETE")
        print("=" * 60)
        print(f"Total time: {total_elapsed / 60:.1f} minutes")
        print(f"\nOutputs:")
        print(f"  Embeddings:   {self.embeddings_dir}")
        print(f"  Ground truth: {self.ground_truth_dir}")
        print(f"  Assignments:  {self.assignments_dir}")
        print(f"  Export:       {self.export_dir}")
        print(f"\nNext: View results in Nestperts dashboard")
        print(f"  python labeller/app.py --data labeller/nestvision")
        print(f"  Open: http://localhost:5000/clusters")


def main():
    parser = argparse.ArgumentParser(
        description='Run ground-truth-anchored species classification pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full pipeline
  python run_full_pipeline.py

  # Force restart from scratch
  python run_full_pipeline.py --force-restart

  # Start from specific stage (e.g., skip embeddings if already generated)
  python run_full_pipeline.py --start-from 2

  # Resume from where it left off
  python run_full_pipeline.py
        """
    )

    parser.add_argument('--crops-dir', type=str,
                        default='data/weak_supervision/bird_crops',
                        help='Path to bird_crops directory')
    parser.add_argument('--image-metadata', type=str,
                        default='data/weak_supervision/image_metadata.json',
                        help='Path to image_metadata.json')
    parser.add_argument('--model', type=str, default='efficientnet',
                        choices=['efficientnet', 'resnet50', 'clip', 'dinov2', 'siglip'],
                        help='Embedding model to use')
    parser.add_argument('--force-restart', action='store_true',
                        help='Force restart from scratch')
    parser.add_argument('--start-from', type=int, default=1, choices=[1, 2, 3, 4],
                        help='Which stage to start from')

    args = parser.parse_args()

    orchestrator = PipelineOrchestrator(
        crops_dir=args.crops_dir,
        model=args.model,
        image_metadata_path=args.image_metadata
    )

    orchestrator.run_all(
        force_restart=args.force_restart,
        start_from=args.start_from
    )


if __name__ == '__main__':
    main()
