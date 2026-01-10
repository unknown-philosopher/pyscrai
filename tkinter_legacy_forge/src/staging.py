"""Staging Service - Manage phase artifacts in the staging directory.

Each phase of the PyScrAI 2.0 pipeline produces staging artifacts:
- FOUNDRY: entities_staging.json
- LOOM: graph_staging.json (entities + relationships)
- CHRONICLE: narrative_report.md
- CARTOGRAPHY: spatial_metadata.json
- ANVIL: (commits to world.db)

This service handles reading/writing these artifacts with validation.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from pyscrai_core import Entity, Relationship

logger = logging.getLogger(__name__)


# Artifact filenames by phase
STAGING_ARTIFACTS = {
    "foundry": "entities_staging.json",
    "loom": "graph_staging.json",
    "chronicle": "narrative_report.md",
    "cartography": "spatial_metadata.json",
}


class StagingService:
    """Manages staging artifacts for the pipeline phases."""
    
    def __init__(self, project_path: Path):
        """Initialize staging service for a project.
        
        Args:
            project_path: Path to the project directory
        """
        self.project_path = Path(project_path)
        self.staging_path = self.project_path / "staging"
        
        # Ensure staging directory exists
        self.staging_path.mkdir(exist_ok=True)
    
    def get_artifact_path(self, phase: str) -> Path:
        """Get the path to a phase's staging artifact.
        
        Args:
            phase: Phase name (foundry, loom, chronicle, cartography)
            
        Returns:
            Path to the artifact file
        """
        filename = STAGING_ARTIFACTS.get(phase.lower())
        if not filename:
            raise ValueError(f"Unknown phase: {phase}")
        return self.staging_path / filename
    
    def artifact_exists(self, phase: str) -> bool:
        """Check if a phase's artifact exists.
        
        Args:
            phase: Phase name
            
        Returns:
            True if artifact file exists
        """
        return self.get_artifact_path(phase).exists()
    
    # =========================================================================
    # FOUNDRY: Entity Staging
    # =========================================================================
    
    def save_entities_staging(
        self,
        entities: list["Entity"],
        source_text: str = "",
        metadata: Optional[dict] = None
    ) -> Path:
        """Save entities to staging for the Foundry phase.
        
        Args:
            entities: List of Entity objects
            source_text: Original source text (for reference)
            metadata: Optional additional metadata
            
        Returns:
            Path to the saved artifact
        """
        artifact_path = self.get_artifact_path("foundry")
        
        data = {
            "phase": "foundry",
            "created_at": datetime.now(UTC).isoformat(),
            "entity_count": len(entities),
            "source_text_preview": source_text[:500] if source_text else "",
            "metadata": metadata or {},
            "entities": [json.loads(e.model_dump_json()) for e in entities]
        }
        
        with open(artifact_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved {len(entities)} entities to {artifact_path}")
        return artifact_path
    
    def load_entities_staging(self) -> tuple[list[dict], dict]:
        """Load entities from Foundry staging.
        
        Returns:
            Tuple of (entity_dicts, metadata)
        """
        artifact_path = self.get_artifact_path("foundry")
        
        if not artifact_path.exists():
            logger.warning("No foundry staging artifact found")
            return [], {}
        
        with open(artifact_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        entities = data.get("entities", [])
        metadata = {
            "created_at": data.get("created_at"),
            "entity_count": data.get("entity_count"),
            "source_text_preview": data.get("source_text_preview"),
            **data.get("metadata", {})
        }
        
        return entities, metadata
    
    # =========================================================================
    # LOOM: Graph Staging
    # =========================================================================
    
    def save_graph_staging(
        self,
        entities: list["Entity"],
        relationships: list["Relationship"],
        layout_data: Optional[dict] = None,
        metadata: Optional[dict] = None
    ) -> Path:
        """Save entities and relationships to staging for the Loom phase.
        
        Args:
            entities: List of Entity objects
            relationships: List of Relationship objects
            layout_data: Optional node positions from graph layout
            metadata: Optional additional metadata
            
        Returns:
            Path to the saved artifact
        """
        artifact_path = self.get_artifact_path("loom")
        
        data = {
            "phase": "loom",
            "created_at": datetime.now(UTC).isoformat(),
            "entity_count": len(entities),
            "relationship_count": len(relationships),
            "metadata": metadata or {},
            "layout": layout_data or {},
            "entities": [json.loads(e.model_dump_json()) for e in entities],
            "relationships": [json.loads(r.model_dump_json()) for r in relationships]
        }
        
        with open(artifact_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved graph ({len(entities)} entities, {len(relationships)} relationships) to {artifact_path}")
        return artifact_path
    
    def load_graph_staging(self) -> tuple[list[dict], list[dict], dict]:
        """Load graph from Loom staging.
        
        Returns:
            Tuple of (entity_dicts, relationship_dicts, metadata)
        """
        artifact_path = self.get_artifact_path("loom")
        
        if not artifact_path.exists():
            # Fall back to foundry if loom doesn't exist yet
            if self.artifact_exists("foundry"):
                entities, meta = self.load_entities_staging()
                return entities, [], meta
            logger.warning("No loom or foundry staging artifact found")
            return [], [], {}
        
        with open(artifact_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        entities = data.get("entities", [])
        relationships = data.get("relationships", [])
        metadata = {
            "created_at": data.get("created_at"),
            "entity_count": data.get("entity_count"),
            "relationship_count": data.get("relationship_count"),
            "layout": data.get("layout", {}),
            **data.get("metadata", {})
        }
        
        return entities, relationships, metadata
    
    # =========================================================================
    # CHRONICLE: Narrative Staging
    # =========================================================================
    
    def save_narrative_staging(
        self,
        narrative_text: str,
        blueprint_name: str = "default",
        focus: str = "",
        fact_check_results: Optional[list[dict]] = None,
        metadata: Optional[dict] = None
    ) -> Path:
        """Save narrative report to staging for the Chronicle phase.
        
        Args:
            narrative_text: Generated narrative markdown
            blueprint_name: Name of the blueprint template used
            focus: Focus area for the narrative
            fact_check_results: Optional fact-checking annotations
            metadata: Optional additional metadata
            
        Returns:
            Path to the saved artifact
        """
        artifact_path = self.get_artifact_path("chronicle")
        
        # For markdown, we embed metadata as YAML frontmatter
        frontmatter = {
            "phase": "chronicle",
            "created_at": datetime.now(UTC).isoformat(),
            "blueprint": blueprint_name,
            "focus": focus,
            "fact_check_passed": all(r.get("valid", True) for r in (fact_check_results or [])),
            **(metadata or {})
        }
        
        # Build markdown with frontmatter
        frontmatter_yaml = "\n".join(f"{k}: {json.dumps(v)}" for k, v in frontmatter.items())
        content = f"---\n{frontmatter_yaml}\n---\n\n{narrative_text}"
        
        with open(artifact_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Also save fact-check results as sidecar JSON if present
        if fact_check_results:
            sidecar_path = artifact_path.with_suffix(".facts.json")
            with open(sidecar_path, 'w', encoding='utf-8') as f:
                json.dump(fact_check_results, f, indent=2)
        
        logger.info(f"Saved narrative report to {artifact_path}")
        return artifact_path
    
    def load_narrative_staging(self) -> tuple[str, dict]:
        """Load narrative from Chronicle staging.
        
        Returns:
            Tuple of (narrative_text, metadata)
        """
        artifact_path = self.get_artifact_path("chronicle")
        
        if not artifact_path.exists():
            logger.warning("No chronicle staging artifact found")
            return "", {}
        
        with open(artifact_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse frontmatter if present
        metadata = {}
        narrative_text = content
        
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                # Parse YAML-like frontmatter
                for line in parts[1].strip().split("\n"):
                    if ": " in line:
                        key, value = line.split(": ", 1)
                        try:
                            metadata[key] = json.loads(value)
                        except json.JSONDecodeError:
                            metadata[key] = value
                narrative_text = parts[2].strip()
        
        return narrative_text, metadata
    
    # =========================================================================
    # CARTOGRAPHY: Spatial Staging
    # =========================================================================
    
    def save_spatial_staging(
        self,
        entity_positions: dict[str, tuple[float, float]],
        regions: Optional[list[dict]] = None,
        metadata: Optional[dict] = None
    ) -> Path:
        """Save spatial metadata to staging for the Cartography phase.
        
        Args:
            entity_positions: Dict mapping entity_id to (x, y) coordinates
            regions: Optional list of region definitions
            metadata: Optional additional metadata
            
        Returns:
            Path to the saved artifact
        """
        artifact_path = self.get_artifact_path("cartography")
        
        data = {
            "phase": "cartography",
            "created_at": datetime.now(UTC).isoformat(),
            "entity_count": len(entity_positions),
            "region_count": len(regions) if regions else 0,
            "metadata": metadata or {},
            "positions": {eid: {"x": x, "y": y} for eid, (x, y) in entity_positions.items()},
            "regions": regions or []
        }
        
        with open(artifact_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved spatial metadata ({len(entity_positions)} positions) to {artifact_path}")
        return artifact_path
    
    def load_spatial_staging(self) -> tuple[dict[str, tuple[float, float]], list[dict], dict]:
        """Load spatial metadata from Cartography staging.
        
        Returns:
            Tuple of (entity_positions, regions, metadata)
        """
        artifact_path = self.get_artifact_path("cartography")
        
        if not artifact_path.exists():
            logger.warning("No cartography staging artifact found")
            return {}, [], {}
        
        with open(artifact_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        positions_raw = data.get("positions", {})
        positions = {eid: (p["x"], p["y"]) for eid, p in positions_raw.items()}
        regions = data.get("regions", [])
        metadata = {
            "created_at": data.get("created_at"),
            "entity_count": data.get("entity_count"),
            "region_count": data.get("region_count"),
            **data.get("metadata", {})
        }
        
        return positions, regions, metadata
    
    # =========================================================================
    # SOURCE DATA POOL: Raw imported files management
    # =========================================================================
    
    def get_sources_path(self) -> Path:
        """Get the path to the sources directory.
        
        Returns:
            Path to the sources directory within staging
        """
        sources_path = self.staging_path / "sources"
        sources_path.mkdir(exist_ok=True)
        return sources_path
    
    def get_sources_manifest_path(self) -> Path:
        """Get the path to the sources manifest file.
        
        Returns:
            Path to sources_manifest.json
        """
        return self.staging_path / "sources_manifest.json"
    
    def save_source_file(
        self,
        file_path: Path,
        text_content: str,
        metadata: Optional[dict] = None,
        active: bool = True
    ) -> str:
        """Save a source file to the sources pool.
        
        Args:
            file_path: Original file path (used for naming)
            text_content: Extracted text content
            metadata: Optional file metadata
            active: Whether the source is active for extraction
            
        Returns:
            Source ID for the saved file
        """
        import hashlib
        from datetime import UTC, datetime
        
        sources_path = self.get_sources_path()
        
        # Generate a unique source ID based on filename and content hash
        content_hash = hashlib.md5(text_content.encode()).hexdigest()[:8]
        source_id = f"{file_path.stem}_{content_hash}"
        
        # Save the text content
        source_file = sources_path / f"{source_id}.txt"
        with open(source_file, 'w', encoding='utf-8') as f:
            f.write(text_content)
        
        # Update the manifest
        manifest = self.load_sources_manifest()
        manifest["sources"][source_id] = {
            "id": source_id,
            "original_filename": file_path.name,
            "original_path": str(file_path),
            "text_file": source_file.name,
            "char_count": len(text_content),
            "added_at": datetime.now(UTC).isoformat(),
            "active": active,
            "metadata": metadata or {},
            "extracted": False,  # Will be True after extraction
        }
        manifest["updated_at"] = datetime.now(UTC).isoformat()
        
        self._save_sources_manifest(manifest)
        
        logger.info(f"Saved source file: {source_id} ({len(text_content)} chars)")
        return source_id
    
    def load_sources_manifest(self) -> dict:
        """Load the sources manifest.
        
        Returns:
            Sources manifest dict with 'sources' key
        """
        manifest_path = self.get_sources_manifest_path()
        
        if not manifest_path.exists():
            return {
                "version": "2.0",
                "created_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
                "sources": {}
            }
        
        with open(manifest_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_sources_manifest(self, manifest: dict) -> None:
        """Save the sources manifest."""
        manifest_path = self.get_sources_manifest_path()
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2)
    
    def get_source_text(self, source_id: str) -> str:
        """Get the text content of a source file.
        
        Args:
            source_id: Source ID
            
        Returns:
            Text content of the source
        """
        manifest = self.load_sources_manifest()
        source_info = manifest["sources"].get(source_id)
        
        if not source_info:
            raise ValueError(f"Source not found: {source_id}")
        
        source_file = self.get_sources_path() / source_info["text_file"]
        with open(source_file, 'r', encoding='utf-8') as f:
            return f.read()
    
    def get_active_sources(self) -> list[dict]:
        """Get list of active source files.
        
        Returns:
            List of source info dicts for active sources
        """
        manifest = self.load_sources_manifest()
        return [
            info for info in manifest["sources"].values()
            if info.get("active", True)
        ]
    
    def get_all_sources(self) -> list[dict]:
        """Get list of all source files.
        
        Returns:
            List of all source info dicts
        """
        manifest = self.load_sources_manifest()
        return list(manifest["sources"].values())
    
    def set_source_active(self, source_id: str, active: bool) -> None:
        """Set a source file's active state.
        
        Args:
            source_id: Source ID
            active: Whether the source should be active
        """
        manifest = self.load_sources_manifest()
        
        if source_id not in manifest["sources"]:
            raise ValueError(f"Source not found: {source_id}")
        
        manifest["sources"][source_id]["active"] = active
        manifest["updated_at"] = datetime.now(UTC).isoformat()
        
        self._save_sources_manifest(manifest)
        logger.info(f"Source {source_id} set to {'active' if active else 'inactive'}")
    
    def mark_source_extracted(self, source_id: str) -> None:
        """Mark a source as having been extracted.
        
        Args:
            source_id: Source ID
        """
        manifest = self.load_sources_manifest()
        
        if source_id in manifest["sources"]:
            manifest["sources"][source_id]["extracted"] = True
            manifest["sources"][source_id]["extracted_at"] = datetime.now(UTC).isoformat()
            manifest["updated_at"] = datetime.now(UTC).isoformat()
            self._save_sources_manifest(manifest)
    
    def delete_source(self, source_id: str) -> None:
        """Delete a source file from the pool.
        
        Args:
            source_id: Source ID
        """
        manifest = self.load_sources_manifest()
        
        if source_id not in manifest["sources"]:
            raise ValueError(f"Source not found: {source_id}")
        
        source_info = manifest["sources"][source_id]
        source_file = self.get_sources_path() / source_info["text_file"]
        
        # Delete the text file
        if source_file.exists():
            source_file.unlink()
        
        # Remove from manifest
        del manifest["sources"][source_id]
        manifest["updated_at"] = datetime.now(UTC).isoformat()
        
        self._save_sources_manifest(manifest)
        logger.info(f"Deleted source: {source_id}")
    
    def get_combined_source_text(self, source_ids: Optional[list[str]] = None) -> str:
        """Get combined text from multiple sources.
        
        Args:
            source_ids: List of source IDs. If None, uses all active sources.
            
        Returns:
            Combined text with source separators
        """
        if source_ids is None:
            sources = self.get_active_sources()
            source_ids = [s["id"] for s in sources]
        
        texts = []
        for source_id in source_ids:
            try:
                text = self.get_source_text(source_id)
                manifest = self.load_sources_manifest()
                source_info = manifest["sources"].get(source_id, {})
                filename = source_info.get("original_filename", source_id)
                texts.append(f"--- SOURCE: {filename} ---\n{text}")
            except Exception as e:
                logger.warning(f"Failed to load source {source_id}: {e}")
        
        return "\n\n".join(texts)
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def get_pipeline_status(self) -> dict[str, bool]:
        """Get completion status of each phase based on artifact existence.
        
        Returns:
            Dict mapping phase name to completion status
        """
        return {
            phase: self.artifact_exists(phase)
            for phase in STAGING_ARTIFACTS.keys()
        }
    
    def clear_staging(self, phase: Optional[str] = None) -> None:
        """Clear staging artifacts.
        
        Args:
            phase: If provided, only clear that phase's artifact.
                   If None, clear all staging artifacts.
        """
        if phase:
            artifact_path = self.get_artifact_path(phase)
            if artifact_path.exists():
                artifact_path.unlink()
                logger.info(f"Cleared staging artifact: {artifact_path}")
        else:
            for phase_name in STAGING_ARTIFACTS.keys():
                artifact_path = self.get_artifact_path(phase_name)
                if artifact_path.exists():
                    artifact_path.unlink()
            logger.info("Cleared all staging artifacts")
