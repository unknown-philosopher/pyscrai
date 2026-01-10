"""
Exporter - Phase 5 Export Utilities.

Provides export functionality for the ANVIL phase:
- JSON export (standard format with all entities/relationships)
- World Bible (Markdown document with organized sections)
- Database backup (SQLite copy with timestamp)
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from forge.utils.logging import get_logger

if TYPE_CHECKING:
    from forge.core.models.entity import Entity
    from forge.core.models.relationship import Relationship
    from forge.systems.storage.database import DatabaseManager

logger = get_logger("phases.p5_finalize.exporter")


class Exporter:
    """Export utilities for the Forge project.
    
    Handles exporting project data to various formats:
    - JSON for interoperability
    - Markdown for human-readable documentation
    - SQLite backup for data preservation
    """
    
    def __init__(
        self,
        project_path: Path,
        db_manager: "DatabaseManager | None" = None,
    ) -> None:
        """Initialize the Exporter.
        
        Args:
            project_path: Path to the project directory
            db_manager: Optional database manager (will load from project if not provided)
        """
        self.project_path = Path(project_path)
        self._db_manager = db_manager
        
        # Ensure export directory exists
        self.export_dir = self.project_path / "export"
        self.export_dir.mkdir(parents=True, exist_ok=True)
        
        logger.debug(f"Exporter initialized: {self.project_path}")
    
    @property
    def db(self) -> "DatabaseManager":
        """Get the database manager, loading if necessary."""
        if self._db_manager is None:
            from forge.systems.storage.database import DatabaseManager
            db_path = self.project_path / "world.db"
            self._db_manager = DatabaseManager(db_path)
        return self._db_manager
    
    # ========== JSON Export ==========
    
    async def export_json(
        self,
        filename: str | None = None,
        include_metadata: bool = True,
        pretty: bool = True,
    ) -> Path:
        """Export all entities and relationships to JSON.
        
        Args:
            filename: Optional filename (defaults to timestamped name)
            include_metadata: Whether to include export metadata
            pretty: Whether to format JSON with indentation
            
        Returns:
            Path to the exported file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = filename or f"world_export_{timestamp}.json"
        
        if not filename.endswith(".json"):
            filename = f"{filename}.json"
        
        output_path = self.export_dir / filename
        
        # Gather data
        entities = self.db.get_all_entities()
        relationships = self.db.get_all_relationships()
        
        # Build export structure
        export_data: dict[str, Any] = {}
        
        if include_metadata:
            export_data["metadata"] = {
                "exported_at": datetime.now().isoformat(),
                "project_path": str(self.project_path),
                "entity_count": len(entities),
                "relationship_count": len(relationships),
                "forge_version": "3.0.0",
            }
        
        export_data["entities"] = [
            self._entity_to_dict(e) for e in entities
        ]
        
        export_data["relationships"] = [
            self._relationship_to_dict(r) for r in relationships
        ]
        
        # Write to file
        indent = 2 if pretty else None
        output_path.write_text(
            json.dumps(export_data, indent=indent, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        
        logger.info(f"Exported JSON: {output_path} ({len(entities)} entities, {len(relationships)} relationships)")
        return output_path
    
    def _entity_to_dict(self, entity: "Entity") -> dict[str, Any]:
        """Convert an Entity to a dictionary for JSON export."""
        return {
            "id": entity.id,
            "name": entity.name,
            "entity_type": entity.entity_type.value if hasattr(entity.entity_type, "value") else str(entity.entity_type),
            "description": entity.description,
            "aliases": entity.aliases,
            "tags": entity.tags,
            "attributes": entity.attributes,
            "location_id": entity.location_id,
            "region_id": entity.region_id,
            "coordinates": list(entity.coordinates) if entity.coordinates else None,
            "layer": entity.layer.value if hasattr(entity.layer, "value") else str(entity.layer),
            "source_documents": entity.source_documents,
            "created_at": entity.created_at.isoformat() if entity.created_at else None,
            "updated_at": entity.updated_at.isoformat() if entity.updated_at else None,
        }
    
    def _relationship_to_dict(self, rel: "Relationship") -> dict[str, Any]:
        """Convert a Relationship to a dictionary for JSON export."""
        return {
            "id": rel.id,
            "source_id": rel.source_id,
            "target_id": rel.target_id,
            "relationship_type": rel.relationship_type.value if hasattr(rel.relationship_type, "value") else str(rel.relationship_type),
            "label": rel.label,
            "description": rel.description,
            "strength": rel.strength,
            "visibility": rel.visibility.value if hasattr(rel.visibility, "value") else str(rel.visibility),
            "attributes": rel.attributes,
            "source_documents": rel.source_documents,
            "created_at": rel.created_at.isoformat() if rel.created_at else None,
            "updated_at": rel.updated_at.isoformat() if rel.updated_at else None,
        }
    
    # ========== World Bible (Markdown) Export ==========
    
    async def export_world_bible(
        self,
        filename: str | None = None,
        include_toc: bool = True,
    ) -> Path:
        """Export to a Markdown World Bible document.
        
        Creates a human-readable document with organized sections
        for each entity type and their relationships.
        
        Args:
            filename: Optional filename
            include_toc: Whether to include a table of contents
            
        Returns:
            Path to the exported file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = filename or f"world_bible_{timestamp}.md"
        
        if not filename.endswith(".md"):
            filename = f"{filename}.md"
        
        output_path = self.export_dir / filename
        
        # Gather data
        entities = self.db.get_all_entities()
        relationships = self.db.get_all_relationships()
        
        # Group entities by type
        entities_by_type: dict[str, list["Entity"]] = {}
        for entity in entities:
            etype = entity.entity_type.value if hasattr(entity.entity_type, "value") else str(entity.entity_type)
            if etype not in entities_by_type:
                entities_by_type[etype] = []
            entities_by_type[etype].append(entity)
        
        # Build relationship lookup
        rel_by_entity: dict[str, list["Relationship"]] = {}
        for rel in relationships:
            if rel.source_id not in rel_by_entity:
                rel_by_entity[rel.source_id] = []
            rel_by_entity[rel.source_id].append(rel)
        
        # Build document
        lines: list[str] = []
        
        # Header
        lines.append("# World Bible")
        lines.append("")
        lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        lines.append("")
        lines.append(f"**Entities:** {len(entities)} | **Relationships:** {len(relationships)}")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # Table of Contents
        if include_toc:
            lines.append("## Table of Contents")
            lines.append("")
            for etype in sorted(entities_by_type.keys()):
                anchor = etype.lower().replace(" ", "-")
                lines.append(f"- [{etype}](#{anchor})")
            lines.append("")
            lines.append("---")
            lines.append("")
        
        # Entity sections
        for etype in sorted(entities_by_type.keys()):
            lines.append(f"## {etype}")
            lines.append("")
            
            for entity in sorted(entities_by_type[etype], key=lambda e: e.name):
                lines.extend(self._entity_to_markdown(entity, rel_by_entity.get(entity.id, [])))
                lines.append("")
            
            lines.append("---")
            lines.append("")
        
        # Write to file
        output_path.write_text("\n".join(lines), encoding="utf-8")
        
        logger.info(f"Exported World Bible: {output_path}")
        return output_path
    
    def _entity_to_markdown(
        self,
        entity: "Entity",
        relationships: list["Relationship"],
    ) -> list[str]:
        """Convert an Entity to Markdown sections."""
        lines: list[str] = []
        
        lines.append(f"### {entity.name}")
        lines.append("")
        
        # Basic info
        if entity.aliases:
            lines.append(f"**Aliases:** {', '.join(entity.aliases)}")
        
        if entity.tags:
            lines.append(f"**Tags:** {', '.join(entity.tags)}")
        
        lines.append("")
        
        # Description
        if entity.description:
            lines.append(entity.description)
            lines.append("")
        
        # Attributes
        if entity.attributes:
            lines.append("**Attributes:**")
            for key, value in entity.attributes.items():
                lines.append(f"- *{key}:* {value}")
            lines.append("")
        
        # Coordinates
        if entity.coordinates:
            lines.append(f"**Location:** ({entity.coordinates[0]:.4f}, {entity.coordinates[1]:.4f})")
            lines.append("")
        
        # Relationships
        if relationships:
            lines.append("**Relationships:**")
            for rel in relationships:
                rel_type = rel.relationship_type.value if hasattr(rel.relationship_type, "value") else str(rel.relationship_type)
                lines.append(f"- {rel_type} → {rel.target_id}")
            lines.append("")
        
        return lines
    
    # ========== Database Backup ==========
    
    async def backup_database(
        self,
        filename: str | None = None,
    ) -> Path:
        """Create a backup of the SQLite database.
        
        Args:
            filename: Optional filename for the backup
            
        Returns:
            Path to the backup file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = filename or f"world_backup_{timestamp}.db"
        
        if not filename.endswith(".db"):
            filename = f"{filename}.db"
        
        source_db = self.project_path / "world.db"
        output_path = self.export_dir / filename
        
        if not source_db.exists():
            raise FileNotFoundError(f"Database not found: {source_db}")
        
        # Copy the database file
        shutil.copy2(source_db, output_path)
        
        logger.info(f"Database backup created: {output_path}")
        return output_path
    
    # ========== Archive Export ==========
    
    async def export_archive(
        self,
        filename: str | None = None,
    ) -> Path:
        """Create a complete project archive (ZIP).
        
        Includes database, narratives, and exports.
        
        Args:
            filename: Optional filename for the archive
            
        Returns:
            Path to the archive file
        """
        import zipfile
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = filename or f"forge_archive_{timestamp}.zip"
        
        if not filename.endswith(".zip"):
            filename = f"{filename}.zip"
        
        output_path = self.export_dir / filename
        
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # Add database
            db_path = self.project_path / "world.db"
            if db_path.exists():
                zf.write(db_path, "world.db")
            
            # Add project manifest
            manifest_path = self.project_path / "project.json"
            if manifest_path.exists():
                zf.write(manifest_path, "project.json")
            
            # Add narratives
            narrative_dir = self.project_path / "narrative"
            if narrative_dir.exists():
                for md_file in narrative_dir.glob("*.md"):
                    zf.write(md_file, f"narrative/{md_file.name}")
            
            # Add custom map
            map_path = self.project_path / "map.png"
            if map_path.exists():
                zf.write(map_path, "map.png")
        
        logger.info(f"Project archive created: {output_path}")
        return output_path
    
    # ========== Import ==========
    
    async def import_json(self, json_path: Path) -> dict[str, int]:
        """Import entities and relationships from a JSON file.
        
        Args:
            json_path: Path to the JSON file
            
        Returns:
            Dictionary with import counts
        """
        from forge.core.models.entity import Entity, EntityType, LocationLayer
        from forge.core.models.relationship import Relationship, RelationType, RelationshipVisibility
        
        if not json_path.exists():
            raise FileNotFoundError(f"JSON file not found: {json_path}")
        
        data = json.loads(json_path.read_text(encoding="utf-8"))
        
        entity_count = 0
        relationship_count = 0
        
        # Import entities
        for e_data in data.get("entities", []):
            try:
                entity = Entity(
                    id=e_data["id"],
                    name=e_data["name"],
                    entity_type=EntityType(e_data.get("entity_type", "ABSTRACT")),
                    description=e_data.get("description", ""),
                    aliases=e_data.get("aliases", []),
                    tags=e_data.get("tags", []),
                    attributes=e_data.get("attributes", {}),
                    layer=LocationLayer(e_data.get("layer", "TERRESTRIAL")),
                )
                
                if e_data.get("coordinates"):
                    entity.coordinates = tuple(e_data["coordinates"])
                
                self.db.save_entity(entity)
                entity_count += 1
                
            except Exception as e:
                logger.warning(f"Failed to import entity: {e}")
        
        # Import relationships
        for r_data in data.get("relationships", []):
            try:
                rel = Relationship(
                    id=r_data["id"],
                    source_id=r_data["source_id"],
                    target_id=r_data["target_id"],
                    relationship_type=RelationType(r_data.get("relationship_type", "RELATED_TO")),
                    label=r_data.get("label", ""),
                    description=r_data.get("description", ""),
                    strength=r_data.get("strength", 0.0),
                    visibility=RelationshipVisibility(r_data.get("visibility", "PUBLIC")),
                    attributes=r_data.get("attributes", {}),
                )
                
                self.db.save_relationship(rel)
                relationship_count += 1
                
            except Exception as e:
                logger.warning(f"Failed to import relationship: {e}")
        
        logger.info(f"Imported {entity_count} entities and {relationship_count} relationships")
        
        return {
            "entities": entity_count,
            "relationships": relationship_count,
        }
