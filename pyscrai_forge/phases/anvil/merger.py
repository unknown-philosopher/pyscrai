"""Phase 5: ANVIL - Smart Merge Engine.

The SmartMergeEngine handles merging staging data into the canonical
world.db with conflict detection and resolution support.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple

if TYPE_CHECKING:
    from pyscrai_core import Entity, Relationship

logger = logging.getLogger(__name__)


class MergeAction(Enum):
    """Actions for merge conflicts."""
    CREATE = "create"      # New entity/relationship
    UPDATE = "update"      # Update existing
    MERGE = "merge"        # Merge with existing (combine attributes)
    SKIP = "skip"          # Skip this item
    DELETE = "delete"      # Delete from staging


class ConflictType(Enum):
    """Types of merge conflicts."""
    DUPLICATE_NAME = "duplicate_name"
    DUPLICATE_ID = "duplicate_id"
    ATTRIBUTE_MISMATCH = "attribute_mismatch"
    ORPHANED_RELATIONSHIP = "orphaned_relationship"
    SIMILARITY_THRESHOLD = "similarity_threshold"


@dataclass
class MergeConflict:
    """A conflict detected during merge."""
    conflict_type: ConflictType
    staging_id: str
    canon_id: Optional[str] = None
    description: str = ""
    similarity: float = 0.0  # 0.0 to 1.0
    suggested_action: MergeAction = MergeAction.CREATE
    details: dict = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


@dataclass
class MergeResult:
    """Result of a merge operation."""
    created: List[str]  # IDs of created entities
    updated: List[str]  # IDs of updated entities
    merged: List[str]   # IDs of merged entities
    skipped: List[str]  # IDs of skipped entities
    conflicts: List[MergeConflict]
    
    @property
    def total_processed(self) -> int:
        return len(self.created) + len(self.updated) + len(self.merged) + len(self.skipped)


class SmartMergeEngine:
    """Engine for merging staging data into canonical database.
    
    Features:
    - Duplicate detection by name/ID
    - Semantic similarity comparison (via MemoryService)
    - Attribute-level diff generation
    - Conflict resolution workflow
    - Provenance tracking
    """
    
    def __init__(
        self,
        similarity_threshold: float = 0.8,
        memory_service: Optional["MemoryService"] = None
    ):
        """Initialize the merge engine.
        
        Args:
            similarity_threshold: Threshold for semantic similarity (0.0-1.0)
            memory_service: Optional MemoryService for semantic comparison
        """
        self.similarity_threshold = similarity_threshold
        self.memory_service = memory_service
    
    def analyze_merge(
        self,
        staging_entities: List["Entity"],
        canon_entities: List["Entity"],
        staging_relationships: Optional[List["Relationship"]] = None,
        canon_relationships: Optional[List["Relationship"]] = None
    ) -> List[MergeConflict]:
        """Analyze staging data for potential merge conflicts.
        
        Args:
            staging_entities: Entities from staging
            canon_entities: Entities in canonical DB
            staging_relationships: Relationships from staging
            canon_relationships: Relationships in canonical DB
            
        Returns:
            List of detected conflicts
        """
        conflicts = []
        
        # Build lookup tables
        canon_by_id = {e.id: e for e in canon_entities}
        canon_by_name = {}
        for e in canon_entities:
            name = e.descriptor.name.lower() if hasattr(e, "descriptor") else ""
            if name:
                canon_by_name.setdefault(name, []).append(e)
        
        staging_relationships = staging_relationships or []
        canon_relationships = canon_relationships or []
        
        # Check each staging entity
        for staging_entity in staging_entities:
            staging_name = staging_entity.descriptor.name.lower() if hasattr(staging_entity, "descriptor") else ""
            
            # Check for ID collision
            if staging_entity.id in canon_by_id:
                canon_entity = canon_by_id[staging_entity.id]
                conflicts.append(MergeConflict(
                    conflict_type=ConflictType.DUPLICATE_ID,
                    staging_id=staging_entity.id,
                    canon_id=canon_entity.id,
                    description=f"Entity ID '{staging_entity.id}' already exists in database",
                    similarity=1.0,
                    suggested_action=MergeAction.UPDATE
                ))
                continue
            
            # Check for name collision
            if staging_name and staging_name in canon_by_name:
                for canon_entity in canon_by_name[staging_name]:
                    similarity = self._calculate_similarity(staging_entity, canon_entity)
                    
                    if similarity >= self.similarity_threshold:
                        conflicts.append(MergeConflict(
                            conflict_type=ConflictType.DUPLICATE_NAME,
                            staging_id=staging_entity.id,
                            canon_id=canon_entity.id,
                            description=f"Entity name '{staging_name}' matches existing entity",
                            similarity=similarity,
                            suggested_action=MergeAction.MERGE if similarity > 0.9 else MergeAction.SKIP,
                            details=self._generate_diff(staging_entity, canon_entity)
                        ))
                    elif similarity >= 0.5:
                        conflicts.append(MergeConflict(
                            conflict_type=ConflictType.SIMILARITY_THRESHOLD,
                            staging_id=staging_entity.id,
                            canon_id=canon_entity.id,
                            description=f"Entity '{staging_name}' similar to existing '{canon_entity.descriptor.name}'",
                            similarity=similarity,
                            suggested_action=MergeAction.CREATE,  # User should review
                            details=self._generate_diff(staging_entity, canon_entity)
                        ))
        
        # Check relationships for orphaned references
        staging_entity_ids = {e.id for e in staging_entities}
        canon_entity_ids = {e.id for e in canon_entities}
        all_entity_ids = staging_entity_ids | canon_entity_ids
        
        for rel in staging_relationships:
            if rel.source_id not in all_entity_ids:
                conflicts.append(MergeConflict(
                    conflict_type=ConflictType.ORPHANED_RELATIONSHIP,
                    staging_id=rel.id if hasattr(rel, 'id') else f"{rel.source_id}->{rel.target_id}",
                    description=f"Relationship source '{rel.source_id}' not found",
                    suggested_action=MergeAction.SKIP
                ))
            
            if rel.target_id not in all_entity_ids:
                conflicts.append(MergeConflict(
                    conflict_type=ConflictType.ORPHANED_RELATIONSHIP,
                    staging_id=rel.id if hasattr(rel, 'id') else f"{rel.source_id}->{rel.target_id}",
                    description=f"Relationship target '{rel.target_id}' not found",
                    suggested_action=MergeAction.SKIP
                ))
        
        return conflicts
    
    def _calculate_similarity(
        self,
        entity1: "Entity",
        entity2: "Entity"
    ) -> float:
        """Calculate similarity between two entities.
        
        Args:
            entity1: First entity
            entity2: Second entity
            
        Returns:
            Similarity score (0.0 to 1.0)
        """
        # If we have a memory service, use semantic similarity
        if self.memory_service:
            try:
                text1 = self._entity_to_text(entity1)
                text2 = self._entity_to_text(entity2)
                return self.memory_service.calculate_similarity(text1, text2)
            except Exception as e:
                logger.warning(f"Semantic similarity failed: {e}")
        
        # Fallback to simple text matching
        return self._simple_similarity(entity1, entity2)
    
    def _simple_similarity(
        self,
        entity1: "Entity",
        entity2: "Entity"
    ) -> float:
        """Calculate simple text-based similarity."""
        text1 = self._entity_to_text(entity1).lower()
        text2 = self._entity_to_text(entity2).lower()
        
        # Jaccard similarity on words
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def _entity_to_text(self, entity: "Entity") -> str:
        """Convert entity to text representation for comparison."""
        parts = []
        
        if hasattr(entity, "descriptor"):
            desc = entity.descriptor
            if hasattr(desc, "name"):
                parts.append(desc.name)
            if hasattr(desc, "description"):
                parts.append(desc.description or "")
            if hasattr(desc, "aliases"):
                parts.extend(desc.aliases or [])
        
        return " ".join(parts)
    
    def _generate_diff(
        self,
        staging_entity: "Entity",
        canon_entity: "Entity"
    ) -> dict:
        """Generate attribute-level diff between entities."""
        diff = {
            "staging": {},
            "canon": {},
            "differences": []
        }
        
        # Compare descriptors
        if hasattr(staging_entity, "descriptor") and hasattr(canon_entity, "descriptor"):
            staging_desc = staging_entity.descriptor
            canon_desc = canon_entity.descriptor
            
            # Compare name
            if hasattr(staging_desc, "name") and hasattr(canon_desc, "name"):
                if staging_desc.name != canon_desc.name:
                    diff["differences"].append({
                        "attribute": "name",
                        "staging": staging_desc.name,
                        "canon": canon_desc.name
                    })
            
            # Compare description
            staging_description = getattr(staging_desc, "description", "")
            canon_description = getattr(canon_desc, "description", "")
            if staging_description != canon_description:
                diff["differences"].append({
                    "attribute": "description",
                    "staging": staging_description[:200] + "..." if len(staging_description) > 200 else staging_description,
                    "canon": canon_description[:200] + "..." if len(canon_description) > 200 else canon_description
                })
            
            # Compare entity type
            staging_type = getattr(staging_desc, "entity_type", None)
            canon_type = getattr(canon_desc, "entity_type", None)
            if staging_type != canon_type:
                diff["differences"].append({
                    "attribute": "entity_type",
                    "staging": str(staging_type),
                    "canon": str(canon_type)
                })
        
        return diff
    
    def execute_merge(
        self,
        staging_entities: List["Entity"],
        staging_relationships: List["Relationship"],
        resolutions: Dict[str, MergeAction],
        db_path: "Path"
    ) -> MergeResult:
        """Execute the merge with resolved conflicts.
        
        Args:
            staging_entities: Entities to merge
            staging_relationships: Relationships to merge
            resolutions: Dict mapping staging_id to MergeAction
            db_path: Path to the database
            
        Returns:
            MergeResult with details of the operation
        """
        result = MergeResult(
            created=[],
            updated=[],
            merged=[],
            skipped=[],
            conflicts=[]
        )
        
        try:
            from pyscrai_forge.src import storage
            
            for entity in staging_entities:
                action = resolutions.get(entity.id, MergeAction.CREATE)
                
                if action == MergeAction.CREATE:
                    storage.save_entity(db_path, entity)
                    result.created.append(entity.id)
                    
                elif action == MergeAction.UPDATE:
                    storage.save_entity(db_path, entity)  # Overwrites existing
                    result.updated.append(entity.id)
                    
                elif action == MergeAction.SKIP:
                    result.skipped.append(entity.id)
                    
                # MERGE would require more complex logic to combine attributes
            
            # Save relationships (skip orphaned ones)
            entity_ids = {e.id for e in staging_entities if resolutions.get(e.id) != MergeAction.SKIP}
            existing_entities = storage.load_all_entities(db_path)
            entity_ids.update(e.id for e in existing_entities)
            
            for rel in staging_relationships:
                if rel.source_id in entity_ids and rel.target_id in entity_ids:
                    storage.save_relationship(db_path, rel)
            
            logger.info(f"Merge complete: {result.total_processed} entities processed")
            
        except Exception as e:
            logger.error(f"Merge execution failed: {e}")
            raise
        
        return result
    
    def get_merge_summary(self, conflicts: List[MergeConflict]) -> dict:
        """Get summary of merge conflicts by type.
        
        Args:
            conflicts: List of detected conflicts
            
        Returns:
            Summary dict
        """
        summary = {
            "total": len(conflicts),
            "by_type": {},
            "by_action": {}
        }
        
        for conflict in conflicts:
            ct = conflict.conflict_type.value
            summary["by_type"][ct] = summary["by_type"].get(ct, 0) + 1
            
            action = conflict.suggested_action.value
            summary["by_action"][action] = summary["by_action"].get(action, 0) + 1
        
        return summary

