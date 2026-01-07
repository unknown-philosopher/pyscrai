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
