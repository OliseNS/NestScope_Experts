"""
Step 0: Cleanup Old Data

Removes stale embeddings and clustering results from the broken pipeline.
Keeps bird crop images and metadata intact.
"""

import shutil
from pathlib import Path


def cleanup(base_dir: str = None, dry_run: bool = False):
    """
    Delete old embedding and clustering data.

    Args:
        base_dir: Project root directory
        dry_run: If True, only print what would be deleted
    """
    if base_dir is None:
        base_dir = Path(__file__).parent.parent.parent.parent
    else:
        base_dir = Path(base_dir)

    crops_dir = base_dir / "data" / "weak_supervision" / "bird_crops"
    frontend_dir = base_dir / "labeller" / "nestvision" / "bird_crops"

    # Directories to delete entirely
    dirs_to_delete = [
        crops_dir / "embeddings",
        crops_dir / "species_clusters",
        frontend_dir / "clusters",
    ]

    # Individual files to delete
    files_to_delete = [
        crops_dir / "pipeline_state.json",
        frontend_dir / "embeddings.npy",
        frontend_dir / "config.json",
    ]

    # Files/dirs to KEEP (verify they exist)
    must_keep = [
        crops_dir / "images",
        crops_dir / "metadata.json",
        base_dir / "data" / "weak_supervision" / "image_metadata.json",
        base_dir / "data" / "weak_supervision" / "photo_mappings_2015_2021.json",
    ]

    prefix = "[DRY RUN] " if dry_run else ""

    print("=" * 60)
    print(f"{prefix}CLEANUP OLD PIPELINE DATA")
    print("=" * 60)

    # Verify critical files exist before deleting anything
    print(f"\n{prefix}Verifying critical files are safe...")
    for path in must_keep:
        if path.exists():
            print(f"  [OK] {path.relative_to(base_dir)}")
        else:
            print(f"  [MISSING] {path.relative_to(base_dir)}")

    # Delete directories
    print(f"\n{prefix}Deleting directories...")
    for dir_path in dirs_to_delete:
        if dir_path.exists():
            if dry_run:
                # Count files for info
                n_files = sum(1 for _ in dir_path.rglob("*") if _.is_file())
                print(f"  Would delete: {dir_path.relative_to(base_dir)} ({n_files} files)")
            else:
                shutil.rmtree(dir_path)
                print(f"  Deleted: {dir_path.relative_to(base_dir)}")
        else:
            print(f"  Skipped (not found): {dir_path.relative_to(base_dir)}")

    # Delete individual files
    print(f"\n{prefix}Deleting files...")
    for file_path in files_to_delete:
        if file_path.exists():
            if dry_run:
                size_mb = file_path.stat().st_size / 1024**2
                print(f"  Would delete: {file_path.relative_to(base_dir)} ({size_mb:.1f} MB)")
            else:
                file_path.unlink()
                print(f"  Deleted: {file_path.relative_to(base_dir)}")
        else:
            print(f"  Skipped (not found): {file_path.relative_to(base_dir)}")

    # Also clean any old backup directories in frontend
    print(f"\n{prefix}Cleaning old backups in frontend dir...")
    if frontend_dir.exists():
        for backup_dir in frontend_dir.glob("clusters_old_backup_*"):
            if dry_run:
                print(f"  Would delete: {backup_dir.relative_to(base_dir)}")
            else:
                shutil.rmtree(backup_dir)
                print(f"  Deleted: {backup_dir.relative_to(base_dir)}")

        for backup_file in frontend_dir.glob("metadata_old_backup_*"):
            if dry_run:
                print(f"  Would delete: {backup_file.relative_to(base_dir)}")
            else:
                backup_file.unlink()
                print(f"  Deleted: {backup_file.relative_to(base_dir)}")

    print(f"\n{prefix}Cleanup complete.")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Cleanup old pipeline data')
    parser.add_argument('--dry-run', action='store_true',
                        help='Only print what would be deleted, do not actually delete')
    args = parser.parse_args()

    cleanup(dry_run=args.dry_run)


if __name__ == '__main__':
    main()
