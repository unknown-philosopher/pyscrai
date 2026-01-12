"""Export Service for PyScrAI Forge.

Provides data export capabilities in various formats.
"""

from __future__ import annotations

import json
import csv
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ExportService:
    """Service for exporting data in various formats."""
    
    def __init__(self, db_connection):
        """Initialize the export service.
        
        Args:
            db_connection: DuckDB connection for querying data
        """
        self.db_conn = db_connection
        self.service_name = "ExportService"
    
    async def export_entities_json(
        self,
        output_path: Path,
        filters: Optional[Dict[str, Any]] = None
    ) -> Path:
        """Export entities to JSON format.
        
        Args:
            output_path: Path to output file
            filters: Optional filters (entity_type, min_relationships, etc.)
            
        Returns:
            Path to exported file
        """
        query = "SELECT id, type, label, metadata FROM entities WHERE 1=1"
        params = []
        
        if filters:
            if "entity_type" in filters:
                query += " AND type = ?"
                params.append(filters["entity_type"])
            if "min_relationships" in filters:
                # This would require a join, simplified for now
                pass
        
        rows = self.db_conn.execute(query, params).fetchall()
        
        entities = []
        for row in rows:
            entities.append({
                "id": row[0],
                "type": row[1],
                "label": row[2],
                "metadata": json.loads(row[3]) if row[3] else {},
            })
        
        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "format_version": "1.0",
            "entity_count": len(entities),
            "entities": entities,
        }
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Exported {len(entities)} entities to {output_path}")
        return output_path
    
    async def export_entities_csv(
        self,
        output_path: Path,
        filters: Optional[Dict[str, Any]] = None
    ) -> Path:
        """Export entities to CSV format.
        
        Args:
            output_path: Path to output file
            filters: Optional filters
            
        Returns:
            Path to exported file
        """
        query = "SELECT id, type, label, metadata FROM entities WHERE 1=1"
        params = []
        
        if filters:
            if "entity_type" in filters:
                query += " AND type = ?"
                params.append(filters["entity_type"])
        
        rows = self.db_conn.execute(query, params).fetchall()
        
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "type", "label", "metadata"])
            
            for row in rows:
                metadata_str = json.dumps(row[3]) if row[3] else ""
                writer.writerow([row[0], row[1], row[2], metadata_str])
        
        logger.info(f"Exported {len(rows)} entities to {output_path}")
        return output_path
    
    async def export_relationships_json(
        self,
        output_path: Path,
        filters: Optional[Dict[str, Any]] = None
    ) -> Path:
        """Export relationships to JSON format.
        
        Args:
            output_path: Path to output file
            filters: Optional filters (relationship_type, min_confidence, etc.)
            
        Returns:
            Path to exported file
        """
        query = "SELECT source, target, type, confidence, metadata FROM relationships WHERE 1=1"
        params = []
        
        if filters:
            if "relationship_type" in filters:
                query += " AND type = ?"
                params.append(filters["relationship_type"])
            if "min_confidence" in filters:
                query += " AND confidence >= ?"
                params.append(filters["min_confidence"])
        
        rows = self.db_conn.execute(query, params).fetchall()
        
        relationships = []
        for row in rows:
            relationships.append({
                "source": row[0],
                "target": row[1],
                "type": row[2],
                "confidence": float(row[3]) if row[3] else 0.0,
                "metadata": json.loads(row[4]) if row[4] else {},
            })
        
        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "format_version": "1.0",
            "relationship_count": len(relationships),
            "relationships": relationships,
        }
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Exported {len(relationships)} relationships to {output_path}")
        return output_path
    
    async def export_graph_json(
        self,
        output_path: Path,
        include_analytics: bool = True
    ) -> Path:
        """Export complete graph to JSON format.
        
        Args:
            output_path: Path to output file
            include_analytics: Whether to include graph analytics
            
        Returns:
            Path to exported file
        """
        # Export entities
        entities_query = "SELECT id, type, label, metadata FROM entities"
        entity_rows = self.db_conn.execute(entities_query).fetchall()
        
        entities = []
        for row in entity_rows:
            entities.append({
                "id": row[0],
                "type": row[1],
                "label": row[2],
                "metadata": json.loads(row[3]) if row[3] else {},
            })
        
        # Export relationships
        rel_query = "SELECT source, target, type, confidence, metadata FROM relationships"
        rel_rows = self.db_conn.execute(rel_query).fetchall()
        
        relationships = []
        for row in rel_rows:
            relationships.append({
                "source": row[0],
                "target": row[1],
                "type": row[2],
                "confidence": float(row[3]) if row[3] else 0.0,
                "metadata": json.loads(row[4]) if row[4] else {},
            })
        
        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "format_version": "1.0",
            "entity_count": len(entities),
            "relationship_count": len(relationships),
            "entities": entities,
            "relationships": relationships,
        }
        
        if include_analytics:
            # Add basic graph statistics
            export_data["analytics"] = {
                "total_nodes": len(entities),
                "total_edges": len(relationships),
                "entity_types": {},
            }
            
            # Count entity types
            for entity in entities:
                entity_type = entity["type"]
                export_data["analytics"]["entity_types"][entity_type] = \
                    export_data["analytics"]["entity_types"].get(entity_type, 0) + 1
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Exported graph with {len(entities)} entities and {len(relationships)} relationships to {output_path}")
        return output_path
    
    async def export_intelligence_report(
        self,
        output_path: Path,
        include_profiles: bool = True,
        include_narratives: bool = True,
        include_analytics: bool = True
    ) -> Path:
        """Export comprehensive intelligence report.
        
        Args:
            output_path: Path to output file
            include_profiles: Whether to include semantic profiles
            include_narratives: Whether to include narratives
            include_analytics: Whether to include graph analytics
            
        Returns:
            Path to exported file
        """
        report: Dict[str, Any] = {
            "export_timestamp": datetime.now().isoformat(),
            "format_version": "1.0",
            "report_type": "intelligence_summary",
        }
        
        # Export graph data
        graph_data = await self.export_graph_json(output_path.parent / "temp_graph.json")
        with open(graph_data, "r", encoding="utf-8") as f:
            graph_export = json.load(f)
        
        report["graph"] = {
            "entities": graph_export["entities"],
            "relationships": graph_export["relationships"],
        }
        
        if include_analytics:
            report["graph"]["analytics"] = graph_export.get("analytics", {})
        
        # Note: Semantic profiles and narratives would need to be stored
        # in the database or retrieved from the intelligence services
        # For now, we'll include placeholders
        
        if include_profiles:
            report["semantic_profiles"] = []  # Would be populated from intelligence services
        
        if include_narratives:
            report["narratives"] = []  # Would be populated from intelligence services
        
        # Clean up temp file
        graph_data.unlink()
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Exported intelligence report to {output_path}")
        return output_path
