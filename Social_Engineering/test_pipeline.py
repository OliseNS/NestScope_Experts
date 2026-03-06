#!/usr/bin/env python3
"""
Test Pipeline - Download samples, extract dots, create visualizations

This script validates the reconstruction approach with 20 test images
"""

import json
import requests
from pathlib import Path
from typing import List, Dict
import urllib.parse
import time

from s3_crawler import S3Crawler
from dot_extractor import DotExtractor


class TestPipeline:
    """End-to-end test pipeline for dot reconstruction"""

    def __init__(self, output_dir: str = "/home/olisemeka.dev/Projects/nexus/Social_Engineering"):
        self.output_dir = Path(output_dir)
        self.data_dir = self.output_dir / "data"
        self.vis_dir = self.output_dir / "vis"
        self.downloads_dir = self.data_dir / "downloads"

        # Create directories
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.vis_dir.mkdir(parents=True, exist_ok=True)
        self.downloads_dir.mkdir(parents=True, exist_ok=True)

        self.crawler = S3Crawler()
        self.extractor = DotExtractor()

    def download_image(self, s3_url: str, save_path: Path) -> bool:
        """Download image from S3"""
        try:
            response = requests.get(s3_url, timeout=30, stream=True)
            response.raise_for_status()

            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            return True

        except Exception as e:
            print(f"   Download failed: {e}")
            return False

    def download_test_samples(self, test_samples: List[Dict]) -> List[Dict]:
        """Download test sample images from S3"""
        print(f"\n Downloading {len(test_samples)} test samples...")
        print("="*60)

        downloaded = []

        for i, sample in enumerate(test_samples):
            filename = sample['filename']
            s3_url = sample['s3_url']

            print(f"\n[{i+1}/{len(test_samples)}] {filename}")
            print(f"  URL: {s3_url}")

            # Create safe filename
            safe_filename = filename.replace(' ', '_').replace('/', '_')
            save_path = self.downloads_dir / safe_filename

            # Skip if already downloaded
            if save_path.exists():
                print(f"    Already downloaded")
                sample['local_path'] = str(save_path)
                downloaded.append(sample)
                continue

            # Download
            if self.download_image(s3_url, save_path):
                print(f"   Downloaded ({save_path.stat().st_size / 1024:.1f} KB)")
                sample['local_path'] = str(save_path)
                downloaded.append(sample)
            else:
                print(f"    Skipped")

            # Rate limiting
            time.sleep(0.5)

        print(f"\n Downloaded {len(downloaded)}/{len(test_samples)} images")
        return downloaded

    def process_test_samples(self, samples: List[Dict]) -> Dict:
        """Process all test samples through dot extraction"""
        print(f"\n Processing {len(samples)} samples for dot extraction...")
        print("="*60)

        results = {
            'total_samples': len(samples),
            'successful': 0,
            'failed': 0,
            'total_dots': 0,
            'samples': []
        }

        for i, sample in enumerate(samples):
            if 'local_path' not in sample:
                continue

            filename = Path(sample['local_path']).name
            print(f"\n[{i+1}/{len(samples)}] {filename}")

            try:
                # Extract dots
                dots, vis_image = self.extractor.extract_dots(
                    sample['local_path'],
                    visualize=True
                )

                # Save visualization
                vis_filename = f"{i+1:03d}_{Path(sample['local_path']).stem}_extracted.jpg"
                vis_path = self.vis_dir / vis_filename

                if vis_image is not None:
                    import cv2
                    cv2.imwrite(str(vis_path), vis_image)
                    print(f"   Saved visualization to {vis_path.name}")

                # Also save dots JSON
                dots_json_path = self.vis_dir / f"{i+1:03d}_{Path(sample['local_path']).stem}_dots.json"
                with open(dots_json_path, 'w') as f:
                    json.dump(dots, f, indent=2)

                print(f"   Found {len(dots)} dots")

                results['successful'] += 1
                results['total_dots'] += len(dots)

                results['samples'].append({
                    'filename': filename,
                    'year': sample.get('year'),
                    'colony': sample.get('colony'),
                    'area': sample.get('area'),
                    'dot_count': len(dots),
                    'visualization': vis_filename,
                    'dots_json': dots_json_path.name,
                    'success': True
                })

            except Exception as e:
                print(f"   Error: {e}")
                results['failed'] += 1

                results['samples'].append({
                    'filename': filename,
                    'error': str(e),
                    'success': False
                })

        print(f"\n Processed {results['successful']}/{results['total_samples']} samples")
        print(f"   Total dots detected: {results['total_dots']}")
        print(f"   Average dots per image: {results['total_dots'] / max(results['successful'], 1):.1f}")

        return results

    def generate_report(self, results: Dict):
        """Generate HTML report of test results"""
        print(f"\n Generating test report...")

        report_path = self.vis_dir / "test_report.html"

        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Dot Extraction Test Report</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: #2c3e50;
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: #3498db;
        }}
        .stat-label {{
            color: #7f8c8d;
            margin-top: 5px;
        }}
        .gallery {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
            gap: 20px;
        }}
        .image-card {{
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .image-card img {{
            width: 100%;
            height: auto;
            display: block;
        }}
        .image-info {{
            padding: 15px;
        }}
        .image-title {{
            font-weight: bold;
            margin-bottom: 10px;
            color: #2c3e50;
        }}
        .image-meta {{
            font-size: 0.9em;
            color: #7f8c8d;
        }}
        .dot-count {{
            background: #3498db;
            color: white;
            padding: 5px 10px;
            border-radius: 4px;
            display: inline-block;
            margin-top: 10px;
        }}
        .success {{
            color: #27ae60;
        }}
        .error {{
            color: #e74c3c;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1> Dot Extraction Test Report</h1>
        <p>Testing expert annotation reconstruction pipeline</p>
    </div>

    <div class="stats">
        <div class="stat-card">
            <div class="stat-value">{results['total_samples']}</div>
            <div class="stat-label">Total Samples</div>
        </div>
        <div class="stat-card">
            <div class="stat-value success">{results['successful']}</div>
            <div class="stat-label">Successful</div>
        </div>
        <div class="stat-card">
            <div class="stat-value error">{results['failed']}</div>
            <div class="stat-label">Failed</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{results['total_dots']}</div>
            <div class="stat-label">Total Dots Detected</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{results['total_dots'] / max(results['successful'], 1):.1f}</div>
            <div class="stat-label">Avg Dots/Image</div>
        </div>
    </div>

    <h2>Sample Results</h2>
    <div class="gallery">
"""

        for sample in results['samples']:
            if not sample.get('success'):
                continue

            html += f"""
        <div class="image-card">
            <img src="{sample['visualization']}" alt="{sample['filename']}">
            <div class="image-info">
                <div class="image-title">{sample['filename']}</div>
                <div class="image-meta">
                    Year: {sample.get('year', 'N/A')} |
                    Colony: {sample.get('colony', 'N/A')} |
                    Area: {sample.get('area', 'N/A')}
                </div>
                <div class="dot-count">
                    {sample['dot_count']} dots detected
                </div>
            </div>
        </div>
"""

        html += """
    </div>
</body>
</html>
"""

        with open(report_path, 'w') as f:
            f.write(html)

        print(f"   Report saved to {report_path}")
        print(f"   Open in browser: file://{report_path}")

    def run(self, n_samples: int = 20):
        """Run complete test pipeline"""
        print("STARTING TEST PIPELINE")
        print("="*60)

        # Step 1: Catalog dotted images
        print("\n Step 1: Cataloging dotted images...")
        catalog = self.crawler.catalog_dotted_images(
            save_to=self.data_dir / "dotted_images_catalog.json"
        )

        # Step 2: Select test samples
        print(f"\n Step 2: Selecting {n_samples} test samples...")
        test_samples = self.crawler.find_test_samples(catalog, n_per_year=5)
        test_samples = test_samples[:n_samples]  # Limit to requested number

        # Save test samples
        with open(self.data_dir / "test_samples.json", 'w') as f:
            json.dump(test_samples, f, indent=2)
        print(f"   Saved to {self.data_dir / 'test_samples.json'}")

        # Step 3: Download samples
        downloaded_samples = self.download_test_samples(test_samples)

        # Step 4: Process samples
        results = self.process_test_samples(downloaded_samples)

        # Save results
        with open(self.vis_dir / "test_results.json", 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n Saved results to {self.vis_dir / 'test_results.json'}")

        # Step 5: Generate report
        self.generate_report(results)

        print("\n" + "="*60)
        print("TEST PIPELINE COMPLETE!")
        print("="*60)
        print(f"\n Output directories:")
        print(f"   Data: {self.data_dir}")
        print(f"   Visualizations: {self.vis_dir}")
        print(f"   Downloads: {self.downloads_dir}")
        print(f"\n View report: file://{self.vis_dir / 'test_report.html'}")


def main():
    """Run test pipeline"""
    pipeline = TestPipeline()
    pipeline.run(n_samples=20)


if __name__ == "__main__":
    main()
