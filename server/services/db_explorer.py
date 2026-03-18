"""
Database Explorer Agent
=======================

Autonomously explores the SQLite database to discover schema, relationships,
and semantic context. Replaces static metadata with dynamic "ground truth"
extracted directly from the database.
"""

import sqlite3
import json
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple

logger = logging.getLogger(__name__)

class DatabaseExplorer:
    """Agent that explores a database to generate rich metadata context."""

    def __init__(self, db_path: str, output_path: str):
        self.db_path = db_path
        self.output_path = output_path

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def explore(self) -> Dict[str, Any]:
        """Perform full database exploration."""
        logger.info(f"🕵️ Agent exploring database: {self.db_path}")
        
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # 1. Discover all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = [row['name'] for row in cursor.fetchall()]
            
            explorer_results = {
                "discovered_at": datetime.now().isoformat(),
                "database_name": Path(self.db_path).name,
                "tables": {},
                "relationships": self._infer_relationships(tables, cursor),
                "semantic_insights": []
            }

            for table in tables:
                logger.info(f"  Exploring table: {table}")
                table_info = self._explore_table(table, cursor)
                explorer_results["tables"][table] = table_info

            # 2. Add high-level semantic insights
            explorer_results["semantic_insights"] = self._generate_insights(explorer_results["tables"])

            # 3. Save to metadata file
            self._save_metadata(explorer_results)
            
            return explorer_results

        finally:
            conn.close()

    def _explore_table(self, table_name: str, cursor: sqlite3.Cursor) -> Dict[str, Any]:
        """Explore a specific table's schema and content."""
        # Get schema
        cursor.execute(f"PRAGMA table_info(\"{table_name}\")")
        columns = [dict(row) for row in cursor.fetchall()]
        
        # Get row count
        cursor.execute(f"SELECT COUNT(*) as count FROM \"{table_name}\"")
        row_count = cursor.fetchone()['count']
        
        # Get sample data
        cursor.execute(f"SELECT * FROM \"{table_name}\" LIMIT 3")
        samples = [dict(row) for row in cursor.fetchall()]
        
        # Identify temporal columns
        time_cols = [c['name'] for c in columns if any(keyword in c['name'].lower() for keyword in ['year', 'date', 'time'])]
        
        # Identify spatial columns
        geo_cols = [c['name'] for c in columns if any(keyword in c['name'].lower() for keyword in ['lat', 'lon', 'coord', 'geo'])]

        return {
            "row_count": row_count,
            "columns": columns,
            "column_names": [c['name'] for c in columns],
            "samples": samples,
            "temporal_columns": time_cols,
            "spatial_columns": geo_cols,
            "has_spatial_data": len(geo_cols) > 0,
            "has_temporal_data": len(time_cols) > 0
        }

    def _infer_relationships(self, tables: List[str], cursor: sqlite3.Cursor) -> List[Dict[str, str]]:
        """Infer potential relationships between tables based on naming conventions."""
        relationships = []
        
        # Hardcoded known relationships for high accuracy
        known = [
            {
                'from_table': 'tblColonyTotals2010-2021_MayJuneCombined',
                'from_column': 'SpeciesCode',
                'to_table': 'tblSpeciesCodes',
                'to_column': 'SpeciesCode',
                'type': 'many-to-one'
            },
            {
                'from_table': 'tblColonyTotals2010-2021_MayJuneCombined',
                'from_column': 'ColonyName',
                'to_table': 'tblRWCWB_ColonyInventory_10Nov22',
                'to_column': 'ColonyName',
                'type': 'many-to-one'
            }
        ]
        relationships.extend(known)
        
        # Logic to find shared column names
        all_table_cols = {}
        for table in tables:
            cursor.execute(f"PRAGMA table_info(\"{table}\")")
            all_table_cols[table] = [row['name'] for row in cursor.fetchall()]
            
        # Basic inference: if two tables share a non-generic column name, they might be related
        generic_cols = {'id', 'notes', 'date', 'year', 'state', 'latitude', 'longitude'}
        
        for i, table_a in enumerate(tables):
            for table_b in tables[i+1:]:
                common = set(all_table_cols[table_a]) & set(all_table_cols[table_b])
                common = common - generic_cols
                
                for col in common:
                    # Check if already in known
                    if not any(r.get('from_table') == table_a and r.get('to_table') == table_b and r.get('from_column') == col for r in relationships):
                        relationships.append({
                            'from_table': table_a,
                            'to_table': table_b,
                            'from_column': col,
                            'to_column': col,
                            'type': 'potential-link'
                        })
                        
        return relationships

    def _generate_insights(self, tables_info: Dict[str, Any]) -> List[str]:
        """Generate high-level semantic insights about the database."""
        insights = []
        
        total_rows = sum(t['row_count'] for t in tables_info.values())
        insights.append(f"Database contains {len(tables_info)} tables with a total of {total_rows:,} records.")
        
        spatial_tables = [name for name, info in tables_info.items() if info['has_spatial_data']]
        if spatial_tables:
            insights.append(f"Spatial data (coordinates) discovered in: {', '.join(spatial_tables)}.")
            
        temporal_tables = [name for name, info in tables_info.items() if info['has_temporal_data']]
        if temporal_tables:
            insights.append(f"Temporal data (years/dates) discovered in: {', '.join(temporal_tables)}.")
            
        # Species specific check
        species_tables = [name for name in tables_info.keys() if 'species' in name.lower()]
        if species_tables:
            insights.append(f"Species-specific metadata found in: {', '.join(species_tables)}.")

        return insights

    def _save_metadata(self, data: Dict[str, Any]):
        """Save the discovered metadata to JSON."""
        output_path = Path(self.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"✅ Metadata saved to {output_path}")
