"""
Phase 5: Finalize (UI: ANVIL) - Entity Management and Editing. 
Orchestrator for the Finalize phase.

Coordinates entity management operations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable

from forge.core.models.entity import Entity, EntityType
from forge.phases.p5_finalize.manager import EntityManager
from forge.phases.p5_finalize.merger import EntityMerger, MergePreview
from forge.utils.logging import get_logger

if TYPE_CHECKING:
    from forge.app.state import ForgeState

logger = get_logger("p5_finalize")


class FinalizeMode(str, Enum):
    """Current mode of the Finalize phase."""
    BROWSE = "browse"
    EDIT = "edit"
    MERGE = "merge"
    SEARCH = "search"


@dataclass
class FinalizeContext:
    """Context for Finalize operations."""
    
    mode: FinalizeMode = FinalizeMode.BROWSE
    selected_entity_id: str | None = None
    filter_type: EntityType | None = None
    search_query: str = ""
    merge_candidates: list[tuple[Entity, Entity, float]] = field(default_factory=list)


class FinalizeOrchestrator:
    """Orchestrates the Finalize phase.
    
    Provides a unified interface for:
    - Entity browsing and filtering
    - Entity editing
    - Merge suggestions and execution
    - Search operations
    
    Usage:
        finalize = FinalizeOrchestrator(state)
        
        # Browse entities
        actors = finalize.get_entities(EntityType.ACTOR)
        
        # Search
        results = finalize.search("John")
        
        # Get merge suggestions
        suggestions = finalize.get_merge_suggestions()
        for a, b, score in suggestions:
            finalize.merge(a, b)
    """
    
    def __init__(self, state: "ForgeState"):
        """Initialize the orchestrator.
        
        Args:
            state: Application state
        """
        self.state = state
        self.manager = EntityManager(state)
        self.merger = EntityMerger(state)
        self.context = FinalizeContext()
    
    # ========== Mode Management ==========
    
    def set_mode(self, mode: FinalizeMode) -> None:
        """Set the current Finalize mode."""
        self.context.mode = mode
        logger.debug(f"Finalize mode: {mode.value}")
    
    def select_entity(self, entity_id: str) -> Entity | None:
        """Select an entity for viewing/editing.
        
        Args:
            entity_id: Entity ID to select
            
        Returns:
            Selected entity or None
        """
        entity = self.manager.get(entity_id)
        if entity:
            self.context.selected_entity_id = entity_id
        return entity
    
    def get_selected(self) -> Entity | None:
        """Get the currently selected entity."""
        if self.context.selected_entity_id:
            return self.manager.get(self.context.selected_entity_id)
        return None
    
    # ========== Entity Operations ==========
    
    def get_entities(
        self,
        entity_type: EntityType | None = None,
    ) -> list[Entity]:
        """Get entities, optionally filtered by type.
        
        Args:
            entity_type: Optional type filter
            
        Returns:
            List of entities
        """
        if entity_type:
            return self.manager.get_by_type(entity_type)
        return self.manager.get_all()
    
    def get_entity(self, entity_id: str) -> Entity | None:
        """Get a single entity by ID."""
        return self.manager.get(entity_id)
    
    def create_entity(
        self,
        name: str,
        entity_type: EntityType,
        description: str = "",
        aliases: list[str] | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> Entity:
        """Create a new entity.
        
        Args:
            name: Entity name
            entity_type: Type of entity
            description: Description
            aliases: List of aliases
            attributes: Custom attributes
            
        Returns:
            Created entity
        """
        from forge.utils.ids import generate_entity_id
        
        entity = Entity(
            id=generate_entity_id(entity_type),
            name=name,
            type=entity_type,
            description=description,
            aliases=aliases or [],
            attributes=attributes or {},
        )
        
        return self.manager.create(entity)
    
    def update_entity(self, entity: Entity) -> Entity:
        """Update an entity.
        
        Args:
            entity: Entity with updated values
            
        Returns:
            Updated entity
        """
        return self.manager.update(entity)
    
    def delete_entity(self, entity_id: str) -> bool:
        """Delete an entity.
        
        Args:
            entity_id: ID of entity to delete
            
        Returns:
            True if deleted
        """
        return self.manager.delete(entity_id)
    
    # ========== Search ==========
    
    def search(
        self,
        query: str,
        entity_types: list[EntityType] | None = None,
        semantic: bool = False,
        limit: int = 50,
    ) -> list[Entity]:
        """Search for entities.
        
        Args:
            query: Search query
            entity_types: Optional type filter
            semantic: Whether to use semantic search
            limit: Maximum results
            
        Returns:
            Matching entities
        """
        self.context.search_query = query
        
        if semantic:
            results = self.manager.search_semantic(query, top_k=limit)
            entities = [e for e, _ in results]
            if entity_types:
                entities = [e for e in entities if e.type in entity_types]
            return entities
        else:
            return self.manager.search(query, entity_types, limit)
    
    # ========== Merge Operations ==========
    
    def get_merge_suggestions(
        self,
        threshold: float = 0.85,
    ) -> list[tuple[Entity, Entity, float]]:
        """Get merge suggestions.
        
        Args:
            threshold: Minimum similarity threshold
            
        Returns:
            List of (entity_a, entity_b, similarity) tuples
        """
        suggestions = self.merger.suggest_merges(threshold)
        self.context.merge_candidates = suggestions
        return suggestions
    
    def preview_merge(
        self,
        primary: Entity,
        secondary: Entity,
    ) -> MergePreview:
        """Preview a merge operation.
        
        Args:
            primary: Entity to keep
            secondary: Entity to merge in
            
        Returns:
            MergePreview
        """
        return self.merger.preview_merge(primary, secondary)
    
    def merge(
        self,
        primary: Entity,
        secondary: Entity,
        reason: str = "Manual merge",
    ) -> Entity:
        """Execute a merge.
        
        Args:
            primary: Entity to keep
            secondary: Entity to merge in
            reason: Reason for merge
            
        Returns:
            Merged entity
        """
        return self.merger.merge(primary, secondary, reason=reason)
    
    # ========== Stats ==========
    
    def get_stats(self) -> dict[str, Any]:
        """Get Finalize statistics.
        
        Returns:
            Statistics dict
        """
        db_stats = self.state.db.get_stats()
        
        type_counts = {}
        for entity_type in EntityType:
            count = self.manager.count(entity_type)
            if count > 0:
                type_counts[entity_type.value] = count
        
        return {
            **db_stats,
            "type_counts": type_counts,
            "mode": self.context.mode.value,
            "selected_entity": self.context.selected_entity_id,
        }
