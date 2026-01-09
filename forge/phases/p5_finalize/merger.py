"""
Entity Merger for Phase 5: Finalize (UI: ANVIL).

Handles merging of duplicate entities with attribute reconciliation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from forge.core.models.entity import Entity
from forge.core.events.mutations import MergeApprovedEvent
from forge.utils.logging import get_logger

if TYPE_CHECKING:
    from forge.app.state import ForgeState

logger = get_logger("p5_finalize.merger")


@dataclass
class MergePreview:
    """Preview of a merge operation.
    
    Shows what the merged entity would look like before committing.
    """
    
    primary_id: str
    secondary_id: str
    merged_name: str
    merged_aliases: list[str]
    merged_description: str
    merged_attributes: dict[str, Any]
    merged_provenance: list[str]
    conflicts: list[str] = field(default_factory=list)
    
    @property
    def has_conflicts(self) -> bool:
        """Check if there are attribute conflicts."""
        return len(self.conflicts) > 0


class EntityMerger:
    """Handles entity merge operations.
    
    Supports:
    - Preview merges before committing
    - Conflict detection for incompatible attributes
    - Relationship preservation during merge
    - Full event logging
    
    Usage:
        merger = EntityMerger(state)
        
        # Preview a merge
        preview = merger.preview_merge(entity_a, entity_b)
        print(f"Conflicts: {preview.conflicts}")
        
        # Execute the merge
        merged = merger.merge(entity_a, entity_b)
    """
    
    def __init__(self, state: "ForgeState"):
        """Initialize the merger.
        
        Args:
            state: Application state
        """
        self.state = state
        self._events: list = []
    
    def preview_merge(
        self,
        primary: Entity,
        secondary: Entity,
        prefer_primary: bool = True,
    ) -> MergePreview:
        """Preview a merge without executing it.
        
        Args:
            primary: Entity to keep as the base
            secondary: Entity to merge into primary
            prefer_primary: Whether to prefer primary values for conflicts
            
        Returns:
            MergePreview showing the result
        """
        conflicts = []
        
        # Merge aliases (combine unique values)
        combined_aliases = list(set(
            primary.aliases + secondary.aliases + [secondary.name]
        ))
        if primary.name in combined_aliases:
            combined_aliases.remove(primary.name)
        
        # Merge descriptions
        if secondary.description and secondary.description != primary.description:
            if primary.description:
                merged_description = f"{primary.description}\n\n{secondary.description}"
            else:
                merged_description = secondary.description
        else:
            merged_description = primary.description
        
        # Merge attributes with conflict detection
        merged_attributes = {}
        all_keys = set(primary.attributes.keys()) | set(secondary.attributes.keys())
        
        for key in all_keys:
            p_val = primary.attributes.get(key)
            s_val = secondary.attributes.get(key)
            
            if p_val is not None and s_val is not None and p_val != s_val:
                # Conflict detected
                conflicts.append(
                    f"Attribute '{key}': primary='{p_val}' vs secondary='{s_val}'"
                )
                merged_attributes[key] = p_val if prefer_primary else s_val
            elif p_val is not None:
                merged_attributes[key] = p_val
            else:
                merged_attributes[key] = s_val
        
        # Merge provenance
        merged_provenance = list(set(primary.provenance + secondary.provenance))
        
        return MergePreview(
            primary_id=primary.id,
            secondary_id=secondary.id,
            merged_name=primary.name,
            merged_aliases=combined_aliases,
            merged_description=merged_description,
            merged_attributes=merged_attributes,
            merged_provenance=merged_provenance,
            conflicts=conflicts,
        )
    
    def merge(
        self,
        primary: Entity,
        secondary: Entity,
        prefer_primary: bool = True,
        reason: str = "Manual merge",
    ) -> Entity:
        """Merge two entities.
        
        Args:
            primary: Entity to keep as the base
            secondary: Entity to merge into primary
            prefer_primary: Whether to prefer primary values for conflicts
            reason: Reason for the merge
            
        Returns:
            The merged entity
        """
        # Get preview
        preview = self.preview_merge(primary, secondary, prefer_primary)
        
        # Create merged entity
        merged = Entity(
            id=primary.id,
            name=preview.merged_name,
            type=primary.type,
            description=preview.merged_description,
            aliases=preview.merged_aliases,
            attributes=preview.merged_attributes,
            provenance=preview.merged_provenance,
            created_at=primary.created_at,
            updated_at=datetime.now(UTC),
            embedding_row_id=primary.embedding_row_id,
        )
        
        # Update relationships pointing to secondary
        self._transfer_relationships(secondary.id, primary.id)
        
        # Save merged entity
        self.state.db.save_entity(merged)
        
        # Update vector memory
        self.state.memory.update_entity(merged)
        
        # Delete secondary
        self.state.db.delete_entity(secondary.id)
        self.state.memory.remove_entity(secondary.id)
        
        # Log event
        event = MergeApprovedEvent(
            entity_id=merged.id,
            merged_ids=[primary.id, secondary.id],
            details={
                "reason": reason,
                "conflicts": preview.conflicts,
            },
        )
        self._events.append(event)
        self.state.db.log_event(event)
        
        self.state.mark_dirty()
        logger.info(
            f"Merged entities: '{secondary.name}' into '{primary.name}'"
        )
        
        return merged
    
    def _transfer_relationships(
        self,
        from_entity_id: str,
        to_entity_id: str,
    ) -> int:
        """Transfer relationships from one entity to another.
        
        Args:
            from_entity_id: Entity to transfer from
            to_entity_id: Entity to transfer to
            
        Returns:
            Number of relationships transferred
        """
        relationships = self.state.db.get_relationships_for_entity(from_entity_id)
        transferred = 0
        
        for rel in relationships:
            if rel.source_id == from_entity_id:
                rel.source_id = to_entity_id
            if rel.target_id == from_entity_id:
                rel.target_id = to_entity_id
            
            # Check for duplicate relationships
            existing = self.state.db.get_relationships_for_entity(to_entity_id)
            is_duplicate = any(
                e.source_id == rel.source_id and
                e.target_id == rel.target_id and
                e.type == rel.type
                for e in existing
            )
            
            if not is_duplicate:
                self.state.db.save_relationship(rel)
                transferred += 1
        
        return transferred
    
    def find_similar(
        self,
        entity: Entity,
        threshold: float = 0.8,
        top_k: int = 10,
    ) -> list[tuple[Entity, float]]:
        """Find entities similar to the given entity.
        
        Args:
            entity: Entity to find similar to
            threshold: Minimum similarity threshold
            top_k: Maximum number of results
            
        Returns:
            List of (entity, similarity) tuples
        """
        results = self.state.memory.find_near_duplicates(
            entity,
            threshold=threshold,
            top_k=top_k,
        )
        
        similar = []
        for entity_id, score in results:
            if entity_id != entity.id:
                found = self.state.db.get_entity(entity_id)
                if found:
                    similar.append((found, score))
        
        return similar
    
    def suggest_merges(
        self,
        threshold: float = 0.85,
    ) -> list[tuple[Entity, Entity, float]]:
        """Suggest entities that might be duplicates.
        
        Args:
            threshold: Minimum similarity for suggestions
            
        Returns:
            List of (entity_a, entity_b, similarity) tuples
        """
        suggestions = []
        seen_pairs = set()
        
        for entity in self.state.db.get_all_entities():
            similar = self.find_similar(entity, threshold=threshold, top_k=5)
            
            for other, score in similar:
                # Avoid duplicate pairs
                pair_key = tuple(sorted([entity.id, other.id]))
                if pair_key not in seen_pairs:
                    seen_pairs.add(pair_key)
                    suggestions.append((entity, other, score))
        
        # Sort by similarity descending
        suggestions.sort(key=lambda x: x[2], reverse=True)
        return suggestions
    
    def get_events(self) -> list:
        """Get events from this session."""
        return self._events.copy()
