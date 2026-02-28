"""
Master Orchestrator: Run Full Species Assignment Pipeline

Executes all 4 stages in sequence with dependency checking and resume support.
"""

import sys
from pathlib import Path
import json
import argparse
from datetime import datetime
import time

# Import stage modules
from stage1_generate_embeddings import EmbeddingGenerator
from stage2_per_image_clustering import PerImageClusterer
from stage3_global_species_assignment import GlobalSpeciesResolver
from stage4_export_for_frontend import FrontendExporter


class PipelineOrchestrator:
    """
    Manages the complete species assignment pipeline.

    Provides:
    - Stage execution with dependency checking
    - Resume support (skip completed stages)
    - Progress tracking and logging
    - Error handling
    """

    def __init__(self, crops_dir: str, output_dir: str, model: str = 'efficientnet'):
        """
        Args:
            crops_dir: Path to bird_crops directory
            output_dir: Path to output directory (parent of bird_crops)
            model: Embedding model to use
        """
        self.crops_dir = Path(crops_dir)
        self.output_dir = Path(output_dir)
        self.model = model

        # Define paths
        self.embeddings_dir = self.crops_dir / "embeddings"
        self.species_clusters_dir = self.crops_dir / "species_clusters"
        self.image_clusters_dir = self.species_clusters_dir / "image_clusters"

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
            "model": None
        }

    def _save_state(self):
        """Save pipeline state to file."""
        self.state["last_run"] = datetime.now().isoformat()
        self.state["model"] = self.model
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)

    def check_stage_dependencies(self, stage: int) -> tuple:
        """
        Verify that required files exist for a stage.

        Args:
            stage: Stage number (1-4)

        Returns:
            (ready: bool, missing: list)
        """
        if stage == 1:
            # Stage 1 requires: metadata.json
            required = [self.crops_dir / "metadata.json"]

        elif stage == 2:
            # Stage 2 requires: embeddings from Stage 1
            required = [
                self.embeddings_dir / "embeddings_all.npy",
                self.embeddings_dir / "embeddings_index.json"
            ]

        elif stage == 3:
            # Stage 3 requires: image_clusters from Stage 2
            required = [self.image_clusters_dir]
            if self.image_clusters_dir.exists():
                cluster_files = list(self.image_clusters_dir.glob("*.json"))
                if len(cluster_files) == 0:
                    return False, ["No cluster JSON files in image_clusters/"]

        elif stage == 4:
            # Stage 4 requires: global_cluster_map from Stage 3
            required = [self.species_clusters_dir / "global_cluster_map.json"]

        else:
            return False, [f"Unknown stage: {stage}"]

        # Check if all required files exist
        missing = [str(f) for f in required if not f.exists()]
        return len(missing) == 0, missing

    def run_stage(self, stage: int, force: bool = False):
        """
        Run a specific stage.

        Args:
            stage: Stage number (1-4)
            force: If True, run even if already completed
        """
        stage_name = f"Stage {stage}"

        # Check if already completed
        if not force and stage in self.state["completed_stages"]:
            print(f"\n✓ {stage_name} already completed (use --force-restart to rerun)")
            return

        # Check dependencies
        ready, missing = self.check_stage_dependencies(stage)
        if not ready:
            print(f"\n❌ {stage_name} dependencies not met:")
            for m in missing:
                print(f"   Missing: {m}")
            print(f"   Run previous stages first")
            return

        # Run stage
        print(f"\n{'=' * 60}")
        print(f"Running {stage_name}")
        print(f"{'=' * 60}")

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

            # Mark as completed
            if stage not in self.state["completed_stages"]:
                self.state["completed_stages"].append(stage)
            self._save_state()

            elapsed = time.time() - start_time
            print(f"\n✅ {stage_name} completed in {elapsed:.1f}s")

        except Exception as e:
            print(f"\n❌ {stage_name} failed with error:")
            print(f"   {str(e)}")
            raise

    def _run_stage1(self):
        """Run Stage 1: Generate embeddings"""
        generator = EmbeddingGenerator(
            crops_dir=str(self.crops_dir),
            output_dir=str(self.crops_dir),
            model_name=self.model
        )
        generator.generate_all_embeddings()

    def _run_stage2(self):
        """Run Stage 2: Per-image clustering"""
        clusterer = PerImageClusterer(
            crops_dir=str(self.crops_dir),
            embeddings_dir=str(self.embeddings_dir),
            output_dir=str(self.crops_dir)
        )
        clusterer.process_all_images()

    def _run_stage3(self):
        """Run Stage 3: Global species resolution"""
        resolver = GlobalSpeciesResolver(
            image_clusters_dir=str(self.image_clusters_dir),
            output_dir=str(self.species_clusters_dir)
        )
        resolver.build_global_cluster_map()

    def _run_stage4(self):
        """Run Stage 4: Export for frontend"""
        exporter = FrontendExporter(
            crops_dir=str(self.crops_dir),
            embeddings_dir=str(self.embeddings_dir),
            species_clusters_dir=str(self.species_clusters_dir)
        )
        exporter.generate_visualization_data()

    def run_all(self, force_restart: bool = False, start_from: int = 1):
        """
        Execute all pipeline stages.

        Args:
            force_restart: If True, restart from scratch
            start_from: Which stage to start from (1-4)
        """
        print("\n" + "=" * 60)
        print("SPECIES ASSIGNMENT PIPELINE")
        print("=" * 60)
        print(f"Crops directory: {self.crops_dir}")
        print(f"Output directory: {self.output_dir}")
        print(f"Embedding model: {self.model}")
        print("=" * 60)

        # Clear state if force restart
        if force_restart:
            print("\n🔄 Force restart: clearing previous state")
            self.state["completed_stages"] = []
            self._save_state()

        # Run stages
        total_start = time.time()

        for stage in range(start_from, 5):
            self.run_stage(stage, force=force_restart)

        total_elapsed = time.time() - total_start

        # Final summary
        print("\n" + "=" * 60)
        print("🎉 PIPELINE COMPLETE!")
        print("=" * 60)
        print(f"Total time: {total_elapsed / 60:.1f} minutes")
        print(f"\nOutput files:")
        print(f"  • Embeddings: {self.embeddings_dir}")
        print(f"  • Image clusters: {self.image_clusters_dir}")
        print(f"  • Global map: {self.species_clusters_dir / 'global_cluster_map.json'}")
        print(f"  • Frontend JSON: {self.species_clusters_dir / 'clusters_for_labeling.json'}")
        print(f"\n🎯 Next step: View results in Nestperts")
        print(f"   cd labeller/")
        print(f"   python app.py --data nestvision")
        print(f"   Open: http://localhost:5000/clusters")
        print("=" * 60)


def main():
    """
    Main entry point for full pipeline.
    """
    parser = argparse.ArgumentParser(
        description='Run full species assignment pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full pipeline
  python run_full_pipeline.py

  # Resume after crash
  python run_full_pipeline.py --resume

  # Force restart from scratch
  python run_full_pipeline.py --force-restart

  # Start from specific stage
  python run_full_pipeline.py --start-from 3

  # Use different model
  python run_full_pipeline.py --model siglip
        """
    )

    parser.add_argument('--crops-dir', type=str,
                        default='../bird_crops',
                        help='Path to bird_crops directory')
    parser.add_argument('--output-dir', type=str,
                        default='..',
                        help='Path to output directory')
    parser.add_argument('--model', type=str, default='efficientnet',
                        choices=['efficientnet', 'resnet50', 'clip', 'dinov2', 'siglip'],
                        help='Embedding model to use')
    parser.add_argument('--force-restart', action='store_true',
                        help='Force restart from scratch (ignore previous state)')
    parser.add_argument('--resume', action='store_true',
                        help='Resume from last checkpoint (default behavior)')
    parser.add_argument('--start-from', type=int, default=1, choices=[1, 2, 3, 4],
                        help='Which stage to start from')

    args = parser.parse_args()

    # Create orchestrator
    orchestrator = PipelineOrchestrator(
        crops_dir=args.crops_dir,
        output_dir=args.output_dir,
        model=args.model
    )

    # Run pipeline
    orchestrator.run_all(
        force_restart=args.force_restart,
        start_from=args.start_from
    )


if __name__ == '__main__':
    main()
