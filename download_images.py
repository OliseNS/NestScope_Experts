#!/usr/bin/env python3
"""
Fast parallel downloader for TWI avian high-resolution images.
Downloads 5000 random images from S3 bucket using threading.
"""

import boto3
from botocore import UNSIGNED
from botocore.config import Config
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
from pathlib import Path
from tqdm import tqdm
import time

# Configuration
BUCKET_NAME = "twi-aviandata"
PREFIX = "HighResolutionImages/"
NUM_IMAGES = 5000
MAX_WORKERS = 32  # Parallel download threads
DOWNLOAD_DIR = Path("demoday_images")
RETRY_ATTEMPTS = 3

def list_all_images(s3_client, bucket, prefix):
    """List all image keys in the S3 bucket."""
    print(f"Listing images from s3://{bucket}/{prefix}...")

    images = []
    paginator = s3_client.get_paginator('list_objects_v2')

    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        if 'Contents' in page:
            for obj in page['Contents']:
                key = obj['Key']
                # Filter for image files
                if key.lower().endswith(('.jpg', '.jpeg', '.png', '.tif', '.tiff')):
                    images.append(key)

    print(f"Found {len(images)} total images")
    return images

def download_image(s3_client, bucket, key, download_dir, pbar):
    """Download a single image with retry logic."""
    local_path = download_dir / Path(key).name

    for attempt in range(RETRY_ATTEMPTS):
        try:
            s3_client.download_file(bucket, key, str(local_path))
            pbar.update(1)
            return True
        except Exception as e:
            if attempt == RETRY_ATTEMPTS - 1:
                pbar.write(f"Failed to download {key}: {e}")
                return False
            time.sleep(0.5 * (attempt + 1))  # Exponential backoff

    return False

def main():
    # Create download directory
    DOWNLOAD_DIR.mkdir(exist_ok=True)
    print(f"Download directory: {DOWNLOAD_DIR.absolute()}")

    # Initialize S3 client (no signature for public bucket)
    s3_config = Config(signature_version=UNSIGNED, max_pool_connections=MAX_WORKERS)
    s3_client = boto3.client('s3', config=s3_config)

    # List all images
    all_images = list_all_images(s3_client, BUCKET_NAME, PREFIX)

    if not all_images:
        print("No images found!")
        return

    # Select random sample
    num_to_download = min(NUM_IMAGES, len(all_images))
    selected_images = random.sample(all_images, num_to_download)
    print(f"Selected {num_to_download} random images for download")

    # Parallel download with progress bar
    print(f"\nDownloading with {MAX_WORKERS} parallel workers...")
    successful = 0
    failed = 0

    with tqdm(total=num_to_download, unit='img', ncols=80) as pbar:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(download_image, s3_client, BUCKET_NAME, key, DOWNLOAD_DIR, pbar): key
                for key in selected_images
            }

            for future in as_completed(futures):
                if future.result():
                    successful += 1
                else:
                    failed += 1

    # Summary
    print(f"\n{'='*50}")
    print(f"Download complete!")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Location: {DOWNLOAD_DIR.absolute()}")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()
