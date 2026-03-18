#!/usr/bin/env python3
"""
Generate AI-compressed metadata for NestChat
==============================================

Reduces metadata from 35k+ tokens to <2k tokens using LLM-powered compression.

Usage:
    python scripts/compress_metadata.py
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from server.services.metadata_compressor import MetadataCompressor
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)

def main():
    # Load environment
    load_dotenv()

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ Error: OPENROUTER_API_KEY not found in .env")
        print("   Add your OpenRouter API key to .env file")
        sys.exit(1)

    db_path = os.getenv("DB_PATH", "data/bird_data_complete.db")
    db_path = str(project_root / db_path)

    if not os.path.exists(db_path):
        print(f"❌ Error: Database not found at {db_path}")
        sys.exit(1)

    # Load model from config
    import yaml
    config_path = project_root / "server" / "config.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)
    model = config['model']['name']

    print(f"🤖 AI-Powered Metadata Compression")
    print(f"   Database: {db_path}")
    print(f"   Model: {model}")
    print()

    # Compress
    compressor = MetadataCompressor(db_path, api_key, model)
    paths = compressor.compress(output_dir=str(project_root / "data"))

    print()
    print(f"✅ Success! Generated 3-tier metadata system:")
    print()
    print(f"   📦 ESSENTIAL (use for 95% of queries):")
    print(f"      {paths['essential']}")
    print()
    print(f"   📚 EXTENDED (fallback when needed):")
    print(f"      {paths['extended']}")
    print()
    print(f"   🗄️  RAW (debug/admin only):")
    print(f"      {paths['raw']}")
    print()

    # Show token comparison
    from pathlib import Path
    essential_size = Path(paths['essential']).stat().st_size
    raw_size = Path(paths['raw']).stat().st_size

    # Rough token estimate: 1 token ≈ 4 chars
    essential_tokens = essential_size // 4
    raw_tokens = raw_size // 4
    compression_ratio = (1 - essential_tokens / raw_tokens) * 100

    print(f"📊 Token Savings:")
    print(f"   Before: ~{raw_tokens:,} tokens")
    print(f"   After:  ~{essential_tokens:,} tokens")
    print(f"   Saved:  ~{raw_tokens - essential_tokens:,} tokens ({compression_ratio:.1f}% reduction)")
    print()
    print(f"💡 Next steps:")
    print(f"   1. Review {paths['essential']} to verify quality")
    print(f"   2. Restart server to use compressed metadata")
    print(f"   3. Test NestChat queries for accuracy")

if __name__ == "__main__":
    main()
