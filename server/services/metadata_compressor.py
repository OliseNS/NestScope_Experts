"""
AI-Powered Metadata Compression
================================

Uses LLM to intelligently compress database metadata from 35k+ tokens
to <2k tokens while preserving query-critical information.

Three-tier approach:
1. ESSENTIAL (always loaded): Core schema needed for 95% of queries
2. EXTENDED (on-demand): Full schema details when needed
3. RAW (fallback): Original verbose metadata
"""

import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class MetadataCompressor:
    """Compresses database metadata using AI-powered analysis."""

    def __init__(self, db_path: str, api_key: str, model: str = "anthropic/claude-sonnet-4"):
        self.db_path = db_path
        self.api_key = api_key
        self.model = model

    def compress(self, output_dir: str = "data/") -> Dict[str, str]:
        """
        Generate compressed metadata at three levels.

        Returns:
            Dict with paths to essential, extended, and raw metadata files
        """
        logger.info("🤖 Starting AI-powered metadata compression...")

        # Step 1: Explore database (raw metadata)
        raw_metadata = self._explore_database()

        # Step 2: Use LLM to compress into essential metadata
        essential_metadata = self._compress_with_llm(raw_metadata)

        # Step 3: Generate extended metadata (mid-tier)
        extended_metadata = self._generate_extended_metadata(raw_metadata)

        # Step 4: Save all three tiers
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        paths = {
            "essential": str(output_dir / "metadata_essential.json"),
            "extended": str(output_dir / "metadata_extended.json"),
            "raw": str(output_dir / "metadata_raw.json")
        }

        # Save files
        with open(paths["essential"], "w") as f:
            json.dump(essential_metadata, f, indent=2)

        with open(paths["extended"], "w") as f:
            json.dump(extended_metadata, f, indent=2)

        with open(paths["raw"], "w") as f:
            json.dump(raw_metadata, f, indent=2)

        # Report compression stats
        essential_size = Path(paths["essential"]).stat().st_size
        raw_size = Path(paths["raw"]).stat().st_size
        compression_ratio = (1 - essential_size / raw_size) * 100

        logger.info(f"✅ Compression complete!")
        logger.info(f"   Essential: {essential_size:,} bytes")
        logger.info(f"   Raw: {raw_size:,} bytes")
        logger.info(f"   Compression: {compression_ratio:.1f}%")

        return paths

    def _explore_database(self) -> Dict[str, Any]:
        """Explore database and gather raw metadata."""
        logger.info("   📊 Exploring database schema...")

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # Get all tables
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
            tables = [row['name'] for row in cursor.fetchall()]

            metadata = {
                "discovered_at": datetime.now().isoformat(),
                "database": Path(self.db_path).name,
                "tables": {}
            }

            for table in tables:
                # Get schema
                cursor.execute(f'PRAGMA table_info("{table}")')
                columns = [dict(row) for row in cursor.fetchall()]

                # Get row count
                cursor.execute(f'SELECT COUNT(*) as count FROM "{table}"')
                row_count = cursor.fetchone()['count']

                # Get sample data
                cursor.execute(f'SELECT * FROM "{table}" LIMIT 3')
                samples = [dict(row) for row in cursor.fetchall()]

                metadata["tables"][table] = {
                    "row_count": row_count,
                    "columns": columns,
                    "samples": samples
                }

            return metadata

        finally:
            conn.close()

    def _compress_with_llm(self, raw_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Use LLM to compress metadata into query-optimized format."""
        logger.info("   🧠 Using LLM to compress metadata...")

        import requests

        # Prepare compact representation for LLM
        schema_summary = self._prepare_schema_for_llm(raw_metadata)

        prompt = f"""You are a database metadata compression expert. Your task is to compress verbose database schema information into ultra-compact, query-optimized metadata.

INPUT DATABASE SCHEMA:
{schema_summary}

OUTPUT REQUIREMENTS:
Generate a JSON object with this EXACT structure (no extra fields):

{{
  "tables": {{
    "table_name": {{
      "purpose": "one-line description",
      "row_count": number,
      "key_columns": ["col1:type", "col2:type"],
      "joins": ["OtherTable.column"],
      "query_hints": ["use this for X queries"]
    }}
  }},
  "critical_rules": [
    "rule 1: always include Lat/Lon for colony queries",
    "rule 2: use ColonyTotals for bird counts, not SpeciesData"
  ],
  "common_patterns": [
    "pattern 1: JOIN colonies ON species.SpeciesCode = ...",
    "pattern 2: GROUP BY ColonyName, Latitude, Longitude"
  ]
}}

COMPRESSION GUIDELINES:
1. Focus ONLY on information needed for SQL query generation
2. Remove ALL redundant details (cid, notnull, dflt_value, pk)
3. Keep only essential column names + types (shorten types: TEXT→T, INTEGER→I)
4. Prioritize relationships and join patterns
5. Include critical query rules (coordinate inclusion, table choice)
6. Target <2000 tokens total

OUTPUT (valid JSON only, no explanation):"""

        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1
                },
                timeout=60
            )
            response.raise_for_status()

            result = response.json()
            compressed_text = result["choices"][0]["message"]["content"]

            # Extract JSON from response (handle markdown code blocks)
            if "```json" in compressed_text:
                compressed_text = compressed_text.split("```json")[1].split("```")[0].strip()
            elif "```" in compressed_text:
                compressed_text = compressed_text.split("```")[1].split("```")[0].strip()

            compressed_metadata = json.loads(compressed_text)

            # Add metadata
            compressed_metadata["_meta"] = {
                "generated_at": datetime.now().isoformat(),
                "compression_version": "1.0",
                "model": self.model
            }

            return compressed_metadata

        except Exception as e:
            logger.error(f"❌ LLM compression failed: {e}")
            logger.warning("   Falling back to rule-based compression...")
            return self._fallback_compression(raw_metadata)

    def _prepare_schema_for_llm(self, raw_metadata: Dict[str, Any]) -> str:
        """Prepare compact schema summary for LLM input."""
        lines = []

        for table_name, table_info in raw_metadata["tables"].items():
            lines.append(f"\nTABLE: {table_name} ({table_info['row_count']:,} rows)")

            # Show column names and types only
            cols = [f"{c['name']}:{c['type']}" for c in table_info["columns"]]
            lines.append(f"  Columns: {', '.join(cols)}")

            # Show sample data (first row only, truncated)
            if table_info["samples"]:
                sample = table_info["samples"][0]
                sample_str = str(sample)[:200]
                lines.append(f"  Sample: {sample_str}...")

        return "\n".join(lines)

    def _fallback_compression(self, raw_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Rule-based compression fallback if LLM fails."""
        compressed = {
            "_meta": {
                "generated_at": datetime.now().isoformat(),
                "compression_version": "1.0-fallback",
                "model": "rule-based"
            },
            "tables": {},
            "critical_rules": [
                "Always include Latitude and Longitude for colony queries",
                "Use tblColonyTotals for bird counts, not tblSpeciesData"
            ],
            "common_patterns": []
        }

        for table_name, table_info in raw_metadata["tables"].items():
            # Extract essential info only
            key_columns = []
            for col in table_info["columns"]:
                col_name = col["name"]
                col_type = col["type"][0]  # Just first letter (T, I, R)

                # Include only "interesting" columns (not generic IDs/Notes)
                if not any(skip in col_name.lower() for skip in ["notes", "additional"]):
                    key_columns.append(f"{col_name}:{col_type}")

            compressed["tables"][table_name] = {
                "row_count": table_info["row_count"],
                "key_columns": key_columns[:10]  # Limit to top 10
            }

        return compressed

    def _generate_extended_metadata(self, raw_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate mid-tier metadata (more detailed than essential, less than raw).
        Includes full column names but removes samples and redundant fields.
        """
        extended = {
            "_meta": {
                "generated_at": datetime.now().isoformat(),
                "tier": "extended"
            },
            "tables": {}
        }

        for table_name, table_info in raw_metadata["tables"].items():
            extended["tables"][table_name] = {
                "row_count": table_info["row_count"],
                "columns": [
                    {
                        "name": col["name"],
                        "type": col["type"]
                    }
                    for col in table_info["columns"]
                ]
            }

        return extended


# CLI for standalone usage
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python metadata_compressor.py <db_path> <api_key> [model]")
        sys.exit(1)

    logging.basicConfig(level=logging.INFO)

    db_path = sys.argv[1]
    api_key = sys.argv[2]
    model = sys.argv[3] if len(sys.argv) > 3 else "anthropic/claude-sonnet-4"

    compressor = MetadataCompressor(db_path, api_key, model)
    paths = compressor.compress()

    print(f"\n✅ Generated compressed metadata:")
    print(f"   Essential: {paths['essential']}")
    print(f"   Extended: {paths['extended']}")
    print(f"   Raw: {paths['raw']}")
